import time
import asyncio
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from ..core.database import SessionLocal
from ..models.api_analytics import APIAnalytics
from ..core.security import decode_token
from ..core.geolocation import get_geolocation_from_ip

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to track API analytics"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip analytics for certain paths
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/static", "/favicon.ico"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get request details
        method = request.method
        endpoint = request.url.path
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        
        # Get geolocation data from IP address
        geo_data = None
        if ip_address:
            geo_data = get_geolocation_from_ip(ip_address)
        
        # Try to get user ID from token
        user_id = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = int(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            pass  # User not authenticated or invalid token
        
        # Get request size
        request_size = None
        if "content-length" in request.headers:
            try:
                request_size = int(request.headers["content-length"])
            except ValueError:
                pass
        
        # Process request
        response = None
        error_message = None
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing request {method} {endpoint}: {e}")
            # Re-raise to let FastAPI handle it
            raise
        finally:
            # Calculate response time
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Get response size
            response_size = None
            if response and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except ValueError:
                    pass
            
            # Store analytics asynchronously
            asyncio.create_task(
                self._store_analytics(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    user_id=user_id,
                    ip_address=ip_address,
                    geo_data=geo_data,
                    user_agent=user_agent,
                    request_size=request_size,
                    response_size=response_size,
                    error_message=error_message
                )
            )
        
        return response
    
    async def _store_analytics(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: int = None,
        ip_address: str = None,
        geo_data: dict = None,
        user_agent: str = None,
        request_size: int = None,
        response_size: int = None,
        error_message: str = None
    ):
        """Store analytics data in database"""
        db = SessionLocal()
        try:
            analytics = APIAnalytics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                ip_address=ip_address,
                country=geo_data.get("country") if geo_data else None,
                country_code=geo_data.get("country_code") if geo_data else None,
                region=geo_data.get("region") if geo_data else None,
                city=geo_data.get("city") if geo_data else None,
                latitude=geo_data.get("lat") if geo_data else None,
                longitude=geo_data.get("lon") if geo_data else None,
                timezone=geo_data.get("timezone") if geo_data else None,
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                error_message=error_message
            )
            db.add(analytics)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to store analytics: {e}")
            db.rollback()
        finally:
            db.close()
