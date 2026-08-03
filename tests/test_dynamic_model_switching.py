import ollama                                                                                                                                                                                
                                                                                                                                                                                                 
# Define our model pool                                                                                                                                                                      
MODELS = {                                                                                                                                                                                   
    "reasoning": "deepseek-r1:8b",       # For planning, logic verification, math                                                                                                            
    "coding_tools": "qwen2.5-coder:7b-instruct", # For writing files, running bash/python, tool syntax                                                                                       
}                                                                                                                                                                                            
                                                                                                                                                                                                
def orchestrate_task(user_prompt: str):                                                                                                                                                      
    messages = []                                                                                                                                                                            
                                                                                                                                                                                                
    # --- PHASE 1: PLANNING (Reasoning Model) ---                                                                                                                                            
    print("\n[Orchestrator] Sending task to REASONING model for planning...")                                                                                                                
    planning_prompt = f"Create a step-by-step plan to solve this task. Do not execute tools yet. Task: {user_prompt}"                                                                        
                                                                                                                                                                                                
    res = ollama.chat(                                                                                                                                                                       
        model=MODELS["reasoning"],                                                                                                                                                           
        messages=[{"role": "user", "content": planning_prompt}],                                                                                                                             
        keep_alive="2m"  # Keep loaded for 2 mins in case we need it for critique                                                                                                            
    )                                                                                                                                                                                        
    plan = res['message']['content']
    print(f"\n[Plan Generated]:\n{plan}")
    
    # Store the plan in messages
    messages.append({"role": "system", "content": f"Here is the execution plan: {plan}"})
    messages.append({"role": "user", "content": user_prompt})
    
    # --- PHASE 2: TOOL USE & CODING (Coder / Tool Model) ---
    max_steps = 5
    for step in range(1, max_steps + 1):
        print(f"\n--- STEP {step}: TOOL EXECUTION ---")
        
        # We switch to the Coding/Tool model
        res = ollama.chat(
            model=MODELS["coding_tools"],
            messages=messages,
            keep_alive="5m"  # Keep loaded since it executes tools step-by-step
        )
        
        assistant_content = res['message']['content']
        print(f"[Agent Response]:\n{assistant_content}")
        messages.append({"role": "assistant", "content": assistant_content})
        
        # Check for final answer
        if "ANSWER:" in assistant_content:
            break
