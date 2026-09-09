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

import _chat_provenance as _prov
import _chat_signal_reducer as _mod
import pytest
from _chat_signal_fixtures import (
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


#: ``(a turn's ``content``, the text extracted from it)``. Content arrives as a
#: bare string or as a block list, and the rows walk what a block list may hold:
#: text blocks joined by a newline, blocks of other types that contribute
#: nothing, a block missing ``type`` but carrying ``text`` (a defensive
#: shape-drift allowance), and a ``text`` value that is not a string. The last
#: three rows are shapes the schema does not describe at all — an integer, a
#: missing content, and a dict where a list belongs — and each extracts to
#: nothing rather than raising.
_EXTRACT_TEXT_CASES = [
    ('hello world', 'hello world'),
    (_text_blocks('first', 'second'), 'first\nsecond'),
    (
        [
            {'type': 'tool_use', 'name': 'Bash'},
            {'type': 'text', 'text': 'kept'},
            {'type': 'tool_result', 'content': 'ignored'},
        ],
        'kept',
    ),
    ([{'text': 'recovered'}], 'recovered'),
    ([{'type': 'text', 'text': 123}], ''),
    (42, ''),
    (None, ''),
    ({'role': 'user'}, ''),
]

_EXTRACT_TEXT_IDS = [
    'a-bare-string-is-the-text',
    'text-blocks-joined-by-newline',
    'blocks-of-other-types-contribute-nothing',
    'a-typeless-block-carrying-text-is-text',
    'a-non-string-text-value-is-ignored',
    'an-integer-is-not-content',
    'none-is-not-content',
    'a-dict-where-a-block-list-belongs',
]


class TestExtractText:
    @pytest.mark.parametrize(('content', 'expected'), _EXTRACT_TEXT_CASES, ids=_EXTRACT_TEXT_IDS)
    def test_content_extracts_to_its_text(self, content, expected):
        """Every content shape extracts to text, and an unknown one to nothing."""
        assert _mod.extract_text(content) == expected


# ---------------------------------------------------------------------------
# Unit tests: is_signal_bearing
# ---------------------------------------------------------------------------


#: The decision markers, written out as an INDEPENDENT oracle rather than read
#: back from the module under test. See
#: ``test_the_marker_tuple_is_the_pinned_literal`` for why.
_MARKER_ORACLE = ('[STATUS]', '[ERROR]', 'AskUserQuestion', '[DECISION]', '[DISPATCH]', '[SKILL]')

#: ``(role, turn text, whether the turn is kept)``. The two roles are filtered by
#: DIFFERENT rules, and the rows show both: a ``user`` turn is kept when it is
#: operator-authored and carries content, so an empty one, a whitespace-only one
#: (both tool-result placeholders) and an injected skill body are all dropped;
#: an ``assistant`` turn is kept only when it carries a decision marker. The last
#: two rows are roles the predicate does not recognise at all — a marker on a
#: non-participating role does not buy retention.
_SIGNAL_BEARING_CASES = [
    ('user', 'please rename the module', True),
    ('user', '', False),
    ('user', '   \n\t  ', False),
    ('user', SKILL_LOAD_TEXT, False),
    ('assistant', 'now [STATUS] running phase', True),
    ('assistant', 'just some prose', False),
    ('tool', '[STATUS] still dropped', False),
    ('system', 'whatever', False),
]

_SIGNAL_BEARING_IDS = [
    'operator-prose-is-kept',
    'an-empty-user-turn-is-dropped',
    'a-whitespace-only-user-turn-is-dropped',
    'an-injected-skill-body-is-dropped',
    'a-marked-assistant-turn-is-kept',
    'an-unmarked-assistant-turn-is-dropped',
    'a-marker-does-not-save-the-tool-role',
    'the-system-role-never-participates',
]


class TestIsSignalBearing:
    @pytest.mark.parametrize(('role', 'text', 'kept'), _SIGNAL_BEARING_CASES, ids=_SIGNAL_BEARING_IDS)
    def test_the_predicate_filters_by_provenance_and_content(self, role, text, kept):
        """Retention is decided by what the turn carries, never by its role alone."""
        assert _mod.is_signal_bearing(role, text) is kept

    def test_operator_quoting_the_marker_line_is_kept(self):
        """The predicate is structural — the marker line alone is not enough.

        An operator who merely mentions the base-directory line, with no
        markdown heading following it, is real signal and must survive.
        """
        text = 'why does the log say Base directory for this skill: /tmp/x ?'
        assert _prov.is_synthetic_skill_load(text) is False
        assert _mod.is_signal_bearing('user', text) is True

    def test_the_marker_tuple_is_the_pinned_literal(self):
        """The markers are named as literals, never read back from the constant.

        A sweep that iterated ``DECISION_MARKERS`` would shrink with the tuple:
        deleting an entry leaves it green while marker-bearing context stops
        reaching the Tier-1 prompt. This equality is the oracle for the
        per-marker sweep below, whose rows are the same literals.
        """
        assert _mod.DECISION_MARKERS == _MARKER_ORACLE

    @pytest.mark.parametrize('marker', _MARKER_ORACLE, ids=_MARKER_ORACLE)
    def test_each_marker_triggers_retention(self, marker: str):
        """Each marker keeps an assistant turn that would otherwise be dropped."""
        assert _mod.is_signal_bearing('assistant', f'prefix {marker} suffix') is True


# ---------------------------------------------------------------------------
# Unit tests: parse_turn
# ---------------------------------------------------------------------------


#: ``(a transcript line, the ``(role, text)`` it parses to, or ``None``)``. Only
#: the first two and the last row are turns. The refusals walk the ladder the
#: parser descends: nothing to decode (blank, whitespace-only), bytes that are
#: not JSON at all, JSON that is not an object, an object with no ``message``, a
#: ``message`` that is not an object, and finally a message whose ``role`` is
#: missing or empty. Each rung is its own row because each is a different place
#: the walk can stop, and a parser that skipped one would still satisfy the rest.
#: The last row is a real turn carrying only non-text blocks — it parses, with an
#: empty text, which is the layering the test below states.
_PARSE_TURN_CASES = [
    (_turn('user', 'hello'), ('user', 'hello')),
    (_turn('assistant', _text_blocks('[STATUS] up')), ('assistant', '[STATUS] up')),
    ('', None),
    ('   \t  ', None),
    ('this is not json', None),
    ('{ broken json', None),
    (json.dumps([1, 2, 3]), None),
    (json.dumps('a bare string'), None),
    (json.dumps({'type': 'summary'}), None),
    (json.dumps({'message': 'not-a-dict'}), None),
    (json.dumps({'message': {'content': 'x'}}), None),
    (json.dumps({'message': {'role': '', 'content': 'x'}}), None),
    (_turn('user', [{'type': 'tool_result', 'content': 'r'}]), ('user', '')),
]

_PARSE_TURN_IDS = [
    'a-user-turn-with-string-content',
    'an-assistant-turn-with-text-blocks',
    'a-blank-line',
    'a-whitespace-only-line',
    'not-json-at-all',
    'truncated-json',
    'json-list-instead-of-object',
    'json-string-instead-of-object',
    'an-event-carrying-no-message',
    'a-message-that-is-not-an-object',
    'a-message-with-no-role',
    'a-message-with-an-empty-role',
    'a-turn-carrying-only-non-text-blocks',
]


class TestParseTurn:
    @pytest.mark.parametrize(('line', 'expected'), _PARSE_TURN_CASES, ids=_PARSE_TURN_IDS)
    def test_a_line_parses_to_a_turn_or_to_nothing(self, line: str, expected) -> None:
        """A line yields ``(role, text)`` only when it really is a turn."""
        assert _mod.parse_turn(line) == expected

    def test_an_empty_text_is_reported_by_parsing_and_dropped_by_reduction(self):
        """The two concerns stay separable across the layer boundary.

        Parsing reports what the turn CARRIED — the last row of the table above
        surfaces an empty text rather than refusing the turn — and the DROP
        happens one layer later, in ``is_signal_bearing``.
        """
        assert _mod.parse_turn(_turn('user', [{'type': 'tool_result', 'content': 'r'}])) == (
            'user',
            '',
        )
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
