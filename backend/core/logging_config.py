import logging
import time
from logging.handlers import RotatingFileHandler

from backend.core.config import Settings


LOG_FORMAT = (
    "%(asctime)sZ %(levelname)s %(name)s "
    "request_id=%(request_id)s %(message)s"
)


class UtcFormatter(logging.Formatter):
    converter = time.gmtime


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging(settings: Settings) -> None:
    """Configure application logging once for the current process."""
    log_file = settings.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = UtcFormatter(LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S")
    request_id_filter = RequestIdFilter()

    handlers: list[logging.Handler] = []
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(request_id_filter)
    handlers.append(file_handler)

    if settings.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(request_id_filter)
        handlers.append(console_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").disabled = True

