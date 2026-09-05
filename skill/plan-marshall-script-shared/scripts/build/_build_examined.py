#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""What a build run actually examined — the population an auto-resolve may act on.

A green build is not, on its own, evidence that a recorded finding is fixed. Two
independent things have to be true before a green run may clear a pending
finding, and neither is implied by the exit code:

1. **The run examined a non-empty population.** A gate that executed nothing
   proves nothing. A ``compile`` that compiled no module, a test command that
   collected no test, and a run whose population could not be determined at all
   are three states that must never be read as "looked, found nothing wrong".
2. **The run performed an analysis that can reach the finding's subject.** A
   ``compile`` cannot evaluate a lint-issue at any scope. Its green says nothing
   whatsoever about the lint dimension — not "clean", not "probably clean", but
   *un-asked*.

Both were missing. ``build-error`` and ``lint-issue`` findings were cleared by
ANY green build regardless of what it ran, which let a ``./pw compile`` run
resolve a 129-item ``plugin-doctor`` record four times over, each time stamping
its own disconfirming evidence ("0 test(s) executed") into the resolution detail.

This module is the deterministic substrate that closes both holes. It is pure —
no I/O, no subprocess, no clock — so the decision is unit-testable in isolation
and identical for every build tool.

Unknown is not empty
--------------------
The distinction this module exists to hold is between a population that was
MEASURED and found empty, and one that could not be measured at all. They are
represented by different values and are never collapsed:

* ``None`` — the population could not be determined (an unrecognised command, a
  test gate whose summary did not parse). Nothing may be concluded from it.
* ``frozenset()`` / ``0`` — the run genuinely examined nothing / executed no
  test. This IS a measurement, and it still authorises no clearing.

Both refuse, so the *behaviour* coincides; the values stay distinct so the
published reason names which of the two actually happened. A refusal that cannot
say why is the same opaque signal one layer up.

Fail-closed by construction
---------------------------
:func:`examined_analyses` recognises the CANONICAL build-command vocabulary
(``compile``, ``quality-gate``, ``module-tests``, ``verify``, …) — the same names
``architecture resolve --command {canonical}`` publishes. A build tool whose
``--command-args`` carry tool-native goals rather than canonical names therefore
resolves to ``None``, and clears nothing. That is deliberate: a wrong-but-plausible
mapping from an unrecognised goal string would silently authorise exactly the
clearing this module exists to refuse.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Analysis kinds — what a build run can actually do
# ---------------------------------------------------------------------------

ANALYSIS_COMPILE = 'compile'
"""Translation / type-consistency analysis (compilation, mypy)."""

ANALYSIS_LINT = 'lint'
"""Static structural / style analysis (ruff, structural linters, header checks)."""

ANALYSIS_TEST = 'test'
"""Test execution — running the tests that exist."""

# ---------------------------------------------------------------------------
# Finding type -> the analyses that can reach it
# ---------------------------------------------------------------------------

FINDING_TYPE_ANALYSES: dict[str, frozenset[str]] = {
    'build-error': frozenset({ANALYSIS_COMPILE}),
    'lint-issue': frozenset({ANALYSIS_LINT}),
    'test-failure': frozenset({ANALYSIS_TEST}),
}
"""Each build finding type mapped to the analysis kinds that can EXERCISE it.

A green run may clear a finding of type ``T`` only when the analyses it performed
intersect ``FINDING_TYPE_ANALYSES[T]``. The map is total over
:data:`BUILD_FINDING_TYPES` by construction — the tuple is derived from these
keys — so a newly-added finding type cannot acquire an implicit empty analysis
set, which would read as "no analysis is required" and clear on every build.
"""

BUILD_FINDING_TYPES: tuple[str, ...] = tuple(FINDING_TYPE_ANALYSES)
"""The three per-type finding stores a build run writes to and reconciles.

Derived from :data:`FINDING_TYPE_ANALYSES` rather than declared beside it, so the
two can never disagree about which types exist.
"""

# ---------------------------------------------------------------------------
# Canonical command -> the analyses it performs
# ---------------------------------------------------------------------------

