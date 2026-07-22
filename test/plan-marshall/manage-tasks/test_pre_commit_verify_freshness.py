#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

The subcommand answers a single deterministic question — "does the unified
change-ledger contain a ``kind=build`` entry with ``status == 'success'`` whose
``worktree_sha`` equals the CURRENT working-tree currency hash?" — and returns
one of three statuses (``fresh``, ``stale``, ``undecidable``) for the
orchestrator to consume as a fail-closed gate. Matching on ``status`` rather
than ``exit_code`` is load-bearing: the build wrapper exits 0 on timeout, so an
exit-code predicate would launder a build that never finished into a false
``fresh`` (regression covered below). See
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness" for the contract.

Before that question is asked at all, the gate consults the single build/no-build
authority (``extension_base.should_execute_build``, the ``manage-config
build-decision`` verb) COMMAND-FREE. A ``not_necessary`` verdict means no
``kind=build`` entry could ever legally exist for this footprint, so the gate
short-circuits to ``fresh`` carrying the verdict's OWN ``reason`` verbatim. The
gate derives no build-necessity signal of its own — it neither reads the
manifest's step shapes nor owns an exemption vocabulary. See ADR-004 §
"Amendment: ``build-decision`` is the sole build/no-build authority".

The freshness primitive is the change-ledger lookup, NOT a file-mtime heuristic.
Tests stub the three module-level boundary functions the command uses:

- ``compute_worktree_sha`` — the working-tree currency hash. Stubbed to a
  deterministic literal so the lookup match is exercised without standing up a
  real git worktree. Returning ``None`` exercises the ``head_unresolvable``
  fail-closed path.
- ``resolve_ledger_path`` — the tracked-config-dir ledger location. Stubbed to a
  temp JSONL file so the test controls the ledger entries directly.
- ``_build_necessity_verdict`` — the command-free consult of the sole authority.
  An autouse fixture pins it to ``build`` so every ledger-scan case reaches the
  scan; the build-necessity cases override it explicitly.

Together they make the gate's three-way decision (``fresh`` / ``stale`` /
``undecidable``) deterministic and isolated from git, the real ledger, and the
live project footprint.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import serialize_toon

from conftest import PROJECT_ROOT

# Load the cmd module via importlib (mirrors the qgate-mechanical test bootstrap).
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_freshness_mod = _load_module(
    '_cmd_pre_commit_verify_freshness_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)
cmd_pre_commit_verify_freshness = _freshness_mod.cmd_pre_commit_verify_freshness

# Captured BEFORE the autouse stub fixture can replace it: the cases that
# exercise the real consult (its call shape and its fail-closed except-branch)
# restore this, not whatever the fixture currently holds.
_REAL_BUILD_NECESSITY_VERDICT = _freshness_mod._build_necessity_verdict

# The current-sha literal the stubbed ``compute_worktree_sha`` returns. A
# ``kind=build`` entry whose ``worktree_sha`` matches this is a fresh build.
_CURRENT_SHA = 'a' * 64
_OTHER_SHA = 'b' * 64


# =============================================================================
# Fixture builders
# =============================================================================


def _write_status(plan_dir: Path, *, worktree_path: str = '') -> Path:
    """Write a minimal ``status.json`` whose metadata.worktree_path is set.

    Empty ``worktree_path`` (the default) leaves the worktree resolution to fall
    back to the current working directory. ``compute_worktree_sha`` is stubbed,
    so the resolved root never reaches real git — the status file exists only so
    ``_resolve_worktree_root`` has a deterministic input.
    """
    status = {
        'plan_id': plan_dir.name,
        'metadata': {'worktree_path': worktree_path},
    }
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps(status), encoding='utf-8')
    return status_path


def _build_entry(
    *,
    worktree_sha: str | None = _CURRENT_SHA,
    exit_code: int = 0,
    status: str | None = 'success',
    notation: str = 'plan-marshall:build-pyproject:pyproject_build',
    plan_id: str | None = 'freshness-test',
    timestamp_iso: str = '2026-06-11T12:00:00Z',
) -> dict:
    """Construct a ``kind=build`` ledger record dict.

    Mirrors the shape produced by ``_ledger_core.build_record``. The gate filters
    on ``kind``, ``status`` and ``worktree_sha`` only — never ``notation``,
    ``exit_code`` or ``plan_id`` — so those fields are parameterised to prove
    tier/tool agnosticism. ``status=None`` omits the key entirely, modelling a
    pre-change row (which must fail closed to ``stale``).
    """
    entry = {
        'kind': 'build',
        'notation': notation,
        'plan_id': plan_id,
        'args': 'run',
        'exit_code': exit_code,
        'worktree_sha': worktree_sha,
        'log_file': None,
        'timestamp_iso': timestamp_iso,
    }
    if status is not None:
        entry['status'] = status
    return entry


