from sqlalchemy import Column, Integer, String, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    fields = Column(JSON, nullable=False) 
    chat_id = Column(String, nullable=False)

    responses = relationship("Response", back_populates="notification")



class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    notification_id = Column(Integer, ForeignKey("notifications.id"))

    notification = relationship("Notification", back_populates="responses")

    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_notif_user"),
    )

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)

