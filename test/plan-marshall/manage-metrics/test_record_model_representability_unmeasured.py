#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan."""


from __future__ import annotations
from _record_model_representability_fixtures import (
    _CONTEXT_COLUMNS,
    _UNMEASURED_FIXTURE,
    _data_rows,
    _drive_scenario,
    analyze_logs,
    audit,
)


# =============================================================================
# The composed record: no field asserts an unearned value
# =============================================================================


def test_unmeasured_dispatch_columns_are_absent_rather_than_zero(plan_context):
    """The dispatch that forwarded no `message.usage` writes the token, not `0`.

    RED against pre-fix code, which coerced every omitted flag to `0` — so "the
    caller passed no measurement" and "the dispatch loaded zero context" produced
    byte-identical rows.
    """
    scenario = _drive_scenario('repr-unmeasured-columns')
    unmeasured_result = scenario['dispatch_results'][1]

    # The result withholds every column the caller did not measure, and names them.
    for column in _CONTEXT_COLUMNS:
        assert column not in unmeasured_result, column
    assert unmeasured_result['unmeasured_context_load_columns'] == ','.join(_CONTEXT_COLUMNS)

    # And the row on disk carries the token rather than four zeros.
    rows = _data_rows(scenario['boundary_path'].read_text(encoding='utf-8'))
    assert len(rows) == 3
    assert rows[1].endswith(',budget_yield,20000,9,90000,unmeasured,unmeasured,unmeasured,unmeasured')
    assert ',20000,9,90000,0,0,0,0' not in rows[1]


def test_unmeasured_fixture_reads_three_ways_in_the_retrospective_reader():
    """One file, both representations, read per column by the retrospective reader."""
    parsed = analyze_logs._parse_dispatch_boundary_file(_UNMEASURED_FIXTURE)

    assert parsed['present'] is True
    rows = parsed['rows']
    assert len(rows) == 3
    # The legacy five columns are untouched by the representation change.
    assert [row['total_tokens'] for row in rows] == [90000, 70000, 50000]
    assert parsed['unknown_count'] == 0
    assert parsed['clean_exit_queue_empty_count'] == 2

    # Row 1 — a dispatch that forwarded no usage at all.
    for column in _CONTEXT_COLUMNS:
        assert column not in rows[0], column
    assert rows[0]['unmeasured_columns'] == list(_CONTEXT_COLUMNS)
    assert rows[0]['unrecognised_columns'] == []

    # Row 2 — three MEASURED zeros beside one column that was never measured.
    assert rows[1]['input_tokens'] == 0
    assert rows[1]['output_tokens'] == 0
    assert rows[1]['cache_read_input_tokens'] == 0
    assert 'cache_creation_input_tokens' not in rows[1]
    assert rows[1]['unmeasured_columns'] == ['cache_creation_input_tokens']

    # Row 3 — real measurements, a measured zero, and the same abstention.
    assert rows[2]['input_tokens'] == 4000
    assert rows[2]['output_tokens'] == 0
    assert rows[2]['cache_read_input_tokens'] == 120000
    assert rows[2]['unmeasured_columns'] == ['cache_creation_input_tokens']
    assert rows[2]['unrecognised_columns'] == []


def test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader():
    """The same file, through the `.claude` audit skill's independent reader.

    The two readers hand-mirror the same `data-format.md` contract from separate
    trees — one of them in a tree the architecture inventory does not crawl — so
    they are exercised against the SAME artifact here rather than each against
    its own.

    Every row of this fixture carries an `unmeasured` token, so every row is
    datable and the reader's fourth state (an UNDATABLE literal `0`) does not
    arise here — `undatable/` is the fixture that exercises it.
    """
    totals = audit._parse_dispatch_boundary_totals(_UNMEASURED_FIXTURE)

    # Summed over the rows that measured each column.
    assert totals['total_tokens'] == 90000 + 70000 + 50000
    assert totals['input_tokens'] == 4000
    assert totals['cache_read_input_tokens'] == 120000
    # A column measured as 0 on every row that measured it is PRESENT as 0 ...
    assert totals['output_tokens'] == 0
    # ... while a column no row ever measured is OMITTED, not returned as 0.
    # The two are the same integer and completely different facts.
    assert 'cache_creation_input_tokens' not in totals


