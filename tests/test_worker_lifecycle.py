"""Worker shutdown and concurrent first-use database ownership regressions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread

import pytest
from PySide6.QtGui import QGuiApplication

from izlek.services.movie_detail import MovieDetailService
from izlek.services.tv_detail import TvDetailService
from izlek.tmdb.client import TmdbClient
from izlek.ui.controllers.transfer_controller import TransferController


@pytest.mark.parametrize("service_type", [MovieDetailService, TvDetailService])
def test_parallel_first_use_owns_only_one_database(service_type, monkeypatch):
    entered = Event()
    release = Event()
    calls = []
    second_initialization = Event()
    module = service_type.__module__

    def initialize():
        calls.append(object())
        if len(calls) > 1:
            second_initialization.set()
        entered.set()
        assert release.wait(timeout=2)
        return calls[-1]

    monkeypatch.setattr(f"{module}.initialize_database", initialize)
    monkeypatch.setattr(f"{module}.create_session_factory", lambda engine: engine)
    service = service_type(TmdbClient())
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(service._sessions)
        assert entered.wait(timeout=2)
        second = executor.submit(service._sessions)
        assert not second_initialization.wait(timeout=0.05)
        release.set()
        assert first.result(timeout=2) is second.result(timeout=2)
    assert len(calls) == 1


def test_shutdown_waits_for_import_before_releasing_database():
    QGuiApplication.instance() or QGuiApplication([])
    entered = Event()
    release = Event()
    closed = Event()
    close_started = Event()

    class Service:
        def close(self):
            closed.set()

    controller = TransferController(service=Service())

    def import_work():
        entered.set()
        assert release.wait(timeout=2)
        assert not closed.is_set()

    work = controller._executor.submit(import_work)
    assert entered.wait(timeout=2)

    def close_controller():
        close_started.set()
        controller.close()

    closer = Thread(target=close_controller)
    closer.start()
    try:
        assert close_started.wait(timeout=2)
        assert not closed.wait(timeout=0.05)
        release.set()
        work.result(timeout=2)
        closer.join(timeout=2)
        assert not closer.is_alive()
        assert closed.is_set()
    finally:
        release.set()
        closer.join(timeout=2)


def test_busy_import_cannot_replace_preview_selection(tmp_path, monkeypatch):
    QGuiApplication.instance() or QGuiApplication([])

    class Service:
        def close(self):
            pass

    controller = TransferController(service=Service())
    original = tmp_path / "original.json"
    controller._import_path = original
    controller._preview = {"media": 3}
    controller._busy = True
    monkeypatch.setattr(controller, "_submit", lambda *args: None)
    try:
        controller.previewImport(str(tmp_path / "other.json"))
        assert controller._import_path == original
        assert controller.preview == {"media": 3}
    finally:
        controller.close()
