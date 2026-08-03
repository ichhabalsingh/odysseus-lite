import re
import json
import time
import ollama
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
MODEL = "qwen2.5-coder:3b-instruct"
REPORT_FILE = "research_report.md"

# =====================================================================
# SEARCH HELPER
# =====================================================================
def web_search(query: str, num_results=3) -> str:
    print(f"   [Search execution]: '{query}'")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
            if not results:
                return f"No results found for '{query}'."
            return "\n".join([f"- Snippet: {r['body']}" for r in results])
    except Exception as e:
        return f"Search failed for '{query}': {str(e)}"

# =====================================================================
# DEEP RESEARCH PIPELINE
# =====================================================================
def run_deep_research(topic: str, max_depth=2):
    print(f"\n==================================================")
    print(f"   LAUNCHING DEEP RESEARCH ON: '{topic}'")
    print("==================================================")
    
    start_time = time.time()
    accumulated_facts = []
    
    # -----------------------------------------------------------------
    # DEPTH 1: INITIAL BROAD SEARCH
    # -----------------------------------------------------------------
    print(f"\n[Depth 1] Generating search queries for broad topic...")
    query_prompt = f"""You are a research planner. Generate exactly 3 distinct search queries to gather broad information on:
"{topic}"

Format your output as a JSON list of strings, e.g.:
["query 1", "query 2", "query 3"]
Do not output markdown code blocks or explanations."""

    res_queries = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": query_prompt}],
        options={"temperature": 0.0},
        keep_alive="5m"
    )
    
    queries_text = res_queries['message']['content'].strip()
    try:
        # Strip potential markdown code wraps
        queries_clean = re.sub(r"^```json\s*", "", queries_text)
        queries_clean = re.sub(r"^```\s*", "", queries_clean)
        queries_clean = re.sub(r"\s*```$", "", queries_clean)
        queries = json.loads(queries_clean)
    except Exception:
        # Fallback split
        queries = [q.strip().strip('"') for q in re.findall(r'"([^"]*)"', queries_text) if q.strip()]
        if not queries:
            queries = [topic] # Fallback to topic
            
    print(f"Generated Queries: {queries}")
    
    # Execute searches and extract facts
    depth_1_results = []
    for q in queries[:3]:
        search_out = web_search(q)
        depth_1_results.append(f"Query: {q}\nResults:\n{search_out}")
        
    print("\n[Depth 1] Extracting facts from initial search...")
    extract_prompt = f"""You are a research analyst. Review the following search results and extract a list of bulleted facts about:
"{topic}"

SEARCH RESULTS:
{"\n---\n".join(depth_1_results)}
"""
    res_facts = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": extract_prompt}],
        options={"temperature": 0.0},
        keep_alive="5m"
    )
    facts_1 = res_facts['message']['content'].strip()
    accumulated_facts.append(facts_1)
    print(f"Extracted Facts (Depth 1):\n{facts_1}\n")

    # -----------------------------------------------------------------
    # DEPTH 2: GAP ANALYSIS & DEEPER SEARCH
    # -----------------------------------------------------------------
    if max_depth >= 2:
        print(f"[Depth 2] Reviewing facts & finding missing gaps...")
        gap_prompt = f"""You are a research planner. Review the facts gathered so far and identify exactly 2 gaps or details that are missing or require clarification.
Generate exactly 2 specific search queries to find those missing details.

FACTS GATHERED:
{facts_1}

Format your output as a JSON list of strings, e.g.:
["specific query 1", "specific query 2"]
Do not output markdown code blocks or explanations."""

        res_gaps = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": gap_prompt}],
            options={"temperature": 0.0},
            keep_alive="5m"
        )
        
        gaps_text = res_gaps['message']['content'].strip()
        try:
            gaps_clean = re.sub(r"^```json\s*", "", gaps_text)
            gaps_clean = re.sub(r"^```\s*", "", gaps_clean)
            gaps_clean = re.sub(r"\s*```$", "", gaps_clean)
            gap_queries = json.loads(gaps_clean)
        except Exception:
            gap_queries = [q.strip().strip('"') for q in re.findall(r'"([^"]*)"', gaps_text) if q.strip()]
            if not gap_queries:
                gap_queries = [f"{topic} details"]
                
        print(f"Generated Gap Queries: {gap_queries}")
        
        depth_2_results = []
        for q in gap_queries[:2]:
            search_out = web_search(q)
            depth_2_results.append(f"Query: {q}\nResults:\n{search_out}")
            
        print("\n[Depth 2] Extracting facts from gap search...")
        extract_gap_prompt = f"""You are a research analyst. Review the new search results and extract bulleted facts.
        
NEW SEARCH RESULTS:
{"\n---\n".join(depth_2_results)}
"""
        res_gap_facts = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": extract_gap_prompt}],
            options={"temperature": 0.0},
            keep_alive="5m"
        )
        facts_2 = res_gap_facts['message']['content'].strip()
        accumulated_facts.append(facts_2)
        print(f"Extracted Facts (Depth 2):\n{facts_2}\n")

    # -----------------------------------------------------------------
    # SYNTHESIS & REPORT WRITING
    # -----------------------------------------------------------------
    print("[Synthesis] Compiling final research report...")
    synthesis_prompt = f"""You are a senior research coordinator.
Compile a comprehensive, structured markdown report about the topic:
"{topic}"

Use all the facts gathered during our research process below. 
Structure the report with professional headings, bullet points, and summaries.

FACTS GATHERED:
{"\n---\n".join(accumulated_facts)}
"""
    res_final = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": synthesis_prompt}],
        options={"temperature": 0.1},
        keep_alive=0 # Unload model after finishing
    )
    report = res_final['message']['content'].strip()
    
    elapsed = time.time() - start_time
    print(f"\n✓ Deep Research finished in {elapsed:.2f} seconds.")
    
    # Save Report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✓ Final report written to {REPORT_FILE}!")

if __name__ == "__main__":
    # Topic that requires multiple perspectives/updates
    test_topic = "Compare the latest stable releases of Python, Rust, and Go as of the current year (2026)."
    run_deep_research(test_topic, max_depth=2)
