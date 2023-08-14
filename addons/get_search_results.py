import fnmatch
import os
import requests
from utils import config

description = "Returns search results from google or YouTube, or local files on windows (Use exact matches or wildcards (*) or it will not work.). This does not display the content of the websites, only the url and a snippet. This is not your memory! Only use if explicitly asked!"

parameters = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query",
        },
        "youtube": {
            "type": "boolean",
            "default": False,
            "description": "If true, search YouTube instead of Google",
        },
        "local_search": {
            "type": "boolean",
            "default": False,
            "description": "If true, search local files instead of Google or YouTube. Use exact matches or wildcards (*) or it will not work.",
        },
    },
    "required": ["query"],
}

def search_files(query, directory=os.path.expanduser("~")):
    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, f"*{query}*"):
            matches.append(os.path.join(root, filename))
    return matches

def process_youtube_results(response):
    if 'items' not in response:
        return "No results found"
    results = []
    for item in response['items'][:5]:
        if 'videoId' in item['id']:
            result = {
                'title': item['snippet']['title'],
                'link': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                'snippet': item['snippet']['description']
            }
            results.append(result)
    # convert to string
    results = str(results)
    return results

def process_google_results(response):
    if 'items' not in response:
        return "No results found"
    results = []
    for item in response['items'][:5]:
        result = {
            'title': item['title'],
            'link': item['link'],
            'snippet': item['snippet']
        }
        results.append(result)
    # convert to string
    results = str(results)
    return results

def search_youtube(query):
    youtube_api_key = config.YOUTUBE_API_KEY
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q={query}&key={youtube_api_key}"
    response = requests.get(url).json()
    return process_youtube_results(response)

def search_google(query):
    google_api_key = config.GOOGLE_API_KEY
    google_cx = config.GOOGLE_CX
    url = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_cx}&q={query}"
    response = requests.get(url).json()
    return process_google_results(response)

def get_search_results(query, youtube=False, local_search=False):
    if local_search:
        return search_files(query)
    elif youtube:
        return search_youtube(query)
    else:
        return search_google(query)
