from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routes import router
from config import api_keys
import openai
from database import Database
import utils
import nltk

nltk.download('punkt')

version = utils.SettingsManager.get_version()

# Load environment variables
openai.api_key = api_keys["openai"]

db = Database()
db.setup_database()

# Defining the FastAPI app and metadata
app = FastAPI(
    title="CLANG API",
    description="""### API specifications\n
Welcome to the `CLANG` API documentation,\n
WIP.
""",
    version=version,
)

origins = os.getenv("ORIGINS")
if origins:
    origins = origins.split(";")
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
