#!/usr/bin/env python3
import os
import sys
import time

# Import configuration and registry from ody.py
from ody import Config, registry, run_bash, read_file, write_file, append_file, query_workspace_rag, web_search

REPORT_FILE = "edge_case_robustness_report.md"

def test_result(name, condition, details=""):
    status = "\033[92m✓ PASS\033[0m" if condition else "\033[91m✗ FAIL\033[0m"
    print(f"[{status}] {name} {details}")
    return condition

def main():
    print("==================================================")
    print("      RUNNING TOOL LAYER EDGE-CASE ROBUSTNESS     ")
    print("==================================================")
    
    results = []
    
    # -----------------------------------------------------------------
    # EDGE CASE 1 & 2: PATH TRAVERSAL ATTACKS (Security Sandbox)
    # -----------------------------------------------------------------
    # Attempting to read outside workspace
    print("\n[Test 1] Read File outside workspace (Path Traversal)")
    out_1 = read_file({"path": "../../../etc/passwd"})
    pass_1 = "Permission Denied" in out_1
    results.append(test_result("Read File Path Traversal Protection", pass_1, f"-> Received: '{out_1}'"))
    
    # Attempting to write outside workspace
    print("\n[Test 2] Write File outside workspace (Path Traversal)")
    out_2 = write_file({"path": "../../../tmp/hack.txt", "content": "hacked"})
    pass_2 = "Permission Denied" in out_2
    results.append(test_result("Write File Path Traversal Protection", pass_2, f"-> Received: '{out_2}'"))

    # -----------------------------------------------------------------
    # EDGE CASE 3: MISSING FILES
    # -----------------------------------------------------------------
    print("\n[Test 3] Read non-existent file")
    out_3 = read_file({"path": "does_not_exist_file_xyz.txt"})
    pass_3 = "Read error" in out_3 or "No such file" in out_3
    results.append(test_result("Missing File Reading Grace", pass_3, f"-> Received: '{out_3}'"))

    # -----------------------------------------------------------------
    # EDGE CASE 4: DEEP NESTED FOLDER WRITING
    # -----------------------------------------------------------------
    print("\n[Test 4] Write file in deep nested non-existent directory")
    nested_path = "nested_test/dir1/dir2/deep_file.txt"
    # Temporarily bypass interactive permission check by mock patching input
    # (Since this is a programmatic validation suite, we mock input() to return 'y')
    import builtins
    original_input = builtins.input
    builtins.input = lambda _: "y"
    
    out_4 = write_file({"path": nested_path, "content": "deep content"})
    pass_4 = "Successfully wrote file" in out_4 and os.path.exists(nested_path)
    results.append(test_result("Auto-mkdir Writing Capability", pass_4, f"-> Received: '{out_4}'"))
    
    # Clean up nested file
    if os.path.exists(nested_path):
        os.remove(nested_path)
        os.removedirs(os.path.dirname(nested_path))

    # -----------------------------------------------------------------
    # EDGE CASE 5 & 6: BASH COMMAND CRASHES & TIMEOUTS
    # -----------------------------------------------------------------
    print("\n[Test 5] Execute failing bash command")
    out_5 = run_bash({"command": "ls non_existent_folder_abc_123"})
    pass_5 = "STDERR:" in out_5 or "No such file" in out_5 or "exit code" in out_5
    results.append(test_result("Bash Failure Capture", pass_5, f"-> Received: '{out_5.strip()}'"))
    
    print("\n[Test 6] Execute hanging bash command (Timeout trigger)")
    t0 = time.time()
    out_6 = run_bash({"command": "sleep 30"})
    elapsed = time.time() - t0
    # Expected: timeout at 15s limit
    pass_6 = "timed out" in out_6 and elapsed < 20
    results.append(test_result("Bash Timeout Isolation", pass_6, f"-> Elapsed: {elapsed:.2f}s | Received: '{out_6}'"))

    # -----------------------------------------------------------------
    # EDGE CASE 7 & 8: RAG EMPTY AND INVALID SNIPPETS
    # -----------------------------------------------------------------
    print("\n[Test 7] RAG query for non-existent term")
    out_7 = query_workspace_rag({"query": "nonexistentkeywordxyz123"})
    pass_7 = "No matching" in out_7
    results.append(test_result("Empty RAG Overlap Grace", pass_7, f"-> Received: '{out_7}'"))
    
    print("\n[Test 8] RAG query with empty arguments")
    out_8 = query_workspace_rag({"query": ""})
    pass_8 = "Error" in out_8
    results.append(test_result("Empty RAG Parameter Handling", pass_8, f"-> Received: '{out_8}'"))

    # -----------------------------------------------------------------
    # EDGE CASE 9 & 10: WEB SEARCH LIMITS
    # -----------------------------------------------------------------
    print("\n[Test 9] Web search empty query")
    out_9 = web_search({"query": ""})
    pass_9 = "Error" in out_9
    results.append(test_result("Empty Web Search Parameter Handling", pass_9, f"-> Received: '{out_9}'"))
    
    # Restore original input
    builtins.input = original_input

    # Compute stats
    passed = sum(1 for r in results if r)
    pass_rate = (passed / len(results)) * 100
    
    # Write Report
    report_md = f"""# Odysseus Lite: Tool Layer Edge-Case Robustness Report

This report documents the programmatic edge-case evaluations of the Odysseus Lite Python tool layer. This ensures that runtime failures are captured and returned as text observations to the LLM instead of raising raw exceptions.

---

## 1. Summary of Robustness Benchmarks
* **Total Edge Cases Tested:** {len(results)}
* **Pass Rate:** **{pass_rate:.1f}%** ({passed}/{len(results)} passed)

---

## 2. Test Execution Logs

| Test ID | Vulnerability/Edge Case | Expected Behavior | Actual Behavior | Result |
| :--- | :--- | :--- | :--- | :--- |
| **TC-001** | Read File Path Traversal | Return 'Permission Denied' | '{out_1}' | {"✓ PASS" if pass_1 else "✗ FAIL"} |
| **TC-002** | Write File Path Traversal | Return 'Permission Denied' | '{out_2}' | {"✓ PASS" if pass_2 else "✗ FAIL"} |
| **TC-003** | Missing File Reading | Return 'Read error' | '{out_3.strip()}' | {"✓ PASS" if pass_3 else "✗ FAIL"} |
| **TC-004** | Deep Directory Writing | Auto-create folders & write | '{out_4}' | {"✓ PASS" if pass_4 else "✗ FAIL"} |
| **TC-005** | Bash Command Failure | Capture STDERR / Exit Code | '{out_5.strip().replace("\n", " ")}' | {"✓ PASS" if pass_5 else "✗ FAIL"} |
| **TC-006** | Bash Command Timeout | Terminate command at 15s limit | '{out_6}' | {"✓ PASS" if pass_6 else "✗ FAIL"} |
| **TC-007** | Empty RAG Match | Return 'No matching snippets' | '{out_7}' | {"✓ PASS" if pass_7 else "✗ FAIL"} |
| **TC-008** | Empty RAG Query | Return 'Error: No query' | '{out_8}' | {"✓ PASS" if pass_8 else "✗ FAIL"} |
| **TC-009** | Empty Web Search Query | Return 'Error: No query' | '{out_9}' | {"✓ PASS" if pass_9 else "✗ FAIL"} |

---

## 3. Core Architectural Safeguards

1. **Active Sandbox Containment (`TC-001`, `TC-002`):**
   * Path checking using `os.path.abspath` and checking prefix start ensures that the agent cannot escape the target workspace folder.
2. **Process Timeout Isolation (`TC-006`):**
   * Commands executed through `subprocess.run(timeout=15)` prevent the agent from getting locked up in infinite loops or hangs.
3. **No Uncaught Exceptions:**
   * All file operations and external shell processes are enclosed in try-except blocks, ensuring that the main agent session thread never crashes.
"""
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n✓ Master Robustness Manual written to {REPORT_FILE}!")

if __name__ == "__main__":
    main()
