#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _pin_start_time_to_past,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding. A
    module whose tests need the real ``plan_not_found`` failure registers the
    plan id via ``_register_unseeded`` first; no test in this module does, so
    the guard here always seeds and the registry stays empty.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


# =============================================================================
# Test: first-class partiality fields (Tier 2 - direct import)
# =============================================================================

class TestCloseValueScopeDiscriminator:
    """A closed row DECLARES which of its values are cumulative and which are last-close.

    The cumulative-vs-last-close split was previously stated only as prose in
    ``data-format.md`` and two docstrings, so a script consumer reading a
    ``close_count > 1`` row off disk had no field-level signal telling it which
    of the row's values are sums. ``_close_phase_accumulating`` now stamps
    ``value_scope`` on EVERY close, plus ``cumulative_fields`` /
    ``last_close_fields`` from the second close onward — the
    ``total_tokens_population`` precedent (a row-level discriminator with a
    documented absent-reads-as default).
    """

    def test_first_close_stamps_single_close_and_omits_the_field_lists(self, plan_context):
        """One close ⇒ `single_close`, and the two list fields are NOT written.

        On a first close the split is vacuous — every value covers the one and
        only close — so writing the lists would state a distinction the row does
        not have.
        """
        cmd_start_phase(ns_start_phase('vs-first', '5-execute'))
        _pin_start_time_to_past('vs-first', '5-execute')
        cmd_end_phase(ns_end_phase('vs-first', '5-execute', total_tokens=1000, tool_uses=4))

        row = manage_metrics.read_metrics_raw('vs-first')['phases']['5-execute']
        assert row['close_count'] == 1
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_SINGLE_CLOSE
        assert 'cumulative_fields' not in row
        assert 'last_close_fields' not in row

    def test_second_close_declares_the_split_on_the_row(self, plan_context):
        """A re-entered row names its cumulative and its last-close fields.

        Asserts the concrete field NAMES the row published — not merely that a
        marker appeared — and cross-checks each named cumulative field against
        the arithmetic it claims: `total_tokens` really is the SUM of the two
        closes' deltas, and `close_count` really is 2.
        """
        cmd_start_phase(ns_start_phase('vs-reentry', '5-execute'))
        _pin_start_time_to_past('vs-reentry', '5-execute')
        cmd_end_phase(ns_end_phase('vs-reentry', '5-execute', total_tokens=1000, tool_uses=4))
        # Loop-back: the same phase is closed a second time.
        cmd_end_phase(ns_end_phase('vs-reentry', '5-execute', total_tokens=250, tool_uses=1))

        row = manage_metrics.read_metrics_raw('vs-reentry')['phases']['5-execute']
        assert row['close_count'] == 2
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_MIXED

        cumulative = row['cumulative_fields'].split(',')
        last_close = row['last_close_fields'].split(',')
        # The declaration names fields the row actually carries, in the module's
        # canonical order.
        assert cumulative == ['close_count', 'duration_seconds', 'total_tokens', 'tool_uses']
        assert last_close == ['start_time', 'end_time']
        # Every declared cumulative field is present on the row it describes.
        for field in cumulative:
            assert field in row, field
        for field in last_close:
            assert field in row, field
        # The claim is true of the values, not only of the labels: both flag
        # values were per-close deltas and were ADDED.
        assert row['total_tokens'] == 1250
        assert row['tool_uses'] == 5

    def test_declaration_never_names_a_field_the_row_lacks(self, plan_context):
        """A close that resolved no token flags declares only what it wrote.

        `_stamp_value_scope` runs as the LAST write of the close and intersects
        with the row's actual keys, so a timestamps-only close (the sanctioned
        inline recording mode) does not claim a `total_tokens` it never wrote.
        """
        cmd_start_phase(ns_start_phase('vs-timestamps', '2-refine'))
        _pin_start_time_to_past('vs-timestamps', '2-refine')
        cmd_end_phase(ns_end_phase('vs-timestamps', '2-refine'))
        cmd_end_phase(ns_end_phase('vs-timestamps', '2-refine'))

        row = manage_metrics.read_metrics_raw('vs-timestamps')['phases']['2-refine']
        assert row['close_count'] == 2
        assert row['value_scope'] == manage_metrics.VALUE_SCOPE_MIXED
        declared = row['cumulative_fields'].split(',')
        assert 'total_tokens' not in declared
        assert 'tool_uses' not in declared
        assert declared == ['close_count', 'duration_seconds']

    def test_re_entered_phase_details_bullet_prints_the_rows_own_declaration(
        self, plan_context
    ):
        """metrics.md renders the row's field lists rather than restating them.

        A hand-restated list at the render site would be a second copy free to
        drift from the writer's, so the bullet is asserted to carry the exact
        strings the row published.
        """
        cmd_start_phase(ns_start_phase('vs-md', '5-execute'))
        _pin_start_time_to_past('vs-md', '5-execute')
        cmd_end_phase(ns_end_phase('vs-md', '5-execute', total_tokens=1000, tool_uses=4))
        cmd_end_phase(ns_end_phase('vs-md', '5-execute', total_tokens=250, tool_uses=1))
        cmd_generate(ns_generate('vs-md'))

        row = manage_metrics.read_metrics_raw('vs-md')['phases']['5-execute']
        md = (plan_context.plan_dir_for('vs-md') / 'metrics.md').read_text()
        bullet = next(line for line in md.splitlines() if line.startswith('- **Closes**'))
        assert '2' in bullet
        assert f'Cumulative across closes: {row["cumulative_fields"]}' in bullet
        assert f'Latest close only: {row["last_close_fields"]}' in bullet


