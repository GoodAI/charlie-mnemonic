import os
import sys
import traceback
import httpx

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import requests
import schedule
import time
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from bs4 import BeautifulSoup
import os
import asyncio

# Global Variables
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


login_url = "http://localhost:8002/login/"
message_url = "http://localhost:8002/message/"
create_chat_tab_url = "http://localhost:8002/create_chat_tab/"
set_active_tab_url = "http://localhost:8002/set_active_tab/"
delete_data_keep_settings_url = "http://localhost:8002/delete_data_keep_settings/"
delete_data_url = "http://localhost:8002/delete_data/"
login_data = {"username": "admin", "password": "admin"}

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
# Add a global variable to track the last check time
LAST_CHECK = datetime.now(timezone.utc)


def process_email(service, user_id, msg_id, message):
    headers = message["payload"]["headers"]
    details = {
        header["name"].lower(): header["value"]
        for header in headers
        if header["name"].lower() in ["from", "to", "date", "bcc", "cc", "subject"]
    }

    attachments_folder = "attachments"
    if not os.path.exists(attachments_folder):
        os.makedirs(attachments_folder)

    def download_attachment(part):
        if "attachmentId" in part["body"]:
            attachment_id = part["body"]["attachmentId"]
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId=user_id, messageId=msg_id, id=attachment_id)
                .execute()
            )
            file_data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))
            path = os.path.join(attachments_folder, part["filename"])
            with open(path, "wb") as f:
                f.write(file_data)
            return part["filename"]
        return None

    def handle_parts(parts):
        plain_text = ""
        attachments = []
        for part in parts:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                plain_text += base64.urlsafe_b64decode(
                    part["body"]["data"].encode("UTF-8")
                ).decode("UTF-8")
            elif "parts" in part:
                sub_plain_text, sub_attachments = handle_parts(part["parts"])
                plain_text += sub_plain_text
                attachments.extend(sub_attachments)
            elif "filename" in part and part["filename"]:
                attachment = download_attachment(part)
                if attachment:
                    attachments.append(attachment)
        return plain_text, attachments

    payload = message["payload"]
    plain_text = ""
    attachments = []
    if "parts" in payload:
        plain_text, attachments = handle_parts(payload["parts"])
    elif payload["mimeType"] == "text/plain" and "data" in payload["body"]:
        plain_text = base64.urlsafe_b64decode(
            payload["body"]["data"].encode("UTF-8")
        ).decode("UTF-8")

    email_details = {
        "from": details.get("from", ""),
        "to": details.get("to", ""),
        "date": details.get("date", ""),
        "cc": details.get("cc", ""),
        "bcc": details.get("bcc", ""),
        "subject": details.get("subject", ""),
        "plain_text": plain_text,
        "attachments": attachments,
    }

    return email_details


def schedule_email_check():
    service = get_gmail_service()
    schedule.every(1).minutes.do(check_for_new_emails, service=service)
    while True:
        schedule.run_pending()
        time.sleep(1)


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def list_messages_with_labels(service, user_id, label_ids=[], max_results=5):
    try:
        response = (
            service.users()
            .messages()
            .list(userId=user_id, labelIds=label_ids, maxResults=max_results)
            .execute()
        )
        messages = response.get("messages", [])
        for message in messages:
            print(message["id"])
            get_message(service, user_id, message["id"])
    except Exception as error:
        print("An error occurred: %s" % error)


def get_message(service, user_id, msg_id):
    try:
        message = (
            service.users()
            .messages()
            .get(userId=user_id, id=msg_id, format="full")
            .execute()
        )
        return message
    except Exception as error:
        print(f"An error occurred: {error}")


def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}


def send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        print(f'Message Id: {message["id"]}')
    except Exception as error:
        print("An error occurred: %s" % error)


async def create_chat_tab(session, username, chat_id, chat_name):
    tab = {"username": username, "chat_id": chat_id, "chat_name": chat_name}
    response = session.post(create_chat_tab_url, json=tab)
    if response.status_code == 200:
        print(f"Chat tab '{chat_name}' created successfully.")
        response = session.post(
            set_active_tab_url, json={"username": username, "chat_id": chat_id}
        )
        if response.status_code == 200:
            print(f"Chat tab '{chat_name}' set as active.")
        else:
            print(f"Failed to set chat tab '{chat_name}' as active.")
    else:
        print(f"Failed to create chat tab '{chat_name}'.")


async def check_for_new_emails(service, session):
    global LAST_CHECK
    now = datetime.now(timezone.utc)
    query = f"after:{int(LAST_CHECK.timestamp())} -label:SENT"
    try:
        response = service.users().messages().list(userId="me", q=query).execute()
        messages = response.get("messages", [])
        if messages:
            print(f"Found {len(messages)} new emails since {LAST_CHECK.isoformat()}:")
            async with httpx.AsyncClient() as client:
                for message in messages:
                    print(f"\nEmail ID: {message['id']}")
                    full_message = get_message(service, "me", message["id"])
                    email_details = process_email(
                        service, "me", message["id"], full_message
                    )
                    print(f"From: {email_details['from']}")
                    print(f"To: {email_details['to']}")
                    print(f"Date: {email_details['date']}")
                    print(f"CC: {email_details['cc']}")
                    print(f"BCC: {email_details['bcc']}")
                    print(f"Subject: {email_details['subject']}")
                    print(f"Content (Plain Text): {email_details['plain_text']}")
                    print(f"Attachments: {email_details['attachments']}")

                    # Create a chat tab for the email
                    chat_id = f"email_{message['id']}"
                    chat_name = f"Email: {email_details['subject']}"
                    await create_chat_tab(
                        session, login_data.get("username"), chat_id, chat_name
                    )

                    pre_prompt = "This is an automated notification for a new email.\n\n It is your job to notify the user of this email and ask what they would like to do with it.\n\n"

                    # prepare a message to send to the chat tab which contains the email content + headers and attachments
                    message = f"{pre_prompt}\nNew Email\nFrom: {email_details['from']}\nTo: {email_details['to']}\nDate: {email_details['date']}\nCC: {email_details['cc']}\nBCC: {email_details['bcc']}\nSubject: {email_details['subject']}\n\n{email_details['plain_text']}\nAttachments: {email_details['attachments']} and id: {message['id']}\n-End of Email-"

                    # Prepare the data for the API call
                    data = {
                        "prompt": message,
                        "display_name": email_details["from"],
                        "chat_id": chat_id,
                        "username": login_data.get("username"),
                    }
                    response = session.post(message_url, json=data)
                    if response.status_code == 200:
                        print(f"\033[92mMessage '{message}' sent successfully.\033[0m")
                        print("\033[93mResponse:\033[0m", response.json()["content"])
                    else:
                        print("\033[91mFailed to send message.\033[0m")
                        print("Status code:", response.status_code)
                        print("Response:", response.text)
        else:
            print(f"No new emails found since {LAST_CHECK.isoformat()}.")
    except Exception as error:
        print(f"Failed to check for new emails: {error}")
        traceback.print_exc()
    finally:
        LAST_CHECK = now


async def main():
    service = get_gmail_service()
    # Create a session to persist cookies across requests
    session = requests.Session()

    # Login request
    response = session.post(login_url, json=login_data)
    # Check if login was successful
    if response.status_code == 200:
        print("Starting email polling service...")
        while True:
            await check_for_new_emails(service, session)
            await asyncio.sleep(60)
    else:
        print("\033[91mLogin failed.\033[0m")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
