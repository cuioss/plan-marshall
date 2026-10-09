#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression suite: a failed finding-persist can never present as a clean pass.

Verification scope — deliberately different from the per-site suites. The
per-site tests (``test_scope_creep_check.py``, ``test_github_pr.py``, …) stub the
persist seam so they can express each outcome cheaply. This suite drives the
**real** ``add_qgate_finding`` validation surface end-to-end, which is precisely
the gap that let the original breakage live: every existing scope-creep test
stubbed ``_emit_finding`` wholesale, so the real function — and the malformed
argv inside it — was never executed by any test.

The scope-creep guard files its warning as type ``triage`` with the rule key
``scope_creep_warning``, a type the store accepts. The one rejection the real
primitive can still return to the guard is therefore the UNREACHED STORE — a
plan directory that is absent under the resolved root — and that is the live
rejection contracts (a) and (b) drive.

Four contracts:

  (a) A persist the REAL primitive rejects produces the loud behaviour — non-zero
      rc, ``error: finding_persist_failed``, the rejected finding's content
      present — and never ``status: success``, never a content-free referral.
      ``cmd_check`` reads the base branch from the plan directory before it
      persists, so the case removes the plan directory between the two, inside
      the already-patched diff read.
  (b) The seam that carried the defect — the emitter's RETURN CONTRACT — is
      pinned directly. The pre-fix ``_emit_finding`` answered a rejection with a
      bare bool, which is the same signal it used for "nothing emitted", so the
      caller had nothing to branch on. The post-fix emitter answers the SAME real
      rejection with a failure descriptor carrying the primitive's message, which
      is what makes (a)'s loud output possible at all.
  (c) A successful persist is unaffected: the finding lands in the store, a
      ``resolution=pending`` readback covers it, and a ``deduplicated``
      re-persist stays benign. This includes the guard's own warning, read back
      from the store as a pending ``triage`` record.
  (d) A residual set the operator already resolved as ``accepted`` or
      ``suppressed`` is not filed again, while a set resolved any other way, a
      grown set, and a different set sharing its first ten names all are.

