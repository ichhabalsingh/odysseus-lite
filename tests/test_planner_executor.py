import os
import sys
import json
import time
import re
import ollama

# Add parent directory to system path to import ody configurations and tools
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ody import Config, registry, LocalRAG

PLANNER_MODEL = "llama3.1:8b"
EXECUTOR_MODEL = "qwen2.5-coder:3b-instruct"

# =====================================================================
# HYPER-TOLERANT PARSER
# =====================================================================
def parse_action_tolerant(text: str) -> tuple:
    action_text = text
    if "ACTION:" in text:
        action_text = text.split("ACTION:")[-1]
        
    write_match = re.search(r'<tool_write_file\s+path="([^"]+)">([\s\S]*?)</tool_write_file>', action_text)
    if write_match:
        return "tool_write_file", {"path": write_match.group(1), "content": write_match.group(2)}

    read_match = re.search(r'<tool_read_file\s+path="([^"]+)"(?:\s*/)?>(?:</tool_read_file>)?', action_text)
    if read_match:
        return "tool_read_file", {"path": read_match.group(1)}

    for name in registry.registry.keys():
        pattern = rf"<{name}>(.*?)</{name}>"
        m = re.search(pattern, action_text, re.DOTALL)
        if m:
            tag = name
            content_inner = m.group(1).strip()
            if not (content_inner.startswith("{") and content_inner.endswith("}")):
                args = {"path": content_inner} if tag == "tool_read_file" else {"query": content_inner}
            else:
                try:
                    args = json.loads(content_inner)
                except:
                    args = {"path": content_inner}
            return tag, args
    return None, None

# =====================================================================
# METHOD A: SINGLE-MODEL REACT
# =====================================================================
def run_single_model_react(goal, target_file, max_cycles=6):
    print(f"\n[SINGLE-MODEL] Starting ReAct loop for goal: {goal}")
    # Remove output file if it exists to ensure clean test
    full_path = os.path.join(Config.WORKSPACE_DIR, target_file)
    if os.path.exists(full_path):
        os.remove(full_path)

    system_prompt = f"""You are a helpful coding assistant. Solve the user's goal step-by-step.
{registry.get_system_instructions()}
Rules:
1. For each turn, you MUST output:
   THOUGHT: Your reasoning.
   ACTION: <tool_name>{{"arguments"}}</tool_name> OR ANSWER: your final answer.
2. You can use raw XML blocks for writing: <tool_write_file path="file.txt">content</tool_write_file>
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"GOAL: {goal}"}
    ]
    
    start_time = time.time()
    cycles = 0
    errors = 0
    success = False
    
    for cycle in range(1, max_cycles + 1):
        cycles += 1
        res = ollama.chat(
            model=EXECUTOR_MODEL,
            messages=messages,
            options={"temperature": 0.1}
        )
        response_content = res['message']['content']
        messages.append({"role": "assistant", "content": response_content})
        
        tag, args = parse_action_tolerant(response_content)
        
        if "ANSWER:" in response_content and not tag:
            print(f"[SINGLE-MODEL] Cycle {cycle}: Answer generated.")
            break
            
        if tag:
            print(f"[SINGLE-MODEL] Cycle {cycle}: Called <{tag}> with {args}")
            observation = registry.execute(tag, args)
            messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
        else:
            errors += 1
            print(f"[SINGLE-MODEL] Cycle {cycle}: No tag found. Error triggered.")
            messages.append({
                "role": "user", 
                "content": "Error: You did not output a valid tool tag. Choose a tool or ANSWER."
            })
            
        # Check if file was successfully created
        if os.path.exists(full_path) and os.path.getsize(full_path) > 10:
            success = True
            
    elapsed = time.time() - start_time
    # Ensure final success check
    if os.path.exists(full_path) and os.path.getsize(full_path) > 10:
        success = True
        
    return {
        "success": success,
        "cycles": cycles,
        "errors": errors,
        "time": round(elapsed, 2)
    }

def run_planner(goal):
    """Planner takes a complex goal and outputs a structured list of tool-constrained steps in JSON format."""
    print(f"\n[PLANNER] Analyzing goal using {PLANNER_MODEL}...")
    
    # Format the list of registered tools
    tools_info = ""
    for name, tool in registry.registry.items():
        tools_info += f"- {name}: {tool['description']} (Usage schema: {tool['usage']})\n"
    tools_info += "- tool_write_file: Write raw file contents. (Usage schema: <tool_write_file path=\"file\">content</tool_write_file>)\n"
    tools_info += "- tool_append_file: Append raw contents. (Usage schema: <tool_append_file path=\"file\">content</tool_append_file>)\n"

    prompt = f"""You are the Schema-Driven Planner. Given a user goal in a coding repository, break it down into a sequence of simple, atomic steps.
