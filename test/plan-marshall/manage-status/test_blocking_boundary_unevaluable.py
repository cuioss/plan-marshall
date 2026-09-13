#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Characterization tests for the UNEVALUABLE branch of the finalize completion boundary.

``_cmd_lifecycle._finalize_findings_refusal`` has three outcomes, and only two of
them were pinned anywhere: the raise (a pending actionable finding refuses the
completion) and the clean zero (the completion proceeds). The third — the
``if blocking is None:`` branch, reached when
``_invariants.assert_finalize_findings_clean`` could not evaluate the findings
state at all (executor unreachable / partial query failure) — had no test, so the
disposition it encodes was decided by whichever code happened to be there.

⚠ **These tests PIN today's behaviour; they do not ENDORSE it.** Today the
completion boundary fails **OPEN** on an unevaluable query: both completion verbs
(``cmd_transition --completed 6-finalize`` and ``cmd_archive``) proceed, with a
WARNING decision-log envelope as the only trace, on the stated rationale that a
degenerate context with no reachable findings subsystem must not strand a
legitimate completion, and that the fail-CLOSED handling belongs to the pre-merge
``findings-check`` gate where the executor is guaranteed present.

Whether fail-open is the right disposition for this boundary is an open operator
question (recorded as a proposal, not settled here): the branch cannot distinguish
"no findings subsystem in this context" from "the findings subsystem broke while
holding a blocking finding", and the second is exactly the state the gate exists
to catch. A change to fail-closed is a deliberate contract decision — these tests
are what makes that change VISIBLE rather than silent, so a future edit that flips
the disposition fails here and is read as the decision it is.

The negative control is what gives the pin its meaning: a CLEAN plan also
proceeds, so "proceeded" alone does not identify this branch. The WARNING envelope
is the only observable that separates "evaluated, and clean" from "never
evaluated", and it is asserted present on the unevaluable path and ABSENT on the
clean one.
"""

import json
from argparse import Namespace
from pathlib import Path

import _invariants as _inv
import pytest
from _manage_status_transition_fixtures import (
    _lifecycle,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
    cmd_transition,
)


@pytest.fixture
def _unevaluable_finding_queries(monkeypatch):
    """Make BOTH pending-findings query paths report "could not evaluate".

    ``_capture_pending_findings_blocking_count`` returns ``None`` as soon as any
    single actionable-type query returns ``None``, so stubbing one would be
    enough to reach the branch — but only for as long as that type keeps its
    position in ``_ACTIONABLE_FINDING_TYPES``. Both paths are stubbed so the
    fixture reaches the unevaluable state regardless of the tuple's order and of
    which type the aggregation happens to visit first.

    Patched on ``_inv`` — the SAME module object ``assert_finalize_findings_clean``
    resolves these helpers as module globals — per the MODULE IDENTITY note in
    ``_manage_status_transition_fixtures``.
    """
    monkeypatch.setattr(_inv, '_query_pending_count_for_type', lambda _pid, _ft: None)
    monkeypatch.setattr(_inv, '_query_pending_qgate_count_aggregated', lambda _pid: None)


@pytest.fixture
def _captured_log_entries(monkeypatch):
    """Capture ``_cmd_lifecycle``'s log_entry calls as ``(kind, plan_id, level, message)``.

    Patched on the lifecycle module object the fixtures export, which is the one
    whose ``_finalize_findings_refusal`` resolves ``log_entry`` as a module global.
    """
    entries: list[tuple] = []
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *args: entries.append(args))
    return entries


def _unevaluable_warnings(entries: list[tuple]) -> list[tuple]:
    """The WARNING decision entries the unevaluable branch emits."""
    return [e for e in entries if e[0] == 'decision' and e[2] == 'WARNING' and 'unevaluable' in e[3]]


def test_transition_completing_finalize_proceeds_when_findings_unevaluable(
    plan_context, _unevaluable_finding_queries, _captured_log_entries
):
    """PIN: completing 6-finalize proceeds (fail-OPEN) when the findings state
    could not be evaluated, emitting exactly one WARNING decision envelope.

    Pins current behaviour. A future fail-closed decision SHOULD break this test.
    """
    plan_id = 'unevaluable-boundary-transition'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result is not None
    assert result['status'] == 'success', (
        f'Today the completion boundary fails OPEN on an unevaluable findings '
        f'query — the transition must proceed. Got {result!r}. If this changed '
        f'deliberately to fail-closed, that is a contract decision: update this '
        f'characterization test and record the decision, do not soften the gate.'
    )
    assert result['completed_phase'] == '6-finalize'

    persisted = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert persisted['current_phase'] == 'complete', (
        'The completion write must have happened — an unevaluable query does not '
        f'skip write_status today. Got current_phase={persisted["current_phase"]!r}.'
    )

    warnings = _unevaluable_warnings(_captured_log_entries)
    assert len(warnings) == 1, (
        f'The WARNING envelope is the ONLY trace that the gate never evaluated; '
        f'without it an unevaluable completion is indistinguishable from a clean '
        f'one. Expected exactly 1, got {len(warnings)}: {_captured_log_entries!r}'
    )
    assert warnings[0][1] == plan_id
    assert 'findings-check' in warnings[0][3], (
        'The envelope must name the pre-merge findings-check gate as the owner of '
        f'the fail-closed path. Got: {warnings[0][3]!r}'
    )


def test_archive_proceeds_when_findings_unevaluable(plan_context, _unevaluable_finding_queries, _captured_log_entries):
    """PIN: a normal-completion archive (no --reason, still in 6-finalize) proceeds
    (fail-OPEN) when the findings state could not be evaluated, emitting exactly
    one WARNING decision envelope.

    Pins current behaviour. A future fail-closed decision SHOULD break this test.
    """
    plan_id = 'unevaluable-boundary-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result is not None
    assert result['status'] == 'success', (
        f'Today the archive completion boundary fails OPEN on an unevaluable '
        f'findings query — the archive must proceed. Got {result!r}.'
    )
    assert 'archived_to' in result, f'the plan directory must have been moved: {result!r}'
    assert (Path(result['archived_to']) / 'status.json').exists()
    assert not plan_context.plan_dir_for(plan_id).exists(), 'the live plan directory must be gone after the move'

    warnings = _unevaluable_warnings(_captured_log_entries)
    assert len(warnings) == 1, (
        f'Expected exactly one unevaluable WARNING envelope from the archive path, '
        f'got {len(warnings)}: {_captured_log_entries!r}'
    )
    assert warnings[0][1] == plan_id


@pytest.mark.parametrize('verb', ['transition', 'archive'])
def test_clean_findings_proceed_without_the_unevaluable_warning(plan_context, _captured_log_entries, monkeypatch, verb):
    """NEGATIVE control: a CLEAN plan proceeds through both completion verbs too —
    so "it proceeded" does NOT identify the unevaluable branch.

    This is what makes the two tests above a pin rather than a tautology: the
    WARNING envelope, not the success, is the observable that distinguishes
    "evaluated, and found nothing blocking" from "never evaluated at all".
    """
    _stub_finding_queries(monkeypatch, {})
    plan_id = f'evaluable-clean-{verb}'
    _seed_finalize_phase_plan(plan_id)

    if verb == 'transition':
        result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))
    else:
        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result is not None
    assert result['status'] == 'success'
    assert _unevaluable_warnings(_captured_log_entries) == [], (
        'A clean, EVALUATED findings state must emit no unevaluable warning — '
        'otherwise the envelope cannot discriminate the two ways a completion '
        f'proceeds. Got: {_captured_log_entries!r}'
    )
