"""Suite-wide guards that keep tests deterministic and CI-safe."""

import socket

import pytest


@pytest.fixture(autouse=True)
def isolate_user_storage(tmp_path, monkeypatch):
    """Keep default controllers away from real libraries and keyring secrets."""
    for name, directory in (
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_STATE_HOME", "state"),
    ):
        monkeypatch.setenv(name, str(tmp_path / "xdg" / directory))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    monkeypatch.setattr("izlek.security.token_store._system_keyring", lambda: None)


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """Fail fast if a test tries to open a real TCP network connection."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock, address):
        if isinstance(address, tuple):
            pytest.fail(f"Gerçek ağ bağlantısı engellendi: {address!r}")
        return real_connect(sock, address)

    def guarded_connect_ex(sock, address):
        if isinstance(address, tuple):
            pytest.fail(f"Gerçek ağ bağlantısı engellendi: {address!r}")
        return real_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
