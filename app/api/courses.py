from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Optional, List

from ..core.database import get_db
from ..core.security import get_current_active_user, get_current_admin_user
from ..core.utils import slugify
from ..core.logger import api_logger, log_error
from ..models.user import User
from ..models.course import Course, Lesson
from ..models.enrollment import Enrollment
from ..schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse,
    CourseListResponse, LessonCreate, LessonUpdate, LessonResponse
)
from ..services.cloudflare import cloudflare_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    published_only: bool = True,
    db: Session = Depends(get_db)
) -> Any:
    """Get all courses with pagination and filters."""
    query = db.query(Course)
    
    # Filter published courses for non-admin users
    if published_only:
        query = query.filter(Course.is_published == True)
    
    # Filter by category
    if category:
        query = query.filter(Course.category == category)
    
    # Search in title and description
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Course.title.ilike(search_term)) | 
            (Course.description.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    courses = query.order_by(Course.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        "courses": courses,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{slug}", response_model=CourseDetailResponse)
async def get_course_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
) -> Any:
    """Get course details by slug."""
    course = db.query(Course).filter(Course.slug == slug).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if course is published or user is admin
    if not course.is_published:
        if not current_user or current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course not available"
            )
    
    return course


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new course (Admin only)."""
    # Generate slug from title
    slug = slugify(course_data.title)
    
    # Check if slug already exists
    existing_course = db.query(Course).filter(Course.slug == slug).first()
    if existing_course:
        # Append timestamp to make it unique
        from datetime import datetime
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
    
    new_course = Course(
        title=course_data.title,
        slug=slug,
        description=course_data.description,
        price=course_data.price,
        category=course_data.category,
        thumbnail_url=course_data.thumbnail_url,
        video_url=course_data.video_url,
        is_published=course_data.is_published,
        creator_id=current_user.id
    )
    
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    return new_course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update a course (Admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Update fields
    update_data = course_data.dict(exclude_unset=True)
    
    # If title is updated, regenerate slug
    if "title" in update_data:
        update_data["slug"] = slugify(update_data["title"])
    
    for field, value in update_data.items():
        setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> None:
    """Delete a course (Admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    db.delete(course)
    db.commit()


# Lesson endpoints
@router.post("/{course_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: int,
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Add a lesson to a course (Admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    new_lesson = Lesson(
        course_id=course_id,
        title=lesson_data.title,
        description=lesson_data.description,
        video_url=lesson_data.video_url,
        duration=lesson_data.duration,
        order=lesson_data.order,
        is_preview=lesson_data.is_preview
    )
    
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    
    return new_lesson


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update a lesson (Admin only)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    update_data = lesson_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)
    
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> None:
    """Delete a lesson (Admin only)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Delete video from Cloudflare Stream if exists
    if lesson.cloudflare_stream_id:
        try:
            await cloudflare_service.delete_video_from_stream(lesson.cloudflare_stream_id)
        except Exception as e:
            logger.warning(f"Failed to delete video from Stream: {str(e)}")
    
    db.delete(lesson)
    db.commit()


@router.post("/lessons/{lesson_id}/upload-video", response_model=LessonResponse)
async def upload_lesson_video(
    lesson_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Upload video for a lesson to Cloudflare Stream (Admin only).
    Supports MP4, MOV, AVI, WebM formats up to 5GB.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/avi"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (5GB max)
    max_size = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 5GB limit"
        )
    
    try:
        # Delete old video from Stream if exists
        if lesson.cloudflare_stream_id:
            try:
                await cloudflare_service.delete_video_from_stream(lesson.cloudflare_stream_id)
            except Exception as e:
                logger.warning(f"Failed to delete old video: {str(e)}")
        
        # Upload to Cloudflare Stream
        upload_result = await cloudflare_service.upload_video_to_stream(
            file_content=file_content,
            filename=file.filename,
            metadata={
                "name": lesson.title,
                "lesson_id": str(lesson_id),
                "course_id": str(lesson.course_id)
            }
        )
        
        # Update lesson with Cloudflare Stream details
        lesson.cloudflare_stream_id = upload_result["uid"]
        lesson.cloudflare_video_uid = upload_result["uid"]
        lesson.video_status = upload_result["status"]
        lesson.thumbnail_url = upload_result.get("thumbnail")
        lesson.video_url = upload_result.get("preview")
        lesson.lesson_type = "video"
        
        # Optionally upload to R2 as backup
        try:
            r2_url = cloudflare_service.upload_to_r2(
                file_content=file_content,
                filename=file.filename
            )
            if r2_url:
                logger.info(f"Video backed up to R2: {r2_url}")
        except Exception as e:
            logger.warning(f"Failed to backup to R2: {str(e)}")
        
        db.commit()
        db.refresh(lesson)
        
        api_logger.info(f"Video uploaded for lesson {lesson_id} by admin {current_user.id}")
        
        return lesson
        
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@router.get("/lessons/{lesson_id}/video-status", response_model=dict)
async def get_lesson_video_status(
    lesson_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get video encoding status from Cloudflare Stream (Admin only).
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    if not lesson.cloudflare_stream_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No video uploaded for this lesson"
        )
    
    try:
        video_details = await cloudflare_service.get_video_details(lesson.cloudflare_stream_id)
        
        # Update lesson if video is ready and duration is available
        if video_details["status"] == "ready":
            lesson.video_status = "ready"
            if video_details.get("duration"):
                lesson.video_duration_seconds = int(video_details["duration"])
            if video_details.get("thumbnail"):
                lesson.thumbnail_url = video_details["thumbnail"]
            db.commit()
        
        return {
            "status": video_details["status"],
            "duration": video_details.get("duration"),
            "thumbnail": video_details.get("thumbnail"),
            "uid": video_details["uid"]
        }
        
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video status: {str(e)}"
        )


@router.get("/{course_id}/check-access")
async def check_course_access(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Check if user has access to a course."""
    # Admin has access to all courses
    if current_user.role == "admin":
        return {"has_access": True, "reason": "admin"}
    
    # Check if user is enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id,
        Enrollment.is_active == True
    ).first()
    
    if enrollment:
        return {"has_access": True, "reason": "enrolled"}
    
    return {"has_access": False, "reason": "not_enrolled"}
