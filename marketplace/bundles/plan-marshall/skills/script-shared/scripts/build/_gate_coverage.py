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

3. **Parity population** (:func:`parity_population`) — the derived set of
   dimensions along which the local gate's coverage is compared to CI's. It is
   returned so a test can assert it is **non-empty**: a parity table derived from
   nothing looks identical to perfect parity, which is exactly the confident-but-
   empty signal this whole effort exists to prevent.

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
#: only a cache hit or a short-circuited no-op processes files this fast. Set
#: deliberately far above any cold-analysis throughput (cold mypy analyses tens
#: of files per second, not thousands) so a legitimate run is never flagged.
#: This is the "distinguish plausible-fast from impossible-fast" line: it keys on
#: throughput relative to the claimed scope, not on raw speed.
MAX_ANALYSIS_THROUGHPUT: float = 2000.0


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
    full intended scope, and as *degraded* when it could not — with the reason,
    so the degradation is named rather than silently folded into a clean pass.
    ``complete`` is the honest verdict: the run checked everything it set out to
    only when nothing was degraded.
    """

    checked: list[str] = field(default_factory=list)
    degraded: list[tuple[str, str]] = field(default_factory=list)

    def record_checked(self, dimension: str) -> None:
        """Record that ``dimension`` was checked over its full scope."""
        self.checked.append(dimension)

    def record_degraded(self, dimension: str, reason: str) -> None:
        """Record that ``dimension`` was NOT fully checked, and why."""
        self.degraded.append((dimension, reason))

    @property
    def complete(self) -> bool:
        """True only when no dimension was degraded — the full-coverage verdict."""
        return not self.degraded


def render_coverage_summary(boundary: CoverageBoundary) -> str:
    """Render a reader-facing coverage summary that distinguishes full from partial.

    The COMPLETE form names what was checked. The PARTIAL form names what was NOT
    fully checked and states, in words, that the pass does not certify those
    dimensions — so a reader asked "is it safe to push?" against a partial
    verdict reads *no, the gate did not check X*, never a clean pass. The wording
    is load-bearing: it is text whose value is what a reader does with it.

    Args:
        boundary: The accumulated :class:`CoverageBoundary`.

    Returns:
        A single multi-line string suitable for printing as the gate's final
        coverage verdict.
    """
    checked = ', '.join(boundary.checked) if boundary.checked else '(nothing)'
    if boundary.complete:
        return f'>>> coverage: COMPLETE — checked over full scope: {checked}'
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
        lines.append(f'    (Fully checked: {checked}.)')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Parity population — the derived comparison set (D1 / D6)
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
    """Return the derived set of local-gate-vs-CI parity dimensions.

    This is the machine-readable form of plan 160's D1 parity table: the
    dimensions along which the in-house gate's coverage is compared to CI's
    (``./pw verify``). It is derived here so a test can assert it is **non-empty**
    — a parity table computed over an empty population is indistinguishable from
    perfect parity, and that empty-looks-like-perfect confusion is the exact
    defect this gate-coverage work exists to prevent.

    The population spans both axes the goal names — scope and freshness — plus
    the honest-coverage-boundary property that is the through-line of both.
    """
    return (
        ParityCell('mypy-production', 'equal', 'whole-tree quality-gate arm == cmd_compile(None)'),
        ParityCell('ruff-rules', 'equal', 'single [tool.ruff.lint] select shared by both'),
        ParityCell('ruff-paths', 'equal', 'ruff check [bundles, test, .claude] on both'),
        ParityCell('mypy-test', 'equal', 'unconditional whole-tree test-compile == cmd_test_compile(None)'),
        ParityCell('spdx-paths', 'equal', 'SPDX over [bundles, test, .claude, targets, build.py] on both'),
        ParityCell('plugin-doctor', 'equal', 'whole-tree quality-gate arm runs the marketplace-wide pass'),
        ParityCell('pytest-scope', 'subset', 'divergence heuristic ignores reverse cross-module coupling (sibling territory)'),
        ParityCell('freshness', 'closed', 'gate runs mypy cold (cache disabled) + duration sanity check, matching cold CI'),
        ParityCell('coverage-boundary', 'closed', 'gate output names its coverage boundary (partial vs full verdict)'),
    )
