from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Any, Optional
from datetime import datetime
import re
import os
import shutil
from pathlib import Path
import uuid

from ..core.database import get_db
from ..core.security import get_current_active_user, get_current_admin_user
from ..models.user import User
from ..models.blog import Blog
from ..schemas.blog import (
    BlogCreate, BlogUpdate, BlogResponse, BlogWithAuthor, BlogListResponse
)

router = APIRouter(prefix="/blogs", tags=["Blogs"])

# Configure upload directory
UPLOAD_DIR = Path("uploads/blog_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def create_slug(title: str) -> str:
    """Generate a URL-friendly slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


@router.post("/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_blog_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """Upload a blog image (Admin only)."""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Return URL path (relative to server)
    image_url = f"/uploads/blog_images/{unique_filename}"
    return {"url": image_url, "filename": unique_filename}


@router.post("", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def create_blog(
    blog_data: BlogCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new blog post (Admin only)."""
    # Generate slug from title
    base_slug = create_slug(blog_data.title)
    slug = base_slug
    counter = 1
    
    # Ensure slug is unique
    while db.query(Blog).filter(Blog.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Determine publish time
    published_at = None
    scheduled_publish_at = blog_data.scheduled_publish_at
    
    if blog_data.is_published and not scheduled_publish_at:
        # Publish immediately
        published_at = datetime.now()
    elif scheduled_publish_at:
        # Check if scheduled time is in the past
        if scheduled_publish_at <= datetime.now():
            published_at = datetime.now()
            scheduled_publish_at = None
            blog_data.is_published = True
    
    new_blog = Blog(
        title=blog_data.title,
        slug=slug,
        content=blog_data.content,
        excerpt=blog_data.excerpt,
        featured_image=blog_data.featured_image,
        author_id=current_user.id,
        is_published=blog_data.is_published,
        published_at=published_at,
        scheduled_publish_at=scheduled_publish_at
    )
    
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    
    return new_blog


@router.get("", response_model=BlogListResponse)
async def get_blogs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    published_only: bool = True,
    db: Session = Depends(get_db)
) -> Any:
    """Get all blog posts with pagination."""
    query = db.query(Blog)
    
    # Filter by published status
    if published_only:
        query = query.filter(Blog.is_published == True)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Blog.title.ilike(search_term)) | 
            (Blog.excerpt.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Pagination
    blogs = query.order_by(Blog.published_at.desc(), Blog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "blogs": blogs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/admin", response_model=BlogListResponse)
async def get_all_blogs_admin(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all blog posts for admin (including drafts)."""
    query = db.query(Blog)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Blog.title.ilike(search_term)) | 
            (Blog.excerpt.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Pagination
    blogs = query.order_by(Blog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "blogs": blogs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/{slug}", response_model=BlogWithAuthor)
async def get_blog_by_slug(
    slug: str,
    db: Session = Depends(get_db)
) -> Any:
    """Get a blog post by slug."""
    blog = db.query(Blog).filter(Blog.slug == slug).first()
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    # Only show published blogs to non-admin users
    if not blog.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    return blog


@router.get("/admin/{blog_id}", response_model=BlogWithAuthor)
async def get_blog_by_id_admin(
    blog_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get a blog post by ID (Admin only)."""
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    return blog


@router.put("/{blog_id}", response_model=BlogResponse)
async def update_blog(
    blog_id: int,
    blog_data: BlogUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update a blog post (Admin only)."""
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    update_data = blog_data.dict(exclude_unset=True)
    
    # If title is updated, regenerate slug
    if "title" in update_data and update_data["title"] != blog.title:
        base_slug = create_slug(update_data["title"])
        slug = base_slug
        counter = 1
        
        while db.query(Blog).filter(Blog.slug == slug, Blog.id != blog_id).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        update_data["slug"] = slug
    
    # Handle publishing logic
    if "is_published" in update_data and update_data["is_published"] and not blog.is_published:
        # Publishing for the first time
        if "scheduled_publish_at" not in update_data or not update_data.get("scheduled_publish_at"):
            # Immediate publish
            update_data["published_at"] = datetime.now()
            update_data["scheduled_publish_at"] = None
    
    # Handle scheduled publish
    if "scheduled_publish_at" in update_data and update_data["scheduled_publish_at"]:
        scheduled_time = update_data["scheduled_publish_at"]
        if scheduled_time <= datetime.now():
            # Scheduled time is in the past, publish now
            update_data["published_at"] = datetime.now()
            update_data["scheduled_publish_at"] = None
            update_data["is_published"] = True
        else:
            # Schedule for future
            update_data["is_published"] = False
            update_data["published_at"] = None
    
    for field, value in update_data.items():
        setattr(blog, field, value)
    
    db.commit()
    db.refresh(blog)
    
    return blog


@router.delete("/{blog_id}")
async def delete_blog(
    blog_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete a blog post (Admin only)."""
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    db.delete(blog)
    db.commit()
    
    return {"message": "Blog post deleted successfully"}
