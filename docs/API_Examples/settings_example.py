import requests
import json

login_url = "http://localhost:8002/login/"
load_settings_url = "http://localhost:8002/load_settings/"
update_settings_url = "http://localhost:8002/update_settings/"
login_data = {"username": "admin", "password": "admin"}

# Create a session to persist cookies across requests
session = requests.Session()

# Login request
response = session.post(login_url, json=login_data)

# Check if login was successful
if response.status_code == 200:
    print("\033[92mLogin successful.\033[0m")
    # Extract the session token and username from the response cookies
    session_token = response.cookies.get("session_token")
    username = response.cookies.get("username")
    # Set the session token and username cookies in the session object
    session.cookies.set("session_token", session_token)
    session.cookies.set("username", username)
else:
    print("\033[91mLogin failed.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)
    exit(1)

# Load settings
print("\n\033[94mLoading settings:\033[0m")
response = session.post(load_settings_url)
if response.status_code == 200:
    settings = response.json()
    print("\033[92mSettings loaded successfully.\033[0m")
    print("Settings:", json.dumps(settings, indent=2))
else:
    print("\033[91mFailed to load settings.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)
    exit(1)

# Update settings - Enable/disable addons
print("\n\033[94mUpdating settings - Enable/disable addons:\033[0m")
update_data = {
    "username": "admin",
    "category": "addons",
    "setting": {
        "generate_image": True,
        "search_duckduckgo": False,
        "visit_website": True,
        "run_python_code": False,
    },
}
response = session.post(update_settings_url, json=update_data)
if response.status_code == 200:
    updated_settings = response.json()
    print("\033[92mSettings updated successfully.\033[0m")
    print(
        "Updated settings (addons category):",
        json.dumps(updated_settings["addons"], indent=2),
    )
else:
    print("\033[91mFailed to update settings.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)

# Update settings - Modify memory token values
print("\n\033[94mUpdating settings - Modify memory token values:\033[0m")
update_data = {
    "username": "admin",
    "category": "memory",
    "setting": {
        "functions": 800,
        "ltm1": 1500,
        "ltm2": 1200,
        "episodic": 500,
        "recent": 1000,
        "notes": 1300,
        "input": 1200,
        "output": 1200,
        "max_tokens": 8000,
        "min_tokens": 700,
    },
}
response = session.post(update_settings_url, json=update_data)
if response.status_code == 200:
    updated_settings = response.json()
    print("\033[92mSettings updated successfully.\033[0m")
    print(
        "Updated settings (memory category):",
        json.dumps(updated_settings["memory"], indent=2),
    )
else:
    print("\033[91mFailed to update settings.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)
