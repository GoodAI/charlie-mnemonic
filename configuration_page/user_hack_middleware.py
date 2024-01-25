from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from classes import LoginUser
from routes import login


class LoginAdminMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method == "GET":
            session_token = request.cookies.get("session_token")

            if session_token is None:
                await login(LoginUser(username="admin", password="admin"), response)
                return RedirectResponse(url=request.url.path)

        return response