import requests
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
    """
    if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
        return {
            "country": "Local",
            "country_code": "LOCAL",
            "region": "Local",
            "city": "Local",
            "lat": 0.0,
            "lon": 0.0,
            "timezone": "UTC"
        }
    
    # Check cache first
    if ip_address in _geolocation_cache:
        return _geolocation_cache[ip_address]
    
    try:
        # Use ip-api.com free API (no key required, 45 requests/minute limit)
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            timeout=2,
            params={"fields": "status,message,country,countryCode,region,regionName,city,lat,lon,timezone"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "success":
                geo_data = {
                    "country": data.get("country", "Unknown"),
                    "country_code": data.get("countryCode", "XX"),
                    "region": data.get("regionName", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "lat": data.get("lat", 0.0),
                    "lon": data.get("lon", 0.0),
                    "timezone": data.get("timezone", "UTC")
                }
                
                # Cache the result
                _geolocation_cache[ip_address] = geo_data
                return geo_data
            else:
                logger.warning(f"IP geolocation lookup failed for {ip_address}: {data.get('message')}")
                return None
    except requests.RequestException as e:
        logger.error(f"Failed to get geolocation for IP {ip_address}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in geolocation lookup for {ip_address}: {e}")
        return None


def clear_geolocation_cache():
    """Clear the geolocation cache (useful for testing or periodic cleanup)"""
    global _geolocation_cache
    _geolocation_cache.clear()
    logger.info("Geolocation cache cleared")


def get_cache_size() -> int:
    """Get the number of cached geolocation entries"""
    return len(_geolocation_cache)
