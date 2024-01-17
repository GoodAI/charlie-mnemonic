import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, Callable

import openai
from elevenlabs import set_api_key as set_elevenlabs_api_key

from configuration_page.dotenv_util import update_dotenv_contents, update_dotenv_file
from simple_utils import get_root
from .redirect_middleware import RedirectToConfigurationMiddleware


def update_openai_api_key(value: str):
    openai.api_key = value


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
        is_valid=lambda: openai.api_key and os.environ.get("OPENAI_API_KEY", None),
    ),
    ConfigurationMeta(
        key="ELEVENLABS_API_KEY",
        update_callback=set_elevenlabs_api_key,
    ),
]

configuration_meta = OrderedDict([(meta.key, meta) for meta in configuration_meta_list])

# TODO: make this configurable
CONFIGURATION_FILE = get_root("user.env")


def modify_settings(settings: Dict[str, str], path: Optional[str] = None):
    invalid_keys = set(settings.keys()) - set(configuration_meta.keys())

    if invalid_keys:
        raise ValueError(
            f"Invalid keys '{','.join(invalid_keys)}', allowed keys are {list(configuration_meta.keys())}"
        )
    for key, meta in configuration_meta.items():
        if key in settings and meta.validate_callback:
            meta.validate_callback(settings[key])

    # TODO: callbacks for certain key updates (update API key in libraries where necessary)
    path = path or os.environ.get("CLANG_SYSTEM_CONFIGURATION_FILE", CONFIGURATION_FILE)
    update_dotenv_file(path=path, updates=settings)
    for key, value in settings.items():
        os.environ[key] = value
        meta = configuration_meta[key]
        if meta.update_callback:
            meta.update_callback(value)
