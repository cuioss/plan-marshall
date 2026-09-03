#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Derivation guard for the branch-cleanup merge-routing contract.

Follows the precedent of ``test_merge_authorization_roster.py``: every
population this module asserts over is **derived** from the authoritative
artifact, never carried as a hardcoded list, and every derived size is published
in the assertion message so a check that passed vacuously against an empty or
half-read population is self-evident from its own output.

The assertions are grounded in the mechanism that was ESTABLISHED — an
off-routing dispatch to an unguarded verb — not in the mechanism the request
hypothesised:

(1) **Closed dispatch set over a DERIVED DOCUMENT SET.** The executable step body
    is not one document, so the guard's population must not be one filename. The
    document set is derived by transitively following every same-directory
    standards link whose surrounding prose *instructs the executor to load and
    execute it*; a link cross-referenced for background is NOT a member. The
    dispatch set is then derived over the UNION and asserted to be exactly
    ``{safe-merge, merge-queue}``. Relocating a merge-shaped dispatch into a
    sibling the step body loads must FAIL the guard, because the assertion is
    bound to the derived set, not to a filename.

(2) **Population-derived preflight parity, from the DISPATCH REGISTRY, over BOTH
    providers.** The merge-shaped verb population comes from each provider's
    ``handlers: HandlerMap`` literal — the closed registry — and NOT from a scan
    for ``def cmd_`` or for handlers that call the CLI. A call-site scan is a
    *sample*, and sampling is what let this population under-enumerate twice
    (GitHub ``cmd_pr_auto_merge`` missed at pass 1, GitLab ``cmd_pr_auto_merge``
    missed at pass 2). The per-member predicate is bound to each handler's
    EXECUTABLE CODE — its identifiers — never to its raw source text; see the
    falsifiability report below for why that distinction is the whole assertion.

(3) **Enumeration completeness, population-derived.** The declared param
    population comes from the step's ``configurable:`` frontmatter; the one-stop
    ``step-params get`` enumeration is parsed independently out of the prose. The
    two are cross-compared, so a param bound later but absent from the one-stop
    read is caught.

(4) **Routing observability.** Every ``use_merge_queue`` consumption site emits a
    decision-log line, and the merge-routing site's line PRECEDES the dispatch it
    selects.

Two vacuity traps this module avoids, both observed in this same area:

* **Cross-check rather than merely parse.** Assertions (1), (2) and (3) compare
  two INDEPENDENTLY derived sides — (1) the dispatches the body issues against
  the closure the section declares, (2) the registry population against each
  handler's own source, (3) the ``configurable:`` frontmatter against the
  enumeration prose. A sibling closure test once opened two documents and never
  compared them, letting a real divergence stay invisible.
* **No assertion bound to state the pipeline has already destroyed.** The
  queue-landing assertion is anchored to an observation taken BEFORE the branch
  prune, never after it — a prune that has already run cannot witness the state
  the assertion is about. It anchors on the prune DISPATCH rather than on a
  mention of the verb, because the gate itself names the verb while explaining
  what it must not let run.

**Pre-fix falsifiability, reported honestly.** Most assertions here were verified
to fail against the pre-fix tree; one half of one assertion was not, and saying
so is more useful than a blanket claim:

* (1) *declared-closure half* — FAILS pre-fix: no closed-dispatch-set table
  existed, so ``rows`` was empty.
* (1) *derived-dispatch half* — PASSES pre-fix. The body already dispatched only
  ``safe-merge`` and ``merge-queue``; what was missing was the *declaration* that
  the set is closed. This half is a regression lock, not a newly-failing check,
  and is documented as such rather than presented as evidence of the fix.
* (2) — FAILS pre-fix for 5 of the 8 parametrized members (both providers'
  ``cmd_pr_merge`` and ``cmd_pr_auto_merge``, plus GitLab's ``cmd_pr_safe_merge``,
  none of which touched the queue/train surface at all).
* (3) — FAILS pre-fix: the one-stop enumeration named 4 of the 9 declared params.
* (4a/4b/4c) — FAIL pre-fix: no observability block, no decision-log line, and no
  routing line to order against the dispatch.
* (5) — FAILS pre-fix: the queue-landing gate did not exist, so the post-merge
  tail ran unconditionally on a merely-enqueued PR.

**Falsifiability of (2b), measured by mutation.** The pre-fix report above says
(2) fails pre-fix for 5 of 8 members, which is true and yet was not enough: it
measured the assertion against the pre-fix TREE, not against the property. Run
against a MUTANT — each real handler with its executable guard lines deleted and
its docstring and comments left verbatim, i.e. a handler that fully documents a
guard it does not perform — the two predicates separate completely:

=================================================  =============  =============
predicate                                          live tree      mutants
=================================================  =============  =============
raw-text search of the handler source              all members    all but one
identifier-bound (``first_queue_symbol``)          all members    no members
=================================================  =============  =============

