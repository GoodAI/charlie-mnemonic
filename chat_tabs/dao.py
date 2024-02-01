import datetime
from typing import List

from sqlalchemy.orm import Session

from chat_tabs.models import ChatTabs


class ChatTabsDAO:
    def __init__(self):
        from user_management.session import engine

        self.engine = engine
        from user_management.session import SessionLocal

        self.session: Session = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        # self.close_session()

    def create_tables(self):
        ChatTabs.metadata.create_all(self.engine)

    def drop_tables(self):
        ChatTabs.metadata.drop_all(self.engine)

    def close_session(self) -> None:
        self.session.close()

    def get_tab_data(self, user_id: int) -> List[ChatTabs]:
        return (
            self.session.query(ChatTabs)
            .filter(ChatTabs.user_id == user_id)
            .order_by(ChatTabs.id)
            .all()
        )

    def get_tab_count(self, user_id: int) -> int:
        return self.session.query(ChatTabs).filter(ChatTabs.user_id == user_id).count()

    def get_tab_description(self, tab_id: str) -> str:
        tab = self.session.query(ChatTabs).filter(ChatTabs.tab_id == tab_id).first()
        return tab.chat_name if tab else None

    def get_active_tab_data(self, user_id: int):
        return (
            self.session.query(ChatTabs)
            .filter(ChatTabs.user_id == user_id, ChatTabs.is_active == True)
            .first()
        )

    def update_created_at(self, user_id: int, chat_id: str):
        self.session.query(ChatTabs).filter(
            ChatTabs.user_id == user_id, ChatTabs.chat_id == chat_id
        ).update({"created_at": datetime.datetime.now()})
        self.session.commit()

    def insert_tab_data(
        self, user_id: int, chat_id: str, chat_name: str, tab_id: str, is_active: bool
    ):
        new_tab = ChatTabs(
            user_id=user_id,
            chat_id=chat_id,
            chat_name=chat_name,
            tab_id=tab_id,
            is_active=is_active,
        )
        self.session.add(new_tab)
        self.session.commit()

    def update_tab_data(
        self, user_id: int, chat_name: str, tab_id: str, is_active: bool
    ):
        self.session.query(ChatTabs).filter(ChatTabs.user_id == user_id).update(
            {"chat_name": chat_name, "tab_id": tab_id, "is_active": is_active}
        )
        self.session.commit()

    def update_tab_description(self, tab_id: str, chat_name: str):
        self.session.query(ChatTabs).filter(ChatTabs.tab_id == tab_id).update(
            {"chat_name": chat_name}
        )
        self.session.commit()

    def set_active_tab(self, user_id: int, tab_id: str):
        self.session.query(ChatTabs).filter(ChatTabs.user_id == user_id).update(
            {"is_active": False}
        )
        self.session.query(ChatTabs).filter(
            ChatTabs.user_id == user_id, ChatTabs.tab_id == tab_id
        ).update({"is_active": True, "is_enabled": True})
        self.session.commit()

    def delete_tab_data(self, user_id: int):
        self.session.query(ChatTabs).filter(ChatTabs.user_id == user_id).delete()
        self.session.commit()

    def disable_tab(self, user_id: int, tab_id: str):
        self.session.query(ChatTabs).filter(
            ChatTabs.user_id == user_id, ChatTabs.tab_id == tab_id
        ).update({"is_enabled": False})
        self.session.commit()

    def needs_tab_description(self, chat_id):
        tab_description = self.get_tab_description(chat_id)
        if tab_description.startswith("New Chat"):
            return True
        else:
            return False
