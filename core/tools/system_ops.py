import subprocess
from core.config import Config

def run_bash(args: dict, permission_callback=None) -> str:
    cmd = args.get("command", "")
    if not cmd:
        return "Error: No command provided."
        
    # Interactive Permission Gate
    if permission_callback:
        approved = permission_callback("tool_bash", f"Execute shell command: `{cmd}`")
        if not approved:
            return "Error: Permission denied by user."
            
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=Config.WORKSPACE_DIR)
        out = ""
        if res.stdout:
            out += f"STDOUT:\n{res.stdout.strip()}\n"
        if res.stderr:
            out += f"STDERR:\n{res.stderr.strip()}\n"
        return out if out else "Command completed with exit code 0."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (15s limit)."
    except Exception as e:
        return f"Execution error: {str(e)}"
