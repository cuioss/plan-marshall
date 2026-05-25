#!/usr/bin/env python3
"""Regression tests for the body-level Signal Gate guard in
``lessons-capture.md``.

The guard is implemented as a documented workflow section in the
markdown body of
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md``,
not as a Python helper. The dispatcher reads the workflow doc and
executes the documented commands in sequence, so these tests assert the
structural shape of the markdown contract that the dispatcher relies on:

- The Signal Gate section exists, sits BEFORE any ``Task:`` dispatch and
  BEFORE the ``Skill: plan-marshall:manage-lessons`` load.
- All three signal sources are named (pending Q-Gate findings,
  ``automated-review`` step outcome, script-failure clusters).
- The all-zero skip branch emits the canonical ``mark-step-done`` call
  with ``--outcome skipped`` and ``--display-detail "no lesson-bearing
  signals"``.
- The continue branch is explicitly documented so the dispatcher knows
  the guard does NOT short-circuit on non-zero signals.
- The intro prose no longer claims unconditional dispatch and instead
  references the conditional Signal Gate.
- The ``Mark Step Complete`` section carries a Branch C example for the
  skipped outcome.

These assertions are deliberately structural — they catch drift between
the workflow narrative and the gate's behavioural contract without
re-implementing the gate logic in Python (which would itself become a
divergence surface).
"""

from pathlib import Path

_WORKFLOW_PATH = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'lessons-capture.md'
)


def _read_workflow() -> str:
    """Read the workflow doc body once per test for substring assertions."""
    return _WORKFLOW_PATH.read_text(encoding='utf-8')


class TestSignalGateStructure:
    """Structural assertions on the Signal Gate section in
    ``lessons-capture.md``."""

    def test_signal_gate_section_present(self) -> None:
        """The workflow body MUST declare a ``### Signal Gate`` section
        so the dispatcher can locate the guard."""
        body = _read_workflow()
        assert '### Signal Gate' in body, (
            'lessons-capture.md must declare a "### Signal Gate" '
            'section housing the body-level early-return guard'
        )

    def test_signal_gate_precedes_manage_lessons_load(self) -> None:
        """The Signal Gate MUST sit BEFORE the
        ``Skill: plan-marshall:manage-lessons`` directive so the LLM
        path is never loaded on the skip branch."""
        body = _read_workflow()
        gate_idx = body.find('### Signal Gate')
        load_idx = body.find('Skill: plan-marshall:manage-lessons')
        assert gate_idx != -1 and load_idx != -1, (
            'lessons-capture.md must contain both the Signal Gate '
            'section and the manage-lessons Skill load'
        )
        assert gate_idx < load_idx, (
            'Signal Gate section must precede the '
            '"Skill: plan-marshall:manage-lessons" load so the '
            'skip branch never loads the LLM-bearing skill'
        )

    def test_signal_gate_precedes_three_step_add_flow(self) -> None:
        """The Signal Gate MUST sit BEFORE the three-step add-flow
        headings so the dispatcher does not enter the add flow on the
        skip branch."""
        body = _read_workflow()
        gate_idx = body.find('### Signal Gate')
        step1_idx = body.find('### Step 1 — Allocate the lesson file')
        assert gate_idx != -1 and step1_idx != -1, (
            'lessons-capture.md must contain both the Signal Gate '
            'section and the three-step add flow'
        )
        assert gate_idx < step1_idx, (
            'Signal Gate section must precede the three-step add '
            'flow (Step 1 — Allocate the lesson file)'
        )


class TestSignalGateSourcesNamed:
    """The Signal Gate MUST explicitly name all three signal sources so
    the dispatcher knows which counts to read."""

    def test_qgate_findings_signal_named(self) -> None:
        """Signal 1 — pending Q-Gate findings via
        ``manage-findings qgate list --resolution pending``."""
        body = _read_workflow()
        assert 'qgate list --plan-id {plan_id} --resolution pending' in body, (
            'Signal Gate must invoke '
            '"manage-findings qgate list --resolution pending" '
            'to read pending Q-Gate finding counts'
        )
        assert 'total_count' in body, (
            'Signal Gate must read the "total_count" field from the '
            'manage-findings qgate list TOON output'
        )

    def test_automated_review_signal_named(self) -> None:
        """Signal 2 — ``automated-review`` step outcome via
        ``manage-status read``."""
        body = _read_workflow()
        assert 'automated-review' in body, (
            'Signal Gate must name the "automated-review" step as a '
            'signal source'
        )
        assert 'manage-status' in body and 'read --plan-id {plan_id}' in body, (
            'Signal Gate must read the automated-review step outcome '
            'via manage-status read'
        )

    def test_script_failure_clusters_signal_named(self) -> None:
        """Signal 3 — script-failure clusters via
        ``manage-logging read --type work`` scanning ``[FAILED]``."""
        body = _read_workflow()
        assert 'manage-logging' in body and '--type work' in body, (
            'Signal Gate must read the work log via '
            'manage-logging read --type work'
        )
        assert '[FAILED]' in body, (
            'Signal Gate must scan for "[FAILED]" markers in the work '
            'log to identify script-failure clusters'
        )


