from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

from ..core.database import get_db
from ..models.api_analytics import APIAnalytics
from ..models.user import User
from ..schemas.api_analytics import (
    APIAnalyticsResponse, APIAnalyticsFilter, EndpointStats,
    APIAnalyticsSummary, APIAnalyticsReport, TimeSeriesData,
    GeographicStats, CityStats
)
from ..core.security import get_current_active_user

router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


def is_admin(current_user: User = Depends(get_current_active_user)):
    """Check if user is admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/summary", response_model=APIAnalyticsSummary)
async def get_analytics_summary(
    hours: int = Query(24, description="Time window in hours"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get overall analytics summary"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Total requests
    total_requests = db.query(func.count(APIAnalytics.id)).filter(
        APIAnalytics.created_at >= start_time
    ).scalar()
    
    # Total unique endpoints
    total_endpoints = db.query(func.count(func.distinct(APIAnalytics.endpoint))).filter(
        APIAnalytics.created_at >= start_time
    ).scalar()
    
    # Average response time
    avg_response_time = db.query(func.avg(APIAnalytics.response_time_ms)).filter(
        APIAnalytics.created_at >= start_time
    ).scalar() or 0
    
    # Total errors (4xx and 5xx)
    total_errors = db.query(func.count(APIAnalytics.id)).filter(
        and_(
            APIAnalytics.created_at >= start_time,
            APIAnalytics.status_code >= 400
        )
    ).scalar()
    
    # Error rate
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    
    # Requests per hour
    requests_per_hour = total_requests / hours if hours > 0 else 0
    
    # Most called endpoints
    most_called = db.query(
        APIAnalytics.endpoint,
        APIAnalytics.method,
        func.count(APIAnalytics.id).label('count')
    ).filter(
        APIAnalytics.created_at >= start_time
    ).group_by(
        APIAnalytics.endpoint, APIAnalytics.method
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    most_called_endpoints = [
        {"endpoint": e.endpoint, "method": e.method, "count": e.count}
        for e in most_called
    ]
    
    # Slowest endpoints
    slowest = db.query(
        APIAnalytics.endpoint,
        APIAnalytics.method,
        func.avg(APIAnalytics.response_time_ms).label('avg_time')
    ).filter(
        APIAnalytics.created_at >= start_time
    ).group_by(
        APIAnalytics.endpoint, APIAnalytics.method
    ).order_by(
        desc('avg_time')
    ).limit(10).all()
    
    slowest_endpoints = [
        {"endpoint": e.endpoint, "method": e.method, "avg_response_time_ms": round(e.avg_time, 2)}
        for e in slowest
    ]
    
    # Status code distribution
    status_distribution = db.query(
        APIAnalytics.status_code,
        func.count(APIAnalytics.id).label('count')
    ).filter(
        APIAnalytics.created_at >= start_time
    ).group_by(
        APIAnalytics.status_code
    ).all()
    
    status_code_distribution = {str(s.status_code): s.count for s in status_distribution}
    
    # Method distribution
    method_distribution_data = db.query(
        APIAnalytics.method,
        func.count(APIAnalytics.id).label('count')
    ).filter(
        APIAnalytics.created_at >= start_time
    ).group_by(
        APIAnalytics.method
    ).all()
    
    method_distribution = {m.method: m.count for m in method_distribution_data}
    
    return APIAnalyticsSummary(
        total_requests=total_requests,
        total_endpoints=total_endpoints,
        avg_response_time_ms=round(avg_response_time, 2),
        total_errors=total_errors,
        error_rate=round(error_rate, 2),
        requests_per_hour=round(requests_per_hour, 2),
        most_called_endpoints=most_called_endpoints,
        slowest_endpoints=slowest_endpoints,
        status_code_distribution=status_code_distribution,
        method_distribution=method_distribution
    )


@router.get("/endpoints", response_model=List[EndpointStats])
async def get_endpoint_stats(
    hours: int = Query(24, description="Time window in hours"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get statistics for all endpoints"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all endpoint combinations
    endpoints = db.query(
        APIAnalytics.endpoint,
        APIAnalytics.method
    ).filter(
        APIAnalytics.created_at >= start_time
    ).distinct().all()
    
    result = []
    for endpoint, method in endpoints:
        # Get stats for this endpoint
        stats = db.query(
            func.count(APIAnalytics.id).label('total_calls'),
            func.avg(APIAnalytics.response_time_ms).label('avg_time'),
            func.min(APIAnalytics.response_time_ms).label('min_time'),
            func.max(APIAnalytics.response_time_ms).label('max_time'),
            func.max(APIAnalytics.created_at).label('last_called')
        ).filter(
            and_(
                APIAnalytics.endpoint == endpoint,
                APIAnalytics.method == method,
                APIAnalytics.created_at >= start_time
            )
        ).first()
        
        # Success count (2xx status codes)
        success_count = db.query(func.count(APIAnalytics.id)).filter(
            and_(
                APIAnalytics.endpoint == endpoint,
                APIAnalytics.method == method,
                APIAnalytics.created_at >= start_time,
                APIAnalytics.status_code >= 200,
                APIAnalytics.status_code < 300
            )
        ).scalar()
        
        # Error count (4xx and 5xx)
        error_count = db.query(func.count(APIAnalytics.id)).filter(
            and_(
                APIAnalytics.endpoint == endpoint,
                APIAnalytics.method == method,
                APIAnalytics.created_at >= start_time,
                APIAnalytics.status_code >= 400
            )
        ).scalar()
        
        total_calls = stats.total_calls
        success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0
        error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0
        
        result.append(EndpointStats(
            endpoint=endpoint,
            method=method,
            total_calls=total_calls,
            avg_response_time_ms=round(stats.avg_time, 2),
            min_response_time_ms=round(stats.min_time, 2),
            max_response_time_ms=round(stats.max_time, 2),
            success_rate=round(success_rate, 2),
            error_rate=round(error_rate, 2),
            last_called=stats.last_called
        ))
    
    # Sort by total calls descending
    result.sort(key=lambda x: x.total_calls, reverse=True)
    return result


@router.get("/time-series", response_model=List[TimeSeriesData])
async def get_time_series(
    hours: int = Query(24, description="Time window in hours"),
    interval_minutes: int = Query(60, description="Interval in minutes"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get time-series data for request volume and response times"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Generate time buckets
    buckets = []
    current = start_time
    while current <= datetime.utcnow():
        next_time = current + timedelta(minutes=interval_minutes)
        
        # Count requests in this bucket
        count = db.query(func.count(APIAnalytics.id)).filter(
            and_(
                APIAnalytics.created_at >= current,
                APIAnalytics.created_at < next_time
            )
        ).scalar()
        
        # Average response time in this bucket
        avg_time = db.query(func.avg(APIAnalytics.response_time_ms)).filter(
            and_(
                APIAnalytics.created_at >= current,
                APIAnalytics.created_at < next_time
            )
        ).scalar() or 0
        
        buckets.append(TimeSeriesData(
            timestamp=current,
            count=count,
            avg_response_time=round(avg_time, 2)
        ))
        
        current = next_time
    
    return buckets


@router.get("/recent-errors", response_model=List[APIAnalyticsResponse])
async def get_recent_errors(
    limit: int = Query(50, description="Number of recent errors"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get recent API errors"""
    errors = db.query(APIAnalytics).filter(
        APIAnalytics.status_code >= 400
    ).order_by(
        desc(APIAnalytics.created_at)
    ).limit(limit).all()
    
    return errors


