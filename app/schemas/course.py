from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# SCORM Schemas
class SCOBase(BaseModel):
    identifier: str
    title: str
    description: Optional[str] = None
    launch_url: str
    scorm_type: str = "sco"  # "sco" or "asset"
    order_index: int = 0
    prerequisites: Optional[Dict[str, Any]] = None
    max_time_allowed: Optional[int] = None
    completion_threshold: Optional[float] = None
    min_normalized_measure: Optional[float] = None
    launch_data: Optional[str] = None
    mastery_score: Optional[float] = None


class SCOCreate(SCOBase):
    course_id: int


class SCOResponse(SCOBase):
    id: int
    course_id: int
    resource_identifier: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class LearnerAttemptResponse(BaseModel):
    id: int
    user_id: int
    sco_id: int
    attempt_number: int
    completion_status: str
    success_status: str
    score_raw: Optional[float] = None
    score_scaled: Optional[float] = None
    total_time: int
    location: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Lesson Schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    lesson_type: str = "video"  # video, text, file, scorm, quiz
    video_url: Optional[str] = None
    content: Optional[str] = None  # For text lessons
    file_url: Optional[str] = None  # For file lessons
    duration: Optional[int] = None
    order: int = 0
    is_preview: bool = False
    is_scorm: bool = False
    sco_id: Optional[int] = None
    
    # Cloudflare Stream fields
    cloudflare_stream_id: Optional[str] = None
    cloudflare_video_uid: Optional[str] = None
    video_status: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_duration_seconds: Optional[int] = None


class LessonCreate(LessonBase):
    section_id: Optional[int] = None


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    lesson_type: Optional[str] = None
    video_url: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    duration: Optional[int] = None
    order: Optional[int] = None
    is_preview: Optional[bool] = None
    is_scorm: Optional[bool] = None
    sco_id: Optional[int] = None
    section_id: Optional[int] = None
    
    # Cloudflare Stream fields
    cloudflare_stream_id: Optional[str] = None
    cloudflare_video_uid: Optional[str] = None
    video_status: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_duration_seconds: Optional[int] = None


class LessonResponse(LessonBase):
    id: int
    course_id: int
    section_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Course Schemas
class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # SCORM fields
    scorm_version: Optional[str] = None
    scorm_package_url: Optional[str] = None
    manifest_identifier: Optional[str] = None
    mastery_score: Optional[float] = None
    completion_threshold: Optional[float] = None
    time_limit_minutes: Optional[int] = None
    launch_data: Optional[str] = None
    max_attempts: Optional[int] = None
    sequencing_rules: Optional[Dict[str, Any]] = None
    navigation_controls: Optional[Dict[str, Any]] = None
    completion_criteria: Optional[Dict[str, Any]] = None
    success_criteria: Optional[Dict[str, Any]] = None


class CourseCreate(CourseBase):
    is_published: bool = False
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return round(v, 2)


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    is_published: Optional[bool] = None
    
    # SCORM fields
    scorm_version: Optional[str] = None
    scorm_package_url: Optional[str] = None
    manifest_identifier: Optional[str] = None
    mastery_score: Optional[float] = None
    completion_threshold: Optional[float] = None
    time_limit_minutes: Optional[int] = None
    launch_data: Optional[str] = None
    max_attempts: Optional[int] = None
    sequencing_rules: Optional[Dict[str, Any]] = None
    navigation_controls: Optional[Dict[str, Any]] = None
    completion_criteria: Optional[Dict[str, Any]] = None
    success_criteria: Optional[Dict[str, Any]] = None


class CourseResponse(CourseBase):
    id: int
    slug: str
    is_published: bool
    creator_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    sections: List[SectionResponse] = []
    lessons: List[LessonResponse] = []
    scos: List[SCOResponse] = []
    
    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    page: int
    page_size: int


# Section Schemas
class SectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order: int = 0


class SectionCreate(SectionBase):
    course_id: int


class SectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    order: Optional[int] = None


class SectionResponse(SectionBase):
    id: int
    course_id: int
    created_at: datetime
    lessons: List[LessonResponse] = []
    
    class Config:
        from_attributes = True


# Quiz Schemas
class QuizQuestionOption(BaseModel):
    id: str
    text: str


class QuizQuestionBase(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"  # multiple_choice, true_false, short_answer
    order: int = 0
    points: float = 1.0
    options: Optional[List[QuizQuestionOption]] = None
    correct_answer: Any  # Can be list, string, or bool
    explanation: Optional[str] = None


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    order: Optional[int] = None
    points: Optional[float] = None
    options: Optional[List[QuizQuestionOption]] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None


class QuizQuestionResponse(QuizQuestionBase):
    id: int
    quiz_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class QuizBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    passing_score: float = 70.0
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    shuffle_questions: bool = False
    show_correct_answers: bool = True


class QuizCreate(QuizBase):
    lesson_id: int
    questions: Optional[List[QuizQuestionCreate]] = []


class QuizUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    passing_score: Optional[float] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    shuffle_questions: Optional[bool] = None
    show_correct_answers: Optional[bool] = None


class QuizResponse(QuizBase):
    id: int
    lesson_id: int
    created_at: datetime
    questions: List[QuizQuestionResponse] = []
    
    class Config:
        from_attributes = True


class QuizAttemptCreate(BaseModel):
    answers: Dict[int, Any]  # {question_id: answer}


class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    user_id: int
    attempt_number: int
    answers: Dict[int, Any]
    score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    passed: bool
    time_taken_seconds: Optional[int] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
