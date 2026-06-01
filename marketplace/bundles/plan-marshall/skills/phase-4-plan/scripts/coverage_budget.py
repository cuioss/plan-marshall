"""Per-task token-budget reserve scaled by the declared scope × thoroughness cell.

D6 of the coverage-contract feature: the per-task budget reserve (the minimum
context window the phase-5-execute loop reserves before starting another task)
scales monotonically with the declared coverage cell. A wider scope (more files
in radius) and a higher thoroughness (deeper relation tracing) both justify a
larger reserve, so the matrix is monotonic on BOTH axes — raising either dial
never lowers the reserve.

The module is a thin pure-function surface so it is unit-testable in isolation:

- :func:`reserve_for_cell` — the deterministic ``(scope, thoroughness) -> int``
  lookup matrix.
- :func:`resolve_and_reserve` — resolves the declared cell via D3's
  ``manage-config coverage resolve`` and returns the reserve for that cell, with
  an ``inherit`` / unconfigured cell mapping to the documented baseline reserve.

The ladders and the coupling constraint are defined once in
``dev-agent-behavior-rules/standards/thoroughness.md`` and resolved by
``manage-config coverage resolve`` (D3) — this module does NOT re-validate the
coupling constraint (an incoherent ``T4 ∧ change-set`` cell is rejected upstream
by D3 before it ever reaches the budget computation).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from file_ops import get_executor_path  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Baseline reserve for an unconfigured / inherit cell. Matches the
# phase-5-execute ``per_task_budget_reserve`` fallback default (the conservative
# yield boundary documented in phase-5-execute/SKILL.md § "Resolving N").
_BASELINE_RESERVE = 50_000

# Per-axis ordinal rank, kept in lock-step with the ladders in
# ``dev-agent-behavior-rules/standards/thoroughness.md`` (and
# ``manage-config/scripts/_cmd_coverage.py``). Rank 0 is reserved for the
# implicit baseline (inherit) so a configured rung always scales strictly above
# the baseline.
_THOROUGHNESS_RANK: dict[str, int] = {'T1': 1, 'T2': 2, 'T3': 3, 'T4': 4, 'T5': 5}
_SCOPE_RANK: dict[str, int] = {
    'change-set': 1,
    'artifact': 2,
    'component': 3,
    'module': 4,
    'overall': 5,
}

# Per-step increment (in tokens) added per rank above the baseline on each axis.
# The reserve is ``BASELINE + (scope_rank - 1) * STEP + (thoroughness_rank - 1)
# * STEP`` — additive on both axes guarantees monotonicity: increasing either
# rank strictly increases the reserve, and a flat axis leaves the reserve
# unchanged on that axis.
_RESERVE_STEP = 25_000


def reserve_for_cell(scope: str, thoroughness: str) -> int:
    """Return the per-task token-budget reserve for a ``(scope, thoroughness)`` cell.

    The reserve scales monotonically on both axes from :data:`_BASELINE_RESERVE`.
    An ``inherit`` (or otherwise unranked) value on either axis contributes the
    baseline rank for that axis only — so an unconfigured dial neither raises nor
    lowers the reserve, and the fully-unconfigured cell returns the baseline.

    Monotonicity contract (verified by the import-time self-check below):
    raising ``scope`` or ``thoroughness`` by one rung never decreases the
    returned reserve.

    Args:
        scope: A scope rung (``change-set`` … ``overall``) or ``inherit``.
        thoroughness: A thoroughness rung (``T1`` … ``T5``) or ``inherit``.

    Returns:
        The per-task token-budget reserve in tokens.
    """
    scope_rank = _SCOPE_RANK.get(scope, 1)
    thoroughness_rank = _THOROUGHNESS_RANK.get(thoroughness, 1)
    return _BASELINE_RESERVE + (scope_rank - 1) * _RESERVE_STEP + (thoroughness_rank - 1) * _RESERVE_STEP


def _run_coverage_resolve(phase: str) -> dict[str, Any] | None:
    """Invoke ``manage-config coverage resolve`` (D3) and return the parsed TOON.

    ``coverage resolve`` reads the project-global ``marshal.json`` coverage
    config and is NOT plan-scoped — its argparse subparser declares only
    ``--role`` / ``--phase`` / ``--default`` (no ``--audit-plan-id``), so the
    command is built with ``--phase`` alone, mirroring ``effort resolve-target``.
    Passing an undeclared ``--audit-plan-id`` would make argparse exit 2 and the
    subprocess return non-zero, silently collapsing every declared cell to the
    baseline reserve.

    Returns ``None`` when the executor is unreachable, the call errors, or the
    output is unparseable — callers map ``None`` to the baseline reserve. This
    degrade-to-baseline contract is intentional and covered by
    ``test_coverage_budget.py`` (unreachable / error / inherit all assert
    baseline). The legitimately-unreachable paths (no executor, not a file,
    subprocess launch failure) degrade silently; the *unexpected* internal
    failures (the executor ran but returned non-zero, or emitted unparseable
    output) emit a ``stderr`` warning before degrading, so a genuine bug does
    not vanish without a trace while still preserving the baseline fallback.
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        return None
    if not executor.is_file():
        return None
    cmd = [
        'python3',
        str(executor),
        'plan-marshall:manage-config:manage-config',
        'coverage',
        'resolve',
        '--phase',
        f'phase-{phase}',
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path(executor).resolve().parent.parent),
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        print(
            f'coverage_budget: coverage resolve exited {result.returncode} '
            f'(phase={phase!r}); degrading to baseline reserve. stderr: '
            f'{result.stderr.strip()}',
            file=sys.stderr,
        )
        return None
    try:
        parsed = parse_toon(result.stdout)
    except Exception as exc:
        print(
            f'coverage_budget: could not parse coverage resolve output '
            f'(phase={phase!r}): {exc}; degrading to baseline reserve.',
            file=sys.stderr,
        )
        return None
    return parsed if isinstance(parsed, dict) else None


