# Odysseus Lite: Master Architectural Blueprint & Benchmarking Report

This blueprint compiles all architectural research, performance benchmarks, VRAM optimization data, and agentic design principles gathered during the development of **Odysseus Lite** on consumer hardware (4 GB VRAM constraints).

---

## 1. Benchmarks & Performance Metrics Compilation

### A. Structured Formatting Optimization
*Tested Model: `granite4.1:3b` | Task: Extracting structured JSON datasets from unformatted meeting emails.*

| Formatting Strategy | Execution Latency | Syntax Format Validity | Primary Performance Characteristics |
| :--- | :--- | :--- | :--- |
| **Zero-Shot JSON** | 7.21 seconds | Valid JSON (Raw) | Slowest. Model undergoes token generation hesitation while organizing JSON formatting on the fly. |
| **Few-Shot JSON** | 3.40 seconds | Valid JSON (Raw) | **2.1x Faster.** Structural examples establish direct paths, reducing thinking token output. |
| **Schema-Constrained** | **2.93 seconds** | **100% Valid (Perfect)** | **2.5x Faster.** Ollama grammar constraint limits token logits directly. Zero formatting errors. |

---

### B. Core Architecture Efficiency Benchmarks
*Tested Models: `granite4.1:3b`, `llama3.1:8b`, `deepseek-r1:1.5b` | Task: Executing a battery of 5 workspace automation tasks.*

| Architectural Configuration | Total Wall Time (5 Tasks) | VRAM Loading Overhead | Output Verbosity | Avg Generation Speed |
| :--- | :--- | :--- | :--- | :--- |
| **Arch A: Unified Agent** (`granite4.1:3b`) | **30.08 seconds** | **13.56s** (Startup only) | 761 tokens (Direct) | **57.50 tokens/sec** |
| **Arch B: Two-Agent Split** (`r1` + `llama3.1`) | 232.31 seconds | 37.54s (Continuous) | 6,859 tokens (Verbose)| 50.29 tokens/sec |
| **Arch C: Scrum Team** (`granite` + `llama3.1`) | 330.94 seconds | 37.59s (Timeout swaps) | 3,905 tokens (Medium) | 31.80 tokens/sec |

---

### C. Context-Assisted Coding Benchmarks
*Tested Model: `llama3.1:8b` | Task: Writing API integrations and code reuse tasks.*

| Strategy | Context Source | Retrieval Latency | Code Syntax Accuracy | Key Takeaway |
| :--- | :--- | :--- | :--- | :--- |
| **Search-Assisted** | DuckDuckGo Scraping | Variable / High | Fails on Scraper Blocks | Raw web scraping is highly fragile due to geoblocks and rate limits. |
| **RAG-Assisted** | Local Workspace RAG | **< 1 millisecond** | **100% Correct Alignment**| Direct indexing ensures semantic code reuse with zero network latency. |

---

## 2. Core Lessons Learned & Design Principles

During the development cycles, five foundational rules were established for building robust local agent systems:

### Rule 1: Use Grammar/Schema Constraints
Never ask a model under 13B parameters to "output JSON" without binding its grammar. Use Ollama's `format` parameter with a JSON schema. It eliminates syntax violations and doubles execution speed.

### Rule 2: Never Use LLMs for Deterministic Testing
Asking small models to evaluate if code execution succeeded is highly prone to hallucination (e.g. model claiming normal prints are errors or making up debuggers like GDB). Use Python's subprocess environment to check `exit_code == 0` and inspect `stderr` programmatically.

### Rule 3: Avoid VRAM Swapping Loops
On 4 GB VRAM GPUs, do not switch between different models during consecutive steps of a single loop. Swapping models in/out of GPU memory adds a **15–20s load delay**. Use a unified model context, or keep loading times low by using a shared model size with `keep_alive` values set to at least 5 minutes.

