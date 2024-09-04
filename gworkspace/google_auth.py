import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.exceptions
from config import origins, PRODUCTION
from utils import convert_username
import secrets
import json

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/cse",
]

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/cse",
]


async def onEnable(username, users_dir):
    creds = None
    username = convert_username(username)
    charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
    full_path = os.path.join(charlie_mnemonic_user_dir, username, "token.json")
    print(f"checking for token at {full_path} for {username}")  # Debug print

    if os.path.exists(full_path):
        print(f"Token exists at {full_path} for {username}")  # Debug print
        try:
            print(f"Reading credentials from {full_path}")  # Debug print
            creds = Credentials.from_authorized_user_file(full_path, SCOPES)
        except ValueError as e:
            print(f"Error reading credentials from {full_path}: {e}")
            creds = None

    if creds and creds.valid:
        print(f"Credentials are valid for {username}")  # Debug print
        missing_scopes = set(SCOPES) - set(creds.scopes)
        if missing_scopes:
            print(f"Missing scopes: {missing_scopes}")  # Debug print
            creds = None
        else:
            return None

    if not creds or not creds.valid:
        print(f"Credentials are invalid for {username}")  # Debug print
        if creds and creds.expired and creds.refresh_token:
            print(f"Credentials are expired for {username}")  # Debug print
            try:
                print(f"Refreshing credentials for {username}")  # Debug print
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError as e:
                print(f"Refresh error: {e}. Deleting token and re-authorizing.")
                os.remove(full_path)
                return await onEnable(username, users_dir)
        else:
            CREDENTIALS_PATH = os.getenv("GOOGLE_CLIENT_SECRET_PATH") or ""
            if os.path.exists(CREDENTIALS_PATH):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_PATH,
                        SCOPES,
                        redirect_uri=get_redirect_uri(),
                    )
                    state = secrets.token_urlsafe(16)
                    store_state(state, username)
                    auth_uri, _ = flow.authorization_url(
                        include_granted_scopes="true",
                        state=state,
                        access_type="offline",
                        prompt="consent",
                    )
                    return {"auth_uri": auth_uri}
                except ValueError as e:
                    return {"error": str(e)}
            else:
                return {"error": "Google client secret path not found"}

    # Save the refreshed or new credentials
    with open(full_path, "w") as token:
        token.write(creds.to_json())

    return None


def get_state_file_path():
    return os.path.join(os.getcwd(), "users", "state_store.json")


def store_state(state, username):
    file_path = get_state_file_path()

    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # If the file doesn't exist, create it with an empty JSON object
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump({}, f)

    # Now open the file in read-write mode
    with open(file_path, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
        data[state] = username
        f.seek(0)
        json.dump(data, f)
        f.truncate()


def get_username_from_state(state):
    file_path = get_state_file_path()
    print(f"State file path: {file_path}")  # Debug print
    if not os.path.exists(file_path):
        print("State file does not exist")  # Debug print
        return None
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
            username = data.get(state)
            print(f"State data: {data}")  # Debug print
            print(f"Retrieved username for state {state}: {username}")  # Debug print
            return username
        except json.JSONDecodeError:
            print("Failed to decode JSON in state file")  # Debug print
            return None


def get_redirect_uri():
    origin_url = origins()
    if PRODUCTION:
        return f"https://{origin_url}/oauth2callback?"
    else:
        return f"http://localhost:8002/oauth2callback?"
