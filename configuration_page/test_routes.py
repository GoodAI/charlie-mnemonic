import os
import dotenv
import openai
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import close_all_sessions

from config import CONFIGURATION_URL
from configuration_page import TEST_KEY_PREFIX
from launcher import create_app
from user_management.session import session_factory

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture
def client(tmp_path):
    os.environ["ORIGINS"] = "*"
    tmp_user_env_file = tmp_path / "user.env"
    os.environ["SINGLE_USER"] = "true"
    os.environ["OPENAI_API_KEY"] = ""
    openai.api_key = ""
    os.environ["CLANG_SYSTEM_CONFIGURATION_FILE"] = str(tmp_user_env_file)

    db_url = "sqlite:///config.db"
    os.environ["NEW_DATABASE_URL"] = db_url

    # Attempt to close all sessions and dispose of the engine (if using SQLAlchemy)
    close_all_sessions()
    if "engine" in session_factory.__dict__:
        session_factory.engine.dispose()

    if os.path.exists("config.db"):
        os.remove("config.db")

    session_factory.get_refreshed()  # Ensure a fresh start for the DB session

    client = TestClient(create_app())

    yield client

    # Cleanup
    client.close()  # Close TestClient, which might also close connections
    close_all_sessions()
    if "engine" in session_factory.__dict__:
        session_factory.engine.dispose()

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


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_update_configuration(client):
    dotenv.load_dotenv()
    test_data = {
        "OPENAI_API_KEY": f"{TEST_KEY_PREFIX}new_key_value",
        "ANTHROPIC_API_KEY": f"{TEST_KEY_PREFIX}new_anthropic_key",
    }

    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {"message": "Configuration updated successfully"}
    assert openai.api_key == f"{TEST_KEY_PREFIX}new_key_value"
    assert os.environ.get("ANTHROPIC_API_KEY") == f"{TEST_KEY_PREFIX}new_anthropic_key"


def test_update_configuration_missing_required(client):
    test_data = {"INVALID_KEY": "new_key_value"}
    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
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


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
# This passes locally, but not in Github Actions
def test_update_configuration_with_file(client, tmp_path):
    test_data = {"OPENAI_API_KEY": f"{TEST_KEY_PREFIX}new_key_value"}
    google_client_secret_path = tmp_path / "google_client_secret.json"
    google_client_secret_path.write_text("{}")

    with open(google_client_secret_path, "rb") as f:
        files = {"GOOGLE_CLIENT_SECRET_PATH": (google_client_secret_path.name, f)}
        response = client.post(
            CONFIGURATION_URL,
            data=test_data,
            files=files,
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Configuration updated successfully"}


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_update_configuration_openai(client):
    dotenv.load_dotenv()
    test_data = {
        "OPENAI_API_KEY": f"{TEST_KEY_PREFIX}new_key_value",
    }

    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {"message": "Configuration updated successfully"}
    assert openai.api_key == f"{TEST_KEY_PREFIX}new_key_value"


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_update_configuration_anthropic(client):
    dotenv.load_dotenv()
    test_data = {
        "ANTHROPIC_API_KEY": f"{TEST_KEY_PREFIX}new_anthropic_key",
    }

    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {"message": "Configuration updated successfully"}
    assert os.environ.get("ANTHROPIC_API_KEY") == f"{TEST_KEY_PREFIX}new_anthropic_key"


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_update_configuration_both(client):
    dotenv.load_dotenv()
    test_data = {
        "OPENAI_API_KEY": f"{TEST_KEY_PREFIX}new_key_value",
        "ANTHROPIC_API_KEY": f"{TEST_KEY_PREFIX}new_anthropic_key",
    }

    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {"message": "Configuration updated successfully"}
    assert openai.api_key == f"{TEST_KEY_PREFIX}new_key_value"
    assert os.environ.get("ANTHROPIC_API_KEY") == f"{TEST_KEY_PREFIX}new_anthropic_key"


def test_update_configuration_missing_both(client):
    test_data = {"GOOGLE_CLIENT_SECRET_PATH": "some_path"}
    response = client.post(
        CONFIGURATION_URL,
        data=test_data,
    )
    assert response.status_code == 400
    assert (
        "Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be provided"
        in response.json()["detail"]
    )


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
# This passes locally, but not in Github Actions
def test_update_configuration_with_file(client, tmp_path):
    test_data = {"OPENAI_API_KEY": f"{TEST_KEY_PREFIX}new_key_value"}
    google_client_secret_path = tmp_path / "google_client_secret.json"
    google_client_secret_path.write_text("{}")

    with open(google_client_secret_path, "rb") as f:
        files = {"GOOGLE_CLIENT_SECRET_PATH": (google_client_secret_path.name, f)}
        response = client.post(
            CONFIGURATION_URL,
            data=test_data,
            files=files,
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Configuration updated successfully"}
