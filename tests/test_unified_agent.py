import re
import json
import subprocess
import os
import time
import ollama
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
MODEL = "llama3.1:8b"  # Modify to granite4.1:3b if you want to test the 3B model

SYSTEM_PROMPT = """You are Odysseus Unified, an advanced workspace agent.
You think step-by-step and use tools to solve user tasks.

For each turn, you MUST output:
1. THOUGHT: Reason about the task, plan next steps, and choose a tool.
2. ACTION: Call exactly ONE tool tag.
3. OBSERVE: You will receive the tool result from the system.
4. ANSWER: Output your final response once the goal is fully achieved.

AVAILABLE TOOLS:
- <tool_search>{"query": "search query"}</tool_search>
  Search the web for documentation, facts, or versions.

- <tool_bash>{"command": "shell command"}</tool_bash>
  Run terminal commands.

- <tool_read_file>{"path": "file_path"}</tool_read_file>
  Read contents of a file in the workspace.

- <tool_write_file>{"path": "file_path", "content": "file contents"}</tool_write_file>
  Write/overwrite a file in the workspace.

Rules:
1. Output exactly ONE action tag per turn.
2. Ensure arguments inside tags are valid JSON.
"""

# --- TOOLS ---
def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            return "\n".join([f"Snippet: {r['body']}" for r in results]) if results else "No results."
    except Exception as e:
        return f"Search error: {str(e)}"

def run_bash(command: str) -> str:
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return (res.stdout + res.stderr) if (res.stdout or res.stderr) else "Command completed."
    except Exception as e:
        return f"Execution error: {str(e)}"

def read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Read error: {str(e)}"

def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Write error: {str(e)}"

def execute_tool(tag: str, args: dict) -> str:
    print(f"\n   [System Executing]: {tag}...")
    if tag == "tool_search":
        return web_search(args.get("query", ""))
    elif tag == "tool_bash":
        return run_bash(args.get("command", ""))
    elif tag == "tool_read_file":
        return read_file(args.get("path", ""))
    elif tag == "tool_write_file":
        return write_file(args.get("path", ""), args.get("content", ""))
    return f"Unknown tool: {tag}"

# --- RUN LOOP ---
def run_unified_agent(prompt: str):
    print(f"Goal: {prompt}\n" + "="*60)
    start_time = time.time()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    max_steps = 8
    for step in range(1, max_steps + 1):
        print(f"\n--- CYCLE {step} ---")
        
        t0 = time.time()
        res = ollama.chat(
            model=MODEL,
            messages=messages,
            options={"temperature": 0.1, "num_ctx": 4096},
            keep_alive="5m"
        )
        print(f"(LLM Response generated in {time.time()-t0:.2f}s)")
        
        assistant_content = res['message']['content']
        print(f"[Agent Response]:\n{assistant_content}")
        messages.append({"role": "assistant", "content": assistant_content})
        
        if "ANSWER:" in assistant_content:
            print(f"\n✓ Task finished in {time.time() - start_time:.2f} seconds!")
            break
            
        action_found = False
        for tag in ["tool_search", "tool_bash", "tool_read_file", "tool_write_file"]:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, assistant_content, re.DOTALL)
            if match:
                action_found = True
                args_str = match.group(1).strip()
                try:
                    args = json.loads(args_str)
                    observation = execute_tool(tag, args)
                except json.JSONDecodeError:
                    observation = f"Error: Invalid JSON format inside <{tag}>."
                
                print(f"[System Observation]: {observation[:200]}...")
                messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
                break
                
        if not action_found:
            messages.append({"role": "user", "content": "Please continue. Use an action tag or formulate your final ANSWER."})

if __name__ == "__main__":
    test_task = "Search the web for the latest stable python version, list files in this folder to see if any python files exist, and write a summary.txt detailing your findings."
    run_unified_agent(test_task)