def _change_entry(*, worktree_sha: str = _CURRENT_SHA) -> dict:
    """Construct a ``kind=change`` ledger record dict (must NOT satisfy the gate)."""
    return {
        'kind': 'change',
        'deliverable_id': 'D1',
        'commit_sha': 'c' * 40,
        'changed_paths': ['src.py'],
        'worktree_sha': worktree_sha,
        'timestamp_iso': '2026-06-11T11:00:00Z',
    }


def _write_ledger(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a JSONL change-ledger file with the given entries and return its path."""
    ledger_path = tmp_path / 'change-ledger.jsonl'
    lines = [json.dumps(entry, sort_keys=True) for entry in entries]
    ledger_path.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    return ledger_path


def _write_manifest(plan_dir: Path, *, verification_steps: list[str]) -> Path:
    """Write an ``execution.toon`` manifest whose ``phase_5.verification_steps`` is set.

    The manifest is NO LONGER an input to the freshness gate — it is written here
    only as a decoy, so the tests can prove the gate ignores it. The retired
    implementation read this file and inferred build necessity from the SHAPE of
    the step list (empty -> ``documentation_only``, all-``quality-gate`` ->
    ``lint_only``); the gate now consults the sole build/no-build authority
    instead, so neither shape may change its outcome.
    """
    manifest = {
        'manifest_version': 1,
        'plan_id': plan_dir.name,
        'phase_5': {
            'early_terminate': len(verification_steps) == 0,
            'verification_steps': verification_steps,
        },
        'phase_6': {'steps': []},
    }
    manifest_path = plan_dir / 'execution.toon'
    manifest_path.write_text(serialize_toon(manifest), encoding='utf-8')
    return manifest_path


def _stub_worktree_sha(monkeypatch, sha: str | None) -> None:
    """Patch ``compute_worktree_sha`` so no real git worktree is required."""
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda root: sha)


def _stub_ledger_path(monkeypatch, ledger_path: Path) -> None:
    """Patch ``resolve_ledger_path`` so the gate reads the test's temp ledger."""
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)


def _stub_verdict(monkeypatch, verdict: dict) -> None:
    """Patch the command-free build-necessity consult to a fixed verdict.

    The real consult resolves the LIVE project footprint via git, which would make
    every case here depend on the checkout's working state. Pinning the verdict
    isolates the gate's own logic — the branch it takes on each verdict — from the
    authority's internals, which are covered by the authority's own tests.
    """
    monkeypatch.setattr(_freshness_mod, '_build_necessity_verdict', lambda _plan_id: verdict)


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Default every case to a ``build`` verdict so the ledger scan is reached.

    A ``build`` verdict is the pass-through: the gate falls straight to the ledger
    scan, which is what the bulk of this file exercises. Cases that exercise the
    short-circuit override this with an explicit ``_stub_verdict`` call.
    """
    _stub_verdict(monkeypatch, {'decision': 'build'})


# =============================================================================
# Tests
# =============================================================================


def test_fresh_when_matching_build_entry_present(plan_context, monkeypatch, tmp_path) -> None:
    """status: fresh — ledger has a successful build for the current sha."""
    plan_dir = plan_context.plan_dir_for('freshness-fresh')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-fresh'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-fresh'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert result['matched_notation'] == 'plan-marshall:build-pyproject:pyproject_build'


def test_stale_when_ledger_empty(plan_context, monkeypatch, tmp_path) -> None:
    """ledger empty -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-empty')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-empty'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert 'ledger_path' in result


def test_stale_when_ledger_absent(plan_context, monkeypatch, tmp_path) -> None:
    """ledger file missing entirely -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-no-file')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Point at a path that was never written.
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-file'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'


def test_stale_when_build_entry_for_different_sha(plan_context, monkeypatch, tmp_path) -> None:
    """ledger has a successful build but for a DIFFERENT sha -> stale (fail)."""
    plan_dir = plan_context.plan_dir_for('freshness-diff-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Successful build, wrong worktree_sha — the worktree mutated since the build.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-diff-sha'))

    assert result['status'] == 'stale', result
    assert result['worktree_sha'] == _CURRENT_SHA


def test_stale_when_only_failed_build_for_current_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A build entry matches the sha but ``status != success`` -> stale (fail closed)."""
    plan_dir = plan_context.plan_dir_for('freshness-failed-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error')]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-failed-build'))

    assert result['status'] == 'stale', result


