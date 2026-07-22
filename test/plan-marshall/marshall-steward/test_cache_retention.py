# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the marshall-steward ``cache_retention`` union-keep sweep.

``cache_retention.py`` partitions a plugin-cache tree into kept and removed
version dirs using a strict UNION of independent keep-rules — a dir is removed
only when NO rule keeps it. These tests construct real cache fixtures on disk
and assert the properties that make the sweep safe to run against the observed
production state (every version dir carrying an ``.orphaned_at`` marker):

* the live / provisioned / manifest-named / executing dirs are never pruned,
  even when EVERY version dir is marked,
* the keep-set is a union and not an intersection — a dir kept by age alone
  survives outside the newest-N, and vice versa,
* ``.orphaned_at`` is never a keep-or-delete oracle,
* the dry run (the default) removes nothing,
* every kept dir carries a keep-reason so a no-op is distinguishable from a
  clean run,
* the ``N``/``D`` knobs are honoured from ``marshal.json`` and fall back to
  ``5``/``3`` with a legible source annotation when the config is absent.

``cache_retention.py`` is a marshall-steward skill script, not on ``PYTHONPATH``
during pytest collection; the canonical ``sys.path.insert`` prologue (see
``pm-plugin-development:plugin-script-architecture`` test-scaffolding.md) makes
it and the shared TOON parser importable.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

# test/plan-marshall/marshall-steward/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLE_SKILLS = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
_SCRIPTS_DIR = _BUNDLE_SKILLS / 'marshall-steward' / 'scripts'
_TOON_SCRIPTS = _BUNDLE_SKILLS / 'ref-toon-format' / 'scripts'
for _dir in (_SCRIPTS_DIR, _TOON_SCRIPTS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import cache_retention  # noqa: E402
from toon_parser import parse_toon  # noqa: E402

_BUNDLE = 'plan-marshall'


@pytest.fixture(autouse=True)
def _no_manifest_env_override(monkeypatch: pytest.MonkeyPatch):
    """Clear ``PM_DIST_MANIFEST`` so manifest resolution uses the fixture tree."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)


def _make_cache(root: Path, versions: list[str], *, mark_all: bool = True, age_days: float = 30.0) -> Path:
    """Build a plugin-cache fixture and return its cache root.

    Every version dir carries an ``.orphaned_at`` marker by default — the
    observed production state the sweep must survive — and is aged well past any
    default ``D`` so the age arm of the union does not mask the other rules.
    """
    cache_root = root / 'plugins' / 'cache' / 'plan-marshall'
    old_mtime = time.time() - age_days * 86400
    for version in versions:
        version_dir = cache_root / _BUNDLE / version
        version_dir.mkdir(parents=True)
        if mark_all:
            (version_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z', encoding='utf-8')
        os.utime(version_dir, (old_mtime, old_mtime))
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _make_project(root: Path, *, keep_versions: int | None, keep_days: int | None, provisioned: str = '') -> Path:
    """Write a ``marshal.json`` project fixture and return the project root."""
    project_root = root / 'proj'
    (project_root / '.plan').mkdir(parents=True)
    retention: dict = {}
    if keep_versions is not None:
        retention['plugin_cache_keep_versions'] = keep_versions
    if keep_days is not None:
        retention['plugin_cache_keep_days'] = keep_days
    system: dict = {'retention': retention}
    if provisioned:
        system['provisioned_version'] = provisioned
    (project_root / '.plan' / 'marshal.json').write_text(json.dumps({'system': system}), encoding='utf-8')
    return project_root


def _make_manifest(root: Path, version: str) -> Path:
    """Write the cache-root ``dist-manifest.json`` naming ``version``."""
    manifest_path = root / 'plugins' / 'marketplaces' / 'plan-marshall' / 'dist-manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({'version': version}), encoding='utf-8')
    return manifest_path


def _kept_versions(report: dict) -> set[str]:
    return {row['version'] for row in report['kept']}


def _removed_versions(report: dict) -> set[str]:
    return {row['version'] for row in report['removed']}


# ============================================================================
# The live-version-never-pruned invariant under full marker saturation
# ============================================================================


def test_pinned_versions_survive_when_every_version_is_marked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """With EVERY version dir carrying ``.orphaned_at`` — the observed 580/580
    state — the newest-on-disk, provisioned, manifest-named and executing dirs
    all survive the sweep."""
    versions = [f'0.1.{n}' for n in range(1, 11)]
    cache_root = _make_cache(tmp_path, versions)
    _make_manifest(tmp_path, '0.1.5')
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=0, provisioned='0.1.3')
    monkeypatch.setattr(
        cache_retention, '_executing_version_dir', lambda: (cache_root / _BUNDLE / '0.1.7').resolve()
    )

    report = cache_retention.sweep(cache_root, apply_changes=False, project_root=project_root)

    kept = _kept_versions(report)
    assert '0.1.10' in kept, 'newest-on-disk must never be pruned'
    assert '0.1.3' in kept, 'the provisioned version must never be pruned'
    assert '0.1.5' in kept, 'the manifest-named version must never be pruned'
    assert '0.1.7' in kept, 'the executing version dir must never be pruned'


def test_orphaned_marker_is_never_a_keep_or_delete_oracle(tmp_path: Path):
    """The partition is identical whether or not the marker is present — the
    marker is advisory and is never consulted."""
    versions = [f'0.1.{n}' for n in range(1, 11)]
    marked_root = _make_cache(tmp_path / 'marked', versions, mark_all=True)
    unmarked_root = _make_cache(tmp_path / 'unmarked', versions, mark_all=False)
    project_root = _make_project(tmp_path, keep_versions=2, keep_days=0)

    marked = cache_retention.sweep(marked_root, project_root=project_root)
    unmarked = cache_retention.sweep(unmarked_root, project_root=project_root)

    assert _kept_versions(marked) == _kept_versions(unmarked)
    assert _removed_versions(marked) == _removed_versions(unmarked)
    assert _removed_versions(marked), 'the fixture must produce removals for the comparison to be meaningful'


def test_executing_version_dir_is_never_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Self-deletion is a real failure mode — the sweep runs from inside the
    cache it prunes — so the executing version dir is pinned unconditionally."""
    versions = [f'0.1.{n}' for n in range(1, 11)]
    cache_root = _make_cache(tmp_path, versions)
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=0)
    monkeypatch.setattr(
        cache_retention, '_executing_version_dir', lambda: (cache_root / _BUNDLE / '0.1.2').resolve()
    )

    report = cache_retention.sweep(cache_root, project_root=project_root)

    assert '0.1.2' in _kept_versions(report)
    assert '0.1.2' not in _removed_versions(report)


