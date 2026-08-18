# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-source footprint path classification, keyed on the declared build-map oracle.

Two retrospective checks partition a realized footprint before evaluating any rule
— ``check-manifest-consistency.py`` (which drops bookkeeping paths before the M1-M4
rules see them) and ``check-routing-decisions.py`` (which asks whether the footprint
touched production code before re-evaluating a ``no_code_delta`` prune predicate) —
and each used to answer "is this path implementation?" from its OWN hardcoded prefix
tuple::

    _BOOKKEEPING_PREFIXES = ('.plan/', '<a project-local dotfile tree>')

That guess can contradict the project's own declared oracle, and did. ``build.map``
in marshal.json is the file-to-build contract: any tree it routes with role
``production`` is production source by the project's own declaration, and a build
extension is free to route a dotfile tree — a project-local skill directory is
routed exactly that way on some targets. Wherever that happened, both checks
discarded production source as bookkeeping before any rule was evaluated, and the
rules then reported a clean pass over the remainder. A footprint drawn entirely
from such a tree survived the filter as the empty set; one drawn mostly from it was
reduced to the handful of entries that happened to lie elsewhere.

Two copies of one wrong rule is how the second site stayed live after the first was
noticed, so the corrected rule lives here ONCE and both checks call it. The oracle
— not this module — decides what a path is; this module only names the categories
and applies the fixed non-oracle rules below.

**What stays outside the oracle, and why.** The rungs :func:`classify_path`
decides without consulting ``build.map`` are, in its order: ``runtime_state``,
``report``, ``documentation``, ``test``. Each exists because the oracle
structurally cannot answer for it, not because a guess was convenient:

- ``runtime_state`` — the ``.plan/`` plan-state directory holds this tooling's own
  per-plan working state, which no build system routes and no build map describes,
  so there is no oracle answer to consult. ⛔ Do NOT justify this rung by calling
  ``.plan/`` git-ignored: a number of files under it ARE git-tracked —
  ``marshal.json`` (which holds ``build.map`` itself) and every
  ``project-architecture/**/enriched.json`` — and ``script-shared``'s
  ``_plan_state_exemption`` module exists precisely because a bare ``.plan/``
  prefix rule keyed on that false premise hid tracked edits. What justifies the
  rung here is the ABSENCE OF AN ORACLE ANSWER, not trackedness; a consumer that
  needs the trackedness question answered must use that module instead.
- ``report`` — the plan's own quality-verification report is a phase-6-finalize
  artifact named by this tooling, not a file type any build system routes.
- ``documentation`` — not a build_map role at all: the vocabulary deliberately has
  none, because documentation has no build-system owner
  (``_extension_constants.py``, ``BUILD_MAP_ROLES``). Recognised by file suffix, a
  language- and layout-independent fact.
- ``test`` — a project whose ``build.map`` carries no ``test`` route would leave
  every test file unrouted, and an unrouted path is treated fail-closed as possible
  production, which would turn a tests-only footprint into a false mis-prune.


Every OTHER classification comes from the oracle.

⛔ These convention sets are **these checks' own**. They are NOT imported from, and
not identical to, ``manage-execution-manifest``'s change-footprint classifier
(``_manifest_core._DOC_SUFFIXES`` carries ``.asciidoc`` as well and has no
directory concept). Do not describe them as that classifier's set.

⚠ What unification changed, precisely — the two halves are NOT alike:

