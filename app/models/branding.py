from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class BrandingSettings(Base):
    """Model for storing platform branding and customization settings"""
    __tablename__ = "branding_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Logo and Favicon
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    
    # Color scheme
    primary_color = Column(String(20), nullable=True, default="#3182CE")  # Chakra blue.500
    secondary_color = Column(String(20), nullable=True, default="#805AD5")  # Chakra purple.500
    accent_color = Column(String(20), nullable=True, default="#38B2AC")  # Chakra teal.500
    
    # Home page customization
    home_hero_title = Column(String(200), nullable=True)
    home_hero_subtitle = Column(Text, nullable=True)
    home_hero_image_url = Column(String(500), nullable=True)
    home_hero_cta_text = Column(String(100), nullable=True, default="Get Started")
    home_hero_cta_link = Column(String(200), nullable=True, default="/courses")
    home_features = Column(JSON, nullable=True)  # Array of feature objects
    
    # About page customization
    about_hero_title = Column(String(200), nullable=True, default="About Us")
    about_hero_subtitle = Column(Text, nullable=True)
    about_mission = Column(Text, nullable=True)
    about_vision = Column(Text, nullable=True)
    about_story = Column(Text, nullable=True)
    about_team = Column(JSON, nullable=True)  # Array of team member objects
    about_values = Column(JSON, nullable=True)  # Array of value objects
    
    # Footer customization
    footer_about_text = Column(Text, nullable=True)
    footer_social_links = Column(JSON, nullable=True)  # Object with social media links
    footer_contact_email = Column(String(200), nullable=True)
    footer_contact_phone = Column(String(50), nullable=True)
    
    # SEO and metadata
    site_title = Column(String(200), nullable=True, default="Learning Management System")
    site_description = Column(Text, nullable=True)
    site_keywords = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<BrandingSettings(id={self.id})>"
