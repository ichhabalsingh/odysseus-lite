import ollama
import time

def test_model(model_name: str, prompt: str):
    print(f"\nLoading {model_name}...")
    start_time = time.time()
    
    try:
        # We use the chat API endpoint, which is the standard for tool calling later
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            keep_alive=0 # 0 means "unload immediately after responding"
        )
        
        elapsed = time.time() - start_time
        print(f"Response received in {elapsed:.2f} seconds.")
        print(f"Output: {response['message']['content']}...")
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Ensure Ollama is running and you have run 'ollama pull {model_name}'")

if __name__ == "__main__":
    # Test with a lightweight model that fits easily in 4GB
    print("Starting VRAM test. Keep an eye on your Task Manager/nvtop.")
    test_model("deepseek-r1:1.5b", "Explain how a CPU works in one short paragraph.")