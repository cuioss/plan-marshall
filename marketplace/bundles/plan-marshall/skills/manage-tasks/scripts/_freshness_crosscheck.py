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
perfectly attributable row may be a single-directory test run. That is why
:func:`cross_check_candidates` selects across them jointly rather than letting
either pick a row the other would refuse.

Joint selection — one row, or a union of rows at the same sha
=============================================================

The evidence a ``fresh`` verdict rests on is the ``contributing`` list: the
positions of the rows that together cover the change. It is built in two steps.

1. **One row.** When a single row is admissible on attribution AND covers the
   change alone, that row is the whole evidence — the first such row in ledger
   file order, a one-element list.
2. **A union.** When no single row does, the admissible rows are combined. The
   change is covered when, for EVERY required analysis, at least one admissible
   row performs that analysis at a scope adequate for the change: whole-tree
   when the change's blast radius is whole-tree, otherwise a scope containing
   the change's module set. A gate that runs ``quality-gate`` and
   ``module-tests`` as separate whole-tree builds covers a ``.py`` footprint
   exactly as one ``verify`` does, and refusing it would demand a redundant
   build that examines nothing new.

⛔ **Scope is judged per analysis and never pooled.** A module-scoped lint run
and a whole-tree test run do not add up to whole-tree lint: each analysis needs
its OWN row at an adequate scope, and two narrow rows never combine into a wide
one. The rules that keep a row from contributing what it did not do are the same
ones that refuse it alone — a row that measured zero tests contributes no test
coverage, and a row whose ``args`` cannot be read or whose canonical is outside
the vocabulary contributes nothing at all.

⛔ **Narrow units are never an input to the coverage dimension.** The change
side is the change's module set and its whole-tree verdict, derived without the
resolver's narrow-unit lists; nothing here reads ``narrow_units``. On the row
side, a row scoped to a narrow unit - one test directory or one test file of a
module - names a part of that module, so it does not contain the change's
module set and is adequate for no required analysis. A green narrow-unit row is
a faster first signal for the step that ran it; it is not evidence that the
change was covered.

The contributing set is deterministic: per required analysis, the first adequate
admissible row in ledger file order. Only rows the attribution dimension admits
may contribute; where attribution could not judge, every row stays admissible.

When the rows still fall short, the refusal names WHICH required analyses no
admissible row performed at an adequate scope (``missing_analyses``). The
per-row tokens alone do not say that once several rows each cover part of the
change, and it is the fact that names the remedy: run the missing analysis,
rather than repeat one already covered.

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

  **The one exception is a whole-tree change against rows whose SCOPE cannot be
  read.** There the inability has a claim attached to it — the change needs every
  required analysis over the whole tree — and an unreadable row substantiates
  none of that claim. That is the ratio this module is built on: fail closed where
  the ledger was asked for the widest evidence and could not show it, pass with
  the inability named everywhere the change asks for less.

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

**The row already carries more than the gate reads — checked, not
assumed.** ``_ledger_core.build_record`` records ``notation``, ``args`` (the
executor argv, stamped on every build-class dispatch as
``' '.join(script_args)``), ``command_args`` (the single ``--command-args``
element), ``command`` (the line the wrapper reported running) and ``outcome``
(the wrapper's whole stdout TOON). The gate reads ``notation`` for attribution,
``command_args`` when present for the payload boundary, and ``args`` for
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

A flag after the canonical is a different matter, and :func:`parse_row_scope`
resolves it conservatively: a KNOWN scope-bearing flag (maven's ``-pl`` /
``--projects`` and npm's ``--workspace``, each grounded in the resolver that emits
it) contributes its value to the scope, a known non-narrowing companion
(``-am`` / ``--also-make``) is ignored, and **any other flag makes the row
unreadable**. Reading an unknown flag as "no scope" would assert whole-tree over a
run that might have been narrowed inside the lost quoting — the false-green
direction — so it is an inability with its reason recorded instead.

**A POSITIONAL token is module scope only for the tool whose positionals are
modules.** The pyproject wrapper's canonical commands take ``<canonical>
<module>``, so its positionals are scope. npm, Maven and Gradle do not: their
discoverers emit the tool's own goals, tasks and script names (``run test``,
``clean install``, ``spotlessCheck check``), and reading those as a module scope
refutes a whole-tree change as ``build_scope_narrow`` when the row in fact ran
whole-tree. Which reading applies is decided by the row's own ``notation`` — the
one field that says what its positionals ARE — never by guessing a tool from its
arguments (:data:`_GOAL_POSITIONAL_NOTATIONS` and
:data:`_PYPROJECT_NOTATION`). A notation the reader does not know is read only
when it carries a single positional (the canonical); with two or more it is an
inability, because the reader cannot tell a module from a goal and either guess
manufactures a coverage claim nobody measured.

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
3. **Only a POSITIVE refutation fails closed, and one inability fails closed with
   it.** A canonical outside the known vocabulary, and a change whose required
   coverage could not be derived, both yield :data:`UNDETERMINED` and pass with the
   inability recorded — the same split fail-direction the attribution dimension
   takes, for the same reason. A row whose SCOPE cannot be read is the exception,
   and only where the change needs whole-tree coverage: that change claims every
   required analysis ran over the whole tree, and a row nobody could place cannot
   show any part of it, so the joint selection refuses it
   (:data:`REASON_SCOPE_UNREADABLE_WHOLE_TREE`) rather than trading the false-green
   for a quiet pass on strictly no evidence. The same row still passes a change
   that needs less, with the inability recorded — so the exception is bounded by
   the change's blast radius, never a general licence to refuse a pre-existing
   ledger row.

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

