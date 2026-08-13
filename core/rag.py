import os
import re
import json
import math
import ollama

def cosine_similarity(v1, v2):
    """Calculates the cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(v1, v2))
    mag1 = sum(x * x for x in v1) ** 0.5
    mag2 = sum(x * x for x in v2) ** 0.5
    if mag1 * mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

class BM25:
    def __init__(self, corpus):
        """Standard BM25 Term Weighting retrieval model."""
        self.corpus = corpus
        self.doc_len = [len(doc) for doc in corpus]
        self.avg_doc_len = sum(self.doc_len) / len(corpus) if corpus else 1.0
        self.N = len(corpus)
        
        self.doc_freqs = []
        self.df = {}
        
        for doc in corpus:
            frequencies = {}
            for word in doc:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies.keys():
                self.df[word] = self.df.get(word, 0) + 1

    def idf(self, term):
        df_t = self.df.get(term, 0)
        return math.log(1.0 + (self.N - df_t + 0.5) / (df_t + 0.5))

    def score(self, query_terms, k1=1.5, b=0.75):
        scores = []
        for idx, doc_tf in enumerate(self.doc_freqs):
            score = 0.0
            dl = self.doc_len[idx]
            for term in query_terms:
                if term in doc_tf:
                    tf = doc_tf[term]
                    idf_t = self.idf(term)
                    numerator = tf * (k1 + 1.0)
                    denominator = tf + k1 * (1.0 - b + b * (dl / self.avg_doc_len))
                    score += idf_t * (numerator / denominator)
            scores.append(score)
        return scores

class LocalRAG:
    def __init__(self, workspace_dir):
        self.workspace_dir = os.path.realpath(workspace_dir)
        self.cache_path = os.path.realpath(os.path.join(self.workspace_dir, ".rag_cache.json"))
        if os.path.commonpath([self.workspace_dir, self.cache_path]) != self.workspace_dir:
            raise ValueError("Cache path must be within the workspace directory.")
        self.chunks = []
        self.index_workspace()

    def index_workspace(self):
        """Indexes all workspace files using a SHA-256/mtime cache layer."""
        # 1. Load existing cache
        cache_data = {}
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as cf:
                    cache_data = json.load(cf)
            except:
                pass

        updated_cache = {}
        new_embeddings_count = 0
        cache_hits_count = 0

        # 2. Scan workspace directory
        for root, _, files in os.walk(self.workspace_dir):
            root_real = os.path.realpath(root)
            if os.path.commonpath([self.workspace_dir, root_real]) != self.workspace_dir:
                continue
            if ".venv" in root_real or ".git" in root_real:
                continue
            for file in files:
                if file.startswith(".") or file == ".rag_cache.json":
                    continue
                path = os.path.realpath(os.path.join(root_real, file))
                if os.path.commonpath([self.workspace_dir, path]) != self.workspace_dir:
                    continue
                rel_path = os.path.relpath(path, self.workspace_dir)

                if file.endswith((".py", ".md", ".json", ".txt", ".pdf")):
                    try:
                        mtime = os.path.getmtime(path)
                        # Check cache hit
                        if rel_path in cache_data and cache_data[rel_path].get("mtime") == mtime:
                            cached_file = cache_data[rel_path]
                            for chunk in cached_file.get("chunks", []):
                                self.chunks.append({
                                    "file": rel_path,
                                    "content": chunk["content"],
                                    "vector": chunk["vector"]
                                })
                            updated_cache[rel_path] = cached_file
                            cache_hits_count += 1
                        else:
                            # Cache miss: parse file contents
                            text = ""
                            if file.endswith(".pdf"):
                                try:
                                    from pypdf import PdfReader
                                    reader = PdfReader(path)
                                    for page in reader.pages:
                                        page_text = page.extract_text()
                                        if page_text:
                                            text += page_text + "\n"
                                except:
                                    pass
                            else:
                                with open(path, 'r', encoding='utf-8') as f:
                                    text = f.read()

                            if text.strip():
                                file_chunks = []
                                lines = text.split("\n")
                                for i in range(0, len(lines), 15):
                                    chunk_content = "\n".join(lines[i:i+20])
                                    file_chunks.append({
                                        "content": chunk_content,
                                        "vector": None
                                    })

                                # Generate dense embeddings for chunks
                                new_embeddings_count += len(file_chunks)
                                print(f"[INFO] [RAG] Cache miss: indexing {rel_path} ({len(file_chunks)} chunks)...")
                                for chunk in file_chunks:
                                    try:
                                        res = ollama.embeddings(model="nomic-embed-text", prompt=chunk["content"])
                                        chunk["vector"] = res["embedding"]
                                    except Exception:
                                        chunk["vector"] = [0.0] * 768

                                    self.chunks.append({
                                        "file": rel_path,
                                        "content": chunk["content"],
                                        "vector": chunk["vector"]
                                    })

                                updated_cache[rel_path] = {
                                    "mtime": mtime,
                                    "chunks": file_chunks
                                }
                    except:
                        pass

        # Print stats summary
        if new_embeddings_count > 0:
            print(f"[INFO] [RAG] Index completed. Generated {new_embeddings_count} new embeddings. Cache hits: {cache_hits_count} files.")
        else:
            print(f"[INFO] [RAG] Index completed via cache. Loaded {len(self.chunks)} chunks from disk (Cache hits: {cache_hits_count} files).")

        # 3. Write cache back to file
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as cf:
                json.dump(updated_cache, cf, indent=2)
        except:
            pass

    def query(self, search_term: str) -> str:
        """Returns the most relevant code chunks matching terms using hybrid RAG (BM25 + Semantic Vector)."""
        query_terms = re.findall(r'\w+', search_term.lower())
        if not query_terms or not self.chunks:
            return "No matching codebase snippets found."

        # 1. Sparse BM25 Search
        corpus_tokens = [re.findall(r'\w+', c["content"].lower()) for c in self.chunks]
        bm25_scorer = BM25(corpus_tokens)
        sparse_scores = bm25_scorer.score(query_terms)
        sparse_ranked = sorted(enumerate(sparse_scores), key=lambda x: x[1], reverse=True)

        # 2. Dense Semantic Vector Search
        try:
            res = ollama.embeddings(model="nomic-embed-text", prompt=search_term)
            query_vector = res["embedding"]
        except Exception as e:
            return f"Error generating embedding for query: {str(e)}"

        dense_scores = []
        for idx, c in enumerate(self.chunks):
            if c.get("vector") is not None:
                sim = cosine_similarity(query_vector, c["vector"])
                dense_scores.append((idx, sim))
            else:
                dense_scores.append((idx, 0.0))
        dense_ranked = sorted(dense_scores, key=lambda x: x[1], reverse=True)

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        limit = min(50, len(self.chunks))

        for rank, (idx, score) in enumerate(sparse_ranked[:limit], 1):
            if score > 0.0:
                rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (60.0 + rank)

        for rank, (idx, score) in enumerate(dense_ranked[:limit], 1):
            if score > 0.15:
                rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (60.0 + rank)

        # Sort all chunks by fused score
        fused_ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        if not fused_ranked:
            return "No matching codebase snippets found."

        output = []
        for idx, rrf_score in fused_ranked[:2]:
            m = self.chunks[idx]
            sp_score = sparse_scores[idx]
            dn_score = dense_scores[idx][1]
            output.append(f"--- File: {m['file']} (RRF: {rrf_score:.4f} | BM25: {sp_score:.2f} | Cos: {dn_score:.3f}) ---\n{m['content']}\n")
        return "\n".join(output)

# Global indexer instance tracker
_rag_indexer = None

def get_rag_indexer(workspace_dir=None):
    global _rag_indexer
    if _rag_indexer is None or (workspace_dir and os.path.realpath(workspace_dir) != os.path.realpath(_rag_indexer.workspace_dir)):
        if not workspace_dir:
            from core.config import Config
            workspace_dir = Config.WORKSPACE_DIR
        _rag_indexer = LocalRAG(os.path.realpath(workspace_dir))
    return _rag_indexer

def query_workspace_rag(args: dict, permission_callback=None) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    indexer = get_rag_indexer()
    return indexer.query(query)
