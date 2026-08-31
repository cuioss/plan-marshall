#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the named `.plan/marshal.json` recovery case in the planning workflow docs.

Plan ``truthful-signals/210-named-recovery-discards-operator-config``.

Three workflow-doc blocks instructed the orchestrator, when a post-dispatch
clean-main assertion reports ``.plan/marshal.json`` dirty, to emit
``Recovery: git checkout -- .plan/marshal.json`` — justified by the claim that
restoring the file from HEAD "is always safe". The justification is a non
sequitur: the clean-main guard establishes only that *the dispatched phase* did
not write the file, not that nobody did. The likeliest author of a dirty
``marshal.json`` in the main checkout is the **operator**, and ``git checkout --``
destroys uncommitted, unstaged edits irrecoverably (no reflog covers a worktree
file). The recovery must instead inspect the diff and require an explicit
operator disposition before any discard.

These tests assert the *derivation* of the assertion class, not a hard-coded
enumeration of the three known sites — pinning only the known sites would
re-create the sample-as-population error this plan exists to prevent. The
population is derived by **assertion shape** (the named-recovery heading for
``.plan/marshal.json``) swept across the directories named in ``SWEPT_DIRS``, so
a new phase boundary that adds such a block under one of them is covered
automatically.

Test-to-deliverable map:

* ``test_named_recovery_never_instructs_unconditional_discard`` — D3(a): no
  derived region instructs an unconditional discard, EVERY derived region is
  inspection-first, and no "always safe" justification survives.
* ``test_named_recovery_inspection_first_population_nonempty_and_covers_known_members``
  — D3(b): the derived population of inspection-first sites is asserted
  non-empty and covers the known members (planning.md + both
  planning-outline.md boundaries). A non-vacuous control proves the sweep
  examined a populated surface, so the non-empty assertion cannot pass on an
  empty sweep.
* ``test_named_recovery_contract_is_a_single_authority`` — D2: the contract
  exists as ONE authority the other sites reference, not as three drifting
  copies.
* ``test_worktree_handling_destructive_instructions_are_inspection_first``
  — D3(b): the section-wise sibling assertion over ``worktree-handling.md``,
  whose § "Recovery Loop" carries a ``###`` heading and so is not matched by the
  ``**Named recovery case —`` shape the sweep above derives. It publishes its own
  denominator and asserts the destructive-section set non-empty, so it cannot
  pass over a surface it failed to read. It is also the matched NEGATIVE control
  for the qualifier: the shipped § "Recovery Loop" inspects content before it
  discards, so it must keep passing.
* ``test_destructive_qualifier_rejects_only_the_named_defect`` — D3(b): the
  matched POSITIVE controls for the qualifier. Each isolates ONE defect while
  satisfying every other clause — a diff that surfaces only paths (under either
  spelling of the flag that suppresses content), a discard placed ahead of the
  diff, a diff of a path other than the one destroyed, and a second discard no
  diff ever inspected. The repaired twin of each is asserted to pass, which is
  what attributes the rejection to that defect rather than to a clause the
  control happened to omit.
