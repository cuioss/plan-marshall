#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2


# --- _apply_lane_resolution --------------------------------------------------
#
# ``dropped`` is a list of ``{step, reason}`` records, not bare ids: each drop
# names the element's effective tier and the posture cutoff that removed it, so
# the drop is diagnosable per step rather than reported as one aggregate line
# naming the whole list at once. ``_dropped_steps`` extracts the id set so the
# membership assertions below read the same as before.


def _dropped_steps(dropped: list[dict[str, str]]) -> set[str]:
    """Return the id set from a ``{step, reason}`` subtraction-record list."""
    return {record['step'] for record in dropped}
