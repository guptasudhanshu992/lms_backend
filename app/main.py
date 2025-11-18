from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from pathlib import Path

from .core.config import settings
from .core.database import engine, Base, SessionLocal
from .core.security import get_password_hash
from .models.user import User
from .models.blog import Blog  # Import Blog to ensure relationship is loaded
from .models.log import Log  # Import Log model
from .models.api_analytics import APIAnalytics  # Import APIAnalytics model
from .core.logger import app_logger, api_logger, log_error
from .core.analytics_middleware import AnalyticsMiddleware
from .api import auth, users, courses, enrollments, payments, admin, blogs, scorm, curriculum, cart_wishlist, coupons, logs, analytics, sitemap, branding


def create_admin_user():
    """Create admin user from environment variables if not exists"""
    db = SessionLocal()
    try:
        # Check if admin exists
        admin_user = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                full_name=settings.ADMIN_FULL_NAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print(f"✓ Admin user created: {settings.ADMIN_EMAIL}")
        else:
            print(f"✓ Admin user already exists: {settings.ADMIN_EMAIL}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


# Create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app_logger.info("Starting FastAPI application...")
    Base.metadata.create_all(bind=engine)
    app_logger.info("Database tables created")
    create_admin_user()  # Create admin user on startup
    app_logger.info("Application startup complete")
    yield
    # Shutdown
    pass


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add analytics middleware
app.add_middleware(AnalyticsMiddleware)

# Mount static files for uploads
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()
    
    # Log request
    api_logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    api_logger.info(
        f"Response: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(exc, f"Unhandled exception in {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to LMS API",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(enrollments.router)
app.include_router(payments.router)
app.include_router(admin.router)
app.include_router(blogs.router)
app.include_router(scorm.router)
app.include_router(curriculum.router)
app.include_router(cart_wishlist.router)
app.include_router(coupons.router)
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(sitemap.router, prefix="/api", tags=["seo"])
app.include_router(branding.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
