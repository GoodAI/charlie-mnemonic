from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from routes import router
from utils import check_api_keys
import logging

# Check if the API keys are set
check_api_keys()

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
    version=0.03,
)

origins = os.getenv("ORIGINS").split(";")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
