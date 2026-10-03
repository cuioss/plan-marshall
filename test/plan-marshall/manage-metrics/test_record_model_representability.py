#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan."""

from __future__ import annotations
from pathlib import Path
from typing import Any

from _record_model_representability_fixtures import (
    _AFFECTED_FILES,
    _COMPLETED_TASKS,
    _CONTEXT_COLUMNS,
    _DELIVERABLE_COUNT,
    _EXEC_CLOSE_ONE_TOKENS,
    _EXEC_CLOSE_TWO_TOKENS,
    _EXEC_CUMULATIVE_TOKENS,
    _HEAD_SHA,
    _LEGACY_FIXTURE,
    _LEGACY_FIXTURE_BYTES,
    _UNDATABLE_FIXTURE,
    _UNDATABLE_FIXTURE_BYTES,
    _drive_scenario,
    analyze_logs,
    manage_metrics,
)


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
    assert 'Cumulative across closes: close_count,duration_seconds,total_tokens,tool_uses.' in scenario['metrics_md']
    assert 'Latest close only: start_time,end_time.' in scenario['metrics_md']


def test_multiply_fired_finalize_step_retains_every_firing(plan_context):
    """The finalize step fired three times, and the entry keeps all three.

    RED against pre-fix code, where `phase_entry[step] = new_entry` retained only
    the terminal `done` and both loop-backs (with their targets) were discarded.
    """
    scenario = _drive_scenario('repr-firings')
    entry = scenario['step_entry']

    # `outcome` still means the LATEST firing and keeps its historical meaning.
    assert entry['outcome'] == 'done'
    assert entry['display_detail'] == 'clean'
    assert entry['head_at_completion'] == _HEAD_SHA
    # A `done` carries no loop_back_target — the key is absent, not stale.
    assert 'loop_back_target' not in entry

    # Both superseded firings survive, oldest first, each naming its own target.
    assert entry['firing_count'] == 3
    assert entry['prior_firings'] == [
        {'outcome': 'loop_back', 'loop_back_target': '5-execute'},
        {'outcome': 'loop_back', 'loop_back_target': '6-finalize'},
    ]


def test_every_persisted_denominator_carries_its_sampling_point(plan_context):
    """Each count lands beside the moment it was taken — never on its own.

    RED against pre-fix code, which persisted numerators only, so every ratio the
    report showed rested on a denominator the record never held and never dated.
    """
    scenario = _drive_scenario('repr-denominators')
    record = scenario['record']
    generated = scenario['generated']

    # The counts are the seeded ones, so the pairing is checked against real
    # values rather than against whatever happened to be written.
    assert record['deliverable_count'] == str(_DELIVERABLE_COUNT)
    assert record['files_modified'] == str(len(_AFFECTED_FILES))
    assert record['tasks_completed'] == str(_COMPLETED_TASKS)

    for name in manage_metrics._DENOMINATOR_FIELDS:
        sampling_point = record[f'{name}_sampling_point']
        assert sampling_point == manage_metrics.SAMPLING_POINT_GENERATE_TIME
        assert sampling_point in manage_metrics.SAMPLING_POINTS
        # The return echoes the same pair the record holds.
        assert generated[f'{name}_sampling_point'] == sampling_point

    # One shared instant names WHEN this call counted them.
    assert record['denominators_sampled_at']
    assert generated['denominators_sampled_at'] == record['denominators_sampled_at']


def test_legacy_fixture_is_byte_identical():
    """The five-column fixture did not move when the representation changed."""
    assert _LEGACY_FIXTURE.read_text(encoding='utf-8') == _LEGACY_FIXTURE_BYTES


def test_legacy_fixture_still_parses_in_the_retrospective_reader():
    """The positional-backward-compatibility floor survives in the reader.

    A row written before the four columns existed recorded no context-load
    measurement at all, so the reader keeps the row AND reports those four as
    unmeasured — never as a measured `0`, which would inject four fabricated
    measurements into every archived plan.
    """
    parsed = analyze_logs._parse_dispatch_boundary_file(_LEGACY_FIXTURE)

    assert parsed['present'] is True
    assert len(parsed['rows']) == 1
    row = parsed['rows'][0]
    # Legacy five columns unchanged.
    assert row['termination_cause'] == 'unknown'
    assert row['total_tokens'] == 80000
    assert row['tool_uses'] == 40
    assert row['duration_ms'] == 90000
    # Four appended columns absent, and reported as unmeasured rather than
    # unrecognised — the row is well-formed, it simply predates the columns.
    for column in _CONTEXT_COLUMNS:
        assert column not in row, column
    assert row['unmeasured_columns'] == list(_CONTEXT_COLUMNS)
    assert row['unrecognised_columns'] == []


