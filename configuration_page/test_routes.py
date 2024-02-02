import os

import openai
import pytest
from fastapi.testclient import TestClient

from config import CONFIGURATION_URL
from launcher import create_app
from user_management.session import session_factory


@pytest.fixture
def client(tmp_path):
    tmp_user_env_file = tmp_path / "user.env"
    os.environ["SINGLE_USER"] = "true"
    os.environ["OPENAI_API_KEY"] = ""
    openai.api_key = ""
    os.environ["CLANG_SYSTEM_CONFIGURATION_FILE"] = str(tmp_user_env_file)
    if os.path.exists("config.db"):
        os.remove("config.db")
    os.environ["NEW_DATABASE_URL"] = "sqlite:///config.db"
    session_factory.get_refreshed()

    yield TestClient(create_app())

    if os.path.exists("config.db"):
        os.remove("config.db")


def test_configuration(client):
    response = client.get(CONFIGURATION_URL)
    assert response.status_code == 200


def test_middleware_redirects(client):
    response = client.get("/")
    assert response.url.path == CONFIGURATION_URL


def test_middleware_redirects_random_url(client):
    response = client.get("/non-existent-url/")
    assert response.url.path == CONFIGURATION_URL


def test_update_configuration(client):
    test_data = {"OPENAI_API_KEY": "new_key_value"}

    response = client.post(CONFIGURATION_URL, json=test_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Configuration updated successfully"}
    assert openai.api_key == "new_key_value"


def test_update_configuration_missing_required(client):
    test_data = {"INVALID_KEY": "new_key_value"}
    response = client.post(CONFIGURATION_URL, json=test_data)
    assert (
        response.status_code == 422
    ), f"""
Expected status code to be 422, but got {response.status_code}
Json: {response.json()}
"""
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "OPENAI_API_KEY"],
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]
    }
