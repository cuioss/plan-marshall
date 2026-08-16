# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provenance-classification and operator-signal tests for ``extract-chat-signal.py``.

The reduction decides Tier 1 (feed the reduced transcript to the LLM) vs Tier 2
(refuse it) from ``no_signal``. That flag is keyed on OPERATOR-AUTHORED counts,
never on how many turns survived: a survivor count rises with every class of
injected instruction text the filter fails to recognise, so a volume-derived
verdict reports more health as the signal it measures degrades.

These tests hold the two directions apart:

- harness-injected turns — using the real block shapes the harness emits, not
  invented ones — must not read as operator signal, however many of them
  survive;
- a genuine operator transcript must still route normally, so a precision fix
  never trades a false-healthy verdict for a false refusal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conftest import load_script_module, parse_ns  # noqa: E402

_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)

BUNDLE = 'plan-marshall'
SKILL = 'plan-retrospective'
SCRIPT = 'extract-chat-signal.py'


# ---------------------------------------------------------------------------
# Real harness block shapes
#
# Every constant below is a shape the harness actually injects, not an invented
# one: a system reminder, a background-task notification, a PR-activity wake
# envelope, a skill body, and the verbatim re-entry notice.
# ---------------------------------------------------------------------------

SYSTEM_REMINDER = (
    '<system-reminder>\n'
    'As you answer the user\'s questions, you can use the following context:\n'
    '# claudeMd\nCodebase and user instructions are shown below.\n'
    '</system-reminder>'
)

TASK_NOTIFICATION = (
    '<task-notification agent="general-purpose" status="completed">\n'
    'The verification sub-agent finished and reported two findings.\n'
    '</task-notification>'
)

WAKE_ENVELOPE = (
    '<wake reason="external-event">'
    '<event source="github" kind="check_run" trust="relay">'
    '{"check": "verify / conclusion", "conclusion": "failure"}'
    '</event></wake>'
)

SKILL_LOAD_TEXT = (
    'Base directory for this skill: /Users/x/.claude/plugins/cache/demo/skills/demo\n\n'
    '# Demo Skill\n\n'
    'Long injected skill body. ' * 40
)

REENTRY_NOTICE = (
    'This session is being continued from a previous conversation that ran out of '
    'context. The conversation is summarized below.'
)

OPERATOR_TEXT = 'stop using the ratio as the check — validate by classification instead'


def _turn(role: str, content) -> str:
    """Produce one JSONL event line carrying a ``message`` with ``role``/``content``."""
    return json.dumps({'type': 'turn', 'message': {'role': role, 'content': content}})


def _tool_use(name: str, use_id: str) -> str:
    """Produce an assistant turn issuing a ``tool_use`` call."""
    return _turn('assistant', [{'type': 'tool_use', 'name': name, 'id': use_id}])


def _tool_result(use_id: str, text: str) -> str:
    """Produce a user turn carrying a ``tool_result`` — the gated-decision channel."""
    return _turn('user', [{'type': 'tool_result', 'tool_use_id': use_id, 'content': text}])


