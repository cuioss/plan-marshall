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
import sys
import tokenize
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT
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

#: The interpreter floor ``first_queue_symbol`` depends on: PEP 701 made an
#: f-string tokenize into its interpolated parts, which is what lets the
#: identifier-bound predicate see inside one.
_PEP_701_FLOOR: tuple[int, int] = (3, 12)

#: The project's packaging metadata — the single source for the DECLARED floor.
_PYPROJECT: Path = Path(PROJECT_ROOT) / 'pyproject.toml'

#: The lower bound of a ``requires-python`` specifier.
_REQUIRES_PYTHON_FLOOR_RE = re.compile(r'>=\s*(\d+)\.(\d+)')


def _declared_python_floor() -> tuple[int, int]:
    """Return the ``project.requires-python`` lower bound as a version tuple.

    Read from the packaging metadata, never from the running interpreter: the
    interpreter reports what happens to be executing this run, while the declared
    floor is what every INSTALL of this project is permitted to be. Only the
    second can be lowered by an edit no CI runner's version would reveal.
    """
    metadata = tomllib.loads(_PYPROJECT.read_text(encoding='utf-8'))
    requires = metadata['project']['requires-python']
    match = _REQUIRES_PYTHON_FLOOR_RE.search(requires)
    assert match is not None, (
        f'{_PYPROJECT} declares requires-python = {requires!r}, which carries no '
        '`>=MAJOR.MINOR` lower bound, so the floor this test grades cannot be read'
    )
    return int(match.group(1)), int(match.group(2))


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
_DISPATCH_TABLE_ROW_RE = re.compile(r'^\|\s*`ci pr ([a-z-]+)`\s*\|\s*(\*\*never\*\*|yes)\s*\|', re.MULTILINE)

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


_OUTCOME_ARM_RE = re.compile(r'^[ \t]*-[ \t]+\*\*(?P<antecedent>[^*]+)\*\*', re.MULTILINE)

_ARM_BOUNDARY_RE = re.compile(r'^(?:[ \t]*(?:-|\d+\.)[ \t]+\*\*|#{1,6}[ \t])', re.MULTILINE)

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


_RE_REVIEW_CONSUMERS: list[Path] = [doc for doc in _re_review_dispatchers() if _matched_arms(_read(doc))]

assert _RE_REVIEW_CONSUMERS, 'no re-review dispatcher document carried a matched arm'


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

_MERGE_SHAPED: dict[str, list[tuple[str, ...]]] = {p: _merge_shaped_registry_keys(p) for p in _PROVIDER_MODULES}

assert _MERGE_SHAPED and all(_MERGE_SHAPED.values()), f'a provider contributed no merge-shaped keys: {_MERGE_SHAPED}'

_MERGE_SHAPED_TOTAL: int = sum(len(v) for v in _MERGE_SHAPED.values())

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


_VOCAB_SENTENCE_RE = re.compile(
    r"an `overall_status` drawn from the handler's vocabulary\s*[—-]\s*(`.+?)\.",
    re.MULTILINE,
)

_CI_API_CONTRACT: Path = _SKILLS / 'tools-integration-ci' / 'standards' / 'api-contract.md'

_API_TOON_ALTERNATION_RE = re.compile(r'^overall_status: ([a-z_]+(?:\|[a-z_]+)+)$', re.MULTILINE)

_API_LOGIC_BLOCK_RE = re.compile(r'\*\*Overall Status Logic\*\*:\n((?:- `[a-z_]+`:[^\n]*\n)+)')

_DERIVE_FN_NAME = '_derive_overall_status'


def _vocabulary_definition_modules() -> list[Path]:
    """Every bundle module that DEFINES ``_derive_overall_status``.

    Derived by scanning, never listed. CodeRabbit's report of this finding named
    one provider as "the authoritative definition"; there are two, and a guard
    bound to a hand-written pair would repeat the same mistake one level up.
    """
    needle = f'def {_DERIVE_FN_NAME}('
    return sorted(path for path in _SKILLS.rglob('*.py') if needle in path.read_text(encoding='utf-8'))


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


_DOC_VOCABULARY_SITES: dict[str, Callable[[], frozenset[str]]] = {
    f'{_BRANCH_CLEANUP.name} § positive-shape requirement': _branch_cleanup_vocabulary,
    f'{_CI_API_CONTRACT.name} § checks status response schema': (_api_contract_schema_vocabulary),
    f'{_CI_API_CONTRACT.name} § Overall Status Logic': _api_contract_logic_vocabulary,
}


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
        'A comment survived the blanking, so comment text can still satisfy a text search over the blanked view.'
    )
    assert 'merge_queue surface at length' not in blanked, (
        'A docstring survived the blanking, so docstring text can still satisfy a text search over the blanked view.'
    )
    assert _SUCCESS_LITERAL in blanked, (
        'The success literal was blanked along with the documentation. It is executable '
        'code and must survive, or the ordering arm loses its right-hand side.'
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
            "An observability decision-log line does not name the value's provenance. "
            'Without it a reader cannot tell whether the bound value came from the '
            'one-stop params object or from an undocumented second read.'
        )


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
    @pytest.mark.parametrize('module', _VOCAB_DEFINITION_MODULES, ids=lambda p: p.parent.parent.name)
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
