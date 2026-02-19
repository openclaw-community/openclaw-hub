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
    provider = Column(String, nullable=True)
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


class Connection(Base):
    """Stored LLM provider / service connections with encrypted credentials"""
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    service = Column(String, nullable=False)
    category = Column(String, nullable=False)
    base_url = Column(String, default="")
    api_key_encrypted = Column(String, default="")
    token_encrypted = Column(String, default="")
    cred_path = Column(String, default="")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Connection(id={self.id}, name={self.name}, service={self.service})>"


class CostConfig(Base):
    """Per-model cost configuration for budget tracking"""
    __tablename__ = "cost_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String, nullable=False, unique=True)
    provider = Column(String, nullable=False)
    input_cost_per_million = Column(Float, default=0.0)
    output_cost_per_million = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CostConfig(model={self.model}, provider={self.provider})>"


class BudgetLimit(Base):
    """Budget limits for dashboard spend tracking"""
    __tablename__ = "budget_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_limit_usd = Column(Float, default=5.0)
    weekly_limit_usd = Column(Float, default=25.0)
    monthly_limit_usd = Column(Float, default=80.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BudgetLimit(daily={self.daily_limit_usd}, weekly={self.weekly_limit_usd}, monthly={self.monthly_limit_usd})>"
