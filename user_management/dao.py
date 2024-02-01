import json

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import sessionmaker, Session

from simple_utils import SingletonMeta
from user_management.models import Users


class UsersDAO(metaclass=SingletonMeta):
    def __init__(self, database_url: str):
        engine = create_engine(database_url)
        self.engine = engine
        SessionLocal = sessionmaker(bind=engine)
        self.session: Session = SessionLocal()


    def create_tables(self):
        Users.metadata.create_all(self.engine)

    def drop_tables(self):
        Users.metadata.drop_all(self.engine)

    def get_user_count(self) -> int:
        return self.session.query(Users).count()

    def get_password_by_username(self, username: str) -> str:
        user = self.session.query(Users).filter_by(username=username).first()
        return user.password if user else None

    def add_user(
        self, username: str, password: str, session_token: str, display_name: str
    ) -> None:
        new_user = Users(
            username=username,
            password=password,
            session_token=session_token,
            display_name=display_name,
        )
        self.session.add(new_user)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete_user_by_username(self, username: str) -> bool:
        affected_rows = self.session.query(Users).filter_by(username=username).delete()
        self.session.commit()
        return affected_rows > 0

    def close_session(self) -> None:
        self.session.close()

    def update_session_token(self, username: str, session_token: str) -> None:
        self.session.query(Users).filter_by(username=username).update(
            {"session_token": session_token}
        )
        self.session.commit()

    def add_or_update_google_user(
        self,
        google_id: str,
        username: str,
        hashed_password: str,
        session_token: str,
        display_name: str,
    ) -> None:
        user = (
            self.session.query(Users)
            .filter((Users.username == username) | (Users.google_id == google_id))
            .first()
        )
        if user:
            user.google_id = google_id
            user.session_token = session_token
            user.password = hashed_password
        else:
            new_user = Users(
                google_id=google_id,
                username=username,
                password=hashed_password,
                session_token=session_token,
                display_name=display_name,
                has_access=True,
                role="user",
            )
            self.session.add(new_user)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def validate_and_clear_session_token(self, username: str) -> bool:
        user = self.session.query(Users).filter_by(username=username).first()
        if user:
            user.session_token = ""  # Clear session token
            self.session.commit()
            return True
        user = self.session.query(Users).filter_by(username=username).first()
        return False

    def check_session_token(self, username: str, session_token: str) -> bool:
        if session_token == "":
            return False
        user = (
            self.session.query(Users)
            .filter_by(username=username, session_token=session_token)
            .first()
        )
        return user is not None

    def get_username(self, user_id: int) -> str:
        user = self.session.query(Users).filter(Users.id == user_id).first()
        return user.username if user else None

    def get_user_id(self, username: str) -> int:
        user = self.session.query(Users).filter(Users.username == username).first()
        return user.id if user else None

    def get_user_profile(self, username: str) -> str:
        try:
            user = self.session.query(Users).filter(Users.username == username).one()
            user_dict = {
                column.name: getattr(user, column.name)
                for column in user.__table__.columns
            }
            return json.dumps(user_dict, default=str)
        except NoResultFound:
            return json.dumps({})
