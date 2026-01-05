"""
Core task execution engine with hierarchical state machine.
"""

import time
import threading
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_HUMAN = "waiting_human"


@dataclass
class TaskNode:
    """Represents a single task node in the execution tree."""
    id: str
    task: str
    action: str
    parallel: bool
    human_gate: bool
    depends_on: List[str]
    sub_tasks: List['TaskNode']
    status: TaskStatus = TaskStatus.PENDING
    parent: Optional['TaskNode'] = None
    task_path: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def __post_init__(self):
        """Initialize task path after creation."""
        if not self.task_path:
            if self.parent:
                self.task_path = f"{self.parent.task_path}/{self.id}"
            else:
                self.task_path = self.id


class TaskEngine:
    """
    Main task orchestration engine with support for:
    - Infinite nesting of tasks
    - Parallel execution
    - Dependency management
    - Human-in-the-loop gates
    - State tracking
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the task engine.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.root_node: Optional[TaskNode] = None
        self.all_nodes: Dict[str, TaskNode] = {}
        self.completed_count = 0
        self.total_count = 0
        self.lock = threading.Lock()
        self.human_gate_events: Dict[str, threading.Event] = {}
        self.retry_manager = None
        self.timeout_manager = None
    
    def execute(self, config: Dict[str, Any]) -> None:
        """
        Execute a task configuration.
        
        Args:
            config: Task configuration dictionary
        """
        print(f"\n{Fore.CYAN}{Style.BRIGHT}🧶 Loom: Starting Task Execution{Style.RESET_ALL}\n")
        
        # Build task tree
        self.root_node = self._build_task_tree(config, parent=None)
        
        # Count total tasks
        self.total_count = self._count_tasks(self.root_node)
        
        print(f"{Fore.GREEN}📊 Total tasks in tree: {self.total_count}{Style.RESET_ALL}\n")
        
        # Execute root task
        self._execute_node(self.root_node)
        
        # Print final summary
        self._print_summary()
    
    def _build_task_tree(self, config: Dict[str, Any], parent: Optional[TaskNode] = None) -> TaskNode:
        """
        Recursively build the task tree from configuration.
        
        Args:
            config: Task configuration
            parent: Parent task node
            
        Returns:
            Constructed task node
        """
        node_id = config.get("id", "root" if parent is None else f"task_{len(self.all_nodes)}")
        
        node = TaskNode(
            id=node_id,
            task=config["task"],
            action=config.get("action", ""),
            parallel=config.get("parallel", False),
            human_gate=config.get("human_gate", False),
            depends_on=config.get("depends_on", []),
            sub_tasks=[],
            parent=parent
        )
        
        # Set task path
        if parent:
            node.task_path = f"{parent.task_path}/{node_id}"
        else:
            node.task_path = node_id
        
        # Register node
        self.all_nodes[node_id] = node
        
        # Build sub-tasks
        for sub_config in config.get("sub_tasks", []):
            sub_node = self._build_task_tree(sub_config, parent=node)
            node.sub_tasks.append(sub_node)
        
        return node
    
    def _count_tasks(self, node: TaskNode) -> int:
        """Recursively count all tasks in the tree."""
        count = 1
        for sub_task in node.sub_tasks:
            count += self._count_tasks(sub_task)
        return count
    
    def _execute_node(self, node: TaskNode) -> None:
        """
        Execute a single task node.
        
        Args:
            node: Task node to execute
        """
        # Check dependencies
        if not self._check_dependencies(node):
            node.status = TaskStatus.BLOCKED
            if self.verbose:
                print(f"{Fore.YELLOW}⏸️  [{node.task_path}] Blocked by dependencies{Style.RESET_ALL}")
            return
        
        # Handle human gate
        if node.human_gate:
            if not self._handle_human_gate(node):
                return
        
        # Update status
        node.status = TaskStatus.RUNNING
        node.start_time = time.time()
        
        self._log_task_start(node)
        
        try:
            # Execute action with timeout if configured
            if node.action:
                if self.timeout_manager:
                    with self.timeout_manager.timeout_context(
                        getattr(node, 'timeout', None),
                        node.id
                    ):
                        result = self._execute_action(node)
                        node.result = result
                else:
                    result = self._execute_action(node)
                    node.result = result
            
            # Execute sub-tasks
            if node.sub_tasks:
                if node.parallel:
                    self._execute_parallel_subtasks(node)
                else:
                    self._execute_sequential_subtasks(node)
            
            # Mark as completed
            node.status = TaskStatus.COMPLETED
            node.end_time = time.time()
            
            with self.lock:
                self.completed_count += 1
            
            self._log_task_complete(node)
            
        except Exception as e:
            # Check if we should retry
            if self.retry_manager and self.retry_manager.should_retry(node):
                try:
                    result = self.retry_manager.retry_task(node, self._execute_node)
                    return
                except Exception as retry_error:
                    # Retry failed, mark as failed
                    pass
            
            node.status = TaskStatus.FAILED
            node.error = str(e)
            node.end_time = time.time()
            
            with self.lock:
                self.completed_count += 1
            
            self._log_task_error(node, e)
            
            # Don't raise if retry manager is handling it
            if not (self.retry_manager and self.retry_manager.should_retry(node)):
                raise
    
    def _check_dependencies(self, node: TaskNode) -> bool:
        """
        Check if all dependencies are satisfied.
        
        Args:
            node: Task node to check
            
        Returns:
            True if all dependencies are satisfied
        """
        if not node.depends_on:
            return True
        
        for dep_id in node.depends_on:
            if dep_id not in self.all_nodes:
                if self.verbose:
                    print(f"{Fore.RED}⚠️  Dependency '{dep_id}' not found{Style.RESET_ALL}")
                return False
            
            dep_node = self.all_nodes[dep_id]
            if dep_node.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def _handle_human_gate(self, node: TaskNode) -> bool:
        """
        Handle human-in-the-loop gate.
        
        Args:
            node: Task node with human gate
            
        Returns:
            True if gate is passed, False otherwise
        """
        node.status = TaskStatus.WAITING_HUMAN
        
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⏸️  HUMAN GATE: {node.task_path}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Task: {node.task}{Style.RESET_ALL}")
        if node.action:
            print(f"{Fore.CYAN}Action: {node.action}{Style.RESET_ALL}")
        
        if node.sub_tasks:
            print(f"{Fore.CYAN}Sub-tasks: {len(node.sub_tasks)}{Style.RESET_ALL}")
        
        response = input(f"\n{Fore.GREEN}Proceed? (y/n/edit): {Style.RESET_ALL}").strip().lower()
        
        if response == 'n':
            print(f"{Fore.RED}❌ Gate rejected. Stopping execution.{Style.RESET_ALL}")
            return False
        elif response == 'edit':
            print(f"{Fore.YELLOW}✏️  Edit mode not yet implemented{Style.RESET_ALL}")
            return False
        
        return True
    
    def _execute_action(self, node: TaskNode) -> Any:
        """
        Execute the action for a task node.
        
        Args:
            node: Task node to execute
            
        Returns:
            Action result
        """
        # In a real implementation, this would integrate with AI models
        # For now, we simulate execution
        if self.verbose:
            print(f"{Fore.BLUE}   Executing action: {node.action}{Style.RESET_ALL}")
        
        # Simulate work
        time.sleep(0.1)
        
        return {"status": "executed", "action": node.action}
    
    def _execute_parallel_subtasks(self, node: TaskNode) -> None:
        """
        Execute sub-tasks in parallel.
        
        Args:
            node: Parent task node
        """
        threads = []
        
        for sub_task in node.sub_tasks:
            thread = threading.Thread(target=self._execute_node, args=(sub_task,))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
    
    def _execute_sequential_subtasks(self, node: TaskNode) -> None:
        """
        Execute sub-tasks sequentially.
        
        Args:
            node: Parent task node
        """
        for sub_task in node.sub_tasks:
            self._execute_node(sub_task)
    
    def _log_task_start(self, node: TaskNode) -> None:
        """Log task start."""
        progress = (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0
        print(f"{Fore.GREEN}▶️  [{node.task_path}] {node.task} {Style.DIM}({progress:.1f}%){Style.RESET_ALL}")
    
    def _log_task_complete(self, node: TaskNode) -> None:
        """Log task completion."""
        duration = node.end_time - node.start_time if node.end_time and node.start_time else 0
        progress = (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0
        print(f"{Fore.GREEN}✅ [{node.task_path}] Completed in {duration:.2f}s {Style.DIM}({progress:.1f}%){Style.RESET_ALL}")
    
    def _log_task_error(self, node: TaskNode, error: Exception) -> None:
        """Log task error."""
        progress = (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0
        print(f"{Fore.RED}❌ [{node.task_path}] Failed: {error} {Style.DIM}({progress:.1f}%){Style.RESET_ALL}")
    
    def _print_summary(self) -> None:
        """Print execution summary."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}📊 Execution Summary{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Completed: {self.completed_count}/{self.total_count} tasks{Style.RESET_ALL}")
        
        # Count by status
        status_counts = {}
        for node in self.all_nodes.values():
            status = node.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

