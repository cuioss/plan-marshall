# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reduction record, counters and byte-measurement contract (``_chat_signal_reducer``).

Governs the runtime-owned reduction record behind ``chat extract-signal``: the
seven-field normalized payload, the operator-signal counters, the byte
measurement, decode robustness, and the role guards. ``no_signal`` is keyed on
OPERATOR-AUTHORED counts, never on how many turns survived: a survivor count
rises with every class of injected instruction text the filter fails to
recognise, so a volume-derived verdict reports more health as the signal it
measures degrades.

The ``over_budget`` flag and the historic field-name mapping are CONSUMER-owned
and are not produced here — the runtime reports ``reduced_bytes`` and the two
``*_count`` families; a consumer derives budget and renames fields. Skipped
routing for a missing file is the operation level's ``transcript_not_found``
no-op, covered in the operation tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _chat_gate_decisions as _gate  # noqa: I001
import _chat_signal_reducer as _mod  # noqa: I001

from _chat_signal_fixtures import (  # noqa: I001, E402
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


def _write(tmp_path: Path, *lines: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / 'session.jsonl'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _reduce(path: Path) -> dict:
    """Reduce a transcript file to the runtime record."""
    return _mod.reduce_chat_signal(path)


class TestGateDecisionRecovery:
    def test_ask_user_question_result_is_a_gate_decision(self, tmp_path):
        """On a gated run the operator answers through a tool result.

        A reducer that reads only free-form `user` turns measures only the
        channel the operator did not use, so a well-instrumented run with many
        gate decisions and no corrections reads as silent.
        """
        path = _write(
            tmp_path,
            chat_tool_use(_gate.OPERATOR_DECISION_TOOL, 'tu_1'),
            chat_tool_result('tu_1', 'Approach: rewrite the filter'),
        )
        result = _reduce(path)
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
        result = _reduce(path)
        assert result['gate_decision_count'] == 1
        assert result['no_signal'] is False

    def test_ordinary_tool_output_is_not_a_gate_decision(self, tmp_path):
        """The counter fails toward NOT counting — build logs are not decisions."""
        path = _write(
            tmp_path,
            chat_tool_use('Bash', 'tu_3'),
            chat_tool_result('tu_3', 'ruff: All checks passed!\nmypy: Success: no issues found'),
        )
        result = _reduce(path)
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
            "    \"The user doesn't want to proceed with this tool use\",\n"
            ')\n'
        )
        path = _write(tmp_path, chat_tool_use('Read', 'tu_5'), chat_tool_result('tu_5', quoted))
        result = _reduce(path)
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True

    def test_gate_decisions_render_under_a_distinct_role(self, tmp_path):
        """A reader can tell a gate decision from a free-form correction."""
        path = _write(
            tmp_path,
            chat_turn('user', OPERATOR_TEXT),
            chat_tool_use(_gate.OPERATOR_DECISION_TOOL, 'tu_4'),
            chat_tool_result('tu_4', 'Option B'),
        )
        result = _reduce(path)
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 1
        assert f'{_gate.OPERATOR_DECISION_ROLE}: Option B' in result['reduced_transcript']


class TestOperatorSignalCounters:
    def test_high_volume_low_signal_is_distinguishable(self, tmp_path):
        """Many survivors, one operator turn — the counters keep them apart."""
        lines = [chat_turn('assistant', f'[STATUS] step {n}') for n in range(20)]
        lines.append(chat_turn('user', OPERATOR_TEXT))
        result = _reduce(_write(tmp_path, *lines))

        assert result['kept_raw_count'] == 21
        assert result['operator_turn_count'] == 1
        assert result['gate_decision_count'] == 0

    def test_high_volume_high_signal_is_distinguishable(self, tmp_path):
        """The same survivor count, twenty of them operator-authored."""
        lines = [chat_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(20)]
        lines.append(chat_turn('assistant', '[STATUS] acknowledged'))
        result = _reduce(_write(tmp_path, *lines))

        assert result['kept_raw_count'] == 21
        assert result['operator_turn_count'] == 20

    def test_survivor_count_alone_cannot_separate_the_two(self, tmp_path):
        """The defect in one assertion: equal volume, opposite signal.

        Both transcripts reduce to the same number of turns, so the pre-fix
        volume-derived verdict rated them identically.
        """
        low = _reduce(
            _write(
                tmp_path / 'low',
                *[chat_turn('assistant', f'[STATUS] {n}') for n in range(5)],
                chat_turn('user', OPERATOR_TEXT),
            )
        )
        high = _reduce(
            _write(
                tmp_path / 'high',
                *[chat_turn('user', f'{OPERATOR_TEXT} ({n})') for n in range(5)],
                chat_turn('assistant', '[STATUS] ok'),
            )
        )
        assert low['kept_raw_count'] == high['kept_raw_count']
        assert low['operator_turn_count'] != high['operator_turn_count']

    def test_gate_decisions_are_not_folded_into_the_kept_turn_count(self, tmp_path):
        """`kept_raw_count` counts RAW turns kept, never synthesised entries.

        The arithmetic identity alone cannot pin this: `dropped_turn_count` is
        derived as `raw - kept`, so the sum holds for any value of `kept`.
        The count itself has to be asserted — one operator turn survives here,
        and the gate decision must not inflate it.
        """
        path = _write(
            tmp_path,
            chat_tool_use(_gate.OPERATOR_DECISION_TOOL, 'tu_6'),
            chat_tool_result('tu_6', 'Option A'),
            chat_turn('user', OPERATOR_TEXT),
        )
        result = _reduce(path)
        assert result['gate_decision_count'] == 1
        assert result['raw_turn_count'] == 3
        assert result['kept_raw_count'] == 1

    def test_decision_ids_survive_an_intervening_turn(self, tmp_path):
        """The id set accumulates across turns; it is not replaced per turn.

        A prompt and its answer are rarely adjacent — anything the assistant
        says in between would reset a replaced set, losing the decision and
        under-counting operator signal.
        """
        path = _write(
            tmp_path,
            chat_tool_use(_gate.OPERATOR_DECISION_TOOL, 'tu_7'),
            chat_turn('assistant', 'some prose between the prompt and the answer'),
            chat_tool_result('tu_7', 'Option C'),
        )
        result = _reduce(path)
        assert result['gate_decision_count'] == 1
        assert result['no_signal'] is False


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
        result = _reduce(path)

        assert result['raw_turn_count'] == 5
        assert result['operator_turn_count'] == 0
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
        assert result['kept_raw_count'] == 0

    def test_low_retention_with_zero_operator_turns_reports_no_signal(self, tmp_path):
        """Very low retention plus zero operator turns MUST report no signal.

        The single cheapest discriminating assertion. The surviving turn is a
        marker-bearing assistant turn — real volume, no operator signal at all
        — so a verdict keyed on survivors reads clean while a verdict keyed on
        operator provenance reads empty.
        """
        lines = [chat_turn('user', SYSTEM_REMINDER) for _ in range(50)]
        lines.append(chat_turn('assistant', '[DISPATCH] launching agent'))
        result = _reduce(_write(tmp_path, *lines))

        assert result['raw_turn_count'] == 51
        assert result['kept_raw_count'] == 1
        assert result['operator_turn_count'] == 0
        assert result['no_signal'] is True

    def test_genuine_operator_transcript_reports_signal(self, tmp_path):
        """The mirror guard: precision must not become refusal.

        A real session — operator prose, a slash command, harness noise,
        marker-bearing assistant turns — still carries signal. A fix that
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
        result = _reduce(path)

        assert result['no_signal'] is False
        assert result['operator_turn_count'] == 3
        assert OPERATOR_TEXT in result['reduced_transcript']
        assert 'Base directory for this skill:' not in result['reduced_transcript']

    def test_operator_turn_annotated_by_the_harness_still_reports_signal(self, tmp_path):
        """An operator turn carrying an attached reminder is still signal."""
        path = _write(tmp_path, chat_turn('user', f'{OPERATOR_TEXT}\n{SYSTEM_REMINDER}'))
        result = _reduce(path)
        assert result['operator_turn_count'] == 1
        assert result['no_signal'] is False

    def test_argumentless_commands_alone_report_no_signal(self, tmp_path):
        """A session of bare commands carries no analysable operator content.

        The operator acted, but `/clear` and `/compact` say nothing this aspect
        can analyse — it looks for pivots, clarifications and corrections. The
        narrowing is deliberate and it fails toward refusal, so it is pinned
        here at the verdict level rather than left to the predicate alone.
        """
        path = _write(
            tmp_path,
            chat_turn('user', '<command-name>/clear</command-name>'),
            chat_turn('user', '<command-name>/compact</command-name>\n<command-args></command-args>'),
        )
        result = _reduce(path)
        assert result['raw_turn_count'] == 2
        assert result['operator_turn_count'] == 0
        assert result['no_signal'] is True

    def test_a_command_with_arguments_reports_signal(self, tmp_path):
        """The counterpart: arguments are operator content, so the turn counts."""
        path = _write(tmp_path, chat_turn('user', SLASH_COMMAND))
        result = _reduce(path)
        assert result['operator_turn_count'] == 1
        assert result['no_signal'] is False


class TestByteMeasurement:
    def test_reduced_bytes_counts_utf8_bytes_not_characters(self, tmp_path):
        """The budget is a BYTE budget, and non-ASCII text costs more than one.

        Measuring characters under-reports the size of any transcript that is
        not plain ASCII, so a reduction several times over the read budget
        would be fed to the Tier-1 prompt as if it fit.
        """
        text = '請修正這個過濾器' * 400
        result = _reduce(_write(tmp_path, chat_turn('user', text)))

        assert result['reduced_bytes'] == len(result['reduced_transcript'].encode('utf-8'))
        assert result['reduced_bytes'] > len(result['reduced_transcript'])


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

        result = _reduce(path)
        assert result['operator_turn_count'] == 1

    def test_missing_file_raises_file_not_found(self, tmp_path):
        """Only a MISSING file raises `FileNotFoundError`.

        This is the runtime's ``transcript_not_found`` signal to the operation,
        which maps it to the no-op. A permission error must NOT be collapsed
        into an absent transcript — widening the raise would silently turn an
        unreadable transcript into `no_signal: true` instead of surfacing it.
        """
        import pytest

        with pytest.raises(FileNotFoundError):
            _reduce(tmp_path / 'absent.jsonl')

    def test_a_permission_error_raises_oserror_not_a_transcript_not_found(self, monkeypatch):
        """A read failure is distinct from an absent file.

        ``FileNotFoundError`` is an ``OSError``, so mapping every ``OSError`` to
        ``transcript_not_found`` would report an unreadable transcript as an
        absent one. The reducer lets ``OSError`` escape so the operation can
        surface it as an error rather than a no-op.
        """
        import pytest

        def _raise(_path):
            raise PermissionError('locked')

        monkeypatch.setattr(_mod, 'read_transcript_lines', _raise)
        with pytest.raises(PermissionError):
            _reduce(Path('/nonexistent/x.jsonl'))


class TestDecoding:
    def test_raw_non_ascii_bytes_decode_as_utf8(self, tmp_path):
        """Real transcripts store non-ASCII raw, not `\\uXXXX`-escaped.

        Claude Code writes its JSONL with `ensure_ascii=False`, so the bytes on
        disk are UTF-8. Decoding them as latin-1 yields mojibake and inflates
        `reduced_bytes`, which can refuse a transcript that fits.
        """
        path = tmp_path / 'session.jsonl'
        line = json.dumps(
            {'type': 'turn', 'message': {'role': 'user', 'content': '請修正這個過濾器'}},
            ensure_ascii=False,
        )
        path.write_bytes(line.encode('utf-8') + b'\n')

        result = _reduce(path)
        assert result['reduced_transcript'] == 'user: 請修正這個過濾器'
        assert result['operator_turn_count'] == 1

    def test_an_undecodable_byte_becomes_the_replacement_character(self, tmp_path):
        """The docstring names the replacement character, so it is pinned.

        `errors='ignore'` would also keep the run alive while silently deleting
        the byte, which is a different contract from the one documented.
        """
        path = tmp_path / 'session.jsonl'
        payload = chat_turn('user', 'revert PLACEHOLDER that change').encode('utf-8')
        path.write_bytes(payload.replace(b'PLACEHOLDER', b'\xe9') + b'\n')

        result = _reduce(path)
        assert '\ufffd' in result['reduced_transcript']


class TestContentRobustness:
    def test_a_non_dict_content_block_is_skipped(self):
        """A stray non-dict block must not abort the extraction."""
        content = [{'type': 'text', 'text': 'please revert that change'}, 'a stray string block']
        assert _mod.extract_text(content) == 'please revert that change'

    def test_a_non_string_role_is_not_a_turn(self):
        """The role must be a string, not merely truthy.

        A numeric role would otherwise be counted in `raw_turn_count` and in
        the dropped denominator, skewing both.
        """
        line = json.dumps({'type': 'turn', 'message': {'role': 1, 'content': 'hi'}})
        assert _mod.parse_message(line) is None

    def test_a_typed_block_carrying_text_is_not_treated_as_text(self):
        """Only an explicit `text` block, or a typeless one, contributes.

        The typeless allowance is defensive against shape drift; widening it to
        any block with a `text` field lets a `tool_use` payload become operator
        prose — a synthetic input raising `operator_turn_count`.
        """
        content = [{'type': 'tool_use', 'name': 'Bash', 'text': 'please revert that change'}]
        assert _mod.extract_text(content) == ''

    def test_a_json_value_error_is_not_a_turn(self):
        """`json.loads` raises plain `ValueError`, not only `JSONDecodeError`.

        An integer literal past CPython's digit-conversion limit raises the
        base class. Catching only the subclass lets it escape and aborts the
        whole pre-pass, losing every operator turn in the transcript.
        """
        assert _mod.parse_message('1' * 5000) is None

    def test_a_form_feed_prefixed_line_still_parses(self):
        """Lines are stripped of Python whitespace before decoding.

        A form feed is Python whitespace but not JSON whitespace, so without
        the strip the turn is dropped — under-counting.
        """
        assert _mod.parse_message('\x0c' + chat_turn('user', 'revert that')) is not None


class TestRoleGuards:
    def test_a_tool_result_on_an_assistant_turn_is_not_a_gate_decision(self, tmp_path):
        """Only a `user` turn carries the operator's side of the channel."""
        path = _write(
            tmp_path,
            chat_turn('assistant', [
                {'type': 'tool_use', 'name': _gate.OPERATOR_DECISION_TOOL, 'id': 'tu_1'},
            ]),
            chat_turn('assistant', [
                {'type': 'tool_result', 'tool_use_id': 'tu_1', 'content': 'Option A'},
            ]),
        )
        result = _reduce(path)
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
        result = _reduce(_write(tmp_path, line))
        assert result['gate_decision_count'] == 0
        assert result['no_signal'] is True
