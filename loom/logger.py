"""
Logging module for Loom task execution.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from colorama import Fore, Style


class LoomLogger:
    """
    Custom logger for Loom with file and console output.
    """
    
    def __init__(
        self,
        name: str = "loom",
        log_file: Optional[Path] = None,
        verbose: bool = False
    ):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            log_file: Path to log file (optional)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        if self.verbose:
            self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def task_start(self, task_path: str, task_name: str, progress: float) -> None:
        """Log task start."""
        self.info(f"▶️  [{task_path}] {task_name} ({progress:.1f}%)")
    
    def task_complete(self, task_path: str, duration: float, progress: float) -> None:
        """Log task completion."""
        self.info(f"✅ [{task_path}] Completed in {duration:.2f}s ({progress:.1f}%)")
    
    def task_error(self, task_path: str, error: str, progress: float) -> None:
        """Log task error."""
        self.error(f"❌ [{task_path}] Failed: {error} ({progress:.1f}%)")
    
    def task_blocked(self, task_path: str, reason: str) -> None:
        """Log task blocked."""
        self.warning(f"⏸️  [{task_path}] Blocked: {reason}")
    
    def human_gate(self, task_path: str, task_name: str) -> None:
        """Log human gate."""
        self.info(f"⏸️  HUMAN GATE: [{task_path}] {task_name}")
    
    def execution_start(self, total_tasks: int) -> None:
        """Log execution start."""
        self.info(f"🧶 Loom: Starting Task Execution ({total_tasks} tasks)")
    
    def execution_complete(self, completed: int, total: int) -> None:
        """Log execution complete."""
        self.info(f"📊 Execution Complete: {completed}/{total} tasks")
    
    def summary(self, summary_data: dict) -> None:
        """Log execution summary."""
        self.info("📊 Execution Summary")
        for key, value in summary_data.items():
            self.info(f"  {key}: {value}")

