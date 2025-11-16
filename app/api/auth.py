from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
from datetime import timedelta

from ..core.database import get_db
from ..core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, decode_token, get_current_active_user
)
from ..core.config import settings
from ..core.utils import generate_reset_token, create_reset_token_expiry, is_token_expired
from ..core.logger import auth_logger, log_error, log_auth_event
from ..core.validation import validate_email, validate_full_name, validate_password, validate_reset_token, validate_oauth_id, validate_url, sanitize_string
from ..core.email_service import email_service
from ..models.user import User
from ..schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    PasswordResetRequest, PasswordReset, RefreshTokenRequest,
    OAuthUserCreate, PasswordChange
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user."""
    # Validate and sanitize inputs
    try:
        clean_email = validate_email(user_data.email)
        clean_name = validate_full_name(user_data.full_name)
        validate_password(user_data.password)  # Only validates, doesn't return (will be hashed)
    except HTTPException as e:
        log_auth_event(f"Signup validation failed: {e.detail}", email=user_data.email, success=False)
        raise
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == clean_email).first()
    
    if existing_user:
        log_auth_event("Signup failed - email already exists", email=user_data.email, success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create new user with sanitized data
        new_user = User(
            email=clean_email,
            full_name=clean_name,
            hashed_password=get_password_hash(user_data.password),
            role="student"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        log_auth_event("User signup successful", user_id=new_user.id, email=new_user.email, success=True)
        
        # Send welcome email asynchronously in background
        background_tasks.add_task(
            email_service.send_welcome_email,
            to_email=new_user.email,
            full_name=new_user.full_name
        )
        
        return new_user
    except Exception as e:
        db.rollback()
        log_error(e, "Error during user signup", user_id=None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """Login and get access token."""
    # Validate and sanitize email input
    try:
        clean_email = validate_email(user_data.email)
    except HTTPException:
        # Don't reveal validation details for login
        log_auth_event("Login failed - invalid email format", email=user_data.email, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Find user by email
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        log_auth_event("Login failed - invalid credentials", email=user_data.email, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        log_auth_event("Login failed - inactive account", user_id=user.id, email=user.email, success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    log_auth_event("Login successful", user_id=user.id, email=user.email, success=True)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Refresh access token using refresh token."""
    try:
        payload = decode_token(token_data.refresh_token)
        token_type = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user
        }
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/password-reset-request")
async def request_password_reset(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """Request a password reset token."""
    # Validate and sanitize email
    try:
        clean_email = validate_email(request_data.email)
    except HTTPException:
        # Don't reveal if email is invalid for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expiry = create_reset_token_expiry()
    
    db.commit()
    
    # Send password reset email asynchronously
    background_tasks.add_task(
        email_service.send_password_reset_email,
        to_email=user.email,
        full_name=user.full_name,
        reset_token=reset_token
    )
    
    log_auth_event("Password reset requested", user_id=user.id, email=user.email, success=True)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
) -> Any:
    """Reset password using reset token."""
    # Validate inputs
    clean_token = validate_reset_token(reset_data.token)
    validate_password(reset_data.new_password)
    
    user = db.query(User).filter(User.reset_token == clean_token).first()
    
    if not user:
        log_auth_event("Password reset failed - invalid token", success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if is_token_expired(user.reset_token_expiry):
        log_auth_event("Password reset failed - expired token", user_id=user.id, email=user.email, success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    
    db.commit()
    
    log_auth_event("Password reset successful", user_id=user.id, email=user.email, success=True)
    
    return {"message": "Password reset successful"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)) -> Any:
    """Logout user (client should discard tokens)."""
    # In a real implementation with Redis, you would blacklist the token here
    return {"message": "Successfully logged out"}


@router.post("/oauth/google", response_model=TokenResponse)
async def oauth_google(user_data: OAuthUserCreate, db: Session = Depends(get_db)) -> Any:
    """Login or register with Google OAuth."""
    # Validate and sanitize OAuth inputs
    clean_email = validate_email(user_data.email)
    clean_name = validate_full_name(user_data.full_name)
    clean_oauth_id = validate_oauth_id(user_data.oauth_id, "Google")
    clean_avatar_url = validate_url(user_data.avatar_url, "Avatar URL") if user_data.avatar_url else None
    
    # Check if user exists with this OAuth provider
    user = db.query(User).filter(
        User.oauth_provider == "google",
        User.oauth_id == clean_oauth_id
    ).first()
    
    if not user:
        # Check if email already exists (regular signup)
        existing_user = db.query(User).filter(User.email == clean_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered with password login"
            )
        
        # Create new OAuth user with sanitized data
        user = User(
            email=clean_email,
            full_name=clean_name,
            oauth_provider="google",
            oauth_id=clean_oauth_id,
            avatar_url=clean_avatar_url,
            role="student",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "type": "refresh"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/oauth/linkedin", response_model=TokenResponse)
async def oauth_linkedin(user_data: OAuthUserCreate, db: Session = Depends(get_db)) -> Any:
    """Login or register with LinkedIn OAuth."""
    # Validate and sanitize OAuth inputs
    clean_email = validate_email(user_data.email)
    clean_name = validate_full_name(user_data.full_name)
    clean_oauth_id = validate_oauth_id(user_data.oauth_id, "LinkedIn")
    clean_avatar_url = validate_url(user_data.avatar_url, "Avatar URL") if user_data.avatar_url else None
    
    # Check if user exists with this OAuth provider
    user = db.query(User).filter(
        User.oauth_provider == "linkedin",
        User.oauth_id == clean_oauth_id
    ).first()
    
    if not user:
        # Check if email already exists (regular signup)
        existing_user = db.query(User).filter(User.email == clean_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered with password login"
            )
        
        # Create new OAuth user with sanitized data
        user = User(
            email=clean_email,
            full_name=clean_name,
            oauth_provider="linkedin",
            oauth_id=clean_oauth_id,
            avatar_url=clean_avatar_url,
            role="student",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "type": "refresh"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Change user password."""
    # Validate new password
    validate_password(password_data.new_password)
    
    # Check if user has a password (not OAuth user)
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth users"
        )
    
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
