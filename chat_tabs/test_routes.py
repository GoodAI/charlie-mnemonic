import os

import pytest
from fastapi.testclient import TestClient

from agentmemory import get_client
from chat_tabs.dao import ChatTabsDAO
from launcher import create_app
from user_management.dao import UsersDAO
from user_management.session import session_factory

from sqlalchemy.orm import close_all_sessions
from sqlalchemy import create_engine


@pytest.fixture
def app():
    os.environ["ORIGINS"] = "*"
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    test_db_path = "sqlite:///test.db"
    os.environ["NEW_DATABASE_URL"] = test_db_path

    # Ensure any existing database connections are closed before deleting the file
    if session_factory.engine:
        session_factory.engine.dispose()

    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except PermissionError:
            print(
                "PermissionError when trying to delete test.db, file might be in use."
            )

    session_factory.get_refreshed()
    from chat_tabs.routes import router as chat_tabs_router

    application = create_app(routers=[chat_tabs_router])

    yield application

    # Properly close all sessions and dispose the engine after tests
    close_all_sessions()
    if session_factory.engine:
        session_factory.engine.dispose()

    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
