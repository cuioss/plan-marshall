# SPDX-License-Identifier: FSL-1.1-ALv2
"""Operator-signal counters and the routing verdict (``extract-chat-signal.py``).

The reduction decides Tier 1 (feed the reduced transcript to the LLM) vs Tier 2
(refuse it) from ``no_signal``. That flag is keyed on OPERATOR-AUTHORED counts,
never on how many turns survived: a survivor count rises with every class of
injected instruction text the filter fails to recognise, so a volume-derived
verdict reports more health as the signal it measures degrades.

The provenance predicate these counters rest on is covered by
``test_chat_provenance.py``; the parsing and output contract by
``test_extract_chat_signal.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import (  # noqa: E402
    OPERATOR_TEXT,
    REENTRY_NOTICE,
    SKILL_LOAD_TEXT,
    SLASH_COMMAND,
    SYSTEM_REMINDER,
    TASK_NOTIFICATION,
    WAKE_ENVELOPE,
    chat_tool_result,
    chat_tool_use,
    chat_turn,
)

from conftest import load_script_module, parse_ns  # noqa: E402

_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)

BUNDLE = 'plan-marshall'
SKILL = 'plan-retrospective'
SCRIPT = 'extract-chat-signal.py'


def _write(tmp_path: Path, *lines: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / 'session.jsonl'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _run(path: Path, *extra: str) -> dict:
    """Invoke ``cmd_run`` through the script's own parser."""
    args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--transcript-path', str(path), *extra)
    return _mod.cmd_run(args)


