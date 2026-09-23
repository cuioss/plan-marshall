#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Render the distilled ``## Intent`` section into the finalize-generated PR body.

Automated reviewers judge a diff on generic correctness plus this repo's
``CLAUDE.md`` rules. None of them knows **what the change was supposed to do** —
implementation-vs-intent divergence (doc-contract drift, vacuous guards, a
predicate that does not do what the outline specified) is this project's most
recurring defect archetype, and no reviewer can catch it without the intent. The
PR description is the only channel that reaches every reviewer, so this script
puts a distilled statement of intent there.

Division of labour — the LLM distils, the SCRIPT decides:

The workflow agent writes its distillation to a scratch draft file with the Write
tool; this script owns every DETERMINISTIC decision about it — whether the
section is emitted at all, whether it fits the budget, and how a
budget-exceeding draft is truncated. The agent MUST NOT count characters or
truncate its own draft. Handing the budget to the agent would make the outcome
non-reproducible and would reintroduce exactly the silent-clip failure this
script exists to prevent.

Behaviour, in order:

1. **Read the outline through the EXISTING reader.** Both sections are read via
   ``manage-solution-outline read --plan-id {id} --section {summary|overview}``.
   This script authors NO second outline reader and never reads
   ``solution_outline.md`` directly — a second reader is precisely the
   source-of-truth duplication that produces drift.
2. **A reader that FAILED is an error, never an omission.** When the reader
   cannot be run (``OSError``), exits non-zero, or prints an envelope that does
   not parse, nothing is known about the outline, so the verb returns
   ``status: error`` / ``error: outline_unreadable`` with a ``detail`` naming the
   section and the cause, and exits 1 — the same shape as its
   ``draft_unreadable`` / ``empty_draft`` / ``body_unreadable`` siblings. Reading
   a failure as "no intent" would publish a PR that silently lacks a section the
   plan did state.
3. **A read that SUCCEEDED and found no outline, or both sections absent/empty =>
   emit NOTHING.** The body file is left BYTE-IDENTICAL and the verb returns
   ``omitted: true`` with an explicit reason. Never an empty heading, never a
   placeholder heading: a ``## Intent`` with nothing under it tells a reviewer less
   than no section at all, while implying the intent was considered and found
   vacuous.
4. **Outline present => render the draft**, enforce the budget, and append the
   section to the body file.
5. **Budget: cut at a sentence, and REPORT the overflow.** See
   :data:`INTENT_BUDGET_CHARS`. A draft over budget is never cut mid-sentence:
   only the complete sentences (or whole paragraphs) that fit are rendered — none
   at all when even the first does not fit — and the truncation marker is
   appended INSIDE the budget, never added on top of it, so the rendered section
   is never larger than the budget it claims to honour. **Silent truncation is
   categorically forbidden**: a clipped intent that looks complete is worse than
   an obviously-clipped one. The return states the overflow explicitly, because
   the body is appended to rather than replaced and ``ci pr view`` is the only way
   to read it back — a caller learns what was dropped from this return or not at
   all.

Return TOON carries ``status``, ``omitted``, ``truncated``, ``chars_written`` and
``budget``; a rendered section additionally carries ``overflow`` (the draft did
not fit), ``draft_chars`` (the draft's length) and ``chars_not_shown`` (how much
of it the rendered section omits).

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy, which injects ``PYTHONPATH`` for ``toon_parser`` and
``marketplace_paths`` — so no in-script ``sys.path`` manipulation is required.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from toon_parser import parse_toon, serialize_toon

# Character budget for the WHOLE rendered section (heading, body, and — when it
# fires — the truncation marker).
#
# Derivation, recorded here so the number is auditable rather than folkloric:
# ``max_description_tokens = 2000`` caps the ENTIRE PR body, and current generated
# bodies run to roughly 4,500 characters, leaving on the order of 2,000-3,000
# characters of headroom. 1500 sits inside that headroom with margin, so adding
# the Intent section cannot push a typical body past the description cap.
INTENT_BUDGET_CHARS = 1500

# The outline sections that constitute "the plan has a stated intent". Read in
# this order; the first non-empty one is enough to emit the section.
_OUTLINE_SECTIONS = ('summary', 'overview')

_HEADING = '## Intent'

# Emitted verbatim when the draft exceeds the budget. ``{shown}`` / ``{total}``
# make the loss quantified rather than merely flagged.
_TRUNCATION_MARKER = (
    '\n\n_[Intent truncated — {shown} of {total} characters shown; full outline in the plan workspace]_'
)


