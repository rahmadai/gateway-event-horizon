"""
Structured logging utilities for all services.
"""

import logging
import sys
from typing import Any, Dict


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure structured logger with JSON formatting.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


class LogContext:
    """
    Context manager for adding structured context to logs.
    
    Usage:
        with LogContext(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
    """
    
    def __init__(self, **context: Any):
        self.context = context
        self.logger = logging.getLogger()
        
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
            
        logging.setLogRecordFactory(record_factory)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
