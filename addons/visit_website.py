import requests
from bs4 import BeautifulSoup
import json
import tiktoken

from config import USERS_DIR
from utils import SettingsManager

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


async def visit_website(urls, include_links=True, include_images=False, username=None):
    if not urls:
        return "No URLs provided."
    settings = await SettingsManager.load_settings(USERS_DIR, username)
    max_tokens = settings.get("memory", {}).get("max_tokens", 4096)
    max_tokens_per_site = max_tokens // len(urls)  # Distribute tokens evenly
    print(f"DEBUG: Max tokens per site: {max_tokens_per_site}")
    result = ""
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()

            site_result = f"URL: {url}\n"

            # Process text
            text = " ".join(soup.stripped_strings)
            site_result += "Text: " + text + "\n"

            # Process links if included
            if include_links:
                links = [
                    link.get("href") for link in soup.find_all("a") if link.get("href")
                ]
                site_result += "Links: " + "\n".join(links) + "\n"

            # Process images if included
            if include_images:
                images = [
                    img.get("src") for img in soup.find_all("img") if img.get("src")
                ]
                site_result += "Images: " + "\n".join(images) + "\n"

            # Truncate site_result to max_tokens_per_site
            tokens = enc.encode(site_result)
            if len(tokens) > max_tokens_per_site:
                site_result = enc.decode(tokens[:max_tokens_per_site])

            result += site_result + "\n\n"
        except Exception as e:
            print(f"Visit website error: {e}")
            result += f"Error for URL {url}: {str(e)}\n\n"

    return result
