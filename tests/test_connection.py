import ollama
import time

def test_connection(model_name="digitsflow/bonsai-8b:latest"):
    print(f"Testing connection to Ollama using model '{model_name}'...")
    start_time = time.time()
    
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': 'Say "Hello, Odysseus is online!"'}],
            options={"temperature": 0.0}
        )
        elapsed = time.time() - start_time
        print(f"Success! Response received in {elapsed:.2f} seconds.")
        print(f"Response: {response['message']['content'].strip()}")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Ensure Ollama is running (`ollama serve`) and that you have pulled the model.")

if __name__ == "__main__":
    test_connection()
