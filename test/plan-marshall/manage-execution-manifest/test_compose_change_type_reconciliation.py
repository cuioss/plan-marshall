#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""change_type scope reconciliation for the ``compose`` verb (plan 350).

``--plan-change-type`` (dest ``change_type``) is a caller-supplied change type; the
plan's SETTLED classification lives at ``status.metadata.change_type`` (the PLAN
scope). The composer makes plan-wide decisions, so the settled classification is
authoritative: a supplied value that contradicts it is REFUSED (naming both scopes);
a matching value or an unclassified plan composes; and the narrowing decision records
which scope it used.

Covers deliverables D1-D4 of
``doc/plans/truthful-signals/350-change-type-is-one-word-for-two-different-scopes``.
"""

import json
from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_reconcile'
)
cmd_compose = _mem.cmd_compose

# Silence the best-effort per-rule decision-log subprocess so the tests do not
# depend on a running executor.
_mem._log_decision = lambda *a, **kw: None


def _compose_ns(
    plan_id: str,
    change_type: str,
    *,
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_and_push: str | None = None,
) -> Namespace:
    if phase_6_steps is None:
        phase_6_steps = ','.join(_mem.DEFAULT_PHASE_6_STEPS)
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _seed_settled(plan_context, plan_id: str, change_type: str) -> None:
    """Seed ``status.metadata.change_type`` — the plan's settled classification."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'change_type': change_type}}, indent=2),
        encoding='utf-8',
    )


# =============================================================================
# D4(a) — the live shape: a plan settled as one type whose caller passes a
# deliverable's type is REFUSED, and the message names BOTH values.
# =============================================================================


def test_settled_vs_deliverable_change_type_is_refused_naming_both(plan_context):
    plan_id = 'reconcile-conflict'
    _seed_settled(plan_context, plan_id, 'bug_fix')
    # The observed instance: settled bug_fix, caller forwards the first deliverable's
    # verification. Compose must refuse rather than silently narrow the whole plan.
    result = cmd_compose(_compose_ns(plan_id, 'verification'))
    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'change_type_scope_conflict'
    # Both values named so the caller need not guess which side is wrong.
    assert 'bug_fix' in result['message']
    assert 'verification' in result['message']
    assert result['settled_change_type'] == 'bug_fix'
    assert result['supplied_change_type'] == 'verification'


# =============================================================================
# D4(b) — a MATCHING pair passes, and the narrowing records the settled (PLAN)
# scope it used.
# =============================================================================


def test_matching_change_type_composes_and_records_settled_scope(plan_context):
    plan_id = 'reconcile-match'
    _seed_settled(plan_context, plan_id, 'bug_fix')
    result = cmd_compose(_compose_ns(plan_id, 'bug_fix', scope_estimate='surgical'))
    assert result is not None
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'settled'
    assert result['effective_change_type'] == 'bug_fix'


# =============================================================================
# D4(c) — CONTROL: a plan with NO settled classification still composes (and the
# supplied value is recorded as the scope used). Without this control the fix
# would block every unclassified plan.
# =============================================================================


def test_no_settled_classification_still_composes(plan_context):
    plan_id = 'reconcile-unsettled'
    # No status.json seeded → no settled classification to reconcile against.
    result = cmd_compose(_compose_ns(plan_id, 'feature'))
    assert result is not None
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'supplied'
    assert result['effective_change_type'] == 'feature'


def test_status_without_change_type_key_still_composes(plan_context):
    """A status.json carrying metadata but no change_type is 'no settled classification'."""
    plan_id = 'reconcile-nochangetype'
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': 'standard'}}),
        encoding='utf-8',
    )
    result = cmd_compose(_compose_ns(plan_id, 'feature'))
    assert result is not None
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'supplied'


def test_malformed_status_json_degrades_to_no_settled(plan_context):
    """A corrupt status.json must not crash compose — it degrades to 'no settled classification'.

    The reconciliation read is fail-closed toward composing on the supplied value: an unreadable
    settled classification is treated as absent, not as a hard error.
    """
    plan_id = 'reconcile-malformed-status'
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text('{not valid json', encoding='utf-8')
    result = cmd_compose(_compose_ns(plan_id, 'feature'))
    assert result is not None
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'supplied'


# =============================================================================
# D4(d) / D3 — the narrowing decision names its scope, and carries its input.
# =============================================================================


def test_narrowing_decision_records_its_scope_and_input(plan_context):
    plan_id = 'reconcile-scope-record'
    _seed_settled(plan_context, plan_id, 'feature')
    result = cmd_compose(_compose_ns(plan_id, 'feature'))
    assert result is not None
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'settled'
    # The decision carries its input — the value it used and both scope candidates.
    assert result['effective_change_type'] == 'feature'
    assert result['settled_change_type'] == 'feature'
    assert result['supplied_change_type'] == 'feature'


