import secrets
from typing import Optional
from datetime import datetime, timedelta


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def create_reset_token_expiry() -> datetime:
    """Create expiry time for reset token (1 hour)."""
    return datetime.utcnow() + timedelta(hours=1)


def is_token_expired(expiry_time: datetime) -> bool:
    """Check if a token has expired."""
    return datetime.utcnow() > expiry_time


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text
