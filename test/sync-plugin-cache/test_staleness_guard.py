#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the sentinel-based staleness guard inside the project-local sync.py.

The guard reads ``target/claude/.emit-marker.json`` and refuses to mirror
the cache when the sentinel is absent, unparseable, or carries a
fingerprint that no longer matches the worktree under
``marketplace/bundles/``. The fingerprint is computed by the shared
``marketplace.targets.claude.source_fingerprint.compute_source_tree_fingerprint``
helper so the emitter (``target.py``) and the guard read the same
algorithm.

Coverage:

* (a) Fresh emit — sentinel + matching fingerprint → sync passes.
* (b) Missing sentinel → sync refuses with the documented message.
* (c) Source modification after emit — fingerprint mismatch → sync refuses.
* (d) ``--skip-staleness-guard`` still bypasses every refusal branch.

Plus focused unit tests for the fingerprint helper (i)–(v).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Ensure the marketplace package is importable so the fingerprint helper
# can be loaded directly in the unit tests below.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from marketplace.targets.claude.source_fingerprint import (  # noqa: E402
    FingerprintError,
    compute_source_tree_fingerprint,
    hash_object,
    list_tracked_files,
)

_SYNC_PY = PROJECT_ROOT / '.claude' / 'skills' / 'sync-plugin-cache' / 'scripts' / 'sync.py'
_SENTINEL_NAME = '.emit-marker.json'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


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


