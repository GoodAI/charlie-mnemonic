import os

import chromadb
from chromadb.config import Settings

from agentmemory.postgres import PostgresClient

DEFAULT_CLIENT_TYPE = "CHROMA"
CLIENT_TYPE = os.environ.get("CLIENT_TYPE", DEFAULT_CLIENT_TYPE)
STORAGE_PATH = os.environ.get("STORAGE_PATH", "./memory")
POSTGRES_CONNECTION_STRING = os.environ.get("POSTGRES_CONNECTION_STRING")
POSTGRES_MODEL_NAME = os.environ.get("POSTGRES_MODEL_NAME", "all-MiniLM-L6-v2")
# client = None


def get_client(client_type=None, username=None, *args, **kwargs):
    # global client
    # if client is not None:
    #     return client
    client = None
    if client_type is None:
        client_type = CLIENT_TYPE

    if client_type == "POSTGRES":
        if POSTGRES_CONNECTION_STRING is None:
            raise EnvironmentError(
                "Postgres connection string not set in environment variables!"
            )
        client = PostgresClient(
            POSTGRES_CONNECTION_STRING,
            model_name=POSTGRES_MODEL_NAME,
            model_path=os.environ["MODEL_PATH"],
        )
    else:
        user_memory_path = os.path.join("users", username)
        client = chromadb.PersistentClient(
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
            path=user_memory_path,
            *args,
            **kwargs,
        )

    return client
