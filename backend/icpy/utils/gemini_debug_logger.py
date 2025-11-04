"""
Gemini Debug Logger - Comprehensive logging for debugging Gemini agent issues

This module provides detailed logging to track:
- Message flow from frontend to backend
- Agent processing lifecycle
- API call timing and responses
- Silent failures and hangs
"""

import logging
import time
import functools
from typing import Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class GeminiDebugLogger:
    """Tracks Gemini agent processing with detailed logging"""
    
    def __init__(self):
        self.active_requests = {}
        self.last_activity = {}
        
    def log_message_received(self, session_id: str, content_preview: str, metadata: dict = None):
        """Log when a user message is received"""
        timestamp = datetime.now().isoformat()
        self.last_activity[session_id] = time.time()
        
        logger.info(
            f"[GEMINI-DEBUG] Message received | "
            f"session={session_id} | "
            f"time={timestamp} | "
            f"content_length={len(content_preview)} | "
            f"preview={content_preview[:100]}... | "
            f"metadata={metadata}"
        )
        
    def log_agent_start(self, session_id: str, agent_type: str):
        """Log when agent processing starts"""
        timestamp = datetime.now().isoformat()
        request_id = f"{session_id}_{int(time.time())}"
        self.active_requests[request_id] = {
            'session_id': session_id,
            'agent_type': agent_type,
            'start_time': time.time(),
            'timestamp': timestamp
        }
        
        logger.info(
            f"[GEMINI-DEBUG] Agent processing started | "
            f"request_id={request_id} | "
            f"session={session_id} | "
            f"agent={agent_type} | "
            f"time={timestamp}"
        )
        
        return request_id
        
    def log_api_call(self, request_id: str, model: str, message_count: int):
        """Log when an API call is made"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            elapsed = time.time() - self.active_requests[request_id]['start_time']
            self.active_requests[request_id]['last_api_call'] = time.time()
        else:
            elapsed = 0
            
        logger.info(
            f"[GEMINI-DEBUG] API call initiated | "
            f"request_id={request_id} | "
            f"model={model} | "
            f"messages={message_count} | "
            f"elapsed={elapsed:.2f}s | "
            f"time={timestamp}"
        )
        
    def log_api_response(self, request_id: str, status_code: int, response_size: int = 0):
        """Log when API response is received"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            total_elapsed = time.time() - self.active_requests[request_id]['start_time']
            api_elapsed = time.time() - self.active_requests[request_id].get('last_api_call', time.time())
        else:
            total_elapsed = 0
            api_elapsed = 0
            
        logger.info(
            f"[GEMINI-DEBUG] API response received | "
            f"request_id={request_id} | "
            f"status={status_code} | "
            f"size={response_size} | "
            f"api_time={api_elapsed:.2f}s | "
            f"total_time={total_elapsed:.2f}s | "
            f"time={timestamp}"
        )
        
    def log_streaming_start(self, request_id: str):
        """Log when streaming starts"""
        timestamp = datetime.now().isoformat()
        
        logger.info(
            f"[GEMINI-DEBUG] Streaming started | "
            f"request_id={request_id} | "
            f"time={timestamp}"
        )
        
    def log_streaming_chunk(self, request_id: str, chunk_size: int, chunk_count: int):
        """Log streaming chunk"""
        # Only log every 10th chunk to avoid spam
        if chunk_count % 10 == 0:
            logger.debug(
                f"[GEMINI-DEBUG] Streaming chunk | "
                f"request_id={request_id} | "
                f"chunk_num={chunk_count} | "
                f"size={chunk_size}"
            )
        
    def log_agent_complete(self, request_id: str, total_chars: int, chunk_count: int):
        """Log when agent processing completes"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            total_elapsed = time.time() - self.active_requests[request_id]['start_time']
            session_id = self.active_requests[request_id]['session_id']
            agent_type = self.active_requests[request_id]['agent_type']
            del self.active_requests[request_id]
        else:
            total_elapsed = 0
            session_id = "unknown"
            agent_type = "unknown"
            
        logger.info(
            f"[GEMINI-DEBUG] Agent processing completed | "
            f"request_id={request_id} | "
            f"session={session_id} | "
            f"agent={agent_type} | "
            f"total_time={total_elapsed:.2f}s | "
            f"chars={total_chars} | "
            f"chunks={chunk_count} | "
            f"time={timestamp}"
        )
        
    def log_error(self, request_id: str, error_type: str, error_message: str):
        """Log errors during processing"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            elapsed = time.time() - self.active_requests[request_id]['start_time']
            session_id = self.active_requests[request_id]['session_id']
            agent_type = self.active_requests[request_id]['agent_type']
            del self.active_requests[request_id]
        else:
            elapsed = 0
            session_id = "unknown"
            agent_type = "unknown"
            
        logger.error(
            f"[GEMINI-DEBUG] Error occurred | "
            f"request_id={request_id} | "
            f"session={session_id} | "
            f"agent={agent_type} | "
            f"error_type={error_type} | "
            f"error={error_message} | "
            f"elapsed={elapsed:.2f}s | "
            f"time={timestamp}"
        )
        
    def log_hang_detected(self, request_id: str, hang_duration: float):
        """Log when a potential hang is detected"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            session_id = self.active_requests[request_id]['session_id']
            agent_type = self.active_requests[request_id]['agent_type']
        else:
            session_id = "unknown"
            agent_type = "unknown"
            
        logger.warning(
            f"[GEMINI-DEBUG] Potential hang detected | "
            f"request_id={request_id} | "
            f"session={session_id} | "
            f"agent={agent_type} | "
            f"hang_duration={hang_duration:.2f}s | "
            f"time={timestamp}"
        )
    
    def log_thought_parts_seen(self, request_id: str, parts_count: int, signatures_present: bool, finish_reason: str = None):
        """Log observation of thought signatures and parts in response"""
        timestamp = datetime.now().isoformat()
        
        if request_id in self.active_requests:
            session_id = self.active_requests[request_id]['session_id']
            agent_type = self.active_requests[request_id]['agent_type']
        else:
            session_id = "unknown"
            agent_type = "unknown"
            
        logger.info(
            f"[GEMINI-DEBUG] Thought parts analysis | "
            f"request_id={request_id} | "
            f"session={session_id} | "
            f"agent={agent_type} | "
            f"parts_count={parts_count} | "
            f"signatures_present={signatures_present} | "
            f"finish_reason={finish_reason} | "
            f"time={timestamp}"
        )
        
    def check_for_hangs(self, timeout: float = 60.0):
        """Check for requests that have been active too long"""
        current_time = time.time()
        hung_requests = []
        
        for request_id, request_info in self.active_requests.items():
            elapsed = current_time - request_info['start_time']
            if elapsed > timeout:
                hung_requests.append((request_id, elapsed))
                
        for request_id, duration in hung_requests:
            self.log_hang_detected(request_id, duration)
            
        return hung_requests


# Global instance
_gemini_debug_logger = None

def get_gemini_debug_logger() -> GeminiDebugLogger:
    """Get or create the global Gemini debug logger"""
    global _gemini_debug_logger
    if _gemini_debug_logger is None:
        _gemini_debug_logger = GeminiDebugLogger()
    return _gemini_debug_logger


def log_gemini_function(func: Callable) -> Callable:
    """Decorator to log Gemini-related function calls"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = time.time()
        logger.debug(f"[GEMINI-DEBUG] Function started: {func_name}")
        
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"[GEMINI-DEBUG] Function completed: {func_name} ({elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[GEMINI-DEBUG] Function failed: {func_name} | "
                f"error={str(e)} | "
                f"elapsed={elapsed:.2f}s"
            )
            raise
            
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = time.time()
        logger.debug(f"[GEMINI-DEBUG] Function started: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"[GEMINI-DEBUG] Function completed: {func_name} ({elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[GEMINI-DEBUG] Function failed: {func_name} | "
                f"error={str(e)} | "
                f"elapsed={elapsed:.2f}s"
            )
            raise
            
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
