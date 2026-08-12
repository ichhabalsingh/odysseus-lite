import os

class Config:
    PLANNER_MODEL = "deepseek-r1:1.5b"
    EXECUTOR_MODEL = "qwen2.5-coder:1.5b"
    NUM_CTX = 8192                       # High context window
    TEMPERATURE = 0.1                    # Deterministic tool execution
    WORKSPACE_DIR = os.getcwd()          # Target workspace directory
    KEEP_ALIVE = "10m"                   # Grace period to prevent VRAM swapping
