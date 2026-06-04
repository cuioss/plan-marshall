#!/usr/bin/env python3
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
) -> Namespace:
    """Build Namespace for end-phase command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
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
) -> Namespace:
    """Build Namespace for accumulate-agent-usage command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
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
# Test: enrich subagent attribution (Tier 2 - direct import)
# =============================================================================


def _write_synthetic_transcript(transcript_path: Path, entries: list[dict]) -> None:
    """Materialise a JSONL transcript file from a list of entry dicts."""
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with transcript_path.open('w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def _agent_return_entry(timestamp: str, usage_block: str) -> dict:
    """Build a JSONL entry shaped like a Claude Code tool_result with embedded <usage>."""
    return {
        'timestamp': timestamp,
        'message': {
            'role': 'user',
            'content': [
                {
                    'type': 'tool_result',
                    'tool_use_id': 'toolu_test',
                    'content': [
                        {'type': 'text', 'text': usage_block},
                    ],
                }
            ],
        },
    }


def _main_context_entry(timestamp: str, input_tokens: int, output_tokens: int) -> dict:
    """Build a JSONL entry shaped like an assistant message with main-context usage."""
    return {
        'timestamp': timestamp,
        'message': {
            'role': 'assistant',
            'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens},
            'content': [{'type': 'text', 'text': 'Working...'}],
        },
    }


_DETERMINISTIC_METRICS_TOON = """plan_id: {plan_id}

[5-execute]
  start_time: 2026-03-27T10:00:00+00:00
  end_time: 2026-03-27T10:30:00+00:00

[6-finalize]
  start_time: 2026-03-27T10:30:01+00:00
  end_time: 2026-03-27T11:00:00+00:00
"""


class TestEnrichSubagentAttribution:
    """enrich walks tool_result content for <usage> tags and attributes by phase window."""

    def _seed_deterministic_metrics(self, plan_dir: Path, plan_id: str) -> None:
        """Write metrics.toon with hand-picked, well-separated phase windows."""
        metrics_path = plan_dir / 'work' / 'metrics.toon'
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(_DETERMINISTIC_METRICS_TOON.format(plan_id=plan_id))

    def test_attributes_subagent_usage_to_matching_phase(self, plan_context, monkeypatch, tmp_path):
        """Subagent <usage> tags fall into the phase whose start/end window contains them."""
        self._seed_deterministic_metrics(plan_context.plan_dir_for('enrich-attr'), 'enrich-attr')

        session_id = 'session-attr'
        projects_root = tmp_path / 'home' / '.claude' / 'projects' / 'plan'
        transcript_path = projects_root / f'{session_id}.jsonl'
        entries = [
            _main_context_entry('2026-03-27T10:15:00+00:00', input_tokens=1000, output_tokens=200),
            _agent_return_entry(
                '2026-03-27T10:15:00+00:00',
                '<usage>total_tokens: 4000\ntool_uses: 5\nduration_ms: 25000</usage>',
            ),
            _agent_return_entry(
                '2026-03-27T10:45:00+00:00',
                '<usage>total_tokens: 9000\ntool_uses: 18\nduration_ms: 90000</usage>',
            ),
        ]
        _write_synthetic_transcript(transcript_path, entries)

        monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path / 'home'))

        result = cmd_enrich(_ns_enrich('enrich-attr', session_id))

        assert result['status'] == 'success'
        assert result['enriched'] is True
        assert result['subagent_phases_attributed'] == 2
        assert result['subagent_calls_attributed'] == 2

        metrics_after = (plan_context.plan_dir_for('enrich-attr') / 'work' / 'metrics.toon').read_text()
        assert 'subagent_total_tokens: 4000' in metrics_after
        assert 'subagent_total_tokens: 9000' in metrics_after

    def test_ignores_subagent_usage_outside_phase_windows(self, plan_context, monkeypatch, tmp_path):
        """Subagent calls whose timestamps predate / postdate any phase window are dropped."""
        self._seed_deterministic_metrics(plan_context.plan_dir_for('enrich-out'), 'enrich-out')

        session_id = 'session-out'
        projects_root = tmp_path / 'home' / '.claude' / 'projects' / 'plan'
        transcript_path = projects_root / f'{session_id}.jsonl'
        entries = [
            # timestamp before any phase started
            _agent_return_entry(
                '1999-01-01T00:00:00+00:00',
                '<usage>total_tokens: 9999\ntool_uses: 99\nduration_ms: 99999</usage>',
            ),
        ]
        _write_synthetic_transcript(transcript_path, entries)

        monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path / 'home'))

        result = cmd_enrich(_ns_enrich('enrich-out', session_id))
        assert result['status'] == 'success'
        assert result['subagent_calls_attributed'] == 0
        assert result['subagent_phases_attributed'] == 0

        metrics_after = (plan_context.plan_dir_for('enrich-out') / 'work' / 'metrics.toon').read_text()
        assert 'subagent_total_tokens' not in metrics_after

    def test_attributes_subagent_tokens_alias_key(self, plan_context, monkeypatch, tmp_path):
        """A <usage> block emitting the `subagent_tokens` alias still yields subagent_total_tokens > 0."""
        self._seed_deterministic_metrics(plan_context.plan_dir_for('enrich-alias'), 'enrich-alias')

        session_id = 'session-alias'
        projects_root = tmp_path / 'home' / '.claude' / 'projects' / 'plan'
        transcript_path = projects_root / f'{session_id}.jsonl'
        entries = [
            _agent_return_entry(
                '2026-03-27T10:15:00+00:00',
                '<usage>subagent_tokens: 7000\ntool_uses: 6\nduration_ms: 30000</usage>',
            ),
        ]
        _write_synthetic_transcript(transcript_path, entries)

        monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path / 'home'))

        result = cmd_enrich(_ns_enrich('enrich-alias', session_id))

        assert result['status'] == 'success'
        assert result['enriched'] is True
        assert result['subagent_calls_attributed'] == 1

        metrics_after = (plan_context.plan_dir_for('enrich-alias') / 'work' / 'metrics.toon').read_text()
        assert 'subagent_total_tokens: 7000' in metrics_after


