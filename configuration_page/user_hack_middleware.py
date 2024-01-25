from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from authentication import Authentication
from routes import set_login_cookies


class LoginAdminMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        session_token = request.cookies.get("session_token")

        if session_token is None:
            auth = Authentication()
            username = "admin"
            password = "admin"
            session_token = auth.login(username, password)
            set_login_cookies(session_token, username, response)

        return response
