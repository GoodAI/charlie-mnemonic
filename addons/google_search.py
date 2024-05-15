import os
import json
import time
import requests
from functools import wraps
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from gworkspace.google_auth import onEnable, SCOPES
from duckduckgo_search import DDGS

description = """
Used to perform web searches using the Google Custom Search API.
Example input format:
   query="python programming", num_results=10

This will return the search result URLs and snippets for the given query. This does not visit the URLs, be sure to use another addon to do that.
"""

parameters = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "num_results": {
            "type": "integer",
            "description": "The number of search results to return.",
            "default": 10,
        },
    },
    "required": ["query"],
}


def get_google_credentials(username, users_dir):
    creds = None
    full_path = os.path.join(users_dir, username, "token.json")
    if os.path.exists(full_path):
        creds = Credentials.from_authorized_user_file(full_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("No valid credentials available")
    return creds


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
        return f"Error performing DuckDuckGo search: {str(e)}, try again later or use different techniques/addons."


def google_search(query, num_results=10, username=None, users_dir="users"):
    if not query:
        return "No search query provided."

    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not cse_id:
        print("GOOGLE_CSE_ID not set. Falling back to DuckDuckGo search.")
        return search_duckduckgo(query, max_results=num_results, username=username)

    try:
        creds = get_google_credentials(username, users_dir)
        search_url = "https://www.googleapis.com/customsearch/v1"
        headers = {"Authorization": f"Bearer {creds.token}"}
        params = {
            "cx": cse_id,
            "q": query,
            "num": num_results,
        }
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        results = response.json().get("items", [])

        result_text = ""
        for result in results:
            result_text += f"Title: {result['title']}\n"
            result_text += f"URL: {result['link']}\n"
            result_text += f"Snippet: {result['snippet']}\n\n"

        return result_text
    except Exception as e:
        print(f"Google Custom Search error: {e}")
        return f"Error performing Google Custom Search: {str(e)}, try again later or use different techniques/addons."
