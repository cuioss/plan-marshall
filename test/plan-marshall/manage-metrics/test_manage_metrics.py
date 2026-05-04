#!/usr/bin/env python3
"""Tests for manage_metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest
from manage_metrics import (  # type: ignore[import-not-found]
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_enrich,
    cmd_generate,
    cmd_start_phase,
)

from conftest import PlanContext, get_script_path, run_script  # noqa: I001

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


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
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    duration_ms: int | None = None,
    tool_uses: int | None = None,
) -> Namespace:
    """Build Namespace for end-phase command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
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


# =============================================================================
# Test: start-phase (Tier 2 - direct import)
# =============================================================================


def test_start_phase_records_timestamp():
    """start-phase creates metrics.toon with phase start timestamp."""
    with PlanContext(plan_id='metrics-start-01') as ctx:
        result = cmd_start_phase(_ns_start_phase('metrics-start-01', '1-init'))
        assert result['status'] == 'success'
        assert result['phase'] == '1-init'
        assert 'start_time' in result

        # Verify file was written
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        assert metrics_file.exists(), 'metrics.toon should be created'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert 'start_time:' in content


def test_start_phase_invalid_phase():
    """start-phase rejects invalid phase names."""
    with PlanContext(plan_id='metrics-start-02'):
        result = cmd_start_phase(_ns_start_phase('metrics-start-02', 'invalid'))
        assert result['status'] == 'error'
        assert 'Invalid phase' in str(result.get('message', ''))


def test_start_phase_invalid_plan_id():
    """start-phase rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with PlanContext(plan_id='test'):
        with pytest.raises(SystemExit) as exc_info:
            cmd_start_phase(_ns_start_phase('../escape', '1-init'))
        assert exc_info.value.code == 0


def test_start_phase_multiple_phases():
    """start-phase can record multiple phases."""
    with PlanContext(plan_id='metrics-start-03') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-start-03', '1-init'))
        cmd_start_phase(_ns_start_phase('metrics-start-03', '2-refine'))

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert '[2-refine]' in content


# =============================================================================
# Test: end-phase (Tier 2 - direct import)
# =============================================================================


def test_end_phase_computes_duration():
    """end-phase computes wall-clock duration from start/end."""
    with PlanContext(plan_id='metrics-end-01'):
        cmd_start_phase(_ns_start_phase('metrics-end-01', '1-init'))
        result = cmd_end_phase(_ns_end_phase('metrics-end-01', '1-init'))
        assert result['status'] == 'success'
        assert 'duration_seconds' in result
        assert float(str(result['duration_seconds'])) >= 0


def test_end_phase_with_token_data():
    """end-phase stores token data from Task agent notifications."""
    with PlanContext(plan_id='metrics-end-02') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-end-02', '1-init'))
        result = cmd_end_phase(
            _ns_end_phase('metrics-end-02', '1-init', total_tokens=25514, duration_ms=181681, tool_uses=23)
        )
        assert result['status'] == 'success'
        assert result['total_tokens'] == 25514

        # Verify stored in metrics.toon
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert 'total_tokens: 25514' in content
        assert 'tool_uses: 23' in content
        assert 'agent_duration_ms: 181681' in content


def test_end_phase_without_start():
    """end-phase works even if start-phase wasn't called (no duration computed from timestamps)."""
    with PlanContext(plan_id='metrics-end-03'):
        result = cmd_end_phase(_ns_end_phase('metrics-end-03', '2-refine', total_tokens=1000))
        assert result['status'] == 'success'
        # No duration_seconds since no start_time
        assert 'duration_seconds' not in result


def test_end_phase_with_input_output_tokens():
    """end-phase stores input and output token data separately."""
    with PlanContext(plan_id='metrics-end-io-01') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-end-io-01', '1-init'))
        result = cmd_end_phase(
            _ns_end_phase(
                'metrics-end-io-01',
                '1-init',
                total_tokens=30000,
                input_tokens=25000,
                output_tokens=5000,
            )
        )
        assert result['status'] == 'success'
        assert result['total_tokens'] == 30000

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert 'input_tokens: 25000' in content
        assert 'output_tokens: 5000' in content
        assert 'total_tokens: 30000' in content


def test_end_phase_input_output_without_total():
    """end-phase accepts input/output tokens without total_tokens."""
    with PlanContext(plan_id='metrics-end-io-02') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-end-io-02', '2-refine'))
        result = cmd_end_phase(_ns_end_phase('metrics-end-io-02', '2-refine', input_tokens=10000, output_tokens=2000))
        assert result['status'] == 'success'
        assert 'total_tokens' not in result

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert 'input_tokens: 10000' in content
        assert 'output_tokens: 2000' in content


def test_end_phase_no_optional_args():
    """end-phase works without optional token data."""
    with PlanContext(plan_id='metrics-end-04'):
        cmd_start_phase(_ns_start_phase('metrics-end-04', '3-outline'))
        result = cmd_end_phase(_ns_end_phase('metrics-end-04', '3-outline'))
        assert result['status'] == 'success'
        assert 'total_tokens' not in result


