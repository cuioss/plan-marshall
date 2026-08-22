#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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
2. **No outline, or both sections absent/empty => emit NOTHING.** The body file
   is left BYTE-IDENTICAL and the verb returns ``omitted: true`` with an explicit
   reason. Never an empty heading, never a placeholder heading: a ``## Intent``
   with nothing under it tells a reviewer less than no section at all, while
   implying the intent was considered and found vacuous.
3. **Outline present => render the draft**, enforce the budget, and append the
   section to the body file.
4. **Budget with VISIBLE truncation.** See :data:`INTENT_BUDGET_CHARS`. A draft
   over budget is truncated at a word boundary and the truncation marker is
   appended INSIDE the budget, never added on top of it — so the rendered
   section is never larger than the budget it claims to honour. **Silent
   truncation is categorically forbidden**: a clipped intent that looks complete
   is worse than an obviously-clipped one, because a reviewer cannot tell the
   statement was cut off mid-thought.

Return TOON carries ``status``, ``omitted``, ``truncated``, ``chars_written``,
and ``budget``.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy, which injects ``PYTHONPATH`` for ``toon_parser`` and
``marketplace_paths`` — so no in-script ``sys.path`` manipulation is required.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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
    '\n\n_[Intent truncated — {shown} of {total} characters shown; '
    'full outline in the plan workspace]_'
)


def _run_outline_read(plan_id: str, section: str) -> dict:
    """Read one outline section through the EXISTING manage-solution-outline reader.

    Deliberately a subprocess call to the canonical reader rather than an import
    or a direct file read: the outline's location, section-splitting rules, and
    absent-file handling belong to that skill, and duplicating any of them here
    would create a second source of truth that drifts.

    A non-zero exit, an unparseable envelope, or a non-success status all degrade
    to an empty dict — "no outline content" — because every one of those means
    the same thing for this script's purposes.
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
    except OSError:
        return {}
    if completed.returncode != 0:
        return {}
    try:
        parsed = parse_toon(completed.stdout)
    except (ValueError, KeyError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def has_outline_intent(plan_id: str) -> bool:
    """Return True when the plan's outline states an intent worth rendering.

    True as soon as ANY of the declared sections carries non-whitespace content.
    False when there is no outline at all, or when every section is absent or
    empty — the omit-entirely case.
    """
    for section in _OUTLINE_SECTIONS:
        payload = _run_outline_read(plan_id, section)
        if payload.get('status') != 'success':
            continue
        if str(payload.get('content') or '').strip():
            return True
    return False


def _truncate_at_word_boundary(text: str, limit: int) -> str:
    """Return ``text`` cut to at most ``limit`` characters, ending on a word boundary.

    Falls back to a hard cut when the first ``limit`` characters contain no
    whitespace to break on — a hard cut is still preferable to overrunning a
    budget the caller has already reserved space against.
    """
    if len(text) <= limit:
        return text
    window = text[:limit]
    cut = window.rstrip()
    boundary = cut.rfind(' ')
    if boundary > 0:
        cut = cut[:boundary]
    return cut.rstrip()


def render_section(draft: str, budget: int = INTENT_BUDGET_CHARS) -> tuple[str, bool]:
    """Render the ``## Intent`` section from ``draft``, honouring ``budget``.

    Returns ``(section_text, truncated)``. The returned text NEVER exceeds
    ``budget``: when the draft does not fit, the truncation marker's own length is
    subtracted from the space available to the prose, so the marker lands INSIDE
    the budget rather than pushing the section past it. That ordering is the whole
    point — a marker appended on top of a budget-filling body would mean the
    section silently overruns the cap it advertises.
    """
    body = draft.strip()
    prefix = f'{_HEADING}\n\n'
    available = budget - len(prefix)

    if len(body) <= available:
        return prefix + body, False

    total = len(body)
    # Reserve the marker's rendered length BEFORE deciding how much prose fits.
    # The marker's own digits depend on the numbers it reports, so render it once
    # with a provisional count and reserve that length; the count only shrinks the
    # prose, never grows the section.
    provisional = _TRUNCATION_MARKER.format(shown=available, total=total)
    prose_room = available - len(provisional)
    if prose_room < 0:
        prose_room = 0
    prose = _truncate_at_word_boundary(body, prose_room)
    marker = _TRUNCATION_MARKER.format(shown=len(prose), total=total)
    return prefix + prose + marker, True


def cmd_render(args: argparse.Namespace) -> int:
    """Append the rendered Intent section to the PR body file, or omit it entirely."""
    body_path = Path(args.body_path)

    if not has_outline_intent(args.plan_id):
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

    section, truncated = render_section(draft)

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
    body_path.write_text(existing + separator + section + '\n', encoding='utf-8')

    print(
        serialize_toon(
            {
                'status': 'success',
                'operation': 'render',
                'omitted': False,
                'truncated': truncated,
                'chars_written': len(section),
                'budget': INTENT_BUDGET_CHARS,
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
