from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime


class SocialLinks(BaseModel):
    """Social media links schema"""
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None


class FeatureItem(BaseModel):
    """Feature item for home page"""
    icon: str = Field(..., description="Icon name or emoji")
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=300)


class TeamMember(BaseModel):
    """Team member for about page"""
    name: str = Field(..., max_length=100)
    role: str = Field(..., max_length=100)
    bio: Optional[str] = None
    image_url: Optional[str] = None
    social_links: Optional[SocialLinks] = None


class ValueItem(BaseModel):
    """Value item for about page"""
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=300)
    icon: Optional[str] = None


class BrandingSettingsBase(BaseModel):
    """Base schema for branding settings"""
    # Logo and Favicon
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    
    # Color scheme
    primary_color: Optional[str] = "#3182CE"
    secondary_color: Optional[str] = "#805AD5"
    accent_color: Optional[str] = "#38B2AC"
    
    # Home page
    home_hero_title: Optional[str] = None
    home_hero_subtitle: Optional[str] = None
    home_hero_image_url: Optional[str] = None
    home_hero_cta_text: Optional[str] = "Get Started"
    home_hero_cta_link: Optional[str] = "/courses"
    home_features: Optional[List[Dict[str, Any]]] = None
    
    # About page
    about_hero_title: Optional[str] = "About Us"
    about_hero_subtitle: Optional[str] = None
    about_mission: Optional[str] = None
    about_vision: Optional[str] = None
    about_story: Optional[str] = None
    about_team: Optional[List[Dict[str, Any]]] = None
    about_values: Optional[List[Dict[str, Any]]] = None
    
    # Footer
    footer_about_text: Optional[str] = None
    footer_social_links: Optional[Dict[str, str]] = None
    footer_contact_email: Optional[str] = None
    footer_contact_phone: Optional[str] = None
    
    # SEO
    site_title: Optional[str] = "Learning Management System"
    site_description: Optional[str] = None
    site_keywords: Optional[str] = None


class BrandingSettingsCreate(BrandingSettingsBase):
    """Schema for creating branding settings"""
    pass


class BrandingSettingsUpdate(BrandingSettingsBase):
    """Schema for updating branding settings (all fields optional)"""
    pass


class BrandingSettingsResponse(BrandingSettingsBase):
    """Schema for branding settings response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
