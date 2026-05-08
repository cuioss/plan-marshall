#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the staleness guard inside the project-local sync.py.

Three scenarios:

(a) target/claude/ absent → script refuses with actionable error pointing
    at the generator command.
(b) target/claude/ exists but stale (oldest target file older than newest
    source file) → script refuses.
(c) Fresh mirror → script proceeds.

Each scenario sets up a fixture (cwd has a marketplace/bundles/ tree
plus a parallel target/claude/ tree with controlled mtimes) and
asserts the guard's exit code + summary message.

The script under test lives at
``.claude/skills/sync-plugin-cache/scripts/sync.py`` (project-local).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

_SYNC_PY = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts' / 'sync.py'


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SYNC_PY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


def _make_marketplace(cwd: Path, bundles: dict[str, str]) -> None:
    for name, version in bundles.items():
        plugin_doc = json.dumps({'name': name, 'version': version}, indent=2) + '\n'
        _write(cwd / 'marketplace' / 'bundles' / name / '.claude-plugin' / 'plugin.json', plugin_doc)
        _write(cwd / 'marketplace' / 'bundles' / name / 'README.md', f'# {name}\n')


def _make_target(cwd: Path, bundles: dict[str, str]) -> None:
    for name, version in bundles.items():
        plugin_doc = json.dumps({'name': name, 'version': version}, indent=2) + '\n'
        _write(cwd / 'target' / 'claude' / name / '.claude-plugin' / 'plugin.json', plugin_doc)
        _write(cwd / 'target' / 'claude' / name / 'README.md', f'# {name}\n')


# ---------------------------------------------------------------------------
# (a) target/claude/ absent
# ---------------------------------------------------------------------------


def test_staleness_guard_refuses_when_target_missing(tmp_path: Path):
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})

    result = _run(cwd=cwd)

    assert result.returncode == 2, f'expected exit 2 for missing target, got {result.returncode}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert int(data['synced_count']) == 0
    msg = data['summary_message']
    assert 'source root not found' in msg
    # Actionable hint to the generator command must be present
    assert 'marketplace/targets/generate.py' in msg


def test_staleness_guard_refuses_when_target_empty(tmp_path: Path):
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    (cwd / 'target' / 'claude').mkdir(parents=True)

    result = _run(cwd=cwd)

    assert result.returncode == 2
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'no bundles' in data['summary_message']


# ---------------------------------------------------------------------------
# (b) target/claude/ exists but stale
# ---------------------------------------------------------------------------


def test_staleness_guard_refuses_when_target_older_than_source(tmp_path: Path):
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_target(cwd, {'demo': '0.1.0'})
    _make_marketplace(cwd, {'demo': '0.1.0'})

    # Target = old; source = recent
    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    result = _run(cwd=cwd)
    assert result.returncode == 2, f'expected refusal, got {result.returncode}: {result.stdout}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'stale' in data['summary_message']


def test_staleness_guard_refuses_when_target_missing_a_bundle(tmp_path: Path):
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo-a': '0.1.0', 'demo-b': '0.2.0'})
    _make_target(cwd, {'demo-a': '0.1.0'})  # Missing demo-b

    result = _run(cwd=cwd)
    assert result.returncode == 2
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'demo-b' in data['summary_message']


# ---------------------------------------------------------------------------
# (c) Fresh mirror — script proceeds
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_staleness_guard_passes_when_target_newer(tmp_path: Path):
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})

    # Target = recent; source = older
    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    cache = tmp_path / 'cache'
    result = _run('--cache-root', str(cache), cwd=cwd)
    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert (cache / 'demo' / '0.1.0' / 'README.md').is_file()


def test_staleness_guard_can_be_skipped_for_recovery(tmp_path: Path):
    """Operator escape hatch: --skip-staleness-guard bypasses all the checks."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    # No marketplace/, no target/ — would normally refuse
    cache = tmp_path / 'cache'

    result = _run(
        '--skip-staleness-guard',
        '--cache-root', str(cache),
        cwd=cwd,
    )
    # No bundles to sync → status: error, exit 1 (different code path from the
    # guard's exit 2). Confirms the guard was skipped.
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'no matching bundles' in data['summary_message']
