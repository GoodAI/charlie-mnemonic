import os
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.params import Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from classes import ConfigurationData
from config import STATIC, CONFIGURATION_URL
from configuration_page import modify_settings
from database import Database
from simple_utils import get_root
from utils import SettingsManager

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


@router.post(CONFIGURATION_URL, response_class=JSONResponse)
async def update_configuration(
    OPENAI_API_KEY: str = Form(...),
    GOOGLE_CLIENT_SECRET_PATH: UploadFile = File(None),
):
    # TODO: security check for login
    try:
        filtered = {"OPENAI_API_KEY": OPENAI_API_KEY}
        #
        if GOOGLE_CLIENT_SECRET_PATH.size > 0:
            user_dir = SettingsManager.get_user_dir()
            file_path = f"{user_dir}/google_client_secret.json"
            with open(file_path, "wb") as f:
                f.write(GOOGLE_CLIENT_SECRET_PATH.file.read())
            filtered["GOOGLE_CLIENT_SECRET_PATH"] = file_path
            os.environ["GOOGLE_CLIENT_SECRET_PATH"] = file_path
        modify_settings(filtered)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
