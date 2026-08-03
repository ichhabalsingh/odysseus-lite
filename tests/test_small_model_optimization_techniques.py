import json
import time
import ollama

# --- CONFIGURATION ---
SMALL_MODEL = "granite4.1:3b"

# Sample Work Data: A messy meeting conversation
MEETING_DATA = """
Hey team, let's align on the roadmap. Mark, we need the database schemas finalized by Friday, August 7th. 
Also, Sarah, please draft the landing page copy before the marketing sync on Monday afternoon. 
Wait, who is preparing the slide deck? Oh, Jeff, you volunteered last week. Make sure that's done by Tuesday morning.
Attendees on the call: Mark, Sarah, Jeff, and David.
"""

# Expected output JSON structure
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "attendees": {
            "type": "array",
            "items": {"type": "string"}
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assignee": {"type": "string"},
                    "task_description": {"type": "string"},
                    "deadline": {"type": "string"}
                },
                "required": ["assignee", "task_description", "deadline"]
            }
        }
    },
    "required": ["attendees", "tasks"]
}

# --- EXPERIMENT 1: STRUCTURED EXTRACTION ---

def test_zero_shot():
    """Test 1: Zero-shot prompt asking for JSON."""
    prompt = f"""
    Extract the list of attendees and the list of tasks (with assignee, task_description, and deadline) from the following meeting transcript.
    Respond ONLY in valid JSON. No explanations.
    
    TRANSCRIPT:
    {MEETING_DATA}
    """
    t0 = time.time()
    res = ollama.chat(
        model=SMALL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    content = res['message']['content'].strip()
    
    # Try parsing
    try:
        data = json.loads(content)
        is_valid = "Yes"
    except Exception:
        # Sometimes models wrap in markdown blocks
        clean_content = content.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(clean_content)
            is_valid = "Yes (Required Markdown Strip)"
        except Exception:
            is_valid = "No (Failed to parse JSON)"
            
    print(f"\n[1A. Zero-Shot Run] Time: {elapsed:.2f}s | Valid JSON: {is_valid}")
    print(f"Output:\n{content}\n" + "-"*50)


def test_few_shot():
    """Test 2: Few-shot prompt showcasing structure."""
    prompt = f"""You are a data extraction assistant. You extract structured data into JSON format.

EXAMPLE INPUT:
"Yesterday we met. John needs to review the contract by next Wednesday. Alice, email the client tomorrow. Attendance: John, Alice."

EXAMPLE OUTPUT:
{{
  "attendees": ["John", "Alice"],
  "tasks": [
    {{"assignee": "John", "task_description": "Review the contract", "deadline": "next Wednesday"}},
    {{"assignee": "Alice", "task_description": "Email the client", "deadline": "tomorrow"}}
  ]
}}

INPUT:
"{MEETING_DATA}"

OUTPUT:"""
    t0 = time.time()
    res = ollama.chat(
        model=SMALL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    content = res['message']['content'].strip()
    
    try:
        json.loads(content)
        is_valid = "Yes"
    except Exception:
        clean_content = content.replace("```json", "").replace("```", "").strip()
        try:
            json.loads(clean_content)
            is_valid = "Yes (Required Markdown Strip)"
        except Exception:
            is_valid = "No (Failed to parse JSON)"
            
    print(f"\n[1B. Few-Shot Run] Time: {elapsed:.2f}s | Valid JSON: {is_valid}")
    print(f"Output:\n{content}\n" + "-"*50)


def test_json_schema():
    """Test 3: Schema-constrained extraction using Ollama's format option."""
    prompt = f"""
    Extract the list of attendees and the list of tasks from this transcript:
    {MEETING_DATA}
    """
    t0 = time.time()
    res = ollama.chat(
        model=SMALL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=JSON_SCHEMA, # Enforce structured grammar output
        options={"temperature": 0.0}
    )
    elapsed = time.time() - t0
    content = res['message']['content'].strip()
    
    try:
        json.loads(content)
        is_valid = "Yes (Perfect Grammar Enforcement)"
    except Exception:
        is_valid = "No"
        
    print(f"\n[1C. Schema-Constrained Run] Time: {elapsed:.2f}s | Valid JSON: {is_valid}")
    print(f"Output:\n{content}\n" + "-"*50)

# --- EXPERIMENT 2: MAP-REDUCE PROCESSING ---

def test_map_reduce_summary():
    """Test 4: Chunked summarization of a large document log."""
    # Simulated long document divided into 3 chunks
    chunks = [
        "Day 1 Log: Server migration started. Team set up VM instances on GCP. Mark configured databases, Sarah created API gateways.",
        "Day 2 Log: Found network latency issue. Sarah resolved load balancer config. Mark ran database stress tests, yielding 400ms delay.",
        "Day 3 Log: Stress tests resolved. Code deployed to production. Jeff and David completed final verification tests. Migration success."
    ]
    
    print("\n=== STARTING MAP-REDUCE SUMMARIZATION ===")
    t_start = time.time()
    
    # 1. MAP: Summarize each chunk separately
    summaries = []
    for idx, chunk in enumerate(chunks, 1):
        print(f" -> Mapping Chunk {idx}...")
        prompt = f"Summarize this log line in one sentence: {chunk}"
        res = ollama.chat(
            model=SMALL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0}
        )
        summaries.append(res['message']['content'].strip())
    
    # 2. REDUCE: Combine the summaries into a final report
    combined_summaries = "\n".join([f"- {s}" for s in summaries])
    print(f"Combined Map Summaries:\n{combined_summaries}")
    
    print(" -> Reducing summaries to final report...")
    reduce_prompt = f"""
    Create a unified final executive summary report based on these daily logs summaries:
    {combined_summaries}
    """
    res_final = ollama.chat(
        model=SMALL_MODEL,
        messages=[{"role": "user", "content": reduce_prompt}],
        options={"temperature": 0.0}
    )
    
    elapsed = time.time() - t_start
    print(f"\n[2. Map-Reduce Complete] Total Time: {elapsed:.2f}s")
    print(f"Final Executive Report:\n{res_final['message']['content'].strip()}\n" + "="*50)


if __name__ == "__main__":
    print("==================================================")
    print("    RUNNING WORK OPTIMIZATION EXPERIMENTS         ")
    print("==================================================")
    
    # Run structured extraction benchmarks
    test_zero_shot()
    test_few_shot()
    test_json_schema()
    
    # Run long-document map-reduce benchmark
    test_map_reduce_summary()
