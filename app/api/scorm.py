from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
from datetime import datetime
import json

from ..core.database import get_db
from ..core.security import get_current_active_user, get_current_admin_user
from ..models.user import User
from ..models.course import SCO, LearnerAttempt
from ..models.enrollment import Enrollment

router = APIRouter(prefix="/scorm", tags=["SCORM"])


# SCORM RTE (Run-Time Environment) API Implementation
# Compliant with SCORM 2004 4th Edition

@router.post("/initialize/{sco_id}")
async def scorm_initialize(
    sco_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSInitialize - Initialize SCORM communication session
    Returns: {"success": true, "error_code": "0", "attempt_id": 123}
    """
    # Get SCO
    sco = db.query(SCO).filter(SCO.id == sco_id).first()
    if not sco:
        return {"success": False, "error_code": "201", "error_message": "Invalid SCO ID"}
    
    # Check enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == sco.course_id,
        Enrollment.is_active == True
    ).first()
    
    if not enrollment:
        return {"success": False, "error_code": "401", "error_message": "User not enrolled"}
    
    # Get or create learner attempt
    attempt = db.query(LearnerAttempt).filter(
        LearnerAttempt.user_id == current_user.id,
        LearnerAttempt.sco_id == sco_id,
        LearnerAttempt.enrollment_id == enrollment.id,
        LearnerAttempt.completion_status.in_(["incomplete", "not attempted"])
    ).first()
    
    if not attempt:
        # Count previous attempts
        attempt_count = db.query(LearnerAttempt).filter(
            LearnerAttempt.user_id == current_user.id,
            LearnerAttempt.sco_id == sco_id
        ).count()
        
        # Create new attempt
        attempt = LearnerAttempt(
            user_id=current_user.id,
            sco_id=sco_id,
            enrollment_id=enrollment.id,
            attempt_number=attempt_count + 1,
            entry="ab-initio",
            completion_status="not attempted"
        )
        db.add(attempt)
    else:
        # Resume existing attempt
        attempt.entry = "resume"
        attempt.last_accessed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(attempt)
    
    return {
        "success": True,
        "error_code": "0",
        "attempt_id": attempt.id,
        "launch_data": sco.launch_data or "",
        "mastery_score": sco.mastery_score
    }


@router.post("/get-value/{attempt_id}")
async def scorm_get_value(
    attempt_id: int,
    element: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSGetValue - Get value from CMI data model
    SCORM 2004 supports cmi.* elements
    """
    attempt = db.query(LearnerAttempt).filter(
        LearnerAttempt.id == attempt_id,
        LearnerAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        return {"success": False, "error_code": "201", "value": ""}
    
    # Map CMI elements to database fields
    cmi_map = {
        "cmi.completion_status": attempt.completion_status,
        "cmi.success_status": attempt.success_status,
        "cmi.score.raw": str(attempt.score_raw) if attempt.score_raw is not None else "",
        "cmi.score.min": str(attempt.score_min) if attempt.score_min is not None else "",
        "cmi.score.max": str(attempt.score_max) if attempt.score_max is not None else "",
        "cmi.score.scaled": str(attempt.score_scaled) if attempt.score_scaled is not None else "",
        "cmi.location": attempt.location or "",
        "cmi.suspend_data": attempt.suspend_data or "",
        "cmi.entry": attempt.entry or "",
        "cmi.exit": attempt.exit_mode or "",
        "cmi.session_time": f"PT{attempt.session_time}S" if attempt.session_time else "PT0S",
        "cmi.total_time": f"PT{attempt.total_time}S" if attempt.total_time else "PT0S",
        "cmi.progress_measure": str(attempt.progress_measure) if attempt.progress_measure is not None else "",
        "cmi.learner_id": str(current_user.id),
        "cmi.learner_name": current_user.full_name or current_user.email,
        "cmi.mode": "normal",
        "cmi.credit": "credit",
    }
    
    value = cmi_map.get(element, "")
    
    return {
        "success": True,
        "error_code": "0",
        "value": value
    }


@router.post("/set-value/{attempt_id}")
async def scorm_set_value(
    attempt_id: int,
    element: str,
    value: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSSetValue - Set value in CMI data model
    Updates are cached until LMSCommit is called
    """
    attempt = db.query(LearnerAttempt).filter(
        LearnerAttempt.id == attempt_id,
        LearnerAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        return {"success": False, "error_code": "201"}
    
    # Update appropriate field based on element
    try:
        if element == "cmi.completion_status":
            if value in ["completed", "incomplete", "not attempted", "unknown"]:
                attempt.completion_status = value
                if value == "completed" and not attempt.completed_at:
                    attempt.completed_at = datetime.utcnow()
        
        elif element == "cmi.success_status":
            if value in ["passed", "failed", "unknown"]:
                attempt.success_status = value
        
        elif element == "cmi.score.raw":
            attempt.score_raw = float(value) if value else None
        
        elif element == "cmi.score.min":
            attempt.score_min = float(value) if value else None
        
        elif element == "cmi.score.max":
            attempt.score_max = float(value) if value else None
        
        elif element == "cmi.score.scaled":
            attempt.score_scaled = float(value) if value else None
        
        elif element == "cmi.location":
            attempt.location = value
        
        elif element == "cmi.suspend_data":
            if len(value) <= 64000:  # SCORM 2004 limit
                attempt.suspend_data = value
            else:
                return {"success": False, "error_code": "405"}  # Data size exceeded
        
        elif element == "cmi.exit":
            attempt.exit_mode = value
        
        elif element == "cmi.session_time":
            # Parse ISO 8601 duration (PT#H#M#S)
            import re
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', value)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = float(match.group(3) or 0)
                attempt.session_time = int(hours * 3600 + minutes * 60 + seconds)
                attempt.total_time += attempt.session_time
        
        elif element == "cmi.progress_measure":
            attempt.progress_measure = float(value) if value else None
        
        else:
            # Handle other elements like interactions, objectives, comments
            pass
        
        attempt.last_accessed_at = datetime.utcnow()
        
        return {"success": True, "error_code": "0"}
    
    except Exception as e:
        return {"success": False, "error_code": "405", "error_message": str(e)}


@router.post("/commit/{attempt_id}")
async def scorm_commit(
    attempt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSCommit - Persist all cached data to database
    """
    attempt = db.query(LearnerAttempt).filter(
        LearnerAttempt.id == attempt_id,
        LearnerAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        return {"success": False, "error_code": "201"}
    
    try:
        db.commit()
        return {"success": True, "error_code": "0"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error_code": "391", "error_message": str(e)}


@router.post("/finish/{attempt_id}")
async def scorm_finish(
    attempt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSFinish - Terminate SCORM communication session
    Commits all data and closes the session
    """
    attempt = db.query(LearnerAttempt).filter(
        LearnerAttempt.id == attempt_id,
        LearnerAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        return {"success": False, "error_code": "201"}
    
    try:
        # Final commit
        attempt.last_accessed_at = datetime.utcnow()
        
        # If completion status is still "not attempted", set to "incomplete"
        if attempt.completion_status == "not attempted":
            attempt.completion_status = "incomplete"
        
        db.commit()
        return {"success": True, "error_code": "0"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error_code": "391", "error_message": str(e)}


@router.get("/get-last-error/{attempt_id}")
async def scorm_get_last_error(
    attempt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    LMSGetLastError - Get the error code from the last API call
    """
    # In a full implementation, this would track the last error
    # For now, return no error
    return {"success": True, "error_code": "0"}


@router.get("/sco/{sco_id}/attempts")
async def get_sco_attempts(
    sco_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all attempts for a SCO by the current user"""
    attempts = db.query(LearnerAttempt).filter(
        LearnerAttempt.sco_id == sco_id,
        LearnerAttempt.user_id == current_user.id
    ).order_by(LearnerAttempt.attempt_number.desc()).all()
    
    return attempts


@router.get("/course/{course_id}/progress")
async def get_course_scorm_progress(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get SCORM progress for all SCOs in a course"""
    from ..models.course import Course
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    scos = db.query(SCO).filter(SCO.course_id == course_id).all()
    
    progress = []
    for sco in scos:
        latest_attempt = db.query(LearnerAttempt).filter(
            LearnerAttempt.sco_id == sco.id,
            LearnerAttempt.user_id == current_user.id
        ).order_by(LearnerAttempt.attempt_number.desc()).first()
        
        progress.append({
            "sco_id": sco.id,
            "title": sco.title,
            "completion_status": latest_attempt.completion_status if latest_attempt else "not attempted",
            "success_status": latest_attempt.success_status if latest_attempt else "unknown",
            "score_scaled": latest_attempt.score_scaled if latest_attempt else None,
            "total_time": latest_attempt.total_time if latest_attempt else 0,
        })
    
    return {"course_id": course_id, "scos": progress}