Every test uses a unique ``plan_id`` (Q-Gate store isolation).
"""

from __future__ import annotations

import json
import re
import shutil
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

# PLAIN import, deliberately: the typed helpers below annotate what ``cmd_check``
# returns, and only a plain import gives mypy the real module — the shared loader
# returns ``Any``, which discards those annotations.
import scope_creep_check as scc
from toon_parser import parse_toon

from conftest import load_script_module

_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
add_qgate_finding = _findings_core.add_qgate_finding
query_qgate_findings = _findings_core.query_qgate_findings
resolve_qgate_finding = _findings_core.resolve_qgate_finding
QGATE_PERSIST_OK = _findings_core.QGATE_PERSIST_OK

# A literal that is deliberately NOT a member of FINDING_TYPES, used where a test
# needs the primitive's type validation to reject a persist. It is not a type any
# producer files.
_INVALID_TYPE = 'not-a-finding-type'

_PHASE = '5-execute'
_DECLARED_FILE = 'src/a.py'
_EXCESS_FILES = [f'extra/{i}.py' for i in range(6)]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _seed_plan(plan_context, plan_id: str) -> Path:
    """Seed a plan that declares one file, so every other changed file is residual."""
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'affected_files': [_DECLARED_FILE]}),
        encoding='utf-8',
    )
    return plan_dir


def _patch_worktree_reads(monkeypatch, residual: list[str] | None = None) -> None:
    """Patch ONLY the git/worktree reads — the store read and the persist stay real."""
    changed = [_DECLARED_FILE, *(_EXCESS_FILES if residual is None else residual)]
    _patch_merge_base(monkeypatch)
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: list(changed))
    monkeypatch.setattr(scc, '_resolve_worktree', lambda plan_id: Path.cwd())


def _patch_merge_base(monkeypatch) -> None:
    """Hold the merge-base resolution at a fixed value.

    A git read like the diff: without it the guard would ask the checkout the
    suite happens to run in for its merge-base with ``origin/main``.
    """
    monkeypatch.setattr(scc, '_resolve_merge_base', lambda worktree, base_branch: 'mergebase123')


def _run_check(plan_id: str) -> int:
    return scc.cmd_check(Namespace(plan_id=plan_id, threshold=None))


def _run_and_parse(plan_id: str, capsys) -> tuple[int, dict[str, Any], str]:
    """Run the guard and return ``(rc, parsed payload, raw stdout)``."""
    rc = _run_check(plan_id)
    out = capsys.readouterr().out
    payload: dict[str, Any] = parse_toon(out)
    return rc, payload, out


def _records(plan_id: str, resolution: str | None = None) -> list[dict[str, Any]]:
    """Read the phase-5 Q-Gate store back through the public query."""
    readback = query_qgate_findings(plan_id, _PHASE, resolution=resolution)
    assert readback['status'] == 'success'
    findings: list[dict[str, Any]] = readback['findings']
    return findings


def _file_and_resolve(plan_id: str, capsys, resolution: str) -> dict[str, Any]:
    """File the warning for the patched residual, then resolve it as ``resolution``.

    Returns the record as it was filed (still carrying ``pending``).
    """
    rc, payload, _out = _run_and_parse(plan_id, capsys)
    assert rc == 0
    assert payload['finding_emitted'] is True
    pending = _records(plan_id, 'pending')
    assert len(pending) == 1
    filed = pending[0]
    resolved = resolve_qgate_finding(plan_id, _PHASE, filed['hash_id'], resolution, 'decided by the operator')
    assert resolved['status'] == 'success'
    return filed


# ---------------------------------------------------------------------------
# Contract (a): a real rejection is loud
# ---------------------------------------------------------------------------


def test_real_rejection_is_loud_and_carries_finding_content(plan_context, monkeypatch, capsys):
    """The real primitive rejects the finding — the command must fail loud.

    The rejection is the unreached store. ``cmd_check`` has already read the
    base branch and resolved its baseline when it asks for the diff, so removing
    the plan directory from inside the patched diff read leaves the guard
    measuring a residual it then cannot persist.
    """
    plan_id = 'qgate-contract-real-rejection'
    plan_dir = _seed_plan(plan_context, plan_id)
    changed = [_DECLARED_FILE, *_EXCESS_FILES]

    def _diff_then_lose_the_plan_dir(worktree, sha):
        shutil.rmtree(plan_dir)
        return list(changed)

    _patch_merge_base(monkeypatch)
    monkeypatch.setattr(scc, '_git_diff_files', _diff_then_lose_the_plan_dir)
    monkeypatch.setattr(scc, '_resolve_worktree', lambda plan_id: Path.cwd())

    # The command emits through the canonical serializer, so the contract is
    # asserted over the PARSED payload rather than over raw substrings. The
    # title carries a colon and commas and is therefore quoted on the wire; a
    # substring assertion against the bare text pinned the pre-quoting shape and
    # would fail on correctly-quoted output.
    rc, payload, _out = _run_and_parse(plan_id, capsys)

    # Loud: non-zero rc plus the typed error.
    assert rc != 0
    assert payload['status'] == 'error'
    assert payload['error'] == 'finding_persist_failed'
    # The primitive's own message, so the cause is diagnosable from the output.
    assert 'was never reached' in payload['message']
    assert plan_id in payload['message']
    # The rejected finding's content travels inline — never a content-free
    # referral to a store that does not hold it. The declarations went with the
    # plan directory, so every changed file is residual.
    assert payload['finding_title'].startswith('Scope creep detected')
    assert 'residual_set=' in payload['finding_detail']
    assert payload['residual_files'] == sorted(changed)
    # The clean-pass shape is unreachable on a rejection.
    assert payload['status'] != 'success'
    assert 'finding_emitted' not in payload

    # And the store genuinely does not hold the finding.
    assert not plan_dir.exists()


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


def test_pre_fix_return_contract_cannot_distinguish_a_rejection_from_no_creep(plan_context, monkeypatch, capsys):
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

    # Post-fix, driven against the REAL primitive's REAL rejection — a plan id
    # with no plan directory, which the primitive refuses as an unreached store:
    # the cause travels back to the caller, which is what makes contract (a)
    # reachable.
    absent_plan_id = 'qgate-contract-no-plan-directory'
    failure = scc._emit_finding(absent_plan_id, _EXCESS_FILES, 5)
    assert isinstance(failure, dict)
    assert 'was never reached' in failure['message']
    assert absent_plan_id in failure['message']
    assert failure['title'].startswith('Scope creep detected')


# ---------------------------------------------------------------------------
# Contract (c): the successful persist path is unaffected
# ---------------------------------------------------------------------------


def test_scope_creep_warning_lands_in_the_store_as_a_pending_triage_record(plan_context, monkeypatch, capsys):
    """The guard's own warning reaches the store and reads back as filed.

    Only the git and worktree reads are patched: the type validation, the
    persist and the readback are all the real ones, so a type the store does not
    accept cannot pass here.
    """
    plan_id = 'qgate-contract-scope-creep-readback'
    _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)

    rc, payload, _out = _run_and_parse(plan_id, capsys)

    assert rc == 0
    assert payload['status'] == 'success'
    assert payload['finding_emitted'] is True
    assert 'finding_resolved_as' not in payload
    assert 'finding_hash_id' not in payload

    pending = _records(plan_id, 'pending')
    assert len(pending) == 1
    record = pending[0]
    assert record['type'] == 'triage'
    assert record['rule'] == 'scope_creep_warning'
    assert record['severity'] == 'warning'
    assert record['title'].startswith('Scope creep detected')
    for path in _EXCESS_FILES:
        assert path in record['title']


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
        finding_type=_INVALID_TYPE,
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


# ---------------------------------------------------------------------------
# Contract (d): a settled residual set is not filed again; anything else is
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('settled_as', ['accepted', 'suppressed'])
def test_settled_residual_set_is_not_filed_again(plan_context, monkeypatch, capsys, settled_as):
    """The same residual set, already decided, files nothing and names the record."""
    plan_id = f'qgate-contract-settled-{settled_as}'
    _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)
    filed = _file_and_resolve(plan_id, capsys, settled_as)

    rc, payload, out = _run_and_parse(plan_id, capsys)

    assert rc == 0
    assert payload['status'] == 'success'
    assert payload['residual_count'] == len(_EXCESS_FILES)
    assert payload['finding_emitted'] is False
    assert payload['finding_resolved_as'] == settled_as
    # Asserted on the wire rather than on the parsed value: a hash id made of
    # digits alone is read back as a number by the parser, which would compare
    # unequal to the stored string for a reason unrelated to this contract.
    assert re.search(rf'^finding_hash_id: "?{re.escape(filed["hash_id"])}"?$', out, re.MULTILINE)

    # The store is unchanged: one record, still settled, nothing pending.
    records = _records(plan_id)
    assert len(records) == 1
    assert records[0]['hash_id'] == filed['hash_id']
    assert records[0]['resolution'] == settled_as
    assert _records(plan_id, 'pending') == []


def test_residual_set_resolved_as_fixed_is_reopened(plan_context, monkeypatch, capsys):
    """Control: ``fixed`` claims the residual is gone, so measuring it again reopens it."""
    plan_id = 'qgate-contract-fixed-is-reopened'
    _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)
    filed = _file_and_resolve(plan_id, capsys, 'fixed')

    rc, payload, _out = _run_and_parse(plan_id, capsys)

    assert rc == 0
    assert payload['finding_emitted'] is True
    assert 'finding_resolved_as' not in payload
    assert 'finding_hash_id' not in payload

    records = _records(plan_id)
    assert len(records) == 1
    assert records[0]['hash_id'] == filed['hash_id']
    assert records[0]['resolution'] == 'pending'


def test_grown_residual_set_is_filed_beside_the_accepted_one(plan_context, monkeypatch, capsys):
    """Accepting one residual set does not accept a larger one."""
    plan_id = 'qgate-contract-grown-set'
    _seed_plan(plan_context, plan_id)
    _patch_worktree_reads(monkeypatch)
    accepted = _file_and_resolve(plan_id, capsys, 'accepted')

    _patch_worktree_reads(monkeypatch, [*_EXCESS_FILES, 'extra/one-more.py'])
    rc, payload, _out = _run_and_parse(plan_id, capsys)

    assert rc == 0
    assert payload['residual_count'] == len(_EXCESS_FILES) + 1
    assert payload['finding_emitted'] is True
    assert 'finding_resolved_as' not in payload

    pending = _records(plan_id, 'pending')
    assert len(pending) == 1
    assert pending[0]['hash_id'] != accepted['hash_id']
    assert 'extra/one-more.py' in pending[0]['title']

    # The accepted record is untouched.
    still_accepted = [r for r in _records(plan_id) if r['hash_id'] == accepted['hash_id']]
    assert len(still_accepted) == 1
    assert still_accepted[0]['resolution'] == 'accepted'
    assert still_accepted[0]['title'] == accepted['title']
    assert still_accepted[0]['detail'] == accepted['detail']


def test_sets_sharing_their_first_ten_names_are_different_sets(plan_context, monkeypatch, capsys):
    """Two eleven-file sets with one title are told apart by the residual digest.

    The title names the first ten sorted paths only, and both sets have the same
    count, so nothing but the digest in the detail separates them.
    """
    plan_id = 'qgate-contract-eleventh-file'
    _seed_plan(plan_context, plan_id)
    shared = [f'extra/{i:02d}.py' for i in range(10)]

    _patch_worktree_reads(monkeypatch, [*shared, 'extra/zz-first.py'])
    accepted = _file_and_resolve(plan_id, capsys, 'accepted')

    _patch_worktree_reads(monkeypatch, [*shared, 'extra/zz-second.py'])
    rc, payload, _out = _run_and_parse(plan_id, capsys)

    assert rc == 0
    assert payload['residual_count'] == 11
    assert payload['finding_emitted'] is True
    assert 'finding_resolved_as' not in payload

    pending = _records(plan_id, 'pending')
    assert len(pending) == 1
    # Same title, same count and threshold — only the digest differs.
    assert pending[0]['title'] == accepted['title']
    assert pending[0]['detail'] != accepted['detail']
    assert pending[0]['hash_id'] != accepted['hash_id']

    still_accepted = [r for r in _records(plan_id) if r['hash_id'] == accepted['hash_id']]
    assert still_accepted[0]['resolution'] == 'accepted'
