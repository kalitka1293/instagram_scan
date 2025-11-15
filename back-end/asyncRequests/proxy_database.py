from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import sys
import os

config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.py')
sys.path.append(os.path.dirname(config_path))

from database import Base

class ProxyResource(Base):
    __tablename__ = "proxy_resources"

    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String, nullable=False)
    cookie_data = Column(Text, nullable=True)
    user_agent_data = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, default=datetime.now)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String, nullable=False)
    usage_count = Column(Integer, default=0)
    reset_time = Column(DateTime, default=datetime.utcnow)