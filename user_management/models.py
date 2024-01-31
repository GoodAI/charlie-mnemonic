from sqlalchemy import Column, Integer, String, Boolean, Float, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    session_token = Column(String(255), nullable=False)
    role = Column(String(255), default="user")
    message_history = Column(Text)
    has_access = Column(Boolean, default=False)
    session_time = Column(Integer, default=0)
    addons_used = Column(String(255))
    settings_used = Column(String(255))
    banned = Column(Boolean, default=False)
    google_id = Column(String(255), unique=True)
    display_name = Column(String(255))
    can_use_avatar = Column(Boolean, default=False)
    avatar_usage = Column(Float)
    whisper_usage = Column(Float)
    first_visit = Column(Boolean, default=True)
    use_custom_system_prompt = Column(Boolean, default=False)
    cot_loops = Column(Integer, default=1)
    receive_mails = Column(Boolean, default=True)
    password_reset_token = Column(String(255))
