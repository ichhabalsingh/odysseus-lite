import ollama
import json
import time

# ------------------------------------------------------------------
# 1. DEFINE THE ACTUAL PYTHON TOOL (The "Hands")
# ------------------------------------------------------------------
def calculate_expression(expression: str) -> str:
    """Safely evaluates a basic math string."""
    try:
        # Note: In production, use a safe math parser instead of eval
        result = eval(expression, {"__builtins__": None}, {})
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_system_status() -> str:
    """Mock tool returning system metrics."""
    return json.dumps({"cpu_usage": "24%", "vram_available": "3.8 GB", "status": "nominal"})

# Map string names to python function objects
TOOL_MAP = {
    "calculate_expression": calculate_expression,
    "get_system_status": get_system_status
}

# ------------------------------------------------------------------
# 2. DEFINE THE TOOL SCHEMAS FOR OLLAMA (The "Instructions")
# ------------------------------------------------------------------
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "calculate_expression",
            "description": "Evaluates a mathematical expression and returns the numerical result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate, e.g., '14 * 25 + 10'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Retrieves real-time system metrics including CPU usage and available VRAM.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ------------------------------------------------------------------
# 3. THE AGENT TOOL EXECUTION LOOP
# ------------------------------------------------------------------
def run_tool_agent(user_prompt: str, model_name: str = "llama3.1:8b"):
    print(f"\n{"="*60}")
    print(f"USER PROMPT: '{user_prompt}'")
    print(f"MODEL: {model_name}")
    print(f"{"="*60}")

    messages = [{"role": "user", "content": user_prompt}]

    # --- STEP A: Ask LLM if it needs a tool ---
    print("\n[Step 1] Sending prompt and tool schemas to LLM...")
    t0 = time.time()
    
    response = ollama.chat(
        model=model_name,
        messages=messages,
        tools=tools_schema,
        keep_alive=0  # Clear VRAM right after decision
    )
    
    print(f"Decision made in {time.time() - t0:.2f}s")
    
    msg = response['message']
    tool_calls = msg.get('tool_calls', [])

    # Check if model triggered a tool
    if not tool_calls:
        print("\n[Result] The model answered directly without using any tools:")
        print(msg['content'])
        return

    # Append assistant's response (with tool call requests) to message history
    messages.append(msg)

    # --- STEP B: Execute requested tools locally ---
    for tool_call in tool_calls:
        func_name = tool_call['function']['name']
        args = tool_call['function']['arguments']
        
        print(f"\n[Step 2] Model requested tool: '{func_name}'")
        print(f"         Arguments generated: {args}")

        if func_name in TOOL_MAP:
            # Execute local Python function
            tool_output = TOOL_MAP[func_name](**args)
            print(f"         Tool Output: {tool_output}")

            # Append tool result back to message history for the final pass
            messages.append({
                "role": "tool",
                "content": tool_output
            })
        else:
            print(f"Requested tool '{func_name}' not found in local registry.")

    # --- STEP C: Pass tool results back to LLM for final answer ---
    print("\n[Step 3] Sending tool outputs back to LLM for natural language response...")
    t0 = time.time()
    
    final_response = ollama.chat(
        model=model_name,
        messages=messages,
        keep_alive=0
    )
    
    print(f"Final response generated in {time.time() - t0:.2f}s")
    print("\n" + "="*60)
    print("FINAL AGENT ANSWER:")
    print("="*60)
    print(final_response['message']['content'])

if __name__ == "__main__":
    # Test 1: Calculation that small models often fail at mental math
    run_tool_agent("What is 142 multiplied by 389 plus 1200?")
    
    # Test 2: System status check
    run_tool_agent("Check my VRAM status and tell me if system resources look good.")