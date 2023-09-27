import psycopg2
import bcrypt
import binascii
import os
from fastapi import HTTPException
from database import Database
import logs

logger = logs.Log(__name__, 'authentication.log').get_logger()

DATABASE_URL = os.environ['DATABASE_URL']
PRODUCTION = os.environ['PRODUCTION']

class Authentication:
    def __init__(self):
        self.db = Database()

    def register(self, username, password):
        self.db.open()
        try:
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            hashed_password_str = hashed_password.decode("utf-8")
            session_token = binascii.hexlify(os.urandom(24)).decode()
            self.db.cursor.execute("INSERT INTO users (username, password, session_token) VALUES (%s, %s, %s)", (username, hashed_password_str, session_token))
            self.db.conn.commit()
            return session_token
        except psycopg2.IntegrityError:
            raise HTTPException(status_code=400, detail="Username already exists.")
        finally:
            self.db.close()

    def login(self, username, password):
        self.db.open()
        self.db.cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        result = self.db.cursor.fetchone()

        if result is None:
            return False

        stored_password = result[0]
        # Make sure stored_password is a string before encoding it to bytes
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode("utf-8")
        stored_password_bytes = stored_password.encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), stored_password_bytes):
            return False

        # If password is correct, generate a session token
        session_token = binascii.hexlify(os.urandom(24)).decode()
        # Store the session token in the database
        self.db.cursor.execute("UPDATE users SET session_token = %s WHERE username = %s", (session_token, username))
        self.db.conn.commit()
        self.db.close()
        logger.debug(f'User: {username} - Session token: {session_token}')
        # Return the session token
        return session_token
        
    def logout(self, username, session_token):
        self.db.open()
        self.db.cursor.execute("SELECT session_token FROM users WHERE username = %s", (username,))
        result = self.db.cursor.fetchone()

        if result is not None:
            stored_token = result[0]
            if stored_token == session_token:
                # If the session token is correct, delete it from the database
                self.db.cursor.execute("UPDATE users SET session_token = '' WHERE username = %s", (username,))
                self.db.conn.commit()
                self.db.close()
                return True
            else:
                return False
        else:
            return False

    def check_token(self, username, session_token):
        if session_token == '':
            return False
        self.db.open()
        self.db.cursor.execute("SELECT session_token FROM users WHERE username = %s", (username,))
        result = self.db.cursor.fetchone()

        if result is not None:
            stored_token = result[0]
            self.db.close()
            if stored_token == session_token:
                return True
        return False

if __name__ == "__main__":
    auth = Authentication()