def test_stale_when_timeout_build_exits_zero_for_current_sha(
    plan_context, monkeypatch, tmp_path
) -> None:
    """THE false-fresh regression: ``exit_code: 0`` + ``status: timeout`` -> stale.

    The build wrapper exits 0 on timeout (the outcome is modeled in its stdout
    TOON, not the exit code). Before the ``status`` predicate, this row proved
    freshness — a build that never finished laundered into a false ``fresh``.
    The gate must now report ``stale`` for it despite the matching sha and the
    zero exit code.
    """
    plan_dir = plan_context.plan_dir_for('freshness-timeout-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status='timeout')],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-timeout-build'))

    assert result['status'] == 'stale', result


def test_stale_when_killed_build_matches_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A ``status: killed`` row (signal-terminated child) must not prove freshness."""
    plan_dir = plan_context.plan_dir_for('freshness-killed-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=-9, status='killed')],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-killed-build'))

    assert result['status'] == 'stale', result


def test_stale_when_row_lacks_status_key(plan_context, monkeypatch, tmp_path) -> None:
    """A pre-change row without a ``status`` key never matches (fail-closed)."""
    plan_dir = plan_context.plan_dir_for('freshness-statusless-row')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status=None)],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-statusless-row'))

    assert result['status'] == 'stale', result


def test_stale_when_only_change_entry_matches_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A ``kind=change`` entry for the current sha must NOT satisfy the gate."""
    plan_dir = plan_context.plan_dir_for('freshness-change-only')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_change_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-change-only'))

    assert result['status'] == 'stale', result


