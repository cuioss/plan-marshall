#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The prescribed orchestrator-tier build hand-back is a termination cause of its own.

Before this member existed a phase-5 leaf that handed a build back — exactly
what the workflow prescribes — was provisionally classified
``voluntary_checkpoint`` and then reclassified ``error`` by the no-progress
rule, so a working hand-back was recorded as a failure. These tests pin the
member's acceptance at the recorder, and the two documents that must name it:
the termination table in ``execution.md`` and the return contract in
``phase-5-execute/SKILL.md``.

The accepted-cause population is DERIVED from
``DISPATCH_TERMINATION_CAUSES``, never hand-listed: a member added later is
exercised here without editing this file.
"""

from pathlib import Path

import pytest
from _manage_metrics_fixtures import ns_record_dispatch_boundary
from _manage_metrics_module_fixtures import (
    cmd_record_dispatch_boundary,
    manage_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EXECUTION_MD = (
    REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'execution.md'
)
PHASE_5_SKILL_MD = REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'phase-5-execute' / 'SKILL.md'

NEW_CAUSE = 'verification_handback'

# ⛔ Vacuity guard — a derived population that emptied would collect zero cases
# at the parametrize below and still report green.
assert manage_metrics.DISPATCH_TERMINATION_CAUSES, 'DISPATCH_TERMINATION_CAUSES is empty'


class TestEveryDeclaredCauseIsAccepted:
    """Every member of the declared enum records a row — the enum is the contract."""

    @pytest.mark.parametrize('cause', manage_metrics.DISPATCH_TERMINATION_CAUSES)
    def test_declared_cause_records_a_successful_row(self, plan_context, cause):
        plan_id = f'vbh-cause-{cause.replace("_", "-")}'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')

        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '5-execute', termination_cause=cause, total_tokens=7)
        )

        assert result['status'] == 'success'
        assert result['termination_cause'] == cause
        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        assert f',{cause},' in artifact.read_text(encoding='utf-8')


class TestHandbackCauseIsNamedInItsTwoDocuments:
    """The cause is stated in the termination table and in the return contract."""

    def test_execution_md_termination_table_carries_the_cause(self):
        text = EXECUTION_MD.read_text(encoding='utf-8')

        # A table ROW, not a bare mention elsewhere in the file: the row starts
        # with the cause and states how it is detected.
        assert f'| `{NEW_CAUSE}` |' in text, 'execution.md must carry the hand-back as a termination-table row'
        assert 'verification_handback: true' in text, 'the row must name the discriminator it keys on'
        assert 'The exemption is scoped to the task the return is about' in text, (
            'the row must state the SCOPED exemption: a hand-back exempts the task it is about, not a further stall beside it'
        )
        assert 'a further non-owed task that stalled in the SAME dispatch is still decided' in text

    def test_phase_5_return_contract_carries_the_discriminator(self):
        text = PHASE_5_SKILL_MD.read_text(encoding='utf-8')

        # The exact contract line, not a bare mention: a prose reference would
        # not give the leaf a field to emit.
        assert 'verification_handback: {true | false}' in text, (
            'the phase-5 return contract block must carry the discriminator field'
        )
        # The four returns that set it, by the section/step names the contract uses.
        for site in ('Step 11b', 'Step 11c', 'running', '--verification-owed'):
            assert site in text, f'the return contract must keep naming {site}'

    def test_the_workflow_no_longer_calls_budget_yield_the_one_legitimate_yield(self):
        text = PHASE_5_SKILL_MD.read_text(encoding='utf-8')

        assert 'The one legitimate yield' not in text, (
            'phase-5-execute must not call budget_yield the one legitimate yield: '
            'the orchestrator-tier hand-back is prescribed by the same file'
        )
        assert 'The two legitimate yields' in text, 'both yields must be named, with their signals'
        assert 'verification_handback' in text and 'budget_yield' in text

    def test_phase_5_names_the_four_task_boundary_points_consistently(self):
        """The "only yields" claim must not contradict the four sanctioned points."""
        text = PHASE_5_SKILL_MD.read_text(encoding='utf-8')

        assert 'These two are the ONLY yields' not in text, (
            'phase-5-execute lists four TASK-boundary re-dispatch points; two of them are '
            'prescribed non-completions with their own ledger causes, not clean yields'
        )
        assert 'These two are the only yields that are NOT error handling' in text
        for point in ('budget_yield', 'verification_handback', 'triage_required', 'baseline_drift'):
            assert point in text, f'the four sanctioned points must keep naming {point}'

    def test_the_voluntary_checkpoint_row_covers_a_malformed_handback_pair(self):
        """A `verification_handback: true` with an empty list must match a row.

        The hand-back row requires a non-empty list, and the voluntary_checkpoint
        row used to exclude every return carrying the discriminator — so a
        discriminator with an empty list matched neither row.
        """
        text = EXECUTION_MD.read_text(encoding='utf-8')

        assert 'without a valid hand-back pair' in text
        assert 'beside an empty `pending_verify_steps[]`' in text

    def test_b7_is_evaluated_on_both_qualifying_returns(self):
        """A hand-back return must still reach the predicate, or D1 can never fire.

        The table classifies a valid hand-back as `verification_handback`, so a
        trigger scoped to returns "provisionally classified voluntary_checkpoint"
        would skip the very return the scoped exemption exists for; a trigger
        covering EVERY non-error return would instead reclassify a legitimate
        `budget_yield`. The trigger names exactly the two cases.
        """
        text = EXECUTION_MD.read_text(encoding='utf-8')

        assert 'in exactly two cases' in text
        assert 'the return is provisionally classified `voluntary_checkpoint`' in text
        assert 'the return carries a hand-back pair' in text
        assert 'keeps its own classification and is not passed through the predicate' in text