def resolve_and_reserve(plan_id: str, phase: str) -> int:
    """Resolve the declared cell for ``phase`` via D3 and return its reserve.

    Calls ``manage-config coverage resolve --phase phase-{phase}`` and applies
    :func:`reserve_for_cell` to the resolved cell. An unconfigured cell (executor
    unreachable, resolve error, or either field resolving to ``inherit``) maps to
    :data:`_BASELINE_RESERVE` — plans that do not declare a coverage cell observe
    the same conservative reserve the phase-5-execute loop used before D6.

    Args:
        plan_id: Plan identifier. Part of the public phase-4-plan Step 8c
            contract (``resolve_and_reserve(plan_id, phase=...)``); retained so
            callers stay stable. ``coverage resolve`` reads the project-global
            ``marshal.json`` config and is NOT plan-scoped, so the id is not
            forwarded to the subprocess (mirrors ``effort resolve-target``).
        phase: Phase key (e.g. ``5-execute``) — the resolver looks up
            ``plan.phase-{phase}.coverage``.

    Returns:
        The per-task token-budget reserve in tokens.
    """
    del plan_id  # project-global resolve; id kept only for the public contract
    parsed = _run_coverage_resolve(phase)
    if parsed is None or parsed.get('status') != 'success':
        return _BASELINE_RESERVE
    thoroughness = parsed.get('thoroughness')
    scope = parsed.get('scope')
    if not isinstance(thoroughness, str) or not isinstance(scope, str):
        return _BASELINE_RESERVE
    return reserve_for_cell(scope, thoroughness)


# --- import-time monotonicity self-check ---------------------------------


def _assert_monotonic() -> None:
    """Verify the matrix is monotonic on both axes (fail fast at import time)."""
    scopes = ['change-set', 'artifact', 'component', 'module', 'overall']
    thoroughnesses = ['T1', 'T2', 'T3', 'T4', 'T5']

    # Monotonic along scope (fixed thoroughness).
    for t in thoroughnesses:
        prev = -1
        for s in scopes:
            value = reserve_for_cell(s, t)
            if value < prev:
                raise ValueError(
                    f'reserve matrix not monotonic on scope at thoroughness={t!r}: '
                    f'scope={s!r} reserve={value} < previous {prev}'
                )
            prev = value

    # Monotonic along thoroughness (fixed scope).
    for s in scopes:
        prev = -1
        for t in thoroughnesses:
            value = reserve_for_cell(s, t)
            if value < prev:
                raise ValueError(
                    f'reserve matrix not monotonic on thoroughness at scope={s!r}: '
                    f'thoroughness={t!r} reserve={value} < previous {prev}'
                )
            prev = value


_assert_monotonic()
