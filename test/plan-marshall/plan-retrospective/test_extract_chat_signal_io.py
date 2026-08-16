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

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns, run_script  # noqa: E402

_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)
_gate = load_script_module('plan-marshall', 'plan-retrospective', '_chat_gate_decisions.py')

BUNDLE, SKILL, SCRIPT = 'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py'
SCRIPT_PATH = MARKETPLACE_ROOT / BUNDLE / 'skills' / SKILL / 'scripts' / SCRIPT


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


class TestDecoding:
    def test_raw_non_ascii_bytes_decode_as_utf8(self):
        """Real transcripts store non-ASCII raw, not `\\uXXXX`-escaped.

        Claude Code writes its JSONL with `ensure_ascii=False`, so the bytes on
        disk are UTF-8. Decoding them as latin-1 yields mojibake and inflates
        `reduced_bytes`, which can refuse a transcript that fits. Every other
        fixture here goes through `json.dumps` with the default
        `ensure_ascii=True`, so nothing else in the suite decodes a raw
        non-ASCII byte.
        """
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'session.jsonl'
            line = json.dumps(
                {'type': 'turn', 'message': {'role': 'user', 'content': '請修正這個過濾器'}},
                ensure_ascii=False,
            )
            path.write_bytes(line.encode('utf-8') + b'\n')

            result = _run(path)
            assert result['reduced_transcript'] == 'user: 請修正這個過濾器'
            assert result['operator_turn_count'] == 1

    def test_an_undecodable_byte_becomes_the_replacement_character(self):
        """The docstring names the replacement character, so it is pinned.

        `errors='ignore'` would also keep the run alive while silently deleting
        the byte, which is a different contract from the one documented.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'session.jsonl'
            payload = chat_turn('user', 'revert PLACEHOLDER that change').encode('utf-8')
            path.write_bytes(payload.replace(b'PLACEHOLDER', b'\xe9') + b'\n')

            result = _run(path)
            assert result['status'] == 'success'
            assert '\ufffd' in result['reduced_transcript']

    def test_a_permission_error_is_not_reported_as_an_absent_transcript(self, monkeypatch):
        """Only a MISSING file maps to `transcript_unavailable`.

        `FileNotFoundError` is an `OSError`, so widening the except clause
        would swallow every read failure and report an unreadable transcript as
        an absent one — silently turning it into `no_signal: true` instead of
        surfacing it.
        """
        import pytest

        def _raise(_path):
            raise PermissionError('locked')

        monkeypatch.setattr(_mod, 'read_transcript_lines', _raise)
        args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--transcript-path', '/nonexistent/x.jsonl')
        with pytest.raises(PermissionError):
            _mod.cmd_run(args)


class TestContentBlockRobustness:
    def test_a_non_dict_content_block_is_skipped(self):
        """A stray non-dict block must not abort the extraction.

        The sibling guard in the gate-decision scanner is pinned; this one
        governs the text path, and without it a malformed block raises and the
        whole aspect is lost.
        """
        content = [{'type': 'text', 'text': 'please revert that change'}, 'a stray string block']
        assert _mod.extract_text(content) == 'please revert that change'

    def test_a_non_string_role_is_not_a_turn(self):
        """The role must be a string, not merely truthy.

        A numeric role would otherwise be counted in `raw_turn_count` and in
        the dropped denominator, skewing both.
        """
        import json

        line = json.dumps({'type': 'turn', 'message': {'role': 1, 'content': 'hi'}})
        assert _mod.parse_message(line) is None


class TestPayloadAndCliContract:
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

    def test_the_success_payload_carries_the_full_transcript_path(self, tmp_path):
        """The path is reported as given, not as a basename.

        The skipped branch's copy of this field is asserted elsewhere; this is
        its pair on the success branch.
        """
        path = _write(tmp_path, chat_turn('user', 'please revert that change'))
        result = _run(path)
        assert result['transcript_path'] == str(path)

    def test_the_skipped_payload_carries_the_full_transcript_path(self, tmp_path):
        """Its pair on the unavailable branch — both halves asserted."""
        missing = tmp_path / 'absent.jsonl'
        result = _run(missing)
        assert result['reason'] == 'transcript_unavailable'
        assert result['transcript_path'] == str(missing)

    def test_flag_abbreviations_are_rejected(self, tmp_path):
        """`allow_abbrev=False` is a script-architecture requirement.

        Accepting `--transcript-pa` widens the CLI surface to prefixes the
        contract does not publish. Driven through the real CLI: `parse_ns`
        intercepts at `main()`'s parse call and never exercises abbreviation,
        so it cannot discriminate this.
        """
        path = _write(tmp_path, chat_turn('user', 'please revert that change'))

        full = run_script(SCRIPT_PATH, 'run', '--transcript-path', str(path))
        assert full.success, full.stderr

        abbreviated = run_script(SCRIPT_PATH, 'run', '--transcript-pa', str(path))
        assert not abbreviated.success
        assert run_script(SCRIPT_PATH, '--hel').returncode != 0

    def test_a_form_feed_prefixed_line_still_parses(self):
        """Lines are stripped of Python whitespace before decoding.

        A form feed is Python whitespace but not JSON whitespace, so without
        the strip the turn is dropped — under-counting.
        """
        assert _mod.parse_message('\x0c' + chat_turn('user', 'revert that')) is not None

    def test_a_non_integer_read_budget_is_rejected(self):
        """The budget is a byte count, so the parser must refuse a float."""
        import pytest

        with pytest.raises(SystemExit):
            parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--transcript-path', '/x.jsonl',
                     '--read-budget-bytes', '1.5')

    def test_the_subcommand_is_required(self):
        """Invoking with no subcommand is a usage error, not a crash."""
        import pytest

        with pytest.raises(SystemExit):
            parse_ns(BUNDLE, SKILL, SCRIPT)


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
