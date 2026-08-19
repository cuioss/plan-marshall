#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


from pathlib import Path

import pytest
from _manage_metrics_fixtures import (
    ns_enrich,
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _ENRICH_TWO_PHASE_METRICS,
    _UNSEEDED_PLAN_IDS,
    SCRIPT_PATH,
    _patch_runtime_op,
    cmd_enrich,
    cmd_generate,
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

        result = cmd_enrich(ns_enrich('enrich-delegate-01', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

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

        result = cmd_enrich(ns_enrich('enrich-delegate-02', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

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

        result = cmd_enrich(ns_enrich('enrich-delegate-03', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

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
        result = cmd_enrich(ns_enrich('enrich-delegate-04', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

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

        result = cmd_generate(ns_generate('gen-4f'))
        assert result['status'] == 'success'

        md = (plan_context.plan_dir_for('gen-4f') / 'metrics.md').read_text()
        assert '- **Input tokens**: 1,000' in md
        assert '- **Output tokens**: 200' in md
        assert '- **Cache read input tokens**: 10,000' in md
        assert '- **Cache creation input tokens**: 400' in md
        assert '- **Billing-weighted total**: 2,700' in md
        # The bullet DEFINES the measure — names its population and its weights —
        # rather than apologising for rendering it.
        assert 'derived-cost population' in md
        assert '0.1 × cache_read' in md
        assert '1.25 × cache_creation' in md
        # And the figure now also has a first-class column of its own.
        assert 'Billing (cost)' in md

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

        result = cmd_generate(ns_generate('gen-4f-absent'))
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

        result = cmd_generate(ns_generate('gen-4f-coexist'))
        assert result['status'] == 'success'
        # total_tokens still flows to the Tokens column / Total tokens detail line.
        assert result['total_tokens'] == 50000
        md = (plan_context.plan_dir_for('gen-4f-coexist') / 'metrics.md').read_text()
        assert '- **Total tokens**: 50,000' in md
        assert '- **Input tokens**: 1,000' in md