- **The documentation sets did not move.** Both retired copies used the same
  ``('.md', '.adoc')`` suffixes; the directory tokens were the manifest copy's
  alone and, after the split into :func:`is_docs_suffix_path` (the classification
  rung) and :func:`is_docs_path` (the manifest rules' predicate), remain the
  manifest copy's alone. Neither consumer's docs behaviour changed.
- **The test sets did move, in both directions**, and :data:`TEST_DIR_TOKENS`
  records each direction against the consumer it reaches.


**``unclassified`` is a could-not-classify, never a classified-as-unimportant.**
A path no declared route covers is one the oracle has no opinion about. Both
consumers treat it fail-closed — retained by the manifest filter, and counted as
possible production by the routing check — because the alternative is a private
guess re-entering through the back door, this time silently and with the oracle's
authority borrowed for it.
"""

from __future__ import annotations

import re

from extension_base import (
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
    read_build_map_routes,
    resolve_route_role,
)

#: The plan-state directory. Decided here because it appears in no build map — this
#: tooling's own per-plan working state is not a file type any build system routes,
#: so no declared route can classify it and there is no oracle answer to defer to.
#: This is the ONE path prefix this module still decides on its own.
#:
#: ⛔ Not because it is git-ignored — it partly is not. ``marshal.json`` (which holds
#: ``build.map``) and every ``project-architecture/**/enriched.json`` are tracked.
#: Trackedness is a different question with a different owner
#: (``script-shared``'s ``_plan_state_exemption``); this classifier answers "what
#: kind of file is this", never "would an edit here be pushable".
RUNTIME_STATE_PREFIXES: tuple[str, ...] = ('.plan/',)

#: Documentation suffixes and directory tokens. Documentation is NOT a build_map
#: role — the role vocabulary deliberately omits it because documentation has no
#: build-system owner — so doc recognition is a file-suffix fact rather than a
#: private guess at implementation-ness. It is THIS module's set, not
#: ``manage-execution-manifest``'s change-footprint classifier's (see the module
#: docstring's ⛔): that one carries ``.asciidoc`` too and has no directory concept.
DOCS_SUFFIXES: tuple[str, ...] = ('.md', '.adoc')
DOCS_DIR_TOKENS: tuple[str, ...] = ('/references/', '/templates/')

#: Test-file recognition by filename/directory convention, for a path no declared
#: route covers. It exists because the oracle can be silent here: a project whose
#: ``build.map`` declares no ``test`` route leaves every test file
#: ``unclassified``, which is treated fail-closed as possible production and would
#: report a tests-only footprint as a mis-prune. A routed path still takes the
#: oracle's role; this fires only where the oracle has no answer.
#:
#: ⚠ This is NOT the union of the two sets the consumers previously carried
#: separately, and the difference is deliberate in both directions:
#:
#: - The name pattern GAINS ``*Spec.java``, which only the manifest copy carried.
#:   For the ROUTING consumer this is an EXONERATING change and is declared as one:
#:   a footprint of only ``src/FooSpec.java`` counted as production before and is
#:   ``test`` now, so a ``no_code_delta`` mis-prune moves ``fail`` → ``pass``. It is
#:   deliberate — a Spock/Spek spec IS a test, and the routing copy's omission was a
#:   gap rather than a policy — and it is bounded: it is reachable only where the
#:   oracle is silent for that path AND the basename matches ``*Spec.java`` AND the
#:   path lies outside ``/test/`` and ``/tests/``. A JVM project routes
#:   ``src/test/**`` as ``test``, so the oracle answers first and the rung is never
#:   consulted.
#: - The directory tokens are the manifest copy's boundary-anchored pair, matched
#:   against ``/{path}``. The routing copy's bare ``('test/', 'tests/', …)`` tokens
#:   were matched with an unanchored ``token in path``, so they also matched
#:   ``latest/foo.py``, ``contest/x.py`` and ``mytest/helper.py`` — a substring
#:   defect, not a recognition. Dropping it moves those paths from ``test`` to
#:   ``unclassified``, which the routing consumer treats as possible production:
#:   the FAIL-CLOSED direction, so it can only widen scrutiny.
#:
#: So "both directions" is literal: the token change is fail-closed, the
#: ``*Spec.java`` change is exonerating, and each is named with its own direction
#: above rather than the pair being described by whichever direction is easier to
#: defend.
TEST_DIR_TOKENS: tuple[str, ...] = ('/test/', '/tests/')
TEST_NAME_RE = re.compile(
    r'(^|/)(test_[^/]+\.py|[^/]+_test\.py|[^/]+Test\.java|[^/]+Spec\.java'
    r'|[^/]+\.test\.js|[^/]+\.spec\.js)$'
)

#: The plan's own quality-verification report, a phase-6-finalize artifact.
REPORT_NAME_RE = re.compile(r'(^|/)quality-verification-report(-audit-[^/]+)?\.md$')

# Category vocabulary. ``PRODUCTION`` / ``TEST`` / ``CONFIG`` are the oracle's own
# role names, carried through verbatim so a reader can trace a verdict back to the
# build_map entry that produced it.
CATEGORY_RUNTIME_STATE = 'runtime_state'
CATEGORY_REPORT = 'report'
CATEGORY_PRODUCTION = ROLE_PRODUCTION
CATEGORY_TEST = ROLE_TEST
CATEGORY_CONFIG = ROLE_CONFIG
CATEGORY_DOCUMENTATION = 'documentation'
CATEGORY_UNCLASSIFIED = 'unclassified'

#: Every category :func:`classify_path` can return, and the set
#: :func:`classify_footprint` seeds its buckets from — so every category key is
#: present in that mapping even at zero, and a reader cannot mistake an absent key
#: for a measured zero.
#:
#: ⚠ Each consumer still SELECTS from this set by name
#: (``check-manifest-consistency._DROPPED_CATEGORIES``,
#: ``check-routing-decisions._PRODUCTION_CATEGORIES``), so adding a category here
#: does not automatically place it in either dispatch. Those selections are pinned
#: as subsets of this tuple by test, which catches a typo but cannot decide where a
#: genuinely new category belongs — that remains an edit at each consumer.
CATEGORIES: tuple[str, ...] = (
    CATEGORY_RUNTIME_STATE,
    CATEGORY_REPORT,
    CATEGORY_PRODUCTION,
    CATEGORY_TEST,
    CATEGORY_CONFIG,
    CATEGORY_DOCUMENTATION,
    CATEGORY_UNCLASSIFIED,
)


def load_oracle_routes() -> list[tuple[str, str | None]]:
    """Return the declared ``(glob, role)`` routes, or an empty list when unavailable.

    Thin pass-through to the build-system-owned reader so both consumers resolve
    the oracle through one call. An empty list means the oracle is UNAVAILABLE (no
    marshal.json, no ``build.map`` block, or no routed entry) — not that the
    project has no production code. With no routes, :func:`classify_path` can still
    answer from its non-oracle rungs — ``runtime_state``, ``report``,
    ``documentation`` and ``test`` all fire without the oracle — and returns
    ``unclassified`` for everything else, which both consumers handle fail-closed.
    """
    return read_build_map_routes()


def oracle_available(routes: list[tuple[str, str | None]]) -> bool:
    """Whether the oracle answered with at least one role-bearing route."""
    return any(role is not None for _glob, role in routes)


def is_runtime_state_path(path: str) -> bool:
    """Whether ``path`` lies under the genuinely-runtime plan-state directory."""
    return path.startswith(RUNTIME_STATE_PREFIXES)


def is_docs_suffix_path(path: str) -> bool:
    """Whether ``path`` is documentation by FILE SUFFIX alone.

    The predicate :func:`classify_path` uses for its ``documentation`` rung, and it
    is suffix-only on purpose. Widening it to the directory tokens
    (:func:`is_docs_path`) would classify a ``.py`` file under a ``references/`` or
    ``templates/`` directory as documentation, and a consumer that reads
    ``documentation`` as "not production" would then EXONERATE a real source
    change — the same unknown-into-exoneration move the ``unclassified`` handling
    exists to refuse, arriving by the other door.
    """
    return path.endswith(DOCS_SUFFIXES)


def is_docs_path(path: str) -> bool:
    """Whether ``path`` is documentation by suffix OR by directory token.

    The WIDER predicate, and deliberately NOT the classification rung — see
    :func:`is_docs_suffix_path` for why the two differ. This one is the rule-side
    predicate ``check-manifest-consistency``'s M1/M3 use to decide whether a
    SURVIVING path is a culprit, carried over from that script unchanged so those
    rules keep the reach they had.

    Using it there is safe precisely because it never decides what is DROPPED: the
    manifest filter keeps ``documentation`` and ``unclassified`` alike, so a wider
    docs recognition inside a rule can only move a path from culprit to
    non-culprit within an already-retained set, never remove it from view.
    """
    if is_docs_suffix_path(path):
        return True
    return any(token in f'/{path}' for token in DOCS_DIR_TOKENS)


def is_test_path(path: str) -> bool:
    """Whether ``path`` is a test file by filename/directory convention.

    The convention fallback for a path the oracle does not route — see
    :data:`TEST_DIR_TOKENS`. Both consumers resolve test-ness from THIS one set, so
    neither carries a private idea of what a test file looks like.

    ⚠ That is not the same as the two always returning the same answer for a given
    path, and they do not. This predicate is consulted directly by
    ``check-manifest-consistency``'s M1/M3 culprit filtering, whereas
    ``check-routing-decisions`` reaches test-ness only through
    :func:`classify_path`, where the ``test`` rung sits BEHIND the oracle and
    behind the ``documentation`` rung. So ``test/foo/README.md`` is ``True`` here
    and ``documentation`` there, and a test-shaped path the oracle routes
    ``production`` is ``True`` here and ``production`` there. Shared vocabulary,
    different question: this asks "does it look like a test", while
    :func:`classify_path` asks "what is it, given everything that can say so".
    """
    if any(token in f'/{path}' for token in TEST_DIR_TOKENS):
        return True
    return bool(TEST_NAME_RE.search(path))


def classify_path(path: str, routes: list[tuple[str, str | None]]) -> str:
    """Return the :data:`CATEGORIES` member describing ``path``.

    Resolution order, and each step's authority:

    1. ``runtime_state`` — the ``.plan/`` prefix, decided here because the oracle
       has no route for this tooling's own plan-state directory.
    2. ``report`` — the plan's own quality-verification report, a finalize artifact.
    3. ``production`` / ``test`` / ``config`` — whatever the ORACLE says, via
       :func:`resolve_route_role`.
    4. ``documentation`` — by FILE SUFFIX only (:func:`is_docs_suffix_path`);
       documentation is not a build_map role, so the oracle cannot answer here.
       The wider :func:`is_docs_path` is deliberately NOT used at this rung — see
       that function for why classifying a ``.py`` under ``references/`` as
       documentation would exonerate a real source change.
    5. ``test`` — filename/directory convention, for a project whose ``build.map``
       declares no ``test`` route. Without this rung such a path would fall to
       ``unclassified``, which both consumers treat as possible production.
    6. ``unclassified`` — no declared route covers it, and neither convention
       recognises it.

    The oracle is consulted BEFORE both conventions, so a routed path keeps the
    role the project declared for it: a project that routes ``*.md`` (this one does
    not) would have that declaration honoured rather than overridden here. The two
    conventions fire only where the oracle is silent.

    Args:
        path: Repo-relative, forward-slashed candidate path.
        routes: The routes from :func:`load_oracle_routes`.

    Returns:
        One of :data:`CATEGORIES`.
    """
    if is_runtime_state_path(path):
        return CATEGORY_RUNTIME_STATE
    if REPORT_NAME_RE.search(path):
        return CATEGORY_REPORT
    role = resolve_route_role(path, routes)
    if role is not None:
        return role
    if is_docs_suffix_path(path):
        return CATEGORY_DOCUMENTATION
    if is_test_path(path):
        return CATEGORY_TEST
    return CATEGORY_UNCLASSIFIED


def classify_footprint(files: list[str], routes: list[tuple[str, str | None]]) -> dict[str, list[str]]:
    """Return ``{category: [path, ...]}`` covering every member of :data:`CATEGORIES`.

    Every category key is present even when empty, so a consumer reading a count
    off this mapping cannot mistake an absent key for a measured zero.

    Args:
        files: Repo-relative, forward-slashed candidate paths.
        routes: The routes from :func:`load_oracle_routes`.

    Returns:
        A mapping from each :data:`CATEGORIES` member to its paths, in input order.
    """
    buckets: dict[str, list[str]] = {category: [] for category in CATEGORIES}
    for path in files:
        buckets[classify_path(path, routes)].append(path)
    return buckets


__all__ = [
    'CATEGORIES',
    'CATEGORY_CONFIG',
    'CATEGORY_DOCUMENTATION',
    'CATEGORY_PRODUCTION',
    'CATEGORY_REPORT',
    'CATEGORY_RUNTIME_STATE',
    'CATEGORY_TEST',
    'CATEGORY_UNCLASSIFIED',
    'DOCS_DIR_TOKENS',
    'DOCS_SUFFIXES',
    'REPORT_NAME_RE',
    'RUNTIME_STATE_PREFIXES',
    'TEST_DIR_TOKENS',
    'TEST_NAME_RE',
    'classify_footprint',
    'classify_path',
    'is_docs_path',
    'is_docs_suffix_path',
    'is_runtime_state_path',
    'is_test_path',
    'load_oracle_routes',
    'oracle_available',
]
