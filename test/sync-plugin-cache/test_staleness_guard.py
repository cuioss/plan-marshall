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


# ---------------------------------------------------------------------------
# (d) Transient-artifact / .gitignore filter scenarios (deliverable D4)
# ---------------------------------------------------------------------------
#
# These four scenarios exercise the rewritten staleness walk that ignores
# git-ignored files and applies the hard-coded transient-artifact denylist
# (``__pycache__``, ``.pyc``, ``.pytest_cache``, ``.mypy_cache``,
# ``.ruff_cache``, ``.coverage``). The guard MUST continue to flag legitimate
# source-file changes — any tracked ``.py`` / ``.md`` / ``.json`` newer than
# ``target/claude/`` still trips it.
#
# Each scenario builds a synthetic git repo with a ``.gitignore`` so the
# git-based ignore probe (``git ls-files --others --ignored
# --exclude-standard``) can run authentically.


def _git_init(cwd: Path) -> None:
    """Initialise a git repo at ``cwd`` with a default identity.

    Tests run in a sandboxed ``tmp_path``; we never push or fetch from these
    repos, but ``git ls-files`` still requires a valid work tree.
    """
    subprocess.run(['git', 'init', '-q'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.invalid'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=cwd, check=True)


def _git_commit_all(cwd: Path, message: str) -> None:
    subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', message], cwd=cwd, check=True)


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_staleness_guard_ignores_transient_pycache_artifact(tmp_path: Path):
    """A ``__pycache__/x.pyc`` newer than target/claude/ MUST NOT trip the guard.

    Reproduces the post-pytest scenario that drove the D4 rewrite: source
    bundles are unchanged but pytest left ``.pyc`` files with fresh
    mtimes; the guard previously refused even though no source drift
    occurred.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    # .gitignore covers __pycache__ exactly the way the real repo does
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)
    _git_commit_all(cwd, 'initial')

    # All tracked files: target newer than source (clean state)
    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    # Now drop a transient .pyc with a mtime newer than target/
    pycache_dir = cwd / 'marketplace' / 'bundles' / 'demo' / '__pycache__'
    pyc_file = pycache_dir / 'demo.cpython-311.pyc'
    _write(pyc_file, 'fake bytecode')
    _set_mtime(pyc_file, new + 60)  # 60s newer than the target

    cache = tmp_path / 'cache'
    result = _run('--cache-root', str(cache), cwd=cwd)
    # Guard MUST NOT trip — the .pyc is filtered by git-ignored probe AND
    # the transient denylist
    assert result.returncode == 0, (
        f'guard tripped on transient artifact (returncode {result.returncode}): {result.stdout}'
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_staleness_guard_trips_on_tracked_source_change(tmp_path: Path):
    """A tracked source file (``README.md``) newer than target MUST trip the guard.

    Belt-and-suspenders check: filtering must NOT mask legitimate source
    drift. Edits to tracked ``.md`` / ``.py`` / ``.json`` files still need
    to trigger a regenerate.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)
    _git_commit_all(cwd, 'initial')

    # Target older than source — guard should trip
    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    # Touch only a tracked source file with a fresh mtime
    tracked_readme = cwd / 'marketplace' / 'bundles' / 'demo' / 'README.md'
    _set_mtime(tracked_readme, new)

    result = _run(cwd=cwd)
    assert result.returncode == 2, (
        f'guard failed to trip on tracked source change (returncode {result.returncode}): {result.stdout}'
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'stale' in data['summary_message']


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_staleness_guard_ignores_pytest_cache_directory(tmp_path: Path):
    """A ``.pytest_cache/`` directory under marketplace/ MUST NOT trip the guard.

    Like ``__pycache__``, ``.pytest_cache`` is a runtime-only artifact
    that should never count as source drift.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '.pytest_cache/\n__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)
    _git_commit_all(cwd, 'initial')

    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    # Drop a .pytest_cache file with a mtime newer than target
    cache_marker = cwd / 'marketplace' / 'bundles' / 'demo' / '.pytest_cache' / 'CACHEDIR.TAG'
    _write(cache_marker, 'Signature: 8a477f597d28d172789f06886806bc55')
    _set_mtime(cache_marker, new + 120)

    cache = tmp_path / 'cache'
    result = _run('--cache-root', str(cache), cwd=cwd)
    assert result.returncode == 0, (
        f'guard tripped on .pytest_cache (returncode {result.returncode}): {result.stdout}'
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_staleness_guard_trips_on_untracked_source_style_file(tmp_path: Path):
    """A brand-new untracked ``.py`` file (NOT ignored) MUST trip the guard.

    The git probe uses ``git ls-files --others --ignored
    --exclude-standard`` which yields *ignored* files only. An untracked
    file that is NOT in ``.gitignore`` is "others, NOT ignored" and is
    therefore left in the candidate set — its fresh mtime should still
    cause the guard to refuse so the new source gets propagated.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init(cwd)
    _git_commit_all(cwd, 'initial')

    old = time.time() - 86400
    new = time.time()
    for path in (cwd / 'marketplace').rglob('*'):
        if path.is_file():
            _set_mtime(path, old)
    for path in (cwd / 'target').rglob('*'):
        if path.is_file():
            _set_mtime(path, new)

    # Drop a new untracked .py file with a mtime newer than target.
    # NOT in .gitignore, NOT yet `git add`-ed → "others, NOT ignored".
    new_source = cwd / 'marketplace' / 'bundles' / 'demo' / 'new_module.py'
    _write(new_source, '# new source file\n')
    _set_mtime(new_source, new + 60)

    result = _run(cwd=cwd)
    assert result.returncode == 2, (
        'guard failed to trip on untracked source file '
        f'(returncode {result.returncode}): {result.stdout}'
    )
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'stale' in data['summary_message']
