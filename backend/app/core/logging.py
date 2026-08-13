import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any

class StructuredFormatter(logging.Formatter):
    """
    Format logs into a structured JSON format or a highly traceable text format.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Include extra attributes if they exist
        for key in ["request_id", "user_id", "organization_id", "endpoint", "status_code", "error"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
                
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger with the structured formatter.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clean up existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    # Suppress verbose standard loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
