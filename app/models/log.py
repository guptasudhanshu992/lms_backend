from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    logger = Column(String(50), nullable=False)  # logger name (api, auth, db, etc.)
    module = Column(String(100))  # Python module
    function = Column(String(100))  # Function name
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)  # Additional context (endpoint, method, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<Log {self.level}: {self.message[:50]}>"
