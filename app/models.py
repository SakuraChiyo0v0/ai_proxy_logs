from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from .database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    method = Column(String)
    url = Column(String)
    request_body = Column(Text, nullable=True)  # Stored as JSON string
    system_prompt = Column(Text, nullable=True) # Extracted system prompt
    response_status = Column(Integer)
    duration = Column(Float, nullable=True)     # In seconds
    error_message = Column(Text, nullable=True)
