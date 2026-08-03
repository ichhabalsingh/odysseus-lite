#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import argparse
import subprocess
import ast
from duckduckgo_search import DDGS
import ollama

# =====================================================================
# 1. CONFIGURATION
# =====================================================================
class Config:
    MODEL = "qwen2.5-coder:3b-instruct"  # Optimized local coder/agent model
    NUM_CTX = 8192                       # High context window
    TEMPERATURE = 0.1                    # Deterministic tool execution
    WORKSPACE_DIR = os.getcwd()          # Target workspace directory
    KEEP_ALIVE = "10m"                   # Grace period to prevent VRAM swapping

# =====================================================================
# 2. THE TOOL REGISTRY (Decorator-based scalability)
# =====================================================================
class ToolRegistry:
    def __init__(self):
        self.registry = {}

    def tool(self, name: str, description: str, usage: str):
        """Decorator to register a python function as an agent tool."""
        def decorator(func):
            self.registry[name] = {
                "func": func,
                "description": description,
                "usage": usage
            }
            return func
        return decorator

    def get_system_instructions(self) -> str:
        """Generates list of tools and formatting rules for the LLM system prompt."""
        instructions = "AVAILABLE TOOLS:\n"
        for name, details in self.registry.items():
            instructions += f"- <{name}>{details['usage']}</{name}>\n  Description: {details['description']}\n\n"
        return instructions

    def execute(self, tag: str, args_dict: dict) -> str:
        """Invokes a registered tool by its XML tag name."""
        if tag not in self.registry:
            return f"Error: Tool <{tag}> is not registered."
        try:
            return self.registry[tag]["func"](args_dict)
        except Exception as e:
            return f"Error executing <{tag}>: {str(e)}"

# Instantiate registry
registry = ToolRegistry()

# =====================================================================
# 3. TOOL DEFINITIONS (Easily add more here)
# =====================================================================

@registry.tool(
    name="tool_bash",
    description="Executes a shell command in the local workspace.",
    usage='{"command": "shell command string"}'
)
def run_bash(args: dict) -> str:
    cmd = args.get("command", "")
    if not cmd:
        return "Error: No command provided."
        
    # Interactive Permission Gate
    print(f"\n\033[91m⚠️  [Agent requesting shell execution]:\033[0m {cmd}")
    approval = input("👉 Approve? (y/n): ").strip().lower()
    if approval not in ["y", "yes"]:
        print("❌ Action denied by user.")
        return "Error: Permission denied by user."
        
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
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

