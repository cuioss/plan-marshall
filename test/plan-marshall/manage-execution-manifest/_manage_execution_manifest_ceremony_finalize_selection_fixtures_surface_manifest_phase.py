#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2


def _lane_dropped_reasons(result: dict) -> dict[str, str]:
    """Index the ``lane_dropped`` subtraction records by step id.

    ``lane_dropped`` carries ``{step, reason}`` records rather than bare ids, so
    each drop names WHY it happened — an explicit ``off`` opt-out versus an
    effective tier above the posture cutoff. Indexing by step keeps the
    membership assertions readable while making the reason available to the
    tests that need to distinguish the two.
    """
    return {record['step']: record['reason'] for record in result['lane_dropped']}
