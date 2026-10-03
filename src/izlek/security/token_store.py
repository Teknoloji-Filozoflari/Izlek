"""TMDb token storage with a system keyring and restricted file fallback."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from izlek.core.paths import app_paths

SERVICE = "izlek.tmdb"
ACCOUNT = "read_access_token"


class KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...


@dataclass(frozen=True)
class StoredToken:
    value: str
    location: str  # "keyring" or "file"


def _system_keyring() -> KeyringBackend | None:
    try:
        import keyring

        if keyring.get_keyring().priority < 1:
            return None
        return keyring
    except Exception:
        return None


class TokenStore:
    """Keep tokens out of the repository, SQLite database, and QSettings."""

    def __init__(
        self,
        fallback_path: Path | None = None,
        keyring_backend: KeyringBackend | None = None,
    ) -> None:
        self.path = fallback_path or app_paths().config / "tmdb-token"
        self.keyring = (
            keyring_backend if keyring_backend is not None else _system_keyring()
        )

    def load(self) -> StoredToken | None:
        if self.path.is_file():
            if self.path.stat().st_mode & 0o077:
                raise PermissionError("TMDb token dosyası izinleri güvenli değil")
            token = self.path.read_text(encoding="utf-8").strip()
            if not token:
                return None
            if self.keyring is None:
                return StoredToken(token, "file")
            try:
                self.keyring.set_password(SERVICE, ACCOUNT, token)
            except Exception:
                return StoredToken(token, "file")
            self.path.unlink()
            return StoredToken(token, "keyring")

        if self.keyring is not None:
            try:
                token = self.keyring.get_password(SERVICE, ACCOUNT)
            except Exception:
                token = None
            if token:
                return StoredToken(token, "keyring")
        return None

    def save(self, token: str) -> str:
        """Store a validated token; return the backend actually used."""
        if not token or any(character.isspace() for character in token):
            raise ValueError("Boş veya boşluk içeren token kaydedilemez")
        if self.keyring is not None:
            try:
                self.keyring.set_password(SERVICE, ACCOUNT, token)
            except Exception:
                pass
            else:
                self.path.unlink(missing_ok=True)
                return "keyring"

        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".tmdb-token-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(token)
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return "file"
