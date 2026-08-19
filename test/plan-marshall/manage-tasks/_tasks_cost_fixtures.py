#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``tasks cost`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
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
