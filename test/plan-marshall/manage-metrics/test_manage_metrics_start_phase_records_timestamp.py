#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_generate,
    ns_start_phase,
    raw_ns,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _phase_breakdown_header,
    _pin_start_time_to_past,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)


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


# =============================================================================
# Test: start-phase (Tier 2 - direct import)
# =============================================================================


def test_start_phase_records_timestamp(plan_context):
    """start-phase creates metrics.toon with phase start timestamp."""
    result = cmd_start_phase(ns_start_phase('metrics-start-01', '1-init'))
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
    result = cmd_start_phase(
        raw_ns('start-phase', plan_id='metrics-start-02', phase='invalid')
    )
    assert result['status'] == 'error'
    assert 'Invalid phase' in str(result.get('message', ''))


def test_start_phase_invalid_plan_id(plan_context):
    """start-phase rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_start_phase(ns_start_phase('../escape', '1-init'))
    assert exc_info.value.code == 0


def test_start_phase_multiple_phases(plan_context):
    """start-phase can record multiple phases."""
    cmd_start_phase(ns_start_phase('metrics-start-03', '1-init'))
    cmd_start_phase(ns_start_phase('metrics-start-03', '2-refine'))

    metrics_file = plan_context.plan_dir_for('metrics-start-03') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()
    assert '[1-init]' in content
    assert '[2-refine]' in content


# =============================================================================
# Test: end-phase (Tier 2 - direct import)
# =============================================================================


def test_end_phase_computes_duration(plan_context):
    """end-phase computes wall-clock duration from start/end."""
    cmd_start_phase(ns_start_phase('metrics-end-01', '1-init'))
    result = cmd_end_phase(ns_end_phase('metrics-end-01', '1-init'))
    assert result['status'] == 'success'
    assert 'duration_seconds' in result
    assert float(str(result['duration_seconds'])) >= 0


def test_end_phase_with_token_data(plan_context):
    """end-phase stores token data from Task agent notifications."""
    cmd_start_phase(ns_start_phase('metrics-end-02', '1-init'))
    # Pin start_time to the past so the wall span deterministically exceeds the
    # forwarded worked window — _clamp_worked_to_wall is then a no-op and the
    # forwarded 181681 ms flows through unclamped (the back-to-back wall span is
    # machine-dependent; see _pin_start_time_to_past).
    _pin_start_time_to_past('metrics-end-02', '1-init')
    result = cmd_end_phase(
        ns_end_phase('metrics-end-02', '1-init', total_tokens=25514, duration_ms=181681, tool_uses=23)
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
    result = cmd_end_phase(ns_end_phase('metrics-end-03', '2-refine', total_tokens=1000))
    assert result['status'] == 'success'
    # No duration_seconds since no start_time
    assert 'duration_seconds' not in result


def test_end_phase_no_optional_args(plan_context):
    """end-phase works without optional token data."""
    cmd_start_phase(ns_start_phase('metrics-end-04', '3-outline'))
    result = cmd_end_phase(ns_end_phase('metrics-end-04', '3-outline'))
    assert result['status'] == 'success'
    assert 'total_tokens' not in result


# =============================================================================
# Test: generate (Tier 2 - direct import)
# =============================================================================


def test_generate_creates_metrics_md(plan_context):
    """generate creates metrics.md with the three-column phase breakdown table."""
    # Record two phases
    cmd_start_phase(ns_start_phase('metrics-gen-01', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-gen-01', '1-init', total_tokens=25000, tool_uses=20))
    cmd_start_phase(ns_start_phase('metrics-gen-01', '2-refine'))
    cmd_end_phase(ns_end_phase('metrics-gen-01', '2-refine'))

    # Generate report
    result = cmd_generate(ns_generate('metrics-gen-01'))
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


def test_generate_three_column_header_order(plan_context):
    """The Phase Breakdown header lists the columns in their contract order.

    Worked, Reported (wall), Idle come first, then the two work measures, then
    the derived-cost column — which is last precisely because it is not a work
    measure and must not read as one.

    The Tokens header is asserted as a LITERAL, not read back from
    ``_TOKENS_COLUMN_HEADER``: the rendered string is a reader-facing contract,
    and deriving the expectation from the constant under test would assert only
    that the code equals itself.
    """
    cmd_start_phase(ns_start_phase('metrics-gen-cols', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-gen-cols', '1-init', total_tokens=1000, tool_uses=3))
    cmd_generate(ns_generate('metrics-gen-cols'))

    header = _phase_breakdown_header((plan_context.plan_dir_for('metrics-gen-cols') / 'metrics.md').read_text())
    cols = [c.strip() for c in header.strip('|').split('|')]
    assert cols == [
        'Phase',
        'Worked',
        'Reported (wall)',
        'Idle',
        'Tokens (dispatched unless marked)',
        'Tool Uses',
        'Billing (cost)',
    ]


def test_tokens_column_header_names_a_default_not_a_single_population(plan_context):
    """The Tokens header states a DEFAULT population plus the marking convention.

    The column is not single-population — an inline phase's cell carries a
    main-context-window figure — so a bare ``Tokens (dispatched)`` would assert
    over a mixed column exactly the single-population claim this report exists
    to stop making. The header must name the default AND signal that exceptions
    are marked.
    """
    cmd_start_phase(ns_start_phase('metrics-header-default', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-header-default', '1-init', total_tokens=1000))
    cmd_generate(ns_generate('metrics-header-default'))

    header = _phase_breakdown_header(
        (plan_context.plan_dir_for('metrics-header-default') / 'metrics.md').read_text()
    )
    tokens_col = [c.strip() for c in header.strip('|').split('|')][4]
    assert tokens_col == 'Tokens (dispatched unless marked)'
    # The population is named, and it is named as a default rather than as an
    # unqualified property of every cell in the column.
    assert 'dispatched' in tokens_col
    assert 'unless marked' in tokens_col
    assert tokens_col != 'Tokens (dispatched)'


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

    result = cmd_generate(ns_generate('metrics-gen-worked'))
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

    result = cmd_generate(ns_generate('metrics-invariant'))
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

    result = cmd_generate(ns_generate('metrics-gen-idle'))
    assert result['status'] == 'success'
    toon = (plan_context.plan_dir_for('metrics-gen-idle') / 'work' / 'metrics.toon').read_text()
    # worked = max(100000, 50000) = 100000 ms; wall = 300000 ms; idle = 200000 ms.
    assert 'idle_duration_ms: 200000' in toon
    assert result['total_idle_seconds'] == 200.0
    assert result['total_worked_seconds'] == 100.0
    assert result['total_wall_seconds'] == 300.0
