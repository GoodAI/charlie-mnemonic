import requests
from bs4 import BeautifulSoup
import json

description = """
Used to visit websites and scrape data from them.
Example input format:
   urls=["https://example.com", "https://example.org"], include_links=true, include_images=false
"""

parameters = {
    "type": "object",
    "properties": {
        "urls": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "The URL of the website to visit.",
            },
        },
        "include_links": {
            "type": "boolean",
            "description": "Whether or not to include links in the scraped data.",
            "default": True,
        },
        "include_images": {
            "type": "boolean",
            "description": "Whether or not to include images in the scraped data.",
            "default": False,
        },
    },
    "required": ["urls"],
}


def visit_website(
    urls, include_links=True, include_images=False, max_length=4000, username=None
):
    if not urls:
        return "No URLs provided."

    result = ""
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            text = " ".join(soup.stripped_strings)
            result += f"URL: {url}\n"
            result += "Text: " + text + "\n"
            if include_links:
                links = [
                    link.get("href") for link in soup.find_all("a") if link.get("href")
                ]
                result += "Links: " + "\n".join(links) + "\n"
            if include_images:
                images = [
                    img.get("src") for img in soup.find_all("img") if img.get("src")
                ]
                result += "Images: " + "\n".join(images) + "\n"
            result += "\n"
        except Exception as e:
            print(f"Visit website error: {e}")
            result += f"Error for URL {url}: {str(e)}\n\n"

    return result[:max_length]