#: The candidate rows cover the change's blast radius — one row alone, or several
#: rows that between them perform every required analysis at an adequate scope.
#: The gate may cite the rows the verdict rests on.
COVERED = 'covered'
#: The readable candidate rows PROVABLY fall short of the change, alone and
#: combined — at least one required analysis was performed by no row at an
#: adequate scope. This is positive knowledge, so it fails closed.
NARROW = 'narrow'
#: The coverage comparison could not be performed on either side. Nothing is
#: known, so — like :data:`UNVERIFIED` on the attribution dimension — it passes
#: with the inability recorded rather than failing closed on no evidence. The one
#: exception is a whole-tree change whose candidate rows carry unreadable scope:
#: there the joint selection refuses (see
#: :data:`REASON_SCOPE_UNREADABLE_WHOLE_TREE`), because that change claims the
#: widest coverage and an unreadable row cannot substantiate any part of it.
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
#: ``scope_cross_check_reason`` when no candidate row can be read for scope: its
#: ``args`` carries no ``--command-args``, or every canonical it names is outside
#: the known vocabulary, or a row carries a flag that is neither a known
#: scope-bearing one nor a known non-narrowing companion — so its blast radius
#: cannot be placed inside or outside the command's lost quoting. The rows were
#: read and said nothing usable about coverage — distinct from a row that said
#: something and was refuted.
REASON_SCOPE_UNREADABLE = 'build_scope_unreadable'
#: ``stale`` reason (and the joint refusal token) when a row's scope cannot be read
#: AND the change needs whole-tree coverage. The coverage dimension still reports
#: :data:`UNDETERMINED` — it genuinely could not judge — but the joint selection
#: refuses, because an inability to show a whole-tree run is not evidence of one.
#: Named apart from :data:`REASON_SCOPE_UNREADABLE` so a reader can tell the
#: ordinary narrow-change pass (inability recorded, no refusal) from this refusal.
REASON_SCOPE_UNREADABLE_WHOLE_TREE = 'build_scope_unreadable_for_whole_tree_change'
#: ``stale`` reason (and ``scope_cross_check_reason``). THE refusal this
#: dimension exists to make.
REASON_SCOPE_NARROW = 'build_scope_narrow'
#: ``stale`` reason for the DISJOINT case, in which neither dimension refused.
#: Named apart from both dimensions' own reasons
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

#: The remedy sentence a refusal carries when a row predates the
#: ``command_args`` field, so the joined ``args`` cannot place a flag that follows
#: the payload. Prose, not a token: it goes into the gate's ``message``, where a
#: reader needs the fix rather than a name for the defect.
LEGACY_ROW_SCOPE_REMEDY = (
    'This row predates the command_args field, so a flag recorded after '
    '--command-args cannot be placed inside or outside the payload: put the '
    "executor's own flag before --command-args (or drop it), and re-run so the row "
    'records the payload as its own field. '
)

#: The executor flag that introduces the canonical command and its scope in a
#: ``kind=build`` row's ``args``. Copied verbatim from the shared ``run``
#: subparser declaration (``_build_cli.add_run_subparser``), which is why this
#: reader works for every build tool rather than only for the Python one.
_COMMAND_ARGS_FLAG = '--command-args'

#: Flags a build tool's resolved executable carries that NARROW the run to a
#: subset of modules, mapped to the number of value tokens each consumes. Each
#: entry is grounded in a resolver in this repository:
#:
#: * ``-pl`` / ``--projects`` — maven's module list (``mod-a`` or ``mod-a,mod-b``),
#:   emitted beside ``-am`` by ``_maven_cmd_discover``;
#: * ``--workspace`` — npm's workspace selector, emitted as ``--workspace=<name>``
#:   by ``_npm_cmd_discover``.
#:
#: ⛔ A flag NOT in this map is deliberately NOT propagated as scope. The ledger
#: joins its argv without quoting, so a flag after the canonical command cannot be
#: placed inside or outside the command's own quoting — reading it as whole-tree
#: would manufacture the false-green this dimension exists to close. Such a row
#: returns ``None`` (UNREADABLE) instead.
_SCOPE_FLAGS: dict[str, int] = {
    '-pl': 1,
    '--projects': 1,
    '--workspace': 1,
}

#: Flags that are KNOWN NOT to narrow the run, so they neither contribute scope
#: nor make the row unreadable. Each is a zero-arity companion of a scope flag the
#: tool's resolved executable emits next to it: maven's ``-am`` / ``--also-make``
#: is always emitted beside ``-pl`` (:mod:`_maven_cmd_discover`), and it only
#: ADDS the selected modules' dependencies. Ignoring it cannot create a
#: whole-tree claim while a scope was actually selected: the ``-pl`` value beside
#: it (or a positional module) still names the scope. With NO scope of any kind
#: the row is unreadable instead — ``package -am`` alone selects nothing.
_SCOPE_NEUTRAL_FLAGS: frozenset[str] = frozenset({'-am', '--also-make'})

