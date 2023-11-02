from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routes import router
from config import api_keys
import openai
import nltk
import logs
import utils
from database import Database

nltk.download("punkt")

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

origins = os.environ["ORIGINS"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
def shutdown_event():
    logs.Log("main", "main.log").get_logger().debug("Shutting down server")


app.include_router(router)
