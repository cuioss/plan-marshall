#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic task cost-sizing for manage-tasks.

This module IMPLEMENTS the cost-sizing rubric defined in
``marketplace/bundles/plan-marshall/skills/phase-4-plan/standards/cost-sizing.md``.
It is a pure, deterministic, total function over signals already present on a
planned task record — it derives a T-shirt cost size
(``XS``/``S``/``M``/``L``/``XL``/``XXL``) and a ``predicted_cost_tokens``
magnitude. No LLM judgement, no I/O, no globals. ``XS`` and ``XXL`` widen the
original ``S``/``M``/``L``/``XL`` scale at both ends; the four original score
bands and magnitudes are unchanged (every canonical worked example in the rubric
still derives the same size), so ``XS`` only fires for trivial tasks below the
old ``S`` floor and ``XXL`` only for tasks above the old ``XL`` ceiling.

The four input signals and their weights (see the rubric § "Signals and
weights"):

* ``step_count``        — DOMINANT. Each step drives a distinct generation pass.
* ``profile``           — code profiles (implementation/module_testing) are
                          heavier than ``verification`` (commands + parsing).
* ``skills_count``      — each declared skill is an in-context skill load.
* ``target_file_count`` — distinct target files read/written.

Build count is DELIBERATELY EXCLUDED. A build is token-cheap (~100 tokens to run
and read its summary, regardless of wall-clock duration). This rubric predicts
TOKEN consumption — the model's generation + reasoning + in-context skill loads —
not wall-clock time, so build count is not a signal and the deriver takes no
build-count input.

The size→token table is passed in (sourced from config
``plan.phase-5-execute.cost_size_token_table``) so this module stays a pure
function; the canonical default table mirrors the rubric § "Size → token table".
"""

from __future__ import annotations

from sensible_number import parse_sensible_int

# --- Weights (rubric § 1) ------------------------------------------------

#: Step-count weight. Dominant term — one extra step outweighs one extra skill
#: or one extra target file.
W_STEP = 10
#: Profile-term weight (multiplies the profile_weight map below).
W_PROFILE = 1
#: Skills-count weight.
W_SKILLS = 3
#: Distinct-target-file-count weight.
W_TARGET_FILES = 4

#: Per-profile additive weight. Code-bearing profiles lift the score above pure
#: verification. Unknown profiles take the middle ``_PROFILE_WEIGHT_DEFAULT``.
PROFILE_WEIGHTS: dict[str, int] = {
    'implementation': 12,
    'module_testing': 12,
    'verification': 4,
}
_PROFILE_WEIGHT_DEFAULT = 8

# --- Thresholds (rubric § 2) ---------------------------------------------

#: Size boundaries, evaluated low→high. A score below the first boundary is XS;
#: at or above the last boundary is XXL. The bands are monotone, so increasing
#: any signal can only raise (never lower) the size. The four original
#: boundaries (``_S_MAX`` / ``_M_MAX`` / ``_L_MAX``) are unchanged; ``_XS_MAX``
#: carves a trivial-task band below the old ``S`` floor and ``_XL_MAX`` carves an
#: ``XXL`` band above the old ``XL`` ceiling — both positioned so every canonical
#: worked example in the rubric still derives the same size.
_XS_MAX = 30
_S_MAX = 60
_M_MAX = 150
_L_MAX = 300
_XL_MAX = 700

#: Ordered size labels, smallest first.
COST_SIZES: tuple[str, ...] = ('XS', 'S', 'M', 'L', 'XL', 'XXL')

# --- Size → token table (rubric § 3) -------------------------------------

#: Canonical default size→token table, mirroring the rubric. Values are the
#: human-friendly magnitude strings (parsed via ``parse_sensible_int``). This
#: default is used when the caller passes no ``size_table``; the operator-tunable
#: surface is the config key ``plan.phase-5-execute.cost_size_token_table``.
DEFAULT_SIZE_TABLE: dict[str, str] = {
    'XS': '5K',
    'S': '25K',
    'M': '60K',
    'L': '130K',
    'XL': '260K',
    'XXL': '520K',
}


def profile_weight(profile: str | None) -> int:
    """Return the additive profile weight for *profile*.

    Args:
        profile: The task profile (``implementation`` / ``module_testing`` /
            ``verification``), or ``None`` / an unknown value.

    Returns:
        The profile's weight; unknown / ``None`` profiles take the default.
    """
    if profile is None:
        return _PROFILE_WEIGHT_DEFAULT
    return PROFILE_WEIGHTS.get(profile, _PROFILE_WEIGHT_DEFAULT)


def compute_score(step_count: int, profile: str | None, skills_count: int, target_file_count: int) -> int:
    """Compute the deterministic weighted cost score (rubric § 1).

    Args:
        step_count: ``len(task.steps)`` — the dominant signal.
        profile: ``task.profile``.
        skills_count: ``len(task.skills)``.
        target_file_count: count of distinct ``steps[].target`` values.

    Returns:
        The weighted-sum score as a non-negative integer.

    Raises:
        ValueError: when any count is negative.
    """
    for name, value in (
        ('step_count', step_count),
        ('skills_count', skills_count),
        ('target_file_count', target_file_count),
    ):
        if value < 0:
            raise ValueError(f'{name} must be non-negative, got {value!r}')

    return (
        (W_STEP * step_count)
        + (W_PROFILE * profile_weight(profile))
        + (W_SKILLS * skills_count)
        + (W_TARGET_FILES * target_file_count)
    )


def score_to_size(score: int) -> str:
    """Map a weighted score to a T-shirt size via the rubric § 2 bands.

    Args:
        score: The weighted score from :func:`compute_score`.

    Returns:
        One of ``XS`` / ``S`` / ``M`` / ``L`` / ``XL`` / ``XXL``.
    """
    if score < _XS_MAX:
        return 'XS'
    if score < _S_MAX:
        return 'S'
    if score < _M_MAX:
        return 'M'
    if score < _L_MAX:
        return 'L'
    if score < _XL_MAX:
        return 'XL'
    return 'XXL'


def resolve_size_table(size_table: dict[str, object] | None) -> dict[str, int]:
    """Parse a size→token table into ``{size: int_tokens}``.

    Args:
        size_table: A mapping of size label → magnitude (``str`` like ``"60K"``
            or ``int``). ``None`` selects :data:`DEFAULT_SIZE_TABLE`.

    Returns:
        The table with every value parsed to a plain ``int`` via
        ``parse_sensible_int``.

    Raises:
        ValueError: when the table is missing a required size key or carries a
            value that does not parse as a sensible int.
    """
    raw = DEFAULT_SIZE_TABLE if size_table is None else size_table
    resolved: dict[str, int] = {}
    for size in COST_SIZES:
        if size not in raw:
            raise ValueError(f'size_table missing required key: {size!r}')
        resolved[size] = parse_sensible_int(raw[size])
    return resolved


def derive_cost_size(
    step_count: int,
    profile: str | None,
    skills_count: int,
    target_file_count: int,
    size_table: dict[str, object] | None = None,
) -> tuple[str, int]:
    """Derive ``(cost_size, predicted_cost_tokens)`` for a task.

    Deterministic and total: every valid (non-negative) signal combination
    yields exactly one ``(size, predicted_cost_tokens)`` pair. Implements the
    rubric in ``phase-4-plan/standards/cost-sizing.md``.

    Args:
        step_count: ``len(task.steps)`` — the dominant signal.
        profile: ``task.profile`` (``implementation`` / ``module_testing`` /
            ``verification`` / unknown).
        skills_count: ``len(task.skills)``.
        target_file_count: count of distinct ``steps[].target`` values.
        size_table: optional size→token map (config-sourced); ``None`` uses the
            canonical :data:`DEFAULT_SIZE_TABLE`.

    Returns:
        A ``(cost_size, predicted_cost_tokens)`` tuple — ``cost_size`` is one of
        ``XS`` / ``S`` / ``M`` / ``L`` / ``XL`` / ``XXL``;
        ``predicted_cost_tokens`` is the integer token magnitude for that size.

    Raises:
        ValueError: when a count is negative or the size table is malformed.
    """
    table = resolve_size_table(size_table)
    score = compute_score(step_count, profile, skills_count, target_file_count)
    size = score_to_size(score)
    return size, table[size]
