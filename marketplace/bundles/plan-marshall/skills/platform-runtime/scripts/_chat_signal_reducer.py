#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reduction engine for the ``chat extract-signal`` runtime operation.

Walks a platform session JSONL transcript and returns its signal-bearing turns
as a reduced text transcript, so the plan-retrospective chat-history aspect can
feed a dense, budget-fitting transcript to the LLM analysis prompt instead of
the raw multi-megabyte JSONL. This is the platform-owned format knowledge of
the operation; all Claude-transcript shape knowledge lives behind this
boundary and is exercised here, never in the consuming skill.

The reduction contract — what counts as operator provenance, why the
no-signal verdict is not a survivor count, the gated-decision channel, and the
published harness-injection marker inventory — is specified in the ``chat
extract-signal`` operation contract (``standards/contract.md``). It is NOT
restated here. What follows is only what a reader of this module needs to
follow the code:

- A ``user`` turn is kept when :func:`_chat_provenance.is_operator_authored`
  finds operator prose remaining after every harness envelope is stripped. The
  predicate is positive and structural, so an envelope shape introduced later
  is recognised without editing this file.
- An ``assistant`` turn is kept when its text carries a decision marker from
  :data:`DECISION_MARKERS`. Assistant turns are context, never operator
  signal: they move neither operator counter, so they cannot affect
  ``no_signal``.
- Operator GATE DECISIONS are recovered from ``tool_result`` blocks and
  rendered under :data:`OPERATOR_DECISION_ROLE`.
- Everything else is dropped.

The reducer never judges — it reduces facts. It returns the raw reduction
outcome plus the ``no_signal`` verdict (``operator_turn_count == 0`` AND
``gate_decision_count == 0``), so an operator-authored count keys the verdict
rather than a survivor count: a survivor count rises with every class of
injected instruction text the filter fails to recognise, so keying the verdict
on it made reported health strengthen as measured signal degraded.

Read budgets are deliberately NOT discovered or applied here. Whether the
reduced text fits the caller's read budget is a consumer-side decision the
runtime must not make; this module reports the reduced byte count and leaves
``over_budget`` to the caller. A missing transcript is reported to the caller
via ``FileNotFoundError`` at the lower-level entry point
(:func:`read_transcript_lines`) so the operation can map it to its
``transcript_not_found`` no-op.

Transcript shape:
    Each JSONL line is one event. A conversational turn carries a ``message``
    object with a ``role`` and ``content``. Content is either a plain string
    or a list of typed blocks; ``text`` blocks feed the reduced transcript and
    the decision-marker scan, while ``tool_use`` / ``tool_result`` blocks feed
    the gate-decision scan. Non-turn events and malformed lines are skipped at
    the boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _chat_gate_decisions import (
    OPERATOR_DECISION_ROLE,
    decision_tool_use_ids,
    extract_gate_decisions,
)
from _chat_provenance import is_operator_authored

# The established plan-marshall decision-marker set. An assistant turn is
# signal-bearing when its text contains at least one of these substrings.
DECISION_MARKERS: tuple[str, ...] = (
    '[STATUS]',
    '[ERROR]',
    'AskUserQuestion',
    '[DECISION]',
    '[DISPATCH]',
    '[SKILL]',
)


@dataclass
class Reduction:
    """The outcome of reducing one transcript.

    Attributes:
        turns: The kept entries, in document order. Each is a dict with
            ``role`` and ``text``; recovered gate decisions carry the
            :data:`OPERATOR_DECISION_ROLE` label rather than ``user``.
        raw_turn_count: Parseable turns seen before reduction.
        kept_raw_count: Raw turns kept, excluding synthesised gate-decision
            entries, so ``raw_turn_count - kept_raw_count`` is what the
            reduction dropped.
        operator_turn_count: Free-form operator-authored ``user`` turns.
        gate_decision_count: Operator decisions recovered from the tool-result
            channel.
    """

    turns: list[dict[str, str]] = field(default_factory=list)
    raw_turn_count: int = 0
    kept_raw_count: int = 0
    operator_turn_count: int = 0
    gate_decision_count: int = 0

    @property
    def dropped_turn_count(self) -> int:
        """Raw turns the reduction removed."""
        return self.raw_turn_count - self.kept_raw_count

    @property
    def has_operator_signal(self) -> bool:
        """True when the transcript carried operator signal of either kind."""
        return bool(self.operator_turn_count or self.gate_decision_count)


