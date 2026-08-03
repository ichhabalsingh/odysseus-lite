import ollama
import time

def run_generator_critic(prompt: str):
    print("=" * 60)
    print(f"PROMPT: {prompt}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # PHASE 1: GENERATOR
    # ------------------------------------------------------------------
    print("\n[Phase 1/3] Generator (hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M) generating initial draft...")
    t0 = time.time()
    
    draft_res = ollama.chat(
        model='hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M',
        messages=[{'role': 'user', 'content': prompt}],
        keep_alive=0  # Immediately free VRAM after execution
    )
    draft = draft_res['message']['content']
    print(f"✓ Completed in {time.time() - t0:.2f}s")

    # ------------------------------------------------------------------
    # PHASE 2: CRITIC
    # ------------------------------------------------------------------
    print("\n[Phase 2/3] Critic (deepseek-r1:1.5b) reviewing draft for flaws...")
    t0 = time.time()
    
    critic_prompt = f"""
    You are a strict code and logic reviewer.
    
    ORIGINAL PROMPT:
    "{prompt}"

    PROPOSED DRAFT:
    {draft}

    Task:
    1. Identify any missing requirements or assumptions.
    2. Find syntax errors, logical bugs, or unhandled edge cases (e.g. empty lists, null inputs).
    3. List 2-3 specific improvements needed.
    Be concise and direct.
    """

    critic_res = ollama.chat(
        model='deepseek-r1:1.5b',
        messages=[{'role': 'user', 'content': critic_prompt}],
        keep_alive=0
    )
    critique = critic_res['message']['content']
    print(f"✓ Completed in {time.time() - t0:.2f}s")

    # ------------------------------------------------------------------
    # PHASE 3: REFINER / SYNTHESIZER
    # ------------------------------------------------------------------
    print("\n[Phase 3/3] Refiner (deepseek-r1:1.5b) building final solution...")
    t0 = time.time()

    refiner_prompt = f"""
    You are an expert developer. Refine and rewrite the initial solution based on the critique.

    ORIGINAL PROMPT:
    "{prompt}"

    INITIAL DRAFT:
    {draft}

    CRITIQUE:
    {critique}

    Produce the final, complete, production-ready response now.
    """

    final_res = ollama.chat(
        model='deepseek-r1:1.5b',
        messages=[{'role': 'user', 'content': refiner_prompt}],
        keep_alive=0
    )
    final_output = final_res['message']['content']
    print(f"✓ Completed in {time.time() - t0:.2f}s")

    # ------------------------------------------------------------------
    # DISPLAY RESULTS
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("CRITIQUE SUMMARY:")
    print("=" * 60)
    print(critique)

    print("\n" + "=" * 60)
    print("FINAL REFINED OUTPUT:")
    print("=" * 60)
    print(final_output)

if __name__ == "__main__":
    # Test prompt with a subtle edge-case trick
    test_prompt = "Write a Python function `get_second_largest(numbers)` that returns the second largest number in a list."
    run_generator_critic(test_prompt)