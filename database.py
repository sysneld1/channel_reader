"""
Database models and session management for Telegram Aggregator Bot
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    subscriptions = relationship("Subscription", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    channel_id = Column(String, index=True)
    channel_title = Column(String)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="subscriptions")
    messages = relationship("ScrapedMessage", back_populates="subscription")


class ScrapedMessage(Base):
    __tablename__ = "scraped_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    channel_id = Column(String, index=True)
    channel_title = Column(String)
    message_id = Column(Integer)
    text = Column(Text)
    media_path = Column(String, nullable=True)
    processed_text = Column(Text)
    summary = Column(Text)
    link = Column(String)
    timestamp = Column(DateTime)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_summarized = Column(Boolean, default=False)
    
    subscription = relationship("Subscription", back_populates="messages")


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    summary_length = Column(String, default="medium")
    include_media = Column(Boolean, default=False)
    notification_time = Column(String, default="09:00")
    daily_digest = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="settings")


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()