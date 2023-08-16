import os
import requests
from bs4 import BeautifulSoup

PRODUCTION = os.environ['PRODUCTION']

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
      "default": True
    },
    "include_images": {
      "type": "boolean",
      "description": "Whether or not to include images in the scraped data.",
      "default": True
    },
  },
  "required": ["url"],
}


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup

def visit_website(url, include_links=True, include_images=True):
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if PRODUCTION:
          service = Service(ChromeDriverManager().install())
          driver = webdriver.Chrome(service=service, options=options)
        else:
          service = Service(ChromeDriverManager("114.0.5735.90").install())
          driver = webdriver.Chrome(service, options=options)
        driver.get(url)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        for script in soup(["script", "style"]):
            script.decompose()

        data = ''

        text = ' '.join(soup.stripped_strings)
        data += 'Text: ' + text + '\n'

        if include_links:
            links = [link.get('href') for link in soup.find_all('a') if link.get('href')]
            data += 'Links: ' + '\n'.join(links) + '\n'

        if include_images:
            images = [img.get('src') for img in soup.find_all('img') if img.get('src')]
            data += 'Images: ' + '\n'.join(images) + '\n'


        driver.quit()

        return data[:4000]

    except Exception as e:
        return str(e)