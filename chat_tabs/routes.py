from fastapi import (
    APIRouter,
    Request,
)
from fastapi.templating import Jinja2Templates

import logs
from chat_tabs.dao import ChatTabsDAO
from classes import (
    UserName,
)
from database import Database
from simple_utils import get_root
from user_management.dao import UsersDAO

logger = logs.Log("routes", "routes.log").get_logger()

from config import STATIC, LOGIN_REQUIRED

router = APIRouter()
templates = Jinja2Templates(directory=get_root(STATIC))


@router.post("/get_chat_tabs/", tags=[LOGIN_REQUIRED])
async def get_chat_tabs(request: Request, user: UserName):
    with UsersDAO() as users_dao, ChatTabsDAO() as chat_tabs_dao:
        user_id = users_dao.get_user_id(user.username)
        tab_data = chat_tabs_dao.get_tab_data(user_id) or []
        active_tab_data = chat_tabs_dao.get_active_tab_data(user_id)
        processed_tab_data = [tab for tab in tab_data if tab.is_enabled]
        if active_tab_data is None:
            active_tab_data = {}
        return {
            "tab_data": processed_tab_data,
            "active_tab_data": active_tab_data,
        }
