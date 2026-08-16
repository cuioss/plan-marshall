#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reduce a Claude Code session JSONL transcript to its signal-bearing turns.

Pure deterministic fact reducer for the ``plan-retrospective`` chat-history
aspect (Aspect 14). Reads the session JSONL at a passed transcript path and
emits a reduced text transcript, so the orchestrator can feed a dense,
budget-fitting transcript to the LLM analysis prompt instead of the raw
multi-megabyte JSONL.

The reduction contract — what counts as operator provenance, why the verdict
is not a survivor count, the gated-decision channel, and the published
harness-injection marker inventory — is specified in
``references/chat-history-analysis.md``. It is NOT restated here. What follows
is only what a reader of this module needs to follow the code:

- A ``user`` turn is kept when :func:`is_operator_authored` finds operator
  prose remaining after every harness envelope is stripped. The predicate is
  positive and structural, so an envelope shape introduced later is
  recognised without editing this file.
- An ``assistant`` turn is kept when its text carries a decision marker from
  :data:`DECISION_MARKERS`. Assistant turns are context, never operator
  signal: they move neither operator counter, so they cannot affect
  ``no_signal``.
- Operator GATE DECISIONS are recovered from ``tool_result`` blocks and
  rendered under :data:`OPERATOR_DECISION_ROLE`.
- Everything else is dropped.

The script never judges — it reduces facts. It returns the two Tier-2 trigger
flags the orchestrator routes on:

- ``no_signal`` — the transcript carried no operator-authored signal of either
  kind (``operator_turn_count == 0`` AND ``gate_decision_count == 0``).
  Deliberately NOT a survivor count: a survivor count rises with every class
  of injected instruction text the filter fails to recognise, so keying the
  verdict on it made reported health strengthen as measured signal degraded.
- ``over_budget`` — the reduced text still exceeds ``--read-budget-bytes``.

``reduced_turn_count`` counts the RAW turns kept, so
``reduced_turn_count + dropped_turn_count == raw_turn_count`` holds. Recovered
gate decisions were never raw turns: they are extra entries in
``reduced_transcript`` counted by ``gate_decision_count`` alone.

Like sibling fact extractors (``script-failure-analysis.py``,
``analyze-logs.py``), this script reads the file from disk directly and does
NOT invoke ``manage-logging`` — archived plans do not participate in
``PLAN_BASE_DIR`` resolution and the transcript path is passed explicitly.

Transcript shape:
    Each JSONL line is one event. A conversational turn carries a ``message``
    object with a ``role`` and ``content``. Content is either a plain string
    or a list of typed blocks; ``text`` blocks feed the reduced transcript and
    the decision-marker scan, while ``tool_use`` / ``tool_result`` blocks feed
    the gate-decision scan. Non-turn events and malformed lines are skipped at
    the boundary.

Usage:
    python3 extract-chat-signal.py run --transcript-path /abs/path/to/session.jsonl
    python3 extract-chat-signal.py run --transcript-path /abs/path --read-budget-bytes 2097152
"""

from __future__ import annotations

import argparse
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
from file_ops import output_toon, safe_main
from input_validation import (
    parse_args_with_toon_errors,
)

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

# Default read budget for the reduced transcript: 2 MiB. When the reduced text
# still exceeds this, the orchestrator falls back to the Tier-2 WARNING finding.
DEFAULT_READ_BUDGET_BYTES = 2 * 1024 * 1024

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
    tool-result channel — so the caller can distinguish surviving VOLUME from
    operator SIGNAL.

    Dropped turns contribute nothing: unmarked assistant prose, tool-output,
    malformed lines, and every ``user`` turn that leaves no operator residue
    (empty or whitespace-only placeholders, whole-envelope harness injections,
    injected skill bodies, and envelope-less harness notices).
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
    ``transcript_unavailable`` reason; an unreadable file (permission error)
    raises ``OSError`` and is surfaced by ``safe_main`` as a structured
    ``internal_error`` TOON.  Invalid UTF-8 bytes are replaced with the Unicode
    replacement character so the pre-pass proceeds robustly on malformed input.
    """
    if not path.is_file():
        raise FileNotFoundError(f'Transcript not found: {path}')
    return path.read_text(encoding='utf-8', errors='replace').splitlines()


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    transcript_path = Path(args.transcript_path)
    read_budget = args.read_budget_bytes

    try:
        lines = read_transcript_lines(transcript_path)
    except FileNotFoundError:
        return {
            'aspect': 'chat-signal-extraction',
            'status': 'skipped',
            'reason': 'transcript_unavailable',
            'transcript_path': str(transcript_path),
            'reduced_turn_count': 0,
            'reduced_bytes': 0,
            'read_budget_bytes': read_budget,
            'no_signal': True,
            'over_budget': False,
            'raw_turn_count': 0,
            'dropped_turn_count': 0,
            'operator_turn_count': 0,
            'gate_decision_count': 0,
            'reduced_transcript': '',
        }

    reduction = reduce_transcript(lines)
    reduced_text = render_reduced(reduction.turns)
    reduced_bytes = len(reduced_text.encode('utf-8'))

    # ``no_signal`` is derived from OPERATOR-AUTHORED counts, never from the
    # survivor count. A survivor count rises with every class of injected
    # instruction text the filter fails to recognise, so keying the verdict on
    # it made the reported health strengthen as the measured signal degraded.
    no_signal = not reduction.has_operator_signal
    over_budget = reduced_bytes > read_budget

    return {
        'aspect': 'chat-signal-extraction',
        'status': 'success',
        'transcript_path': str(transcript_path),
        'reduced_turn_count': reduction.kept_raw_count,
        'raw_turn_count': reduction.raw_turn_count,
        'dropped_turn_count': reduction.dropped_turn_count,
        'operator_turn_count': reduction.operator_turn_count,
        'gate_decision_count': reduction.gate_decision_count,
        'reduced_bytes': reduced_bytes,
        'read_budget_bytes': read_budget,
        'no_signal': no_signal,
        'over_budget': over_budget,
        'reduced_transcript': reduced_text,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Reduce a session JSONL transcript to its signal-bearing turns',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Reduce a transcript to signal-bearing turns',
        allow_abbrev=False,
    )
    run_parser.add_argument(
        '--transcript-path',
        required=True,
        help='Absolute path to the session JSONL transcript',
    )
    run_parser.add_argument(
        '--read-budget-bytes',
        type=int,
        default=DEFAULT_READ_BUDGET_BYTES,
        help=(
            'Read budget in bytes for the reduced transcript '
            f'(default {DEFAULT_READ_BUDGET_BYTES}); over_budget is set when the '
            'reduced text exceeds this'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
