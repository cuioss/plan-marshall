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
replaced by the wording the change retired must fail. Two things are kept apart
there — the control proves the SECTION no longer carries the statement, and the
SECTION BOUNDARY (the next heading of the same or a higher level) is what keeps a
sentence in a LATER section from answering for this one. A control cannot prove
the absence of a duplicate elsewhere in the file (it replaces every occurrence),
so the boundary, not the control, holds that direction.
"""

from __future__ import annotations

import re

import pytest

from conftest import PROJECT_ROOT, get_skill_dir

_SKILLS = get_skill_dir('plan-marshall', 'manage-tasks').parent

#: A markdown heading line. Only a `.md` document is treated as sectioned: the
#: executor template is Python source, where a ``# …`` line is a comment, not a
#: heading, and bounding a docstring pin at the next comment would measure
#: nothing real.
_HEADING = re.compile(r'^(#{1,6})\s', re.MULTILINE)

#: The sentence the change retired from the client's interaction-logging section.
#: The document carried it in BOLD, and the needle is the bare sentence so an
#: emphasised or unemphasised copy is caught alike. A reworded variant (a singular
#: verb, a different noun) is a DIFFERENT sentence and is not what this sweep
#: claims to catch.
_RETIRED_PLAN_LESS_SILENCE = 'Plan-less builds are silent by design.'

#: The sentence the parent document carried, verbatim: the exact wording a planted
#: control uses, so the mutation reproduces the retired claim rather than a
#: paraphrase of it.
_PARENT_PLAN_LESS_SILENCE = '**Plan-less builds are silent by design.**'

#: The wording the recorder's docstring used to describe its hash root.
_RETIRED_CWD_HASH = "against the executor's cwd"


def _doc(*parts: str):
    return _SKILLS.joinpath(*parts)


class _Pin:
    """One pinned document statement, with the control's planted sentence.

    ``retired_provenance`` says what the control CLAIMS about history:

    * ``parent`` — the retired wording is quoted from the document as it stood
      BEFORE the PLAN-LB-146 change, recorded in ``_PARENT_WORDING`` and checked
      against it;
    * ``planted`` — the control makes NO history claim. The substituted text is a
      mutation planted to prove the pin is section-scoped, whether or not some
      earlier revision of the document happened to contain it.
    """

    def __init__(
        self,
        *,
        label: str,
        path,
        marker: str,
        snippet: str,
        retired: str,
        retired_provenance: str = 'planted',
    ) -> None:
        self.label = label
        self.path = path
        self.marker = marker
        self.snippet = snippet
        self.retired = retired
        self.retired_provenance = retired_provenance


#: How far past the marker the snippet may sit in a document with NO headings to
#: bound it (the executor template is Python source). In a markdown document the
#: SECTION boundary is the bound instead, so a short section cannot reach into
#: the next one. The pins in `_PINS` all resolve to a section.
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
        retired_provenance='parent',
    ),
    _Pin(
        label='executor template — its module docstring states the same schema',
        path=PROJECT_ROOT
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'tools-script-executor'
        / 'templates'
        / 'execute-script.py.template',
        marker='Runtime side-effects:',
        snippet='worktree_sha_at_dispatch',
        retired='worktree_sha (the working-tree currency hash), log_file',
    ),
    _Pin(
        label='manage-tasks/SKILL.md — a build that recorded no tree is named',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker="| `build_tree_unrecorded` | THIS PLAN's NEWEST `kind=build` row records",
        snippet='Establish whether the tree would not resolve',
        retired='Re-run the build.',
    ),
    _Pin(
        label='manage-tasks/SKILL.md — the recorder and the gate hash one tree',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker='**The hash is computed against the tree the wrapped build ran in',
        snippet='from the `--project-dir` the wrapper builds in',
        retired='The hash is computed against whatever directory the build process happened to run in.',
    ),
    _Pin(
        label='manage-tasks/SKILL.md — absent and null say different things',
        path=_doc('manage-tasks', 'SKILL.md'),
        marker='**Absent and null say different things',
        snippet='recorded nothing about the tree',
        retired='both optional and None for a row written before they existed',
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
        label='manage-change-ledger/SKILL.md — the pair is read by presence',
        path=_doc('manage-change-ledger', 'SKILL.md'),
        marker='read by **presence**',
        snippet='a writer that recorded nothing about the tree omits BOTH',
        retired='both optional and `None` for a row written before they existed',
    ),
    _Pin(
        label='build-server-client/SKILL.md — both replies name the built tree',
        path=_doc('build-server-client', 'SKILL.md'),
        marker='### Both replies name the tree they built',
        snippet='`wait` states the SAME three',
        retired=_PARENT_PLAN_LESS_SILENCE,
    ),
    _Pin(
        label='build-server-client/SKILL.md — a plan-less submit leaves a trace',
        path=_doc('build-server-client', 'SKILL.md'),
        marker='- **Every plan-less outcome is traced, not silent.**',
        snippet='GLOBAL work log',
        retired=_PARENT_PLAN_LESS_SILENCE,
    ),
)


#: The parent's own wording, recorded from the commit that retired it, per pin
#: label. Only a pin whose control QUOTES history belongs here; a control that
#: substitutes a line the parent never held is labelled ``planted`` on the pin and
#: is deliberately absent — see
#: ``test_every_retired_string_is_parent_text_or_labelled_a_planted_mutation``.
_PARENT_WORDING: dict[str, str] = {
    'executor template — the row names the root and both hashes': (
        ":func:`compute_worktree_sha` against the executor's cwd (pinned to the\n"
        '    worktree in phase-5, the main checkout otherwise)'
    ),
}


def _section_span(text: str, marker: str, *, heading_bounded: bool) -> tuple[int, int] | None:
    """Return the span of the SECTION that carries ``marker``, or ``None``.

    In a markdown document the span runs from the nearest heading at or before
    the marker to the next heading of the same or a higher level, so a sentence
    in a LATER section can never answer for an earlier one — which a flat
    character window cannot promise, because a short section ends before the
    window does. A document with no headings to bound it (the executor template
    is Python source) falls back to a ``_WINDOW``-character span, and that
    fallback is the weaker guarantee.
    """
    start = text.find(marker)
    if start < 0:
        return None
    if not heading_bounded:
        return start, min(len(text), start + _WINDOW)
    heading_level: int | None = None
    heading_start = start
    for match in _HEADING.finditer(text):
        if match.start() > start:
            break
        heading_level = len(match.group(1))
        heading_start = match.start()
    if heading_level is None:
        return start, min(len(text), start + _WINDOW)
    for match in _HEADING.finditer(text, start + 1):
        if len(match.group(1)) <= heading_level:
            return heading_start, match.start()
    return heading_start, len(text)


def _states(text: str, marker: str, snippet: str, *, heading_bounded: bool) -> bool:
    """Whether the SECTION opened by ``marker`` carries ``snippet``."""
    span = _section_span(text, marker, heading_bounded=heading_bounded)
    if span is None:
        return False
    return snippet in text[span[0] : span[1]]


def _pin_states(pin: _Pin, text: str) -> bool:
    """Whether ``text`` carries ``pin``'s statement in ``pin``'s own section."""
    return _states(text, pin.marker, pin.snippet, heading_bounded=pin.path.suffix == '.md')


@pytest.mark.parametrize('pin', _PINS, ids=[pin.label for pin in _PINS])
def test_each_document_states_the_pinned_behaviour(pin: _Pin) -> None:
    """A document that drifts away from the pinned statement fails HERE."""
    assert pin.path.is_file(), f'{pin.label}: {pin.path} is missing'
    assert _pin_states(pin, pin.path.read_text(encoding='utf-8')), (
        f'{pin.label}: the section opened by {pin.marker!r} does not carry {pin.snippet!r}'
    )


@pytest.mark.parametrize('pin', _PINS, ids=[pin.label for pin in _PINS])
def test_a_planted_copy_of_the_retired_wording_fails_every_pin(pin: _Pin) -> None:
    """Mutation control per pin: replace the sentence, the pin must go red.

    The mutation substitutes the retired wording for every occurrence of the
    pinned sentence, so the control proves the SECTION stops carrying it. It
    cannot detect a duplicate elsewhere in the file, and does not claim to: the
    SECTION BOUNDARY is what keeps a later section from answering for this one.
    """
    text = pin.path.read_text(encoding='utf-8')
    assert _pin_states(pin, text), f'{pin.label}: nothing pinned to mutate'

    planted = text.replace(pin.snippet, pin.retired)
    assert planted != text, f'{pin.label}: the pinned sentence is absent — the control would be vacuous'
    assert not _pin_states(pin, planted), (
        f'{pin.label}: a planted copy of the retired wording still passes — the pin is too loose'
    )


def _shipped_documents() -> dict[str, str]:
    """Every markdown document the marketplace ships, keyed by repo-relative path."""
    marketplace = PROJECT_ROOT / 'marketplace'
    return {
        path.relative_to(PROJECT_ROOT).as_posix(): path.read_text(encoding='utf-8')
        for path in sorted(marketplace.rglob('*.md'))
    }


def _documents_carrying(sentence: str, documents: dict[str, str]) -> list[str]:
    """The documents in ``documents`` that still carry ``sentence``."""
    return [name for name, text in sorted(documents.items()) if sentence in text]


def test_no_document_still_describes_the_plan_less_submit_as_silent() -> None:
    """The retired claim is gone from the whole MARKETPLACE tree, not one bundle.

    The client's interaction-logging section stated plan-less silence twice — the
    bullet and its closing sentence — so a section-scoped pin alone could pass
    while the other statement kept the old behaviour alive. The sweep therefore
    covers every bundle the marketplace ships, which is what the docstring claims.
    """
    offenders = _documents_carrying(_RETIRED_PLAN_LESS_SILENCE, _shipped_documents())

    assert offenders == [], f'the retired plan-less-silence claim survives in: {offenders}'


def test_the_sweep_catches_a_planted_copy_of_the_parents_sentence() -> None:
    """Mutation control for the sweep: plant the PARENT's sentence, it is found.

    The sweep is the one check here that reads the whole tree, so a sweep searching
    a sentence no document ever carried would pass on every real tree while
    catching nothing at all. The planted copy is the parent document's own bold
    sentence, which is the exact wording the claim was retired in — and the needle
    is the bare sentence, so either spelling is caught.
    """
    documents = _shipped_documents()
    target = 'marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md'
    assert _documents_carrying(_RETIRED_PLAN_LESS_SILENCE, documents) == [], (
        'the shipped tree is not clean, so this control would be vacuous'
    )

    documents[target] = documents[target] + '\n' + _PARENT_PLAN_LESS_SILENCE + '\n'

    assert _documents_carrying(_RETIRED_PLAN_LESS_SILENCE, documents) == [target]


@pytest.mark.parametrize('pin', _PINS, ids=[pin.label for pin in _PINS])
def test_every_retired_string_is_parent_text_or_labelled_a_planted_mutation(pin: _Pin) -> None:
    """A control's ``retired`` string either QUOTES the parent or says it does not.

    A mutation control that substitutes wording the document never held proves less
    than it appears to: it shows the pin is section-scoped, not that the document
    stopped making the retired claim. Every pin therefore declares where its
    retired wording came from, and each one that claims history is checked against
    the parent wording recorded here.
    """
    assert pin.retired_provenance in {'parent', 'planted'}, pin.label
    if pin.retired_provenance == 'planted':
        return
    assert pin.label in _PARENT_WORDING, f'{pin.label}: the pin claims parent provenance but records no parent wording'
    parent_text = _PARENT_WORDING[pin.label]
    assert pin.retired in parent_text, (
        f'{pin.label}: the retired string {pin.retired!r} is absent from the parent '
        f'wording this pin records ({parent_text!r}) — label it a planted mutation '
        'instead of presenting it as history'
    )


def test_no_pin_is_labelled_a_history_quote_without_recording_one() -> None:
    """The provenance table holds exactly the pins that claim it — no dead entries."""
    declared_parent = {pin.label for pin in _PINS if pin.retired_provenance == 'parent'}

    assert declared_parent == set(_PARENT_WORDING), (
        f'pins claiming parent provenance: {sorted(declared_parent)}; recorded parent '
        f'wording: {sorted(_PARENT_WORDING)}'
    )
