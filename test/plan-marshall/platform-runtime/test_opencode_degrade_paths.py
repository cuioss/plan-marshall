#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Degrade-path pins for the OpenCode runtime and the sentinel convention.

The identity-bearing operations decline on exactly THREE genuine grounds —
``OPENCODE_SESSION_ID`` unset, the session database absent, and the database
schema unsupported — and each carries its NAMED reason plus the alternative. The
metrics primitive keeps its own decline ground, the absent token-persistence
boundary, and no manual count is ever reported as success.

The ``hook_not_configured`` absence guard and the sentinel-meaning guard are
unchanged by the move to a measured identity: ``hook_not_configured`` still names
Claude wiring OpenCode does not have, and absent identity still reads as the
sentinel through the shared guard.
"""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from opencode_runtime import OpenCodeRuntime
from runtime_base import NO_SESSION_IDENTITY, has_session_identity
from toon_parser import parse_toon


@pytest.fixture()
def runtime() -> OpenCodeRuntime:
    """Return a fresh OpenCodeRuntime instance."""
    return OpenCodeRuntime()


def _parse(toon_str: str) -> dict[str, Any]:
    """Parse a TOON string and assert it is non-empty."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict)
    return result


def _point_at_db(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    """Point the runtime's session store at *db_path*, ahead of ambient overrides."""
    monkeypatch.delenv('OPENCODE_DB', raising=False)
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))


def test_session_capture_unset_environment_declines(runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ground 1 — the identity variable is unset."""
    monkeypatch.delenv('OPENCODE_SESSION_ID', raising=False)

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert 'OPENCODE_SESSION_ID' in result['reason']
    assert result['alternative']


def test_session_capture_absent_database_declines(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ground 2 — the variable is set but the session database is absent."""
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    _point_at_db(monkeypatch, tmp_path / 'absent.db')

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'db_not_found'
    assert result['alternative']


def test_session_capture_unsupported_schema_declines(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ground 3 — the database carries no schema this reader understands."""
    db_path = tmp_path / 'opencode.db'
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute('CREATE TABLE unrelated (id TEXT)')
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    _point_at_db(monkeypatch, db_path)

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'schema_unsupported'


def test_metrics_normalized_tokens_absent_database_declines(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The same absent-store ground declines the metrics primitive by name."""
    _point_at_db(monkeypatch, tmp_path / 'absent.db')
    windows = [('5-execute', '2026-10-20T10:00:00+00:00', '2026-10-20T10:30:00+00:00')]

    result = _parse(runtime.metrics_normalized_tokens('ses-root', windows, str(tmp_path / 'out.json')))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'db_not_found'
    assert result['alternative']


def test_metrics_capture_manual_count_never_succeeds(runtime: OpenCodeRuntime) -> None:
    """No manual token count is reported as success — the persistence boundary is absent."""
    for total in (None, 0, 1, 42000):
        result = _parse(runtime.metrics_capture('my-plan', '5-execute', total))
        assert result['status'] == 'no-op'
        assert result['reason']
        assert result['alternative']
        assert result.get('tokens_captured') is None


def test_chat_extract_signal_declines_with_transcript_not_found(runtime: OpenCodeRuntime) -> None:
    """chat extract-signal still declines: there is no transcript to reduce."""
    result = _parse(runtime.chat_extract_signal('sid'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'transcript_not_found'
    assert result['alternative']


def test_opencode_never_returns_hook_not_configured(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The hook_not_configured error names Claude wiring; opencode answers no-op."""
    monkeypatch.delenv('OPENCODE_DB', raising=False)
    monkeypatch.setenv('OPENCODE_DB_PATH', str(tmp_path / 'absent.db'))
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    for payload in (
        runtime.session_capture('my-plan'),
        runtime.metrics_capture('my-plan', '5-execute', None),
        runtime.metrics_capture('my-plan', '5-execute', 10),
        runtime.wait_for('build-job', 'job-1', 60),
    ):
        result = _parse(payload)
        assert result.get('error') != 'hook_not_configured'


def test_sentinel_meaning_guard() -> None:
    """Absent identity reads as the sentinel through the named guard."""
    assert NO_SESSION_IDENTITY == 'NO_SESSION_IDENTITY'
    assert has_session_identity('abc123') is True
    assert has_session_identity(None) is False
    assert has_session_identity('') is False
    assert has_session_identity('   ') is False
    assert has_session_identity(NO_SESSION_IDENTITY) is False
    # Whitespace is stripped for the sentinel comparison too, not only for the
    # emptiness test: a padded sentinel is still the sentinel.
    assert has_session_identity(f' {NO_SESSION_IDENTITY} ') is False
