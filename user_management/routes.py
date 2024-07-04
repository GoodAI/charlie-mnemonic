from datetime import datetime, timedelta, timezone
import json
import os

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.params import Form
from fastapi.responses import (
    Response,
)
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.responses import RedirectResponse
from starlette.websockets import WebSocket

import logs
from authentication import Authentication
from classes import (
    LoginUser,
    User,
    UserCheckToken,
)
from common.websocket import authenticate_websocket
from config import STATIC, LOGIN_REQUIRED, PRODUCTION, origins, ADMIN_REQUIRED
from configuration_page.middleware import set_user_as_logged_in
from simple_utils import get_root
from user_management.dao import UsersDAO, AdminControlsDAO

templates = Jinja2Templates(directory=get_root(STATIC))
router = APIRouter()

logger = logs.Log("routes-users", "routes.log").get_logger()


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
async def login(request: Request, user: LoginUser, response: Response):
    auth = Authentication()
    session_token = auth.login(user.username, user.password)
    if session_token:
        set_login_cookies(session_token, user.username, response)
        set_user_as_logged_in(session_token, user.username, request)
        return {"message": "User logged in successfully"}
    else:
        raise HTTPException(status_code=401, detail="User login failed")


def set_login_cookies(
    session_token: str, username: str, response: Response, duration_days: int = 90
) -> None:
    expiracy_date = datetime.now(timezone.utc) + timedelta(days=duration_days)
    # Set Samesite to Strict for local deployment
    cookie_params = {
        "httponly": False,
        "samesite": "Strict",
        "expires": expiracy_date,
    }

    if PRODUCTION:
        cookie_params["domain"] = origins()

    response.set_cookie(key="session_token", value=session_token, **cookie_params)

    response.set_cookie(key="username", value=username, **cookie_params)


# logout route
@router.post(
    "/logout/",
    tags=["Authentication", LOGIN_REQUIRED],
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
async def logout(request: Request):
    auth = Authentication()
    success = auth.logout(request.state.user.username)
    request.cookies["session_token"] = ""
    request.cookies["username"] = ""
    if success:
        return {"message": "User logged out successfully"}
    else:
        raise HTTPException(status_code=401, detail="User logout failed")


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
        set_login_cookies(session_token, user.username, response)
        return {
            "message": "User registered successfully",
            "display_name": user.display_name,
        }
    else:
        raise HTTPException(status_code=400, detail="User registration failed")


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


@router.post("/admin/update_user/{user_id}", tags=[LOGIN_REQUIRED, ADMIN_REQUIRED])
async def update_user(
    request: Request,
    user_id: int,
    has_access: str = Form(...),
    role: str = Form(...),
):
    user = request.state.user
    with UsersDAO() as db:
        has_access_bool = True if has_access == "true" else False
        db.update_user(user_id, has_access_bool, role)
        logger.info(f"User {user.username} (role: {user.role}) updated user: {user_id}")
        return {"message": f"User {user_id} updated successfully"}


@router.post("/admin/update_controls")
async def update_controls(
    request: Request,
    id: int = Form(...),
    daily_spending_limit: int = Form(...),
    allow_access: bool = Form(...),
    maintenance: bool = Form(...),
):
    with AdminControlsDAO() as db:
        if id == "" or id == None:
            id = 1
        db.update_admin_controls(
            id, daily_spending_limit, allow_access=allow_access, maintenance=maintenance
        )
    return RedirectResponse(url="/admin/statistics/1", status_code=303)


@router.websocket("/ws/authtest")
async def websocket_endpoint(websocket: WebSocket):
    await authenticate_websocket(websocket)
    await websocket.close()


from google_auth_oauthlib.flow import InstalledAppFlow
from gworkspace.google_auth import SCOPES, get_redirect_uri


@router.get("/oauth2callback")
async def oauth2callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not found"}

    flow = InstalledAppFlow.from_client_secrets_file(
        os.getenv("GOOGLE_CLIENT_SECRET_PATH"),
        SCOPES,
        redirect_uri=get_redirect_uri(),
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Save the credentials
    print(f"State: {request.query_params.get('state')}")  # Debug print
    username = get_username_from_state(request.query_params.get("state"))
    print(f"Username: {username}")  # Debug print
    full_path = os.path.join("users", username, "token.json")
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as token:
        token.write(creds.to_json())

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def authenticate_user(auth_code):
    CREDENTIALS_PATH = (
        os.getenv("GOOGLE_CLIENT_SECRET_PATH") or "users/google_client_secret.json"
    )
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_PATH,
        SCOPES,
        redirect_uri=get_redirect_uri(),
    )
    # Add these parameters to ensure we always get a refresh token
    flow.fetch_token(
        code=auth_code,
        # Include these additional parameters
        prompt="consent",
        access_type="offline",
    )
    credentials = flow.credentials
    return credentials


# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_state_file_path():
    return os.path.join(os.getcwd(), "users", "state_store.json")


def get_username_from_state(state):
    file_path = get_state_file_path()
    print(f"State file path: {file_path}")  # Debug print
    if not os.path.exists(file_path):
        print("State file does not exist")  # Debug print
        return None
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
            username = data.get(state)
            print(f"State data: {data}")  # Debug print
            print(f"Retrieved username for state {state}: {username}")  # Debug print
            return username
        except json.JSONDecodeError:
            print("Failed to decode JSON in state file")  # Debug print
            return None
