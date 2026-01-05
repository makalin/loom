"""
Task validation and analysis tools.
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from loom.config import load_task_config, validate_task_config
from loom.utils import validate_dependency_graph, get_dependency_chain


class TaskValidator:
    """
    Validates task configurations and provides analysis.
    """
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    def validate_file(self, config_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a task configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            config = load_task_config(config_path)
        except Exception as e:
            return False, [str(e)]
        
        # Additional validations
        errors.extend(self._validate_structure(config))
        errors.extend(self._validate_dependencies(config))
        
        return len(errors) == 0, errors
    
    def _validate_structure(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration structure."""
        errors = []
        
        if "task" not in config:
            errors.append("Missing required field: 'task'")
        
        if "sub_tasks" in config:
            if not isinstance(config["sub_tasks"], list):
                errors.append("'sub_tasks' must be a list")
            else:
                for i, sub_task in enumerate(config["sub_tasks"]):
                    if not isinstance(sub_task, dict):
                        errors.append(f"Sub-task {i} must be a dictionary")
                    else:
                        sub_errors = self._validate_structure(sub_task)
                        errors.extend([f"Sub-task {i}: {e}" for e in sub_errors])
        
        return errors
    
    def _validate_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """Validate dependencies."""
        errors = []
        
        # Build a map of all task IDs
        task_ids = set()
        
        def _collect_ids(cfg: Dict[str, Any], prefix: str = ""):
            task_id = cfg.get("id", f"{prefix}root")
            if task_id in task_ids:
                errors.append(f"Duplicate task ID: {task_id}")
            task_ids.add(task_id)
            
            for i, sub_task in enumerate(cfg.get("sub_tasks", [])):
                sub_id = sub_task.get("id", f"{task_id}_subtask_{i}")
                _collect_ids(sub_task, f"{task_id}_")
        
        _collect_ids(config)
        
        # Validate depends_on references
        def _validate_deps(cfg: Dict[str, Any]):
            for dep_id in cfg.get("depends_on", []):
                if dep_id not in task_ids:
                    errors.append(f"Dependency '{dep_id}' references non-existent task")
            
            for sub_task in cfg.get("sub_tasks", []):
                _validate_deps(sub_task)
        
        _validate_deps(config)
        
        return errors
    
    def analyze_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Analyze a task configuration and provide insights.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Analysis dictionary
        """
        try:
            config = load_task_config(config_path)
        except Exception as e:
            return {"error": str(e)}
        
        analysis = {
            "total_tasks": 0,
            "max_depth": 0,
            "parallel_tasks": 0,
            "human_gates": 0,
            "tasks_with_dependencies": 0,
            "tasks_with_actions": 0,
            "dependency_chains": []
        }
        
        def _analyze(cfg: Dict[str, Any], depth: int = 0):
            analysis["total_tasks"] += 1
            analysis["max_depth"] = max(analysis["max_depth"], depth)
            
            if cfg.get("parallel", False):
                analysis["parallel_tasks"] += 1
            
            if cfg.get("human_gate", False):
                analysis["human_gates"] += 1
            
            if cfg.get("depends_on"):
                analysis["tasks_with_dependencies"] += 1
            
            if cfg.get("action"):
                analysis["tasks_with_actions"] += 1
            
            for sub_task in cfg.get("sub_tasks", []):
                _analyze(sub_task, depth + 1)
        
        _analyze(config)
        
        return analysis
    
    def check_dependency_cycles(self, config_path: Path) -> Tuple[bool, List[str]]:
        """
        Check for circular dependencies in configuration.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (has_cycles, list_of_cycles)
        """
        try:
            config = load_task_config(config_path)
        except Exception as e:
            return False, [str(e)]
        
        # Build node map for validation
        nodes = {}
        
        def _build_nodes(cfg: Dict[str, Any], parent_id: Optional[str] = None):
            task_id = cfg.get("id", "root" if parent_id is None else f"task_{len(nodes)}")
            nodes[task_id] = {
                "id": task_id,
                "depends_on": cfg.get("depends_on", [])
            }
            
            for sub_task in cfg.get("sub_tasks", []):
                _build_nodes(sub_task, task_id)
        
        _build_nodes(config)
        
        return validate_dependency_graph(nodes)

