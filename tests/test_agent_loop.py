import re                                                                                                                                                                                    
import json                                                                                                                                                                                  
import ollama                                                                                                                                                                                
                                                                                                                                                                                                
# The System Prompt instructs the model on how to format its thoughts and actions                                                                                                            
SYSTEM_PROMPT = """You are Odysseus Lite, an AI agent. You think step-by-step and use tools to solve tasks.                                                                                  
                                                                                                                                                                                                
For any task, follow this exact structure:                                                                                                                                                   
1. THOUGHT: Explain what you need to do and which tool to use.                                                                                                                               
2. ACTION: Call a tool using XML tags.                                                                                                                                                       
3. OBSERVE: You will receive the output of the tool from the user.                                                                                                                           
4. ANSWER: Output your final response once you have the answer.                                                                                                                              
                                                                                                                                                                                                
AVAILABLE TOOLS:                                                                                                                                                                             
- <tool_echo>{"message": "string to echo back"}</tool_echo>                                                                                                                                  
- <tool_add>{"a": integer, "b": integer}</tool_add>                                                                                                                                          
                                                                                                                                                                                                
Always format your actions as valid JSON inside the tags. Do not call multiple tools at once.                                                                                                
"""                                                                                                                                                                                          
                                                                                                                                                                                                
def execute_mock_tool(tag: str, args: dict) -> str:                                                                                                                                          
    """A mock tool executor to verify parsing logic works."""                                                                                                                                
    if tag == "tool_echo":                                                                                                                                                                   
        return f"Echoed back: {args.get('message', '')}"                                                                                                                                     
    elif tag == "tool_add":                                                                                                                                                                  
        a = args.get('a', 0)                                                                                                                                                                 
        b = args.get('b', 0)                                                                                                                                                                 
        return f"Result of {a} + {b} is {a + b}"                                                                                                                                             
    else:                                                                                                                                                                                    
        return f"Unknown tool: {tag}"                                                                                                                                                        
                                                                                                                                                                                                
def run_agent(prompt: str, model_name="llama3.1:8b"):                                                                                                                          
    print(f"User Prompt: {prompt}\n" + "="*50)                                                                                                                                               
                                                                                                                                                                                                
    # Initialize message history                                                                                                                                                             
    messages = [                                                                                                                                                                             
        {"role": "system", "content": SYSTEM_PROMPT},                                                                                                                                        
        {"role": "user", "content": prompt}                                                                                                                                                  
    ]                                                                                                                                                                                        
                                                                                                                                                                                                
    max_steps = 5                                                                                                                                                                            
    for step in range(1, max_steps + 1):                                                                                                                                                     
        print(f"\n--- STEP {step} ---")                                                                                                                                                      
                                                                                                                                                                                                
        # Get response from the model                                                                                                                                                        
        response = ollama.chat(                                                                                                                                                              
            model=model_name,                                                                                                                                                                
            messages=messages,                                                                                                                                                               
            options={"temperature": 0.1, "num_ctx": 4096}                                                                                                                                    
        )                                                                                                                                                                                    
                                                                                                                                                                                                
        assistant_content = response['message']['content']                                                                                                                                   
        print(f"[Agent Response]:\n{assistant_content}")                                                                                                                                     
                                                                                                                                                                                                
        # Append response to memory                                                                                                                                                          
        messages.append({"role": "assistant", "content": assistant_content})                                                                                                                 
                                                                                                                                                                                                
        # Check if model provided the final answer                                                                                                                                           
        if "ANSWER:" in assistant_content:                                                                                                                                                   
            print("\nAgent finished successfully!")                                                                                                                                        
            break                                                                                                                                                                            
                                                                                                                                                                                                
        # Parse for tool calls
        action_found = False
        for tag in ["tool_echo", "tool_add"]:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, assistant_content, re.DOTALL)
            if match:
                action_found = True
                args_str = match.group(1).strip()
                print(f"\n[Detected Tool Call]: {tag} with args: {args_str}")

                try:
                    args = json.loads(args_str)
                    observation = execute_mock_tool(tag, args)
                except json.JSONDecodeError:
                    observation = "Error: Invalid JSON inside the tool tag."

                print(f"[System Observation]: {observation}")

                # Feed the observation back to the agent
                messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
                break

        if not action_found:
            # The model replied but did not trigger a tool or output ANSWER
            print("\n[Warning]: Agent did not request a tool or provide ANSWER. Prompting to continue...")
            messages.append({"role": "user", "content": "Please continue. Call a tool or provide your final ANSWER."})

if __name__ == "__main__":
    # This prompt forces the agent to use the mock add tool first, then formulate an answer
    run_agent("Add the numbers 4392 and 8291, then echo 'Addition complete!' using the tools.")