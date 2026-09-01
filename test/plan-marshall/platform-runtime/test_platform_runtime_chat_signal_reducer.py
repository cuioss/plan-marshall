# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parsing, reduction and output-contract tests for ``_chat_signal_reducer``.

These exercise the runtime-owned reduction engine behind the ``chat
extract-signal`` operation: text extraction, the signal-bearing predicate, turn
parsing and the transcript walk. The operation's success payload and routing
flags are covered in the operation-level tests; this module pins the pure
reduction mechanics.
"""


from __future__ import annotations

import json

import _chat_provenance as _prov  # noqa: I001
import _chat_signal_reducer as _mod  # noqa: I001
from _chat_signal_fixtures import (  # noqa: I001, E402
    SKILL_LOAD_TEXT,
)
from _chat_signal_fixtures import (
    chat_text_blocks as _text_blocks,
)
from _chat_signal_fixtures import (
    chat_turn as _turn,
)

# ---------------------------------------------------------------------------
# Unit tests: extract_text
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_plain_string_content_returned_verbatim(self):
        assert _mod.extract_text('hello world') == 'hello world'

    def test_text_blocks_joined_by_newline(self):
        content = _text_blocks('first', 'second')
        assert _mod.extract_text(content) == 'first\nsecond'

    def test_non_text_blocks_skipped(self):
        content = [
            {'type': 'tool_use', 'name': 'Bash'},
            {'type': 'text', 'text': 'kept'},
            {'type': 'tool_result', 'content': 'ignored'},
        ]
        assert _mod.extract_text(content) == 'kept'

    def test_typeless_block_with_text_treated_as_text(self):
        # Defensive shape drift: a block missing ``type`` but carrying ``text``.
        content = [{'text': 'recovered'}]
        assert _mod.extract_text(content) == 'recovered'

    def test_unknown_shape_yields_empty_string(self):
        assert _mod.extract_text(42) == ''
        assert _mod.extract_text(None) == ''
        assert _mod.extract_text({'role': 'user'}) == ''

    def test_block_with_non_string_text_ignored(self):
        content = [{'type': 'text', 'text': 123}]
        assert _mod.extract_text(content) == ''


# ---------------------------------------------------------------------------
# Unit tests: is_signal_bearing
# ---------------------------------------------------------------------------


class TestIsSignalBearing:
    def test_operator_authored_user_turn_kept(self):
        """A genuine operator utterance is kept — the predicate filters by
        provenance and content, not by role alone."""
        assert _mod.is_signal_bearing('user', 'please rename the module') is True

    def test_user_turn_dropped_when_empty_or_whitespace(self):
        """Empty and whitespace-only user turns are tool-result placeholders
        carrying no operator signal, and are dropped."""
        assert _mod.is_signal_bearing('user', '') is False
        assert _mod.is_signal_bearing('user', '   \n\t  ') is False

    def test_synthetic_skill_load_user_turn_dropped(self):
        assert _mod.is_signal_bearing('user', SKILL_LOAD_TEXT) is False

    def test_operator_quoting_the_marker_line_is_kept(self):
        """The predicate is structural — the marker line alone is not enough.

        An operator who merely mentions the base-directory line, with no
        markdown heading following it, is real signal and must survive.
        """
        text = 'why does the log say Base directory for this skill: /tmp/x ?'
        assert _prov.is_synthetic_skill_load(text) is False
        assert _mod.is_signal_bearing('user', text) is True

    def test_assistant_turn_kept_with_decision_marker(self):
        assert _mod.is_signal_bearing('assistant', 'now [STATUS] running phase') is True

    def test_assistant_turn_dropped_without_marker(self):
        assert _mod.is_signal_bearing('assistant', 'just some prose') is False

    def test_each_marker_triggers_retention(self):
        """Markers are named as literals, never read back from the constant.

        Iterating ``DECISION_MARKERS`` makes the test shrink with the tuple:
        deleting an entry leaves it green while marker-bearing context stops
        reaching the Tier-1 prompt.
        """
        expected = ('[STATUS]', '[ERROR]', 'AskUserQuestion', '[DECISION]', '[DISPATCH]', '[SKILL]')
        assert _mod.DECISION_MARKERS == expected
        for marker in expected:
            assert _mod.is_signal_bearing('assistant', f'prefix {marker} suffix') is True

    def test_other_roles_dropped(self):
        assert _mod.is_signal_bearing('tool', '[STATUS] still dropped') is False
        assert _mod.is_signal_bearing('system', 'whatever') is False


# ---------------------------------------------------------------------------
# Unit tests: parse_turn
# ---------------------------------------------------------------------------


class TestParseTurn:
    def test_parses_valid_user_turn(self):
        line = _turn('user', 'hello')
        assert _mod.parse_turn(line) == ('user', 'hello')

    def test_parses_assistant_text_blocks(self):
        line = _turn('assistant', _text_blocks('[STATUS] up'))
        assert _mod.parse_turn(line) == ('assistant', '[STATUS] up')

    def test_blank_line_returns_none(self):
        assert _mod.parse_turn('') is None
        assert _mod.parse_turn('   \t  ') is None

    def test_non_json_line_returns_none(self):
        assert _mod.parse_turn('this is not json') is None
        assert _mod.parse_turn('{ broken json') is None

    def test_non_object_payload_returns_none(self):
        assert _mod.parse_turn(json.dumps([1, 2, 3])) is None
        assert _mod.parse_turn(json.dumps('a bare string')) is None

    def test_event_without_message_returns_none(self):
        assert _mod.parse_turn(json.dumps({'type': 'summary'})) is None

    def test_message_not_object_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': 'not-a-dict'})) is None

    def test_missing_role_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': {'content': 'x'}})) is None

    def test_empty_role_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': {'role': '', 'content': 'x'}})) is None

    def test_turn_with_only_non_text_blocks_yields_empty_text(self):
        """``parse_turn`` still surfaces the empty text — the DROP happens one
        layer later, in ``is_signal_bearing``, so the two concerns stay
        separable (parsing reports what the turn carried; reduction decides
        whether it is signal)."""
        line = _turn('user', [{'type': 'tool_result', 'content': 'r'}])
        assert _mod.parse_turn(line) == ('user', '')
        assert _mod.is_signal_bearing('user', '') is False


# ---------------------------------------------------------------------------
# Unit tests: reduce_transcript
# ---------------------------------------------------------------------------


class TestReduceTranscript:
    def test_keeps_operator_and_marked_assistant_drops_rest(self):
        lines = [
            _turn('user', 'do the thing'),
            _turn('assistant', 'thinking out loud with no marker'),
            _turn('assistant', _text_blocks('[DISPATCH] launching agent')),
            _turn('tool', 'tool output that must be dropped'),
        ]
        reduction = _mod.reduce_transcript(lines)
        kept, raw = reduction.turns, reduction.raw_turn_count
        assert kept == [
            {'role': 'user', 'text': 'do the thing'},
            {'role': 'assistant', 'text': '[DISPATCH] launching agent'},
        ]
        assert raw == 4

    def test_drops_empty_and_synthetic_user_turns(self):
        """The reduction keeps only the operator turn out of four user turns."""
        lines = [
            _turn('user', 'rename the module please'),
            _turn('user', SKILL_LOAD_TEXT),
            _turn('user', ''),
            _turn('user', '   \n  '),
        ]
        reduction = _mod.reduce_transcript(lines)
        kept, raw = reduction.turns, reduction.raw_turn_count
        assert kept == [{'role': 'user', 'text': 'rename the module please'}]
        assert raw == 4

    def test_preserves_document_order(self):
        lines = [
            _turn('assistant', '[STATUS] a'),
            _turn('user', 'b'),
            _turn('assistant', '[ERROR] c'),
        ]
        kept = _mod.reduce_transcript(lines).turns
        assert [t['text'] for t in kept] == ['[STATUS] a', 'b', '[ERROR] c']

    def test_malformed_lines_dropped_silently(self):
        lines = [
            'not json at all',
            '{ truncated',
            _turn('user', 'survives'),
            json.dumps({'type': 'summary'}),
        ]
        reduction = _mod.reduce_transcript(lines)
        kept, raw = reduction.turns, reduction.raw_turn_count
        assert kept == [{'role': 'user', 'text': 'survives'}]
        # Malformed and non-turn lines never parse, so they are not raw turns.
        assert raw == 1

    def test_empty_history_keeps_nothing(self):
        reduction = _mod.reduce_transcript([])
        assert reduction.turns == []
        assert reduction.raw_turn_count == 0

    def test_all_unmarked_assistant_keeps_nothing(self):
        lines = [
            _turn('assistant', 'prose one'),
            _turn('assistant', 'prose two'),
            _turn('tool', 'output'),
        ]
        reduction = _mod.reduce_transcript(lines)
        kept, raw = reduction.turns, reduction.raw_turn_count
        assert kept == []
        assert raw == 3
