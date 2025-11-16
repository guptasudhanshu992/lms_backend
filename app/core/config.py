from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "LMS MVP"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development or production
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = ""
    
    def get_database_url(self) -> str:
        """Return appropriate database URL based on environment"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if self.ENVIRONMENT.lower() == "production":
            # Production: PostgreSQL
            return os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:password@localhost:5432/lms_db"
            )
        else:
            # Development: SQLite
            return "sqlite:///./lms.db"
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@yourlms.com"
    FROM_NAME: str = "LMS Platform"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Admin User
    ADMIN_EMAIL: str = "admin@lms.com"
    ADMIN_PASSWORD: str = "Admin@123456"
    ADMIN_FULL_NAME: str = "System Administrator"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