CANONICAL_ANALYSES: dict[str, frozenset[str]] = {
    'compile': frozenset({ANALYSIS_COMPILE}),
    'test-compile': frozenset({ANALYSIS_COMPILE}),
    'quality-gate': frozenset({ANALYSIS_COMPILE, ANALYSIS_LINT}),
    'module-tests': frozenset({ANALYSIS_TEST}),
    'integration-tests': frozenset({ANALYSIS_TEST}),
    'e2e': frozenset({ANALYSIS_TEST}),
    'coverage': frozenset({ANALYSIS_TEST}),
    'verify': frozenset({ANALYSIS_COMPILE, ANALYSIS_LINT, ANALYSIS_TEST}),
}
"""The canonical build-command vocabulary mapped to the analyses each performs.

PARTIAL over the authoritative command set by design, not by omission. A command
this vocabulary cannot describe is ABSENT rather than mapped to the empty set:
absent means undetermined (:func:`examined_analyses` returns ``None`` and
:func:`clearable_finding_types` then clears nothing), whereas an empty set would
publish a measured "examined nothing" that is false.

Which commands those are is stated rather than left to inference —
:data:`NON_ANALYSIS_COMMANDS` names each one with its reason, and
``TestMapsArePopulationDerived`` asserts the two together cover every member of
``ALL_CANONICAL_COMMANDS``. A newly-added canonical command therefore cannot
join the vocabulary silently: it must be mapped here or explained there.
"""

NON_ANALYSIS_COMMANDS: dict[str, str] = {
    'clean': (
        'removes build output and analyses nothing itself; it is also very often '
        'the head of a chain (``clean verify``) whose later goals do the real '
        'work, so its leading token does not determine what the run examined'
    ),
    'benchmark': (
        'produces runtime timings, which are not a verdict in any of the three '
        'analysis kinds this vocabulary distinguishes'
    ),
    'arch-gate': (
        'reports architectural-constraint violations, which are none of '
        ':data:`BUILD_FINDING_TYPES`, so no analysis kind here describes what a '
        'green one is entitled to clear'
    ),
    'install': (
        'the analyses it performs are build-tool-dependent — Maven runs the whole '
        'lifecycle including tests, npm resolves dependencies and runs none — so '
        'the token alone does not determine them'
    ),
    'clean-install': (
        'the ``clean`` + ``install`` chain, undetermined for both reasons above'
    ),
    'package': (
        'assembles an archive from already-built output; like ``install`` it is '
        'build-tool-dependent whether any analysis ran under it, and any that did '
        'belongs to the goals that preceded it'
    ),
}
"""Authoritative canonical commands this vocabulary deliberately does NOT map.

The residue of :data:`CANONICAL_ANALYSES` over ``ALL_CANONICAL_COMMANDS``, each
member carrying why no analysis set can honestly describe it. Declared as a map
rather than a bare set so the reason is attached to the member instead of to a
comment beside it, and so the guard can assert every member HAS one — an
unexplained entry here would be the silent absence this pairing exists to end.
"""


def examined_analyses(command_args: str | None) -> frozenset[str] | None:
    """Return the analyses a build invocation performed, or ``None`` when unknown.

    The leading whitespace-delimited token of ``command_args`` is the canonical
    command name; any trailing tokens are scope (a module name, tool flags) and do
    not change WHICH analyses run, only over how much. A leading token outside
    :data:`CANONICAL_ANALYSES` yields ``None`` — the population is undetermined,
    not empty.

    Args:
        command_args: The build invocation's ``--command-args`` value, e.g.
            ``'quality-gate plan-marshall'``. ``None`` or blank yields ``None``.

    Returns:
        The frozen set of analysis kinds the run performed, or ``None`` when the
        command is not one this vocabulary describes.
    """
    if not command_args:
        return None
    tokens = command_args.strip().split()
    if not tokens:
        return None
    return CANONICAL_ANALYSES.get(tokens[0])