Each step MUST map directly to one of the available tools below. Do not plan steps that cannot be executed by these tools.

Available Tools:
{tools_info}

Output the plan as a JSON list of objects. Each object MUST contain:
- "tool": The exact tool name from the list.
- "description": The task description for the Executor.

Do not output any other explanation, markdown, or text.

Example JSON output:
[
  {{"tool": "tool_read_file", "description": "Read the file grade_rice.py to inspect its categories"}},
  {{"tool": "tool_write_file", "description": "Write the categories summary to tests_summary.txt"}}
]

User Goal: {goal}
"""
    response = ollama.chat(
        model=PLANNER_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response['message']['content'].strip()
    
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    
    if content.startswith("```json"): content = content[7:]
    if content.startswith("```"): content = content[3:]
    if content.endswith("```"): content = content[:-3]
    content = content.strip()
    
    print(f"[PLANNER OUTPUT] Cleaned Plan Content:\n{content}")
    
    try:
        steps = json.loads(content)
        return steps
    except Exception as e:
        print(f"[PLANNER ERROR] Failed to parse JSON plan: {e}. Trying fallback.")
        # Fallback to parsing basic list structure if JSON parsing failed
        steps = []
        matches = re.findall(r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*\}', content)
        for tool, desc in matches:
            steps.append({"tool": tool, "description": desc})
        if not steps:
            # Vague list mapping fallback
            steps = [{"tool": "tool_read_file", "description": f"Attempt step: {content}"}]
        return steps

def run_executor_step(step_obj, step_num, total_steps, history_context):
    """Executor takes a pre-mapped tool and description, and generates the arguments."""
    tool_name = step_obj.get("tool", "tool_read_file")
    step_desc = step_obj.get("description", "")
    
    print(f"\n[EXECUTOR] Step {step_num}/{total_steps}: Using {tool_name} to '{step_desc}'")
    
    # Retrieve schema info
    tool_desc = "Custom file writing"
    tool_usage = "XML block"
    if tool_name in registry.registry:
        tool_desc = registry.registry[tool_name]['description']
        tool_usage = registry.registry[tool_name]['usage']
        
    prompt = f"""You are the Executor. Your target is to run the tool "{tool_name}" to accomplish this goal:
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
    response = ollama.chat(
        model=EXECUTOR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1}
    )
    content = response['message']['content'].strip()
    print(f"--- Executor Output ---\n{content}\n-----------------------")
    
    # Isolate ACTION block
    action_text = content
    if "ACTION:" in content:
        action_text = content.split("ACTION:")[-1]
        
    # Standard hyper-tolerant parser
    write_match = re.search(r'<tool_write_file\s+path="([^"]+)">([\s\S]*?)</tool_write_file>', action_text)
    if write_match:
        tag, args = "tool_write_file", {"path": write_match.group(1), "content": write_match.group(2)}
    elif re.search(r'<tool_append_file\s+path="([^"]+)">([\s\S]*?)</tool_append_file>', action_text):
        append_match = re.search(r'<tool_append_file\s+path="([^"]+)">([\s\S]*?)</tool_append_file>', action_text)
        tag, args = "tool_append_file", {"path": append_match.group(1), "content": append_match.group(2)}
    else:
        read_match = re.search(r'<tool_read_file\s+path="([^"]+)"(?:\s*/)?>(?:</tool_read_file>)?', action_text)
        if read_match:
            tag, args = "tool_read_file", {"path": read_match.group(1)}
        else:
            tag, args = None, None
            # Generic tag matching fallback
            pattern = rf"<{tool_name}>(.*?)</{tool_name}>"
            m = re.search(pattern, action_text, re.DOTALL)
            if m:
                tag = tool_name
                content_inner = m.group(1).strip()
                if not (content_inner.startswith("{") and content_inner.endswith("}")):
                    args = {"path": content_inner} if tag == "tool_read_file" else {"query": content_inner}
                else:
                    try:
                        args = json.loads(content_inner)
                    except:
                        args = {"path": content_inner}
                        
    if tag:
        print(f"[ACTION] Running <{tag}> with {args}")
        observation = registry.execute(tag, args)
        
        # State Compactor: Condense raw tool observation into a 1-2 sentence summary
        print("[COMPACTOR] Condensing tool observation...")
        compact_prompt = f"""Summarize the key information found in this tool observation for the step "{step_desc}".
Keep it to 1 or 2 sentences max. Focus only on facts, paths, ports, or versions found.

Tool Observation:
{observation[:4000]}
"""
        compact_res = ollama.chat(
            model=EXECUTOR_MODEL,
            messages=[{"role": "user", "content": compact_prompt}],
            options={"temperature": 0.1}
        )
        summary = compact_res['message']['content'].strip()
        print(f"[COMPACTOR] Summary: {summary}")
        
        return f"Step: {step_desc}\nAction: <{tag}> {args}\nResult Summary: {summary}\n\n"
    else:
        print("[EXECUTOR ERROR] No tool tag outputted by Executor.")
        return f"Step: {step_desc}\nAction: None\nResult: {content}\n\n"

