import os
import pytest
from sqlalchemy.orm import close_all_sessions
from starlette.testclient import TestClient
import openai
import tempfile
import dotenv
from config import CONFIGURATION_URL
from launcher import create_app
from user_management.session import session_factory


@pytest.fixture
def client():
    db_file = "user.db"
    db_url = f"sqlite:///{db_file}?cache=shared"
    os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5432/postgres"
    os.environ["NEW_DATABASE_URL"] = db_url

    # Dispose of engine and close all sessions to ensure clean teardown
    if hasattr(session_factory, "engine"):
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

    app = create_app()
    client = TestClient(app)
    yield client

    # Close client and dispose engine after test run
    client.close()

    if hasattr(session_factory, "engine"):
        session_factory.engine.dispose()
        close_all_sessions()

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError as e:
            print(f"Failed to delete {db_file} after tests due to PermissionError: {e}")


@pytest.fixture(autouse=True)
def config_file_path():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    os.environ["CLANG_SYSTEM_CONFIGURATION_FILE"] = tmp.name
    return tmp.name


@pytest.fixture(autouse=False)
def fake_openai_key():
    openai.api_key = "accepted-fake-key"
    os.environ["OPENAI_API_KEY"] = "accepted-fake-key"
    yield


@pytest.fixture(autouse=False)
def no_openai_key():
    openai.api_key = ""
    os.environ["OPENAI_API_KEY"] = ""
    yield


@pytest.fixture(autouse=False)
def none_openai_key():
    openai.api_key = None
    del os.environ["OPENAI_API_KEY"]
    yield


def test_configuration_page_working(client, fake_openai_key):
    response = client.get(CONFIGURATION_URL)
    assert response.status_code == 200


def test_updating_invalid_key(client, fake_openai_key):
    response = client.post(CONFIGURATION_URL, json={"testkey": "value"})
    content = response.json()
    assert (
        response.status_code == 422
    ), f"""
    Expected 422, but was {response.status_code}
    Content:
    {content}
    """
    assert "detail" in content
    assert content["detail"] == [
        {
            "loc": ["body", "OPENAI_API_KEY"],
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]


def test_updating_set_openai_key(client, config_file_path, fake_openai_key):
    response = client.post(CONFIGURATION_URL, json={"OPENAI_API_KEY": "value"})
    content = response.json()
    assert response.status_code == 200
    assert "message" in content
    assert content["message"] == "Configuration updated successfully"
    with open(config_file_path) as f:
        assert (
            f.read()
            == """
OPENAI_API_KEY=value
""".strip()
        )
    assert openai.api_key == "value"


def test_missing_json_body(client, fake_openai_key):
    response = client.post(CONFIGURATION_URL)
    content = response.json()
    assert (
        response.status_code == 422
    ), f"""
Expected 422, but was {response.status_code}
Content:
{content}
"""
    assert "detail" in content
    assert content["detail"] == [
        {"loc": ["body"], "msg": "field required", "type": "value_error.missing"}
    ]


def test_redirect_on_missing_openai_key(client, no_openai_key):
    response = client.get("/")
    assert response.url.path == CONFIGURATION_URL


def test_redirect_on_missing_openai_key_none(client, none_openai_key):
    response = client.get("/")
    assert response.url.path == CONFIGURATION_URL


def test_no_redirect_openai_key(client, fake_openai_key):
    response = client.get("/")
    assert response.url.path == "/"
