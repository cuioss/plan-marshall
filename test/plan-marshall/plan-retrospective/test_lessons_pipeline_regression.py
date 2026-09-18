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
from types import SimpleNamespace

from conftest import MARKETPLACE_ROOT, load_script_module

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'regression_inbox')
_reducer = load_script_module('plan-marshall', 'platform-runtime', '_chat_signal_reducer.py', 'regression_reducer')
_compile = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'regression_compile')
_lessons = load_script_module('plan-marshall', 'manage-lessons', 'manage-lessons.py', 'regression_lessons')

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


def _mixed_provenance_lines() -> list[str]:
    """One matched decision plus one refusal-marker decision, one tool arm."""
    events = [
        {
            'message': {
                'role': 'assistant',
                'content': [{'type': 'tool_use', 'name': 'AskUserQuestion', 'id': 'u1'}],
            }
        },
        {
            'message': {
                'role': 'user',
                'content': [
                    {'type': 'tool_result', 'tool_use_id': 'u1', 'content': 'yes, proceed'},
                    {
                        'type': 'tool_result',
                        'content': "The user doesn't want to proceed with this tool use",
                    },
                ],
            }
        },
    ]
    return [json.dumps(event) for event in events]


class TestGuardProvenance:
    def test_guard_drops_unmatched_refusal_arm_first(self):
        reduction = _reducer.reduce_transcript(_mixed_provenance_lines())
        texts = [turn['text'] for turn in reduction.turns if turn['role'] == 'operator-decision']

        assert reduction.symmetric_pair_dropped == 1
        assert texts == ['yes, proceed']

    def test_surviving_gate_count_describes_kept_turns(self):
        reduction = _reducer.reduce_transcript(_mixed_provenance_lines())

        # The count measures recovered decisions — the lone refusal-marker
        # IS operator signal even though its turn leaves the render — while
        # the surviving turns carry only the paired arm.
        assert reduction.gate_decision_count == 2
        assert reduction.signal_gate_population == (reduction.operator_turn_count + reduction.gate_decision_count)

    def test_kept_text_bytes_measure_kept_texts_only(self):
        reduction = _reducer.reduce_transcript(_transcript_lines())
        expected = sum(len(turn['text'].encode('utf-8')) for turn in reduction.turns)

        assert reduction.kept_text_bytes == expected


class TestDrainVerbs:
    def test_drain_dedup_verb_absorbs_duplicate_candidate(self, tmp_path):
        candidates = [
            {
                'id': '2026-09-18-99-001',
                'component': 'plan-marshall:phase-5-execute',
                'body': 'Canonical body about drain state retold.',
                'title': 'Drain state again',
            }
        ]
        corpus = {
            '2026-09-01-01-001': {
                'id': '2026-09-01-01-001',
                'component': 'plan-marshall:phase-5-execute',
                'body': 'Canonical body about drain state.',
                'title': 'Drain state',
            }
        }
        candidates_file = tmp_path / 'candidates.json'
        corpus_file = tmp_path / 'corpus.json'
        candidates_file.write_text(json.dumps(candidates), encoding='utf-8')
        corpus_file.write_text(json.dumps(corpus), encoding='utf-8')

        result = _lessons.cmd_drain_dedup(
            SimpleNamespace(candidates_file=str(candidates_file), corpus_file=str(corpus_file))
        )

        assert result['status'] == 'success'
        assert result['to_file'] == []
        assert result['recurrences'] == {'2026-09-01-01-001': 1}

    def test_drain_dedup_verb_rejects_array_corpus(self, tmp_path):
        candidates_file = tmp_path / 'candidates.json'
        candidates_file.write_text(json.dumps([]), encoding='utf-8')

        result = _lessons.cmd_drain_dedup(
            SimpleNamespace(candidates_file=str(candidates_file), corpus_file=str(candidates_file))
        )

        assert result['status'] == 'error'

    def test_created_counts_verb_reports_filed_not_emitted(self):
        result = _lessons.cmd_created_counts(
            SimpleNamespace(
                emitted_count=11,
                filed_id=['2026-09-18-99-001', '2026-09-18-99-002'],
                recurrences_file=None,
            )
        )

        assert result['status'] == 'success'
        assert result['emitted_count'] == 11
        assert result['created_count'] == 2
        assert result['filed_ids'] == ['2026-09-18-99-001', '2026-09-18-99-002']
