"""
Database models for AI Gateway
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Request(Base):
    """Log of LLM requests through the gateway"""
    __tablename__ = "requests"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    workflow_name = Column(String, index=True)
    model = Column(String, index=True)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost_usd = Column(Float)
    latency_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Request(id={self.id}, model={self.model}, tokens={self.total_tokens})>"


class Workflow(Base):
    """Stored workflow configurations"""
    __tablename__ = "workflows"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    config_yaml = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Workflow(name={self.name})>"
