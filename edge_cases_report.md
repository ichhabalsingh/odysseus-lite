# Odysseus Lite: Edge Cases and Limits Evaluation Report

This report evaluates how the local 3B model (`granite4.1:3b`) handles context scaling (drift) and advanced multi-tool execution in a single turn.

---

## 1. Summary of Limits

| Test Scenario | Performance Metric | Result | Impact on Agent Design |
| :--- | :--- | :--- | :--- |
| **Test A: Context Degradation** | Instruction adherence at 3.5k tokens | Yes (Format Maintained) | Determines maximum context length before system reset is needed. |
| **Test B: Parallel Tool Calling** | Multi-tag generation in 1 turn | No (Failed to call tools) | Determines if loop cycles can be minimized through batch execution. |

---

## 2. In-Depth Case Review

### 📦 Test A: Context Degradation & Drift
* **Distraction Size:** 3,500 tokens.
* **Goal:** Verify if the model still formats bash tool calls.
* **Raw Model Output (Took 4.93s):**
```
<tool_bash>{"command": "ls"}</tool_bash>
```
* **Analysis:** If the model successfully outputted `<tool_bash>`, the 3B parameter context attention remained intact under heavy workloads.

---

### 🔀 Test B: Parallel Tool Calling
* **Goal:** Request Python and Rust version searches in one message.
* **Extracted JSON Blocks (0 found):**
```json
[]
```
* **Raw Model Output (Took 3.95s):**
```
ACTION: <tool_search>{"query": "latest Python version"}<tool_search>{"query": "latest Rust stable version"}
```
* **Analysis:** If multiple JSON blocks were successfully generated, we can upgrade the Odysseus Lite bridge to run parallel tool calls concurrently using Python threads, saving up to 50% wall-time latency.