class TestGateDecisionRecovery:
    def test_ask_user_question_result_is_a_gate_decision(self, tmp_path):
        """On a gated run the operator answers through a tool result.

        A reducer that reads only free-form `user` turns measures only the
        channel the operator did not use, so a well-instrumented run with many
        gate decisions and no corrections reads as silent.
        """
        path = _write(
            tmp_path,
            chat_tool_use(_mod.OPERATOR_DECISION_TOOL, 'tu_1'),
            chat_tool_result('tu_1', 'Approach: rewrite the filter'),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 1
        assert result['operator_turn_count'] == 0
        assert result['no_signal'] is False
        assert 'Approach: rewrite the filter' in result['reduced_transcript']

    def test_operator_refusal_is_a_gate_decision(self, tmp_path):
        """A refused tool call is the operator acting through the permission gate."""
        path = _write(
            tmp_path,
            chat_tool_use('Bash', 'tu_2'),
            chat_tool_result('tu_2', "The user doesn't want to proceed with this tool use."),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 1
        assert result['no_signal'] is False

    def test_ordinary_tool_output_is_not_a_gate_decision(self, tmp_path):
        """The counter fails toward NOT counting — build logs are not decisions."""
        path = _write(
            tmp_path,
            chat_tool_use('Bash', 'tu_3'),
            chat_tool_result('tu_3', 'ruff: All checks passed!\nmypy: Success: no issues found'),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True

    def test_tool_result_quoting_a_refusal_marker_is_not_a_decision(self, tmp_path):
        """A file body that merely CONTAINS a refusal notice is not a decision.

        The reducer runs over this project's own retrospective sessions, so a
        session that read the module declaring these markers would otherwise
        count that read as operator signal and report a clean verdict — a
        synthetic input raising an operator-signal counter, exactly the defect
        the reduction exists to remove. The notice must BE the payload.
        """
        quoted = (
            'OPERATOR_REFUSAL_MARKERS = (\n'
            '    "The user doesn\'t want to proceed with this tool use",\n'
            ')\n'
        )
        path = _write(tmp_path, chat_tool_use('Read', 'tu_5'), chat_tool_result('tu_5', quoted))
        result = _run(path)
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True

    def test_gate_decisions_render_under_a_distinct_role(self, tmp_path):
        """A reader can tell a gate decision from a free-form correction."""
        path = _write(
            tmp_path,
            chat_turn('user', OPERATOR_TEXT),
            chat_tool_use(_mod.OPERATOR_DECISION_TOOL, 'tu_4'),
            chat_tool_result('tu_4', 'Option B'),
        )
        result = _run(path)
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 1
        assert f'{_mod.OPERATOR_DECISION_ROLE}: Option B' in result['reduced_transcript']


class TestOperatorSignalCounters:
    def test_high_volume_low_signal_is_distinguishable(self, tmp_path):
        """Many survivors, one operator turn — the counters keep them apart."""
        lines = [chat_turn('assistant', f'[STATUS] step {n}') for n in range(20)]
        lines.append(chat_turn('user', OPERATOR_TEXT))
        result = _run(_write(tmp_path, *lines))

        assert result['reduced_turn_count'] == 21
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 0

    def test_high_volume_high_signal_is_distinguishable(self, tmp_path):
        """The same survivor count, twenty of them operator-authored."""
        lines = [chat_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(20)]
        lines.append(chat_turn('assistant', '[STATUS] acknowledged'))
        result = _run(_write(tmp_path, *lines))

        assert result['reduced_turn_count'] == 21
        assert result['operator_turn_count'] == 20

    def test_survivor_count_alone_cannot_separate_the_two(self, tmp_path):
        """The defect in one assertion: equal volume, opposite signal.

        Both transcripts reduce to the same number of turns, so the pre-fix
        volume-derived verdict rated them identically.
        """
        low = _run(
            _write(
                tmp_path / 'low',
                *[chat_turn('assistant', f'[STATUS] {n}') for n in range(5)],
                chat_turn('user', OPERATOR_TEXT),
            )
        )
        high = _run(
            _write(
                tmp_path / 'high',
                *[chat_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(5)],
                chat_turn('assistant', '[STATUS] ok'),
            )
        )
        assert low['reduced_turn_count'] == high['reduced_turn_count']
        assert low['operator_turn_count'] != high['operator_turn_count']

    def test_kept_and_dropped_counts_still_sum_to_the_raw_count(self, tmp_path):
        """Recovered gate decisions were never raw turns, so the identity holds.

        `reduced_turn_count + dropped_turn_count == raw_turn_count` is
        arithmetic a caller may rely on; folding synthesised decision entries
        into the kept count would silently break it.
        """
        path = _write(
            tmp_path,
            chat_tool_use(_mod.OPERATOR_DECISION_TOOL, 'tu_6'),
            chat_tool_result('tu_6', 'Option A'),
            chat_turn('user', OPERATOR_TEXT),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 1
        assert (
            result['reduced_turn_count'] + result['dropped_turn_count']
            == result['raw_turn_count']
        )


class TestNoSignalVerdict:
    def test_transcript_of_harness_injections_reports_no_signal(self, tmp_path):
        """The discriminating regression, in the shape that fails pre-fix.

        Every turn here is a harness injection, so the surviving set is
        entirely non-operator. The pre-fix verdict was `len(kept) == 0`, and
        because these envelopes are not the two originally-enumerated classes
        they survived — reporting a healthy transcript over instruction text.
        """
        path = _write(
            tmp_path,
            chat_turn('user', SYSTEM_REMINDER),
            chat_turn('user', TASK_NOTIFICATION),
            chat_turn('user', WAKE_ENVELOPE),
            chat_turn('user', REENTRY_NOTICE),
            chat_turn('user', SKILL_LOAD_TEXT),
        )
        result = _run(path)

        assert result['raw_turn_count'] == 5
        assert result['operator_turn_count'] == 0
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
        assert result['reduced_turn_count'] == 0

    def test_low_retention_with_zero_operator_turns_reports_no_signal(self, tmp_path):
        """Very low retention plus zero operator turns MUST report no signal.

        The single cheapest discriminating assertion. The surviving turn is a
        marker-bearing assistant turn — real volume, no operator signal at all
        — so a verdict keyed on survivors reads clean while a verdict keyed on
        operator provenance reads empty.
        """
        lines = [chat_turn('user', SYSTEM_REMINDER) for _ in range(50)]
        lines.append(chat_turn('assistant', '[DISPATCH] launching agent'))
        result = _run(_write(tmp_path, *lines))

        assert result['raw_turn_count'] == 51
        assert result['reduced_turn_count'] == 1
        assert result['operator_turn_count'] == 0
        assert result['no_signal'] is True

    def test_genuine_operator_transcript_still_routes_normally(self, tmp_path):
        """The mirror guard: precision must not become refusal.

        A real session — operator prose, a slash command, harness noise,
        marker-bearing assistant turns — still reaches Tier 1. A fix that
        started refusing real transcripts would have traded one false verdict
        for another.
        """
        path = _write(
            tmp_path,
            chat_turn('user', OPERATOR_TEXT),
            chat_turn('user', SYSTEM_REMINDER),
            chat_turn('assistant', '[DECISION] chose the positive predicate'),
            chat_turn('user', SLASH_COMMAND),
            chat_turn('user', 'also update the aspect contract in lock-step'),
            chat_turn('user', SKILL_LOAD_TEXT),
        )
        result = _run(path)

        assert result['no_signal'] is False
        assert result['over_budget'] is False
        assert result['operator_turn_count'] == 3
        assert OPERATOR_TEXT in result['reduced_transcript']
        assert 'Base directory for this skill:' not in result['reduced_transcript']

    def test_operator_turn_annotated_by_the_harness_still_routes(self, tmp_path):
        """An operator turn carrying an attached reminder is still signal."""
        path = _write(tmp_path, chat_turn('user', f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}'))
        result = _run(path)
        assert result['operator_turn_count'] == 1
        assert result['no_signal'] is False

    def test_missing_transcript_reports_zero_counters(self, tmp_path):
        """The unavailable-transcript branch carries the counters too."""
        result = _run(tmp_path / 'absent.jsonl')
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'
        assert result['operator_turn_count'] == 0
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
