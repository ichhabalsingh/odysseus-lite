import re
import json
import time
import ollama

# --- CONFIGURATION ---
MODEL = "granite4.1:3b"

# =====================================================================
# TEST A: CONTEXT DEGRADATION & INSTRUCTION DRIFT
# =====================================================================
def run_context_degradation_test():
    print("\n--- Running Test A: Context Degradation & Instruction Drift ---")
    
    system_prompt = """You are Odysseus Lite, a terminal assistant.
Always format your commands as: <tool_bash>{"command": "shell command"}</tool_bash>.
Do not output plain text replies. Only output tool calls."""
    
    # Generate 3,500 tokens of distraction text (simulating heavy codebase read logs)
    distraction_chunk = "Log Entry: User logged in. Database check OK. CPU Load: 15%. VRAM usage: 2.1 GB. Server active.\n" * 280
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Here is the codebase workspace data to inspect:\n" + distraction_chunk},
        {"role": "assistant", "content": "Observed. I have loaded the workspace history into memory."},
        {"role": "user", "content": "Now, list the files in the directory. You must use the tool."}
    ]
    
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=messages,
        options={"temperature": 0.0, "num_ctx": 8192} # Open up the context window
    )
    elapsed = time.time() - t0
    content = res['message']['content'].strip()
    
    # Verify XML format
    match = re.search(r"<tool_bash>(.*?)</tool_bash>", content, re.DOTALL)
    adhered = "Yes (Format Maintained)" if match else "No (Dropped XML Formatting!)"
    
    print(f"Elapsed: {elapsed:.2f}s | Adherence: {adhered}")
    print(f"Output:\n{content}\n" + "-"*50)
    return elapsed, adhered, content


# =====================================================================
# TEST B: PARALLEL TOOL CALLING
# =====================================================================
def run_parallel_tool_test():
    print("\n--- Running Test B: Parallel Tool Calling ---")
    
    system_prompt = """You are Odysseus Lite, a parallel executor.
If a task requires multiple lookups, you can call MULTIPLE tools in parallel in a single message.
Example:
THOUGHT: I need to check two things.
ACTION: <tool_search>{"query": "A"}</tool_search> <tool_search>{"query": "B"}</tool_search>"""
    
    prompt = "Search the web for the latest Python version and the latest Rust stable version simultaneously."
    
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    content = res['message']['content'].strip()
    
    # Extract all occurrences of tool_search
    matches = re.findall(r"<tool_search>(.*?)</tool_search>", content, re.DOTALL)
    
    is_parallel = "No"
    if len(matches) > 1:
        is_parallel = f"Yes (Called {len(matches)} tools in parallel!)"
    elif len(matches) == 1:
        is_parallel = "No (Only called 1 tool)"
    else:
        is_parallel = "No (Failed to call tools)"
        
    print(f"Elapsed: {elapsed:.2f}s | Parallel Trigger: {is_parallel}")
    print(f"Output:\n{content}\n" + "-"*50)
    return elapsed, is_parallel, matches, content


# =====================================================================
# MAIN RUNNER
# =====================================================================
def main():
    print("==================================================")
    print("   RUNNING ADVANCED LIMITS & EDGE CASES BENCHMARK  ")
    print("==================================================")
    
    t_deg, r_deg, out_deg = run_context_degradation_test()
    t_par, r_par, matches, out_par = run_parallel_tool_test()
    
    # Write report
    report_file = "edge_cases_report.md"
    report_content = f"""# Odysseus Lite: Edge Cases and Limits Evaluation Report

This report evaluates how the local 3B model (`{MODEL}`) handles context scaling (drift) and advanced multi-tool execution in a single turn.

---

## 1. Summary of Limits

| Test Scenario | Performance Metric | Result | Impact on Agent Design |
| :--- | :--- | :--- | :--- |
| **Test A: Context Degradation** | Instruction adherence at 3.5k tokens | {r_deg} | Determines maximum context length before system reset is needed. |
| **Test B: Parallel Tool Calling** | Multi-tag generation in 1 turn | {r_par} | Determines if loop cycles can be minimized through batch execution. |

---

## 2. In-Depth Case Review

### 📦 Test A: Context Degradation & Drift
* **Distraction Size:** 3,500 tokens.
* **Goal:** Verify if the model still formats bash tool calls.
* **Raw Model Output (Took {t_deg:.2f}s):**
```
{out_deg}
```
* **Analysis:** If the model successfully outputted `<tool_bash>`, the 3B parameter context attention remained intact under heavy workloads.

---

### 🔀 Test B: Parallel Tool Calling
* **Goal:** Request Python and Rust version searches in one message.
* **Extracted JSON Blocks ({len(matches)} found):**
```json
{json.dumps(matches, indent=2)}
```
* **Raw Model Output (Took {t_par:.2f}s):**
```
{out_par}
```
* **Analysis:** If multiple JSON blocks were successfully generated, we can upgrade the Odysseus Lite bridge to run parallel tool calls concurrently using Python threads, saving up to 50% wall-time latency.
"""
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n✓ Edge case tests complete. Report written to {report_file}!")

if __name__ == "__main__":
    main()
