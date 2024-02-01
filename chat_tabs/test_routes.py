import os

import pytest
from fastapi.testclient import TestClient

from chat_tabs.dao import ChatTabsDAO
from launcher import create_app


@pytest.fixture
def client():
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    if os.path.exists("test.db"):
        os.remove("test.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///test.db?cache=shared"
    from chat_tabs.routes import router as chat_tabs_router

    app = create_app(
        middlewares=[],
        routers=[chat_tabs_router],
    )
    client = TestClient(app)
    return client


def test_get_chat_tabs(client: TestClient):
    chat_tabs_dao = ChatTabsDAO()
    chat_tabs_dao.insert_tab_data(1, "chat123", "Test Chat", "tab123", True)

    response = client.post(
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
    assert response.json() == {
        "tab_data": [],
        "active_tab_data": {},
    }
