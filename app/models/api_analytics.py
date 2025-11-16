from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.sql import func
from ..core.database import Base


class APIAnalytics(Base):
    """Model for storing API analytics data"""
    __tablename__ = "api_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)  # e.g., "/api/auth/login"
    method = Column(String(10), nullable=False, index=True)  # GET, POST, PUT, DELETE
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Float, nullable=False)  # Response time in milliseconds
    user_id = Column(Integer, nullable=True, index=True)  # User who made the request (if authenticated)
    ip_address = Column(String(45), nullable=True, index=True)  # IPv4 or IPv6
    country = Column(String(100), nullable=True, index=True)  # Country name
    country_code = Column(String(10), nullable=True)  # ISO country code
    region = Column(String(100), nullable=True)  # Region/State
    city = Column(String(100), nullable=True)  # City
    latitude = Column(Float, nullable=True)  # Latitude
    longitude = Column(Float, nullable=True)  # Longitude
    timezone = Column(String(50), nullable=True)  # Timezone
    user_agent = Column(String(500), nullable=True)
    request_size = Column(Integer, nullable=True)  # Size in bytes
    response_size = Column(Integer, nullable=True)  # Size in bytes
    error_message = Column(String(1000), nullable=True)  # Error details if failed
    extra_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_endpoint_method', 'endpoint', 'method'),
        Index('idx_created_at_endpoint', 'created_at', 'endpoint'),
        Index('idx_status_created', 'status_code', 'created_at'),
    )
    
    def __repr__(self):
        return f"<APIAnalytics {self.method} {self.endpoint} - {self.status_code} ({self.response_time_ms}ms)>"
