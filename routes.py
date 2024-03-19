import json
import os
import shutil
import signal
import tempfile
import urllib.parse
import zipfile
from datetime import datetime
from typing import Optional
import llmcalls

import logs
from fastapi import (
    APIRouter,
    HTTPException,
    File,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    Form,
    Depends,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
    JSONResponse,
)
from fastapi.security import HTTPBearer
from fastapi.security.api_key import APIKeyCookie
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.oauth2 import id_token

from authentication import Authentication
from chat_tabs.dao import ChatTabsDAO
from classes import (
    UserName,
    editSettings,
    userMessage,
    noTokenMessage,
    UserGoogle,
    generateAudioMessage,
    regenerateMessage,
)
from database import Database
from memory import (
    export_memory_to_file,
    import_file_to_memory,
    get_last_message,
)
from simple_utils import get_root, convert_name
from user_management.dao import UsersDAO, AdminControlsDAO
from user_management.routes import set_login_cookies
from utils import (
    process_message,
    AudioProcessor,
    AddonManager,
    SettingsManager,
    BrainProcessor,
    MessageParser,
)

logger = logs.Log("routes", "routes.log").get_logger()

from config import (
    api_keys,
    STATIC,
    LOGIN_REQUIRED,
    PRODUCTION,
    ADMIN_REQUIRED,
    USERS_DIR,
)

router = APIRouter()
templates = Jinja2Templates(directory=get_root(STATIC))

connections = {}


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    version = SettingsManager.get_version()
    with AdminControlsDAO() as db:
        daily_limit = db.get_daily_limit()
        template_name = (
            "maintenance.html" if db.get_maintenance_mode() else "index.html"
        )
    context = {
        "request": request,
        "version": version,
        "daily_limit": daily_limit,
        "production": PRODUCTION,
    }

    return templates.TemplateResponse(template_name, context)


@router.get("/styles.css")
async def read_root():
    try:
        return FileResponse("static/styles.css")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


async def send_debug_message(username: str, message: str):
    connection = connections.get(username)
    # logger.info(f"connection length: {len(connections)}")
    if connection:
        try:
            await connection.send_text(message)
        except Exception as e:
            logger.error(
                f"An error occurred when sending a message to user {username}: {e}"
            )
    else:
        logger.error(f"No active websocket connection for user {username}")


@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Send a response back to the client
                await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        # Handle client disconnection
        if username in connections:
            del connections[username]
        logger.debug(f"User {username} disconnected")
    except ConnectionResetError:
        # Handle client disconnection
        del connections[username]
        logger.debug(f"User {username} disconnected")
    except Exception as e:
        # Handle any other exceptions
        del connections[username]
        logger.error(f"An error occurred with user {username}: {e}")


