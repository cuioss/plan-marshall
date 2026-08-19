#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan."""


from __future__ import annotations
from _record_model_representability_fixtures import (
    _CONTEXT_COLUMNS,
    _EXEC_CLOSE_ONE_TOKENS,
    _EXEC_CLOSE_TWO_TOKENS,
    _EXEC_CUMULATIVE_TOKENS,
    _data_rows,
    _drive_scenario,
    analyze_logs,
    manage_metrics,
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


def test_the_previously_impossible_row_now_states_what_it_measured(plan_context):
    """The exact case once certified `partial: false` while being impossible.

    The 5-execute row carries 125000 tokens against 0 tool uses, and its
    `start_time` names only the second entry. Pre-fix, the record's single
    published verdict was `partial: false` — a completeness claim over a row
    whose figures cannot be reconciled with its own timestamps. Post-fix, three
    separate facts are readable off the record, and none of them is a
    completeness claim:

      1. the verdict names the `end_time`-presence predicate and nothing wider;
      2. the row states that its total is a SUM across closes;
      3. the row states that its `start_time` covers only the latest close.
    """
    scenario = _drive_scenario('repr-impossible-row')
    exec_row = scenario['record']['phases']['5-execute']

    # (1) The only verdict the record publishes, and what it is keyed on.
    assert scenario['generated']['any_phase_missing_end_time'] is False
    assert '5-execute' not in scenario['generated']['phases_missing_end_time']

    # The row's own arithmetic: a non-zero token total against zero tool uses,
    # which the verdict above never looked at and no longer claims to have.
    assert exec_row['total_tokens'] == _EXEC_CUMULATIVE_TOKENS
    assert exec_row['tool_uses'] == 0

    # (2) + (3) The row declares the split, so the total is legible as a sum of
    # two closes rather than as one close's implausible figure.
    assert exec_row['close_count'] == 2
    assert exec_row['value_scope'] == manage_metrics.VALUE_SCOPE_MIXED
    assert 'total_tokens' in exec_row['cumulative_fields'].split(',')
    assert 'start_time' in exec_row['last_close_fields'].split(',')
    # The declared total genuinely differs from either close's own figure —
    # otherwise "it is cumulative" would be an unfalsifiable label.
    assert exec_row['total_tokens'] != _EXEC_CLOSE_ONE_TOKENS
    assert exec_row['total_tokens'] != _EXEC_CLOSE_TWO_TOKENS


def test_re_entered_row_declares_its_cumulative_vs_last_close_split(plan_context):
    """`value_scope` + the two field lists name the split, field by field.

    RED against pre-fix code, where the split existed only as prose in
    `data-format.md`: a script consumer reading a `close_count > 1` row off disk
    had no field-level signal telling it which values were sums.
    """
    scenario = _drive_scenario('repr-value-scope')
    record = scenario['record']
    exec_row = record['phases']['5-execute']

    assert exec_row['value_scope'] == 'mixed_cumulative_and_last_close'
    # The lists name only fields the row actually carries — no `agent_duration_ms`
    # here, because this scenario forwarded no `--duration-ms`.
    assert exec_row['cumulative_fields'] == 'close_count,duration_seconds,total_tokens,tool_uses'
    assert exec_row['last_close_fields'] == 'start_time,end_time'
    assert 'agent_duration_ms' not in exec_row

    # The negative control: a phase closed ONCE declares the split vacuous and
    # writes no field lists at all, so the mixed scope above is not unconditional.
    finalize_row = record['phases']['6-finalize']
    assert finalize_row['close_count'] == 1
    assert finalize_row['value_scope'] == 'single_close'
    assert 'cumulative_fields' not in finalize_row
    assert 'last_close_fields' not in finalize_row

    # The rendered report reads the row's OWN declaration rather than restating
    # the split from render-site knowledge.
    assert '**Closes**: 2' in scenario['metrics_md']
    assert (
        'Cumulative across closes: close_count,duration_seconds,total_tokens,tool_uses.'
        in scenario['metrics_md']
    )
    assert 'Latest close only: start_time,end_time.' in scenario['metrics_md']
