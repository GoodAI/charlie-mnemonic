import pytest
from starlette.testclient import TestClient

from .dao import UsersDAO
from .test_routes import client


def test_register_success(client: TestClient):
    new_user = {
        "username": "newuser",
        "password": "newpassword",
        "display_name": "New User",
    }

    response = client.post("/register/", json=new_user)

    assert response.status_code == 200
    assert response.json() == {
        "message": "User registered successfully",
        "display_name": new_user["display_name"],
    }

    assert "session_token" in response.cookies
    assert "username" in response.cookies
    assert response.cookies["username"] == new_user["username"]

    with UsersDAO() as dao:
        user = dao.get_user(new_user["username"])
        assert user.username == new_user["username"]
        assert user.display_name == new_user["display_name"]
        assert user.session_token == response.cookies["session_token"]


def test_register_username_exists(client: TestClient):
    new_user = {
        "username": "newuser",
        "password": "newpassword",
        "display_name": "New User",
    }

    response = client.post("/register/", json=new_user)

    assert response.status_code == 200, "First registration should succeed"

    response = client.post("/register/", json=new_user)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Email already exists or other database error."
    }


@pytest.fixture
def setup_user_with_valid_token():
    with UsersDAO() as users_dao:
        users_dao.add_user(
            username="validuser",
            password="password",
            session_token="validtoken",
            display_name="Valid User",
        )
    return "validuser", "validtoken"


@pytest.fixture
def setup_user_with_invalid_token():
    with UsersDAO() as users_dao:
        users_dao.add_user(
            username="invaliduser",
            password="password",
            session_token="invalidtoken",
            display_name="Invalid User",
        )
    return "invaliduser", "wrongtoken"


def test_check_token_valid(client: TestClient, setup_user_with_valid_token):
    username, session_token = setup_user_with_valid_token

    response = client.post(
        "/check_token/", json={"username": username, "session_token": session_token}
    )

    assert response.status_code == 200, "Expected status code 200 for valid token"
    assert response.json() == {
        "message": "Token is valid"
    }, "Unexpected response content for valid token"


def test_check_token_invalid(client: TestClient, setup_user_with_invalid_token):
    username, invalid_token = setup_user_with_invalid_token

    response = client.post(
        "/check_token/", json={"username": username, "session_token": invalid_token}
    )

    assert response.status_code == 401, "Expected status code 401 for invalid token"
    assert (
        response.json().get("detail") == "Token is invalid"
    ), "Unexpected response content for invalid token"
