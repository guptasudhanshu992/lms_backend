# Geographic Analytics Endpoints

Add these endpoints to the analytics.py file:

```python
from ..schemas.api_analytics import GeographicStats, CityStats

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
```
