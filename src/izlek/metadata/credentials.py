"""Keyring-backed credentials for optional metadata sources (not TMDb)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from izlek.core.paths import app_paths
from izlek.metadata.catalog import SourceId
from izlek.security.token_store import KeyringBackend, StoredToken, _system_keyring


class SourceCredentialStore:
    """Store one API credential per metadata source outside QSettings/SQLite."""

    def __init__(
        self,
        source_id: SourceId | str,
        fallback_path: Path | None = None,
        keyring_backend: KeyringBackend | None = None,
    ) -> None:
        self.source_id = SourceId(source_id)
        if self.source_id is SourceId.TMDB:
            raise ValueError("TMDb için mevcut TokenStore kullanılmalıdır.")
        self.path = fallback_path or (
            app_paths().config / f"{self.source_id.value}-credential"
        )
        self.keyring = (
            keyring_backend if keyring_backend is not None else _system_keyring()
        )

    @property
    def service(self) -> str:
        return f"izlek.{self.source_id.value}"

    @property
    def account(self) -> str:
        return "api_credential"

    def load(self) -> StoredToken | None:
        if self.path.is_file():
            if sys.platform != "win32" and self.path.stat().st_mode & 0o077:
                raise PermissionError(
                    f"{self.source_id.value} kimlik dosyası izinleri güvenli değil"
                )
            token = self.path.read_text(encoding="utf-8").strip()
            if not token:
                return None
            if self.keyring is None:
                return StoredToken(token, "file")
            try:
                self.keyring.set_password(self.service, self.account, token)
            except Exception:
                return StoredToken(token, "file")
            self.path.unlink()
            return StoredToken(token, "keyring")

        if self.keyring is not None:
            try:
                token = self.keyring.get_password(self.service, self.account)
            except Exception:
                token = None
            if token:
                return StoredToken(token, "keyring")
        return None

    def save(self, token: str) -> str:
        if not token or any(character.isspace() for character in token):
            raise ValueError("Boş veya boşluk içeren kimlik bilgisi kaydedilemez")
        if self.keyring is not None:
            try:
                self.keyring.set_password(self.service, self.account, token)
            except Exception:
                pass
            else:
                self.path.unlink(missing_ok=True)
                return "keyring"

        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.source_id.value}-credential-", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(token)
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return "file"

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
        if self.keyring is None:
            return
        try:
            # Empty password is the portable clear; backends vary on delete_password.
            self.keyring.set_password(self.service, self.account, "")
        except Exception:
            pass