#: The one notation whose POSITIONAL payload tokens are module names: the
#: pyproject wrapper's canonical commands take ``<canonical> <module>``, so every
#: positional after the canonical is scope.
_PYPROJECT_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

#: Notations whose positional payload tokens are the tool's OWN goals, tasks or
#: script names rather than module names. Each is emitted by a discoverer that
#: records the tool-native shape:
#:
#: * ``plan-marshall:build-maven:maven`` — ``clean install``, ``test``, and
#:   ``verify -pl X -am`` (:mod:`_maven_cmd_discover`);
#: * ``plan-marshall:build-gradle:gradle`` — ``spotlessCheck check``,
#:   ``test jacocoTestReport``, and the single tokens ``build`` / ``test``
#:   (:mod:`_gradle_cmd_discover`);
#: * ``plan-marshall:build-npm:npm`` — ``install``, ``run build``, ``run lint``,
#:   ``run test`` (:mod:`_npm_cmd_discover`).
#:
#: For these, the first positional is still the canonical — the same reading
#: ``_build_examined.examined_analyses`` takes — every remaining positional is
#: dropped, and the scope is only what a known scope-bearing flag selects.
#: Reading a goal as a module would refute every whole-tree change of a project
#: built by one of these tools, which is the false red :func:`parse_row_scope`
#: exists to avoid.
_GOAL_POSITIONAL_NOTATIONS: frozenset[str] = frozenset(
    {
        'plan-marshall:build-maven:maven',
        'plan-marshall:build-gradle:gradle',
        'plan-marshall:build-npm:npm',
    }
)

#: The ``run`` subparser's OWN flags — the ones that sit in a legacy row's joined
#: ``args`` beside the payload, in the same unquoted token stream, so the reader
#: cannot tell whether they belonged to the payload or to the executor. Each
#: consumes one value token. Copied from the shared subparser declaration
#: (``_build_cli.add_run_subparser``: ``--timeout``, ``--mode``, ``--format`` and
#: ``--execution-mode``, plus the ``--project-dir`` / ``--plan-id`` pair) and the
#: tool-local extras npm and pyproject declare (``--working-dir``, ``--env``).
#:
#: Only one of these can be the flag that made a legacy row unreadable, because
#: only these are the EXECUTOR's: any other flag either belongs to the build tool
#: itself (``-k``, ``-Ppre-commit``) or is a scope-bearing one the reader already
#: knows (``-pl``, ``--workspace``).
_EXECUTOR_RUN_FLAGS: dict[str, int] = {
    '--timeout': 1,
    '--mode': 1,
    '--format': 1,
    '--execution-mode': 1,
    '--project-dir': 1,
    '--plan-id': 1,
    '--working-dir': 1,
    '--env': 1,
}


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
        analyses: The analysis kinds the change can break.
        whole_tree: True when only a whole-tree run covers the change — the
            footprint spans several modules, touches cross-module infrastructure,
            contains a path no registered module owns, or resolves to a module
            that is named only (a test tree that is no bundle, or one reached
            through the declared source-to-test mapping).
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
    except Exception:  # an import can fail as more than ImportError
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
    resolved module set does. A row scoped to a test tree that is no bundle is
    never adequate: the resolver reports every footprint that names such a tree
    as ``divergence_possible``.

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


def freshness_inputs_for_composition(
    footprint: list[str],
    scoped_modules: tuple[str, ...],
    divergence_possible: bool,
) -> dict[str, Any]:
    """Expose the freshness inputs the D7 gate composition consumes.

    This helper publishes the shared surface: the live ``footprint``, the
    resolver-derived ``scoped_modules`` and ``divergence_possible`` verdict,
    and the derived :class:`RequiredCoverage` (or the
    ``required_coverage_unknown`` reason token when the vocabulary cannot be
    loaded and nothing could be derived). The pre-commit-verify-freshness
    gate's ``_resolve_required_coverage`` consumes this helper for its
    vocabulary-plus-derivation tail and reconstructs the frozen
    :class:`RequiredCoverage` from the plain-values dict, so the gate and
    every other reader of this surface derive the requirement from one
    helper rather than each inlining the same two calls.

    Args:
        footprint: The live plan footprint, repo-relative.
        scoped_modules: The module set ``resolve_test_scope`` derived from it.
        divergence_possible: ``resolve_test_scope``'s whole-tree verdict.

    Returns:
        A dict carrying ``footprint``, ``scoped_modules``,
        ``divergence_possible``, and either ``required`` (the derived
        :class:`RequiredCoverage` as ``analyses`` / ``whole_tree`` / ``modules``
        plain values) or ``reason`` (:data:`REASON_REQUIRED_COVERAGE_UNKNOWN`).
    """
    vocabulary, reason = load_analysis_vocabulary()
    if vocabulary is None:
        return {
            'footprint': list(footprint),
            'scoped_modules': list(scoped_modules),
            'divergence_possible': divergence_possible,
            'required': None,
            'reason': reason or REASON_REQUIRED_COVERAGE_UNKNOWN,
        }
    required = required_coverage(footprint, scoped_modules, divergence_possible, vocabulary)
    return {
        'footprint': list(footprint),
        'scoped_modules': list(scoped_modules),
        'divergence_possible': divergence_possible,
        'required': {
            'analyses': sorted(required.analyses),
            'whole_tree': required.whole_tree,
            'modules': sorted(required.modules),
        },
        'reason': None,
    }


