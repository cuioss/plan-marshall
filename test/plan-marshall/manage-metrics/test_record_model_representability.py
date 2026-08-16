#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan.

The three fixes this module composes were each pinned in isolation by their own
deliverable's unit tests. What no unit test can show is whether the RECORD — the
one artifact a downstream consumer actually reads — still asserts a value it did
not earn once all four shapes coexist on the same plan:

* a phase closed TWICE by a finalize loop-back, so some of its fields are sums
  across closes and others are scoped to the latest close;
* a finalize step fired ``loop_back`` -> ``loop_back`` -> ``done``, so its entry
  has three firings and only one ``outcome``;
* dispatch-boundary rows where some context-load flags were passed and some were
  not, so the same column is a measurement on one row and an abstention on
  another;
* denominators counted from live plan state, so every ratio the record supports
  names the moment its reference class was taken.

That composition is the case the spec named: a plan certified ``partial: false``
while being arithmetically impossible. This module drives it through the REAL
verbs — ``start-phase`` / ``phase-boundary`` / ``end-phase`` from
``manage-metrics``, ``record-dispatch-boundary`` from the same module,
``mark-step-done`` from ``manage-status``, then ``generate`` — and asserts on the
composed result.

**Evidence-assertion obligation.** This plan's subject is a class of records that
pass while proving nothing about what they measured, so its own tests must not
reproduce that shape. Every assertion below pins the concrete observed evidence —
a field's presence-vs-absence, its value, the firing count, the named predicate,
the sampling point — and never only a terminal pass/fail or a bare "no error
raised". A test that asserts only the outcome cannot distinguish a record that
stated its uncertainty from one that examined nothing.

Two fixture-backed companions close the reader side, where the archived history
lives and cannot be migrated:

* the new ``unmeasured/`` dispatch-boundary fixture carries unmeasured columns
  ALONGSIDE measured zeros on one file, and is read by BOTH the
  ``plan-retrospective`` reader and the ``.claude`` audit skill's ledger reader;
* the read-only ``legacy/`` five-column fixture is asserted byte-identical and
  still parses in both readers, proving the positional-backward-compatibility
  floor survived the representation change.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, get_script_path, load_script_module, parse_ns
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_phase_boundary,
    ns_record_dispatch_boundary,
    ns_start_phase,
)

# ---------------------------------------------------------------------------
# Modules under composition
# ---------------------------------------------------------------------------
#
# Three production surfaces, loaded the way each of their own test modules loads
# them. `manage-metrics.py` and `analyze-logs.py` have kebab-case filenames (not
# valid Python identifiers), so they come in through importlib by file location.

_METRICS_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
_metrics_spec = importlib.util.spec_from_file_location('manage_metrics_representability', _METRICS_PATH)
assert _metrics_spec is not None and _metrics_spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_metrics_spec)
_metrics_spec.loader.exec_module(manage_metrics)

cmd_start_phase = manage_metrics.cmd_start_phase
cmd_phase_boundary = manage_metrics.cmd_phase_boundary
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_generate = manage_metrics.cmd_generate
cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_representability_lifecycle'
)
_mark_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_mark_step.py', '_representability_mark_step'
)
_status_core = load_script_module(
    'plan-marshall', 'manage-status', '_status_core.py', '_representability_status_core'
)
cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status

_ANALYZE_LOGS_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'analyze-logs.py'
)
_analyze_spec = importlib.util.spec_from_file_location(
    'analyze_logs_representability', str(_ANALYZE_LOGS_PATH)
)
assert _analyze_spec is not None and _analyze_spec.loader is not None
analyze_logs = importlib.util.module_from_spec(_analyze_spec)
_analyze_spec.loader.exec_module(analyze_logs)

# The `.claude` audit skill is a project-local script, not a marketplace-bundle
# script, so `conftest.get_script_path` does not resolve it — its `scripts/` dir
# goes on sys.path directly. `import_module` (rather
# than a second file-location load) reuses the one canonical module instance, so
# the schema constants compared below are the same objects the reader returns.
_AUDIT_SCRIPTS_DIR = PROJECT_ROOT / '.claude' / 'skills' / 'audit-archived-plan-retrospectives' / 'scripts'
if str(_AUDIT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AUDIT_SCRIPTS_DIR))
audit = importlib.import_module('audit')


