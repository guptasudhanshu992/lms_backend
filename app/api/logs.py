from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.log import Log
from ..schemas.log import LogResponse, LogFilter
from ..core.logger import api_logger, log_error
import os
from pathlib import Path

router = APIRouter()


def is_admin(current_user: User = Depends(get_current_user)):
    """Check if user is admin"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/admin/logs", response_model=List[LogResponse])
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger: Optional[str] = Query(None, description="Filter by logger name"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """
    Get logs from database with filtering options (Admin only)
    """
    try:
        query = db.query(Log)
        
        # Apply filters
        if level:
            query = query.filter(Log.level == level.upper())
        if logger:
            query = query.filter(Log.logger == logger)
        if user_id:
            query = query.filter(Log.user_id == user_id)
        if start_date:
            query = query.filter(Log.created_at >= start_date)
        if end_date:
            query = query.filter(Log.created_at <= end_date)
        
        # Order by most recent first
        query = query.order_by(Log.created_at.desc())
        
        # Pagination
        logs = query.offset(offset).limit(limit).all()
        
        api_logger.info(f"Admin {current_user.email} retrieved {len(logs)} logs")
        return logs
        
    except Exception as e:
        log_error(e, "Error retrieving logs", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/admin/logs/count")
async def get_logs_count(
    level: Optional[str] = Query(None),
    logger: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Get count of logs by level"""
    try:
        query = db.query(Log)
        
        if level:
            query = query.filter(Log.level == level.upper())
        if logger:
            query = query.filter(Log.logger == logger)
        if start_date:
            query = query.filter(Log.created_at >= start_date)
        if end_date:
            query = query.filter(Log.created_at <= end_date)
        
        total = query.count()
        
        # Count by level
        levels = {}
        for log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            count = db.query(Log).filter(Log.level == log_level)
            if start_date:
                count = count.filter(Log.created_at >= start_date)
            if end_date:
                count = count.filter(Log.created_at <= end_date)
            levels[log_level.lower()] = count.count()
        
        return {
            "total": total,
            "by_level": levels
        }
        
    except Exception as e:
        log_error(e, "Error getting log counts", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get log counts")


@router.get("/admin/logs/recent-errors")
async def get_recent_errors(
    hours: int = Query(24, le=168, description="Hours to look back"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Get recent error and warning logs"""
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        logs = db.query(Log).filter(
            Log.level.in_(['ERROR', 'CRITICAL', 'WARNING']),
            Log.created_at >= since
        ).order_by(Log.created_at.desc()).limit(limit).all()
        
        return logs
        
    except Exception as e:
        log_error(e, "Error retrieving recent errors", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve recent errors")


@router.delete("/admin/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=7, le=365, description="Delete logs older than this many days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Delete logs older than specified days"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = db.query(Log).filter(
            Log.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        
        api_logger.info(f"Admin {current_user.email} deleted {deleted_count} logs older than {days} days")
        
        return {
            "message": f"Deleted {deleted_count} logs older than {days} days",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        log_error(e, "Error cleaning up logs", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to cleanup logs")


@router.get("/admin/logs/file/{log_type}")
async def download_log_file(
    log_type: str = PathParam(..., pattern="^(app|api|database|auth|error)$"),
    current_user: User = Depends(is_admin)
):
    """Download raw log file"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    try:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_file = log_dir / f"{log_type}.log"
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        api_logger.info(f"Admin {current_user.email} downloaded {log_type} log file")
        
        return FileResponse(
            path=log_file,
            filename=f"{log_type}_{datetime.utcnow().strftime('%Y%m%d')}.log",
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, f"Error downloading log file {log_type}", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to download log file")
