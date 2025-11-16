from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, List

from ..core.database import get_db
from ..core.security import get_current_admin_user
from ..models.user import User
from ..models.course import Course
from ..models.enrollment import Enrollment
from ..models.payment import Payment
from ..schemas.user import UserResponse
from ..schemas.course import CourseResponse, CourseDetailResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get admin dashboard statistics."""
    # Total users
    total_users = db.query(User).count()
    total_students = db.query(User).filter(User.role == "student").count()
    total_admins = db.query(User).filter(User.role == "admin").count()
    
    # Total courses
    total_courses = db.query(Course).count()
    published_courses = db.query(Course).filter(Course.is_published == True).count()
    
    # Total enrollments
    total_enrollments = db.query(Enrollment).count()
    active_enrollments = db.query(Enrollment).filter(Enrollment.is_active == True).count()
    
    # Total revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == 'completed'
    ).scalar() or 0.0
    
    # Recent transactions (last 10)
    recent_payments = db.query(Payment).order_by(
        Payment.created_at.desc()
    ).limit(10).all()
    
    return {
        "users": {
            "total": total_users,
            "students": total_students,
            "admins": total_admins
        },
        "courses": {
            "total": total_courses,
            "published": published_courses,
            "draft": total_courses - published_courses
        },
        "enrollments": {
            "total": total_enrollments,
            "active": active_enrollments
        },
        "revenue": {
            "total": total_revenue
        },
        "recent_payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "course_id": p.course_id,
                "amount": p.amount,
                "status": p.status,
                "created_at": p.created_at
            } for p in recent_payments
        ]
    }


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all users (Admin only)."""
    users = db.query(User).all()
    return users


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user details (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update full_name if provided
    if "full_name" in update_data and update_data["full_name"]:
        user.full_name = update_data["full_name"]
    
    # Update email if provided
    if "email" in update_data and update_data["email"]:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(User.email == update_data["email"], User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = update_data["email"]
    
    # Update is_active if provided
    if "is_active" in update_data:
        user.is_active = update_data["is_active"]
    
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user role (Admin only)."""
    if role not in ["admin", "student"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role
    db.commit()
    db.refresh(user)
    
    return {"message": "User role updated successfully", "user": user}


@router.get("/enrollments")
async def get_all_enrollments(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all enrollments (Admin only)."""
    enrollments = db.query(Enrollment).all()
    return enrollments


@router.get("/courses/{course_id}/enrollments")
async def get_course_enrollments(
    course_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all enrollments for a specific course (Admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course_id
    ).all()
    
    return {
        "course_id": course_id,
        "course_title": course.title,
        "total_enrollments": len(enrollments),
        "enrollments": enrollments
    }


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course_by_id(
    course_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get course details by ID (Admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return course
