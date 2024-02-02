import json
import math
from typing import Optional, Dict, Any, List

from sqlalchemy.exc import SQLAlchemyError, NoResultFound

from common.dao import AbstractDAO
from user_management.models import Users, AdminControls


class UsersDAO(AbstractDAO):
    def __init__(self):
        super().__init__(Users)

    def get_user_count(self) -> int:
        return self.session.query(Users).count()

    def create_default_user(self):
        user_count = self.get_user_count()
        if user_count > 0:
            return
        from config import (
            SINGLE_USER_USERNAME,
            SINGLE_USER_DISPLAY_NAME,
            SINGLE_USER_PASSWORD,
        )
        from authentication import Authentication

        Authentication().register(
            username=SINGLE_USER_USERNAME,
            password=SINGLE_USER_PASSWORD,
            display_name=SINGLE_USER_DISPLAY_NAME,
        )
        user_id = self.get_user_id(SINGLE_USER_USERNAME)
        self.update_user(
            user_id=user_id,
            access=True,
            role="admin",
        )

    def update_user(self, user_id: int, access: bool, role: str) -> None:
        self.session.query(Users).filter(Users.id == user_id).update(
            {Users.has_access: access, Users.role: role}
        )
        self.session.commit()

    def get_password_by_username(self, username: str) -> str:
        user = self.session.query(Users).filter_by(username=username).first()
        return user.password if user else None

    def add_user(
        self, username: str, password: str, session_token: str, display_name: str
    ) -> int:
        new_user = Users(
            username=username,
            password=password,
            session_token=session_token,
            display_name=display_name,
        )
        self.session.add(new_user)
        try:
            self.session.commit()
            return new_user.id
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete_user_by_username(self, username: str) -> bool:
        affected_rows = self.session.query(Users).filter_by(username=username).delete()
        self.session.commit()
        return affected_rows > 0

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

    def get_user(self, username: str) -> Optional[Users]:
        return self.session.query(Users).filter(Users.username == username).first()

    def update_display_name(self, username: str, display_name: str) -> bool:
        user = self.session.query(Users).filter(Users.username == username).first()
        if user:
            user.display_name = display_name
            self.session.commit()
            return True
        return False

    def get_total_statistics_pages(self, items_per_page: int) -> int:
        total_items = self.get_user_count()
        return math.ceil(total_items / float(items_per_page))

    def get_display_name(self, username: str) -> Optional[str]:
        user = self.get_user(username)
        if user:
            return user.display_name
        return None

    def get_user_access(self, username):
        user = self.get_user(username)
        if user:
            return user.has_access
        return None

    def get_user_role(self, username):
        user = self.get_user(username)
        if user:
            return user.role
        return None


class AdminControlsDAO(AbstractDAO):
    def __init__(self):
        super().__init__(AdminControls)

    def get_admin_controls_json(self) -> str:
        rows = self.session.query(AdminControls).all()
        if not rows:
            return json.dumps({"id": 1, "daily_spending_limit": 10}, default=str)
        # Assuming rows[0] is an instance of AdminControls
        return json.dumps(rows[0].__dict__, default=str)

    def get_admin_controls(self) -> List[AdminControls]:
        return self.session.query(AdminControls).all()

    def get_daily_limit(self) -> int:
        row = self.session.query(AdminControls).first()
        if row:
            return row.daily_spending_limit
        else:
            return 1

    def update_admin_controls(
        self, id: int, daily_spending_limit: int, allow_access: bool, maintenance: bool
    ) -> None:
        obj = self.session.merge(
            AdminControls(
                id=id,
                daily_spending_limit=daily_spending_limit,
                allow_access=allow_access,
                maintenance=maintenance,
            )
        )
        self.session.add(obj)
        self.session.commit()

    def get_maintenance_mode(self) -> bool:
        row = self.session.query(AdminControls).first()
        if row:
            return row.maintenance
        else:
            return False

    def get_admin_control(self, id: int) -> AdminControls:
        return self.session.query(AdminControls).filter_by(id=id).first()

    def add_admin_control(self, **kwargs) -> None:
        admin_control = AdminControls(**kwargs)
        self.session.add(admin_control)
        self.session.commit()

    def update_admin_control(self, id: int, **kwargs) -> None:
        self.session.query(AdminControls).filter_by(id=id).update(kwargs)
        self.session.commit()

    def delete_admin_control(self, id: int) -> None:
        self.session.query(AdminControls).filter(AdminControls.id == id).delete()
        self.session.commit()
