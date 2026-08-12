#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the dispatch-record emission seam in ``effort resolve-target``.

The dispatch audit's evidence used to be a HAND-WRITTEN ``manage-logging work``
``[DISPATCH]`` line placed once per role in a workflow doc, so a step that
re-fired N times logged once (or not at all). Moving the emission INTO
``resolve-target`` — the single script call every execution-context dispatch
makes to compute its target — makes the record ride the resolve: every firing
resolves, so every firing emits, PER FIRING rather than once per role.

These tests drive the new ``--workflow`` / ``--plan-id`` / ``--caller`` input
shape through the CLI entry point (per the plugin-script-architecture
"new input shape's first boundary test is a CLI test" rule) and read the
emitted records back through ``plan_logging`` (same path resolution as the
write), asserting:

- (D3b) a resolve that previously emitted nothing now emits;
- (D3a) a re-fired step (the observed five-fire shape) emits one record per fire;
- (D3c) a role fired N times produces N records, not one;
- (D3d) the emission's population is non-empty and the emission set equals the
  envelope (resolve) set, field-for-field;
- (D2)  both audit surfaces (decision-log resolve record + work-log [DISPATCH]
  line) are written from the ONE seam, so they share an emitter;
- backward-compat: a bare resolve with no ``--workflow`` still emits nothing.
"""

import json

from plan_logging import read_decision_log, read_work_log
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')

_WORKFLOW = 'plan-marshall:phase-5-execute/SKILL.md'
_CALLER = 'plan-marshall:plan-marshall'


def _init_plan(plan_context, plan_id: str) -> None:
    """Create an initialized plan dir (status.json sentinel) in the plans store."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': plan_id}), encoding='utf-8')


def _seed_marshal(plan_context) -> None:
    """Write a minimal initialized marshal.json so ``resolve-target`` resolves."""
    from test_helpers import create_marshal_json

    create_marshal_json(plan_context.fixture_dir)


def _resolve(plan_id: str, *extra: str):
    """Run ``effort resolve-target`` through the CLI with the seam-emission args."""
    return run_script(
        SCRIPT_PATH,
        'effort',
        'resolve-target',
        '--phase',
        'phase-5-execute',
        '--workflow',
        _WORKFLOW,
        '--plan-id',
        plan_id,
        '--caller',
        _CALLER,
        *extra,
    )


def _dispatch_lines(plan_id: str) -> list[str]:
    """The work-log ``[DISPATCH]`` message bodies for ``plan_id``."""
    result = read_work_log(plan_id)
    assert result['status'] == 'success'
    return [e['message'] for e in result['entries'] if e['message'].startswith('[DISPATCH]')]


def _resolve_records(plan_id: str) -> list[str]:
    """The decision-log ``effort resolve-target`` message bodies for ``plan_id``."""
    result = read_decision_log(plan_id)
    assert result['status'] == 'success'
    return [e['message'] for e in result['entries'] if 'effort resolve-target' in e['message']]


# =============================================================================
# (D3b) A resolve that previously emitted nothing now emits.
# =============================================================================


def test_resolve_target_now_emits_a_dispatch_line(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'emit-once')

    result = _resolve('emit-once')

    assert result.returncode == 0, result.stderr
    lines = _dispatch_lines('emit-once')
    assert len(lines) == 1, f'expected exactly one [DISPATCH] line, got {lines}'


# =============================================================================
# (D3a) A re-fired step emits one record per fire — the observed five-fire shape.
# =============================================================================


def test_re_fired_step_emits_one_record_per_fire(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'five-fire')

    for _ in range(5):
        result = _resolve('five-fire')
        assert result.returncode == 0, result.stderr

    lines = _dispatch_lines('five-fire')
    assert len(lines) == 5, f'five fires must emit five records, got {len(lines)}: {lines}'


# =============================================================================
# (D3c) A role fired N times produces N records, not one — per-firing assertion.
# =============================================================================


def test_role_fired_n_times_produces_n_records(plan_context):
    _seed_marshal(plan_context)
    for n in (1, 2, 3, 7):
        plan_id = f'per-firing-{n}'
        _init_plan(plan_context, plan_id)
        for _ in range(n):
            assert _resolve(plan_id).returncode == 0
        lines = _dispatch_lines(plan_id)
        assert len(lines) == n, f'{n} fires must produce {n} records, got {len(lines)}'


# =============================================================================
# (D3d) Population non-empty AND emission set == envelope (resolve) set.
# =============================================================================


def test_emission_set_equals_envelope_set(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'population')

    for _ in range(4):
        assert _resolve('population').returncode == 0

    dispatch_lines = _dispatch_lines('population')
    resolve_records = _resolve_records('population')

    # Population is non-empty ...
    assert dispatch_lines, 'the emission population must be non-empty'
    assert resolve_records, 'the envelope (resolve) population must be non-empty'
    # ... and the emission set equals the envelope set (one [DISPATCH] per resolve).
    assert len(dispatch_lines) == len(resolve_records) == 4


def test_dispatch_line_fields_match_the_resolved_envelope(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'fields')

    result = _resolve('fields')
    assert result.returncode == 0, result.stderr
    resolved = parse_toon(result.stdout)
    target = resolved['target']
    level = resolved['level']
    role = resolved['role']

    lines = _dispatch_lines('fields')
    assert len(lines) == 1
    line = lines[0]
    # The five literal audit fields, carrying the resolved envelope's values.
    assert f'target={target}' in line
    assert f'level={level}' in line
    assert f'role={role}' in line
    assert f'workflow={_WORKFLOW}' in line
    assert 'plan_id=fields' in line
    assert line.startswith(f'[DISPATCH] ({_CALLER})')


# =============================================================================
# (D2) Both audit surfaces are written from the ONE seam — they share an emitter.
# =============================================================================


def test_both_surfaces_written_from_the_seam(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'both-surfaces')

    assert _resolve('both-surfaces').returncode == 0

    # Surface A — work-log [DISPATCH] line (the observable side of the pairing).
    assert len(_dispatch_lines('both-surfaces')) == 1
    # Surface B — decision-log resolution record (the intent side of the pairing).
    assert len(_resolve_records('both-surfaces')) == 1


# =============================================================================
# Backward-compat: a bare resolve with no --workflow still emits nothing.
# =============================================================================


def test_bare_resolve_without_workflow_emits_nothing(plan_context):
    _seed_marshal(plan_context)
    _init_plan(plan_context, 'bare')

    result = run_script(
        SCRIPT_PATH,
        'effort',
        'resolve-target',
        '--phase',
        'phase-5-execute',
    )

    assert result.returncode == 0, result.stderr
    assert _dispatch_lines('bare') == []
    assert _resolve_records('bare') == []
