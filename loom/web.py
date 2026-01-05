"""
Web server and Kanban GUI for Loom task visualization.
"""

import json
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Flask, render_template_string, jsonify, request

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

from loom.engine import TaskEngine, TaskNode, TaskStatus
from loom.config import load_task_config
from loom.state import StateManager
from loom.utils import flatten_task_tree, create_task_summary


class LoomWebServer:
    """
    Web server for Loom Kanban GUI.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Initialize web server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        if HAS_CORS:
            CORS(self.app)
        
        self.engine: Optional[TaskEngine] = None
        self.current_config: Optional[Dict[str, Any]] = None
        self.execution_thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Serve the Kanban board HTML."""
            return render_template_string(KANBAN_HTML)
        
        @self.app.route('/api/status')
        def get_status():
            """Get current execution status."""
            if not self.engine or not self.engine.root_node:
                return jsonify({
                    "running": False,
                    "tasks": [],
                    "summary": {},
                    "workers": 0,
                    "tool_calls": 0
                })
            
            tasks = flatten_task_tree(self.engine.root_node)
            summary = create_task_summary(self.engine.all_nodes)
            
            # Count active workers (running tasks)
            active_workers = sum(1 for task in tasks if task.get('status') == 'running')
            
            # Calculate tool calls (approximate as completed tasks)
            tool_calls = self.engine.completed_count
            
            return jsonify({
                "running": self.execution_thread is not None and self.execution_thread.is_alive(),
                "tasks": tasks,
                "summary": summary,
                "progress": {
                    "completed": self.engine.completed_count,
                    "total": self.engine.total_count,
                    "percentage": (self.engine.completed_count / self.engine.total_count * 100) if self.engine.total_count > 0 else 0
                },
                "workers": active_workers,
                "tool_calls": tool_calls,
                "start_time": self.start_time
            })
        
        @self.app.route('/api/load', methods=['POST'])
        def load_task():
            """Load a task configuration file."""
            data = request.json or {}
            task_file = data.get('file')
            
            if not task_file:
                return jsonify({"error": "No file specified"}), 400
            
            try:
                # Try to resolve the file path
                file_path = Path(task_file)
                
                # If relative path, try common locations
                if not file_path.is_absolute():
                    # Try current directory
                    if not file_path.exists():
                        # Try tasks directory
                        tasks_path = Path("tasks") / file_path.name
                        if tasks_path.exists():
                            file_path = tasks_path
                        else:
                            # Try just the filename in tasks
                            file_path = Path("tasks") / file_path
                
                if not file_path.exists():
                    return jsonify({"error": f"File not found: {task_file}"}), 404
                
                config = load_task_config(file_path)
                self.current_config = config
                
                # Build tree without executing
                engine = TaskEngine(verbose=False)
                engine.root_node = engine._build_task_tree(config, parent=None)
                engine.total_count = engine._count_tasks(engine.root_node)
                
                tasks = flatten_task_tree(engine.root_node)
                
                return jsonify({
                    "success": True,
                    "config": config,
                    "tasks": tasks,
                    "total_tasks": engine.total_count,
                    "file_path": str(file_path)
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        
        @self.app.route('/api/run', methods=['POST'])
        def run_task():
            """Start task execution."""
            if self.execution_thread and self.execution_thread.is_alive():
                return jsonify({"error": "Execution already running"}), 400
            
            if not self.current_config:
                return jsonify({"error": "No task loaded"}), 400
            
            def _execute():
                self.engine = TaskEngine(verbose=True)
                self.start_time = time.time()
                self.engine.execute(self.current_config)
            
            self.execution_thread = threading.Thread(target=_execute, daemon=True)
            self.execution_thread.start()
            
            return jsonify({"success": True, "message": "Execution started"})
        
        @self.app.route('/api/stop', methods=['POST'])
        def stop_task():
            """Stop task execution."""
            # Note: This is a simple implementation. In production, you'd want
            # proper thread cancellation
            return jsonify({"success": True, "message": "Stop requested"})
        
        @self.app.route('/api/states')
        def list_states():
            """List saved execution states."""
            state_manager = StateManager()
            states = state_manager.list_states()
            return jsonify({"states": states})
        
        @self.app.route('/api/state/<execution_id>')
        def get_state(execution_id: str):
            """Get a specific execution state."""
            state_manager = StateManager()
            state = state_manager.load_state(execution_id)
            
            if not state:
                return jsonify({"error": "State not found"}), 404
            
            return jsonify(state)
    
    def run(self, debug: bool = False):
        """
        Run the web server.
        
        Args:
            debug: Enable debug mode
        """
        print(f"\n🌐 Loom Kanban GUI starting on http://{self.host}:{self.port}")
        print(f"📊 Open your browser to view the task board\n")
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)


# Professional Dark-Themed Kanban Board HTML Template
KANBAN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧶 Loom - Professional Kanban Board</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --accent-gray: #64748b;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .top-bar {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .top-bar-left {
            display: flex;
            align-items: center;
            gap: 24px;
        }
        
        .project-stats {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .stat-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .worker-status {
            background: var(--accent-green);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .worker-status::before {
            content: "●";
            animation: pulse-dot 2s infinite;
        }
        
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .top-bar-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .action-btn {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .action-btn:hover {
            background: var(--bg-hover);
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        .btn-primary {
            background: var(--accent-blue);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-primary:hover {
            background: #2563eb;
            transform: translateY(-1px);
        }
        
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .file-input-group {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        
        .file-input {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            width: 300px;
        }
        
        .file-input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        
        .review-banner {
            background: var(--accent-yellow);
            color: #1e293b;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 600;
        }
        
        .review-badge {
            background: #1e293b;
            color: var(--accent-yellow);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }
        
        .kanban-container {
            padding: 24px;
            max-width: 1800px;
            margin: 0 auto;
        }
        
        .kanban-board {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .kanban-column {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            min-height: 500px;
            display: flex;
            flex-direction: column;
        }
        
        .column-header {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .column-count {
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            min-width: 24px;
            text-align: center;
        }
        
        .column-sections {
            flex: 1;
            overflow-y: auto;
            max-height: calc(100vh - 300px);
        }
        
        .section {
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            padding: 0 4px;
        }
        
        .task-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }
        
        .task-card:hover {
            background: var(--bg-hover);
            border-color: var(--accent-blue);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        .task-card.pending {
            border-left: 3px solid var(--accent-gray);
        }
        
        .task-card.running {
            border-left: 3px solid var(--accent-blue);
            animation: card-pulse 2s infinite;
        }
        
        .task-card.completed {
            border-left: 3px solid var(--accent-green);
        }
        
        .task-card.failed {
            border-left: 3px solid var(--accent-red);
        }
        
        .task-card.blocked {
            border-left: 3px solid var(--accent-yellow);
        }
        
        .task-card.waiting_human {
            border-left: 3px solid var(--accent-purple);
        }
        
        @keyframes card-pulse {
            0%, 100% { 
                box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
            }
            50% { 
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0);
            }
        }
        
        .task-tag {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        
        .tag-pending { background: #475569; color: #cbd5e1; }
        .tag-starting { background: #3b82f6; color: white; }
        .tag-running { background: #3b82f6; color: white; }
        .tag-completed { background: #10b981; color: white; }
        .tag-failed { background: #ef4444; color: white; }
        .tag-blocked { background: #f59e0b; color: #1e293b; }
        .tag-awaiting { background: #f59e0b; color: #1e293b; }
        .tag-shipped { background: #64748b; color: white; }
        
        .task-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
            line-height: 1.4;
        }
        
        .task-mission {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 8px;
            font-style: italic;
        }
        
        .task-mission::before {
            content: "Mission: ";
            font-weight: 600;
        }
        
        .task-path {
            font-size: 11px;
            color: var(--text-muted);
            font-family: 'Monaco', 'Menlo', monospace;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border-color);
        }
        
        .task-action {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border-color);
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
        }
        
        .empty-state-text {
            font-size: 13px;
            margin-top: 8px;
        }
        
        .bottom-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
        }
        
        .bottom-bar-left {
            display: flex;
            align-items: center;
            gap: 16px;
            color: var(--text-muted);
            font-size: 13px;
        }
        
        .timestamp {
            font-weight: 600;
            color: var(--text-secondary);
        }
        
        .agent-status {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .agent-status-line {
            color: var(--text-secondary);
        }
        
        .agent-status-value {
            color: var(--text-primary);
            font-weight: 600;
        }
        
        .progress-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--bg-secondary);
            z-index: 1000;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            transition: width 0.3s ease;
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--bg-tertiary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-gray);
        }
    </style>
</head>
<body>
    <div class="progress-overlay">
        <div class="progress-bar" id="globalProgress" style="width: 0%;"></div>
    </div>
    
    <div class="top-bar">
        <div class="top-bar-left">
            <div class="project-stats">
                <div class="stat-item">
                    <div class="stat-label">Total</div>
                    <div class="stat-value" id="statTotal">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Active</div>
                    <div class="stat-value" id="statActive">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Review</div>
                    <div class="stat-value" id="statReview">0</div>
                </div>
            </div>
            <div class="worker-status" id="workerStatus" style="display: none;">
                Running <span id="workerCount">0</span> workers
            </div>
        </div>
        <div class="top-bar-right">
            <div class="file-input-group">
                <input type="text" id="filePathInput" class="file-input" placeholder="tasks/dashboard.yaml" />
                <button id="loadBtn" class="btn-primary">📁 Load</button>
            </div>
            <button class="action-btn" id="refreshBtn" title="Refresh">🔄</button>
            <button class="btn-primary" id="runBtn" disabled>▶️ Run</button>
            <button class="action-btn" id="stopBtn" disabled>⏹️ Stop</button>
            <button class="btn-primary" id="newIdeaBtn">+ New Idea</button>
        </div>
    </div>
    
    <div id="reviewBanner" class="review-banner" style="display: none;">
        <span>Review</span>
        <span class="review-badge" id="reviewCount">0</span>
    </div>
    
    <div class="kanban-container">
        <div class="kanban-board" id="kanbanBoard">
            <div class="empty-state">
                <div style="font-size: 48px; margin-bottom: 12px;">📋</div>
                <div class="empty-state-text">Load a task configuration to get started</div>
            </div>
        </div>
    </div>
    
    <div class="bottom-bar">
        <div class="bottom-bar-left">
            <span class="timestamp" id="timestamp"></span>
            <span id="humanAction" style="display: none;">- <strong>Human Action</strong></span>
        </div>
        <div class="agent-status" id="agentStatus" style="display: none;">
            <div class="agent-status-line">
                <span class="agent-status-value" id="agentCount">0</span> Agents Running
            </div>
            <div class="agent-status-line">
                <span class="agent-status-value" id="toolCalls">0</span> tool calls
            </div>
        </div>
    </div>
    
    <script>
        let pollInterval = null;
        let currentTasks = [];
        let isRunning = false;
        
        const filePathInput = document.getElementById('filePathInput');
        const loadBtn = document.getElementById('loadBtn');
        const refreshBtn = document.getElementById('refreshBtn');
        const runBtn = document.getElementById('runBtn');
        const stopBtn = document.getElementById('stopBtn');
        const newIdeaBtn = document.getElementById('newIdeaBtn');
        const kanbanBoard = document.getElementById('kanbanBoard');
        const globalProgress = document.getElementById('globalProgress');
        const reviewBanner = document.getElementById('reviewBanner');
        
        // Stats elements
        const statTotal = document.getElementById('statTotal');
        const statActive = document.getElementById('statActive');
        const statReview = document.getElementById('statReview');
        const workerStatus = document.getElementById('workerStatus');
        const workerCount = document.getElementById('workerCount');
        const agentStatus = document.getElementById('agentStatus');
        const agentCount = document.getElementById('agentCount');
        const toolCalls = document.getElementById('toolCalls');
        const timestamp = document.getElementById('timestamp');
        
        function updateTimestamp() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            timestamp.textContent = timeStr;
        }
        updateTimestamp();
        setInterval(updateTimestamp, 1000);
        
        filePathInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                loadBtn.click();
            }
        });
        
        loadBtn.addEventListener('click', async () => {
            const filePath = filePathInput.value.trim();
            if (!filePath) {
                alert('Please enter a file path');
                return;
            }
            
            try {
                const response = await fetch('/api/load', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file: filePath })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentTasks = data.tasks;
                    renderBoard(data.tasks);
                    runBtn.disabled = false;
                    filePathInput.value = data.file_path || filePath;
                    updateStats(data.tasks);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error loading file: ' + error.message);
            }
        });
        
        refreshBtn.addEventListener('click', () => {
            if (pollInterval) {
                updateStatus();
            }
        });
        
        runBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/run', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    isRunning = true;
                    runBtn.disabled = true;
                    stopBtn.disabled = false;
                    startPolling();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error starting execution: ' + error.message);
            }
        });
        
        stopBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/stop', { method: 'POST' });
                stopBtn.disabled = true;
                stopPolling();
                isRunning = false;
            } catch (error) {
                alert('Error stopping execution: ' + error.message);
            }
        });
        
        newIdeaBtn.addEventListener('click', () => {
            filePathInput.value = '';
            filePathInput.focus();
        });
        
        function startPolling() {
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(updateStatus, 1000);
            updateStatus();
        }
        
        function stopPolling() {
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        }
        
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.tasks && data.tasks.length > 0) {
                    currentTasks = data.tasks;
                    renderBoard(data.tasks);
                    updateStats(data.tasks);
                    
                    if (data.progress) {
                        const percentage = Math.round(data.progress.percentage);
                        globalProgress.style.width = percentage + '%';
                    }
                    
                    if (data.workers !== undefined) {
                        if (data.workers > 0) {
                            workerStatus.style.display = 'flex';
                            workerCount.textContent = data.workers;
                        } else {
                            workerStatus.style.display = 'none';
                        }
                    }
                    
                    if (data.tool_calls !== undefined) {
                        if (data.tool_calls > 0) {
                            agentStatus.style.display = 'flex';
                            agentCount.textContent = data.workers || 0;
                            toolCalls.textContent = data.tool_calls;
                        }
                    }
                }
                
                if (!data.running && pollInterval) {
                    stopPolling();
                    runBtn.disabled = false;
                    stopBtn.disabled = true;
                    isRunning = false;
                }
            } catch (error) {
                console.error('Error updating status:', error);
            }
        }
        
        function updateStats(tasks) {
            const total = tasks.length;
            const active = tasks.filter(t => t.status === 'running').length;
            const review = tasks.filter(t => t.status === 'waiting_human' || t.status === 'blocked').length;
            
            statTotal.textContent = total;
            statActive.textContent = active;
            statReview.textContent = review;
            
            if (review > 0) {
                reviewBanner.style.display = 'flex';
                document.getElementById('reviewCount').textContent = review;
            } else {
                reviewBanner.style.display = 'none';
            }
        }
        
        function renderBoard(tasks) {
            const columns = {
                'pending': { title: '⏳ Pending', icon: '⏳', tasks: [] },
                'running': { title: '🔄 Running', icon: '🔄', tasks: [] },
                'waiting_human': { title: '👤 Human Gate', icon: '👤', tasks: [] },
                'completed': { title: '✅ Completed', icon: '✅', tasks: [] },
                'failed': { title: '❌ Failed', icon: '❌', tasks: [] },
                'blocked': { title: '⏸️ Blocked', icon: '⏸️', tasks: [] }
            };
            
            tasks.forEach(task => {
                const status = task.status || 'pending';
                if (columns[status]) {
                    columns[status].tasks.push(task);
                } else if (status === 'completed' && task.task_path.includes('shipped')) {
                    // Handle shipped tasks
                    if (!columns['shipped']) {
                        columns['shipped'] = { title: '📦 Shipped', icon: '📦', tasks: [] };
                    }
                    columns['shipped'].tasks.push(task);
                } else {
                    columns['pending'].tasks.push(task);
                }
            });
            
            kanbanBoard.innerHTML = Object.entries(columns).map(([key, column]) => `
                <div class="kanban-column">
                    <div class="column-header">
                        <span>${column.title}</span>
                        <span class="column-count">${column.tasks.length}</span>
                    </div>
                    <div class="column-sections">
                        ${column.tasks.length === 0 ? 
                            '<div class="empty-state"><div class="empty-state-text">No tasks</div></div>' :
                            column.tasks.map(task => renderTaskCard(task)).join('')
                        }
                    </div>
                </div>
            `).join('');
        }
        
        function renderTaskCard(task) {
            const statusMap = {
                'pending': { tag: 'PENDING', class: 'tag-pending' },
                'running': { tag: 'RUNNING', class: 'tag-running' },
                'starting': { tag: 'STARTING', class: 'tag-starting' },
                'completed': { tag: 'COMPLETED', class: 'tag-completed' },
                'failed': { tag: 'FAILED', class: 'tag-failed' },
                'blocked': { tag: 'BLOCKED', class: 'tag-blocked' },
                'waiting_human': { tag: 'AWAITING HUMAN', class: 'tag-awaiting' }
            };
            
            const statusInfo = statusMap[task.status] || statusMap['pending'];
            const mission = task.action || 'Build MVP';
            
            return `
                <div class="task-card ${task.status}" data-task-id="${task.id}">
                    <div class="task-tag ${statusInfo.class}">${statusInfo.tag}</div>
                    <div class="task-title">${task.task || task.id}</div>
                    <div class="task-mission">${mission}</div>
                    ${task.task_path ? `<div class="task-path">${task.task_path}</div>` : ''}
                    ${task.action && task.action !== mission ? `<div class="task-action">${task.action}</div>` : ''}
                </div>
            `;
        }
        
        // Initial empty state
        renderBoard([]);
    </script>
</body>
</html>
"""
