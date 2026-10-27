"""Filtered TMDb Discover results for the desktop exploration page."""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from izlek.i18n import t
from izlek.security.token_store import TokenStore
from izlek.services.discover import DiscoverService
from izlek.services.image_service import ImageService
from izlek.services.personal_media import PersonalMediaService
from izlek.tmdb.client import NetworkError, TmdbClient, TMDbError
from izlek.tmdb.models import MovieSummary, TvSummary
from izlek.ui.controllers.messages import network_unavailable
