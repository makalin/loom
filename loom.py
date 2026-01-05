#!/usr/bin/env python3
"""
Loom: Autonomous Task Weaver
Main entry point for the task orchestration engine.
"""

import sys
import os
import argparse
import uuid
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from loom.engine import TaskEngine
from loom.config import load_task_config
from loom.cli_tools import (
    list_tasks, validate_task, show_task_info,
    list_states, export_results, show_state
)
from loom.state import StateManager
from loom.logger import LoomLogger
from loom.retry import RetryManager, RetryStrategy
from loom.timeout import TimeoutManager
from loom.utils import calculate_task_hash
from loom.web import LoomWebServer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Loom: Autonomous Task Weaver - Execute complex multi-step AI engineering workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  loom --run tasks/dashboard.yaml          # Run a task
  loom --list                              # List all tasks
  loom --validate tasks/dashboard.yaml     # Validate a task
  loom --info tasks/dashboard.yaml         # Show task info
  loom --states                            # List saved states
  loom --export <execution_id>             # Export results
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a task configuration')
    run_parser.add_argument(
        'task_file',
        type=str,
        help='Path to task YAML configuration file'
    )
    run_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    run_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without executing tasks'
    )
    run_parser.add_argument(
        '--retry',
        type=int,
        default=3,
        help='Maximum number of retries for failed tasks (default: 3)'
    )
    run_parser.add_argument(
        '--timeout',
        type=float,
        help='Default timeout for tasks in seconds'
    )
    run_parser.add_argument(
        '--save-state',
        action='store_true',
        help='Save execution state'
    )
    run_parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all available tasks')
    list_parser.add_argument(
        '--tasks-dir',
        type=str,
        default='tasks',
        help='Directory containing task files (default: tasks)'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a task configuration')
    validate_parser.add_argument(
        'task_file',
        type=str,
        help='Path to task YAML configuration file'
    )
    validate_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed validation info'
    )
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show detailed task information')
    info_parser.add_argument(
        'task_file',
        type=str,
        help='Path to task YAML configuration file'
    )
    
    # States command
    states_parser = subparsers.add_parser('states', help='List saved execution states')
    
    # State command
    state_parser = subparsers.add_parser('state', help='Show details of a saved state')
    state_parser.add_argument(
        'execution_id',
        type=str,
        help='Execution identifier'
    )
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export execution results')
    export_parser.add_argument(
        'execution_id',
        type=str,
        help='Execution identifier'
    )
    export_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: <execution_id>_results.json)'
    )
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Start Kanban board web interface')
    gui_parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    gui_parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    gui_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    # Backward compatibility: --run flag
    parser.add_argument(
        '--run',
        type=str,
        help='Path to task YAML configuration file (deprecated, use "run" command)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without executing tasks'
    )
    
    args = parser.parse_args()
    
    # Handle backward compatibility
    if args.run:
        args.command = 'run'
        args.task_file = args.run
    
    # Execute command
    if args.command == 'run' or args.run:
        _run_task(args)
    elif args.command == 'list':
        list_tasks(Path(args.tasks_dir))
    elif args.command == 'validate':
        success = validate_task(Path(args.task_file), args.verbose)
        sys.exit(0 if success else 1)
    elif args.command == 'info':
        show_task_info(Path(args.task_file))
    elif args.command == 'states':
        list_states()
    elif args.command == 'state':
        show_state(args.execution_id)
    elif args.command == 'export':
        output_path = Path(args.output) if args.output else None
        export_results(args.execution_id, output_path)
    elif args.command == 'gui':
        server = LoomWebServer(host=args.host, port=args.port)
        server.run(debug=args.debug)
    else:
        parser.print_help()
        sys.exit(1)


def _run_task(args):
    """Run a task configuration."""
    task_file = Path(args.task_file if hasattr(args, 'task_file') else args.run)
    
    if not task_file.exists():
        print(f"❌ Error: Task file not found: {task_file}", file=sys.stderr)
        sys.exit(1)
    
    # Load configuration
    try:
        config = load_task_config(task_file)
    except Exception as e:
        print(f"❌ Error loading task configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.dry_run:
        print("✅ Configuration validated successfully (dry-run mode)")
        return
    
    # Initialize logger
    log_file = Path(args.log_file) if hasattr(args, 'log_file') and args.log_file else None
    logger = LoomLogger(verbose=args.verbose, log_file=log_file)
    
    # Initialize engine with retry and timeout
    engine = TaskEngine(verbose=args.verbose)
    
    # Add retry manager if specified
    if hasattr(args, 'retry') and args.retry > 0:
        retry_manager = RetryManager(max_retries=args.retry)
        engine.retry_manager = retry_manager
    
    # Add timeout manager if specified
    if hasattr(args, 'timeout') and args.timeout:
        timeout_manager = TimeoutManager(default_timeout=args.timeout)
        engine.timeout_manager = timeout_manager
    
    # Generate execution ID
    execution_id = str(uuid.uuid4())[:8]
    state_manager = StateManager()
    
    try:
        # Execute
        engine.execute(config)
        
        # Save state if requested
        if hasattr(args, 'save_state') and args.save_state:
            if engine.root_node:
                state_manager.save_state(
                    execution_id,
                    engine.root_node,
                    engine.all_nodes,
                    metadata={
                        "task_file": str(task_file),
                        "config_hash": calculate_task_hash(config)
                    }
                )
                print(f"\n💾 State saved: {execution_id}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
        
        # Save state on interrupt if requested
        if hasattr(args, 'save_state') and args.save_state:
            if engine.root_node:
                state_manager.save_state(
                    execution_id,
                    engine.root_node,
                    engine.all_nodes,
                    metadata={
                        "task_file": str(task_file),
                        "interrupted": True
                    }
                )
                print(f"💾 State saved: {execution_id} (interrupted)")
        
        sys.exit(130)
    except Exception as e:
        print(f"❌ Execution error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

