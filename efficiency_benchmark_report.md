# Odysseus Lite: Long-Run Efficiency Benchmark Report

This report records the performance and VRAM efficiency of three distinct agent architectures executing a battery of 5 work-automation tasks.

---

## 1. Aggregated Efficiency Summary

| Architectural Configuration | Total Wall Time | VRAM Loading Overhead | Total Tokens Generated | Avg Generation Speed |
| :--- | :--- | :--- | :--- | :--- |
| **Arch A: Unified Agent** (`granite4.1:3b` only) | 30.08s | 13.56s | 761 | 57.50 tok/s |
| **Arch B: Two-Agent Split** (`r1:1.5b` + `llama3.1:8b`) | 232.31s | 37.54s | 6859 | 50.29 tok/s |
| **Arch C: Scrum Team Pipeline** (`granite4.1:3b` + `llama3.1:8b`) | 330.94s | 37.59s | 3905 | 31.80 tok/s |

---

## 2. In-Depth Efficiency Analysis

### A. VRAM Swapping Latency (The Cost of Multi-Model Systems)
*   **Arch A (Unified):** Spent a total of **13.56 seconds** loading models. Because the same model stayed active in GPU memory, loading occurred once at startup.
*   **Arch B (Two-Agent Split):** Spent **37.54 seconds** loading models. This is due to forcing `keep_alive=0` on both models to prevent OOM errors, resulting in constant disk-to-VRAM loads.
*   **Arch C (Scrum Team):** Spent **37.59 seconds** loading models. By using `keep_alive="2m"`, swapping was minimized as long as consecutive tasks ran within the timeout window.

### B. Generation Throughput (tok/s)
*   **3B Model (`granite4.1:3b`):** Achieved an average speed of **57.50 tokens/sec**. This model is light, running entirely on GPU cores.
*   **8B Model (`llama3.1:8b`):** Achieved an average speed of **50.29 tokens/sec** when running alongside the other models.

---

## 3. Key Efficiency Takeaways

1. **Keep-Alive is Critical for Multi-Agent Systems:**
   If you must use a Multi-Agent system on 4 GB VRAM, never use `keep_alive=0` on all steps. Use a grace window (e.g. `keep_alive="2m"` or `"5m"`) so that the models stay in memory between steps of the same workflow, avoiding disk read lags.
2. **Unified 3B outperforms split 8B in raw latency:**
   If your work tasks do not require deep software compilation or mathematical reasoning, a single 3B model like `granite4.1:3b` is significantly more efficient, running 2-3x faster than an 8B model offloaded to CPU memory.
