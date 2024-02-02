import binascii
import os
from typing import Optional

import bcrypt
import logs
from fastapi import HTTPException
from unidecode import unidecode

from config import new_database_url
from user_management.dao import UsersDAO

logger = logs.Log("authentication", "authentication.log").get_logger()


class Authentication:
    def __init__(self):
        self.dao = UsersDAO()

    def register(self, username: str, password: str, display_name: str) -> str:
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        hashed_password_str = hashed_password.decode("utf-8")
        session_token = binascii.hexlify(os.urandom(24)).decode()

        try:
            self.dao.add_user(
                username, hashed_password_str, session_token, display_name
            )
            return session_token
        except Exception as e:
            raise HTTPException(
                status_code=400, detail="Email already exists or other database error."
            ) from e

    def delete_user(self, username: str) -> None:
        self.dao.delete_user_by_username(username)

    def force_login(self, username: str, regenerate_token: bool) -> str:
        session_token = self.dao.get_user(username).session_token
        if regenerate_token or not session_token:
            session_token = binascii.hexlify(os.urandom(24)).decode()
            self.dao.update_session_token(username, session_token)
        logger.debug(f"User: {username} - Session token: {session_token}")
        return session_token

    def login(self, username: str, password: str) -> Optional[str]:
        stored_password = self.dao.get_password_by_username(username)
        if stored_password and bcrypt.checkpw(
            password.encode("utf-8"), stored_password.encode("utf-8")
        ):
            return self.force_login(username, regenerate_token=True)
        return None

    def convert_name(self, name: str) -> str:
        name = unidecode(name).replace(" ", "_").lower()
        return name

    def google_login(self, id_info: dict) -> str:
        display_name, google_id, username = (
            id_info["name"],
            id_info["sub"],
            id_info["email"],
        )
        session_token = binascii.hexlify(os.urandom(24)).decode()
        hashed_password = bcrypt.hashpw(
            session_token.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        self.dao.add_or_update_google_user(
            google_id, username, hashed_password, session_token, display_name
        )
        logger.debug(f"User: {username} - Session token: {session_token}")
        return session_token

    def logout(self, username: str) -> bool:
        if self.dao.validate_and_clear_session_token(username):
            return True
        return False

    def check_token(self, username: str, session_token: str) -> bool:
        return self.dao.check_session_token(username, session_token)
