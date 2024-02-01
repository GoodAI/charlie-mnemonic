from sqlalchemy import Column, Integer, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from user_management.models import Base


class ChatTabs(Base):
    __tablename__ = "chat_tabs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tab_id = Column(Text, nullable=False)
    chat_id = Column(Text, default="0")
    chat_name = Column(Text, default="new chat")
    is_active = Column(Boolean, default=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    user = relationship("Users")
