"""
Utility functions for Loom task orchestration.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


def calculate_task_hash(config: Dict[str, Any]) -> str:
    """
    Calculate a hash for a task configuration.
    
    Args:
        config: Task configuration dictionary
        
    Returns:
        SHA256 hash string
    """
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


def format_timestamp(timestamp: Optional[float]) -> str:
    """
    Format timestamp in human-readable format.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def flatten_task_tree(node: Any, result: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Flatten a task tree into a list of all nodes.
    
    Args:
        node: Task node to flatten
        result: Accumulator list (internal use)
        
    Returns:
        List of all task nodes
    """
    if result is None:
        result = []
    
    node_dict = {
        "id": node.id,
        "task": node.task,
        "task_path": node.task_path,
        "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
        "action": node.action,
        "parallel": node.parallel,
        "human_gate": node.human_gate,
        "depends_on": node.depends_on,
        "parent_id": node.parent.id if node.parent else None,
    }
    
    if hasattr(node, 'start_time'):
        node_dict["start_time"] = node.start_time
        node_dict["end_time"] = node.end_time
        if node.start_time and node.end_time:
            node_dict["duration"] = node.end_time - node.start_time
    
    if hasattr(node, 'result'):
        node_dict["result"] = node.result
    
    if hasattr(node, 'error'):
        node_dict["error"] = node.error
    
    result.append(node_dict)
    
    for sub_task in getattr(node, 'sub_tasks', []):
        flatten_task_tree(sub_task, result)
    
    return result


def find_node_by_path(nodes: Dict[str, Any], task_path: str) -> Optional[Any]:
    """
    Find a node by its task path.
    
    Args:
        nodes: Dictionary of all nodes
        task_path: Task path to search for
        
    Returns:
        Node if found, None otherwise
    """
    for node in nodes.values():
        if node.task_path == task_path:
            return node
        # Recursively search sub-tasks
        for sub_task in getattr(node, 'sub_tasks', []):
            result = find_node_by_path({sub_task.id: sub_task}, task_path)
            if result:
                return result
    return None


def get_dependency_chain(nodes: Dict[str, Any], node_id: str) -> List[str]:
    """
    Get the full dependency chain for a node.
    
    Args:
        nodes: Dictionary of all nodes
        node_id: Node ID to get dependencies for
        
    Returns:
        List of dependency IDs in order
    """
    if node_id not in nodes:
        return []
    
    node = nodes[node_id]
    chain = []
    visited = set()
    
    def _traverse(nid: str):
        if nid in visited:
            return
        visited.add(nid)
        
        if nid in nodes:
            n = nodes[nid]
            for dep in getattr(n, 'depends_on', []):
                _traverse(dep)
                if dep not in chain:
                    chain.append(dep)
            if nid not in chain:
                chain.append(nid)
    
    _traverse(node_id)
    return chain


def validate_dependency_graph(nodes: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that the dependency graph has no cycles.
    
    Args:
        nodes: Dictionary of all nodes
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    def _has_cycle(node_id: str, path: List[str]) -> bool:
        if node_id in path:
            cycle = path[path.index(node_id):] + [node_id]
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
            return True
        
        if node_id not in nodes:
            return False
        
        node = nodes[node_id]
        for dep in getattr(node, 'depends_on', []):
            if _has_cycle(dep, path + [node_id]):
                return True
        return False
    
    for node_id in nodes:
        _has_cycle(node_id, [])
    
    return len(errors) == 0, errors


def aggregate_results(node: Any) -> Dict[str, Any]:
    """
    Aggregate results from a task node and all its children.
    
    Args:
        node: Task node to aggregate
        
    Returns:
        Aggregated results dictionary
    """
    aggregated = {
        "node_id": node.id,
        "task": node.task,
        "task_path": node.task_path,
        "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
        "result": getattr(node, 'result', None),
        "error": getattr(node, 'error', None),
        "children": []
    }
    
    for sub_task in getattr(node, 'sub_tasks', []):
        aggregated["children"].append(aggregate_results(sub_task))
    
    return aggregated


def create_task_summary(nodes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of all tasks.
    
    Args:
        nodes: Dictionary of all nodes
        
    Returns:
        Summary dictionary
    """
    summary = {
        "total_tasks": len(nodes),
        "by_status": {},
        "by_type": {
            "with_actions": 0,
            "with_subtasks": 0,
            "parallel": 0,
            "with_gates": 0,
            "with_dependencies": 0
        },
        "tasks": []
    }
    
    for node in nodes.values():
        # Count by status
        status = node.status.value if hasattr(node.status, 'value') else str(node.status)
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        
        # Count by type
        if node.action:
            summary["by_type"]["with_actions"] += 1
        if node.sub_tasks:
            summary["by_type"]["with_subtasks"] += 1
        if node.parallel:
            summary["by_type"]["parallel"] += 1
        if node.human_gate:
            summary["by_type"]["with_gates"] += 1
        if node.depends_on:
            summary["by_type"]["with_dependencies"] += 1
        
        # Add task info
        task_info = {
            "id": node.id,
            "task": node.task,
            "task_path": node.task_path,
            "status": status
        }
        summary["tasks"].append(task_info)
    
    return summary

