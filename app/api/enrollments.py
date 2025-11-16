from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, List

from ..core.database import get_db
from ..core.security import get_current_active_user
from ..models.user import User
from ..models.course import Course
from ..models.enrollment import Enrollment
from ..schemas.enrollment import (
    EnrollmentCreate, EnrollmentResponse, EnrollmentWithCourse, EnrollmentStatsResponse
)

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment_data: EnrollmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Enroll user in a course (requires payment verification)."""
    # Check if course exists
    course = db.query(Course).filter(Course.id == enrollment_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if already enrolled
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == enrollment_data.course_id
    ).first()
    
    if existing_enrollment:
        if existing_enrollment.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already enrolled in this course"
            )
        else:
            # Reactivate enrollment
            existing_enrollment.is_active = True
            db.commit()
            db.refresh(existing_enrollment)
            return existing_enrollment
    
    # Create new enrollment
    new_enrollment = Enrollment(
        user_id=current_user.id,
        course_id=enrollment_data.course_id,
        is_active=True,
        progress=0.0
    )
    
    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)
    
    return new_enrollment


@router.get("/my-courses", response_model=List[EnrollmentWithCourse])
async def get_my_enrollments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all courses the current user is enrolled in."""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.is_active == True
    ).all()
    
    return enrollments


@router.get("/stats", response_model=EnrollmentStatsResponse)
async def get_enrollment_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get enrollment statistics for current user."""
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()
    
    total_enrollments = len(enrollments)
    active_enrollments = sum(1 for e in enrollments if e.is_active)
    completed_courses = sum(1 for e in enrollments if e.progress >= 100)
    in_progress_courses = sum(1 for e in enrollments if 0 < e.progress < 100)
    
    return {
        "total_enrollments": total_enrollments,
        "active_enrollments": active_enrollments,
        "completed_courses": completed_courses,
        "in_progress_courses": in_progress_courses
    }


@router.get("/{course_id}", response_model=EnrollmentResponse)
async def get_enrollment_by_course(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get enrollment details for a specific course."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enrolled in this course"
        )
    
    return enrollment


@router.put("/{enrollment_id}/progress")
async def update_enrollment_progress(
    enrollment_id: int,
    progress: float,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update course progress for an enrollment."""
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id,
        Enrollment.user_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    if progress < 0 or progress > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Progress must be between 0 and 100"
        )
    
    enrollment.progress = progress
    db.commit()
    db.refresh(enrollment)
    
    return {"message": "Progress updated successfully", "progress": enrollment.progress}
