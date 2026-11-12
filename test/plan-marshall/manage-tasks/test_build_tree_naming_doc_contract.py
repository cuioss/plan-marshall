#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The prose and the pins say the same thing about a build row's tree.

The recorder hashes the plan's worktree root, the freshness gate matches on the
root the row recorded and on the row's two hashes, and the build-server client's
replies name the tree they built. Three documents state that behaviour — the
recorder's own prose in the executor template, the gate's section in
``manage-tasks/SKILL.md``, and the client's section in
``build-server-client/SKILL.md`` — and each statement is pinned here.

Every pin reads the REAL document, inside the SECTION that states the behaviour,
and each carries a planted-copy control: the document with the pinned sentence
replaced by the wording the change retired must fail. A pin that only looked for
a token somewhere in the file could not fail that way, because the rest of the
file still names the token — which is exactly the weakness the controls close.
"""

from __future__ import annotations

import pytest

from conftest import PROJECT_ROOT, get_skill_dir

_SKILLS = get_skill_dir('plan-marshall', 'manage-tasks').parent

#: The sentence the change retired from the client's interaction-logging section.
#: Quoted exactly as the document carried it.
_RETIRED_PLAN_LESS_SILENCE = 'A plan-less build is silent by design.'

#: The wording the recorder's docstring used to describe its hash root.
_RETIRED_CWD_HASH = "against the executor's cwd"


def _doc(*parts: str):
    return _SKILLS.joinpath(*parts)


class _Pin:
    """One pinned document statement, with the control's planted sentence."""

    def __init__(self, *, label: str, path, marker: str, snippet: str, retired: str) -> None:
        self.label = label
        self.path = path
        self.marker = marker
        self.snippet = snippet
        self.retired = retired


#: How far past the marker the snippet may sit. Wide enough for a section, narrow
#: enough that a sentence in a LATER section cannot satisfy this one.
_WINDOW = 6000


_PINS = (
    _Pin(
        label='executor template — the row names the root and both hashes',
        path=PROJECT_ROOT
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'tools-script-executor'
        / 'templates'
        / 'execute-script.py.template',
        marker='The row names the tree it hashed',
        snippet="the tree's hash BEFORE the build ran",
        retired=_RETIRED_CWD_HASH,
    ),
    _Pin(
        label='manage-tasks/SKILL.md — the recorder and the gate hash one root',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker="**The hash is computed against the plan's worktree root",
        snippet="same root's hash captured BEFORE the build ran",
        retired='The hash is computed against whatever directory the build process happened to run in.',
    ),
    _Pin(
        label='manage-tasks/SKILL.md — a rewriting build is named, with its remedy',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker='| `worktree_rewritten_by_build` | Rows carry this sha',
        snippet='Commit the rewrite and re-run.',
        retired='Re-run the build.',
    ),
    _Pin(
        label='manage-tasks/SKILL.md — a row hashed against another root is named',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker='| `worktree_root_mismatch` | Rows carry this sha',
        snippet="Re-dispatch the build against this plan's tree",
        retired='Re-run the build.',
    ),
    _Pin(
        label='build-server-client/SKILL.md — both replies name the built tree',
        path=_doc('build-server-client', 'SKILL.md'),
        marker='### Both replies name the tree they built',
        snippet='`wait` states the SAME three',
        retired=_RETIRED_PLAN_LESS_SILENCE,
    ),
    _Pin(
        label='build-server-client/SKILL.md — a plan-less submit leaves a trace',
        path=_doc('build-server-client', 'SKILL.md'),
        marker='- **Plan-less builds are traced, not silent.**',
        snippet='GLOBAL work log',
        retired=_RETIRED_PLAN_LESS_SILENCE,
    ),
)


def _states(text: str, marker: str, snippet: str) -> bool:
    """Whether the section opened by ``marker`` carries ``snippet``."""
    start = text.find(marker)
    if start < 0:
        return False
    return snippet in text[start : start + _WINDOW]


@pytest.mark.parametrize('pin', _PINS, ids=[pin.label for pin in _PINS])
def test_each_document_states_the_pinned_behaviour(pin: _Pin) -> None:
    """A document that drifts away from the pinned statement fails HERE."""
    assert pin.path.is_file(), f'{pin.label}: {pin.path} is missing'
    assert _states(pin.path.read_text(encoding='utf-8'), pin.marker, pin.snippet), (
        f'{pin.label}: the section opened by {pin.marker!r} does not carry {pin.snippet!r}'
    )


@pytest.mark.parametrize('pin', _PINS, ids=[pin.label for pin in _PINS])
def test_a_planted_copy_of_the_retired_wording_fails_every_pin(pin: _Pin) -> None:
    """Mutation control per pin: replace the sentence, the pin must go red.

    The mutation substitutes the retired wording for the pinned sentence, so the
    control proves the pin is anchored to the statement rather than to a token
    that happens to appear elsewhere in the same document.
    """
    text = pin.path.read_text(encoding='utf-8')
    assert _states(text, pin.marker, pin.snippet), f'{pin.label}: nothing pinned to mutate'

    planted = text.replace(pin.snippet, pin.retired)
    assert planted != text, f'{pin.label}: the pinned sentence is absent — the control would be vacuous'
    assert not _states(planted, pin.marker, pin.snippet), (
        f'{pin.label}: a planted copy of the retired wording still passes — the pin is too loose'
    )


def test_no_document_still_describes_the_plan_less_submit_as_silent() -> None:
    """The retired claim is gone from the whole marketplace tree, not only its section.

    The client's interaction-logging section stated plan-less silence twice — the
    bullet and its closing sentence — so a section-scoped pin alone could pass
    while the other statement kept the old behaviour alive.
    """
    offenders = [
        path.relative_to(_SKILLS).as_posix()
        for path in sorted(_SKILLS.rglob('*.md'))
        if _RETIRED_PLAN_LESS_SILENCE in path.read_text(encoding='utf-8')
    ]

    assert offenders == [], f'the retired plan-less-silence claim survives in: {offenders}'
