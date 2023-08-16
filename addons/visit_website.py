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
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def visit_website(url, include_links=True, include_images=True):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        if PRODUCTION:
          driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        else:
          driver = webdriver.Chrome(ChromeDriverManager("114.0.5735.90").install(), options=options)
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