def extract_text(content: Any) -> str:
    """Return the plain-text payload of a turn's ``content``.

    ``content`` is either a plain string (legacy / simple turns) or a list of
    typed content blocks (the common multi-block shape). Only ``text`` blocks
    contribute; tool-use / tool-result / image blocks carry no conversational
    text and are skipped. A block missing a ``type`` but carrying a ``text``
    field is treated as text (defensive against shape drift).

    Returns the concatenation of all text blocks joined by newlines, or the
    string itself when ``content`` is already a string. Any other shape yields
    the empty string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get('type')
            text = block.get('text')
            if block_type == 'text' and isinstance(text, str):
                parts.append(text)
            elif block_type is None and isinstance(text, str):
                parts.append(text)
        return '\n'.join(parts)
    return ''


def is_signal_bearing(role: str, text: str) -> bool:
    """Return True when the turn should be kept in the reduced transcript.

    A ``user`` turn is kept only when :func:`is_operator_authored` finds
    operator prose surviving the harness envelopes. An ``assistant`` turn is
    kept when it carries a decision marker; every other role is dropped.
    """
    if role == 'user':
        return is_operator_authored(text)
    if role == 'assistant':
        return any(marker in text for marker in DECISION_MARKERS)
    return False


def parse_message(line: str) -> dict[str, Any] | None:
    """Parse one JSONL ``line`` into its ``message`` object, or ``None``.

    Returns ``None`` for blank lines, non-JSON lines, non-object payloads,
    events with no ``message`` object, and turns whose ``role`` is missing or
    empty.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        event = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(event, dict):
        return None
    message = event.get('message')
    if not isinstance(message, dict):
        return None
    role = message.get('role')
    if not isinstance(role, str) or not role:
        return None
    return message


def parse_turn(line: str) -> tuple[str, str] | None:
    """Parse one JSONL ``line`` into ``(role, text)`` or ``None``.

    The reduced text is the extracted text payload (may be empty for a turn
    that carried only non-text blocks). ``None`` is returned for every shape
    :func:`parse_message` rejects.
    """
    message = parse_message(line)
    if message is None:
        return None
    return str(message['role']), extract_text(message.get('content'))


def reduce_transcript(lines: list[str]) -> Reduction:
    """Walk JSONL ``lines`` and return the :class:`Reduction`.

    Kept entries are in document order. Alongside the surviving turns the walk
    counts the two operator-signal classes separately — free-form
    operator-authored ``user`` turns, and gate decisions recovered from the
    tool-result channel — so a caller can distinguish surviving VOLUME from
    operator SIGNAL.

    Dropped turns contribute nothing: unmarked assistant prose, tool-output,
    malformed lines, and every ``user`` turn that leaves no operator residue
    (empty or whitespace-only placeholders, whole-envelope harness injections,
    injected skill bodies, and envelope-less harness notices that did not also
    yield operator-bearing text).
    """
    result = Reduction()
    decision_ids: set[str] = set()
    for line in lines:
        message = parse_message(line)
        if message is None:
            continue
        result.raw_turn_count += 1
        role = str(message['role'])
        content = message.get('content')
        if role == 'assistant':
            decision_ids |= decision_tool_use_ids(content)
        if role == 'user':
            for decision in extract_gate_decisions(content, decision_ids):
                result.turns.append({'role': OPERATOR_DECISION_ROLE, 'text': decision})
                result.gate_decision_count += 1
        text = extract_text(content)
        if is_signal_bearing(role, text):
            result.turns.append({'role': role, 'text': text})
            result.kept_raw_count += 1
            if role == 'user':
                result.operator_turn_count += 1
    return result


def render_reduced(turns: list[dict[str, str]]) -> str:
    blocks = [f'{turn["role"]}: {turn["text"]}' for turn in turns]
    return '\n\n'.join(blocks)


def read_transcript_lines(path: Path) -> list[str]:
    """Return the raw lines of the transcript at ``path``.

    A missing file raises ``FileNotFoundError`` so the caller can map it to the
    ``transcript_not_found`` reason; an unreadable file (permission error)
    raises ``OSError`` and is surfaced as a structured error TOON. Invalid
    UTF-8 bytes are replaced with the Unicode replacement character so the
    reduction proceeds robustly on malformed input.
    """
    if not path.is_file():
        raise FileNotFoundError(f'Transcript not found: {path}')
    return path.read_text(encoding='utf-8', errors='replace').splitlines()


def reduce_chat_signal(transcript_path: Path) -> dict[str, Any]:
    """Reduce the transcript at *transcript_path* to its normalized record.

    Returns the seven normalized fields that make up the operation's success
    payload. ``no_signal`` is derived from OPERATOR-AUTHORED counts, never from
    the survivor count (see module docstring). The reduced byte count is
    reported so the caller can own its read-budget decision; the reduction is
    never truncated here.

    Raises:
        FileNotFoundError: No file exists at *transcript_path*; the operation
            maps this to its ``transcript_not_found`` no-op.
        OSError: The record could not be read (e.g. permission error); surfaced
            as an operation error.
    """
    lines = read_transcript_lines(transcript_path)
    reduction = reduce_transcript(lines)
    reduced_text = render_reduced(reduction.turns)
    return {
        'reduced_transcript': reduced_text,
        'raw_turn_count': reduction.raw_turn_count,
        'kept_raw_count': reduction.kept_raw_count,
        'operator_turn_count': reduction.operator_turn_count,
        'gate_decision_count': reduction.gate_decision_count,
        'reduced_bytes': len(reduced_text.encode('utf-8')),
        'no_signal': not reduction.has_operator_signal,
    }
