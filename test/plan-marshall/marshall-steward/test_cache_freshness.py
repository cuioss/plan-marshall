# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshall-steward ``cache_freshness`` verdict emitter.

``cache_freshness.py`` is a pure deterministic emitter: its ``check`` subcommand
compares the newest plugin-cache version dir against the version recorded in the
marketplace-clone-root ``dist-manifest.json`` and emits the three-valued
``fresh | stale | unknown`` verdict. These tests construct real cache/clone
fixtures on disk (the clone-root mapping is a literal
``/plugins/cache/<mp>`` → ``/plugins/marketplaces/<mp>`` path rewrite, so the
fixture must carry those segments verbatim) and assert:

* each of the three verdicts against its constructed input,
* the never-vacuous-fresh invariant on every ``unknown`` branch,
* that ``unknown`` carries ``refuses_upgrade: true`` and is distinguishable
  from ``stale``,
* that no input combination yields a fourth verdict or an age-inferred
  downgrade of ``unknown``,
* that the remediation string names the operator commands literally, and that
  it carries the closing session-reload step — in that order, and on every
  refusing verdict — because an update the running session never reloads leaves
  that session reading the pre-update cache.

``cache_freshness.py`` is a marshall-steward skill script, reached through the
shared ``conftest.load_script_module`` loader; the shared TOON parser imports by
name, because the root conftest puts every marketplace ``scripts/`` directory on
``sys.path`` before any test module is imported.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import load_script_module

cache_freshness = load_script_module('plan-marshall', 'marshall-steward', 'cache_freshness.py')

_VERDICTS = {'fresh', 'stale', 'unknown'}


@pytest.fixture(autouse=True)
def _no_manifest_env_override(monkeypatch: pytest.MonkeyPatch):
    """Clear ``PM_DIST_MANIFEST`` so manifest resolution uses the fixture tree.

    The imported resolution order short-circuits on that environment variable;
    an ambient value from another test (or the developer's shell) would make
    every fixture resolve to the same manifest.
    """
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)


