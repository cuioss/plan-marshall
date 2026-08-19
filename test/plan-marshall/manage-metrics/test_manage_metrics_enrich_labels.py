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


def test_enrich_labels_a_dispatched_plus_inline_phase_as_mixed(plan_context, monkeypatch):
    """A mixed phase keeps its dispatched total and records the inline part apart.

    `total_tokens` stays byte-identical (explicit-wins), the inline spend is a
    separate field of a different population, and the row reads `mixed` so a
    consumer knows the dispatched figure does NOT cover the whole phase.
    """
    plan_id = 'population-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})

    row = _phase_row(plan_id, '6-finalize')
    assert row['total_tokens'] == 88000, 'the dispatched total must never be overwritten'
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MIXED


def test_enrich_labels_a_dispatch_only_phase_as_dispatched(plan_context, monkeypatch):
    """No inline attribution → the row is labelled dispatched and carries no inline field."""
    plan_id = 'population-dispatched'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    _run_enrich_with_buckets(
        plan_id, monkeypatch, {'5-execute': {'cache_read_input_tokens': 250000}}
    )

    row = _phase_row(plan_id, '5-execute')
    assert row['total_tokens'] == 42000
    assert 'inline_main_context_tokens' not in row
    assert row['total_tokens_population'] == manage_metrics.POPULATION_DISPATCHED


def test_repeated_enrich_keeps_an_inline_only_row_labelled_inline(plan_context, monkeypatch):
    """A second enrich run must not read its OWN fold as a dispatched total.

    The inline branch writes `total_tokens`, so a branch keyed on
    `not total_tokens` is self-defeating: run two sees run one's fold, falls
    through to the mixed branch, and stamps `mixed` on a row where nothing was
    ever dispatched. Re-invocation is the ordinary case — `record-metrics` runs
    enrich on every finalize entry and a loop-back re-enters it — so a
    single-run assertion proves nothing about the stamp a report actually reads.
    """
    plan_id = 'population-enrich-idempotent-inline'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']
    first = dict(_phase_row(plan_id, '1-init'))
    assert first['total_tokens_population'] == manage_metrics.POPULATION_INLINE
    assert first['total_tokens'] == _INLINE_SUM

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']
    second = _phase_row(plan_id, '1-init')

    # The discriminator survives the re-run, and the folded figure is unchanged —
    # the second run recognised its own prior fold instead of re-classifying it.
    assert second['total_tokens_population'] == manage_metrics.POPULATION_INLINE
    assert second['total_tokens'] == first['total_tokens']
    assert second['inline_main_context_tokens'] == _INLINE_SUM


def test_repeated_enrich_keeps_a_genuinely_mixed_row_labelled_mixed(plan_context, monkeypatch):
    """Matched control: the idempotence fix does not disable the `mixed` stamp.

    Keying the inline branch off the discriminator could have been "widened" into
    never reaching the mixed branch at all, which would pass the inline test
    above while destroying the signature it exists to distinguish. A row carrying
    a REAL dispatched total plus inline spend must still read `mixed` on the
    first run and on every run after it.
    """
    plan_id = 'population-enrich-idempotent-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    assert _phase_row(plan_id, '6-finalize')['total_tokens_population'] == (
        manage_metrics.POPULATION_MIXED
    )

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    row = _phase_row(plan_id, '6-finalize')

    assert row['total_tokens_population'] == manage_metrics.POPULATION_MIXED
    assert row['total_tokens'] == 88000, 'the dispatched total must never be overwritten'
    assert row['inline_main_context_tokens'] == _INLINE_SUM


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
