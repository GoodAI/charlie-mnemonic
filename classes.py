from typing import Union, Dict, Any, OrderedDict
from pydantic import BaseModel, Field, validator

from configuration_page import configuration_meta


class User(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str
    display_name: str = Field(..., min_length=1, max_length=50)


class LoginUser(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str


class UserGoogle(BaseModel):
    credentials: str


class UserName(BaseModel):
    username: str


class RecentMessages(BaseModel):
    username: str
    chat_id: str


class EditTabDescription(BaseModel):
    username: str
    chat_id: str
    description: str


class UserCheckToken(BaseModel):
    username: str
    session_token: str


class userMessage(BaseModel):
    prompt: str
    username: str
    display_name: str
    chat_id: str


class CreateChat(BaseModel):
    username: str
    chat_name: str
    chat_id: str


class setActiveChat(BaseModel):
    username: str
    chat_id: str


class regenerateMessage(BaseModel):
    uuid: str
    username: str
    chat_id: str


class userImageMessage(BaseModel):
    prompt: str
    username: str
    display_name: str
    image: str


class UserUpdate(BaseModel):
    has_access: bool
    role: str


class generateAudioMessage(BaseModel):
    prompt: str
    username: str


class noTokenMessage(BaseModel):
    prompt: str
    username: str
    password: str
    chat_id: str
    display_name: str


class editSettings(BaseModel):
    username: str
    category: str
    setting: Union[str, Dict[str, Any]]
    value: Union[str, int, bool, None]


class AsciiColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    PINK = "\033[95m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    BROWN = "\033[93m"
    PURPLE = "\033[95m"
    GREY = "\033[90m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    WARNING = "\033[93m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


class ConfigurationData(BaseModel):
    OPENAI_API_KEY: str = Field(
        ...,
        title="OpenAI API key",
        description="This key is used for general OpenAI API calls and is required for the agent to work.",
    )

    @staticmethod
    def for_frontend():
        schema = ConfigurationData.schema()
        result = []
        for key, single_property in schema["properties"].items():
            meta = configuration_meta[key]
            result.append(
                (
                    key,
                    {
                        "key": key,
                        "title": single_property["title"],
                        "help_text": single_property["description"],
                        "input_type": meta.input_type,
                        "required": key in schema["required"],
                        "value": meta.value,
                    },
                )
            )
        return OrderedDict(result)

    @validator("OPENAI_API_KEY", pre=True, always=True)
    def check_not_empty(cls, v, field):
        if field.required and (v is None or v == ""):
            raise ValueError(f"{field.name} is required and cannot be empty")
        return v
