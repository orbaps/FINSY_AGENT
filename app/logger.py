"""
Logging configuration and utilities.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from app.config import Config


def setup_logging():
    """Configure application logging"""
    # Create logger
    logger = logging.getLogger("finsy")
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    try:
        file_handler = RotatingFileHandler(
            "app/logs/finsy.log",
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # If we can't create log file, just use console
        pass
    
    return logger


def get_logger(name: str = "finsy") -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)


# Initialize logging on import
logger = setup_logging()


