from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from classes import UserCheckToken
from config import LOGIN_REQUIRED, SINGLE_USER_USERNAME
from user_management.dao import UsersDAO
from user_management.models import Users


def get_route(request: Request) -> Match:
    for route in request.app.router.routes:
        match, scope = route.matches(request)
        if match == Match.FULL:
            return route


def set_user_as_logged_in(session_token: str, username: str, request: Request) -> Users:
    with UsersDAO() as users_dao:
        user = users_dao.get_user(username)
        request.state.user = user
    return user


def check_token_login(request: Request) -> bool:
    session_token = request.cookies.get("session_token")
    username = request.cookies.get("username")
    if session_token:
        from authentication import Authentication

        auth = Authentication()
        if auth.check_token(username=username, session_token=session_token):
            return True
    try:
        return request.state.user is not None
    except AttributeError:
        # shouldn't really happen, only if LoginAdminMiddleware and LoginRequiredCheckMiddleware are
        # missing (in some test setup for example)
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
            user_check_token = set_user_as_logged_in(session_token, username, request)
        else:
            request.state.user = None

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
        request.state.user = None
        username = SINGLE_USER_USERNAME

        new_session_token = None
        if not check_token_login(request):
            from authentication import Authentication

            auth = Authentication()
            new_session_token = auth.force_login(username)
            set_user_as_logged_in(new_session_token, username, request)

        response = await call_next(request)

        if new_session_token:
            from user_management.routes import set_login_cookies

            set_login_cookies(new_session_token, username, response)

        return response