# ---------------------------------------------------------------------------
# The composed scenario's pinned magnitudes
# ---------------------------------------------------------------------------
#
# Named rather than inlined because several assertions below are ABOUT the
# relationship between them — the cumulative total is the sum of the two closes
# and therefore differs from either one, which is the whole reason the row has to
# declare which of its values are cumulative.

#: 5-execute's first close: the tokens the pre-loop-back run reported.
_EXEC_CLOSE_ONE_TOKENS = 80000
#: 5-execute's second close, after the finalize loop-back re-entered it.
_EXEC_CLOSE_TWO_TOKENS = 45000
#: What the row therefore holds — a SUM, not either close's own figure.
_EXEC_CUMULATIVE_TOKENS = _EXEC_CLOSE_ONE_TOKENS + _EXEC_CLOSE_TWO_TOKENS

#: The four per-dispatch context-load columns, in canonical order.
_CONTEXT_COLUMNS = (
    'input_tokens',
    'output_tokens',
    'cache_read_input_tokens',
    'cache_creation_input_tokens',
)

#: Dispatch 1 — every context-load flag supplied (a fully measured row).
_DISPATCH_MEASURED = {
    'input_tokens': 38000,
    'output_tokens': 4000,
    'cache_read_input_tokens': 210000,
    'cache_creation_input_tokens': 12000,
}
#: Dispatch 3 — a MEASURED ZERO on two columns and no flag at all on the other
#: two. The point of the row: `0` and "not measured" must not look alike.
_DISPATCH_MIXED = {'input_tokens': 0, 'cache_read_input_tokens': 0}

#: Denominator sources seeded into the plan dir, and the counts they must yield.
_DELIVERABLE_COUNT = 3
_AFFECTED_FILES = ['a.py', 'b.py', 'c.py', 'd.md', 'e.md']
_TASK_STATUSES = ['done', 'done', 'done', 'pending']
_COMPLETED_TASKS = 3

#: The finalize step driven three times. `automatic-review` declares
#: `head_dependent: true`, so its terminal `done` must carry a SHA — a `done`
#: with no anchor is refused and writes nothing, which would silently leave the
#: assertions reading the SECOND firing.
_STEP = 'automatic-review'
_HEAD_SHA = 'e' * 40


# ---------------------------------------------------------------------------
# Namespace builders
# ---------------------------------------------------------------------------


def _ns_dispatch(
    plan_id: str,
    termination_cause: str,
    total_tokens: int,
    tool_uses: int,
    duration_ms: int,
    context_load: dict[str, int],
) -> Namespace:
    """Build a `record-dispatch-boundary` Namespace from the script's own parser.

    A context-load column absent from *context_load* is left at the parser's own
    default for an omitted flag, so the namespace matches what the real CLI
    produces; the writer reads the column back with `getattr(args, column, None)`.
    """
    return ns_record_dispatch_boundary(
        plan_id,
        '5-execute',
        termination_cause,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
        **context_load,
    )


