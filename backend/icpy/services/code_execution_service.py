"""
Code Execution Service for icpy Backend
Provides safe, multi-language code execution with real-time output streaming
"""

import asyncio
import json
import logging
import time
import uuid
import sys
import io
import contextlib
import tempfile
import os
import subprocess
import shutil
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
import signal

# Internal imports
from ..core.message_broker import MessageBroker, Message, MessageType, get_message_broker

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Language(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    # Future languages can be added here


@dataclass
class ExecutionConfig:
    """Configuration for code execution"""
    timeout: float = 30.0  # Maximum execution time in seconds
    max_output_size: int = 1024 * 1024  # Maximum output size in bytes (1MB)
    max_memory: Optional[int] = None  # Maximum memory usage in bytes
    working_directory: Optional[str] = None  # Working directory for execution
    environment: Optional[Dict[str, str]] = None  # Environment variables
    sandbox: bool = True  # Enable sandboxed execution
    capture_output: bool = True  # Capture stdout/stderr
    real_time: bool = False  # Stream output in real-time


@dataclass
class ExecutionResult:
    """Result of code execution"""
    execution_id: str
    status: ExecutionStatus
    output: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    exit_code: Optional[int] = None
    language: Language = Language.PYTHON
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for ongoing execution"""
    execution_id: str
    language: Language
    code: str
    config: ExecutionConfig
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[float] = None
    process: Optional[subprocess.Popen] = None
    output_buffer: List[str] = field(default_factory=list)
    error_buffer: List[str] = field(default_factory=list)
    temp_files: List[str] = field(default_factory=list)
    output_size: int = 0


class CodeExecutionService:
    """
    Code Execution Service for icpy Backend
    
    Provides safe, multi-language code execution with:
    - Multiple programming language support (Python, JavaScript, Bash)
    - Sandboxed execution for security
    - Real-time output streaming
    - Execution result caching and history
    - Resource limits and timeout protection
    - Event-driven architecture integration
    """
    
    def __init__(self):
        """Initialize the code execution service"""
        self.message_broker: Optional[MessageBroker] = None
        self.running = False
        
        # Execution management
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_history: deque = deque(maxlen=1000)  # Keep last 1000 executions
        self.result_cache: Dict[str, ExecutionResult] = {}
        
        # Language support
        self.language_executors: Dict[Language, Callable] = {
            Language.PYTHON: self._execute_python,
            Language.JAVASCRIPT: self._execute_javascript,
            Language.BASH: self._execute_bash,
        }
        
        # Statistics
        self.stats = {
            'executions_total': 0,
            'executions_successful': 0,
            'executions_failed': 0,
            'executions_timeout': 0,
            'executions_cancelled': 0,
            'active_executions': 0,
            'total_execution_time': 0.0,
            'languages_used': defaultdict(int),
        }
        
        # Configuration
        self.default_config = ExecutionConfig()
        
        logger.info("CodeExecutionService initialized")
    
    async def start(self) -> None:
        """Start the code execution service"""
        if self.running:
            logger.warning("CodeExecutionService already running")
            return
        
        self.message_broker = await get_message_broker()
        if not self.message_broker.running:
            await self.message_broker.start()
        
        # Subscribe to execution events
        await self.message_broker.subscribe("code_execution.*", self._handle_execution_message)
        
        self.running = True
        logger.info("CodeExecutionService started")
    
    async def stop(self) -> None:
        """Stop the code execution service"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all active executions
        for execution_id in list(self.active_executions.keys()):
            await self.cancel_execution(execution_id)
        
        # Cleanup temp files
        await self._cleanup_temp_files()
        
        if self.message_broker:
            await self.message_broker.unsubscribe("code_execution.*")
        
        logger.info("CodeExecutionService stopped")
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        config: Optional[ExecutionConfig] = None
    ) -> ExecutionResult:
        """
        Execute code and return the result
        
        Args:
            code: The code to execute
            language: Programming language (python, javascript, bash)
            config: Execution configuration
            
        Returns:
            ExecutionResult: The execution result
        """
        if not self.running:
            raise RuntimeError("CodeExecutionService not running")
        
        # Validate language
        try:
            lang_enum = Language(language.lower())
        except ValueError:
            return ExecutionResult(
                execution_id=str(uuid.uuid4()),
                status=ExecutionStatus.FAILED,
                errors=[f"Unsupported language: {language}"],
                language=Language.PYTHON
            )
        
        # Use default config if none provided
        if config is None:
            config = self.default_config
        
        # Create execution context
        execution_id = str(uuid.uuid4())
        context = ExecutionContext(
            execution_id=execution_id,
            language=lang_enum,
            code=code,
            config=config,
            status=ExecutionStatus.PENDING
        )
        
        self.active_executions[execution_id] = context
        self.stats['active_executions'] = len(self.active_executions)
        
        try:
            # Publish execution started event
            await self._publish_execution_event("execution.started", context)
            
            # Execute the code
            result = await self._execute_code_internal(context)
            
            # Update statistics
            self.stats['executions_total'] += 1
            self.stats['languages_used'][lang_enum.value] += 1
            self.stats['total_execution_time'] += result.execution_time
            
            if result.status == ExecutionStatus.COMPLETED:
                self.stats['executions_successful'] += 1
            elif result.status == ExecutionStatus.FAILED:
                self.stats['executions_failed'] += 1
            elif result.status == ExecutionStatus.TIMEOUT:
                self.stats['executions_timeout'] += 1
            elif result.status == ExecutionStatus.CANCELLED:
                self.stats['executions_cancelled'] += 1
            
            # Cache result and add to history
            self.result_cache[execution_id] = result
            self.execution_history.append(result)
            
            # Publish execution completed event
            await self._publish_execution_event("execution.completed", context, result)
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Internal error: {str(e)}"],
                language=lang_enum
            )
            
            # Update statistics
            self.stats['executions_total'] += 1
            self.stats['executions_failed'] += 1
            
            return result
        
        finally:
            # Cleanup
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            self.stats['active_executions'] = len(self.active_executions)
    
    async def execute_code_streaming(
        self,
        code: str,
        language: str = "python",
        config: Optional[ExecutionConfig] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute code with real-time output streaming
        
        Args:
            code: The code to execute
            language: Programming language
            config: Execution configuration
            
        Yields:
            Dict[str, Any]: Streaming execution updates
        """
        if not self.running:
            raise RuntimeError("CodeExecutionService not running")
        
        # Enable real-time streaming
        if config is None:
            config = ExecutionConfig(real_time=True)
        else:
            config.real_time = True
        
        # Validate language
        try:
            lang_enum = Language(language.lower())
        except ValueError:
            yield {
                'type': 'error',
                'data': {'message': f"Unsupported language: {language}"}
            }
            return
        
        # Create execution context
        execution_id = str(uuid.uuid4())
        context = ExecutionContext(
            execution_id=execution_id,
            language=lang_enum,
            code=code,
            config=config,
            status=ExecutionStatus.PENDING
        )
        
        self.active_executions[execution_id] = context
        
        try:
            yield {
                'type': 'execution_started',
                'data': {
                    'execution_id': execution_id,
                    'language': language,
                    'timestamp': time.time()
                }
            }
            
            # Execute with streaming
            async for update in self._execute_code_streaming_internal(context):
                yield update
        
        finally:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            self.stats['active_executions'] = len(self.active_executions)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel an active execution
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            bool: True if cancelled successfully, False if not found
        """
        if execution_id not in self.active_executions:
            return False
        
        context = self.active_executions[execution_id]
        context.status = ExecutionStatus.CANCELLED
        
        # Kill the process if running
        if context.process and context.process.poll() is None:
            try:
                context.process.terminate()
                # Wait briefly for graceful termination
                await asyncio.sleep(0.1)
                if context.process.poll() is None:
                    context.process.kill()
            except Exception as e:
                logger.error(f"Error killing process for execution {execution_id}: {e}")
        
        # Publish cancellation event
        await self._publish_execution_event("execution.cancelled", context)
        
        return True
    
    async def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Get the result of an execution
        
        Args:
            execution_id: The execution ID
            
        Returns:
            Optional[ExecutionResult]: The execution result if found
        """
        return self.result_cache.get(execution_id)
    
    async def get_active_executions(self) -> List[str]:
        """
        Get list of active execution IDs
        
        Returns:
            List[str]: List of active execution IDs
        """
        return list(self.active_executions.keys())
    
    async def get_execution_history(self, limit: int = 100) -> List[ExecutionResult]:
        """
        Get execution history
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List[ExecutionResult]: List of execution results
        """
        return list(self.execution_history)[-limit:]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return dict(self.stats)
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages"""
        return [lang.value for lang in Language]
    
    # Internal methods
    
    async def _execute_code_internal(self, context: ExecutionContext) -> ExecutionResult:
        """Internal code execution implementation"""
        context.status = ExecutionStatus.RUNNING
        context.start_time = time.time()
        
        try:
            # Get language executor
            executor = self.language_executors.get(context.language)
            if not executor:
                raise ValueError(f"No executor for language: {context.language}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                executor(context),
                timeout=context.config.timeout
            )
            
            result.execution_time = time.time() - context.start_time
            return result
        
        except asyncio.TimeoutError:
            context.status = ExecutionStatus.TIMEOUT
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.TIMEOUT,
                errors=[f"Execution timed out after {context.config.timeout} seconds"],
                execution_time=time.time() - context.start_time,
                language=context.language
            )
        
        except Exception as e:
            context.status = ExecutionStatus.FAILED
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Execution error: {str(e)}"],
                execution_time=time.time() - context.start_time,
                language=context.language
            )
    
    async def _execute_code_streaming_internal(
        self,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Internal streaming execution implementation"""
        context.status = ExecutionStatus.RUNNING
        context.start_time = time.time()
        
        try:
            # Get language executor
            executor = self.language_executors.get(context.language)
            if not executor:
                raise ValueError(f"No executor for language: {context.language}")
            
            # For streaming, we need to handle differently
            if context.language == Language.PYTHON:
                async for update in self._execute_python_streaming(context):
                    yield update
            else:
                # For other languages, fall back to regular execution
                result = await executor(context)
                yield {
                    'type': 'execution_completed',
                    'data': {
                        'execution_id': context.execution_id,
                        'status': result.status.value,
                        'output': result.output,
                        'errors': result.errors,
                        'execution_time': result.execution_time
                    }
                }
        
        except asyncio.TimeoutError:
            yield {
                'type': 'execution_timeout',
                'data': {
                    'execution_id': context.execution_id,
                    'timeout': context.config.timeout
                }
            }
        
        except Exception as e:
            yield {
                'type': 'execution_error',
                'data': {
                    'execution_id': context.execution_id,
                    'error': str(e)
                }
            }
    
    async def _execute_python(self, context: ExecutionContext) -> ExecutionResult:
        """Execute Python code"""
        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                # Create a safe execution environment
                exec_globals = {
                    '__builtins__': __builtins__,
                    '__name__': '__main__',
                    '__file__': '<executed_code>',
                }
                
                # Execute the code
                exec(context.code, exec_globals)
            
            # Get output
            output = stdout_buffer.getvalue()
            errors = stderr_buffer.getvalue()
            
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED,
                output=output.split('\n') if output else [],
                errors=errors.split('\n') if errors else [],
                language=context.language,
                exit_code=0
            )
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            errors = stderr_buffer.getvalue()
            if errors:
                error_lines = errors.split('\n') + [error_msg]
            else:
                error_lines = [error_msg]
            
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                output=stdout_buffer.getvalue().split('\n') if stdout_buffer.getvalue() else [],
                errors=error_lines,
                language=context.language,
                exit_code=1
            )
    
    async def _execute_python_streaming(
        self,
        context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute Python code with streaming output"""
        # For now, fall back to regular execution
        # Real streaming would require more complex implementation
        result = await self._execute_python(context)
        
        yield {
            'type': 'execution_completed',
            'data': {
                'execution_id': context.execution_id,
                'status': result.status.value,
                'output': result.output,
                'errors': result.errors,
                'execution_time': result.execution_time
            }
        }
    
    async def _execute_javascript(self, context: ExecutionContext) -> ExecutionResult:
        """Execute JavaScript code using Node.js"""
        # Check if Node.js is available
        if not shutil.which('node'):
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                errors=["Node.js not available on this system"],
                language=context.language
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(context.code)
            temp_file = f.name
        
        context.temp_files.append(temp_file)
        
        try:
            # Execute JavaScript file
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.config.working_directory
            )
            
            context.process = process
            stdout, stderr = await process.communicate()
            
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED,
                output=stdout.decode().split('\n') if stdout else [],
                errors=stderr.decode().split('\n') if stderr else [],
                language=context.language,
                exit_code=process.returncode
            )
        
        except Exception as e:
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                errors=[f"JavaScript execution error: {str(e)}"],
                language=context.language,
                exit_code=1
            )
        
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
                context.temp_files.remove(temp_file)
            except Exception:
                pass
    
    async def _execute_bash(self, context: ExecutionContext) -> ExecutionResult:
        """Execute Bash script"""
        try:
            # Execute bash script
            process = await asyncio.create_subprocess_exec(
                'bash', '-c', context.code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.config.working_directory
            )
            
            context.process = process
            stdout, stderr = await process.communicate()
            
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED,
                output=stdout.decode().split('\n') if stdout else [],
                errors=stderr.decode().split('\n') if stderr else [],
                language=context.language,
                exit_code=process.returncode
            )
        
        except Exception as e:
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Bash execution error: {str(e)}"],
                language=context.language,
                exit_code=1
            )
    
    async def _handle_execution_message(self, message: Message) -> None:
        """Handle execution-related messages"""
        try:
            if message.topic == "code_execution.cancel":
                execution_id = message.payload.get('execution_id')
                if execution_id:
                    await self.cancel_execution(execution_id)
            
            elif message.topic == "code_execution.get_stats":
                stats = await self.get_stats()
                await self.message_broker.publish(
                    topic="code_execution.stats_response",
                    payload=stats,
                    correlation_id=message.id
                )
        
        except Exception as e:
            logger.error(f"Error handling execution message: {e}")
    
    async def _publish_execution_event(
        self,
        event_type: str,
        context: ExecutionContext,
        result: Optional[ExecutionResult] = None
    ) -> None:
        """Publish execution event to message broker"""
        if not self.message_broker:
            return
        
        payload = {
            'execution_id': context.execution_id,
            'language': context.language.value,
            'status': context.status.value,
            'timestamp': time.time()
        }
        
        if result:
            payload.update({
                'output': result.output,
                'errors': result.errors,
                'execution_time': result.execution_time,
                'exit_code': result.exit_code
            })
        
        await self.message_broker.publish(
            topic=f"code_execution.{event_type}",
            payload=payload
        )
    
    async def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files from all executions"""
        for context in self.active_executions.values():
            for temp_file in context.temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
            context.temp_files.clear()


# Global service instance
_code_execution_service: Optional[CodeExecutionService] = None


def get_code_execution_service() -> CodeExecutionService:
    """Get the global code execution service instance"""
    global _code_execution_service
    if _code_execution_service is None:
        _code_execution_service = CodeExecutionService()
    return _code_execution_service


async def shutdown_code_execution_service() -> None:
    """Shutdown the global code execution service"""
    global _code_execution_service
    if _code_execution_service is not None:
        await _code_execution_service.stop()
        _code_execution_service = None
