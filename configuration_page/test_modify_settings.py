import os
import tempfile

import dotenv
import openai
import pytest

from configuration_page import modify_settings


@pytest.fixture
def config_file_path():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        os.environ["CLANG_SYSTEM_CONFIGURATION_FILE"] = tmp.name
        return tmp.name


def test_updating_invalid_key(config_file_path):
    with pytest.raises(ValueError) as excinfo:
        modify_settings({"testkey": "value"})
    assert "Invalid keys 'testkey', allowed keys are" in str(excinfo.value)


def test_updating_set_openai_key(config_file_path):
    new_key = "new_key_value"
    modify_settings({"OPENAI_API_KEY": new_key})
    with open(config_file_path) as f:
        assert f.read() == f"OPENAI_API_KEY={new_key}"
    assert openai.api_key == new_key
    assert dotenv.dotenv_values(config_file_path)["OPENAI_API_KEY"] == new_key


def test_creates_file(config_file_path):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        os.remove(tmp.name)
        modify_settings({"OPENAI_API_KEY": "value"}, path=tmp.name)
        assert os.path.exists(tmp.name)
