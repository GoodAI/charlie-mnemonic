import os
from dataclasses import dataclass
from typing import Any
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import close_all_sessions
from starlette.websockets import WebSocketDisconnect

from launcher import create_app
from user_management.session import session_factory
from user_management.test_dao_user import dao_session


@pytest.fixture
def client():
    db_file = "user.db"
    db_url = f"sqlite:///{db_file}?cache=shared"
    os.environ["ORIGINS"] = "*"
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    os.environ["NEW_DATABASE_URL"] = db_url

    # Dispose of engine and close all sessions before starting tests
    if hasattr(session_factory, "engine") and session_factory.engine:
        session_factory.engine.dispose()
        close_all_sessions()

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError as e:
            print(
                f"Failed to delete {db_file} before tests due to PermissionError: {e}"
            )

    session_factory.get_refreshed()
    from configuration_page.redirect_middleware import RedirectToConfigurationMiddleware
    from configuration_page.middleware import LoginRequiredCheckMiddleware
    from user_management.routes import router as user_management_router

    app = create_app(
        middlewares=[RedirectToConfigurationMiddleware, LoginRequiredCheckMiddleware],
        routers=[user_management_router],
    )
    client = TestClient(app)
    yield client

    client.close()

    # Dispose of engine and close all sessions after tests
    if hasattr(session_factory, "engine"):
        session_factory.engine.dispose()
        close_all_sessions()

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError as e:
            print(f"Failed to delete {db_file} after tests due to PermissionError: {e}")


@pytest.fixture
def authentication(client):
    from authentication import Authentication

    return Authentication()


@dataclass
class LoggedInClient:
    client: TestClient
    cookie_header: str
    response: Any = None


@pytest.fixture
def logged_in_client(client, authentication):
    authentication.dao.create_tables()
    random_user_id = f"newuser_{uuid.uuid4().hex}"
    authentication.register(random_user_id, "testpassword", "Test User")

    response = client.post(
        "/login/", json={"username": random_user_id, "password": "testpassword"}
    )
    cookies = response.cookies
    cookie_header = "; ".join([f"{name}={value}" for name, value in cookies.items()])

    return LoggedInClient(client, cookie_header=cookie_header, response=response)


def test_logout(logged_in_client: LoggedInClient):
    logout_response = logged_in_client.client.post(
        "/logout/", headers={"Cookie": logged_in_client.cookie_header}, json={}
    )
    assert (
        logout_response.status_code == 200
    ), f"""
Expected status code to be 200, but got {logout_response.status_code}
Json: {logout_response.json()}
"""
    assert "User logged out successfully" in logout_response.json()["message"]


def test_login_bad_password(dao_session, client: TestClient, authentication):
    authentication.dao.create_tables()
    random_user_id = f"newuser_{uuid.uuid4().hex}"
    authentication.register(random_user_id, "testpassword", "Test User")

    login_response = client.post(
        "/login/", json={"username": random_user_id, "password": "incorrect_password"}
    )
    assert (
        login_response.status_code == 401
    ), f"""
Expected status code to be 401, but got {login_response.status_code}
Json: {login_response.json()}
"""


def test_login_nonexitent_user(dao_session, client: TestClient, authentication):
    login_response = client.post(
        "/login/",
        json={"username": "non-existent-user", "password": "incorrect_password"},
    )
    assert (
        login_response.status_code == 401
    ), f"""
Expected status code to be 401, but got {login_response.status_code}
Json: {login_response.json()}
"""


def test_login_no_password(dao_session, client: TestClient, authentication):
    login_response = client.post("/login/", json={"username": "non-existent-user"})
    assert (
        login_response.status_code == 422
    ), f"""
Expected status code to be 422, but got {login_response.status_code}
Json: {login_response.json()}
"""


def test_websocket_endpoint(logged_in_client, authentication):
    with logged_in_client.client.websocket_connect(
        "/ws/authtest", headers={"Cookie": logged_in_client.cookie_header}
    ) as websocket:
        data = websocket.receive_text()
        assert data == "Connection successful"

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_text()


def test_websocket_endpoint_not_logged_in(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/authtest"):
            pass
