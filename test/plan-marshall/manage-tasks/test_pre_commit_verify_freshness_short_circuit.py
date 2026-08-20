#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks."""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _CURRENT_SHA,
    _OTHER_SHA,
    _REAL_BUILD_NECESSITY_VERDICT,
    _RESOLVED_NOTATIONS,
    _build_entry,
    _capture_worktree_root,
    _freshness_mod,
    _stub_expected_notations,
    _stub_ledger_path,
    _stub_verdict,
    _stub_worktree_sha,
    _write_ledger,
    _write_manifest,
    _write_status,
    cmd_pre_commit_verify_freshness,
)
from _resolve_project_dir_fixtures import (
    CANONICAL_WORKTREE,
    patch_query_worktree_path,
    worktree_query_result,
)


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Stub the ONE resolver seam so no case shells out to ``manage-status``.

    The gate resolves its worktree root through ``resolve_plan_context``, whose
    only external touch point is ``file_ops._query_worktree_path``. Stubbing
    that seam (rather than the gate's own resolution) keeps the real delegation
    chain executing while making every case hermetic and subprocess-free.
    """
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _plan_id: worktree_query_result(True, str(Path.cwd())),
    )


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Default every case to a ``build`` verdict so the ledger scan is reached.

    A ``build`` verdict is the pass-through: the gate falls straight to the ledger
    scan, which is what the bulk of this file exercises. Cases that exercise the
    short-circuit override this with an explicit ``_stub_verdict`` call.
    """
    _stub_verdict(monkeypatch, {'decision': 'build'})


@pytest.fixture(autouse=True)
def _expected_notations_resolve(monkeypatch):
    """Pin the notation cross-check's resolved set for every case in this file.

    The real resolver runs the live architecture crawl against the checkout,
    which would make every case here depend on the working tree AND pay for a
    crawl per test. Pinning the set to the notations this file's fixtures use
    isolates the gate's own logic from the resolver's; the resolver's own
    behaviour — including what it does when resolution fails — is covered in
    ``test_freshness_notation_crosscheck_*.py``.
    """
    _stub_expected_notations(monkeypatch, _RESOLVED_NOTATIONS)


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


def test_worktree_root_routes_through_the_resolver(
    plan_context, monkeypatch, tmp_path
) -> None:
    """The root reaches the single ``get-worktree-path`` seam, exactly once."""
    plan_dir = plan_context.plan_dir_for('freshness-routing')
    _write_status(plan_dir)
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    with patch_query_worktree_path(True) as mock:
        cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-routing'))

    assert seen == [Path(CANONICAL_WORKTREE)]
    assert mock.call_count == 1, (
        'the freshness gate did not reach the single resolver seam exactly once '
        f'(call_count={mock.call_count})'
    )


def test_worktree_root_ignores_status_metadata(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``status.metadata.worktree_path`` decoy must NOT steer the resolution.

    The retired implementation read exactly this field. Seeding it with a path
    the resolver does not return proves the hand-read is gone: if the decoy ever
    wins again, the resolver has been bypassed.
    """
    plan_dir = plan_context.plan_dir_for('freshness-decoy')
    decoy = tmp_path / 'decoy-worktree'
    decoy.mkdir()
    _write_status(plan_dir, worktree_path=str(decoy))
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    with patch_query_worktree_path(True):
        cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-decoy'))

    assert seen == [Path(CANONICAL_WORKTREE)], (
        'the gate followed status.metadata.worktree_path instead of the resolver'
    )
