import json
import logging
import os
from datetime import UTC, datetime


class UtcFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds")


class TextFormatter(UtcFormatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        return (
            f"{self.formatTime(record)} {record.levelname:<8s} "
            f"[{record.name}] {record.message}"
        )


class JsonFormatter(UtcFormatter):
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted JSON string.
        NOTE - not currently used - included to demonstrate formatting for logging JSON to cloudwatch. 
        """
        event = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            # Include exception information in the JSON event if available
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("github_explorer")
    if logger.handlers:
        return logger

    log_format = os.getenv("LOG_FORMAT", "").strip().lower() or "text"
    formatter = JsonFormatter() if log_format == "json" else TextFormatter()

    log_level = os.getenv("LOG_LEVEL", "").strip().upper() or "DEBUG"
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    if log_format not in {"text", "json"}:
        logger.warning("Unsupported LOG_FORMAT; using text. Expected 'text' or 'json'.")
    logger.debug("Application debug logging enabled.")
    return logger
