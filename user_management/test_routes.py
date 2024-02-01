import os

import pytest
from fastapi.testclient import TestClient

from launcher import create_app


@pytest.fixture
def client():
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    if os.path.exists("test.db"):
        os.remove("test.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///test.db?cache=shared"
    from configuration_page.redirect_middleware import RedirectToConfigurationMiddleware
    from configuration_page.middleware import LoginRequiredCheckMiddleware
    from user_management.routes import router as user_management_router

    app = create_app(
        middlewares=[RedirectToConfigurationMiddleware, LoginRequiredCheckMiddleware],
        routers=[user_management_router],
    )
    client = TestClient(app)
    return client


@pytest.fixture
def authentication(client):
    from authentication import Authentication

    return Authentication()


def test_logout(client: TestClient, authentication):
    authentication.dao.create_tables()
    authentication.register("testuser", "testpassword", "Test User")

    login_response = client.post(
        "/login/", json={"username": "testuser", "password": "testpassword"}
    )
    assert (
        login_response.status_code == 200
    ), f"""
Expected status code to be 200, but got {login_response.status_code}
Json: {login_response.json()}
"""

    logout_response = client.post("/logout/", cookies=login_response.cookies, json={})
    assert (
        logout_response.status_code == 200
    ), f"""
Expected status code to be 200, but got {logout_response.status_code}
Json: {logout_response.json()}
"""
    assert "User logged out successfully" in logout_response.json()["message"]