def _write(tmp_path: Path, *lines: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / 'session.jsonl'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _run(path: Path, *extra: str) -> dict:
    """Invoke ``cmd_run`` through the script's own parser."""
    args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--transcript-path', str(path), *extra)
    return _mod.cmd_run(args)


# ---------------------------------------------------------------------------
# The positive predicate
# ---------------------------------------------------------------------------


class TestOperatorAuthoredPredicate:
    def test_operator_prose_is_operator_authored(self):
        """Free-form operator text is the signal the reduction exists to keep."""
        assert _mod.is_operator_authored(OPERATOR_TEXT) is True

    def test_whole_harness_envelope_is_not_operator_authored(self):
        """A turn that is nothing but a harness envelope carries no operator prose."""
        for injected in (SYSTEM_REMINDER, TASK_NOTIFICATION, WAKE_ENVELOPE):
            assert _mod.is_operator_authored(injected) is False

    def test_unrecognised_wrapper_fails_toward_synthetic(self):
        """A wrapper nobody enumerated still classifies as synthetic.

        This is the whole point of the positive predicate. An enumeration of
        known synthetic shapes fails toward "operator" for a wrapper the
        harness adds later, which inflates the survivor count and manufactures
        a falsely healthy verdict; residue-based classification fails the other
        way.
        """
        unknown = '<some-wrapper-invented-after-this-test>\ntext\n</some-wrapper-invented-after-this-test>'
        assert _mod.is_operator_authored(unknown) is False

    def test_stacked_envelopes_leave_no_residue(self):
        """Several concatenated envelopes are still wholly synthetic."""
        assert _mod.is_operator_authored(f'{SYSTEM_REMINDER}\n\n{TASK_NOTIFICATION}') is False

    def test_operator_prose_with_attached_envelope_survives(self):
        """The harness attaches reminders to genuine operator turns.

        Presence of an envelope is not the test — emptiness of the residue is —
        so an operator turn does not become synthetic by being annotated.
        """
        assert _mod.is_operator_authored(f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}') is True

    def test_operator_quoting_markup_survives(self):
        """Markup inside operator prose leaves residue, so the turn is kept."""
        assert _mod.is_operator_authored('replace <div>x</div> with a span') is True

    def test_reentry_notice_is_not_operator_authored(self):
        assert _mod.is_operator_authored(REENTRY_NOTICE) is False

    def test_skill_body_and_empty_remain_synthetic(self):
        """The two originally-enumerated classes still classify as synthetic."""
        assert _mod.is_operator_authored(SKILL_LOAD_TEXT) is False
        assert _mod.is_operator_authored('   \n\t ') is False

    def test_signal_bearing_user_branch_delegates_to_the_predicate(self):
        """``is_signal_bearing`` is the predicate for the ``user`` role."""
        assert _mod.is_signal_bearing('user', SYSTEM_REMINDER) is False
        assert _mod.is_signal_bearing('user', OPERATOR_TEXT) is True


# ---------------------------------------------------------------------------
# The gated-decision channel
# ---------------------------------------------------------------------------


class TestGateDecisionRecovery:
    def test_ask_user_question_result_is_a_gate_decision(self, tmp_path):
        """On a gated run the operator answers through a tool result.

        A reducer that reads only free-form ``user`` turns measures only the
        channel the operator did not use, so a well-instrumented run with many
        gate decisions and no corrections reads as silent.
        """
        path = _write(
            tmp_path,
            _tool_use(_mod.OPERATOR_DECISION_TOOL, 'tu_1'),
            _tool_result('tu_1', 'Approach: rewrite the filter'),
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
            _tool_use('Bash', 'tu_2'),
            _tool_result('tu_2', "The user doesn't want to proceed with this tool use."),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 1
        assert result['no_signal'] is False

    def test_ordinary_tool_output_is_not_a_gate_decision(self, tmp_path):
        """The counter fails toward NOT counting — build logs are not decisions."""
        path = _write(
            tmp_path,
            _tool_use('Bash', 'tu_3'),
            _tool_result('tu_3', 'ruff: All checks passed!\nmypy: Success: no issues found'),
        )
        result = _run(path)
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True

    def test_gate_decisions_render_under_a_distinct_role(self, tmp_path):
        """A reader can tell a gate decision from a free-form correction."""
        path = _write(
            tmp_path,
            _turn('user', OPERATOR_TEXT),
            _tool_use(_mod.OPERATOR_DECISION_TOOL, 'tu_4'),
            _tool_result('tu_4', 'Option B'),
        )
        result = _run(path)
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 1
        assert f'{_mod.OPERATOR_DECISION_ROLE}: Option B' in result['reduced_transcript']


# ---------------------------------------------------------------------------
# The two counters: volume vs signal
# ---------------------------------------------------------------------------


class TestOperatorSignalCounters:
    def test_high_volume_low_signal_is_distinguishable(self, tmp_path):
        """Many survivors, one operator turn — the counters keep them apart."""
        lines = [_turn('assistant', f'[STATUS] step {n}') for n in range(20)]
        lines.append(_turn('user', OPERATOR_TEXT))
        result = _run(_write(tmp_path, *lines))

        assert result['reduced_turn_count'] == 21
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 0

    def test_high_volume_high_signal_is_distinguishable(self, tmp_path):
        """The same survivor count, twenty of them operator-authored."""
        lines = [_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(20)]
        lines.append(_turn('assistant', '[STATUS] acknowledged'))
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
                *[_turn('assistant', f'[STATUS] {n}') for n in range(5)],
                _turn('user', OPERATOR_TEXT),
            )
        )
        high = _run(
            _write(
                tmp_path / 'high',
                *[_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(5)],
                _turn('assistant', '[STATUS] ok'),
            )
        )
        assert low['reduced_turn_count'] == high['reduced_turn_count']
        assert low['operator_turn_count'] != high['operator_turn_count']


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


