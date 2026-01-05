# 🧶 Loom: Autonomous Task Weaver

**Loom** is a sophisticated task orchestration engine designed to execute complex, multi-step AI engineering workflows. Unlike simple linear scripts, Loom uses a **hierarchical state machine** to manage dependencies, parallelize sub-tasks, and integrate human-in-the-loop decision making.

## 🚀 Technical Architecture

Loom is built to handle non-linear engineering problems by treating development as a **directed acyclic graph (DAG)** of tasks.

### Core Engine Capabilities

* **🌲 Infinite Nesting:** Define recursive task structures where high-level goals (e.g., "Refactor Auth") automatically spawn sub-tasks (e.g., "Update Schema" → "Migrate Data") to any depth, allowing for massive project decomposition.

* **⚡ Parallel Execution:** Native support for `parallel: true`, enabling concurrent workers to tackle independent sub-tasks simultaneously, significantly reducing execution time and maximizing CPU efficiency.

* **🔗 Dependency Management:** The `depends_on` logic ensures a strict execution order, blocking downstream tasks until their prerequisites are successfully validated. Automatic cycle detection prevents circular dependencies.

* **⏸️ Human Gates:** Integrated `human_gate: true` pauses execution for critical decisions, allowing a developer to approve or edit AI-generated code before the next branch of the tree starts.

* **📊 State Tracking:** Real-time progress monitoring using `TASK_PATH`, providing the exact position of every worker within the nested hierarchy and a calculated percentage of completion.

* **🔄 Retry Mechanism:** Configurable retry strategies (immediate, exponential backoff, linear backoff, fixed delay) with automatic retry for failed tasks.

* **⏱️ Timeout Handling:** Per-task and global timeout support to prevent tasks from hanging indefinitely.

* **💾 State Persistence:** Save and resume execution state, allowing you to pause and continue long-running workflows.

* **📝 Comprehensive Logging:** File and console logging with colored output, task-specific logging, and verbose mode support.

* **✅ Validation & Analysis:** Built-in task validation, dependency cycle detection, and configuration analysis tools.

## 🛠️ Configuration Example

Loom supports advanced YAML-based task definitions:

```yaml
task: "Build User Dashboard"
parallel: true
sub_tasks:
  - id: "api_gen"
    task: "Generate FastAPI Endpoints"
    action: "Generate FastAPI endpoints for dashboard data"
    sub_tasks:
      - id: "user_stats"
        task: "User Statistics Endpoint"
        action: "Create /api/dashboard/stats endpoint"
      - id: "recent_activity"
        task: "Recent Activity Endpoint"
        action: "Create /api/dashboard/activity endpoint"
  
  - id: "ui_gen"
    task: "Create React Components"
    action: "Build React dashboard components"
    depends_on: ["api_gen"]
    sub_tasks:
      - id: "dashboard_layout"
        task: "Dashboard Layout"
        action: "Create main dashboard layout component"
      - id: "stats_widget"
        task: "Statistics Widget"
        action: "Create statistics display widget"
        depends_on: ["dashboard_layout"]
  
  - id: "security_review"
    task: "Security Review"
    human_gate: true
    action: "Review generated auth logic"
    depends_on: ["api_gen", "ui_gen"]
```

## 📦 Installation & Setup

```bash
# Clone the orchestration engine
git clone https://github.com/makalin/loom.git
cd loom

# Install dependencies
pip install -r requirements.txt

# Verify installation
python loom.py --help
```

## 🎯 Usage

### Kanban GUI (Web Interface)

Launch the interactive Kanban board to visualize and manage tasks:

```bash
# Start the web interface (default: http://127.0.0.1:5000)
loom gui

# Custom host and port
loom gui --host 0.0.0.0 --port 8080

# Enable debug mode
loom gui --debug
```

The Kanban board provides:
- **Real-time task visualization** - See tasks move through columns (Pending → Running → Completed)
- **Interactive task management** - Load task files, start/stop execution
- **Progress tracking** - Visual progress bar and statistics
- **Task details** - View task paths, dependencies, and metadata
- **Status indicators** - Color-coded cards for different task states

### Running Tasks

```bash
# Basic execution
loom run tasks/dashboard.yaml

# With retry and timeout
loom run tasks/dashboard.yaml --retry 5 --timeout 300

# Save execution state
loom run tasks/dashboard.yaml --save-state

# Enable verbose output and logging
loom run tasks/dashboard.yaml --verbose --log-file loom.log

# Dry run (validate without executing)
loom run tasks/dashboard.yaml --dry-run
```

### Task Management

```bash
# List all available tasks
loom list

# Validate a task configuration
loom validate tasks/dashboard.yaml

# Show detailed task information
loom info tasks/dashboard.yaml

# Validate with detailed analysis
loom validate tasks/dashboard.yaml --verbose
```

### State Management

```bash
# List all saved execution states
loom states

# Show details of a specific state
loom state <execution_id>

# Export execution results
loom export <execution_id> --output results.json
```

### Backward Compatibility

The legacy `--run` flag is still supported:

```bash
python loom.py --run ./tasks/refactor.yaml
python loom.py --run ./tasks/refactor.yaml --verbose --dry-run
```

## 🧩 Module Overview

### Core Modules

