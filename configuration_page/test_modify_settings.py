import os
import tempfile

import dotenv
import openai
import pytest

from configuration_page import modify_settings, validate_openai_key, TEST_KEY_PREFIX


@pytest.fixture
def config_file_path():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        os.environ["CLANG_SYSTEM_CONFIGURATION_FILE"] = tmp.name
        return tmp.name


def test_validate_openai_key():
    with pytest.raises(ValueError):
        validate_openai_key("invalid_key")


def test_updating_set_openai_key(config_file_path):
    new_key = f"{TEST_KEY_PREFIX}new_key_value"
    modify_settings({"OPENAI_API_KEY": new_key})
    with open(config_file_path) as f:
        assert f.read() == f"OPENAI_API_KEY={new_key}"
    assert openai.api_key == new_key
    assert dotenv.dotenv_values(config_file_path)["OPENAI_API_KEY"] == new_key


def test_creates_file(config_file_path):
    modify_settings(
        {"OPENAI_API_KEY": f"{TEST_KEY_PREFIX}value"}, path=config_file_path
    )
    assert os.path.exists(config_file_path), "Configuration file was not created."
    with open(config_file_path) as f:
        content = f.read()
        assert (
            f"OPENAI_API_KEY={TEST_KEY_PREFIX}value" in content
        ), "OPENAI_API_KEY was not correctly set in the configuration file."
    config = dotenv.dotenv_values(config_file_path)
    assert (
        config.get("OPENAI_API_KEY") == f"{TEST_KEY_PREFIX}value"
    ), "OPENAI_API_KEY was not correctly set according to dotenv."
