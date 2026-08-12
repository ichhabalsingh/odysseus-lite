# Odysseus Lite

**Odysseus Lite** is a secure, fully offline local AI workspace co-pilot. Built to run on standard consumer hardware (low VRAM constraints) using Ollama, it implements a highly resilient dual-model **Planner-Executor split**, codebase hybrid RAG grounding, a file-hash caching layer, dynamic JSON Schema constraints, observation state compaction, and sandboxed interactive permission gates.

It features both a **Command Line Interface (CLI)** and a sleek, glassmorphic **One Dark web dashboard** that streams live plans, thoughts, and execution logs in real-time.

---

## Motivation

Modern AI coding assistants have revolutionized software development, but they present critical trade-offs that restrict their adoption:

*   **The Privacy Dilemma:** Proprietary codebases, sensitive configuration files, and internal schemas are routinely uploaded to third-party cloud servers. For developers handling private repositories or subject to strict compliance, cloud-reliant tools are a security risk.
*   **Prohibitive SaaS Costs:** Continuous agentic loops—where an assistant iterates on fixing a bug or refactoring code—can consume millions of tokens, leading to high recurring API bills.
*   **Hardware Accessibility Barriers:** Most modern agentic frameworks are designed for high-end GPUs or massive cloud clusters. Developers operating on standard workstations or consumer laptops (under 4GB VRAM) lack accessible options.
*   **Rogue Autonomy Risks:** Allowing an autonomous agent to write files or run shell commands without checkpoints is dangerous. A single hallucinated command can corrupt database tables, delete code, or freeze the operating system.

**Odysseus Lite** addresses these problems. It demonstrates that by combining a **dual-model Planner-Executor split**, a **cached hybrid RAG engine**, and **interactive human-in-the-loop permission gates**, developers can run a highly capable, private, and secure coding partner entirely on consumer-grade local hardware.

---

## Example Use Cases

Here are general examples of tasks you can assign to Odysseus Lite:

### 1. Codebase Refactoring and Analysis
*   **Prompt:** "Search the codebase for all functions matching connect_db. Replace them with the new pool-based get_db_connection function in database.py, and run the python tests to ensure nothing broke."
*   **Agent Path:** The agent will use `tool_workspace_rag` to locate the definitions, read the target files, modify them, and run the test suite via the bash tool.

### 2. Interactive Document Ingestion and Synthesis
*   **Prompt:** "Search the workspace for the PDF document called metrics_report.pdf, read its contents, and compile a summary of the latency metrics to metrics_summary.md."
*   **Agent Path:** The agent will query the index, extract text from the binary PDF pages, and write the compiled markdown report.

### 3. Automated Error Diagnostics and Healing
*   **Prompt:** "Execute python test_model.py. If there are any failing tests, check the source file of the failing modules, apply the fix, and re-run to confirm."
*   **Agent Path:** The agent runs the script, captures the traceback, reads the buggy files, writes the patch, and re-runs to verify.

---

## Key Features

*   **Offline First (100% Private):** Runs entirely locally using lightweight models via Ollama. No data ever leaves your machine.
*   **JSON Schema Constraints (Ollama format API):** 
    *   Binds the token outputs of local models directly using structured JSON schemas.
    *   Prevents tool hallucinations and syntax violations by enforcing strict `enum` constraints on generated tools, ensuring 100% parser compatibility on small models (1.5B - 3B parameters).
*   **Hybrid RAG Search with Local Cache:**
    *   Combines sparse keyword search (BM25) and dense semantic search (`nomic-embed-text` vectors) using Reciprocal Rank Fusion (RRF).
    *   Caches calculated embeddings in a local `.rag_cache.json` using file modification times (`mtime`), reducing startup and re-indexing latency to milliseconds.
*   **State Compactor (Memory Optimization):**
    *   Dynamically condenses large tool output payloads (like raw file contents or RAG indexes exceeding 500 characters) into concise 1-2 sentence summaries.
    *   Reduces agent latency by **over 57%** and completely prevents context-window overflow and parsing drift.
*   **Dual-Interface Control:**
    *   **CLI Mode:** Run commands directly in your terminal with custom workspace target, planner model, and executor model flags.
    *   **Web Dashboard:** A premium, glassmorphic UI streaming live agent outputs (Plan, Thoughts, Actions, and Observations) via Server-Sent Events (SSE).
*   **Interactive Security Permission Gates:** 
    *   Prevents rogue AI actions. Before running any shell command (`tool_bash`) or editing/writing files, the system halts and waits for explicit human confirmation.
    *   Terminal prompts require a strict y/n confirmation.
    *   The Web UI displays a red slide-down alert panel overlay requiring click-to-approve confirmation before resuming.