# ============================================================================
# Union, not intersection
# ============================================================================


def test_dir_kept_by_age_alone_survives_outside_newest_n(tmp_path: Path):
    """A young dir outside the newest-N still survives — the age rule keeps it
    on its own."""
    cache_root = _make_cache(tmp_path, ['0.1.1', '0.1.2', '0.1.3'], age_days=30.0)
    young = cache_root / _BUNDLE / '0.1.1'
    now = time.time()
    os.utime(young, (now, now))
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=3)

    report = cache_retention.sweep(cache_root, project_root=project_root)

    kept = {row['version']: row['reason'] for row in report['kept']}
    assert kept['0.1.1'] == cache_retention.KEEP_YOUNGER_THAN_D
    assert '0.1.2' in _removed_versions(report), 'the old middle version has no keep-rule and must be removed'


def test_dir_kept_by_newest_n_alone_survives_despite_age(tmp_path: Path):
    """An ancient dir inside the newest-N still survives — the count rule keeps
    it on its own, so the union is not an intersection."""
    cache_root = _make_cache(tmp_path, ['0.1.1', '0.1.2', '0.1.3'], age_days=365.0)
    project_root = _make_project(tmp_path, keep_versions=2, keep_days=1)

    report = cache_retention.sweep(cache_root, project_root=project_root)

    kept = {row['version']: row['reason'] for row in report['kept']}
    assert kept['0.1.2'] == cache_retention.KEEP_NEWEST_N
    assert kept['0.1.3'] == cache_retention.KEEP_NEWEST_N


# ============================================================================
# Dry run / apply, and report legibility
# ============================================================================