@router.get("/slow-requests", response_model=List[APIAnalyticsResponse])
async def get_slow_requests(
    threshold_ms: float = Query(1000, description="Response time threshold in ms"),
    limit: int = Query(50, description="Number of slow requests"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get slowest API requests"""
    slow_requests = db.query(APIAnalytics).filter(
        APIAnalytics.response_time_ms >= threshold_ms
    ).order_by(
        desc(APIAnalytics.response_time_ms)
    ).limit(limit).all()
    
    return slow_requests


@router.get("/report", response_model=APIAnalyticsReport)
async def get_analytics_report(
    hours: int = Query(24, description="Time window in hours"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics report"""
    summary = await get_analytics_summary(hours=hours, current_user=current_user, db=db)
    endpoint_stats = await get_endpoint_stats(hours=hours, current_user=current_user, db=db)
    time_series = await get_time_series(hours=hours, interval_minutes=60, current_user=current_user, db=db)
    recent_errors = await get_recent_errors(limit=20, current_user=current_user, db=db)
    
    return APIAnalyticsReport(
        summary=summary,
        endpoint_stats=endpoint_stats,
        time_series=time_series,
        recent_errors=recent_errors
    )


@router.delete("/cleanup")
async def cleanup_old_analytics(
    days: int = Query(30, description="Delete analytics older than N days"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Delete old analytics data"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted_count = db.query(APIAnalytics).filter(
        APIAnalytics.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Deleted {deleted_count} analytics records older than {days} days",
        "deleted_count": deleted_count
    }


@router.get("/search", response_model=List[APIAnalyticsResponse])
async def search_analytics(
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    user_id: Optional[int] = None,
    min_response_time: Optional[float] = None,
    max_response_time: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Search analytics with filters"""
    query = db.query(APIAnalytics)
    
    if endpoint:
        query = query.filter(APIAnalytics.endpoint.contains(endpoint))
    if method:
        query = query.filter(APIAnalytics.method == method)
    if status_code:
        query = query.filter(APIAnalytics.status_code == status_code)
    if user_id:
        query = query.filter(APIAnalytics.user_id == user_id)
    if min_response_time:
        query = query.filter(APIAnalytics.response_time_ms >= min_response_time)
    if max_response_time:
        query = query.filter(APIAnalytics.response_time_ms <= max_response_time)
    if start_date:
        query = query.filter(APIAnalytics.created_at >= start_date)
    if end_date:
        query = query.filter(APIAnalytics.created_at <= end_date)
    
    results = query.order_by(desc(APIAnalytics.created_at)).offset(offset).limit(limit).all()
    return results


@router.get("/geographic", response_model=List[GeographicStats])
async def get_geographic_stats(
    hours: int = Query(24, description="Time window in hours"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get geographic distribution of API requests"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by country
    countries = db.query(
        APIAnalytics.country,
        APIAnalytics.country_code,
        func.count(APIAnalytics.id).label('request_count'),
        func.avg(APIAnalytics.response_time_ms).label('avg_time'),
        func.count(func.distinct(APIAnalytics.user_id)).label('unique_users')
    ).filter(
        and_(
            APIAnalytics.created_at >= start_time,
            APIAnalytics.country.isnot(None)
        )
    ).group_by(
        APIAnalytics.country, APIAnalytics.country_code
    ).all()
    
    result = []
    for country in countries:
        # Calculate error rate for this country
        total_requests = country.request_count
        error_count = db.query(func.count(APIAnalytics.id)).filter(
            and_(
                APIAnalytics.created_at >= start_time,
                APIAnalytics.country == country.country,
                APIAnalytics.status_code >= 400
            )
        ).scalar()
        
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        result.append(GeographicStats(
            country=country.country,
            country_code=country.country_code,
            request_count=country.request_count,
            avg_response_time_ms=round(country.avg_time, 2),
            error_rate=round(error_rate, 2),
            unique_users=country.unique_users
        ))
    
    # Sort by request count
    result.sort(key=lambda x: x.request_count, reverse=True)
    return result


@router.get("/cities", response_model=List[CityStats])
async def get_city_stats(
    hours: int = Query(24, description="Time window in hours"),
    limit: int = Query(20, description="Top N cities"),
    current_user: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    """Get city-level statistics"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    cities = db.query(
        APIAnalytics.city,
        APIAnalytics.region,
        APIAnalytics.country,
        APIAnalytics.latitude,
        APIAnalytics.longitude,
        func.count(APIAnalytics.id).label('request_count')
    ).filter(
        and_(
            APIAnalytics.created_at >= start_time,
            APIAnalytics.city.isnot(None)
        )
    ).group_by(
        APIAnalytics.city,
        APIAnalytics.region,
        APIAnalytics.country,
        APIAnalytics.latitude,
        APIAnalytics.longitude
    ).order_by(
        desc('request_count')
    ).limit(limit).all()
    
    return [
        CityStats(
            city=c.city,
            region=c.region,
            country=c.country,
            request_count=c.request_count,
            latitude=c.latitude,
            longitude=c.longitude
        )
        for c in cities
    ]