"""

from __future__ import annotations

import re

import pytest

from conftest import MARKETPLACE_ROOT

WORKFLOW_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow'
)

#: The layer-D recovery document lives here, NOT under the planning workflow
#: directory. A population-derived guard whose population is drawn from the wrong
#: directory set is the shrunk-population failure mode — the sweep looks total
#: while the surface it never reaches carries the defect.
WORKTREE_STANDARDS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'workflow-integration-git' / 'standards'
)

#: Every directory the named-recovery heading sweep covers.
SWEPT_DIRS = (WORKFLOW_DIR, WORKTREE_STANDARDS_DIR)

#: The layer-D recovery document, swept directly by the sibling assertion.
WORKTREE_HANDLING = WORKTREE_STANDARDS_DIR / 'worktree-handling.md'

#: The stable assertion-shape identifier for a named-recovery site. Derivation
#: keys on this heading, not on a command string — the command is exactly the
#: thing the fix removes, so a command-string sweep would report the class
#: "closed" the moment the fix lands.
HEADING_MARKER = 'Named recovery case — `.plan/marshal.json`'

#: The region owned by one named-recovery contract ends at the next unrelated
#: bold directive or markdown heading. The region deliberately extends past the
#: recovery block through its ``**Cross-references**`` sub-section, so an
#: "always"-flavoured justification in a cross-reference bullet is in scope too.
_REGION_BOUNDARY = re.compile(r'^(#{2,6}\s|\*\*Metrics\*\*|\*\*Phase handshake|\*\*Step\s)')

#: The destructive form: any ``git checkout``/``git restore`` aimed at the
#: operator's file, under ANY lead-in. The former pattern required a literal
#: ``Recovery:`` prefix, so a block that issued the same command under different
#: wording carried the identical hazard and matched nothing.
_UNCONDITIONAL_DISCARD = re.compile(r'git (?:checkout|restore)\b[^\n`]*\.plan/marshal\.json')

#: Any concrete ``git diff`` inspection command aimed at ``.plan/marshal.json``.
#: Widened from the single literal ``git diff -- .plan/marshal.json`` so a
#: restatement cannot evade the single-authority test merely by dropping the
#: ``--`` separator or adding an option. ``[^\n`]*`` keeps the match inside one
#: contiguous command span, so prose that merely names ``git diff`` in one code
#: span and the path in another does not read as an inspection command.
_INSPECTION_COMMAND = re.compile(r'git diff\b[^\n`]*\.plan/marshal\.json')

#: A destructive discard aimed at ANY path, not only ``marshal.json``. The
#: layer-D recovery loop reverts ``{path}``, so the marshal.json-keyed pattern
#: above cannot see it. The ``operands`` group captures the pathspec the command
#: destroys: an ordering check that cannot name its target can only ask "was
#: there a diff somewhere earlier", which a diff of an unrelated path satisfies.
#: The lead-in is non-greedy so each destructive command in a line is matched on
#: its own instead of collapsing into the last one.
_DESTRUCTIVE_ANY_PATH = re.compile(
    r'git\b[^\n`]*?\b(?:checkout\s+--|restore(?:\s+--)?)\s+(?P<operands>[^\n`]*)'
)

#: A ``git diff`` command span, captured to the end of its contiguous span so the
#: flags the command carries are part of the match. ``[^\n`]*`` on both sides keeps
#: the span inside one code span, so prose naming ``git diff`` in one span and a
#: flag in another is never read as a single command. ``operands`` captures
#: everything after the ``diff`` verb — where both the mode flags and the
#: pathspec live.
_DIFF_COMMAND_SPAN = re.compile(r'git\b[^\n`]*?\bdiff\b(?P<operands>[^\n`]*)')

#: Diff modes that surface only PATHS or counts, never content. A section whose
#: sole inspection command is one of these satisfies the letter of "run a diff"
#: while leaving the reader unable to see what they are about to destroy, so it
#: does not count as content inspection. The lookarounds keep ``-s`` from matching
#: inside ``--stat``/``--shortstat``/``--name-status``.
#:
#: The set is derived by sweeping git-diff's output-mode options rather than by
#: patching the one spelling a reviewer happened to name: a list that rejects a
#: flag while admitting its documented synonym has the same hole it claims to
#: close, and one named instance is a sample, not the population. The sweep's two
#: findings, both of which the enumeration had missed:
#:
#: * ``--no-patch`` — git's own long synonym for the listed ``-s``. It was the
#:   only synonym gap, because ``-s`` was the only short flag enumerated; every
#:   other listed mode has no alternate spelling.
#: * the ``--dirstat`` family (``--dirstat``, its ``-X`` short form, and the
#:   ``--cumulative`` / ``--dirstat-by-file`` parameter aliases) and
#:   ``--compact-summary`` — same defect class, absent from the list entirely
#:   rather than as a synonym of a member.
#:
#: Width modifiers (``--stat-width`` and friends) are deliberately absent: they
#: qualify a mode rather than select one, and never appear without it.
_METADATA_ONLY_DIFF = re.compile(
    r'(?<![\w-])'
    r'(?:'
    r'--name-only|--name-status|--numstat|--shortstat|--stat'
    r'|--compact-summary|--summary|--raw|--quiet'
    r'|--dirstat-by-file|--dirstat|--cumulative|-X'
    r'|--no-patch|-s'
    r')'
    r'(?![\w-])'
)

#: Wording that presents a destructive revert as the DEFAULT disposition rather
#: than one an operator must choose. ``(typical case)`` was the shipped form.
_REVERT_PRESUMED_DEFAULT = re.compile(r'typical case|usual case', re.IGNORECASE)

#: Section boundaries in a standards document: any markdown ATX heading.
_MD_HEADING = re.compile(r'^#{1,6}\s')

#: The cross-reference that points at the single authority — accepted as a
#: ``- `` bullet or as an inline ``§`` citation, since both are pointers.
_AUTHORITY_POINTER = re.compile(
    r'`plan-marshall:plan-marshall/workflow/planning\.md`\s*§\s*"Named recovery case'
)

#: The operator-disposition enumeration that only the authority may carry.
#: Keyed on BOTH dispositions appearing as list items: naming the operator's two
#: choices IS the contract, so a site carrying both has restated it.
_DISPOSITION_KEEP = re.compile(r'^\s*[-*]\s+\**Keep\**\s*[—:-]', re.MULTILINE)
_DISPOSITION_DISCARD = re.compile(r'^\s*[-*]\s+\**Discard\**\s*[—:-]', re.MULTILINE)


def _derive_named_recovery_regions() -> list[tuple]:
    """Sweep every swept directory for named ``.plan/marshal.json`` recovery blocks.

    Returns a list of ``(path, region_text, heading_lineno)`` — the derived
    population. Empty return is a real signal (the class moved or vanished),
    never silently treated as "clean".

    The sweep covers :data:`SWEPT_DIRS`, which includes the
    ``workflow-integration-git/standards`` directory the layer-D recovery
    document lives in. That widening does NOT by itself cover the layer-D
    recovery loop: it is headed ``### Recovery Loop``, while this derivation
    keys on the ``**Named recovery case`` marker, so the heading shapes do not
    match. It is done so the population is correct for any future
    ``**Named recovery case —``-marked region added under that directory;
    :func:`test_worktree_handling_destructive_instructions_are_inspection_first`
    is what covers the layer-D loop today.
    """
    regions: list[tuple] = []
    for directory in SWEPT_DIRS:
        for md in sorted(directory.glob('*.md')):
            lines = md.read_text(encoding='utf-8').splitlines()
            for i, line in enumerate(lines):
                if HEADING_MARKER in line and line.lstrip().startswith('**Named recovery case'):
                    block = [line]
                    for j in range(i + 1, min(i + 40, len(lines))):
                        if _REGION_BOUNDARY.match(lines[j]):
                            break
                        block.append(lines[j])
                    regions.append((md, '\n'.join(block), i + 1))
    return regions


def _has_unconditional_discard_directive(text: str) -> bool:
    return bool(_UNCONDITIONAL_DISCARD.search(text))


def _has_always_safety_claim(text: str) -> bool:
    low = text.lower()
    return 'always safe' in low or 'always a spurious' in low


def _is_inspection_first(text: str) -> bool:
    """A region that mandates inspection and an explicit operator disposition
    before any discard, and carries no "always safe" justification.

    The destructive-command signature is deliberately NOT part of this test.
    Once ``_UNCONDITIONAL_DISCARD`` was broadened to match the command under any
    lead-in it also matches the authority's own *cautionary* mention ("...would
    destroy those edits irrecoverably"), so folding it in here would make the
    property unsatisfiable for the one region that states the contract. The two
    are combined at the offender rule instead: carrying the command is an
    offence only where the region does not also mandate inspection-then-
    disposition.
    """
    low = text.lower()
    return (
        ('inspect' in low or 'git diff' in low)
        and 'operator' in low
        and ('disposition' in low or 'confirm' in low or 'decide' in low)
        and not _has_always_safety_claim(text)
    )


def _is_authority(text: str) -> bool:
    """Only the single authority carries a concrete ``git diff`` inspection
    command against ``marshal.json``. The reference sites point to it instead."""
    return bool(_INSPECTION_COMMAND.search(text))


def _restates_contract(text: str) -> bool:
    """Whether ``text`` carries the operator-disposition enumeration.

    Structural by design rather than a line or character budget: a budget needs
    a threshold nobody can settle, and drifts as the prose is edited. Carrying
    both ``Keep`` and ``Discard`` as list items IS the contract.
    """
    return bool(_DISPOSITION_KEEP.search(text)) and bool(_DISPOSITION_DISCARD.search(text))


def _references_authority(text: str) -> bool:
    """Whether a non-authority region DEFERS to the authority rather than restating it.

    Replaces the former ``'planning.md' in low and 'named recovery' in low``
    heuristic, which a full restatement satisfies just as easily as a pointer:
    the region heading makes the second term true by construction, and any
    restatement that names its source makes the first true. Deference is now
    two-sided — an explicit pointer to the authority section MUST be present,
    and the operator-disposition enumeration MUST NOT.
    """
    return bool(_AUTHORITY_POINTER.search(text)) and not _restates_contract(text)


def _derive_document_sections(path) -> list[tuple[str, int, str]]:
    """Split ``path`` into ``(heading, heading_lineno, section_text)`` by ATX heading."""
    lines = path.read_text(encoding='utf-8').splitlines()
    starts = [i for i, line in enumerate(lines) if _MD_HEADING.match(line)]
    return [
        (
            lines[start].strip(),
            start + 1,
            '\n'.join(lines[start : (starts[n + 1] if n + 1 < len(starts) else len(lines))]),
        )
        for n, start in enumerate(starts)
    ]


def _command_paths(operands: str) -> set[str]:
    """The pathspec operands of a git command tail.

    Tokens after an explicit ``--`` separator are paths by definition. Without a
    separator the non-flag tokens are the candidates, which can over-collect (a
    revision in ``git diff HEAD`` reads as a path) — deliberately, because that
    error direction NARROWS what a diff is credited with covering. Crediting a
    diff too widely is the failure this guard exists to catch, so ambiguity
    resolves toward rejection.
    """
    tokens = operands.split()
    if '--' in tokens:
        candidates = tokens[tokens.index('--') + 1 :]
    else:
        candidates = [token for token in tokens if not token.startswith('-')]
    return {stripped for stripped in (t.strip('`*_,;:') for t in candidates) if stripped}


def _content_diff_spans(text: str) -> list[tuple[int, set[str]]]:
    """``(start offset, pathspec)`` for every diff in ``text`` that surfaces CONTENT.

    A ``git diff`` whose span carries a metadata-only mode is excluded: it prints
    paths or counts, so it cannot be the command that lets a reader see what a
    later discard would destroy.
    """
    return [
        (m.start(), _command_paths(m.group('operands')))
        for m in _DIFF_COMMAND_SPAN.finditer(text)
        if not _METADATA_ONLY_DIFF.search(m.group(0))
    ]


def _diff_covers(diff_paths: set[str], destroyed: set[str]) -> bool:
    """Whether a content diff surfaced what a destructive command destroys.

    A diff carrying no pathspec at all (``git diff``) surfaces the whole tree and
    so covers any path. Otherwise it must name one of the paths the destructive
    command targets — which also means a destructive command whose own pathspec
    could not be read is covered only by a whole-tree diff, never by a
    path-scoped one.
    """
    return not diff_paths or bool(diff_paths & destroyed)


def _inspection_precedes_disposal(text: str) -> bool:
    """Whether EVERY destructive command is preceded by a content diff of the path IT destroys.

    "Inspect, then dispose" is an ordering property, and a conjunction of
    order-free searches cannot express it: a section that reverts the path and
    only afterwards suggests reading it satisfies every clause while inverting
    the contract. Two further properties are load-bearing, and both were absent
    while this compared only the FIRST diff against the FIRST destructive match:

    * **Per target.** A section that inspected once and then discarded twice
      qualified on the strength of the first pair, leaving every later discard
      unexamined. Each destructive command is now checked on its own.
    * **Path-aware.** Neither pattern captured its operands, so diffing ``a.txt``
      and discarding ``b.txt`` read as inspect-then-dispose. The diff must now
      name the path the discard destroys (or carry no pathspec, surfacing all).

    A section with no destructive command at all is vacuously ordered, but still
    requires a content diff to exist — the qualifier is only ever applied to
    sections that carry a discard, so this cannot pass an uninspected section.
    """
    diffs = _content_diff_spans(text)
    if not diffs:
        return False
    for destructive in _DESTRUCTIVE_ANY_PATH.finditer(text):
        destroyed = _command_paths(destructive.group('operands'))
        if not any(
            offset < destructive.start() and _diff_covers(diff_paths, destroyed)
            for offset, diff_paths in diffs
        ):
            return False
    return True


def _is_destructive_instruction_qualified(text: str) -> bool:
    """Whether a section carrying a destructive discard also properly qualifies it.

    Deliberately stricter than :func:`_is_inspection_first`. The layer-D recovery
    loop already said "Inspect ``newly_dirty[]``" and "Decide per-path", so the
    generic predicate passed it while step 1 surfaced only PATHS and the revert
    bullet was labelled "(typical case)". A reader cannot dispose of content they
    have not seen, so the qualifier requires a concrete diff command that
    surfaces the change *of the path it destroys, ahead of every discard*, an
    explicit operator disposition, the irrecoverability caveat, and no wording
    presenting the revert as the default.
    """
    low = text.lower()
    return (
        _inspection_precedes_disposal(text)
        and 'operator' in low
        and ('disposition' in low or 'confirm' in low or 'decide' in low)
        and ('irrecoverab' in low or 'reflog' in low)
        and not _REVERT_PRESUMED_DEFAULT.search(text)
    )


#: Matched control pairs for :func:`_is_destructive_instruction_qualified`. Each
#: pair differs ONLY in the defect named by its id: both members carry a
#: destructive command, an operator disposition, and the irrecoverability caveat,
#: and neither presents the revert as a default. That is what makes the rejection
#: attributable to the named defect rather than to an incidentally missing clause.
#: The matched NEGATIVE control is the shipped § "Recovery Loop" section, asserted
#: by :func:`test_worktree_handling_destructive_instructions_are_inspection_first`.
_CONTROL_METADATA_ONLY_DIFF = """### Recovery (control)

