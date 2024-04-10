# Example code for the Charlie API calls


import requests
import json

login_url = "http://localhost:8002/login/"
message_url = "http://localhost:8002/message/"
create_chat_tab_url = "http://localhost:8002/create_chat_tab/"
set_active_tab_url = "http://localhost:8002/set_active_tab/"
delete_data_keep_settings_url = "http://localhost:8002/delete_data_keep_settings/"
delete_data_url = "http://localhost:8002/delete_data/"
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

# Create chat tabs
chat_tabs = [
    {"username": "admin", "chat_id": "cats", "chat_name": "Cats Conversation"},
    {"username": "admin", "chat_id": "smalltalk", "chat_name": "Small Talk"},
]

for tab in chat_tabs:
    response = session.post(create_chat_tab_url, json=tab)
    if response.status_code == 200:
        print(f"\033[92mChat tab '{tab['chat_name']}' created successfully.\033[0m")
    else:
        print(f"\033[91mFailed to create chat tab '{tab['chat_name']}'.\033[0m")
        print("Status code:", response.status_code)
        print("Response:", response.text)

# Conversation in the "cats" tab
cats_messages = ["Name me 2 cat breeds", "2 more"]

print("\n\033[94mConversation in the 'cats' tab:\033[0m")
# Set "cats" tab as active
response = session.post(
    set_active_tab_url, json={"username": "admin", "chat_id": "cats"}
)
if response.status_code == 200:
    print("\033[92mActive tab set to 'cats'.\033[0m")
else:
    print("\033[91mFailed to set active tab to 'cats'.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)

for message in cats_messages:
    message_data = {
        "prompt": message,
        "display_name": "Joe",
        "chat_id": "cats",
        "username": "admin",
    }
    response = session.post(message_url, json=message_data)
    if response.status_code == 200:
        print(f"\033[92mMessage '{message}' sent successfully.\033[0m")
        print("\033[93mResponse:\033[0m", response.json()["content"])
    else:
        print("\033[91mFailed to send message.\033[0m")
        print("Status code:", response.status_code)
        print("Response:", response.text)

# Conversation in the "smalltalk" tab
smalltalk_messages = [
    "Hi there!",
    "What was my first message to you?",
]

print("\n\033[94mConversation in the 'smalltalk' tab:\033[0m")
# Set "smalltalk" tab as active
response = session.post(
    set_active_tab_url, json={"username": "admin", "chat_id": "smalltalk"}
)
if response.status_code == 200:
    print("\033[92mActive tab set to 'smalltalk'.\033[0m")
else:
    print("\033[91mFailed to set active tab to 'smalltalk'.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)

for message in smalltalk_messages:
    message_data = {
        "prompt": message,
        "display_name": "Joe",
        "chat_id": "smalltalk",
        "username": "admin",
    }
    response = session.post(message_url, json=message_data)
    if response.status_code == 200:
        print(f"\033[92mMessage '{message}' sent successfully.\033[0m")
        print("\033[93mResponse:\033[0m", response.json()["content"])
    else:
        print("\033[91mFailed to send message.\033[0m")
        print("Status code:", response.status_code)
        print("Response:", response.text)

# Delete user data while keeping settings
print("\n\033[94mDeleting user data while keeping settings:\033[0m")
response = session.post(delete_data_keep_settings_url)
if response.status_code == 200:
    print("\033[92mUser data deleted successfully while keeping settings.\033[0m")
else:
    print("\033[91mFailed to delete user data while keeping settings.\033[0m")
    print("Status code:", response.status_code)
    print("Response:", response.text)

# Or use the following to delete all user data
# Delete all user data
# print("\n\033[94mDeleting all user data:\033[0m")
# response = session.post(delete_data_url)
# if response.status_code == 200:
#     print("\033[92mAll user data deleted successfully.\033[0m")
# else:
#     print("\033[91mFailed to delete all user data.\033[0m")
#     print("Status code:", response.status_code)
#     print("Response:", response.text)
