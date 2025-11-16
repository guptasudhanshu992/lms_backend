import re
from typing import Optional
from fastapi import HTTPException, status


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize string input to prevent injection attacks.
    Removes potentially dangerous characters and limits length.
    """
    if not value:
        return ""
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    return value[:max_length]


def validate_email(email: str) -> str:
    """
    Validate and sanitize email address.
    Returns sanitized email or raises HTTPException.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    # Sanitize
    email = sanitize_string(email, max_length=255).lower()
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check length
    if len(email) < 5 or len(email) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email must be between 5 and 255 characters"
        )
    
    return email


def validate_full_name(name: str) -> str:
    """
    Validate and sanitize full name.
    Returns sanitized name or raises HTTPException.
    """
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required"
        )
    
    # Sanitize
    name = sanitize_string(name, max_length=255)
    
    # Check if empty after sanitization
    if not name or len(name.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name cannot be empty"
        )
    
    # Check length
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 2 characters long"
        )
    
    if len(name) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must not exceed 255 characters"
        )
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    name_pattern = r'^[a-zA-Z\s\'-]+$'
    if not re.match(name_pattern, name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name can only contain letters, spaces, hyphens, and apostrophes"
        )
    
    return name


def validate_password(password: str) -> None:
    """
    Validate password strength.
    Raises HTTPException if password doesn't meet requirements.
    """
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    
    # Check length
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not exceed 128 characters"
        )
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/`~]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )


def sanitize_coupon_code(code: str) -> str:
    """
    Sanitize and validate coupon code.
    Returns sanitized code or raises HTTPException.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code is required"
        )
    
    # Convert to uppercase and remove whitespace
    code = code.upper().strip()
    
    # Remove potentially dangerous characters
    code = re.sub(r'[^A-Z0-9\-_]', '', code)
    
    # Check length
    if len(code) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code must be at least 3 characters long"
        )
    
    if len(code) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code must not exceed 50 characters"
        )
    
    return code


def validate_reset_token(token: str) -> str:
    """
    Validate and sanitize password reset token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is required"
        )
    
    # Remove whitespace
    token = token.strip()
    
    # Only allow alphanumeric characters and hyphens (typical UUID format)
    if not re.match(r'^[a-zA-Z0-9\-]+$', token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token format"
        )
    
    return token


def sanitize_search_query(query: str, max_length: int = 100) -> str:
    """
    Sanitize search query to prevent SQL injection.
    """
    if not query:
        return ""
    
    # Basic sanitization
    query = sanitize_string(query, max_length=max_length)
    
    # Remove SQL special characters that could be dangerous
    # Keep alphanumeric, spaces, and basic punctuation
    query = re.sub(r'[^\w\s\-.,!?\'"]', '', query)
    
    return query.strip()


def validate_oauth_id(oauth_id: str, provider: str) -> str:
    """
    Validate OAuth ID from provider.
    """
    if not oauth_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth ID from {provider} is required"
        )
    
    # Sanitize
    oauth_id = sanitize_string(oauth_id, max_length=255)
    
    # Only allow alphanumeric and basic separators
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', oauth_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth ID format"
        )
    
    return oauth_id


def validate_url(url: Optional[str], field_name: str = "URL") -> Optional[str]:
    """
    Validate and sanitize URL (for avatar URLs, etc.).
    """
    if not url:
        return None
    
    # Sanitize
    url = sanitize_string(url, max_length=500).strip()
    
    # Basic URL validation
    url_pattern = r'^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$'
    if not re.match(url_pattern, url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    
    # Ensure it's https for security (optional but recommended)
    if not url.startswith('https://'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must use HTTPS"
        )
    
    return url
