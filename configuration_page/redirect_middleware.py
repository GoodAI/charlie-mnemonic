import os

import openai
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import STATIC, CONFIGURATION_URL


def is_configuration_missing(request: Request):
    from configuration_page import configuration_meta_list

    for meta in configuration_meta_list:
        if meta.is_valid and not meta.is_valid():
            return True
    return False


class RedirectToConfigurationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "GET"
            and not request.url.path.startswith(f"/{STATIC}/")
            and not request.url.path.startswith(CONFIGURATION_URL)
        ):
            if is_configuration_missing(request):
                return RedirectResponse(url=CONFIGURATION_URL)

        return await call_next(request)
