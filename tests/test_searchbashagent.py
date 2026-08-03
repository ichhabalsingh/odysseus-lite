import re                                                                                                                                                                                    
import json                                                                                                                                                                                  
import subprocess                                                                                                                                                                            
import ollama                                                                                                                                                                                
from duckduckgo_search import DDGS                                                                                                                                                           
                                                                                                                                                                                                
# --- SYSTEM INSTRUCTIONS ---                                                                                                                                                                
SYSTEM_PROMPT = """You are Odysseus Lite, a terminal assistant.                                                                                                                              
You think step-by-step to solve user commands using Bash and Web Search tools.                                                                                                               
                                                                                                                                                                                                
For every turn, you must output:                                                                                                                                                             
1. THOUGHT: Reason about what you need to do.                                                                                                                                                
2. ACTION: Choose exactly one tool tag to run.                                                                                                                                               
3. OBSERVE: You will receive the output.                                                                                                                                                     
4. ANSWER: Output your final response once the task is finished.                                                                                                                             
                                                                                                                                                                                                
AVAILABLE TOOLS:                                                                                                                                                                             
- <tool_search>{"query": "search term"}</tool_search>                                                                                                                                        
    Use this to find documentation, API usage, or facts on the web.                                                                                                                            
                                                                                                                                                                                                
- <tool_bash>{"command": "shell command"}</tool_bash>                                                                                                                                        
    Use this to run terminal commands, write/modify files, or run scripts.                                                                                                                     
                                                                                                                                                                                                
Rules:                                                                                                                                                                                       
1. Only output ONE tool tag per step.                                                                                                                                                        
2. Ensure the arguments inside the tags are valid JSON.                                                                                                                                      
"""                                                                                                                                                                                          
                                                                                                                                                                                                
# --- TOOL IMPLEMENTATIONS ---                                                                                                                                                               
def web_search(query: str) -> str:                                                                                                                                                           
    """Runs a DuckDuckGo search and formats top results."""                                                                                                                                  
    print(f"   [Executing Web Search]: '{query}'")                                                                                                                                           
    try:                                                                                                                                                                                     
        with DDGS() as ddgs:                                                                                                                                                                 
            results = list(ddgs.text(query, max_results=3))                                                                                                                                  
            if not results:                                                                                                                                                                  
                return "No search results found."                                                                                                                                            
            output = []                                                                                                                                                                      
            for r in results:                                                                                                                                                                
                output.append(f"Title: {r['title']}\nSnippet: {r['body']}\n")                                                                                                                
            return "\n".join(output)                                                                                                                                                         
    except Exception as e:                                                                                                                                                                   
        return f"Search error: {str(e)}"                                                                                                                                                     
                                                                                                                                                                                                
def run_bash(command: str) -> str:                                                                                                                                                           
    """Executes a bash command locally and returns output/errors."""                                                                                                                         
    print(f"   [Executing Bash Command]: '{command}'")                                                                                                                                       
    try:                                                                                                                                                                                     
        # Run command with 10s timeout to prevent hanging                                                                                                                                    
        result = subprocess.run(                                                                                                                                                             
            command,                                                                                                                                                                         
            shell=True,                                                                                                                                                                      
            capture_output=True,                                                                                                                                                             
            text=True,                                                                                                                                                                       
            timeout=10                                                                                                                                                                       
        )                                                                                                                                                                                    
        output = ""                                                                                                                                                                          
        if result.stdout:                                                                                                                                                                    
            output += f"STDOUT:\n{result.stdout}\n"                                                                                                                                          
        if result.stderr:                                                                                                                                                                    
            output += f"STDERR:\n{result.stderr}\n"                                                                                                                                          
        return output if output else "Command completed successfully with no output."                                                                                                        
    except subprocess.TimeoutExpired:                                                                                                                                                        
        return "Error: Command execution timed out (10s limit)."                                                                                                                             
    except Exception as e:                                                                                                                                                                   
        return f"Execution error: {str(e)}"                                                                                                                                                  
                                                                                                                                                                                                
# --- MAIN AGENT LOOP ---                                                                                                                                                                    
def run_agent(prompt: str, model_name="qwen2.5-coder:1.5b-base"):                                                                                                                          
    print(f"User Prompt: {prompt}\n" + "="*60)                                                                                                                                               
                                                                                                                                                                                                
    messages = [                                                                                                                                                                             
        {"role": "system", "content": SYSTEM_PROMPT},                                                                                                                                        
        {"role": "user", "content": prompt}                                                                                                                                                  
    ]                                                                                                                                                                                        
                                                                                                                                                                                                
    for step in range(1, 6):                                                                                                                                                                 
        print(f"\n--- STEP {step} ---")                                                                                                                                                      
                                                                                                                                                                                                
        response = ollama.chat(                                                                                                                                                              
            model=model_name,                                                                                                                                                                
            messages=messages,                                                                                                                                                               
            options={"temperature": 0.1, "num_ctx": 4096}                                                                                                                                    
        )                                                                                                                                                                                    
                                                                                                                                                                                                
        assistant_content = response['message']['content']                                                                                                                                   
        print(f"[Agent Response]:\n{assistant_content}")                                                                                                                                     
        messages.append({"role": "assistant", "content": assistant_content})                                                                                                                 
                                                                                                                                                                                                
        if "ANSWER:" in assistant_content:                                                                                                                                                   
            print("\n✓ Task completed!")                                                                                                                                                     
            break                                                                                                                                                                            
                                                                                                                                                                                                
        # Parse for tool calls                                                                                                                                                               
        action_found = False                                                                                                                                                                 
        
        # Check for Web Search
        search_match = re.search(r"<tool_search>(.*?)</tool_search>", assistant_content, re.DOTALL)
        if search_match:
            action_found = True
            try:
                args = json.loads(search_match.group(1).strip())
                observation = web_search(args.get("query", ""))
            except Exception as e:
                observation = f"JSON Error: {str(e)}"
            messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
            print(f"[System Observation]: {observation[:200]}...") # truncate preview
            
        # Check for Bash Execution
        bash_match = re.search(r"<tool_bash>(.*?)</tool_bash>", assistant_content, re.DOTALL)
        if bash_match and not action_found:
            action_found = True
            try:
                args = json.loads(bash_match.group(1).strip())
                observation = run_bash(args.get("command", ""))
            except Exception as e:
                observation = f"JSON Error: {str(e)}"
            messages.append({"role": "user", "content": f"OBSERVE: {observation}"})
            print(f"[System Observation]:\n{observation}")
            
        if not action_found:
            messages.append({"role": "user", "content": "Please continue. Use a tool or output your final ANSWER."})

if __name__ == "__main__":
    # Test task: Find out the latest stable version of Python and output a directory list using bash
    test_prompt = "Find out what the current year is (search if needed), then write a simple bash command to list the contents of the current folder."
    run_agent(test_prompt)
