import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


async def onEnable(username, users_dir):
    creds = None
    full_path = os.path.join(users_dir, username, "token.json")
    if os.path.exists(full_path):
        creds = Credentials.from_authorized_user_file(full_path, SCOPES)

    if creds and creds.valid:
        # Check if the existing token has all the required scopes
        missing_scopes = set(SCOPES) - set(creds.scopes)
        if missing_scopes:
            # If there are missing scopes, request a new token with the missing scopes
            creds = None
        else:
            return None  # No need to request a new token

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            CREDENTIALS_PATH = os.getenv("GOOGLE_CLIENT_SECRET_PATH") or ""
            # try to check if the path and file exists
            if os.path.exists(CREDENTIALS_PATH):
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH,
                    SCOPES,
                    redirect_uri="http://localhost:8002/oauth2callback?username="
                    + username,
                )
                auth_uri, _ = flow.authorization_url(include_granted_scopes="true")
                return auth_uri
            else:
                return None

    # Save the updated credentials
    with open(full_path, "w") as token_file:
        token_file.write(creds.to_json())

    return None