def _row_payload_tokens(entry: dict[str, Any]) -> list[str] | None:
    """Return the ``--command-args`` payload tokens ``entry`` records, or ``None``.

    Prefers the executor's ``command_args`` field: that value is the ONE argv
    element the flag received, so it needs no marker search and can never absorb
    a flag that sat after it. Falls back to the marker search in the joined
    ``args`` for a row written before that field existed.

    Args:
        entry: A ``kind=build`` ledger row.

    Returns:
        The payload tokens in order, or ``None`` when the row carries no payload.
        An empty list is a recorded-but-empty payload, which the caller rejects
        rather than reading as whole-tree.
    """
    recorded = entry.get('command_args')
    if isinstance(recorded, str):
        return recorded.split()
    args = entry.get('args')
    if not isinstance(args, str):
        return None
    tokens = args.split()
    for position, token in enumerate(tokens):
        if token == _COMMAND_ARGS_FLAG:
            return tokens[position + 1 :]
        if token.startswith(f'{_COMMAND_ARGS_FLAG}='):
            return [token.split('=', 1)[1], *tokens[position + 1 :]]
    return None


def parse_row_scope(entry: dict[str, Any]) -> RowScope | None:
    """Read the canonical and scope a ``kind=build`` row records, or ``None``.

    Reads the payload the row recorded — the ``command_args`` field when the
    executor wrote one, otherwise the tokens that follow ``--command-args`` in the
    joined ``args`` — and takes its first non-flag as the canonical. What the
    REMAINING positional tokens mean is decided by the row's own ``notation``,
    because that is the only field that says what its tool's positionals ARE:

    * a pyproject row (:data:`_PYPROJECT_NOTATION`) keeps the ``<canonical>
      <module>`` reading: its positionals are module names and are scope;
    * an npm, Maven or Gradle row (:data:`_GOAL_POSITIONAL_NOTATIONS`) carries the
      tool's own goals, tasks or script names, never module names: its remaining
      positionals are dropped and contribute no scope, exactly as
      ``_build_examined.examined_analyses`` reads only the first token;
    * any other notation — absent or unknown — is read only when it carries ONE
      positional token; two or more return ``None``, because the reader cannot
      tell a module from a goal and either guess would manufacture a coverage
      claim nobody measured.

    A KNOWN scope-bearing flag (:data:`_SCOPE_FLAGS`) contributes its value to the
    scope for every notation, since the flag is what selects the tool's modules.
    In the joined fallback both the space-separated (``--command-args verify``) and
    the joined (``--command-args=verify``) spellings are accepted, because argparse
    accepts both and the ledger stamps whichever the caller used.

    ⛔ ``None`` means UNREADABLE and is never equivalent to a ``RowScope`` with an
    empty ``scope_tokens``. Empty tokens assert *whole-tree*, which is the widest
    possible coverage claim; returning it for a row nobody could parse would
    manufacture exactly the false-green this dimension exists to remove. ``args``
    that is absent, not a string, carries no ``--command-args``, or carries one
    with no following non-flag token all yield ``None``.

    A flag that is NOT a known scope-bearing one also yields ``None`` rather than
    silently ending the scope. The ledger joins ``args`` WITHOUT quoting, so a
    flag after the canonical cannot be placed inside or outside the command's own
    quoting — an unknown flag might be narrowing the build (``-k foo``,
    ``-Dtest=…``) or might be the executor's own (``--timeout``), and reading
    either as whole-tree is the false-green direction. The fail direction is an
    inability whose reason is recorded, never a coverage credit: the row cannot
    certify a WHOLE-TREE change (the joint selection refuses it, see
    :data:`REASON_SCOPE_UNREADABLE_WHOLE_TREE`) and still passes a change that
    needs less, with the inability recorded. The one exception is a KNOWN
    non-narrowing companion (:data:`_SCOPE_NEUTRAL_FLAGS`,
    maven's ``-am`` / ``--also-make``): it provably cannot narrow, so it is
    ignored rather than making the row unreadable.

    ``command`` is deliberately not consulted as a fallback — see the module
    docstring for why a build-tool-specific command line cannot be read for scope
    without risking a wrong *whole-tree* answer.

    Args:
        entry: A ``kind=build`` ledger row.

    Returns:
        The recorded :class:`RowScope`, or ``None`` when it cannot be read.
    """
    rest = _row_payload_tokens(entry)
    if rest is None:
        return None
    payload: list[str] = []
    scope: list[str] = []
    saw_neutral = False
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in _SCOPE_NEUTRAL_FLAGS:
            saw_neutral = True
            index += 1
            continue
        if token.startswith('-'):
            name, separator, inline = token.partition('=')
            arity = _SCOPE_FLAGS.get(name)
            if arity is None:
                return None
            if separator:
                values = [inline]
            else:
                values = []
                for offset in range(1, arity + 1):
                    if index + offset >= len(rest) or rest[index + offset].startswith('-'):
                        return None
                    values.append(rest[index + offset])
                index += arity
            if not all(values):
                return None
            parts = [part for value in values for part in value.split(',') if part]
            if not parts:
                # ``-pl=`` / ``-pl=,`` names no scope at all. Returning an empty
                # tuple here would assert whole-tree on the back of a flag that was
                # meant to narrow — the one direction this reader must never take.
                return None
            scope.extend(parts)
        elif token:
            payload.append(token)
        index += 1
    if not payload:
        return None
    notation = entry.get('notation')
    if isinstance(notation, str) and notation in _GOAL_POSITIONAL_NOTATIONS:
        # The remaining positionals are the tool's own goals, tasks or script
        # names. They narrow nothing, so they are dropped rather than read as a
        # module scope: ``run test`` is a whole-tree run, and only the tool's own
        # scope flag can narrow it.
        payload = payload[:1]
    elif notation != _PYPROJECT_NOTATION and len(payload) > 1:
        return None
    if saw_neutral and not scope and len(payload) == 1:
        # A neutral companion with NO scope of any kind (``package -am``) is not a
        # whole-tree claim: the flag only means "also the selected modules'
        # dependencies", and the resolver never emits it without ``-pl``. Nothing
        # selected the modules, so the blast radius is unreadable rather than the
        # widest possible one.
        return None
    return RowScope(canonical=payload[0], scope_tokens=tuple(payload[1:] + scope))


