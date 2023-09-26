import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import signal
import sys
from fastapi import APIRouter, Depends, Query,  FastAPI, HTTPException, BackgroundTasks, File, Request, UploadFile, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
import requests
from utils import MessageSender, process_message, OpenAIResponser, AudioProcessor, AddonManager
from authentication import Authentication
from pydantic import BaseModel
from classes import User, UserCheckToken, UserName, editSettings, userMessage
import openai
import shutil
from brain import DatabaseManager
from database import Database
from memory import export_memory_to_file

router = APIRouter()

connections = {}

PRODUCTION = os.environ['PRODUCTION']
isOnHttps = PRODUCTION # False

ORIGINS = os.getenv("ORIGINS")
if ORIGINS:
    LIVE_DOMAIN = ORIGINS.split(";")[0]
else:
    LIVE_DOMAIN = "localhost"


users_dir = 'users' # end with a slash

router.mount("/static", StaticFiles(directory="static"), name="static")
router.mount("/d-id", StaticFiles(directory="d-id"), name="d-id")

@router.get("/")
async def read_root():
    if PRODUCTION == 'true':
        try:
            return FileResponse('static/live_index.html')
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Item not found")
    else:
        try:
            return FileResponse('static/local_index.html')
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Item not found")


@router.get("/d-id/{file}")
async def read_did(file: str):
    if PRODUCTION == 'true':
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        try:
            return FileResponse(f'd-id/{file}')
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Item not found")

@router.get("/styles.css")
async def read_root():
    try:
        return FileResponse('static/styles.css')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")

def get_token(request: Request):
    return request.cookies.get('session_token')

async def send_debug_message(username: str, message: str):
    connection = connections.get(username)
    print(f"connection length: {len(connections)}")
    if connection:
        try:
            await connection.send_text(message)
        except Exception as e:
            print(f"An error occurred when sending a message to user {username}: {e}")
    else:
        print(f"No active websocket connection for user {username}")


@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_text('pong')
            else:
                print(f'User {username} sent: {data}')
                # Send a response back to the client
                await websocket.send_text(f'Received: {data}')
    except WebSocketDisconnect:
        # Handle client disconnection
        del connections[username]
        print(f'User {username} disconnected')
    except ConnectionResetError:
        # Handle client disconnection
        del connections[username]
        print(f'User {username} disconnected')
    except Exception as e:
        # Handle any other exceptions
        del connections[username]
        print(f'An error occurred with user {username}: {e}')

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
                "application/json": {
                    "example": {"detail": "User registration failed"}
                }
            },
        },
    },
)
async def register(user: User, response: Response):
    auth = Authentication()
    session_token = auth.register(user.username, user.password)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == 'true':
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=LIVE_DOMAIN)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=LIVE_DOMAIN)
        else:
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date)
        return {'message': 'User registered successfully'}
    else:
        raise HTTPException(status_code=400, detail="User registration failed")
    
# login route
@router.post("/login/",
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
                "application/json": {
                    "example": {"detail": "User login failed"}
                }
            }, 
        }, 
    }, 
)
async def login(user: User, response: Response):
    auth = Authentication()
    session_token = auth.login(user.username, user.password)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == 'true':
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=LIVE_DOMAIN)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=LIVE_DOMAIN)
        else:
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date)
        return {'message': 'User logged in successfully'}
    else:
        raise HTTPException(status_code=401, detail="User login failed")
    
# logout route
@router.post("/logout/",
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
                "application/json": {
                    "example": {"detail": "User logout failed"}
                }
            },
        },
    },)
async def logout(user: UserCheckToken):
    auth = Authentication()
    success = auth.logout(user.username, user.session_token)
    if success:
        return {'message': 'User logged out successfully'}
    else:
        raise HTTPException(status_code=401, detail="User logout failed")
    