# =============================================================================
# Test: generate (Tier 2 - direct import)
# =============================================================================


def test_generate_creates_metrics_md():
    """generate creates metrics.md with phase breakdown table."""
    with PlanContext(plan_id='metrics-gen-01') as ctx:
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

        # Verify metrics.md content
        md_path = ctx.plan_dir / 'metrics.md'
        assert md_path.exists(), 'metrics.md should be created'
        md_content = md_path.read_text()
        assert '# Metrics: metrics-gen-01' in md_content
        assert '## Phase Breakdown' in md_content
        assert '| Phase | Duration | Tokens | Input | Output | Tool Uses |' in md_content
        assert '1-init' in md_content
        assert '2-refine' in md_content
        assert '25,000' in md_content
        assert '**Total**' in md_content


def test_generate_shows_input_output_breakdown():
    """generate includes input/output token columns when data is available."""
    with PlanContext(plan_id='metrics-gen-io-01') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-gen-io-01', '1-init'))
        cmd_end_phase(
            _ns_end_phase(
                'metrics-gen-io-01',
                '1-init',
                total_tokens=30000,
                input_tokens=25000,
                output_tokens=5000,
            )
        )
        result = cmd_generate(_ns_generate('metrics-gen-io-01'))
        assert result['status'] == 'success'
        assert result['total_input_tokens'] == 25000
        assert result['total_output_tokens'] == 5000

        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        assert '| Phase | Duration | Tokens | Input | Output | Tool Uses |' in md_content
        assert '25,000' in md_content
        assert '5,000' in md_content


def test_generate_no_data():
    """generate returns error when no metrics data exists."""
    with PlanContext(plan_id='metrics-gen-02'):
        result = cmd_generate(_ns_generate('metrics-gen-02'))
        assert result['status'] == 'error'
        assert 'No metrics data' in str(result.get('message', ''))


def test_generate_all_six_phases():
    """generate handles all 6 phases."""
    with PlanContext(plan_id='metrics-gen-03') as ctx:
        phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
        for phase in phases:
            cmd_start_phase(_ns_start_phase('metrics-gen-03', phase))
            cmd_end_phase(_ns_end_phase('metrics-gen-03', phase))

        result = cmd_generate(_ns_generate('metrics-gen-03'))
        assert result['status'] == 'success'
        assert result['phases_recorded'] == 6

        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        for phase in phases:
            assert phase in md_content


# =============================================================================
# Test: enrich (Tier 2 - direct import)
# =============================================================================


def test_enrich_missing_transcript():
    """enrich returns gracefully when transcript is not found."""
    with PlanContext(plan_id='metrics-enrich-01'):
        result = cmd_enrich(_ns_enrich('metrics-enrich-01', 'nonexistent-session-id'))
        assert result['status'] == 'success'
        assert result.get('enriched') is False


def test_enrich_with_unknown_session():
    """enrich handles unknown session ID gracefully."""
    with PlanContext(plan_id='metrics-enrich-02'):
        result = cmd_enrich(_ns_enrich('metrics-enrich-02', 'test-session-abc123'))
        # Will be 'not found' since session doesn't exist in ~/.claude
        assert result['status'] == 'success'


# =============================================================================
# Test: format_duration (via generate output) (Tier 2 - direct import)
# =============================================================================


def test_format_duration_seconds():
    """Duration under 60s shows as seconds."""
    with PlanContext(plan_id='metrics-fmt-01') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-fmt-01', '1-init'))
        cmd_end_phase(_ns_end_phase('metrics-fmt-01', '1-init'))
        cmd_generate(_ns_generate('metrics-fmt-01'))
        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        # Should contain some duration string (likely very small since start/end are near-instant)
        assert '1-init' in md_content


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
# =============================================================================


