
from typing import Union
from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str

class UserName(BaseModel):
    username: str

class UserCheckToken(BaseModel):
    username: str
    session_token: str

class userMessage(BaseModel):
    prompt: str
    username: str

class noTokenMessage(BaseModel):
    prompt: str
    username: str
    password: str

class editSettings(BaseModel):
    username: str
    category: str
    setting: str
    value: Union[str, int, bool]

class AsciiColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    PINK = '\033[95m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    BROWN = '\033[93m'
    PURPLE = '\033[95m'
    GREY = '\033[90m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    WARNING = '\033[93m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'