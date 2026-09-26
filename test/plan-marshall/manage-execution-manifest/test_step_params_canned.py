# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import (
    _FLOOR_LANE_STEP,
    _IMMUNE_TO_OFF_CLASSES,
    _LANE_BLOCKS,
    _OPT_OUT_LANE_STEP,
    _mem,
)


def test_the_canned_lane_blocks_agree_with_the_shipped_classification():
    """Anti-vacuity: each canned class sits on the same side of the floor as production.

    The two cases below compose against ``_LANE_BLOCKS``, not against the shipped
    frontmatter, so a reclassification in production cannot fail them — it can
    only leave them describing a step that no longer behaves that way. That is
    exactly how the previous fixture went stale: it pinned ``lessons-capture`` as
    ``core`` after ``lessons-capture`` was reclassified to ``prunable``, and the
    monkeypatched resolver kept the arm green. This guard ties the two together on the one axis
    the cases turn on, reading the shipped class rather than restating it.
    """
    for step_id, expect_immune in ((_FLOOR_LANE_STEP, True), (_OPT_OUT_LANE_STEP, False)):
        canned = _LANE_BLOCKS[step_id]
        assert (canned['class'] in _IMMUNE_TO_OFF_CLASSES) is expect_immune, (
            f'the canned block for {step_id} ({canned}) no longer matches the premise of these cases.'
        )

        shipped = _mem._resolve_element_lane(step_id)
        assert shipped, f'{step_id} resolves no shipped lane block, so it is not lane-participating at all'
        assert (shipped['class'] in _IMMUNE_TO_OFF_CLASSES) is expect_immune, (
            f'{step_id} was reclassified in production ({shipped}), so the canned block '
            f'{canned} now describes behaviour the shipped step no longer has.'
        )