def test_undecidable_when_worktree_sha_unresolvable(plan_context, monkeypatch, tmp_path) -> None:
    """ledger query cannot run because the sha is undefined -> conservative fail.

    ``compute_worktree_sha`` returns ``None`` (non-git directory / repo with no
    commit), so no positive freshness proof can be established and the gate fails
    closed BEFORE the ledger is even consulted.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, None)
    # A fresh-looking ledger exists but must be irrelevant — the sha is undefined.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-sha'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'head_unresolvable'


def test_fresh_match_is_notation_and_tier_agnostic(plan_context, monkeypatch, tmp_path) -> None:
    """A non-pyproject, plan-less (``plan_id=None``) build still satisfies the gate.

    The query filters on ``kind``, ``status`` and ``worktree_sha`` only — so a
    Maven build from an orchestrator-driven global-tier run with ``plan_id=None``
    proves freshness exactly as a plan-scoped pyproject build does.
    """
    plan_dir = plan_context.plan_dir_for('freshness-agnostic')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _build_entry(
                worktree_sha=_CURRENT_SHA,
                notation='plan-marshall:build-maven:maven',
                plan_id=None,
            )
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-agnostic'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-maven:maven'


def test_fresh_among_mixed_entries(plan_context, monkeypatch, tmp_path) -> None:
    """The matching successful build is found among non-matching noise entries."""
    plan_dir = plan_context.plan_dir_for('freshness-mixed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _change_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error'),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status='timeout'),
            _build_entry(worktree_sha=_CURRENT_SHA, notation='plan-marshall:build-npm:npm'),
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-mixed'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-npm:npm'


def test_malformed_ledger_lines_are_skipped(plan_context, monkeypatch, tmp_path) -> None:
    """A ledger with garbage lines around a valid entry still resolves fresh.

    ``read_entries`` tolerates and skips malformed JSONL lines, so a corrupt line
    must not turn a genuine fresh build into a query error.
    """
    plan_dir = plan_context.plan_dir_for('freshness-malformed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = tmp_path / 'change-ledger.jsonl'
    valid = json.dumps(_build_entry(worktree_sha=_CURRENT_SHA), sort_keys=True)
    ledger_path.write_text(
        'not-json-at-all\n' + valid + '\n{ broken json\n', encoding='utf-8'
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-malformed'))

    assert result['status'] == 'fresh', result


# =============================================================================
# Build-necessity short-circuit — the sole build/no-build authority
# =============================================================================
#
# The gate no longer infers build necessity from the manifest's step SHAPE (the
# retired ``documentation_only`` / ``lint_only`` exemptions). It consults the one
# authority COMMAND-FREE — "does anything in this footprint need a build?" — and:
#
#   * ``not_necessary`` -> short-circuit to ``fresh`` BEFORE the ledger scan,
#     forwarding the verdict's OWN ``reason`` verbatim. No ``kind=build`` entry
#     could legally exist for a footprint that needs no build, so demanding one
#     would be an impossible demand rather than a gate.
#   * ``build``         -> fall through to the ledger scan unchanged.
#
# The manifest is written in several cases below purely as a DECOY: whatever its
# step list looks like, it must not move the outcome.


def test_not_necessary_verdict_short_circuits_to_fresh(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``not_necessary`` verdict -> fresh, before the ledger is ever consulted.

    Fail-closed boundary values (``None`` sha, missing ledger file) prove the
    short-circuit fires ahead of them: had the gate reached the scan, the ``None``
    sha would have forced ``undecidable / head_unresolvable``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-build-needed')
    _write_status(plan_dir)
    _stub_verdict(
        monkeypatch,
        {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
    )
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-build-needed'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-no-build-needed'
    # No ledger fields — the short-circuit returns before the scan.
    assert 'worktree_sha' not in result
    assert 'ledger_path' not in result


def test_short_circuit_forwards_the_verdict_reason_verbatim(
    plan_context, monkeypatch, tmp_path
) -> None:
    """The gate reports the authority's reason, never one of its own.

    Owning an exemption vocabulary is what made the gate a second oracle: a
    hardcoded reason can state a cause the verdict never gave. Forwarding the
    verdict's text verbatim is the structural guarantee that it cannot.
    """
    plan_dir = plan_context.plan_dir_for('freshness-reason-forwarded')
    _write_status(plan_dir)
    _stub_verdict(
        monkeypatch,
        {
            'decision': 'not_necessary',
            'reason': 'build_map registers no globs — project has no buildable file types',
        },
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-reason-forwarded'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == (
        'build_map registers no globs — project has no buildable file types'
    )
    # The retired shape-derived vocabulary must not reappear.
    assert result['reason'] not in ('documentation_only', 'lint_only')


def test_short_circuit_beats_an_otherwise_stale_ledger(
    plan_context, monkeypatch, tmp_path
) -> None:
    """``not_necessary`` wins over a ledger that would otherwise report stale.

    A real worktree sha plus a ledger holding only a build for a DIFFERENT sha is
    the canonical ``stale`` setup. The short-circuit must still win because it
    precedes the ledger scan.
    """
    plan_dir = plan_context.plan_dir_for('freshness-nb-stale-ledger')
    _write_status(plan_dir)
    _stub_verdict(
        monkeypatch, {'decision': 'not_necessary', 'reason': 'plan footprint is empty'}
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-nb-stale-ledger'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'plan footprint is empty'


def test_build_verdict_falls_through_to_the_ledger_scan(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``build`` verdict is a pure pass-through -> the scan governs the outcome."""
    plan_dir = plan_context.plan_dir_for('freshness-build-needed')
    _write_status(plan_dir)
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-build-needed'))

    assert result['status'] == 'stale', result


def test_consult_is_command_free(plan_context, monkeypatch, tmp_path) -> None:
    """The gate asks the plan-wide question — it passes NO canonical command.

    The question "does this plan need a freshness proof?" is plan-wide, and the
    verdict does not vary by command, so nominating a representative command
    would be meaningless ceremony that invites a future reader to believe the
    command matters. This pins the actual call arguments at the lowest boundary:
    ``should_execute_build(None, plan_id)``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-command-free')
    _write_status(plan_dir)
    # Undo the autouse stub so the REAL _build_necessity_verdict runs and its
    # delegation to the authority is observed.
    monkeypatch.setattr(
        _freshness_mod, '_build_necessity_verdict', _REAL_BUILD_NECESSITY_VERDICT
    )
    calls: list[tuple] = []

    import extension_base

    def _record(canonical_command, plan_id, *args, **kwargs):
        calls.append((canonical_command, plan_id))
        return {'decision': 'not_necessary', 'reason': 'stubbed'}

    monkeypatch.setattr(extension_base, 'should_execute_build', _record)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-command-free'))

    assert calls == [(None, 'freshness-command-free')]
    assert result['status'] == 'fresh', result
    assert result['reason'] == 'stubbed'


def test_unobtainable_verdict_fails_closed_into_the_ledger_scan(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A consult that raises degrades to ``build`` -> the scan still gates.

    The fail-closed direction matters: an authority that cannot be reached must
    never be read as "no build was needed", which would wave the plan through
    without any freshness proof at all.
    """
    plan_dir = plan_context.plan_dir_for('freshness-verdict-error')
    _write_status(plan_dir)
    # Undo the autouse stub so the real helper's except-branch runs.
    monkeypatch.setattr(
        _freshness_mod, '_build_necessity_verdict', _REAL_BUILD_NECESSITY_VERDICT
    )

    import extension_base

    def _boom(*_args, **_kwargs):
        raise RuntimeError('marshal.json unreadable')

    monkeypatch.setattr(extension_base, 'should_execute_build', _boom)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-verdict-error'))

    assert result['status'] == 'stale', result


