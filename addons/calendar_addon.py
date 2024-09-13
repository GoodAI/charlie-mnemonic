import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
from gworkspace.google_auth import onEnable
from utils import convert_username

description = """
Used to create, read, update, and delete events using the Google Calendar API. You can create new events with Google Meet links, list events to get the event IDs and details and then use the ID to update existing events, and/or delete events.
Example input format:
   action="list", max_results=10, time_min="2023-05-01T00:00:00Z", time_max="2023-05-31T23:59:59Z"
   action="create", summary="Meeting", description="Team meeting", start_time="2023-05-15T10:00:00", end_time="2023-05-15T11:00:00", attendees=["attendee1@example.com", "attendee2@example.com"], timezone="Europe/Brussels", create_meet_link=True
   action="update", event_id="<event-id>", summary="Updated Meeting", description="Updated team meeting, please review changes", start_time="2023-05-15T10:30:00", end_time="2023-05-15T11:30:00", attendees=["antony.alloin@goodai.com", "more@emails.com"]
   action="delete", event_id="<event-id>"
"""

parameters = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The action to perform: 'list', 'create', 'update', or 'delete'.",
            "enum": ["list", "create", "update", "delete"],
        },
        "max_results": {
            "type": "integer",
            "description": "The maximum number of events to retrieve when listing.",
            "default": 10,
        },
        "time_min": {
            "type": "string",
            "description": "The start of the time range for listing events (ISO 8601 format).",
        },
        "time_max": {
            "type": "string",
            "description": "The end of the time range for listing events (ISO 8601 format).",
        },
        "summary": {
            "type": "string",
            "description": "The summary or title of the event.",
        },
        "description": {
            "type": "string",
            "description": "The description or details of the event.",
        },
        "start_time": {
            "type": "string",
            "description": "The start time of the event (ISO 8601 format).",
        },
        "end_time": {
            "type": "string",
            "description": "The end time of the event (ISO 8601 format).",
        },
        "attendees": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "A list of email addresses of the attendees.",
        },
        "event_id": {
            "type": "string",
            "description": "The ID of the event to update or delete.",
        },
        "timezone": {
            "type": "string",
            "description": "The timezone for the start and end times of the event (e.g., 'America/New_York').",
        },
        "include_working_locations": {
            "type": "boolean",
            "description": "Whether to include working locations in the response.",
            "default": False,
        },
        "create_meet_link": {
            "type": "boolean",
            "description": "Whether to create a Google Meet link for the event.",
            "default": True,
        },
    },
    "required": ["action"],
}

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


async def calendar_addon(
    action,
    max_results=10,
    time_min=None,
    time_max=None,
    summary=None,
    description=None,
    start_time=None,
    end_time=None,
    attendees=None,
    event_id=None,
    username=None,
    users_dir="users",
    path=None,
    timezone=None,
    include_working_locations=False,
    create_meet_link=True,
):
    username = convert_username(username)
    creds = None
    full_path = (
        os.path.join(users_dir, username, "token.json") if path is None else path
    )

    if os.path.exists(full_path):
        creds = Credentials.from_authorized_user_file(
            full_path, ["https://www.googleapis.com/auth/calendar"]
        )

    if not creds or not creds.valid:
        print(f"Cal Credentials are invalid for {username}")  # Debug print
        if creds and creds.expired and creds.refresh_token:
            print(f"Cal Credentials are expired for {username}")  # Debug print
            try:
                creds.refresh(Request())
                # Save the refreshed credentials
                with open(full_path, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                return f"Error refreshing credentials: {str(e)}. Please run the 'onEnable' function."
        else:
            return "Credentials are missing or invalid. Please run the 'onEnable' function."

    # Check if the required scope is present
    if "https://www.googleapis.com/auth/calendar" not in creds.scopes:
        return "Calendar scope is missing. Please run the 'onEnable' function to grant the necessary permissions."

    try:
        service = build("calendar", "v3", credentials=creds)

        if action == "list":
            now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min or now,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            result = ""
            event_count = 0
            for event in events:
                event_id = event["id"]
                if include_working_locations or "_" not in event_id:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))
                    location = event.get("location", "No location specified")
                    attendees = event.get("attendees", [])
                    attendee_list = ", ".join(
                        [attendee.get("email", "") for attendee in attendees]
                    )
                    google_meet_link = event.get("hangoutLink", "No Google Meet link")
                    result += f"Event ID: {event['id']}\nSummary: {event['summary']}\nDescription: {event.get('description', 'No description')}\nStart: {start}\nEnd: {end}\nLocation: {location}\nAttendees: {attendee_list}\nGoogle Meet Link: {google_meet_link}\n\n"
                    event_count += 1
                    if event_count == max_results:
                        break
            if not result:
                return "No events found."
            return result

        elif action == "create":
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone,
                },
                "attendees": (
                    [{"email": attendee} for attendee in attendees] if attendees else []
                ),
            }
            if create_meet_link:
                event["conferenceData"] = {
                    "createRequest": {"requestId": f"{event_id}_hangoutsMeet"}
                }
                event = (
                    service.events()
                    .insert(calendarId="primary", body=event, conferenceDataVersion=1)
                    .execute()
                )
                return f"Event created. Event ID: {event['id']}\nGoogle Meet Link: {event['hangoutLink']}"
            else:
                event = (
                    service.events().insert(calendarId="primary", body=event).execute()
                )
                return f"Event created. Event ID: {event['id']}"

        elif action == "update":
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )
            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if start_time:
                event["start"] = {
                    "dateTime": start_time,
                    "timeZone": timezone,
                }
            if end_time:
                event["end"] = {
                    "dateTime": end_time,
                    "timeZone": timezone,
                }
            if attendees:
                event["attendees"] = (
                    [{"email": attendee} for attendee in attendees] if attendees else []
                )
            updated_event = (
                service.events()
                .update(calendarId="primary", eventId=event_id, body=event)
                .execute()
            )
            return f"Event updated. Event ID: {updated_event['id']}"

        elif action == "delete":
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return f"Event with ID {event_id} deleted."

        else:
            return "Invalid action. Please specify 'list', 'create', 'update', or 'delete'."

    except HttpError as error:
        return f"An error occurred: {error}"