1. **Surface every path in `newly_dirty[]`.**

   ```bash
   git -C {main_checkout} diff --name-only -- {path}
   ```

2. **Obtain an explicit operator disposition for that one path.**
   `git -C {main_checkout} checkout -- {path}` destroys uncommitted, unstaged
   content **irrecoverably** — no reflog covers a worktree file.
"""

_CONTROL_CONTENT_DIFF = _CONTROL_METADATA_ONLY_DIFF.replace('diff --name-only --', 'diff --')

_CONTROL_DISPOSAL_BEFORE_INSPECTION = """### Recovery (control)

1. **Revert the path.** `git -C {main_checkout} checkout -- {path}` drops the
   dirty state **irrecoverably** — no reflog covers a worktree file.
2. **Then read what was there** with `git -C {main_checkout} diff -- {path}` and
   record the operator disposition for it.
"""

_CONTROL_INSPECTION_BEFORE_DISPOSAL = """### Recovery (control)

1. **Read what is there** with `git -C {main_checkout} diff -- {path}` and
   record the operator disposition for it.
2. **Revert the path.** `git -C {main_checkout} checkout -- {path}` drops the
   dirty state **irrecoverably** — no reflog covers a worktree file.
"""

#: ``--no-patch`` is git's own long synonym for ``-s``. Differs from its repaired
#: twin ONLY in that flag, so a rejection is attributable to the synonym gap and
#: not to a metadata-only mode the control happened to pick.
_CONTROL_NO_PATCH_DIFF = _CONTROL_METADATA_ONLY_DIFF.replace(
    'diff --name-only --', 'diff --no-patch --'
)

#: Inspects one path and destroys a DIFFERENT one. Every clause of the qualifier
#: is satisfied — the diff surfaces content and precedes the discard — so the only
#: thing separating it from its repaired twin is which path the diff names.
_CONTROL_DIFFS_ONE_PATH_DISCARDS_ANOTHER = _CONTROL_INSPECTION_BEFORE_DISPOSAL.replace(
    'diff -- {path}', 'diff -- {other_path}'
)

_CONTROL_SECOND_DISCARD_UNINSPECTED = """### Recovery (control)

