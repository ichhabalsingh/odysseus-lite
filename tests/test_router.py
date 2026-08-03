import ollama
import time
import json

# --- 1. Define the Agents (Workers) ---
AGENTS = {
    "MATH": {
        "model": "deepseek-r1:1.5b",
        "prompt": "You are a math expert. Think step-by-step and show your work.",
        "description": "Use this for math, logic puzzles, or physics."
    },
    "CODE": {
        "model": "llama3:8b-instruct-q8_0",
        "prompt": "You are a Senior Python Security Engineer. Write secure, production-grade Python code. NEVER use eval(), exec(), or os.system() with unsanitized input. Handle all edge cases and exceptions explicitly. Return ONLY the raw code string, with absolutely no markdown formatting, backticks, or explanatory text.",
        "description": "Use this for writing or debugging code."
    },
    "GENERAL": {
        "model": "llama3.1:8b", 
        "prompt": "You are a helpful assistant.",
        "description": "Use this for general writing, chatting, or questions."
    }
}

# --- 2. Build the Router ---
def route_task(user_prompt: str) -> str:
    """Uses a small model to classify the intent of the prompt."""
    
    router_prompt = f"""
    Read the following prompt and classify it into exactly ONE of these categories: [MATH, CODE, GENERAL].
    Do not output any other text. Only output the category name.

    PROMPT: {user_prompt}
    CATEGORY:
    """
    
    print("\n[ROUTER] Classifying intent...")
    t0 = time.time()
    
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": router_prompt}],
        keep_alive=0 
    )
    
    intent = response['message']['content'].strip().upper()
    print(f"✓ Router chose: {intent} (in {time.time()-t0:.2f}s)")
    
    return intent if intent in AGENTS else "GENERAL"

# --- 3. The Main Execution Loop ---
def run_odysseus_lite(user_prompt: str):
    print(f"\n{"="*60}\nPROMPT: {user_prompt}\n{"="*60}")
    
    selected_agent = route_task(user_prompt)
    agent_config = AGENTS[selected_agent]
    
    print(f"\n[EXECUTOR] Loading {agent_config['model']} for {selected_agent} task...")
    t0 = time.time()
    
    # We set up the kwargs for the API call
    chat_kwargs = {
        "model": agent_config['model'],
        "messages": [
            {"role": "system", "content": agent_config['prompt']},
            {"role": "user", "content": user_prompt}
        ],
        "keep_alive": 0
    }

    # If it's the CODE agent, we force structured JSON output
    if selected_agent == "CODE":
        chat_kwargs["format"] = {
            "type": "object",
            "properties": {
                "python_code": {
                    "type": "string",
                    "description": "The raw, executable Python code with no markdown formatting."
                }
            },
            "required": ["python_code"]
        }
        # It's recommended to set temperature to 0 for deterministic schema outputs
        chat_kwargs["options"] = {"temperature": 0}
    
    response = ollama.chat(**chat_kwargs)
    
    print(f"Execution completed (in {time.time()-t0:.2f}s)")
    print("\nOUTPUT:")
    
    # If it was a CODE task, we extract the code from the JSON
    if selected_agent == "CODE":
        try:
            # Parse the stringified JSON returned by the model
            structured_data = json.loads(response['message']['content'])
            print(structured_data.get('python_code', 'Error: No code found in JSON.'))
        except json.JSONDecodeError:
            print("Failed to parse the structured output.")
            print("Raw response:", response['message']['content'])
    else:
        # Otherwise, just print the normal text
        print(response['message']['content'])

if __name__ == "__main__":
    # Test 2: Code
    run_odysseus_lite("Write a Python function to parse a JSON string into a dictionary, handling errors.")