import webbrowser
import subprocess
import os

description = "This addon allows you to open a web browser window or any app on the user's PC."

parameters = {
    "type": "object",
    "properties": {
        "url_or_app_path": {
            "type": "string",
            "description": "The URL to open in the web browser or the path to the app to open.",
        },
    },
    "required": ["url_or_app_path"],
}

def open_url_or_app(url_or_app_path):
    try:
        # Try to open the URL or app
        if url_or_app_path.startswith('http://') or url_or_app_path.startswith('https://'):
            webbrowser.open(url_or_app_path)
            return f"Opened {url_or_app_path} in web browser."
        elif os.path.exists(url_or_app_path):
            subprocess.Popen(url_or_app_path)
            return f"Opened {url_or_app_path}."
        else:
            return f"Could not open {url_or_app_path}. Check if the URL or app path is correct."
    except Exception as e:
        return str(e)