def _payload_without_executor_run_flags(tokens: list[str]) -> list[str] | None:
    """Return ``tokens`` with every declared executor ``run`` flag removed.

    A declared flag is dropped together with its one value token, and the
    ``--flag=value`` spelling drops the whole token. ``None`` means a declared
    flag had no value to drop, so no reconstruction of the payload is possible.

    Args:
        tokens: The row's recorded payload-and-tail tokens.

    Returns:
        The remaining tokens, or ``None`` when a declared flag carries no value.
    """
    remaining: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        name, separator, _inline = token.partition('=')
        arity = _EXECUTOR_RUN_FLAGS.get(name)
        if arity is None:
            remaining.append(token)
            index += 1
            continue
        if separator:
            index += 1
            continue
        if index + arity >= len(tokens):
            return None
        index += arity + 1
    return remaining


def row_scope_remedy_hint(entry: dict[str, Any]) -> str | None:
    """Name the row-specific remedy when ``entry`` is unreadable for want of the field.

    A row that carries a ``--command-args`` payload in its joined ``args`` but no
    ``command_args`` field cannot say whether a later flag belonged to the payload
    or to the executor. Telling its reader to "re-run a build" loops — the re-run
    writes the same shape — so the refusal names the changes that work.

    The hint applies only where that ambiguity is the actual cause: the tail after
    the payload must carry one of the ``run`` subparser's OWN flags
    (:data:`_EXECUTOR_RUN_FLAGS`) AND the payload with those flags and their
    values removed must parse. A row made unreadable by a flag that belongs to the
    build tool (``module-tests -k foo``) has no executor flag to move, and naming
    one would send its reader after a remedy that does not exist.

    Args:
        entry: A ``kind=build`` ledger row.

    Returns:
        :data:`LEGACY_ROW_SCOPE_REMEDY` for that shape, otherwise ``None``.
    """
    if isinstance(entry.get('command_args'), str):
        return None
    if parse_row_scope(entry) is not None:
        return None
    tokens = _row_payload_tokens(entry)
    if not tokens:
        return None
    stripped = _payload_without_executor_run_flags(tokens)
    if stripped is None:
        return None
    if parse_row_scope({**entry, 'command_args': ' '.join(stripped)}) is None:
        return None
    return LEGACY_ROW_SCOPE_REMEDY


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

    Evaluated from the most decisive fact to the least: a row nobody could parse,
    then a READABLE scope that provably built less than the change needs, then a
    canonical outside the vocabulary, then the analyses. Scope comes before the
    canonical because the vocabulary is PARTIAL by design — an unmapped canonical
    is an inability that passes, and it must not mask a row that positively
    recorded a narrower blast radius.

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
    if not _scope_adequate(scope, required):
        return ROW_SCOPE_TOO_NARROW
    performed = vocabulary.by_canonical.get(scope.canonical)
    if performed is None:
        return ROW_CANONICAL_UNKNOWN
    if not required.analyses <= performed:
        return ROW_CANONICAL_TOO_WEAK
    if vocabulary.test in required.analyses and _measured_zero_tests(entry):
        return ROW_TESTS_EXECUTED_ZERO
    return None


#: The per-row refusals that are INABILITIES rather than refutations. A candidate
#: list in which every row took one of these routes is :data:`UNDETERMINED`.
_INABILITY_REFUSALS = frozenset({ROW_ARGS_UNREADABLE, ROW_CANONICAL_UNKNOWN})


