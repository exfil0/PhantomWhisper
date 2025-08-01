# phantom_whisper/logger.py
import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys 

def get_logger(name: str):
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    if logger.handlers: # Prevent adding handlers multiple times if imported elsewhere
        return logger

    logger.setLevel(logging.INFO)

    log_dir = Path("./logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / "phantom_whisper.log"

    # Console Handler for immediate feedback (plain text)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    # File Handler for structured logging (JSON per line) with rotation
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024, # 5 MB per file
        backupCount=5 # Keep 5 backup files
    )

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            # Base record attributes to include (copying from standard LogRecord fields)
            log_entry = {
                "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%f%z"), # ISO-8601 with microseconds and timezone
                "level": record.levelname,
                "logger_name": record.name,
            }

            # Prepare message and any extra fields
            message = self.formatMessage(record) # Format message first to resolve %/{} formatting
            
            # Add other LogRecord fields that are frequently useful
            for attr in ['lineno', 'pathname', 'funcName', 'process', 'processName', 'thread', 'threadName']:
                if hasattr(record, attr):
                    log_entry[attr] = getattr(record, attr)
            
            # Merge all custom 'extra' attributes from the record's __dict__
            # Only include attributes not starting with '_' and not already in the standard set
            forbidden_keys = set(dir(logging.LogRecord)) # Get all standard attributes from LogRecord class
            # Ensure common internal logging keys are not accidentally overwritten by custom 'extra' fields
            forbidden_keys.update({'msg', 'args', 'exc_info', 'exc_text', 'stack_info', 'message'}) 

            # Now, selectively add custom extra fields
            for key, value in record.__dict__.items():
                if not key.startswith('_') and key not in forbidden_keys:
                    log_entry[key] = value

            # Add the formatted message last to avoid accidental overwrites by 'extra' fields
            log_entry["message"] = message

            # Fix timestamp for strict RFC 3339 compliance (add colon to timezone offset)
            ts = log_entry["timestamp"]
            # Detect 4-digit offset (e.g., '+0000') and reformat
            # This handles both positive and negative offsets if they are 4 digits without a colon
            if ((('+' in ts and len(ts.split('+')[-1]) == 4) and ts.endswith(ts.split('+')[-1])) or 
                (('-' in ts and len(ts.split('-')[-1]) == 4) and ts.endswith(ts.split('-')[-1]))):
                
                split_char = '+' if '+' in ts else '-'
                parts = ts.rsplit(split_char, 1)
                offset = parts[1] # This will be 4 digits, e.g., '0000' or '0530'
                ts = f"{parts[0]}{split_char}{offset[:2]}:{offset[2:]}" # Insert colon
            log_entry["timestamp"] = ts
            
            # Defensive guard for formatStack for Python < 3.8
            if hasattr(self, "formatStack") and record.stack_info: # Only try to format if exists and info is there
                log_entry['stack_info'] = self.formatStack(record.stack_info)
            if record.exc_info: # formatException is available on all Python 3 versions
                log_entry['exc_info'] = self.formatException(record.exc_info)
            
            return json.dumps(log_entry)

    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    
    return logger