def test_dry_run_removes_nothing(tmp_path: Path):
    """The default dry run reports removals but leaves every directory on disk."""
    versions = ['0.1.1', '0.1.2', '0.1.3']
    cache_root = _make_cache(tmp_path, versions)
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=0)

    report = cache_retention.sweep(cache_root, apply_changes=False, project_root=project_root)

    assert report['applied'] is False
    assert report['removed_count'] > 0
    for version in versions:
        assert (cache_root / _BUNDLE / version).is_dir(), 'a dry run must not unlink anything'


def test_apply_removes_only_the_unkept(tmp_path: Path):
    """``--apply`` unlinks exactly the dirs no rule kept, and nothing else."""
    versions = ['0.1.1', '0.1.2', '0.1.3']
    cache_root = _make_cache(tmp_path, versions)
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=0)

    report = cache_retention.sweep(cache_root, apply_changes=True, project_root=project_root)

    assert report['applied'] is True
    for version in _removed_versions(report):
        assert not (cache_root / _BUNDLE / version).exists()
    for version in _kept_versions(report):
        assert (cache_root / _BUNDLE / version).is_dir()


def test_every_kept_dir_names_a_keep_reason(tmp_path: Path):
    """A run that removed nothing still explains why each dir was kept."""
    cache_root = _make_cache(tmp_path, ['0.1.1', '0.1.2'])
    project_root = _make_project(tmp_path, keep_versions=5, keep_days=0)

    report = cache_retention.sweep(cache_root, project_root=project_root)

    assert report['removed_count'] == 0
    assert report['swept_count'] == 2
    assert len(report['kept']) == 2
    for row in report['kept']:
        assert row['reason']
        assert row['bundle'] == _BUNDLE
    assert report['summary_message']


# ============================================================================
# Knob resolution
# ============================================================================


def test_non_default_knobs_are_honoured_from_marshal_json(tmp_path: Path):
    """A constructed ``marshal.json`` changes the keep-set and the report names
    the file it resolved the knobs from."""
    cache_root = _make_cache(tmp_path, [f'0.1.{n}' for n in range(1, 11)])
    project_root = _make_project(tmp_path, keep_versions=7, keep_days=0)

    report = cache_retention.sweep(cache_root, project_root=project_root)

    assert report['keep_versions'] == 7
    assert report['keep_days'] == 0
    assert 'marshal.json' in report['knob_source']
    assert len(report['kept']) >= 7


def test_absent_config_falls_back_to_documented_defaults(tmp_path: Path):
    """With no ``marshal.json`` the sweep falls back to 5/3 and annotates the
    source so a surprising keep-set stays diagnosable."""
    cache_root = _make_cache(tmp_path, ['0.1.1'])
    project_root = tmp_path / 'no-config'
    project_root.mkdir()

    report = cache_retention.sweep(cache_root, project_root=project_root)

    assert report['keep_versions'] == cache_retention.DEFAULT_KEEP_VERSIONS == 5
    assert report['keep_days'] == cache_retention.DEFAULT_KEEP_DAYS == 3
    assert report['knob_source'] == 'defaults'


def test_unresolvable_cache_root_reports_error_and_sweeps_nothing(tmp_path: Path):
    """A cache root that does not exist yields a structured error and no sweep."""
    report = cache_retention.sweep(tmp_path / 'no-such-cache', apply_changes=True)

    assert report['status'] == 'error'
    assert report['error'] == 'cache_root_unresolvable'
    assert report['swept_count'] == 0
    assert report['removed_count'] == 0


# ============================================================================
# CLI surface
# ============================================================================


def test_cli_sweep_defaults_to_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """``sweep`` without ``--apply`` exits 0, reports ``applied: false``, and
    leaves the tree intact."""
    versions = ['0.1.1', '0.1.2']
    cache_root = _make_cache(tmp_path, versions)
    project_root = _make_project(tmp_path, keep_versions=1, keep_days=0)

    exit_code = cache_retention.main(
        ['sweep', '--cache-root', str(cache_root), '--project-root', str(project_root)]
    )
    parsed = parse_toon(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed['status'] == 'success'
    assert parsed['applied'] is False
    for version in versions:
        assert (cache_root / _BUNDLE / version).is_dir()