def _scope_adequate(scope: RowScope, required: RequiredCoverage) -> bool:
    """Return True when ``scope`` is wide enough for the change.

    A row with no scope tokens ran whole-tree and is adequate for any change. A
    scoped row is adequate only for a change that is not whole-tree and whose
    module set it contains.
    """
    if not scope.scope_tokens:
        return True
    if required.whole_tree:
        return False
    return required.modules <= set(scope.scope_tokens)


def row_contribution(
    entry: dict[str, Any],
    required: RequiredCoverage,
    vocabulary: AnalysisVocabulary,
) -> frozenset[str]:
    """Return the required analyses ``entry`` performed at an adequate scope.

    This is what a row may lend to a union of rows. Scope is judged for the row
    as a whole, so a row too narrow for the change contributes nothing — it never
    lends its analyses to a wider row, and never borrows a wider row's scope.

    A row that measured zero tests contributes no test coverage, though it still
    contributes whatever else it performed. A row whose ``args`` cannot be read,
    or whose canonical is outside the vocabulary, contributes nothing.

    Args:
        entry: A ``kind=build`` ledger row.
        required: What the change needs covered.
        vocabulary: The canonical→analyses map.

    Returns:
        The subset of ``required.analyses`` this row covers, possibly empty.
    """
    scope = parse_row_scope(entry)
    if scope is None:
        return frozenset()
    performed = vocabulary.by_canonical.get(scope.canonical)
    if performed is None or not _scope_adequate(scope, required):
        return frozenset()
    contributed = required.analyses & performed
    if _measured_zero_tests(entry):
        contributed -= {vocabulary.test}
    return contributed


def union_contributors(
    candidates: list[dict[str, Any]],
    required: RequiredCoverage,
    vocabulary: AnalysisVocabulary,
    admissible: list[int],
) -> dict[int, list[str]] | None:
    """Combine the admissible rows into one covering set, or return ``None``.

    For each required analysis the FIRST admissible row, in the order
    ``admissible`` lists them, that performs it at an adequate scope is credited
    with it. The change is covered only when every required analysis found such a
    row.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order.
        required: What the change needs covered.
        vocabulary: The canonical→analyses map.
        admissible: The positions in ``candidates`` that may contribute, in
            ledger file order.

    Returns:
        Position → the sorted analyses that row is credited with, ordered by
        position, or ``None`` when some required analysis has no adequate row. An
        empty requirement yields an empty mapping.
    """
    contributions = {position: row_contribution(candidates[position], required, vocabulary) for position in admissible}
    credited: dict[int, list[str]] = {}
    for analysis in sorted(required.analyses):
        owner = next((position for position in admissible if analysis in contributions[position]), None)
        if owner is None:
            return None
        credited.setdefault(owner, []).append(analysis)
    return {position: credited[position] for position in sorted(credited)}


