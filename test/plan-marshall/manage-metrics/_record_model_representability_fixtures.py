#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Shared preamble for the ``record model representability`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

End-to-end regression over a re-entered, multiply-fired, partly-unmeasured, denominated plan.

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
reproduce that shape. Every assertion pins the concrete observed evidence —
a field's presence-vs-absence, its value, the firing count, the named predicate,
the sampling point — and never only a terminal pass/fail or a bare "no error
raised". A test that asserts only the outcome cannot distinguish a record that
stated its uncertainty from one that examined nothing.

Fixture-backed companions close the reader side, where the archived history lives
and cannot be migrated. Each is read by BOTH the ``plan-retrospective`` reader and
the ``.claude`` audit skill's ledger reader, which hand-mirror one contract from
separate trees, so a change that moved only one of them fails here:

* the ``unmeasured/`` dispatch-boundary fixture carries unmeasured columns
  ALONGSIDE measured zeros on one file;
* the ``undatable/`` fixture carries the pre-token writer's shape — nine columns,
  every context-load cell a literal ``0``, nothing on the row dating it — so both
  readers must decline to report those zeros as measurements;
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
# the schema constants compared against are the same objects the reader returns.
_AUDIT_SCRIPTS_DIR = PROJECT_ROOT / '.claude' / 'skills' / 'audit-archived-plan-retrospectives' / 'scripts'


if str(_AUDIT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AUDIT_SCRIPTS_DIR))


audit = importlib.import_module('audit')


# ---------------------------------------------------------------------------
# The composed scenario's pinned magnitudes
# ---------------------------------------------------------------------------
#
# Named rather than inlined because several assertions are ABOUT the
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


def _write_metrics(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name / 'metrics.toon'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


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


# =============================================================================
# The undatable-zero fixture: one artifact, both readers, one provenance gate
# =============================================================================

_UNDATABLE_FIXTURE = (
    _FIXTURES_DIR / 'undatable' / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
)


#: The undatable fixture's exact bytes — the pre-token writer's row shape, which
#: defaulted every omitted context-load column to a literal `0`. Pinned as a
#: literal because the claim under test is what THESE bytes mean; a fixture
#: compared only to itself could never falsify a drift in them.
_UNDATABLE_FIXTURE_BYTES = (
    'plan_id: dispatch-loop-replay-undatable\n'
    'phase: 5-execute\n'
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
    '2026-03-02T09:00:00Z,clean_exit_queue_empty,90000,45,100000,0,0,0,0\n'
    '2026-03-02T09:05:00Z,clean_exit_queue_empty,70000,30,80000,0,0,0,0\n'
)