@registry.tool(
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
            if not results:
                return "No search results found."
            return "\n".join([f"Source: {r['href']}\nSnippet: {r['body']}\n" for r in results])
    except Exception as e:
        return f"Search failed: {str(e)}"

@registry.tool(
    name="tool_read_file",
    description="Reads the text content of a file relative to the workspace. Automatically extracts text from PDF files.",
    usage='{"path": "file_path"}'
)
def read_file(args: dict) -> str:
    path = args.get("path", "")
    if not path:
        return "Error: No file path provided."
    safe_path = os.path.abspath(os.path.join(Config.WORKSPACE_DIR, path))
    if not safe_path.startswith(os.path.abspath(Config.WORKSPACE_DIR)):
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

@registry.tool(
    name="tool_write_file",
    description="Writes raw content directly to a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_write_file path="file.txt">content here</tool_write_file>'
)
def write_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
    safe_path = os.path.abspath(os.path.join(Config.WORKSPACE_DIR, path))
    if not safe_path.startswith(os.path.abspath(Config.WORKSPACE_DIR)):
        return "Permission Denied: Path is outside workspace."
        
    # Interactive Permission Gate
    print(f"\n\033[91m⚠️  [Agent requesting file write]:\033[0m {path}")
    approval = input("👉 Approve? (y/n): ").strip().lower()
    if approval not in ["y", "yes"]:
        print("❌ Action denied by user.")
        return "Error: Permission denied by user."
        
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote file to {path}"
    except Exception as e:
        return f"Write error: {str(e)}"

@registry.tool(
    name="tool_append_file",
    description="Appends raw content to the end of a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_append_file path="file.txt">content to append</tool_append_file>'
)
def append_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
    safe_path = os.path.abspath(os.path.join(Config.WORKSPACE_DIR, path))
    if not safe_path.startswith(os.path.abspath(Config.WORKSPACE_DIR)):
        return "Permission Denied: Path is outside workspace."
        
    # Interactive Permission Gate
    print(f"\n\033[91m⚠️  [Agent requesting file append]:\033[0m {path}")
    approval = input("👉 Approve? (y/n): ").strip().lower()
    if approval not in ["y", "yes"]:
        print("❌ Action denied by user.")
        return "Error: Permission denied by user."
        
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
        return f"Successfully appended content to {path}"
    except Exception as e:
        return f"Append error: {str(e)}"

# =====================================================================
# 4. WORKSPACE RAG ENGINE
# =====================================================================
class LocalRAG:
    def __init__(self, workspace_dir):
        self.workspace_dir = workspace_dir
        self.chunks = []
        self.index_workspace()

    def chunk_and_add(self, path, text):
        lines = text.split("\n")
        for i in range(0, len(lines), 15):
            chunk = "\n".join(lines[i:i+20]) # Overlap of 5 lines
            self.chunks.append({
                "file": os.path.relpath(path, self.workspace_dir),
                "content": chunk
            })

    def index_workspace(self):
        """Indexes all readable files in the project, including PDFs."""
        for root, _, files in os.walk(self.workspace_dir):
            if ".venv" in root or ".git" in root:
                continue
            for file in files:
                path = os.path.join(root, file)
                if file.endswith((".py", ".md", ".json", ".txt")):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        self.chunk_and_add(path, text)
                    except:
                        pass
                elif file.endswith(".pdf"):
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(path)
                        text = ""
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        if text.strip():
                            self.chunk_and_add(path, text)
                    except:
                        pass

    def query(self, search_term: str) -> str:
        """Returns the most relevant code chunks matching terms."""
        terms = set(re.findall(r'\w+', search_term.lower()))
        matches = []
        for c in self.chunks:
            c_words = set(re.findall(r'\w+', c["content"].lower()))
            overlap = len(terms.intersection(c_words))
            if overlap > 0:
                matches.append((overlap, c))
        matches.sort(key=lambda x: x[0], reverse=True)
        if not matches:
            return "No matching codebase snippets found."
        
        output = []
        for score, m in matches[:2]:
            output.append(f"--- File: {m['file']} ---\n{m['content']}\n")
        return "\n".join(output)

# Initialize global RAG
rag_indexer = LocalRAG(Config.WORKSPACE_DIR)

@registry.tool(
    name="tool_workspace_rag",
    description="Queries local codebase files for existing helper functions, definitions, or documentation.",
    usage='{"query": "search query"}'
)
def query_workspace_rag(args: dict) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    return rag_indexer.query(query)

# =====================================================================
# 5. AGENT EXECUTION SESSION (State, Loop, & Debugging)
# =====================================================================
class AgentSession:
    def __init__(self, goal: str):
        self.goal = goal
        self.messages = []
        self.setup_session()

    def log_debug(self, section: str, text: str, color="\033[94m"):
        """Prints highly readable console headers for tracking thoughts/actions."""
        end_color = "\033[0m"
        print(f"\n{color}=== {section} ==={end_color}\n{text}")

    def setup_session(self):
        """Builds system instructions containing the registered tools list."""
        system_prompt = f"""You are Odysseus Lite, a terminal workspace assistant.
You think step-by-step and call tools to achieve tasks.

For each turn, you MUST output:
1. THOUGHT: Reason about the problem and decide which tool is needed next.
2. ACTION: Choose EXACTLY ONE tool tag to run.
   OR
   ANSWER: Provide your final response once the goal is complete.

{registry.get_system_instructions()}
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

    def repair_broken_xml_tags(self, output_text: str) -> str:
        """Detects missing closing XML tags commonly dropped by 3B models and auto-closes them."""
        tags = ["tool_search", "tool_bash", "tool_write_file", "tool_append_file", "tool_read_file", "tool_workspace_rag"]
        repaired_text = output_text
        for tag in tags:
            start_tag = f"<{tag}"
            end_tag = f"</{tag}>"
            if start_tag in repaired_text and end_tag not in repaired_text:
                repaired_text = repaired_text.strip() + end_tag
        return repaired_text

    def parse_action(self, text: str) -> tuple:
        """Parses output for tool tags, handling JSON block writing separately."""
        # Isolate the ACTION section to prevent thought-tag leakage
        action_text = text
        if "ACTION:" in text:
            action_text = text.split("ACTION:")[-1]
        elif "ACTION" in text:
            action_text = text.split("ACTION")[-1]

        # 1. Parse File Write / Append separately to bypass JSON string constraints
        write_match = re.search(r'<tool_write_file\s+path="([^"]+)">([\s\S]*?)</tool_write_file>', action_text)
        if write_match:
            return "tool_write_file", {"path": write_match.group(1), "content": write_match.group(2)}

        append_match = re.search(r'<tool_append_file\s+path="([^"]+)">([\s\S]*?)</tool_append_file>', action_text)
        if append_match:
            return "tool_append_file", {"path": append_match.group(1), "content": append_match.group(2)}

        # 2. Parse general tool tags
        for tag in registry.registry.keys():
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

    def run(self, max_cycles=10):
        self.log_debug("GOAL", self.goal, color="\033[95m")
        
        for cycle in range(1, max_cycles + 1):
            print(f"\n--- Cycle {cycle}/{max_cycles} ---")
            
            # Query LLM
            res = ollama.chat(
                model=Config.MODEL,
                messages=self.messages,
                keep_alive=Config.KEEP_ALIVE,
                options={
                    "temperature": Config.TEMPERATURE,
                    "num_ctx": Config.NUM_CTX
                }
            )
            
            response_content = res['message']['content']
            
            # Run auto-fix tag repair
            response_content = self.repair_broken_xml_tags(response_content)
            
            self.messages.append({"role": "assistant", "content": response_content})
            
            # Print thoughts & actions to stdout
            # Split thought and action for presentation
            thought_match = re.search(r"THOUGHT:(.*?)(?=ACTION:|ANSWER:|$)", response_content, re.DOTALL)
            if thought_match:
                self.log_debug("THOUGHT", thought_match.group(1).strip())
            
            if "ANSWER:" in response_content:
                answer_content = response_content.split("ANSWER:")[-1].strip()
                self.log_debug("ANSWER", answer_content, color="\033[92m")
                break
                
            # Parse and execute action
            tag, args = self.parse_action(response_content)
            
            if tag:
                self.log_debug("ACTION", f"<{tag}> {args}", color="\033[93m")
                observation = registry.execute(tag, args)
                self.log_debug("OBSERVATION", observation, color="\033[90m")
                self.messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
            elif isinstance(args, str) and args.startswith("Error:"):
                # Invalid JSON syntax
                self.log_debug("ACTION ERROR", args, color="\033[91m")
                self.messages.append({"role": "user", "content": f"OBSERVE: {args}"})
            else:
                # No action found
                prompt_more = "Please continue. Select a registered tool or output your final ANSWER."
                self.messages.append({"role": "user", "content": prompt_more})

# =====================================================================
# 6. CLI ENTRYPOINT
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odysseus Lite: Local AI Workspace Assistant CLI")
    parser.add_argument("goal", type=str, help="The research or coding task goal for the agent.")
    parser.add_argument("-w", "--workspace", type=str, default=os.getcwd(), help="Path to the workspace directory to scan and work in.")
    args = parser.parse_args()
    
    # Update configuration with target workspace path
    Config.WORKSPACE_DIR = os.path.abspath(args.workspace)
    if not os.path.exists(Config.WORKSPACE_DIR):
        print(f"Error: Workspace path '{Config.WORKSPACE_DIR}' does not exist.")
        sys.exit(1)
        
    print(f"Target Workspace: {Config.WORKSPACE_DIR}")
    
    # Re-initialize the local RAG engine for the target workspace
    rag_indexer = LocalRAG(Config.WORKSPACE_DIR)
    
    # Check if Ollama is running and has the model pulled
    try:
        # Preload the model to save startup latency
        ollama.chat(model=Config.MODEL, messages=[{"role": "user", "content": "ping"}], keep_alive=Config.KEEP_ALIVE)
    except Exception as e:
        print(f"Error: Cannot connect to Ollama. Make sure 'ollama serve' is running and you have run 'ollama pull {Config.MODEL}'.")
        print(f"Details: {e}")
        sys.exit(1)
        
    session = AgentSession(args.goal)
    session.run()
