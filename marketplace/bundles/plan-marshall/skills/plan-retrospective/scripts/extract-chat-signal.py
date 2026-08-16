#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reduce a Claude Code session JSONL transcript to its signal-bearing turns.

Pure deterministic fact reducer for the ``plan-retrospective`` chat-history
aspect (Aspect 14). Reads the session JSONL at a passed transcript path and
emits a reduced text transcript keeping ONLY signal-bearing turns, so the
orchestrator can feed a dense, budget-fitting transcript to the LLM analysis
prompt instead of the raw multi-megabyte JSONL.

Reduction contract (positive provenance predicate + decision-marker scan):

- A ``"role": "user"`` turn is kept only when :func:`is_operator_authored`
  says operator prose survives the harness envelopes. The predicate is
  POSITIVE and STRUCTURAL rather than an enumeration of known synthetic
  shapes: every harness-injected envelope is stripped, and the turn is kept
  only if prose REMAINS. The three synthetic classes it recognises are

  * an EMPTY or whitespace-only turn (a tool-result placeholder that carried
    no text block);
  * a turn that is WHOLLY a harness envelope — one or more XML-ish tag blocks
    with nothing outside them. The match is generic over the tag NAME, so a
    wrapper the harness introduces later is recognised without editing this
    file;
  * a SYNTHETIC SKILL-LOAD turn — a skill body injected into the
    conversation, recognized by its structural signature (a ``Base directory
    for this skill:`` line followed by a markdown heading) — or a verbatim
    harness re-entry notice.

  ⚠ The direction of failure is deliberate. An enumeration of synthetic
  shapes fails toward "operator" when the harness adds a wrapper nobody
  listed, which inflates the survivor count and manufactures a falsely
  healthy verdict. This predicate fails toward "synthetic" instead: an
  unrecognised envelope leaves no residue and is dropped. The cost is that an
  operator turn consisting of nothing but a tag block is misread as
  synthetic; that trade is intentional.

- A ``"role": "assistant"`` turn is kept ONLY when its text contains at least
  one of the established plan-marshall decision markers:
  ``[STATUS]``, ``[ERROR]``, ``AskUserQuestion``, ``[DECISION]``,
  ``[DISPATCH]``, ``[SKILL]``. An assistant turn is NEVER operator signal —
  it is retained for context and counted separately.
- OPERATOR GATE DECISIONS are recovered from the tool-result channel. On a
  gated run the operator answers with a permission decision or an
  ``AskUserQuestion`` selection, and those arrive as ``tool_result`` blocks —
  not as ``user`` prose — so a reducer that reads only free-form turns
  measures only the channel the operator did not use. Such results are
  rendered into the reduced transcript under the ``operator-decision`` role
  and counted in ``gate_decision_count``.
- Every other turn (tool-output, assistant prose without a marker, build logs
  echoed into the transcript) is dropped.

The script never judges — it reduces facts. It provides the signal that lets
the orchestrator decide Tier 1 (reduced transcript → LLM) vs Tier 2 (WARNING
finding + ``reason: transcript_too_large``):

- ``no_signal`` — true when the transcript carried NO OPERATOR-AUTHORED
  SIGNAL of either kind: zero operator-authored ``user`` turns AND zero
  operator gate decisions. It is deliberately NOT a count of survivors.
  A survivor count answers "did the reduction keep anything?", which grows
  with every class of injected instruction text the filter fails to
  recognise — so the verdict strengthened as the signal it measured
  degraded. Keying the flag on operator-authored counts breaks that coupling:
  retaining more framework boilerplate can no longer move it.
- ``over_budget`` — true when the reduced text still exceeds the read budget
  (``--read-budget-bytes``, default 2 MiB). The orchestrator emits the same
  WARNING finding + ``reason: transcript_too_large``.

Either flag (``no_signal`` OR ``over_budget``) is the Tier-2 trigger; when both
are false the reduced transcript is the Tier-1 input to the LLM prompt.