class OutlineUnreadable(Exception):
    """The outline reader FAILED, so nothing is known about the outline's intent.

    Distinct from a read that succeeded and found nothing: that one is an omission,
    this one is an error the caller must surface. ``section`` names the section
    being read and ``cause`` what went wrong.
    """

    def __init__(self, section: str, cause: str) -> None:
        super().__init__(f'section {section}: {cause}')
        self.section = section
        self.cause = cause


def _run_outline_read(plan_id: str, section: str) -> dict:
    """Read one outline section through the EXISTING manage-solution-outline reader.

    Deliberately a subprocess call to the canonical reader rather than an import
    or a direct file read: the outline's location, section-splitting rules, and
    absent-file handling belong to that skill, and duplicating any of them here
    would create a second source of truth that drifts.

    Returns the parsed envelope of a read that RAN — including a ``status: error``
    envelope, which is the reader's own answer (the outline or the section is
    absent). Raises :class:`OutlineUnreadable` when the reader could not be run, exited
    non-zero, or printed an envelope that does not parse: none of those is an answer
    about the outline, so none may be read as "no outline content".
    """
    try:
        completed = subprocess.run(
            [
                sys.executable,
                '.plan/execute-script.py',
                'plan-marshall:manage-solution-outline:manage-solution-outline',
                'read',
                '--plan-id',
                plan_id,
                '--section',
                section,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise OutlineUnreadable(section, f'reader could not be run: {exc}') from exc
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise OutlineUnreadable(section, f'reader exited {completed.returncode}: {stderr or "no stderr"}')
    try:
        parsed = parse_toon(completed.stdout)
    except (ValueError, KeyError) as exc:
        raise OutlineUnreadable(section, f'reader envelope does not parse: {exc}') from exc
    if not isinstance(parsed, dict):
        raise OutlineUnreadable(section, 'reader envelope is not a mapping')
    return parsed


def has_outline_intent(plan_id: str) -> bool:
    """Return True when the plan's outline states an intent worth rendering.

    True as soon as ANY of the declared sections carries non-whitespace content.
    False when every read succeeded and found no outline at all, or every section
    absent or empty — the omit-entirely case. A reader failure is neither: it
    propagates as :class:`OutlineUnreadable`.
    """
    for section in _OUTLINE_SECTIONS:
        payload = _run_outline_read(plan_id, section)
        if payload.get('status') != 'success':
            continue
        if str(payload.get('content') or '').strip():
            return True
    return False


# Where a unit of prose ends: a sentence terminator (with any closing bracket, quote
# or emphasis marker riding on it) followed by whitespace or the end of the text,
# or a blank line ending a paragraph — so a bullet or heading without terminal
# punctuation still ends as a whole unit. The pattern is matched against the WHOLE
# draft, never against a clipped window, so a terminator that only looks final
# because the window ends right after it (``3.5``, ``e.g.x``) is not a boundary.
_SENTENCE_END = re.compile(r'[.!?][)\]"\'*_`]*(?=\s|$)|\n[ \t]*\n')


def _complete_sentences_within(text: str, limit: int) -> str:
    """Return the longest prefix of ``text`` that ends on a sentence or paragraph boundary within ``limit``.

    Returns the empty string when not even the first sentence fits: rendering no
    prose is honest, a sentence cut part-way is not — it reads as a complete
    statement that says something different.
    """
    if len(text) <= limit:
        return text
    cut = 0
    for match in _SENTENCE_END.finditer(text):
        # A sentence keeps its terminator; a paragraph break ends before the blank line.
        candidate = match.start() if match.group().startswith('\n') else match.end()
        if candidate > limit:
            break
        cut = candidate
    return text[:cut].rstrip()


class IntentRender(NamedTuple):
    """The rendered section and the overflow facts a caller reports."""

    section: str
    #: The draft did not fit the budget, so part of it is not shown.
    truncated: bool
    #: Length of the (stripped) draft.
    draft_chars: int
    #: How many of the draft's characters the rendered section omits.
    chars_not_shown: int


def render_section(draft: str, budget: int = INTENT_BUDGET_CHARS) -> IntentRender:
    """Render the ``## Intent`` section from ``draft``, honouring ``budget``.

    The returned section NEVER exceeds ``budget``: when the draft does not fit, the
    truncation marker's own length is subtracted from the space available to the
    prose, so the marker lands INSIDE the budget rather than pushing the section past
    it — a marker appended on top of a budget-filling body would mean the section
    silently overruns the cap it advertises. The prose that remains is cut at a
    sentence or paragraph boundary, never mid-sentence.
    """
    body = draft.strip()
    prefix = f'{_HEADING}\n\n'
    available = budget - len(prefix)
    total = len(body)

    if total <= available:
        return IntentRender(prefix + body, False, total, 0)

    # Reserve the marker's rendered length BEFORE deciding how much prose fits.
    # The marker's own digits depend on the numbers it reports, so render it once
    # with a provisional count and reserve that length; the count only shrinks the
    # prose, never grows the section.
    provisional = _TRUNCATION_MARKER.format(shown=available, total=total)
    prose_room = max(available - len(provisional), 0)
    prose = _complete_sentences_within(body, prose_room)
    marker = _TRUNCATION_MARKER.format(shown=len(prose), total=total)
    return IntentRender(prefix + prose + marker, True, total, total - len(prose))


def cmd_render(args: argparse.Namespace) -> int:
    """Append the rendered Intent section to the PR body file, or omit it entirely."""
    body_path = Path(args.body_path)

    try:
        outline_has_intent = has_outline_intent(args.plan_id)
    except OutlineUnreadable as exc:
        # Nothing is known about the outline, so neither rendering nor omitting is
        # a supported answer. The body file is left untouched.
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'render',
                    'error': 'outline_unreadable',
                    'detail': str(exc),
                }
            )
        )
        return 1

    if not outline_has_intent:
        # Byte-identical body. No heading, no placeholder — see the module
        # docstring for why an empty section is worse than none.
        print(
            serialize_toon(
                {
                    'status': 'success',
                    'operation': 'render',
                    'omitted': True,
                    'reason': 'no outline intent: solution_outline.md absent, or its '
                    'summary and overview sections are both absent or empty',
                    'truncated': False,
                    'chars_written': 0,
                    'budget': INTENT_BUDGET_CHARS,
                }
            )
        )
        return 0

    try:
        draft = Path(args.draft_path).read_text(encoding='utf-8')
    except OSError as exc:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'render',
                    'error': 'draft_unreadable',
                    'detail': f'{args.draft_path}: {exc}',
                }
            )
        )
        return 1

    if not draft.strip():
        # The outline states an intent but the agent supplied nothing to render.
        # Fail loud rather than emitting an empty heading.
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'render',
                    'error': 'empty_draft',
                    'detail': 'the plan has an outline intent but the draft file is empty',
                }
            )
        )
        return 1

    rendered = render_section(draft)

    try:
        existing = body_path.read_text(encoding='utf-8')
    except OSError as exc:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'render',
                    'error': 'body_unreadable',
                    'detail': f'{args.body_path}: {exc}',
                }
            )
        )
        return 1

    separator = '' if existing.endswith('\n\n') else ('\n' if existing.endswith('\n') else '\n\n')
    body_path.write_text(existing + separator + rendered.section + '\n', encoding='utf-8')

    print(
        serialize_toon(
            {
                'status': 'success',
                'operation': 'render',
                'omitted': False,
                'truncated': rendered.truncated,
                'chars_written': len(rendered.section),
                'budget': INTENT_BUDGET_CHARS,
                # The overflow, stated rather than left to be inferred from the body:
                # the section is appended, and this return is where a caller learns
                # how much of the draft a reviewer will not see.
                'overflow': rendered.truncated,
                'draft_chars': rendered.draft_chars,
                'chars_not_shown': rendered.chars_not_shown,
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``render`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Render the distilled ## Intent section into the finalize-generated PR '
            'body. Omits the section entirely when the plan has no outline intent.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    render_parser = subparsers.add_parser(
        'render',
        help='Append the Intent section to the PR body, or omit it entirely',
        allow_abbrev=False,
    )
    render_parser.add_argument('--plan-id', required=True, help='Plan identifier (kebab-case)')
    render_parser.add_argument(
        '--draft-path',
        required=True,
        help=(
            'Scratch file carrying the LLM-authored distillation. The agent writes '
            'it with the Write tool and MUST NOT count characters or truncate it — '
            'the budget is enforced here, deterministically.'
        ),
    )
    render_parser.add_argument(
        '--body-path',
        required=True,
        help='PR body file the rendered section is appended to (left byte-identical when omitted)',
    )
    render_parser.set_defaults(func=cmd_render)
    return parser


def main() -> int:
    """Entry point."""
    args = build_parser().parse_args()
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
