#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-closure check for the lessons-store resolution audit.

Case (d) of the fail-open regression suite: assert that every site which
actually resolves the lessons-learned store carries a disposition row in
``manage-lessons/standards/cwd-keyed-store-resolution-audit.md``.

**The population is derived from the STORE, not from a roster.** This is the
load-bearing property, not an implementation detail. A roster-derived
population — "the manage-lessons verbs", "the finalize steps" — is closed under
the roster, so it excludes by construction any resolver living outside it. Such
a check would have reported this very surface clean while
``manage-status/scripts/_cmd_lifecycle.py`` sat outside the roster carrying all
three failure directions. Deriving from the declaring source instead (resolver
call sites, the shared constant, and the bare quoted literal) makes the
population closed under the store, which is the thing the audit is about.

The check publishes the derived population size and asserts it is non-empty, so
it can never pass vacuously from an empty population; and it asserts
``_cmd_lifecycle.py`` is a member as a negative-control anchor proving the
derivation reaches outside the ``manage-lessons`` skill.

The path heuristics, sweep patterns, and per-site dispositions are NOT copied
here — see
``marketplace/bundles/plan-marshall/skills/manage-lessons/standards/cwd-keyed-store-resolution-audit.md``,
which is the single home for that enforcement-critical content.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines

from conftest import MARKETPLACE_ROOT

#: The audit standard whose disposition table the derived population is checked against.
_AUDIT_STANDARD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-lessons'
    / 'standards'
    / 'cwd-keyed-store-resolution-audit.md'
)

#: The section holding one ``### {path}`` heading per dispositioned member.
_DISPOSITIONS_HEADING = '## Dispositions'

#: The three derivation arms, mirroring the audit standard's own sweeps.
#:
#: Arm 1 names BOTH canonical resolvers deliberately. ``resolve_lesson_store``
#: is the migration target, so an arm watching only ``get_lessons_dir`` would
#: stop covering precisely the consumers a migration just fixed — the same
#: population-erasure trap the audit's roster critique describes.
#:
#: Arm 3 matches the QUOTED literal only. An unquoted ``lessons-learned`` in a
#: docstring or comment resolves nothing; requiring the quotes is what keeps
#: prose mentions out of the population without hand-listing exclusions.
_DERIVATION_ARMS = (
    re.compile(r'\b(?:get_lessons_dir|resolve_lesson_store)\b'),
    re.compile(r'\bDIR_LESSONS\b'),
    re.compile(r"""['"]lessons-learned['"]"""),
)

#: Negative-control anchor: a member that lives OUTSIDE the manage-lessons
#: skill. Its presence proves the derivation is closed under the store rather
#: than under the skill directory.
_OUTSIDE_SKILL_ANCHOR = 'manage-status/scripts/_cmd_lifecycle.py'


def _derive_population() -> list[str]:
    """Return every marketplace script that resolves the lessons-learned store.

    Walks the real ``marketplace/bundles/**/scripts/**/*.py`` tree and keeps a
    file when any derivation arm matches its text. Returns repo-relative
    POSIX paths, sorted, so the population is deterministic.
    """
    members: set[str] = set()
    repo_root = MARKETPLACE_ROOT.parent.parent
    for path in MARKETPLACE_ROOT.rglob('*.py'):
        if '__pycache__' in path.parts or 'scripts' not in path.parts:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            # An unreadable file is a coverage gap, not an absence — fail loudly
            # rather than silently shrinking the population.
            raise AssertionError(f'Could not read candidate script: {path}') from None
        if any(arm.search(text) for arm in _DERIVATION_ARMS):
            members.add(path.relative_to(repo_root).as_posix())
    return sorted(members)


def _dispositioned_paths() -> list[str]:
    """Return the ``### {path}`` heading of every row in the audit's Dispositions section."""
    text = _AUDIT_STANDARD.read_text(encoding='utf-8')
    lines = section_lines(text, _DISPOSITIONS_HEADING, stop_prefixes=('## ',))
    return [line.strip()[4:].strip() for line in lines if line.startswith('### ')]


def test_audit_standard_exists():
    """The audit standard the population is checked against must exist."""
    assert _AUDIT_STANDARD.is_file(), f'Missing audit standard: {_AUDIT_STANDARD}'


def test_derived_population_is_non_empty_and_published():
    """The population is non-empty, and its size is published in the failure message.

    A closure check over an empty population passes vacuously — it would report
    "every member is dispositioned" while ranging over nothing. Publishing the
    size is what makes that failure mode visible instead of silent.
    """
    population = _derive_population()
    assert population, (
        'Derived lessons-store population is EMPTY — the derivation arms matched '
        'nothing, so the closure check below would pass vacuously.'
    )
    assert len(population) >= 3, (
        f'Derived population size: {len(population)} — implausibly small for the '
        f'lessons-store surface, which suggests a broken derivation arm rather '
        f'than a genuinely narrow surface. Members: {population}'
    )


def test_derivation_reaches_outside_the_manage_lessons_skill():
    """``_cmd_lifecycle.py`` is in the population — the negative-control anchor.

    This is the site a roster-derived population omitted by construction. If it
    ever drops out of the derived set, the derivation has silently re-acquired
    the blind spot the audit exists to close.
    """
    population = _derive_population()
    assert any(member.endswith(_OUTSIDE_SKILL_ANCHOR) for member in population), (
        f'Negative-control anchor {_OUTSIDE_SKILL_ANCHOR!r} is absent from the '
        f'derived population of {len(population)} member(s): {population}. The '
        f'derivation is no longer closed under the store.'
    )


def test_every_derived_member_carries_a_disposition_row():
    """Every derived store-resolution site is dispositioned in the audit standard.

    Matching is by path SUFFIX because the audit's headings are skill-relative
    (``manage-status/scripts/_cmd_lifecycle.py``) while the derivation yields
    repo-relative paths. The audit may carry MORE rows than the derivation
    yields — prose-only and already-fail-closed members are recorded there as
    first-class JUSTIFY evidence — so the assertion is containment, not equality.
    """
    population = _derive_population()
    dispositioned = _dispositioned_paths()
    assert dispositioned, (
        f'No "### " disposition rows found under {_DISPOSITIONS_HEADING!r} in '
        f'{_AUDIT_STANDARD} — the closure check has nothing to range over.'
    )

    undispositioned = [
        member
        for member in population
        if not any(member.endswith(heading) for heading in dispositioned)
    ]
    assert not undispositioned, (
        f'{len(undispositioned)} of {len(population)} derived store-resolution '
        f'site(s) carry no disposition row in the audit standard:\n  '
        + '\n  '.join(undispositioned)
        + f'\nDispositioned rows ({len(dispositioned)}): {dispositioned}'
    )