The returned TOON also carries ``raw_turn_count`` and ``dropped_turn_count`` so
the caller can see how much the reduction removed, plus the two operator-signal
counters (``operator_turn_count``, ``gate_decision_count``) that distinguish
"kept 200 turns, 3 operator-authored" from "kept 200 operator turns".

Like sibling fact extractors (``script-failure-analysis.py``,
``analyze-logs.py``), this script reads the file from disk directly and does
NOT invoke ``manage-logging`` — archived plans do not participate in
``PLAN_BASE_DIR`` resolution and the transcript path is passed explicitly.

Transcript shape:
    Each JSONL line is one event. A conversational turn carries a ``message``
    object with a ``role`` (``user`` / ``assistant``) and ``content``. Content
    is either a plain string or a list of typed blocks; only ``text`` blocks
    contribute to the reduced transcript and to the decision-marker scan,
    while ``tool_use`` / ``tool_result`` blocks feed the gate-decision scan.
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
from dataclasses import dataclass, field
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

# A harness-injected envelope: an XML-ish tag block. Matched GENERICALLY over
# the tag name — the point of the pattern is that a wrapper introduced after
# this file was written is still recognised, which is exactly what an
# enumeration of known tag names cannot do. Self-closing tags count too.
_HARNESS_ENVELOPE_RE = re.compile(
    r'<(?P<tag>[A-Za-z][-\w.]*)(?:\s[^<>]*)?/>'
    r'|<(?P<open>[A-Za-z][-\w.]*)(?:\s[^<>]*)?>.*?</(?P=open)\s*>',
    re.DOTALL,
)

# Verbatim harness re-entry notices. Unlike the envelopes above these carry no
# tag to key on, so they are matched as literal prefixes of the residue.
REENTRY_NOTICES: tuple[str, ...] = (
    'This session is being continued from a previous conversation',
    'Caveat: The messages below were generated by the user while running local commands',
)

# The tool through which the harness asks the operator to decide. A
# ``tool_result`` answering one of its calls carries an operator decision.
OPERATOR_DECISION_TOOL = 'AskUserQuestion'

# Verbatim harness notices reporting that the OPERATOR refused or interrupted a
# tool call. These are gate decisions: the operator acted, through the
# permission channel rather than through prose.
OPERATOR_REFUSAL_MARKERS: tuple[str, ...] = (
    "The user doesn't want to proceed with this tool use",
    "The user doesn't want to take this action right now",
    '[Request interrupted by user',
)

# Role label under which recovered gate decisions are rendered. Distinct from
# ``user`` so a reader can tell a free-form correction from a gate decision.
OPERATOR_DECISION_ROLE = 'operator-decision'


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


def strip_harness_envelopes(text: str) -> str:
    """Return ``text`` with every harness-injected tag block removed.

    The residue is what an operator wrote OUTSIDE the harness's envelopes. The
    harness routinely attaches an envelope to a genuine operator turn, so a
    turn is synthetic only when the residue is empty — not merely because an
    envelope is present.
    """
    return _HARNESS_ENVELOPE_RE.sub('', text)


def is_reentry_notice(text: str) -> bool:
    """Return True when ``text`` opens with a verbatim harness re-entry notice."""
    head = text.lstrip()
    return any(head.startswith(notice) for notice in REENTRY_NOTICES)


def is_operator_authored(text: str) -> bool:
    """Return True when ``text`` carries operator-authored prose.

    The positive predicate behind the whole reduction: rather than asking
    "does this match a known synthetic shape?" — which admits every shape
    nobody enumerated — it asks whether operator prose SURVIVES once the
    harness's own injection markers are removed. A turn with no residue is
    synthetic, whatever wrapper produced it.
    """
    if not text.strip():
        return False
    if is_synthetic_skill_load(text):
        return False
    residue = strip_harness_envelopes(text)
    if not residue.strip():
        return False
    return not is_reentry_notice(residue)


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
        refused = any(marker in text for marker in OPERATOR_REFUSAL_MARKERS)
        if answered_prompt or refused:
            decisions.append(text)
    return decisions


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
    injected skill bodies, and re-entry notices).
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
        'reduced_turn_count': len(reduction.turns),
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
