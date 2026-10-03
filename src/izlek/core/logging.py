"""Local application logging without import-time filesystem changes."""

import logging
from logging.handlers import RotatingFileHandler

from izlek.core.paths import AppPaths, app_paths


def configure_logging(paths: AppPaths | None = None) -> logging.Logger:
    """Write bounded application logs in the XDG state directory."""
    resolved = app_paths() if paths is None else paths
    resolved.logs.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_file = resolved.logs / "izlek.log"
    logger = logging.getLogger("izlek")
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        if isinstance(handler, RotatingFileHandler):
            if handler.baseFilename == str(log_file):
                return logger
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    return logger
