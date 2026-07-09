#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the inline-phase (omit-`<usage>`) recording mode.

A phase that runs *inline* in the main orchestrator context — rather than as a
dispatched `execution-context` leaf — produces no agent `<usage>` envelope, so
its `phase-boundary` / `end-phase` close OMITS `--total-tokens` /
`--duration-ms` / `--tool-uses`. This is the sanctioned inline recording mode,
NOT an incomplete call: the closing phase's `end_time` is stamped
unconditionally and `generate`'s partiality verdict keys a phase's *recorded*
status solely off that `end_time` marker.

These tests lock in that contract for the topology this plan ships:
  - the inline **1-init → 2-refine** boundary (phase-1-init runs inline), and
  - the recipe-inline **2-refine → 3-outline** / **3-outline → 4-plan**
    boundaries,
all closing with the usage flags omitted, must record as *recorded* — never
listed under `unrecorded_phases` and never flipping `partial` to true —
preserving the #812 floor-not-truth semantics unchanged for a fully-recorded
six-phase plan.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import get_script_path

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location(
    'manage_metrics', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)
cmd_phase_boundary = manage_metrics.cmd_phase_boundary
cmd_start_phase = manage_metrics.cmd_start_phase
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_generate = manage_metrics.cmd_generate


# =============================================================================
# require_plan_exists guard fixture (mirrors test_manage_metrics_phase_boundary)
# =============================================================================
#
# Every plan-scoped writer in manage-metrics.py carries a require_plan_exists
# guard that returns ``error: plan_not_found`` unless the plan dir holds a
# ``status.json`` sentinel. The ``plan_context`` fixture creates plan dirs
# without that sentinel, so the positive tests below would otherwise trip the
# guard. This autouse fixture patches the guard chokepoint to auto-materialise
# the sentinel for any plan whose dir exists.


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        plan_dir = real_get_plan_dir(plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)
        sentinel = plan_dir / 'status.json'
        if not sentinel.is_file():
            sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


# =============================================================================
# Namespace helpers
# =============================================================================


def _ns_start_phase(plan_id, phase):
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_boundary(
    plan_id,
    prev_phase,
    next_phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='phase-boundary',
        func=cmd_phase_boundary,
    )


def _ns_end_phase(
    plan_id,
    phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='end-phase',
        func=cmd_end_phase,
    )


def _ns_generate(plan_id):
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _phase_block(content: str, phase: str) -> str:
    """Return the metrics.toon text block for a single [phase] section."""
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _field(block: str, key: str) -> str | None:
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(f'{key}:'):
            return s.split(':', 1)[1].strip()
    return None


def _drive_full_six_phase_plan(plan_id: str) -> None:
    """Record a complete six-phase plan with the inline phases closed usage-free.

    Models the shipped topology: phase-1-init and the recipe-inline refine /
    outline phases run inline (no agent `<usage>`), so their closing
    `phase-boundary` calls OMIT the token/duration/tool-uses flags. The
    dispatched phases (4-plan, 5-execute, 6-finalize) close with usage data.
    Every phase ends up with an `end_time`, so the plan is fully recorded.
    """
    # 1-init opens via the phase-1-init Step 3a self-record, then closes inline.
    cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
    # Inline boundaries — usage flags OMITTED (no agent <usage> envelope).
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    # Dispatched boundaries — usage data present.
    cmd_phase_boundary(
        _ns_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute', total_tokens=42000, tool_uses=15)
    )
    cmd_phase_boundary(
        _ns_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize', total_tokens=88000, tool_uses=30)
    )
    cmd_end_phase(_ns_end_phase(plan_id, phase='6-finalize', total_tokens=31000, tool_uses=12))


# =============================================================================
# Inline-phase recording: fully-recorded plan is NOT partial
# =============================================================================


def test_inline_init_refine_boundary_records_not_partial(plan_context):
    """A fully-recorded six-phase plan whose init→refine boundary closed inline
    (usage flags omitted) reports partial: false with no unrecorded phases."""
    _drive_full_six_phase_plan('inline-full')

    result = cmd_generate(_ns_generate('inline-full'))

    assert result['status'] == 'success'
    # The inline close of 1-init must NOT make the report partial.
    assert result['partial'] is False
    assert result['unrecorded_phases'] == []


def test_inline_init_phase_is_recorded_without_token_data(plan_context):
    """The inline-closed 1-init row carries end_time (recorded) but no token data."""
    _drive_full_six_phase_plan('inline-init-row')
    cmd_generate(_ns_generate('inline-init-row'))

    content = (plan_context.plan_dir_for('inline-init-row') / 'work' / 'metrics.toon').read_text()
    init_block = _phase_block(content, '1-init')

    # Recorded: end_time stamped by the inline boundary.
    assert _field(init_block, 'end_time') is not None
    # Inline mode: no <usage>-derived fields written for the closing phase.
    assert _field(init_block, 'total_tokens') is None
    assert _field(init_block, 'tool_uses') is None


def test_inline_init_phase_absent_from_unrecorded_list(plan_context):
    """1-init never appears under unrecorded_phases despite carrying no usage data."""
    _drive_full_six_phase_plan('inline-not-unrecorded')
    result = cmd_generate(_ns_generate('inline-not-unrecorded'))

    assert '1-init' not in result['unrecorded_phases']
    # The persisted top-level marker agrees with the returned verdict.
    content = (plan_context.plan_dir_for('inline-not-unrecorded') / 'work' / 'metrics.toon').read_text()
    assert 'partial: false' in content
    assert 'unrecorded_phases:' in content


def test_recipe_inline_refine_outline_boundaries_are_recorded(plan_context):
    """The recipe-inline 2-refine and 3-outline phases (closed usage-free) are recorded."""
    _drive_full_six_phase_plan('inline-recipe')
    result = cmd_generate(_ns_generate('inline-recipe'))

    assert result['partial'] is False
    for phase in ('2-refine', '3-outline'):
        assert phase not in result['unrecorded_phases']

    content = (plan_context.plan_dir_for('inline-recipe') / 'work' / 'metrics.toon').read_text()
    for phase in ('2-refine', '3-outline'):
        block = _phase_block(content, phase)
        assert _field(block, 'end_time') is not None
        # Recipe-inline close carries no token data either.
        assert _field(block, 'total_tokens') is None


# =============================================================================
# Negative control: an un-closed phase DOES flip partial (verdict is real)
# =============================================================================


def test_unclosed_phase_still_flips_partial(plan_context):
    """A phase with no end_time is unrecorded — proving the verdict isn't always false.

    This guards against a regression that would treat every phase as recorded
    (which would make the positive tests pass vacuously). The 6-finalize phase
    is started but never closed, so it must surface as unrecorded / partial.
    """
    plan_id = 'inline-partial-neg'
    cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute'))
    # 5-execute → 6-finalize opens 6-finalize but it is never closed (no end_time).
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize'))

    result = cmd_generate(_ns_generate(plan_id))

    assert result['partial'] is True
    assert result['unrecorded_phases'] == ['6-finalize']
    # The inline-closed early phases are still recorded — only 6-finalize is missing.
    assert '1-init' not in result['unrecorded_phases']
    assert '2-refine' not in result['unrecorded_phases']