# =====================================================================
# METHOD B: PLANNER-EXECUTOR
# =====================================================================
def run_planner_executor(goal, target_file):
    print(f"\n[PLANNER-EXECUTOR] Starting workflow for goal: {goal}")
    full_path = os.path.join(Config.WORKSPACE_DIR, target_file)
    if os.path.exists(full_path):
        os.remove(full_path)

    start_time = time.time()
    
    # 1. Planner Phase
    steps = run_planner(goal)
    print(f"[PLANNER] Schema Steps generated: {steps}")
    
    # 2. Executor Phase
    history_context = ""
    cycles = 0
    errors = 0
    success = False
    
    for idx, step in enumerate(steps, 1):
        cycles += 1
        result = run_executor_step(step, idx, len(steps), history_context)
        history_context += result
        if "Action: None" in result or "Error" in result:
            errors += 1
            
        if os.path.exists(full_path) and os.path.getsize(full_path) > 10:
            success = True

    elapsed = time.time() - start_time
    if os.path.exists(full_path) and os.path.getsize(full_path) > 10:
        success = True
        
    return {
        "success": success,
        "cycles": cycles,
        "errors": errors,
        "time": round(elapsed, 2)
    }

# =====================================================================
# BENCHMARK SUITE
# =====================================================================
def run_benchmark():
    Config.WORKSPACE_DIR = "/home/omen/Projects/Rice"
    _ = LocalRAG(Config.WORKSPACE_DIR)
    
    tasks = [
        {
            "id": 1,
            "goal": "Read requirements.txt and write a detailed summary list of dependencies and their versions to req_summary.txt",
            "file": "req_summary.txt"
        },
        {
            "id": 2,
            "goal": "Read main.py, check if there is any CORS middleware or port configuration, and write the findings report to cors_report.txt",
            "file": "cors_report.txt"
        },
        {
            "id": 3,
            "goal": "Read smart_grade_rice.py and grade_rice.py, compare their best model weight pt paths, and write the comparison to yolo_comparison.txt",
            "file": "yolo_comparison.txt"
        }
    ]
    
    results = []
    
    for t in tasks:
        print(f"\n==================================================")
        print(f"RUNNING BENCHMARK TASK {t['id']}: {t['goal']}")
        print(f"==================================================")
        
        # Method A
        res_a = run_single_model_react(t["goal"], t["file"])
        
        # Method B
        res_b = run_planner_executor(t["goal"], t["file"])
        
        results.append({
            "id": t["id"],
            "goal": t["goal"],
            "react": res_a,
            "split": res_b
        })
        
    # Clean up created files
    for t in tasks:
        full_path = os.path.join(Config.WORKSPACE_DIR, t["file"])
        if os.path.exists(full_path):
            os.remove(full_path)
            
    # Print comparison matrix
    print("\n" + "="*80)
    print("                    ODYSSEUS LITE BENCHMARK REPORT")
    print("="*80)
    print(f"{'Task ID':<8}{'Architecture':<22}{'Success':<12}{'Cycles':<10}{'Errors':<10}{'Time (s)':<10}")
    print("-"*80)
    
    for r in results:
        print(f"Task {r['id']:<4}    {'Single-Model ReAct':<22}{str(r['react']['success']):<12}{r['react']['cycles']:<10}{r['react']['errors']:<10}{r['react']['time']:<10}")
        print(f"         {'Planner-Executor':<22}{str(r['split']['success']):<12}{r['split']['cycles']:<10}{r['split']['errors']:<10}{r['split']['time']:<10}")
        print("-"*80)

if __name__ == "__main__":
    run_benchmark()
