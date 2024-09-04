import json
import os
import shutil
import signal
import tempfile
import urllib.parse
import zipfile
from datetime import datetime
from typing import List, Optional
from agentmemory.helpers import chroma_collection_to_list
from agentmemory.main import search_memory
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
    CreateChat,
    UserName,
    editSettings,
    setActiveChat,
    userMessage,
    noTokenMessage,
    UserGoogle,
    generateAudioMessage,
    regenerateMessage,
    emailMessage,
    TimeTravelMessage,
)
from database import Database
from memory import (
    export_memory_to_file,
    import_file_to_memory,
    get_last_message,
    get_memories,
    update_memory,
    delete_memory,
    MemoryManager,
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
    queryRewrite,
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


def format_timestamp(value, format="%Y-%m-%d %H:%M:%S"):
    return datetime.fromtimestamp(value).strftime(format)


def trim_leading_zeros(value):
    return value.lstrip("0")


def round_number(value, decimals=2):
    if value is None:
        return "N/A"
    return round(value, decimals)


router = APIRouter()
templates = Jinja2Templates(directory=get_root(STATIC))
# Register a custom filter with Jinja2 environment
templates.env.filters["format_timestamp"] = format_timestamp
templates.env.filters["trim_leading_zeros"] = trim_leading_zeros
templates.env.filters["round"] = round_number

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


@router.get(
    "/memory_explorer/{category}", response_class=HTMLResponse, tags=[LOGIN_REQUIRED]
)
async def get_memory_explorer(request: Request, category: str):
    with UsersDAO() as dao:
        username = request.state.user.username
        memories = get_memories(category, username=username)
        return templates.TemplateResponse(
            "memory_explorer.html",
            {"request": request, "category": category, "memories": memories},
        )


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
            if data == '{"type":"ping"}':
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(
                    json.dumps({"type": "message", "content": f"Received: {data}"})
                )
    except WebSocketDisconnect:
        # Handle client disconnection
        if username in connections:
            del connections[username]
        logger.debug(f"User {username} disconnected due to WebSocketDisconnect")
    except ConnectionResetError:
        # Handle client disconnection
        if username in connections:
            del connections[username]
        logger.debug(f"User {username} disconnected due to ConnectionResetError")
    except Exception as e:
        # Handle any other exceptions
        if username in connections:
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
    # check if the google_client_secret.json exists in the users directory
    if os.path.exists(os.path.join(USERS_DIR, "google_client_secret.json")):
        from gworkspace.google_auth import onEnable

        result = await onEnable(username, USERS_DIR)
        if isinstance(result, dict) and "auth_uri" in result:
            settings["auth_uri"] = result["auth_uri"]
        elif isinstance(result, dict) and "error" in result:
            settings["error"] = result["error"]

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

    # check if the calendar_addon or gmail_addon is enabled
    if (
        "calendar_addon" in settings["addons"]
        and settings["addons"]["calendar_addon"]
        or "gmail_addon" in settings["addons"]
        and settings["addons"]["gmail_addon"]
    ):
        from gworkspace.google_auth import onEnable

        auth_uri = await onEnable(username, USERS_DIR)
        if isinstance(auth_uri, dict) and "error" in auth_uri:
            settings["error"] = auth_uri["error"]
            settings["auth_uri"] = None
            # TODO: redirect to the configuration page
            settings["addons"]["calendar_addon"] = False
            settings["addons"]["gmail_addon"] = False
        else:
            settings["auth_uri"] = auth_uri

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
        # this logic is a bit weird when used as API
        else:
            chat_tabs_dao.update_created_at(user_id, message.chat_id)
            if active_tab_data is not None:
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


@router.post("/create_chat_tab/", tags=[LOGIN_REQUIRED])
async def create_chat_tab(request: Request, message: CreateChat):
    user = request.state.user
    with ChatTabsDAO() as chat_tabs_dao:
        user_id = user.id
        chat_tabs_dao.insert_tab_data(
            user_id, message.chat_id, message.chat_name, message.chat_id, False
        )
    return {"message": "Chat tab created successfully"}


@router.post("/set_active_tab/", tags=[LOGIN_REQUIRED])
async def set_active_tab(request: Request, message: setActiveChat):
    user = request.state.user
    with ChatTabsDAO() as chat_tabs_dao:
        user_id = user.id
        chat_tabs_dao.set_active_tab(user_id, message.chat_id)
    return {"message": "Active tab set successfully"}


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
    llmcalls.user_pressed_stop(user.username)
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
        image_path, prompt, image_file.filename, username
    )
    return await process_message(
        prompt, username, "users", display_name, result, chat_id
    )


