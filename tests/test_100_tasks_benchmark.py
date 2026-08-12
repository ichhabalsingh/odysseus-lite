#!/usr/bin/env python3
import time
import json
import re
import os
import sys
import argparse
import subprocess
import ollama

# Add parent directory to system path to import core config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import Config

# --- CONFIGURATION ---
MODEL = Config.EXECUTOR_MODEL
REPORT_FILE = "100_tasks_benchmark_report.md"

# =====================================================================
# THE 100 TASK DATABASE (Divided into 5 domains)
# =====================================================================
TASKS = [
    # --- DOMAIN 1: SOFTWARE ENGINEERING (Tasks 1-20) ---
    {"id": "ENG-001", "domain": "Engineering", "task": "Write a python function to check if a string is a palindrome."},
    {"id": "ENG-002", "domain": "Engineering", "task": "Parse traceback 'KeyError: \"user_id\"' in user_data.py line 12 and suggest a fix."},
    {"id": "ENG-003", "domain": "Engineering", "task": "Write a bash command to check VRAM status using nvidia-smi."},
    {"id": "ENG-004", "domain": "Engineering", "task": "Write a python function that merges two sorted lists."},
    {"id": "ENG-005", "domain": "Engineering", "task": "Create a git commit message for fixing a memory leak in database.py."},
    {"id": "ENG-006", "domain": "Engineering", "task": "Write a script to convert Celsius to Fahrenheit."},
    {"id": "ENG-007", "domain": "Engineering", "task": "Parse traceback 'ZeroDivisionError: division by zero' in calc.py line 45."},
    {"id": "ENG-008", "domain": "Engineering", "task": "Write a python regex to validate email addresses."},
    {"id": "ENG-009", "domain": "Engineering", "task": "Create a bash command to count files in a directory matching *.py."},
    {"id": "ENG-010", "domain": "Engineering", "task": "Write a python function that checks if a number is prime."},
    {"id": "ENG-011", "domain": "Engineering", "task": "Parse traceback 'TypeError: unsupported operand' in utils.py line 30."},
    {"id": "ENG-012", "domain": "Engineering", "task": "Write a bash command to print the last 15 lines of a log.txt file."},
    {"id": "ENG-013", "domain": "Engineering", "task": "Write a python script that parses a URL into components."},
    {"id": "ENG-014", "domain": "Engineering", "task": "Create a git commit message for adding local RAG search features."},
    {"id": "ENG-015", "domain": "Engineering", "task": "Write a python function that returns the second largest value in a list."},
    {"id": "ENG-016", "domain": "Engineering", "task": "Parse traceback 'IndexError: list index out of range' in process.py line 8."},
    {"id": "ENG-017", "domain": "Engineering", "task": "Write a python script to list all environment variables starting with PATH."},
    {"id": "ENG-018", "domain": "Engineering", "task": "Write a bash command to check current memory and CPU usage on Linux."},
    {"id": "ENG-019", "domain": "Engineering", "task": "Write a python function to check if two words are anagrams."},
    {"id": "ENG-020", "domain": "Engineering", "task": "Create a python script that generates a random password of length 12."},

    # --- DOMAIN 2: OPERATIONS & BUSINESS (Tasks 21-40) ---
    {"id": "OPS-021", "domain": "Operations", "task": "Calculate total and tax for invoice: 3 items @ $12.50, shipping $5.00, tax 7%."},
    {"id": "OPS-022", "domain": "Operations", "task": "Format raw standup: 'Alice finished landing page, Bob resolved VM issue' to markdown update."},
    {"id": "OPS-023", "domain": "Operations", "task": "Calculate total for invoice: 10 items @ $9.99, shipping free, tax 8%."},
    {"id": "OPS-024", "domain": "Operations", "task": "Format team log: 'Mark resolved DB bug, Sarah deployed API' to status report."},
    {"id": "OPS-025", "domain": "Operations", "task": "Calculate tax for: subtotal $250.00, tax rate 10%."},
    {"id": "OPS-026", "domain": "Operations", "task": "Extract Client name and Invoice ID from: 'INV-1092 client Acme Corp date Aug 3rd'."},
    {"id": "OPS-027", "domain": "Operations", "task": "Format log: 'Jeff completed slides, Client meeting set for Tue 10 AM' to status update."},
    {"id": "OPS-028", "domain": "Operations", "task": "Calculate total value: 5 boxes @ $45.00, shipping $12.00, tax-exempt."},
    {"id": "OPS-029", "domain": "Operations", "task": "Extract invoice items: 'Purchased 2x Gears ($20 each) and 1x Screw ($5)'."},
    {"id": "OPS-030", "domain": "Operations", "task": "Format task list: 'Sarah deploy, Mark database migration, Jeff review slides' to roadmap."},
    {"id": "OPS-031", "domain": "Operations", "task": "Calculate total: 100 units @ $1.50, shipping $10.00, tax 5%."},
    {"id": "OPS-032", "domain": "Operations", "task": "Format client email summarizing that migrations were successful and meeting is Tue."},
    {"id": "OPS-033", "domain": "Operations", "task": "Calculate discount: 20% off a $150.00 product."},
    {"id": "OPS-034", "domain": "Operations", "task": "Extract info: 'Invoice INV-900 for Client Delta Inc total value $1250.00'."},
    {"id": "OPS-035", "domain": "Operations", "task": "Format Standup: 'Sarah worked on API, Mark did code review' to client report."},
    {"id": "OPS-036", "domain": "Operations", "task": "Calculate total: 3 tickets @ $75.00 each, processing fee $2.50 each."},
    {"id": "OPS-037", "domain": "Operations", "task": "Extract items from: 'Order: 5x pens ($1 each) and 2x pads ($3 each)'."},
    {"id": "OPS-038", "domain": "Operations", "task": "Format update: 'Meeting rescheduled to Wed 11 AM, Sarah api done' to status list."},
    {"id": "OPS-039", "domain": "Operations", "task": "Calculate net profit: revenue $5000, costs $3200."},
    {"id": "OPS-040", "domain": "Operations", "task": "Format log: 'Mark code complete, Sarah dev test passed' to release notes."},

    # --- DOMAIN 3: MEDICAL (Tasks 41-60) ---
    {"id": "MED-041", "domain": "Medical", "task": "Summarize case: Patient Jane Doe 30yo, complaints of sore throat 2 days, BP 120/80. Add medical disclaimer."},
    {"id": "MED-042", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports dry cough, HR 72, BP 115/75. Warm fluids plan."},
    {"id": "MED-043", "domain": "Medical", "task": "Summarize case: Patient Bob Smith 50yo, chest tightness since morning, BP 140/90. Urgent EKG plan. Add medical disclaimer."},
    {"id": "MED-044", "domain": "Medical", "task": "Format clinical SOAP report for: Patient has headache, HR 80, BP 122/80. Pain relief plan."},
    {"id": "MED-045", "domain": "Medical", "task": "Extract symptoms from: 'Patient complains of fever, chills, and body aches for 2 days'."},
    {"id": "MED-046", "domain": "Medical", "task": "Summarize case: Patient child 5yo, fever 101F, no rash, active. Warm fluids plan. Add medical disclaimer."},
    {"id": "MED-047", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports knee pain after fall, swelling present, BP 118/76."},
    {"id": "MED-048", "domain": "Medical", "task": "Extract symptoms from: 'Patient reports shortness of breath and wheezing when walking'."},
    {"id": "MED-049", "domain": "Medical", "task": "Summarize case: Patient 65yo, routine check, history of HTN, BP 135/85. Meds refill. Add medical disclaimer."},
    {"id": "MED-050", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports stomach ache, nausea, BP 110/70."},
    {"id": "MED-051", "domain": "Medical", "task": "Extract symptoms from: 'Patient has sinus pressure, nasal congestion, and sore throat'."},
    {"id": "MED-052", "domain": "Medical", "task": "Summarize case: Patient 22yo, sprained ankle playing soccer, swelling, BP 120/80. RICE plan. Add medical disclaimer."},
    {"id": "MED-053", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports ear irritation, pain on chewing, BP 116/74."},
    {"id": "MED-054", "domain": "Medical", "task": "Extract symptoms from: 'Patient has dizzy spells and lightheadedness when standing up'."},
    {"id": "MED-055", "domain": "Medical", "task": "Summarize case: Patient 40yo, back pain after lifting box, BP 122/78. Rest plan. Add medical disclaimer."},
    {"id": "MED-056", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports fatigue, insomnia, BP 115/72."},
    {"id": "MED-057", "domain": "Medical", "task": "Extract symptoms from: 'Patient has skin irritation, itching, and redness on arm'."},
    {"id": "MED-058", "domain": "Medical", "task": "Summarize case: Patient 35yo, annual physical, BP 118/76. All labs normal. Add medical disclaimer."},
    {"id": "MED-059", "domain": "Medical", "task": "Format clinical SOAP report for: Patient reports heartburn, acid reflux, BP 120/80."},
    {"id": "MED-060", "domain": "Medical", "task": "Extract symptoms from: 'Patient complains of joint stiffness and swelling in fingers'."},

    # --- DOMAIN 4: EDUCATION & TEACHING (Tasks 61-80) ---
    {"id": "EDU-061", "domain": "Education", "task": "Generate a 1-question physics quiz on gravity with options and an answer key."},
    {"id": "EDU-062", "domain": "Education", "task": "Generate a 1-question math quiz on basic fractions with options and an answer key."},
    {"id": "EDU-063", "domain": "Education", "task": "Generate a 1-question history quiz on World War II with options and an answer key."},
    {"id": "EDU-064", "domain": "Education", "task": "Generate a 1-question biology quiz on cells with options and an answer key."},
    {"id": "EDU-065", "domain": "Education", "task": "Generate a 1-question chemistry quiz on atoms with options and an answer key."},
    {"id": "EDU-066", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching photosynthesis to 5th graders."},
    {"id": "EDU-067", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching fractions to 3rd graders."},
    {"id": "EDU-068", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching solar systems to 4th graders."},
    {"id": "EDU-069", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching water cycles to 5th graders."},
    {"id": "EDU-070", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching ecosystems to 6th graders."},
    {"id": "EDU-071", "domain": "Education", "task": "Generate a 1-question geography quiz on capitals with options and an answer key."},
    {"id": "EDU-072", "domain": "Education", "task": "Generate a 1-question literature quiz on Shakespeare with options and an answer key."},
    {"id": "EDU-073", "domain": "Education", "task": "Generate a 1-question physics quiz on velocity with options and an answer key."},
    {"id": "EDU-074", "domain": "Education", "task": "Generate a 1-question math quiz on decimals with options and an answer key."},
    {"id": "EDU-075", "domain": "Education", "task": "Generate a 1-question history quiz on Roman Empire with options and an answer key."},
    {"id": "EDU-076", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching Newton's laws to 7th graders."},
    {"id": "EDU-077", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching plate tectonics to 8th graders."},
    {"id": "EDU-078", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching US Constitution to 9th graders."},
    {"id": "EDU-079", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching cell division to 10th graders."},
    {"id": "EDU-080", "domain": "Education", "task": "Create a short 3-step lesson plan outline for teaching chemical reactions to 9th graders."},

    # --- DOMAIN 5: STUDENT STUDY CARDS (Tasks 81-100) ---
    {"id": "STU-081", "domain": "Student", "task": "Convert to study cards: 'Mitochondria are double-membraned. They generate ATP, earning them the powerhouse nickname.'"},
    {"id": "STU-082", "domain": "Student", "task": "Convert to study cards: 'The Magna Carta was signed in 1215 by King John, limiting royal authority.'"},
    {"id": "STU-083", "domain": "Student", "task": "Convert to study cards: 'Photosynthesis converts carbon dioxide and water into oxygen and glucose using sunlight.'"},
    {"id": "STU-084", "domain": "Student", "task": "Convert to study cards: 'DNA is a double helix molecule containing genetic instructions for development.'"},
    {"id": "STU-085", "domain": "Student", "task": "Convert to study cards: 'The Declaration of Independence was adopted on July 4, 1776, announcing separation from Britain.'"},
    {"id": "STU-086", "domain": "Student", "task": "Convert to study cards: 'Water freezes at 0 degrees Celsius and boils at 100 degrees Celsius under standard pressure.'"},
    {"id": "STU-087", "domain": "Student", "task": "Convert to study cards: 'The Earth revolves around the sun once every 365.25 days, creating seasonal changes.'"},
    {"id": "STU-088", "domain": "Student", "task": "Convert to study cards: 'A molecule of water consists of two hydrogen atoms bonded to one oxygen atom.'"},
    {"id": "STU-089", "domain": "Student", "task": "Convert to study cards: 'Protons have a positive charge, electrons have a negative charge, and neutrons have no charge.'"},
    {"id": "STU-090", "domain": "Student", "task": "Convert to study cards: 'Romeo and Juliet is a tragedy written by William Shakespeare early in his career.'"},
    {"id": "STU-091", "domain": "Student", "task": "Convert to study cards: 'The atomic number of an element is determined by the number of protons in its nucleus.'"},
    {"id": "STU-092", "domain": "Student", "task": "Convert to study cards: 'The French Revolution began in 1789, leading to the overthrow of the monarchy.'"},
    {"id": "STU-093", "domain": "Student", "task": "Convert to study cards: 'Gravity is a fundamental force that attracts any two objects with mass toward each other.'"},
    {"id": "STU-094", "domain": "Student", "task": "Convert to study cards: 'The nervous system transmits signals between the brain and the rest of the body.'"},
    {"id": "STU-095", "domain": "Student", "task": "Convert to study cards: 'The Gutenberg press was invented in 1440, revolutionizing book printing in Europe.'"},
    {"id": "STU-096", "domain": "Student", "task": "Convert to study cards: 'Light travels at approximately 300,000 kilometers per second in a vacuum.'"},
    {"id": "STU-097", "domain": "Student", "task": "Convert to study cards: 'The Amazon Rainforest produces a significant portion of the Earth's oxygen supply.'"},
    {"id": "STU-098", "domain": "Student", "task": "Convert to study cards: 'An isotope is an atom with the same number of protons but a different number of neutrons.'"},
    {"id": "STU-099", "domain": "Student", "task": "Convert to study cards: 'The first successful airplane flight was made by the Wright brothers in 1903.'"},
    {"id": "STU-100", "domain": "Student", "task": "Convert to study cards: 'Plate tectonics is the theory that Earth's outer shell is divided into several plates that glide.'"}
]

# =====================================================================
# SYSTEM PROMPTS & SCHEMAS FOR TEST VALIDATION
# =====================================================================
SYSTEM_PROMPTS = {
    "Engineering": "You are a software engineer. Solve this programming task directly. Respond with raw outputs or clean markdown code blocks.",
    "Operations": "You are an operations analyst. Structure the data or calculations. Respond clearly in markdown.",
    "Medical": "You are a clinician. Summarize this medical task. Include a 'MEDICAL DISCLAIMER' block at the very top. Formulate sections as Subjective, Objective, Assessment, Plan.",
    "Education": "You are a teacher. Create lesson outlines or quizzes with an ANSWER KEY at the bottom.",
    "Student": "You are a study assistant. Convert text into study cards formatted exactly as Q: and A:."
}

# =====================================================================
# THE BENCHMARK RUNNER
# =====================================================================
def run_task(task_obj: dict) -> dict:
    t0 = time.time()
    
    prompt = task_obj["task"]
    domain = task_obj["domain"]
    system_prompt = SYSTEM_PROMPTS[domain]
    
    try:
        res = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.1, "num_ctx": 4096},
            keep_alive="5m"
        )
        elapsed = time.time() - t0
        content = res['message']['content'].strip()
        
        # Programmatic Validation rules
        is_success = True
        reason = "Pass"
        
        content_lower = content.lower()
        if domain == "Medical" and "medical disclaimer" not in content_lower:
            is_success = False
            reason = "Failed Medical Disclaimer check"
        elif domain == "Education" and "answer key" not in content_lower and "quiz" in prompt:
            is_success = False
            reason = "Failed Answer Key check"
        elif domain == "Student" and ("q:" not in content_lower or "a:" not in content_lower):
            is_success = False
            reason = "Failed Study Card Q&A formatting check"
            
        return {
            "id": task_obj["id"],
            "domain": domain,
            "task": prompt,
            "elapsed": elapsed,
            "success": is_success,
            "reason": reason,
            "output_preview": content[:100].replace("\n", " ") + "..."
        }
    except Exception as e:
        return {
            "id": task_obj["id"],
            "domain": domain,
            "task": prompt,
            "elapsed": time.time() - t0,
            "success": False,
            "reason": f"Execution Error: {str(e)}",
            "output_preview": "N/A"
        }

def main():
    parser = argparse.ArgumentParser(description="Odysseus Lite 100-Task Benchmark Runner")
    parser.add_argument("--sample", type=int, default=10, help="Number of random tasks to sample (default: 10, max: 100)")
    args = parser.parse_args()
    
    sample_size = min(max(args.sample, 1), 100)
    
    print("==================================================")
    print(f"   STARTING BENCHMARK: RUNNING {sample_size} TASKS OUT OF 100")
    print("==================================================")
    
    import random
    random.seed(42)
    
    sampled_tasks = []
    domains = ["Engineering", "Operations", "Medical", "Education", "Student"]
    tasks_per_domain = max(1, sample_size // 5)
    
    for d in domains:
        domain_tasks = [t for t in TASKS if t["domain"] == d]
        sampled_tasks.extend(random.sample(domain_tasks, min(tasks_per_domain, len(domain_tasks))))
        
    sampled_tasks = sampled_tasks[:sample_size]
    
    run_results = []
    total_time = 0
    
    for idx, t in enumerate(sampled_tasks, 1):
        print(f"[{idx}/{sample_size}] Running {t['id']} ({t['domain']})...")
        res = run_task(t)
        run_results.append(res)
        total_time += res["elapsed"]
        status = "PASS" if res["success"] else f"FAIL ({res['reason']})"
        print(f"     Time: {res['elapsed']:.2f}s | Status: {status}")
        
    passed_runs = [r for r in run_results if r["success"]]
    pass_rate = (len(passed_runs) / len(run_results)) * 100
    avg_latency = total_time / len(run_results)
    
    print("\nBenchmarks completed!")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Avg Latency: {avg_latency:.2f}s / task")
    print(f"  Pass Rate: {pass_rate:.1f}% ({len(passed_runs)}/{len(run_results)})")
    
    # Generate Markdown Report
    report_md = f"""# Odysseus Lite: 100-Task Architectural Robustness Report
 
This report evaluates the instruction-adherence, domain adaptability, and speed of a local 1.5B model (`{MODEL}`) executing tasks drawn from a 100-task battery.
 
---
 
## 1. Executive Performance Metrics
* **Total Tasks Executed:** {sample_size} (Sampled from the 100-task database)
* **Combined Runtime:** {total_time:.2f} seconds
* **Average Task Latency:** {avg_latency:.2f} seconds
* **Programmatic Pass Rate:** **{pass_rate:.1f}%** ({len(passed_runs)}/{len(run_results)} passed)
 
---
 
## 2. Domain-Specific Breakdown
 
| Domain | Tasks Run | Passes | Fails | Pass Rate | Avg Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    
    for d in domains:
        d_runs = [r for r in run_results if r["domain"] == d]
        d_passes = [r for r in d_runs if r["success"]]
        d_rate = (len(d_passes) / len(d_runs)) * 100 if d_runs else 0
        d_latency = sum(r["elapsed"] for r in d_runs) / len(d_runs) if d_runs else 0
        report_md += f"| **{d}** | {len(d_runs)} | {len(d_passes)} | {len(d_runs) - len(d_passes)} | {d_rate:.1f}% | {d_latency:.2f}s |\n"
        
    report_md += """
---
 
## 3. Comprehensive Task Execution Logs
 
| Task ID | Domain | Task Query | Status | Latency | Output Preview |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    
    for r in run_results:
        status = "PASS" if r["success"] else f"FAIL ({r['reason']})"
        report_md += f"| {r['id']} | {r['domain']} | {r['task']} | {status} | {r['elapsed']:.2f}s | {r['output_preview']} |\n"
        
    report_md += """
---
 
## 4. Engineering Recommendations for Domain Tuning
 
1. **Medical Clinical SOPs:**
   * Guardrail check: Ensure a parser checks for the string `MEDICAL DISCLAIMER` before logging notes to patient histories.
2. **Education/Quiz Workloads:**
   * Qwen 1.5B model writes excellent multiple-choice structures, but require an explicit instruction to append the `ANSWER KEY` to the bottom to avoid cheating/incomplete outputs.
3. **Student Study Aids:**
   * Forcing the Q&A pattern card structure is best done by providing a few-shot exemplar in the system prompt.
"""
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"\nMaster Report written successfully to {REPORT_FILE}!")

if __name__ == "__main__":
    main()
