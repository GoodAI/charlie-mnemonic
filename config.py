import os
from typing import Dict, Optional

api_keys: Dict[str, Optional[str]] = {}


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
            "elevenlabs": os.getenv("ELEVENLABS_API_KEY"),
            "d-id": os.getenv("D_ID_API_KEY"),
        }
    )
    return api_keys


update_api_keys()

STATIC = "static"
CONFIGURATION_URL = "/configuration/"
