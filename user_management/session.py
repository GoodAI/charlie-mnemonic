from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config import new_database_url

engine = create_engine(new_database_url())
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