# =============================================================================
# Anti-regression: the manifest's step SHAPE is no longer an oracle
# =============================================================================
#
# These are the load-bearing cases for the consolidation. Each pairs a manifest
# whose shape WOULD have driven the retired predicate with a verdict that
# disagrees, and asserts the verdict wins. Without them the two mechanics could
# silently be reintroduced side by side and every other test would still pass.


def test_empty_step_list_does_not_exempt_when_a_build_is_necessary(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Empty ``verification_steps`` + ``build`` verdict -> still gated.

    The retired ``documentation_only`` exemption keyed on exactly this manifest
    shape and would have short-circuited to ``fresh``, waving through a code
    footprint with no build proof.
    """
    plan_dir = plan_context.plan_dir_for('freshness-empty-steps-but-code')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=[])
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-empty-steps-but-code')
    )

    assert result['status'] == 'stale', result


def test_all_quality_gate_steps_do_not_exempt_when_a_build_is_necessary(
    plan_context, monkeypatch, tmp_path
) -> None:
    """All-``quality-gate`` steps + ``build`` verdict -> still gated.

    The retired ``lint_only`` exemption keyed on exactly this manifest shape.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-steps-but-code')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir,
        verification_steps=['verify:quality-gate', 'default:verify:quality-gate'],
    )
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-lint-steps-but-code')
    )

    assert result['status'] == 'stale', result


def test_build_shaped_steps_still_exempt_a_footprint_needing_no_build(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A markdown-only footprint is exempt even though the manifest composes builds.

    The converse gap the consolidation closes: a plan whose manifest carries
    ``module-tests`` / ``coverage`` steps was NEVER exempt under the retired
    shape predicate, so a docs-only footprint that ran no build failed closed on
    a build proof it could not possibly produce. The footprint decides now.
    """
    plan_dir = plan_context.plan_dir_for('freshness-docs-footprint-build-steps')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir,
        verification_steps=['verify:quality-gate', 'verify:module-tests', 'verify:coverage'],
    )
    _stub_verdict(
        monkeypatch,
        {
            'decision': 'not_necessary',
            'reason': 'plan footprint touches no build_map glob — only non-buildable files changed',
        },
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-docs-footprint-build-steps')
    )

    assert result['status'] == 'fresh', result
    assert 'no build_map glob' in result['reason']


def test_absent_manifest_is_irrelevant_to_the_gate(
    plan_context, monkeypatch, tmp_path
) -> None:
    """No ``execution.toon`` at all changes nothing — the manifest is not read.

    The retired predicate degraded to "no exemption" on a missing manifest; the
    gate now never opens the file, so its absence is simply not a signal.
    """
    plan_dir = plan_context.plan_dir_for('freshness-nb-no-manifest')
    _write_status(plan_dir)
    # Deliberately do NOT write execution.toon.
    _stub_verdict(
        monkeypatch, {'decision': 'not_necessary', 'reason': 'plan footprint is empty'}
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-nb-no-manifest'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'plan footprint is empty'


def test_malformed_manifest_is_irrelevant_to_the_gate(
    plan_context, monkeypatch, tmp_path
) -> None:
    """An unparseable manifest cannot affect the gate — it is never parsed."""
    plan_dir = plan_context.plan_dir_for('freshness-nb-bad-manifest')
    _write_status(plan_dir)
    (plan_dir / 'execution.toon').write_text(
        '{ this is not valid toon\n  : : :\n', encoding='utf-8'
    )
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-nb-bad-manifest'))

    assert result['status'] == 'fresh', result
    assert result['worktree_sha'] == _CURRENT_SHA
