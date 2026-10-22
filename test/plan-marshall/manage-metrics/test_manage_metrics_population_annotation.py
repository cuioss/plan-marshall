#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Scope: which population a rendered row declares — when a total is marked because an
inline row fed it, when an inline measure is excluded from the dispatched maximum,
and when a report carries no annotation at all.
"""

import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _INLINE_BUCKET,
    _INLINE_SUM,
    _UNSEEDED_PLAN_IDS,
    _phase_row,
    _run_enrich_with_buckets,
    _seed_guarded_plan_dirs,
    _total_tokens_cell,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

# ⛔ Vacuity guard — the population table belongs to the production module, so emptying
# it there collects zero cases at the parametrize sites below and still reports green.
assert manage_metrics.TOKEN_POPULATIONS, 'manage_metrics.TOKEN_POPULATIONS is empty'


@pytest.mark.parametrize(
    'raw',
    [
        None,
        0,
        0.0,
        False,
        '',
        [],
        {},
        'subagent',
        'DISPATCHED',
    ],
)
def test_absent_or_unrecognised_population_reads_as_dispatched(raw):
    """The falsy/unknown domain collapses to `dispatched`, never to a bogus marker.

    A row that was never enriched carries no discriminator, and without enrich the
    only source `total_tokens` can have had is dispatched `<usage>` / the
    accumulator — so absent legitimately means dispatched. The falsy values and
    the near-miss strings are covered explicitly because a truthiness or a
    substring test over this field would classify some of them differently and
    render a marker no reader can interpret.
    """
    assert manage_metrics._token_population({'total_tokens_population': raw}) == (manage_metrics.POPULATION_DISPATCHED)
    assert manage_metrics._token_population({}) == manage_metrics.POPULATION_DISPATCHED


@pytest.mark.parametrize('population', manage_metrics.TOKEN_POPULATIONS)
def test_each_declared_population_round_trips(population):
    """Every declared population is recognised — the guard above is not a blanket."""
    assert manage_metrics._token_population({'total_tokens_population': population}) == population


@pytest.mark.parametrize('population', manage_metrics.TOKEN_POPULATIONS)
def test_total_tokens_bullet_names_its_population(plan_context, population):
    """Every rendered `Total tokens` bullet carries a population qualifier.

    Parameterized over `TOKEN_POPULATIONS` rather than a hand-listed pair, so a
    population added later cannot render unlabelled and still pass.
    """
    plan_id = f'population-bullet-{population.replace("_", "-")}'
    cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
    cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=31000))
    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases']['4-plan']['total_tokens_population'] = population
    manage_metrics.write_metrics(plan_id, data)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    bullets = [line for line in report.splitlines() if line.startswith('- **Total tokens**:')]
    assert bullets, 'no Total tokens bullet was rendered'
    for bullet in bullets:
        assert manage_metrics._POPULATION_BULLET_NOTE[population] in bullet


def test_total_row_is_marked_when_an_inline_row_fed_the_sum(plan_context, monkeypatch):
    """The Total inherits the column default, so a cross-population sum is marked.

    The column header declares `dispatched` as the unmarked default. A Total fed
    by an `(inline)` row is therefore an exception like any other cell, and an
    unmarked one would assert precisely the dispatched-total claim the annotation
    directly beneath it denies — the partition-labelled-a-whole defect, relocated
    from the field name to the Total row.
    """
    plan_id = 'population-total-spans'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert '(spans populations)' in _total_tokens_cell(report)
    # The annotation states the marker, so the reader has its key.
    assert '`(spans populations)`' in report
    assert 'not a dispatched total' in report


def test_total_row_is_unmarked_when_every_contributing_row_is_dispatched(plan_context, monkeypatch):
    """Matched negative control: a single-population Total takes NO marker.

    Without this, the positive assertion above would pass over an implementation
    that marked the Total unconditionally — which would state "spans
    populations" on a Total that spans exactly one, and prove nothing about the
    discriminator driving it.
    """
    plan_id = 'population-total-single'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    # No row was enriched, so every fed row is an unmarked dispatched
    # measurement and the Total spans exactly one population.
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert '(spans populations)' not in _total_tokens_cell(report)
    assert '(spans populations)' not in report
    assert '(inline)' not in report
    assert '(main + sub-agent)' not in report
    assert '> Tokens population:' not in report


def test_inline_phase_tokens_cell_and_annotation_declare_the_population(plan_context, monkeypatch):
    """The breakdown never presents an inline figure as a dispatched one.

    Three render sites must agree: the cell carries an `(inline)` marker, the
    annotation under the table declares the unmarked default AND states that the
    Total is no longer a dispatched total, and the phase's own bullet names the
    main-context population.
    """
    plan_id = 'population-render-inline'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    init_row = next(line for line in report.splitlines() if line.startswith('| 1-init '))
    assert '(inline)' in init_row

    execute_row = next(line for line in report.splitlines() if line.startswith('| 5-execute '))
    assert '(inline)' not in execute_row and '(mixed)' not in execute_row

    assert '> Tokens population:' in report
    assert '1-init' in report.split('> Tokens population:', 1)[1].split('\n', 1)[0]
    assert 'not a dispatched total' in report
    assert manage_metrics._POPULATION_BULLET_NOTE[manage_metrics.POPULATION_INLINE] in report


def test_whole_phase_row_renders_both_populations_summed(plan_context, monkeypatch):
    """A phase with main-context AND dispatched spend renders the sum, marked.

    This is the row shape the landing's total is read from: the cell carries both
    populations' spend, the marker names the composition, and the annotation
    states that the main-context part is INCLUDED rather than excluded.
    """
    plan_id = 'population-inline-competing-measure'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    bucket = dict(_INLINE_BUCKET, subagent_total_tokens=30000, subagent_samples=1)

    # Two runs: the second must recompose exactly what the first composed.
    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': bucket})
    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': bucket})

    row = _phase_row(plan_id, '1-init')
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT
    assert row['total_tokens'] == _INLINE_SUM + 30000
    # The dispatched figure is preserved, and it — not the whole-phase total — is
    # the only figure eligible for the dispatched-population comparison.
    assert manage_metrics._reconcile_dispatched_measures(row) == ('subagent_total_tokens', 30000)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    init_row = next(line for line in report.splitlines() if line.startswith('| 1-init '))
    assert f'{_INLINE_SUM + 30000:,}' in init_row
    assert '(main + sub-agent)' in init_row
    assert '`(main + sub-agent)`' in report
    # A single composed row means the Total spans exactly one population — which
    # it must still DECLARE, because it is not the column's dispatched default.
    assert '(spans populations)' not in _total_tokens_cell(report)
    assert '(main + sub-agent)' in _total_tokens_cell(report)


def test_legacy_inline_row_with_subagent_evidence_is_not_labelled_as_having_dispatched_nothing(
    plan_context, monkeypatch
):
    """A row stamped inline that also recorded sub-agent work is composed, not mislabelled.

    The inline stamp claims the phase dispatched nothing. The base code could
    stamp it on a bucket that also carried sub-agent usage, so rendering such a
    row unchanged would print a false claim.
    """
    plan_id = 'population-legacy-inline-with-subagent'
    cmd_start_phase(ns_start_phase(plan_id, '3-outline'))
    cmd_end_phase(ns_end_phase(plan_id, '3-outline'))
    data = manage_metrics.read_metrics_raw(plan_id)
    row = data['phases']['3-outline']
    row['inline_main_context_tokens'] = 6000
    row['total_tokens'] = 6000
    row['total_tokens_population'] = manage_metrics.POPULATION_INLINE
    row['subagent_total_tokens'] = 30000
    row['subagent_samples'] = 1
    manage_metrics.write_metrics(plan_id, data)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    row_line = next(line for line in report.splitlines() if line.startswith('| 3-outline '))
    assert 'dispatched nothing' not in report
    assert '(main + sub-agent)' in row_line
    assert '36,000' in row_line


def test_inline_total_tokens_is_excluded_from_the_dispatched_maximum():
    """A main-context figure may not enter a dispatched-population comparison.

    The inline figure is the larger number here, so an unfiltered max would
    render it as the dispatched total — the exact cross-population mislabel the
    discriminator exists to prevent.
    """
    row = {
        'total_tokens': 900000,
        'total_tokens_population': manage_metrics.POPULATION_INLINE,
        'subagent_total_tokens': 12000,
    }

    assert manage_metrics._reconcile_dispatched_measures(row) == (
        'subagent_total_tokens',
        12000,
    )


def test_inline_only_row_has_no_eligible_dispatched_measure():
    """A phase that dispatched nothing offers nothing to the dispatched maximum."""
    row = {
        'total_tokens': 60000,
        'total_tokens_population': manage_metrics.POPULATION_INLINE,
    }

    assert manage_metrics._reconcile_dispatched_measures(row) is None


def test_whole_phase_row_declares_its_included_inline_spend(plan_context, monkeypatch):
    """A whole-phase row is marked, and the annotation says the inline part IS counted."""
    plan_id = 'population-render-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize '))
    assert '(main + sub-agent)' in finalize_row
    assert '`(main + sub-agent)`' in report
    # The inline bullet states that the Total INCLUDES this figure — the
    # relationship the pre-composition text got backwards.
    assert 'included in the Total tokens figure' in report


def test_legacy_mixed_row_keeps_its_marker_and_feeds_the_dispatched_population(plan_context):
    """A row stamped `mixed` before the composition landed still renders truthfully.

    Its cell IS the dispatched figure with the inline spend excluded, so it must
    keep the `(mixed)` marker and must not make the Total look cross-population.
    """
    plan_id = 'population-render-mixed-legacy'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))
    data = manage_metrics.read_metrics_raw(plan_id)
    row = data['phases']['5-execute']
    row['inline_main_context_tokens'] = 6000
    row['total_tokens_population'] = manage_metrics.POPULATION_MIXED
    manage_metrics.write_metrics(plan_id, data)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    execute_row = next(line for line in report.splitlines() if line.startswith('| 5-execute '))
    assert '42,000' in execute_row
    assert '(mixed)' in execute_row
    assert '`(mixed)`' in report
    assert '(spans populations)' not in _total_tokens_cell(report)
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert stored[manage_metrics._TOTALS_POPULATION_FIELD] == manage_metrics.POPULATION_DISPATCHED


def test_dispatched_only_report_carries_no_population_annotation(plan_context):
    """Negative control: a wholly-dispatched plan gets no marker and no annotation.

    Without this the marker assertions above would pass over a report that
    annotates unconditionally, which would prove nothing about the discriminator.
    """
    plan_id = 'population-render-dispatched'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert '> Tokens population:' not in report
    assert '(inline)' not in report
    assert '(mixed)' not in report
    assert manage_metrics._POPULATION_BULLET_NOTE[manage_metrics.POPULATION_DISPATCHED] in report


def test_four_message_usage_bullets_render_under_the_main_context_heading(plan_context, monkeypatch):
    """Every `message.usage` bullet names its population — via a group heading.

    An API field name states no population at all, so these four were the only
    rendered token figures carrying no population claim whatsoever.

    The bullet set is derived from `_FOUR_FIELD_USAGE_LABELS` — the same tuple
    the render loop iterates — rather than from four hand-written names, so a
    fifth usage field added later cannot render unlabelled and still pass. It is
    deliberately NOT derived from `_INLINE_MAIN_CONTEXT_FIELDS`, which holds only
    three fields (it excludes `cache_read_input_tokens`) and would silently leave
    the cache-read bullet uncovered.
    """
    plan_id = 'population-four-field-group'
    cmd_start_phase(ns_start_phase(plan_id, '2-refine'))
    cmd_end_phase(ns_end_phase(plan_id, '2-refine', total_tokens=42000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'2-refine': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')
    lines = report.splitlines()

    assert 'Main-context-window' in manage_metrics._FOUR_FIELD_GROUP_HEADING
    # Assert presence before indexing: a bare `.index()` on a missing heading
    # raises ValueError, which reports the absence as a crash rather than as the
    # contract failure it is.
    assert manage_metrics._FOUR_FIELD_GROUP_HEADING in lines, (
        'the four message.usage bullets rendered with no population heading'
    )
    heading_idx = lines.index(manage_metrics._FOUR_FIELD_GROUP_HEADING)

    # Every field the render loop knows about, whose fixture value is non-zero,
    # renders as a nested bullet inside the group the heading opens.
    expected = [
        f'  - **{label}**: {int(_INLINE_BUCKET[field]):,}'
        for field, label in manage_metrics._FOUR_FIELD_USAGE_LABELS
        if _INLINE_BUCKET.get(field)
    ]
    assert expected, 'fixture must exercise at least one four-field bullet'
    assert lines[heading_idx + 1 : heading_idx + 1 + len(expected)] == expected

    # No four-field bullet may escape the group by rendering at top level. The
    # nested form starts with two spaces, so a PREFIX test is what discriminates
    # them — an exact-membership test would match neither form and assert nothing.
    for _field, label in manage_metrics._FOUR_FIELD_USAGE_LABELS:
        top_level = f'- **{label}**:'
        assert not any(ln.startswith(top_level) for ln in lines), f'{label} rendered outside the population group'
