"""
Workflow Engine for ICPY Agentic Workflows

This module provides workflow execution capabilities with support for sequential,
parallel, and conditional agent execution with dependency resolution.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Set
from pathlib import Path

from ..base_agent import BaseAgent, AgentConfig, AgentMessage, AgentStatus


class WorkflowStatus(Enum):
    """Workflow execution status"""
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Type of workflow task"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    AGENT_HANDOFF = "agent_handoff"


@dataclass
class WorkflowTask:
    """Individual task within a workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_type: TaskType = TaskType.SEQUENTIAL
    agent_id: Optional[str] = None
    agent_config: Optional[AgentConfig] = None
    task_content: str = ""
    dependencies: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution"""
    name: str
    description: str = ""
    tasks: List[WorkflowTask] = field(default_factory=list)
    global_timeout: Optional[int] = None
    auto_save: bool = True
    save_path: Optional[str] = None
    recovery_enabled: bool = True
    parallel_limit: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Current state of workflow execution"""
    workflow_id: str
    status: WorkflowStatus
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    task_results: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, BaseAgent] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


class WorkflowEngine:
    """
    Async workflow execution engine with dependency resolution
    
    Supports sequential, parallel, and conditional execution patterns
    with agent handoff mechanisms and state persistence.
    """
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.workflow_id = str(uuid.uuid4())
        self.state = WorkflowState(
            workflow_id=self.workflow_id,
            status=WorkflowStatus.CREATED
        )
        self.event_handlers = []
        self.running_tasks = {}
        self.task_semaphore = asyncio.Semaphore(config.parallel_limit)
        
    async def initialize(self) -> bool:
        """Initialize workflow and validate configuration"""
        try:
            # Validate task dependencies
            if not self._validate_dependencies():
                raise ValueError("Invalid task dependencies detected")
            
            # Create agents for tasks that need them
            await self._initialize_agents()
            
            self.state.status = WorkflowStatus.READY
            await self._emit_event("workflow_initialized", {"workflow_id": self.workflow_id})
            return True
            
        except Exception as e:
            self.state.status = WorkflowStatus.FAILED
            self.state.error_message = str(e)
            await self._emit_event("workflow_failed", {"error": str(e)})
            return False
    
    async def execute(self) -> bool:
        """Execute the workflow"""
        if self.state.status != WorkflowStatus.READY:
            return False
        
        try:
            self.state.status = WorkflowStatus.RUNNING
            self.state.start_time = datetime.utcnow()
            await self._emit_event("workflow_started", {"workflow_id": self.workflow_id})
            
            # Execute tasks based on dependency graph
            await self._execute_workflow()
            
            if self.state.status == WorkflowStatus.RUNNING:
                self.state.status = WorkflowStatus.COMPLETED
                self.state.end_time = datetime.utcnow()
                await self._emit_event("workflow_completed", {"workflow_id": self.workflow_id})
            
            # Auto-save if enabled
            if self.config.auto_save:
                await self._save_state()
            
            return self.state.status == WorkflowStatus.COMPLETED
            
        except Exception as e:
            self.state.status = WorkflowStatus.FAILED
            self.state.error_message = str(e)
            self.state.end_time = datetime.utcnow()
            await self._emit_event("workflow_failed", {"error": str(e)})
            return False
    
    async def pause(self) -> bool:
        """Pause workflow execution"""
        if self.state.status == WorkflowStatus.RUNNING:
            self.state.status = WorkflowStatus.PAUSED
            
            # Pause all running agents
            for agent in self.state.agents.values():
                await agent.pause()
            
            await self._emit_event("workflow_paused", {"workflow_id": self.workflow_id})
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume workflow execution"""
        if self.state.status == WorkflowStatus.PAUSED:
            self.state.status = WorkflowStatus.RUNNING
            
            # Resume all paused agents
            for agent in self.state.agents.values():
                await agent.resume()
            
            await self._emit_event("workflow_resumed", {"workflow_id": self.workflow_id})
            return True
        return False
    
    async def cancel(self) -> bool:
        """Cancel workflow execution"""
        if self.state.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            self.state.status = WorkflowStatus.CANCELLED
            
            # Stop all running agents
            for agent in self.state.agents.values():
                await agent.stop()
            
            await self._emit_event("workflow_cancelled", {"workflow_id": self.workflow_id})
            return True
        return False
    
    async def add_task(self, task: WorkflowTask) -> bool:
        """Add a task to the workflow"""
        if self.state.status not in [WorkflowStatus.CREATED, WorkflowStatus.READY]:
            return False
        
        self.config.tasks.append(task)
        await self._emit_event("task_added", {"task_id": task.id, "task_name": task.name})
        return True
    
    async def get_task_result(self, task_identifier: str) -> Optional[Any]:
        """Get result of a completed task by ID or name"""
        # First try by task ID
        result = self.state.task_results.get(task_identifier)
        if result is not None:
            return result
        
        # If not found, try to find by task name
        for task in self.config.tasks:
            if task.name == task_identifier:
                return self.state.task_results.get(task.id)
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get workflow status and progress"""
        total_tasks = len(self.config.tasks)
        completed_tasks = len(self.state.completed_tasks)
        
        return {
            'workflow_id': self.workflow_id,
            'name': self.config.name,
            'status': self.state.status.value,
            'progress': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': len(self.state.failed_tasks),
                'percentage': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            'current_task': self.state.current_task,
            'start_time': self.state.start_time.isoformat() if self.state.start_time else None,
            'end_time': self.state.end_time.isoformat() if self.state.end_time else None,
            'error_message': self.state.error_message,
            'agents': {agent_id: agent.get_status() for agent_id, agent in self.state.agents.items()}
        }
    
    def add_event_handler(self, handler: Callable[[str, Dict[str, Any]], None]):
        """Add event handler for workflow events"""
        self.event_handlers.append(handler)
    
    # Private methods
    async def _execute_workflow(self):
        """Execute workflow tasks based on dependency graph"""
        # Build dependency graph
        dependency_graph = self._build_dependency_graph()
        
        # Execute tasks in topological order
        executed_tasks = set()
        
        while len(executed_tasks) < len(self.config.tasks):
            # Find tasks ready to execute (all dependencies satisfied)
            ready_tasks = []
            for task in self.config.tasks:
                if (task.id not in executed_tasks and 
                    all(dep in executed_tasks for dep in task.dependencies)):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                break  # No more tasks can be executed
            
            # Execute ready tasks
            if len(ready_tasks) == 1 or any(task.task_type == TaskType.SEQUENTIAL for task in ready_tasks):
                # Sequential execution
                for task in ready_tasks:
                    await self._execute_task(task)
                    executed_tasks.add(task.id)
            else:
                # Parallel execution
                tasks_to_execute = [task for task in ready_tasks if task.task_type == TaskType.PARALLEL]
                if tasks_to_execute:
                    await self._execute_tasks_parallel(tasks_to_execute)
                    executed_tasks.update(task.id for task in tasks_to_execute)
    
    async def _execute_task(self, task: WorkflowTask):
        """Execute a single task"""
        try:
            self.state.current_task = task.id
            await self._emit_event("task_started", {"task_id": task.id, "task_name": task.name})
            
            # Check conditions if conditional task
            if task.task_type == TaskType.CONDITIONAL:
                if not self._evaluate_conditions(task.conditions):
                    self.state.completed_tasks.append(task.id)
                    await self._emit_event("task_skipped", {"task_id": task.id, "reason": "conditions_not_met"})
                    return
            
            # Get or create agent for task
            agent = await self._get_task_agent(task)
            
            # Execute task with agent
            result = ""
            async for message in agent.execute(task.task_content):
                if message.message_type == "text":
                    result += message.content
                elif message.message_type == "error":
                    raise Exception(message.content)
            
            # Store result
            self.state.task_results[task.id] = result
            self.state.completed_tasks.append(task.id)
            
            await self._emit_event("task_completed", {
                "task_id": task.id, 
                "task_name": task.name,
                "result_length": len(result)
            })
            
        except Exception as e:
            self.state.failed_tasks.append(task.id)
            await self._emit_event("task_failed", {
                "task_id": task.id, 
                "task_name": task.name,
                "error": str(e)
            })
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self._execute_task(task)
            else:
                raise
    
    async def _execute_tasks_parallel(self, tasks: List[WorkflowTask]):
        """Execute multiple tasks in parallel"""
        async with self.task_semaphore:
            coroutines = [self._execute_task(task) for task in tasks]
            await asyncio.gather(*coroutines, return_exceptions=True)
    
    async def _get_task_agent(self, task: WorkflowTask) -> BaseAgent:
        """Get or create agent for task execution"""
        if task.agent_id and task.agent_id in self.state.agents:
            return self.state.agents[task.agent_id]
        
        # Create new agent
        from ..base_agent import DefaultAgent
        
        config = task.agent_config or AgentConfig(
            name=f"agent_{task.id}",
            framework="openai",
            role="task_executor"
        )
        
        agent = DefaultAgent(config)
        await agent.initialize()
        
        agent_id = task.agent_id or agent.agent_id
        self.state.agents[agent_id] = agent
        
        return agent
    
    async def _initialize_agents(self):
        """Initialize agents specified in workflow configuration"""
        for task in self.config.tasks:
            if task.agent_config:
                from ..base_agent import DefaultAgent
                agent = DefaultAgent(task.agent_config)
                await agent.initialize()
                
                agent_id = task.agent_id or agent.agent_id
                self.state.agents[agent_id] = agent
    
    def _validate_dependencies(self) -> bool:
        """Validate that task dependencies form a valid DAG"""
        # Create mapping from task names to IDs for backward compatibility
        task_name_to_id = {task.name: task.id for task in self.config.tasks}
        task_ids = {task.id for task in self.config.tasks}
        task_names = {task.name for task in self.config.tasks}
        
        # Check all dependencies exist (can be either names or IDs)
        for task in self.config.tasks:
            for dep in task.dependencies:
                if dep not in task_ids and dep not in task_names:
                    return False
        
        # Convert name dependencies to ID dependencies for cycle checking
        for task in self.config.tasks:
            resolved_deps = []
            for dep in task.dependencies:
                if dep in task_name_to_id:
                    resolved_deps.append(task_name_to_id[dep])
                elif dep in task_ids:
                    resolved_deps.append(dep)
            task.dependencies = resolved_deps
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id):
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False
                
            visited.add(task_id)
            rec_stack.add(task_id)
            
            # Find task by ID
            task = next((t for t in self.config.tasks if t.id == task_id), None)
            if task:
                for dep in task.dependencies:
                    if has_cycle(dep):
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in self.config.tasks:
            if has_cycle(task.id):
                return False
        
        return True
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph for workflow execution"""
        graph = {}
        for task in self.config.tasks:
            graph[task.id] = task.dependencies.copy()
        return graph
    
    def _evaluate_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Evaluate conditional logic for task execution"""
        if not conditions:
            return True
        
        # Simple condition evaluation - can be extended
        for key, expected_value in conditions.items():
            if key.startswith("task_result:"):
                task_id = key.split(":", 1)[1]
                actual_value = self.state.task_results.get(task_id)
                if actual_value != expected_value:
                    return False
            elif key.startswith("task_status:"):
                task_id = key.split(":", 1)[1]
                if task_id not in self.state.completed_tasks:
                    return False
        
        return True
    
    async def _save_state(self):
        """Save workflow state for recovery"""
        if not self.config.save_path:
            return
        
        state_data = {
            'workflow_id': self.workflow_id,
            'config': {
                'name': self.config.name,
                'description': self.config.description,
                'global_timeout': self.config.global_timeout,
                'auto_save': self.config.auto_save,
                'recovery_enabled': self.config.recovery_enabled,
                'parallel_limit': self.config.parallel_limit,
                'metadata': self.config.metadata
            },
            'state': {
                'status': self.state.status.value,
                'current_task': self.state.current_task,
                'completed_tasks': self.state.completed_tasks,
                'failed_tasks': self.state.failed_tasks,
                'task_results': self.state.task_results,
                'start_time': self.state.start_time.isoformat() if self.state.start_time else None,
                'end_time': self.state.end_time.isoformat() if self.state.end_time else None,
                'error_message': self.state.error_message
            }
        }
        
        save_path = Path(self.config.save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            json.dump(state_data, f, indent=2)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit workflow event to all handlers"""
        event_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'workflow_id': self.workflow_id,
            **data
        }
        
        for handler in self.event_handlers:
            try:
                handler(event_type, event_data)
            except Exception as e:
                print(f"Event handler failed: {e}")


# Workflow builder utility functions
def create_sequential_workflow(name: str, tasks: List[Dict[str, Any]]) -> WorkflowConfig:
    """Create a sequential workflow from task definitions"""
    workflow_tasks = []
    
    for i, task_def in enumerate(tasks):
        task = WorkflowTask(
            name=task_def.get('name', f'task_{i}'),
            task_type=TaskType.SEQUENTIAL,
            task_content=task_def.get('content', ''),
            agent_config=AgentConfig(
                name=task_def.get('agent_name', f'agent_{i}'),
                framework=task_def.get('framework', 'openai'),
                role=task_def.get('role', 'assistant')
            )
        )
        
        # Add dependency on previous task using task ID
        if i > 0:
            task.dependencies = [workflow_tasks[i-1].id]
        
        workflow_tasks.append(task)
    
    return WorkflowConfig(name=name, tasks=workflow_tasks)


def create_parallel_workflow(name: str, tasks: List[Dict[str, Any]]) -> WorkflowConfig:
    """Create a parallel workflow from task definitions"""
    workflow_tasks = []
    
    for i, task_def in enumerate(tasks):
        task = WorkflowTask(
            name=task_def.get('name', f'task_{i}'),
            task_type=TaskType.PARALLEL,
            task_content=task_def.get('content', ''),
            agent_config=AgentConfig(
                name=task_def.get('agent_name', f'agent_{i}'),
                framework=task_def.get('framework', 'openai'),
                role=task_def.get('role', 'assistant')
            )
        )
        
        workflow_tasks.append(task)
    
    return WorkflowConfig(name=name, tasks=workflow_tasks)
