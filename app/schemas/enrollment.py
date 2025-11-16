from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .course import CourseResponse


class EnrollmentBase(BaseModel):
    course_id: int


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    is_active: bool
    progress: float
    enrolled_at: datetime
    last_accessed: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EnrollmentWithCourse(EnrollmentResponse):
    course: CourseResponse
    
    class Config:
        from_attributes = True


class EnrollmentStatsResponse(BaseModel):
    total_enrollments: int
    active_enrollments: int
    completed_courses: int
    in_progress_courses: int
