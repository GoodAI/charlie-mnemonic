import json
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
Manages emails using the Google API.

Examples:
1. List emails or drafts:
   action="list", list_type="draft/email", max_results=10
2. Send email(s):
   action="send", emails=[{"to":"test@test.com", "subject":"Test 1", "body":"Body 1", "attachments":["path/file1.pdf"]}, {"to":"test2@test.com", "subject":"Test 2", "body":"Body 2", "attachments":["path/img.jpg"]}]
3. Save draft(s):
   action="draft", emails=[{"to":"test@test.com", "subject":"Draft 1", "body":"Body 1", "attachments":[]}, {"to":"test2@test.com", "subject":"Draft 2", "body":"Body 2", "attachments":[]}]
4. Send draft(s) by ID:
   action="send_draft", message_id="[<message-ids>]"
5. Delete email:
   action="delete", message_id="<message-id>"
6. Retrieve email:
   action="retrieve", message_id="<message-id>"
7. Update draft(s):
   action="update_draft", drafts=[{"message_id":"<id1>", "to":"to1", "subject":"Subj 1", "body":"Body 1", "attachments":[]}, {"message_id":"<id2>", "to":"to2", "subject":"Subj 2", "body":"Body 2", "attachments":[]}]
"""

parameters = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The action to perform: 'list', 'send', 'delete', or 'retrieve'.",
            "enum": [
                "list",
                "send",
                "delete",
                "retrieve",
                "draft",
                "send_draft",
                "update_draft",
            ],
        },
        "max_results": {
            "type": "integer",
            "description": "The maximum number of emails to retrieve when reading.",
            "default": 10,
        },
        "emails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
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
                    "attachments": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": "A list of file paths to attach to the email when sending an email.",
                    },
                },
                "required": ["to", "subject", "body"],
            },
            "description": "A list of emails to send or save as drafts.",
        },
        "message_id": {
            "type": "string",
            "description": "The ID of the message to delete or retrieve.",
        },
        "list_type": {
            "type": "string",
            "description": "The type of list to retrieve: 'draft' or 'email'.",
            "default": "email",
        },
        "drafts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The ID of the draft to update.",
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
                    "attachments": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": "A list of file paths to attach to the email when sending an email.",
                    },
                },
                "required": ["message_id", "to", "subject", "body"],
            },
            "description": "A list of drafts to update.",
        },
    },
    "required": ["action"],
}


def gmail_addon(
    action,
    max_results=10,
    emails=None,
    message_id=None,
    askconfirm=True,
    username=None,
    attachments=None,
    users_dir="users",
    path=None,
    list_type="email",
    drafts=None,
    draft_ids=None,
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
    
    if action == "list":
        if list_type == "email":
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
                        (
                            header["value"]
                            for header in headers
                            if header["name"] == "From"
                        ),
                        "Unknown Sender",
                    )
                    date = next(
                        (
                            header["value"]
                            for header in headers
                            if header["name"] == "Date"
                        ),
                        "Unknown Date",
                    )
                    snippet = msg["snippet"]
                    result += f"Message ID: {message['id']}\nSubject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}\n\n"
                return result
            except Exception as e:
                return f"Error reading emails: {str(e)}"
        if list_type == "draft":
            try:
                results = (
                    service.users()
                    .drafts()
                    .list(userId="me", maxResults=max_results)
                    .execute()
                )

                drafts = results.get("drafts", [])
                result = ""
                for message in drafts:
                    msg = (
                        service.users()
                        .drafts()
                        .get(userId="me", id=message["id"])
                        .execute()
                    ).get("message", {})

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
                        (
                            header["value"]
                            for header in headers
                            if header["name"] == "From"
                        ),
                        "Unknown Sender",
                    )
                    date = next(
                        (
                            header["value"]
                            for header in headers
                            if header["name"] == "Date"
                        ),
                        "Unknown Date",
                    )
                    snippet = msg["snippet"]
                    result += f"Message ID: {message['id']}\nSubject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}\n\n"
                return result
            except Exception as e:
                return f"Error reading emails: {str(e)}"

    elif action == "draft":
        try:
            results = []
            for email in emails:
                to = email.get("to")
                subject = email.get("subject")
                body = email.get("body")
                attachments = email.get("attachments", [])

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

                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                create_message = {"message": {"raw": raw_message}}
                draft = (
                    service.users()
                    .drafts()
                    .create(userId="me", body=create_message)
                    .execute()
                )

                results.append(f"Email saved as draft. Draft ID: {draft['id']}")
            return results
        except Exception as e:
            return f"Error saving email as draft: {str(e)}"

    elif action == "send":
        try:
            results = []
            for email in emails:
                to = email.get("to")
                subject = email.get("subject")
                body = email.get("body")
                attachments = email.get("attachments", [])

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
                if (
                    askconfirm or askconfirm == "True"
                ):  # llm sometimes puts this as string ¯\_(ツ)_/¯
                    # send as draft and return confirmation message + draft id
                    draft = (
                        service.users()
                        .drafts()
                        .create(userId="me", body={"message": create_message})
                        .execute()
                    )
                    send_confirmation = {
                        "action": "confirm_email",
                        "to": to,
                        "subject": subject,
                        "body": body,
                        "attachments": attachments,
                        "draft_id": draft["id"],
                    }

                    results.append(send_confirmation)
                else:
                    send_message = (
                        service.users()
                        .messages()
                        .send(userId="me", body=create_message)
                        .execute()
                    )
                    results.append(f"Email sent. Message ID: {send_message['id']}")
            return results
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
    
    elif action == "send_draft":
        try:
            if isinstance(message_id, str):
                message_id = [message_id]
            results = []
            for draft_id in message_id:
                draft_message = service.users().drafts().get(userId="me", id=draft_id).execute()
                message = draft_message["message"]
                headers = message["payload"]["headers"]
                
                to = next(header["value"] for header in headers if header["name"].lower() == "to")
                subject = next(header["value"] for header in headers if header["name"].lower() == "subject")
                
                # Initialize body and attachments
                body = ""
                attachments = []
                
                # Check if the message payload has 'parts' or 'body'
                if "parts" in message["payload"]:
                    for part in message["payload"]["parts"]:
                        if part["mimeType"] == "text/plain" and "data" in part["body"]:
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                        elif "filename" in part and part["filename"]:
                            attachments.append(part["filename"])
                elif "body" in message["payload"] and "data" in message["payload"]["body"]:
                    body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode()
                else:
                    return "Error: No 'data' field found in the message payload."
                
                send_confirmation = {
                    "action": "confirm_email",
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "attachments": attachments,
                    "draft_id": draft_id,
                }
                results.append(send_confirmation)
            return results
        except Exception as e:
            return f"Error sending email: {str(e)}"

    elif action == "update_draft":
        try:
            results = []
            for draft in drafts:
                message_id = draft.get("message_id")
                to = draft.get("to")
                subject = draft.get("subject")
                body = draft.get("body")
                attachments = draft.get("attachments", [])

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

                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                create_message = {"message": {"raw": raw_message}}
                draft = (
                    service.users()
                    .drafts()
                    .update(userId="me", id=message_id, body=create_message)
                    .execute()
                )

                results.append(f"Email updated as draft. New draft ID: {draft['id']}")
            return results

        except Exception as e:
            return f"Error updating email as draft: {str(e)}"
    else:
        return "Invalid action. Please specify 'list', 'send', 'delete', 'update' or 'retrieve'."

def create_mime_message_with_attachments(to, subject, body, attachments):
    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    for attachment_path in attachments:
        part = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(attachment_path)}",
        )
        message.attach(part)

    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_email_by_id(message_id, username, message_type="draft", users_dir="users", path=None):
    """
    Sends an email or draft by ID without asking for confirmation.

    Args:
        message_id (str): The ID of the message or draft.
        username (str): The username to identify the token.json file location.
        message_type (str): Type of the message, either 'email' or 'draft'.
        users_dir (str): Directory where user data is stored.
        path (str): Path to the token.json file, if different from the default.

    Returns:
        str: Result message indicating success or failure.
    """
    creds = None
    full_path = (
        os.path.join(users_dir, username, "token.json") if path is None else path
    )
    if os.path.exists(full_path):
        creds = Credentials.from_authorized_user_file(full_path, None)
    if not creds or not creds.valid:
        print("Invalid or missing credentials")
        return "Error: Invalid or missing credentials. Please restart the client or run the 'onEnable' function."
    service = build("gmail", "v1", credentials=creds)

    try:
        if message_type == "email":
            message = service.users().messages().get(userId="me", id=message_id).execute()
        elif message_type == "draft":
            draft = service.users().drafts().get(userId="me", id=message_id).execute()
            message = draft["message"]
        else:
            print("Invalid message type")
            return "Invalid message type. Please specify 'email' or 'draft'."

        headers = message.get("payload", {}).get("headers", [])
        to = next(header["value"] for header in headers if header["name"].lower() == "to")
        subject = next(header["value"] for header in headers if header["name"].lower() == "subject")
        body = ""
        attachments = []

        # Helper function to decode the email body
        def decode_email_body(part):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode()

        if "parts" in message["payload"]:
            for part in message["payload"]["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    body = decode_email_body(part)
                elif part["mimeType"] == "text/html" and "data" in part["body"]:
                    body = decode_email_body(part)
                elif "filename" in part and part["filename"]:
                    attachment_data = part["body"].get("attachmentId")
                    attachment = service.users().messages().attachments().get(userId="me", messageId=message_id, id=attachment_data).execute()
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    file_path = os.path.join("/tmp", part["filename"])
                    with open(file_path, "wb") as f:
                        f.write(file_data)
                    attachments.append(file_path)
        elif "body" in message["payload"] and "data" in message["payload"]["body"]:
            body = decode_email_body(message["payload"])

        if not body:
            print("No email body found")
            return "Error: No email body found."

        mime_message = create_mime_message_with_attachments(to, subject, body, attachments)

        send_message = (
            service.users().messages().send(userId="me", body=mime_message).execute()
        )

        # Delete the draft after sending
        if message_type == "draft":
            service.users().drafts().delete(userId="me", id=message_id).execute()

        # Clean up the temporary attachment files
        for attachment in attachments:
            os.remove(attachment)

        return f"Message sent. Message ID: {send_message['id']}"
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return f"Error sending message: {str(e)}"