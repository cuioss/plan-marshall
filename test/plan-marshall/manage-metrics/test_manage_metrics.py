#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, run_script  # noqa: I001

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)
cmd_accumulate_agent_usage = manage_metrics.cmd_accumulate_agent_usage
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_enrich = manage_metrics.cmd_enrich
cmd_generate = manage_metrics.cmd_generate
cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary
cmd_start_phase = manage_metrics.cmd_start_phase


# =============================================================================
# Helpers
# =============================================================================


def _ns_start_phase(plan_id: str, phase: str) -> Namespace:
    """Build Namespace for start-phase command."""
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_end_phase(
    plan_id: str,
    phase: str,
    total_tokens: int | None = None,
    duration_ms: int | None = None,
    tool_uses: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """Build Namespace for end-phase command."""
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


def _ns_generate(plan_id: str) -> Namespace:
    """Build Namespace for generate command."""
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _ns_enrich(plan_id: str, session_id: str) -> Namespace:
    """Build Namespace for enrich command."""
    return Namespace(plan_id=plan_id, session_id=session_id, command='enrich', func=cmd_enrich)


def _ns_accumulate(
    plan_id: str,
    phase: str,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """Build Namespace for accumulate-agent-usage command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
        retrospective_tokens=retrospective_tokens,
        command='accumulate-agent-usage',
        func=cmd_accumulate_agent_usage,
    )


def _pin_start_time_to_past(plan_id: str, phase: str) -> None:
    """Pin a phase's ``start_time`` far in the past so the wall span deterministically
    exceeds any test's worked window.

    ``cmd_end_phase`` derives ``duration_seconds`` from ``end_time - start_time`` and
    feeds it to ``_clamp_worked_to_wall``. When start→end fire back-to-back the real
    wall span is ~0ms locally but can reach ~1000ms on a slow CI runner, which made
    the forwarded worked window clamp to a machine-dependent value (flaky). Pinning
    ``start_time`` to a fixed instant well before ``now`` makes the wall span always
    exceed the worked window, so the clamp is a deterministic no-op and the forwarded /
    accumulator ``duration_ms`` flows through unchanged. The dedicated
    ``TestClampWorkedToWall`` unit tests cover the down-clamp branch directly.
    """
    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases'].setdefault(phase, {})['start_time'] = '2020-01-01T00:00:00+00:00'
    manage_metrics.write_metrics(plan_id, data)


# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================
#
# TASK-1 added a require_plan_exists guard to every plan-scoped writer in
# manage-metrics.py (start-phase, end-phase, generate, phase-boundary,
# accumulate-agent-usage, enrich). The guard returns ``error: plan_not_found``
# unless the plan directory carries a ``status.json`` sentinel. The
# ``plan_context`` fixture creates plan dirs without that sentinel, so every
# positive test below would otherwise trip the guard.
#
# The autouse fixture below patches ``manage_metrics.require_plan_exists`` so
# that, during these tests, it auto-materialises the ``status.json`` sentinel for
# any plan whose dir exists but is not explicitly registered as "unseeded". This
# is the real guard chokepoint — it fires regardless of whether a test resolves
# its plan dir before or after calling the writer. Guard-negative tests register
# their plan_id via ``_register_unseeded`` so the patched guard lets the genuine
# ``plan_not_found`` branch run.

_UNSEEDED_PLAN_IDS: set[str] = set()


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


def _register_unseeded(plan_id: str) -> str:
    """Mark ``plan_id`` so the autouse guard-seeder leaves it un-sentinelled.

    Returns the plan_id for inline use. Negative guard tests call this so the
    patched ``require_plan_exists`` runs its genuine ``plan_not_found`` branch.
    """
    _UNSEEDED_PLAN_IDS.add(plan_id)
    return plan_id


def _unseeded_plan_dir(plan_context, plan_id: str) -> Path:
    """Create a plan dir WITHOUT the ``status.json`` sentinel (orphan plan dir).

    Goes straight to ``plans_dir`` (bypassing any seeding helper) so the guard's
    ``plan_not_found`` branch fires. Asserts the sentinel is absent to keep the
    negative tests honest if the seeding policy ever changes. The returned path
    equals ``manage_metrics.get_plan_dir(plan_id)`` under the ``plan_context``
    ``PLAN_BASE_DIR`` redirect, so it matches the ``plan_dir`` the guard reports.
    """
    plan_dir = plan_context.plans_dir / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    assert not (plan_dir / 'status.json').exists(), 'negative test requires an unseeded plan dir'
    return plan_dir


# =============================================================================
# Test: start-phase (Tier 2 - direct import)
# =============================================================================


def test_start_phase_records_timestamp(plan_context):
    """start-phase creates metrics.toon with phase start timestamp."""
    result = cmd_start_phase(_ns_start_phase('metrics-start-01', '1-init'))
    assert result['status'] == 'success'
    assert result['phase'] == '1-init'
    assert 'start_time' in result

    # Verify file was written
    metrics_file = plan_context.plan_dir_for('metrics-start-01') / 'work' / 'metrics.toon'
    assert metrics_file.exists(), 'metrics.toon should be created'
    content = metrics_file.read_text()
    assert '[1-init]' in content
    assert 'start_time:' in content


def test_start_phase_invalid_phase(plan_context):
    """start-phase rejects invalid phase names."""
    result = cmd_start_phase(_ns_start_phase('metrics-start-02', 'invalid'))
    assert result['status'] == 'error'
    assert 'Invalid phase' in str(result.get('message', ''))


def test_start_phase_invalid_plan_id(plan_context):
    """start-phase rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_start_phase(_ns_start_phase('../escape', '1-init'))
    assert exc_info.value.code == 0


def test_start_phase_multiple_phases(plan_context):
    """start-phase can record multiple phases."""
    cmd_start_phase(_ns_start_phase('metrics-start-03', '1-init'))
    cmd_start_phase(_ns_start_phase('metrics-start-03', '2-refine'))

    metrics_file = plan_context.plan_dir_for('metrics-start-03') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()
    assert '[1-init]' in content
    assert '[2-refine]' in content


# =============================================================================
# Test: end-phase (Tier 2 - direct import)
# =============================================================================


def test_end_phase_computes_duration(plan_context):
    """end-phase computes wall-clock duration from start/end."""
    cmd_start_phase(_ns_start_phase('metrics-end-01', '1-init'))
    result = cmd_end_phase(_ns_end_phase('metrics-end-01', '1-init'))
    assert result['status'] == 'success'
    assert 'duration_seconds' in result
    assert float(str(result['duration_seconds'])) >= 0


def test_end_phase_with_token_data(plan_context):
    """end-phase stores token data from Task agent notifications."""
    cmd_start_phase(_ns_start_phase('metrics-end-02', '1-init'))
    # Pin start_time to the past so the wall span deterministically exceeds the
    # forwarded worked window — _clamp_worked_to_wall is then a no-op and the
    # forwarded 181681 ms flows through unclamped (the back-to-back wall span is
    # machine-dependent; see _pin_start_time_to_past).
    _pin_start_time_to_past('metrics-end-02', '1-init')
    result = cmd_end_phase(
        _ns_end_phase('metrics-end-02', '1-init', total_tokens=25514, duration_ms=181681, tool_uses=23)
    )
    assert result['status'] == 'success'
    assert result['total_tokens'] == 25514

    # Verify stored in metrics.toon
    metrics_file = plan_context.plan_dir_for('metrics-end-02') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()
    assert 'total_tokens: 25514' in content
    assert 'tool_uses: 23' in content
    assert 'agent_duration_ms: 181681' in content


def test_end_phase_without_start(plan_context):
    """end-phase works even if start-phase wasn't called (no duration computed from timestamps)."""
    result = cmd_end_phase(_ns_end_phase('metrics-end-03', '2-refine', total_tokens=1000))
    assert result['status'] == 'success'
    # No duration_seconds since no start_time
    assert 'duration_seconds' not in result


def test_end_phase_no_optional_args(plan_context):
    """end-phase works without optional token data."""
    cmd_start_phase(_ns_start_phase('metrics-end-04', '3-outline'))
    result = cmd_end_phase(_ns_end_phase('metrics-end-04', '3-outline'))
    assert result['status'] == 'success'
    assert 'total_tokens' not in result


# =============================================================================
# Test: generate (Tier 2 - direct import)
# =============================================================================


def test_generate_creates_metrics_md(plan_context):
    """generate creates metrics.md with the three-column phase breakdown table."""
    # Record two phases
    cmd_start_phase(_ns_start_phase('metrics-gen-01', '1-init'))
    cmd_end_phase(_ns_end_phase('metrics-gen-01', '1-init', total_tokens=25000, tool_uses=20))
    cmd_start_phase(_ns_start_phase('metrics-gen-01', '2-refine'))
    cmd_end_phase(_ns_end_phase('metrics-gen-01', '2-refine'))

    # Generate report
    result = cmd_generate(_ns_generate('metrics-gen-01'))
    assert result['status'] == 'success'
    assert result['phases_recorded'] == 2
    assert result['total_tokens'] == 25000
    # Pre-formatted display fields are populated alongside the raw values.
    assert isinstance(result['total_worked_formatted'], str)
    assert isinstance(result['total_wall_formatted'], str)
    assert isinstance(result['total_idle_formatted'], str)
    assert result['total_tokens_formatted'] == '25K'

    # Verify metrics.md content
    md_path = plan_context.plan_dir_for('metrics-gen-01') / 'metrics.md'
    assert md_path.exists(), 'metrics.md should be created'
    md_content = md_path.read_text()
    assert '# Metrics: metrics-gen-01' in md_content
    assert '## Phase Breakdown' in md_content
    # Header is padded to uniform per-column width; check for the column names rather
    # than the exact unpadded string.
    assert '| Phase' in md_content
    assert '| Worked' in md_content
    assert '| Reported (wall)' in md_content
    assert '| Idle' in md_content
    assert '| Tokens' in md_content and '| Tool Uses' in md_content
    # The legacy single Duration column is gone.
    assert '| Duration ' not in md_content
    assert '1-init' in md_content
    assert '2-refine' in md_content
    assert '25,000' in md_content
    assert '**Total**' in md_content


def _phase_breakdown_header(md_content: str) -> str:
    """Return the header row of the ## Phase Breakdown table."""
    lines = md_content.splitlines()
    bd_idx = lines.index('## Phase Breakdown')
    for line in lines[bd_idx:]:
        if line.startswith('| Phase'):
            return line
    raise AssertionError('Phase Breakdown header row not found')


def test_generate_three_column_header_order(plan_context):
    """The Phase Breakdown header lists Worked, Reported (wall), Idle in order."""
    cmd_start_phase(_ns_start_phase('metrics-gen-cols', '1-init'))
    cmd_end_phase(_ns_end_phase('metrics-gen-cols', '1-init', total_tokens=1000, tool_uses=3))
    cmd_generate(_ns_generate('metrics-gen-cols'))

    header = _phase_breakdown_header((plan_context.plan_dir_for('metrics-gen-cols') / 'metrics.md').read_text())
    cols = [c.strip() for c in header.strip('|').split('|')]
    assert cols == ['Phase', 'Worked', 'Reported (wall)', 'Idle', 'Tokens', 'Tool Uses']


def test_generate_worked_rollup_uses_max_not_sum(plan_context):
    """Worked time = max(agent_duration_ms, subagent_duration_ms) — never additive.

    The prior additive formula double-counted the orchestrator/subagent overlap
    span (the orchestrator is awaiting the subagent return, not doing
    independent compute) and could produce ``Worked > Reported (wall)``,
    breaking the per-phase ``Worked <= wall`` invariant and forcing Idle to
    clamp to zero. The max(...) form lets the longer attribution subsume the
    shorter overlap.
    """
    # Seed metrics.toon directly so the exact field set is deterministic.
    # wall = 120s; agent = 60s; subagent = 90s. With the additive formula
    # this would yield worked=150s > wall=120s (invariant violation). With
    # max(...), worked=90s and the invariant holds.
    manage_metrics.write_metrics(
        'metrics-gen-worked',
        {
            'phases': {
                '5-execute': {
                    'duration_seconds': 120,
                    'agent_duration_ms': 60000,
                    'subagent_duration_ms': 90000,
                },
            },
        },
    )

    result = cmd_generate(_ns_generate('metrics-gen-worked'))
    assert result['status'] == 'success'
    # worked = max(60s, 90s) = 90s; wall = 120s; idle = 30s.
    assert result['total_worked_seconds'] == 90.0
    assert result['total_wall_seconds'] == 120.0
    assert result['total_idle_seconds'] == 30.0
    toon = (plan_context.plan_dir_for('metrics-gen-worked') / 'work' / 'metrics.toon').read_text()
    assert 'idle_duration_ms: 30000' in toon


def test_worked_le_wall_invariant_holds_for_subagent_dispatching_phases(plan_context):
    """Worked <= Reported (wall) invariant — holds for every phase that
    dispatches a subagent within the phase window.

    Three subagent-dispatching phases (1-init, 3-outline, 5-execute) are
    seeded with overlapping agent + subagent attribution spans. After the
    fix, every per-phase worked value MUST be <= the corresponding wall
    value and Idle MUST be non-blank (non-zero) for each.
    """
    manage_metrics.write_metrics(
        'metrics-invariant',
        {
            'phases': {
                '1-init': {
                    'duration_seconds': 200,
                    'agent_duration_ms': 80000,
                    'subagent_duration_ms': 150000,
                },
                '3-outline': {
                    'duration_seconds': 400,
                    'agent_duration_ms': 120000,
                    'subagent_duration_ms': 250000,
                },
                '5-execute': {
                    'duration_seconds': 900,
                    'agent_duration_ms': 300000,
                    'subagent_duration_ms': 600000,
                },
            },
        },
    )

    result = cmd_generate(_ns_generate('metrics-invariant'))
    assert result['status'] == 'success'

    toon = (plan_context.plan_dir_for('metrics-invariant') / 'work' / 'metrics.toon').read_text()
    # Per-phase invariant: worked = max(agent, subagent), idle = wall - worked.
    # 1-init: worked=150s, wall=200s, idle=50s.
    # 3-outline: worked=250s, wall=400s, idle=150s.
    # 5-execute: worked=600s, wall=900s, idle=300s.
    assert 'idle_duration_ms: 50000' in toon
    assert 'idle_duration_ms: 150000' in toon
    assert 'idle_duration_ms: 300000' in toon

    # Total worked never exceeds total wall.
    assert result['total_worked_seconds'] <= result['total_wall_seconds']
    # Total idle is the residual.
    assert result['total_idle_seconds'] == (
        result['total_wall_seconds'] - result['total_worked_seconds']
    )


def test_generate_idle_residual_and_zero_clamp(plan_context):
    """idle_duration_ms = max(0, wall_clock - worked), including the zero-clamp branch."""
    # Phase with idle time: wall-clock (300s) > worked (agent 100s + subagent 50s).
    manage_metrics.write_metrics(
        'metrics-gen-idle',
        {
            'phases': {
                '5-execute': {
                    'duration_seconds': 300,
                    'agent_duration_ms': 100000,
                    'subagent_duration_ms': 50000,
                },
            },
        },
    )

    result = cmd_generate(_ns_generate('metrics-gen-idle'))
    assert result['status'] == 'success'
    toon = (plan_context.plan_dir_for('metrics-gen-idle') / 'work' / 'metrics.toon').read_text()
    # worked = max(100000, 50000) = 100000 ms; wall = 300000 ms; idle = 200000 ms.
    assert 'idle_duration_ms: 200000' in toon
    assert result['total_idle_seconds'] == 200.0
    assert result['total_worked_seconds'] == 100.0
    assert result['total_wall_seconds'] == 300.0


def test_generate_total_row_sums_three_columns_independently(plan_context):
    """The Total row sums Worked, Reported (wall), and Idle independently."""
    manage_metrics.write_metrics(
        'metrics-gen-total',
        {
            'phases': {
                '1-init': {'duration_seconds': 200, 'agent_duration_ms': 120000},
                '2-refine': {'duration_seconds': 100, 'agent_duration_ms': 40000},
            },
        },
    )

    result = cmd_generate(_ns_generate('metrics-gen-total'))
    assert result['status'] == 'success'
    # worked total = 120 + 40 = 160 s; wall total = 200 + 100 = 300 s;
    # idle total = (200-120) + (100-40) = 80 + 60 = 140 s.
    assert result['total_worked_seconds'] == 160.0
    assert result['total_wall_seconds'] == 300.0
    assert result['total_idle_seconds'] == 140.0


def test_generate_no_data(plan_context):
    """generate returns error when no metrics data exists."""
    result = cmd_generate(_ns_generate('metrics-gen-02'))
    assert result['status'] == 'error'
    assert 'No metrics data' in str(result.get('message', ''))


def test_generate_all_six_phases(plan_context):
    """generate handles all 6 phases."""
    phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
    for phase in phases:
        cmd_start_phase(_ns_start_phase('metrics-gen-03', phase))
        cmd_end_phase(_ns_end_phase('metrics-gen-03', phase))

    result = cmd_generate(_ns_generate('metrics-gen-03'))
    assert result['status'] == 'success'
    assert result['phases_recorded'] == 6

    md_content = (plan_context.plan_dir_for('metrics-gen-03') / 'metrics.md').read_text()
    for phase in phases:
        assert phase in md_content


# =============================================================================
# Test: enrich (Tier 2 - direct import)
# =============================================================================


def test_enrich_missing_transcript(plan_context):
    """enrich returns gracefully when transcript is not found."""
    result = cmd_enrich(_ns_enrich('metrics-enrich-01', 'nonexistent-session-id'))
    assert result['status'] == 'success'
    assert result.get('enriched') is False


def test_enrich_with_unknown_session(plan_context):
    """enrich handles unknown session ID gracefully."""
    result = cmd_enrich(_ns_enrich('metrics-enrich-02', 'test-session-abc123'))
    # Will be 'not found' since session doesn't exist in ~/.claude
    assert result['status'] == 'success'


# =============================================================================
# Test: format_duration (via generate output) (Tier 2 - direct import)
# =============================================================================


def test_format_duration_seconds(plan_context):
    """Duration under 60s shows as seconds."""
    cmd_start_phase(_ns_start_phase('metrics-fmt-01', '1-init'))
    cmd_end_phase(_ns_end_phase('metrics-fmt-01', '1-init'))
    cmd_generate(_ns_generate('metrics-fmt-01'))
    md_content = (plan_context.plan_dir_for('metrics-fmt-01') / 'metrics.md').read_text()
    # Should contain some duration string (likely very small since start/end are near-instant)
    assert '1-init' in md_content


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
# =============================================================================


def test_cli_start_phase_roundtrip(plan_context):
    """CLI plumbing: start-phase subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    # The subprocess runs the REAL require_plan_exists guard (the autouse
    # in-process monkeypatch does not reach a child process), so the plan must
    # carry a status.json sentinel on disk before the call.
    (plan_context.plan_dir_for('cli-plumb-01') / 'status.json').write_text('{}', encoding='utf-8')
    result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-01', '--phase', '1-init')
    assert result.success, f'Script failed: {result.stderr}'
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['phase'] == '1-init'


def test_cli_generate_roundtrip(plan_context):
    """CLI plumbing: generate subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    # Seed the status.json sentinel on disk: the subprocess runs the real
    # require_plan_exists guard (the autouse monkeypatch is in-process only).
    (plan_context.plan_dir_for('cli-plumb-02') / 'status.json').write_text('{}', encoding='utf-8')
    run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
    run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
    result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'cli-plumb-02')
    assert result.success, f'Script failed: {result.stderr}'
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['phases_recorded'] == 1


# =============================================================================
# Test: accumulate-agent-usage (Tier 2 - direct import)
# =============================================================================


class TestAccumulateAgentUsage:
    """Cover the accumulate-agent-usage subcommand: file create, sum, isolate."""

    def test_creates_file_when_absent(self, plan_context):
        """First call creates the per-phase accumulator file with the supplied totals."""
        result = cmd_accumulate_agent_usage(
            _ns_accumulate('accum-create', '6-finalize', total_tokens=12345, tool_uses=7, duration_ms=8000)
        )
        assert result['status'] == 'success'
        assert result['phase'] == '6-finalize'
        assert result['total_tokens'] == 12345
        assert result['tool_uses'] == 7
        assert result['duration_ms'] == 8000
        assert result['samples'] == 1

        acc_path = plan_context.plan_dir_for('accum-create') / 'work' / 'metrics-accumulator-6-finalize.toon'
        assert acc_path.exists(), 'Accumulator file should be created on first call'
        content = acc_path.read_text()
        assert 'plan_id: accum-create' in content
        assert 'phase: 6-finalize' in content
        assert 'total_tokens: 12345' in content
        assert 'tool_uses: 7' in content
        assert 'duration_ms: 8000' in content
        assert 'samples: 1' in content

    def test_sums_across_calls(self, plan_context):
        """Repeated calls sum the totals and increment the samples counter."""
        cmd_accumulate_agent_usage(
            _ns_accumulate('accum-sum', '6-finalize', total_tokens=100, tool_uses=2, duration_ms=1000)
        )
        cmd_accumulate_agent_usage(
            _ns_accumulate('accum-sum', '6-finalize', total_tokens=250, tool_uses=5, duration_ms=2500)
        )
        result = cmd_accumulate_agent_usage(
            _ns_accumulate('accum-sum', '6-finalize', total_tokens=50, duration_ms=500)
        )
        assert result['total_tokens'] == 400
        assert result['tool_uses'] == 7  # third call omitted tool_uses → unchanged
        assert result['duration_ms'] == 4000
        assert result['samples'] == 3

    def test_phase_isolation(self, plan_context):
        """5-execute and 6-finalize accumulators do not collide."""
        cmd_accumulate_agent_usage(_ns_accumulate('accum-iso', '5-execute', total_tokens=1000, tool_uses=10))
        cmd_accumulate_agent_usage(_ns_accumulate('accum-iso', '6-finalize', total_tokens=2000, tool_uses=20))

        five = (plan_context.plan_dir_for('accum-iso') / 'work' / 'metrics-accumulator-5-execute.toon').read_text()
        six = (plan_context.plan_dir_for('accum-iso') / 'work' / 'metrics-accumulator-6-finalize.toon').read_text()
        assert 'total_tokens: 1000' in five
        assert 'tool_uses: 10' in five
        assert 'total_tokens: 2000' in six
        assert 'tool_uses: 20' in six

    def test_invalid_phase_rejected(self, plan_context):
        """Unknown phase names produce a structured error response."""
        result = cmd_accumulate_agent_usage(_ns_accumulate('accum-bad', 'not-a-phase', total_tokens=1))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_phase'

    def test_omitted_flags_leave_existing_totals_unchanged(self, plan_context):
        """A no-flag call still increments samples but leaves totals untouched."""
        cmd_accumulate_agent_usage(
            _ns_accumulate('accum-noop', '6-finalize', total_tokens=42, tool_uses=3, duration_ms=999)
        )
        result = cmd_accumulate_agent_usage(_ns_accumulate('accum-noop', '6-finalize'))
        assert result['total_tokens'] == 42
        assert result['tool_uses'] == 3
        assert result['duration_ms'] == 999
        assert result['samples'] == 2


# =============================================================================
# Test: end-phase accumulator fallback (Tier 2 - direct import)
# =============================================================================


class TestEndPhaseAccumulatorFallback:
    """end-phase reads the per-phase accumulator file when explicit flags are omitted."""

    def test_reads_accumulator_when_flags_absent(self, plan_context):
        """end-phase without flags pulls totals from work/metrics-accumulator-{phase}.toon."""
        cmd_start_phase(_ns_start_phase('ep-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('ep-fallback', '6-finalize', total_tokens=5000, tool_uses=12, duration_ms=60000)
        )
        # Pin start_time so the clamp is a deterministic no-op (see _pin_start_time_to_past).
        _pin_start_time_to_past('ep-fallback', '6-finalize')

        result = cmd_end_phase(_ns_end_phase('ep-fallback', '6-finalize'))

        assert result['status'] == 'success'
        assert result['total_tokens'] == 5000
        assert result.get('accumulator_used') is True

        metrics = (plan_context.plan_dir_for('ep-fallback') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 5000' in metrics
        assert 'tool_uses: 12' in metrics
        # Accumulator's worked window (60000 ms) flows through unclamped.
        assert 'agent_duration_ms: 60000' in metrics

    def test_explicit_flags_override_accumulator(self, plan_context):
        """Explicitly passed flags always win — accumulator does not double-count."""
        cmd_start_phase(_ns_start_phase('ep-override', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('ep-override', '6-finalize', total_tokens=999, tool_uses=99, duration_ms=99999)
        )

        result = cmd_end_phase(
            _ns_end_phase('ep-override', '6-finalize', total_tokens=12345, tool_uses=42, duration_ms=8000)
        )

        assert result['total_tokens'] == 12345
        # accumulator_used flips only when the flag was absent
        assert result.get('accumulator_used') is None or result.get('accumulator_used') is False

    def test_partial_explicit_flags_use_accumulator_for_missing(self, plan_context):
        """end-phase fills only the omitted fields from the accumulator."""
        cmd_start_phase(_ns_start_phase('ep-partial', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('ep-partial', '6-finalize', total_tokens=7777, tool_uses=20, duration_ms=4000)
        )
        # Pin start_time so the clamp is a deterministic no-op (see _pin_start_time_to_past).
        _pin_start_time_to_past('ep-partial', '6-finalize')

        # Pass only --total-tokens; --tool-uses / --duration-ms must come from accumulator.
        result = cmd_end_phase(_ns_end_phase('ep-partial', '6-finalize', total_tokens=10000))

        assert result['total_tokens'] == 10000
        metrics = (plan_context.plan_dir_for('ep-partial') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 10000' in metrics
        assert 'tool_uses: 20' in metrics
        # Accumulator's worked window (4000 ms) flows through unclamped.
        assert 'agent_duration_ms: 4000' in metrics

    def test_no_accumulator_no_flags_records_timestamps_only(self, plan_context):
        """When neither accumulator nor flags are present, end-phase records timestamps only."""
        cmd_start_phase(_ns_start_phase('ep-bare', '6-finalize'))
        result = cmd_end_phase(_ns_end_phase('ep-bare', '6-finalize'))
        assert result['status'] == 'success'
        assert 'total_tokens' not in result

        metrics = (plan_context.plan_dir_for('ep-bare') / 'work' / 'metrics.toon').read_text()
        # No token data should be present, but end_time should be recorded
        assert 'end_time' in metrics
        assert 'total_tokens' not in metrics


class TestRetrospectiveTokensAccumulatorCarry:
    """retrospective_tokens flows accumulate-agent-usage → accumulator file → end-phase / phase-boundary.

    Anchored to lesson 2026-06-08-19-003: the plan-retrospective dispatches under
    `--phase phase-6-finalize`, so its spend is otherwise folded silently into the
    [6-finalize] total. The finalize retrospective step seeds the per-phase
    accumulator with `accumulate-agent-usage --retrospective-tokens`; the
    end-of-phase recorder (cmd_end_phase / cmd_phase_boundary) then reads it back
    as a fallback when its own explicit flag is omitted. These assertions cover
    the full producer (accumulate) → recorder (end-phase / phase-boundary) carry.
    """

    def test_accumulate_records_retrospective_tokens(self, plan_context):
        """accumulate-agent-usage --retrospective-tokens lands in the accumulator file and result."""
        result = cmd_accumulate_agent_usage(
            _ns_accumulate('retro-accum-create', '6-finalize', total_tokens=10000, retrospective_tokens=4000)
        )
        assert result['status'] == 'success'
        assert result['retrospective_tokens'] == 4000
        assert result['total_tokens'] == 10000

        acc_path = (
            plan_context.plan_dir_for('retro-accum-create') / 'work' / 'metrics-accumulator-6-finalize.toon'
        )
        content = acc_path.read_text()
        assert 'retrospective_tokens: 4000' in content

    def test_accumulate_sums_retrospective_tokens_across_calls(self, plan_context):
        """Repeated retrospective_tokens contributions sum like the other accumulator fields."""
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-accum-sum', '6-finalize', retrospective_tokens=1500)
        )
        result = cmd_accumulate_agent_usage(
            _ns_accumulate('retro-accum-sum', '6-finalize', retrospective_tokens=2500)
        )
        assert result['retrospective_tokens'] == 4000

    def test_accumulate_omitted_retrospective_tokens_stays_zero(self, plan_context):
        """A call without --retrospective-tokens leaves the running total at zero."""
        result = cmd_accumulate_agent_usage(
            _ns_accumulate('retro-accum-omit', '6-finalize', total_tokens=500)
        )
        assert result['retrospective_tokens'] == 0

    def test_end_phase_reads_retrospective_tokens_from_accumulator(self, plan_context):
        """end-phase without --retrospective-tokens pulls it from the accumulator file."""
        cmd_start_phase(_ns_start_phase('retro-ep-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-ep-fallback', '6-finalize', total_tokens=8000, retrospective_tokens=3000)
        )
        _pin_start_time_to_past('retro-ep-fallback', '6-finalize')

        result = cmd_end_phase(_ns_end_phase('retro-ep-fallback', '6-finalize'))

        assert result['status'] == 'success'
        assert result['retrospective_tokens'] == 3000
        metrics = (
            plan_context.plan_dir_for('retro-ep-fallback') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 3000' in metrics

    def test_end_phase_explicit_retrospective_tokens_overrides_accumulator(self, plan_context):
        """An explicit --retrospective-tokens flag wins over the accumulator value."""
        cmd_start_phase(_ns_start_phase('retro-ep-override', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-ep-override', '6-finalize', retrospective_tokens=999)
        )
        _pin_start_time_to_past('retro-ep-override', '6-finalize')

        result = cmd_end_phase(
            _ns_end_phase('retro-ep-override', '6-finalize', retrospective_tokens=5000)
        )

        assert result['retrospective_tokens'] == 5000
        metrics = (
            plan_context.plan_dir_for('retro-ep-override') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 5000' in metrics

    def test_end_phase_no_accumulator_no_flag_omits_retrospective_tokens(self, plan_context):
        """Without an accumulator value and without the flag, the field never appears."""
        cmd_start_phase(_ns_start_phase('retro-ep-absent', '6-finalize'))
        result = cmd_end_phase(_ns_end_phase('retro-ep-absent', '6-finalize', total_tokens=1000))

        assert result['status'] == 'success'
        assert 'retrospective_tokens' not in result
        metrics = (
            plan_context.plan_dir_for('retro-ep-absent') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics

    def test_end_phase_zero_accumulator_omits_retrospective_tokens(self, plan_context):
        """When the accumulator carries retrospective_tokens=0, end-phase omits the field.

        The documentation states the field should be absent when no retrospective ran.
        A zero accumulator value must not be written (it is indistinguishable from
        'no retrospective ran').
        """
        cmd_start_phase(_ns_start_phase('retro-ep-zero', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-ep-zero', '6-finalize', total_tokens=5000, retrospective_tokens=0)
        )
        _pin_start_time_to_past('retro-ep-zero', '6-finalize')

        result = cmd_end_phase(_ns_end_phase('retro-ep-zero', '6-finalize'))

        assert result['status'] == 'success'
        assert 'retrospective_tokens' not in result
        metrics = (
            plan_context.plan_dir_for('retro-ep-zero') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics

    def test_phase_boundary_reads_retrospective_tokens_from_accumulator(self, plan_context):
        """phase-boundary closes the prev phase reading retrospective_tokens from its accumulator."""
        cmd_start_phase(_ns_start_phase('retro-pb-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-pb-fallback', '6-finalize', total_tokens=7000, retrospective_tokens=2200)
        )
        _pin_start_time_to_past('retro-pb-fallback', '6-finalize')

        result = manage_metrics.cmd_phase_boundary(
            _ns_phase_boundary('retro-pb-fallback', prev_phase='6-finalize', next_phase='6-finalize')
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-fallback') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 2200' in metrics

    def test_phase_boundary_explicit_retrospective_tokens_overrides_accumulator(self, plan_context):
        """An explicit --retrospective-tokens flag on phase-boundary wins over the accumulator."""
        cmd_start_phase(_ns_start_phase('retro-pb-override', '5-execute'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-pb-override', '5-execute', retrospective_tokens=111)
        )
        _pin_start_time_to_past('retro-pb-override', '5-execute')

        result = manage_metrics.cmd_phase_boundary(
            _ns_phase_boundary(
                'retro-pb-override',
                prev_phase='5-execute',
                next_phase='6-finalize',
                retrospective_tokens=6000,
            )
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-override') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 6000' in metrics

    def test_phase_boundary_zero_accumulator_omits_retrospective_tokens(self, plan_context):
        """When the accumulator carries retrospective_tokens=0, phase-boundary omits the field.

        Symmetric with test_end_phase_zero_accumulator_omits_retrospective_tokens: a zero
        accumulator value must not be written to the closed phase row.
        """
        cmd_start_phase(_ns_start_phase('retro-pb-zero', '6-finalize'))
        cmd_accumulate_agent_usage(
            _ns_accumulate('retro-pb-zero', '6-finalize', total_tokens=4000, retrospective_tokens=0)
        )
        _pin_start_time_to_past('retro-pb-zero', '6-finalize')

        result = manage_metrics.cmd_phase_boundary(
            _ns_phase_boundary('retro-pb-zero', prev_phase='6-finalize', next_phase='6-finalize')
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-zero') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics


class TestClampWorkedToWall:
    """Direct, timing-independent coverage of _clamp_worked_to_wall.

    The end-phase integration tests pin start_time to the past so the clamp is a
    no-op (the back-to-back wall span is machine-dependent). These unit tests cover
    the clamp's three branches deterministically by passing phase_data explicitly.
    """

    def test_clamps_down_when_wall_span_smaller_than_worked(self):
        """When the wall span is shorter than the worked window, clamp to the wall span."""
        clamped = manage_metrics._clamp_worked_to_wall({'duration_seconds': 1.0}, 4000)
        assert clamped == 1000

    def test_returns_worked_when_wall_span_larger(self):
        """When the wall span exceeds the worked window, return the worked value unchanged."""
        clamped = manage_metrics._clamp_worked_to_wall({'duration_seconds': 600.0}, 4000)
        assert clamped == 4000

    def test_returns_worked_when_duration_seconds_absent(self):
        """Without a recorded wall span, the clamp never bounds the worked value."""
        clamped = manage_metrics._clamp_worked_to_wall({}, 4000)
        assert clamped == 4000


# =============================================================================
# Test: _reconcile_accumulator_into_phase (Tier 2 - direct call)
# =============================================================================


class TestReconcileAccumulatorIntoPhase:
    """Direct, deterministic coverage of _reconcile_accumulator_into_phase.

    The helper folds a phase's durable on-disk accumulator totals into its
    metrics row in place, with explicit-wins precedence: a field already present
    on the row (recorded by end-phase / phase-boundary) is NEVER overwritten, and
    only a truthy accumulator value backfills an absent field. These unit tests
    pass phase_data and accumulator dicts explicitly so every branch is exercised
    without touching the filesystem; TestGenerateReconcilesAccumulator covers the
    cmd_generate integration path.
    """

    def test_backfills_all_three_fields_into_unclosed_row(self):
        """An unclosed row (wall span only) is backfilled from the accumulator."""
        # duration_seconds=600 keeps the folded-duration clamp a deterministic no-op.
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 12345, 'tool_uses': 7, 'duration_ms': 60000}
        )
        assert phase_data['total_tokens'] == 12345
        assert phase_data['tool_uses'] == 7
        assert phase_data['agent_duration_ms'] == 60000
        assert phase_data['agent_duration_seconds'] == 60.0

    def test_explicit_total_tokens_is_not_overwritten(self):
        """A row that already carries total_tokens keeps its own value (explicit-wins)."""
        phase_data = {'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'total_tokens': 999})
        assert phase_data['total_tokens'] == 50000

    def test_explicit_tool_uses_is_not_overwritten(self):
        """A row that already carries tool_uses keeps its own value (explicit-wins)."""
        phase_data = {'tool_uses': 30}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'tool_uses': 9})
        assert phase_data['tool_uses'] == 30

    def test_explicit_agent_duration_ms_is_not_overwritten(self):
        """A row with agent_duration_ms is untouched — agent_duration_seconds is not added."""
        phase_data = {'duration_seconds': 600, 'agent_duration_ms': 300000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 99999})
        assert phase_data['agent_duration_ms'] == 300000
        assert 'agent_duration_seconds' not in phase_data

    def test_empty_accumulator_is_a_noop(self):
        """An absent/empty accumulator leaves the row unchanged."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {})
        assert phase_data == {'duration_seconds': 600}

    def test_zero_accumulator_values_are_not_backfilled(self):
        """Falsy accumulator values (zero) never backfill — indistinguishable from absent."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 0, 'tool_uses': 0, 'duration_ms': 0}
        )
        assert 'total_tokens' not in phase_data
        assert 'tool_uses' not in phase_data
        assert 'agent_duration_ms' not in phase_data

    def test_partial_backfill_only_absent_fields(self):
        """Only the absent fields are folded; present fields win."""
        phase_data = {'duration_seconds': 600, 'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 999, 'tool_uses': 7}
        )
        assert phase_data['total_tokens'] == 50000  # explicit wins
        assert phase_data['tool_uses'] == 7  # absent → folded

    def test_duration_clamped_to_wall_span_during_fold(self):
        """A folded duration_ms is clamped to the row's wall span."""
        phase_data = {'duration_seconds': 1.0}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 1000
        assert phase_data['agent_duration_seconds'] == 1.0

    def test_duration_unclamped_when_wall_span_absent(self):
        """Without a recorded wall span the folded duration flows through unclamped."""
        phase_data: dict = {}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 4000
        assert phase_data['agent_duration_seconds'] == 4.0


# =============================================================================
# Test: cmd_generate reconciles each phase against its accumulator
# =============================================================================


class TestGenerateReconcilesAccumulator:
    """cmd_generate folds each phase's durable accumulator into its row before rendering.

    Anchored to the terminal-phase gap: a 6-finalize row that accrued subagent
    tokens (via accumulate-agent-usage) but was never closed by end-phase /
    phase-boundary would otherwise drop those tokens from the report. generate
    reconciles the row against the on-disk accumulator so the snapshot survives,
    while leaving explicitly-closed rows untouched (explicit-wins precedence).
    """

    def test_generate_folds_accumulator_into_unclosed_phase_row(self, plan_context):
        """An unclosed 6-finalize row surfaces its accumulator totals after generate."""
        # Producer: seed the durable accumulator (subagent returns during finalize).
        cmd_accumulate_agent_usage(
            _ns_accumulate(
                'recon-gen-unclosed', '6-finalize', total_tokens=12345, tool_uses=7, duration_ms=60000
            )
        )
        # The phase row exists (wall span recorded) but was never token-closed.
        manage_metrics.write_metrics(
            'recon-gen-unclosed',
            {'phases': {'6-finalize': {'duration_seconds': 600}}},
        )

        result = cmd_generate(_ns_generate('recon-gen-unclosed'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-unclosed')['phases']['6-finalize']
        assert six['total_tokens'] == 12345
        assert six['tool_uses'] == 7
        # 60000 ms < 600 s wall → clamp no-op; folded as agent_duration_ms.
        assert six['agent_duration_ms'] == 60000
        toon = (plan_context.plan_dir_for('recon-gen-unclosed') / 'work' / 'metrics.toon').read_text()
        assert 'agent_duration_ms: 60000' in toon

    def test_generate_preserves_explicit_row_over_divergent_accumulator(self, plan_context):
        """A token-closed row wins over a divergent accumulator (explicit-wins)."""
        cmd_accumulate_agent_usage(
            _ns_accumulate(
                'recon-gen-explicit', '6-finalize', total_tokens=999, tool_uses=9, duration_ms=99999
            )
        )
        manage_metrics.write_metrics(
            'recon-gen-explicit',
            {
                'phases': {
                    '6-finalize': {
                        'duration_seconds': 600,
                        'total_tokens': 50000,
                        'tool_uses': 30,
                        'agent_duration_ms': 300000,
                    },
                },
            },
        )

        result = cmd_generate(_ns_generate('recon-gen-explicit'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-explicit')['phases']['6-finalize']
        assert six['total_tokens'] == 50000
        assert six['tool_uses'] == 30
        assert six['agent_duration_ms'] == 300000

    def test_generate_partial_row_folds_only_absent_fields(self, plan_context):
        """A row with an explicit total_tokens folds only the missing fields from the accumulator."""
        cmd_accumulate_agent_usage(
            _ns_accumulate(
                'recon-gen-partial', '6-finalize', total_tokens=999, tool_uses=7, duration_ms=60000
            )
        )
        manage_metrics.write_metrics(
            'recon-gen-partial',
            {'phases': {'6-finalize': {'duration_seconds': 600, 'total_tokens': 50000}}},
        )

        result = cmd_generate(_ns_generate('recon-gen-partial'))
        assert result['status'] == 'success'

        six = manage_metrics.read_metrics_raw('recon-gen-partial')['phases']['6-finalize']
        assert six['total_tokens'] == 50000  # explicit wins
        assert six['tool_uses'] == 7  # folded from accumulator
        assert six['agent_duration_ms'] == 60000  # folded from accumulator


# =============================================================================
# Test: enrich delegates to the platform-runtime normalized-tokens op
# =============================================================================
#
# manage-metrics no longer parses a transcript. cmd_enrich computes this plan's
# phase windows, invokes the platform-runtime `metrics normalized-tokens` op via
# subprocess, reads the per-phase JSON sidecar the op writes, and persists the
# normalized numbers. These tests patch the subprocess boundary so the op's
# behaviour is simulated without a real Claude transcript.


_ENRICH_TWO_PHASE_METRICS = (
    'plan_id: {plan_id}\n\n'
    'phases:\n'
    '  5-execute:\n'
    '    start_time: 2026-01-01T10:00:00+00:00\n'
    '    end_time: 2026-01-01T11:00:00+00:00\n'
)


class _FakeCompleted:
    """Minimal stand-in for subprocess.CompletedProcess carrying a TOON stdout."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.returncode = 0
        self.stderr = ''


def _patch_runtime_op(monkeypatch, *, status: str, per_phase: dict | None, counters: dict | None):
    """Patch subprocess.run so the runtime-op call writes *per_phase* and returns a TOON.

    The fake reads the ``--output-file`` argument from the constructed argv and
    writes ``per_phase`` to it as JSON (mirroring what the real Claude runtime op
    does), then returns a CompletedProcess whose stdout is a TOON envelope with the
    requested ``status`` and ``counters``.
    """
    counters = counters or {}

    def _fake_run(argv, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        output_file = None
        for i, token in enumerate(argv):
            if token == '--output-file' and i + 1 < len(argv):
                output_file = argv[i + 1]
        if status == 'success' and per_phase is not None and output_file is not None:
            Path(output_file).write_text(json.dumps(per_phase), encoding='utf-8')
        lines = [f'status: {status}', 'operation: metrics normalized-tokens']
        for key, value in counters.items():
            lines.append(f'{key}: {value}')
        return _FakeCompleted('\n'.join(lines) + '\n')

    monkeypatch.setattr(manage_metrics.subprocess, 'run', _fake_run)


class TestEnrichDelegatesToRuntimeOp:
    """cmd_enrich consumes the runtime op's normalized per-phase numbers."""

    def test_persists_normalized_four_fields_and_billing_total(self, plan_context, monkeypatch):
        """A success op response is persisted into the plan's metrics phase row."""
        plan_dir = plan_context.plan_dir_for('enrich-delegate-01')
        manage_metrics.write_metrics(
            'enrich-delegate-01',
            {'plan_id': 'enrich-delegate-01'},
        )
        # Seed the phase window the op will be handed.
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='enrich-delegate-01'), encoding='utf-8'
        )

        per_phase = {
            '5-execute': {
                'input': 1000,
                'output': 200,
                'cache_read': 10000,
                'cache_creation': 400,
                'input_tokens': 1000,
                'output_tokens': 200,
                'cache_read_input_tokens': 10000,
                'cache_creation_input_tokens': 400,
                'billing_weighted_total': 2700,
                'total': 2700,
                'subagent_total_tokens': 7000,
                'subagent_tool_uses': 6,
                'subagent_duration_ms': 30000,
                'subagent_samples': 1,
            }
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase=per_phase,
            counters={
                'message_count': 4,
                'subagent_phases_attributed': 1,
                'subagent_calls_attributed': 1,
                'subagent_transcripts_walked': 1,
                'four_field_phases_attributed': 1,
            },
        )

        result = cmd_enrich(_ns_enrich('enrich-delegate-01', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is True
        assert result['message_count'] == 4
        assert result['subagent_transcripts_walked'] == 1
        assert result['four_field_phases_attributed'] == 1

        five = manage_metrics.read_metrics_raw('enrich-delegate-01')['phases']['5-execute']
        assert five['input_tokens'] == 1000
        assert five['output_tokens'] == 200
        assert five['cache_read_input_tokens'] == 10000
        assert five['cache_creation_input_tokens'] == 400
        assert five['billing_weighted_total'] == 2700
        assert five['subagent_total_tokens'] == 7000
        assert five['subagent_tool_uses'] == 6
        assert five['subagent_duration_ms'] == 30000
        assert five['subagent_samples'] == 1

    def test_noop_response_degrades_gracefully(self, plan_context, monkeypatch):
        """A `no-op` op response (no transcript) yields enriched=False, no persistence."""
        manage_metrics.write_metrics('enrich-delegate-02', {'plan_id': 'enrich-delegate-02'})
        _patch_runtime_op(monkeypatch, status='no-op', per_phase=None, counters={})

        result = cmd_enrich(_ns_enrich('enrich-delegate-02', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is False
        # No four-field data should have been written.
        phases = manage_metrics.read_metrics_raw('enrich-delegate-02').get('phases', {})
        five = phases.get('5-execute', {})
        assert 'input_tokens' not in five

    def test_op_invocation_failure_degrades_gracefully(self, plan_context, monkeypatch):
        """When the subprocess raises, cmd_enrich reports enriched=False (no crash)."""
        manage_metrics.write_metrics('enrich-delegate-03', {'plan_id': 'enrich-delegate-03'})

        def _raise(*args, **kwargs):  # noqa: ANN002, ANN003
            raise OSError('boom')

        monkeypatch.setattr(manage_metrics.subprocess, 'run', _raise)

        result = cmd_enrich(_ns_enrich('enrich-delegate-03', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is False

    def test_non_dict_phase_bucket_is_skipped_without_raising(self, plan_context, monkeypatch):
        """A non-dict per-phase bucket value is skipped, not crashed on (TypeError guard)."""
        plan_dir = plan_context.plan_dir_for('enrich-delegate-04')
        manage_metrics.write_metrics('enrich-delegate-04', {'plan_id': 'enrich-delegate-04'})
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='enrich-delegate-04'), encoding='utf-8'
        )

        # A malformed op sidecar: one valid bucket and one non-dict bucket value.
        per_phase = {
            '5-execute': {
                'input_tokens': 50,
                'output_tokens': 10,
                'billing_weighted_total': 60,
                'total': 60,
            },
            '6-finalize': 'not-a-dict',
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase=per_phase,
            counters={'message_count': 1},
        )

        # Must not raise on the non-dict bucket.
        result = cmd_enrich(_ns_enrich('enrich-delegate-04', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        phases = manage_metrics.read_metrics_raw('enrich-delegate-04')['phases']
        # The valid bucket was persisted; the non-dict bucket was skipped.
        assert phases['5-execute']['input_tokens'] == 50
        assert 'input_tokens' not in phases.get('6-finalize', {})


class TestManageMetricsHasNoTranscriptCode:
    """Regression: the Claude-transcript engine no longer lives in manage-metrics.

    The transcript engine (transcript discovery, message.usage parse, <usage> tag,
    strict-UUID, cache-pricing weights) was relocated to claude_runtime. These
    assertions guard against a re-introduction.
    """

    def test_no_transcript_engine_symbols(self):
        """The removed transcript-engine helpers/constants are absent from the module."""
        for symbol in (
            'USAGE_TAG_RE',
            'USAGE_FIELD_RE',
            'SESSION_ID_RE',
            'USAGE_FOUR_FIELDS',
            'BILLING_WEIGHT_CACHE_READ',
            'BILLING_WEIGHT_CACHE_CREATION',
            '_sum_subagent_transcript',
            '_billing_weighted_total',
            '_attribute_subagent_usage',
            '_add_usage_four_fields',
            '_window_for_timestamp',
            '_extract_text_payload',
            '_resolve_subagent_transcripts',
        ):
            assert not hasattr(manage_metrics, symbol), f'{symbol} should have been relocated'

    def test_source_has_no_claude_transcript_path_or_parse(self):
        """The manage-metrics source no longer hard-codes the Claude transcript layout.

        The ``.claude/projects`` path derivation and the transcript JSONL parse are
        the transcript engine — both relocated to claude_runtime. (The ``<usage>``
        return-tag continues to be consumed by the accumulate-agent-usage storage
        path, so its string still legitimately appears; the assertion targets only
        the transcript-engine markers.)
        """
        source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
        assert '.claude/projects' not in source
        # The strict-UUID transcript guard and cache-pricing weights are gone.
        assert 'SESSION_ID_RE' not in source
        assert 'BILLING_WEIGHT' not in source


class TestGenerateRendersFourFieldUsage:
    """cmd_generate renders the four usage fields and the billing-weighted total."""

    def test_renders_four_fields_and_billing_total(self, plan_context):
        """metrics.md Phase Details renders each new field plus the billing note."""
        manage_metrics.write_metrics(
            'gen-4f',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'input_tokens': 1000,
                        'output_tokens': 200,
                        'cache_read_input_tokens': 10000,
                        'cache_creation_input_tokens': 400,
                        'billing_weighted_total': 2700,
                    },
                },
            },
        )

        result = cmd_generate(_ns_generate('gen-4f'))
        assert result['status'] == 'success'

        md = (plan_context.plan_dir_for('gen-4f') / 'metrics.md').read_text()
        assert '- **Input tokens**: 1,000' in md
        assert '- **Output tokens**: 200' in md
        assert '- **Cache read input tokens**: 10,000' in md
        assert '- **Cache creation input tokens**: 400' in md
        assert '- **Billing-weighted total**: 2,700' in md
        # The honest-semantics note accompanies the billing line.
        assert 'billing-cost figure, not a work-comparable measure' in md

    def test_absent_four_fields_render_nothing(self, plan_context):
        """A phase without the four fields renders no usage-view lines (no '- **Input tokens**')."""
        manage_metrics.write_metrics(
            'gen-4f-absent',
            {
                'phases': {
                    '1-init': {'duration_seconds': 100, 'agent_duration_ms': 50000},
                },
            },
        )

        result = cmd_generate(_ns_generate('gen-4f-absent'))
        assert result['status'] == 'success'

        md = (plan_context.plan_dir_for('gen-4f-absent') / 'metrics.md').read_text()
        assert '- **Input tokens**' not in md
        assert '- **Billing-weighted total**' not in md

    def test_total_tokens_column_unchanged_alongside_four_fields(self, plan_context):
        """The legacy Tokens column still renders total_tokens when the four fields exist."""
        manage_metrics.write_metrics(
            'gen-4f-coexist',
            {
                'phases': {
                    '5-execute': {
                        'duration_seconds': 600,
                        'agent_duration_ms': 300000,
                        'total_tokens': 50000,
                        'input_tokens': 1000,
                        'output_tokens': 200,
                        'billing_weighted_total': 1200,
                    },
                },
            },
        )

        result = cmd_generate(_ns_generate('gen-4f-coexist'))
        assert result['status'] == 'success'
        # total_tokens still flows to the Tokens column / Total tokens detail line.
        assert result['total_tokens'] == 50000
        md = (plan_context.plan_dir_for('gen-4f-coexist') / 'metrics.md').read_text()
        assert '- **Total tokens**: 50,000' in md
        assert '- **Input tokens**: 1,000' in md


# =============================================================================
# Test: first-class partiality fields (Tier 2 - direct import)
# =============================================================================


def _recorded_phase_row() -> dict:
    """A phase row that satisfies the recorded predicate (carries an end_time).

    A canonical phase is "recorded" iff its metrics.toon row carries an
    ``end_time`` (the boundary-close marker). The duration/agent fields are
    incidental — only ``end_time`` drives the partiality verdict — but they
    keep the seeded row shaped like a real closed phase.
    """
    return {
        'start_time': '2020-01-01T00:00:00+00:00',
        'end_time': '2020-01-01T00:10:00+00:00',
        'duration_seconds': 600,
        'agent_duration_ms': 60000,
    }


class TestGeneratePartialityFields:
    """generate emits a first-class partiality verdict across all three surfaces.

    Deliverable 2: ``generate`` derives ``partial`` (true whenever any canonical
    phase lacks a recorded boundary) and ``unrecorded_phases`` (the offending
    canonical phases in phase order). The verdict surfaces in three places:
    the ``generate`` return TOON, two top-level keys in ``metrics.toon``, and a
    ``> Partial: …`` marker rendered under the ``## Phase Breakdown`` heading. A
    fully-recorded six-phase plan reports ``partial: false`` with an empty list
    and renders no marker.
    """

    def test_return_toon_reports_partial_true_with_unrecorded_phase(self, plan_context):
        """An under-counted plan (6-finalize never closed) reports partial=True in the return."""
        # Canonical under-count: the first five phases are closed but 6-finalize
        # never had its boundary recorded (interrupt / loop-back / never-reached).
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-true-return', {'phases': phases})

        result = cmd_generate(_ns_generate('partial-true-return'))
        assert result['status'] == 'success'
        assert result['partial'] is True
        assert result['unrecorded_phases'] == ['6-finalize']

    def test_return_toon_partial_field_is_bool_and_list(self, plan_context):
        """The return carries `partial` as a bool and `unrecorded_phases` as a list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:3]}
        manage_metrics.write_metrics('partial-types', {'phases': phases})

        result = cmd_generate(_ns_generate('partial-types'))
        assert isinstance(result['partial'], bool)
        assert isinstance(result['unrecorded_phases'], list)

    def test_fully_recorded_plan_reports_partial_false(self, plan_context):
        """A plan with all six canonical phases closed reports partial=False, empty list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-false-full', {'phases': phases})

        result = cmd_generate(_ns_generate('partial-false-full'))
        assert result['status'] == 'success'
        assert result['partial'] is False
        assert result['unrecorded_phases'] == []

    def test_unrecorded_phases_listed_in_canonical_order(self, plan_context):
        """unrecorded_phases preserves canonical phase order, not insertion order."""
        # Record only 3-outline and 5-execute; the other four are unrecorded.
        recorded = {'3-outline', '5-execute'}
        phases = {name: _recorded_phase_row() for name in recorded}
        manage_metrics.write_metrics('partial-order', {'phases': phases})

        result = cmd_generate(_ns_generate('partial-order'))
        assert result['partial'] is True
        expected = [name for name in manage_metrics.PHASE_NAMES if name not in recorded]
        assert result['unrecorded_phases'] == expected
        assert result['unrecorded_phases'] == ['1-init', '2-refine', '4-plan', '6-finalize']

    def test_row_without_end_time_counts_as_unrecorded(self, plan_context):
        """The predicate keys on end_time — a started-but-unclosed row is unrecorded.

        Distinguishes "phase has a row" from "phase is recorded": 4-plan carries a
        start_time but no end_time, so it must appear in unrecorded_phases even
        though its row exists.
        """
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        # Strip 4-plan's end_time: a row present but never boundary-closed.
        phases['4-plan'] = {'start_time': '2020-01-01T00:00:00+00:00', 'duration_seconds': 600}
        manage_metrics.write_metrics('partial-unclosed-row', {'phases': phases})

        result = cmd_generate(_ns_generate('partial-unclosed-row'))
        assert result['partial'] is True
        assert result['unrecorded_phases'] == ['4-plan']

    def test_partiality_fields_persisted_to_metrics_toon(self, plan_context):
        """partial and unrecorded_phases land as top-level keys in metrics.toon."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-toon', {'phases': phases})

        cmd_generate(_ns_generate('partial-toon'))

        # Parsed top-level keys (written before the first [phase] block).
        data = manage_metrics.read_metrics_raw('partial-toon')
        assert data['partial'] == 'true'
        assert data['unrecorded_phases'] == '6-finalize'

        # The literal tokens are present in the file (round-trip target).
        toon = (plan_context.plan_dir_for('partial-toon') / 'work' / 'metrics.toon').read_text()
        assert 'partial: true' in toon
        assert 'unrecorded_phases: 6-finalize' in toon

    def test_fully_recorded_metrics_toon_reports_partial_false_empty_list(self, plan_context):
        """A fully-recorded plan persists partial: false with an empty unrecorded list."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-toon-false', {'phases': phases})

        cmd_generate(_ns_generate('partial-toon-false'))

        data = manage_metrics.read_metrics_raw('partial-toon-false')
        assert data['partial'] == 'false'
        assert data['unrecorded_phases'] == ''
        toon = (plan_context.plan_dir_for('partial-toon-false') / 'work' / 'metrics.toon').read_text()
        assert 'partial: false' in toon

    def test_metrics_md_marker_renders_under_phase_breakdown_heading(self, plan_context):
        """The marker line renders between the ## Phase Breakdown heading and the table."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES[:5]}
        manage_metrics.write_metrics('partial-md-marker', {'phases': phases})

        cmd_generate(_ns_generate('partial-md-marker'))

        md = (plan_context.plan_dir_for('partial-md-marker') / 'metrics.md').read_text()
        marker = '> Partial: unrecorded phases — 6-finalize'
        assert marker in md

        md_lines = md.splitlines()
        heading_idx = md_lines.index('## Phase Breakdown')
        marker_idx = next(i for i, line in enumerate(md_lines) if line.startswith('> Partial:'))
        header_idx = next(i for i, line in enumerate(md_lines) if line.startswith('| Phase'))
        # Marker sits after the heading and before the breakdown table header row.
        assert heading_idx < marker_idx < header_idx

    def test_fully_recorded_metrics_md_renders_no_marker(self, plan_context):
        """A fully-recorded plan renders no partiality marker in metrics.md."""
        phases = {name: _recorded_phase_row() for name in manage_metrics.PHASE_NAMES}
        manage_metrics.write_metrics('partial-md-none', {'phases': phases})

        cmd_generate(_ns_generate('partial-md-none'))

        md = (plan_context.plan_dir_for('partial-md-none') / 'metrics.md').read_text()
        assert '> Partial:' not in md


# =============================================================================
# Test: record-dispatch-boundary (Tier 2 - direct import)
# =============================================================================


def _ns_record_dispatch_boundary(
    plan_id: str,
    phase: str,
    termination_cause: str,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
) -> Namespace:
    """Build Namespace for record-dispatch-boundary command.

    The four per-dispatch context-load fields (``input_tokens``,
    ``output_tokens``, ``cache_read_input_tokens``,
    ``cache_creation_input_tokens``) default to ``None`` so every existing call
    site exercises the default-to-0 path that ``cmd_record_dispatch_boundary``
    applies when a flag is omitted, while the legacy five columns stay
    positionally unchanged.
    """
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        termination_cause=termination_cause,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        command='record-dispatch-boundary',
        func=cmd_record_dispatch_boundary,
    )


# The 5 newly added termination causes (3 phase-6 + 2 phase-4 outcomes) along
# with the canonical destination phase for each. The legacy 5-value set
# (voluntary_checkpoint, task_complete_returned_verbatim, harness_cancellation,
# error, clean_exit_queue_empty) is unchanged and already exercised implicitly
# wherever cmd_record_dispatch_boundary is invoked; the new tests focus on the
# extension.
_NEW_TERMINATION_CAUSES_WITH_PHASE = [
    ('step_complete', '6-finalize'),
    ('blocked_user_review', '6-finalize'),
    ('blocked_session_restart', '6-finalize'),
    ('task_batch_complete', '4-plan'),
    ('agent_returned', '4-plan'),
]


class TestDispatchTerminationCausesEnum:
    """Structural assertions on the DISPATCH_TERMINATION_CAUSES tuple."""

    def test_enum_contains_exactly_eleven_values(self):
        """The enum extends to exactly 11 entries — the legacy 5, the phase-6/phase-4
        extension (5), plus the budget_yield phase-5 dispatch-loop signal."""
        assert len(manage_metrics.DISPATCH_TERMINATION_CAUSES) == 11

    def test_enum_preserves_legacy_five_values(self):
        """The legacy 5 entries remain present so prior callers do not break."""
        legacy = {
            'voluntary_checkpoint',
            'task_complete_returned_verbatim',
            'harness_cancellation',
            'error',
            'clean_exit_queue_empty',
        }
        assert legacy.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_6_finalize_causes(self):
        """The three phase-6-finalize outcomes are present in the extended enum."""
        phase6 = {'step_complete', 'blocked_user_review', 'blocked_session_restart'}
        assert phase6.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_4_plan_causes(self):
        """The two phase-4-plan outcomes are present in the extended enum."""
        phase4 = {'task_batch_complete', 'agent_returned'}
        assert phase4.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_budget_yield_cause(self):
        """The phase-5 budget-bounded dispatch loop's yield signal is present."""
        assert 'budget_yield' in manage_metrics.DISPATCH_TERMINATION_CAUSES

    def test_enum_has_no_duplicate_values(self):
        """Every termination cause is distinct — budget_yield is additive, not a rename."""
        causes = manage_metrics.DISPATCH_TERMINATION_CAUSES
        assert len(causes) == len(set(causes))


class TestRecordDispatchBoundaryAcceptsNewCauses:
    """cmd_record_dispatch_boundary accepts each of the 5 new termination causes."""

    @pytest.mark.parametrize(
        'cause,phase',
        _NEW_TERMINATION_CAUSES_WITH_PHASE,
        ids=[c for c, _ in _NEW_TERMINATION_CAUSES_WITH_PHASE],
    )
    def test_new_cause_records_row_to_per_phase_artifact(self, plan_context, cause, phase):
        """Each new termination cause produces a successful record and a per-phase artifact file."""
        plan_id = f'rdb-new-{cause.replace("_", "-")}'
        # Seed status.json so cmd_record_dispatch_boundary's require_plan_exists
        # guard accepts the plan (lesson 2026-05-15-X: orphan-plan-dir guard).
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                phase,
                termination_cause=cause,
                total_tokens=1234,
                tool_uses=5,
                duration_ms=6789,
            )
        )

        assert result['status'] == 'success', result
        assert result['termination_cause'] == cause
        assert result['phase'] == phase
        assert result['total_tokens'] == 1234
        assert result['tool_uses'] == 5
        assert result['duration_ms'] == 6789
        assert result['rows_recorded'] == 1

        # Verify the per-phase artifact file exists at the expected path.
        artifact = pdir / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'
        assert artifact.exists(), f'expected {artifact} to be created'
        content = artifact.read_text(encoding='utf-8')
        assert f'phase: {phase}' in content
        # Each row is "<timestamp>,<cause>,<total>,<tools>,<duration>"; the cause
        # token must appear on the data line.
        assert f',{cause},1234,5,6789' in content

    def test_phase_6_finalize_artifact_path_is_used_for_finalize_causes(self, plan_context):
        """The three phase-6-finalize causes all land in the 6-finalize artifact file."""
        plan_id = 'rdb-phase6-grouped'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('step_complete', 'blocked_user_review', 'blocked_session_restart'):
            result = cmd_record_dispatch_boundary(
                _ns_record_dispatch_boundary(plan_id, '6-finalize', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon'
        assert artifact.exists()
        content = artifact.read_text(encoding='utf-8')
        assert ',step_complete,' in content
        assert ',blocked_user_review,' in content
        assert ',blocked_session_restart,' in content
        # Three data rows were appended into the same file.
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 3

    def test_phase_4_plan_artifact_path_is_used_for_plan_causes(self, plan_context):
        """The two phase-4-plan causes both land in the 4-plan artifact file."""
        plan_id = 'rdb-phase4-grouped'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('task_batch_complete', 'agent_returned'):
            result = cmd_record_dispatch_boundary(
                _ns_record_dispatch_boundary(plan_id, '4-plan', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon'
        assert artifact.exists()
        content = artifact.read_text(encoding='utf-8')
        assert ',task_batch_complete,' in content
        assert ',agent_returned,' in content
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 2


class TestRecordDispatchBoundaryAcceptsBudgetYield:
    """budget_yield is the phase-5 budget-bounded dispatch loop's yield signal.

    The phase-5-execute envelope yields to the orchestrator at a TASK boundary
    when the per-task budget reserve is exhausted; the orchestrator records that
    yield via record-dispatch-boundary with termination_cause=budget_yield. The
    cause lands in the 5-execute artifact file.
    """

    def test_budget_yield_records_row_to_phase_5_artifact(self, plan_context):
        """budget_yield is accepted and recorded into the 5-execute boundary artifact."""
        plan_id = 'rdb-budget-yield'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='budget_yield',
                total_tokens=119000,
                tool_uses=42,
                duration_ms=300000,
            )
        )

        assert result['status'] == 'success', result
        assert result['termination_cause'] == 'budget_yield'
        assert result['phase'] == '5-execute'
        assert result['total_tokens'] == 119000
        assert result['rows_recorded'] == 1

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        assert artifact.exists(), f'expected {artifact} to be created'
        content = artifact.read_text(encoding='utf-8')
        assert 'phase: 5-execute' in content
        assert ',budget_yield,119000,42,300000' in content

    def test_budget_yield_appends_alongside_other_phase_5_causes(self, plan_context):
        """budget_yield rows coexist with other 5-execute causes in the same artifact."""
        plan_id = 'rdb-budget-yield-mixed'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('budget_yield', 'clean_exit_queue_empty'):
            result = cmd_record_dispatch_boundary(
                _ns_record_dispatch_boundary(plan_id, '5-execute', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        assert ',budget_yield,' in content
        assert ',clean_exit_queue_empty,' in content
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 2


class TestRecordDispatchBoundaryRejectsInvalidCause:
    """An unknown termination_cause still surfaces the structured error."""

    def test_invalid_cause_returns_invalid_termination_cause_error(self, plan_context):
        """An unknown cause produces status=error with error=invalid_termination_cause."""
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                'rdb-invalid-cause', '6-finalize', termination_cause='not_a_real_cause'
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_termination_cause'
        assert 'not_a_real_cause' in str(result.get('message', ''))

    def test_legacy_unknown_value_still_rejected(self, plan_context):
        """The legacy fallback value 'unknown' was removed and must continue to reject."""
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                'rdb-legacy-unknown', '6-finalize', termination_cause='unknown'
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_termination_cause'


class TestRecordDispatchBoundaryLegacyCausesStillPass:
    """The 5 legacy termination causes continue to record successfully."""

    @pytest.mark.parametrize(
        'cause',
        [
            'voluntary_checkpoint',
            'task_complete_returned_verbatim',
            'harness_cancellation',
            'error',
            'clean_exit_queue_empty',
        ],
    )
    def test_legacy_cause_records_row(self, plan_context, cause):
        """Each legacy termination cause still produces a successful record."""
        plan_id = f'rdb-legacy-{cause.replace("_", "-")}'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(plan_id, '5-execute', termination_cause=cause)
        )
        assert result['status'] == 'success'
        assert result['termination_cause'] == cause
        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        assert artifact.exists()
        assert f',{cause},' in artifact.read_text(encoding='utf-8')


class TestRecordDispatchBoundaryContextLoadColumns:
    """The four per-dispatch context-load columns are appended after the legacy five.

    Deliverable 4: record-dispatch-boundary records four context-load columns —
    ``input_tokens``, ``output_tokens``, ``cache_read_input_tokens``,
    ``cache_creation_input_tokens`` — appended at the END of each row. They
    default to 0 when their flags are omitted, mirroring the existing optional
    ``total_tokens`` / ``tool_uses`` / ``duration_ms`` fields, and the legacy
    five columns (``timestamp``, ``termination_cause``, ``total_tokens``,
    ``tool_uses``, ``duration_ms``) stay positionally unchanged. The canonical
    column order / count / defaults are owned by manage-metrics
    ``standards/data-format.md`` (Per-Dispatch Context-Load Attribution section).
    """

    def test_context_load_columns_recorded_when_supplied(self, plan_context):
        """All four context-load flags land in the result dict and the data row."""
        plan_id = 'rdb-ctx-supplied'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=84211,
                tool_uses=38,
                duration_ms=412390,
                input_tokens=38000,
                output_tokens=4000,
                cache_read_input_tokens=210000,
                cache_creation_input_tokens=12000,
            )
        )

        assert result['status'] == 'success', result
        assert result['input_tokens'] == 38000
        assert result['output_tokens'] == 4000
        assert result['cache_read_input_tokens'] == 210000
        assert result['cache_creation_input_tokens'] == 12000

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # Full nine-column data row: legacy five then the four context-load columns.
        assert ',clean_exit_queue_empty,84211,38,412390,38000,4000,210000,12000' in content

    def test_context_load_columns_default_to_zero_when_omitted(self, plan_context):
        """Omitting the four flags records 0 for each (result dict + row tail)."""
        plan_id = 'rdb-ctx-default-zero'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=1000,
                tool_uses=5,
                duration_ms=2000,
            )
        )

        assert result['status'] == 'success', result
        assert result['input_tokens'] == 0
        assert result['output_tokens'] == 0
        assert result['cache_read_input_tokens'] == 0
        assert result['cache_creation_input_tokens'] == 0

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # Legacy five carry the supplied values; the four context columns are 0.
        assert ',clean_exit_queue_empty,1000,5,2000,0,0,0,0' in content

    def test_header_declares_nine_column_order(self, plan_context):
        """The artifact header lists the legacy five then the four context-load columns."""
        plan_id = 'rdb-ctx-header'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id, '5-execute', termination_cause='clean_exit_queue_empty'
            )
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        assert (
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
            'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:'
        ) in content

    def test_legacy_five_columns_positionally_unchanged(self, plan_context):
        """The first five comma-fields are the legacy columns in order, with the
        four context-load columns following at positions 5-8."""
        plan_id = 'rdb-ctx-positional'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='budget_yield',
                total_tokens=1234,
                tool_uses=5,
                duration_ms=6789,
                input_tokens=11,
                output_tokens=22,
                cache_read_input_tokens=33,
                cache_creation_input_tokens=44,
            )
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        data_lines = [
            line for line in artifact.read_text(encoding='utf-8').splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 1
        parts = data_lines[0].split(',')
        # Nine columns total: legacy five at positions 0-4, context-load at 5-8.
        assert len(parts) == 9
        # parts[0] is the timestamp (non-empty); legacy positions 1-4 unchanged.
        assert parts[0]
        assert parts[1] == 'budget_yield'
        assert parts[2] == '1234'
        assert parts[3] == '5'
        assert parts[4] == '6789'
        # The four appended context-load columns follow in canonical order.
        assert parts[5:] == ['11', '22', '33', '44']

    def test_partial_context_load_flags_default_remainder_to_zero(self, plan_context):
        """Supplying only input_tokens defaults the other three context columns to 0."""
        plan_id = 'rdb-ctx-partial'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            _ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                input_tokens=500,
            )
        )

        assert result['input_tokens'] == 500
        assert result['output_tokens'] == 0
        assert result['cache_read_input_tokens'] == 0
        assert result['cache_creation_input_tokens'] == 0

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # total/tool/duration omitted → 0; input=500; remaining context cols 0.
        assert ',clean_exit_queue_empty,0,0,0,500,0,0,0' in content


# =============================================================================
# Test: require_plan_exists guard on plan-scoped writers (orphan-plan-dir guard)
# =============================================================================


def _ns_phase_boundary(
    plan_id: str,
    prev_phase: str,
    next_phase: str,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """Build Namespace for phase-boundary command."""
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
        retrospective_tokens=retrospective_tokens,
        command='phase-boundary',
        func=manage_metrics.cmd_phase_boundary,
    )


class TestPlanDirGuardOnWriters:
    """Each plan-scoped writer returns ``plan_not_found`` for an uninitialised plan dir.

    TASK-1 routed every plan-scoped writer through ``_guard_plan_exists``, which
    calls ``require_plan_exists`` and converts ``PlanNotFoundError`` into a
    structured ``error: plan_not_found`` envelope instead of silently creating an
    orphan plan tree. These tests assert the guard fires — and the envelope shape
    is uniform — for each guarded command when the plan dir exists but carries no
    ``status.json`` sentinel (the canonical orphan-plan-dir shape).

    The writers all run their argument validation (phase-name / cause checks)
    BEFORE the guard, so each invocation below uses valid phase names to reach the
    guard branch.
    """

    # (label, callable building the result from an unseeded plan_id) for every
    # writer routed through _guard_plan_exists in manage-metrics.py.
    _GUARDED_WRITERS = [
        ('start-phase', lambda pid: cmd_start_phase(_ns_start_phase(pid, '1-init'))),
        ('end-phase', lambda pid: cmd_end_phase(_ns_end_phase(pid, '1-init'))),
        ('generate', lambda pid: cmd_generate(_ns_generate(pid))),
        (
            'phase-boundary',
            lambda pid: manage_metrics.cmd_phase_boundary(
                _ns_phase_boundary(pid, '4-plan', '5-execute')
            ),
        ),
        (
            'accumulate-agent-usage',
            lambda pid: cmd_accumulate_agent_usage(
                _ns_accumulate(pid, '5-execute', total_tokens=10)
            ),
        ),
        ('enrich', lambda pid: cmd_enrich(_ns_enrich(pid, 'any-session'))),
    ]

    @pytest.mark.parametrize(
        'label,invoke',
        _GUARDED_WRITERS,
        ids=[label for label, _ in _GUARDED_WRITERS],
    )
    def test_writer_returns_plan_not_found_for_orphan_plan_dir(
        self, plan_context, label, invoke
    ):
        """An orphan plan dir (exists, no status.json) yields error: plan_not_found."""
        plan_id = _register_unseeded(f'guard-orphan-{label}')
        plan_dir = _unseeded_plan_dir(plan_context, plan_id)

        result = invoke(plan_id)

        assert result['status'] == 'error', result
        assert result['error'] == 'plan_not_found', result
        assert result['plan_id'] == plan_id
        # The envelope surfaces the resolved plan dir and a human-readable message.
        assert str(plan_dir) == result['plan_dir']
        assert 'status.json' in str(result['message'])

        # The guard must NOT have created any metrics artifact for the orphan plan.
        assert not (plan_dir / 'work' / 'metrics.toon').exists()

    @pytest.mark.parametrize(
        'label,invoke',
        _GUARDED_WRITERS,
        ids=[label for label, _ in _GUARDED_WRITERS],
    )
    def test_writer_returns_plan_not_found_when_plan_dir_absent(
        self, plan_context, label, invoke
    ):
        """A plan_id whose dir was never created also trips the guard."""
        plan_id = _register_unseeded(f'guard-absent-{label}')
        # Deliberately do NOT create the directory — the guard must reject it.

        result = invoke(plan_id)

        assert result['status'] == 'error', result
        assert result['error'] == 'plan_not_found', result
        assert result['plan_id'] == plan_id

    def test_writer_succeeds_once_status_json_is_seeded(self, plan_context):
        """Control case: seeding the sentinel flips the same writer back to success.

        Guards the negative tests against a false positive — the failure must come
        from the missing sentinel, not from an unrelated error in the writer path.
        """
        plan_id = 'guard-positive-control'
        # Seeded via the autouse fixture (plan_id is not registered as unseeded).
        result = cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
        assert result['status'] == 'success', result
        assert result['phase'] == '1-init'


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: ``cmd_accumulate_agent_usage``'s
    docstring must spell the accumulator location as ``.plan/local/plans/`` — the
    legacy bare ``.plan/plans/`` form is incorrect since runtime state moved
    under ``.plan/local``.
    """
    import re

    source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