def _ns_mark_step(
    plan_id: str,
    outcome: str,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    """A `mark-step-done` namespace from manage-status.py's own parser."""
    argv = [
        'mark-step-done', '--plan-id', plan_id, '--phase', '6-finalize',
        '--step', _STEP, '--outcome', outcome,
    ]
    if force:
        argv.append('--force')
    for flag, value in (
        ('--display-detail', display_detail),
        ('--head-at-completion', head_at_completion),
        ('--loop-back-target', loop_back_target),
    ):
        if value is not None:
            argv += [flag, value]
    parsed: Namespace = parse_ns('plan-marshall', 'manage-status', 'manage-status.py', *argv)
    return parsed


# ---------------------------------------------------------------------------
# Scenario construction
# ---------------------------------------------------------------------------


def _seed_denominator_sources(plan_dir: Path) -> None:
    """Write the three live sources `generate` counts its denominators from.

    Each is a MOVING quantity in production, which is why the record has to name
    the moment it read them; here they are pinned so the counts are checkable.
    """
    outline = ['# Solution: composed representability fixture', '', '## Deliverables', '']
    for index in range(1, _DELIVERABLE_COUNT + 1):
        outline.append(f'### {index}. Deliverable {index}')
        outline.append('')
    (plan_dir / 'solution_outline.md').write_text('\n'.join(outline) + '\n', encoding='utf-8')

    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'affected_files': _AFFECTED_FILES}), encoding='utf-8'
    )

    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for index, status in enumerate(_TASK_STATUSES, start=1):
        (tasks_dir / f'TASK-{index:03d}.json').write_text(
            json.dumps({'number': index, 'status': status}), encoding='utf-8'
        )


def _drive_scenario(plan_id: str) -> dict[str, Any]:
    """Drive the whole plan through the real verbs and return everything observed.

    Every verb call's `status` is asserted here rather than in the individual
    tests. A refused write returns an error dict and writes NOTHING, so an
    unasserted failure downstream would leave a later assertion reading an
    earlier state and reporting a defect that is really a setup fault.
    """
    _make_plan(plan_id)
    plan_dir = Path(manage_metrics.get_plan_dir(plan_id))
    _seed_denominator_sources(plan_dir)

    assert cmd_start_phase(ns_start_phase(plan_id, '1-init'))['status'] == 'success'
    # The three inline boundaries close usage-free — the sanctioned inline
    # recording mode, and the reason `end_time` presence is the only thing the
    # renamed verdict may claim to have checked.
    for prev_phase, next_phase in (
        ('1-init', '2-refine'),
        ('2-refine', '3-outline'),
        ('3-outline', '4-plan'),
    ):
        assert cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase, next_phase))['status'] == 'success'
    assert (
        cmd_phase_boundary(
            ns_phase_boundary(plan_id, '4-plan', '5-execute', total_tokens=52000, tool_uses=18)
        )['status']
        == 'success'
    )

    # Three phase-5 dispatch terminations: fully measured, wholly unmeasured, and
    # a per-column mix carrying two measured zeros.
    dispatch_results = [
        cmd_record_dispatch_boundary(
            _ns_dispatch(plan_id, 'budget_yield', 60000, 25, 300000, _DISPATCH_MEASURED)
        ),
        cmd_record_dispatch_boundary(_ns_dispatch(plan_id, 'budget_yield', 20000, 9, 90000, {})),
        cmd_record_dispatch_boundary(
            _ns_dispatch(plan_id, 'clean_exit_queue_empty', 45000, 16, 150000, _DISPATCH_MIXED)
        ),
    ]
    for result in dispatch_results:
        assert result['status'] == 'success', result

    # 5-execute closes for the FIRST time. tool_uses is a measured 0 alongside a
    # non-zero token total — the row shape the old `partial: false` certified.
    assert (
        cmd_phase_boundary(
            ns_phase_boundary(
                plan_id, '5-execute', '6-finalize', total_tokens=_EXEC_CLOSE_ONE_TOKENS, tool_uses=0
            )
        )['status']
        == 'success'
    )
    assert (
        cmd_mark_step_done(
            _ns_mark_step(
                plan_id,
                'loop_back',
                display_detail='findings round 1',
                loop_back_target='5-execute',
            )
        )['status']
        == 'success'
    )

    # The loop-back re-enters 5-execute and closes it a SECOND time.
    assert cmd_start_phase(ns_start_phase(plan_id, '5-execute'))['status'] == 'success'
    assert (
        cmd_phase_boundary(
            ns_phase_boundary(
                plan_id, '5-execute', '6-finalize', total_tokens=_EXEC_CLOSE_TWO_TOKENS, tool_uses=0
            )
        )['status']
        == 'success'
    )
    assert (
        cmd_mark_step_done(
            _ns_mark_step(
                plan_id,
                'loop_back',
                force=True,
                display_detail='findings round 2',
                loop_back_target='6-finalize',
            )
        )['status']
        == 'success'
    )
    assert (
        cmd_mark_step_done(
            _ns_mark_step(
                plan_id,
                'done',
                force=True,
                display_detail='clean',
                head_at_completion=_HEAD_SHA,
            )
        )['status']
        == 'success'
    )

    assert (
        cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=31000, tool_uses=12))['status']
        == 'success'
    )

    generated = cmd_generate(ns_generate(plan_id))
    assert generated['status'] == 'success', generated

    return {
        'plan_id': plan_id,
        'plan_dir': plan_dir,
        'dispatch_results': dispatch_results,
        'generated': generated,
        'record': manage_metrics.read_metrics_raw(plan_id),
        'metrics_toon_path': plan_dir / 'work' / 'metrics.toon',
        'metrics_toon': (plan_dir / 'work' / 'metrics.toon').read_text(encoding='utf-8'),
        'metrics_md': (plan_dir / 'metrics.md').read_text(encoding='utf-8'),
        'boundary_path': plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon',
        'step_entry': read_status(plan_id)['metadata']['phase_steps']['6-finalize'][_STEP],
    }


