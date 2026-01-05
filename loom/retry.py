"""
Retry mechanism for failed tasks.
"""

import time
from typing import Callable, Any, Optional, Dict
from enum import Enum

from loom.engine import TaskNode, TaskStatus
from colorama import Fore, Style


class RetryStrategy(Enum):
    """Retry strategies."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


class RetryManager:
    """
    Manages retry logic for failed tasks.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum number of retries
            strategy: Retry strategy
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_counts: Dict[str, int] = {}
    
    def should_retry(self, node: TaskNode) -> bool:
        """
        Check if a task should be retried.
        
        Args:
            node: Task node that failed
            
        Returns:
            True if should retry, False otherwise
        """
        if node.status != TaskStatus.FAILED:
            return False
        
        retry_count = self.retry_counts.get(node.id, 0)
        return retry_count < self.max_retries
    
    def get_retry_delay(self, node: TaskNode) -> float:
        """
        Get the delay before retrying a task.
        
        Args:
            node: Task node to retry
            
        Returns:
            Delay in seconds
        """
        retry_count = self.retry_counts.get(node.id, 0)
        
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (2 ** retry_count)
            return min(delay, self.max_delay)
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * (retry_count + 1)
            return min(delay, self.max_delay)
        elif self.strategy == RetryStrategy.FIXED_DELAY:
            return self.base_delay
        else:
            return self.base_delay
    
    def record_retry(self, node: TaskNode) -> None:
        """
        Record that a task is being retried.
        
        Args:
            node: Task node being retried
        """
        self.retry_counts[node.id] = self.retry_counts.get(node.id, 0) + 1
    
    def reset_retry_count(self, node: TaskNode) -> None:
        """
        Reset retry count for a node.
        
        Args:
            node: Task node
        """
        if node.id in self.retry_counts:
            del self.retry_counts[node.id]
    
    def get_retry_count(self, node: TaskNode) -> int:
        """
        Get current retry count for a node.
        
        Args:
            node: Task node
            
        Returns:
            Retry count
        """
        return self.retry_counts.get(node.id, 0)
    
    def retry_task(self, node: TaskNode, execute_func: Callable[[TaskNode], Any]) -> Any:
        """
        Retry a failed task.
        
        Args:
            node: Task node to retry
            execute_func: Function to execute the task
            
        Returns:
            Task result
        """
        if not self.should_retry(node):
            raise Exception(f"Task {node.id} exceeded max retries ({self.max_retries})")
        
        self.record_retry(node)
        retry_count = self.get_retry_count(node)
        
        delay = self.get_retry_delay(node)
        if delay > 0:
            print(f"{Fore.YELLOW}⏳ Retrying [{node.task_path}] (attempt {retry_count}/{self.max_retries}) after {delay:.1f}s...{Style.RESET_ALL}")
            time.sleep(delay)
        else:
            print(f"{Fore.YELLOW}🔄 Retrying [{node.task_path}] (attempt {retry_count}/{self.max_retries})...{Style.RESET_ALL}")
        
        # Reset status and error
        node.status = TaskStatus.PENDING
        node.error = None
        node.result = None
        
        # Execute
        return execute_func(node)

