from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from classes import UserCheckToken
from config import LOGIN_REQUIRED, SINGLE_USER_USERNAME


def get_route(request: Request) -> Match:
    for route in request.app.router.routes:
        match, scope = route.matches(request)
        if match == Match.FULL:
            return route


def login_user_request(
    session_token: str, username: str, request: Request
) -> UserCheckToken:
    user_check_token = UserCheckToken(username=username, session_token=session_token)
    request.state.user = user_check_token
    return user_check_token


def check_token_login(request: Request) -> bool:
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    if session_token:
        from authentication import Authentication

        auth = Authentication()
        return auth.check_token(username=username, session_token=session_token)
    return False


class LoginRequiredCheckMiddleware(BaseHTTPMiddleware):
    """
    This middleware checks if the route has the LOGIN_REQUIRED
    tag and throws 401 if it does and the user is not logged in.
    It also sets request.state.user to the user of type UserCheckToken if the user is logged in.
    """

    async def dispatch(self, request: Request, call_next):
        user_check_token = None

        if check_token_login(request):
            username = request.cookies.get("username")
            session_token = request.cookies.get("session_token")
            user_check_token = login_user_request(session_token, username, request)

        route = get_route(request)
        if route and getattr(route, "tags", None):
            tags = route.tags
            if LOGIN_REQUIRED in tags and not user_check_token:
                raise HTTPException(
                    status_code=401, detail=f"Not authenticated for {route}"
                )

        return await call_next(request)


class LoginAdminMiddleware(BaseHTTPMiddleware):
    """
    This middleware automatically logs in user if not logged in.
    This is used for single user mode.
    """

    async def dispatch(self, request: Request, call_next):
        username = SINGLE_USER_USERNAME

        new_session_token = None
        if not check_token_login(request):
            from authentication import Authentication

            auth = Authentication()
            new_session_token = auth.force_login(username)
            login_user_request(new_session_token, username, request)

        response = await call_next(request)

        if new_session_token:
            from user_management.routes import set_login_cookies

            set_login_cookies(new_session_token, username, response)

        return response
