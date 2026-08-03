# Odysseus Lite: Architectural Evaluation Summary

This document summarizes the results of evaluating the **Unified Agent** versus the **Two-Agent Split** architectures under local execution constraints (4 GB VRAM GPU).

---

## 1. Architectural Metrics Comparison

Below is the execution data compiled from the comparative test runs:

| Evaluation Metric | Option A: Unified Agent (`test_unified_agent.py`) | Option B: Two-Agent Split (`test_two_agent_split.py`) |
| :--- | :--- | :--- |
| **Orchestrator Model** | `llama3.1:8b` (Single Model) | `deepseek-r1:1.5b` (Reasoning Planner) |
| **Executor Model** | `llama3.1:8b` (Single Model) | `llama3.1:8b` (Tool Executor) |
| **Total Cycles Run** | 8 Cycles (hit maximum limit) | 8 Cycles (completed final answer) |
| **Total Run Time** | **~114 seconds** | **~172 seconds** |
| **Tool Tag Syntax** | **Perfect** (strictly 1 action per turn) | **Weak** (roleplayed system outputs in Cycle 1) |
| **JSON Reliability** | **100% Valid JSON** | **Failed 2 Cycles** (newline escaping in string) |
| **VRAM Management** | **Excellent** (0 VRAM model swaps) | **Poor** (disk-to-VRAM model swapping delay) |

---

## 2. Key Insights and Anomalies

### A. The "Dialogue Roleplay" Hallucination (Option B)
When instructed with a list of system observation steps (`OBSERVE:`), the executor model in the Split architecture hallucinated the entire future conversation in Cycle 1 (generating its thoughts, actions, and mock system observations all in one turn).
*   *Solution:* Simplify system prompts to instruct the model **only** on what it generates (`THOUGHT:` and `ACTION:`), leaving system boundaries implicit.

### B. JSON Escaping Failures (Option B)
Writing files via JSON arguments (`{"path": "file.txt", "content": "multi\nline\ntext"}`) is a common failure point for models under 13B parameters. Escaping raw newlines (`\n` vs `\\n`) and nested quotes often leads to JSON parsing failures.
*   *Solution:* Use non-JSON XML attributes for block-writing files:
    ```xml
    <tool_write_file path="summary.txt">
    Raw multi-line content goes here
    Line 2
    </tool_write_file>
    ```

### C. VRAM Thrashing on 4 GB Hardware
Under a 4 GB VRAM limit, loading `deepseek-r1:1.5b` and then swapping to `llama3.1:8b` forces Ollama to offload model weights from GPU memory to System RAM. This introduces a **15–20 second loading latency** on transition, reducing execution responsiveness.

---

## 3. Final Recommendation

For **Odysseus Lite**, the **Unified Agent (Option A)** is the clear choice. 

### Recommended Stack Optimization:
1.  **Model:** Standardize on **`granite4.1:3b`** or **`qwen2.5-coder:3b-instruct`**.
    *   3B parameter models fit entirely inside 4 GB VRAM, providing sub-second token generation speed.
    *   `qwen2.5-coder` series has native coding and XML-parsing capabilities equivalent to 8B models.
2.  **Tool Format:** Maintain the XML tag format (`<tool_name>...</tool_name>`) but switch the file writing action from JSON to raw block parsing.
3.  **Deterministic QA:** Let Python verify compilation and test runs. Only use the LLM to write code or analyze actual tracebacks when `stderr` catches an error.
