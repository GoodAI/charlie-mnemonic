import os

import pytest
from fastapi.testclient import TestClient

from chat_tabs.dao import ChatTabsDAO
from launcher import create_app
from user_management.dao import UsersDAO
from user_management.session import session_factory


@pytest.fixture
def app():
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    if os.path.exists("test.db"):
        os.remove("test.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///test.db"

    session_factory.get_refreshed()
    from chat_tabs.routes import router as chat_tabs_router

    return create_app(
        routers=[chat_tabs_router],
    )


@pytest.fixture
def client(app):
    client = TestClient(app)
    return client


@pytest.fixture
def client_with_logged_user(app):
    client = TestClient(app)
    with UsersDAO() as users_dao:
        users_dao.add_user(
            username="testuser",
            password="testpassword",
            session_token="testtoken",
            display_name="Test User",
        )
        print(users_dao.get_user_id("testuser"))
    client.cookies.set("session_token", "testtoken")
    client.cookies.set("username", "testuser")
    return client


def test_get_chat_tabs(client_with_logged_user: TestClient):
    with UsersDAO() as users_dao:
        user_id = users_dao.get_user_id("testuser")

    with ChatTabsDAO() as chat_tabs_dao:
        chat_tabs_dao.insert_tab_data(user_id, "chat123", "Test Chat", "tab123", True)

    response = client_with_logged_user.post(
        "/get_chat_tabs/",
        json={
            "username": "testuser",
        },
    )
    assert (
        response.status_code == 200
    ), f"""
Expected status code 200, got {response.status_code}
{response.json()}
    """
    response_json = response.json()

    # removing created_at from response to keep the test stable
    response_json["active_tab_data"].pop("created_at", None)
    for item in response_json["tab_data"]:
        item.pop("created_at", None)

    assert response_json == {
        "active_tab_data": {
            "chat_id": "chat123",
            "chat_name": "Test Chat",
            "id": 1,
            "is_active": True,
            "is_enabled": True,
            "tab_id": "tab123",
            "user_id": 2,
        },
        "tab_data": [
            {
                "chat_id": "chat123",
                "chat_name": "Test Chat",
                "id": 1,
                "is_active": True,
                "is_enabled": True,
                "tab_id": "tab123",
                "user_id": 2,
            }
        ],
    }
