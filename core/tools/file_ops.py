import os
from core.config import Config

def is_path_in_workspace(path: str) -> tuple[bool, str]:
    """Helper to verify if a path points inside the workspace directory, resolving all symlinks/relative paths."""
    real_workspace = os.path.realpath(Config.WORKSPACE_DIR)
    resolved_path = os.path.realpath(os.path.join(real_workspace, path))
    is_safe = os.path.commonpath([real_workspace, resolved_path]) == real_workspace
    return is_safe, resolved_path

def read_file(args: dict, permission_callback=None) -> str:
    path = args.get("path", "")
    if not path:
        return "Error: No file path provided."
    
    is_safe, safe_path = is_path_in_workspace(path)
    if not is_safe:
        return "Permission Denied: Path is outside workspace."
        
    try:
        # PDF parsing fallback
        if safe_path.lower().endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(safe_path)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text if text.strip() else "PDF is empty or has no readable text."
            except Exception as pe:
                return f"PDF read error: {str(pe)}"
                
        # Standard text file read
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Read error: {str(e)}"

def write_file(args: dict, permission_callback=None) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
        
    is_safe, safe_path = is_path_in_workspace(path)
    if not is_safe:
        return "Permission Denied: Path is outside workspace."
        
    # Interactive Permission Gate
    if permission_callback:
        approved = permission_callback("tool_write_file", f"Write to file: `{path}`")
        if not approved:
            return "Error: Permission denied by user."
            
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote file to {path}"
    except Exception as e:
        return f"Write error: {str(e)}"

def append_file(args: dict, permission_callback=None) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: No path provided."
        
    is_safe, safe_path = is_path_in_workspace(path)
    if not is_safe:
        return "Permission Denied: Path is outside workspace."
        
    # Interactive Permission Gate
    if permission_callback:
        approved = permission_callback("tool_append_file", f"Append to file: `{path}`")
        if not approved:
            return "Error: Permission denied by user."
            
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
        return f"Successfully appended content to {path}"
    except Exception as e:
        return f"Append error: {str(e)}"
