from duckduckgo_search import DDGS
import json

description = """
Used to perform web searches using the DuckDuckGo search engine.
Example input format:
   query="python programming", region="wt-wt", safesearch="moderate", timelimit="d", max_results=10

   wt-wt = No region (default)
"""

parameters = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "region": {
            "type": "string",
            "description": "The region for the search (e.g., us-en, uk-en, ru-ru).",
            "default": "wt-wt",
        },
        "safesearch": {
            "type": "string",
            "description": "The safe search setting (on, moderate, off).",
            "default": "moderate",
        },
        "timelimit": {
            "type": "string",
            "description": "The time limit for the search (d, w, m, y).",
            "default": None,
        },
        "max_results": {
            "type": "integer",
            "description": "The maximum number of search results to return.",
            "default": None,
        },
    },
    "required": ["query"],
}


def search_duckduckgo(
    query,
    region="wt-wt",
    safesearch="moderate",
    timelimit=None,
    max_results=None,
    username=None,
):
    if not query:
        return "No search query provided."

    try:
        ddgs = DDGS()
        results = ddgs.text(
            keywords=query,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            max_results=max_results,
        )
        result_text = ""
        for result in results:
            result_text += f"Title: {result['title']}\n"
            result_text += f"URL: {result['href']}\n"
            result_text += f"Snippet: {result['body']}\n\n"
        return result_text
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return f"Error performing DuckDuckGo search: {str(e)}"
