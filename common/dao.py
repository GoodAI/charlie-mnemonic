from abc import ABC
from typing import Type, Generic

from sqlalchemy import Engine
from sqlalchemy.orm import Session, DeclarativeMeta

from user_management.models import Base
from user_management.session import session_factory


class AbstractDAO(ABC):
    engine: Engine = None
    session: Session = None
    model: Type[DeclarativeMeta]

    def __init__(self, model: Type[DeclarativeMeta]):
        sess = session_factory.get_session()
        self.engine = sess.engine
        self.session: Session = sess.session
        self.model = model

    def create_all_tables(self):
        Base.metadata.create_all(self.engine)

    def drop_all_tables(self):
        Base.metadata.drop_all(self.engine)

    def create_tables(self):
        self.model.metadata.create_all(self.engine)

    def drop_tables(self):
        self.model.metadata.drop_all(self.engine)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_session()

    def close_session(self) -> None:
        self.session.close()
