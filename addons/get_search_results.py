import fnmatch
import os
import requests
import config

description = "Returns search results from google or YouTube. This does not display the content of the websites, only the url and a snippet. So do a webvisit after using this. This is not your memory! Only use if explicitly asked!"

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
    },
    "required": ["query", "youtube"],
}


def search_files(query, directory=os.path.expanduser("~")):
    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, f"*{query}*"):
            matches.append(os.path.join(root, filename))
    return matches


def process_youtube_results(response):
    if "items" not in response:
        return "No results found"
    results = []
    for item in response["items"][:5]:
        if "videoId" in item["id"]:
            result = {
                "title": item["snippet"]["title"],
                "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "snippet": item["snippet"]["description"],
            }
            results.append(result)
    # convert to string
    results = str(results)
    return results


def process_google_results(response):
    if "items" not in response:
        return "No results found"
    results = []
    for item in response["items"][:5]:
        result = {
            "title": item["title"],
            "link": item["link"],
            "snippet": item["snippet"],
        }
        results.append(result)
    # convert to string
    results = str(results)
    return results


def search_youtube(query):
    youtube_api_key = config.api_keys["youtube"]
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q={query}&key={youtube_api_key}"
    response = requests.get(url).json()
    return process_youtube_results(response)


def search_google(query):
    google_api_key = config.api_keys["google"]
    google_cx = config.api_keys["google_cx"]
    url = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_cx}&q={query}"
    response = requests.get(url).json()
    return process_google_results(response)


def get_search_results(query, youtube=False, username=None):
    if youtube:
        return search_youtube(query)
    else:
        return search_google(query)