def test_undatable_fixture_carries_no_post_token_fingerprint():
    """The fixture is the pre-token writer's shape: nine columns, all zeros.

    Asserted on the BYTES rather than through the reader, so the premise the
    reader test below rests on — that nothing in this file dates it to the
    current writer — is established independently of the code under test.
    """
    assert _UNDATABLE_FIXTURE.read_text(encoding='utf-8') == _UNDATABLE_FIXTURE_BYTES
    assert 'unmeasured' not in _UNDATABLE_FIXTURE_BYTES


def test_undatable_zeros_are_not_measurements_in_the_retrospective_reader():
    """An undatable `0` is not a measurement.

    The retrospective reader names the state per column
    (`indeterminate_columns`) and keeps the legacy five columns, which sit
    outside the datability gate.
    """
    parsed = analyze_logs._parse_dispatch_boundary_file(_UNDATABLE_FIXTURE)

    assert parsed['present'] is True
    assert len(parsed['rows']) == 2
    for row in parsed['rows']:
        for column in _CONTEXT_COLUMNS:
            assert column not in row, column
        assert row['indeterminate_columns'] == list(_CONTEXT_COLUMNS)
        # Never folded into either neighbour: the writer made no statement, and
        # the reader parsed the cells fine.
        assert row['unmeasured_columns'] == []
        assert row['unrecognised_columns'] == []

    # The legacy five columns are outside the gate and still read.
    assert [row['total_tokens'] for row in parsed['rows']] == [90000, 70000]


# =============================================================================
# Divergence-class fixtures: the header, not the position, names a column
# =============================================================================
#
# The retrospective reader resolves the four context-load columns BY NAME from
# the declared `rows[]{...}:` header. Name-resolution and position-resolution
# agree on every artifact the current writer produces, because the writer emits
# the canonical order; they come apart exactly where a header disagrees with the
# canonical position — and there a positional reader yields a different measured
# set and a different datability verdict from the same bytes.
#
# One fixture per divergence class, each asserting the concrete measured values
# the header-name resolution yields. The cross-plan auditor's ledger reader
# mirrors the same contract from the `plan-marshall-telemetry` repository, where
# its half of these classes is pinned.

#: The canonical ten-column header, in the order the writer emits.
_DIVERGENCE_CANONICAL_HEADER = (
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens,step_id}:\n'
)

#: (a) A header declaring only the legacy five, above a row carrying all nine.
_SHORT_HEADER_BYTES = (
    'plan_id: divergence-short-header\n'
    'phase: 5-execute\n'
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
    '2026-07-01T09:00:00Z,clean_exit_queue_empty,50000,20,120000,38000,4000,210000,12000\n'
)

#: (b) A corrupt legacy `total_tokens` beside a NONZERO context-load cell.
_MALFORMED_LEGACY_BYTES = (
    'plan_id: divergence-malformed-legacy\n'
    'phase: 5-execute\n'
    + _DIVERGENCE_CANONICAL_HEADER
    + '2026-07-01T09:00:00Z,clean_exit_queue_empty,not-an-int,7,30000,9100,0,0,0,\n'
)

#: (c) No `rows[]{...}:` header line at all — nothing declares what the cells mean.
_NO_HEADER_BYTES = (
    'plan_id: divergence-no-header\n'
    'phase: 5-execute\n'
    '2026-07-01T09:00:00Z,clean_exit_queue_empty,50000,20,120000,38000,4000,210000,12000\n'
)

#: (d) A header REORDERING the last two context columns. The cells follow the
#: header, so name-resolution and position-resolution disagree on exactly those
#: two — and the two values are far apart, so a transposition cannot pass.
_REORDERED_HEADER_BYTES = (
    'plan_id: divergence-reordered-header\n'
    'phase: 5-execute\n'
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}:\n'
    '2026-07-01T09:00:00Z,clean_exit_queue_empty,50000,20,120000,38000,4000,12000,210000\n'
)


def _write_divergence_fixture(tmp_path: Path, name: str, body: str) -> Path:
    """Materialise one divergence-class artifact and return its path."""
    path = tmp_path / name / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _measured_context(parsed: dict[str, Any]) -> dict[str, int]:
    """The context-load columns the reader measured, with their values.

    Presence-keyed, because the reader signals "not measured" by OMITTING the
    key — for an unmeasured, an unrecognised and an indeterminate cell alike.
    Compared as a whole MAPPING, not just a key set, which is what catches a
    reader that measured the right columns with the wrong values: precisely the
    reordered-header case, where all four columns read as measured and only the
    values betray a transposition.
    """
    return {column: row[column] for row in parsed['rows'] for column in _CONTEXT_COLUMNS if column in row}


