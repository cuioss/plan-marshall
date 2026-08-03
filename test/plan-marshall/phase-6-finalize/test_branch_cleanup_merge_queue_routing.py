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

===========================================  =========  =========
predicate                                    hits/8 on  hits/8 on
                                             live tree  mutants
===========================================  =========  =========
raw-text search of the handler source              8/8        7/8
identifier-bound (:func:`_first_queue_symbol`)     8/8        0/8
===========================================  =========  =========

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

import io
import re
import tokenize
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
#:
#: Matched ONLY against IDENTIFIER tokens of the handler under test (see
#: :func:`_first_queue_symbol`), never against its raw source text. Against raw
#: text the pattern is satisfied by the handler's own DOCSTRING — every
#: merge-shaped handler documents the queue/train surface it guards — so the
#: predicate would report a hit for a handler that merely talks about the queue
#: and never probes it, and the ordering arm below could not fail at all,
#: because a docstring necessarily precedes every executable literal. Binding
#: the match to identifiers binds it to the artifact under test: the executable
#: code. :func:`test_queue_guard_predicate_is_falsifiable` locks that property.
#:
#: Deliberately UNANCHORED — no leading ``\b``. Identifiers carry the vocabulary
#: mid-token (``skip_merge_queue_preflight``, ``_refuse_on_required_merge_queue``,
#: ``_probe_merge_train_state``, ``_MERGE_TRAIN_INELIGIBLE_HINT``), and ``_`` is
#: a word character, so a word-boundary anchor matches only the identifiers that
#: BEGIN with the vocabulary. Against prose the anchor is invisible — every prose
#: mention has real boundaries — which is why it survives a raw-text match and
#: silently under-matches the moment the predicate is bound to code.
_QUEUE_VOCAB_RE = re.compile(r'(?i)merge[_-]?(?:queue|train)')

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


def _line_starts(source: str) -> list[int]:
    """Absolute character offset at which each 1-based source line begins.

    Lets a ``(row, col)`` token position be converted back to the absolute
    offset the ordering assertion compares on, so every position this module
    reports is an offset into the ORIGINAL handler text.
    """
    starts = [0, 0]
    position = 0
    for line in source.splitlines(keepends=True):
        position += len(line)
        starts.append(position)
    return starts


def _tokens(source: str) -> list[tokenize.TokenInfo]:
    """Tokenize one handler fragment.

    Deliberately un-guarded: a fragment that cannot be tokenized is a handler
    this module cannot reason about, and a loud error is the honest outcome —
    swallowing it would silently downgrade every derivation below to "no hits
    found", which is indistinguishable from a passing check.
    """
    return list(tokenize.generate_tokens(io.StringIO(source).readline))


def _first_queue_symbol(source: str, own_symbol: str) -> tuple[int, str] | None:
    """First ``(offset, identifier)`` in ``source`` naming the queue/train surface.

    The predicate behind assertion (2b), and it is deliberately narrow in two
    ways — each closing a way the check could pass without the property holding:

    * **Identifiers only.** Docstrings, comments and string literals are excluded
      by construction, because only ``NAME`` tokens are considered. A handler
      that merely *describes* the queue in prose therefore yields ``None``. This
      is the load-bearing narrowing: matching raw text made both arms of (2b)
      satisfiable by the handler docstrings, and made the ordering arm
      structurally incapable of failing.
    * **Not the handler's own name.** ``cmd_pr_merge_queue`` contains the
      vocabulary in its own identifier, so an unfiltered scan would match the
      ``def`` line of exactly the two verbs whose guard matters most — again at
      an offset preceding every literal, so again unfalsifiable.

    Returns ``None`` when the handler references no queue/train symbol.
    """
    starts = _line_starts(source)
    for token in _tokens(source):
        if token.type != tokenize.NAME or token.string == own_symbol:
            continue
        if _QUEUE_VOCAB_RE.search(token.string):
            row, col = token.start
            return starts[row] + col, token.string
    return None


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
    starts = _line_starts(source)
    chars = list(source)
    statement_start = True
    depth = 0
    for token in _tokens(source):
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
    editing this file. What is asserted is that the handler's EXECUTABLE CODE
    references the platform queue/train surface, and that it does so BEFORE the
    handler can return a success envelope — a verb that probed only after
    asserting success would report a disposition it had not yet established.

    **Bound to the artifact, not to prose.** Both arms read
    :func:`_first_queue_symbol` / :func:`_code_without_prose`, which see only
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

    hit = _first_queue_symbol(source, handler)
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
    raw_hit = _QUEUE_VOCAB_RE.search(_PROSE_ONLY_HANDLER)
    assert raw_hit is not None, (
        'The prose-only fixture no longer mentions the queue/train vocabulary in its '
        'documentation, so it cannot demonstrate the raw-text failure mode and arm 2 below '
        'would prove nothing. Restore the docstring/comment mentions.'
    )

    assert _first_queue_symbol(_PROSE_ONLY_HANDLER, 'cmd_pr_prose_only') is None, (
        'The queue-guard predicate reported a hit for a handler that references the '
        'platform surface ONLY in its docstring and comments. It is therefore satisfiable '
        'by prose and assertion (2b) is vacuous — every merge-shaped handler documents the '
        'queue it guards, so the check would pass whether or not the guard exists.'
    )

    guarded = _first_queue_symbol(_GUARDED_HANDLER, 'cmd_pr_guarded')
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
