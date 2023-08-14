
from pydantic import BaseModel
import os

from dotenv import load_dotenv

load_dotenv()

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

class editSettings(BaseModel):
    username: str
    addon: str
    enabled: bool

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

class config:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    CHATGPT_MODEL = os.environ["CHATGPT_MODEL"]
    OPENAI_EMBEDDING_MODEL = os.environ["OPENAI_EMBEDDING_MODEL"] # not used right now
    OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
    GOOGLE_CX = os.environ["GOOGLE_CX"]
    YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
    HOUSE_API_URL = os.environ["HOUSE_API_URL"]
    HOUSE_API_KEY = os.environ["HOUSE_API_KEY"]
    ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]