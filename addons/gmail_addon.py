import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from gworkspace.google_auth import onEnable


description = """
Used to read, send, delete, and retrieve emails using the Google Workspace API.
Example input format:
   action="read", max_results=10
   action="send", to="recipient@example.com", subject="Test Email", body="This is a test email.", attachments=["path/to/file1.pdf", "path/to/image.jpg"]
   action="delete", message_id="<message-id>"
   action="retrieve", message_id="<message-id>"
"""

parameters = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The action to perform: 'read', 'send', 'delete', or 'retrieve'.",
            "enum": ["read", "send", "delete", "retrieve"],
        },
        "max_results": {
            "type": "integer",
            "description": "The maximum number of emails to retrieve when reading.",
            "default": 10,
        },
        "to": {
            "type": "string",
            "description": "The recipient's email address when sending an email.",
        },
        "subject": {
            "type": "string",
            "description": "The subject of the email when sending an email.",
        },
        "body": {
            "type": "string",
            "description": "The body of the email when sending an email.",
        },
        "message_id": {
            "type": "string",
            "description": "The ID of the message to delete or retrieve.",
        },
        "attachments": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "A list of file paths to attach to the email when sending an email.",
        },
    },
    "required": ["action"],
}


def gmail_addon(
    action,
    max_results=10,
    to=None,
    subject=None,
    body=None,
    message_id=None,
    username=None,
    attachments=None,
    users_dir="users",
    path=None,
):
    creds = None
    full_path = (
        os.path.join(users_dir, username, "token.json") if path is None else path
    )
    if os.path.exists(full_path):
        creds = Credentials.from_authorized_user_file(full_path, None)
    if not creds or not creds.valid:
        return "Error: Invalid or missing credentials. Please restart the client or run the 'onEnable' function."
    service = build("gmail", "v1", credentials=creds)
    if action == "read":
        try:
            results = (
                service.users()
                .messages()
                .list(userId="me", maxResults=max_results)
                .execute()
            )
            messages = results.get("messages", [])
            result = ""
            for message in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"])
                    .execute()
                )
                payload = msg["payload"]
                headers = payload["headers"]
                subject = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"].lower() == "subject"
                    ),
                    "No Subject",
                )
                sender = next(
                    (header["value"] for header in headers if header["name"] == "From"),
                    "Unknown Sender",
                )
                date = next(
                    (header["value"] for header in headers if header["name"] == "Date"),
                    "Unknown Date",
                )
                snippet = msg["snippet"]
                result += f"Message ID: {message['id']}\nSubject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}\n\n"
            return result
        except Exception as e:
            return f"Error reading emails: {str(e)}"

    elif action == "send":
        try:
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject

            message.attach(MIMEText(body, "plain"))

            if attachments:
                for attachment_path in attachments:
                    converted_path = (
                        attachment_path.replace("/data/", "").replace("data/", "")
                        if attachment_path.startswith("/data/")
                        or attachment_path.startswith("data/")
                        else attachment_path
                    )
                    full_path = os.path.join("users", username, "data", converted_path)
                    with open(full_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(attachment_path)}",
                        )
                        message.attach(part)

            create_message = {
                "raw": base64.urlsafe_b64encode(message.as_bytes()).decode()
            }
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            return f"Email sent. Message ID: {send_message['id']}"
        except Exception as e:
            return f"Error sending email: {str(e)}"

    elif action == "delete":
        try:
            service.users().messages().delete(userId="me", id=message_id).execute()
            return f"Email with ID {message_id} deleted."
        except Exception as e:
            return f"Error deleting email: {str(e)}"

    elif action == "retrieve":
        try:
            message = (
                service.users().messages().get(userId="me", id=message_id).execute()
            )
            payload = message["payload"]
            headers = payload["headers"]
            subject = [
                header["value"] for header in headers if header["name"] == "Subject"
            ][0]
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                        break
            else:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode()
            return f"Subject: {subject}\nBody: {body}"
        except Exception as e:
            return f"Error retrieving email: {str(e)}"

    else:
        return "Invalid action. Please specify 'read', 'send', 'delete', or 'retrieve'."
