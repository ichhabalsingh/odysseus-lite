import os
import re
import json
import time
import subprocess
import threading
import queue
import ast
from flask import Flask, render_template, request, jsonify, Response
from duckduckgo_search import DDGS
from ody import Config, LocalRAG
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
        self.model = "qwen2.5-coder:3b-instruct"
        self.rag_indexer = None

state = AgentState()

# =====================================================================
# TOOL REGISTRY & ACTIONS
# =====================================================================
class WebToolRegistry:
    def __init__(self):
        self.registry = {}

    def tool(self, name: str, description: str, usage: str):
        def decorator(func):
            self.registry[name] = {"func": func, "description": description, "usage": usage}
            return func
        return decorator

    def get_instructions(self) -> str:
        instructions = "AVAILABLE TOOLS:\n"
        for name, details in self.registry.items():
            instructions += f"- <{name}>{details['usage']}</{name}>\n  Description: {details['description']}\n\n"
        return instructions

    def execute(self, name: str, args: dict) -> str:
        if name not in self.registry:
            return f"Error: Tool {name} not found."
        try:
            return self.registry[name]["func"](args)
        except Exception as e:
            return f"Tool Execution Error: {str(e)}"

web_registry = WebToolRegistry()

@web_registry.tool(
    name="tool_bash",
    description="Executes a shell command in the local workspace.",
    usage='{"command": "shell command string"}'
)
def web_run_bash(args: dict) -> str:
    cmd = args.get("command", "")
    if not cmd:
        return "Error: No command provided."
        
    # Request permission from Web UI
    decision = request_ui_permission("tool_bash", f"Execute shell command: `{cmd}`")
    if decision != "y":
        return "Error: Permission denied by user."
        
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=state.workspace_dir)
        out = ""
        if res.stdout:
            out += f"STDOUT:\n{res.stdout.strip()}\n"
        if res.stderr:
            out += f"STDERR:\n{res.stderr.strip()}\n"
        return out if out else "Command completed with exit code 0."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (15s limit)."
    except Exception as e:
        return f"Execution error: {str(e)}"

@web_registry.tool(
    name="tool_search",
    description="Searches the web for facts, API documentation, or code syntax.",
    usage='{"query": "search keywords"}'
)
def web_search(args: dict) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            return "\n".join([f"Source: {r['href']}\nSnippet: {r['body']}\n" for r in results]) if results else "No results."
    except Exception as e:
        return f"Search failed: {str(e)}"

@web_registry.tool(
    name="tool_read_file",
    description="Reads the text content of a file relative to the workspace. Automatically extracts text from PDF files.",
    usage='{"path": "file_path"}'
)
def web_read_file(args: dict) -> str:
    path = args.get("path", "")
    if not path:
        return "Error: No file path provided."
    safe_path = os.path.abspath(os.path.join(state.workspace_dir, path))
    if not safe_path.startswith(os.path.abspath(state.workspace_dir)):
        return "Permission Denied: Path is outside workspace."
    try:
        # PDF parsing fallback
        if safe_path.lower().endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(safe_path)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text if text.strip() else "PDF is empty or has no readable text."
            except Exception as pe:
                return f"PDF read error: {str(pe)}"
                
        # Standard text file read
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Read error: {str(e)}"

@web_registry.tool(
    name="tool_write_file",
    description="Writes raw content directly to a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_write_file path="file.txt">content here</tool_write_file>'
)
def web_write_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
    safe_path = os.path.abspath(os.path.join(state.workspace_dir, path))
    if not safe_path.startswith(os.path.abspath(state.workspace_dir)):
        return "Permission Denied: Path is outside workspace."
        
    decision = request_ui_permission("tool_write_file", f"Write to file: `{path}`")
    if decision != "y":
        return "Error: Permission denied by user."
        
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote file to {path}"
    except Exception as e:
        return f"Write error: {str(e)}"

@web_registry.tool(
    name="tool_append_file",
    description="Appends raw content to the end of a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_append_file path="file.txt">content to append</tool_append_file>'
)
def web_append_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
    safe_path = os.path.abspath(os.path.join(state.workspace_dir, path))
    if not safe_path.startswith(os.path.abspath(state.workspace_dir)):
        return "Permission Denied: Path is outside workspace."
        
    decision = request_ui_permission("tool_append_file", f"Append to file: `{path}`")
    if decision != "y":
        return "Error: Permission denied by user."
        
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
        return f"Successfully appended content to {path}"
    except Exception as e:
        return f"Append error: {str(e)}"

@web_registry.tool(
    name="tool_workspace_rag",
    description="Queries local codebase files for existing helper functions, definitions, or documentation.",
    usage='{"query": "search query"}'
)
def web_query_workspace_rag(args: dict) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    if not state.rag_indexer:
        state.rag_indexer = LocalRAG(state.workspace_dir)
    return state.rag_indexer.query(query)

