from datetime import datetime, timedelta, timezone
import json
import os
import signal
from fastapi import APIRouter, HTTPException, BackgroundTasks, File, Request, UploadFile, WebSocket, WebSocketDisconnect, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils import process_message, OpenAIResponser, AudioProcessor, AddonManager, SettingsManager, BrainProcessor, MessageParser
from authentication import Authentication
from classes import User, UserCheckToken, UserName, editSettings, userMessage, noTokenMessage
import shutil
from database import Database
from memory import export_memory_to_file, import_file_to_memory, wipe_all_memories, stop_database
import tempfile
import zipfile
import logs

logger = logs.Log(__name__, 'routes.log').get_logger()

router = APIRouter()
templates = Jinja2Templates(directory="static")

connections = {}

PRODUCTION = os.environ['PRODUCTION']

ORIGINS = "https://clang.goodai.com"

users_dir = 'users' # end with a slash

router.mount("/static", StaticFiles(directory="static"), name="static")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    version = SettingsManager.get_version()
    if PRODUCTION == 'true':
        try:
            return templates.TemplateResponse("live_index.html", {"request": request, "version": version})
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Item not found")
    else:
        try:
            return templates.TemplateResponse("local_index.html", {"request": request, "version": version})
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Item not found")

def get_token(request: Request):
    return request.cookies.get('session_token')

async def send_debug_message(username: str, message: str):
    connection = connections.get(username)
    #logger.info(f"connection length: {len(connections)}")
    if connection:
        try:
            await connection.send_text(message)
        except Exception as e:
            logger.error(f"An error occurred when sending a message to user {username}: {e}")
    else:
        logger.error(f"No active websocket connection for user {username}")


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
                # Send a response back to the client
                await websocket.send_text(f'Received: {data}')
    except WebSocketDisconnect:
        # Handle client disconnection
        del connections[username]
        logger.debug(f'User {username} disconnected')
    except ConnectionResetError:
        # Handle client disconnection
        del connections[username]
        logger.debug(f'User {username} disconnected')
    except Exception as e:
        # Handle any other exceptions
        del connections[username]
        logger.error(f'An error occurred with user {username}: {e}')

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
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=ORIGINS)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=ORIGINS)
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
    auth = Authentication()
    success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    await AddonManager.load_addons(user.username, users_dir)
    with open(os.path.join(users_dir, user.username, 'settings.json'), 'r') as f:
        settings = json.load(f)
    logger.debug(f'Loaded settings for user {user.username}')
    logger.debug(settings)
    total_tokens_used, total_cost = get_token_usage(user.username)
    settings['usage'] = {"total_tokens": total_tokens_used, "total_cost": total_cost}
    return settings

def get_token_usage(username):
    db = Database()
    db.open()
    # get the user_id for the given username
    db.cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
    user_id = db.cursor.fetchone()
    if user_id is None:
        db.close()
        return 0, 0

    user_id = user_id[0]

    # get the token usage from the statistics table
    db.cursor.execute(f"SELECT total_tokens_used, prompt_tokens, completion_tokens FROM statistics WHERE user_id = {user_id}")
    result = db.cursor.fetchone()
    db.close()
    if result is None:
        return 0, 0 

    prompt_tokens_used = result[1] if result[1] is not None else 0
    completion_tokens_used = result[2] if result[2] is not None else 0
    prompt_cost = round(prompt_tokens_used * 0.03 / 1000, 3)
    completion_cost = round(completion_tokens_used * 0.06 / 1000, 3)
    total_cost = round(prompt_cost + completion_cost, 3)
    return result[0], total_cost

