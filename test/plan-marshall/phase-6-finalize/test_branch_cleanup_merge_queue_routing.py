#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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
    missed at pass 2).

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
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

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

#: The candidate merge-shaped ``pr`` sub-verbs. This is the VOCABULARY the
#: derivations filter against — not a membership claim. WHICH of these are
#: dispatched, and which are registered, is derived below.
_MERGE_SHAPED_VERBS: frozenset[str] = frozenset({'merge', 'auto-merge', 'safe-merge', 'merge-queue'})

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

#: One provider ``handlers: HandlerMap`` registry literal.
_HANDLER_MAP_RE = re.compile(r'handlers:\s*HandlerMap\s*=\s*\{(.*?)\n    \}', re.DOTALL)

#: One registry row: a ``('group', 'verb'[, 'sub'])`` key.
_HANDLER_ROW_RE = re.compile(r"\(\s*('[^']+'(?:\s*,\s*'[^']+')*)\s*\)\s*:")

#: A top-level ``def name(`` in a handler source.
_DEF_RE = re.compile(r'^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', re.MULTILINE)

#: A symbol that touches the platform queue / train state. Derived per provider
#: from the module's own vocabulary rather than listed, so a guard renamed or a
#: new probe helper added is picked up without editing this file.
_QUEUE_VOCAB_RE = re.compile(r'(?i)\bmerge[_-]?(?:queue|train)')

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
    """
    match = _HANDLER_MAP_RE.search(_read(_PROVIDER_MODULES[provider]))
    assert match, (
        f'No `handlers: HandlerMap = {{...}}` literal was found in '
        f'{_PROVIDER_MODULES[provider].name}. The registry IS the population; without it '
        'every parity assertion below is vacuous.'
    )
    keys: list[tuple[str, ...]] = []
    for raw in _HANDLER_ROW_RE.findall(match.group(1)):
        keys.append(tuple(part.strip().strip("'") for part in raw.split(',')))
    return keys


def _registry_handler_names(provider: str) -> dict[tuple[str, ...], str]:
    """Map each registry key to the handler symbol it is bound to."""
    match = _HANDLER_MAP_RE.search(_read(_PROVIDER_MODULES[provider]))
    assert match
    bindings: dict[tuple[str, ...], str] = {}
    for line in match.group(1).splitlines():
        row = _HANDLER_ROW_RE.search(line)
        if row is None:
            continue
        key = tuple(part.strip().strip("'") for part in row.group(1).split(','))
        _, _, handler = line.partition('):')
        bindings[key] = handler.strip().rstrip(',').strip()
    return bindings


def _merge_shaped_registry_keys(provider: str) -> list[tuple[str, ...]]:
    """The merge-shaped subset of a provider's registry — derived, not listed."""
    return [
        key
        for key in _registry_keys(provider)
        if len(key) == 2 and key[0] == 'pr' and key[1] in _MERGE_SHAPED_VERBS
    ]


_REGISTRY_SIZES: dict[str, int] = {p: len(_registry_keys(p)) for p in _PROVIDER_MODULES}
_MERGE_SHAPED: dict[str, list[tuple[str, ...]]] = {
    p: _merge_shaped_registry_keys(p) for p in _PROVIDER_MODULES
}
_MERGE_SHAPED_TOTAL: int = sum(len(v) for v in _MERGE_SHAPED.values())


def _handler_source(provider: str, symbol: str) -> str:
    """The source text of one handler function, across the provider's modules."""
    for path in _PROVIDER_HANDLER_SOURCES[provider]:
        text = _read(path)
        marker = f'\ndef {symbol}('
        start = text.find(marker)
        if start == -1:
            continue
        body_start = start + 1
        nxt = _DEF_RE.search(text, body_start + 1)
        end = nxt.start() if nxt else len(text)
        return text[body_start:end]
    return ''


def test_registry_populations_are_published_and_plausible():
    """(2a) All three derived sizes are published, and none is vacuous.

    A parity check that ran against an empty or half-read registry would report
    "every member passes" while covering nothing. Publishing the three sizes in
    the failure message makes that state self-evident from the test output.
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
    assert _MERGE_SHAPED_TOTAL == 8, (
        f'Derived merge-shaped subset size = {_MERGE_SHAPED_TOTAL}, expected 8 '
        f'(4 verbs x 2 providers). Derived registry sizes: github={_REGISTRY_SIZES["github"]}, '
        f'gitlab={_REGISTRY_SIZES["gitlab"]}. Per provider the merge-shaped members are '
        f'{ {p: [k[1] for k in v] for p, v in _MERGE_SHAPED.items()} }. A subset smaller than '
        'the closed vocabulary means a verb is registered under a name this derivation does '
        'not see — which is exactly how cmd_pr_auto_merge was missed twice.'
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
    editing this file. What is asserted is that the handler body references the
    platform queue/train surface at all, and that it does so BEFORE it can return
    a success envelope — a verb that probed only after asserting success would
    report a disposition it had not yet established.

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

    hit = _QUEUE_VOCAB_RE.search(source)
    assert hit, (
        f'{provider}:{handler} ({key[0]} {key[1]}) never references the platform '
        'queue/train surface. Every merge-shaped verb must establish the platform state '
        'before acting: an immediate merge on a queued target closes the PR unmerged, and '
        'an enqueue against an unconfigured target silently degrades to plain auto-merge.'
    )

    success_at = source.find(_SUCCESS_LITERAL)
    if success_at != -1:
        assert hit.start() < success_at, (
            f'{provider}:{handler} references the platform queue/train surface only AFTER '
            f'its first {_SUCCESS_LITERAL} literal (guard at {hit.start()}, success at '
            f'{success_at}). A verb that probes after asserting success reports a '
            'disposition it had not established when it claimed it.'
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

    The two sides are counted independently — reads on one side, observability
    markers on the other — and compared. Adding a fifth consumption site without
    its decision-log line fails here; so does deleting an observability block
    from an existing site.
    """
    text = _read(_BRANCH_CLEANUP)
    reads = _USE_MERGE_QUEUE_READ_RE.findall(text)
    markers = text.count(_OBSERVABILITY_MARKER)

    assert reads, (
        'No `use_merge_queue` consumption site was derived from '
        f'{_BRANCH_CLEANUP.name}. The routing is demonstrably driven by that param, so an '
        'empty derivation means the read marker stopped matching and this check is vacuous.'
    )
    assert markers == len(reads), (
        f'Derived {len(reads)} `use_merge_queue` consumption site(s) but {markers} '
        f'{_OBSERVABILITY_MARKER} block(s). Every site that BINDS the value must emit a '
        'decision-log line naming the bound value, its provenance, and the branch it '
        'selects — otherwise which branch a run took is unreconstructible from the log.'
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

    prune_guard = text[prune_at - 2000 : prune_at]
    assert '{merge_landed}' in prune_guard, (
        'The `prune-local-and-remote-ref` dispatch is not gated on `{merge_landed}`. '
        'Without the guard the prune runs whether or not the queue merge landed, which is '
        'the destructive outcome the gate exists to prevent.'
    )
