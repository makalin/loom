# 🧶 Loom: Autonomous Task Weaver

**Loom** is a sophisticated task orchestration engine designed to execute complex, multi-step AI engineering workflows. Unlike simple linear scripts, Loom uses a **hierarchical state machine** to manage dependencies, parallelize sub-tasks, and integrate human-in-the-loop decision making.

## 🚀 Technical Architecture

Loom is built to handle non-linear engineering problems by treating development as a **directed acyclic graph (DAG)** of tasks.

### Core Engine Capabilities:

* **🌲 Infinite Nesting:** Define recursive task structures where high-level goals (e.g., "Refactor Auth") automatically spawn sub-tasks (e.g., "Update Schema" → "Migrate Data") to any depth.
* **⚡ Parallel Execution:** Native support for `parallel: true`, enabling concurrent workers to tackle independent sub-tasks simultaneously, significantly reducing execution time.
* **🔗 Dependency Management:** The `depends_on` logic ensures a strict execution order, blocking downstream tasks until their prerequisites are successfully validated.
* **⏸️ Human Gates:** Integrated `human_gate: true` pauses execution for critical decisions, allowing a developer to approve or edit AI-generated code before the next branch of the tree starts.
* **📊 State Tracking:** Real-time progress monitoring using `TASK_PATH`, providing the exact position of every worker within the nested hierarchy and a calculated percentage of completion.

## 🛠️ Configuration Example

Loom maintains backward compatibility with legacy markdown configs while supporting advanced YAML-based task definitions:

```yaml
task: "Build User Dashboard"
parallel: true
sub_tasks:
  - id: "api_gen"
    action: "Generate FastAPI endpoints"
  - id: "ui_gen"
    action: "Create React components"
    depends_on: ["api_gen"]
  - id: "security_review"
    human_gate: true
    action: "Review generated auth logic"

```

## 📦 Installation & Setup

```bash
# Clone the orchestration engine
git clone https://github.com/makalin/loom.git
cd loom

# Install the high-performance core
pip install -r requirements.txt

# Run a workspace audit
python loom.py --run ./tasks/refactor.yaml

```

## 🤝 Roadmap

* **Model Agnostic Provider Layer:** Swap between Claude, GPT, and local models for specific sub-tasks within the same tree.
* **Visual Debugger:** A web-based DAG visualizer to watch tasks execute in real-time.
* **Aggregate Logic:** Automated merging of outputs from parallel children into a single cohesive pull request.

---

**Developed by [Mehmet T. AKALIN](https://dv.com.tr/makalin/) & [Digital Vision](https://dv.com.tr).**
