#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two-dimensional cross-check for the ``pre-commit-verify-freshness`` gate.

Notation: imported as a module (PYTHONPATH) — ``from _freshness_crosscheck
import cross_check_candidates``. NOT an executor entry point.

The gate's primary predicate answers *"is there a successful ``kind=build`` row
against the current working-tree sha?"*. That predicate asserts a row EXISTS; it
never asks whether the row is evidence of a build **this project performs**, and
it never asks whether the build that row records actually **covered** the change
the gate is about to let through. Those are three different questions, and the
gap between them is not theoretical — each has produced a real false-green:

* **Attribution.** The gate has been satisfied by a row naming a package-manager
  build the project has no module for, written into the shared ledger by
  something other than a real build of this tree. The verdict happened to be
  right; the evidence did not support it.
* **Coverage.** At worktree sha ``858061bc`` the ledger held THREE ``kind=build``
  rows for the same tree: a whole-tree ``module-tests`` that TIMED OUT, a
  module-scoped ``module-tests`` that FAILED, and a single-directory 573-test run
  that SUCCEEDED. The gate returned ``fresh`` on the third and reported the
  evidence ``corroborated``, because every ``pyproject_build`` invocation carries
  the identical notation — so the attribution dimension alone cannot tell a
  573-test directory run from a whole-tree ``verify``, nor a zero-test ``compile``
  from either.

A gate that is right for the wrong reason produces no failure to learn from, so
it can stay wrong indefinitely. This module therefore cross-checks each candidate
row on TWO independent dimensions, reported separately and never folded:

**Dimension 1 — attribution (notation).** Compares each candidate row's
``notation`` against the set of build notations the project's architecture
actually resolves to (``manage-architecture``'s
``resolve_project_build_notations``). The comparison target is deliberately the
ARCHITECTURE, not the ledger: comparing ledger rows against other ledger rows
would let a polluted ledger corroborate itself.

**Dimension 2 — coverage (blast radius).** Compares the CANONICAL and the SCOPE
the row records against what the change needs. Both sides are already in the
substrate — see :func:`parse_row_scope` for the row side and
:func:`required_coverage` for the change side — so this is a gap in the
PREDICATE, not in the data.

The two dimensions answer different questions and can disagree in both
directions: an unattributable row may name a whole-tree ``verify``, and a
perfectly attributable row may be a single-directory test run. A row may be cited
as the gate's evidence only when it satisfies BOTH, which is why
:func:`cross_check_candidates` selects across them jointly rather than letting
either pick a row the other would refuse.

Three-valued verdict, never collapsed
=====================================

:data:`CORROBORATED`
    The row's notation is one the architecture resolves. The evidence is
    auditable and related; the gate may pass on it.

:data:`REFUTED`
    The architecture resolved a non-empty notation set and **no** candidate row's
    notation is in it — including the case where no candidate carries a usable
    notation at all (missing, empty, or not a string). It is the whole candidate
    list that is refuted, never a single row: one corroborating row is enough to
    pass. No candidate can then be evidence of a build of this project, and the
    gate MUST fail closed.

:data:`UNVERIFIED`
    The notation set could not be established (the crawl raised, or resolved no
    build notation anywhere). Nothing is known about the row's relatedness.

The fail-direction, and why it splits
=====================================

An uncross-checkable match must not *silently* pass; that leaves two candidate
directions, and this module takes a different one for each of the two ways a
cross-check can decline to corroborate — because they are different facts:

