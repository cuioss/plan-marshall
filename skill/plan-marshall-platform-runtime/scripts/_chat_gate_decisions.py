#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Recovery of operator gate decisions from the tool-result channel.

On a gated run the operator's decisions arrive as ``tool_result`` blocks, not
as ``user`` prose, so a reducer that reads only free-form turns measures only
the channel the operator did not use. This module recognises those results for
the ``chat extract-signal`` runtime operation; the contract it implements is
specified in the ``chat extract-signal`` operation contract
(``standards/contract.md``) § "The gated-decision channel".

Both tests are deliberately narrow — the answering tool-use id, or a verbatim
refusal notice anchored at the start of the payload — because a counter of
operator signal must fail toward NOT counting.
"""

from __future__ import annotations

from typing import Any

# The tool through which the harness asks the operator to decide. A
# ``tool_result`` answering one of its calls carries an operator decision.
OPERATOR_DECISION_TOOL = 'AskUserQuestion'

# Verbatim harness notices reporting that the OPERATOR refused or interrupted a
# tool call. These are gate decisions: the operator acted, through the
# permission channel rather than through prose.
#
# ⚠ Matched only as a PREFIX of the whole result payload, never as a substring.
# A refusal notice IS the entire payload; matching anywhere would count any
# tool result that merely quotes the phrase — a `Read` of this very file — as
# an operator decision, which is the synthetic-input-raises-the-counter defect
# this module exists to remove.
OPERATOR_REFUSAL_MARKERS: tuple[str, ...] = (
    "The user doesn't want to proceed with this tool use",
    "The user doesn't want to take this action right now",
    '[Request interrupted by user',
)

# Role label under which recovered gate decisions are rendered. Distinct from
# ``user`` so a reader can tell a free-form correction from a gate decision.
OPERATOR_DECISION_ROLE = 'operator-decision'


def _iter_blocks(content: Any) -> list[dict[str, Any]]:
    """Return ``content``'s dict blocks, or an empty list for any other shape."""
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def decision_tool_use_ids(content: Any) -> set[str]:
    """Return the ids of :data:`OPERATOR_DECISION_TOOL` calls in ``content``.

    Correlating on the tool-use id is structural: it identifies the operator's
    answer without matching on any phrasing the tool happens to emit.
    """
    ids: set[str] = set()
    for block in _iter_blocks(content):
        if block.get('type') != 'tool_use':
            continue
        if block.get('name') != OPERATOR_DECISION_TOOL:
            continue
        use_id = block.get('id')
        if isinstance(use_id, str) and use_id:
            ids.add(use_id)
    return ids


def flatten_tool_result(content: Any) -> str:
    """Return a ``tool_result`` block's payload as plain text.

    A result payload is a bare string or a list of typed blocks; anything else
    yields the empty string.
    """
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in _iter_blocks(content):
        text = block.get('text')
        if isinstance(text, str):
            parts.append(text)
    return '\n'.join(parts)


def extract_gate_decisions(content: Any, decision_ids: set[str]) -> list[str]:
    """Return the operator gate decisions carried by a ``user`` turn's blocks.

    A ``tool_result`` is an operator decision when it answers an
    :data:`OPERATOR_DECISION_TOOL` call (matched by tool-use id) or when it
    carries one of the verbatim :data:`OPERATOR_REFUSAL_MARKERS`. Both tests
    are narrow on purpose: a counter of operator signal must fail toward NOT
    counting, so ordinary tool output is never mistaken for a decision.
    """
    decisions: list[str] = []
    for block in _iter_blocks(content):
        if block.get('type') != 'tool_result':
            continue
        text = flatten_tool_result(block.get('content'))
        if not text.strip():
            continue
        use_id = block.get('tool_use_id')
        answered_prompt = isinstance(use_id, str) and use_id in decision_ids
        head = text.lstrip()
        refused = any(head.startswith(marker) for marker in OPERATOR_REFUSAL_MARKERS)
        if answered_prompt or refused:
            decisions.append(text)
    return decisions
