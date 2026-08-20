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
    _EXEC_CLOSE_ONE_TOKENS,
    _EXEC_CLOSE_TWO_TOKENS,
    _EXEC_CUMULATIVE_TOKENS,
    _HEAD_SHA,
    _LEGACY_FIXTURE,
    _LEGACY_FIXTURE_BYTES,
    _OLD_SCHEMA,
    _PHASE_BODY,
    _PRE_812,
    _UNDATABLE_FIXTURE,
    _UNDATABLE_FIXTURE_BYTES,
    _archived_plan,
    _drive_scenario,
    _write_metrics,
    analyze_logs,
    audit,
    manage_metrics,
)


# =============================================================================
# The composed record: no field asserts an unearned value
# =============================================================================

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


# =============================================================================
# Companion: an OLD-schema archived record, distinguishable from both neighbours
# =============================================================================

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


# =============================================================================
# Fixtures: one file carrying both representations, and the legacy floor
# =============================================================================

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


# =============================================================================
# The undatable-zero fixture: one artifact, both readers, one provenance gate
# =============================================================================

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
