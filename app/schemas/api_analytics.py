from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class APIAnalyticsResponse(BaseModel):
    """Response schema for individual analytics record"""
    id: int
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    user_id: Optional[int]
    ip_address: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    region: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]
    user_agent: Optional[str]
    request_size: Optional[int]
    response_size: Optional[int]
    error_message: Optional[str]
    extra_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIAnalyticsFilter(BaseModel):
    """Filter schema for analytics queries"""
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    limit: int = 100
    offset: int = 0


class EndpointStats(BaseModel):
    """Statistics for a specific endpoint"""
    endpoint: str
    method: str
    total_calls: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    success_rate: float  # Percentage of 2xx responses
    error_rate: float  # Percentage of 4xx/5xx responses
    last_called: datetime


class APIAnalyticsSummary(BaseModel):
    """Overall API analytics summary"""
    total_requests: int
    total_endpoints: int
    avg_response_time_ms: float
    total_errors: int
    error_rate: float
    requests_per_hour: float
    most_called_endpoints: List[Dict[str, Any]]
    slowest_endpoints: List[Dict[str, Any]]
    status_code_distribution: Dict[str, int]
    method_distribution: Dict[str, int]


class TimeSeriesData(BaseModel):
    """Time-series data for charts"""
    timestamp: datetime
    count: int
    avg_response_time: float


class APIAnalyticsReport(BaseModel):
    """Comprehensive analytics report"""
    summary: APIAnalyticsSummary
    endpoint_stats: List[EndpointStats]
    time_series: List[TimeSeriesData]
    recent_errors: List[APIAnalyticsResponse]


class GeographicStats(BaseModel):
    """Geographic statistics for API usage"""
    country: str
    country_code: str
    request_count: int
    avg_response_time_ms: float
    error_rate: float
    unique_users: int


class CityStats(BaseModel):
    """City-level statistics"""
    city: str
    region: str
    country: str
    request_count: int
    latitude: Optional[float]
    longitude: Optional[float]
