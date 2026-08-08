#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reduce a Claude Code session JSONL transcript to its signal-bearing turns.

Pure deterministic fact reducer for the ``plan-retrospective`` chat-history
aspect (Aspect 14). Reads the session JSONL at a passed transcript path and
emits a reduced text transcript keeping ONLY signal-bearing turns, so the
orchestrator can feed a dense, budget-fitting transcript to the LLM analysis
prompt instead of the raw multi-megabyte JSONL.

Reduction contract (provenance-filter + decision-marker scan):

- A ``"role": "user"`` turn is kept only when it is OPERATOR-AUTHORED. The
  harness injects two classes of synthetic ``user`` turn that carry no operator
  signal and are dropped:
  * an EMPTY or whitespace-only turn (a tool-result placeholder that carried no
    text block);
  * a SYNTHETIC SKILL-LOAD turn — a skill body injected into the conversation,
    recognized by its structural signature (a ``Base directory for this skill:``
    line followed by a markdown heading).
  Filtering by turn ROLE alone made these indistinguishable from real operator
  utterances, so the "reduced" transcript was dominated by framework
  boilerplate (measured: ~90% of 285 KB, fewer than 10 of 287 turns
  operator-authored) and a transcript with almost no operator signal was
  confidently classified Tier 1.
- A ``"role": "assistant"`` turn is kept ONLY when its text contains at least
  one of the established plan-marshall decision markers:
  ``[STATUS]``, ``[ERROR]``, ``AskUserQuestion``, ``[DECISION]``,
  ``[DISPATCH]``, ``[SKILL]``.
- Every other turn (tool-output, assistant prose without a marker, build logs
  echoed into the transcript) is dropped.

The script never judges — it reduces facts. It provides the signal that lets
the orchestrator decide Tier 1 (reduced transcript → LLM) vs Tier 2 (WARNING
finding + ``reason: transcript_too_large``):

- ``no_signal`` — true when the reduction kept zero turns. Because the surviving
  set is now operator-authored content by construction, this is an honest
  "no operator signal in this transcript" verdict rather than a count of
  framework boilerplate. The orchestrator emits a WARNING finding and
  ``status: skipped, reason: transcript_too_large``.
- ``over_budget`` — true when the reduced text still exceeds the read budget
  (``--read-budget-bytes``, default 2 MiB). The orchestrator emits the same
  WARNING finding + ``reason: transcript_too_large``.

Either flag (``no_signal`` OR ``over_budget``) is the Tier-2 trigger; when both
are false the reduced transcript is the Tier-1 input to the LLM prompt.

The returned TOON also carries ``raw_turn_count`` and ``dropped_turn_count`` so
the caller can see how much the reduction removed.

Like sibling fact extractors (``script-failure-analysis.py``,
``analyze-logs.py``), this script reads the file from disk directly and does
NOT invoke ``manage-logging`` — archived plans do not participate in
``PLAN_BASE_DIR`` resolution and the transcript path is passed explicitly.

Transcript shape:
    Each JSONL line is one event. A conversational turn carries a ``message``
    object with a ``role`` (``user`` / ``assistant``) and ``content``. Content
    is either a plain string or a list of typed blocks; only ``text`` blocks
    contribute to the reduced transcript and to the decision-marker scan.
    Non-turn events (summaries, meta lines) and malformed lines are skipped at
    the boundary.

Usage:
    python3 extract-chat-signal.py run --transcript-path /abs/path/to/session.jsonl
    python3 extract-chat-signal.py run --transcript-path /abs/path --read-budget-bytes 2097152
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

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

# Structural signature of a synthetic skill-load turn: the harness injects a
# loaded skill's body as a ``user`` turn whose text opens with the base-directory
# line and continues into the skill's markdown body.
_SKILL_LOAD_MARKER = 'Base directory for this skill:'
_MARKDOWN_HEADING_RE = re.compile(r'^#{1,6}\s+\S', re.MULTILINE)


def is_synthetic_skill_load(text: str) -> bool:
    """Return True when ``text`` is a skill body injected as a synthetic user turn.

    Recognized structurally rather than by any single substring: the text must
    carry the ``Base directory for this skill:`` line AND a markdown heading
    somewhere after it — the shape of an injected SKILL.md body. Requiring both
    keeps an operator who merely quotes the marker line from being dropped.
    """
    index = text.find(_SKILL_LOAD_MARKER)
    if index == -1:
        return False
    return _MARKDOWN_HEADING_RE.search(text, index) is not None


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

    A ``user`` turn is kept only when it is operator-authored: empty and
    whitespace-only turns (tool-result placeholders) and synthetic skill-load
    turns are dropped. Assistant and other-role handling is unchanged.
    """
    if role == 'user':
        if not text.strip():
            return False
        return not is_synthetic_skill_load(text)
    if role == 'assistant':
        return any(marker in text for marker in DECISION_MARKERS)
    return False


def parse_turn(line: str) -> tuple[str, str] | None:
    """Parse one JSONL ``line`` into ``(role, text)`` or ``None``.

    Returns ``None`` for blank lines, non-JSON lines, non-object payloads,
    events with no ``message`` object, and turns whose ``role`` is missing.
    The reduced text is the extracted text payload (may be empty for a turn
    that carried only non-text blocks).
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
    text = extract_text(message.get('content'))
    return role, text


def reduce_transcript(lines: list[str]) -> tuple[list[dict[str, str]], int]:
    """Walk JSONL ``lines`` and return ``(kept_turns, raw_turn_count)``.

    Each kept turn is a dict ``{'role': ..., 'text': ...}``, in document order.
    ``raw_turn_count`` is the number of parseable turns seen before reduction, so
    the caller can report how much was dropped.

    Dropped turns contribute nothing: unmarked assistant prose, tool-output,
    malformed lines, empty or whitespace-only ``user`` turns (tool-result
    placeholders carrying no text block), and synthetic skill-load ``user``
    turns.
    """
    kept: list[dict[str, str]] = []
    raw_turn_count = 0
    for line in lines:
        parsed = parse_turn(line)
        if parsed is None:
            continue
        raw_turn_count += 1
        role, text = parsed
        if is_signal_bearing(role, text):
            kept.append({'role': role, 'text': text})
    return kept, raw_turn_count


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
            'reduced_transcript': '',
        }

    turns, raw_turn_count = reduce_transcript(lines)
    reduced_text = render_reduced(turns)
    reduced_bytes = len(reduced_text.encode('utf-8'))

    # ``no_signal`` is computed from the SURVIVING turn count — the set that is
    # operator-authored by construction after the reduction above.
    no_signal = len(turns) == 0
    over_budget = reduced_bytes > read_budget

    return {
        'aspect': 'chat-signal-extraction',
        'status': 'success',
        'transcript_path': str(transcript_path),
        'reduced_turn_count': len(turns),
        'raw_turn_count': raw_turn_count,
        'dropped_turn_count': raw_turn_count - len(turns),
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
