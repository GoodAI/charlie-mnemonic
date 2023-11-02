from datetime import datetime, timedelta, timezone
import json
import os
import signal
from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
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
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyCookie
import urllib.parse
from unidecode import unidecode
from utils import (
    process_message,
    OpenAIResponser,
    AudioProcessor,
    AddonManager,
    SettingsManager,
    BrainProcessor,
    MessageParser,
)
from authentication import Authentication
from classes import (
    LoginUser,
    User,
    UserCheckToken,
    UserName,
    editSettings,
    userMessage,
    noTokenMessage,
    UserGoogle,
    generateAudioMessage,
)
import shutil
from database import Database
from memory import (
    export_memory_to_file,
    import_file_to_memory,
    wipe_all_memories,
    stop_database,
)
import tempfile
import zipfile
import logs
from typing import Optional
from jose import jwt
from jose.exceptions import JWTError
from google.oauth2 import id_token
from google.auth.transport import requests

logger = logs.Log("routes", "routes.log").get_logger()

from config import api_keys

router = APIRouter()
templates = Jinja2Templates(directory="static")

connections = {}

PRODUCTION = os.environ["PRODUCTION"]

ORIGINS = os.environ["ORIGINS"]

users_dir = "users"

router.mount("/static", StaticFiles(directory="static"), name="static")
router.mount("/d-id", StaticFiles(directory="d-id"), name="d-id")


@router.get("/d-id/api.json")
async def read_did_api_json():
    data = {"key": api_keys["d-id"], "url": "https://api.d-id.com"}
    return JSONResponse(content=data)


@router.get("/d-id/{file}")
async def read_did(file: str):
    try:
        return FileResponse(f"d-id/{file}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    version = SettingsManager.get_version()
    daily_limit = 0
    with Database() as db:
        daily_limit = db.get_daily_limit()
        maintenance_mode = db.get_maintenance_mode()

    if (
        maintenance_mode == "true"
        or maintenance_mode == "True"
        or maintenance_mode == True
    ):
        return templates.TemplateResponse(
            "maintenance.html",
            {
                "request": request,
                "version": version,
                "daily_limit": daily_limit,
                "production": PRODUCTION,
            },
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "version": version,
                "daily_limit": daily_limit,
                "production": PRODUCTION,
            },
        )


@router.get("/styles.css")
async def read_root():
    try:
        return FileResponse("static/styles.css")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


def get_token(request: Request):
    return request.cookies.get("session_token")


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