# check token route
@router.post("/check_token/",
    tags=["Authentication"],
    summary="Check if a token is valid",
    description="This endpoint allows you to check if a token is valid by providing a username and session token. If the token is valid, a success message will be returned. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Token is valid",
            "content": {
                "application/json": {
                    "example": {"message": "Token is valid"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def check_token(user: UserCheckToken):
    auth = Authentication()
    success = auth.check_token(user.username, user.session_token)
    if success:
        return {'message': 'Token is valid'}
    else:
        raise HTTPException(status_code=401, detail="Token is invalid")
  
# load settings route
@router.post("/load_settings/",
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
                        "settings": {
                            "category": {
                                "setting": "value"
                            }
                        }
                    }
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_get_settings(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    print('session_token: ' + str(session_token))
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    await AddonManager.load_addons(user.username, users_dir)
    with open(os.path.join(users_dir, user.username, 'settings.json'), 'r') as f:
        settings = json.load(f)
    print(settings)
    total_tokens_used, total_cost = get_token_usage(user.username)
    settings['usage'] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    return settings

def get_token_usage(username):
    db = Database()
    db.open()
    db.cursor.execute(f"SELECT total_tokens_used, prompt_tokens, completion_tokens FROM users WHERE username = '{username}'")
    result = db.cursor.fetchone()
    db.close()
    prompt_cost = round(result[1] * 0.03 / 1000, 3)
    completion_cost = round(result[2] * 0.06 / 1000, 3)
    total_cost = round(prompt_cost + completion_cost, 3)
    return result[0], total_cost

# update settings route
@router.post("/update_settings/",
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
                        "settings": {
                            "category": {
                                "setting": "value"
                            }
                        }
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
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_update_settings(request: Request, user: editSettings):
    print(user)
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
    settings_file = os.path.join(user_dir, 'settings.json')
    if not os.path.exists(settings_file):
        # create the settings file
        with open(settings_file, 'w') as f:
            json.dump({}, f)
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    if user.category in settings:
        if user.setting in settings[user.category]:
            if str(user.value).lower() == 'true':
                settings[user.category][user.setting] = True
            elif str(user.value).lower() == 'false':
                settings[user.category][user.setting] = False
            elif user.value.isdigit():
                settings[user.category][user.setting] = int(user.value)
            else:
                settings[user.category][user.setting] = user.value
        else:
            raise HTTPException(status_code=400, detail="Setting not found")
    else:
        raise HTTPException(status_code=400, detail="Category not found")
    with open(settings_file, 'w') as f:
        json.dump(settings, f)
    total_tokens_used, total_cost = get_token_usage(user.username)
    settings['usage'] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    return settings


# openAI response route
@router.post("/message/",
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
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_message(request: Request, message: userMessage, background_tasks: BackgroundTasks = None):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    return await process_message(message.prompt, message.username, background_tasks, users_dir)

# openAI response route without modules
@router.post("/message_no_modules/",
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
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_message_no_modules(request: Request, message: userMessage, audio_path: str = None):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    openai_response = OpenAIResponser("gpt-4-0613", 1, 512, 1)
    messages = [
        {"role": "system", "content": message.username + ': ' + message.prompt + '\nAssistant: '}
    ]
    response = await openai_response.get_response(messages)
    return  response['choices'][0]['message']['content']


# message route with audio
@router.post("/message_audio/",
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
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },
    )
async def handle_message_audio(request: Request, audio_file: UploadFile, background_tasks: BackgroundTasks = None):
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")

    result = await AudioProcessor.upload_audio(users_dir, username, audio_file, background_tasks)

    return result 

@router.post("/generate_audio/",
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
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_generate_audio(request: Request, message: userMessage, background_tasks: BackgroundTasks = None):
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    
    audio_path, audio = await AudioProcessor.generate_audio(message.prompt, username, users_dir)
    return FileResponse(audio_path, media_type="audio/wav")

@router.post("/save_data/", tags=["Data"],
             summary="Save data to a JSON file",
    description="This endpoint allows you to save the user's data to a JSON file by providing a username and session token. If the token is valid, the data will be saved to a JSON file. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns the JSON file if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "Data saved successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Data saved successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_save_data(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    
    # Export memory to a JSON file
    json_file_path = os.path.join(users_dir, user.username, "memory.json")
    export_memory_to_file(path=json_file_path, username=user.username)

    # Serve the JSON file
    return FileResponse(json_file_path, media_type="application/json", filename="memory.json")


@router.post("/delete_data/",
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
                    "application/json": {
                        "example": {"detail": "Token is invalid"}
                    }
                },
            },
            },)
async def handle_delete_data(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    memory_file = os.path.join(users_dir, user.username)
    dbmanager = DatabaseManager()
    dbmanager.delete_db(memory_file)
    await asyncio.sleep(1)
    # Delete the user's directory
    shutil.rmtree(os.path.join(users_dir, user.username), ignore_errors=True, onerror=None)
    
    return {'message': 'User data deleted successfully'}

@router.post("/upload_data/",
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
                    "application/json": {
                        "example": {"detail": "Token is invalid"}
                    }
                },
            },
            },)
async def handle_upload_data(request: Request, username: str = Form(...), data_file: UploadFile = File(...)):
    print(username)
    print(data_file.filename)
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    
    # Delete the user's directory
    shutil.rmtree(os.path.join(users_dir, username))
    
    # Create the user's directory
    os.makedirs(os.path.join(users_dir, username))
    
    # Save the uploaded file to the user's directory
    with open(os.path.join(users_dir, username, data_file.filename), "wb") as buffer:
        shutil.copyfileobj(data_file.file, buffer)
    
    # Unzip the file
    shutil.unpack_archive(os.path.join(users_dir, username, data_file.filename), os.path.join(users_dir, username))
    
    # Delete the .zip file
    os.remove(os.path.join(users_dir, username, data_file.filename))
    
    return {'message': 'User data uploaded successfully'}

@router.post("/abort_button/",
    tags=["Messaging"],
    summary="Abort the AI",
    description="This endpoint allows you to abort the AI by providing a username and session token. If the token is valid, the AI will be aborted. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "AI aborted successfully",
            "content": {
                "application/json": {
                    "example": {"message": "AI aborted successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {
                    "example": {"detail": "Token is invalid"}
                }
            },
        },
    },)
async def handle_abort_button(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    # kill the process, this will need a manual restart or a cron job/supervisor/...
    os.kill(os.getpid(), signal.SIGINT)