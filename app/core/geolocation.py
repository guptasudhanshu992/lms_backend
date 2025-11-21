import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Cache for IP geolocation data to avoid excessive API calls
_geolocation_cache: Dict[str, Dict[str, Any]] = {}


def get_geolocation_from_ip(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Get geolocation data from IP address using ip-api.com (free, no key required)
    
    Returns dict with: country, country_code, region, city, lat, lon, timezone
    Returns None if lookup fails
    
    TEMPORARILY DISABLED: Returns local data to avoid blocking requests
    """
    # Always return local data to avoid blocking - geolocation disabled for now
    return {
        "country": "Local",
        "country_code": "LOCAL",
        "region": "Local",
        "city": "Local",
        "lat": 0.0,
        "lon": 0.0,
        "timezone": "UTC"
    }


def clear_geolocation_cache():
    """Clear the geolocation cache (useful for testing or periodic cleanup)"""
    global _geolocation_cache
    _geolocation_cache.clear()
    logger.info("Geolocation cache cleared")


def get_cache_size() -> int:
    """Get the number of cached geolocation entries"""
    return len(_geolocation_cache)
