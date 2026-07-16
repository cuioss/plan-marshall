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

The freshness primitive is the change-ledger lookup, NOT a file-mtime heuristic.
Tests stub the two module-level boundary functions the command imports:

- ``compute_worktree_sha`` — the working-tree currency hash. Stubbed to a
  deterministic literal so the lookup match is exercised without standing up a
  real git worktree. Returning ``None`` exercises the ``head_unresolvable``
  fail-closed path.
- ``resolve_ledger_path`` — the tracked-config-dir ledger location. Stubbed to a
  temp JSONL file so the test controls the ledger entries directly.

Together they make the gate's three-way decision (``fresh`` / ``stale`` /
``undecidable``) deterministic and isolated from both git and the real ledger.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

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

    The ``documentation_only`` exemption (``_is_documentation_only``) reads
    ``execution.toon`` from the plan dir and parses TOON, returning ``True`` only
    when ``phase_5.verification_steps`` is an empty list. Serializing via
    ``serialize_toon`` guarantees the on-disk format round-trips through the
    ``parse_toon`` the helper-under-test uses to read it back — the same path the
    production ``manage-execution-manifest`` composer writes.

    An empty ``verification_steps`` list models a documentation-only plan (no
    build step runs); a non-empty list models a code-only / mixed plan that must
    still be gated by the ledger scan.
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
# documentation_only exemption
# =============================================================================
#
# A documentation-only plan composes an empty ``phase_5.verification_steps`` in
# its ``execution.toon`` manifest, runs no build, and therefore stamps no
# ``kind=build`` ledger entry. The gate must EXEMPT such a plan (short-circuit to
# ``fresh`` / ``documentation_only`` BEFORE the ledger scan) rather than fail
# closed on the missing build proof. The exemption fires ONLY when the manifest
# is present AND ``phase_5.verification_steps`` is empty; an absent manifest, a
# malformed manifest, or a non-empty step list must fall through to the ledger
# scan unchanged (regression coverage that code-only / mixed plans stay gated).


def test_documentation_only_exempts_when_verification_steps_empty(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Empty ``phase_5.verification_steps`` -> fresh / documentation_only.

    The exemption short-circuits BEFORE the ledger scan, so the gate passes even
    though no build proof exists. Both the sha stub and the ledger stub are set
    to fail-closed values (``None`` sha, missing ledger file) to prove the
    short-circuit fires ahead of them.
    """
    plan_dir = plan_context.plan_dir_for('freshness-docs-only')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=[])
    # Fail-closed boundary values — if the exemption did NOT short-circuit first,
    # the None sha would force ``undecidable / head_unresolvable``.
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-docs-only'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'documentation_only'
    assert result['plan_id'] == 'freshness-docs-only'
    # No ledger fields — the short-circuit returns before the scan.
    assert 'worktree_sha' not in result
    assert 'ledger_path' not in result


def test_documentation_only_exemption_ignores_stale_ledger(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Empty steps exempt even when the ledger would otherwise report stale.

    A real worktree sha plus a ledger holding only a build for a DIFFERENT sha is
    the canonical ``stale`` setup. The exemption must still win because it
    precedes the ledger scan.
    """
    plan_dir = plan_context.plan_dir_for('freshness-docs-stale-ledger')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=[])
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-docs-stale-ledger')
    )

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'documentation_only'


