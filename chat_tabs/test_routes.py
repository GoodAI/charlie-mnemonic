import os

import pytest
from fastapi.testclient import TestClient

from agentmemory import get_client
from chat_tabs.dao import ChatTabsDAO
from launcher import create_app
from user_management.dao import UsersDAO
from user_management.session import session_factory


@pytest.fixture
def app():
    os.environ["ORIGINS"] = "*"
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    if os.path.exists("test.db"):
        os.remove("test.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///test.db"

    session_factory.get_refreshed()
    from chat_tabs.routes import router as chat_tabs_router

    yield create_app(
        routers=[chat_tabs_router],
    )

    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def client(app):
    client = TestClient(app)
    return client


@pytest.fixture
def client_with_logged_user(app):
    client = TestClient(app)
    with UsersDAO() as users_dao:
        user_id = users_dao.add_user(
            username="testuser",
            password="testpassword",
            session_token="testtoken",
            display_name="Test User",
        )
        users_dao.update_user(user_id, access=True, role="admin")
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


def test_delete_chat_tab(client_with_logged_user: TestClient):
    username = "testuser"
    chat_id = "chat123"
    with UsersDAO() as users_dao, ChatTabsDAO() as chat_tabs_dao:
        user_id = users_dao.get_user_id(username)
        chat_tabs_dao.insert_tab_data(user_id, chat_id, "Test Chat", "tab123", True)

        tab_data = chat_tabs_dao.get_tab_data(user_id)
        assert len(tab_data) == 1, f"Expected 1 tab, got {len(tab_data)}"
        assert tab_data[0].is_enabled, "Tab should initially be enabled"

    response = client_with_logged_user.post(
        "/delete_chat_tab/",
        json={
            "username": username,
            "chat_id": chat_id,
        },
    )
    assert (
        response.status_code == 200
    ), f"Expected status code 200, got {response.status_code}"
    assert response.json() == {"message": "Tab deleted successfully"}
    assert len(tab_data) == 1, f"Expected 1 tab, got {len(tab_data)}"

    with ChatTabsDAO() as chat_tabs_dao:
        tab_data_after_deletion = chat_tabs_dao.get_tab_data(user_id)
        assert not tab_data_after_deletion[
            0
        ].is_enabled, "Tab should be disabled after deletion"


@pytest.fixture()
def setup_chat_tabs(client_with_logged_user: TestClient):
    with UsersDAO() as users_dao:
        user_id = users_dao.get_user_id("testuser")
    with ChatTabsDAO() as chat_tabs_dao:
        chat_tabs_dao.insert_tab_data(user_id, "chat123", "Test Chat", "tab123", True)
        chat_tabs_dao.set_active_tab(user_id, "tab123")


def test_empty_recent_messages(client_with_logged_user: TestClient, setup_chat_tabs):
    response = client_with_logged_user.post(
        "/get_recent_messages/",
        json={
            "username": "testuser",
            "chat_id": "chat123",
        },
    )

    assert (
        response.status_code == 200
    ), f"""
Expected status code 200, got {response.status_code}

{response.text}
"""
    assert response.json() == {
        "recent_messages": []
    }, f"Unexpected response content: {response.json()}"


@pytest.mark.usefixtures("setup_chat_tabs")
def test_delete_data_keep_settings(client_with_logged_user: TestClient):
    username = "testuser"
    with UsersDAO() as users_dao:
        user_id = users_dao.get_user_id(username)
    response = client_with_logged_user.post(
        "/delete_data_keep_settings/", json={"username": username}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User data deleted successfully"}

    with ChatTabsDAO() as chat_tabs_dao:
        assert chat_tabs_dao.get_tab_data(user_id) == []

    db_client = get_client(username=username)
    collections = db_client.list_collections()
    assert collections == []


@pytest.fixture
def client_with_data(app):
    client = TestClient(app)
    with UsersDAO() as users_dao:
        user_id = users_dao.add_user(
            "testuser", "password", "sessiontoken", "Test User"
        )
    with ChatTabsDAO() as chat_tabs_dao:
        chat_tabs_dao.insert_tab_data(user_id, "chat123", "Test Chat", "tab123", True)

    client.cookies.set("session_token", "sessiontoken")
    client.cookies.set("username", "testuser")
    return client, user_id


def test_delete_data(client_with_data):
    client, user_id = client_with_data

    response = client.post("/delete_data/")

    assert (
        response.status_code == 200
    ), "Expected status code 200 for successful data deletion"
    assert response.json() == {
        "message": "User data deleted successfully"
    }, f"Unexpected response content, {response.json()}"

    with ChatTabsDAO() as chat_tabs_dao:
        assert (
            chat_tabs_dao.get_tab_data(user_id) == []
        ), "Expected no chat tabs for the user after deletion"