# register route
@router.post(
    "/register/",
    tags=["Authentication"],
    summary="Register a new user",
    description="This endpoint allows you to register a new user by providing a username and password. If the registration is successful, a session token and username will be set in cookies which expire after 90 days. The cookies' secure attribute is set to True, httponly is set to False, and samesite is set to 'None'. If the registration fails, an HTTP 400 error will be returned.",
    response_description="Returns a success message if the user is registered successfully, else returns an HTTPException with status code 400.",
    responses={
        200: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User registered successfully"}
                }
            },
        },
        400: {
            "description": "User registration failed",
            "content": {
                "application/json": {"example": {"detail": "User registration failed"}}
            },
        },
    },
)
async def register(user: User, response: Response):
    auth = Authentication()
    session_token = auth.register(user.username, user.password, user.display_name)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == "true":
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
            response.set_cookie(
                key="username",
                value=user.username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
        else:
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
            response.set_cookie(
                key="username",
                value=user.username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
        return {
            "message": "User registered successfully",
            "display_name": user.display_name,
        }
    else:
        raise HTTPException(status_code=400, detail="User registration failed")


# login route
@router.post(
    "/login/",
    tags=["Authentication"],
    summary="Login a user",
    description="This endpoint allows you to login a user by providing a username and password. If the login is successful, a session token and username will be set in cookies which expire after 90 days. The cookies' secure attribute is set to True, httponly is set to False, and samesite is set to 'None'. If the login fails, an HTTP 401 error will be returned.",
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
async def login(user: LoginUser, response: Response):
    auth = Authentication()
    session_token = auth.login(user.username, user.password)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == "true":
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
            response.set_cookie(
                key="username",
                value=user.username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
        else:
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
            response.set_cookie(
                key="username",
                value=user.username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
        return {"message": "User logged in successfully"}
    else:
        raise HTTPException(status_code=401, detail="User login failed")


# logout route
@router.post(
    "/logout/",
    tags=["Authentication"],
    summary="Logout a user",
    description="This endpoint allows you to logout a user by providing a username and session token. If the logout is successful, the session token and username cookies will be deleted. If the logout fails, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the user is logged out successfully, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "User logged out successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User logged out successfully"}
                }
            },
        },
        401: {
            "description": "User logout failed",
            "content": {
                "application/json": {"example": {"detail": "User logout failed"}}
            },
        },
    },
)
async def logout(user: UserCheckToken):
    auth = Authentication()
    success = auth.logout(user.username, user.session_token)
    if success:
        return {"message": "User logged out successfully"}
    else:
        raise HTTPException(status_code=401, detail="User logout failed")


# check token route
@router.post(
    "/check_token/",
    tags=["Authentication"],
    summary="Check if a token is valid",
    description="This endpoint allows you to check if a token is valid by providing a username and session token. If the token is valid, a success message will be returned. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Token is valid",
            "content": {"application/json": {"example": {"message": "Token is valid"}}},
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def check_token(user: UserCheckToken):
    auth = Authentication()
    success = auth.check_token(user.username, user.session_token)
    if success:
        return {"message": "Token is valid"}
    else:
        raise HTTPException(status_code=401, detail="Token is invalid")


# load settings route
@router.post(
    "/load_settings/",
    tags=["Settings"],
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
async def handle_get_settings(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    await AddonManager.load_addons(user.username, users_dir)
    with open(os.path.join(users_dir, user.username, "settings.json"), "r") as f:
        settings = json.load(f)
    logger.debug(f"Loaded settings for user {user.username}")
    logger.debug(settings)
    total_tokens_used, total_cost = 0, 0
    with Database() as db:
        total_tokens_used, total_cost = db.get_token_usage(user.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            user.username, True
        )
        display_name = db.get_display_name(user.username)
    settings["usage"] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    settings["daily_usage"] = {"daily_cost": total_daily_cost}
    settings["display_name"] = display_name
    return settings


def count_tokens(message):
    return MessageParser.num_tokens_from_string(message)


# update settings route
@router.post(
    "/update_settings/",
    tags=["Settings"],
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
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    # create the directory if it doesn't exist
    user_dir = os.path.join(users_dir, user.username)
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
        if user.setting in settings[user.category]:
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
        with Database() as db:
            if user.setting == "display_name":
                db.update_display_name(user.username, user.value)
            else:
                raise HTTPException(status_code=400, detail="Setting not found")
    else:
        raise HTTPException(status_code=400, detail="Category not found")
    with open(settings_file, "w") as f:
        json.dump(settings, f)
    with Database() as db:
        total_tokens_used, total_cost = db.get_token_usage(user.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            user.username, True
        )
        display_name = db.get_display_name(user.username)
    settings["usage"] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    settings["daily_usage"] = {"daily_cost": total_daily_cost}
    settings["display_name"] = display_name
    return settings


# openAI response route
@router.post(
    "/message/",
    tags=["Messaging"],
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
async def handle_message(
    request: Request, message: userMessage, background_tasks: BackgroundTasks = None
):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    (
        total_tokens_used,
        total_cost,
        daily_limit,
        total_daily_tokens_used,
        total_daily_cost,
        display_name,
    ) = (0, 0, 0, 0, 0, "")
    with Database() as db:
        total_tokens_used, total_cost = db.get_token_usage(message.username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(
            message.username, True
        )
        display_name = db.get_display_name(message.username)
        daily_limit = db.get_daily_limit()
        has_access = db.get_user_access(message.username)
    if not has_access or has_access == "false" or has_access == "False":
        logger.info(f"user {message.username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    if total_daily_cost >= daily_limit:
        logger.info(f"user {message.username} reached daily limit")
        raise HTTPException(
            status_code=400,
            detail="You reached your daily limit. Please wait until tomorrow to continue using the service.",
        )
    return await process_message(
        message.prompt,
        message.username,
        background_tasks,
        users_dir,
        message.display_name,
    )


@router.post("/message_with_image/", tags=["Messaging"])
async def handle_message_image(
    request: Request, image_file: UploadFile, prompt: str = Form(...)
):
    print(prompt)
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    if count_tokens(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    with Database() as db:
        total_tokens_used, total_cost = db.get_token_usage(username)
        total_daily_tokens_used, total_daily_cost = db.get_token_usage(username, True)
        display_name = db.get_display_name(username)[0]
        daily_limit = db.get_daily_limit()
        has_access = db.get_user_access(username)
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
    if image_file.size > 5000000:
        raise HTTPException(
            status_code=400,
            detail="Image is too big, please use an image that is less than 5mb",
        )
    # save the image to the user's directory
    converted_name = convert_name(username)
    user_dir = os.path.join(users_dir, converted_name, "data")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    image_path = os.path.join(user_dir, image_file.filename)
    with open(image_path, "wb") as f:
        f.write(image_file.file.read())
    # get the image description
    # add the image as markdown to the prompt
    url_encoded_image = urllib.parse.quote(image_file.filename)
    prompt = "![image](data/" + url_encoded_image + ' "image")<p>' + prompt + "</p>"
    result = await MessageParser.get_image_description(
        image_path, prompt, image_file.filename
    )
    return await process_message(
        prompt, username, None, users_dir, display_name, result
    )


@router.post("/get_recent_messages/")
async def get_recent_messages(
    request: Request, message: UserName, background_tasks: BackgroundTasks = None
):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    with Database() as db:
        has_access = db.get_user_access(message.username)
        recent_messages = MessageParser.get_recent_messages(message.username)
    if not has_access or has_access == "false" or has_access == "False":
        logger.info(f"user {message.username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    return recent_messages


# openAI response route without modules
@router.post(
    "/message_no_modules/",
    tags=["Messaging"],
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
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    openai_response = OpenAIResponser("gpt-4-0613", 1, 512, 1, message.username)
    messages = [
        {
            "role": "system",
            "content": message.username + ": " + message.prompt + "\nAssistant: ",
        }
    ]
    response = await openai_response.get_response(messages)
    return response["choices"][0]["message"]["content"]


# message route with audio
@router.post(
    "/message_audio/",
    tags=["Messaging"],
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
async def handle_message_audio(
    request: Request, audio_file: UploadFile, background_tasks: BackgroundTasks = None
):
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")

    result = await AudioProcessor.upload_audio(
        users_dir, username, audio_file, background_tasks
    )

    return result


@router.post(
    "/generate_audio/",
    tags=["Text to Speech"],
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
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    audio_path, audio = await AudioProcessor.generate_audio(
        message.prompt, message.username, users_dir
    )
    with Database() as db:
        db.add_voice_usage(message.username, len(message.prompt))
    return FileResponse(audio_path, media_type="audio/wav")


@router.post(
    "/save_data/",
    tags=["Data"],
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
async def handle_save_data(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")

    # Export memory to a JSON file
    json_file_path = os.path.join(users_dir, user.username, "memory.json")
    export_memory_to_file(path=json_file_path, username=user.username)

    # get the user's notes directory and settings file
    user_notes_dir = os.path.join(users_dir, user.username, "notes")
    settings_file = os.path.join(users_dir, user.username, "settings.json")

    # create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # copy the user's notes directory, settings file and memory file to the temporary directory
        shutil.copytree(user_notes_dir, os.path.join(temp_dir, "notes"))
        shutil.copy2(settings_file, os.path.join(temp_dir, "settings.json"))
        shutil.copy2(json_file_path, os.path.join(temp_dir, "memory.json"))

        # get current date
        current_date = datetime.now().strftime("%Y%m%d")

        # create zip filename
        zip_filename = f"{user.username}_{current_date}_clang_data.zip"

        # zip the temporary directory
        shutil.make_archive(
            os.path.join(users_dir, user.username, "data"), "zip", temp_dir
        )

        # rename the zip file
        shutil.move(
            os.path.join(users_dir, user.username, "data.zip"),
            os.path.join(users_dir, user.username, zip_filename),
        )

    # serve the zip file
    # return FileResponse(os.path.join(users_dir, user.username, zip_filename), media_type="application/zip", filename=zip_filename)

    # todo: note that this method reads the entire file content into memory, which could cause issues for large files. If files are large,
    # we should stick with the FileResponse function and try to find out why it’s not setting the ‘Content-Disposition’ header correctly.
    file_path = os.path.join(users_dir, user.username, zip_filename)
    with open(file_path, "rb") as file:
        content = file.read()

    response = Response(content, media_type="application/zip")
    response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
    return response


@router.post(
    "/delete_data/",
    tags=["Data"],
    summary="Delete user data",
    description="This endpoint allows you to delete the user's data by providing a username and session token. If the token is valid, the user's data will be deleted. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "User data deleted successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User data deleted successfully"}
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
async def handle_delete_data(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    wipe_all_memories(user.username)
    stop_database(user.username)
    # remove all users recent messages
    await BrainProcessor.delete_recent_messages(user.username)
    # delete the whole user directory, using ignore_errors=True to avoid errors for the db file that is still open
    shutil.rmtree(os.path.join(users_dir, user.username), ignore_errors=True)
    return {"message": "User data deleted successfully"}


@router.post(
    "/upload_data/",
    tags=["Data"],
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
async def handle_upload_data(
    request: Request, username: str = Form(...), data_file: UploadFile = File(...)
):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")

    # Save the uploaded file to the user's directory
    file_path = os.path.join(users_dir, username, data_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(data_file.file, buffer)

    # Check if the file is a zip file
    if zipfile.is_zipfile(file_path):
        # Extract the zip file
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(os.path.join(users_dir, username))

        # Check for 'memory.json', and 'settings.json'
        if "memory.json" not in os.listdir(
            os.path.join(users_dir, username)
        ) or "settings.json" not in os.listdir(os.path.join(users_dir, username)):
            raise HTTPException(
                status_code=400, detail="Zip file is missing required files"
            )

        # Verify 'memory.json' is a valid JSON file
        try:
            with open(os.path.join(users_dir, username, "memory.json")) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="'memory.json' is not a valid JSON file"
            )

        # Verify 'settings.json' is a valid JSON file
        try:
            with open(os.path.join(users_dir, username, "settings.json")) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="'settings.json' is not a valid JSON file"
            )

        # Import the data into memory
        import_file_to_memory(
            path=os.path.join(users_dir, username, "memory.json"),
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
    tags=["Messaging"],
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
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
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
    auth = Authentication()
    session_token = auth.login(message.username, message.password)
    if not session_token:
        raise HTTPException(status_code=401, detail="User login failed")
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    return await process_message(message.prompt, message.username, None, users_dir)


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
async def handle_notoken_generate_audio(message: noTokenMessage):
    auth = Authentication()
    session_token = auth.login(message.username, message.password)
    if not session_token:
        raise HTTPException(status_code=401, detail="User login failed")
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
    audio_path, audio = await AudioProcessor.generate_audio(
        message.prompt, message.username, users_dir
    )
    return FileResponse(audio_path, media_type="audio/wav")


security = HTTPBearer()


def get_current_username(
    username: Optional[str] = Depends(APIKeyCookie(name="username")),
    session_token: Optional[str] = Depends(APIKeyCookie(name="session_token")),
):
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid authorization code")
    return username


@router.post("/admin/update_user/{user_id}")
async def update_user(
    user_id: int,
    has_access: str = Form(...),
    role: str = Form(...),
    username: str = Depends(get_current_username),
):
    with Database() as db:
        role_db = db.get_user_role(username)[0]
    if role_db != "admin":
        logger.warning(
            f"User {username} (role: {role_db}) is not authorized to update this user: {user_id}"
        )
        raise HTTPException(
            status_code=403, detail="You are not authorized to update this user"
        )
    else:
        with Database() as db:
            db.update_user(user_id, has_access, role)
            logger.info(f"User {username} (role: {role_db}) updated user: {user_id}")
            return {"message": f"User {user_id} updated successfully"}


@router.get("/admin/statistics/{page}", response_class=HTMLResponse)
async def get_statistics(
    request: Request,
    page: int,
    items_per_page: int = 5,
    username: str = Depends(get_current_username),
):
    with Database() as db:
        role = db.get_user_role(username)[0]
    if role != "admin":
        logger.warning(
            f"User {username} (role: {role}) is not authorized to view this page: /admin/statistics/{page}"
        )
        raise HTTPException(
            status_code=403, detail="You are not authorized to view this page"
        )
    else:
        with Database() as db:
            global_stats = json.loads(db.get_global_statistics())
            # Fetch data based on page number and items per page
            page_statistics = json.loads(db.get_statistics(page, items_per_page))
            total_pages = db.get_total_statistics_pages(items_per_page)
            admin_controls = json.loads(db.get_admin_controls())
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


@router.get("/admin/statistics/user/{user_id}", response_class=HTMLResponse)
async def get_user_statistics(
    request: Request, user_id: int, username: str = Depends(get_current_username)
):
    # get the user's role from the database
    with Database() as db:
        role = db.get_user_role(username)[0]
    if role != "admin":
        logger.warning(
            f"User {username} (role: {role}) is not authorized to view this page: /admin/statistics/user/{user_id}"
        )
        raise HTTPException(
            status_code=403, detail="You are not authorized to view this page"
        )
    else:
        with Database() as db:
            user_stats = json.loads(db.get_user_statistics(user_id))
            return templates.TemplateResponse(
                "user_stats.html", {"request": request, "rows": user_stats}
            )


@router.post("/admin/update_controls")
async def update_controls(
    request: Request,
    username: str = Depends(get_current_username),
    id: int = Form(...),
    daily_spending_limit: str = Form(...),
    allow_access: str = Form(...),
    maintenance: str = Form(...),
):
    with Database() as db:
        role = db.get_user_role(username)[0]
        if role != "admin":
            raise HTTPException(
                status_code=403, detail="You are not authorized to perform this action"
            )
        with Database() as db:
            if id == "" or id == None:
                id = 1
            db.update_admin_controls(
                id, daily_spending_limit, allow_access, maintenance
            )
        return RedirectResponse(url="/admin/statistics/1", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
async def get_user_profile(
    request: Request, username: str = Depends(get_current_username)
):
    with Database() as db:
        user_id = db.get_user_id(username)
        daily_stats = json.loads(db.get_user_statistics(user_id))
        user_profile = json.loads(db.get_user_profile(username))
        return templates.TemplateResponse(
            "user_profile.html",
            {"request": request, "profile": user_profile, "daily_stats": daily_stats},
        )


@router.get("/data/{file_path:path}")
async def read_file(file_path: str, username: str = Depends(get_current_username)):
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
    if id_info["email_verified"] == False:
        raise HTTPException(
            status_code=401, detail="User login failed, email not verified"
        )

    # compare aud with client id
    if id_info["aud"] != os.environ.get("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=403, detail="Invalid authorization code")

    auth = Authentication()
    session_token = auth.google_login(id_info)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == "true":
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
            response.set_cookie(
                key="username",
                value=username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
                domain=ORIGINS,
            )
        else:
            response.set_cookie(
                key="session_token",
                value=session_token,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
            response.set_cookie(
                key="username",
                value=username,
                secure=True,
                httponly=False,
                samesite="None",
                expires=expiracy_date,
            )
        return {"message": "User logged in successfully"}
    else:
        raise HTTPException(status_code=401, detail="User login failed")


@router.post("/delete_recent_messages/")
async def delete_recent_messages(request: Request, message: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    # remove all users recent messages
    await BrainProcessor.delete_recent_messages(message.username)
    return {"message": "Recent messages deleted successfully"}


def convert_name(name):
    # Convert non-ASCII characters to ASCII
    name = unidecode(name)
    # replace spaces with underscores
    name = name.replace(" ", "_")
    name = name.replace("@", "_")
    name = name.replace(".", "_")
    # lowercase the name
    return name.lower()