### Rule 4: Local RAG is Superior to Raw Web Scraping
Web scrapers fail without dedicated API keys. A zero-dependency workspace RAG engine (using simple keyword overlaps on code blocks) runs instantly offline, matches coding style, and keeps context limits safe.

### Rule 5: Delegate Arithmetic to Python
Small models struggle with math logic in text. Let the model extract parameters (e.g. quantity and prices) into a JSON schema, and execute the calculations in Python.

---

## 3. Recommended Odysseus Lite Production Stack

For your local workspace, the most efficient and robust setup is the **Unified Agent with Local RAG (Architecture A)**:

```
            [User Terminal Request]
                      │
                      ▼
       [Local RAG Codebase Search]  ◄── Index files on-disk (<1ms)
                      │
                      ▼
        [Unified Granite 3B / Llama 3B]
       - Stays loaded in GPU (VRAM safe)
       - Uses XML tool tags for action
                      │
             ┌────────┴────────┐
             ▼                 ▼
        [Bash Tool]     [Search Tool]
        (Local Run)     (API Search)
             │                 │
             └────────┬────────┘
                      ▼
         [Deterministic Python QA]
        - Exit Code & Stderr checks
                      │
                      ▼
              [Final Solution]
```

---

## 4. Edge Cases, Limits & Adherence Benchmarks

To establish the operational boundaries of a local 3B model (`granite4.1:3b`), we executed stress tests on context size and syntax generation complexity:

### A. Context Degradation Resilience (Test A)
*   **The Setup:** Injected a 3,500-token distraction block (simulating long logs or file contents) into the history before asking for a tool action.
*   **The Result:** **Format Maintained (Success).** The model outputted a perfect `<tool_bash>{"command": "ls"}</tool_bash>`.
*   **Engineering Takeaway:** Local 3B models are highly context-resilient. You can feed them several files and log histories in the context window (using `num_ctx: 8192`) without the model forgetting its formatting rules.

### B. Parallel Tool Calling Syntax Collapse (Test B)
*   **The Setup:** Challenged the model to request two separate search queries in a single message turn.
*   **The Result:** **Syntax Failure.** The model outputted:
    `ACTION: <tool_search>{"query": "latest Python version"}<tool_search>{"query": "latest Rust stable version"}`
    *The model failed to generate the closing XML tags (`</tool_search>`) when attempting parallel generation.*
*   **Engineering Takeaway:** Do not attempt parallel/batch tool generation with models under 8B parameters. They lose track of structural enclosures. **Enforce strict, sequential (one-at-a-time) tool execution in your python bridge.**

---

## 5. Local Deep Research Architecture

To determine if local 3B models can perform recursive "Deep Research" (similar to OpenAI Deep Research or Perplexity Pro), we implemented a multi-stage Python state machine:

### A. The Setup (test_deep_research.py)
*   **Methodology:**
    1.  **Stage 1 (Map):** Prompt the LLM to generate 3 initial broad search queries. Run searches. Extract bulleted facts.
    2.  **Stage 2 (Gap Analysis):** Feed the extracted facts to the LLM. Ask it to identify 2 missing gaps and generate 2 follow-up search queries. Run searches. Extract follow-up facts.
    3.  **Stage 3 (Reduce/Synthesis):** Feed all accumulated facts (from Stage 1 and 2) to the LLM to write a structured markdown report.
*   **The Result:** **Highly Successful.** The entire recursive research and synthesis loop completed in **23.24 seconds** on `qwen2.5-coder:3b-instruct`, compiling a professional 50-line report (`research_report.md`).

### B. Engineering Takeaway
Do not let a small model plan and manage a recursive research queue itself (it will forget its search logs and get lost in context). Instead, **use Python to manage the loop logic** (query queue, search executing, recursion depth) and let the local 3B model focus on **single-step cognitive tasks** (generating queries, extracting facts from text, and compiling reports). This achieves "Deep Research" capabilities with zero API costs in under 25 seconds.