def _make_plan(plan_id: str) -> None:
    result = cmd_create(
        parse_ns(
            'plan-marshall', 'manage-status', 'manage-status.py', 'create',
            '--plan-id', plan_id,
            '--title', 'Record model representability',
            '--phases', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
        )
    )
    assert result['status'] == 'success', result


def _data_rows(content: str) -> list[str]:
    """Return only the dispatch-boundary data rows, skipping the TOON header."""
    return [
        line
        for line in content.splitlines()
        if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
    ]


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
#
# Archived `metrics.toon` files are immutable history that still carry the
# retired keys. The reader must report that state EXPLICITLY — never default it,
# never read it as a clean verdict, and never fold it into the pre-#812 bucket,
# which is a different fact about a different corpus.

_PHASE_BODY = '[4-plan]\n  total_tokens: 100\n[5-execute]\n  total_tokens: 0\n'
_CURRENT_CLEAN = 'any_phase_missing_end_time: false\nphases_missing_end_time: \n' + _PHASE_BODY
_OLD_SCHEMA = 'partial: true\nunrecorded_phases: 5-execute\n' + _PHASE_BODY
_PRE_812 = _PHASE_BODY


def _archived_plan(repo_root: Path, body: str) -> Any:
    """Stage a one-plan archived corpus whose metrics.toon carries *body*."""
    plan_dir = repo_root / '.plan' / 'local' / 'archived-plans' / 'sample-plan'
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text('{"scope_estimate": "surgical"}', encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding='utf-8'
    )
    (plan_dir / 'work' / 'metrics.toon').write_text(body, encoding='utf-8')
    return audit.collect_inputs(plan_dir)


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


def _write_metrics(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name / 'metrics.toon'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


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

_FIXTURES_DIR = (
    PROJECT_ROOT / 'test' / 'plan-marshall' / 'plan-retrospective' / 'fixtures' / 'dispatch-loop-replay'
)
_UNMEASURED_FIXTURE = _FIXTURES_DIR / 'unmeasured' / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
_LEGACY_FIXTURE = _FIXTURES_DIR / 'legacy' / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'

#: The legacy fixture's exact bytes. Pinned as a literal rather than compared
#: against itself: the claim is that the file did NOT change across the
#: representation change, and a file compared only to itself can never falsify
#: that.
_LEGACY_FIXTURE_BYTES = (
    'plan_id: dispatch-loop-replay-legacy\n'
    'phase: 5-execute\n'
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
    '2026-04-15T09:00:00Z,unknown,80000,40,90000\n'
)


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


def test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader():
    """The same file, through the `.claude` audit skill's independent reader.

    The two readers hand-mirror the same `data-format.md` contract from separate
    trees — one of them in a tree the architecture inventory does not crawl — so
    they are exercised against the SAME artifact here rather than each against
    its own.
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