# =====================================================================
# INTERACTIVE PERMISSION COORDINATION
# =====================================================================
def request_ui_permission(tool_tag: str, detail_message: str) -> str:
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
    return decision

# =====================================================================
# AGENT EXECUTION SESSION (Threaded runner)
# =====================================================================
class WebAgentSession:
    def __init__(self, goal: str):
        self.goal = goal
        self.messages = []
        self.setup_session()

    def setup_session(self):
        system_prompt = f"""You are Odysseus Lite, a terminal workspace assistant.
You think step-by-step and call tools to achieve tasks.

For each turn, you MUST output:
1. THOUGHT: Reason about the problem and decide which tool is needed next.
2. ACTION: Choose EXACTLY ONE tool tag to run.
   OR
   ANSWER: Provide your final response once the goal is complete.

{web_registry.get_instructions()}
Rules:
1. Output exactly ONE action tag OR the final ANSWER per turn.
2. Ensure JSON inside tags is valid.
3. NEVER write thought explanations or conversational text inside the tool tags. The tag must contain ONLY the valid JSON/python dict or raw block content.
4. For file writing/appending, use raw block XML format: 
   <tool_write_file path="file.txt">content here</tool_write_file>
   <tool_append_file path="file.txt">content to append</tool_append_file>
"""
        self.messages.append({"role": "system", "content": system_prompt})
        self.messages.append({"role": "user", "content": self.goal})

    def parse_action(self, text: str) -> tuple:
        # Isolate the ACTION section to prevent thought-tag leakage
        action_text = text
        if "ACTION:" in text:
            action_text = text.split("ACTION:")[-1]
        elif "ACTION" in text:
            action_text = text.split("ACTION")[-1]

        write_match = re.search(r'<tool_write_file\s+path="([^"]+)">([\s\S]*?)</tool_write_file>', action_text)
        if write_match:
            return "tool_write_file", {"path": write_match.group(1), "content": write_match.group(2)}

        append_match = re.search(r'<tool_append_file\s+path="([^"]+)">([\s\S]*?)</tool_append_file>', action_text)
        if append_match:
            return "tool_append_file", {"path": append_match.group(1), "content": append_match.group(2)}

        read_match = re.search(r'<tool_read_file\s+path="([^"]+)"(?:\s*/)?>(?:</tool_read_file>)?', action_text)
        if read_match:
            return "tool_read_file", {"path": read_match.group(1)}

        for tag in web_registry.registry.keys():
            if tag in ["tool_write_file", "tool_append_file"]:
                continue
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, action_text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                # Auto-wrap raw strings if not a JSON object
                if not (content.startswith("{") and content.endswith("}")):
                    if tag in ["tool_workspace_rag", "tool_search"]:
                        return tag, {"query": content}
                    elif tag == "tool_read_file":
                        return tag, {"path": content}
                try:
                    args = json.loads(content)
                    return tag, args
                except json.JSONDecodeError:
                    try:
                        args = ast.literal_eval(content)
                        return tag, args
                    except Exception:
                        return None, f"Error: Invalid JSON/Python dict inside <{tag}>."
        return None, None

    def run_planner(self, goal: str) -> list:
        state.event_queue.put({"type": "status", "message": "Analyzing goal and generating plan..."})
        tools_info = web_registry.get_instructions()
        prompt = f"""You are the Schema-Driven Planner. Break down the user goal into a sequence of atomic steps.
Each step MUST map directly to one of the available tools below. Do not plan steps that cannot be executed by these tools.

{tools_info}

Output the plan as a JSON list of objects. Each object MUST contain:
- "tool": The exact tool name from the list.
- "description": The task description for the Executor.

Do not output any other text or markdown.

Example JSON output:
[
  {{"tool": "tool_read_file", "description": "Read the file grade_rice.py to inspect its categories"}},
  {{"tool": "tool_write_file", "description": "Write the categories summary to tests_summary.txt"}}
]

User Goal: {goal}
"""
        try:
            res = ollama.chat(
                model=Config.PLANNER_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            content = res['message']['content'].strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception:
            # Fallback regex parser
            steps = []
            matches = re.findall(r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*\}', content if 'content' in locals() else "")
            for tool, desc in matches:
                steps.append({"tool": tool, "description": desc})
            return steps if steps else [{"tool": "tool_read_file", "description": f"Process: {goal}"}]

    def compact_observation(self, step_desc: str, observation: str) -> str:
        if len(observation) < 500:
            return observation
        state.event_queue.put({"type": "status", "message": "State Compactor active: condensing tool observation..."})
        prompt = f"""Summarize the key information found in this tool observation for the step "{step_desc}".
Keep it to 1 or 2 sentences max. Focus only on facts, paths, ports, or versions found.

Tool Observation:
{observation[:4000]}
"""
        res = ollama.chat(
            model=state.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        return res['message']['content'].strip()

    def execute_loop(self):
        # 1. Run Planner
        steps = self.run_planner(self.goal)
        state.event_queue.put({"type": "status", "message": f"Generated {len(steps)} steps. Initializing execution..."})
        
        # Broadcast steps to log timeline
        steps_display = "\\n".join([f"{i}. [{s.get('tool')}] {s.get('description')}" for i, s in enumerate(steps, 1)])
        state.event_queue.put({"type": "thought", "message": f"Generated Step Plan:\\n{steps_display}"})
        
        history_context = ""
        
        # 2. Loop steps
        for idx, step in enumerate(steps, 1):
            tool_name = step.get("tool", "tool_read_file")
            step_desc = step.get("description", "")
            
            state.event_queue.put({"type": "cycle", "message": f"Step {idx}/{len(steps)}"})
            state.event_queue.put({"type": "status", "message": f"Executing: {step_desc} ({tool_name})"})
            
            tool_desc = "Custom writing"
            tool_usage = "XML block"
            if tool_name in web_registry.registry:
                tool_desc = web_registry.registry[tool_name]['description']
                tool_usage = web_registry.registry[tool_name]['usage']
                
            prompt = f"""You are the Executor. Your current target is to run the tool "{tool_name}" to accomplish this goal:
"{step_desc}"

Previous history:
{history_context}

Tool Schema:
- {tool_name}: {tool_desc} (Usage format: {tool_usage})
If this is tool_write_file or tool_append_file, output raw XML block:
<{tool_name} path="filename">content</{tool_name}>

Otherwise, output standard tool tag:
<{tool_name}>{{"arguments"}}</{tool_name}>

You MUST output:
THOUGHT: Explain why you are choosing the arguments.
ACTION: The tool block populated with your arguments.
"""
            try:
                res = ollama.chat(
                    model=state.model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.1, "num_ctx": 8192}
                )
            except Exception as e:
                state.event_queue.put({"type": "error", "message": f"Ollama Connection Error: {str(e)}"})
                break
                
            response_content = res['message']['content'].strip()
            
            # Repackage XML format
            for tag in ["tool_search", "tool_bash", "tool_write_file", "tool_append_file", "tool_read_file"]:
                if f"<{tag}" in response_content and f"</{tag}>" not in response_content:
                    response_content = response_content.strip() + f"</{tag}>"
                    
            # Stream thought to dashboard
            thought_match = re.search(r"THOUGHT:(.*?)(?=ACTION:|ANSWER:|$)", response_content, re.DOTALL)
            if thought_match:
                state.event_queue.put({"type": "thought", "message": thought_match.group(1).strip()})
                
            # Parse action
            tag, args = self.parse_action(response_content)
            if not tag:
                tag = tool_name
                args = {"path": step_desc}
                
            state.event_queue.put({"type": "action", "tool": tag, "args": f"<{tag}> {args}"})
            
            # Execute tool (blocks if permission requested)
            observation = web_registry.execute(tag, args)
            state.event_queue.put({"type": "observation", "message": f"Ran tool <{tag}>: {observation[:200]}..."})
            
            # Compact observation
            compact_obs = self.compact_observation(step_desc, observation)
            if len(observation) >= 500:
                state.event_queue.put({"type": "thought", "message": f"[State Compactor] Condensation:\\n{compact_obs}"})
                
            history_context += f"Step: {step_desc}\nAction: <{tag}> {args}\nResult: {compact_obs}\n\n"

        state.event_queue.put({"type": "status", "message": "Goal achieved successfully."})
        state.event_queue.put({"type": "answer", "message": "Task complete. Output generated successfully."})

# =====================================================================
# FLASK WEB INTERFACE APIS
# =====================================================================

@app.route('/')
def index():
    # Render static front page
    return render_template('index.html', default_path=state.workspace_dir, current_model=state.model)

@app.route('/run', methods=['POST'])
def run_agent():
    data = request.json
    goal = data.get("goal", "")
    workspace = data.get("workspace", "")
    model = data.get("model", "")
    
    if not goal:
        return jsonify({"status": "error", "message": "No goal provided"}), 400
        
    state.workspace_dir = os.path.abspath(workspace)
    state.model = model
    
    # Verify path
    if not os.path.exists(state.workspace_dir):
        return jsonify({"status": "error", "message": "Workspace path does not exist"}), 400
        
    # Re-initialize local RAG for the target workspace
    state.rag_indexer = LocalRAG(state.workspace_dir)
        
    # Flush queue
    while not state.event_queue.empty():
        try:
            state.event_queue.get_nowait()
        except queue.Empty:
            break
            
    # Start agent thread
    session = WebAgentSession(goal)
    threading.Thread(target=session.execute_loop, daemon=True).start()
    
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
        print("✓ Connected to Ollama.")
    except Exception as e:
        print(f"Warning: Could not preload models over Ollama. details: {e}")
        
    # Run server locally
    app.run(host='127.0.0.1', port=5000, debug=True)
