#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan."""


from __future__ import annotations
from _record_model_representability_fixtures import (
    _AFFECTED_FILES,
    _COMPLETED_TASKS,
    _CONTEXT_COLUMNS,
    _CURRENT_CLEAN,
    _DELIVERABLE_COUNT,
    _HEAD_SHA,
    _LEGACY_FIXTURE,
    _LEGACY_FIXTURE_BYTES,
    _OLD_SCHEMA,
    _PHASE_BODY,
    _PRE_812,
    _UNDATABLE_FIXTURE,
    _UNDATABLE_FIXTURE_BYTES,
    _UNMEASURED_FIXTURE,
    _archived_plan,
    _drive_scenario,
    _write_metrics,
    analyze_logs,
    audit,
    manage_metrics,
)


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


def test_the_generated_record_reads_as_current_schema_in_the_archived_reader(plan_context):
    """The producer's own output satisfies the archived-history reader.

    Closes the loop the rename opened: `generate` writes the new keys and the
    audit skill's three-state reader must classify that file as `current` — not
    as one of the two unreadable states, which would floor every figure derived
    from a freshly written record.
    """
    scenario = _drive_scenario('repr-audit-current')

    presence = audit.parse_metrics_end_time_presence(scenario['metrics_toon_path'])

    assert presence.schema == audit.METRICS_SCHEMA_CURRENT
    assert presence.readable is True
    assert presence.any_phase_missing_end_time is False
    assert presence.phases_missing_end_time == frozenset()
    assert presence.forces_floor is False
    assert presence.unreadable_note == ''


def test_old_schema_record_is_distinct_from_a_clean_verdict_and_from_pre_812(tmp_path):
    """Three records, three verdicts, no two of them equal.

    Asserted as a THREE-way comparison rather than three independent single-file
    assertions, because the defect being ruled out is precisely a collapse: the
    pre-rename reader degraded an absent key to `(False, set())`, so old-schema
    and pre-#812 would both have read as clean.
    """
    clean = audit.parse_metrics_end_time_presence(_write_metrics(tmp_path, 'clean', _CURRENT_CLEAN))
    old = audit.parse_metrics_end_time_presence(_write_metrics(tmp_path, 'old', _OLD_SCHEMA))
    pre = audit.parse_metrics_end_time_presence(_write_metrics(tmp_path, 'pre', _PRE_812))

    # The three schemas are pairwise distinct.
    assert {clean.schema, old.schema, pre.schema} == {
        audit.METRICS_SCHEMA_CURRENT,
        audit.METRICS_SCHEMA_OLD,
        audit.METRICS_SCHEMA_PRE_812,
    }

    # The clean record is the ONE state that yields a verdict and no floor.
    assert clean.readable is True
    assert clean.any_phase_missing_end_time is False
    assert clean.forces_floor is False
    assert clean.unreadable_note == ''

    # The old-schema record names 5-execute under the retired keys, and the
    # reader still refuses to read a value out of it.
    assert old.readable is False
    assert old.any_phase_missing_end_time is None
    assert old.phases_missing_end_time is None
    assert old.explained_phases == frozenset()
    assert old.forces_floor is True
    assert 'old-schema' in old.unreadable_note

    # The pre-#812 record is the legitimate historical degrade, and says so in
    # wording that cannot be mistaken for the old-schema note.
    assert pre.readable is False
    assert pre.forces_floor is True
    assert 'pre-#812' in pre.unreadable_note
    assert 'old-schema' not in pre.unreadable_note


def test_old_schema_record_does_not_buy_a_zero_token_phase_out_of_blind(tmp_path):
    """The retired keys explain nothing at the check level either.

    Same zero-token 5-execute in all three corpora, so the difference in verdict
    is traceable to the marker schema and to nothing else.
    """
    clean_marked = audit.check_input_integrity(
        _archived_plan(
            tmp_path / 'marked',
            'any_phase_missing_end_time: true\nphases_missing_end_time: 5-execute\n' + _PHASE_BODY,
        )
    )
    old_schema = audit.check_input_integrity(_archived_plan(tmp_path / 'old', _OLD_SCHEMA))

    # A CURRENT marker explains the zero-token execute — `partial`, never blind.
    assert clean_marked['metrics_marker_schema'] == audit.METRICS_SCHEMA_CURRENT
    assert clean_marked['data_confidence'] == 'partial'
    assert '5-execute' not in clean_marked['metrics_blind']

    # The retired keys do not, and the bucket names which unreadable state it was.
    assert old_schema['metrics_marker_schema'] == audit.METRICS_SCHEMA_OLD
    assert old_schema['data_confidence'] == 'blind'
    assert '5-execute' in old_schema['metrics_blind']


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


def test_legacy_fixture_is_byte_identical():
    """The five-column fixture did not move when the representation changed."""
    assert _LEGACY_FIXTURE.read_text(encoding='utf-8') == _LEGACY_FIXTURE_BYTES


def test_legacy_fixture_still_parses_in_both_readers():
    """The positional-backward-compatibility floor survived, in both readers.

    A row written before the four columns existed recorded no context-load
    measurement at all, so both readers must keep the row AND report those four
    as unmeasured — never as a measured `0`, which would inject four fabricated
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

    totals = audit._parse_dispatch_boundary_totals(_LEGACY_FIXTURE)
    assert totals['total_tokens'] == 80000
    for column in _CONTEXT_COLUMNS:
        assert column not in totals, column


def test_undatable_fixture_carries_no_post_token_fingerprint():
    """The fixture is the pre-token writer's shape: nine columns, all zeros.

    Asserted on the BYTES rather than through either reader, so the premise both
    reader tests below rest on — that nothing in this file dates it to the
    current writer — is established independently of the code under test.
    """
    assert _UNDATABLE_FIXTURE.read_text(encoding='utf-8') == _UNDATABLE_FIXTURE_BYTES
    assert 'unmeasured' not in _UNDATABLE_FIXTURE_BYTES


def test_undatable_zeros_are_not_measurements_in_either_reader():
    """One artifact, both readers, one verdict: an undatable `0` is not measured.

    The two readers parse the same on-disk ledger from separate trees and cannot
    share a constant, so they are exercised against the SAME file here. The
    retrospective reader names the state per column (`indeterminate_columns`);
    the audit ledger reader sums rather than emitting per-row states, so the same
    verdict surfaces there as the field's ABSENCE from the totals. A change that
    moved only one reader fails this test.
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

    totals = audit._parse_dispatch_boundary_totals(_UNDATABLE_FIXTURE)

    # The legacy five columns are outside the gate and still sum.
    assert totals['total_tokens'] == 90000 + 70000
    # ABSENT, not `0` — the same fact the retrospective reader names
    # `indeterminate`, in the shape this reader can express.
    for column in _CONTEXT_COLUMNS:
        assert column not in totals, column