* **A refutation is positive knowledge** ("the architecture resolves maven and
  nothing else; this row says npm"), so it **fails closed**. This is the defect
  class the gate exists to close, and admitting it with a warning would leave the
  false-green in place while merely annotating it.
* **An inability to resolve is the absence of knowledge**, so it **passes with
  the inability recorded in the decision record** (``notation_cross_check:
  unverified`` plus a ``notation_cross_check_reason``). Failing closed here would
  block every legitimate pre-commit transition in a working tree whose
  architecture has not been discovered — a project mid-onboarding, a fresh
  clone, a synthetic fixture tree — none of which is evidence of anything wrong.
  The gate's PRIMARY predicate has already been satisfied at that point; refusing
  on a supplementary check that could not run trades a false-green for a
  false-red on strictly less evidence.

⛔ The two are never folded together. ``unverified`` is a stated sentinel, not a
quiet ``corroborated``: it always reaches the decision record, so "passed
uncross-checked" is visible to a reader rather than indistinguishable from
"passed cross-checked" (ADR-015 — an absent identity is a stated sentinel, and
every presence guard is a meaning guard).

A doc-only carve-out was considered and REFUSED
===============================================

The obvious way to spend less on this check is to exempt a footprint that
touched only markdown. That is refused here on a hard constraint, and the
refusal is recorded in the shipped source rather than only in a run report,
because an unexplained absence invites the next author to add it.

**Markdown under the bundle tree is a build input in this repository.** Tests
read and assert on the BODIES of bundle documents — ``test/plan-marshall/
test_triage_loop_back_target.py`` parses ``marketplace/bundles/plan-marshall/
skills/plan-marshall/workflow/triage.md`` and fails when its classification
table changes — so a markdown-only edit can turn the suite red exactly as a
``*.py`` edit can. A doc-only freshness exemption would therefore hand back a
``fresh`` verdict for a tree whose tests were never run against it, which is the
whole defect class this module exists to close, re-entering through the
exemption. Build necessity is not this module's question in any case: it is
owned by the single ``build-decision`` authority the gate consults BEFORE the
ledger scan (see the caller's module docstring), and that authority reads the
project's own ``build.map`` globs rather than a hard-coded notion of which
suffixes matter.

Reading the scope off the row — what is available, and what is not
==================================================================

**The row already carries more than the gate used to read — checked, not
assumed.** ``_ledger_core.build_record`` records ``notation``, ``args`` (the
executor argv, stamped on every build-class dispatch as
``' '.join(script_args)``), ``command`` (the line the wrapper reported running)
and ``outcome`` (the wrapper's whole stdout TOON). The gate historically read
none of them; it now reads ``notation`` for attribution and ``args`` for
coverage.

``args`` is the coverage source rather than ``command`` because it is OUR argv
shape, uniform across every build tool: the canonical and its scope always follow
``--command-args``. ``command`` is the wrapper's own resolved line, so its shape
is build-tool-specific — ``mvn -pl mod verify`` carries the module in a flag that
precedes the goal, and a generic reader that scanned for the first canonical
token would see ``verify`` with nothing after it and conclude *whole-tree*. That
is precisely the false-green direction, so ``command`` is NOT used as a fallback:
a row whose ``args`` carries no ``--command-args`` is reported UNDETERMINED
instead of guessed at. See :func:`parse_row_scope`.

⚠ ``args`` is joined **without quoting**, so a module-scoped
``run --command-args "verify plan-marshall"`` is stamped as
``run --command-args verify plan-marshall``: the argument boundary is gone, and a
reader cannot tell whether ``plan-marshall`` was inside the quoted value or a
separate positional. That ambiguity does not affect this check, because both
readings name the SAME blast radius — an invocation that mentions
``plan-marshall`` and nothing wider. What the ambiguity would break is a claim
about the argv's *structure*, which nothing here makes.

The claim the gate now makes, and why it is bounded
====================================================

The consumer-facing documents already promised the stronger claim the predicate
did not make: ``phase-6-finalize/standards/push.md`` says freshness "verifies
that the most recent ``verify`` run actually observed this version of the code"
and ``phase-6-finalize/SKILL.md`` says it validates "that a ``verify`` was
actually performed", while this skill's own contract said only "a successful
build was observed against this tree". That disagreement WAS the defect, stated
in prose. It is now closed in the direction the consumers already assumed, and
``manage-tasks/SKILL.md`` § "Pre-Commit Verify Freshness" states the resulting
contract.

⛔ **Closing it in the strict direction has a mirror-image failure mode — a
legitimate transition refused because the footprint only ever warranted a
compile — and three properties bound it:**

1. **Necessity is decided upstream.** The caller consults the single
   ``build-decision`` authority BEFORE the ledger scan, so a footprint that needs
   no build never reaches this module at all.
2. **The requirement is DERIVED from the change, not fixed.** A footprint with no
   ``.py`` file does not require the compile/lint dimensions, and an empty
   footprint requires nothing — see :func:`required_coverage`. The gate demands a
   whole-tree ``verify`` only of a change whose blast radius is whole-tree.
3. **Only a POSITIVE refutation fails closed.** A row whose scope cannot be read,
   a canonical outside the known vocabulary, and a change whose required coverage
   could not be derived all yield :data:`UNDETERMINED`, which passes with the
   inability recorded — the same split fail-direction the attribution dimension
   takes, for the same reason.

Structural stale verdicts are NOT this module's business
========================================================

A tree mutated after its last build is correctly ``stale``: the stamp was never
wrong, the commit invalidated it. Nothing here re-stamps, relaxes the sha
comparison, or otherwise softens that verdict — a candidate only reaches this
module once it has ALREADY matched on ``kind``, ``status`` and ``worktree_sha``,
so a mutated tree has no candidates and never gets here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: The row's notation is one the project's architecture resolves.
CORROBORATED = 'corroborated'
#: The architecture resolved a notation set that does not contain the row's.
REFUTED = 'refuted'
#: The notation set could not be established; relatedness is unknown.
UNVERIFIED = 'unverified'

#: ``notation_cross_check_reason`` when the resolver was reached and could not
#: produce a usable set — it raised while running, or it returned something that
#: is not a set of notations at all. Both are faults in the resolution rather
#: than in reaching it, which is what separates this from
#: :data:`REASON_RESOLVER_UNIMPORTABLE`.
REASON_RESOLUTION_FAILED = 'architecture_resolution_failed'
#: ``notation_cross_check_reason`` when the resolver could not even be IMPORTED.
#: Distinct from :data:`REASON_RESOLUTION_FAILED` because the two are different
#: facts with different owners: an un-crawlable project is a legitimate quiet
#: pass, while an unimportable resolver means THIS CHECK IS BROKEN — a deployment
#: or ``PYTHONPATH`` fault that will report ``unverified`` on every row forever.
#: Both pass the gate (neither is a refutation), so folding them would cost
#: nothing at the gate and everything to a reader trying to find out why the
#: cross-check never corroborates anything.
REASON_RESOLVER_UNIMPORTABLE = 'architecture_resolver_unimportable'
#: ``notation_cross_check_reason`` when the resolver ran but resolved no build notation.
REASON_NO_NOTATIONS_RESOLVED = 'architecture_resolved_no_build_notations'
#: ``notation_cross_check_reason`` when every candidate row carried no notation.
REASON_NOTATION_ABSENT = 'notation_absent'
#: ``notation_cross_check_reason`` when candidate notations are all unresolved by the architecture.
REASON_NOTATION_UNRELATED = 'notation_unrelated'

# ---------------------------------------------------------------------------
# Dimension 2 — coverage (blast radius)
# ---------------------------------------------------------------------------

#: At least one candidate row records a build whose canonical and scope cover the
#: change's blast radius. The gate may cite that row.
COVERED = 'covered'
#: Every candidate row that could be read records a build PROVABLY narrower than
#: the change — a weaker canonical, a narrower scope, or a measured zero tests.
#: This is positive knowledge, so it fails closed.
NARROW = 'narrow'
#: The coverage comparison could not be performed on either side. Nothing is
#: known, so — like :data:`UNVERIFIED` on the attribution dimension — it passes
#: with the inability recorded rather than failing closed on no evidence.
UNDETERMINED = 'undetermined'

#: ``scope_cross_check_reason`` when the change's required coverage could not be
#: derived (the live footprint or the registered-module set was unresolvable).
#: Refusing here would block a transition on an input nobody measured.
REASON_REQUIRED_COVERAGE_UNKNOWN = 'required_coverage_unknown'
#: ``scope_cross_check_reason`` when the canonical→analyses vocabulary could not
#: be imported. Like :data:`REASON_RESOLVER_UNIMPORTABLE` on the attribution
#: dimension this means THIS CHECK IS BROKEN rather than that the project is
#: un-crawlable, so it is named apart.
REASON_VOCABULARY_UNIMPORTABLE = 'analysis_vocabulary_unimportable'
#: ``scope_cross_check_reason`` when no candidate row's ``args`` carries a
#: readable ``--command-args``, or every canonical it names is outside the known
#: vocabulary. The rows were read and said nothing usable — distinct from a row
#: that said something and was refuted.
REASON_SCOPE_UNREADABLE = 'build_scope_unreadable'
#: ``stale`` reason (and ``scope_cross_check_reason``) when every readable row
#: records a build narrower than the change. THE refusal this dimension exists to
#: make.
REASON_SCOPE_NARROW = 'build_scope_narrow'
#: ``stale`` reason for the DISJOINT case: neither dimension refused, yet no
#: single row satisfies both — every attributable row was narrow and every
#: covering row was unattributable. Named apart from both dimensions' own reasons
#: because it is a property of the candidate list rather than a verdict either
#: dimension reached, and a reader told ``build_scope_narrow`` here would go
#: looking for a refusal the coverage check never made.
REASON_NO_ADMISSIBLE_ROW = 'no_row_both_attributable_and_adequate'

#: Per-row refusal tokens, reported in ``row_scopes`` so a reader sees WHICH route
#: each row took rather than only that the row was rejected. The set spans BOTH
#: refusal classes — a row that was READ and found narrow, and a row that could not
#: be READ at all — so it is deliberately not described as a narrowness set, and
#: carries no cardinal that a token added below would silently falsify.
ROW_CANONICAL_UNKNOWN = 'canonical_outside_vocabulary'
ROW_CANONICAL_TOO_WEAK = 'canonical_performs_too_few_analyses'
ROW_SCOPE_TOO_NARROW = 'scope_narrower_than_change'
ROW_TESTS_EXECUTED_ZERO = 'tests_executed_zero'
ROW_ARGS_UNREADABLE = 'args_carry_no_command_args'

#: The executor flag that introduces the canonical command and its scope in a
#: ``kind=build`` row's ``args``. Copied verbatim from the shared ``run``
#: subparser declaration (``_build_cli.add_run_subparser``), which is why this
#: reader works for every build tool rather than only for the Python one.
_COMMAND_ARGS_FLAG = '--command-args'


@dataclass(frozen=True)
class AnalysisVocabulary:
    """The canonical→analyses map plus the three analysis-kind names.

    Loaded from ``_build_examined`` rather than restated, so this module and the
    build-run population reporter can never disagree about which analyses a
    canonical performs. That map is PARTIAL over the canonical vocabulary by
    design (``clean``, ``install``, ``package`` and friends are deliberately
    unmapped), so a lookup miss means *undetermined*, never *performs nothing*.

    Attributes:
        by_canonical: Canonical command name → the analyses it performs.
        compile: The translation / type-consistency analysis kind name.
        lint: The static structural / style analysis kind name.
        test: The test-execution analysis kind name.
    """

    by_canonical: dict[str, frozenset[str]]
    compile: str
    lint: str
    test: str


@dataclass(frozen=True)
class RequiredCoverage:
    """What a build must have done to be evidence for THIS change.

    Attributes:
        analyses: The analysis kinds the change can break, so a citable row's
            canonical must perform at least these.
        whole_tree: True when only a whole-tree run covers the change — the
            footprint spans several modules, touches cross-module infrastructure,
            or contains a path no registered module owns.
        modules: The module set a scoped run must cover when ``whole_tree`` is
            False. Empty only for an empty footprint, which requires nothing.
    """

    analyses: frozenset[str]
    whole_tree: bool
    modules: frozenset[str]


@dataclass(frozen=True)
class RowScope:
    """The blast radius a ``kind=build`` row records.

    Attributes:
        canonical: The canonical command token that followed ``--command-args``.
        scope_tokens: The remaining non-flag tokens — the module / directory
            scope. EMPTY means whole-tree, which is why an unreadable row must
            never be represented as a ``RowScope`` with no tokens: see
            :func:`parse_row_scope`, which returns ``None`` for that case.
    """

    canonical: str
    scope_tokens: tuple[str, ...]


def load_analysis_vocabulary() -> tuple[AnalysisVocabulary | None, str | None]:
    """Load the canonical→analyses vocabulary, or say why it could not be.

    Wraps the ``_build_examined`` import the same way
    :func:`resolve_expected_notations` wraps the architecture resolver: the
    cross-skill import is in-function so this module keeps no hard top-level
    dependency on the build bundle's scripts dir, and every failure raised WHILE
    importing (not merely ``ImportError`` — importing executes another module's
    body, which can raise anything) becomes one named reason.

    Returns:
        ``(vocabulary, reason)``. Exactly one side is informative.
    """
    try:
        from _build_examined import (
            ANALYSIS_COMPILE,
            ANALYSIS_LINT,
            ANALYSIS_TEST,
            CANONICAL_ANALYSES,
        )
    except Exception:  # noqa: BLE001 — an import can fail as more than ImportError
        return None, REASON_VOCABULARY_UNIMPORTABLE
    return (
        AnalysisVocabulary(
            by_canonical=dict(CANONICAL_ANALYSES),
            compile=ANALYSIS_COMPILE,
            lint=ANALYSIS_LINT,
            test=ANALYSIS_TEST,
        ),
        None,
    )


def required_coverage(
    footprint: list[str],
    scoped_modules: tuple[str, ...],
    divergence_possible: bool,
    vocabulary: AnalysisVocabulary,
) -> RequiredCoverage:
    """Derive what a build must have covered to be evidence for this footprint.

    Two rules, both stated here rather than inferred, because each decides a
    refusal:

    **Which analyses.** A non-empty footprint requires the TEST analysis
    unconditionally. That is not a Python-specific assumption: markdown under the
    bundle tree is a build input in this repository — tests read and assert on the
    BODIES of bundle documents — so a markdown-only edit can turn the suite red
    exactly as a ``*.py`` edit can, and the same reasoning that refuses a doc-only
    freshness carve-out (see the module docstring) refuses a doc-only test
    exemption. The COMPILE and LINT analyses are required additionally when the
    footprint contains a ``.py`` path, and only then: demanding a type-check of a
    change that altered no source would be the mirror-image false-red.

    **Which scope.** ``divergence_possible`` is taken verbatim from
    ``_test_scope_divergence.resolve_test_scope`` — the single existing authority
    on whether a scoped run could pass while a whole-tree run fails. When it is
    True only a whole-tree row covers the change; otherwise a row scoped to the
    resolved module set does.

    The empty footprint requires nothing at all (no analyses, no modules,
    ``whole_tree`` False), so every row covers it. That state is unreachable in
    production — the caller's ``build-decision`` consult returns ``not_necessary``
    for an empty footprint and short-circuits before the ledger scan — and is
    represented honestly rather than special-cased, so a direct caller of this
    function gets the truthful answer instead of a refusal it cannot act on.

    Args:
        footprint: The live plan footprint, repo-relative.
        scoped_modules: The module set ``resolve_test_scope`` derived from it.
        divergence_possible: ``resolve_test_scope``'s whole-tree verdict.
        vocabulary: The loaded analysis-kind names.

    Returns:
        A frozen :class:`RequiredCoverage`.
    """
    if not footprint:
        return RequiredCoverage(analyses=frozenset(), whole_tree=False, modules=frozenset())
    analyses = {vocabulary.test}
    if any(path.endswith('.py') for path in footprint):
        analyses |= {vocabulary.compile, vocabulary.lint}
    return RequiredCoverage(
        analyses=frozenset(analyses),
        whole_tree=divergence_possible,
        modules=frozenset(scoped_modules),
    )


def parse_row_scope(entry: dict[str, Any]) -> RowScope | None:
    """Read the canonical and scope a ``kind=build`` row records, or ``None``.

    Reads ``args`` — the executor argv — and takes the tokens that follow
    ``--command-args`` up to the next flag: the first is the canonical, the rest
    are the scope. Both the space-separated (``--command-args verify``) and the
    joined (``--command-args=verify``) spellings are accepted, because argparse
    accepts both and the ledger stamps whichever the caller used.

    ⛔ ``None`` means UNREADABLE and is never equivalent to a ``RowScope`` with an
    empty ``scope_tokens``. Empty tokens assert *whole-tree*, which is the widest
    possible coverage claim; returning it for a row nobody could parse would
    manufacture exactly the false-green this dimension exists to remove. ``args``
    that is absent, not a string, carries no ``--command-args``, or carries one
    with no following non-flag token all yield ``None``.

    ``command`` is deliberately not consulted as a fallback — see the module
    docstring for why a build-tool-specific command line cannot be read for scope
    without risking a wrong *whole-tree* answer.

    Args:
        entry: A ``kind=build`` ledger row.

    Returns:
        The recorded :class:`RowScope`, or ``None`` when it cannot be read.
    """
    args = entry.get('args')
    if not isinstance(args, str):
        return None
    tokens = args.split()
    rest: list[str] = []
    for position, token in enumerate(tokens):
        if token == _COMMAND_ARGS_FLAG:
            rest = tokens[position + 1:]
            break
        if token.startswith(f'{_COMMAND_ARGS_FLAG}='):
            rest = [token.split('=', 1)[1], *tokens[position + 1:]]
            break
    else:
        return None
    payload = []
    for token in rest:
        if token.startswith('-'):
            break
        if token:
            payload.append(token)
    if not payload:
        return None
    return RowScope(canonical=payload[0], scope_tokens=tuple(payload[1:]))


def _measured_zero_tests(entry: dict[str, Any]) -> bool:
    """Return True when the row MEASURED that it executed no test.

    The wrapper publishes ``tests_run`` alongside ``tests_population`` precisely
    so a measured zero stays distinguishable from an unknown count, and only the
    measured zero is a refutation here. An absent, unparseable or ``unknown``
    population says nothing about how many tests ran, and treating it as zero
    would refuse a legitimate run for having an unreadable payload.

    Args:
        entry: A ``kind=build`` ledger row.

    Returns:
        True only when the row's own outcome payload says it ran zero tests.
    """
    outcome = entry.get('outcome')
    if not isinstance(outcome, dict):
        return False
    if outcome.get('tests_population') != 'measured':
        return False
    return outcome.get('tests_run') == 0


def _row_refusal(
    entry: dict[str, Any],
    required: RequiredCoverage,
    vocabulary: AnalysisVocabulary,
) -> str | None:
    """Return why ``entry`` does not cover ``required``, or ``None`` when it does.

    Evaluated in order of how much the row said: a row nobody could parse, then a
    canonical outside the vocabulary, then the two substantive refusals. The first
    two are inabilities and the caller reports them as :data:`UNDETERMINED`; the
    rest are positive refutations and fail the gate closed.

    Args:
        entry: A ``kind=build`` ledger row.
        required: What the change needs covered.
        vocabulary: The canonical→analyses map.

    Returns:
        One of the ``ROW_*`` tokens, or ``None`` when the row covers the change.
    """
    scope = parse_row_scope(entry)
    if scope is None:
        return ROW_ARGS_UNREADABLE
    performed = vocabulary.by_canonical.get(scope.canonical)
    if performed is None:
        return ROW_CANONICAL_UNKNOWN
    if not required.analyses <= performed:
        return ROW_CANONICAL_TOO_WEAK
    if scope.scope_tokens:
        if required.whole_tree:
            return ROW_SCOPE_TOO_NARROW
        if not required.modules <= set(scope.scope_tokens):
            return ROW_SCOPE_TOO_NARROW
    if vocabulary.test in required.analyses and _measured_zero_tests(entry):
        return ROW_TESTS_EXECUTED_ZERO
    return None


#: The per-row refusals that are INABILITIES rather than refutations. A candidate
#: list in which every row took one of these routes is :data:`UNDETERMINED`; one
#: in which any row took a different route is :data:`NARROW`.
_INABILITY_REFUSALS = frozenset({ROW_ARGS_UNREADABLE, ROW_CANONICAL_UNKNOWN})


def scope_check_candidates(
    candidates: list[dict[str, Any]],
    required: RequiredCoverage | None,
    vocabulary: AnalysisVocabulary | None,
    *,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    """Decide which candidate rows cover the change's blast radius.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order.
        required: What the change needs covered, or ``None`` when the caller
            could not derive it.
        vocabulary: The loaded canonical→analyses map, or ``None`` when it could
            not be loaded.
        unavailable_reason: The caller's own reason token when ``required`` is
            ``None``. Defaults to :data:`REASON_REQUIRED_COVERAGE_UNKNOWN`; a
            caller that knows a more specific cause passes it so the record names
            what to repair.

    Returns:
        A dict carrying ``verdict`` (:data:`COVERED` / :data:`NARROW` /
        :data:`UNDETERMINED`), ``covered_positions`` (the positions in
        ``candidates`` of every covering row, in file order), ``reason``
        (``None`` on :data:`COVERED`, otherwise the naming constant) and
        ``row_scopes`` — one ``'{canonical} {scope}: {verdict}'`` line per
        candidate, so the decision record shows WHAT each row recorded and why it
        was or was not citable rather than only the aggregate.
    """
    if vocabulary is None:
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'reason': REASON_VOCABULARY_UNIMPORTABLE,
            'row_scopes': [],
        }
    if required is None:
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'reason': unavailable_reason or REASON_REQUIRED_COVERAGE_UNKNOWN,
            'row_scopes': [],
        }

    covered: list[int] = []
    refusals: list[str] = []
    row_scopes: list[str] = []
    for position, entry in enumerate(candidates):
        refusal = _row_refusal(entry, required, vocabulary)
        scope = parse_row_scope(entry)
        rendered = 'unreadable' if scope is None else ' '.join((scope.canonical, *scope.scope_tokens))
        row_scopes.append(f'{rendered}: {refusal or COVERED}')
        if refusal is None:
            covered.append(position)
        else:
            refusals.append(refusal)

    if covered:
        return {
            'verdict': COVERED,
            'covered_positions': covered,
            'reason': None,
            'row_scopes': row_scopes,
        }
    # Every row refused. The verdict turns on WHICH refusals occurred: a list in
    # which nothing could be read is an absence of knowledge, while a single
    # substantive refutation means the ledger positively shows a build narrower
    # than the change — and one such row is enough to fail closed, exactly as one
    # corroborating row is enough to pass on the attribution dimension.
    if not refusals or all(refusal in _INABILITY_REFUSALS for refusal in refusals):
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'reason': REASON_SCOPE_UNREADABLE,
            'row_scopes': row_scopes,
        }
    return {
        'verdict': NARROW,
        'covered_positions': [],
        'reason': REASON_SCOPE_NARROW,
        'row_scopes': row_scopes,
    }


def resolve_expected_notations(project_dir: str) -> tuple[frozenset[str], str | None]:
    """Resolve the project's build-notation set, or say why it could not be.

    Wraps ``manage-architecture``'s ``resolve_project_build_notations`` so the
    gate never has to distinguish "the crawl raised" from "the crawl ran and
    found nothing" at the call site. The cross-skill import is in-function, the
    same discipline the caller uses for its ``build-decision`` consult: this
    command module keeps no hard top-level dependency on another skill's scripts
    dir, so it stays importable when ``manage-architecture`` is not on the path.

    Args:
        project_dir: Project root to resolve against — the gate's already
            resolved worktree root.

    Returns:
        ``(notations, reason)``. Exactly one side is informative: a non-empty
        ``notations`` with ``reason is None``, or an empty ``notations`` with a
        non-``None`` reason naming which inability occurred. An empty set is
        NEVER returned as a refutation-grade answer — see the module docstring.

        The three inabilities are named apart rather than folded, because they
        have different owners: :data:`REASON_RESOLVER_UNIMPORTABLE` is a fault in
        THIS check's own deployment (the resolver could not even be reached),
        :data:`REASON_RESOLUTION_FAILED` is a fault in the resolution itself (it
        raised while running, or returned a value that is not a set of
        notations), and :data:`REASON_NO_NOTATIONS_RESOLVED` is the ordinary
        un-crawled project.
        All three pass the gate, so the distinction buys nothing there and
        everything for a reader asking why nothing ever corroborates.
    """
    try:
        from _cmd_client_query import resolve_project_build_notations
    except Exception:  # noqa: BLE001 — see below: an import can fail as more than ImportError
        # NOT just ``ImportError``. Importing this module executes another
        # skill's module body, and that body can raise anything: today
        # ``_cmd_client_build`` resolves its bundles root at module scope via
        # ``marketplace_paths.resolve_bundles_root``, which raises ``RuntimeError``
        # by design "so import-time misconfiguration fails loudly". Loudly is
        # right for a build tool and wrong here — it escaped this function
        # entirely, past the guard below, and gave the gate's callers a traceback
        # instead of a TOON ``status``. Every failure raised WHILE importing is a
        # deployment or PYTHONPATH fault, which is exactly what
        # REASON_RESOLVER_UNIMPORTABLE names, so all of them map to it.
        return frozenset(), REASON_RESOLVER_UNIMPORTABLE
    try:
        notations = resolve_project_build_notations(project_dir)
    except Exception:  # noqa: BLE001 — any resolver failure is an inability, not a refutation
        return frozenset(), REASON_RESOLUTION_FAILED
    # Defence against a FUTURE resolver, not a live hazard: today
    # ``resolve_project_build_notations`` has a single ``return frozenset(...)``,
    # so it cannot hand back a non-container. A second return that could would
    # pass the truthiness test below and then raise TypeError from the ``in``
    # comparison in cross_check_candidates — OUTSIDE this try, escaping the gate.
    # The guard belongs here rather than at the comparison because this is the
    # function whose job is to turn every inability into a named reason.
    if not isinstance(notations, (frozenset, set)):
        return frozenset(), REASON_RESOLUTION_FAILED
    if not notations:
        return frozenset(), REASON_NO_NOTATIONS_RESOLVED
    return notations, None


def _candidate_notation(entry: dict[str, Any]) -> str:
    """Return ``entry``'s notation as a string, or ``''`` when it carries none."""
    notation = entry.get('notation')
    return notation if isinstance(notation, str) else ''


def cross_check_candidates(
    candidates: list[dict[str, Any]],
    project_dir: str,
    required: RequiredCoverage | None = None,
    *,
    coverage_unavailable_reason: str | None = None,
) -> dict[str, Any]:
    """Cross-check already-matching build rows on BOTH dimensions.

    ``candidates`` are the rows that ALREADY satisfy the gate's primary
    predicate (``kind == 'build'``, ``status == 'success'``,
    ``worktree_sha == current``), in ledger file order. This function decides
    which of them — if any — may be cited as the evidence for a ``fresh``
    verdict.

    The whole candidate list is examined rather than only the first match, and
    that is load-bearing for precision in the passing direction: a project that
    legitimately builds with several notations can have an unrelated row sitting
    ahead of a related one in file order, and returning on the first match would
    refuse a plan whose real evidence is two lines further down. One row that
    satisfies both dimensions is enough; only a list in which NONE does is a
    refusal.

    ⛔ **Selection is JOINT, not per-dimension.** A row is citable only when it is
    admissible on attribution AND on coverage, so the two dimensions cannot each
    pick a row the other would refuse — which is exactly how a 573-test
    directory run came to be cited as ``corroborated`` for a whole-tree change.
    An admissible row is one its dimension either endorsed or could not judge;
    where a dimension returned its refusal verdict (:data:`REFUTED` /
    :data:`NARROW`) no row is citable at all. Among the jointly-admissible rows
    the first in file order is chosen, matching the pre-cross-check behaviour of
    the gate's scan. The ledger is pure-append, so file order is write order.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order. MUST be
            non-empty — the caller handles the no-candidate case as ``stale``
            before reaching here, and this function has no honest verdict for an
            empty list: ``refuted`` would assert "no row carries a notation"
            about zero rows, and ``unverified`` would hand the caller a
            ``chosen`` index addressing nothing.
        project_dir: Project root the architecture is resolved against.
        required: What the change needs covered, or ``None`` when the caller
            could not derive it (the coverage dimension then reports
            :data:`UNDETERMINED` and refuses nothing).
        coverage_unavailable_reason: The caller's reason token for a ``None``
            ``required``, forwarded to :func:`scope_check_candidates`.

    Returns:
        A dict carrying, for the attribution dimension, ``verdict``
        (:data:`CORROBORATED` / :data:`REFUTED` / :data:`UNVERIFIED`),
        ``expected_notations`` (the sorted resolved set), ``candidate_notations``
        (the sorted distinct notations the candidates carried, a row carrying
        none contributing nothing) and ``reason`` (``None`` on
        :data:`CORROBORATED`); for the coverage dimension, ``scope_verdict``
        (:data:`COVERED` / :data:`NARROW` / :data:`UNDETERMINED`),
        ``scope_reason`` (``None`` on :data:`COVERED`) and ``row_scopes`` (the
        per-row rendering); and jointly ``chosen`` — the POSITION in
        ``candidates`` of the cited row, or ``None`` when either dimension
        refused or the two admissible sets are disjoint.

        ``chosen`` is a position rather than the row object so the caller can map
        it back to its own addressing (a ledger index) without either side
        depending on object identity. Handing back the dict instead would force
        the caller to recover the position by ``id()`` — sound only while this
        function returns one of the very objects it was passed, which is not a
        property its signature promises.

    Raises:
        ValueError: If ``candidates`` is empty. A precondition violation is a
            programming error and is failed fast rather than answered with
            whichever verdict the code happens to reach first.
    """
    if not candidates:
        raise ValueError(
            'cross_check_candidates requires at least one candidate row; the '
            'no-candidate case is the caller\'s stale route, not a cross-check verdict'
        )

    expected, resolution_reason = resolve_expected_notations(project_dir)
    candidate_notations = sorted({n for n in map(_candidate_notation, candidates) if n})

    if resolution_reason is not None:
        notation_verdict = UNVERIFIED
        notation_reason: str | None = resolution_reason
        attributable = list(range(len(candidates)))
        expected_notations: list[str] = []
    else:
        expected_notations = sorted(expected)
        attributable = [
            position
            for position, entry in enumerate(candidates)
            if _candidate_notation(entry) in expected
        ]
        if attributable:
            notation_verdict, notation_reason = CORROBORATED, None
        else:
            notation_verdict = REFUTED
            # A row with no notation at all and a row naming an unresolved build
            # are both refusals, but they need different remedies — one says
            # "this row was not written by the dispatch boundary", the other says
            # "this row is from a build this project does not perform" — so they
            # are named apart rather than folded into one message.
            notation_reason = (
                REASON_NOTATION_UNRELATED if candidate_notations else REASON_NOTATION_ABSENT
            )

    vocabulary, vocabulary_reason = load_analysis_vocabulary()
    scope = scope_check_candidates(
        candidates,
        required,
        vocabulary,
        unavailable_reason=coverage_unavailable_reason or vocabulary_reason,
    )

    # An UNDETERMINED dimension admits every row: it has shown nothing about any
    # of them, and treating "could not judge" as "judged unfit" would fail closed
    # on the absence of evidence — the direction this module refuses on both
    # dimensions for the same reason.
    coverable = (
        set(range(len(candidates)))
        if scope['verdict'] == UNDETERMINED
        else set(scope['covered_positions'])
    )
    admissible = [position for position in attributable if position in coverable]
    refused = notation_verdict == REFUTED or scope['verdict'] == NARROW
    chosen = admissible[0] if (not refused and admissible) else None

    # ``joint_reason`` is the ONE token the caller renders when nothing is
    # citable, and the disjoint case needs its own: both dimensions can decline to
    # refuse while still sharing no row — every attributable row was narrow AND
    # every covering row was unattributable — and reporting that as either
    # dimension's reason would name a refusal neither of them made.
    if chosen is not None:
        joint_reason: str | None = None
    elif notation_verdict == REFUTED:
        joint_reason = notation_reason
    elif scope['verdict'] == NARROW:
        joint_reason = scope['reason']
    else:
        joint_reason = REASON_NO_ADMISSIBLE_ROW

    return {
        'verdict': notation_verdict,
        'chosen': chosen,
        'expected_notations': expected_notations,
        'candidate_notations': candidate_notations,
        'reason': notation_reason,
        'scope_verdict': scope['verdict'],
        'scope_reason': scope['reason'],
        'row_scopes': scope['row_scopes'],
        'joint_reason': joint_reason,
    }