1. **Read what is there** with `git -C {main_checkout} diff -- {first_path}` and
   record the operator disposition for it.
2. **Revert the first path.** `git -C {main_checkout} checkout -- {first_path}`
   drops the dirty state **irrecoverably** — no reflog covers a worktree file.
3. **Revert the second path.** `git -C {main_checkout} checkout -- {second_path}`
   drops it just as irrecoverably.
"""

_CONTROL_SECOND_DISCARD_INSPECTED = """### Recovery (control)

1. **Read what is there** with `git -C {main_checkout} diff -- {first_path}` and
   record the operator disposition for it.
2. **Revert the first path.** `git -C {main_checkout} checkout -- {first_path}`
   drops the dirty state **irrecoverably** — no reflog covers a worktree file.
3. **Read the second path** with `git -C {main_checkout} diff -- {second_path}`
   and record the operator disposition for it too.
4. **Revert the second path.** `git -C {main_checkout} checkout -- {second_path}`
   drops it just as irrecoverably.
"""


@pytest.mark.parametrize(
    ('defective', 'repaired'),
    [
        (_CONTROL_METADATA_ONLY_DIFF, _CONTROL_CONTENT_DIFF),
        (_CONTROL_NO_PATCH_DIFF, _CONTROL_CONTENT_DIFF),
        (_CONTROL_DISPOSAL_BEFORE_INSPECTION, _CONTROL_INSPECTION_BEFORE_DISPOSAL),
        (_CONTROL_DIFFS_ONE_PATH_DISCARDS_ANOTHER, _CONTROL_INSPECTION_BEFORE_DISPOSAL),
        (_CONTROL_SECOND_DISCARD_UNINSPECTED, _CONTROL_SECOND_DISCARD_INSPECTED),
    ],
    ids=[
        'a-name-only-diff-surfaces-paths-not-content',
        'a-no-patch-diff-is-the-long-synonym-of-a-rejected-short-flag',
        'a-discard-ahead-of-the-diff-inverts-the-order',
        'a-diff-of-one-path-does-not-cover-a-discard-of-another',
        'a-second-discard-that-no-diff-ever-inspected',
    ],
)
def test_destructive_qualifier_rejects_only_the_named_defect(defective, repaired):
    """The qualifier rejects each isolated defect — a diff that never shows
    content (under either spelling of the suppressing flag), a discard placed
    ahead of the diff, a diff of a path other than the one destroyed, and a
    second discard nothing inspected — and accepts the repaired twin of each.

    Both halves are asserted because either alone is uninformative: a rejection
    with no matching acceptance cannot show WHICH clause fired, and an acceptance
    with no matching rejection cannot show the clause fires at all.
    """
    assert defective != repaired, (
        'the pair is identical, so the assertions below contradict each other and '
        'one must fail — a control built by string substitution whose pattern did '
        'not match produces exactly this, and would otherwise look like a real defect'
    )
    assert _DESTRUCTIVE_ANY_PATH.search(defective), (
        'control does not carry a destructive command, so the qualifier would '
        'never be applied to it in production — the rejection would be vacuous'
    )
    assert not _is_destructive_instruction_qualified(defective)
    assert _is_destructive_instruction_qualified(repaired), (
        'the repaired twin must pass — otherwise the rejection above is caused by '
        'some other missing clause, not by the defect this control isolates'
    )


def test_worktree_handling_destructive_instructions_are_inspection_first():
    """The layer-D recovery document carries no destructive discard instruction
    without an inspection-plus-operator-disposition qualifier in the same section.

    This is the sibling assertion that covers the fourth destructive site.
    ``worktree-handling.md`` § "Recovery Loop" carries a ``### ``-shaped heading,
    not the ``**Named recovery case`` marker the region derivation keys on, so
    the widened directory sweep does not reach it. This assertion reaches it
    directly, section by section.
    """
    sections = _derive_document_sections(WORKTREE_HANDLING)
    assert sections, f'no sections derived from {WORKTREE_HANDLING} — the sweep is vacuous'

    destructive = [
        (heading, lineno, text)
        for heading, lineno, text in sections
        if _DESTRUCTIVE_ANY_PATH.search(text)
    ]
    # Non-vacuous control, with the population size published: the document DOES
    # carry destructive instructions, so the qualifier assertion below examines a
    # populated surface instead of passing on an empty one.
    assert destructive, (
        f'no destructive discard instruction found across {len(sections)} sections of '
        f'{WORKTREE_HANDLING.name} — the qualifier assertion would pass vacuously; '
        'confirm the sweep still matches the document'
    )

    # The qualifier checks each destructive COMMAND against a diff of the path it
    # destroys, so the command count — not the section count alone — is the
    # denominator the per-target loop iterates. Published in the message rather
    # than asserted: it is derived from the same pattern that selected the
    # sections above, so an assertion on it could never fail independently.
    commands = sum(len(_DESTRUCTIVE_ANY_PATH.findall(text)) for _, _, text in destructive)

    offenders = [
        f'{heading} (line {lineno})'
        for heading, lineno, text in destructive
        if not _is_destructive_instruction_qualified(text)
    ]
    assert not offenders, (
        f'destructive discard instruction without an inspection-plus-operator-disposition '
        f'qualifier in the same section of {WORKTREE_HANDLING.name} '
        f'({len(destructive)} of {len(sections)} sections carry one, '
        f'{commands} destructive command(s) checked against the diff of the path each '
        f'destroys):\n  ' + '\n  '.join(offenders)
    )


def test_named_recovery_never_instructs_unconditional_discard():
    """No derived named-recovery region instructs an unconditional discard, EVERY
    region is inspection-first, and no "always safe" justification survives.

    The universal inspection-first assertion is what makes the population-derived
    sweep worth deriving: the two literal signatures alone pass any reworded site
    that avoids their exact wording, so a fourth destructive block was invisible
    to a test that swept every region."""
    regions = _derive_named_recovery_regions()
    assert regions, (
        'assertion-shape sweep for the named `.plan/marshal.json` recovery case '
        'matched nothing — the contract moved or the derivation is vacuous'
    )
    offenders: list[str] = []
    for path, block, lineno in regions:
        # Literal-signature floor, retained as an additional check.
        if _has_always_safety_claim(block):
            offenders.append(f'{path.name}:{lineno} — "always safe"/"always a spurious" justification')
        # UNIVERSAL assertion: every derived region — not merely the three
        # already-known members — must mandate inspection then an explicit
        # operator disposition. A reworded site that carries the cross-reference
        # bullet and avoids the "always safe" phrasing clears every literal
        # signature and is caught only here.
        if not _is_inspection_first(block):
            if _has_unconditional_discard_directive(block):
                offenders.append(
                    f'{path.name}:{lineno} — `git checkout`/`git restore` against '
                    'marshal.json with no inspection-then-disposition mandate'
                )
            else:
                offenders.append(
                    f'{path.name}:{lineno} — not inspection-first (needs inspection '
                    'plus an explicit operator disposition)'
                )
    assert not offenders, (
        'destructive named-recovery text survives (a dirty `marshal.json` is most '
        'likely uncommitted operator config, and `git checkout --` destroys it '
        'irrecoverably):\n  ' + '\n  '.join(offenders)
    )


def test_named_recovery_inspection_first_population_nonempty_and_covers_known_members():
    """D3(b): the derived population of inspection-first named-recovery sites is
    non-empty and covers the known members.

    The plain sweep is the non-vacuous control — it proves the derivation
    examined a populated surface, so the non-empty assertion below cannot be
    satisfied by an empty sweep (a matched-nothing sweep looks identical to a
    clean tree, which is exactly the confusion this epic is named for)."""
    regions = _derive_named_recovery_regions()
    # Non-vacuous control: the surface is populated.
    assert regions, (
        'assertion-shape sweep matched nothing — cannot distinguish a fixed class '
        'from a vanished one'
    )
    known_files = {path.name for path, _, _ in regions}
    assert 'planning.md' in known_files
    assert 'planning-outline.md' in known_files
    assert sum(1 for path, _, _ in regions if path.name == 'planning-outline.md') >= 2, (
        'planning-outline.md must carry the named-recovery case at both the '
        'outline and plan phase boundaries'
    )

    # The derived population of correctly-handled sites — asserted non-empty.
    inspection_first = [(path, block) for path, block, _ in regions if _is_inspection_first(block)]
    assert inspection_first, (
        'no named-recovery site mandates inspection-before-discard with an '
        'explicit operator disposition — the class is unfixed'
    )
    covered = {path.name for path, _ in inspection_first}
    assert 'planning.md' in covered
    assert 'planning-outline.md' in covered
    assert sum(1 for path, _ in inspection_first if path.name == 'planning-outline.md') >= 2, (
        'both planning-outline.md boundaries must handle the recovery inspection-first'
    )


def test_named_recovery_contract_is_a_single_authority():
    """D2: the named-recovery contract is ONE authority the other sites reference,
    not three near-identical copies (which drift, as this triplet already did)."""
    regions = _derive_named_recovery_regions()
    assert regions, 'assertion-shape sweep matched nothing'
    authorities = [(path, block) for path, block, _ in regions if _is_authority(block)]
    assert len(authorities) == 1, (
        'expected exactly ONE named-recovery authority (the block carrying the '
        f'concrete inspection command); found {len(authorities)}: '
        f'{[path.name for path, _ in authorities]} — collapse the copies to a '
        'single authority the sites reference, do not synchronise them'
    )
    _, authority_block = authorities[0]
    for path, block, lineno in regions:
        if block == authority_block:
            continue
        assert _references_authority(block), (
            f'{path.name}:{lineno} restates the named-recovery contract instead of '
            'referencing the single authority — where a copy exists, delete the '
            'copy (do not synchronise it)'
        )
