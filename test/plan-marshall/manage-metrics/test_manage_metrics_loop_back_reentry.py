#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end loop-back re-entry regression test for manage-metrics.

Where the write-site unit tests in ``test_manage_metrics_phase_boundary.py``
exercise ``cmd_end_phase`` / ``cmd_phase_boundary`` one call at a time, this
module drives the WHOLE loop-back sequence through the public command surface
and asserts against the two persisted artifacts a consumer actually reads —
``work/metrics.toon`` and the rendered ``metrics.md``:

    start-phase    5-execute
    phase-boundary 5-execute  -> 6-finalize   (usage forwarded)
    phase-boundary 6-finalize -> 5-execute    (THE LOOP-BACK: re-stamps 5-execute.start_time)
    phase-boundary 5-execute  -> 6-finalize   (closes 5-execute a SECOND time)
    generate

The defect this guards: the write sites once assigned the closing phase's
``total_tokens`` / ``tool_uses`` / ``agent_duration_ms`` with plain ``=``, so the
second close REPLACED the first entry's totals. Against the pre-fix write path
``5-execute`` would report only the final close's 30 000 tokens; after the fix it
reports the 130 000 summed across both entries. Every assertion below is written
so it discriminates the two behaviours rather than passing under either.
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
cmd_start_phase = manage_metrics.cmd_start_phase
cmd_phase_boundary = manage_metrics.cmd_phase_boundary
cmd_generate = manage_metrics.cmd_generate


# =============================================================================
# require_plan_exists guard fixture
# =============================================================================
#
# Every plan-scoped writer in manage-metrics.py carries a require_plan_exists
# guard that returns ``error: plan_not_found`` unless the plan directory holds a
# ``status.json`` sentinel. The ``plan_context`` fixture creates plan dirs without
# it, so the autouse fixture below patches the guard chokepoint to auto-seed the
# sentinel — the same pattern used in test_manage_metrics_phase_boundary.py.


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint."""
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
# Namespace + parsing helpers
# =============================================================================


def _ns_start_phase(plan_id, phase):
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_boundary(plan_id, prev_phase, next_phase, total_tokens=None, duration_ms=None, tool_uses=None):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=None,
        command='phase-boundary',
        func=cmd_phase_boundary,
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
        stripped = line.strip()
        if stripped.startswith(f'{key}:'):
            return stripped.split(':', 1)[1].strip()
    return None


def _breakdown_cells(md_content: str, phase: str) -> list[str]:
    """Return the Phase Breakdown table cells for ``phase``, padding stripped.

    Cell order is Phase, Worked, Reported (wall), Idle, Tokens, Tool Uses. Cells
    are compared rather than substring-matched because the accumulated figure
    ``130,000`` CONTAINS the per-close figure ``30,000`` — a substring assertion
    would pass under the replace defect it is meant to catch.
    """
    for line in md_content.splitlines():
        if line.startswith(f'| {phase} '):
            return [cell.strip() for cell in line.strip().strip('|').split('|')]
    raise AssertionError(f'Phase Breakdown row for {phase} not found')


# The forwarded per-close usage. Entry 1 is the original 5-execute run; entry 2 is
# the work done after the finalize loop-back re-entered it.
_ENTRY_1 = {'total_tokens': 100_000, 'tool_uses': 50, 'duration_ms': 300_000}
_ENTRY_2 = {'total_tokens': 30_000, 'tool_uses': 10, 'duration_ms': 180_000}


def _drive_loop_back_sequence(monkeypatch, plan_id: str) -> dict:
    """Run the full loop-back command sequence on a frozen clock.

    Timeline (frozen so every span is exact rather than real-wall-clock):

        13:00:00  start-phase    5-execute
        13:10:00  phase-boundary 5-execute  -> 6-finalize   (entry 1 usage)
        13:20:00  phase-boundary 6-finalize -> 5-execute    (loop-back; re-stamps start)
        13:35:00  phase-boundary 5-execute  -> 6-finalize   (entry 2 usage, second close)
        13:40:00  generate

    Returns the ``generate`` result dict.
    """

    def _at(timestamp: str) -> None:
        monkeypatch.setattr(manage_metrics, 'now_utc_iso', lambda: timestamp)

    _at('2026-05-08T13:00:00+00:00')
    cmd_start_phase(_ns_start_phase(plan_id, '5-execute'))

    # Entry 1 closes 5-execute (600 s active span) and opens 6-finalize.
    _at('2026-05-08T13:10:00+00:00')
    first = cmd_phase_boundary(_ns_boundary(plan_id, '5-execute', '6-finalize', **_ENTRY_1))
    assert first['status'] == 'success'
    assert first['prev_close_count'] == 1

    # THE LOOP-BACK: finalize hands control back to execute, re-stamping
    # 5-execute.start_time to 13:20:00.
    _at('2026-05-08T13:20:00+00:00')
    loop_back = cmd_phase_boundary(
        _ns_boundary(plan_id, '6-finalize', '5-execute', total_tokens=40_000, tool_uses=20, duration_ms=120_000)
    )
    assert loop_back['status'] == 'success'

    # Entry 2 closes 5-execute a SECOND time (900 s active span from the
    # re-stamped start) and re-opens 6-finalize.
    _at('2026-05-08T13:35:00+00:00')
    second = cmd_phase_boundary(_ns_boundary(plan_id, '5-execute', '6-finalize', **_ENTRY_2))
    assert second['status'] == 'success'
    assert second['prev_close_count'] == 2

    _at('2026-05-08T13:40:00+00:00')
    # Annotated explicitly: the entrypoint is importlib-loaded, so its cmd_* return
    # type is Any and returning it bare would trip mypy's no-any-return.
    result: dict = cmd_generate(_ns_generate(plan_id))
    assert result['status'] == 'success'
    return result


# =============================================================================
# metrics.toon — the re-entered row holds the sum across both entries
# =============================================================================


def test_loop_back_reentry_accumulates_every_field_in_metrics_toon(plan_context, monkeypatch):
    """The re-entered 5-execute row sums both entries' usage and wall span."""
    plan_id = 'e2e-loopback-toon'
    _drive_loop_back_sequence(monkeypatch, plan_id)

    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '5-execute')

    expected_tokens = _ENTRY_1['total_tokens'] + _ENTRY_2['total_tokens']
    expected_tool_uses = _ENTRY_1['tool_uses'] + _ENTRY_2['tool_uses']
    expected_worked_ms = _ENTRY_1['duration_ms'] + _ENTRY_2['duration_ms']

    assert _field(block, 'total_tokens') == str(expected_tokens)
    assert _field(block, 'tool_uses') == str(expected_tool_uses)
    assert _field(block, 'agent_duration_ms') == str(expected_worked_ms)
    # 600 s (entry 1) + 900 s (entry 2, anchored on the re-stamped start_time).
    assert _field(block, 'duration_seconds') == '1500.0'

    # Discriminator: the replace defect would leave ONLY entry 2's figures here.
    assert _field(block, 'total_tokens') != str(_ENTRY_2['total_tokens'])
    assert _field(block, 'tool_uses') != str(_ENTRY_2['tool_uses'])
    assert _field(block, 'agent_duration_ms') != str(_ENTRY_2['duration_ms'])
    assert _field(block, 'duration_seconds') != '900.0'


