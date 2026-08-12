import logging

logger = logging.getLogger("odysseus.registry")

class ToolRegistry:
    def __init__(self, permission_callback=None):
        self.registry = {}
        # permission_callback: Callable[[str, str], bool]
        # Should return True if approved, False if denied.
        self.permission_callback = permission_callback

    def tool(self, name: str, description: str, usage: str):
        """Decorator to register a python function as an agent tool."""
        def decorator(func):
            self.registry[name] = {
                "func": func,
                "description": description,
                "usage": usage
            }
            return func
        return decorator

    def get_system_instructions(self) -> str:
        """Generates list of tools and formatting rules for the LLM system prompt."""
        instructions = "AVAILABLE TOOLS:\n"
        for name, details in self.registry.items():
            instructions += f"- <{name}>{details['usage']}</{name}>\n  Description: {details['description']}\n\n"
        return instructions

    def get_instructions(self) -> str:
        """Alias for get_system_instructions for web compatibility."""
        return self.get_system_instructions()

    def execute(self, tag: str, args_dict: dict) -> str:
        """Invokes a registered tool by its XML tag name."""
        if tag not in self.registry:
            return f"Error: Tool <{tag}> is not registered."
        try:
            func = self.registry[tag]["func"]
            # Call tool passing the args and the permission callback
            return func(args_dict, self.permission_callback)
        except Exception as e:
            return f"Error executing <{tag}>: {str(e)}"
