from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class LogBase(BaseModel):
    level: str
    message: str
    logger: str
    module: Optional[str] = None
    function: Optional[str] = None
    user_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None


class LogCreate(LogBase):
    pass


class LogResponse(LogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LogFilter(BaseModel):
    level: Optional[str] = None
    logger: Optional[str] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
