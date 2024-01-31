import os


def is_single_user():
    return os.environ.get("SINGLE_USER", "").lower() == "true"
