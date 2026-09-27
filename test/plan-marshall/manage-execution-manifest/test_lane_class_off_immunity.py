# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_lane_class_off_immunity.py: fixture."""

from _manage_execution_manifest_lane_class_off_immunity_fixtures import (
    _FLOOR_STEPS,
    _IMMUNE_TO_OFF_CLASSES,
    _OPT_OUT_STEP,
    _RECLASSIFIED_STEP,
    _mem,
    _restore_footprint_resolvers,
)

# --- anti-vacuity: every fixture's class comes from the live resolver ---------


def test_every_fixture_class_is_derived():
    """Each fixture step's ``lane.class`` is READ, not assumed.

    Reading these from memory would let every arm below pass for a reason
    unrelated to the immunity rule — a floor arm satisfied by a step that is no
    longer floor-classed, or a matched negative satisfied by one that never was.
    The floor membership itself is derived too: the arms assert against
    ``_IMMUNE_TO_OFF_CLASSES``, not against the literal ``'core'``.
    """
    for step in [*_FLOOR_STEPS, 'archive-plan']:
        lane = _mem._resolve_element_lane(step)
        assert lane, f'{step} resolves no lane block, so it is not lane-participating at all'
        assert lane.get('class') in _IMMUNE_TO_OFF_CLASSES, (
            f'{step} no longer resolves to a floor class ({lane}) — the floor arms below are void.'
        )

    for step in (_OPT_OUT_STEP, _RECLASSIFIED_STEP):
        lane = _mem._resolve_element_lane(step)
        assert lane, f'{step} resolves no lane block'
        assert lane.get('class') not in _IMMUNE_TO_OFF_CLASSES, (
            f'{step} resolves to a FLOOR class ({lane}) — its off would be neutralized, '
            f'so it cannot serve as the matched negative.'
        )
