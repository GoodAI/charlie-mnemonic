import os
from typing import Dict, Optional

from simple_utils import get_root

api_keys: Dict[str, Optional[str]] = {}

default_params = {
    "model": "gpt-4-turbo-preview",
    "temperature": 0.3,
    "max_tokens": 1000,
}

fakedata = [
    {
        "type": "function",
        "function": {
            "name": "none",
            "description": "you have no available functions",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    }
]


# Get API keys from environment variables
def update_api_keys() -> Dict[str, Optional[str]]:
    api_keys.update(
        {
            "openai": os.getenv("OPENAI_API_KEY"),
            "chatgpt_model": os.getenv("CHATGPT_MODEL"),
            "memory_model": os.getenv("MEMORY_MODEL"),
            "openai_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL"),
            "openweather": os.getenv("OPENWEATHER_API_KEY"),
            "google": os.getenv("GOOGLE_API_KEY"),
            "google_cx": os.getenv("GOOGLE_CX"),
            "youtube": os.getenv("YOUTUBE_API_KEY"),
            "house_api_url": os.getenv("HOUSE_API_URL"),
            "house_api_key": os.getenv("HOUSE_API_KEY"),
            "d-id": os.getenv("D_ID_API_KEY"),
        }
    )
    return api_keys


update_api_keys()

STATIC = "static"
CONFIGURATION_URL = "/configuration/"
LOGIN_REQUIRED = "login_required"
ADMIN_REQUIRED = "admin_required"
SINGLE_USER_USERNAME = os.environ.get("SINGLE_USER_USERNAME", "admin")
SINGLE_USER_DISPLAY_NAME = os.environ.get("SINGLE_USER_DISPLAY_NAME", "admin")
SINGLE_USER_PASSWORD = os.environ.get("SINGLE_USER_PASSWORD", "admin")
DEFAULT_CLANG_SYSTEM_CONFIGURATION_FILE = get_root("users/user.env")
PRODUCTION = os.getenv("PRODUCTION", "false").lower() in ["true", "1", "yes"]


def origins():
    return os.environ["ORIGINS"]


def database_url():
    return os.environ["DATABASE_URL"]


def new_database_url():
    return os.environ["NEW_DATABASE_URL"]
