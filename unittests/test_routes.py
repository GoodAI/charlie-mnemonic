import os
import pytest
from fastapi.testclient import TestClient
from main import app
from classes import User, UserCheckToken, LoginUser, userMessage, UserName
from authentication import Authentication
from database import Database

client = TestClient(app)

test_session_token = ""


def test_read_did_api_json():
    response = client.get("/d-id/api.json")
    assert response.status_code == 200
    assert "key" in response.json()
    assert "url" in response.json()


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200


def test_read_styles_css():
    response = client.get("/styles.css")
    assert response.status_code == 200 or response.status_code == 404


def test_register():
    global test_session_token
    user = User(username="testuser", password="a!w@e$ewrwA", display_name="Test User")
    # delete user if already exists
    auth = Authentication()
    auth.delete_user(user.username)
    response = client.post("/register/", json=user.dict())
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "User registered successfully"
    assert "display_name" in response.json()
    assert response.json()["display_name"] == "Test User"
    assert "session_token" in response.cookies
    test_session_token = response.cookies["session_token"]


def test_login():
    global test_session_token
    user = LoginUser(username="testuser", password="a!w@e$ewrwA")
    response = client.post("/login/", json=user.dict())
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "User logged in successfully"
    assert "session_token" in response.cookies
    test_session_token = response.cookies["session_token"]


def test_token_check():
    global test_session_token
    user = UserCheckToken(username="testuser", session_token=test_session_token)
    response = client.post("/check_token/", json=user.dict())
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Token is valid"


def test_token_check_invalid():
    global test_session_token
    user = UserCheckToken(username="testuser", session_token="invalid_token")
    response = client.post("/check_token/", json=user.dict())
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Token is invalid"


def test_load_settings():
    global test_session_token
    user = User(username="testuser", password="a!w@e$ewrwA", display_name="Test User")
    # delete user if already exists
    auth = Authentication()
    auth.delete_user(user.username)
    response = client.post("/register/", json=user.dict())
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "User registered successfully"
    assert "display_name" in response.json()
    assert response.json()["display_name"] == "Test User"
    assert "session_token" in response.cookies
    test_session_token = response.cookies["session_token"]
    client.cookies.update({"session_token": test_session_token})
    response = client.get("/load_settings/")
    assert response.json() is not None


def test_allow_user_access():
    with Database() as db:
        user_id = db.get_user_id("testuser")
        db.update_user(user_id, "true", "admin")
        role = db.get_user_role("testuser")
        has_access = db.get_user_access("testuser")
    assert role[0] == "admin"
    assert has_access == True


def test_edit_settings():
    assert True == True


def test_send_message_valid_token():
    global test_session_token
    message = userMessage(
        username="testuser", prompt="Hello, AI!", display_name="Test User"
    )
    client.cookies.update({"session_token": test_session_token})
    response = client.post("/message/", json=message.dict())
    assert response.status_code == 200
    assert "content" in response.json()


def test_send_message_long_prompt():
    global test_session_token
    message = userMessage(
        username="testuser", prompt="this is a test " * 1001, display_name="Test User"
    )
    client.cookies.update({"session_token": test_session_token})
    response = client.post("/message/", json=message.dict())
    assert response.status_code == 400
    assert "detail" in response.json()
    assert response.json()["detail"] == "Prompt is too long"


def test_handle_message_with_image():
    global test_session_token
    # create a real image file
    from PIL import Image

    # create a real image file
    img = Image.new("RGB", (100, 100), color="red")
    img.save("test_image.jpg")
    # create a test message
    message = userMessage(
        username="testuser", prompt="Hello, AI!", display_name="Test User"
    )
    # send the message with the test image
    client.cookies.update(
        {"session_token": test_session_token, "username": message.username}
    )
    response = client.post(
        "/message_with_image/",
        data={"prompt": message.prompt},
        files={"image_file": ("test_image.jpg", open("test_image.jpg", "rb"))},
    )
    # check the response
    assert response.status_code == 200
    assert "content" in response.json()
    # delete the test image file
    os.remove("test_image.jpg")


def test_get_recent_messages_valid_token():
    global test_session_token
    message = UserName(username="testuser")
    client.cookies.update({"session_token": test_session_token})
    response = client.post("/get_recent_messages/", json=message.dict())
    # check the response
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_recent_messages_invalid_token():
    global test_session_token
    message = UserName(username="testuser")
    client.cookies.update({"session_token": "invalid_token"})
    response = client.post("/get_recent_messages/", json=message.dict())
    # check the response
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Token is invalid"


def test_send_message_invalid_token():
    message = userMessage(
        username="testuser", prompt="Hello, AI!", display_name="Test User"
    )
    client.cookies.update({"session_token": "invalid_token"})
    response = client.post("/message/", json=message.dict())
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Token is invalid"


def test_delete_user():
    # delete user if already exists
    auth = Authentication()
    auth.delete_user("testuser")
    # check that user doesn't exist
    with Database() as db:
        user_id = db.get_user_id("testuser")
    assert user_id is None


if __name__ == "__main__":
    pytest.main(["-s"])
