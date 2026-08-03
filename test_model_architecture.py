import re
import json
import subprocess
import os
import ollama

# --- PERSONAS ---
MANAGER_PROMPT = """You are the Project Manager. 
Analyze the user request, create a step-by-step logic plan, and specify the requirements.
CRITICAL: Do NOT write any Python code, functions, or python syntax in your plan. Describe the logic in plain text steps only."""

DEVELOPER_PROMPT = """You are the Lead Developer. 
Your task is to write a single, complete, executable Python script that implements the Manager's plan.
Requirements:
1. Define the necessary functions.
2. Include the input data driver at the bottom of the script (call the functions with the test data and print the results).
3. Return ONLY raw Python code. Do NOT output markdown code blocks (```python) or explanations. Start directly with the code."""

# --- MODELS ---
PRIMARY_MODEL = "granite4.1:3b"
CODER_MODEL = "llama3.1:8b"

def run_bash(command: str) -> dict:
    """Executes a bash command and returns exit code, stdout, and stderr."""
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return {"code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
    except Exception as e:
        return {"code": -1, "stdout": "", "stderr": str(e)}

# --- SCRUM WORKFLOW ---
def run_scrum_pipeline(user_request: str):
    print(f"\nUser Goal: {user_request}\n" + "="*60)
    
    # 1. MANAGER DEFINES PLAN (Plain Text Only)
    print("\n[MANAGER] Creating execution plan...")
    res_mgr = ollama.chat(
        model=PRIMARY_MODEL,
        messages=[
            {"role": "system", "content": MANAGER_PROMPT},
            {"role": "user", "content": user_request}
        ]
    )
    plan = res_mgr['message']['content']
    print(f"Manager Plan:\n{plan}\n")
    
    script_path = "app.py"
    max_debug_cycles = 4
    bug_report = ""
    
    for cycle in range(1, max_debug_cycles + 1):
        print(f"\n=== DEVELOPMENT & TESTING CYCLE {cycle} ===")
        
        # 2. DEVELOPER WRITES CODE
        dev_instruction = f"Based on the plan:\n{plan}\nWrite the Python script for '{script_path}'."
        if cycle > 1:
            dev_instruction += f"\n\nCRITICAL: Your previous draft failed compilation or execution. Fix this error:\n{bug_report}"
            
        print("[DEVELOPER] Writing code...")
        res_dev = ollama.chat(
            model=CODER_MODEL,
            messages=[
                {"role": "system", "content": DEVELOPER_PROMPT},
                {"role": "user", "content": dev_instruction}
            ]
        )
        code = res_dev['message']['content'].strip()
        
        # Clean up any potential markdown wraps if the model outputted them
        code = re.sub(r"^```python\s*", "", code)
        code = re.sub(r"^```\s*", "", code)
        code = re.sub(r"\s*```$", "", code)
        
        # Write code to file
        with open(script_path, "w") as f:
            f.write(code)
        print(f"✓ Code written to {script_path}")
        
        # 3. TESTER RUNS THE CODE (Deterministic validation)
        print("[TESTER] Running the python script...")
        run_results = run_bash(f"python3 {script_path}")
        
        stdout_output = run_results['stdout'].strip()
        stderr_output = run_results['stderr'].strip()
        exit_code = run_results['code']
        
        print(f"Exit Code: {exit_code}")
        print(f"Stdout:\n{stdout_output}")
        print(f"Stderr:\n{stderr_output}")
        
        # QA Assertion logic
        is_success = True
        error_msg = ""
        
        if exit_code != 0:
            is_success = False
            error_msg += f"Script exited with a non-zero code ({exit_code}).\n"
            
        if stderr_output:
            is_success = False
            error_msg += f"Syntax/Execution Error:\n{stderr_output}\n"
            
        if not stdout_output and is_success:
            is_success = False
            error_msg += "Output Error: The script executed successfully but produced NO stdout output. You must print results.\n"
            
        if is_success:
            print("\n✓ Python QA Tests Passed successfully!")
            print(f"\nFinal Output from Script:\n{stdout_output}")
            
            # Clean up the test file
            if os.path.exists(script_path):
                os.remove(script_path)
            return
        else:
            print(f"\n[QA FAILED]: Sending traceback to Developer...")
            bug_report = error_msg
            
    print("\n\n✗ Failed to resolve bugs within the maximum development cycles.")
    if os.path.exists(script_path):
        os.remove(script_path)

if __name__ == "__main__":
    test_request = "Create a python script that divides 100 by a list of numbers: [10, 5, 0, 2] and prints each result."
    run_scrum_pipeline(test_request)