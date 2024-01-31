from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.responses import (
    Response,
)
from fastapi.templating import Jinja2Templates

from authentication import Authentication
from classes import (
    LoginUser,
)
from config import STATIC, LOGIN_REQUIRED, PRODUCTION, origins
from configuration_page.middleware import login_user_request
from simple_utils import get_root

templates = Jinja2Templates(directory=get_root(STATIC))
router = APIRouter()


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
        login_user_request(session_token, user.username, request)
        return {"message": "User logged in successfully"}
    else:
        raise HTTPException(status_code=401, detail="User login failed")


def set_login_cookies(
    session_token: str, username: str, response: Response, duration_days: int = 90
) -> None:
    expiracy_date = datetime.now(timezone.utc) + timedelta(days=duration_days)
    cookie_params = {
        "secure": PRODUCTION,
        "httponly": False,
        "samesite": "None",
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
    if success:
        return {"message": "User logged out successfully"}
    else:
        raise HTTPException(status_code=401, detail="User logout failed")