# load settings route
@router.post(
    "/load_settings/",
    tags=["Settings", LOGIN_REQUIRED],
    summary="Load settings",
    description="This endpoint allows you to load the user's settings by providing a username and session token. If the token is valid, the settings will be returned. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the user's settings if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Settings loaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Settings loaded successfully",
                        "settings": {"category": {"setting": "value"}},
                    }
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_get_settings(request: Request):
    username = request.state.user.username
    await AddonManager.load_addons(username, USERS_DIR)
    with open(os.path.join(USERS_DIR, username, "settings.json"), "r") as f:
        settings = json.load(f)
    logger.debug(f"Loaded settings for user {username}")
    logger.debug(settings)
    total_tokens_used, total_cost = 0, 0
    with Database() as db, UsersDAO() as dao:
        total_tokens_used, total_cost = db.get_token_usage(username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(username, True)
        display_name = dao.get_display_name(username)
    settings["usage"] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    settings["daily_usage"] = {"daily_cost": total_daily_cost}
    settings["display_name"] = display_name
    return settings


def count_tokens(message):
    return MessageParser.num_tokens_from_string(message)


# update settings route
@router.post(
    "/update_settings/",
    tags=["Settings", LOGIN_REQUIRED],
    summary="Update settings",
    description="This endpoint allows you to update the user's settings by providing a username, session token, category, setting, and value. If the token is valid, the settings will be updated. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the user's updated settings if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Settings updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Settings updated successfully",
                        "settings": {"category": {"setting": "value"}},
                    }
                }
            },
        },
        400: {
            "description": "Category or setting not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category or setting not found"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_update_settings(request: Request, user: editSettings):
    username = request.state.user.username
    # create the directory if it doesn't exist
    user_dir = os.path.join(USERS_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    # check if the settings file exists
    settings_file = os.path.join(user_dir, "settings.json")
    if not os.path.exists(settings_file):
        # create the settings file
        with open(settings_file, "w") as f:
            json.dump({}, f)
    with open(settings_file, "r") as f:
        settings = json.load(f)
    if user.category in settings:
        if isinstance(user.setting, dict):
            # iterate over the dictionary
            for key, value in user.setting.items():
                # update the settings
                settings[user.category][key] = value
        elif user.setting in settings[user.category]:
            if str(user.value).lower() == "true":
                settings[user.category][user.setting] = True
            elif str(user.value).lower() == "false":
                settings[user.category][user.setting] = False
            elif user.value.isdigit():
                settings[user.category][user.setting] = int(user.value)
            else:
                settings[user.category][user.setting] = user.value
        else:
            raise HTTPException(status_code=400, detail="Setting not found")
    elif user.category == "db":
        with UsersDAO() as db:
            if user.setting == "display_name":
                db.update_display_name(username, user.value)
            else:
                raise HTTPException(status_code=400, detail="Setting not found")
    else:
        raise HTTPException(status_code=400, detail="Category not found")
    with open(settings_file, "w") as f:
        json.dump(settings, f)
    with Database() as db, UsersDAO() as dao:
        total_tokens_used, total_cost = db.get_token_usage(username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(username, True)
        display_name = dao.get_display_name(username)
    settings["usage"] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    settings["daily_usage"] = {"daily_cost": total_daily_cost}
    settings["display_name"] = display_name
    return settings


# openAI response route
@router.post(
    "/message/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Send a message to the AI",
    description="This endpoint allows you to send a message to the AI by providing a username, session token, and prompt. If the token is valid, the AI will respond to the prompt. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the AI's response if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "AI responded successfully",
            "content": {
                "application/json": {
                    "example": {"message": "AI responded successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_message(request: Request, message: userMessage):
    user = request.state.user
    settings = await SettingsManager.load_settings(USERS_DIR, user.username)
    if count_tokens(message.prompt) > settings["memory"]["input"]:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    (
        total_tokens_used,
        total_cost,
        daily_limit,
        total_daily_tokens_used,
        total_daily_cost,
        display_name,
    ) = (0, 0, 0, 0, 0, "")
    with Database() as db, UsersDAO() as dao, ChatTabsDAO() as chat_tabs_dao, AdminControlsDAO() as admin_controls_dao:
        total_tokens_used, total_cost = db.get_token_usage(user.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            user.username, True
        )
        display_name = dao.get_display_name(user.username)
        daily_limit = admin_controls_dao.get_daily_limit()
        has_access = dao.get_user_access(user.username)
        user_id = dao.get_user_id(user.username)
        tab_data = chat_tabs_dao.get_tab_data(user_id)
        active_tab_data = chat_tabs_dao.get_active_tab_data(user_id)
        # if no active tab, set chat_id to 0
        if message.chat_id is None and active_tab_data is None:
            message.chat_id = "0"
            # put the data in the database
            chat_tabs_dao.insert_tab_data(
                user_id, message.chat_id, "new chat", message.chat_id, True
            )
        # if there is an active tab, set chat_id to the active tab's chat_id
        else:
            chat_tabs_dao.update_created_at(user_id, message.chat_id)
            message.chat_id = active_tab_data.chat_id
    if not has_access or has_access == "false" or has_access == "False":
        logger.info(f"user {user.username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    if total_daily_cost >= daily_limit:
        logger.info(f"user {user.username} reached daily limit")
        raise HTTPException(
            status_code=400,
            detail="You reached your daily limit. Please wait until tomorrow to continue using the service.",
        )
    return await process_message(
        message.prompt,
        user.username,
        USERS_DIR,
        message.display_name,
        chat_id=message.chat_id,
    )


@router.post("/regenerate_response/", tags=[LOGIN_REQUIRED])
async def regenerate_response(request: Request, message: regenerateMessage):
    user = request.state.user
    settings = await SettingsManager.load_settings(USERS_DIR, user.username)

    (
        total_tokens_used,
        total_cost,
        daily_limit,
        total_daily_tokens_used,
        total_daily_cost,
        display_name,
    ) = (0, 0, 0, 0, 0, "")
    print(
        f"getting user data for {user.username} to regenerate response with uuid {message.uuid} and chat_id {message.chat_id}"
    )
    with Database() as db, UsersDAO() as dao, ChatTabsDAO() as chat_tabs_dao, AdminControlsDAO() as admin_controls_dao:
        total_tokens_used, total_cost = db.get_token_usage(user.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            user.username, True
        )
        display_name = dao.get_display_name(user.username)
        daily_limit = admin_controls_dao.get_daily_limit()
        has_access = dao.get_user_access(user.username)
        user_id = dao.get_user_id(user.username)
        tab_data = chat_tabs_dao.get_tab_data(user_id)
        active_tab_data = chat_tabs_dao.get_active_tab_data(user_id)
        last_message = get_last_message(
            "active_brain", message.chat_id, user.username, message.uuid
        )
        # if no active tab, set chat_id to 0
        if active_tab_data is None:
            message.chat_id = "0"
            # put the data in the database
            chat_tabs_dao.insert_tab_data(
                user_id, message.chat_id, "new chat", message.chat_id, True
            )
        # if there is an active tab, set chat_id to the active tab's chat_id
        else:
            chat_tabs_dao.update_created_at(user_id, message.chat_id)
            message.chat_id = active_tab_data.chat_id
    if not has_access or has_access == "false" or has_access == "False":
        logger.info(f"user {user.username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    if total_daily_cost >= daily_limit:
        logger.info(f"user {user.username} reached daily limit")
        raise HTTPException(
            status_code=400,
            detail="You reached your daily limit. Please wait until tomorrow to continue using the service.",
        )
    return await process_message(
        last_message,
        user.username,
        USERS_DIR,
        display_name,
        chat_id=message.chat_id,
        regenerate=True,
        uuid=message.uuid,
    )


@router.post("/stop_streaming/", tags=[LOGIN_REQUIRED])
async def stop_streaming(request: Request, user: UserName):
    llmcalls.OpenAIResponser.user_pressed_stop(user.username)
    return {"message": "Streaming stopped successfully"}


@router.post("/message_with_image/", tags=["Messaging", LOGIN_REQUIRED])
async def handle_message_image(
    request: Request,
    image_file: UploadFile,
    prompt: str = Form(...),
    chat_id: str = Form(...),
):
    user = request.state.user
    username = user.username
    settings = await SettingsManager.load_settings(USERS_DIR, username)
    if count_tokens(prompt) > settings["memory"]["input"]:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    with Database() as db, UsersDAO() as dao, ChatTabsDAO() as chat_tabs_dao, AdminControlsDAO() as admin_controls_dao:
        total_tokens_used, total_cost = db.get_token_usage(user.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            user.username, True
        )
        display_name = dao.get_display_name(user.username)
        daily_limit = admin_controls_dao.get_daily_limit()
        has_access = dao.get_user_access(user.username)
        user_id = dao.get_user_id(user.username)
        tab_data = chat_tabs_dao.get_tab_data(user_id)
        active_tab_data = chat_tabs_dao.get_active_tab_data(user_id)
        # if no active tab, set chat_id to 0
        if active_tab_data is None:
            chat_id = "0"
            # put the data in the database
            chat_tabs_dao.insert_tab_data(user_id, chat_id, "new chat", chat_id, True)
        # if there is an active tab, set chat_id to the active tab's chat_id
        else:
            chat_tabs_dao.update_created_at(user_id, chat_id)
            chat_id = active_tab_data.chat_id
    if not has_access or has_access == "false" or has_access == "False":
        logger.info(f"user {username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    if total_daily_cost >= daily_limit:
        logger.info(f"user {username} reached daily limit")
        raise HTTPException(
            status_code=400,
            detail="You reached your daily limit. Please wait until tomorrow to continue using the service.",
        )
    # check the size of the image, if it's too big +5mb, return an error
    if image_file.size > 20000000:
        raise HTTPException(
            status_code=400,
            detail="Image is too big, please use an image that is less than 20mb",
        )
    # save the image to the user's directory
    converted_name = convert_name(username)
    user_dir = os.path.join(USERS_DIR, converted_name, "data")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    image_path = os.path.join(user_dir, image_file.filename)
    with open(image_path, "wb") as f:
        f.write(image_file.file.read())
    # get the image description
    # add the image as markdown to the prompt
    url_encoded_image = urllib.parse.quote(image_file.filename)
    prompt = "![image](data/" + url_encoded_image + ' "image")<p>' + prompt + "</p>"
    result = await MessageParser.start_image_description(
        image_path, prompt, image_file.filename
    )
    return await process_message(
        prompt, username, "users", display_name, result, chat_id
    )


# openAI response route without modules
@router.post(
    "/message_no_modules/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Send a message to the AI without modules",
    description="This endpoint allows you to send a message to the AI by providing a username, session token, and prompt. If the token is valid, the AI will respond to the prompt. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the AI's response if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "AI responded successfully",
            "content": {
                "application/json": {
                    "example": {"message": "AI responded successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_message_no_modules(
    request: Request, message: userMessage, audio_path: str = None
):
    user = request.state.user
    openai_response = OpenAIResponser("gpt-4-0613", 1, 512, 1, user.username)
    messages = [
        {
            "role": "system",
            "content": user.username + ": " + message.prompt + "\nAssistant: ",
        }
    ]
    response = await openai_response.get_response(messages)
    return response.choices[0].message.content


# message route with audio
@router.post(
    "/message_audio/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Send an Audio message and get a transcript",
    description="This endpoint allows you to send an audio message to the AI by providing a username, session token, and audio file. If the token is valid, a transcript of the audio is sent back. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a transcript of the audio if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Audio message sent successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Audio message sent successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_message_audio(request: Request, audio_file: UploadFile):
    return await AudioProcessor.upload_audio(
        USERS_DIR, request.state.user.username, audio_file
    )


@router.post(
    "/generate_audio/",
    tags=["Text to Speech", LOGIN_REQUIRED],
    summary="Generate audio from text",
    description="This endpoint allows you to generate audio from text by providing a username, session token, and prompt. If the token is valid, an audio file is sent back. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns an audio file if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Audio generated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Audio generated successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_generate_audio(request: Request, message: generateAudioMessage):
    user = request.state.user
    audio_path = await AudioProcessor.generate_audio(
        message.prompt, user.username, USERS_DIR
    )

    with Database() as db:
        db.add_voice_usage(user.username, len(message.prompt))
    return FileResponse(audio_path, media_type="audio/wav")


@router.post(
    "/save_data/",
    tags=["Data", LOGIN_REQUIRED],
    summary="Save data to a JSON file",
    description="This endpoint allows you to save the user's data to a JSON file by providing a username and session token. If the token is valid, the data will be saved to a JSON file. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the JSON file if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Data saved successfully",
            "content": {
                "application/json": {"example": {"message": "Data saved successfully"}}
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_save_data(request: Request):
    user = request.state.user

    if os.environ.get("IS_SINGLE_USER") == "true":
        # Paths for memory file and settings file
        json_file_path = os.path.join("data", "user", user.username, "memory.json")
        settings_file = os.path.join("data", "user", user.username, "settings.json")
    else:
        # Paths for memory file and settings file
        json_file_path = os.path.join(USERS_DIR, user.username, "memory.json")
        settings_file = os.path.join(USERS_DIR, user.username, "settings.json")

    # create the json_file_path and settings_file if they don't exist
    if not os.path.exists(json_file_path):
        with open(json_file_path, "w") as f:
            json.dump({}, f)
    if not os.path.exists(settings_file):
        with open(settings_file, "w") as f:
            json.dump({}, f)
    # Check if the memory file exists
    if not os.path.exists(json_file_path):
        # todo: add an empty memory file
        pass

    # Export memory to a JSON file if it exists
    if os.path.exists(json_file_path):
        export_memory_to_file(path=json_file_path, username=user.username)

    # Get the user's notes directory
    user_notes_dir = os.path.join(USERS_DIR, user.username, "notes")

    # Check if the notes directory exists, if not create an empty one
    if not os.path.exists(user_notes_dir):
        os.makedirs(user_notes_dir)

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the user's notes directory
        shutil.copytree(user_notes_dir, os.path.join(temp_dir, "notes"))

        # Check and copy the settings file
        if os.path.exists(settings_file):
            shutil.copy2(settings_file, os.path.join(temp_dir, "settings.json"))

        # Check and copy the memory file
        if os.path.exists(json_file_path):
            shutil.copy2(json_file_path, os.path.join(temp_dir, "memory.json"))

        # Get current date
        current_date = datetime.now().strftime("%Y%m%d")

        # Create zip filename
        zip_filename = f"{user.username}_{current_date}_clang_data.zip"

        # Zip the temporary directory
        shutil.make_archive(
            os.path.join(USERS_DIR, user.username, "data"), "zip", temp_dir
        )

        # Rename the zip file
        shutil.move(
            os.path.join(USERS_DIR, user.username, "data.zip"),
            os.path.join(USERS_DIR, user.username, zip_filename),
        )

    # Serve the zip file
    file_path = os.path.join(USERS_DIR, user.username, zip_filename)
    with open(file_path, "rb") as file:
        content = file.read()

    response = Response(content, media_type="application/zip")
    response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
    return response


@router.post(
    "/upload_data/",
    tags=["Data", LOGIN_REQUIRED],
    summary="Upload user data",
    description="This endpoint allows you to upload the user's data by providing a username, session token, and data file. If the token is valid, the user's data will be uploaded. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "User data uploaded successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User data uploaded successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_upload_data(request: Request, data_file: UploadFile = File(...)):
    user = request.state.user
    username = user.username

    # Save the uploaded file to the user's directory
    file_path = os.path.join(USERS_DIR, username, data_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(data_file.file, buffer)

    # Check if the file is a zip file
    if zipfile.is_zipfile(file_path):
        # Extract the zip file
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(os.path.join(USERS_DIR, username))

        # Check for 'memory.json', and 'settings.json'
        if "memory.json" not in os.listdir(
            os.path.join(USERS_DIR, username)
        ) or "settings.json" not in os.listdir(os.path.join(USERS_DIR, username)):
            raise HTTPException(
                status_code=400, detail="Zip file is missing required files"
            )

        # Verify 'memory.json' is a valid JSON file
        try:
            with open(os.path.join(USERS_DIR, username, "memory.json")) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="'memory.json' is not a valid JSON file"
            )

        # Verify 'settings.json' is a valid JSON file
        try:
            with open(os.path.join(USERS_DIR, username, "settings.json")) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="'settings.json' is not a valid JSON file"
            )

        # Import the data into memory
        import_file_to_memory(
            path=os.path.join(USERS_DIR, username, "memory.json"),
            replace=True,
            username=username,
        )

        # Delete the zip file
        os.remove(file_path)
    else:
        raise HTTPException(status_code=400, detail="Wrong file format!")

    return JSONResponse(content={"message": "User data uploaded successfully"})


@router.post(
    "/abort_button/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Abort the AI",
    description="This endpoint allows you to abort the AI by providing a username and session token. If the token is valid, the AI will be aborted. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "AI aborted successfully",
            "content": {
                "application/json": {"example": {"message": "AI aborted successfully"}}
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_abort_button(request: Request, user: UserName):
    # kill the process, this will need a manual restart or a cron job/supervisor/...
    os.kill(os.getpid(), signal.SIGINT)


# no token message route
@router.post(
    "/notoken_message/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Send a message without token",
    description="This endpoint allows the user to send a message to the AI by providing a prompt, username and password. The AI will respond to the prompt.",
    response_description="Returns the AI's response.",
    responses={
        200: {
            "description": "AI responded successfully",
            "content": {
                "application/json": {
                    "example": {"message": "AI responded successfully"}
                }
            },
        },
    },
)
async def handle_notoken_message(request: Request, message: noTokenMessage):
    user = request.stat.user
    settings = await SettingsManager.load_settings(USERS_DIR, user.username)
    if count_tokens(message.prompt) > settings["memory"]["input"]:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    return await process_message(message.prompt, user.username, None, USERS_DIR)


@router.post(
    "/notoken_generate_audio/",
    tags=["Text to Speech"],
    summary="Generate audio from text without token",
    description="This endpoint allows you to generate audio from text by providing a username, session token, and prompt. If the token is valid, an audio file is sent back. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns an audio file if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Audio generated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Audio generated successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_notoken_generate_audio(request: Request, message: noTokenMessage):
    user = request.stat.user
    settings = await SettingsManager.load_settings(USERS_DIR, user.username)
    if count_tokens(message.prompt) > settings["memory"]["input"]:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    audio_path, audio = await AudioProcessor.generate_audio(
        message.prompt, user.username, USERS_DIR
    )
    return FileResponse(audio_path, media_type="audio/wav")


@router.get(
    "/admin/statistics/{page}",
    response_class=HTMLResponse,
    tags=[LOGIN_REQUIRED, ADMIN_REQUIRED],
)
async def get_statistics(
    request: Request,
    page: int,
    items_per_page: int = 5,
):
    with Database() as db, UsersDAO() as users, AdminControlsDAO() as admin_controls:
        global_stats = json.loads(db.get_global_statistics())
        # Fetch data based on page number and items per page
        page_statistics = json.loads(db.get_statistics(page, items_per_page))
        total_pages = users.get_total_statistics_pages(items_per_page)
        admin_controls = json.loads(admin_controls.get_admin_controls_json())
        return templates.TemplateResponse(
            "stats.html",
            {
                "request": request,
                "rows": page_statistics,
                "chart_data": json.dumps(page_statistics).replace('"', '\\"'),
                "page": page,
                "items_per_page": items_per_page,
                "total_pages": total_pages,
                "statistics": global_stats,
                "admin_controls": admin_controls,
            },
        )


@router.get(
    "/admin/statistics/user/{user_id}",
    response_class=HTMLResponse,
    tags=[LOGIN_REQUIRED, ADMIN_REQUIRED],
)
async def get_user_statistics(request: Request, user_id: int):
    with Database() as db:
        user_stats = json.loads(db.get_user_statistics(user_id))
        return templates.TemplateResponse(
            "user_stats.html", {"request": request, "rows": user_stats}
        )


@router.get("/profile", response_class=HTMLResponse)
async def get_user_profile(request: Request):
    with Database() as db, UsersDAO() as users:
        user = request.state.user
        daily_stats = json.loads(db.get_user_statistics(user.id))
        user_profile = json.loads(users.get_user_profile(user.username))
        return templates.TemplateResponse(
            "user_profile.html",
            {
                "request": request,
                "profile": user_profile,
                "daily_stats": daily_stats,
                "production": PRODUCTION,
            },
        )


@router.get("/data/{file_path:path}", tags=[LOGIN_REQUIRED])
async def read_file(request: Request, file_path: str):
    username = request.state.user.username
    converted_name = convert_name(username)
    host_path = os.path.join(os.getcwd(), "users", converted_name, "data", file_path)
    if os.path.exists(host_path):
        response = FileResponse(host_path)
        # no cache for data files
        response.headers["Cache-Control"] = "public, max-age=0"
        return response
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@router.get("/{file_path:path}")
async def read_file(file_path: str):
    try:
        if os.path.exists(f"static/{file_path}"):
            response = FileResponse(f"static/{file_path}")
            response.headers["Cache-Control"] = "public, max-age=86400"
            return response
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@router.post(
    "/google-login/",
    tags=["Authentication"],
    summary="Login with google",
    description="This endpoint allows you to login a user with google If the login is successful, a session token and username will be set in cookies which expire after 90 days. The cookies' secure attribute is set to True, httponly is set to False, and samesite is set to 'None'. If the login fails, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the user is logged in successfully, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "User logged in successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User logged in successfully"}
                }
            },
        },
        401: {
            "description": "User login failed",
            "content": {
                "application/json": {"example": {"detail": "User login failed"}}
            },
        },
    },
)
async def google_login(request: UserGoogle, response: Response):
    credential = request.credentials
    request = requests.Request()
    id_info = id_token.verify_oauth2_token(
        credential, request, os.environ.get("GOOGLE_CLIENT_ID")
    )
    username = id_info["email"]
    logger.debug(f"User {username} logged in with Google:\n{id_info}")

    # check if email is verified
    if not id_info["email_verified"]:
        raise HTTPException(
            status_code=401, detail="User login failed, email not verified"
        )

    # compare aud with client id
    if id_info["aud"] != os.environ.get("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=403, detail="Invalid authorization code")

    auth = Authentication()
    session_token = auth.google_login(id_info)
    if session_token:
        set_login_cookies(
            session_token=session_token, username=username, response=response
        )
        return {"message": "User logged in successfully"}
    else:
        raise HTTPException(status_code=401, detail="User login failed")


@router.post("/delete_recent_messages/", tags=[LOGIN_REQUIRED])
async def delete_recent_messages(request: Request, message: UserName):
    # remove all users recent messages
    await BrainProcessor.delete_recent_messages(message.username)
    return {"message": "Recent messages deleted successfully"}
