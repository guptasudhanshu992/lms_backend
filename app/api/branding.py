from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

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


@router.get("/settings", response_model=BrandingSettingsResponse)
async def get_branding_settings(db: Session = Depends(get_db)):
    """
    Get current branding settings (public endpoint).
    Returns default settings if none exist.
    """
    settings = db.query(BrandingSettings).first()
    
    if not settings:
        # Return default settings
        settings = BrandingSettings(
            id=1,
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
