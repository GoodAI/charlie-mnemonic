import os
from typing import Dict, Optional

from simple_utils import get_root

api_keys: Dict[str, Optional[str]] = {}

default_params = {
    "model": "gpt-4o",
    "temperature": 0.1,
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
USERS_DIR = "users"

MEMORY_MODEL = os.environ.get("MEMORY_MODEL", default_params["model"])
CHATGPT_MODEL = os.environ.get("CHATGPT_MODEL", default_params["model"])

# not used for now, embedding model used in the ChromaDB files
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-davinci-003")


def origins():
    return os.environ["ORIGINS"]


def database_url():
    return os.environ["DATABASE_URL"]


def new_database_url():
    return os.environ["NEW_DATABASE_URL"]
