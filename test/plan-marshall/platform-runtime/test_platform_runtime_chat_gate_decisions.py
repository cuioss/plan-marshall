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

import _chat_gate_decisions as _mod
import _chat_signal_reducer as _reducer

REFUSAL = "The user doesn't want to proceed with this tool use. The tool use was rejected."


def _result_block(use_id: str, content) -> list[dict]:
    """One ``tool_result`` block, whose payload may be a string or a block list."""
    return [{'type': 'tool_result', 'tool_use_id': use_id, 'content': content}]


def _text_blocks(*texts: str) -> list[dict[str, str]]:
    return [{'type': 'text', 'text': t} for t in texts]


class TestFlattenToolResult:
    def test_bare_string_payload_returned_verbatim(self):
        assert _mod.flatten_tool_result('plain output') == 'plain output'

    def test_block_list_joined_by_newline(self):
        assert _mod.flatten_tool_result(_text_blocks('first', 'second')) == 'first\nsecond'

    def test_blocks_without_text_are_skipped(self):
        content = [{'type': 'image'}, {'type': 'text', 'text': 'kept'}, 'not-a-dict']
        assert _mod.flatten_tool_result(content) == 'kept'

    def test_non_string_text_is_skipped(self):
        assert _mod.flatten_tool_result([{'type': 'text', 'text': 42}]) == ''

    def test_unknown_shapes_yield_empty_string(self):
        assert _mod.flatten_tool_result(None) == ''
        assert _mod.flatten_tool_result(17) == ''


class TestDecisionToolUseIds:
    def test_collects_ids_of_the_decision_tool_only(self):
        content = [
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': 'tu_ask'},
            {'type': 'tool_use', 'name': 'Bash', 'id': 'tu_bash'},
        ]
        assert _mod.decision_tool_use_ids(content) == {'tu_ask'}

    def test_ignores_malformed_and_idless_blocks(self):
        content = [
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL},
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': ''},
            {'type': 'tool_use', 'name': _mod.OPERATOR_DECISION_TOOL, 'id': 7},
        ]
        assert _mod.decision_tool_use_ids(content) == set()

    def test_non_list_content_yields_no_ids(self):
        """A non-list payload has no blocks to scan.

        The witnesses are deliberately non-iterable and dict-shaped: a bare
        string is iterable, so it is filtered by the per-block dict check
        rather than by the list guard, and cannot discriminate.
        """
        assert _mod.decision_tool_use_ids(None) == set()
        assert _mod.decision_tool_use_ids({'type': 'tool_use', 'id': 'x'}) == set()

    def test_the_tool_name_must_match_exactly(self):
        """A namespaced tool merely CONTAINING the name is not the decision tool.

        A substring comparison would admit `mcp__srv__AskUserQuestion`, and any
        later result answering that id would score a gate decision — a
        synthetic input raising an operator-signal counter.
        """
        content = [{
            'type': 'tool_use',
            'name': f'mcp__srv__{_mod.OPERATOR_DECISION_TOOL}',
            'id': 'tu_x',
        }]
        assert _mod.decision_tool_use_ids(content) == set()

    def test_only_tool_use_blocks_are_scanned(self):
        """The block type narrows the scan, independently of the tool name.

        A differently-typed block bearing the same name must not contribute an
        id — a spurious id makes any later result answering it register as a
        gate decision.
        """
        content = [{
            'type': 'mcp_tool_use',
            'name': _mod.OPERATOR_DECISION_TOOL,
            'id': 'mcp_1',
        }]
        assert _mod.decision_tool_use_ids(content) == set()


class TestPublishedConstants:
    def test_the_decision_role_label_is_pinned(self):
        """The label is published in the operation contract and read by the LLM.

        Every other reference is symbolic, so mutating it — to `user` above
        all — would destroy the very distinction the constant exists to make,
        with the suite still green.
        """
        assert _mod.OPERATOR_DECISION_ROLE == 'operator-decision'
        assert _mod.OPERATOR_DECISION_ROLE != 'user'


class TestExtractGateDecisions:
    def test_answering_the_decision_tool_is_a_decision(self):
        blocks = _result_block('tu_ask', 'Option B')
        assert _mod.extract_gate_decisions(blocks, {'tu_ask'}) == ['Option B']

    def test_verbatim_refusal_is_a_decision(self):
        assert _mod.extract_gate_decisions(_result_block('tu_1', REFUSAL), set()) == [REFUSAL]

    def test_refusal_quoted_mid_payload_is_not_a_decision(self):
        """The notice must BE the payload, not appear inside it.

        The reducer runs over this project's own sessions, so a read of the
        module declaring these markers would otherwise score an operator
        decision.
        """
        quoted = f'MARKERS = (\n    "{REFUSAL}",\n)\n'
        assert _mod.extract_gate_decisions(_result_block('tu_1', quoted), set()) == []

    def test_refusal_matching_is_case_sensitive(self):
        """The notices are verbatim harness strings, matched as written.

        A case-insensitive compare admits prose that merely quotes the wording
        in another case — a synthetic input raising `gate_decision_count` and
        flipping `no_signal`. This is the gate-side twin of the provenance
        notice comparison.
        """
        quoted = "the user doesn't want to proceed with this tool use — quoted in a doc"
        assert _mod.extract_gate_decisions(_result_block('t', quoted), set()) == []

    def test_refusal_survives_a_leading_empty_block(self):
        """A multi-block payload puts a newline in front of the notice.

        `flatten_tool_result` joins blocks with a newline, so a first empty
        block shifts the marker off position zero. Without leading-whitespace
        tolerance the decision is lost — under-counting operator signal, which
        drives the verdict toward a false `no_signal: true`.
        """
        blocks = _result_block('tu_1', _text_blocks('', REFUSAL))
        assert _mod.extract_gate_decisions(blocks, set()) == [f'\n{REFUSAL}']

    def test_whitespace_only_payload_is_not_a_decision(self):
        """Emptiness is judged after stripping, not by bare falsiness.

        A multi-block payload of empty and blank blocks flattens to whitespace,
        which is not an operator decision. Counting it would let a synthetic
        input raise an operator-signal counter — what this module exists to
        prevent.
        """
        blocks = _result_block('tu_ask', _text_blocks('', ' '))
        assert _mod.extract_gate_decisions(blocks, {'tu_ask'}) == []

    def test_ordinary_tool_output_is_not_a_decision(self):
        blocks = _result_block('tu_1', 'ruff: All checks passed!')
        assert _mod.extract_gate_decisions(blocks, set()) == []

    def test_non_tool_result_blocks_are_ignored(self):
        """The block TYPE decides, not whether a payload happens to be present.

        The witness carries a `content` key so it would flatten to a refusal
        under a missing type guard; a block without one is dropped by the
        emptiness check instead and cannot tell the two apart.
        """
        content = [{'type': 'text', 'text': 'hello', 'content': REFUSAL}]
        assert _mod.extract_gate_decisions(content, set()) == []

    def test_unhashable_tool_use_id_is_not_a_decision(self):
        """A malformed id must not abort the reduction.

        Membership-testing an unhashable id raises, which would take down the
        whole transcript rather than skipping one block.
        """
        blocks = _result_block(['not', 'hashable'], 'Option A')
        assert _mod.extract_gate_decisions(blocks, {'tu_ask'}) == []

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
