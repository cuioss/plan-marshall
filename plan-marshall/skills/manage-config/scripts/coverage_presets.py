# SPDX-License-Identifier: FSL-1.1-ALv2
"""Static coverage expander for the ``manage-config coverage expand`` verb.

Defines :class:`CoveragePresets` — a constant-class that transcribes the
expansion table authored in
``persona-plan-marshall-agent/standards/coverage-gathering-contract.md``
§ "The Expansion Table". The contract standard is authoritative for the
*operational instruction text*; this module is authoritative for *emitting*
it. A lock-step test
(``test/plan-marshall/manage-config/test_coverage_presets.py``) asserts the
two stay identical.

Modeled structurally on ``plan-marshall/scripts/effort_presets.py``: a
constant-class with static tables, ``expand`` / ``describe`` / ``all_cells``
classmethods that return deep copies, and an import-time self-check that
rejects any incoherent table cell.

Unlike ``effort_presets.py`` — which deliberately re-declares
``ALLOWED_LEVELS`` to stay import-free of the ``manage-config`` skill scripts
— this module lives *inside* ``manage-config/scripts/`` alongside the
resolver, so it imports the existing ladder constants and the coupling
validator directly from ``_cmd_coverage`` rather than re-declaring them.

The expansion is the COMPOSITION of two per-rung instructions:

- the **scope rung → breadth instruction** (which items to cover), and
- the **thoroughness rung → depth instruction** (how deeply to cover them,
  which relations to trace).

``inherit`` on either dial collapses the whole cell to the
behavior-preserving instruction ("behave exactly as today — no breadth or
depth change"). An incoherent cell (``thoroughness >= T4 AND scope <
component``) is rejected at expansion time via the shared
:func:`_validate_coupling`, so it never appears as a valid expansion.
"""

from __future__ import annotations

from _cmd_coverage import (
    ALLOWED_SCOPE,
    ALLOWED_THOROUGHNESS,
    _validate_coupling,
    _validate_scope,
    _validate_thoroughness,
)

# The behavior-preserving instruction returned for any cell where either dial
# is ``inherit``. Mirrors the ``inherit / inherit`` row of the contract's
# expansion table.
_BEHAVIOR_PRESERVING = (
    'Behave exactly as the component does today — no breadth change, no '
    'depth change.'
)


