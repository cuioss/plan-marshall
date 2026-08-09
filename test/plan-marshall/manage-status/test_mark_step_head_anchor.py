#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Fail-closed guard for the head-anchor obligation on a head-dependent ``done``.

``head_dependent: true`` declares that a step's verdict is computed against one
specific worktree HEAD. The obligation that follows — persist that SHA via
``--head-at-completion`` on the terminal ``done`` record — used to be *stated*
in prose and enforced nowhere, so a step could record ``done`` with no anchor
and nothing would notice. Two independent consumers break silently when it does:

* The dispatcher's re-entry check compares the live HEAD against the recorded
  SHA. With no SHA there is nothing to compare, so the record stands as green
  for a diff no check ever ran against.
* A step that re-fires across loop-back rounds scopes each round against the
  previous round's recorded SHA (``default:pre-submission-self-review`` passes it
  to its surfacer as ``--since-ref``). With no anchor the next round cannot
  define its delta and silently degrades to a full re-sweep.

These tests pin the refusal and its matched controls:

(a) A head-dependent ``done`` with NO anchor is refused, AND nothing is written.
    The write assertion is separate from the status assertion on purpose: a
    refusal that still persisted a partial record would satisfy the error check
    while leaving exactly the unanchored record the refusal exists to prevent.
