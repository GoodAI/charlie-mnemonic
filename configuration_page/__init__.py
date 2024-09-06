import os
import sys
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, Callable

import openai
from dotenv import load_dotenv
from openai import AuthenticationError
from anthropic import Anthropic

from config import update_api_keys, DEFAULT_CLANG_SYSTEM_CONFIGURATION_FILE
from configuration_page.dotenv_util import update_dotenv_contents, update_dotenv_file

TEST_KEY_PREFIX = "test-token-"


def is_openai_available():
    return bool(os.environ.get("OPENAI_API_KEY"))


def is_anthropic_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def is_any_ai_available():
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    result = bool(openai_key) or bool(anthropic_key)
    return result


def update_openai_api_key(value: str):
    openai.api_key = value


def update_google_client_key(value: str):
    os.environ["GOOGLE_CLIENT_SECRET_PATH"] = value


def validate_google_client_key(value: str):
    if value.startswith(TEST_KEY_PREFIX):
        # when we see this prefix, we ignore the validator (used in tests)
        return
    if not os.path.exists(value):
        raise ValueError("Google client secret file does not exist.")


def validate_openai_key(value: str):
    if value.startswith(TEST_KEY_PREFIX):
        # when we see this prefix, we ignore the validator (used in tests)
        return
    openai.api_key = value
    try:
        openai.models.list()
    except AuthenticationError as e:
        raise ValueError("Invalid OpenAI API key.") from e


def update_anthropic_api_key(value: str):
    os.environ["ANTHROPIC_API_KEY"] = value


def validate_anthropic_key(value: str):
    if value.startswith(TEST_KEY_PREFIX):
        print("Test key detected, skipping validation")
        return
    try:
        client = Anthropic(api_key=value)
        token_count = client.count_tokens("Validating Anthropic API key")
    except Exception as e:
        print(f"Anthropic key validation failed: {str(e)}")
        raise ValueError("Invalid Anthropic API key.") from e


def reload_configuration():
    load_dotenv()
    load_dotenv(dotenv_path=configuration_file(), override=True)
    update_api_keys()
    for config_meta_item in configuration_meta_list:
        value = os.environ.get(config_meta_item.key, None)
        if value:
            config_meta_item.update_callback(value)


@dataclass
class ConfigurationMeta:
    key: str
    validate_callback: Optional[Callable[[str], None]] = None
    update_callback: Optional[Callable[[str], None]] = None
    is_valid: Optional[Callable[[], bool]] = None
    input_type: str = "password"

    @property
    def value(self) -> str:
        return os.environ.get(self.key, "")


configuration_meta_list = [
    ConfigurationMeta(
        key="OPENAI_API_KEY",
        update_callback=update_openai_api_key,
        validate_callback=validate_openai_key,
        is_valid=is_openai_available,
    ),
    ConfigurationMeta(
        key="GOOGLE_CLIENT_SECRET_PATH",
        update_callback=update_google_client_key,
        input_type="file",
    ),
    ConfigurationMeta(
        key="ANTHROPIC_API_KEY",
        update_callback=update_anthropic_api_key,
        validate_callback=validate_anthropic_key,
        is_valid=is_anthropic_available,
    ),
]

configuration_meta = OrderedDict([(meta.key, meta) for meta in configuration_meta_list])


def configuration_file() -> str:
    return os.environ.get(
        "CLANG_SYSTEM_CONFIGURATION_FILE", DEFAULT_CLANG_SYSTEM_CONFIGURATION_FILE
    )


def modify_settings(settings: Dict[str, str], path: Optional[str] = None):
    invalid_keys = set(settings.keys()) - set(configuration_meta.keys())

    if invalid_keys:
        raise ValueError(
            f"Invalid keys '{','.join(invalid_keys)}', allowed keys are {list(configuration_meta.keys())}"
        )
    for key, meta in configuration_meta.items():
        if key in settings and meta.validate_callback:
            meta.validate_callback(settings[key])

    path = path or configuration_file()
    update_dotenv_file(path=path, updates=settings)
    for key, value in settings.items():
        os.environ[key] = value
        meta = configuration_meta[key]
        if meta.update_callback:
            meta.update_callback(value)

    # Check AI availability after setting the environment variables
    is_any_ai_available()