class CoveragePresets:
    """Static expander for coverage ``(thoroughness, scope)`` cells.

    Transcribes the expansion table from
    ``persona-plan-marshall-agent/standards/coverage-gathering-contract.md``.
    The two per-rung tables (:data:`_SCOPE_BREADTH` and
    :data:`_THOROUGHNESS_DEPTH`) are composed by :meth:`expand` into the
    operational instruction block for a requested cell.

    The classmethods (:meth:`expand`, :meth:`describe`, :meth:`all_cells`)
    are the only sanctioned access path. They return fresh values so callers
    cannot mutate the class-level constants.
    """

    # ---- per-rung instruction tables ------------------------------------

    # Scope rung -> breadth instruction (which items to cover). Keyed by the
    # concrete scope rungs from ALLOWED_SCOPE (excluding 'inherit', which
    # collapses to the behavior-preserving instruction).
    _SCOPE_BREADTH: dict[str, str] = {
        'change-set': (
            'Cover only the items the current change touches — the narrowest '
            'radius. Untouched siblings are out of scope.'
        ),
        'artifact': (
            'Cover the single file/document/class the change lives in, in '
            'full, including its untouched in-file content.'
        ),
        'component': (
            'Cover the cohesive unit (skill, package, feature) the artifact '
            'belongs to, including its untouched siblings.'
        ),
        'module': (
            'Cover the build/deploy unit (bundle) the component belongs to.'
        ),
        'overall': (
            'Cover the entire codebase / full corpus — the widest radius.'
        ),
    }

    # Thoroughness rung -> depth instruction (how deeply to cover, which
    # relations to trace). Keyed by the concrete thoroughness rungs from
    # ALLOWED_THOROUGHNESS (excluding 'inherit').
    _THOROUGHNESS_DEPTH: dict[str, str] = {
        'T1': (
            'Sampled: run tools across all in-scope items, read a '
            'representative subset in full, assume the remainder. No relation '
            'tracing. One lens.'
        ),
        'T2': (
            'Full-read: read every in-scope item in full, in isolation. No '
            'cross-item relation tracing. One lens.'
        ),
        'T3': (
            'Full-read + local relations: T2 plus trace each item\'s '
            'immediate neighborhood one hop out — direct callers, tests, '
            'direct cross-references.'
        ),
        'T4': (
            'Full-read + global relations: T2 plus build and consult a '
            'scope-wide relation model (call graph, cross-reference graph, '
            'duplicate-contract detection) before acting. Requires scope >= '
            'component.'
        ),
        'T5': (
            'Exhaustive / adversarial: T4 plus an independent completeness '
            'pass — a what-did-I-miss critic, a loop-until-dry sweep that '
            'repeats until no further gap surfaces, and a declared-vs-achieved '
            'reconciliation.'
        ),
    }

    # ---- public API ------------------------------------------------------

    @classmethod
    def expand(cls, thoroughness: str, scope: str) -> str:
        """Return the operational instruction block for ``(thoroughness, scope)``.

        Composition rule: the instruction is the scope rung's breadth
        instruction followed by the thoroughness rung's depth instruction.
        Whenever either dial is ``inherit`` the whole cell collapses to the
        behavior-preserving instruction.

        Args:
            thoroughness: A member of ``ALLOWED_THOROUGHNESS``.
            scope: A member of ``ALLOWED_SCOPE``.

        Returns:
            The composed instruction block (a plain string).

        Raises:
            ValueError: When either dial is outside its allowed enum, or when
                the pair violates the coupling constraint
                (``thoroughness >= T4 AND scope < component``).
        """
        ok, err = _validate_thoroughness(thoroughness, 'coverage expand --thoroughness')
        if not ok:
            raise ValueError(err or f"invalid thoroughness '{thoroughness}'")
        ok, err = _validate_scope(scope, 'coverage expand --scope')
        if not ok:
            raise ValueError(err or f"invalid scope '{scope}'")
        ok, err = _validate_coupling(thoroughness, scope)
        if not ok:
            raise ValueError(err or 'coverage coupling violation')

        if thoroughness == 'inherit' or scope == 'inherit':
            return _BEHAVIOR_PRESERVING

        breadth = cls._SCOPE_BREADTH[scope]
        depth = cls._THOROUGHNESS_DEPTH[thoroughness]
        return f'Breadth ({scope}): {breadth} Depth ({thoroughness}): {depth}'

    @classmethod
    def describe(cls, thoroughness: str, scope: str) -> str:
        """Return a one-line human summary of the ``(thoroughness, scope)`` cell.

        Accepts the same input and raises the same errors as :meth:`expand`.
        """
        ok, err = _validate_thoroughness(thoroughness, 'coverage expand --thoroughness')
        if not ok:
            raise ValueError(err or f"invalid thoroughness '{thoroughness}'")
        ok, err = _validate_scope(scope, 'coverage expand --scope')
        if not ok:
            raise ValueError(err or f"invalid scope '{scope}'")
        ok, err = _validate_coupling(thoroughness, scope)
        if not ok:
            raise ValueError(err or 'coverage coupling violation')

        if thoroughness == 'inherit' or scope == 'inherit':
            return 'inherit/inherit — behavior-preserving (behave exactly as today)'
        return f'{thoroughness} over {scope}'

    @classmethod
    def all_cells(cls) -> list[tuple[str, str]]:
        """Return every coherent ``(thoroughness, scope)`` cell in the table.

        Excludes ``inherit`` on either axis (the behavior-preserving collapse)
        and excludes cells the coupling constraint rejects. Used by the
        lock-step test to enumerate the table.
        """
        cells: list[tuple[str, str]] = []
        for thoroughness in cls._THOROUGHNESS_DEPTH:
            for scope in cls._SCOPE_BREADTH:
                ok, _ = _validate_coupling(thoroughness, scope)
                if ok:
                    cells.append((thoroughness, scope))
        return cells


# --- import-time self-check ----------------------------------------------


def _validate_table() -> None:
    """Validate the per-rung tables against the ladder enums at import time.

    Checks (raises :class:`ValueError` on the first failure):

    1. Every ``_SCOPE_BREADTH`` key is a concrete (non-``inherit``) member of
       ``ALLOWED_SCOPE``, and every concrete scope rung is present.
    2. Every ``_THOROUGHNESS_DEPTH`` key is a concrete (non-``inherit``)
       member of ``ALLOWED_THOROUGHNESS``, and every concrete thoroughness
       rung is present.
    3. Every composed concrete cell that the coupling validator accepts can be
       expanded without raising (no incoherent cell slips into the table).

    Run once at module load so a missing rung or a typo fails fast rather than
    surfacing only when a specific cell is requested at runtime.
    """
    concrete_scope = tuple(s for s in ALLOWED_SCOPE if s != 'inherit')
    concrete_thoroughness = tuple(t for t in ALLOWED_THOROUGHNESS if t != 'inherit')

    scope_keys = set(CoveragePresets._SCOPE_BREADTH)
    if scope_keys != set(concrete_scope):
        raise ValueError(
            f'_SCOPE_BREADTH keys {sorted(scope_keys)} do not match the '
            f'concrete scope ladder {sorted(concrete_scope)}'
        )

    thoroughness_keys = set(CoveragePresets._THOROUGHNESS_DEPTH)
    if thoroughness_keys != set(concrete_thoroughness):
        raise ValueError(
            f'_THOROUGHNESS_DEPTH keys {sorted(thoroughness_keys)} do not '
            f'match the concrete thoroughness ladder {sorted(concrete_thoroughness)}'
        )

    for thoroughness, scope in CoveragePresets.all_cells():
        # Must not raise for any cell all_cells deems coherent.
        CoveragePresets.expand(thoroughness, scope)


_validate_table()
