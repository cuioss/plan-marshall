# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure helpers for gate-coverage honesty: freshness, coverage boundary, parity.

The in-house pre-push build gate must be a *truthful* proxy for CI: where it
checks less than CI, or where it cannot substantiate a verdict, its own output
must say so rather than reporting a clean pass that means less than it appears
to. Three pure, tool-agnostic helpers back that property; ``build.py`` wires
them into the mypy-running commands and the ``verify`` / ``quality-gate``
summaries.

Fail-closed classification discipline
-------------------------------------
This module applies rule (d) "require an affirmative success signal, never
absence-of-change" and rule (b) "fail closed on undetermined / empty state" from
``ref-code-quality/standards/error-handling.md`` — see that document for the rule
statements rather than re-deriving them here.

1. **Freshness** (:func:`classify_check_duration`) — a stale incremental cache
   answers *"nothing I have cached changed"* and that is consumed as *"the tree
   type-checks"*. That is absence-of-change laundered into success. The precise
   fix lives in ``build.py`` (the gate runs mypy with the cache disabled, so the
   verdict is always computed against the current tree, matching CI's cold run).
   This function is the independent honest-signal backstop: a check that reports
   success over a substantial file set in a wall-time no real analysis could
   achieve did not actually check those files, so its "success" is not an
   affirmative signal and the caller fails closed on it. It is calibrated
   conservatively — a legitimate run, cold or warm, small or large, is never
   flagged — because a check that flags every fast gate would be disabled within
   a week, which is worse than not having it.

2. **Coverage boundary** (:class:`CoverageBoundary` / :func:`render_coverage_summary`)
   — a footprint the gate could not fully check must be *distinguishable* in the
   gate's own output from one that genuinely passed. The boundary accumulates
   what was checked and what was degraded (with the reason), and the renderer
   emits a summary whose PARTIAL form tells a reader the pass does not certify
   the un-checked dimensions.

2b. **Structural scope limit** (:class:`AnalysisLimit` / :func:`structural_limits`)
   — a *second*, orthogonal honesty property, and the one a COMPLETE verdict needs
   most. Coverage boundary answers *"did the gate check everything it set out to?"*;
   this answers *"and what can that check never see, however wide its scope?"* The
   distinction is load-bearing: a PARTIAL verdict is cured by re-running the degraded
   dimension, whereas a structural limit is a property of the ANALYSIS and is not
   cured by anything. mypy decides type consistency, so it cannot decide whether a
   well-typed value is the right one; pytest executes the tests that exist, so it is
   silent on inputs no test supplies; a structural linter checks the SHAPE of a
   document, so it cannot check whether a documented claim is TRUE. Those are exactly
   the defect classes an external reviewer keeps finding on a diff whose every
   in-house gate is green, and the defect this block closes is not that the gates are
   narrow — it is that **a narrow gate's green reads as whole-tree assurance**. The
   limits are derived from the dimensions the run ACTUALLY recorded, so a gate that
   analysed less states less; a dimension with no registered limit renders as UNKNOWN
   rather than being omitted, since omission would make the block read as exhaustive.

3. **Parity population** (:func:`parity_population`) — a **RECORDED** set of
   dimensions along which the local gate's coverage was compared to CI's. It is
   recorded, not derived: the cells and their notes were written by hand at plan
   160 and re-verified against ``origin/main`` at ``61a43e5``. It is returned so a
   test can assert it is **non-empty**: a parity table computed over nothing looks
   identical to perfect parity, which is exactly the confident-but-empty signal
   this whole effort exists to prevent. A non-empty assertion over a recorded
   literal is a weaker guarantee than one over a derivation, and calling it
   "derived" would overstate it — so at least one cell is additionally re-checked
   against the substrate it describes (see the function's own docstring).

All functions are pure — no I/O, no subprocess, no clock. Durations, file counts
and dimension verdicts are supplied by the caller, so the module is deterministic
and unit-testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Freshness — duration plausibility (D4)
# ---------------------------------------------------------------------------

#: A file set smaller than this is legitimately fast to check even from a warm
#: cache or on a tiny scope, so its duration is never judged. The plausibility
#: verdict applies only to a *substantial* file set, where "success in no time"
#: is the signal that no analysis actually ran.
SUSPECT_MIN_FILES: int = 100

#: The ceiling on files-per-second above which no real type-analysis occurred —
#: only a cache hit or a short-circuited no-op processes files this fast. This is
#: the "distinguish plausible-fast from impossible-fast" line, and it keys on
#: throughput relative to the claimed scope rather than on raw speed.
#:
#: The value is calibrated between two measurements, not picked as a round number
#: comfortably above everything:
#:
#: * The INCIDENT this backstop exists to catch reported success over 660 files in
#:   2-5 s — 132-330 files/s. A ceiling at or above 220.0 (= 660 / 3.0) therefore
#:   rates that incident *plausible*, and the backstop never bites on the very
#:   event it was written for. A ceiling set far above every conceivable run is
#:   not conservative; it is inert.
#: * A genuine COLD whole-tree run on this tree measures 417 files in 5.84 s =
#:   71 files/s, with mypy under ``--no-incremental`` — the way ``build.py``
#:   always runs it, so this is the throughput of the gate's own honest path, not
#:   of a warm cache.
#:
#: 200.0 sits between them. It flags the incident band from 200 files/s upward
#: (660 files in 3.3 s or faster) while leaving ~2.8x headroom over the measured
#: cold throughput, so a legitimate cold run — including one on a materially
#: faster machine — is not flagged. A small scope is not judged at all (see
#: :data:`SUSPECT_MIN_FILES`), because a check that flagged every fast gate would
#: be disabled within a week, which is worse than not having one.
MAX_ANALYSIS_THROUGHPUT: float = 200.0


@dataclass(frozen=True)
class DurationVerdict:
    """Whether a check's reported success is plausible for the work it claims.

    Attributes:
        plausible: True when the wall-time is consistent with really having
            checked ``files_checked`` files. False when the check reported
            success in a time no real analysis of that many files could take —
            the verdict is then not an affirmative success signal and the caller
            MUST fail closed on it.
        reason: A human-readable explanation when ``plausible`` is False; None
            when plausible. Mirrored into the audit/diagnostic surface so the
            degradation is legible rather than inferred.
    """

    plausible: bool
    reason: str | None


def classify_check_duration(files_checked: int, elapsed_seconds: float) -> DurationVerdict:
    """Judge whether reporting success over ``files_checked`` files in ``elapsed_seconds`` is plausible.

    A small file set (below :data:`SUSPECT_MIN_FILES`) is always plausible — a
    tiny scope is legitimately fast, and flagging it would make the check fire on
    every quick run. For a substantial file set, success is *implausible* when the
    implied throughput exceeds :data:`MAX_ANALYSIS_THROUGHPUT` (including the
    degenerate zero/negative-elapsed case, which is infinite throughput): no real
    type-analysis processes files that fast, so the checker answered from a cache
    or ran nothing at all.

    Args:
        files_checked: The number of source files the check claims to have
            covered. A conservative lower bound (e.g. the top-level file set) is
            fine — undercounting lowers the implied throughput, which only makes
            the verdict *less* likely to flag, never more.
        elapsed_seconds: Wall-clock seconds the check took.

    Returns:
        A frozen :class:`DurationVerdict`.
    """
    if files_checked < SUSPECT_MIN_FILES:
        return DurationVerdict(plausible=True, reason=None)
    if elapsed_seconds <= 0.0:
        return DurationVerdict(
            plausible=False,
            reason=(
                f'reported success over {files_checked} files in '
                f'{elapsed_seconds:.3f}s — no measurable work; the verdict rests '
                f'on a cache, not on the current tree'
            ),
        )
    throughput = files_checked / elapsed_seconds
    if throughput > MAX_ANALYSIS_THROUGHPUT:
        return DurationVerdict(
            plausible=False,
            reason=(
                f'reported success over {files_checked} files in '
                f'{elapsed_seconds:.3f}s = {throughput:.0f} files/s, above the '
                f'{MAX_ANALYSIS_THROUGHPUT:.0f} files/s ceiling real analysis '
                f'cannot beat — the verdict rests on a cache, not on the current tree'
            ),
        )
    return DurationVerdict(plausible=True, reason=None)


# ---------------------------------------------------------------------------
# Coverage boundary — honest partial-vs-full verdict (D5)
# ---------------------------------------------------------------------------


@dataclass
class CoverageBoundary:
    """Accumulator for what a gate run did and did not fully check.

    A dimension is recorded as *checked* when the gate ran the check over its
    full intended scope, as *degraded* when it could not — with the reason, so
    the degradation is named rather than silently folded into a clean pass — and
    as *empty-scope* when the gate reached the check but its scope held nothing
    to analyse. The third state is separate on purpose: an attempt over an empty
    scope is neither a pass nor a gap, and folding it into either one is what let
    a silently-skipped scope read as coverage.

    ``complete`` is the honest verdict and requires an AFFIRMATIVE signal: at
    least one dimension checked over its full scope, AND nothing degraded. A
    boundary that recorded nothing is NOT complete — "no dimension was degraded"
    is vacuously true of a run that checked nothing, so reading it as a full pass
    is absence-of-change laundered into success, which is rule (d) in this
    module's own docstring. An empty-scope record is not an affirmative signal
    either: it certifies that there was nothing to check, never that something
    checked out.
    """

    checked: list[str] = field(default_factory=list)
    degraded: list[tuple[str, str]] = field(default_factory=list)
    empty_scope: list[tuple[str, str]] = field(default_factory=list)

    def record_checked(self, dimension: str) -> None:
        """Record that ``dimension`` was checked over its full scope."""
        self.checked.append(dimension)

    def record_degraded(self, dimension: str, reason: str) -> None:
        """Record that ``dimension`` was NOT fully checked, and why."""
        self.degraded.append((dimension, reason))

    def record_empty_scope(self, dimension: str, scope: str) -> None:
        """Record that ``dimension`` was attempted but ``scope`` held nothing to check.

        The alternative — returning early with no record at all — leaves the
        dimension indistinguishable from one the gate never performs, which is
        the absence-read-as-coverage shape this module exists to close.
        """
        self.empty_scope.append((dimension, scope))

    @property
    def complete(self) -> bool:
        """True only when something was affirmatively checked and nothing was degraded."""
        return bool(self.checked) and not self.degraded


# ---------------------------------------------------------------------------
# Structural scope limit — what a green does NOT evaluate (plan 130 D0)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisLimit:
    """What one kind of analysis does, and what it therefore cannot evaluate.

    Attributes:
        analysis: The analysis the dimension actually performs, in one clause.
        cannot_evaluate: The defect class that analysis structurally cannot reach.
            It is a statement about the ANALYSIS, never about its scope — a limit
            phrased as "only the files it was given" would be a scope statement,
            which :class:`CoverageBoundary` already reports and which widening the
            scope would cure.
    """

    analysis: str
    cannot_evaluate: str


#: Analysis-kind -> its structural limit, keyed by the dimension STEM the gate
#: records (see :func:`dimension_stem`). Each entry names a defect class that
#: survives a fully-scoped green run of that analysis, so a reader of the verdict
#: can answer "what could still be wrong despite this passing?".
_ANALYSIS_LIMITS: dict[str, AnalysisLimit] = {
    'mypy(production)': AnalysisLimit(
        analysis='infers and checks type consistency across declarations, call sites and returns',
        cannot_evaluate=(
            'whether a well-typed value is the correct one. A binary read of a '
            'three-valued observable type-checks exactly as the three-way read does, '
            'so coercing an unknown into a positive passes this dimension'
        ),
    ),
    'mypy(test)': AnalysisLimit(
        analysis='checks type consistency across the test tree',
        cannot_evaluate=(
            'whether a well-typed test asserts anything meaningful. A test driven by a '
            'stub that encodes the retired behaviour type-checks and passes, so it '
            'cannot show that the test exercises the real code path'
        ),
    ),
    'ruff': AnalysisLimit(
        analysis='matches the enabled lint-rule set against the AST',
        cannot_evaluate=(
            'any defect no enabled rule encodes, and the semantics of the code its '
            'patterns do match — a rule family absent from the select list is not a '
            'clean result, it is an un-asked question'
        ),
    ),
    'SPDX headers': AnalysisLimit(
        analysis='checks that each in-scope file carries the literal header line',
        cannot_evaluate='anything whatsoever about the file content below that line',
    ),
    'plugin-doctor': AnalysisLimit(
        analysis='statically lints marketplace structure, frontmatter, and skill-body shape',
        cannot_evaluate=(
            'whether a documented claim is true. It checks that a workflow doc has the '
            'required shape, never that the remedy the doc prescribes is reachable, is '
            'invoked, or describes what the code does'
        ),
    ),
    'module-tests': AnalysisLimit(
        analysis='executes the tests that exist',
        cannot_evaluate=(
            'behaviour under inputs no test supplies. A green suite is evidence about '
            'the cases it encodes and is silent on every other one, so it cannot '
            'distinguish "correct" from "never exercised"'
        ),
    ),
}


def dimension_stem(dimension: str) -> str:
    """Return the analysis-kind key for a recorded dimension label.

    The gate records dimensions with a per-run scope suffix in brackets
    (``mypy(production) [660 files, cache disabled]``). The limit registry is keyed
    by analysis kind, so the varying suffix is stripped before lookup — keying on
    the full label would miss the registry on every real run.

    Args:
        dimension: The dimension label as recorded on the boundary.

    Returns:
        The text before the first ``' ['``, stripped.
    """
    return dimension.split(' [', 1)[0].strip()


def analysis_limit(stem: str) -> AnalysisLimit | None:
    """Return the registered structural limit for an analysis kind, or None.

    ``None`` means the analysis kind is not characterised here. The caller MUST
    render that as an explicit UNKNOWN rather than omitting the dimension: an
    omitted dimension makes the limit block read as exhaustive over a run that
    included an analysis nobody characterised.
    """
    return _ANALYSIS_LIMITS.get(stem)


def structural_limits(dimensions: list[str]) -> tuple[tuple[str, AnalysisLimit | None], ...]:
    """Pair each checked dimension with its structural limit, in recorded order.

    Derived from the dimensions the run ACTUALLY recorded — not from a fixed
    boilerplate block — so a gate that analysed less states fewer limits. Duplicate
    stems collapse to their first occurrence, since the limit is a property of the
    analysis kind rather than of the individual invocation.

    Args:
        dimensions: The boundary's ``checked`` labels, suffixes included.

    Returns:
        One ``(stem, limit_or_None)`` pair per distinct analysis kind, in order of
        first appearance. A ``None`` limit marks an uncharacterised analysis.
    """
    seen: set[str] = set()
    pairs: list[tuple[str, AnalysisLimit | None]] = []
    for dimension in dimensions:
        stem = dimension_stem(dimension)
        if stem in seen:
            continue
        seen.add(stem)
        pairs.append((stem, analysis_limit(stem)))
    return tuple(pairs)


def _render_structural_limits(boundary: CoverageBoundary) -> list[str]:
    """Render the per-analysis structural-limit block, or nothing when none applies.

    Returns an empty list for a boundary that checked nothing: attaching a
    scope-limit statement to a run that performed no analysis would read as though
    something had been analysed.

    The dimensions this run did NOT cover are deliberately not rendered here —
    see :func:`coverage_gaps`, which needs two scope facts the boundary alone
    cannot supply and must not be guessed from it.
    """
    pairs = structural_limits(boundary.checked)
    if not pairs:
        return []
    lines = [
        '    scope limit — what a green here does NOT evaluate, per analysis:',
    ]
    for stem, limit in pairs:
        if limit is None:
            lines.append(
                f'      - {stem}: UNKNOWN — no structural limit is registered for this '
                f'analysis, so this verdict cannot state what its green leaves '
                f'un-evaluated. Treat its coverage as UNKNOWN, not as complete.'
            )
            continue
        lines.append(f'      - {stem}: {limit.analysis}; it cannot evaluate {limit.cannot_evaluate}.')
    lines.append(
        '    These are properties of the analyses themselves, not of their scope: '
        'widening the scope does not reach them, and re-running does not cure them. '
        'A green above is evidence about the dimensions listed and is not whole-tree '
        'assurance that the change is sound.'
    )
    return lines


# ---------------------------------------------------------------------------
# Uncovered dimensions — WHY a dimension is absent, and the remedy each implies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageGaps:
    """The dimensions a run did not cover, split by WHY — each implying its own remedy.

    A dimension this run never recorded leaves NO trace: not checked, not
    degraded, simply absent. A reader then cannot tell *"this gate does not run
    tests"* from *"tests were fine"*, which is the absence-read-as-coverage shape
    one level up from the one the per-analysis limits close. Naming the absence
    is necessary — but naming it with ONE reason is how the previous form went
    wrong: it derived a single "this gate never performs them" list from
    ``registry - attempted``, which reads a per-INVOCATION absence as a statement
    about the COMMAND. A module-scoped ``quality-gate`` printed that the gate
    never performs ``plugin-doctor``, which is simply false — it performs it
    whole-tree.

    Attributes:
        not_at_this_scope: Dimensions this gate DOES perform, but not at the scope
            this invocation ran. Remedy: re-run at a wider scope, which reaches them.
        not_by_this_gate: Dimensions no invocation of this gate performs at ANY
            scope. Remedy: none here — widening the scope does not reach them, so
            only a different command, or CI, can cover their defect classes.
        empty_scope: ``(dimension, scope)`` pairs the gate DID reach, whose scope
            held nothing to analyse. Remedy: none — there is nothing to check, so
            the dimension is vacuously covered rather than skipped.
        scope_declared: False when the caller did not state what its invocation
            could run. Both derived sets are then empty because nothing
            substantiates them, and the renderer says so instead of printing a
            confident empty list.
    """

    not_at_this_scope: tuple[str, ...]
    not_by_this_gate: tuple[str, ...]
    empty_scope: tuple[tuple[str, str], ...]
    scope_declared: bool


def coverage_gaps(
    boundary: CoverageBoundary,
    could_run: frozenset[str] | None = None,
    gate_dimensions: frozenset[str] | None = None,
) -> CoverageGaps:
    """Classify the registered dimensions this run left uncovered, by reason.

    Splitting the absence by reason needs two facts the boundary cannot supply —
    what THIS invocation could have run at its scope, and what the gate performs
    at ANY scope — so the caller states both rather than the renderer inferring
    them. Degraded dimensions are excluded from both derived sets: those were
    attempted, and the PARTIAL verdict already reports them; listing them again
    would report one gap twice under two names.

    Args:
        boundary: The accumulated :class:`CoverageBoundary`.
        could_run: The dimension stems THIS invocation could have run at its
            scope. ``None`` means the caller did not declare it.
        gate_dimensions: The dimension stems this gate performs at ANY scope.
            ``None`` means the caller did not declare it.

    Returns:
        A :class:`CoverageGaps`. When either declaration is missing,
        ``scope_declared`` is False and both derived sets are empty — an
        undeclared scope yields an explicit unknown, never a confident empty list.
    """
    attempted = {dimension_stem(d) for d in boundary.checked}
    attempted |= {dimension_stem(d) for d, _ in boundary.degraded}
    attempted |= {dimension_stem(d) for d, _ in boundary.empty_scope}
    empty = tuple(boundary.empty_scope)
    if could_run is None or gate_dimensions is None:
        return CoverageGaps((), (), empty, scope_declared=False)
    return CoverageGaps(
        not_at_this_scope=tuple(sorted((gate_dimensions - could_run) - attempted)),
        not_by_this_gate=tuple(sorted((set(_ANALYSIS_LIMITS) - gate_dimensions) - attempted)),
        empty_scope=empty,
        scope_declared=True,
    )


def _render_coverage_gaps(gaps: CoverageGaps) -> list[str]:
    """Render the uncovered-dimension clauses, each stating the remedy it implies."""
    lines: list[str] = []
    for dimension, scope in gaps.empty_scope:
        lines.append(
            f'    attempted, nothing in scope — {dimension}: {scope}. The gate '
            f'reached this check and found nothing to analyse, so the dimension is '
            f'vacuously covered: there is nothing here to re-run, and no result is '
            f'being withheld.'
        )
    if not gaps.scope_declared:
        lines.append(
            '    uncovered dimensions: UNKNOWN — this invocation did not declare '
            'which analyses its scope could run, so this verdict cannot say which '
            'of them were left out because of the scope and which this gate never '
            'performs. Treat every dimension absent from the list above as '
            'un-evaluated, not as passed.'
        )
        return lines
    if gaps.not_at_this_scope:
        lines.append(
            f'    not performed at this scope: {", ".join(gaps.not_at_this_scope)} — '
            f'performed by this gate, but NOT at the scope this invocation ran. '
            f'Absent as a consequence of the scope, NOT because they passed; a run at '
            f'a wider scope reaches them.'
        )
    if gaps.not_by_this_gate:
        lines.append(
            f'    not performed by this gate at all: {", ".join(gaps.not_by_this_gate)} — '
            f'no invocation of this gate performs them at any scope, so widening the '
            f'scope does not reach them either. Only a different command, or CI, '
            f'covers their defect classes.'
        )
    return lines


def render_coverage_summary(
    boundary: CoverageBoundary,
    could_run: frozenset[str] | None = None,
    gate_dimensions: frozenset[str] | None = None,
) -> str:
    """Render a reader-facing coverage summary that distinguishes full, partial and unknown.

    There are THREE verdicts, not two. The COMPLETE form names what was checked.
    The PARTIAL form names what was NOT fully checked and states, in words, that
    the pass does not certify those dimensions — so a reader asked "is it safe to
    push?" against a partial verdict reads *no, the gate did not check X*, never a
    clean pass. The UNKNOWN form is the empty boundary: a run that recorded
    nothing at all certifies nothing, and it gets its own verdict rather than
    falling through to COMPLETE with an easily-overlooked empty checked-list. The
    wording is load-bearing: it is text whose value is what a reader does with it.

    **Both forms carry the structural scope limit** (:func:`structural_limits`),
    because the two properties answer different questions and the COMPLETE form
    needs the second one most. A COMPLETE verdict is the one a reader most readily,
    and most wrongly, reads as assurance that the change is sound. The appended
    block states per analysis what that green does not
    evaluate at all, so the reader can answer *"what could still be wrong despite
    this passing?"*. PARTIAL carries it too: without it, naming the un-run dimension
    still implies the dimensions that DID run cover their subject completely.

    Args:
        boundary: The accumulated :class:`CoverageBoundary`.
        could_run: The dimension stems this invocation could have run at its
            scope, forwarded to :func:`coverage_gaps`. ``None`` renders the
            uncovered dimensions as an explicit UNKNOWN instead of splitting them.
        gate_dimensions: The dimension stems this gate performs at any scope, also
            forwarded to :func:`coverage_gaps`.

    Returns:
        A single multi-line string suitable for printing as the gate's final
        coverage verdict.
    """
    gaps = coverage_gaps(boundary, could_run, gate_dimensions)
    if not boundary.checked and not boundary.degraded:
        # The explicit-unknown verdict. Neither a pass nor a named gap exists, so
        # there is no evidence in either direction — and an absence of evidence
        # must not render as the same word a fully-checked run renders as.
        lines = [
            '>>> coverage: UNKNOWN — this run recorded no dimension it checked and '
            'none it failed to check, so it certifies nothing. An empty coverage '
            'boundary is an absence of evidence, never evidence of coverage: read '
            'it as "the gate established nothing here", not as a pass.'
        ]
        lines.extend(_render_coverage_gaps(gaps))
        return '\n'.join(lines)
    if boundary.complete:
        lines = [
            f'>>> coverage: COMPLETE over the dimensions below — checked over full '
            f'scope: {", ".join(boundary.checked)}'
        ]
    else:
        lines = [
            '>>> coverage: PARTIAL — this pass does NOT certify the whole tree. '
            'The gate did NOT fully check:',
        ]
        for dimension, reason in boundary.degraded:
            lines.append(f'      - {dimension}: {reason}')
        lines.append(
            '    A clean exit here is NOT a full pass — the dimensions above are '
            'un-certified, so it is not safe to treat this as CI-equivalent.'
        )
        if boundary.checked:
            lines.append(f'    (Fully checked: {", ".join(boundary.checked)}.)')
    lines.extend(_render_structural_limits(boundary))
    lines.extend(_render_coverage_gaps(gaps))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Parity population — the recorded comparison set
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParityCell:
    """One dimension along which the local gate's coverage is compared to CI's.

    Attributes:
        dimension: The check dimension being compared.
        verdict: ``'equal'`` (local gate covers exactly what CI does),
            ``'subset'`` (local gate can cover less), or ``'closed'`` (a former
            divergence now reconciled by this or a sibling change). Any value
            other than ``'equal'``/``'closed'`` marks an axis needing attention.
        note: Short evidence for the verdict.
    """

    dimension: str
    verdict: str
    note: str


def parity_population() -> tuple[ParityCell, ...]:
    """Return the RECORDED set of local-gate-vs-CI parity dimensions.

    This is the machine-readable form of plan 160's D1 parity table: the
    dimensions along which the in-house gate's coverage was compared to CI's
    (``./pw verify``). **The cells are a recorded literal, not a derivation.**
    Each ``verdict`` and ``note`` was established by reading both sides at plan
    160 and re-verified against ``origin/main`` at ``61a43e5``; nothing recomputes
    them, and no production code consumes this function — its sole consumer is the
    test suite.

    Naming that honestly matters because the alternative reading is the defect
    this module exists to prevent: a hand-written table described as "derived"
    invites a reader to trust its cells as current, when in fact a change to
    either side leaves them stale and silent. Building real derivation machinery
    for an artifact with no production consumer is a capability change and was
    deliberately not taken; relabelling it and binding one cell to its substrate
    was.

    **One cell IS re-checked against its substrate**: ``spdx-paths`` names the
    exact path list the whole-tree quality gate hands to the SPDX checker, and
    ``test/plan-marshall/build-pyproject/test_gate_coverage_parity_substrate.py``
    asserts that note against ``build.py``'s actual construction. A note that
    drifts from the code fails the build instead of quietly misdescribing it. The
    other cells remain recorded-only, and that asymmetry is deliberate rather than
    an oversight.

    The population spans both axes the goal names — scope and freshness — plus
    the honest-coverage-boundary property that is the through-line of both.
    """
    return (
        ParityCell('mypy-production', 'equal', 'whole-tree quality-gate arm == cmd_compile(None)'),
        ParityCell('ruff-rules', 'equal', 'single [tool.ruff.lint] select shared by both'),
        ParityCell('ruff-paths', 'equal', 'ruff check [bundles, targets, test, .claude] on both'),
        ParityCell('mypy-test', 'equal', 'unconditional whole-tree test-compile == cmd_test_compile(None)'),
        ParityCell('spdx-paths', 'equal', 'SPDX over [bundles, test, .claude, targets, build.py] on both'),
        ParityCell('plugin-doctor', 'equal', 'whole-tree quality-gate arm runs the marketplace-wide pass'),
        ParityCell('pytest-scope', 'subset', 'divergence heuristic ignores reverse cross-module coupling (sibling territory)'),
        ParityCell('freshness', 'closed', 'gate runs mypy cold (cache disabled) + duration sanity check, matching cold CI'),
        ParityCell('coverage-boundary', 'closed', 'gate output names its coverage boundary (partial vs full verdict)'),
        # The two SHARED-BLIND cells. A parity table that lists only the dimensions
        # somebody checks reads as though the unlisted ones do not exist; recording
        # a dimension whose coverage is equal AND ZERO is what keeps 'equal' from
        # meaning 'equally well covered'. Both are blind spots, not divergences —
        # CI runs this same build.py — so the verdict is 'equal' and the note has
        # to carry the zero, or the cell overstates.
        ParityCell(
            'ruff-mypy-build-py', 'equal',
            'build.py is in no ruff path list and in no mypy scope on either side '
            '(SPDX headers do cover it) — coverage is equal and zero',
        ),
        ParityCell(
            'ruff-mypy-targets', 'equal',
            'marketplace/targets is in no ruff path list and in no mypy scope on '
            'either side (SPDX headers do cover it) — coverage is equal and zero',
        ),
    )
