"""
Timeout handling for task execution.
"""

import threading
from typing import Optional, Dict
from contextlib import contextmanager

from colorama import Fore, Style


class TimeoutError(Exception):
    """Raised when a task times out."""
    pass


class TimeoutManager:
    """
    Manages timeouts for task execution.
    """
    
    def __init__(self, default_timeout: Optional[float] = None):
        """
        Initialize timeout manager.
        
        Args:
            default_timeout: Default timeout in seconds (None for no timeout)
        """
        self.default_timeout = default_timeout
        self.active_timeouts: Dict[str, threading.Timer] = {}
    
    @contextmanager
    def timeout_context(self, timeout: Optional[float], task_id: str):
        """
        Context manager for timeout handling.
        
        Args:
            timeout: Timeout in seconds (None to use default, 0 for no timeout)
            task_id: Task identifier for logging
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if timeout is None or timeout <= 0:
            # No timeout
            yield
            return
        
        def _timeout_handler():
            raise TimeoutError(f"Task {task_id} timed out after {timeout}s")
        
        timer = threading.Timer(timeout, _timeout_handler)
        timer.start()
        self.active_timeouts[task_id] = timer
        
        try:
            yield
        finally:
            if task_id in self.active_timeouts:
                self.active_timeouts[task_id].cancel()
                del self.active_timeouts[task_id]
    
    def cancel_timeout(self, task_id: str) -> None:
        """
        Cancel timeout for a task.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self.active_timeouts:
            self.active_timeouts[task_id].cancel()
            del self.active_timeouts[task_id]
    
    def check_timeout(self, start_time: float, timeout: Optional[float], task_id: str) -> bool:
        """
        Check if a task has timed out.
        
        Args:
            start_time: Task start time
            timeout: Timeout in seconds
            task_id: Task identifier
            
        Returns:
            True if timed out, False otherwise
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if timeout is None or timeout <= 0:
            return False
        
        import time
        elapsed = time.time() - start_time
        return elapsed >= timeout
    
    def get_remaining_time(self, start_time: float, timeout: Optional[float]) -> Optional[float]:
        """
        Get remaining time for a task.
        
        Args:
            start_time: Task start time
            timeout: Timeout in seconds
            
        Returns:
            Remaining time in seconds, or None if no timeout
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if timeout is None or timeout <= 0:
            return None
        
        import time
        elapsed = time.time() - start_time
        remaining = timeout - elapsed
        return max(0, remaining)

