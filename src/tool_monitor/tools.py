# tools.py
# Tool registry — all callable implementations.
# The harness imports TOOLS and never calls these functions directly.

import os
from typing import Any


def _tool_search(args: dict) -> str:
    from ddgs import DDGS
    query = args.get("query", "").strip()
    if not query:
        return "Error: no query provided."
    
    try:
        # Coerce the generator to a list to ensure actual execution
        results = list(DDGS().text(query, max_results=4))
    except Exception as e:
        return f"Search failed: {e}"
        
    if not results:
        return "No results found."
        
    lines = []
    for r in results:
        lines.append(f"[{r.get('title', 'No Title')}]\n{r.get('body', '')}\nSource: {r.get('href', '')}")
    return "\n\n".join(lines)


def _tool_summarize(args: dict) -> str:
    text = args.get("text", "").strip()
    if not text:
        return "Error: no text provided."
    return text[:4000] if len(text) > 4000 else text


def _tool_file_write(args: dict) -> str:
    path = args.get("path", "").strip()
    content = args.get("content", "")
    if not path:
        return "Error: no path provided."
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Wrote {len(content)} bytes to {path}."


def _tool_http_post(args: dict) -> str:
    import httpx
    url = args.get("url", "").strip()
    payload = args.get("payload", {})
    if not url:
        return "Error: no URL provided."
    response = httpx.post(url, json=payload, timeout=10)
    return f"POST {url} → {response.status_code} ({len(response.content)} bytes)"


TOOLS: dict[str, Any] = {
    "echo":       lambda args: args.get("message", ""),
    "search":     _tool_search,
    "summarize":  _tool_summarize,
    "file_write": _tool_file_write,
    "http_post":  _tool_http_post,
}