# =============================================================================
# Test: record-dispatch-boundary (Tier 2 - direct import)
# =============================================================================

class TestDispatchTerminationCausesEnum:
    """Structural assertions on the DISPATCH_TERMINATION_CAUSES tuple."""

    def test_enum_contains_exactly_twelve_values(self):
        """The enum extends to exactly 12 entries — the legacy 5, the phase-6/phase-4
        extension (5), the budget_yield phase-5 dispatch-loop signal, plus
        returned_with_findings (the productive-loop-back member)."""
        assert len(manage_metrics.DISPATCH_TERMINATION_CAUSES) == 12

    def test_enum_contains_returned_with_findings_cause(self):
        """The productive-non-completion member is present.

        A findings-bearing loop-back is a success of the dispatched step and a
        non-completion of the loop; before this member the dispatch ledger had no
        token for it and such returns fell through to `error`. RED before the
        member was added.
        """
        assert 'returned_with_findings' in manage_metrics.DISPATCH_TERMINATION_CAUSES

    def test_enum_preserves_legacy_five_values(self):
        """The legacy 5 entries remain present so prior callers do not break."""
        legacy = {
            'voluntary_checkpoint',
            'task_complete_returned_verbatim',
            'harness_cancellation',
            'error',
            'clean_exit_queue_empty',
        }
        assert legacy.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_6_finalize_causes(self):
        """The three phase-6-finalize outcomes are present in the extended enum."""
        phase6 = {'step_complete', 'blocked_user_review', 'blocked_session_restart'}
        assert phase6.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_4_plan_causes(self):
        """The two phase-4-plan outcomes are present in the extended enum."""
        phase4 = {'task_batch_complete', 'agent_returned'}
        assert phase4.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_budget_yield_cause(self):
        """The phase-5 budget-bounded dispatch loop's yield signal is present."""
        assert 'budget_yield' in manage_metrics.DISPATCH_TERMINATION_CAUSES

    def test_enum_has_no_duplicate_values(self):
        """Every termination cause is distinct — budget_yield is additive, not a rename."""
        causes = manage_metrics.DISPATCH_TERMINATION_CAUSES
        assert len(causes) == len(set(causes))
