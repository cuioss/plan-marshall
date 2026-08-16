# SPDX-License-Identifier: FSL-1.1-ALv2
"""Transcript-reading and budget-measurement contract (``extract-chat-signal.py``).

The pre-pass reads a file from disk and measures the reduced text against a
byte budget. Both are contracts other documents rely on: the
``transcript_unavailable`` skip token is normative in
``references/chat-history-analysis.md``, and ``over_budget`` selects the tier.

These are the scalar computations at the edges of the reduction — encoding,
budget comparison, decode robustness, and the role guards that decide which
turns the gate-decision scan may see.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import chat_turn  # noqa: E402

from conftest import load_script_module, parse_ns  # noqa: E402

_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)
_gate = load_script_module('plan-marshall', 'plan-retrospective', '_chat_gate_decisions.py')

BUNDLE, SKILL, SCRIPT = 'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py'


def _run(path: Path, *extra: str) -> dict:
    args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--transcript-path', str(path), *extra)
    return _mod.cmd_run(args)


def _write(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / 'session.jsonl'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


class TestByteMeasurement:
    def test_reduced_bytes_counts_utf8_bytes_not_characters(self, tmp_path):
        """The budget is a BYTE budget, and non-ASCII text costs more than one.

        Measuring characters under-reports the size of any transcript that is
        not plain ASCII, so a reduction several times over the read budget
        would be fed to the Tier-1 prompt as if it fit.
        """
        text = '請修正這個過濾器' * 400
        result = _run(_write(tmp_path, chat_turn('user', text)))

        assert result['reduced_bytes'] == len(result['reduced_transcript'].encode('utf-8'))
        assert result['reduced_bytes'] > len(result['reduced_transcript'])

    def test_non_ascii_transcript_trips_the_budget_it_exceeds(self, tmp_path):
        """The same text, measured in bytes, is correctly refused."""
        text = '請修正這個過濾器' * 400
        result = _run(_write(tmp_path, chat_turn('user', text)), '--read-budget-bytes', '6000')
        assert result['over_budget'] is True


class TestBudgetBoundary:
    def test_reduced_text_exactly_at_the_budget_is_not_over(self, tmp_path):
        """`over_budget` is strictly greater-than: an exact fit still routes.

        At the boundary a `>=` comparison refuses a transcript that fits, which
        is a false Tier-2 skip.
        """
        result = _run(_write(tmp_path, chat_turn('user', 'x' * 100)))
        exact = result['reduced_bytes']
        at_budget = _run(_write(tmp_path, chat_turn('user', 'x' * 100)), '--read-budget-bytes', str(exact))
        one_under = _run(_write(tmp_path, chat_turn('user', 'x' * 100)), '--read-budget-bytes', str(exact - 1))

        assert at_budget['over_budget'] is False
        assert one_under['over_budget'] is True


class TestTranscriptReading:
    def test_invalid_utf8_degrades_instead_of_failing(self, tmp_path):
        """A malformed byte must not take down the whole aspect.

        The reduction is a pre-pass over a file nobody controls; a strict
        decode would lose every operator turn in the transcript rather than
        the one damaged line.
        """
        path = tmp_path / 'session.jsonl'
        payload = chat_turn('user', 'please revert that change').encode('utf-8')
        path.write_bytes(b'{"broken": "\xe9"}\n' + payload + b'\n')

        result = _run(path)
        assert result['status'] == 'success'
        assert result['operator_turn_count'] == 1

    def test_a_directory_path_reports_the_unavailable_token(self, tmp_path):
        """The skip token is normative, so every unreadable path must yield it.

        Letting the error escape would surface `internal_error` instead of
        `transcript_unavailable`, and downstream aggregation keys on the token.
        """
        result = _run(tmp_path)
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'
        assert result['no_signal'] is True


class TestRoleGuards:
    def test_a_tool_result_on_an_assistant_turn_is_not_a_gate_decision(self, tmp_path):
        """Only a `user` turn carries the operator's side of the channel."""
        line = chat_turn('assistant', [
            {'type': 'tool_result', 'tool_use_id': 'tu_1', 'content': 'Option A'},
        ])
        result = _run(_write(tmp_path, chat_turn('assistant', [
            {'type': 'tool_use', 'name': _gate.OPERATOR_DECISION_TOOL, 'id': 'tu_1'},
        ]), line))
        assert result['gate_decision_count'] == 0

    def test_a_user_turn_cannot_register_its_own_decision_prompt(self, tmp_path):
        """The prompt is the assistant's; a `user` turn claiming one is synthetic.

        Scanning both roles for prompts would let a single crafted turn supply
        the id and answer it — a synthetic input raising an operator counter.
        """
        line = chat_turn('user', [
            {'type': 'tool_use', 'name': _gate.OPERATOR_DECISION_TOOL, 'id': 'tu_2'},
            {'type': 'tool_result', 'tool_use_id': 'tu_2', 'content': 'Option B'},
        ])
        result = _run(_write(tmp_path, line))
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
