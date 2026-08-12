import re
import json
import ast
from core.config import Config

class AgentSession:
    def __init__(self, goal: str, registry,
                 on_status=None, on_thought=None, on_action=None, 
                 on_observation=None, on_cycle=None, on_answer=None, 
                 on_error=None):
        self.goal = goal
        self.registry = registry
        self.messages = []
        
        # Lifecycle hooks
        self.on_status = on_status or (lambda msg: None)
        self.on_thought = on_thought or (lambda thought: None)
        self.on_action = on_action or (lambda tool, args: None)
        self.on_observation = on_observation or (lambda msg: None)
        self.on_cycle = on_cycle or (lambda msg: None)
        self.on_answer = on_answer or (lambda msg: None)
        self.on_error = on_error or (lambda msg: None)
        
        self.setup_session()

    def setup_session(self):
        system_prompt = f"""You are Odysseus Lite, a terminal workspace assistant.
You think step-by-step and call tools to achieve tasks.

{self.registry.get_system_instructions()}
"""
        self.messages.append({"role": "system", "content": system_prompt})
        self.messages.append({"role": "user", "content": self.goal})

    def repair_broken_xml_tags(self, output_text: str) -> str:
        tags = ["tool_search", "tool_bash", "tool_write_file", "tool_append_file", "tool_read_file", "tool_workspace_rag"]
        repaired_text = output_text
        for tag in tags:
            start_tag = f"<{tag}"
            end_tag = f"</{tag}>"
            if start_tag in repaired_text and end_tag not in repaired_text:
                repaired_text = repaired_text.strip() + end_tag
        return repaired_text

    def parse_action(self, text: str) -> tuple:
        action_text = text
        if "ACTION:" in text:
            action_text = text.split("ACTION:")[-1]
        elif "ACTION" in text:
            action_text = text.split("ACTION")[-1]

        write_match = re.search(r'<tool_write_file\s+path="([^"]+)">([\s\S]*?)</tool_write_file>', action_text)
        if write_match:
            return "tool_write_file", {"path": write_match.group(1), "content": write_match.group(2)}

        append_match = re.search(r'<tool_append_file\s+path="([^"]+)">([\s\S]*?)</tool_append_file>', action_text)
        if append_match:
            return "tool_append_file", {"path": append_match.group(1), "content": append_match.group(2)}

        read_match = re.search(r'<tool_read_file\s+path="([^"]+)"(?:\s*/)?>(?:</tool_read_file>)?', action_text)
        if read_match:
            return "tool_read_file", {"path": read_match.group(1)}

        for tag in self.registry.registry.keys():
            if tag in ["tool_write_file", "tool_append_file"]:
                continue
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, action_text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                if not (content.startswith("{") and content.endswith("}")):
                    if tag in ["tool_workspace_rag", "tool_search"]:
                        return tag, {"query": content}
                    elif tag == "tool_read_file":
                        return tag, {"path": content}
                try:
                    args = json.loads(content)
                    return tag, args
                except json.JSONDecodeError:
                    try:
                        args = ast.literal_eval(content)
                        return tag, args
                    except Exception:
                        return None, f"Error: Invalid JSON/Python dict inside <{tag}>."
        return None, None

    def run_planner(self) -> list:
        self.on_status("Analyzing goal and generating plan...")
        tools_info = self.registry.get_system_instructions()
        prompt = f"""You are the Schema-Driven Planner. Break down the user goal into a sequence of atomic steps.
Each step MUST map directly to one of the available tools below. Do not plan steps that cannot be executed by these tools.

{tools_info}

Output the plan as a JSON object with a single "steps" property containing a list of objects. Each step object MUST contain:
- "tool": The exact tool name from the list.
- "description": The task description for the Executor.

User Goal: {self.goal}
"""
        tool_names = list(self.registry.registry.keys())
        planner_schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "enum": tool_names
                            },
                            "description": {"type": "string"}
                        },
                        "required": ["tool", "description"]
                    }
                }
            },
            "required": ["steps"]
        }
        
        import ollama
        res = ollama.chat(
            model=Config.PLANNER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format=planner_schema
        )
        content = res['message']['content'].strip()
        
        try:
            plan_data = json.loads(content)
            return plan_data.get("steps", [])
        except Exception:
            steps = []
            matches = re.findall(r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*\}', content)
            for tool, desc in matches:
                steps.append({"tool": tool, "description": desc})
            return steps if steps else [{"tool": "tool_read_file", "description": f"Process goal: {self.goal}"}]

    def compact_observation(self, step_desc: str, observation: str) -> str:
        if len(observation) < 500:
            return observation
        self.on_status("State Compactor active: condensing tool observation...")
        prompt = f"""Summarize the key information found in this tool observation for the step "{step_desc}".
Keep it to 1 or 2 sentences max. Focus only on facts, paths, ports, or versions found.

Tool Observation:
{observation[:4000]}
"""
        import ollama
        res = ollama.chat(
            model=Config.EXECUTOR_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        return res['message']['content'].strip()

    def execute_loop(self):
        try:
            steps = self.run_planner()
        except Exception as e:
            self.on_error(f"Planner generation error: {str(e)}")
            return
            
        self.on_status(f"Generated {len(steps)} steps. Initializing execution...")
        steps_display = "\\n".join([f"{i}. [{s.get('tool')}] {s.get('description')}" for i, s in enumerate(steps, 1)])
        self.on_thought(f"Generated Step Plan:\\n{steps_display}")
        
        history_context = ""
        import ollama
        
        for idx, step in enumerate(steps, 1):
            tool_name = step.get("tool", "tool_read_file")
            step_desc = step.get("description", "")
            
            self.on_cycle(f"Step {idx}/{len(steps)}")
            self.on_status(f"Executing: {step_desc} ({tool_name})")
            
            tool_desc = "Custom writing"
            if tool_name in self.registry.registry:
                tool_desc = self.registry.registry[tool_name]['description']
                
            prompt = f"""You are the Executor. Your current target is to run the tool "{tool_name}" to accomplish this goal:
"{step_desc}"

Previous history:
{history_context}

Output a JSON object containing:
- "thought": A detailed explanation of why you are running this tool and choosing the arguments.
- "arguments": A JSON object containing the parameters required by the tool.

Tool Details:
- Name: {tool_name}
- Description: {tool_desc}
"""
            # Define specific arguments schemas based on targeted tool
            args_schema = {"type": "object"}
            if tool_name == "tool_bash":
                args_schema = {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"}
                    },
                    "required": ["command"]
                }
            elif tool_name in ["tool_search", "tool_workspace_rag"]:
                args_schema = {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            elif tool_name == "tool_read_file":
                args_schema = {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            elif tool_name in ["tool_write_file", "tool_append_file"]:
                args_schema = {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }

            executor_schema = {
                "type": "object",
                "properties": {
                    "thought": {"type": "string"},
                    "arguments": args_schema
                },
                "required": ["thought", "arguments"]
            }

            try:
                res = ollama.chat(
                    model=Config.EXECUTOR_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    format=executor_schema,
                    options={
                        "temperature": Config.TEMPERATURE,
                        "num_ctx": Config.NUM_CTX
                    }
                )
            except Exception as e:
                self.on_error(f"Ollama Connection Error: {str(e)}")
                break
                
            response_content = res['message']['content'].strip()
            
            try:
                executor_data = json.loads(response_content)
                thought = executor_data.get("thought", "")
                args = executor_data.get("arguments", {})
                tag = tool_name
            except Exception as parse_err:
                self.on_error(f"Failed to parse executor output JSON: {str(parse_err)}")
                thought = "Error parsing executor thought."
                tag = tool_name
                args = {"path": step_desc}
            
            if thought:
                self.on_thought(thought)
                
            self.on_action(tag, f"<{tag}> {args}")
            
            observation = self.registry.execute(tag, args)
            self.on_observation(f"Ran tool <{tag}>: {observation[:200]}...")
            
            compact_obs = self.compact_observation(step_desc, observation)
            if len(observation) >= 500:
                self.on_thought(f"[State Compactor] Condensation:\\n{compact_obs}")
                
            history_context += f"Step: {step_desc}\nAction: <{tag}> {args}\nResult: {compact_obs}\n\n"
            
        self.on_status("Goal achieved successfully.")
        self.on_answer(history_context)
