from duckduckgo_search import DDGS

def web_search(args: dict, permission_callback=None) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: No search query provided."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No search results found."
            return "\n".join([f"Source: {r['href']}\nSnippet: {r['body']}\n" for r in results])
    except Exception as e:
        return f"Search failed: {str(e)}"
