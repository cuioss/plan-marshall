#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Foundational-skill notation extraction and resolution, shared by the guards.

A ``## Foundational Practices`` block names the skills a body cannot run
without. Two things about that name make it awkward to guard, and both are
properties of the tree rather than of any one body:

- **The spelling is target-specific.** A Claude-target body writes
  ``plan-marshall:persona-plan-marshall-agent``; the same body as generated for
  OpenCode writes ``plan-marshall-persona-plan-marshall-agent``; the Antigravity
  export puts the same name inside a ``view_file`` call. A guard that resolves
  only the ``:`` spelling reports every non-Claude target as naming a skill that
  does not exist.
- **The retirement is invisible from the source alone.** A body in the SOURCE
  can only name a skill the source contains, so a source-scoped check alone can
  never catch a DEPLOYED tree still naming a notation the marketplace retired.

So the registry is the marketplace source tree — re-read on every call, never
restated as a list — and the resolution accepts either spelling. Neither is a
convenience: a hardcoded skill list is a snapshot that goes stale silently, and
a single-spelling resolver turns a target's naming convention into a red build.

Usage:
    from _foundational_skills import (
        FOUNDATIONAL_PRACTICES_HEADING,
        MARKETPLACE_ROOT,
        extract_foundational_notations,
        resolve_notation,
    )
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT as _CONFTEST_MARKETPLACE_ROOT
from conftest import PROJECT_ROOT as _CONFTEST_PROJECT_ROOT

#: The block whose ``Skill:`` / ``name:`` entries declare a body's
#: non-negotiable skills. Bodies without this block declare no foundational
#: skill, so there is nothing for the load-or-fail-closed rule to bind.
#:
#: Matched as a HEADING LINE, never as a bare substring: the canonical rule
#: document refers to the block by name in prose (``a body's `## Foundational
#: Practices` block``), and a substring match reads that reference as a second
#: declaration — the rule document would then be swept for the notations it
#: discusses, including the retired ones it exists to name.
FOUNDATIONAL_PRACTICES_HEADING = '## Foundational Practices'

_FOUNDATIONAL_PRACTICES_RE = re.compile(r'^## Foundational Practices[ \t]*$', re.MULTILINE)

#: The marketplace source tree IS the live registry. Every skill the marketplace
#: ships is a directory under ``marketplace/bundles/{bundle}/skills/{skill}/``.
#: Re-read per call, so a skill added or removed after this module was written is
#: reflected without a second edit.
#:
#: Bound through :class:`~pathlib.Path` rather than reused straight from conftest:
#: the conftest constant is untyped, so reusing the NAME would leave the
#: re-binding as ``Any`` under ``mypy --strict`` and take the ``bool`` every
#: ``is_file()``-returning helper promises down to ``Any`` with it.
MARKETPLACE_ROOT = Path(_CONFTEST_MARKETPLACE_ROOT)

#: The repository-relative root of the GENERATED target trees — the deployment
#: surface the freshness guard reads. It is the generator's own output
#: (``./pw generate``), not a hand-maintained copy, so what the guard reads is
#: what the deploy step publishes.
TARGET_ROOT = Path(_CONFTEST_PROJECT_ROOT) / 'target'

#: The block a ``## Foundational Practices`` section runs until. A body's next
#: same-or-higher heading ends it; ``##`` is the level this section is authored
#: at, so the terminating heading is the next one at that level or above.
_SECTION_TERMINATOR = re.compile(r'^#{1,2} ', re.MULTILINE)

#: A notation as the Claude target writes it, or as a ``name:`` field spells it
#: inside a tool call. Both carry the ``bundle:skill`` shape.
_COLON_NOTATION = re.compile(r'\b([a-z0-9][a-z0-9-]*):([a-z0-9][a-z0-9-]*)\b')

#: A notation as the OpenCode / Antigravity targets write it — the two segments
#: joined by a hyphen rather than a colon, because the deployed directory name is
#: the flattened ``{bundle}-{skill}``. Matched only when the flat name resolves
#: against a real skill directory, so an ordinary hyphenated word in prose
#: (``fail-closed``) is never mistaken for a notation.
_FLAT_NOTATION = re.compile(r'\b([a-z0-9][a-z0-9-]*)-([a-z0-9][a-z0-9-]*)\b')


def foundational_section(body: str) -> str | None:
    """Return the ``## Foundational Practices`` section of *body*, or ``None``.

    ``None`` means the body declares no foundational skill — an ordinary
    outcome, distinct from a block that exists but names nothing resolvable.
    The heading is located as a heading LINE, so a prose mention of the block's
    name inside another document is not read as a second declaration.
    """
    match = _FOUNDATIONAL_PRACTICES_RE.search(body)
    if match is None:
        return None
    rest = body[match.end() :]
    terminator = _SECTION_TERMINATOR.search(rest)
    return rest[: terminator.start()] if terminator else rest


def skill_exists(bundle: str, skill: str) -> bool:
    """Whether ``{bundle}/{skill}`` is a skill the marketplace actually ships."""
    return (MARKETPLACE_ROOT / bundle / 'skills' / skill / 'SKILL.md').is_file()


def resolve_notation(notation: str) -> tuple[str, str] | None:
    """Resolve a possibly-target-rewritten notation to its ``(bundle, skill)``.

    Returns ``None`` when no shipped skill matches. The ``:`` spelling is tried
    first because it is the source spelling; the flat ``-`` spelling is tried
    only when it resolves against a real skill directory, so prose containing a
    hyphenated word is not read as a notation.

    A caller receiving ``None`` must FAIL, never skip and never substitute a
    default: an unresolvable foundational-skill name is exactly the condition
    the load-or-fail-closed rule exists for, and a guard that passes on it
    inverts the rule.
    """
    if ':' in notation:
        bundle, _, skill = notation.partition(':')
        if skill_exists(bundle, skill):
            return bundle, skill
        return None
    match = _FLAT_NOTATION.fullmatch(notation)
    if match is None:
        return None
    for split in range(len(notation) - 1, 0, -1):
        if notation[split] != '-':
            continue
        bundle, skill = notation[:split], notation[split + 1 :]
        if skill_exists(bundle, skill):
            return bundle, skill
    return None


def extract_foundational_notations(body: str) -> set[str]:
    """Return every skill notation the body's foundational block names.

    Only the block is read, so a notation appearing elsewhere in the body — in a
    cross-reference, an example, a retirement note — is not mistaken for a
    declaration. Every spelling the targets emit is collected, and the caller
    resolves each one, because a body that mixes spellings is not a defect worth
    failing on while the resolution question is still open.
    """
    section = foundational_section(body)
    if section is None:
        return set()
    found = {f'{bundle}:{skill}' for bundle, skill in _COLON_NOTATION.findall(section)}
    # ``findall`` on a two-group pattern yields TUPLES, so the joined name is
    # rebuilt here rather than the match object — a tuple leaking into the
    # returned set would reach ``resolve_notation`` as a non-string and fail
    # there instead of here, a long way from the cause.
    found |= {
        joined
        for bundle, skill in _FLAT_NOTATION.findall(section)
        if (joined := f'{bundle}-{skill}') and resolve_notation(joined) is not None
    }
    return found