class TestSignalGateSkipBranch:
    """The all-zero skip branch MUST emit the canonical
    ``mark-step-done`` call so the phase_steps_complete invariant is
    satisfied even when no LLM dispatch fires."""

    _EXPECTED_DETAIL = 'no lesson-bearing signals'

    def test_skip_branch_uses_skipped_outcome(self) -> None:
        """The skip branch MUST use ``--outcome skipped`` so it is
        distinguishable from a normal advisory pass-through (Branch B
        uses ``--outcome done``)."""
        body = _read_workflow()
        assert '--outcome skipped' in body, (
            'Signal Gate skip branch must invoke mark-step-done with '
            '"--outcome skipped" to distinguish it from Branch B '
            '("no lessons recorded" with --outcome done)'
        )

    def test_skip_branch_uses_canonical_display_detail(self) -> None:
        """The skip branch MUST carry the exact display-detail string
        ``"no lesson-bearing signals"`` — downstream consumers may grep
        for this token to identify a Signal Gate short-circuit."""
        body = _read_workflow()
        token = f'--display-detail "{self._EXPECTED_DETAIL}"'
        assert token in body, (
            'Signal Gate skip branch must carry the canonical '
            'display-detail string ' + repr(self._EXPECTED_DETAIL)
        )

    def test_skip_branch_does_not_load_manage_lessons(self) -> None:
        """The skip branch MUST explicitly state that
        ``manage-lessons`` is not loaded and the three-step add flow
        is not entered."""
        body = _read_workflow()
        assert 'Do NOT load `manage-lessons`' in body, (
            'Signal Gate skip branch must state "Do NOT load '
            '`manage-lessons`" so the dispatcher does not pre-load '
            'the LLM-bearing skill on the skip path'
        )

    def test_skip_branch_returns_zero_lessons(self) -> None:
        """The skip branch MUST return ``lessons_recorded: 0``."""
        body = _read_workflow()
        assert 'lessons_recorded: 0' in body, (
            'Signal Gate skip branch must return '
            '"lessons_recorded: 0" in the TOON output'
        )


class TestSignalGateContinueBranch:
    """The continue branch MUST be explicitly documented so the
    dispatcher knows the body proceeds into the add flow on any
    non-zero signal."""

    def test_continue_branch_documented(self) -> None:
        """The doc MUST name a "Continue branch" so the dispatcher's
        non-zero-signal path is explicit, not implicit."""
        body = _read_workflow()
        assert 'Continue branch' in body, (
            'lessons-capture.md must explicitly document the '
            '"Continue branch" so non-zero-signal handling is not '
            'left implicit'
        )

    def test_continue_branch_proceeds_to_manage_lessons(self) -> None:
        """The continue branch MUST reference proceeding to the
        ``Skill: plan-marshall:manage-lessons`` load below."""
        body = _read_workflow()
        # The wording is intentionally checked on a phrase rather than
        # a full sentence so prose tightening does not break the test.
        assert 'proceed to the' in body and 'manage-lessons' in body, (
            'Continue branch must reference proceeding into the '
            'manage-lessons Skill load below'
        )


class TestIntroProseReflectsConditionalGate:
    """The intro prose MUST no longer claim unconditional dispatch and
    MUST instead describe the conditional Signal Gate."""

    def test_no_unconditional_dispatch_when_manifested_claim(self) -> None:
        """The legacy claim "Unconditional dispatch when manifested"
        MUST be replaced — it contradicts the body-level guard."""
        body = _read_workflow()
        assert 'Unconditional dispatch when manifested' not in body, (
            'lessons-capture.md must no longer claim "Unconditional '
            'dispatch when manifested" — the body-level Signal Gate '
            'makes the dispatch conditional'
        )

    def test_no_no_skip_conditional_branching_claim(self) -> None:
        """The legacy claim "no skip-conditional branching at this
        layer" MUST be removed — the Signal Gate IS that branching."""
        body = _read_workflow()
        assert 'no skip-conditional branching at this layer' not in body, (
            'lessons-capture.md must no longer claim there is "no '
            'skip-conditional branching at this layer" — the Signal '
            'Gate provides exactly that branching'
        )

    def test_intro_describes_conditional_dispatch(self) -> None:
        """The intro MUST describe the conditional shape so the
        dispatcher narrative matches the body."""
        body = _read_workflow()
        # Either label is acceptable as long as the conditional shape
        # is named explicitly in prose.
        markers = (
            'Conditional dispatch based on signal presence',
            'body-level skip-conditional branching',
        )
        assert any(marker in body for marker in markers), (
            'Intro prose must describe the conditional Signal Gate '
            'shape; expected one of: ' + repr(markers)
        )


class TestBranchCExampleAdded:
    """The Mark Step Complete section MUST surface a Branch C example
    so the skipped outcome is a first-class output."""

    def test_branch_c_example_present(self) -> None:
        """A "Branch C" example MUST exist documenting the skipped
        outcome with the canonical display-detail."""
        body = _read_workflow()
        assert 'Branch C' in body, (
            'Mark Step Complete section must add a Branch C example '
            'covering the Signal Gate skipped outcome'
        )

    def test_output_contract_lists_no_lesson_bearing_signals(self) -> None:
        """The Output section MUST include the Signal Gate
        display-detail variant so the contract is exhaustive."""
        body = _read_workflow()
        assert 'no lesson-bearing signals' in body, (
            'Output section must include the "no lesson-bearing '
            'signals" display-detail variant so the contract is '
            'exhaustive'
        )