def test_non_empty_verification_steps_still_gated_by_ledger(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A code-only / mixed plan (non-empty steps) is NOT exempted -> still gated.

    Regression guard: the exemption must fire ONLY for empty steps. With a
    non-empty step list and a ledger that holds no matching build, the gate falls
    through to the ledger scan and reports ``stale``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-code-only')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=['quality-gate', 'module-tests'])
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-code-only'))

    assert result['status'] == 'stale', result
    assert 'reason' not in result or result.get('reason') != 'documentation_only'


def test_non_empty_verification_steps_still_resolves_fresh_with_matching_build(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A non-exempt plan with a matching build still resolves fresh via the scan.

    Confirms the fall-through path is the ORDINARY ledger gate (not a degraded
    branch): a code-only plan with a successful build for the current sha passes
    on its own freshness proof, with no documentation_only reason attached. The
    step list carries a build/test step (``module-tests``) so the lint-only
    exemption does NOT fire — the gate must reach the ledger scan.
    """
    plan_dir = plan_context.plan_dir_for('freshness-code-fresh')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=['quality-gate', 'module-tests'])
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-code-fresh'))

    assert result['status'] == 'fresh', result
    assert result.get('reason') not in ('documentation_only', 'lint_only')
    assert result['worktree_sha'] == _CURRENT_SHA


def test_absent_manifest_falls_through_to_ledger_scan(
    plan_context, monkeypatch, tmp_path
) -> None:
    """No ``execution.toon`` -> no exemption -> ordinary ledger scan.

    Regression guard: a missing manifest must NOT be treated as documentation_only.
    With no matching build, the gate reports ``stale``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-manifest')
    _write_status(plan_dir)
    # Deliberately do NOT write execution.toon.
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-manifest'))

    assert result['status'] == 'stale', result
    assert result.get('reason') != 'documentation_only'


def test_malformed_manifest_falls_through_to_ledger_scan(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A manifest that does not parse -> no exemption -> ordinary ledger scan.

    ``_is_documentation_only`` degrades to ``False`` (no exemption) on any parse
    error, so the gate falls through to the ledger scan rather than failing on
    the unreadable manifest.
    """
    plan_dir = plan_context.plan_dir_for('freshness-bad-manifest')
    _write_status(plan_dir)
    (plan_dir / 'execution.toon').write_text(
        '{ this is not valid toon\n  : : :\n', encoding='utf-8'
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-bad-manifest'))

    # Fell through to the scan, which finds the matching build -> fresh, but via
    # the ordinary path, NOT the documentation_only short-circuit.
    assert result['status'] == 'fresh', result
    assert result.get('reason') != 'documentation_only'
    assert result['worktree_sha'] == _CURRENT_SHA


def test_manifest_without_verification_steps_key_falls_through(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``phase_5`` block lacking ``verification_steps`` -> no exemption.

    ``_is_documentation_only`` returns ``True`` only when ``verification_steps``
    is present AND an empty list. An absent key (``None``) is not an empty list,
    so the plan is not exempted and the ledger scan governs the outcome.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-steps-key')
    _write_status(plan_dir)
    manifest = {
        'manifest_version': 1,
        'plan_id': 'freshness-no-steps-key',
        'phase_5': {'early_terminate': False},
        'phase_6': {'steps': []},
    }
    (plan_dir / 'execution.toon').write_text(
        serialize_toon(manifest), encoding='utf-8'
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-steps-key'))

    assert result['status'] == 'stale', result
    assert result.get('reason') != 'documentation_only'


# =============================================================================
# lint_only exemption
# =============================================================================
#
# A lint-only plan composes a NON-empty ``phase_5.verification_steps`` whose every
# entry resolves (by trailing ``:``-segment) to a structural-lint role
# (``quality-gate``) and none resolves to a build/test role. Structural lint never
# stamps a ``kind=build`` ledger entry, so — exactly like a documentation-only
# plan — such a plan legitimately runs no build and needs no freshness proof. The
# gate must EXEMPT it (short-circuit to ``fresh`` / ``lint_only`` BEFORE the ledger
# scan) rather than fail closed. The exemption fires ONLY when the list is
# non-empty AND every step is a quality-gate step; any build/test step
# (``module-tests``, ``coverage``, the bare ``verify`` alias) disables it and the
# plan falls through to the ledger scan (regression coverage that mixed plans stay
# gated).


def test_lint_only_exempts_when_all_steps_are_quality_gate(
    plan_context, monkeypatch, tmp_path
) -> None:
    """All-``quality-gate`` steps -> fresh / lint_only.

    The exemption short-circuits BEFORE the ledger scan, so the gate passes even
    though no build proof exists. Fail-closed boundary values (``None`` sha,
    missing ledger file) prove the short-circuit fires ahead of them.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-only')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=['quality-gate'])
    # Fail-closed boundary values — if the exemption did NOT short-circuit first,
    # the None sha would force ``undecidable / head_unresolvable``.
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-lint-only'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'lint_only'
    assert result['plan_id'] == 'freshness-lint-only'
    # No ledger fields — the short-circuit returns before the scan.
    assert 'worktree_sha' not in result
    assert 'ledger_path' not in result


def test_lint_only_resolves_role_through_default_and_verify_prefixes(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Prefixed step IDs resolve to ``quality-gate`` -> still lint_only.

    ``verify:quality-gate`` and ``default:verify:quality-gate`` both resolve to
    the ``quality-gate`` role via the trailing ``:``-segment, so a list mixing the
    prefixed forms is still all-lint and the exemption fires.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-prefixed')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir,
        verification_steps=['verify:quality-gate', 'default:verify:quality-gate'],
    )
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-lint-prefixed'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'lint_only'


def test_lint_only_exemption_ignores_stale_ledger(
    plan_context, monkeypatch, tmp_path
) -> None:
    """All-lint steps exempt even when the ledger would otherwise report stale.

    A real worktree sha plus a ledger holding only a build for a DIFFERENT sha is
    the canonical ``stale`` setup. The exemption must still win because it
    precedes the ledger scan.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-stale-ledger')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=['quality-gate'])
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-lint-stale-ledger')
    )

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'lint_only'


def test_lint_only_disabled_by_module_tests_step(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``module-tests`` step disables the lint-only exemption -> still gated.

    Regression guard: a single build/test step among quality-gate steps means the
    plan DOES run a build and must be gated by the ledger. With no matching build,
    the gate falls through to the ledger scan and reports ``stale``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-plus-tests')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir, verification_steps=['quality-gate', 'verify:module-tests']
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-lint-plus-tests'))

    assert result['status'] == 'stale', result
    assert result.get('reason') != 'lint_only'


def test_lint_only_disabled_by_coverage_step(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``coverage`` step disables the lint-only exemption -> still gated.

    Regression guard mirroring the ``module-tests`` case for the ``coverage``
    build/test role.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-plus-coverage')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir, verification_steps=['quality-gate', 'verify:coverage']
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-lint-plus-coverage')
    )

    assert result['status'] == 'stale', result
    assert result.get('reason') != 'lint_only'


def test_lint_only_disabled_by_bare_verify_alias(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A bare ``verify`` step disables the lint-only exemption -> still gated.

    The bare ``verify`` alias is a build/test role (it runs the full pipeline), so
    a list containing it is NOT all-lint and the exemption must not fire.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-plus-verify')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=['quality-gate', 'verify'])
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-lint-plus-verify'))

    assert result['status'] == 'stale', result
    assert result.get('reason') != 'lint_only'


def test_lint_only_not_triggered_by_empty_steps(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Empty steps are documentation_only, NOT lint_only.

    The lint-only predicate requires a NON-empty list; an empty list is the
    documentation-only case and must short-circuit with ``reason:
    documentation_only`` (the documentation-only branch precedes the lint-only
    branch in the handler).
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-empty')
    _write_status(plan_dir)
    _write_manifest(plan_dir, verification_steps=[])
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-lint-empty'))

    assert result['status'] == 'fresh', result
    assert result['reason'] == 'documentation_only'


def test_lint_only_falls_through_to_ledger_scan_for_matching_build(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A mixed (lint + build) plan with a matching build still resolves fresh.

    Confirms the disabled-exemption fall-through reaches the ORDINARY ledger gate:
    a mixed plan with a successful build for the current sha passes on its own
    freshness proof, with no lint_only reason attached.
    """
    plan_dir = plan_context.plan_dir_for('freshness-lint-mixed-fresh')
    _write_status(plan_dir)
    _write_manifest(
        plan_dir, verification_steps=['quality-gate', 'verify:module-tests']
    )
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-lint-mixed-fresh')
    )

    assert result['status'] == 'fresh', result
    assert result.get('reason') not in ('documentation_only', 'lint_only')
    assert result['worktree_sha'] == _CURRENT_SHA