def uncovered_analyses(
    candidates: list[dict[str, Any]],
    required: RequiredCoverage,
    vocabulary: AnalysisVocabulary,
    admissible: list[int],
) -> list[str]:
    """Name the required analyses no admissible row performed at an adequate scope.

    This is what a refusal owes its reader. Per-row tokens say why each row falls
    short alone; with rows that each perform part of what the change requires,
    they do not say which analysis is still missing — and that is the one fact
    that names the remedy.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order.
        required: What the change needs covered.
        vocabulary: The canonical→analyses map.
        admissible: The positions in ``candidates`` that may contribute.

    Returns:
        The sorted uncovered analyses. Empty when the admissible rows cover the
        change between them.
    """
    covered: set[str] = set()
    for position in admissible:
        covered |= row_contribution(candidates[position], required, vocabulary)
    return sorted(required.analyses - covered)


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
        ``candidates`` of every row that covers the change ALONE, in file
        order), ``union_positions`` (the positions the verdict rests on when no
        single row covers but the rows combined do — empty otherwise),
        ``reason`` (``None`` on :data:`COVERED`, otherwise the naming constant)
        and ``row_scopes`` — one ``'{canonical} {scope}: {verdict}'`` line per
        candidate, so the decision record shows WHAT each row recorded and
        whether it covers the change alone rather than only the aggregate. A row
        that contributes to a union still carries its own per-row refusal token
        there: the token says the row does not cover the change by itself, which
        stays true. ``missing_analyses`` is the sorted list of required analyses
        no row performed at an adequate scope. It is populated only on
        :data:`NARROW`: it is empty on :data:`COVERED`, and empty on
        :data:`UNDETERMINED`, where nothing could be judged and so nothing is
        known to be missing.
    """
    if vocabulary is None:
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'union_positions': [],
            'missing_analyses': [],
            'reason': REASON_VOCABULARY_UNIMPORTABLE,
            'row_scopes': [],
        }
    if required is None:
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'union_positions': [],
            'missing_analyses': [],
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
            'union_positions': [],
            'missing_analyses': [],
            'reason': None,
            'row_scopes': row_scopes,
        }
    # No row covers the change alone. Several rows at the same sha may still
    # cover it between them, each analysis judged at its own row's scope.
    # An empty mapping is an empty requirement no row could be read for — nothing
    # was established, so it falls through to the refusal classification below.
    every_row = list(range(len(candidates)))
    union = union_contributors(candidates, required, vocabulary, every_row)
    if union:
        return {
            'verdict': COVERED,
            'covered_positions': [],
            'union_positions': list(union),
            'missing_analyses': [],
            'reason': None,
            'row_scopes': row_scopes,
        }
    # The rows fall short alone and combined. The verdict turns on WHICH refusals
    # occurred: a list in which nothing could be read is an absence of knowledge,
    # while a single substantive refutation means the ledger positively shows a
    # build narrower than the change — and one such row is enough to fail closed,
    # exactly as one corroborating row is enough to pass on the attribution
    # dimension.
    if not refusals or all(refusal in _INABILITY_REFUSALS for refusal in refusals):
        # Nothing could be read, so nothing is known to be missing either: naming
        # an analysis here would assert a gap no row was shown to have.
        return {
            'verdict': UNDETERMINED,
            'covered_positions': [],
            'union_positions': [],
            'missing_analyses': [],
            'reason': REASON_SCOPE_UNREADABLE,
            'row_scopes': row_scopes,
        }
    return {
        'verdict': NARROW,
        'covered_positions': [],
        'union_positions': [],
        'missing_analyses': uncovered_analyses(candidates, required, vocabulary, every_row),
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
    except Exception:  # see below: an import can fail as more than ImportError
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
    except Exception:  # any resolver failure is an inability, not a refutation
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


def _joint_contributors(
    candidates: list[dict[str, Any]],
    attributable: list[int],
    scope: dict[str, Any],
    required: RequiredCoverage | None,
    vocabulary: AnalysisVocabulary | None,
) -> dict[int, list[str]]:
    """Return the rows the evidence rests on, each with its credited analyses.

    Called only when neither dimension refused. Three routes, in order:

    * The coverage dimension could not judge. It has shown nothing about any
      row, and treating "could not judge" as "judged unfit" would fail closed on
      the absence of evidence, so the first attributable row is cited with no
      analysis credited to it.
    * An attributable row covers the change alone. The first such row in file
      order is the whole evidence.
    * Otherwise the attributable rows are combined — see
      :func:`union_contributors`.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order.
        attributable: The positions attribution admits, in file order.
        scope: The coverage dimension's own verdict dict.
        required: What the change needs covered, or ``None``.
        vocabulary: The canonical→analyses map, or ``None``.

    Returns:
        Position → sorted credited analyses, ordered by position. Empty when no
        attributable rows cover the change.
    """
    if not attributable:
        return {}
    if scope['verdict'] == UNDETERMINED or required is None or vocabulary is None:
        return {attributable[0]: []}
    covering_alone = set(scope['covered_positions'])
    alone = next((position for position in attributable if position in covering_alone), None)
    if alone is not None:
        return {alone: sorted(required.analyses)}
    return union_contributors(candidates, required, vocabulary, attributable) or {}


def _unreadable_scope_blocks_whole_tree(
    candidates: list[dict[str, Any]],
    required: RequiredCoverage | None,
    scope: dict[str, Any],
) -> bool:
    """Whether an unreadable row's inability refuses a WHOLE-TREE change.

    The split fail-direction this module takes — a refutation fails closed, an
    inability passes with the inability recorded — holds for every change whose
    blast radius a row could still substantiate on another dimension. It does not
    hold where the change needs WHOLE-TREE coverage and a candidate row's scope
    could not be read at all: there the row can join neither an adequate answer
    nor a refusal, and passing it would assert coverage nobody measured. Such a
    change needs every required analysis at whole-tree scope, so an unreadable row
    can only be evidence of something narrower — or of nothing.

    The rows are re-read here rather than judged from the dimension's reason token,
    because one :data:`UNDETERMINED` verdict can come from an unreadable ``args``
    or from a canonical outside the vocabulary. Only the first is this refusal:
    the second is the vocabulary's documented partiality, which stays an inability
    that passes.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order.
        required: What the change needs covered, or ``None`` when underivable.
        scope: The coverage dimension's verdict dict.

    Returns:
        True only for a whole-tree change whose coverage verdict is
        :data:`UNDETERMINED` and at least one candidate row cannot be read for
        scope. A verdict whose reason is
        :data:`REASON_VOCABULARY_UNIMPORTABLE` is never this refusal: that token
        says THIS CHECK IS BROKEN, which must stay visible rather than be
        relabelled as a property of the rows.
    """
    if required is None or not required.whole_tree:
        return False
    if scope['verdict'] != UNDETERMINED:
        return False
    if scope['reason'] == REASON_VOCABULARY_UNIMPORTABLE:
        return False
    return any(parse_row_scope(entry) is None for entry in candidates)


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
    refuse a plan whose real evidence is two lines further down.

    ⛔ **Selection is JOINT, not per-dimension.** The two dimensions cannot each
    pick a row the other would refuse — which is exactly how a 573-test
    directory run came to be cited as ``corroborated`` for a whole-tree change.
    An admissible row is one its dimension either endorsed or could not judge;
    where a dimension returned its refusal verdict (:data:`REFUTED` /
    :data:`NARROW`) no row is citable at all. The ledger is pure-append, so file
    order is write order.

    The evidence is the ``contributing`` list. A jointly-admissible row that
    covers the change alone is the whole evidence — the first such row in file
    order. When there is none, the attributable rows are combined: the change is
    covered when every required analysis is performed by at least one of them at
    an adequate scope, and the list names the first adequate row per analysis.
    A row attribution refused never contributes, however wide it ran.

    Args:
        candidates: Matching ``kind=build`` rows in ledger file order. MUST be
            non-empty — the caller handles the no-candidate case as ``stale``
            before reaching here, and this function has no honest verdict for an
            empty list: ``refuted`` would assert "no row carries a notation"
            about zero rows, and ``unverified`` would hand the caller a
            ``contributing`` list addressing nothing.
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
        per-row rendering); and jointly ``contributing`` — the ordered POSITIONS
        in ``candidates`` of the rows the evidence rests on, empty when either
        dimension refused or no admissible rows cover the change — and
        ``contributing_analyses``, a list parallel to ``contributing`` naming the
        sorted required analyses each of those rows is credited with (an empty
        list for a row cited while the coverage dimension could not judge) — and
        ``missing_analyses``, the sorted required analyses that no row
        attribution admits performed at an adequate scope. That list is empty
        whenever ``contributing`` is not, and empty where the requirement or the
        vocabulary was unavailable, since nothing can then be named. On an
        attribution refusal no row is admissible, so it names every required
        analysis.

        ``contributing`` holds positions rather than row objects so the caller
        can map each back to its own addressing (a ledger index) without either
        side depending on object identity. Handing back the dicts instead would
        force the caller to recover the positions by ``id()`` — sound only while
        this function returns the very objects it was passed, which is not a
        property its signature promises.

    Raises:
        ValueError: If ``candidates`` is empty. A precondition violation is a
            programming error and is failed fast rather than answered with
            whichever verdict the code happens to reach first.
    """
    if not candidates:
        raise ValueError(
            'cross_check_candidates requires at least one candidate row; the '
            "no-candidate case is the caller's stale route, not a cross-check verdict"
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
        attributable = [position for position, entry in enumerate(candidates) if _candidate_notation(entry) in expected]
        if attributable:
            notation_verdict, notation_reason = CORROBORATED, None
        else:
            notation_verdict = REFUTED
            # A row with no notation at all and a row naming an unresolved build
            # are both refusals, but they need different remedies — one says
            # "this row was not written by the dispatch boundary", the other says
            # "this row is from a build this project does not perform" — so they
            # are named apart rather than folded into one message.
            notation_reason = REASON_NOTATION_UNRELATED if candidate_notations else REASON_NOTATION_ABSENT

    vocabulary, vocabulary_reason = load_analysis_vocabulary()
    scope = scope_check_candidates(
        candidates,
        required,
        vocabulary,
        unavailable_reason=coverage_unavailable_reason or vocabulary_reason,
    )

    whole_tree_unreadable = _unreadable_scope_blocks_whole_tree(candidates, required, scope)
    refused = notation_verdict == REFUTED or scope['verdict'] == NARROW or whole_tree_unreadable
    credited: dict[int, list[str]] = (
        {} if refused else _joint_contributors(candidates, attributable, scope, required, vocabulary)
    )
    contributing = list(credited)

    # ``joint_reason`` is the ONE token the caller renders when nothing is
    # citable, and the disjoint case needs its own: both dimensions can decline to
    # refuse while still sharing no rows — the attributable rows fall short of the
    # change AND every row that would close the gap was unattributable — and
    # reporting that as either dimension's reason would name a refusal neither of
    # them made.
    if contributing:
        joint_reason: str | None = None
    elif notation_verdict == REFUTED:
        joint_reason = notation_reason
    elif scope['verdict'] == NARROW:
        joint_reason = scope['reason']
    elif whole_tree_unreadable:
        joint_reason = REASON_SCOPE_UNREADABLE_WHOLE_TREE
    else:
        joint_reason = REASON_NO_ADMISSIBLE_ROW

    # What a refusal still lacks is judged over the rows that MAY be cited: an
    # analysis only an unattributable row performed is still missing. Where the
    # requirement or the vocabulary is unavailable nothing can be named, and an
    # unreadable scope names nothing either — the row may have performed every
    # required analysis at a scope nobody could place, so naming a gap would
    # assert a shortfall the ledger does not show.
    if contributing or required is None or vocabulary is None or whole_tree_unreadable:
        missing_analyses: list[str] = []
    else:
        missing_analyses = uncovered_analyses(candidates, required, vocabulary, attributable)

    return {
        'verdict': notation_verdict,
        'contributing': contributing,
        'contributing_analyses': [credited[position] for position in contributing],
        'missing_analyses': missing_analyses,
        'expected_notations': expected_notations,
        'candidate_notations': candidate_notations,
        'reason': notation_reason,
        'scope_verdict': scope['verdict'],
        'scope_reason': scope['reason'],
        'row_scopes': scope['row_scopes'],
        'joint_reason': joint_reason,
    }
