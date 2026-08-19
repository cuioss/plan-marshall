#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for deterministic task cost-sizing (_tasks_cost.py).

The pure deriver in ``_tasks_cost.py`` IMPLEMENTS the rubric defined in
``marketplace/bundles/plan-marshall/skills/phase-4-plan/standards/cost-sizing.md``.
These tests pin the four-signal weighted score, the score→size band mapping,
the size→token table, the public ``derive_cost_size`` entry point, and the
``derive-cost-size`` CLI subcommand integration via ``manage-tasks``.

Per the task contract, the canonical thresholds are NOT inline-copied as bare
magic numbers into assertions: each boundary test references the rubric weights
imported from the module under test (``W_STEP`` / ``W_PROFILE`` / ``W_SKILLS`` /
``W_TARGET_FILES`` / ``_XS_MAX`` / ``_S_MAX`` / ``_M_MAX`` / ``_L_MAX`` /
``_XL_MAX``), so the assertions track the single source of truth in
``cost-sizing.md`` rather than duplicating it. The rubric's six-size band
semantics (XS ``< 30``, S ``[30,60)``, M ``[60,150)``, L ``[150,300)``,
XL ``[300,700)``, XXL ``>= 700``) are exercised at and around each band
boundary. The four original boundaries (60/150/300) and magnitudes are unchanged;
XS and XXL widen the scale at both ends.

Tier 2 (direct import) tests for the pure functions, plus Tier 3 subprocess
tests for the ``derive-cost-size`` CLI plumbing.
"""




from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')


_cost = load_script_module('plan-marshall', 'manage-tasks', '_tasks_cost.py', '_tasks_cost_under_test')


profile_weight = _cost.profile_weight


compute_score = _cost.compute_score


score_to_size = _cost.score_to_size


resolve_size_table = _cost.resolve_size_table


derive_cost_size = _cost.derive_cost_size


W_STEP = _cost.W_STEP


W_PROFILE = _cost.W_PROFILE


W_SKILLS = _cost.W_SKILLS


W_TARGET_FILES = _cost.W_TARGET_FILES


PROFILE_WEIGHTS = _cost.PROFILE_WEIGHTS


_PROFILE_WEIGHT_DEFAULT = _cost._PROFILE_WEIGHT_DEFAULT


_XS_MAX = _cost._XS_MAX


_S_MAX = _cost._S_MAX


_M_MAX = _cost._M_MAX


_L_MAX = _cost._L_MAX


_XL_MAX = _cost._XL_MAX


COST_SIZES = _cost.COST_SIZES


DEFAULT_SIZE_TABLE = _cost.DEFAULT_SIZE_TABLE


def _score_only(step_count, profile, skills_count, target_file_count):
    """Recompute the rubric weighted-sum from the imported weights.

    Used to derive boundary signal combinations for the band tests without
    hard-coding raw score literals — the weights come from the module under
    test, which mirrors the rubric § 1 weighting table.
    """
    return (
        (W_STEP * step_count)
        + (W_PROFILE * profile_weight(profile))
        + (W_SKILLS * skills_count)
        + (W_TARGET_FILES * target_file_count)
    )