def test_loop_back_reentry_records_close_count_two(plan_context, monkeypatch):
    """close_count is 2 on the re-entered phase and 1 on the phase closed once."""
    plan_id = 'e2e-loopback-close-count'
    _drive_loop_back_sequence(monkeypatch, plan_id)

    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    assert _field(_phase_block(content, '5-execute'), 'close_count') == '2'
    # 6-finalize was closed exactly once — by the loop-back boundary.
    assert _field(_phase_block(content, '6-finalize'), 'close_count') == '1'


def test_loop_back_reentry_preserves_worked_within_accumulated_wall(plan_context, monkeypatch):
    """The Worked <= Reported (wall) invariant survives the re-entry."""
    plan_id = 'e2e-loopback-invariant'
    _drive_loop_back_sequence(monkeypatch, plan_id)

    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '5-execute')
    wall_s = float(_field(block, 'duration_seconds'))
    worked_s = float(_field(block, 'agent_duration_seconds'))
    assert worked_s <= wall_s
    # The accumulated worked span (480 s) is real work, not a clamp artifact.
    assert worked_s == 480.0


def test_loop_back_reentry_start_time_stays_scoped_to_latest_entry(plan_context, monkeypatch):
    """start_time reflects the LATEST entry, so it diverges from duration_seconds.

    The documented consequence of accumulating the wall span: a ``close_count > 1``
    row deliberately does not satisfy ``duration_seconds == end_time - start_time``.
    """
    plan_id = 'e2e-loopback-divergence'
    _drive_loop_back_sequence(monkeypatch, plan_id)

    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    block = _phase_block(content, '5-execute')
    assert _field(block, 'start_time') == '2026-05-08T13:20:00+00:00'
    assert _field(block, 'end_time') == '2026-05-08T13:35:00+00:00'
    # Timestamp span is 900 s; the accumulated active span is 1500 s.
    assert float(_field(block, 'duration_seconds')) == 1500.0


# =============================================================================
# metrics.md — the re-entry is visible in the rendered report
# =============================================================================


def test_loop_back_reentry_renders_marker_naming_the_reentered_phase(plan_context, monkeypatch):
    """generate names 5-execute — the phase actually re-entered — in the marker."""
    plan_id = 'e2e-loopback-marker'
    result = _drive_loop_back_sequence(monkeypatch, plan_id)

    assert result['re_entered_phases'] == ['5-execute']

    content = (plan_context.plan_dir_for(plan_id) / 'work' / 'metrics.toon').read_text()
    assert 're_entered_phases: 5-execute' in content

    md = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text()
    assert '> Re-entered phases: 5-execute' in md
    assert '- **Closes**: 2' in md

    # The marker sits between the heading and the breakdown table.
    md_lines = md.splitlines()
    heading_idx = md_lines.index('## Phase Breakdown')
    marker_idx = next(i for i, line in enumerate(md_lines) if line.startswith('> Re-entered phases:'))
    header_idx = next(i for i, line in enumerate(md_lines) if line.startswith('| Phase'))
    assert heading_idx < marker_idx < header_idx


def test_loop_back_reentry_renders_accumulated_tokens_cell(plan_context, monkeypatch):
    """The Phase Breakdown Tokens cell for 5-execute shows the accumulated figure."""
    plan_id = 'e2e-loopback-tokens-cell'
    _drive_loop_back_sequence(monkeypatch, plan_id)

    md = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text()
    cells = _breakdown_cells(md, '5-execute')
    tokens_cell, tool_uses_cell = cells[4], cells[5]

    # 100 000 + 30 000, thousands-separated as the renderer formats it.
    assert tokens_cell == '130,000'
    # Discriminator: the replace defect would render entry 2's 30,000 alone.
    assert tokens_cell != '30,000'
    assert tool_uses_cell == '60'