def _git_init_and_commit(cwd: Path, message: str = 'initial') -> None:
    """Initialise a git repo at ``cwd`` and commit every staged file.

    The fingerprint helper requires ``cwd`` to be a real git work tree
    because every primitive shells out to ``git``. Tests run in an
    isolated ``tmp_path`` and never touch any remote.
    """
    subprocess.run(['git', 'init', '-q'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.invalid'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=cwd, check=True)
    subprocess.run(['git', 'config', 'commit.gpgsign', 'false'], cwd=cwd, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', message], cwd=cwd, check=True)


def _write_sentinel(cwd: Path, fingerprint: str | None) -> Path:
    """Write the emit-marker sentinel into ``cwd/target/claude/``.

    Mirrors the payload shape that ``marketplace.targets.claude.target``
    writes at the end of every successful emit. Passing ``None`` for
    ``fingerprint`` reproduces the degraded sentinel emitted by the
    non-git fallback (the guard refuses on null too).
    """
    payload: dict[str, str | None] = {
        'emit_completed_at': '2026-05-27T12:00:00+00:00',
        'source_tree_fingerprint': fingerprint,
    }
    sentinel = cwd / 'target' / 'claude' / _SENTINEL_NAME
    _write(sentinel, json.dumps(payload, indent=2) + '\n')
    return sentinel


def _compute_fingerprint_for(cwd: Path) -> str:
    """Compute the live fingerprint for the test repo's marketplace tree."""
    return compute_source_tree_fingerprint(cwd)


# =============================================================================
# (a) Fresh emit — sentinel + matching fingerprint passes
# =============================================================================


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_fresh_emit_with_matching_fingerprint_passes(tmp_path: Path) -> None:
    """A sentinel written with the live fingerprint lets sync proceed."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)

    fingerprint = _compute_fingerprint_for(cwd)
    _write_sentinel(cwd, fingerprint)

    cache = tmp_path / 'cache'
    result = _run('--cache-root', str(cache), cwd=cwd)
    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    # The demo bundle landed in the cache at the version recorded in plugin.json
    assert (cache / 'demo' / '0.1.0' / 'README.md').is_file()


# =============================================================================
# (b) Missing sentinel → refusal
# =============================================================================


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_missing_sentinel_refuses(tmp_path: Path) -> None:
    """Sync refuses with the documented message when the sentinel is absent."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)
    # Deliberately do NOT write the sentinel.

    result = _run(cwd=cwd)
    assert result.returncode == 2, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'sentinel missing or unreadable' in data['summary_message']
    assert 'finalize-step-deploy-target' in data['summary_message']


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_unparseable_sentinel_refuses(tmp_path: Path) -> None:
    """A corrupted sentinel JSON triggers the same refusal branch."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)
    _write(cwd / 'target' / 'claude' / _SENTINEL_NAME, 'not-json{')

    result = _run(cwd=cwd)
    assert result.returncode == 2
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'sentinel' in data['summary_message']


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_sentinel_with_null_fingerprint_refuses(tmp_path: Path) -> None:
    """The non-git fallback sentinel (null fingerprint) must NOT pass the guard."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)
    _write_sentinel(cwd, None)

    result = _run(cwd=cwd)
    assert result.returncode == 2
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'source_tree_fingerprint' in data['summary_message']


# =============================================================================
# (c) Source modification after emit → fingerprint mismatch → refusal
# =============================================================================


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_source_drift_after_emit_refuses(tmp_path: Path) -> None:
    """Mutating a tracked file after the sentinel was written trips the guard."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)

    fingerprint = _compute_fingerprint_for(cwd)
    _write_sentinel(cwd, fingerprint)

    # Mutate the worktree AFTER the sentinel is written — this is the
    # canonical "source changed since last emit" scenario.
    tracked = cwd / 'marketplace' / 'bundles' / 'demo' / 'README.md'
    tracked.write_text('# demo CHANGED\n', encoding='utf-8')

    result = _run(cwd=cwd)
    assert result.returncode == 2, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'source tree changed since last emit' in data['summary_message']
    assert 'finalize-step-deploy-target' in data['summary_message']


# =============================================================================
# (d) --skip-staleness-guard bypasses every refusal branch
# =============================================================================


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_skip_staleness_guard_bypasses_missing_sentinel(tmp_path: Path) -> None:
    """--skip-staleness-guard reaches the sync path even when the sentinel is missing."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    # No marketplace/, no target/ — guard would normally refuse with rc 2.
    cache = tmp_path / 'cache'

    result = _run(
        '--skip-staleness-guard',
        '--cache-root', str(cache),
        cwd=cwd,
    )
    # No bundles to sync → exit 1 with a different message (proves the
    # guard did not fire; we got past it to the "no bundles" path).
    assert result.returncode == 1, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'no matching bundles' in data['summary_message']


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
@pytest.mark.skipif(shutil.which('rsync') is None, reason='rsync not on PATH')
def test_skip_staleness_guard_bypasses_fingerprint_mismatch(tmp_path: Path) -> None:
    """--skip-staleness-guard reaches the sync path even with a stale sentinel."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _make_target(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)
    # Sentinel with a wrong fingerprint — guard would refuse without --skip.
    _write_sentinel(cwd, 'deadbeef' * 5)

    cache = tmp_path / 'cache'
    result = _run('--skip-staleness-guard', '--cache-root', str(cache), cwd=cwd)
    assert result.returncode == 0, result.stdout
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert (cache / 'demo' / '0.1.0' / 'README.md').is_file()


# =============================================================================
# Fingerprint helper — focused unit tests (i)–(v)
# =============================================================================


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_fingerprint_is_deterministic_across_repeated_calls(tmp_path: Path) -> None:
    """(i) The fingerprint must be byte-stable for an unchanged tree."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0', 'demo2': '0.2.0'})
    _git_init_and_commit(cwd)

    first = compute_source_tree_fingerprint(cwd)
    second = compute_source_tree_fingerprint(cwd)
    third = compute_source_tree_fingerprint(cwd)
    assert first == second == third
    assert len(first) == 40  # sha-1 hex


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_fingerprint_sorts_paths_before_folding(tmp_path: Path) -> None:
    """(ii) The helper folds paths in sorted order, so iteration order is irrelevant.

    Indirect check: the helper sorts paths from ``git ls-files`` and the
    git output itself is already sorted (alphabetic by full path). We
    cross-check by computing the digest manually with the same sorted
    order — a divergence would imply the helper deviates from the
    documented algorithm.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0', 'alpha': '0.5.0', 'zeta': '0.9.0'})
    _git_init_and_commit(cwd)

    paths = list_tracked_files(cwd)
    assert paths == sorted(paths), 'list_tracked_files MUST return sorted paths'

    expected = hashlib.sha1()
    for path in paths:
        blob_sha = hash_object(cwd, path)
        expected.update(f'{path}:{blob_sha}\n'.encode())
    assert compute_source_tree_fingerprint(cwd) == expected.hexdigest()


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_fingerprint_excludes_untracked_and_gitignored_paths(tmp_path: Path) -> None:
    """(iii) Untracked + gitignored files MUST NOT contribute to the digest."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _write(cwd / '.gitignore', '__pycache__/\n*.pyc\n')
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)

    baseline = compute_source_tree_fingerprint(cwd)

    # Drop a gitignored .pyc and an untracked (but not gitignored) helper
    # file under a non-marketplace path. Neither should affect the
    # fingerprint, the former because git filters it, the latter because
    # it lives outside marketplace/bundles/ (the helper's prefix).
    _write(cwd / 'marketplace' / 'bundles' / 'demo' / '__pycache__' / 'x.pyc', 'bytecode')
    _write(cwd / 'sandbox' / 'scratch.py', '# untracked, outside prefix\n')

    after = compute_source_tree_fingerprint(cwd)
    assert after == baseline


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_fingerprint_changes_when_tracked_worktree_file_mutates(tmp_path: Path) -> None:
    """(iv) Mutating a tracked worktree file (without commit) changes the digest.

    This is the canonical worktree-reflection guarantee — the property
    that motivates using ``git hash-object`` per file rather than the
    HEAD tree SHA or the INDEX blob SHAs (both of which would miss
    uncommitted edits and let the guard silently pass on a drifted
    tree).
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)
    baseline = compute_source_tree_fingerprint(cwd)

    # Mutate the worktree only — do NOT commit or stage.
    (cwd / 'marketplace' / 'bundles' / 'demo' / 'README.md').write_text(
        '# demo MUTATED\n', encoding='utf-8'
    )
    drifted = compute_source_tree_fingerprint(cwd)
    assert drifted != baseline


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_hash_object_matches_git_native_invocation(tmp_path: Path) -> None:
    """(v) Per-file blob SHA must equal ``git hash-object`` invoked independently.

    Locks the contract that the helper delegates to git's primitive
    rather than computing a Python-side hash. A drift here would
    indicate the helper started reading file bytes itself.
    """
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    _git_init_and_commit(cwd)

    path = 'marketplace/bundles/demo/README.md'
    helper_sha = hash_object(cwd, path)
    native = subprocess.run(
        ['git', '-C', str(cwd), 'hash-object', path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert helper_sha == native


@pytest.mark.skipif(shutil.which('git') is None, reason='git not on PATH')
def test_fingerprint_raises_outside_git_repo(tmp_path: Path) -> None:
    """The helper refuses on non-git trees — no silent zero-hash fallback."""
    cwd = tmp_path / 'project'
    cwd.mkdir()
    _make_marketplace(cwd, {'demo': '0.1.0'})
    # NO git init — call must raise FingerprintError.

    with pytest.raises(FingerprintError):
        compute_source_tree_fingerprint(cwd)