_TWO_PHASE_METRICS_TOON = """plan_id: {plan_id}

[2-refine]
  start_time: 2026-03-27T09:00:00+00:00
  end_time: 2026-03-27T09:30:00+00:00

[5-execute]
  start_time: 2026-03-27T10:00:00+00:00
  end_time: 2026-03-27T10:30:00+00:00
"""


def _seed_subagent_jsonl(
    sub_dir: Path,
    name: str,
    entries: list[dict],
) -> Path:
    """Write a subagent transcript JSONL with the given message entries."""
    sub_dir.mkdir(parents=True, exist_ok=True)
    path = sub_dir / name
    with path.open('w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    return path


def _subagent_msg(timestamp: str, input_tokens: int, output_tokens: int) -> dict:
    """Build a subagent JSONL entry shaped like a Claude Code assistant message."""
    return {
        'timestamp': timestamp,
        'message': {
            'role': 'assistant',
            'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens},
            'content': [{'type': 'text', 'text': 'sub work'}],
        },
    }


class TestEnrichSubagentTranscriptWalk:
    """cmd_enrich walks ~/.claude/projects/{slug}/{sid}/subagents/agent-*.jsonl per message."""

    _METRICS_FIXTURE = _TWO_PHASE_METRICS_TOON

    def _seed_two_phase_metrics(self, plan_dir: Path, plan_id: str) -> None:
        metrics_path = plan_dir / 'work' / 'metrics.toon'
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(self._METRICS_FIXTURE.format(plan_id=plan_id))

    def _patch_session_paths(self, monkeypatch, tmp_path) -> str:
        """Monkeypatch Path.home and manage_metrics._resolve_cwd to a controlled root.

        Returns the fixed cwd used by manage_metrics for slug derivation.
        """
        fake_cwd = '/fake/repo'
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path / 'home'))
        monkeypatch.setattr(manage_metrics, '_resolve_cwd', lambda: fake_cwd)
        return fake_cwd

    def test_two_subagent_files_counted(self, plan_context, monkeypatch, tmp_path):
        """Two agent-*.jsonl files under {slug}/{sid}/subagents/ are walked and counted."""
        self._seed_two_phase_metrics(plan_context.plan_dir_for('enrich-sub-01'), 'enrich-sub-01')

        fake_cwd = self._patch_session_paths(monkeypatch, tmp_path)
        slug = fake_cwd.replace('/', '-')
        session_id = '11111111-1111-1111-1111-111111111101'

        # Parent transcript: at least one valid message to drive the walk.
        parent_root = tmp_path / 'home' / '.claude' / 'projects' / slug
        parent_transcript = parent_root / f'{session_id}.jsonl'
        _write_synthetic_transcript(parent_transcript, [
            _main_context_entry('2026-03-27T09:15:00+00:00', input_tokens=100, output_tokens=10),
        ])

        sub_dir = parent_root / session_id / 'subagents'
        _seed_subagent_jsonl(
            sub_dir,
            'agent-001.jsonl',
            [
                _subagent_msg('2026-03-27T09:20:00+00:00', 500, 50),
                _subagent_msg('2026-03-27T09:25:00+00:00', 700, 70),
            ],
        )
        _seed_subagent_jsonl(
            sub_dir,
            'agent-002.jsonl',
            [
                _subagent_msg('2026-03-27T10:10:00+00:00', 900, 90),
            ],
        )

        result = cmd_enrich(_ns_enrich('enrich-sub-01', session_id))

        assert result['status'] == 'success'
        assert result['subagent_transcripts_walked'] == 2

    def test_main_context_only_fixture_walks_no_subagents(self, plan_context, monkeypatch, tmp_path):
        """No subagent directory → subagent_transcripts_walked is zero."""
        self._seed_two_phase_metrics(plan_context.plan_dir_for('enrich-sub-02'), 'enrich-sub-02')

        fake_cwd = self._patch_session_paths(monkeypatch, tmp_path)
        slug = fake_cwd.replace('/', '-')
        session_id = '11111111-1111-1111-1111-111111111102'

        parent_root = tmp_path / 'home' / '.claude' / 'projects' / slug
        parent_transcript = parent_root / f'{session_id}.jsonl'
        _write_synthetic_transcript(parent_transcript, [
            _main_context_entry('2026-03-27T09:15:00+00:00', input_tokens=100, output_tokens=10),
        ])
        # Deliberately do NOT seed a subagents directory.

        result = cmd_enrich(_ns_enrich('enrich-sub-02', session_id))

        assert result['status'] == 'success'
        assert result['subagent_transcripts_walked'] == 0

    def test_subagent_transcripts_walked_matches_file_count(self, plan_context, monkeypatch, tmp_path):
        """The subagent_transcripts_walked count matches the number of agent-*.jsonl files discovered."""
        self._seed_two_phase_metrics(plan_context.plan_dir_for('enrich-sub-04'), 'enrich-sub-04')

        fake_cwd = self._patch_session_paths(monkeypatch, tmp_path)
        slug = fake_cwd.replace('/', '-')
        session_id = '11111111-1111-1111-1111-111111111104'

        parent_root = tmp_path / 'home' / '.claude' / 'projects' / slug
        parent_transcript = parent_root / f'{session_id}.jsonl'
        _write_synthetic_transcript(parent_transcript, [
            _main_context_entry('2026-03-27T09:15:00+00:00', input_tokens=10, output_tokens=1),
        ])
        sub_dir = parent_root / session_id / 'subagents'
        for i, name in enumerate(['agent-a.jsonl', 'agent-b.jsonl', 'agent-c.jsonl']):
            _seed_subagent_jsonl(
                sub_dir,
                name,
                [_subagent_msg(f'2026-03-27T09:{20 + i}:00+00:00', 10, 1)],
            )

        result = cmd_enrich(_ns_enrich('enrich-sub-04', session_id))
        assert result['status'] == 'success'
        assert result['subagent_transcripts_walked'] == 3


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
) -> Namespace:
    """Build Namespace for record-dispatch-boundary command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        termination_cause=termination_cause,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
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

    def test_enum_contains_exactly_ten_values(self):
        """The enum extends from the legacy 5 to exactly 10 entries — no more, no less."""
        assert len(manage_metrics.DISPATCH_TERMINATION_CAUSES) == 10

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
) -> Namespace:
    """Build Namespace for phase-boundary command."""
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
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
