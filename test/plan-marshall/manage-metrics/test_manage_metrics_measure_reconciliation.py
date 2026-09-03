#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* Symmetric reconciliation across the competing dispatched-population measures
* billing_weighted_total as a first-class cost figure
"""


from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _seed_billing_phases,
    _seed_guarded_plan_dirs,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

# =============================================================================
# Symmetric reconciliation across the competing dispatched-population measures
# =============================================================================
#
# Three fields measure the SAME dispatched leaves by three routes. The maximum is
# applied to all three or to none: comparing only two of them let the third
# exceed the rendered figure with the report never saying so.


def test_subagent_total_wins_when_it_is_the_largest_eligible_measure():
    """The third measure competes. The observed 4-plan shape: 577,452 > 439,628.

    Before the symmetric rule, `subagent_total_tokens` had no comparison site at
    all — it could exceed the figure the report rendered and nothing said so.
    """
    row = {
        'total_tokens': 439628,
        'dispatch_boundary_total': 400000,
        'subagent_total_tokens': 577452,
    }

    assert manage_metrics._reconcile_dispatched_measures(row) == (
        'subagent_total_tokens',
        577452,
    )


def test_partial_boundary_measure_never_wins_the_maximum():
    """A boundary sum covering fewer dispatches than the phase had is a floor.

    It is the LARGEST number on the row, so a coverage-blind max would pick it.
    """
    row = {
        'total_tokens': 100000,
        'dispatch_boundary_total': 900000,
        'dispatch_boundary_rows_recorded': 2,
        'subagent_samples': 7,
    }

    assert manage_metrics._reconcile_dispatched_measures(row) == ('total_tokens', 100000)


def test_complete_boundary_measure_does_win_the_maximum():
    """Matched control: the same shape with full coverage DOES win.

    Without this, the partial-exclusion test above would pass over a rule that
    simply never lets the boundary measure win.
    """
    row = {
        'total_tokens': 100000,
        'dispatch_boundary_total': 900000,
        'dispatch_boundary_rows_recorded': 7,
        'subagent_samples': 7,
    }

    assert manage_metrics._reconcile_dispatched_measures(row) == (
        'dispatch_boundary_total',
        900000,
    )


def test_reconciliation_covers_every_declared_measure_field():
    """The rule is applied to ALL declared measures — never to a subset.

    Derived from `_DISPATCHED_MEASURE_FIELDS`: a fourth measure added to the
    tuple without being made winnable fails here rather than silently sitting
    outside the comparison, which is how `subagent_total_tokens` stayed invisible.
    """
    fields = manage_metrics._DISPATCHED_MEASURE_FIELDS
    assert len(fields) >= 3

    for index, field in enumerate(fields):
        # Make exactly this field the strict maximum among all declared measures.
        row: dict[str, int] = dict.fromkeys(fields, 1000)
        row[field] = 9000 + index
        winner = manage_metrics._reconcile_dispatched_measures(row)
        assert winner == (field, 9000 + index), f'{field} cannot win the maximum'


def test_reconciliation_annotation_names_the_winning_measure(plan_context):
    """The annotation says WHICH measure won and what it beat.

    The retired string asserted an unqualified "same-population max" without
    naming the winner, so a reader could not tell which route produced the cell.
    """
    plan_id = 'reconcile-annotation'
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
    cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=439628))
    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases']['4-plan']['subagent_total_tokens'] = 577452
    manage_metrics.write_metrics(plan_id, data)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert 'subagent_total_tokens 577,452' in report
    assert '(> total_tokens 439,628)' in report
    plan_row = next(line for line in report.splitlines() if line.startswith('| 4-plan '))
    assert '577,452' in plan_row


def test_boundary_bullet_declares_coverage_and_drops_the_false_parenthetical(plan_context):
    """The bullet states its coverage instead of claiming an unearned max."""
    plan_id = 'reconcile-bullet'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=100000))
    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases']['5-execute']['dispatch_boundary_total'] = 90000
    data['phases']['5-execute']['dispatch_boundary_rows_recorded'] = 2
    data['phases']['5-execute']['subagent_samples'] = 7
    manage_metrics.write_metrics(plan_id, data)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    bullet = next(
        line for line in report.splitlines() if line.startswith('- **Dispatch-boundary total**:')
    )
    assert 'PARTIAL: 2 of 7 dispatch(es) recorded' in bullet
    assert 'did not win the maximum' in bullet
    # The retired claim must be gone from the whole report, not just this bullet.
    assert 'same-population max' not in report


# =============================================================================
# billing_weighted_total as a first-class cost figure
# =============================================================================

def test_billing_column_is_rendered_with_its_own_total(plan_context):
    """The Billing column and its Total are distinct from every work column."""
    plan_id = 'billing-column'
    _seed_billing_phases(plan_id, {'4-plan': 41003, '5-execute': 78000})

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    header = next(line for line in report.splitlines() if line.startswith('| Phase '))
    assert 'Billing (cost)' in header

    total_row = next(line for line in report.splitlines() if line.startswith('| **Total**'))
    cells = [cell.strip() for cell in total_row.strip().strip('|').split('|')]
    # Last column is Billing; the Tokens column is unchanged by its presence.
    assert '119,003' in cells[-1]
    assert '20,000' in cells[-3]


def test_billing_total_carries_the_partiality_marker(plan_context):
    """A phase lacking the field makes the Billing Total render `(n=k/6)`.

    The column inherits the same symmetric aggregation rule as every other
    column, so a partial cost total cannot read as a complete one.
    """
    plan_id = 'billing-partial'
    _seed_billing_phases(plan_id, {'4-plan': 41003})
    # A second recorded phase with NO billing figure — the column is 1/6, and the
    # phase itself renders `-`.
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=10000))

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    total_row = next(line for line in report.splitlines() if line.startswith('| **Total**'))
    cells = [cell.strip() for cell in total_row.strip().strip('|').split('|')]
    assert cells[-1] == '**41,003 (n=1/6)**'

    execute_row = next(line for line in report.splitlines() if line.startswith('| 5-execute '))
    execute_cells = [cell.strip() for cell in execute_row.strip().strip('|').split('|')]
    assert execute_cells[-1] == '-'


def test_billing_is_never_summed_into_the_tokens_total(plan_context):
    """Matched control: a large cost figure leaves the dispatched Total unmoved.

    The two measures answer different questions over different populations, so a
    cost figure entering the work total would be a category error, not a bigger
    number.
    """
    plan_id = 'billing-not-summed'
    _seed_billing_phases(plan_id, {'5-execute': 5_000_000})

    result = cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert result['total_tokens'] == 10000
    assert result['total_billing_weighted'] == 5_000_000
    total_row = next(line for line in report.splitlines() if line.startswith('| **Total**'))
    cells = [cell.strip() for cell in total_row.strip().strip('|').split('|')]
    assert '10,000' in cells[-3]
    assert '5,010,000' not in total_row


def test_billing_bullet_states_the_measure_rather_than_apologising(plan_context):
    """The bullet defines the figure; incomparability is a property, not a caveat."""
    plan_id = 'billing-bullet'
    _seed_billing_phases(plan_id, {'5-execute': 78000})

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    bullet = next(
        line for line in report.splitlines() if line.startswith('- **Billing-weighted total**:')
    )
    assert 'derived-cost population' in bullet
    assert '0.1 × cache_read' in bullet
    assert '1.25 × cache_creation' in bullet
    assert 'never summed' in bullet
    # The retired disclaimer form is gone.
    assert 'not a work-comparable measure' not in report
