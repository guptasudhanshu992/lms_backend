import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json
from typing import Optional
from sqlalchemy.orm import Session
from ..core.database import SessionLocal

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Custom JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
            
        return json.dumps(log_data)


# Configure loggers
def setup_logger(name: str, level=logging.INFO):
    """Setup a logger with both file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Console handler with standard formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with JSON formatting for parsing
    file_handler = RotatingFileHandler(
        LOGS_DIR / f"{name}.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    
    # Error file handler
    error_handler = RotatingFileHandler(
        LOGS_DIR / f"{name}_error.log",
        maxBytes=10485760,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    return logger


# Application loggers
app_logger = setup_logger("app")
api_logger = setup_logger("api")
db_logger = setup_logger("database")
auth_logger = setup_logger("auth")
error_logger = setup_logger("error")


# Helper functions for common logging patterns
def log_api_request(endpoint: str, method: str, user_id: Optional[int] = None, ip_address: Optional[str] = None):
    """Log API request"""
    extra = {
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id,
        "ip_address": ip_address
    }
    api_logger.info(f"{method} {endpoint}", extra=extra)


def log_api_response(endpoint: str, method: str, status_code: int, duration: float, user_id: Optional[int] = None):
    """Log API response"""
    extra = {
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration": duration,
        "user_id": user_id
    }
    api_logger.info(f"{method} {endpoint} - {status_code} ({duration:.3f}s)", extra=extra)


def log_error(error: Exception, context: str = "", user_id: Optional[int] = None):
    """Log error with context"""
    extra = {"user_id": user_id} if user_id else {}
    error_logger.error(f"{context}: {str(error)}", exc_info=True, extra=extra)


def log_db_query(query: str, duration: float):
    """Log database query"""
    db_logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}...")


def log_auth_event(event: str, user_id: Optional[int] = None, email: Optional[str] = None, success: bool = True):
    """Log authentication event"""
    extra = {"user_id": user_id}
    level = logging.INFO if success else logging.WARNING
    message = f"Auth event: {event} - User: {email or user_id} - Success: {success}"
    auth_logger.log(level, message, extra=extra)


# Store logs in database for admin viewing
def store_log_in_db(level: str, message: str, logger_name: str, module: str = None, 
                    function: str = None, user_id: int = None, extra_data: dict = None):
    """Store important logs in database for admin viewing"""
    from ..models.log import Log
    
    try:
        db = SessionLocal()
        log_entry = Log(
            level=level,
            message=message,
            logger=logger_name,
            module=module,
            function=function,
            user_id=user_id,
            extra_data=extra_data
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        # Don't let logging errors crash the application
        print(f"Failed to store log in database: {e}")


# Custom handler to store logs in database
class DatabaseHandler(logging.Handler):
    """Handler that stores logs in database"""
    
    def emit(self, record):
        # Only store WARNING and above in database
        if record.levelno >= logging.WARNING:
            extra_data = {
                "line": record.lineno,
                "exception": self.format(record.exc_info) if record.exc_info else None
            }
            
            if hasattr(record, "user_id"):
                extra_data["user_id"] = record.user_id
            if hasattr(record, "endpoint"):
                extra_data["endpoint"] = record.endpoint
            if hasattr(record, "method"):
                extra_data["method"] = record.method
                
            store_log_in_db(
                level=record.levelname,
                message=record.getMessage(),
                logger_name=record.name,
                module=record.module,
                function=record.funcName,
                user_id=getattr(record, "user_id", None),
                extra_data=extra_data
            )


# Add database handler to error logger
db_handler = DatabaseHandler()
db_handler.setLevel(logging.WARNING)
error_logger.addHandler(db_handler)
api_logger.addHandler(db_handler)
auth_logger.addHandler(db_handler)
