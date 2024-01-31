from fastapi import APIRouter, HTTPException, Request
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
    with Database() as db:
        daily_limit = db.get_daily_limit()
        maintenance_mode = db.get_maintenance_mode()

    config = ConfigurationData.for_frontend()

    return templates.TemplateResponse(
        "configuration.html",
        context=locals(),
    )


@router.post(CONFIGURATION_URL, response_class=JSONResponse)
async def update_configuration(config_data: ConfigurationData):
    # TODO: security check for login
    try:
        filtered = {k: v for k, v in config_data.dict().items() if v is not None}
        modify_settings(filtered)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
