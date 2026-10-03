"""Logging creates only its own directory when configured."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from izlek.core.logging import configure_logging
from izlek.core.paths import app_paths


def test_configure_logging_is_repeatable(tmp_path: Path):
    paths = app_paths(env={}, home=tmp_path)
    logger = configure_logging(paths)
    assert configure_logging(paths) is logger
    assert sum(isinstance(item, RotatingFileHandler) for item in logger.handlers) == 1
    logger.info("phase zero ready")
    assert "phase zero ready" in (paths.logs / "izlek.log").read_text()

    for handler in logger.handlers[:]:
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(logging.NOTSET)
