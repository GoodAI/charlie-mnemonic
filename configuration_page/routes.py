from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.params import Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from classes import ConfigurationData
from config import STATIC, CONFIGURATION_URL
from configuration_page import modify_settings
from database import Database
from simple_utils import get_root
from utils import SettingsManager
import os

templates = Jinja2Templates(directory=get_root(STATIC))
router = APIRouter()


@router.get(CONFIGURATION_URL, response_class=HTMLResponse)
async def configuration(request: Request):
    # TODO: security check for login
    version = SettingsManager.get_version()
    config = ConfigurationData.for_frontend()

    return templates.TemplateResponse(
        "configuration.html",
        context=locals(),
    )


@router.post(CONFIGURATION_URL)
async def update_configuration(
    request: Request,
    OPENAI_API_KEY: str = Form(None),
    ANTHROPIC_API_KEY: str = Form(None),
    GOOGLE_CLIENT_SECRET_PATH: UploadFile = File(None),
):
    try:
        filtered = {}
        if OPENAI_API_KEY:
            filtered["OPENAI_API_KEY"] = OPENAI_API_KEY
        if ANTHROPIC_API_KEY:
            filtered["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

        if not filtered:
            raise ValueError(
                "Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be provided"
            )

        if GOOGLE_CLIENT_SECRET_PATH and GOOGLE_CLIENT_SECRET_PATH.size > 0:
            file_path = os.path.join("users", "google_client_secret.json")
            with open(file_path, "wb") as f:
                f.write(GOOGLE_CLIENT_SECRET_PATH.file.read())
            filtered["GOOGLE_CLIENT_SECRET_PATH"] = file_path
            os.environ["GOOGLE_CLIENT_SECRET_PATH"] = file_path

        modify_settings(filtered)

        return JSONResponse(
            content={"message": "Configuration updated successfully", "redirect": "/"}
        )
    except Exception as e:
        print(f"Error in update_configuration: {str(e)}")
        return JSONResponse(status_code=400, content={"error": str(e)})
