from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from routes import router
import logging
from config import api_keys
import openai

# Load environment variables
openai.api_key = api_keys["openai"]

# add more logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Defining the FastAPI app and metadata
app = FastAPI(
    title="CLANG API",
    description="""### API specifications\n
Welcome to the `CLANG` API documentation,\n
WIP.
""",
    version=0.21,
)

origins = "https://clang.goodai.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)