import binascii
import os
from typing import Optional

import bcrypt
import logs
import psycopg2
from fastapi import HTTPException
from unidecode import unidecode

from database import Database

logger = logs.Log("authentication", "authentication.log").get_logger()

DATABASE_URL = os.environ["DATABASE_URL"]
PRODUCTION = os.environ["PRODUCTION"]


class Authentication:
    def __init__(self):
        self.db = Database()

    def register(self, username, password, display_name):
        self.db.open()
        try:
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            hashed_password_str = hashed_password.decode("utf-8")
            session_token = binascii.hexlify(os.urandom(24)).decode()
            self.db.cursor.execute(
                "INSERT INTO users (username, password, session_token, display_name) VALUES (%s, %s, %s, %s)",
                (username, hashed_password_str, session_token, display_name),
            )
            self.db.conn.commit()
            return session_token
        except psycopg2.IntegrityError:
            raise HTTPException(status_code=400, detail="Email already exists.")
        finally:
            self.db.close()

    def delete_user(self, username):
        self.db.open()
        cursor = self.db.cursor
        cursor.execute(
            "DELETE FROM statistics WHERE user_id = (SELECT id FROM users WHERE username = %s)",
            (username,),
        )
        cursor.execute(
            "DELETE FROM daily_stats WHERE user_id = (SELECT id FROM users WHERE username = %s)",
            (username,),
        )
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        self.db.conn.commit()
        self.db.close()

    def force_login(self, username: str) -> str:
        self.db.open()
        session_token = binascii.hexlify(os.urandom(24)).decode()

        # Store the session token in the database
        self.db.cursor.execute(
            "UPDATE users SET session_token = %s WHERE username = %s",
            (session_token, username),
        )
        self.db.conn.commit()
        self.db.close()
        logger.debug(f"User: {username} - Session token: {session_token}")
        # Return the session token
        return session_token

    def login(self, username: str, password: str) -> Optional[str]:
        self.db.open()
        self.db.cursor.execute(
            "SELECT password FROM users WHERE username = %s", (username,)
        )
        result = self.db.cursor.fetchone()
        self.db.conn.commit()
        self.db.close()

        if result is None:
            return None

        stored_password = result[0]
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode("utf-8")

        if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
            return self.force_login(username)
        else:
            return None

    def convert_name(self, name):
        # Convert non-ASCII characters to ASCII
        name = unidecode(name)
        # replace spaces with underscores
        name = name.replace(" ", "_")
        # lowercase the name
        return name.lower()

    def google_login(self, id_info):
        display_name, google_id, username = (
            id_info["name"],
            id_info["sub"],
            id_info["email"],
        )
        session_token = binascii.hexlify(os.urandom(24)).decode()
        hashed_password_str = bcrypt.hashpw(
            session_token.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        self.db.open()
        self.db.cursor.execute(
            "SELECT username, id FROM users WHERE username = %s OR google_id = %s",
            (username, google_id),
        )
        user = self.db.cursor.fetchone()

        if user is None:
            # If the user doesn't exist, create a new user
            self.db.cursor.execute(
                """
                INSERT INTO users (google_id, username, password, session_token, has_access, role, display_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    google_id,
                    username,
                    hashed_password_str,
                    session_token,
                    False,
                    "user",
                    display_name,
                ),
            )
        else:
            # If the user exists, update the session token and google_id
            self.db.cursor.execute(
                """
                UPDATE users SET google_id = %s, session_token = %s, password = %s WHERE username = %s OR google_id = %s
            """,
                (google_id, session_token, hashed_password_str, username, google_id),
            )

        self.db.conn.commit()
        self.db.close()
        logger.debug(f"User: {username} - Session token: {session_token}")
        return session_token

    def logout(self, username, session_token):
        self.db.open()
        self.db.cursor.execute(
            "SELECT session_token FROM users WHERE username = %s", (username,)
        )
        result = self.db.cursor.fetchone()

        if result is not None:
            stored_token = result[0]
            if stored_token == session_token:
                # If the session token is correct, delete it from the database
                self.db.cursor.execute(
                    "UPDATE users SET session_token = '' WHERE username = %s",
                    (username,),
                )
                self.db.conn.commit()
                self.db.close()
                return True
            else:
                return False
        else:
            return False

    def check_token(self, username, session_token):
        if session_token == "":
            return False
        self.db.open()
        self.db.cursor.execute(
            "SELECT session_token FROM users WHERE username = %s", (username,)
        )
        result = self.db.cursor.fetchone()

        if result is not None:
            stored_token = result[0]
            self.db.close()
            if stored_token == session_token:
                return True
        return False


if __name__ == "__main__":
    auth = Authentication()