def test_reconciliation_emits_auditable_decision_log_line(plan_context):
    """The narrowing input is written to the decision log so it can be audited later."""
    plan_id = 'reconcile-log'
    _seed_settled(plan_context, plan_id, 'bug_fix')
    captured: list[tuple[str, str]] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda pid, msg: captured.append((pid, msg))
    try:
        cmd_compose(_compose_ns(plan_id, 'bug_fix', scope_estimate='surgical'))
    finally:
        _mem._emit_decision_log = original
    recon = [msg for _pid, msg in captured if 'change_type reconciliation' in msg]
    assert recon, 'no change_type reconciliation decision-log line emitted'
    assert 'settled' in recon[0]
    assert 'bug_fix' in recon[0]


# =============================================================================
# D2 — the flag rename is a RENAME, not an alias: --plan-change-type is accepted,
# and the old --change-type spelling is rejected (no dual spelling survives).
# =============================================================================


def test_new_plan_change_type_flag_is_accepted(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-new-flag',
        '--plan-change-type',
        'feature',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
    )
    assert result.returncode == 0, f'compose failed: stderr={result.stderr!r}'
    data = result.toon()
    assert data['status'] == 'success'


# =============================================================================
# A settled classification OUTSIDE VALID_CHANGE_TYPES is UNUSABLE, not a
# conflicting scope. It degrades to "no settled classification", so compose falls
# through to the supplied value, and the discard is named in the decision log.
# =============================================================================

#: The non-canonical settled value the cases below seed — a plausible near-miss
#: rather than nonsense, because the defect being pinned was a real settled value
#: that no supplied value could ever equal.
_UNUSABLE_SETTLED = 'feature_breaking'


def test_unusable_settled_sweep_population_is_non_empty():
    """Guard the parametrized sweep below against a vacuous population.

    The sweep derives its cases from ``VALID_CHANGE_TYPES`` rather than a hand-listed
    copy, so an empty or renamed constant would silently reduce it to zero cases and
    still report green. Publishing the population here is what makes that visible.
    """
    assert _mem.VALID_CHANGE_TYPES, 'VALID_CHANGE_TYPES is empty — the sweep below is vacuous'
    assert _UNUSABLE_SETTLED not in _mem.VALID_CHANGE_TYPES


@pytest.mark.parametrize('supplied', _mem.VALID_CHANGE_TYPES)
def test_non_canonical_settled_never_conflicts_with_any_canonical_supplied(plan_context, supplied):
    """A non-canonical settled value composes against EVERY canonical supplied value.

    Reading the settled value verbatim fed it to the equality test in the
    reconciliation block, which then refused for every member of the vocabulary — so
    compose could not be satisfied by any argument the caller could pass. That is a
    defective classification, not a conflict between two scopes, and it must degrade
    to the supplied value instead of refusing.
    """
    slug = supplied.replace('_', '-')
    plan_id = f'reconcile-unusable-{slug}'
    _seed_settled(plan_context, plan_id, _UNUSABLE_SETTLED)
    result = cmd_compose(_compose_ns(plan_id, supplied))
    assert result is not None
    assert result.get('error') != 'change_type_scope_conflict'
    assert result['status'] == 'success'
    assert result['change_type_scope'] == 'supplied'
    assert result['effective_change_type'] == supplied


def test_unusable_settled_discard_is_named_in_the_decision_log(plan_context):
    """The discard is auditable: the log line names the value that was thrown away.

    Degrading to ``None`` makes "absent" and "unusable" indistinguishable in the
    read's return, so without this line a settled classification could be rejected
    with no record that it ever existed.
    """
    plan_id = 'reconcile-unusable-log'
    _seed_settled(plan_context, plan_id, _UNUSABLE_SETTLED)
    captured: list[tuple[str, str]] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda pid, msg: captured.append((pid, msg))
    try:
        cmd_compose(_compose_ns(plan_id, 'bug_fix'))
    finally:
        _mem._emit_decision_log = original
    discards = [msg for _pid, msg in captured if 'discarded unusable settled' in msg]
    assert discards, 'no discard decision-log line emitted for the unusable settled value'
    assert _UNUSABLE_SETTLED in discards[0]


def test_old_change_type_flag_is_rejected(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-old-flag',
        '--change-type',
        'feature',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
    )
    # argparse rejects the removed flag (exit 2), proving the rename is not an alias.
    # The error names the now-required --plan-change-type (argparse reports the missing
    # required option), confirming the old spelling no longer satisfies the parser.
    assert result.returncode != 0
    assert '--plan-change-type' in result.stderr