def count_tokens(message):
    return MessageParser.num_tokens_from_string(message)

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
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")
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
    if count_tokens(message.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt is too long")    
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

    # get the user's notes directory and settings file
    user_notes_dir = os.path.join(users_dir, user.username, 'notes')
    settings_file = os.path.join(users_dir, user.username, 'settings.json')

    # create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:

        # copy the user's notes directory, settings file and memory file to the temporary directory
        shutil.copytree(user_notes_dir, os.path.join(temp_dir, 'notes'))
        shutil.copy2(settings_file, os.path.join(temp_dir, 'settings.json'))
        shutil.copy2(json_file_path, os.path.join(temp_dir, 'memory.json'))

        # get current date
        current_date = datetime.now().strftime("%Y%m%d")

        # create zip filename
        zip_filename = f"{user.username}_{current_date}_clang_data.zip"

        # zip the temporary directory
        shutil.make_archive(os.path.join(users_dir, user.username, 'data'), 'zip', temp_dir)

        # rename the zip file
        shutil.move(os.path.join(users_dir, user.username, 'data.zip'), os.path.join(users_dir, user.username, zip_filename))

    # serve the zip file
    return FileResponse(os.path.join(users_dir, user.username, zip_filename), media_type="application/zip", filename=zip_filename)


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
    wipe_all_memories(user.username)
    stop_database(user.username)
    # remove all users recent messages
    await BrainProcessor.delete_recent_messages(user.username)
    # delete the whole user directory, using ignore_errors=True to avoid errors for the db file that is still open
    shutil.rmtree(os.path.join(users_dir, user.username), ignore_errors=True)
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
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(users_dir, username))
        
        # Check for 'memory.json', and 'settings.json'
        if 'memory.json' not in os.listdir(os.path.join(users_dir, username)) or \
        'settings.json' not in os.listdir(os.path.join(users_dir, username)):
            raise HTTPException(status_code=400, detail="Zip file is missing required files")

        # Verify 'memory.json' is a valid JSON file
        try:
            with open(os.path.join(users_dir, username, 'memory.json')) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="'memory.json' is not a valid JSON file")

        # Verify 'settings.json' is a valid JSON file
        try:
            with open(os.path.join(users_dir, username, 'settings.json')) as f:
                json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="'settings.json' is not a valid JSON file")

        # Import the data into memory
        import_file_to_memory(path=os.path.join(users_dir, username, 'memory.json'), replace=True, username=username)

        # Delete the zip file
        os.remove(file_path)
    else:
        raise HTTPException(status_code=400, detail="Wrong file format!")

    return JSONResponse(content={'message': 'User data uploaded successfully'})

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

# no token message route
@router.post("/notoken_message/",
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

@router.get("/admin/statistics", tags=["Admin"],
            summary="Get statistics",
    description="This endpoint allows you to get statistics about the users.",
    response_description="Returns statistics about the users.",
    responses={
        200: {
            "description": "Statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "total_users": 1,
                        "total_messages": 1,
                        "total_tokens_used": 1,
                        "total_voice_usage": 1,
                        "user_statistics": [
                            {
                                "username": "user",
                                "amount_of_messages": 1,
                                "total_tokens_used": 1,
                                "voice_usage": 1
                            }
                        ]
                    }
                }
            },
        },
    },)
async def get_statistics():
    db = Database()
    db.open()
    db.cursor.execute("SELECT * FROM users INNER JOIN statistics ON users.id = statistics.user_id")
    user_data = db.cursor.fetchall()
    db.close()
    
    # Calculate overall statistics
    total_users = len(user_data)
    # user[0] = id:
    # user[1] = username:
    # user[2] = password:
    # user[3] = session_token:
    # user[4] = message_history:
    # user[5] = has_access:
    # user[6] = role:
    # user[7] = id:
    # statistics
    # user[8] = user_id:
    # user[9] = amount_of_messages:
    # user[10] = total_tokens_used:
    # user[11] = prompt_tokens:
    # user[12] = completion_tokens:
    # user[13] = voice_usage:
    total_messages = sum([user[9] for user in user_data])
    total_tokens_used = sum([user[10] for user in user_data])
    total_voice_usage = sum([user[13] for user in user_data])

    # Prepare user statistics
    user_statistics = []
    for user in user_data:
        user_statistics.append({
            "username": user[1],
            "role": user[6],
            "amount_of_messages": user[9],
            "total_tokens_used": user[10],
            "voice_usage": user[13]
        })

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "total_tokens_used": total_tokens_used,
        "total_voice_usage": total_voice_usage,
        "user_statistics": user_statistics
    }

@router.get("/{file_path:path}")
async def read_file(file_path: str):
    try:
        if os.path.exists(f'static/{file_path}'):
            response = FileResponse(f'static/{file_path}')
            response.headers["Cache-Control"] = "public, max-age=86400"
            return response
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")