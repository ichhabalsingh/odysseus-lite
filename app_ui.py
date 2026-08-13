import os
import json
import threading
import queue
from flask import Flask, render_template, request, jsonify, Response

from core.config import Config
from core.registry import ToolRegistry
from core.session import AgentSession
from core.tools.system_ops import run_bash
from core.tools.web_ops import web_search
from core.tools.file_ops import read_file, write_file, append_file
from core.rag import query_workspace_rag, get_rag_indexer
import ollama

app = Flask(__name__)

# =====================================================================
# GLOBAL STATE
# =====================================================================
class AgentState:
    def __init__(self):
        self.active_session = None
        self.event_queue = queue.Queue()
        self.permission_event = threading.Event()
        self.user_decision = None
        self.current_permission_request = None
        self.workspace_dir = os.getcwd()
        self.model = "qwen2.5-coder:1.5b"
        self.planner_model = "deepseek-r1:1.5b"

state = AgentState()

# =====================================================================
# INTERACTIVE PERMISSION COORDINATION
# =====================================================================
def web_permission_gate(tool_tag: str, detail_message: str) -> bool:
    """Blocks execution and posts a permission request event to the SSE stream."""
    state.permission_event.clear()
    state.current_permission_request = {"tool": tool_tag, "message": detail_message}
    
    # Broadcast to frontend
    state.event_queue.put({
        "type": "permission_request",
        "tool": tool_tag,
        "message": detail_message
    })
    
    # Block thread until user responds
    state.permission_event.wait()
    decision = state.user_decision
    state.current_permission_request = None
    return decision == "y"

# =====================================================================
# TOOL REGISTRY & REGISTRATION
# =====================================================================
web_registry = ToolRegistry(permission_callback=web_permission_gate)

web_registry.tool(
    name="tool_bash",
    description="Executes a shell command in the local workspace.",
    usage='{"command": "shell command string"}'
)(run_bash)

web_registry.tool(
    name="tool_search",
    description="Searches the web for facts, API documentation, or code syntax.",
    usage='{"query": "search keywords"}'
)(web_search)

web_registry.tool(
    name="tool_read_file",
    description="Reads the text content of a file relative to the workspace. Automatically extracts text from PDF files.",
    usage='{"path": "file_path"}'
)(read_file)

web_registry.tool(
    name="tool_write_file",
    description="Writes raw content directly to a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_write_file path="file.txt">content here</tool_write_file>'
)(write_file)

web_registry.tool(
    name="tool_append_file",
    description="Appends raw content to the end of a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_append_file path="file.txt">content to append</tool_append_file>'
)(append_file)

web_registry.tool(
    name="tool_workspace_rag",
    description="Queries local codebase files for existing helper functions, definitions, or documentation.",
    usage='{"query": "search query"}'
)(query_workspace_rag)

# =====================================================================
# AGENT RUNNER THREAD
# =====================================================================
def run_agent_loop(goal: str):
    session = AgentSession(
        goal=goal,
        registry=web_registry,
        on_status=lambda msg: state.event_queue.put({"type": "status", "message": msg}),
        on_thought=lambda msg: state.event_queue.put({"type": "thought", "message": msg}),
        on_action=lambda tool, args: state.event_queue.put({"type": "action", "tool": tool, "args": args}),
        on_observation=lambda msg: state.event_queue.put({"type": "observation", "message": msg}),
        on_cycle=lambda msg: state.event_queue.put({"type": "cycle", "message": msg}),
        on_answer=lambda history: state.event_queue.put({"type": "answer", "message": "Task complete. Output generated successfully."}),
        on_error=lambda msg: state.event_queue.put({"type": "error", "message": msg})
    )
    session.execute_loop()

# =====================================================================
# FLASK WEB INTERFACE APIS
# =====================================================================
@app.route('/')
def index():
    return render_template('index.html', default_path=state.workspace_dir, current_model=state.model, current_planner=state.planner_model)

@app.route('/run', methods=['POST'])
def run_agent():
    data = request.json
    goal = data.get("goal", "")
    workspace = data.get("workspace", "")
    model = data.get("model", "")
    planner_model = data.get("planner_model", "llama3.1:8b")
    
    if not goal:
        return jsonify({"status": "error", "message": "No goal provided"}), 400
        
    state.workspace_dir = os.path.abspath(workspace)
    state.model = model
    state.planner_model = planner_model
    
    # Sync with core configuration
    Config.WORKSPACE_DIR = state.workspace_dir
    Config.EXECUTOR_MODEL = state.model
    Config.PLANNER_MODEL = state.planner_model
    
    if not os.path.exists(state.workspace_dir):
        return jsonify({"status": "error", "message": "Workspace path does not exist"}), 400
        
    # Re-initialize local RAG for the target workspace
    get_rag_indexer(state.workspace_dir)
        
    # Flush event queue
    while not state.event_queue.empty():
        try:
            state.event_queue.get_nowait()
        except queue.Empty:
            break
            
    # Start agent thread
    threading.Thread(target=run_agent_loop, args=(goal,), daemon=True).start()
    
    return jsonify({"status": "success", "message": "Agent initialized"})

@app.route('/approve', methods=['POST'])
def approve_permission():
    data = request.json
    decision = data.get("decision", "n") # 'y' or 'n'
    state.user_decision = decision
    state.permission_event.set()
    return jsonify({"status": "success"})

@app.route('/stream')
def sse_stream():
    """Streams live log events directly to the browser chat window."""
    def event_generator():
        while True:
            # Block until event is put in queue
            event = state.event_queue.get()
            yield f"data: {json.dumps(event)}\n\n"
    return Response(event_generator(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Make templates directory if missing
    os.makedirs('templates', exist_ok=True)
    
    # Pre-warm models in memory
    try:
        ollama.chat(model=Config.EXECUTOR_MODEL, messages=[{"role": "user", "content": "ping"}], keep_alive=Config.KEEP_ALIVE)
        ollama.chat(model=Config.PLANNER_MODEL, messages=[{"role": "user", "content": "ping"}], keep_alive=Config.KEEP_ALIVE)
        print("[INFO] Connected to Ollama.")
    except Exception as e:
        print(f"[WARNING] Could not preload models over Ollama. details: {e}")
        
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "t", "yes")
    app.run(host='127.0.0.1', port=5000, debug=debug_mode)
