import os
import shutil

from fastapi import (
    APIRouter,
    Request,
    HTTPException,
)
from fastapi.templating import Jinja2Templates

import logs
from agentmemory import wipe_all_memories, stop_database
from chat_tabs.dao import ChatTabsDAO
from classes import (
    EditTabDescription,
    RecentMessages,
)
from routes import users_dir
from simple_utils import get_root
from utils import MessageParser, BrainProcessor

logger = logs.Log("routes", "routes.log").get_logger()

from config import STATIC, LOGIN_REQUIRED

router = APIRouter()
templates = Jinja2Templates(directory=get_root(STATIC))


@router.post("/get_chat_tabs/", tags=[LOGIN_REQUIRED])
async def get_chat_tabs(request: Request):
    with ChatTabsDAO() as chat_tabs_dao:
        user_id = request.state.user.id
        tab_data = chat_tabs_dao.get_tab_data(user_id) or []
        active_tab_data = chat_tabs_dao.get_active_tab_data(user_id)
        processed_tab_data = [tab for tab in tab_data if tab.is_enabled]
        if active_tab_data is None:
            active_tab_data = {}
        return {
            "tab_data": processed_tab_data,
            "active_tab_data": active_tab_data,
        }


@router.post("/delete_chat_tab/", tags=[LOGIN_REQUIRED])
async def delete_chat_tab(request: Request, user: RecentMessages):
    with ChatTabsDAO() as chat_tabs_dao:
        if chat_tabs_dao.disable_tab(request.state.user.id, chat_id=user.chat_id):
            return {"message": "Tab deleted successfully"}
        return {"message": "Error while updating tab"}


@router.post("/get_recent_messages/", tags=[LOGIN_REQUIRED])
async def get_recent_messages(request: Request, message: RecentMessages):
    with ChatTabsDAO() as chat_tabs_dao:
        user = request.state.user
        tab_data = chat_tabs_dao.get_tab_data(user.id)
        active_tab_data = chat_tabs_dao.get_active_tab_data(user.id)

        tab_exists = False
        for tab in tab_data:
            if tab.chat_id == message.chat_id:
                tab_exists = True
                break
        if not tab_exists:
            # if not, insert a new row
            chat_tabs_dao.insert_tab_data(
                user.id,
                message.chat_id,
                f"New Chat",
                message.chat_id,
                False,
            )
        if active_tab_data is None or message.chat_id != active_tab_data.chat_id:
            chat_tabs_dao.set_active_tab(user.id, message.chat_id)

        recent_messages = await MessageParser.get_recent_messages(
            message.username, message.chat_id
        )
    if not user.has_access:
        logger.info(f"user {message.username} does not have access")
        raise HTTPException(
            status_code=400,
            detail="You do not have access yet, ask permission from the administrator or wait for your trial to start",
        )
    return {"recent_messages": recent_messages}


@router.post("/delete_data_keep_settings/", tags=[LOGIN_REQUIRED])
async def handle_delete_data_keep_settings(request: Request):
    user = request.state.user
    wipe_all_memories(user.username)
    stop_database(user.username)
    # remove all users recent messages
    await BrainProcessor.delete_recent_messages(user.username)
    # remove chat tabs from the database
    with ChatTabsDAO() as chat_tabs_dao:
        chat_tabs_dao.delete_tab_data(request.state.user.id)
    return {"message": "User data deleted successfully"}


@router.post(
    "/delete_data/",
    tags=["Data", LOGIN_REQUIRED],
    summary="Delete user data",
    description="This endpoint allows you to delete the user's data by providing a username and session token. If the token is valid, the user's data will be deleted. If the token is invalid, an HTTP 401 error will be returned.",
    response_description="Returns a success message if the token is valid, else returns an HTTPException with status code 401.",
    responses={
        200: {
            "description": "User data deleted successfully",
            "content": {
                "application/json": {
                    "example": {"message": "User data deleted successfully"}
                }
            },
        },
        401: {
            "description": "Token is invalid",
            "content": {
                "application/json": {"example": {"detail": "Token is invalid"}}
            },
        },
    },
)
async def handle_delete_data(request: Request):
    user = request.state.user
    wipe_all_memories(user.username)
    stop_database(user.username)
    await BrainProcessor.delete_recent_messages(user.username)
    with ChatTabsDAO() as db:
        db.delete_tab_data(user.id)
    shutil.rmtree(os.path.join(users_dir, user.username), ignore_errors=True)
    return {"message": "User data deleted successfully"}


# update_chat_tab_description route
@router.post("/update_chat_tab_description/", tags=[LOGIN_REQUIRED])
async def update_chat_tab_description(request: Request, user: EditTabDescription):
    with ChatTabsDAO() as chat_tabs_dao:
        chat_tabs_dao.update_tab_description(user.chat_id, user.description)
    return {"message": "Tab description updated successfully"}