@router.post("/message_with_files/", tags=["Messaging", LOGIN_REQUIRED])
async def handle_message_files(
    request: Request,
    files: List[UploadFile] = File(...),
    prompt: str = Form(...),
    chat_id: str = Form(...),
):
    file_details = ""
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
    # check the total size of all files, if it's too big +200mb, return an error
    total_size = sum(file.size for file in files)
    if total_size > 200000000:
        raise HTTPException(
            status_code=400,
            detail="Total file size is too big, please use files that are less than 20mb in total",
        )
    # save the files to the user's directory
    converted_name = convert_name(username)
    user_dir = os.path.join(USERS_DIR, converted_name, "data")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    file_paths = []
    for file in files:
        file_path = os.path.join(user_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        file_paths.append(file_path)
    # add the file paths to the prompt
    for file_path in file_paths:
        if file_path.lower().endswith(
            (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".bmp",
                ".webp",
                ".jfif",
                ".pjpeg",
                ".pjp",
                ".ico",
            )
        ):
            url_encoded_image = urllib.parse.quote(os.path.basename(file_path))
            file_details += f'\n![image](data/{url_encoded_image} "image")\n'
        else:
            url_encoded_file = urllib.parse.quote(os.path.basename(file_path))
            file_details += (
                f"\n[data/{os.path.basename(file_path)}](data/{url_encoded_file})\n"
            )
    prompt = file_details + "<p>" + prompt + "</p>"
    result = MessageParser.add_file_paths_to_message(prompt, file_details)
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
async def handle_message_no_modules(request: Request, message: userMessage):
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
    tags=["Messaging"],
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
async def handle_notoken_message(message: noTokenMessage):
    user = message.username
    settings = await SettingsManager.load_settings(USERS_DIR, user)
    if count_tokens(message.prompt) > settings["memory"]["input"]:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    return await process_message(
        message.prompt, user, USERS_DIR, message.display_name, chat_id=message.chat_id
    )


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
    user = request.state.user
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


@router.post("/edit_memory/", tags=[LOGIN_REQUIRED])
async def edit_memory(
    request: Request,
    memory_id: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
):
    username = request.state.user.username
    update_memory(category, memory_id, text=content, username=username)
    return {"message": "Memory updated successfully"}


@router.post("/delete_memory/", tags=[LOGIN_REQUIRED])
async def delete_memory_route(
    request: Request, memory_id: str = Form(...), category: str = Form(...)
):
    user = request.state.user
    username = user.username if user else None
    delete_memory(category, id=memory_id, username=username)
    return {"message": "Memory deleted successfully"}


@router.post("/search_memories/", tags=[LOGIN_REQUIRED])
async def search_memories(
    request: Request, category: str = Form(...), search_query: str = Form(...)
):
    username = request.state.user.username
    memories = search_memory(category, search_query, username=username, n_results=20)

    # Include the distance value in each memory object
    for memory in memories:
        memory["distance"] = memory.get("distance", 0.0)

    # Sort the memories by distance in ascending order
    memories.sort(key=lambda x: x.get("distance", 0.0))

    return templates.TemplateResponse(
        "memory_table_body.html",
        {"request": request, "category": category, "memories": memories},
    )


@router.post("/sort_memories/", tags=[LOGIN_REQUIRED])
async def sort_memories(
    request: Request,
    category: str = Form(...),
    sort_by: str = Form(...),
    sort_order: str = Form(...),
    search_query: str = Form(...),
):
    username = request.state.user.username
    memories = search_memory(category, search_query, username=username, n_results=20)

    # Sort the memories based on the selected sorting option and order
    if sort_by == "created_at":
        memories.sort(
            key=lambda x: x["metadata"]["created_at"], reverse=sort_order == "desc"
        )
    elif sort_by == "distance":
        memories.sort(
            key=lambda x: x.get("distance", 0.0), reverse=sort_order == "desc"
        )
    else:
        memories.sort(key=lambda x: x["id"], reverse=sort_order == "desc")

    # Include the distance value in each memory object
    for memory in memories:
        memory["distance"] = memory.get("distance", 0.0)

    return templates.TemplateResponse(
        "memory_table_body.html",
        {"request": request, "category": category, "memories": memories},
    )


# route to send a gmail email by id
@router.post("/send_email/", tags=[LOGIN_REQUIRED])
async def send_email(request: Request, message: emailMessage):
    user = request.state.user
    username = user.username
    draft_id = message.draft_id
    from addons.gmail_addon import send_email_by_id

    response = send_email_by_id(draft_id, username)
    return response


@router.post("/search_chats/", tags=[LOGIN_REQUIRED])
async def search_memories(
    request: Request,
    category: str = Form(...),
    search_query: str = Form(...),
    sort_by: str = Form(...),
    sort_order: str = Form(...),
    exact_match: bool = Form(False),
):
    username = request.state.user.username

    memories = search_memory(
        category,
        search_query,
        username=username,
        n_results=100,
        max_distance=1.4,
        min_distance=0.0,
        exact_match=exact_match,
    )

    # Sort the memories based on the selected sorting option and order
    if sort_by == "created_at":
        memories.sort(
            key=lambda x: x["metadata"]["created_at"], reverse=sort_order == "desc"
        )
    elif sort_by == "distance" and not exact_match:
        memories.sort(
            key=lambda x: x.get("distance", 0.0), reverse=sort_order == "desc"
        )
    else:
        memories.sort(key=lambda x: x["id"], reverse=sort_order == "desc")
    settings = await SettingsManager.load_settings(USERS_DIR, username)
    # get episodic memories
    memory_manager = MemoryManager()
    memory_manager.model_used = settings["active_model"]["active_model"]
    episodic_memory = await memory_manager.get_episodic_memory(
        search_query, username, search_query, 2560, settings=settings
    )
    # add the episodic memory to the memories if it exists
    if episodic_memory:
        # convert the query response to list and return
        result_list = chroma_collection_to_list(episodic_memory)
        memories.extend(result_list)

    # Include the distance value in each memory object
    for memory in memories:
        if isinstance(memory, dict):
            memory["distance"] = memory.get("distance", 0.0)
            # get the title of the chat tab based on the chat_id
            with ChatTabsDAO() as chat_tabs_dao:
                chat_id = memory.get("metadata", {}).get("chat_id")
                if chat_id:
                    chat_title = chat_tabs_dao.get_tab_description(chat_id)
                    memory["chat_title"] = chat_title
        else:
            print("memory is not a dict", memory)

    rewritten = await queryRewrite(search_query, username, USERS_DIR, memories)

    rewritten_memories = search_memory(
        category,
        rewritten,
        username=username,
        n_results=100,
        max_distance=1.4,
        min_distance=0.0,
        exact_match=exact_match,
    )

    return JSONResponse(
        content={
            "category": category,
            "memories": memories,
            "rewritten": rewritten,
            "rewritten_memories": rewritten_memories,
        }
    )


@router.post(
    "/time_travel_message/",
    tags=["Messaging", LOGIN_REQUIRED],
    summary="Send a message with a custom timestamp",
    description="This endpoint allows you to send a message to the AI with a custom timestamp, enabling 'time travel' functionality.",
    response_description="Returns the AI's response to the time-travelled message.",
    responses={
        200: {
            "description": "AI responded successfully to time-travelled message",
            "content": {
                "application/json": {
                    "example": {
                        "message": "AI responded successfully to time-travelled message"
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
async def handle_time_travel_message(request: Request, message: TimeTravelMessage):
    user = request.state.user
    settings = await SettingsManager.load_settings(USERS_DIR, user.username)
    if count_tokens(message.prompt) > settings["memory"]["input"]:
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

        if not has_access:
            raise HTTPException(status_code=400, detail="You do not have access.")
        if total_daily_cost >= daily_limit:
            raise HTTPException(status_code=400, detail="You reached your daily limit.")

        # Handle chat_id logic
        if message.chat_id is None:
            message.chat_id = "0"
            chat_tabs_dao.insert_tab_data(
                user_id, message.chat_id, "new chat", message.chat_id, True
            )
        else:
            chat_tabs_dao.update_created_at(user_id, message.chat_id)

    # Process the time-travelled message
    return await process_message(
        message.prompt,
        user.username,
        USERS_DIR,
        message.display_name,
        chat_id=message.chat_id,
        timestamp=message.timestamp,
    )
