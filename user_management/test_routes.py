import os

import pytest
from fastapi.testclient import TestClient

from launcher import create_app
from user_management.session import session_factory
from user_management.test_dao import dao_session


@pytest.fixture
def client():
    os.environ["ORIGINS"] = "*"
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"

    if os.path.exists("user.db"):
        os.remove("user.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///user.db?cache=shared"

    session_factory.get_refreshed()
    from configuration_page.redirect_middleware import RedirectToConfigurationMiddleware
    from configuration_page.middleware import LoginRequiredCheckMiddleware
    from user_management.routes import router as user_management_router

    app = create_app(
        middlewares=[RedirectToConfigurationMiddleware, LoginRequiredCheckMiddleware],
        routers=[user_management_router],
    )
    yield TestClient(app)

    if os.path.exists("user.db"):
        os.remove("user.db")


@pytest.fixture
def authentication(client):
    from authentication import Authentication

    return Authentication()


def test_logout(dao_session, client: TestClient, authentication):
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


def test_login_bad_password(dao_session, client: TestClient, authentication):
    authentication.dao.create_tables()
    authentication.register("testuser", "testpassword", "Test User")

    login_response = client.post(
        "/login/", json={"username": "testuser", "password": "incorrect_password"}
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
