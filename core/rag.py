import os
import re
import ollama

def cosine_similarity(v1, v2):
    """Calculates the cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(v1, v2))
    mag1 = sum(x * x for x in v1) ** 0.5
    mag2 = sum(x * x for x in v2) ** 0.5
    if mag1 * mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

class LocalRAG:
    def __init__(self, workspace_dir):
        self.workspace_dir = workspace_dir
        self.chunks = []
        self.index_workspace()

    def chunk_and_add(self, path, text):
        lines = text.split("\n")
        for i in range(0, len(lines), 15):
            chunk = "\n".join(lines[i:i+20]) # Overlap of 5 lines
            self.chunks.append({
                "file": os.path.relpath(path, self.workspace_dir),
                "content": chunk,
                "vector": None
            })

    def index_workspace(self):
        """Indexes all readable files in the project and generates vector embeddings."""
        # 1. Walk filesystem to gather code chunks
        for root, _, files in os.walk(self.workspace_dir):
            if ".venv" in root or ".git" in root:
                continue
            for file in files:
                path = os.path.join(root, file)
                if file.endswith((".py", ".md", ".json", ".txt")):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        self.chunk_and_add(path, text)
                    except:
                        pass
                elif file.endswith(".pdf"):
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(path)
                        text = ""
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        if text.strip():
                            self.chunk_and_add(path, text)
                    except:
                        pass

        # 2. Generate embeddings for all extracted chunks via Ollama
        if self.chunks:
            print(f"[INFO] [RAG] Generating semantic embeddings for {len(self.chunks)} code chunks...")
            for idx, chunk in enumerate(self.chunks, 1):
                try:
                    res = ollama.embeddings(model="nomic-embed-text", prompt=chunk["content"])
                    chunk["vector"] = res["embedding"]
                except Exception as e:
                    # Fallback to zero vector on failures to prevent crashes
                    chunk["vector"] = [0.0] * 768

    def query(self, search_term: str) -> str:
        """Returns the most relevant code chunks matching terms semantically."""
        try:
            res = ollama.embeddings(model="nomic-embed-text", prompt=search_term)
            query_vector = res["embedding"]
        except Exception as e:
            return f"Error generating embedding for query: {str(e)}"

        # Compute cosine similarity for all chunks
        matches = []
        for c in self.chunks:
            if c.get("vector") is not None:
                sim = cosine_similarity(query_vector, c["vector"])
                matches.append((sim, c))

        # Sort matches by similarity score descending
        matches.sort(key=lambda x: x[0], reverse=True)

        # Basic threshold filter to reject entirely unrelated results
        if not matches or matches[0][0] < 0.15:
            return "No matching codebase snippets found."

        output = []
        for score, m in matches[:2]:
            output.append(f"--- File: {m['file']} (Similarity: {score:.3f}) ---\n{m['content']}\n")
        return "\n".join(output)

# Global indexer instance tracker
_rag_indexer = None

def get_rag_indexer(workspace_dir=None):
    global _rag_indexer
    # Force reindexing if workspace path changes
    if _rag_indexer is None or (workspace_dir and os.path.abspath(workspace_dir) != os.path.abspath(_rag_indexer.workspace_dir)):
        if not workspace_dir:
            from core.config import Config
            workspace_dir = Config.WORKSPACE_DIR
        _rag_indexer = LocalRAG(os.path.abspath(workspace_dir))
    return _rag_indexer

def query_workspace_rag(args: dict, permission_callback=None) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    indexer = get_rag_indexer()
    return indexer.query(query)