* **`loom.engine`** - Main task orchestration engine with hierarchical state machine
* **`loom.config`** - YAML configuration loading and validation
* **`loom.utils`** - Utility functions for task management, formatting, and analysis
* **`loom.state`** - State persistence and result export
* **`loom.logger`** - Comprehensive logging system
* **`loom.retry`** - Retry mechanism with multiple strategies
* **`loom.timeout`** - Timeout handling for task execution
* **`loom.validator`** - Task validation and dependency analysis
* **`loom.cli_tools`** - CLI utility functions
* **`loom.templates`** - Task template generators for common patterns
* **`loom.web`** - Web server and Kanban GUI

### Key Features by Module

**State Management:**
- Save/load execution state
- Resume interrupted workflows
- Export results to JSON/YAML
- List and manage saved states

**Retry System:**
- Multiple retry strategies (immediate, exponential backoff, linear, fixed delay)
- Configurable max retries
- Automatic retry on failure

**Validation:**
- YAML syntax validation
- Dependency cycle detection
- Structure validation
- Configuration analysis

**Utilities:**
- Task tree flattening
- Dependency chain analysis
- Result aggregation
- Duration and timestamp formatting
- Task summary generation

## 📋 Task Configuration Reference

### Required Fields

* `task` - Task name/description (required)

### Optional Fields

* `id` - Unique task identifier (auto-generated if not provided)
* `action` - Action description or command to execute
* `parallel` - Boolean, enable parallel execution of sub-tasks (default: `false`)
* `human_gate` - Boolean, pause for human approval (default: `false`)
* `depends_on` - List of task IDs that must complete first
* `sub_tasks` - List of sub-task configurations
* `timeout` - Task timeout in seconds (optional)

### Example: Complex Workflow

```yaml
task: "Deploy Microservice"
parallel: false
sub_tasks:
  - id: "build"
    task: "Build Application"
    action: "Build Docker image"
    parallel: true
    sub_tasks:
      - id: "build_api"
        task: "Build API"
        action: "docker build -t api:latest ./api"
      - id: "build_worker"
        task: "Build Worker"
        action: "docker build -t worker:latest ./worker"
  
  - id: "test"
    task: "Run Tests"
    action: "Run test suite"
    depends_on: ["build"]
  
  - id: "security_scan"
    task: "Security Scan"
    human_gate: true
    action: "Review security scan results"
    depends_on: ["test"]
  
  - id: "deploy"
    task: "Deploy to Production"
    action: "Deploy to production environment"
    depends_on: ["security_scan"]
```

## 🔧 Advanced Features

### Retry Strategies

Configure retry behavior when initializing the engine:

```python
from loom import RetryManager, RetryStrategy

retry_manager = RetryManager(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=60.0
)
```

### Timeout Management

Set timeouts for tasks:

```python
from loom import TimeoutManager

timeout_manager = TimeoutManager(default_timeout=300)  # 5 minutes
```

### State Persistence

Save and resume execution:

```python
from loom import StateManager

state_manager = StateManager()
state_manager.save_state(execution_id, root_node, all_nodes)
# Later...
state = state_manager.load_state(execution_id)
```

### Task Templates

Generate common task patterns:

```python
from loom.templates import (
    generate_parallel_template,
    generate_sequential_template,
    generate_pipeline_template,
    generate_refactor_template
)

# Parallel execution template
template = generate_parallel_template(
    "Process Data",
    ["Extract", "Transform", "Load"]
)
```

## 🎨 Kanban GUI Features

The web-based Kanban board provides a visual interface for task management:

### Features

* **Real-time Updates** - Tasks automatically update as they execute
* **Column Organization** - Tasks organized by status:
  - ⏳ Pending
  - 🔄 Running (with pulse animation)
  - ✅ Completed
  - ❌ Failed
  - ⏸️ Blocked
  - 👤 Human Gate

* **Task Cards** - Each card shows:
  - Task ID and name
  - Task path in hierarchy
  - Action description
  - Badges for parallel execution, human gates, and dependencies

* **Progress Tracking** - Visual progress bar and statistics
* **Interactive Controls** - Load tasks, start/stop execution
* **Responsive Design** - Works on desktop and mobile devices

### Usage

1. Start the GUI: `loom gui`
2. Open your browser to `http://127.0.0.1:5000`
3. Enter a task file path (e.g., `tasks/dashboard.yaml`)
4. Click "Load Task" to visualize the task tree
5. Click "Run" to start execution
6. Watch tasks move through the Kanban columns in real-time

## 🤝 Roadmap

* **Model Agnostic Provider Layer:** Swap between Claude, GPT, and local models for specific sub-tasks within the same tree.
* **Enhanced Visual Debugger:** Advanced DAG visualization with dependency graphs and execution flow.
* **Resume from State:** Automatic resumption of interrupted workflows from saved state.
* **Task Templates Library:** Pre-built templates for common engineering workflows.
* **Task Drag & Drop:** Reorder tasks in the Kanban board.
* **Task History:** View execution history and compare runs.

## 📄 License

See [LICENSE](LICENSE) file for details.

---

**Developed by [Mehmet T. AKALIN](https://dv.com.tr/makalin/) & [Digital Vision](https://dv.com.tr).**