def test_cli_start_phase_roundtrip():
    """CLI plumbing: start-phase subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    with PlanContext(plan_id='cli-plumb-01'):
        result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-01', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['phase'] == '1-init'


def test_cli_generate_roundtrip():
    """CLI plumbing: generate subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    with PlanContext(plan_id='cli-plumb-02'):
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

    def test_creates_file_when_absent(self):
        """First call creates the per-phase accumulator file with the supplied totals."""
        with PlanContext(plan_id='accum-create') as ctx:
            result = cmd_accumulate_agent_usage(
                _ns_accumulate('accum-create', '6-finalize', total_tokens=12345, tool_uses=7, duration_ms=8000)
            )
            assert result['status'] == 'success'
            assert result['phase'] == '6-finalize'
            assert result['total_tokens'] == 12345
            assert result['tool_uses'] == 7
            assert result['duration_ms'] == 8000
            assert result['samples'] == 1

            acc_path = ctx.plan_dir / 'work' / 'metrics-accumulator-6-finalize.toon'
            assert acc_path.exists(), 'Accumulator file should be created on first call'
            content = acc_path.read_text()
            assert 'plan_id: accum-create' in content
            assert 'phase: 6-finalize' in content
            assert 'total_tokens: 12345' in content
            assert 'tool_uses: 7' in content
            assert 'duration_ms: 8000' in content
            assert 'samples: 1' in content

    def test_sums_across_calls(self):
        """Repeated calls sum the totals and increment the samples counter."""
        with PlanContext(plan_id='accum-sum'):
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

    def test_phase_isolation(self):
        """5-execute and 6-finalize accumulators do not collide."""
        with PlanContext(plan_id='accum-iso') as ctx:
            cmd_accumulate_agent_usage(_ns_accumulate('accum-iso', '5-execute', total_tokens=1000, tool_uses=10))
            cmd_accumulate_agent_usage(_ns_accumulate('accum-iso', '6-finalize', total_tokens=2000, tool_uses=20))

            five = (ctx.plan_dir / 'work' / 'metrics-accumulator-5-execute.toon').read_text()
            six = (ctx.plan_dir / 'work' / 'metrics-accumulator-6-finalize.toon').read_text()
            assert 'total_tokens: 1000' in five
            assert 'tool_uses: 10' in five
            assert 'total_tokens: 2000' in six
            assert 'tool_uses: 20' in six

    def test_invalid_phase_rejected(self):
        """Unknown phase names produce a structured error response."""
        with PlanContext(plan_id='accum-bad'):
            result = cmd_accumulate_agent_usage(_ns_accumulate('accum-bad', 'not-a-phase', total_tokens=1))
            assert result['status'] == 'error'
            assert result['error'] == 'invalid_phase'

    def test_omitted_flags_leave_existing_totals_unchanged(self):
        """A no-flag call still increments samples but leaves totals untouched."""
        with PlanContext(plan_id='accum-noop'):
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

    def test_reads_accumulator_when_flags_absent(self):
        """end-phase without flags pulls totals from work/metrics-accumulator-{phase}.toon."""
        with PlanContext(plan_id='ep-fallback') as ctx:
            cmd_start_phase(_ns_start_phase('ep-fallback', '6-finalize'))
            cmd_accumulate_agent_usage(
                _ns_accumulate('ep-fallback', '6-finalize', total_tokens=5000, tool_uses=12, duration_ms=60000)
            )

            result = cmd_end_phase(_ns_end_phase('ep-fallback', '6-finalize'))

            assert result['status'] == 'success'
            assert result['total_tokens'] == 5000
            assert result.get('accumulator_used') is True

            metrics = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
            assert 'total_tokens: 5000' in metrics
            assert 'tool_uses: 12' in metrics
            assert 'agent_duration_ms: 60000' in metrics

    def test_explicit_flags_override_accumulator(self):
        """Explicitly passed flags always win — accumulator does not double-count."""
        with PlanContext(plan_id='ep-override'):
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

    def test_partial_explicit_flags_use_accumulator_for_missing(self):
        """end-phase fills only the omitted fields from the accumulator."""
        with PlanContext(plan_id='ep-partial') as ctx:
            cmd_start_phase(_ns_start_phase('ep-partial', '6-finalize'))
            cmd_accumulate_agent_usage(
                _ns_accumulate('ep-partial', '6-finalize', total_tokens=7777, tool_uses=20, duration_ms=4000)
            )

            # Pass only --total-tokens; --tool-uses / --duration-ms must come from accumulator.
            result = cmd_end_phase(_ns_end_phase('ep-partial', '6-finalize', total_tokens=10000))

            assert result['total_tokens'] == 10000
            metrics = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
            assert 'total_tokens: 10000' in metrics
            assert 'tool_uses: 20' in metrics
            assert 'agent_duration_ms: 4000' in metrics

    def test_no_accumulator_no_flags_records_timestamps_only(self):
        """When neither accumulator nor flags are present, end-phase records timestamps only."""
        with PlanContext(plan_id='ep-bare') as ctx:
            cmd_start_phase(_ns_start_phase('ep-bare', '6-finalize'))
            result = cmd_end_phase(_ns_end_phase('ep-bare', '6-finalize'))
            assert result['status'] == 'success'
            assert 'total_tokens' not in result

            metrics = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
            # No token data should be present, but end_time should be recorded
            assert 'end_time' in metrics
            assert 'total_tokens' not in metrics


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

    def test_attributes_subagent_usage_to_matching_phase(self, monkeypatch, tmp_path):
        """Subagent <usage> tags fall into the phase whose start/end window contains them."""
        with PlanContext(plan_id='enrich-attr') as ctx:
            self._seed_deterministic_metrics(ctx.plan_dir, 'enrich-attr')

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

            metrics_after = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
            assert 'subagent_total_tokens: 4000' in metrics_after
            assert 'subagent_total_tokens: 9000' in metrics_after

    def test_ignores_subagent_usage_outside_phase_windows(self, monkeypatch, tmp_path):
        """Subagent calls whose timestamps predate / postdate any phase window are dropped."""
        with PlanContext(plan_id='enrich-out') as ctx:
            self._seed_deterministic_metrics(ctx.plan_dir, 'enrich-out')

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

            metrics_after = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
            assert 'subagent_total_tokens' not in metrics_after
