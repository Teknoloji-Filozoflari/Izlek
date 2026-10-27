"""Nonblocking TV detail and episode progress bridge for QML."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from sqlalchemy.exc import SQLAlchemyError

from izlek.i18n import t
from izlek.metadata.settings import MetadataSettings
