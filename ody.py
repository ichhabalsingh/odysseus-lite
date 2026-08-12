#!/usr/bin/env python3
import os
import sys
import argparse
import ollama

from core.config import Config
from core.registry import ToolRegistry
from core.session import AgentSession
from core.tools.system_ops import run_bash
from core.tools.web_ops import web_search
from core.tools.file_ops import read_file, write_file, append_file
from core.rag import query_workspace_rag, get_rag_indexer, LocalRAG

# =====================================================================
# 1. CLI LIFECYCLE HANDLERS & PERMISSION GATE
# =====================================================================
def log_debug(section: str, text: str, color="\033[94m"):
    """Prints highly readable console headers for tracking thoughts/actions."""
    end_color = "\033[0m"
    print(f"\n{color}=== {section} ==={end_color}\n{text}")

def cli_permission_gate(tool_tag: str, detail_message: str) -> bool:
    """CLI handler for interactive user approval before running critical tools."""
    print(f"\n\033[91m[WARNING] [Agent requesting shell/file permission]:\033[0m {detail_message}")
    approval = input("Approve? (y/n): ").strip().lower()
    if approval in ["y", "yes"]:
        return True
    print("[DENIED] Action denied by user.")
    return False

# Lifecycle callback functions
def on_status(msg: str):
    print(f"[INFO] [Status] {msg}")

def on_thought(thought: str):
    log_debug("THOUGHT", thought)

def on_action(tag: str, args_str: str):
    log_debug("ACTION", args_str, color="\033[93m")

def on_observation(msg: str):
    log_debug("OBSERVATION", msg, color="\033[90m")

def on_cycle(msg: str):
    print(f"\n--- {msg} ---")

def on_answer(history_context: str):
    print("\n=== GOAL COMPLETE ===")
    log_debug("FINAL RESULTS SUMMARY", history_context, color="\033[92m")

def on_error(msg: str):
    print(f"\033[91m[ERROR] Error: {msg}\033[0m")

# =====================================================================
# 2. TOOL REGISTRY & REGISTRATION
# =====================================================================
registry = ToolRegistry(permission_callback=cli_permission_gate)

registry.tool(
    name="tool_bash",
    description="Executes a shell command in the local workspace.",
    usage='{"command": "shell command string"}'
)(run_bash)

registry.tool(
    name="tool_search",
    description="Searches the web for facts, API documentation, or code syntax.",
    usage='{"query": "search keywords"}'
)(web_search)

registry.tool(
    name="tool_read_file",
    description="Reads the text content of a file relative to the workspace. Automatically extracts text from PDF files.",
    usage='{"path": "file_path"}'
)(read_file)

registry.tool(
    name="tool_write_file",
    description="Writes raw content directly to a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_write_file path="file.txt">content here</tool_write_file>'
)(write_file)

registry.tool(
    name="tool_append_file",
    description="Appends raw content to the end of a file. Immune to JSON escaping errors.",
    usage='Use XML block tagging: <tool_append_file path="file.txt">content to append</tool_append_file>'
)(append_file)

registry.tool(
    name="tool_workspace_rag",
    description="Queries local codebase files for existing helper functions, definitions, or documentation.",
    usage='{"query": "search query"}'
)(query_workspace_rag)

# =====================================================================
# 3. CLI ENTRYPOINT
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odysseus Lite: Local AI Workspace Assistant CLI")
    parser.add_argument("goal", type=str, help="The research or coding task goal for the agent.")
    parser.add_argument("-w", "--workspace", type=str, default=os.getcwd(), help="Path to the workspace directory to scan and work in.")
    parser.add_argument("-p", "--planner", type=str, default=Config.PLANNER_MODEL, help="Model to use for step planning.")
    parser.add_argument("-e", "--executor", type=str, default=Config.EXECUTOR_MODEL, help="Model to use for step execution.")
    args = parser.parse_args()
    
    # Update configurations
    Config.WORKSPACE_DIR = os.path.abspath(args.workspace)
    Config.PLANNER_MODEL = args.planner
    Config.EXECUTOR_MODEL = args.executor
    if not os.path.exists(Config.WORKSPACE_DIR):
        print(f"Error: Workspace path '{Config.WORKSPACE_DIR}' does not exist.")
        sys.exit(1)
        
    print(f"Target Workspace: {Config.WORKSPACE_DIR}")
    
    # Re-initialize the local RAG engine for the target workspace
    get_rag_indexer(Config.WORKSPACE_DIR)
    
    # Check if Ollama is running and has models pulled
    try:
        ollama.chat(model=Config.EXECUTOR_MODEL, messages=[{"role": "user", "content": "ping"}], keep_alive=Config.KEEP_ALIVE)
        ollama.chat(model=Config.PLANNER_MODEL, messages=[{"role": "user", "content": "ping"}], keep_alive=Config.KEEP_ALIVE)
    except Exception as e:
        print(f"Error: Cannot connect to Ollama. Make sure 'ollama serve' is running and you have pulled '{Config.EXECUTOR_MODEL}' and '{Config.PLANNER_MODEL}'.")
        print(f"Details: {e}")
        sys.exit(1)
        
    session = AgentSession(
        goal=args.goal,
        registry=registry,
        on_status=on_status,
        on_thought=on_thought,
        on_action=on_action,
        on_observation=on_observation,
        on_cycle=on_cycle,
        on_answer=on_answer,
        on_error=on_error
    )
    session.execute_loop()
