from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
from pathlib import Path
import uuid

from ..core.database import get_db
from ..core.security import get_current_admin_user
from ..models.user import User
from ..models.branding import BrandingSettings
from ..schemas.branding import (
    BrandingSettingsCreate,
    BrandingSettingsUpdate,
    BrandingSettingsResponse
)

router = APIRouter(prefix="/api/branding", tags=["branding"])

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads/branding")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/settings", response_model=BrandingSettingsResponse)
async def get_branding_settings(db: Session = Depends(get_db)):
    """
    Get current branding settings (public endpoint).
    Returns default settings if none exist, creating them in the database.
    """
    settings = db.query(BrandingSettings).first()
    
    if not settings:
        # Create default settings in database
        settings = BrandingSettings(
            logo_url=None,
            favicon_url=None,
            primary_color="#3182CE",
            secondary_color="#805AD5",
            accent_color="#38B2AC",
            site_title="Learning Management System",
            home_hero_cta_text="Get Started",
            home_hero_cta_link="/courses",
            about_hero_title="About Us"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/settings", response_model=BrandingSettingsResponse)
async def update_branding_settings(
    settings_data: BrandingSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update branding settings (admin only).
    Creates new settings if none exist.
    """
    settings = db.query(BrandingSettings).first()
    
    if not settings:
        # Create new settings
        settings = BrandingSettings()
        db.add(settings)
    
    # Update fields
    update_data = settings_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/settings", response_model=BrandingSettingsResponse)
async def create_branding_settings(
    settings_data: BrandingSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create initial branding settings (admin only).
    Only works if no settings exist.
    """
    existing = db.query(BrandingSettings).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Branding settings already exist. Use PUT to update."
        )
    
    settings = BrandingSettings(**settings_data.model_dump())
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    return settings


@router.delete("/settings")
async def reset_branding_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Reset branding settings to defaults (admin only).
    """
    settings = db.query(BrandingSettings).first()
    if settings:
        db.delete(settings)
        db.commit()
    
    return {"message": "Branding settings reset to defaults"}


@router.post("/upload/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload logo image (admin only).
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"logo_{uuid.uuid4().hex}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update settings
    settings = db.query(BrandingSettings).first()
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
    
    # Store relative path for URL
    settings.logo_url = f"/uploads/branding/{unique_filename}"
    db.commit()
    db.refresh(settings)
    
    return {"url": settings.logo_url, "message": "Logo uploaded successfully"}


@router.post("/upload/favicon")
async def upload_favicon(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload favicon image (admin only).
    """
    # Validate file type
    allowed_types = ["image/png", "image/x-icon", "image/vnd.microsoft.icon", "image/ico", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: ICO, PNG, SVG"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "ico"
    unique_filename = f"favicon_{uuid.uuid4().hex}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update settings
    settings = db.query(BrandingSettings).first()
    if not settings:
        settings = BrandingSettings()
        db.add(settings)
    
    settings.favicon_url = f"/uploads/branding/{unique_filename}"
    db.commit()
    db.refresh(settings)
    
    return {"url": settings.favicon_url, "message": "Favicon uploaded successfully"}


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    image_type: str = "general",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload general image (hero images, team photos, etc.) - admin only.
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{image_type}_{uuid.uuid4().hex}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"url": f"/uploads/branding/{unique_filename}", "message": "Image uploaded successfully"}
