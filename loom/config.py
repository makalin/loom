"""
Configuration loading and validation for Loom task definitions.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_task_config(config_path: Path) -> Dict[str, Any]:
    """
    Load and validate a task configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Validated task configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If file doesn't exist
    """
    if not isinstance(config_path, Path):
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")
    
    if not config:
        raise ValueError("Configuration file is empty")
    
    # Validate and normalize configuration
    validated = validate_task_config(config)
    return validated


def validate_task_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize task configuration structure.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Validated and normalized configuration
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    # Required fields
    if "task" not in config:
        raise ValueError("Configuration must include a 'task' field")
    
    # Normalize structure
    validated = {
        "task": str(config["task"]),
        "parallel": config.get("parallel", False),
        "human_gate": config.get("human_gate", False),
        "depends_on": config.get("depends_on", []),
        "action": config.get("action", ""),
        "sub_tasks": []
    }
    
    # Validate and process sub_tasks
    if "sub_tasks" in config:
        if not isinstance(config["sub_tasks"], list):
            raise ValueError("'sub_tasks' must be a list")
        
        for i, sub_task in enumerate(config["sub_tasks"]):
            if not isinstance(sub_task, dict):
                raise ValueError(f"Sub-task {i} must be a dictionary")
            
            validated_sub = validate_task_config(sub_task)
            
            # Preserve id if present
            if "id" in sub_task:
                validated_sub["id"] = str(sub_task["id"])
            else:
                validated_sub["id"] = f"subtask_{i}"
            
            validated["sub_tasks"].append(validated_sub)
    
    # Validate depends_on
    if validated["depends_on"]:
        if not isinstance(validated["depends_on"], list):
            raise ValueError("'depends_on' must be a list")
        validated["depends_on"] = [str(dep) for dep in validated["depends_on"]]
    
    return validated

