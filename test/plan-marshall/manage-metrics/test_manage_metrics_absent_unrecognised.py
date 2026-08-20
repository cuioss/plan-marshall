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
    _INLINE_BUCKET,
    _INLINE_SUM,
    _UNSEEDED_PLAN_IDS,
    _phase_row,
    _run_enrich_with_buckets,
    _total_tokens_cell,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
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
    assert manage_metrics._token_population({'total_tokens_population': raw}) == (
        manage_metrics.POPULATION_DISPATCHED
    )
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
    plan_id = f'population-bullet-{population}'
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

    # 6-finalize is `mixed` — a dispatched cell whose row ALSO records inline
    # spend that the cell EXCLUDES. A mixed row therefore does NOT make the Total
    # cross-population, and the Total must stay unmarked despite a marker being
    # present in the table.
    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert '(mixed)' in report, 'fixture must actually produce a marked row'
    assert '(spans populations)' not in _total_tokens_cell(report)
    assert '(spans populations)' not in report


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


def test_inline_row_carrying_a_competing_dispatched_measure_renders_both_markers(
    plan_context, monkeypatch
):
    """An `inline` row that ALSO carries a dispatched measure keeps both markers.

    This is the row shape the non-idempotent population stamp destroyed, so the
    coverage gap and the defect are one surface. Re-stamped `mixed`,
    `_eligible_dispatched_measures` stops excluding the folded main-context
    `total_tokens` (it becomes a candidate for the dispatched maximum) and
    `cmd_generate` stops collecting the row into `inline_population_phases`,
    silently dropping the Total's `(spans populations)` marker. Driven through
    the render with the stamp idempotent, three things must hold together: the
    competing dispatched measure wins the cell, the cell still carries the row's
    `(inline)` population marker, and the Total still declares that it spans
    populations.

    The fixture makes the folded figure the SMALLER of the two, so no assertion
    below can pass by accidentally rendering the excluded main-context measure.
    """
    plan_id = 'population-inline-competing-measure'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    bucket = dict(_INLINE_BUCKET, subagent_total_tokens=30000, subagent_samples=1)
    assert 30000 > _INLINE_SUM, 'the dispatched measure must be the strict maximum'

    # Two runs: the second is what the pre-fix stamp mislabelled.
    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': bucket})
    _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': bucket})

    row = _phase_row(plan_id, '1-init')
    assert row['total_tokens_population'] == manage_metrics.POPULATION_INLINE
    assert row['total_tokens'] == _INLINE_SUM
    # The folded main-context figure stays out of the dispatched comparison; the
    # genuinely dispatched measure is the only eligible one.
    assert manage_metrics._reconcile_dispatched_measures(row) == ('subagent_total_tokens', 30000)

    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    init_row = next(line for line in report.splitlines() if line.startswith('| 1-init '))
    assert '30,000' in init_row, 'the winning dispatched measure must render in the cell'
    assert f'{_INLINE_SUM:,}' not in init_row, 'the excluded inline figure must not win the cell'
    assert '(inline)' in init_row

    assert '(spans populations)' in _total_tokens_cell(report)
    assert '`(spans populations)`' in report


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


def test_mixed_phase_declares_its_excluded_inline_spend(plan_context, monkeypatch):
    """A mixed row is marked, and the annotation says the inline part is excluded."""
    plan_id = 'population-render-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    finalize_row = next(line for line in report.splitlines() if line.startswith('| 6-finalize '))
    assert '(mixed)' in finalize_row
    assert '`(mixed)`' in report
    assert 'excluded from both the cell and the **Total**' in report
    # The inline bullet must not claim to stand alongside a dispatched total on
    # the inline-only signature and must claim exactly that here.
    assert 'surfaced alongside the dispatched Total tokens' in report


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


def test_four_message_usage_bullets_render_under_the_main_context_heading(
    plan_context, monkeypatch
):
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
    assert lines[heading_idx + 1: heading_idx + 1 + len(expected)] == expected

    # No four-field bullet may escape the group by rendering at top level. The
    # nested form starts with two spaces, so a PREFIX test is what discriminates
    # them — an exact-membership test would match neither form and assert nothing.
    for _field, label in manage_metrics._FOUR_FIELD_USAGE_LABELS:
        top_level = f'- **{label}**:'
        assert not any(ln.startswith(top_level) for ln in lines), (
            f'{label} rendered outside the population group'
        )