(b) A head-dependent ``done` WITH an anchor is written — the positive control
    that keeps (a) from passing because the verb rejects everything.
(c) A NON-head-dependent ``done`` with no anchor is written — the negative
    control that keeps (a) from passing because the verb demands an anchor
    universally rather than only where the fact is declared.
(d) A head-dependent NON-``done`` outcome with no anchor is written — the
    obligation binds ``done`` alone, so a ``failed`` record stays writable.
(e) An unresolvable derivation WARNS rather than refusing. An unresolvable
    derivation must not manufacture an unsubstantiated refusal, and must not
    pass silently either.

**The step fixtures are DERIVED from the live frontmatter population, never
hardcoded**, and the population sizes are published by their own test. A
hardcoded step name would keep passing after that step stopped declaring the
fact, and a mis-swept or empty population would make every case above vacuously
green — which is precisely the defect class this plan exists to remove. The
derivation reuses the registry's OWN path (``find_implementors`` plus
``extension_discovery._read_frontmatter_fields``), so no second parser exists to
drift from the one the handler itself consults.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

import extension_discovery
from extension_discovery import find_implementors

from _step_key_canonical import canonicalize_step_key
from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_head_anchor_lifecycle'
)
_mark_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_mark_step.py', '_head_anchor_mark_step'
)
_status_core = load_script_module(
    'plan-marshall', 'manage-status', '_status_core.py', '_head_anchor_core'
)

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status

#: The ext-point whose implementors declare the fact under test.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the membership declaration.
_FACT_KEY = 'head_dependent'

#: A syntactically valid anchor. Its VALUE is never resolved by the handler —
#: the obligation is presence, not reachability — so a fixed literal is honest
#: here in a way a hardcoded step name would not be.
_ANCHOR = 'a' * 40


def _partition_steps() -> tuple[list[str], list[str]]:
    """Split the live finalize-step population by the ``head_dependent`` fact.

    Returns ``(head_dependent, non_head_dependent)`` as canonicalized step ids.
    Both halves are derived from discovery, so a step that gains or drops the
    declaration moves between them with no edit here. Ids are canonicalized
    because discovery names a built-in step ``default:{bare}`` while the handler
    compares against the bare canonical key.
    """
    head_dependent: list[str] = []
    non_head_dependent: list[str] = []
    for record in find_implementors(_EXT_POINT):
        fields = extension_discovery._read_frontmatter_fields(
            Path(str(record.get('path', ''))), (_FACT_KEY,)
        )
        step_id = canonicalize_step_key(str(record.get('name', '')))
        if not step_id:
            continue
        if bool(fields.get(_FACT_KEY, False)):
            head_dependent.append(step_id)
        else:
            non_head_dependent.append(step_id)
    return sorted(set(head_dependent)), sorted(set(non_head_dependent))


def _a_head_dependent_step() -> str:
    """One representative member of the live head-dependent population."""
    head_dependent, _ = _partition_steps()
    assert head_dependent, (
        'The head-dependent population is EMPTY, so every refusal assertion in '
        'this module would pass vacuously. Either no step doc declares '
        f'{_FACT_KEY}: true, or find_implementors({_EXT_POINT!r}) discovered no '
        'step docs at all.'
    )
    return head_dependent[0]


def _a_non_head_dependent_step() -> str:
    """One representative member of the live NON-head-dependent population."""
    _, non_head_dependent = _partition_steps()
    assert non_head_dependent, (
        'The non-head-dependent population is EMPTY, so the negative control '
        'below cannot discriminate: with nothing to contrast against, a verb '
        'that demanded an anchor universally would still read as green.'
    )
    return non_head_dependent[0]


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Head Anchor Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _args(
    plan_id: str,
    step: str,
    outcome: str,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase='6-finalize',
        step=step,
        outcome=outcome,
        force=False,
        display_detail=None,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
        fact=None,
    )


def _recorded_steps(plan_id: str) -> dict:
    """The persisted ``6-finalize`` step records, or an empty dict."""
    persisted: dict = read_status(plan_id)
    metadata: dict = persisted.get('metadata', {})
    phase_steps: dict = metadata.get('phase_steps', {})
    recorded: dict = phase_steps.get('6-finalize', {})
    return recorded


# ---------------------------------------------------------------------------
# Population publication — the anti-vacuity foundation
# ---------------------------------------------------------------------------


def test_both_populations_are_non_empty_and_published():
    """Publish the derived population sizes both halves of the guard rest on.

    Checked FIRST and on its own: every assertion below draws its fixture step
    from one of these two populations, so an empty or mis-swept derivation would
    make them green without testing anything. Reporting the sizes in the failure
    message is what turns a future regression into a diagnosable one rather than
    a silent re-vacuuming.
    """
    head_dependent, non_head_dependent = _partition_steps()

    assert head_dependent, (
        f'Derived head-dependent population is EMPTY (non-head-dependent: '
        f'{len(non_head_dependent)}). Every refusal assertion would be vacuous.'
    )
    assert non_head_dependent, (
        f'Derived non-head-dependent population is EMPTY (head-dependent: '
        f'{len(head_dependent)}). The negative control would be vacuous.'
    )
    # The partition is over ONE discovered population, so the two halves must be
    # disjoint — an id in both would mean the fact was read two different ways.
    assert not set(head_dependent) & set(non_head_dependent), (
        f'A step id landed in BOTH halves of the partition: '
        f'{sorted(set(head_dependent) & set(non_head_dependent))}'
    )


# ---------------------------------------------------------------------------
# (a) the refusal, and the nothing-was-written half of it
# ---------------------------------------------------------------------------


def test_head_dependent_done_without_anchor_is_refused(plan_context):
    plan_id = 'head-anchor-refused'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    result = cmd_mark_step_done(_args(plan_id, step, 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'missing_head_at_completion'
    assert result['step'] == step
    # The message must name the missing field, so the caller can act on it
    # without reading the handler.
    assert 'head-at-completion' in result['message']


def test_refused_call_writes_nothing(plan_context):
    """The refusal is total — no partial record survives it.

    Asserted separately from the status check above because the two can diverge:
    a handler that returned the error AFTER persisting would satisfy the status
    assertion while leaving exactly the unanchored record the refusal exists to
    prevent.
    """
    plan_id = 'head-anchor-refused-no-write'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    cmd_mark_step_done(_args(plan_id, step, 'done'))

    assert _recorded_steps(plan_id) == {}


# ---------------------------------------------------------------------------
# (b) positive control — the anchor makes the same call succeed
# ---------------------------------------------------------------------------


def test_head_dependent_done_with_anchor_is_written(plan_context):
    plan_id = 'head-anchor-accepted'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    result = cmd_mark_step_done(
        _args(plan_id, step, 'done', head_at_completion=_ANCHOR)
    )

    assert result['status'] == 'success'
    assert result['head_at_completion'] == _ANCHOR
    assert _recorded_steps(plan_id)[step]['head_at_completion'] == _ANCHOR


# ---------------------------------------------------------------------------
# (c) negative control — the obligation is scoped to the declaring population
# ---------------------------------------------------------------------------


def test_non_head_dependent_done_without_anchor_is_written(plan_context):
    """A step that does NOT declare the fact keeps recording without an anchor.

    Without this control, a handler that demanded an anchor from EVERY step
    would satisfy the refusal test while breaking every other finalize step.
    """
    plan_id = 'head-anchor-not-required'
    _make_plan(plan_id)
    step = _a_non_head_dependent_step()

    result = cmd_mark_step_done(_args(plan_id, step, 'done'))

    assert result['status'] == 'success'
    assert step in _recorded_steps(plan_id)


def test_step_outside_the_finalize_population_is_written(plan_context):
    """A phase-5 step matches no finalize-step implementor and is unaffected.

    ``mark-step-done`` records steps for every phase. A step simply absent from
    the finalize-step population is a RESOLVED "not head-dependent", not an
    unresolved derivation, so it neither refuses nor warns.
    """
    plan_id = 'head-anchor-foreign-step'
    _make_plan(plan_id)

    result = cmd_mark_step_done(_args(plan_id, 'some-phase-5-step', 'done'))

    assert result['status'] == 'success'
    assert 'warning' not in result


# ---------------------------------------------------------------------------
# (d) the obligation binds `done` alone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('outcome', ['failed', 'skipped'])
def test_head_dependent_non_done_outcome_without_anchor_is_written(
    plan_context, outcome
):
    """Only a terminal ``done`` carries the obligation.

    A ``failed`` record in particular MUST stay writable without an anchor:
    forwarding one there is permitted (the next round reads it as its delta
    anchor) but never required, so refusing it would break the loop-back path
    this plan depends on.
    """
    plan_id = f'head-anchor-{outcome}'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    result = cmd_mark_step_done(_args(plan_id, step, outcome))

    assert result['status'] == 'success'
    assert step in _recorded_steps(plan_id)


# ---------------------------------------------------------------------------
# (e) an unresolvable derivation warns rather than refusing
# ---------------------------------------------------------------------------


def test_unresolvable_derivation_warns_and_still_writes(plan_context, monkeypatch):
    """An empty discovery result is diagnosable, not a refusal.

    The failure mode is asymmetric by design: the guard fails CLOSED only when it
    positively derived ``head_dependent: true``. When the derivation machinery
    cannot answer at all, refusing would manufacture an unsubstantiated verdict,
    so the record is written and carries the reason instead.
    """
    plan_id = 'head-anchor-underivable'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    monkeypatch.setattr(extension_discovery, 'find_implementors', lambda _ext: [])

    result = cmd_mark_step_done(_args(plan_id, step, 'done'))

    assert result['status'] == 'success'
    assert 'warning' in result
    assert 'no finalize-step implementors' in result['warning']
    assert step in _recorded_steps(plan_id)


def test_ordinary_success_carries_no_warning_key(plan_context):
    """The warning is omitted entirely when the derivation resolved.

    Pairs with the case above: without it, a handler that attached a warning to
    every record would satisfy the warning assertion while making the field
    meaningless.
    """
    plan_id = 'head-anchor-no-warning'
    _make_plan(plan_id)
    step = _a_head_dependent_step()

    result = cmd_mark_step_done(
        _args(plan_id, step, 'done', head_at_completion=_ANCHOR)
    )

    assert result['status'] == 'success'
    assert 'warning' not in result
