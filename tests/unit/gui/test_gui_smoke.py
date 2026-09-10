"""GUI smoke tests (tkinter). Window is withdrawn; no dialogs."""

from __future__ import annotations

import contextlib
from unittest.mock import patch

import pytest

from bindery.gui import BinderyApp
from bindery.orchestration.progress import ProgressEvent


@pytest.fixture
def app() -> BinderyApp:
    """Create a hidden BinderyApp for tests."""
    instance = BinderyApp()
    instance.root.withdraw()
    yield instance
    with contextlib.suppress(Exception):
        if hasattr(instance, "_after_id"):
            instance.root.after_cancel(instance._after_id)
        instance.root.destroy()


def test_app_title_includes_version(app: BinderyApp) -> None:
    """Window title starts with bindery."""
    assert app.root.title().startswith("bindery")


def test_append_log_updates_text(app: BinderyApp) -> None:
    """Logging writes into the text widget."""
    app._append_log("hello")
    content = app._log.get("1.0", "end")
    assert "hello" in content


def test_handle_progress_sets_fraction(app: BinderyApp) -> None:
    """Progress events drive the progress bar."""
    app._handle_progress(ProgressEvent(stage="transform", completed=1, total=2, current="a.png"))
    assert float(app._progress["value"]) == pytest.approx(50.0)


def test_start_requires_paths(app: BinderyApp) -> None:
    """Empty form does not start a worker (dialog mocked)."""
    with patch("bindery.gui.messagebox.showerror") as showerror:
        app._start()
    assert showerror.called
    assert app._worker is None or not app._worker.is_alive()


def test_cli_gui_is_listed() -> None:
    """Help text documents the gui verb."""
    from bindery.cli import _USAGE

    assert "bindery gui" in _USAGE
