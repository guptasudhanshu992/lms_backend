from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..core.security import get_current_user, get_current_admin_user
from ..models import User, Course, Section, Lesson, Quiz, QuizQuestion, QuizAttempt
from ..schemas.course import (
    SectionCreate, SectionUpdate, SectionResponse,
    LessonCreate, LessonUpdate, LessonResponse,
    QuizCreate, QuizUpdate, QuizResponse,
    QuizQuestionCreate, QuizQuestionUpdate, QuizQuestionResponse,
    QuizAttemptCreate, QuizAttemptResponse
)
from datetime import datetime

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


# ==================== SECTION ENDPOINTS ====================

@router.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
def create_section(
    section_data: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new section in a course"""
    # Verify course exists and user has permission
    course = db.query(Course).filter(Course.id == section_data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    section = Section(**section_data.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.get("/sections/{section_id}", response_model=SectionResponse)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific section"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@router.put("/sections/{section_id}", response_model=SectionResponse)
def update_section(
    section_id: int,
    section_data: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a section"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    for key, value in section_data.model_dump(exclude_unset=True).items():
        setattr(section, key, value)
    
    db.commit()
    db.refresh(section)
    return section


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a section and all its lessons"""
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    db.delete(section)
    db.commit()
    return None


@router.get("/courses/{course_id}/sections", response_model=List[SectionResponse])
def get_course_sections(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sections for a course"""
    sections = db.query(Section).filter(Section.course_id == course_id).order_by(Section.order).all()
    return sections


# ==================== LESSON ENDPOINTS ====================

@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
def create_lesson(
    lesson_data: LessonCreate,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new lesson in a course"""
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Verify section exists if provided
    if lesson_data.section_id:
        section = db.query(Section).filter(Section.id == lesson_data.section_id).first()
        if not section or section.course_id != course_id:
            raise HTTPException(status_code=404, detail="Section not found or doesn't belong to this course")
    
    lesson_dict = lesson_data.model_dump()
    lesson = Lesson(**lesson_dict, course_id=course_id)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    for key, value in lesson_data.model_dump(exclude_unset=True).items():
        setattr(lesson, key, value)
    
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    db.delete(lesson)
    db.commit()
    return None


@router.get("/courses/{course_id}/lessons", response_model=List[LessonResponse])
def get_course_lessons(
    course_id: int,
    section_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all lessons for a course or section"""
    query = db.query(Lesson).filter(Lesson.course_id == course_id)
    if section_id:
        query = query.filter(Lesson.section_id == section_id)
    lessons = query.order_by(Lesson.order).all()
    return lessons


# ==================== QUIZ ENDPOINTS ====================

@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
def create_quiz(
    quiz_data: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new quiz for a lesson"""
    # Verify lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == quiz_data.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Check if lesson already has a quiz
    existing_quiz = db.query(Quiz).filter(Quiz.lesson_id == quiz_data.lesson_id).first()
    if existing_quiz:
        raise HTTPException(status_code=400, detail="Lesson already has a quiz")
    
    # Create quiz
    quiz_dict = quiz_data.model_dump(exclude={'questions'})
    quiz = Quiz(**quiz_dict)
    db.add(quiz)
    db.flush()  # Get quiz.id
    
    # Create questions
    if quiz_data.questions:
        for question_data in quiz_data.questions:
            question = QuizQuestion(**question_data.model_dump(), quiz_id=quiz.id)
            db.add(question)
    
    # Update lesson type to quiz
    lesson.lesson_type = "quiz"
    
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.put("/quizzes/{quiz_id}", response_model=QuizResponse)
def update_quiz(
    quiz_id: int,
    quiz_data: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    for key, value in quiz_data.model_dump(exclude_unset=True).items():
        setattr(quiz, key, value)
    
    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a quiz and all its questions"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Update lesson type
    lesson = db.query(Lesson).filter(Lesson.id == quiz.lesson_id).first()
    if lesson:
        lesson.lesson_type = "video"
    
    db.delete(quiz)
    db.commit()
    return None


# ==================== QUIZ QUESTION ENDPOINTS ====================

@router.post("/quizzes/{quiz_id}/questions", response_model=QuizQuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    quiz_id: int,
    question_data: QuizQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Add a question to a quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    question = QuizQuestion(**question_data.model_dump(), quiz_id=quiz_id)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.put("/questions/{question_id}", response_model=QuizQuestionResponse)
def update_question(
    question_id: int,
    question_data: QuizQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a quiz question"""
    question = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    for key, value in question_data.model_dump(exclude_unset=True).items():
        setattr(question, key, value)
    
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a quiz question"""
    question = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    db.delete(question)
    db.commit()
    return None


# ==================== QUIZ ATTEMPT ENDPOINTS ====================

@router.post("/quizzes/{quiz_id}/attempts", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED)
def submit_quiz_attempt(
    quiz_id: int,
    attempt_data: QuizAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a quiz attempt and get graded results"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check attempt limit
    if quiz.max_attempts:
        previous_attempts = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id
        ).count()
        if previous_attempts >= quiz.max_attempts:
            raise HTTPException(status_code=400, detail="Maximum attempts reached")
    
    # Calculate score
    total_points = 0
    earned_points = 0
    
    for question in quiz.questions:
        total_points += question.points
        user_answer = attempt_data.answers.get(question.id)
        
        # Check if answer is correct
        if user_answer is not None:
            if isinstance(question.correct_answer, list):
                # Multiple choice (multiple answers)
                if set(user_answer) == set(question.correct_answer):
                    earned_points += question.points
            else:
                # Single answer
                if str(user_answer).lower() == str(question.correct_answer).lower():
                    earned_points += question.points
    
    percentage = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = percentage >= quiz.passing_score
    
    # Get attempt number
    attempt_number = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == current_user.id
    ).count() + 1
    
    # Create attempt record
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        attempt_number=attempt_number,
        answers=attempt_data.answers,
        score=earned_points,
        max_score=total_points,
        percentage=percentage,
        passed=passed,
        submitted_at=datetime.utcnow()
    )
    
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/quizzes/{quiz_id}/attempts", response_model=List[QuizAttemptResponse])
def get_quiz_attempts(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all attempts for a quiz by the current user"""
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == current_user.id
    ).order_by(QuizAttempt.started_at.desc()).all()
    return attempts


@router.get("/attempts/{attempt_id}", response_model=QuizAttemptResponse)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific quiz attempt"""
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    # Only allow user to see their own attempts (unless admin)
    if attempt.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return attempt
