#!/usr/bin/env python3
"""Tests for the triage workflow's loop_back_target granularity classification.

The triage workflow (`plan-marshall/workflow/triage.md` § Step 7 "Loop-back
signalling and granularity classification") owns the rule that maps each
disposition type to one of two `loop_back_target` values:

- `5-execute` — fix-task-required dispositions (FIX with `fix_tasks_created > 0`,
  `overflow_deferred > 0`).
- `6-finalize` — inline-fixable dispositions (SUPPRESS, narrow-rationale
  ACCEPT, single-annotation FIX).

The classification logic itself lives in markdown (consumed by the LLM core);
this test pins the contract by asserting that the classification table is
present in `triage.md` and enumerates the three canonical disposition
shapes, AND that the workflow's Output TOON shape declares
`loop_back_target` as a required field on every `status: loop_back` return.

Combined with the four manage-status `--loop-back-target` validation tests
in `test/plan-marshall/manage-status/test_manage_status.py`, this gives
end-to-end coverage of the hybrid loopback contract: the triage workflow
emits the field, the persistence layer validates it, and the dispatcher
hook (covered by `test_phase_6_manifest_executor.py`) routes on it.
"""

from pathlib import Path

_TRIAGE_MD = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'triage.md'
)


class TestTriageGranularityClassification:
    """Three-disposition classification rule for loop_back_target."""

    def test_triage_md_exists(self) -> None:
        """Sanity check — the workflow file must exist before any other
        assertion is meaningful."""
        assert _TRIAGE_MD.is_file(), (
            f'Expected triage.md at {_TRIAGE_MD} — the loop_back_target '
            'classification rule depends on this file existing.'
        )

    def test_triage_md_documents_loop_back_target_field(self) -> None:
        """`triage.md` MUST mention `loop_back_target` by name in Step 7
        so that downstream call sites (automated-review.md,
        sonar-roundtrip.md) know the field is part of the workflow's
        return contract."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        assert 'loop_back_target' in text, (
            'triage.md must reference loop_back_target by name in the '
            'Step 7 classification rule and Output TOON shape.'
        )

    def test_triage_md_documents_5_execute_target_for_fix_task_required(self) -> None:
        """Disposition 1: FIX with `fix_tasks_created > 0` → `5-execute`."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        # The classification table or rule prose must mention both halves of
        # the rule: the trigger condition and the resulting target value.
        assert 'fix_tasks_created' in text, (
            'triage.md must reference fix_tasks_created in the granularity '
            'classification rule.'
        )
        assert '5-execute' in text, (
            'triage.md must mention 5-execute as a loop_back_target value.'
        )

    def test_triage_md_documents_5_execute_target_for_overflow(self) -> None:
        """Disposition 2: `overflow_deferred > 0` → `5-execute`."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        assert 'overflow_deferred' in text, (
            'triage.md must reference overflow_deferred in the granularity '
            'classification rule.'
        )

    def test_triage_md_documents_6_finalize_target_for_inline_fixable(self) -> None:
        """Disposition 3: SUPPRESS / narrow ACCEPT / single-annotation FIX
        (no fix-task allocation, no overflow) → `6-finalize`."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        assert '6-finalize' in text, (
            'triage.md must mention 6-finalize as a loop_back_target value '
            'for the inline-fixable granularity tier.'
        )
        # The inline-fixable tier mentions SUPPRESS and ACCEPT explicitly.
        text_lower = text.lower()
        assert 'suppress' in text_lower, (
            'triage.md must mention SUPPRESS as part of the inline-fixable '
            'classification.'
        )
        assert 'accept' in text_lower, (
            'triage.md must mention ACCEPT as part of the inline-fixable '
            'classification.'
        )

    def test_triage_md_output_block_declares_loop_back_target(self) -> None:
        """The Output TOON block in triage.md MUST declare
        `loop_back_target` as a field on `status: loop_back` returns —
        downstream callers (automated-review.md / sonar-roundtrip.md) MUST
        be able to read the field from the workflow's return TOON."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        # Locate the Output section.
        assert '## Output' in text, (
            'triage.md must declare an Output section.'
        )
        output_idx = text.index('## Output')
        # The next section header (or end of file) bounds the Output block.
        next_section_idx = text.find('\n## ', output_idx + len('## Output'))
        if next_section_idx == -1:
            next_section_idx = len(text)
        output_block = text[output_idx:next_section_idx]
        assert 'loop_back_target' in output_block, (
            'triage.md Output block must declare loop_back_target as a '
            'returned field — downstream callers read this from the '
            'workflow\'s return TOON to forward it to mark-step-done.'
        )

    def test_triage_md_documents_computation_rule(self) -> None:
        """The classification table must be supplemented by an explicit
        computation rule that resolves ambiguous mixed cases — when ANY
        fix-task-required disposition fires, target=5-execute, else
        target=6-finalize."""
        text = _TRIAGE_MD.read_text(encoding='utf-8')
        # The computation rule mentions both branches explicitly.
        assert 'Computation rule' in text or 'computation rule' in text, (
            'triage.md must include an explicit computation rule resolving '
            'mixed-disposition cases.'
        )


class TestTriageGranularityCallSiteAlignment:
    """Cross-file alignment — automated-review.md and sonar-roundtrip.md
    MUST forward `loop_back_target` to mark-step-done so the dispatcher
    hook can route on it."""

    def test_automated_review_forwards_loop_back_target(self) -> None:
        """`automated-review.md` Branch C / "Handle findings (loop-back)"
        MUST forward `loop_back_target` to `mark-step-done --loop-back-target`."""
        path = (
            Path(__file__).parent.parent.parent
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'workflow'
            / 'automated-review.md'
        )
        text = path.read_text(encoding='utf-8')
        assert '--loop-back-target' in text, (
            'automated-review.md must forward --loop-back-target to '
            'mark-step-done on every loop_back outcome.'
        )

    def test_sonar_roundtrip_forwards_loop_back_target(self) -> None:
        """`sonar-roundtrip.md` MUST forward `loop_back_target` to
        `mark-step-done --loop-back-target`."""
        path = (
            Path(__file__).parent.parent.parent
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'workflow'
            / 'sonar-roundtrip.md'
        )
        text = path.read_text(encoding='utf-8')
        assert '--loop-back-target' in text, (
            'sonar-roundtrip.md must forward --loop-back-target to '
            'mark-step-done on every loop_back outcome.'
        )

    def test_phase_6_skill_md_documents_granularity_branch(self) -> None:
        """`phase-6-finalize/SKILL.md` Step 3 § 7b MUST branch on
        `loop_back_target` — `5-execute` triggers full-phase rollback,
        `6-finalize` triggers inline replay."""
        path = (
            Path(__file__).parent.parent.parent
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'SKILL.md'
        )
        text = path.read_text(encoding='utf-8')
        assert 'loop_back_target' in text, (
            'phase-6-finalize/SKILL.md must read loop_back_target in the '
            'continuation hook (§ 7b).'
        )
        # Both granularity tiers must be mentioned in the hook.
        # The granularity branch is documented in Step 3 § 7b.
        # Locate § 7b (the "7b. Loop-back continuation hook" subsection).
        assert '7b. Loop-back continuation hook' in text, (
            'phase-6-finalize/SKILL.md must declare a "7b. Loop-back '
            'continuation hook" subsection inside Step 3.'
        )
        hook_idx = text.index('7b. Loop-back continuation hook')
        # The next sibling subsection (or end of file) bounds the hook.
        next_subsection_idx = text.find('\n#### ', hook_idx)
        if next_subsection_idx == -1:
            next_subsection_idx = len(text)
        hook_block = text[hook_idx:next_subsection_idx]
        assert '5-execute' in hook_block and '6-finalize' in hook_block, (
            'Loop-back continuation hook must explicitly branch on both '
            'loop_back_target values (5-execute and 6-finalize).'
        )

    def test_execution_md_documents_dual_target_prompts(self) -> None:
        """`plan-marshall/workflow/execution.md` § "Loop-back continuation"
        ELSE branch MUST display target-specific prompts — different text
        for `5-execute` vs `6-finalize`."""
        path = (
            Path(__file__).parent.parent.parent
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'plan-marshall'
            / 'workflow'
            / 'execution.md'
        )
        text = path.read_text(encoding='utf-8')
        assert 'Loop-back continuation' in text, (
            'execution.md must declare a "Loop-back continuation" section.'
        )
        # Both target-specific prompt branches must exist.
        assert 'loop_back_target' in text, (
            'execution.md must read loop_back_target from the persisted '
            'phase_steps record before displaying user prompts.'
        )
        assert 'inline replay' in text or 'replay the finalize step' in text, (
            'execution.md must describe the 6-finalize inline replay shape '
            'in the user-facing prompt.'
        )
