#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Gated-decision recovery tests (``_chat_gate_decisions``, platform-runtime).

On a gated run the operator's decisions arrive as ``tool_result`` blocks rather
than as prose, so this module is the only thing that can see that channel. Both
of its tests are deliberately narrow — the answering tool-use id, or a verbatim
refusal notice anchored at the payload start — because a counter of operator
signal must fail toward NOT counting.

The payload arrives in two shapes: a bare string, and a list of typed blocks
joined by newlines. The list shape is what makes the anchoring and emptiness
checks load-bearing, since a leading empty block puts a newline in front of the
notice.
"""

from __future__ import annotations

from typing import Any

import _chat_gate_decisions as _mod
import _chat_signal_reducer as _reducer
import pytest

REFUSAL = "The user doesn't want to proceed with this tool use. The tool use was rejected."


def _result_block(use_id: Any, content: Any) -> list[dict]:
    """One ``tool_result`` block, whose payload may be a string or a block list.

    ``use_id`` is deliberately untyped: one row below hands it an UNHASHABLE
    value, because a malformed id must be skipped rather than raise out of the
    membership test and take the whole transcript down with it.
    """
    return [{'type': 'tool_result', 'tool_use_id': use_id, 'content': content}]


def _text_blocks(*texts: str) -> list[dict[str, str]]:
    return [{'type': 'text', 'text': t} for t in texts]


#: ``(a tool_result payload, the text it flattens to)``. A payload arrives as a
#: bare string or as a list of typed blocks, and the rows walk what the list form
#: can contain: text blocks joined by a newline, a block carrying no text at all,
#: an entry that is not a dict, and a ``text`` value that is not a string. The
#: last two rows are shapes the schema does not describe — neither is a payload,
#: and both flatten to nothing rather than raising.
_FLATTEN_CASES = [
    ('plain output', 'plain output'),
    (_text_blocks('first', 'second'), 'first\nsecond'),
    ([{'type': 'image'}, {'type': 'text', 'text': 'kept'}, 'not-a-dict'], 'kept'),
    ([{'type': 'text', 'text': 42}], ''),
    (None, ''),
    (17, ''),
]

_FLATTEN_IDS = [
    'bare-string-returned-verbatim',
    'block-list-joined-by-newline',
    'textless-and-non-dict-blocks-are-skipped',
    'non-string-text-is-skipped',
    'none-is-not-a-payload',
    'an-integer-is-not-a-payload',
]


class TestFlattenToolResult:
    @pytest.mark.parametrize(('content', 'expected'), _FLATTEN_CASES, ids=_FLATTEN_IDS)
    def test_a_payload_flattens_to_its_text(self, content, expected):
        """Every payload shape flattens to text, and an unknown one to nothing."""
        assert _mod.flatten_tool_result(content) == expected


#: ``(assistant content, the decision tool-use ids it yields)``. Only the first
#: row yields an id; every other row is a near-miss that must NOT, because a
#: spurious id makes any later result answering it register as an operator
#: decision — a synthetic input raising a counter of operator signal.
#:
#: The near-misses are: a block with no id, an empty id and a non-string id;
#: content that is not a list at all (the witnesses are deliberately
#: non-iterable and dict-shaped, since a bare string is iterable and would be
#: filtered by the per-block dict check rather than by the list guard, and so
#: could not discriminate); a NAMESPACED tool whose name merely CONTAINS the
#: decision tool's, which a substring comparison would admit; and a
#: differently-TYPED block carrying the right name, which pins that the type
#: narrows the scan independently of the name.
_DECISION_ID_CASES = [
    (
        [
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': 'tu_ask'},
            {'type': 'tool_use', 'name': 'Bash', 'id': 'tu_bash'},
        ],
        {'tu_ask'},
    ),
    (
        [
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL},
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': ''},
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': 7},
        ],
        set(),
    ),
    (None, set()),
    ({'type': 'tool_use', 'id': 'x'}, set()),
    (
        [{
            'type': 'tool_use',
            'name': f'mcp__srv__{_mod.OPERATOR_DECISION_TOOL}',
            'id': 'tu_x',
        }],
        set(),
    ),
    (
        [{'type': 'mcp_tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': 'mcp_1'}],
        set(),
    ),
]

_DECISION_ID_IDS = [
    'the-decision-tools-id-only',
    'absent-empty-and-non-string-ids',
    'content-is-not-a-list',
    'content-is-a-bare-block-not-a-list',
    'a-namespaced-tool-is-not-the-decision-tool',
    'a-differently-typed-block-is-not-scanned',
]


class TestDecisionToolUseIds:
    @pytest.mark.parametrize(('content', 'expected'), _DECISION_ID_CASES, ids=_DECISION_ID_IDS)
    def test_only_the_decision_tools_own_ids_are_collected(self, content, expected):
        """An id is collected only from a ``tool_use`` block naming the decision tool."""
        assert _mod.decision_tool_use_ids(content) == expected


class TestPublishedConstants:
    def test_the_decision_role_label_is_pinned(self):
        """The label is published in the operation contract and read by the LLM.

        Every other reference is symbolic, so mutating it — to `user` above
        all — would destroy the very distinction the constant exists to make,
        with the suite still green.
        """
        assert _mod.OPERATOR_DECISION_ROLE == 'operator-decision'
        assert _mod.OPERATOR_DECISION_ROLE != 'user'


#: ``(blocks, the known decision tool-use ids, the decisions extracted)``. Two
#: shapes count as a decision and everything else must not, because this counter
#: has to fail toward NOT counting: a synthetic input that raises it flips the
#: run's ``no_signal`` verdict on no operator signal at all.
#:
#: The two counting rows are an answer to the decision tool (matched by id) and a
#: refusal notice that IS the payload. The third row is the same notice QUOTED
#: mid-payload — the reducer runs over this project's own sessions, so a read of
#: the module declaring these markers would otherwise score a decision. The
#: fourth re-cases the notice, since a case-insensitive compare admits prose that
#: merely quotes the wording.
#:
#: The fifth row runs the other way and is the only one that must NOT
#: under-count: ``flatten_tool_result`` joins blocks with a newline, so a leading
#: empty block shifts the marker off position zero, and without leading-whitespace
#: tolerance a real refusal is lost. The rest are non-decisions: a payload that
#: flattens to whitespace (emptiness is judged after stripping, not by bare
#: falsiness); ordinary tool output; a differently-TYPED block that carries a
#: ``content`` key, so it would flatten to a refusal under a missing type guard;
#: and an unhashable id, whose membership test would raise and take down the whole
#: transcript rather than skipping one block.
_GATE_DECISION_CASES = [
    (_result_block('tu_ask', 'Option B'), {'tu_ask'}, ['Option B']),
    (_result_block('tu_1', REFUSAL), set(), [REFUSAL]),
    (_result_block('tu_1', f'MARKERS = (\n    "{REFUSAL}",\n)\n'), set(), []),
    (
        _result_block(
            't', "the user doesn't want to proceed with this tool use — quoted in a doc"
        ),
        set(),
        [],
    ),
    (_result_block('tu_1', _text_blocks('', REFUSAL)), set(), [f'\n{REFUSAL}']),
    (_result_block('tu_ask', _text_blocks('', ' ')), {'tu_ask'}, []),
    (_result_block('tu_1', 'ruff: All checks passed!'), set(), []),
    ([{'type': 'text', 'text': 'hello', 'content': REFUSAL}], set(), []),
    (_result_block(['not', 'hashable'], 'Option A'), {'tu_ask'}, []),
]

_GATE_DECISION_IDS = [
    'an-answer-to-the-decision-tool',
    'a-verbatim-refusal-notice',
    'the-notice-quoted-mid-payload',
    'the-notice-in-another-case',
    'a-refusal-behind-a-leading-empty-block',
    'a-payload-that-flattens-to-whitespace',
    'ordinary-tool-output',
    'a-non-tool-result-block-carrying-content',
    'an-unhashable-tool-use-id',
]


class TestExtractGateDecisions:
    @pytest.mark.parametrize(
        ('blocks', 'decision_ids', 'expected'), _GATE_DECISION_CASES, ids=_GATE_DECISION_IDS
    )
    def test_only_a_real_operator_decision_is_extracted(self, blocks, decision_ids, expected):
        """Two shapes count — an answer to the decision tool, and a verbatim refusal."""
        assert _mod.extract_gate_decisions(blocks, decision_ids) == expected

    def test_every_refusal_marker_is_recognised(self):
        """Each marker is named as a literal, never read back from the constant.

        Iterating `OPERATOR_REFUSAL_MARKERS` would make the test shrink with the
        tuple: deleting an entry, or mistyping one, would leave it green while a
        real refusal stopped being recognised — under-counting operator signal
        toward a false `no_signal: true`. That is this plan's own thesis applied
        to its own tests: a loop over the list under test cannot detect the list
        changing.
        """
        expected = (
            "The user doesn't want to proceed with this tool use",
            "The user doesn't want to take this action right now",
            '[Request interrupted by user',
        )
        assert _mod.OPERATOR_REFUSAL_MARKERS == expected
        for marker in expected:
            payload = f'{marker} — the rest of the notice'
            assert _mod.extract_gate_decisions(_result_block('t', payload), set()) == [payload]

    def test_the_decision_tool_name_is_the_harness_literal(self):
        """The tool name is the entire structural correlation for this channel.

        Every other reference is symbolic, so a rename or typo would silently
        disable gated-decision recovery with the suite still green. Pinned to
        the literal, and to the reducer's own copy of it, so the two cannot
        drift apart.
        """
        assert _mod.OPERATOR_DECISION_TOOL == 'AskUserQuestion'
        assert _mod.OPERATOR_DECISION_TOOL in _reducer.DECISION_MARKERS
