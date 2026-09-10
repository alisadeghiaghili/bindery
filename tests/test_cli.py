"""CLI entry-point tests for v0.1.0."""

from __future__ import annotations

import sys

import pytest

from bindery import get_version
from bindery.cli import main


def test_no_args_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Default invocation reports the package version."""
    code = main([])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--version`` prints the same string as the default path."""
    code = main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_short_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``-V`` is an alias for ``--version``."""
    code = main(["-V"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` exits zero and mentions future commands."""
    code = main(["--help"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Usage: bindery" in captured.out


def test_short_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``-h`` is an alias for ``--help``."""
    code = main(["-h"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Usage: bindery" in captured.out


def test_unknown_args_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """Unknown flags are a usage error."""
    code = main(["--nope"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown arguments" in captured.err


def test_uses_sys_argv_when_argv_is_none(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``argv=None`` reads the real process argv (minus program name)."""
    monkeypatch.setattr(sys, "argv", ["bindery", "--version"])
    code = main(None)
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"
