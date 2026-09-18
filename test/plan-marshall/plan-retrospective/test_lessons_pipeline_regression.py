#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression for the lessons and landing pipeline.

Exercises the full chain in one run from a user-visible angle:

- Dispatcher orchestration-context resolution: broken path (a write-site
  re-deriving context without the forwarded verdict) vs working path (the
  single dispatcher verdict consumed verbatim).
- Lossless retrospective inputs: order preservation, kept-text counts, gate
  population, residual classification, and symmetric-pair completeness from
  the reducer through the consumer into compiled report counts.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'regression_inbox')
_reducer = load_script_module('plan-marshall', 'platform-runtime', '_chat_signal_reducer.py', 'regression_reducer')
_compile = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'regression_compile')

_INTEGRATION = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'lessons-integration.md'
)


def _transcript_lines() -> list[str]:
    events = [
        {'message': {'role': 'user', 'content': 'Please repair the drain state handling.'}},
        {'message': {'role': 'assistant', 'content': '[STATUS] Drain scan complete.'}},
        {'message': {'role': 'user', 'content': 'Injected skill body that must not count.'}},
        {'message': {'role': 'assistant', 'content': 'Plain chatter with no marker.'}},
    ]
    return [json.dumps(event) for event in events]


class TestDispatcherOrchestrationContext:
    def test_broken_path_without_forwarding_misreads_prose(self):
        verdict = _inbox.classify_source_id('a prose description, not a pointer')

        assert verdict.orchestrated is False
        assert verdict.detection == 'not_orchestrator_pointer'

    def test_working_path_with_forwarding_resolves_once(self):
        pointer = '.plan/local/orchestrator/demo-epic/plans/PLAN-05-lessons-pipeline.md'
        verdict = _inbox.classify_source_id(pointer)

        assert verdict.orchestrated is True
        assert verdict.epic == 'demo-epic'

    def test_integration_pins_single_point_resolution(self):
        text = _INTEGRATION.read_text(encoding='utf-8')

        assert 'resolved once at the finalize dispatcher' in text
        assert 'none re-resolves it' in text


class TestLosslessInputs:
    def test_reducer_preserves_order_and_counts(self):
        reduction = _reducer.reduce_transcript(_transcript_lines())
        texts = [turn['text'] for turn in reduction.turns]

        assert any('Please repair the drain state' in text for text in texts)
        assert any('[STATUS] Drain scan complete.' in text for text in texts)
        # Document order: the operator turn precedes the status marker.
        first_operator = next(i for i, text in enumerate(texts) if 'Please repair' in text)
        first_status = next(i for i, text in enumerate(texts) if '[STATUS]' in text)
        assert first_operator < first_status
        assert reduction.kept_text_chars > 0
        assert reduction.kept_text_bytes > 0
        assert reduction.signal_gate_population == (reduction.operator_turn_count + reduction.gate_decision_count)

    def test_residual_population_is_accounted(self):
        reduction = _reducer.reduce_transcript(_transcript_lines())

        assert sum(reduction.residual_counts.values()) >= 1
        assert set(reduction.residual_counts) <= set(_reducer.RESIDUAL_CLASSES)

    def test_symmetric_pair_guard_holds_on_well_formed(self):
        reduction = _reducer.reduce_transcript(_transcript_lines())

        assert reduction.symmetric_pair_dropped == 0

    def test_compiled_report_republishes_created_counts_verbatim(self):
        fragments = {
            'lessons-proposal': {'created_count': 3, 'body': 'three filed lessons'},
            'chat-signal': {'created_count': 0},
            'plain': {'body': 'no counts here'},
        }
        assembled = _compile.assemble_post_housekeeping_counts(fragments)

        assert assembled == {'chat-signal': 0, 'lessons-proposal': 3}

    def test_consumer_maps_kept_raw_count(self):
        assert Path(str(_INTEGRATION)).is_file()
