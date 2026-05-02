from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Business(Base):
    """Один tenant = один бизнес"""
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True)
    owner_telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)           # О компании
    faq = Column(Text)                   # FAQ в свободном тексте
    system_prompt = Column(Text)         # Кастомный промпт для AI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="business")
    chat_sessions = relationship("ChatSession", back_populates="business")

class Order(Base):
    """Заказ от клиента"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    client_telegram_id = Column(String, nullable=False)
    client_name = Column(String(200))
    details = Column(Text, nullable=False) # Что заказал
    status = Column(String(50), default="new")  # new/confirmed/done
    created_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="orders")

class ChatSession(Base):
    """История диалога для контекста AI"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    client_telegram_id = Column(String, nullable=False)
    messages = Column(JSON, default=list)  # [{role, content}, ...]
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    business = relationship("Business", back_populates="chat_sessions")