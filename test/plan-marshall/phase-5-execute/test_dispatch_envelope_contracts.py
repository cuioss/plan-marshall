#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Closure tests pinning the PLAN-05 dispatch-envelope contracts.

One test per contract, each grounded in its lesson evidence:

* (a) Step-owned dispatch body contract (lesson 2026-09-17-19-004, precursor
  2026-09-03-07-001): ``operations.md`` declares ``requires_prompt_fields``
  per dispatch pattern, states the generic-deferral rule, and names the
  author/verifier choreography.
* (b) Fix-task loop-back dispatch envelope (lesson 2026-09-17-19-005, folded
  inbox evidence git-branch-mechanics-001 item 6): the seam states which
  fields are carried vs omitted on loop-back re-entry, and a fix task
  arriving with a null envelope is re-assigned at loop-back entry instead of
  executing invisible to the envelope-filtered executor.
* (c) ``loop_back_target`` contract (lesson 2026-09-17-19-006, triage.md
  Step 7 computation rule): ``operations.md`` requires ``loop_back_target``
  on every ``loop_back`` return, omits it on ``success``, and matches the
  ``5-execute`` vs ``6-finalize`` computation rule verbatim in behaviour.
"""

from __future__ import annotations

from pathlib import Path

from inject_project_dir import (
    LOOP_BACK_CARRIED_FIELDS,
    LOOP_BACK_OMITTED_FIELDS,
    inject_project_dir,
    resolve_loop_back_envelope,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATIONS_MD = (
    REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-5-execute'
    / 'standards'
    / 'operations.md'
)

PLAN_ID = 'dispatch-envelope-closure'


def _operations_text() -> str:
    """Read the phase-5 operations reference under test."""
    return OPERATIONS_MD.read_text(encoding='utf-8')


def test_step_owned_body_declares_requires_prompt_fields_and_defers():
    """Contract (a): step-owned bodies own their fields; generic defers."""
    # Arrange — the operations reference as shipped.
    text = _operations_text()

    # Act — collect the contract sentences the deliverable requires.
    has_section = '## Step-owned dispatch bodies' in text
    has_field_name = 'requires_prompt_fields' in text
    has_deferral = 'defers to that body' in text
    has_choreography = 'Author/verifier choreography' in text

    # Assert — every element of the D1 contract is stated.
    assert has_section, 'operations.md must declare the Step-owned dispatch bodies section'
    assert has_field_name, 'each dispatch pattern must declare requires_prompt_fields'
    assert has_deferral, 'generic dispatch must defer to the step-owned body when one is declared'
    assert has_choreography, 'author/verifier choreography must be named for each step-owned body'


def test_loop_back_envelope_states_fields_and_null_envelope_reassigns():
    """Contract (b): carried/omitted envelope fields plus null-envelope rule."""
    # Arrange — the stated envelope vocabulary at the seam.
    # Act — read the carried vs omitted field sets.
    carried = set(LOOP_BACK_CARRIED_FIELDS)
    omitted = set(LOOP_BACK_OMITTED_FIELDS)

    # Assert — the D2 carried/omitted contract is stated ...
    assert {'plan_id', 'envelope_id', 'worktree_materialized'} <= carried
    assert 'project-dir' in omitted
    assert carried.isdisjoint(omitted), 'no field may be both carried and omitted'

    # ... and the null-envelope execution rule is enforced: a fix task
    # arriving with envelope_id None re-runs the envelope assignment ...
    null_result = resolve_loop_back_envelope(PLAN_ID, None)
    assert null_result['action'] == 'assign'
    assert null_result['assignment_required'] is True

    # ... while an assigned envelope carries its fields through ...
    assigned_result = resolve_loop_back_envelope(PLAN_ID, 1, worktree_materialized=True)
    assert assigned_result['action'] == 'carry'
    assert assigned_result['assignment_required'] is False
    carried_fields = assigned_result['carried_fields']
    assert isinstance(carried_fields, dict)
    assert carried_fields['plan_id'] == PLAN_ID
    assert carried_fields['envelope_id'] == 1

    # ... and the injection seam itself is unregressed: Bucket B commands
    # still get exactly one --plan-id and legacy --project-dir still passes
    # through untouched.
    rewritten, injected = inject_project_dir(
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests"',
        PLAN_ID,
    )
    assert injected is True
    assert rewritten.count('--plan-id') == 1
    legacy = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --project-dir /some/explicit/worktree --command-args "module-tests"'
    )
    passthrough, passthrough_injected = inject_project_dir(legacy, PLAN_ID)
    assert passthrough_injected is False
    assert passthrough == legacy


def test_loop_back_target_required_on_loop_back_and_omitted_on_success():
    """Contract (c): loop_back_target granularity matches triage.md Step 7."""
    # Arrange — the operations reference as shipped.
    text = _operations_text()

    # Act — collect the contract sentences the deliverable requires.
    has_section = 'loop_back_target' in text
    has_required = 'MUST carry `loop_back_target`' in text
    has_omitted = 'MUST omit it' in text
    has_computation = 'fix_tasks_created > 0' in text and 'overflow_deferred > 0' in text
    has_five_execute = '"5-execute"' in text
    has_six_finalize = '"6-finalize"' in text
    has_forwarding = '--loop-back-target' in text

    # Assert — the D3 contract mirrors the triage.md Step 7 computation rule:
    # REQUIRED on every loop_back return, omitted on success, 5-execute when
    # fix_tasks_created > 0 OR overflow_deferred > 0 else 6-finalize,
    # forwarded verbatim to mark-step-done.
    assert has_section, 'operations.md must document the loop_back_target contract'
    assert has_required, 'loop_back_target must be REQUIRED on every loop_back return'
    assert has_omitted, 'loop_back_target must be omitted on success outcomes'
    assert has_computation, 'the 5-execute vs 6-finalize computation rule must be stated'
    assert has_five_execute and has_six_finalize, 'both granularity tiers must be named'
    assert has_forwarding, 'callers must forward the field verbatim to mark-step-done'