def _make_cache(tmp_path: Path, versions: list[str]) -> Path:
    """Build a plugin-cache fixture and return its cache root.

    Lays out ``<tmp>/plugins/cache/plan-marshall/<bundle>/<version>/`` for each
    supplied version. The ``/plugins/cache/`` segment is load-bearing: the
    imported manifest resolver maps it to ``/plugins/marketplaces/`` to find the
    clone-root manifest.
    """
    cache_root = tmp_path / 'plugins' / 'cache' / 'plan-marshall'
    for version in versions:
        (cache_root / 'plan-marshall' / version).mkdir(parents=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _make_clone_manifest(tmp_path: Path, version: str) -> Path:
    """Write a marketplace-clone-root ``dist-manifest.json`` and return its path."""
    manifest_path = tmp_path / 'plugins' / 'marketplaces' / 'plan-marshall' / 'dist-manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({'version': version}), encoding='utf-8')
    return manifest_path


# ============================================================================
# The three verdicts
# ============================================================================


def test_cache_at_manifest_version_is_fresh(tmp_path: Path):
    """A cache whose newest version equals the clone-root manifest is ``fresh``
    and does not refuse the upgrade."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])
    _make_clone_manifest(tmp_path, '0.1.100')

    result = cache_freshness.check_freshness(cache_root)

    assert result['freshness'] == 'fresh'
    assert result['refuses_upgrade'] is False
    assert result['remediation'] == ''
    assert result['cache_version'] == '0.1.100'
    assert result['manifest_version'] == '0.1.100'


def test_cache_ahead_of_manifest_is_fresh(tmp_path: Path):
    """A cache NEWER than the clone-root manifest is still ``fresh`` — the gate
    refuses only when the consumer is BEHIND."""
    cache_root = _make_cache(tmp_path, ['0.1.200'])
    _make_clone_manifest(tmp_path, '0.1.100')

    result = cache_freshness.check_freshness(cache_root)

    assert result['freshness'] == 'fresh'
    assert result['refuses_upgrade'] is False


def test_cache_behind_manifest_is_stale_and_refuses(tmp_path: Path):
    """A cache BEHIND the clone-root manifest is ``stale``, refuses the upgrade,
    and carries the verbatim remediation."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])
    _make_clone_manifest(tmp_path, '0.1.200')

    result = cache_freshness.check_freshness(cache_root)

    assert result['freshness'] == 'stale'
    assert result['refuses_upgrade'] is True
    assert result['remediation'] == cache_freshness.REMEDIATION
    assert result['cache_version'] == '0.1.100'
    assert result['manifest_version'] == '0.1.200'


def test_unresolvable_clone_manifest_is_unknown_never_fresh(tmp_path: Path):
    """No resolvable clone-root manifest yields ``unknown`` — NEVER a vacuous
    ``fresh`` — with a legible warning and a refusal."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])

    result = cache_freshness.check_freshness(cache_root)

    assert result['freshness'] == 'unknown'
    assert result['freshness'] != 'fresh'
    assert result['refuses_upgrade'] is True
    assert result['manifest_version'] == 'unknown'
    assert result['warning']


def test_unresolvable_cache_root_is_unknown(tmp_path: Path):
    """A cache root that does not exist yields ``unknown`` and refuses."""
    result = cache_freshness.check_freshness(tmp_path / 'no-such-cache')

    assert result['freshness'] == 'unknown'
    assert result['refuses_upgrade'] is True
    assert result['cache_version'] == 'unknown'
    assert result['warning']


def test_cache_root_without_version_dirs_is_unknown(tmp_path: Path):
    """A materialized cache root carrying no version directory yields
    ``unknown`` rather than an unsubstantiated verdict."""
    cache_root = _make_cache(tmp_path, [])
    (cache_root / 'plan-marshall').mkdir(parents=True)

    result = cache_freshness.check_freshness(cache_root)

    assert result['freshness'] == 'unknown'
    assert result['refuses_upgrade'] is True


# ============================================================================
# Invariants: verdict set, refusal semantics, no inferred fallback
# ============================================================================


def test_no_input_combination_yields_a_fourth_verdict(tmp_path: Path):
    """Across the full fixture matrix the verdict is always one of exactly three
    values, and ``refuses_upgrade`` is False only on ``fresh``."""
    cases = [
        (['0.1.100'], '0.1.100'),
        (['0.1.100'], '0.1.200'),
        (['0.1.200'], '0.1.100'),
        (['0.1.9', '0.1.10'], '0.1.10'),
        ([], None),
        (['0.1.100'], None),
    ]
    for index, (versions, manifest_version) in enumerate(cases):
        case_dir = tmp_path / f'case{index}'
        cache_root = _make_cache(case_dir, versions)
        if manifest_version is not None:
            _make_clone_manifest(case_dir, manifest_version)

        result = cache_freshness.check_freshness(cache_root)

        assert result['freshness'] in _VERDICTS
        assert result['refuses_upgrade'] is (result['freshness'] != 'fresh')


def test_unknown_and_stale_are_distinct_but_both_refuse(tmp_path: Path):
    """``unknown`` and ``stale`` are distinguishable verdicts, yet both refuse
    the upgrade and both name the same operator commands."""
    stale_dir = tmp_path / 'stale'
    stale_root = _make_cache(stale_dir, ['0.1.100'])
    _make_clone_manifest(stale_dir, '0.1.200')
    unknown_root = _make_cache(tmp_path / 'unknown', ['0.1.100'])

    stale = cache_freshness.check_freshness(stale_root)
    unknown = cache_freshness.check_freshness(unknown_root)

    assert stale['freshness'] == 'stale'
    assert unknown['freshness'] == 'unknown'
    assert stale['freshness'] != unknown['freshness']
    assert stale['refuses_upgrade'] is True
    assert unknown['refuses_upgrade'] is True
    assert stale['remediation'] == unknown['remediation'] == cache_freshness.REMEDIATION


def test_unknown_is_not_downgraded_by_cache_age(tmp_path: Path):
    """No age/mtime-based fallback exists: an ancient cache dir yields the same
    ``unknown`` verdict as a freshly-created one when no manifest resolves."""
    young_root = _make_cache(tmp_path / 'young', ['0.1.100'])
    old_dir = tmp_path / 'old'
    old_root = _make_cache(old_dir, ['0.1.100'])
    ancient = 10_000.0
    os.utime(old_root / 'plan-marshall' / '0.1.100', (ancient, ancient))
    os.utime(old_root, (ancient, ancient))

    young = cache_freshness.check_freshness(young_root)
    old = cache_freshness.check_freshness(old_root)

    assert young['freshness'] == old['freshness'] == 'unknown'
    assert young['refuses_upgrade'] == old['refuses_upgrade'] is True


def test_every_verdict_declares_its_local_clone_comparison_scope(tmp_path: Path):
    """Every verdict — fresh, stale, unknown — stamps
    ``compared_against: local_clone_manifest``, so a ``fresh`` result discloses it
    compares only against the LOCAL clone and never claims upstream currency. This
    is the upstream-skew guard: an upstream-blind ``fresh`` cannot masquerade as an
    upstream-currency claim, because it names the scope it actually checked."""
    fresh_dir = tmp_path / 'fresh'
    fresh_root = _make_cache(fresh_dir, ['0.1.200'])
    _make_clone_manifest(fresh_dir, '0.1.100')
    fresh = cache_freshness.check_freshness(fresh_root)
    assert fresh['freshness'] == 'fresh'
    assert fresh['compared_against'] == 'local_clone_manifest'

    stale_dir = tmp_path / 'stale'
    stale_root = _make_cache(stale_dir, ['0.1.100'])
    _make_clone_manifest(stale_dir, '0.1.200')
    stale = cache_freshness.check_freshness(stale_root)
    assert stale['freshness'] == 'stale'
    assert stale['compared_against'] == 'local_clone_manifest'

    unknown = cache_freshness.check_freshness(tmp_path / 'no-such-cache')
    assert unknown['freshness'] == 'unknown'
    assert unknown['compared_against'] == 'local_clone_manifest'


def test_remediation_names_the_commands_literally():
    """The remediation names the non-destructive update command verbatim and a
    version-verify step, and never reaches for the destructive uninstall/reinstall.

    `/plugin update plan-marshall` updates the installed plugin in place; the old
    uninstall + reinstall guidance was destructive and wrong. The version-verify
    step is what confirms the update actually landed."""
    assert '/plugin update plan-marshall' in cache_freshness.REMEDIATION
    # non-destructive: the remediation must NOT tell the operator to run the
    # destructive uninstall/install commands (the defect this correction fixes)
    assert '/plugin uninstall' not in cache_freshness.REMEDIATION
    assert '/plugin install' not in cache_freshness.REMEDIATION
    # the update is followed by a version-verify step
    assert 'version' in cache_freshness.REMEDIATION


def test_remediation_closes_with_the_session_reload_step():
    """The remediation ends with the session-reload step, and names how to
    resolve it on both runtimes.

    Updating the cache is not the same as the running session SEEING the update:
    the plugin registry is pinned at session start, so an operator who updates
    and carries on keeps reading the pre-update cache and concludes the update
    did not work. A remediation that stops at 'update, then verify the version'
    stops one step short of the outcome it promises."""
    remediation = cache_freshness.REMEDIATION

    # the reload step itself, and the seam that resolves the runtime directive
    assert "reload the session's plugin set" in remediation
    assert 'platform_runtime session reload-directive' in remediation
    # both runtimes are named: the Claude directive, and OpenCode's no-op
    # alternative — otherwise an OpenCode operator is told to run a directive
    # their runtime does not have.
    assert '/reload-plugins' in remediation
    assert 'full session restart' in remediation


def test_remediation_orders_update_then_verify_then_reload():
    """The three steps appear in causal order.

    Order is the whole point: a reload performed BEFORE the update reloads the
    pre-update cache, and a version-verify performed after a reload of the old
    cache reports the old version. Asserting mere presence of the three clauses
    would pass on any permutation, including the ones that do not work."""
    remediation = cache_freshness.REMEDIATION

    update_at = remediation.index("'/plugin update plan-marshall'")
    verify_at = remediation.index('confirming plan-marshall reports the expected version')
    reload_at = remediation.index("reload the session's plugin set")

    assert update_at < verify_at < reload_at
    # the reload is the LAST of the three, not merely present somewhere
    assert reload_at == max(update_at, verify_at, reload_at)


def test_every_refusing_verdict_emits_the_reload_step(tmp_path: Path):
    """Both refusing verdicts hand the operator the reload step.

    ``stale`` and ``unknown`` are distinct verdicts reached by different
    branches; this asserts the reload instruction is in the string the operator
    actually RECEIVES on each of them, not merely in the module constant."""
    stale_dir = tmp_path / 'stale'
    stale_root = _make_cache(stale_dir, ['0.1.100'])
    _make_clone_manifest(stale_dir, '0.1.200')
    unknown_root = _make_cache(tmp_path / 'unknown', ['0.1.100'])

    stale = cache_freshness.check_freshness(stale_root)
    unknown = cache_freshness.check_freshness(unknown_root)

    assert stale['freshness'] == 'stale'
    assert unknown['freshness'] == 'unknown'
    for verdict in (stale, unknown):
        assert verdict['refuses_upgrade'] is True
        assert "reload the session's plugin set" in verdict['remediation']
        assert 'platform_runtime session reload-directive' in verdict['remediation']

    # the non-refusing verdict carries no remediation at all, so the reload step
    # is not emitted to an operator who has nothing to do.
    fresh_dir = tmp_path / 'fresh'
    fresh_root = _make_cache(fresh_dir, ['0.1.200'])
    _make_clone_manifest(fresh_dir, '0.1.100')
    fresh = cache_freshness.check_freshness(fresh_root)
    assert fresh['freshness'] == 'fresh'
    assert fresh['remediation'] == ''


def test_cli_stale_verdict_carries_the_reload_step_through_toon(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """The reload step survives TOON serialization to the CLI consumer.

    The remediation is a long single-line value containing quotes, an em dash and
    parentheses; this asserts the operator-facing text reaches stdout intact
    rather than being truncated or re-wrapped into a value the parser splits."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])
    _make_clone_manifest(tmp_path, '0.1.200')

    exit_code = cache_freshness.main(['check', '--cache-root', str(cache_root)])
    parsed = parse_toon(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed['freshness'] == 'stale'
    assert parsed['remediation'] == cache_freshness.REMEDIATION


def test_newest_cache_version_orders_numerically(tmp_path: Path):
    """Version-dir selection is a numeric tuple compare, so ``0.1.9`` never
    shadows ``0.1.10``."""
    cache_root = _make_cache(tmp_path, ['0.1.9', '0.1.10'])

    assert cache_freshness.newest_cache_version(cache_root) == '0.1.10'


def test_check_is_read_only(tmp_path: Path):
    """The verb mutates nothing — the fixture tree is byte-identical afterwards."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])
    _make_clone_manifest(tmp_path, '0.1.200')
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))

    cache_freshness.check_freshness(cache_root)

    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*')) == before


# ============================================================================
# CLI surface
# ============================================================================


def test_cli_check_emits_parseable_toon(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """``check --cache-root`` exits 0 and emits the documented TOON keys."""
    cache_root = _make_cache(tmp_path, ['0.1.100'])
    _make_clone_manifest(tmp_path, '0.1.200')

    exit_code = cache_freshness.main(['check', '--cache-root', str(cache_root)])
    parsed = parse_toon(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed['status'] == 'success'
    assert parsed['freshness'] == 'stale'
    assert {
        'freshness',
        'refuses_upgrade',
        'cache_version',
        'manifest_version',
        'compared_against',
        'remediation',
    }.issubset(parsed.keys())