class TestNoSignalVerdict:
    def test_transcript_of_harness_injections_reports_no_signal(self, tmp_path):
        """The discriminating regression, in the shape that fails pre-fix.

        Every turn here is a real harness injection, so the surviving set is
        entirely non-operator. The pre-fix verdict was ``len(kept) == 0``, and
        because these envelopes are not the two originally-enumerated classes
        they all survived — reporting a healthy transcript over pure
        instruction text.
        """
        path = _write(
            tmp_path,
            _turn('user', SYSTEM_REMINDER),
            _turn('user', TASK_NOTIFICATION),
            _turn('user', WAKE_ENVELOPE),
            _turn('user', REENTRY_NOTICE),
            _turn('user', SKILL_LOAD_TEXT),
        )
        result = _run(path)

        assert result['operator_turn_count'] == 0
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
        assert result['reduced_turn_count'] == 0

    def test_low_retention_with_zero_operator_turns_reports_no_signal(self, tmp_path):
        """Very low retention plus zero operator turns MUST report no signal.

        The single cheapest discriminating assertion. The surviving turn is a
        marker-bearing assistant turn — real volume, and no operator signal at
        all — so a verdict keyed on survivors reads clean while a verdict keyed
        on operator provenance reads empty.
        """
        lines = [_turn('user', SYSTEM_REMINDER) for _ in range(50)]
        lines.append(_turn('assistant', '[DISPATCH] launching agent'))
        result = _run(_write(tmp_path, *lines))

        assert result['raw_turn_count'] == 51
        assert result['reduced_turn_count'] == 1
        assert result['operator_turn_count'] == 0
        assert result['no_signal'] is True

    def test_genuine_operator_transcript_still_routes_normally(self, tmp_path):
        """The mirror guard: precision must not become refusal.

        A real session — operator prose, harness noise, marker-bearing
        assistant turns — still reaches Tier 1. A fix that started refusing
        real transcripts would have traded one false verdict for another.
        """
        path = _write(
            tmp_path,
            _turn('user', OPERATOR_TEXT),
            _turn('user', SYSTEM_REMINDER),
            _turn('assistant', '[DECISION] chose the positive predicate'),
            _turn('user', 'also update the aspect contract in lock-step'),
            _turn('user', SKILL_LOAD_TEXT),
        )
        result = _run(path)

        assert result['no_signal'] is False
        assert result['over_budget'] is False
        assert result['operator_turn_count'] == 2
        assert OPERATOR_TEXT in result['reduced_transcript']
        assert 'Base directory for this skill:' not in result['reduced_transcript']

    def test_operator_turn_annotated_by_the_harness_still_routes(self, tmp_path):
        """An operator turn carrying an attached reminder is still signal."""
        path = _write(tmp_path, _turn('user', f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}'))
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
