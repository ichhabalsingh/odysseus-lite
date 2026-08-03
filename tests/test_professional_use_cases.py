import json
import time
import os
import ollama

# --- CONFIGURATION ---
MODEL = "granite4.1:3b"
DOC_FILE = "professional_use_cases.md"

# --- USE CASE DATA & SCHEMAS ---

# 1. Software Engineer: Traceback Triage
TRACEBACK_DATA = """
Traceback (most recent call last):
  File "app/utils.py", line 42, in process_user_data
    user_status = database["users"][user_id]["status"]
IndexError: list index out of range
"""

BUG_SCHEMA = {
    "type": "object",
    "properties": {
        "file": {"type": "string"},
        "line_number": {"type": "integer"},
        "exception_type": {"type": "string"},
        "root_cause": {"type": "string"},
        "remediation": {"type": "string"}
    },
    "required": ["file", "line_number", "exception_type", "root_cause", "remediation"]
}

# 2. Project Manager: Developer Standup -> Status Report
STANDUP_UPDATES = """
- Sarah: Finished landing page API deployment to dev. Had some issues with AWS credentials but sorted it out.
- Mark: DB migrations ran successfully. We found a duplication bug in user tables but resolved it.
- Jeff: Slide deck draft 1 finished. Client meeting confirmed for Tuesday 10 AM EST.
"""

# 3. Operations Analyst: Raw Invoice Extraction
INVOICE_DATA = """
Invoice ID: INV-2026-9081
Client: ACME Corporation
Shipment Date: August 3rd, 2026
Items purchased:
- 4x Heavy Duty Gears @ $25.00 each
- 2x Titanium Screws @ $7.50 each
Standard shipping fee: $15.00
Tax: 8.5% applied to subtotal (shipping is tax-exempt).
"""

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_id": {"type": "string"},
        "client": {"type": "string"},
        "subtotal": {"type": "number"},
        "tax": {"type": "number"},
        "total": {"type": "number"}
    },
    "required": ["invoice_id", "client", "subtotal", "tax", "total"]
}

# 4. Content Marketer: Social Copy
PRODUCT_SPEC = """
OdyDB is an embedded database engine written in Rust. It features sub-millisecond reads, native vector embeddings storage for AI search, and is ACID compliant. Designed for running light database instances directly in edge applications (IoT, mobile, and desktop apps).
"""

# --- RUNNING USE CASE TESTS ---

def run_software_engineer() -> tuple:
    print(" -> Running Software Engineer Case...")
    prompt = f"Analyze this traceback and extract the details:\n{TRACEBACK_DATA}"
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=BUG_SCHEMA,
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    return elapsed, json.loads(res['message']['content'])

def run_project_manager() -> tuple:
    print(" -> Running Project Manager Case...")
    prompt = f"""You are a professional Project Manager. 
Convert these developer standup notes into a polished Weekly Status Update for the client.
Use professional headings, formatting, and bullet points. Highlight key accomplishments and the upcoming meeting.

STANDUP NOTES:
{STANDUP_UPDATES}
"""
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2}
    )
    elapsed = time.time() - t0
    return elapsed, res['message']['content'].strip()

def run_operations_analyst() -> tuple:
    print(" -> Running Operations Analyst Case...")
    prompt = f"Calculate totals and extract invoice properties from this raw invoice:\n{INVOICE_DATA}"
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=INVOICE_SCHEMA,
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    return elapsed, json.loads(res['message']['content'])

def run_content_marketer() -> tuple:
    print(" -> Running Content Marketer Case...")
    prompt = f"""You are a SaaS Copywriter. 
Based on these product specifications:
{PRODUCT_SPEC}

Generate exactly two promotional posts:
1. LinkedIn Post (professional tone, details edge database constraints, 2 hashtags).
2. Twitter/X Post (punchy, focused on speed/Rust, max 280 characters).
"""
    t0 = time.time()
    res = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.7}
    )
    elapsed = time.time() - t0
    return elapsed, res['message']['content'].strip()

# --- MAIN EXECUTION ---
def main():
    print("==================================================")
    print("      RUNNING PROFESSIONAL USE CASES TEST         ")
    print("==================================================")
    
    # Run tests
    t_eng, r_eng = run_software_engineer()
    t_pm, r_pm = run_project_manager()
    t_ops, r_ops = run_operations_analyst()
    t_mkt, r_mkt = run_content_marketer()
    
    print("\n✓ All tests completed. Writing documentation to professional_use_cases.md...")
    
    # Formulate markdown documentation
    md_content = f"""# Odysseus Lite: Professional Use Cases & Optimization Benchmarks

This document records the evaluation of a local 3B parameter model (`{MODEL}`) executing specific tasks across four different professional roles.

---

## 1. Summary of Benchmarks

| Professional Role | Task Description | Optimization Pattern | Execution Time | Output Validity |
| :--- | :--- | :--- | :--- | :--- |
| **Software Engineer** | Bug Traceback Triage | JSON Schema Constraint | {t_eng:.2f}s | 100% Valid JSON |
| **Project Manager** | Standup to Client Report | Few-Shot / Formatting Prompt | {t_pm:.2f}s | Valid Markdown |
| **Operations Analyst** | Invoice Property Extraction | JSON Schema Constraint | {t_ops:.2f}s | 100% Valid JSON |
| **Content Marketer** | SaaS Copywriting | Creativity / Persona Prompt | {t_mkt:.2f}s | Valid Markdown |

---

## 2. Professional Workflows & Outputs

### 🛠️ Use Case 1: The Software Engineer
* **Objective:** Automatically parse errors from logs to format bug reports and trigger automated CI/CD workflows.
* **Output (Generated in {t_eng:.2f}s):**
```json
{json.dumps(r_eng, indent=2)}
```

### 📋 Use Case 2: The Project Manager
* **Objective:** Streamline administrative reporting by turning developer-facing updates into polished, client-facing language.
* **Output (Generated in {t_pm:.2f}s):**
{r_pm}

### 📊 Use Case 3: The Operations Analyst
* **Objective:** Automate paper-to-system operations by extracting invoice IDs, computing totals, and validating taxes from raw OCR text.
* **Output (Generated in {t_ops:.2f}s):**
```json
{json.dumps(r_ops, indent=2)}
```

### ✍️ Use Case 4: The Content Marketer
* **Objective:** Accelerate product marketing by drafting contextual, platform-specific copy from developer specifications.
* **Output (Generated in {t_mkt:.2f}s):**
{r_mkt}

---

## 3. Practical Guidelines for Deploying 3B Models in Workflows

1. **Automated Data Processing (Engineer & Analyst):**
   When formatting matters, use **Schema Constraint**. It prevents the model from generating boilerplate text (like "Here is your JSON:") and matches database insertion requirements perfectly.
2. **Text Refactoring (Project Manager):**
   Keep the prompt instruction list concise. Small models follow markdown headings and lists reliably if you structure the input notes with simple hyphen points.
3. **Copywriting (Marketer):**
   Set the model temperature higher (e.g., `0.7` to `0.9`) to generate punchy and creative language hooks.
"""
    
    with open(DOC_FILE, "w", encoding="utf-8") as f:
        f.write(md_content)
    print("✓ Documentation written successfully!")

if __name__ == "__main__":
    main()
