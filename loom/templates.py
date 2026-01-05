"""
Task template generators for common patterns.
"""

from typing import Dict, Any, List, Optional


def generate_parallel_template(task_name: str, subtasks: List[str]) -> Dict[str, Any]:
    """
    Generate a template for parallel task execution.
    
    Args:
        task_name: Name of the main task
        subtasks: List of sub-task names
        
    Returns:
        Task configuration dictionary
    """
    template = {
        "task": task_name,
        "parallel": True,
        "sub_tasks": []
    }
    
    for i, subtask_name in enumerate(subtasks):
        template["sub_tasks"].append({
            "id": f"task_{i+1}",
            "task": subtask_name,
            "action": f"Execute {subtask_name}"
        })
    
    return template


def generate_sequential_template(task_name: str, subtasks: List[str]) -> Dict[str, Any]:
    """
    Generate a template for sequential task execution.
    
    Args:
        task_name: Name of the main task
        subtasks: List of sub-task names
        
    Returns:
        Task configuration dictionary
    """
    template = {
        "task": task_name,
        "parallel": False,
        "sub_tasks": []
    }
    
    prev_id = None
    for i, subtask_name in enumerate(subtasks):
        task_id = f"task_{i+1}"
        task_config = {
            "id": task_id,
            "task": subtask_name,
            "action": f"Execute {subtask_name}"
        }
        
        if prev_id:
            task_config["depends_on"] = [prev_id]
        
        template["sub_tasks"].append(task_config)
        prev_id = task_id
    
    return template


def generate_pipeline_template(
    stages: List[Dict[str, str]],
    with_gates: bool = False
) -> Dict[str, Any]:
    """
    Generate a pipeline template with stages.
    
    Args:
        stages: List of stage dictionaries with 'name' and 'action' keys
        with_gates: Add human gates between stages
        
    Returns:
        Task configuration dictionary
    """
    template = {
        "task": "Pipeline Execution",
        "parallel": False,
        "sub_tasks": []
    }
    
    prev_id = None
    for i, stage in enumerate(stages):
        stage_id = f"stage_{i+1}"
        stage_config = {
            "id": stage_id,
            "task": stage.get("name", f"Stage {i+1}"),
            "action": stage.get("action", ""),
            "parallel": stage.get("parallel", False)
        }
        
        if prev_id:
            stage_config["depends_on"] = [prev_id]
        
        if with_gates and i > 0:
            stage_config["human_gate"] = True
        
        template["sub_tasks"].append(stage_config)
        prev_id = stage_id
    
    return template


def generate_refactor_template(
    component_name: str,
    steps: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a refactoring task template.
    
    Args:
        component_name: Name of component to refactor
        steps: Optional list of refactoring steps
        
    Returns:
        Task configuration dictionary
    """
    if steps is None:
        steps = [
            "Update Schema",
            "Create Migration",
            "Update API",
            "Update Tests",
            "Security Review"
        ]
    
    template = {
        "task": f"Refactor {component_name}",
        "parallel": False,
        "sub_tasks": [
            {
                "id": "schema_update",
                "task": steps[0] if len(steps) > 0 else "Update Schema",
                "action": f"Update schema for {component_name}"
            },
            {
                "id": "migration",
                "task": steps[1] if len(steps) > 1 else "Create Migration",
                "action": f"Create migration for {component_name}",
                "depends_on": ["schema_update"]
            },
            {
                "id": "api_update",
                "task": steps[2] if len(steps) > 2 else "Update API",
                "action": f"Update API for {component_name}",
                "depends_on": ["migration"]
            },
            {
                "id": "tests",
                "task": steps[3] if len(steps) > 3 else "Update Tests",
                "action": f"Update tests for {component_name}",
                "depends_on": ["api_update"]
            },
            {
                "id": "security_review",
                "task": steps[4] if len(steps) > 4 else "Security Review",
                "human_gate": True,
                "action": f"Review security for {component_name}",
                "depends_on": ["tests"]
            }
        ]
    }
    
    return template

