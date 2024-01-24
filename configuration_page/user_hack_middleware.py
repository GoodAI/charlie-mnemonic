from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from classes import LoginUser
from routes import login


class LoginAdminMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        session_token = request.cookies.get("session_token")
        print(session_token)
        if session_token is None:
            print("Redirecting to login")
            result = await login(
                LoginUser(username="admin", password="admin"), response
            )
            print(result)
        return response
