from dataclasses import dataclass

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session

from config import new_database_url


@dataclass
class SessionWithEngine:
    engine: Engine = None
    session: Session = None


@dataclass
class SessionFactory:
    engine: Engine = None
    SessionLocal = None

    def get_refreshed(self) -> SessionWithEngine:
        self.engine = create_engine(new_database_url())
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
        return SessionWithEngine(engine=self.engine, session=self.SessionLocal())

    def get_session(self) -> SessionWithEngine:
        if self.engine is None:
            return self.get_refreshed()
        return SessionWithEngine(engine=self.engine, session=self.SessionLocal())


session_factory = SessionFactory()
