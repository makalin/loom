"""
CLI utility tools for Loom.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from colorama import Fore, Style

from loom.config import load_task_config
from loom.validator import TaskValidator
from loom.state import StateManager
from loom.utils import format_duration, format_timestamp, create_task_summary


def list_tasks(tasks_dir: Path = Path("tasks")) -> None:
    """
    List all available task configurations.
    
    Args:
        tasks_dir: Directory containing task files
    """
    tasks_dir = Path(tasks_dir)
    
    if not tasks_dir.exists():
        print(f"{Fore.RED}❌ Tasks directory not found: {tasks_dir}{Style.RESET_ALL}")
        return
    
    task_files = list(tasks_dir.glob("*.yaml")) + list(tasks_dir.glob("*.yml"))
    
    if not task_files:
        print(f"{Fore.YELLOW}No task files found in {tasks_dir}{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}📋 Available Tasks{Style.RESET_ALL}\n")
    
    for task_file in sorted(task_files):
        try:
            config = load_task_config(task_file)
            task_name = config.get("task", "Unknown")
            print(f"  {Fore.GREEN}•{Style.RESET_ALL} {task_file.name}")
            print(f"    {Fore.CYAN}Task:{Style.RESET_ALL} {task_name}")
            
            # Count sub-tasks
            def _count_subtasks(cfg: Dict[str, Any]) -> int:
                count = len(cfg.get("sub_tasks", []))
                for sub_task in cfg.get("sub_tasks", []):
                    count += _count_subtasks(sub_task)
                return count
            
            subtask_count = _count_subtasks(config)
            if subtask_count > 0:
                print(f"    {Fore.CYAN}Sub-tasks:{Style.RESET_ALL} {subtask_count}")
            print()
        except Exception as e:
            print(f"  {Fore.RED}✗{Style.RESET_ALL} {task_file.name} {Fore.RED}(Error: {e}){Style.RESET_ALL}\n")


def validate_task(task_file: Path, verbose: bool = False) -> bool:
    """
    Validate a task configuration file.
    
    Args:
        task_file: Path to task file
        verbose: Show detailed validation info
        
    Returns:
        True if valid, False otherwise
    """
    task_file = Path(task_file)
    
    if not task_file.exists():
        print(f"{Fore.RED}❌ Task file not found: {task_file}{Style.RESET_ALL}")
        return False
    
    validator = TaskValidator()
    is_valid, errors = validator.validate_file(task_file)
    
    if is_valid:
        print(f"{Fore.GREEN}✅ Task configuration is valid{Style.RESET_ALL}")
        
        if verbose:
            analysis = validator.analyze_config(task_file)
            print(f"\n{Fore.CYAN}Analysis:{Style.RESET_ALL}")
            for key, value in analysis.items():
                print(f"  {key}: {value}")
        
        # Check for cycles
        has_cycles, cycle_errors = validator.check_dependency_cycles(task_file)
        if has_cycles:
            print(f"{Fore.GREEN}✅ No circular dependencies detected{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Circular dependencies found:{Style.RESET_ALL}")
            for error in cycle_errors:
                print(f"  {Fore.RED}•{Style.RESET_ALL} {error}")
            return False
        
        return True
    else:
        print(f"{Fore.RED}❌ Task configuration has errors:{Style.RESET_ALL}")
        for error in errors:
            print(f"  {Fore.RED}•{Style.RESET_ALL} {error}")
        return False


def show_task_info(task_file: Path) -> None:
    """
    Show detailed information about a task configuration.
    
    Args:
        task_file: Path to task file
    """
    task_file = Path(task_file)
    
    if not task_file.exists():
        print(f"{Fore.RED}❌ Task file not found: {task_file}{Style.RESET_ALL}")
        return
    
    try:
        config = load_task_config(task_file)
        validator = TaskValidator()
        analysis = validator.analyze_config(task_file)
    except Exception as e:
        print(f"{Fore.RED}❌ Error loading task: {e}{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}📊 Task Information: {task_file.name}{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}Task:{Style.RESET_ALL} {config.get('task', 'N/A')}")
    print(f"{Fore.GREEN}Action:{Style.RESET_ALL} {config.get('action', 'N/A')}")
    print(f"{Fore.GREEN}Parallel:{Style.RESET_ALL} {config.get('parallel', False)}")
    print(f"{Fore.GREEN}Human Gate:{Style.RESET_ALL} {config.get('human_gate', False)}")
    print(f"\n{Fore.CYAN}Statistics:{Style.RESET_ALL}")
    for key, value in analysis.items():
        if key != "dependency_chains":
            print(f"  {key}: {value}")


def list_states() -> None:
    """
    List all saved execution states.
    """
    state_manager = StateManager()
    states = state_manager.list_states()
    
    if not states:
        print(f"{Fore.YELLOW}No saved states found{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}💾 Saved Execution States{Style.RESET_ALL}\n")
    
    for state in states:
        execution_id = state.get("execution_id", "unknown")
        timestamp = state.get("timestamp", "unknown")
        root_task = state.get("root_task", "unknown")
        
        print(f"  {Fore.GREEN}•{Style.RESET_ALL} {execution_id}")
        print(f"    {Fore.CYAN}Task:{Style.RESET_ALL} {root_task}")
        print(f"    {Fore.CYAN}Timestamp:{Style.RESET_ALL} {timestamp}")
        print()


def export_results(execution_id: str, output_path: Optional[Path] = None) -> None:
    """
    Export execution results to a file.
    
    Args:
        execution_id: Execution identifier
        output_path: Output file path (optional)
    """
    state_manager = StateManager()
    
    if output_path is None:
        output_path = Path(f"{execution_id}_results.json")
    
    try:
        result_path = state_manager.export_results(execution_id, output_path)
        print(f"{Fore.GREEN}✅ Results exported to: {result_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error exporting results: {e}{Style.RESET_ALL}")


def show_state(execution_id: str) -> None:
    """
    Show details of a saved execution state.
    
    Args:
        execution_id: Execution identifier
    """
    state_manager = StateManager()
    state = state_manager.load_state(execution_id)
    
    if not state:
        print(f"{Fore.RED}❌ State not found: {execution_id}{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}💾 Execution State: {execution_id}{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}Timestamp:{Style.RESET_ALL} {state.get('timestamp', 'N/A')}")
    print(f"{Fore.GREEN}Root Task:{Style.RESET_ALL} {state.get('root_node_id', 'N/A')}")
    
    nodes = state.get("nodes", {})
    print(f"{Fore.GREEN}Total Tasks:{Style.RESET_ALL} {len(nodes)}")
    
    # Count by status
    status_counts = {}
    for node_data in nodes.values():
        status = node_data.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n{Fore.CYAN}Status Summary:{Style.RESET_ALL}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

