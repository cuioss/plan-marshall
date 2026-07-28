#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Cross-cutting regression suite: a failed finding-persist can never present as a clean pass.

Verification scope — deliberately different from the per-site suites. The
per-site tests (``test_scope_creep_check.py``, ``test_github_pr.py``, …) stub the
persist seam so they can express each outcome cheaply. This suite drives the
**real** ``add_qgate_finding`` validation surface end-to-end, which is precisely
the gap that let the original breakage live: every existing scope-creep test
stubbed ``_emit_finding`` wholesale, so the real function — and the malformed
argv inside it — was never executed by any test.

Three contracts:

  (a) A persist the REAL primitive rejects produces the loud behaviour — non-zero
      rc, ``error: finding_persist_failed``, the rejected finding's content
      present — and never ``status: success``, never a content-free referral.
  (b) The seam that carried the defect — the emitter's RETURN CONTRACT — is
      pinned directly. The pre-fix ``_emit_finding`` answered a rejection with a
      bare bool, which is the same signal it used for "nothing emitted", so the
      caller had nothing to branch on. The post-fix emitter answers the SAME real
      rejection with a failure descriptor carrying the primitive's message, which
      is what makes (a)'s loud output possible at all.
  (c) A successful persist is unaffected: the finding lands in the store, a
      ``resolution=pending`` readback covers it, and a ``deduplicated``
      re-persist stays benign.

Every test uses a unique ``plan_id`` (Q-Gate store isolation).
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-5-execute', 'scope_creep_check.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scope_creep_check as scc  # noqa: E402

_findings_core = load_script_module(
    'plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core'
)
add_qgate_finding = _findings_core.add_qgate_finding
query_qgate_findings = _findings_core.query_qgate_findings
QGATE_PERSIST_OK = _findings_core.QGATE_PERSIST_OK

# The finding type scope_creep_check passes. It is deliberately NOT a member of
# FINDING_TYPES — closing that taxonomy gap is a separate plan's scope — so the
# real primitive rejects it. That live rejection is what this suite drives.
_SCOPE_CREEP_TYPE = 'scope_creep_warning'

_EXCESS_FILES = [f'extra/{i}.py' for i in range(6)]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _seed_plan(plan_context, plan_id: str) -> Path:
    """Seed a plan whose residual file-set exceeds the default threshold."""
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(
        json.dumps({'plan_creation_sha': 'deadbeef', 'affected_files': ['src/a.py']}),
        encoding='utf-8',
    )
    return plan_dir


def _patch_worktree_reads(monkeypatch) -> None:
    """Patch ONLY the git/worktree reads — the persist stays real."""
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: ['src/a.py', *_EXCESS_FILES])
    monkeypatch.setattr(scc, '_resolve_worktree', lambda plan_id: Path.cwd())


def _run_check(plan_id: str) -> int:
    return scc.cmd_check(Namespace(plan_id=plan_id, threshold=None))


# ---------------------------------------------------------------------------
# Contract (a): a real rejection is loud
# ---------------------------------------------------------------------------


def test_real_rejection_is_loud_and_carries_finding_content(plan_context, monkeypatch, capsys):
    """The real primitive rejects the finding — the command must fail loud."""
    plan_id = 'qgate-contract-real-rejection'
    plan_dir = _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)

    rc = _run_check(plan_id)
    out = capsys.readouterr().out

    # Loud: non-zero rc plus the typed error.
    assert rc != 0
    assert 'status: error' in out
    assert 'error: finding_persist_failed' in out
    # The primitive's own message, so the cause is diagnosable from the output.
    assert 'Invalid finding type' in out
    assert _SCOPE_CREEP_TYPE in out
    # The rejected finding's content travels inline — never a content-free
    # referral to a store that does not hold it.
    assert 'finding_title: Scope creep detected' in out
    assert 'finding_detail:' in out
    for path in _EXCESS_FILES:
        assert path in out
    # The clean-pass shape is unreachable on a rejection.
    assert 'status: success' not in out
    assert 'finding_emitted: true' not in out

    # And the store genuinely does not hold the finding.
    store = plan_dir / 'artifacts' / 'findings' / 'qgate-5-execute.jsonl'
    assert not store.exists()


# ---------------------------------------------------------------------------
# Contract (b): the pre-fix return contract could not carry a rejection
# ---------------------------------------------------------------------------


def _pre_fix_emit_finding(plan_id: str, residual: list[str], threshold: int) -> bool:
    """Reconstruction of the PRE-FIX ``_emit_finding`` — kept red on purpose.

    Reproduces the two compounding defects the fix removed:

    1. The persist was a hand-built ``manage-findings qgate add`` argv rather
       than the in-process primitive.
    2. The result was guarded with ``returncode == 0``, which is structurally
       incapable of detecting an operation failure — those exit 0 and carry
       ``status: error`` in the TOON.

    The argv is not reconstructed (no subprocess is spawned here); what matters
    is the return contract: a bare ``False`` on every rejection, which the
    PRE-FIX ``cmd_check`` then reported as ``finding_emitted: false`` under
    ``status: success``.
    """
    return False