def test_measured_zero_dispatch_column_is_present_as_zero(plan_context):
    """A measured `0` is still `0` — on the row, and in the result.

    The matched control for the test above: both rows sit in the SAME file, so a
    reader that collapsed the two representations would have to fail one of them.
    """
    scenario = _drive_scenario('repr-measured-zero')
    mixed_result = scenario['dispatch_results'][2]

    # The two measured zeros are present AS zeros ...
    assert mixed_result['input_tokens'] == 0
    assert mixed_result['cache_read_input_tokens'] == 0
    # ... and only the two genuinely unmeasured columns are withheld.
    assert 'output_tokens' not in mixed_result
    assert 'cache_creation_input_tokens' not in mixed_result
    assert mixed_result['unmeasured_context_load_columns'] == (
        'output_tokens,cache_creation_input_tokens'
    )

    rows = _data_rows(scenario['boundary_path'].read_text(encoding='utf-8'))
    assert rows[2].endswith(',clean_exit_queue_empty,45000,16,150000,0,unmeasured,0,unmeasured')
    # The fully measured first dispatch keeps all four values and declares nothing
    # unmeasured — the third point of the three-way distinction.
    assert rows[0].endswith(',budget_yield,60000,25,300000,38000,4000,210000,12000')
    assert scenario['dispatch_results'][0]['unmeasured_context_load_columns'] == ''


def test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader(plan_context):
    """The file the writer just produced round-trips through the real reader.

    Producer and consumer are pinned against each other on ONE artifact, so a
    representation change that moved only one of them would fail here.
    """
    scenario = _drive_scenario('repr-roundtrip')

    parsed = analyze_logs._parse_dispatch_boundary_file(scenario['boundary_path'])

    assert parsed['present'] is True
    rows = parsed['rows']
    assert len(rows) == 3

    measured, unmeasured, mixed = rows
    assert measured['input_tokens'] == 38000
    assert measured['cache_creation_input_tokens'] == 12000
    assert measured['unmeasured_columns'] == []
    assert measured['unrecognised_columns'] == []

    for column in _CONTEXT_COLUMNS:
        assert column not in unmeasured, column
    assert unmeasured['unmeasured_columns'] == list(_CONTEXT_COLUMNS)
    assert unmeasured['unrecognised_columns'] == []

    assert mixed['input_tokens'] == 0
    assert mixed['cache_read_input_tokens'] == 0
    assert 'output_tokens' not in mixed
    assert mixed['unmeasured_columns'] == ['output_tokens', 'cache_creation_input_tokens']
    assert mixed['unrecognised_columns'] == []


def test_verdict_is_published_under_the_end_time_predicate_key(plan_context):
    """The record names the predicate it computed, and emits no retired key.

    RED against pre-fix code, which published the same `end_time`-presence check
    under `partial` / `unrecorded_phases` — names that asserted a completeness
    verdict the check never performed.
    """
    scenario = _drive_scenario('repr-verdict-key')
    generated = scenario['generated']
    record = scenario['record']

    # Every canonical phase was closed, so the check reports the marker present.
    assert generated['any_phase_missing_end_time'] is False
    assert generated['phases_missing_end_time'] == []
    assert record['any_phase_missing_end_time'] == 'false'
    assert record['phases_missing_end_time'] == ''

    # Breaking rename, no dual-key shim: the retired pair appears nowhere — not
    # in the persisted record, not in the return, not in the rendered file.
    for retired in ('partial', 'unrecorded_phases'):
        assert retired not in record, retired
        assert retired not in generated, retired
    assert 'partial: false' not in scenario['metrics_toon']
    assert 'unrecorded_phases:' not in scenario['metrics_toon']
    assert 'Partial: unrecorded phases' not in scenario['metrics_md']
