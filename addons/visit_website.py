import requests
from bs4 import BeautifulSoup

description = "Used to visit websites"

parameters = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL of the website to visit.",
        },
        "include_links": {
            "type": "boolean",
            "description": "Whether or not to include links in the scraped data.",
            "default": True,
        },
        "include_images": {
            "type": "boolean",
            "description": "Whether or not to include images in the scraped data.",
            "default": True,
        },
    },
    "required": ["url"],
}


def visit_website(
    url, include_links=True, include_images=True, max_length=4000, username=None
):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()

        data = ""

        text = " ".join(soup.stripped_strings)
        data += "Text: " + text + "\n"

        if include_links:
            links = [
                link.get("href") for link in soup.find_all("a") if link.get("href")
            ]
            data += "Links: " + "\n".join(links) + "\n"

        if include_images:
            images = [img.get("src") for img in soup.find_all("img") if img.get("src")]
            data += "Images: " + "\n".join(images) + "\n"

        return data[:max_length]

    except Exception as e:
        print(f"Visit website error: {e}")
        return str(e)
