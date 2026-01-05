"""
State persistence for Loom task execution.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from loom.engine import TaskNode, TaskStatus


class StateManager:
    """
    Manages saving and loading execution state.
    """
    
    def __init__(self, state_dir: Path = Path(".loom_state")):
        """
        Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
    
    def save_state(
        self,
        execution_id: str,
        root_node: TaskNode,
        all_nodes: Dict[str, TaskNode],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save execution state to disk.
        
        Args:
            execution_id: Unique execution identifier
            root_node: Root task node
            all_nodes: Dictionary of all nodes
            metadata: Additional metadata to save
            
        Returns:
            Path to saved state file
        """
        state_file = self.state_dir / f"{execution_id}.state"
        
        # Serialize nodes (convert to dict for JSON)
        nodes_data = {}
        for node_id, node in all_nodes.items():
            nodes_data[node_id] = self._serialize_node(node)
        
        state = {
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "root_node_id": root_node.id,
            "nodes": nodes_data,
            "metadata": metadata or {}
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str)
        
        return state_file
    
    def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load execution state from disk.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            State dictionary or None if not found
        """
        state_file = self.state_dir / f"{execution_id}.state"
        
        if not state_file.exists():
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        return state
    
    def list_states(self) -> List[Dict[str, Any]]:
        """
        List all saved states.
        
        Returns:
            List of state metadata dictionaries
        """
        states = []
        
        for state_file in self.state_dir.glob("*.state"):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    states.append({
                        "execution_id": state.get("execution_id", state_file.stem),
                        "timestamp": state.get("timestamp", "unknown"),
                        "root_task": state.get("nodes", {}).get(
                            state.get("root_node_id", ""), {}
                        ).get("task", "unknown")
                    })
            except Exception:
                continue
        
        return sorted(states, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete_state(self, execution_id: str) -> bool:
        """
        Delete a saved state.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            True if deleted, False if not found
        """
        state_file = self.state_dir / f"{execution_id}.state"
        
        if state_file.exists():
            state_file.unlink()
            return True
        
        return False
    
    def _serialize_node(self, node: TaskNode) -> Dict[str, Any]:
        """Serialize a task node to dictionary."""
        return {
            "id": node.id,
            "task": node.task,
            "action": node.action,
            "parallel": node.parallel,
            "human_gate": node.human_gate,
            "depends_on": node.depends_on,
            "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
            "task_path": node.task_path,
            "parent_id": node.parent.id if node.parent else None,
            "start_time": node.start_time,
            "end_time": node.end_time,
            "result": node.result,
            "error": node.error,
            "sub_task_ids": [st.id for st in node.sub_tasks]
        }
    
    def export_results(self, execution_id: str, output_path: Path) -> Path:
        """
        Export execution results to a file.
        
        Args:
            execution_id: Execution identifier
            output_path: Path to export file
            
        Returns:
            Path to exported file
        """
        state = self.load_state(execution_id)
        
        if not state:
            raise ValueError(f"State not found for execution: {execution_id}")
        
        # Flatten and format results
        results = {
            "execution_id": execution_id,
            "timestamp": state.get("timestamp"),
            "summary": self._create_results_summary(state),
            "tasks": state.get("nodes", {})
        }
        
        output_path = Path(output_path)
        
        if output_path.suffix == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
        elif output_path.suffix == '.yaml':
            import yaml
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(results, f, default_flow_style=False)
        else:
            # Default to JSON
            output_path = output_path.with_suffix('.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
        
        return output_path
    
    def _create_results_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary from state data."""
        nodes = state.get("nodes", {})
        
        summary = {
            "total_tasks": len(nodes),
            "by_status": {},
            "completed": 0,
            "failed": 0,
            "pending": 0
        }
        
        for node_data in nodes.values():
            status = node_data.get("status", "unknown")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            if status == "completed":
                summary["completed"] += 1
            elif status == "failed":
                summary["failed"] += 1
            elif status == "pending":
                summary["pending"] += 1
        
        return summary

