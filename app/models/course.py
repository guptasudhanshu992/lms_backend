from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0.0, nullable=False)
    category = Column(String(100), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False)
    
    # SCORM Compliance Fields
    scorm_version = Column(String(50), nullable=True)  # e.g., "2004 4th Edition", "1.2"
    scorm_package_url = Column(String(500), nullable=True)  # URL to uploaded SCORM package
    manifest_identifier = Column(String(255), nullable=True)  # From imsmanifest.xml
    mastery_score = Column(Float, nullable=True)  # Minimum score for completion
    completion_threshold = Column(Float, nullable=True)  # Completion percentage threshold
    time_limit_minutes = Column(Integer, nullable=True)  # Maximum time for course
    launch_data = Column(Text, nullable=True)  # Launch parameters for SCORM content
    max_attempts = Column(Integer, nullable=True)  # Maximum attempts allowed
    
    # Sequencing and Navigation (SCORM 2004)
    sequencing_rules = Column(JSON, nullable=True)  # JSON sequencing rules
    navigation_controls = Column(JSON, nullable=True)  # Navigation settings
    
    # Completion Criteria
    completion_criteria = Column(JSON, nullable=True)  # JSON completion rules
    success_criteria = Column(JSON, nullable=True)  # JSON success rules
    
    # Creator
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_courses", foreign_keys=[creator_id])
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="course", cascade="all, delete-orphan", order_by="Section.order")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="course")
    scos = relationship("SCO", back_populates="course", cascade="all, delete-orphan")


class Section(Base):
    """Course sections to organize lessons"""
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="sections")
    lessons = relationship("Lesson", back_populates="section", cascade="all, delete-orphan", order_by="Lesson.order")


class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)  # Optional section grouping
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Lesson Type and Content
    lesson_type = Column(String(50), default="video")  # video, text, file, scorm, quiz
    video_url = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # HTML/Markdown content for text lessons
    file_url = Column(String(500), nullable=True)  # For downloadable files
    
    duration = Column(Integer, nullable=True)  # Duration in seconds
    order = Column(Integer, default=0)
    is_preview = Column(Boolean, default=False)  # Can be viewed without enrollment
    
    # SCORM SCO Integration
    sco_id = Column(Integer, ForeignKey("scos.id"), nullable=True)  # Link to SCORM SCO
    is_scorm = Column(Boolean, default=False)  # Is this a SCORM lesson?
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="lessons")
    section = relationship("Section", back_populates="lessons")
    sco = relationship("SCO", foreign_keys=[sco_id])
    quiz = relationship("Quiz", back_populates="lesson", uselist=False, cascade="all, delete-orphan")


class Quiz(Base):
    """Quiz attached to a lesson"""
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Quiz Settings
    passing_score = Column(Float, default=70.0)  # Percentage required to pass
    time_limit_minutes = Column(Integer, nullable=True)  # Time limit in minutes
    max_attempts = Column(Integer, nullable=True)  # Maximum attempts allowed (null = unlimited)
    shuffle_questions = Column(Boolean, default=False)
    show_correct_answers = Column(Boolean, default=True)  # Show answers after submission
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    lesson = relationship("Lesson", back_populates="quiz")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.order")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """Individual quiz question"""
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice")  # multiple_choice, true_false, short_answer
    order = Column(Integer, default=0)
    points = Column(Float, default=1.0)
    
    # Options (for multiple choice/true-false)
    options = Column(JSON, nullable=True)  # [{"id": "a", "text": "Option A"}, ...]
    correct_answer = Column(JSON, nullable=False)  # ["a"] for single, ["a", "c"] for multiple, "true/false", or text
    explanation = Column(Text, nullable=True)  # Explanation shown after answering
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    """Track user attempts on quizzes"""
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Attempt data
    attempt_number = Column(Integer, default=1)
    answers = Column(JSON, nullable=False)  # {question_id: answer}
    score = Column(Float, nullable=True)  # Score achieved
    max_score = Column(Float, nullable=True)  # Maximum possible score
    percentage = Column(Float, nullable=True)  # Percentage score
    passed = Column(Boolean, default=False)
    time_taken_seconds = Column(Integer, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User")


class SCO(Base):
    """Shareable Content Object - SCORM content unit"""
    __tablename__ = "scos"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    
    # SCO Identifiers
    identifier = Column(String(255), nullable=False, unique=True)  # From manifest
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Launch Information
    launch_url = Column(String(500), nullable=False)  # Entry point URL
    scorm_type = Column(String(50), nullable=False)  # "sco" or "asset"
    resource_identifier = Column(String(255), nullable=True)
    
    # Sequencing
    order_index = Column(Integer, default=0)
    prerequisites = Column(JSON, nullable=True)  # Prerequisite SCO IDs
    max_time_allowed = Column(Integer, nullable=True)  # Seconds
    time_limit_action = Column(String(50), nullable=True)  # "exit,message", "continue,message", etc.
    
    # Completion and Success
    completion_threshold = Column(Float, nullable=True)
    min_normalized_measure = Column(Float, nullable=True)  # Minimum score (0.0-1.0)
    
    # Data
    launch_data = Column(Text, nullable=True)  # Static launch parameters
    mastery_score = Column(Float, nullable=True)
    
    # Relationships
    course = relationship("Course", back_populates="scos")
    attempts = relationship("LearnerAttempt", back_populates="sco", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LearnerAttempt(Base):
    """Track learner attempts on SCORM SCOs"""
    __tablename__ = "learner_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sco_id = Column(Integer, ForeignKey("scos.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    
    # Attempt Tracking
    attempt_number = Column(Integer, default=1)
    
    # SCORM Data Model (cmi.*)
    completion_status = Column(String(50), default="incomplete")  # incomplete, completed, not attempted, unknown
    success_status = Column(String(50), default="unknown")  # passed, failed, unknown
    score_raw = Column(Float, nullable=True)  # Raw score
    score_min = Column(Float, nullable=True)  # Minimum possible score
    score_max = Column(Float, nullable=True)  # Maximum possible score
    score_scaled = Column(Float, nullable=True)  # Scaled score (0.0-1.0)
    
    # Time Tracking
    session_time = Column(Integer, default=0)  # Seconds for this session
    total_time = Column(Integer, default=0)  # Total seconds across all sessions
    
    # Location and Suspend Data
    location = Column(String(1000), nullable=True)  # Bookmark location
    suspend_data = Column(Text, nullable=True)  # Serialized suspend data (max 64000 chars)
    
    # Entry and Exit
    entry = Column(String(50), nullable=True)  # "ab-initio", "resume", ""
    exit_mode = Column(String(50), nullable=True)  # "time-out", "suspend", "logout", "normal", ""
    
    # Interactions (stored as JSON)
    interactions = Column(JSON, nullable=True)  # Array of interaction data
    
    # Objectives (stored as JSON)
    objectives = Column(JSON, nullable=True)  # Array of objective data
    
    # Comments
    comments_from_learner = Column(JSON, nullable=True)
    comments_from_lms = Column(JSON, nullable=True)
    
    # Progress
    progress_measure = Column(Float, nullable=True)  # 0.0-1.0
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    sco = relationship("SCO", back_populates="attempts")
    enrollment = relationship("Enrollment")