*   **PDF Parsing Integration:** Programmatic binary text extraction via `pypdf` which integrates directly into both the read tool and the RAG indexer.
*   **Hang-Protection (Process Isolation):** All shell commands are sandboxed with a strict 15-second execution timeout to prevent infinite loops or terminal freeze.

---

## Core System Architecture

```mermaid
graph TD
    A[User Request] -->|Web UI / CLI| B[Planner Model]
    B -->|JSON Schema Constraints| C[Executor Model]
    C -->|Execute Step| D{Tool Permission Guard}
    D -->|y/n Prompt| E[User Confirmation]
    E -->|Approve| F[Execute Tool]
    E -->|Deny| G[Abort Step]
    F -->|Raw Observation| H[State Compactor]
    H -->|1-2 Sentence Summary| I[Compact History Context]
    I -->|Next Step Context| C
```

---

## Quick Start

### Step 1: Install Ollama (Local LLM Engine)

Select the command/installer for your Operating System:

*   **Windows:**
    1. Download the Windows installer from [Ollama's Official Website](https://ollama.com/download/windows).
    2. Run the `.exe` installer.
    3. Open PowerShell and pull the recommended models:
       ```bash
       ollama pull deepseek-r1:1.5b
       ollama pull qwen2.5-coder:1.5b
       ollama pull nomic-embed-text
       ```

*   **Linux:**
    1. Open terminal and run:
       ```bash
       curl -fsSL https://ollama.com/install.sh | sh
       ```
    2. Start the service and pull the models:
       ```bash
       ollama pull deepseek-r1:1.5b
       ollama pull qwen2.5-coder:1.5b
       ollama pull nomic-embed-text
       ```

*   **macOS:**
    1. Download the macOS zip from [Ollama's Official Website](https://ollama.com/download/mac).
    2. Unzip, move `Ollama.app` to your Applications folder, and pull models:
       ```bash
       ollama pull deepseek-r1:1.5b
       ollama pull qwen2.5-coder:1.5b
       ollama pull nomic-embed-text
       ```

---

### Step 2: Setup Python & Requirements

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/ichhabalsingh/odysseus-lite.git
    cd odysseus-lite
    ```

2.  **Initialize Virtual Environment:**
    *   **Linux / macOS:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   **Windows (PowerShell):**
        ```powershell
        python -m venv .venv
        .venv\Scripts\Activate.ps1
        ```

3.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

### Run via Web Dashboard
Start the local server daemon:
```bash
python app_ui.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

1.  Enter your target **Workspace Path** in the Control Center.
2.  Choose your **Executor Model** and **Planner Model** from the dropdown selectors.
3.  Type your coding or research goal.
4.  Click **Initialize Agent**.
5.  Monitor execution logs and click **Approve** or **Deny** on the top alert panel when the agent requests permissions.

---

### Run via Command Line (CLI)
You can target any workspace directory on your machine using the CLI and customize the models:
```bash
python ody.py "Search codebase for categories and write to notes.txt" -w /path/to/project -p deepseek-r1:1.5b -e qwen2.5-coder:1.5b
```

#### CLI Parameters:
*   `-w`, `--workspace`: Path to the workspace directory to scan and work in (defaults to current working directory).
*   `-p`, `--planner`: Local model to use for step planning (defaults to `deepseek-r1:1.5b`).
*   `-e`, `--executor`: Local model to use for step execution (defaults to `qwen2.5-coder:1.5b`).

The terminal will halt and prompt you: `Approve? (y/n):` before executing commands or saving file updates.

---

## Safety Sandboxing Guidelines

*   **Timeout Containment:** Any shell command executed via `tool_bash` that runs longer than 15 seconds is forcibly terminated (`SIGKILL`), releasing the thread.
*   **Path Traversal Protection:** Absolute path checks prevent the agent from reading or writing files outside the targeted workspace (e.g. attempting to read `/etc/passwd` returns a `Permission Denied` error string).

---

## Contributing

Contributions are welcome! If you would like to help improve Odysseus Lite, please follow these steps:

1. Fork the repository and create your feature branch.
2. Ensure your changes adhere to local performance optimizations and do not add cloud dependencies.
3. Test changes locally to verify system reliability and model formatting boundaries.
4. Submit a detailed pull request outlining your changes and their motivation.

For major architectural updates, please open an issue first to discuss what you would like to change.