Stated as ratios rather than against a standing denominator, because the counts
above are the values OBSERVED at that mutation run — over the eight members the
population held at the time — and NOT a live expectation. This change de-pinned
the fixed eight-member expectation precisely because a behaviour-derived
population may legitimately grow (see the module docstring's population note), so
a transcribed ``/8`` would go stale on the first added merge-shaped verb and this
module would then document a number its own assertions reject.

The identifier-bound predicate, its ``QUEUE_VOCAB_RE`` vocabulary and the
tokenizing helpers it needs are imported from
:mod:`_merge_shaped_roster`, the designated single source for this derivation,
rather than redefined here — and so is the registry derivation itself: the
``handlers: HandlerMap`` grammar, the row grammar, the ``MERGE_SHAPED_VERBS``
vocabulary and the ast-based handler-body lookup. This module defines no
registry regex of its own. Two copies of a registry grammar drift
independently, and a copy that stopped matching would shrink this guard's
population while the sibling suite reading the same registry stayed green, with
nothing reporting the divergence. Only the PATH resolution stays local, because
which module files to read is this guard's own subject.

The raw-text predicate accepts 7 of the 8 gutted handlers, because this diff gave
every merge-shaped handler a docstring naming the queue or the train. Both arms
of (2b) were therefore satisfied by prose the same commit authored, and the
ordering arm was structurally incapable of failing — a docstring necessarily
precedes every executable literal in the body it documents. (The single mutant
the raw-text predicate rejects, ``github:auto-merge``, is an accident of spelling:
its prose writes "merge queue" with a space, which the word-anchored form did not
match.) The identifier-bound predicate rejects every mutant while still finding
all 8 live guards, so it discriminates rather than merely rejecting.

Two defects the mutation run exposed in the fix itself, both now locked by
:func:`test_queue_guard_predicate_is_falsifiable` and
:func:`test_prose_blanking_is_offset_preserving`:

* the ``\\b`` anchor that was invisible against prose matched only identifiers
  BEGINNING with the vocabulary once the predicate read code (5 of 8 members
  regressed);
* docstring blanking without bracket-depth tracking erased the ``'status'`` key
  of the success envelope itself, destroying the ordering arm's right-hand side.
"""

from __future__ import annotations

import ast
import re
import tokenize
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT
from _merge_shaped_roster import (
    QUEUE_VOCAB_RE,
    ProviderSources,
    derive_population,
    first_queue_symbol,
    handler_source,
    line_starts,
    registry_handler_names,
    registry_keys,
    source_tokens,
)

_BUNDLE_ROOT: Path = Path(MARKETPLACE_ROOT)
_SKILLS: Path = _BUNDLE_ROOT / 'plan-marshall' / 'skills'
_STANDARDS_DIR: Path = _SKILLS / 'phase-6-finalize' / 'standards'
_BRANCH_CLEANUP: Path = _STANDARDS_DIR / 'branch-cleanup.md'

#: The two provider handler modules. The registry population is read from these.
_PROVIDER_MODULES: dict[str, Path] = {
    'github': _SKILLS / 'workflow-integration-github' / 'scripts' / 'github_ops.py',
    'gitlab': _SKILLS / 'workflow-integration-gitlab' / 'scripts' / 'gitlab_ops.py',
}

#: Where each provider's merge-shaped handler BODIES live. GitHub splits its PR
#: handlers into a submodule; GitLab defines them inline. Both are read as text —
#: the guard is a source-level derivation, not an import-time one.
_PROVIDER_HANDLER_SOURCES: dict[str, tuple[Path, ...]] = {
    'github': (
        _SKILLS / 'workflow-integration-github' / 'scripts' / '_github_pr.py',
        _SKILLS / 'workflow-integration-github' / 'scripts' / 'github_ops.py',
    ),
    'gitlab': (_SKILLS / 'workflow-integration-gitlab' / 'scripts' / 'gitlab_ops.py',),
}

#: The dispatch set the step body is permitted to issue. This IS the contract
#: under assertion, stated once here and cross-checked against the derived set.
_EXPECTED_DISPATCH_SET: frozenset[str] = frozenset({'safe-merge', 'merge-queue'})

#: One row of the closed-dispatch-set table the owning section declares. Parsing
#: it gives a DECLARED reachability population that is independent of the derived
#: one — so the closure assertion compares two real sides rather than comparing a
#: derivation against a literal in this file.
_DISPATCH_TABLE_ROW_RE = re.compile(
    r'^\|\s*`ci pr ([a-z-]+)`\s*\|\s*(\*\*never\*\*|yes)\s*\|', re.MULTILINE
)

#: A merge-shaped ``ci pr`` verb. Alternatives are ordered longest-first and the
#: trailing guard rejects a longer verb, so ``pr merge-queue`` is never read as
#: ``pr merge`` plus noise.
_PR_VERB_RE = re.compile(r'\bpr\s+(merge-queue|safe-merge|auto-merge|merge)(?![-\w])')

#: What makes a fenced block an EXECUTABLE dispatch rather than a narrative
#: mention: it runs the executor against the CI abstraction. A prose sentence
#: naming a verb, a table row, or an ``AskUserQuestion`` description that quotes
#: a command carries neither token and is correctly excluded.
_EXECUTOR_MARKER = 'execute-script.py'
_CI_NOTATION = 'tools-integration-ci:ci'

#: A same-directory Markdown link to another standards document.
_LOCAL_MD_LINK_RE = re.compile(r'\]\((?!https?:)([^)/#]+\.md)(?:#[^)]*)?\)')

#: The membership predicate for the derived document set: the prose around the
#: link instructs the executor to LOAD AND EXECUTE the target. A link that is
#: merely cross-referenced for background is not a member.
_LOAD_AND_EXECUTE_RE = re.compile(r'load and execute', re.IGNORECASE)

#: One ``configurable:`` frontmatter key.
_CONFIGURABLE_KEY_RE = re.compile(r'^\s*-\s+key:\s*(\S+)\s*$', re.MULTILINE)

#: A backticked token inside the one-stop enumeration sentence.
_BACKTICKED_RE = re.compile(r'`([a-z0-9_]+)`')

#: The sentence that enumerates the one-stop ``step-params get`` param set.
#: Line-scoped and non-greedy on purpose: a ``DOTALL`` match would run from the
#: first ``The `…` `` anywhere in the document to this sentence's tail and sweep
#: in every unrelated backticked token on the way, silently inflating the
#: "enumerated" side until the completeness check could not fail.
_ONE_STOP_SENTENCE_RE = re.compile(
    r'^The (`.+?) params are all step-owned params of the `default:branch-cleanup` step\.',
    re.MULTILINE,
)

#: A ``use_merge_queue`` CONSUMPTION site: a section that binds the value. Matched
#: case-insensitively — one site reads it mid-sentence ("— read `use_merge_queue`
#: off …"), and a case-sensitive matcher silently undercounts the population.
_USE_MERGE_QUEUE_READ_RE = re.compile(r'read `use_merge_queue` off', re.IGNORECASE)

#: The mandatory observability marker each consumption site must carry.
_OBSERVABILITY_MARKER = '**Observability (mandatory)**'

#: The heading of the section that ENCLOSES the `prune-local-and-remote-ref`
#: dispatch. Used to anchor the prune-guard window on the real section boundary
#: rather than on a fixed character count: a fixed window silently slides the
#: `{merge_landed}` guard sentence out of view as the section grows, and a
#: negative start index would slice from the END of the document.
_PRUNE_SECTION_HEADING = '#### Release the cross-plan merge-lock (both paths)'

#: The success-literal marker used for the "before returning success" ordering.
_SUCCESS_LITERAL = "'status': 'success'"


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _fenced_blocks(text: str) -> list[str]:
    """Every fenced code block in ``text``."""
    return text.split('```')[1::2]


# ---------------------------------------------------------------------------
# (1) Derived document set  →  derived dispatch set
# ---------------------------------------------------------------------------


def _load_and_execute_links(doc: Path) -> set[Path]:
    """Same-directory standards documents ``doc`` instructs the executor to run.

    The membership predicate is the LOAD-AND-EXECUTE instruction in the prose
    around the link, not the link itself: ``branch-cleanup.md`` cross-references
    several sibling standards for background, and none of those is part of the
    executable step body.
    """
    members: set[Path] = set()
    for line in _read(doc).splitlines():
        if not _LOAD_AND_EXECUTE_RE.search(line):
            continue
        for target in _LOCAL_MD_LINK_RE.findall(line):
            candidate = (doc.parent / target).resolve()
            if candidate.is_file():
                members.add(candidate)
    return members


def _derive_document_set() -> list[Path]:
    """The transitive closure of load-and-execute links from ``branch-cleanup.md``.

    Returned sorted so the published population is stable and reviewable.
    """
    seen: set[Path] = {_BRANCH_CLEANUP.resolve()}
    frontier = [_BRANCH_CLEANUP.resolve()]
    while frontier:
        current = frontier.pop()
        for member in _load_and_execute_links(current):
            if member not in seen:
                seen.add(member)
                frontier.append(member)
    return sorted(seen)


_DOCUMENT_SET: list[Path] = _derive_document_set()


def _dispatched_merge_verbs(doc: Path) -> set[str]:
    """The merge-shaped ``ci pr`` verbs ``doc`` actually DISPATCHES.

    Assertion is on invocation SHAPE, never on token presence: only a fenced
    block that runs the executor against the CI abstraction counts. That is what
    keeps a narrative mention — ``branch-cleanup.md``'s historical note that
    safe-merge "replaces the former ``pr merge`` → ``pr auto-merge``
    branch-protection fallback sequence", and the closed-dispatch-set table that
    names both verbs precisely to declare them unreachable — from being read as
    a dispatch.
    """
    verbs: set[str] = set()
    for block in _fenced_blocks(_read(doc)):
        if _EXECUTOR_MARKER not in block or _CI_NOTATION not in block:
            continue
        verbs.update(_PR_VERB_RE.findall(block))
    return verbs


def test_derived_document_set_is_non_empty_and_reaches_the_sub_standard():
    """The document-set derivation resolves the whole executable step body.

    Asserted first and on its own: every dispatch assertion below iterates this
    population, so a derivation that silently collapsed to one file (or to none)
    would make the closure check pass while covering a fraction of the body.
    """
    names = [doc.name for doc in _DOCUMENT_SET]
    assert _BRANCH_CLEANUP.resolve() in _DOCUMENT_SET, (
        f'The derived document set does not contain its own root. Derived: {names}'
    )
    assert len(_DOCUMENT_SET) >= 2, (
        f'Derived document-set size = {len(_DOCUMENT_SET)} ({names}). The executable step '
        'body is NOT one document: branch-cleanup.md instructs the executor to load and '
        'execute branch-cleanup-rereview.md, so a derivation yielding a single member has '
        'lost the transitive follow and every dispatch assertion below covers only part of '
        'the body.'
    )


# ---------------------------------------------------------------------------
# The re-review DECLINE routing, asserted STRUCTURALLY over a derived consumer set
# ---------------------------------------------------------------------------
#
# ``github_re_review await_fresh_review`` matches on EITHER a review that named the
# merge candidate's SHA (``head_sha_verified: true``) OR a bare comment that merely
# post-dates the trigger (``false``). A consumer reading ``matched`` alone credits a
# review that never named the commit it matched.
#
# ⛔ Substring presence cannot express that. The previous form of this guard asserted
# that the words ``head_sha_verified``, ``declined`` and ``{declined_bots}`` each
# appeared SOMEWHERE in one document — which discriminates against the pre-fix text
# and against nothing else. A document that mentioned the bit in a background note,
# routed on ``matched`` alone, and accumulated declines on the VERIFIED arm would
# satisfy every one of those assertions while crediting exactly the outcome the fix
# exists to reject. What has to be asserted is the ANTECEDENT relationship: the false
# polarity is the condition of the branch that accumulates ``{declined_bots}``, and
# the true polarity is not.

#: An outcome ARM: a bullet whose bold lead states the condition it fires on.
_OUTCOME_ARM_RE = re.compile(r'^[ \t]*-[ \t]+\*\*(?P<antecedent>[^*]+)\*\*', re.MULTILINE)

#: Where an arm's BODY ends: the next arm, the next numbered bold list item, or the
#: next heading. Bounding on all three keeps a trailing arm from absorbing the rest
#: of the document — which would let any later ``{declined_bots}`` mention satisfy it.
_ARM_BOUNDARY_RE = re.compile(r'^(?:[ \t]*(?:-|\d+\.)[ \t]+\*\*|#{1,6}[ \t])', re.MULTILINE)

#: The re-review registry invocation that produces the outcome these arms consume.
_RE_REVIEW_NOTATION = 'workflow-integration-github:github_re_review'


def _re_review_dispatchers() -> list[Path]:
    """Every marketplace document that DISPATCHES ``github_re_review re-review``.

    The consumer set is derived, never listed: a third document that starts
    triggering re-reviews inherits this guard instead of escaping it. Membership is
    invocation SHAPE — an executor call against the re-review registry inside a
    fenced block — so the canonical-invocation reference in a SKILL.md prose
    paragraph, and every cross-reference to this walkthrough, are correctly excluded.
    """
    return sorted(
        path
        for path in _BUNDLE_ROOT.rglob('*.md')
        if any(
            _EXECUTOR_MARKER in block and _RE_REVIEW_NOTATION in block and 're-review' in block
            for block in _fenced_blocks(_read(path))
        )
    )


def _outcome_arms(text: str) -> list[tuple[str, str]]:
    """``(antecedent, body)`` for every outcome arm in ``text``.

    Takes TEXT rather than a path so the negative control below drives this exact
    parser over synthetic documents. A control that re-implemented the slicing would
    only prove its own copy discriminates.
    """
    boundaries = [m.start() for m in _ARM_BOUNDARY_RE.finditer(text)]
    arms: list[tuple[str, str]] = []
    for match in _OUTCOME_ARM_RE.finditer(text):
        following = [offset for offset in boundaries if offset > match.start()]
        end = following[0] if following else len(text)
        arms.append((match.group('antecedent'), text[match.end() : end]))
    return arms


def _matched_arms(text: str) -> list[tuple[str, str]]:
    """The outcome arms whose antecedent fires on a ``matched: true`` return."""
    return [(ante, body) for ante, body in _outcome_arms(text) if 'matched: true' in ante]


def _decline_routing_defects(text: str) -> list[str]:
    """Every way ``text``'s ``matched`` arms fail the decline-routing contract.

    One predicate, three defect shapes, so the assertions and the negative control
    below read the SAME rule rather than two spellings of it:

    * a ``matched: true`` arm that does not state the ``head_sha_verified`` polarity;
    * a false-polarity arm that does not accumulate ``{declined_bots}`` in its body;
    * a verified-polarity arm that DOES accumulate it.
    """
    defects: list[str] = []
    for antecedent, body in _matched_arms(text):
        label = antecedent.strip()
        if 'head_sha_verified' not in antecedent:
            defects.append(f'{label!r}: branches on matched alone, with no polarity stated')
            continue
        if 'head_sha_verified: false' in antecedent and '{declined_bots}' not in body:
            defects.append(f'{label!r}: the decline arm accumulates no {{declined_bots}}')
        if 'head_sha_verified: true' in antecedent and '{declined_bots}' in body:
            defects.append(f'{label!r}: a VERIFIED review is accumulated as a decline')
    return defects


#: Documents that dispatch the re-review registry AND branch on its ``matched``
#: outcome. Derived in two independent steps — the dispatch is a fenced invocation,
#: the consumption is a bold-lead arm — so a document that gains a `matched`-alone
#: arm joins this population and is then held to the polarity contract below.
_RE_REVIEW_CONSUMERS: list[Path] = [
    doc for doc in _re_review_dispatchers() if _matched_arms(_read(doc))
]


def test_the_re_review_consumer_set_is_derived_and_plural():
    """The polarity sweep below runs over a NON-EMPTY, multi-document population.

    Asserted on its own and first: the sweep is parametrized over this set, and a
    parametrize over an empty list produces a skip rather than a failure — so a
    derivation that stopped matching would report clean while covering nothing. The
    floor is two because the decline routing exists at two consumer families (the
    automatic-review step body's triggers, and the branch-cleanup re-review
    walkthrough), and the whole defect this closes was one of them consulting the bit
    while the other did not. A single-document population cannot see that class of
    divergence at all.
    """
    dispatchers = [doc.name for doc in _re_review_dispatchers()]
    consumers = [doc.name for doc in _RE_REVIEW_CONSUMERS]

    assert dispatchers, (
        'no document was found dispatching `github_re_review re-review`. The step body '
        'demonstrably triggers re-reviews, so an empty derivation means the '
        'invocation-shape predicate stopped matching and every assertion below is vacuous.'
    )
    assert len(consumers) >= 2, (
        f'Derived re-review consumer set = {consumers} (from dispatchers {dispatchers}). '
        'Both the automatic-review step body and the branch-cleanup re-review walkthrough '
        'branch on the `matched` outcome; a smaller population means one of them stopped '
        'resolving and its decline routing is no longer covered here.'
    )


@pytest.mark.parametrize('doc', _RE_REVIEW_CONSUMERS, ids=lambda d: d.name)
def test_the_false_polarity_is_the_antecedent_of_the_decline_branch(doc):
    """``head_sha_verified: false`` CONDITIONS the branch that accumulates declines.

    The structural claim a presence check cannot express, in all three directions
    (:func:`_decline_routing_defects`): every ``matched: true`` arm states the
    polarity; every false-polarity arm accumulates ``{declined_bots}`` in its OWN body,
    so the decline is recorded where it is observed rather than merely mentioned
    somewhere in the document; and no VERIFIED-polarity arm accumulates it. That last
    direction is the one the old assertions could not see at all — a document that
    credited a review of this HEAD as a decline, or that accumulated on both
    polarities, satisfied "the token appears" while routing exactly backwards.

    Both polarities are additionally required to be PRESENT, because the contract is a
    discrimination: a document carrying only the false arm would pass the routing
    checks while saying nothing about what a verified review does.
    """
    text = _read(doc)
    matched = _matched_arms(text)
    assert matched, f'{doc.name} is in the consumer set but yielded no `matched: true` arm'

    polarities = {
        polarity
        for polarity in ('true', 'false')
        if any(f'head_sha_verified: {polarity}' in ante for ante, _body in matched)
    }
    assert polarities == {'true', 'false'}, (
        f'{doc.name} branches on only {sorted(polarities) or "neither"} of the '
        'head_sha_verified polarities. Both arms must exist: without the false arm an '
        'incremental-review decline falls through the completed-review path, and without '
        'the true arm nothing shows the decline accumulation is bound to the false one.'
    )

    defects = _decline_routing_defects(text)
    assert not defects, (
        f'{doc.name} does not route the re-review outcome on head_sha_verified: '
        + '; '.join(defects)
    )


def test_the_decline_routing_predicate_rejects_each_defect_shape():
    """Matched negative control: the predicate really can fail, on each shape it names.

    The sweep above is only ever observed against documents that route correctly,
    which shows the parser can recognise a compliant arm — never that it can reject a
    non-compliant one. Every defect shape is exercised against the SAME
    :func:`_decline_routing_defects` the sweep calls, and a compliant control is run
    through it too, so this is a discrimination rather than a predicate that rejects
    everything.
    """
    matched_alone = '- **When `matched: true`**, the fresh review is now on the PR.\n'
    unrecorded = (
        '- **When `matched: true` AND `head_sha_verified: false`**, the bot declined.\n'
    )
    inverted = (
        '- **When `matched: true` AND `head_sha_verified: true`**, add `{bot_kind}` to the '
        'accumulating `{declined_bots}` set.\n'
        '- **When `matched: true` AND `head_sha_verified: false`**, the review landed.\n'
    )
    compliant = (
        '- **When `matched: true` AND `head_sha_verified: true`**, the fresh review is on '
        'the PR.\n'
        '- **When `matched: true` AND `head_sha_verified: false`**, add `{bot_kind}` to the '
        'accumulating `{declined_bots}` set.\n'
    )

    assert _decline_routing_defects(matched_alone) == [
        "'When `matched: true`': branches on matched alone, with no polarity stated"
    ]
    assert _decline_routing_defects(unrecorded) == [
        "'When `matched: true` AND `head_sha_verified: false`': the decline arm "
        'accumulates no {declined_bots}'
    ]
    assert _decline_routing_defects(inverted) == [
        "'When `matched: true` AND `head_sha_verified: true`': a VERIFIED review is "
        'accumulated as a decline',
        "'When `matched: true` AND `head_sha_verified: false`': the decline arm "
        'accumulates no {declined_bots}',
    ]
    assert _decline_routing_defects(compliant) == []


def test_the_barrier_forwards_the_decline_observation_on_its_predicate_call():
    """The accumulated set reaches the predicate as a quoted ``--declined-bots`` value.

    Bound to the DISPATCH rather than to the document text: the flag has to ride the
    ``review_completeness check`` invocation the barrier actually issues, and its
    interpolation has to be quoted, or an empty decline set collapses the flag and
    steals the next token. A prose mention of the flag satisfies neither.
    """
    invocations = [
        block
        for block in _fenced_blocks(_read(_BRANCH_CLEANUP))
        if _EXECUTOR_MARKER in block
        and 'automatic-review:review_completeness' in block
        and re.search(r'\bcheck\b', block)
    ]
    assert invocations, (
        f'{_BRANCH_CLEANUP.name} issues no `review_completeness check` invocation, so the '
        'forwarding this test asserts has nothing to ride on.'
    )
    forwarding = [block for block in invocations if '--declined-bots "{declined_bots}"' in block]
    assert forwarding, (
        f'none of the {len(invocations)} `review_completeness check` invocation(s) in '
        f'{_BRANCH_CLEANUP.name} forwards --declined-bots "{{declined_bots}}". Without it a '
        'decline accumulated by the re-review walkthrough never resolves to the blocking '
        '`declined` member at the merge gate.'
    )


def test_dispatch_set_over_the_derived_document_set_is_closed():
    """(1) Over the UNION of the derived document set, the dispatch set is exactly two.

    ``pr merge`` and ``pr auto-merge`` appear nowhere in any member AS A DISPATCH.
    The assertion is bound to the derived set rather than to a filename, so
    relocating a merge-shaped dispatch out of ``branch-cleanup.md`` and into
    ``branch-cleanup-rereview.md`` — or into any future sibling the step body
    loads — fails here rather than slipping through.
    """
    per_doc = {doc.name: sorted(_dispatched_merge_verbs(doc)) for doc in _DOCUMENT_SET}
    union: set[str] = set()
    for verbs in per_doc.values():
        union.update(verbs)

    assert union, (
        f'ZERO merge-shaped dispatches were derived across the {len(_DOCUMENT_SET)} '
        f'document(s) {list(per_doc)}. The step body demonstrably issues a merge, so an '
        'empty derivation means the invocation-shape predicate stopped matching — and '
        'every closure assertion below would pass vacuously.'
    )
    assert union == set(_EXPECTED_DISPATCH_SET), (
        f'The derived dispatch set is {sorted(union)}, not {sorted(_EXPECTED_DISPATCH_SET)}. '
        f'Per document: {per_doc}. `ci pr safe-merge` and `ci pr merge-queue` are the ONLY '
        'merge dispatches this step may issue; `ci pr merge` and `ci pr auto-merge` are not '
        'reachable from it under any condition, and neither is a fallback for the other.'
    )

    # Second, independent side: what the owning section DECLARES as reachable.
    # Comparing the derived set against a literal in this file alone would be
    # half a check — it would catch a document that gained a dispatch, but not a
    # document whose own closure declaration disagreed with what it dispatches.
    rows = _DISPATCH_TABLE_ROW_RE.findall(_read(_BRANCH_CLEANUP))
    assert rows, (
        'branch-cleanup.md declares no closed-dispatch-set table. The closure must be '
        'STATED at the owning section — a reader of the step body cannot otherwise tell '
        'that `ci pr merge` and `ci pr auto-merge` are unreachable rather than merely '
        'unused today. See § "Merge routing (`use_merge_queue`)" → "The dispatch set is '
        'CLOSED".'
    )
    declared_reachable = {verb for verb, mark in rows if mark == 'yes'}
    declared_unreachable = {verb for verb, mark in rows if mark != 'yes'}

    assert declared_unreachable, (
        f'The declared dispatch table marks nothing unreachable ({rows}). A table listing '
        'only the permitted verbs states no closure at all — the whole point is naming the '
        'verbs that must NOT be reachable.'
    )
    assert declared_reachable == union, (
        f'The section DECLARES {sorted(declared_reachable)} reachable but the derived '
        f'dispatch set is {sorted(union)}. The declaration and the executable body must '
        'agree; a divergence means one of the two silently moved.'
    )
    assert not (declared_unreachable & union), (
        f'{sorted(declared_unreachable & union)} is declared unreachable yet is actually '
        'dispatched by the step body.'
    )


@pytest.mark.parametrize('doc', _DOCUMENT_SET, ids=lambda d: d.name)
def test_no_member_dispatches_an_unreachable_merge_verb(doc):
    """No individual member issues ``pr merge`` / ``pr auto-merge``.

    The union assertion above proves the SET is closed; this proves it per
    member, so a document that gained a forbidden dispatch is named directly
    rather than reported as a set difference.
    """
    forbidden = _dispatched_merge_verbs(doc) - _EXPECTED_DISPATCH_SET
    assert not forbidden, (
        f'{doc.name} dispatches {sorted(forbidden)}, which the closed dispatch set forbids. '
        'See branch-cleanup.md § "Merge routing (`use_merge_queue`)" → "The dispatch set is '
        'CLOSED".'
    )


def test_prose_mentions_are_not_counted_as_dispatches():
    """The invocation-shape predicate distinguishes a dispatch from a mention.

    Pinned explicitly because the closed-dispatch-set table and the historical
    fallback note both name the forbidden verbs in prose. A predicate keyed to
    token presence would read those as dispatches and fail — and, worse, a
    predicate later "fixed" by dropping them would stop seeing real dispatches
    written in the same block.
    """
    text = _read(_BRANCH_CLEANUP)
    assert 'pr auto-merge' in text, (
        'branch-cleanup.md no longer mentions `pr auto-merge` anywhere. This test is a '
        'precondition check: without a prose mention present, it cannot demonstrate that '
        'mentions are excluded, and it would pass vacuously.'
    )
    assert 'auto-merge' not in _dispatched_merge_verbs(_BRANCH_CLEANUP), (
        'A prose mention of `pr auto-merge` was counted as a dispatch. The predicate must '
        'assert on invocation shape (an executor + CI-notation fenced block), never on '
        'token presence.'
    )


# ---------------------------------------------------------------------------
# (2) Population-derived preflight parity, from the DISPATCH REGISTRY
# ---------------------------------------------------------------------------


def _registry_keys(provider: str) -> list[tuple[str, ...]]:
    """Every ``(group, verb[, sub])`` key in a provider's ``HandlerMap`` literal.

    The registry is the CLOSED population. Deriving from it — rather than from a
    ``def cmd_`` scan or a search for handlers that shell out to the CLI — is what
    stops the sample-read-as-enumeration failure that missed ``cmd_pr_auto_merge``
    on each provider in turn.

    Path resolution stays here; the grammar comes from the shared roster, which
    fails loudly on a registry literal it cannot find rather than yielding an
    empty derivation every assertion below would then pass vacuously over.
    """
    return registry_keys(_read(_PROVIDER_MODULES[provider]))


def _registry_handler_names(provider: str) -> dict[tuple[str, ...], str]:
    """Map each registry key to the handler symbol it is bound to."""
    return registry_handler_names(_read(_PROVIDER_MODULES[provider]))


def _provider_sources(provider: str) -> ProviderSources:
    """One provider's derivation inputs as text; path resolution stays local."""
    return ProviderSources(
        registry_text=_read(_PROVIDER_MODULES[provider]),
        handler_texts=tuple(_read(path) for path in _PROVIDER_HANDLER_SOURCES[provider]),
    )


def _merge_shaped_registry_keys(provider: str) -> list[tuple[str, ...]]:
    """The merge-shaped subset of a provider's registry — derived by BEHAVIOUR.

    Membership comes from :func:`derive_population`, which classifies a registry
    key as merge-shaped when the handler it binds reaches the platform
    queue/train surface in its own executable code.

    It is deliberately NOT filtered through ``MERGE_SHAPED_VERBS``. The shared
    roster names that constant a MIRROR of this derivation and forbids narrowing
    a derived set through it: filtering the registry by a hand-listed vocabulary
    is precisely what made "population-complete" mean "complete over four
    pre-named verbs", dropping a merge-shaped handler registered under any other
    name before any guard saw it. The bidirectional mirror-vs-behaviour drift
    check lives in the sibling ``test_merge_shaped_offrouting_refusal`` suite,
    which is where the vocabulary is legitimately read.

    ``unresolved`` entries are NOT folded in here: a handler whose source could
    not be located is a member this derivation cannot speak about, and the
    sibling suite asserts that bucket is empty rather than silently absorbing it.
    """
    population = derive_population({provider: _provider_sources(provider)})
    return [('pr', verb) for _provider, verb, _symbol in population.members]


_REGISTRY_SIZES: dict[str, int] = {p: len(_registry_keys(p)) for p in _PROVIDER_MODULES}
_MERGE_SHAPED: dict[str, list[tuple[str, ...]]] = {
    p: _merge_shaped_registry_keys(p) for p in _PROVIDER_MODULES
}
_MERGE_SHAPED_TOTAL: int = sum(len(v) for v in _MERGE_SHAPED.values())

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. Every other size in this module travels only in a
#: FAILURE message, which is silent on exactly the run a shrunken population is
#: most likely to slip through: the green one.
GUARD_POPULATION_LABEL = 'merge-shaped registry members'
GUARD_POPULATION_SIZE = _MERGE_SHAPED_TOTAL


def _handler_source(provider: str, symbol: str) -> str:
    """The source text of one handler function, across the provider's modules.

    Delegates the LOOKUP to the shared roster, which resolves a bound symbol to
    its own top-level statement by parsing rather than by slicing to the next
    ``def``. A slice over-reads — it swallows every module-level constant sitting
    between two functions, crediting a handler with vocabulary it never
    references — and it cannot see a factory-bound handler at all, since those
    have no ``def`` line. Path resolution stays here.
    """
    return handler_source(symbol, tuple(_read(path) for path in _PROVIDER_HANDLER_SOURCES[provider]))


def _code_without_prose(source: str) -> str:
    """``source`` with every comment and docstring blanked to spaces.

    Offset-preserving — blanked characters become spaces and newlines are kept —
    so an index into the result is also an index into the original text and can
    be compared against the identifier offsets above.

    Used for the success-literal side of the ordering assertion, so a handler
    that happens to quote ``'status': 'success'`` inside its own documentation
    cannot move the boundary the guard is required to precede.

    A string counts as a docstring only when it opens a statement at bracket
    depth ZERO. The depth condition is load-bearing: a multi-line dict literal
    emits ``NL`` between its entries, so without it every string KEY on its own
    line — including the ``'status'`` of the success envelope itself — reads as
    a statement-opening string and gets blanked, erasing the very literal this
    view exists to locate.
    """
    starts = line_starts(source)
    chars = list(source)
    statement_start = True
    depth = 0
    for token in source_tokens(source):
        is_docstring = token.type == tokenize.STRING and statement_start and depth == 0
        if is_docstring or token.type == tokenize.COMMENT:
            begin = starts[token.start[0]] + token.start[1]
            finish = starts[token.end[0]] + token.end[1]
            for index in range(begin, min(finish, len(chars))):
                if chars[index] != '\n':
                    chars[index] = ' '
        if token.type == tokenize.OP:
            if token.string in '([{':
                depth += 1
            elif token.string in ')]}':
                depth -= 1
        if token.type != tokenize.COMMENT:
            statement_start = token.type in (
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.INDENT,
                tokenize.DEDENT,
            )
    return ''.join(chars)


def test_registry_populations_are_published_and_plausible():
    """(2a) The derived sizes are published, and none is vacuous.

    A parity check that ran against an empty or half-read registry would report
    "every member passes" while covering nothing. Publishing the sizes in the
    failure message makes that state self-evident from the test output; the
    merge-shaped total is additionally published on EVERY run — passing included
    — through ``GUARD_POPULATION_SIZE`` and the root conftest's
    ``pytest_report_header``.

    **No total is pinned for the merge-shaped subset, and that is a consequence
    of the derivation.** Membership is decided by BEHAVIOUR — whether a handler
    reaches the queue/train surface — not by a verb name, so an unlisted
    merge-shaped verb makes the total LARGER and an equality pin would fail on
    exactly the correct outcome. The collapse this arm must catch is a provider
    whose registry or handler sources stopped resolving, and per-provider
    non-emptiness catches that where a total cannot: a halved population is
    still a population.
    """
    assert _REGISTRY_SIZES['github'] >= 30, (
        f'GitHub registry size = {_REGISTRY_SIZES["github"]} — implausibly small for a '
        'registry carrying the pr / checks / issue / branch / repo surface. The literal was '
        'probably only partly matched, which would silently shrink the merge-shaped subset.'
    )
    assert _REGISTRY_SIZES['gitlab'] >= 30, (
        f'GitLab registry size = {_REGISTRY_SIZES["gitlab"]} — implausibly small; see the '
        'GitHub message above.'
    )
    by_provider = {p: sorted(k[1] for k in v) for p, v in _MERGE_SHAPED.items()}
    empty = sorted(p for p, verbs in by_provider.items() if not verbs)
    assert not empty, (
        f'{empty} contributes ZERO merge-shaped members while the derived total is '
        f'{_MERGE_SHAPED_TOTAL} (per provider: {by_provider}). Derived registry sizes: '
        f'github={_REGISTRY_SIZES["github"]}, gitlab={_REGISTRY_SIZES["gitlab"]}. Both '
        'providers register the merge-shaped surface, so an empty side means that provider '
        'stopped resolving and every parametrized arm below silently stopped covering it. A '
        'total-only check cannot see this: a halved population is still a population.'
    )


@pytest.mark.parametrize(
    'provider,key',
    [(p, k) for p in sorted(_MERGE_SHAPED) for k in _MERGE_SHAPED[p]],
    ids=[f'{p}:{k[1]}' for p in sorted(_MERGE_SHAPED) for k in _MERGE_SHAPED[p]],
)
def test_every_merge_shaped_verb_reaches_its_platform_queue_guard(provider, key):
    """(2b) Every registered merge-shaped verb consults the queue/train state.

    The guard vocabulary is DERIVED from each provider's own module text rather
    than listed, so a renamed helper or a newly added probe is covered without
    editing this file. What is asserted is that the handler's EXECUTABLE CODE
    references the platform queue/train surface, and that it does so BEFORE the
    handler can return a success envelope — a verb that probed only after
    asserting success would report a disposition it had not yet established.

    **Bound to the artifact, not to prose.** Both arms read
    ``first_queue_symbol`` / :func:`_code_without_prose`, which see only
    identifiers and only non-documentation text. Matching the raw handler source
    instead would satisfy both arms from the handler's own docstring — every
    merge-shaped handler documents the surface it guards — and the ordering arm
    could then never fail, since a docstring precedes every literal in the body.
    :func:`test_queue_guard_predicate_is_falsifiable` pins that the predicate
    reports NO hit for a handler that only talks about the queue.

    The provider asymmetry is real and deliberate: GitHub's queue is
    base-branch-scoped, GitLab's train is project-scoped, and GitLab's
    ``pr merge-queue`` reaches the train through its dedicated enqueue endpoint
    rather than through the read-only probe. Keying on the shared vocabulary
    rather than on one helper name is what lets one assertion cover all three
    shapes without flattening the asymmetry.
    """
    handler = _registry_handler_names(provider)[key]
    source = _handler_source(provider, handler)
    assert source, (
        f'{provider}:{handler} is registered under {key} but its source could not be located '
        f'in {[p.name for p in _PROVIDER_HANDLER_SOURCES[provider]]}. A handler whose body '
        'cannot be read is a member this parity check silently skips.'
    )

    hit = first_queue_symbol(source, handler)
    assert hit is not None, (
        f'{provider}:{handler} ({key[0]} {key[1]}) references no platform queue/train SYMBOL '
        'in its executable code. Every merge-shaped verb must establish the platform state '
        'before acting: an immediate merge on a queued target closes the PR unmerged, and '
        'an enqueue against an unconfigured target silently degrades to plain auto-merge. '
        'A docstring naming the queue does not satisfy this — the guard must be code.'
    )
    guard_at, guard_symbol = hit

    success_at = _code_without_prose(source).find(_SUCCESS_LITERAL)
    if success_at != -1:
        assert guard_at < success_at, (
            f'{provider}:{handler} reaches the platform queue/train surface only AFTER '
            f'its first {_SUCCESS_LITERAL} literal (guard {guard_symbol!r} at {guard_at}, '
            f'success at {success_at}). A verb that probes after asserting success reports '
            'a disposition it had not established when it claimed it.'
        )


def test_ordering_arm_covers_a_published_non_empty_population():
    """(2c) The ordering arm of (2b) is exercised by a NON-EMPTY, published subset.

    The per-member ordering assertion above only runs when the success literal is
    found (``if success_at != -1``). A handler that builds its success envelope
    with a different spelling, through a helper, or by dict mutation therefore
    contributes NO ordering check — and says nothing about it in the test output.
    Were every member to take that branch, the arm would cover nothing while all
    ``_MERGE_SHAPED_TOTAL`` parametrizations still reported green.

    This is the same published-population discipline the rest of the module
    follows: the exercising and skipping sets are derived here over the WHOLE
    merge-shaped population, and both counts plus the skipped member names are
    published, so an arm that has quietly shrunk is visible from the failure
    message alone rather than having to be inferred from a green run.
    """
    exercising: list[str] = []
    skipping: list[str] = []
    for provider in sorted(_MERGE_SHAPED):
        handler_names = _registry_handler_names(provider)
        for key in _MERGE_SHAPED[provider]:
            handler = handler_names[key]
            source = _handler_source(provider, handler)
            label = f'{provider}:{handler}'
            if source and _code_without_prose(source).find(_SUCCESS_LITERAL) != -1:
                exercising.append(label)
            else:
                skipping.append(label)

    assert len(exercising) + len(skipping) == _MERGE_SHAPED_TOTAL, (
        f'Ordering-arm population = {len(exercising) + len(skipping)}, but the derived '
        f'merge-shaped population is {_MERGE_SHAPED_TOTAL}. The two must agree, or this '
        'test is reporting coverage over a population it did not actually walk.'
    )
    assert exercising, (
        f'The ordering arm of (2b) is exercised by 0 of {_MERGE_SHAPED_TOTAL} merge-shaped '
        f'members — every member skipped it. Skipped: {sorted(skipping)}. The arm is guarded '
        f'by finding {_SUCCESS_LITERAL} in the handler\'s non-prose code, so a population-wide '
        'skip means that literal no longer matches how these handlers build their success '
        'envelope (a different spelling, a helper, or dict mutation). The per-member '
        'assertions would all still pass while asserting nothing about ordering.'
    )


#: A handler whose ONLY reference to the platform queue/train surface is prose:
#: a docstring and a comment. It never probes. This is the negative case (2b)
#: must reject — and the case a raw-text match accepts, which is precisely how
#: that arm became unfalsifiable.
_PROSE_ONLY_HANDLER = '''
def cmd_pr_prose_only(args):
    """Handle 'pr prose-only' — talks about the merge queue and the merge train.

    Documents the platform merge_queue surface at length, exactly as every real
    merge-shaped handler does, and probes none of it.
    """
    # A merge-train preflight belongs here and is deliberately absent.
    return {
        'status': 'success',
        'operation': 'pr_prose_only',
    }
'''

#: The positive control: the same handler with a real, executable guard whose
#: identifier names the surface. Pins that the narrowed predicate still SEES a
#: genuine guard — a check that rejected everything would be just as useless as
#: one that accepted everything.
_GUARDED_HANDLER = '''
def cmd_pr_guarded(args):
    """Handle 'pr guarded' — probes before it reports."""
    refusal = _refuse_on_required_merge_queue(args, 'pr_guarded')
    if refusal is not None:
        return refusal
    return {
        'status': 'success',
        'operation': 'pr_guarded',
    }
'''


def test_queue_guard_predicate_is_falsifiable():
    """The (2b) predicate REJECTS a handler that only talks about the queue.

    Asserted against synthetic handlers rather than the live tree, because the
    property under test is a property of the PREDICATE and must stay checkable
    even when every real handler is correctly guarded. Three arms:

    1. A raw-text match on the prose-only handler HITS — recording, executably,
       why the predicate had to be narrowed rather than leaving that as a claim
       in a comment.
    2. The identifier-bound predicate returns ``None`` for that same handler, so
       (2b) fails for it. This is the arm that makes (2b) falsifiable: without
       it, every parametrized member could pass on its docstring alone.
    3. The predicate still finds the guard in the positive control, and reports
       it BEFORE the success literal, so arm 2 is a real discrimination and not
       a predicate that rejects everything.
    """
    raw_hit = QUEUE_VOCAB_RE.search(_PROSE_ONLY_HANDLER)
    assert raw_hit is not None, (
        'The prose-only fixture no longer mentions the queue/train vocabulary in its '
        'documentation, so it cannot demonstrate the raw-text failure mode and arm 2 below '
        'would prove nothing. Restore the docstring/comment mentions.'
    )

    assert first_queue_symbol(_PROSE_ONLY_HANDLER, 'cmd_pr_prose_only') is None, (
        'The queue-guard predicate reported a hit for a handler that references the '
        'platform surface ONLY in its docstring and comments. It is therefore satisfiable '
        'by prose and assertion (2b) is vacuous — every merge-shaped handler documents the '
        'queue it guards, so the check would pass whether or not the guard exists.'
    )

    guarded = first_queue_symbol(_GUARDED_HANDLER, 'cmd_pr_guarded')
    assert guarded is not None, (
        'The queue-guard predicate missed a real, executable guard '
        '(`_refuse_on_required_merge_queue`). A predicate that rejects everything is no '
        'more useful than one that accepts everything.'
    )
    guard_at, _ = guarded
    success_at = _code_without_prose(_GUARDED_HANDLER).find(_SUCCESS_LITERAL)
    assert success_at != -1, 'The positive-control fixture lost its success literal.'
    assert guard_at < success_at, (
        f'The positive control places its guard at {guard_at} but its success literal at '
        f'{success_at}; the ordering arm cannot be exercised against it.'
    )


def test_prose_blanking_is_offset_preserving():
    """:func:`_code_without_prose` blanks documentation without shifting offsets.

    The ordering assertion compares an identifier offset taken from the ORIGINAL
    text against a success-literal offset taken from the blanked text. If
    blanking changed the length, the two would be measured on different rulers
    and the comparison would silently drift — a wrong verdict rather than a
    failure.
    """
    blanked = _code_without_prose(_PROSE_ONLY_HANDLER)

    assert len(blanked) == len(_PROSE_ONLY_HANDLER), (
        f'Blanked length {len(blanked)} != original {len(_PROSE_ONLY_HANDLER)}. Offsets '
        'from the two views are no longer comparable.'
    )
    assert 'merge-train preflight' not in blanked, (
        'A comment survived the blanking, so comment text can still satisfy a text search '
        'over the blanked view.'
    )
    assert 'merge_queue surface at length' not in blanked, (
        'A docstring survived the blanking, so docstring text can still satisfy a text '
        'search over the blanked view.'
    )
    assert _SUCCESS_LITERAL in blanked, (
        'The success literal was blanked along with the documentation. It is executable '
        'code and must survive, or the ordering arm loses its right-hand side.'
    )


# ---------------------------------------------------------------------------
# (3) Enumeration completeness, population-derived
# ---------------------------------------------------------------------------


def _declared_params() -> list[str]:
    """The step's declared param population, from its ``configurable:`` frontmatter."""
    text = _read(_BRANCH_CLEANUP)
    _, _, after = text.partition('configurable:')
    front, _, _ = after.partition('\n---')
    return _CONFIGURABLE_KEY_RE.findall(front)


def _one_stop_enumerated_params() -> list[str]:
    """The params the one-stop ``step-params get`` sentence enumerates.

    Parsed out of the PROSE, independently of the frontmatter, so the two sides
    of the completeness check are genuinely different derivations rather than the
    same list compared with itself.
    """
    match = _ONE_STOP_SENTENCE_RE.search(_read(_BRANCH_CLEANUP))
    if match is None:
        return []
    return [token for token in _BACKTICKED_RE.findall(match.group(1)) if '_' in token]


def test_one_stop_enumeration_names_every_declared_param():
    """(3) The one-stop read enumerates the step's whole declared param population.

    Both sides are derived, and from different places: the left from the
    ``configurable:`` frontmatter, the right from the enumeration sentence in
    § "Conflict-Severity Classifier". A param declared but missing from the
    enumeration is one a later section binds off a ``params`` object that was
    never documented as carrying it — the drift that left ``use_merge_queue`` and
    the four merge-hold knobs unlisted while four sections read them.
    """
    declared = _declared_params()
    enumerated = _one_stop_enumerated_params()

    assert declared, (
        'ZERO params were derived from the `configurable:` frontmatter of '
        f'{_BRANCH_CLEANUP.name}. Every assertion below would pass vacuously against an '
        'empty population.'
    )
    assert enumerated, (
        'The one-stop `step-params get` enumeration sentence was not found in '
        f'{_BRANCH_CLEANUP.name} § "Conflict-Severity Classifier". Without it there is no '
        'documented one-stop read to check the declared population against.'
    )

    missing = [key for key in declared if key not in enumerated]
    assert not missing, (
        f'Declared param population size = {len(declared)} {declared}; the one-stop '
        f'enumeration names {len(enumerated)} {enumerated}. Missing from the enumeration: '
        f'{missing}. Every param the step declares is read off the SAME one-stop `params` '
        'object, so one left out of the enumeration is a read no reader of that section '
        'knows to expect.'
    )


# ---------------------------------------------------------------------------
# (4) Routing observability
# ---------------------------------------------------------------------------


def test_every_use_merge_queue_consumption_site_is_observable():
    """(4a) Each ``use_merge_queue`` read carries a mandatory observability line.

    Asserts a **per-site relationship**, not merely equal totals. Equal counts are
    satisfied by a document that lost one site's marker and duplicated another's —
    exactly the compensating-error shape a guard like this exists to catch, and
    a real risk here because this guard has already reported green over a site it
    could not see. Each derived read is therefore paired with the FIRST
    observability marker that follows it, and the pairing must be injective: two
    reads may not claim the same marker, and no marker may be left over.

    Neither side is pinned to a cardinality literal, deliberately: a hardcoded
    count would have to be hand-edited every time a site is added.
    """
    text = _read(_BRANCH_CLEANUP)
    read_offsets = [m.start() for m in _USE_MERGE_QUEUE_READ_RE.finditer(text)]
    marker_offsets = [
        m.start() for m in re.finditer(re.escape(_OBSERVABILITY_MARKER), text)
    ]

    assert read_offsets, (
        'No `use_merge_queue` consumption site was derived from '
        f'{_BRANCH_CLEANUP.name}. The routing is demonstrably driven by that param, so an '
        'empty derivation means the read marker stopped matching and this check is vacuous.'
    )

    # Pair each read with the first marker at or after it. A site whose marker was
    # deleted claims the NEXT site's marker, which then leaves the last read
    # unpaired — so a compensating duplicate elsewhere cannot mask the deletion.
    claimed: dict[int, int] = {}
    for read_at in read_offsets:
        following = [off for off in marker_offsets if off >= read_at]
        assert following, (
            f'The `use_merge_queue` consumption site at offset {read_at} is followed by no '
            f'{_OBSERVABILITY_MARKER} block. Every site that BINDS the value must emit a '
            'decision-log line naming the bound value, its provenance, and the branch it '
            'selects — otherwise which branch a run took is unreconstructible from the log.'
        )
        marker_at = following[0]
        assert marker_at not in claimed, (
            f'Two `use_merge_queue` consumption sites (offsets {claimed[marker_at]} and '
            f'{read_at}) share a single {_OBSERVABILITY_MARKER} block at offset {marker_at}. '
            'A site whose own block was deleted is borrowing its neighbour\'s; equal totals '
            'would have hidden this.'
        )
        claimed[marker_at] = read_at

    assert len(claimed) == len(marker_offsets), (
        f'{len(marker_offsets)} {_OBSERVABILITY_MARKER} block(s) exist but only '
        f'{len(claimed)} are claimed by a consumption site. An unclaimed block is either a '
        'duplicate masking a deletion elsewhere, or a marker whose site stopped matching '
        'the derivation — both are the vacuity this guard exists to prevent.'
    )


def test_every_observability_line_names_the_value_and_its_provenance():
    """(4b) The observability lines are falsifiable, not decorative.

    A line that logged only "routing decided" would satisfy a marker count while
    recording nothing a reader could act on. Each must carry the bound value and
    where it came from.
    """
    text = _read(_BRANCH_CLEANUP)
    logged = [
        block
        for block in _fenced_blocks(text)
        if 'manage-logging' in block and 'use_merge_queue={use_merge_queue}' in block
    ]
    expected = text.count(_OBSERVABILITY_MARKER)

    assert logged, (
        'No decision-log invocation names `use_merge_queue={use_merge_queue}` anywhere in '
        f'{_BRANCH_CLEANUP.name}. Asserted before the equality below because a document '
        'carrying zero observability blocks would otherwise satisfy `0 == 0` and report '
        'green against a completely unobservable routing.'
    )
    assert len(logged) == expected, (
        f'{expected} observability block(s) are declared but only {len(logged)} '
        'decision-log invocation(s) actually name `use_merge_queue={use_merge_queue}`.'
    )
    for block in logged:
        assert 'provenance' in block, (
            'An observability decision-log line does not name the value\'s provenance. '
            'Without it a reader cannot tell whether the bound value came from the '
            'one-stop params object or from an undocumented second read.'
        )


def test_merge_routing_decision_precedes_the_dispatch_it_selects():
    """(4c) The routing line is emitted BEFORE the dispatch, not after it.

    An observability line written after the dispatch records what happened but
    cannot be read as the reason it happened — and on an aborted run it is never
    written at all, which is exactly the run whose routing a reader most needs.
    """
    text = _read(_BRANCH_CLEANUP)
    heading = '#### Merge routing (`use_merge_queue`)'
    start = text.find(heading)
    assert start != -1, f'{_BRANCH_CLEANUP.name} carries no {heading!r} section.'
    section = text[start:]

    log_at = section.find('Branch cleanup merge routing: use_merge_queue=')
    assert log_at != -1, (
        'The merge-routing section emits no decision-log line naming the bound '
        '`use_merge_queue` value and the verb about to be dispatched.'
    )

    dispatch_at = -1
    for block in _fenced_blocks(section):
        if _EXECUTOR_MARKER in block and _CI_NOTATION in block and _PR_VERB_RE.search(block):
            dispatch_at = section.find(block)
            break
    assert dispatch_at != -1, (
        'The merge-routing section issues no merge-shaped `ci pr` dispatch, so the '
        'ordering this test asserts has nothing to order against — the section moved and '
        'this guard is now anchored to the wrong place.'
    )
    assert log_at < dispatch_at, (
        f'The merge-routing decision-log line appears at {log_at}, AFTER the dispatch it '
        f'selects at {dispatch_at}. Bypass-before-dispatch ordering requires the routing '
        'decision be recorded before the verb it chooses is issued.'
    )


# ---------------------------------------------------------------------------
# Queue-landing gate: anchored BEFORE the prune, never after it
# ---------------------------------------------------------------------------


def test_queue_landing_gate_precedes_and_guards_the_branch_prune():
    """The landing corroboration is anchored to a pre-prune observation.

    ``enqueued: true`` says the PR joined the queue, not that the queue merged
    it. The post-merge tail — worktree removal, ``switch-and-pull``, and above all
    ``prune-local-and-remote-ref`` — assumes a landed merge, and pruning the head
    branch out from under a still-queued PR destroys the ref the queue merge
    needs.

    This assertion is deliberately bound to the gate's position and to the guard
    the prune section carries, NOT to any state observable after the prune: a
    prune that has already run cannot witness whether it should have.
    """
    text = _read(_BRANCH_CLEANUP)
    gate_heading = '### Wait for the Queue Merge to Land (bounded)'
    gate_at = text.find(gate_heading)
    assert gate_at != -1, (
        f'{_BRANCH_CLEANUP.name} carries no {gate_heading!r} section. Without it the '
        'post-merge tail runs on a still-queued PR.'
    )

    # Anchor on the prune DISPATCH, not on a prose mention of the verb: the gate
    # itself names `prune-local-and-remote-ref` while explaining what it must NOT
    # let run, so a plain substring search lands inside the gate and collapses the
    # section this test then inspects to nothing.
    prune_at = -1
    for block in _fenced_blocks(text):
        if _EXECUTOR_MARKER in block and 'prune-local-and-remote-ref' in block:
            found = text.find(block)
            if found > gate_at:
                prune_at = found
                break
    assert prune_at != -1, (
        'No `prune-local-and-remote-ref` DISPATCH follows the queue-landing gate — the '
        'ordering this test asserts has nothing to order against.'
    )
    assert gate_at < prune_at, (
        f'The queue-landing gate appears at {gate_at}, AFTER the branch prune at '
        f'{prune_at}. The gate must precede every post-merge action it governs.'
    )

    gate_section = text[gate_at:prune_at]
    assert 'merge_queue_wait_budget_seconds' in gate_section, (
        'The queue-landing gate declares no bound. An unbounded wait on a platform this '
        'step does not control is not a gate.'
    )
    for obligation in ('merge_lock release', 'without pruning'):
        assert obligation in gate_section, (
            f'The queue-landing gate does not state its {obligation!r} obligation. Its '
            'failure path MUST release the merge mutex and return WITHOUT pruning — a '
            'held lock blocks every other plan, and a prune destroys the queue\'s ref.'
        )

    # Anchor the guard window on the ENCLOSING heading rather than on a fixed
    # character count: a fixed window fails without a real regression as soon as
    # the section grows past it, and a prune offset below the window size would
    # make the start index negative and slice from the END of the document.
    heading_at = text.rfind(_PRUNE_SECTION_HEADING, 0, prune_at)
    assert heading_at != -1, (
        f'The enclosing heading {_PRUNE_SECTION_HEADING!r} was not found anywhere before '
        f'the `prune-local-and-remote-ref` dispatch at {prune_at}. This test anchors the '
        'prune-guard window on that heading; if the section was renamed, re-point this '
        'anchor at the new heading rather than widening the window back to a fixed size.'
    )

    prune_guard = text[heading_at:prune_at]
    assert '{merge_landed}' in prune_guard, (
        'The `prune-local-and-remote-ref` dispatch is not gated on `{merge_landed}`. '
        'Without the guard the prune runs whether or not the queue merge landed, which is '
        'the destructive outcome the gate exists to prevent.'
    )


# =============================================================================
# (6) The CI `overall_status` vocabulary the positive-shape requirement names is
#     PARITY-GUARDED against both provider definitions, never merely transcribed
# =============================================================================
#
# The CI-gate section's "Positive shape requirement" admits a snapshot only when
# its `overall_status` is drawn from the handler's vocabulary, and names the four
# values inline. A hand-copied population standing in for an authoritative
# definition goes stale SILENTLY IN BOTH DIRECTIONS: a handler that gains a value
# makes the gate reject a valid snapshot, one that loses a value makes it admit an
# unsupported one — and the gate's whole purpose is to STOP on a shape it cannot
# vouch for, so a stale list is a false verdict either way.
#
# The definition is NOT singular. `_derive_overall_status` exists once per
# provider, and the definition population below is DERIVED by scanning the bundle
# tree rather than named — so a third provider added later joins the parity check
# on arrival instead of drifting outside a two-entry list nobody revisits.
#
# NEITHER IS THE DOCUMENTED SIDE. This guard originally bound one document — the
# branch-cleanup positive-shape requirement — and stayed green while the CI
# abstraction's own API contract went on declaring a THREE-value set for the same
# field, in two places, omitting `none`. A parity guard that covers one statement
# of a closed set does not protect the set; it protects that statement, and every
# unguarded sibling is free to drift exactly as the guarded one no longer can. So
# the doc side below is a POPULATION of sites, each with its own extractor,
# because the sites state the set in different forms (a prose sentence, a TOON
# alternation, a bullet block) and a single regex silently covers only the form it
# was written for.

#: The branch-cleanup sentence that names the vocabulary, and the backticked
#: tokens inside it. Line-scoped and non-greedy: a document-wide match would sweep
#: in every unrelated backticked token and inflate the doc side until the equality
#: could not fail.
_VOCAB_SENTENCE_RE = re.compile(
    r"an `overall_status` drawn from the handler's vocabulary\s*[—-]\s*(`.+?)\.",
    re.MULTILINE,
)

#: The CI API contract document, which states the same set twice in two forms.
_CI_API_CONTRACT: Path = _SKILLS / 'tools-integration-ci' / 'standards' / 'api-contract.md'

#: The `checks status` response-schema line. Requires an ALTERNATION (two or more
#: `|`-joined values), so a single-valued illustrative `overall_status: pending`
#: elsewhere in the document is not mistaken for a declaration of the set.
_API_TOON_ALTERNATION_RE = re.compile(
    r'^overall_status: ([a-z_]+(?:\|[a-z_]+)+)$', re.MULTILINE
)

#: The `Overall Status Logic` bullet block in the same document — one `- \`value\`:`
#: row per member.
_API_LOGIC_BLOCK_RE = re.compile(
    r'\*\*Overall Status Logic\*\*:\n((?:- `[a-z_]+`:[^\n]*\n)+)'
)

#: The function whose returned literals ARE the vocabulary.
_DERIVE_FN_NAME = '_derive_overall_status'


def _vocabulary_definition_modules() -> list[Path]:
    """Every bundle module that DEFINES ``_derive_overall_status``.

    Derived by scanning, never listed. CodeRabbit's report of this finding named
    one provider as "the authoritative definition"; there are two, and a guard
    bound to a hand-written pair would repeat the same mistake one level up.
    """
    needle = f'def {_DERIVE_FN_NAME}('
    return sorted(
        path
        for path in _SKILLS.rglob('*.py')
        if needle in path.read_text(encoding='utf-8')
    )


def _returned_status_literals(path: Path) -> frozenset[str]:
    """The set of first-tuple-element string literals ``_derive_overall_status`` returns.

    Bound to the EXECUTABLE code via ``ast``, not to the source text: the
    docstring of both definitions also spells the four values out, so a text scan
    would be satisfied by prose a gutted function could keep verbatim.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != _DERIVE_FN_NAME:
            continue
        for ret in (n for n in ast.walk(node) if isinstance(n, ast.Return)):
            value = ret.value
            if isinstance(value, ast.Tuple) and value.elts:
                value = value.elts[0]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                values.add(value.value)
    return frozenset(values)


_VOCAB_DEFINITION_MODULES = _vocabulary_definition_modules()

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it: an empty
# population is a pytest SKIP, not a failure, and a parity check over zero
# definitions is vacuously green.
assert _VOCAB_DEFINITION_MODULES, (
    f'no module under {_SKILLS} defines {_DERIVE_FN_NAME} — the vocabulary-parity '
    'population is vacuous and every assertion below would pass over an empty set'
)


def _branch_cleanup_vocabulary() -> frozenset[str]:
    """The values the branch-cleanup positive-shape requirement names."""
    text = _BRANCH_CLEANUP.read_text(encoding='utf-8')
    match = _VOCAB_SENTENCE_RE.search(text)
    assert match is not None, (
        f'{_BRANCH_CLEANUP.name} no longer states the `overall_status` vocabulary in the '
        'form this guard parses. The positive-shape requirement is only as good as the '
        'population it admits, so re-point this regex at the new wording rather than '
        'dropping the parity check.'
    )
    return frozenset(_BACKTICKED_RE.findall(match.group(1)))


def _api_contract_schema_vocabulary() -> frozenset[str]:
    """The values the `checks status` response schema declares as an alternation."""
    text = _CI_API_CONTRACT.read_text(encoding='utf-8')
    matches = _API_TOON_ALTERNATION_RE.findall(text)
    assert len(matches) == 1, (
        f'{_CI_API_CONTRACT.name} carries {len(matches)} `overall_status` alternation '
        f'line(s) ({matches}), expected exactly one. Zero means the response schema no '
        'longer declares the set in the form this guard parses — re-point the regex '
        'rather than dropping the site, because an unparsed site is an unguarded one. '
        'More than one means the document states the set in two schema blocks that this '
        'extractor would silently union.'
    )
    return frozenset(matches[0].split('|'))


def _api_contract_logic_vocabulary() -> frozenset[str]:
    """The values the `Overall Status Logic` bullet block enumerates."""
    text = _CI_API_CONTRACT.read_text(encoding='utf-8')
    match = _API_LOGIC_BLOCK_RE.search(text)
    assert match is not None, (
        f'{_CI_API_CONTRACT.name} no longer carries an `Overall Status Logic` bullet '
        'block in the form this guard parses. Re-point the regex rather than dropping '
        'the site — this block is what a consumer builds its branch table from.'
    )
    return frozenset(_BACKTICKED_RE.findall(match.group(1)))


#: Every DOCUMENTED statement of the `overall_status` closed set, each with the
#: extractor its own form needs. Keyed by a human-readable site label so a failure
#: names WHICH statement drifted rather than only which file.
#:
#: This is the population the guard's coverage claim is made over. It is
#: hand-listed, and that is a real residual limit rather than an oversight: a site
#: is a passage inside a document, not a file, so no scan enumerates them —
#: which is precisely why `test_the_documented_sites_are_plural` publishes the
#: size, so a shrinking population is visible instead of silently narrowing the
#: guard back to the single-site shape that let a sibling drift.
_DOC_VOCABULARY_SITES: dict[str, Callable[[], frozenset[str]]] = {
    f'{_BRANCH_CLEANUP.name} § positive-shape requirement': _branch_cleanup_vocabulary,
    f'{_CI_API_CONTRACT.name} § checks status response schema': (
        _api_contract_schema_vocabulary
    ),
    f'{_CI_API_CONTRACT.name} § Overall Status Logic': _api_contract_logic_vocabulary,
}


class TestOverallStatusVocabularyParity:
    """EVERY documented `overall_status` list equals what EVERY provider returns.

    Two independently derived populations — the documented sites in
    :data:`_DOC_VOCABULARY_SITES`, and the ``_derive_overall_status``
    returned-literal set of each definition module — with every cross pair
    asserted equal. A handler change therefore fails the build here instead of
    silently invalidating the CI gate; a provider drifting away from its sibling
    fails too; and so does a document that states the set and falls behind, which
    is the failure the single-site shape of this guard could not see.
    """

    def test_the_definition_population_is_published_and_plural(self):
        """The scan found the definitions, and found more than one of them.

        Published as a size so a shrinking scan is visible on the failure message.
        The plurality assertion is the finding's own correction made structural:
        the reported "one authoritative definition" was wrong, and a guard that
        could pass while seeing only one provider would re-admit that error.
        """
        assert len(_VOCAB_DEFINITION_MODULES) >= 2, (
            f'the scan found only {len(_VOCAB_DEFINITION_MODULES)} definition(s) of '
            f'{_DERIVE_FN_NAME} '
            f'({[p.name for p in _VOCAB_DEFINITION_MODULES]}) — cross-provider parity '
            'cannot be demonstrated from a single side, so either a provider module '
            'moved or the scan regressed'
        )

    def test_the_documented_sites_are_plural(self):
        """More than one document states this set, and the guard covers them all.

        Published as a size because the site population is the one side of this
        guard that no scan derives (a site is a passage, not a file). The single
        assertion that matters is plurality: a guard narrowed back to one site
        would pass while every other statement of the set drifted, which is the
        exact state this section was extended to end.
        """
        assert len(_DOC_VOCABULARY_SITES) >= 2, (
            f'only {len(_DOC_VOCABULARY_SITES)} documented site '
            f'({sorted(_DOC_VOCABULARY_SITES)}) is covered. A one-site parity guard '
            'protects that statement, not the closed set: the CI API contract declared a '
            'three-value set for this field, in two places, for as long as this guard read '
            'branch-cleanup.md alone. Add the site back rather than shrinking the coverage.'
        )

    @pytest.mark.parametrize('site', sorted(_DOC_VOCABULARY_SITES))
    def test_each_documented_site_is_non_empty(self, site):
        """Each doc side is real content, not an empty match the equality accepts."""
        doc_vocab = _DOC_VOCABULARY_SITES[site]()
        assert doc_vocab, (
            f'{site} matched its extractor but yielded no values — an empty doc side '
            'would compare equal to an empty derived side and the parity check would be '
            'vacuous'
        )

    @pytest.mark.parametrize('site', sorted(_DOC_VOCABULARY_SITES))
    @pytest.mark.parametrize(
        'module', _VOCAB_DEFINITION_MODULES, ids=lambda p: p.parent.parent.name
    )
    def test_definition_vocabulary_matches_each_documented_site(self, module, site):
        """Every provider's returned-literal set equals every documented statement."""
        derived = _returned_status_literals(module)
        assert derived, (
            f'{module} defines {_DERIVE_FN_NAME} but no string literal was read off its '
            'return statements — the ast derivation regressed, and an empty derived side '
            'would make this comparison vacuous'
        )
        doc_vocab = _DOC_VOCABULARY_SITES[site]()
        assert derived == doc_vocab, (
            f'{module.name}:{_DERIVE_FN_NAME} returns {sorted(derived)} but {site} admits '
            f'{sorted(doc_vocab)}. A consumer reading that site would '
            f'{"reject a valid" if derived - doc_vocab else "admit an unsupported"} '
            'value. Update every side together — the handler is authoritative.'
        )

    def test_the_providers_agree_with_each_other(self):
        """Cross-provider parity, asserted directly rather than inferred via the doc.

        Each provider is compared to the doc above, so agreement between them
        follows — but only while the doc assertion holds. Asserting it directly is
        what keeps the cross-provider claim standing on its own evidence, and names
        the divergence per-provider when it breaks.
        """
        by_module = {p: _returned_status_literals(p) for p in _VOCAB_DEFINITION_MODULES}
        distinct = set(by_module.values())
        assert len(distinct) == 1, (
            'the provider definitions of '
            f'{_DERIVE_FN_NAME} disagree: '
            f'{ {p.name: sorted(v) for p, v in by_module.items()} }. One provider gained or '
            'lost a status the other did not, so a caller cannot rely on a single vocabulary.'
        )