def test_short_header_leaves_undeclared_columns_unmeasured(tmp_path):
    """(a) A header narrower than its rows: the undeclared cells measure NOTHING.

    The header declares only the legacy five, so the four trailing cells are
    values that no column name claims. The reader declines them — reading them
    would attribute four measurements to columns the file never said it was
    recording, which is what a positional read of cells 5-8 does.
    """
    path = _write_divergence_fixture(tmp_path, 'short-header', _SHORT_HEADER_BYTES)

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    # No context-load column is measured ...
    assert _measured_context(parsed) == {}
    # ... and the reader files them as UNMEASURED rather than unrecognised: an
    # undeclared column is one the row states nothing about, not a cell the
    # reader tried and failed to parse.
    assert len(parsed['rows']) == 1
    row = parsed['rows'][0]
    assert row['unmeasured_columns'] == list(_CONTEXT_COLUMNS)
    assert row['unrecognised_columns'] == []
    assert row['indeterminate_columns'] == []

    # The five columns the header DOES declare still read — the row is kept, not
    # discarded for being wider than its header.
    assert row['total_tokens'] == 50000
    assert row['tool_uses'] == 20
    assert row['duration_ms'] == 120000


def test_corrupt_legacy_cell_keeps_its_row_readable(tmp_path):
    """(b) A corrupt `total_tokens` must not discard the row's context-load cells.

    The legacy five carry a numeric default and predate the `unmeasured` token, so
    a corrupt cell there degrades to `0` — the one place a default is correct,
    because those columns cannot abstain. What must NOT happen is losing the rest
    of the row with it: this row's `9100` is a real measurement the reader parsed
    perfectly well.
    """
    path = _write_divergence_fixture(tmp_path, 'malformed-legacy', _MALFORMED_LEGACY_BYTES)

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert _measured_context(parsed) == {
        'input_tokens': 9100,
        'output_tokens': 0,
        'cache_read_input_tokens': 0,
        'cache_creation_input_tokens': 0,
    }

    # The row survived its corrupt legacy cell.
    assert len(parsed['rows']) == 1
    row = parsed['rows'][0]

    # The nonzero cell is measured — and it DATES the row, so its three sibling
    # zeros are genuine measured zeros rather than undatable ones.
    assert row['input_tokens'] == 9100
    assert row['output_tokens'] == 0
    assert row['cache_read_input_tokens'] == 0
    assert row['cache_creation_input_tokens'] == 0
    assert row['indeterminate_columns'] == []
    assert row['unmeasured_columns'] == []
    assert row['unrecognised_columns'] == []

    # The corrupt legacy cell degrades to 0 ...
    assert row['total_tokens'] == 0
    # ... and its intact legacy neighbours are untouched by that degrade.
    assert row['tool_uses'] == 7
    assert row['duration_ms'] == 30000


def test_missing_header_measures_nothing(tmp_path):
    """(c) With no `rows[]{...}:` header, no cell has a declared meaning.

    Column names come from the header; a file carrying none declares nothing, so
    the reader may not attribute its cells to columns. It reports an empty
    measured set rather than falling back on the canonical order — a guess that
    would be indistinguishable from a measurement.
    """
    path = _write_divergence_fixture(tmp_path, 'no-header', _NO_HEADER_BYTES)

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert _measured_context(parsed) == {}

    # The file EXISTS — this is not the absent-artifact path — and still yields no
    # rows. "Present but undeclared" and "missing" are different facts, and only
    # the first one keeps `present` True.
    assert parsed['present'] is True
    assert parsed['rows'] == []
    assert parsed['clean_exit_queue_empty_count'] == 0
    assert parsed['unknown_count'] == 0


def test_reordered_header_is_read_by_name_not_by_position(tmp_path):
    """(d) A header that reorders two columns must not transpose their values.

    The header declares `cache_creation_input_tokens` BEFORE
    `cache_read_input_tokens` and the cells follow the header, so name-resolution
    and position-resolution disagree on exactly these two columns. The two
    magnitudes are deliberately far apart so a transposition cannot pass
    unnoticed.
    """
    path = _write_divergence_fixture(tmp_path, 'reordered-header', _REORDERED_HEADER_BYTES)

    parsed = analyze_logs._parse_dispatch_boundary_file(path)

    assert _measured_context(parsed) == {
        'input_tokens': 38000,
        'output_tokens': 4000,
        'cache_read_input_tokens': 210000,
        'cache_creation_input_tokens': 12000,
    }

    assert len(parsed['rows']) == 1
    row = parsed['rows'][0]
    # Each value lands under the name the HEADER gave it ...
    assert row['cache_read_input_tokens'] == 210000
    assert row['cache_creation_input_tokens'] == 12000
    # ... and the two are genuinely distinct, so this assertion is falsifiable by
    # exactly the transposition a positional reader produces.
    assert row['cache_read_input_tokens'] != row['cache_creation_input_tokens']

    # The two columns the reorder did not touch are unaffected, so the fixture
    # isolates the reorder rather than perturbing the whole row.
    assert row['input_tokens'] == 38000
    assert row['output_tokens'] == 4000
    assert row['unmeasured_columns'] == []
    assert row['unrecognised_columns'] == []
    assert row['indeterminate_columns'] == []