def test_pre_fix_return_contract_cannot_distinguish_a_rejection_from_no_creep(
    plan_context, monkeypatch, capsys
):
    """The pre-fix emitter collapsed a lost finding into the no-creep shape.

    Contract (b), pinned at the seam that actually carried the defect: the
    emitter's return value. The pre-fix emitter answered a REJECTED persist with
    the same bare ``False`` it used for "nothing emitted", so ``cmd_check`` had
    nothing to branch on and printed the ordinary no-creep output. The post-fix
    emitter answers the SAME real rejection with a failure descriptor carrying
    the primitive's own message — the input contract (a)'s loud output is built
    from.

    The pre-fix bool is deliberately NOT routed through the current
    ``cmd_check``: that caller's contract (``None``-or-dict) changed together
    with the emitter as one fix, so a bool is not a state the current code path
    can reach, and feeding it one would exercise a shape that never existed in
    either the pre-fix or the post-fix program.
    """
    plan_id = 'qgate-contract-pre-fix-shape'
    _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)

    # The no-creep output of the REAL command, with the threshold raised above
    # the residual: this is the shape a lost finding used to be confused with.
    assert scc.cmd_check(Namespace(plan_id=plan_id, threshold=len(_EXCESS_FILES) + 1)) == 0
    no_creep_out = capsys.readouterr().out
    assert 'status: success' in no_creep_out
    assert 'finding_emitted: false' in no_creep_out
    assert 'error: finding_persist_failed' not in no_creep_out

    # Pre-fix: a rejection is answered with the same content-free bool, so it is
    # indistinguishable from the no-creep run above.
    assert _pre_fix_emit_finding(plan_id, _EXCESS_FILES, 5) is False

    # Post-fix, driven against the REAL primitive's REAL rejection: the cause
    # travels back to the caller, which is what makes contract (a) reachable.
    failure = scc._emit_finding(plan_id, _EXCESS_FILES, 5)
    assert isinstance(failure, dict)
    assert 'Invalid finding type' in failure['message']
    assert _SCOPE_CREEP_TYPE in failure['message']
    assert failure['title'].startswith('Scope creep detected')


# ---------------------------------------------------------------------------
# Contract (c): the successful persist path is unaffected
# ---------------------------------------------------------------------------


def test_successful_persist_lands_and_readback_covers_it(plan_context):
    """A valid finding lands in the store and a pending readback covers it."""
    plan_id = 'qgate-contract-success-readback'
    plan_context.plan_dir_for(plan_id)

    result = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type='test-failure',
        title='test_foo failed',
        detail='AssertionError: 1 != 2',
    )

    assert result['status'] in QGATE_PERSIST_OK

    # The readback gate the phase-5 referral is now conditioned on.
    readback = query_qgate_findings(plan_id, '5-execute', resolution='pending')
    assert readback['status'] == 'success'
    assert readback['filtered_count'] == 1
    assert readback['findings'][0]['title'] == 'test_foo failed'


def test_deduplicated_repersist_stays_benign_and_readback_is_stable(plan_context):
    """A ``deduplicated`` re-persist is in-store and must not read as a rejection."""
    plan_id = 'qgate-contract-dedup-readback'
    plan_context.plan_dir_for(plan_id)

    first = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type='test-failure',
        title='test_bar failed',
        detail='AssertionError: none is not true',
    )
    second = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type='test-failure',
        title='test_bar failed',
        detail='AssertionError: none is not true',
    )

    assert first['status'] in QGATE_PERSIST_OK
    assert second['status'] in QGATE_PERSIST_OK
    assert second['status'] != first['status'], 'the re-persist must be the dedup outcome'
    assert second['hash_id'] == first['hash_id']

    # The readback still covers exactly one record — a dedup adds nothing but
    # loses nothing either.
    readback = query_qgate_findings(plan_id, '5-execute', resolution='pending')
    assert readback['filtered_count'] == 1


def test_rejected_persist_is_absent_from_the_readback(plan_context):
    """The readback gate is what makes a lost finding detectable at the leaf.

    A rejected persist leaves the store short, so a referral conditioned on the
    readback count cannot claim the finding is there.
    """
    plan_id = 'qgate-contract-readback-short'
    plan_context.plan_dir_for(plan_id)

    landed = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type='test-failure',
        title='test_landed failed',
        detail='AssertionError: landed',
    )
    rejected = add_qgate_finding(
        plan_id=plan_id,
        phase='5-execute',
        source='qgate',
        finding_type=_SCOPE_CREEP_TYPE,
        title='test_lost failed',
        detail='AssertionError: lost',
    )

    assert landed['status'] in QGATE_PERSIST_OK
    assert rejected['status'] not in QGATE_PERSIST_OK

    # Two persists attempted, one record readable — the short readback is the
    # signal the phase-5 referral gate branches on.
    readback = query_qgate_findings(plan_id, '5-execute', resolution='pending')
    assert readback['filtered_count'] == 1
    assert readback['findings'][0]['title'] == 'test_landed failed'
