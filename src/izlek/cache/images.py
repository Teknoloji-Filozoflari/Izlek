"""Disk storage for downloaded TMDb images only."""

import hashlib
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from izlek.core.paths import app_paths

IMAGE_CACHE_MAX_AGE = timedelta(days=180)


class ImageDiskCache:
    """Store validated image bytes under hash-based filenames."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or app_paths().cache / "images"

    def path_for(self, kind: str, image_path: str) -> Path:
        """Return a stable, safe path independent of TMDb filename contents."""
        digest = hashlib.sha256(f"{kind}:{image_path}".encode()).hexdigest()
        return self.root / f"{digest}.img"

    def get(self, kind: str, image_path: str) -> Path | None:
        """Return an image cache entry only while it remains within retention."""
        path = self.path_for(kind, image_path)
        if not path.is_file():
            return None
        try:
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        except OSError:
            return None
        if modified_at >= datetime.now(UTC) - IMAGE_CACHE_MAX_AGE:
            return path
        try:
            path.unlink()
        except OSError:
            pass
        return None

    def put(self, kind: str, image_path: str, content: bytes) -> Path:
        """Atomically replace a cache entry after the caller validates content."""
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path_for(kind, image_path)
        descriptor, temporary = tempfile.mkstemp(prefix=".image-", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(content)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target

    def size_bytes(self) -> int:
        """Measure image cache bytes for a future settings display."""
        if not self.root.exists():
            return 0
        return sum(
            path.stat().st_size
            for path in self.root.glob("*.img")
            if path.is_file()
        )

    def clear(self) -> int:
        """Remove disposable image entries and return the number removed."""
        if not self.root.exists():
            return 0
        removed = 0
        for path in self.root.glob("*.img"):
            if not path.is_file():
                continue
            try:
                path.unlink()
            except OSError:
                continue
            removed += 1
        return removed