def resolve_tests_run(analyses: frozenset[str] | None, parsed_total: int | None) -> int | None:
    """Resolve the executed-test count, keeping "unknown" distinct from zero.

    A parsed summary is authoritative whatever it says. Absent one, the honest
    value depends on whether the run was even supposed to execute tests: a gate
    that performs no test analysis genuinely ran zero (a MEASURED zero), while a
    test-bearing gate whose summary did not parse ran an UNKNOWN number — the log
    may be truncated, the daemon job log may carry only the wrapper's own TOON, or
    the parser may have failed. Reporting the latter as ``0`` is the false
    could-not-look that made a 2750-test run announce it had tested nothing.

    Args:
        analyses: The analyses the run performed, or ``None`` when unknown.
        parsed_total: The executed-test count a parser produced, or ``None`` when
            no test summary was parsed.

    Returns:
        The executed-test count, or ``None`` when it could not be determined.
    """
    if parsed_total is not None:
        return parsed_total
    if analyses is None:
        return None
    if ANALYSIS_TEST in analyses:
        return None
    return 0


def clearable_finding_types(
    analyses: frozenset[str] | None, tests_run: int | None
) -> tuple[str, ...]:
    """Return the finding types this green run is entitled to clear.

    A type is clearable only when the run performed at least one analysis that can
    reach it. ``test-failure`` carries the additional, stronger requirement that
    the run executed a MEASURED non-zero number of tests: a test gate that
    collected nothing, or whose count is unknown, clears no recorded test failure.

    An unknown population (``analyses is None``) clears nothing at all — there is
    no basis on which to entitle anything.

    Args:
        analyses: The analyses the run performed, or ``None`` when unknown.
        tests_run: The executed-test count, or ``None`` when unknown.

    Returns:
        The clearable finding types in :data:`BUILD_FINDING_TYPES` order, possibly
        empty.
    """
    if analyses is None:
        return ()
    clearable: list[str] = []
    for finding_type in BUILD_FINDING_TYPES:
        if not (FINDING_TYPE_ANALYSES[finding_type] & analyses):
            continue
        if finding_type == 'test-failure' and not (tests_run is not None and tests_run > 0):
            continue
        clearable.append(finding_type)
    return tuple(clearable)


def population_label(analyses: frozenset[str] | None, tests_run: int | None) -> str:
    """Render the population a clearing decision was made on, for publication.

    The label is stamped into the resolution detail of every auto-resolved finding
    and into the run's own stderr line, so the population is PUBLISHED rather than
    left implicit. Unknown renders as the word, never as a zero or an empty list.

    Args:
        analyses: The analyses the run performed, or ``None`` when unknown.
        tests_run: The executed-test count, or ``None`` when unknown.

    Returns:
        A single-line, human-readable population description.
    """
    if analyses is None:
        examined = 'analyses examined: unknown'
    elif not analyses:
        examined = 'analyses examined: none'
    else:
        examined = f'analyses examined: {", ".join(sorted(analyses))}'
    counted = 'unknown' if tests_run is None else str(tests_run)
    return f'{examined}; {counted} test(s) executed'


def refusal_reason(analyses: frozenset[str] | None, tests_run: int | None) -> str | None:
    """Name why this run may clear nothing, or ``None`` when it may clear something.

    Only called for its explanatory value: the caller decides WHAT to clear from
    :func:`clearable_finding_types`. A refusal that cannot state its cause is
    indistinguishable from a run that simply had nothing pending, which is the
    opaque signal this module exists to replace.

    Args:
        analyses: The analyses the run performed, or ``None`` when unknown.
        tests_run: The executed-test count, or ``None`` when unknown.

    Returns:
        A short reason token, or ``None`` when at least one type is clearable.

    The branches are exhaustive without a dead residual: once ``analyses`` is a
    determined, non-empty set that reaches at least one finding type, the ONLY way
    the clearable set can still be empty is that the single reachable type is
    ``test-failure`` under an unmeasured or zero count — every other reachable type
    clears on analysis alone.
    """
    if clearable_finding_types(analyses, tests_run):
        return None
    if analyses is None:
        return 'population_unknown'
    if not analyses:
        return 'population_empty'
    reachable = {t for t in BUILD_FINDING_TYPES if FINDING_TYPE_ANALYSES[t] & analyses}
    if not reachable:
        return 'no_analysis_reaches_a_finding_type'
    return 'tests_unmeasured' if tests_run is None else 'tests_executed_zero'
