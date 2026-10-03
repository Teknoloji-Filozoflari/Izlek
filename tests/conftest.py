"""Suite-wide guards that keep tests deterministic and CI-safe."""

import socket

import pytest


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
