from datetime import datetime, timedelta, timezone
import json
import os
from fastapi import APIRouter, Depends, Query,  FastAPI, HTTPException, BackgroundTasks, File, Request, UploadFile, WebSocket
from fastapi.responses import StreamingResponse, Response
from utils import process_message, OpenAIResponser, upload_audio
from authentication import Authentication
from pydantic import BaseModel
from classes import User, UserCheckToken, UserName, editSettings, userMessage
import openai
from utils import load_addons

router = APIRouter()

connections = {}

PRODUCTION = os.environ['PRODUCTION']
isOnHttps = PRODUCTION # False

users_dir = 'users/' # end with a slash


def get_token(request: Request):
    return request.cookies.get('session_token')

async def send_debug_message(username: str, message: str):
    if username in connections:
        print(f"Sending message to user {username}:\n{message}")
        await connections[username].send_text(message)
    else:
        print(f"No active websocket connection for user {username}")


@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            print(f'User {username} sent: {data}')
            # Send a response back to the client
            await websocket.send_text(f'Received: {data}')
    except:
        # Handle disconnection
        del connections[username]

# register route
@router.post("/register/",
    tags=["Authentication"])
async def register(user: User, response: Response):
    with Authentication() as auth:
        session_token = auth.register(user.username, user.password)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == 'true':
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=".airobin.net")
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=".airobin.net")
        else:
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date)
        return {'message': 'User registered successfully'}
    else:
        raise HTTPException(status_code=400, detail="User registration failed")
    
# login route
@router.post("/login/",
    tags=["Authentication"])
async def login(user: User, response: Response):
    with Authentication() as auth:
        session_token = auth.login(user.username, user.password)
    if session_token:
        expiracy_date = datetime.now(timezone.utc) + timedelta(days=90)
        if PRODUCTION == 'true':
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=".airobin.net")
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date, domain=".airobin.net")
        else:
            response.set_cookie(key="session_token", value=session_token, secure=True, httponly=False, samesite="None", expires=expiracy_date)
            response.set_cookie(key="username", value=user.username, secure=True, httponly=False, samesite="None", expires=expiracy_date)
        return {'message': 'User logged in successfully'}
    else:
        raise HTTPException(status_code=401, detail="User login failed")
    
# logout route
@router.post("/logout/",
    tags=["Authentication"])
async def logout(user: UserCheckToken):
    with Authentication() as auth:
        success = auth.logout(user.username, user.session_token)
    if success:
        return {'message': 'User logged out successfully'}
    else:
        raise HTTPException(status_code=401, detail="User logout failed")
    
# check token route
@router.post("/check_token/",
    tags=["Authentication"])
async def check_token(user: UserCheckToken):
    with Authentication() as auth:
        success = auth.check_token(user.username, user.session_token)
    if success:
        return {'message': 'Token is valid'}
    else:
        raise HTTPException(status_code=401, detail="Token is invalid")
    
# load settings route
@router.post("/load_settings/",
    tags=["Settings"])
async def handle_get_settings(request: Request, user: UserName):
    session_token = request.cookies.get("session_token")
    print('session_token: ' + str(session_token))
    with Authentication() as auth:
        success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    load_addons(user.username, users_dir)
    with open(users_dir + user.username + '/settings.json', 'r') as f:
        settings = json.load(f)
    print(settings)
    return settings

# update settings route
@router.post("/update_settings/",
    tags=["Settings"])
async def handle_update_settings(request: Request, user: editSettings):
    session_token = request.cookies.get("session_token")
    with Authentication() as auth:
        success = auth.check_token(user.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    # create the directory if it doesn't exist
    if not os.path.exists(users_dir + user.username):
        os.makedirs(users_dir + user.username)
    # check if the settings file exists
    if not os.path.exists(users_dir + user.username + '/settings.json'):
        # create the settings file
        with open(users_dir + user.username + '/settings.json', 'w') as f:
            json.dump({}, f)
    with open(users_dir + user.username + '/settings.json', 'r') as f:
        settings = json.load(f)
    settings[user.addon] = user.enabled
    with open(users_dir + user.username + '/settings.json', 'w') as f:
        json.dump(settings, f)
    return settings

# openAI response route
@router.post("/message/",
    tags=["Messaging"])
async def handle_message(request: Request, message: userMessage, audio_path: str = None, background_tasks: BackgroundTasks = None):
    session_token = request.cookies.get("session_token")
    with Authentication() as auth:
        success = auth.check_token(message.username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    return await process_message(message.prompt,message. username, audio_path, background_tasks, users_dir)

# openAI response route without modules
@router.post("/message_no_modules/",
    tags=["Messaging"])
async def handle_message_no_modules(request: Request, message: userMessage, audio_path: str = None):
    session_token = request.cookies.get("session_token")
    with Authentication() as auth:
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
    tags=["Messaging"])
async def handle_message_audio(username: str, session_token: str, audio_file: UploadFile, background_tasks: BackgroundTasks = None):
    with Authentication() as auth:
        success = auth.check_token(username, session_token)
    if not success:
        raise HTTPException(status_code=401, detail="Token is invalid")
    return await upload_audio(users_dir + username, audio_file, background_tasks)