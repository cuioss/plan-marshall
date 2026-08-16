#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The one home for the compose subtraction-record decision-log line shape.

``manage-execution-manifest`` writes a ``[STATUS]`` decision-log line for every
candidate a gate removes, and the retrospective's routing-decisions aspect reads
those lines back to establish WHY a step left ``phase_6.steps``. Before this
module the two sides each carried their own copy of the shape — the writer as an
f-string, the reader as a hand-written regex — and the copies drifted: the writer
moved to one line per dropped step with the posture in a trailing parenthetical,
while the reader kept matching the retired aggregate form with the posture in the
middle. The reader's pattern could then never match, so every posture-cutoff drop
fell through to the predicate-re-evaluation branch and was reported as a
mis-prune. Both sides now derive from the segments below, so the shape cannot
drift again without breaking both at once.

The canonical rendering is documented at ``standards/decision-rules.md``; that
document and this module state the same shape, and this module is what both the
writer and the reader execute.
"""

from __future__ import annotations

import re

#: The caller prefix every compose decision-log line carries.
COMPOSE_CALLER = '(plan-marshall:manage-execution-manifest:compose)'

#: The literal segments of the subtraction-record line. Named separately so the
#: formatter and the parser below are built from the SAME tokens rather than from
#: two independently-maintained spellings of them.
_STATUS_TAG = '[STATUS]'
_DASH = '—'
_DROP_VERB = 'dropped'


def format_dropped_record(gate_name: str, step: str, reason: str, target: str = '') -> str:
    """Render the subtraction-record line for one removed candidate.

    Args:
        gate_name: The gate the drop is attributed to (e.g. ``lane_resolution``).
        step: The removed step reference, verbatim as the candidate list held it.
        reason: The gate's own reason for this step's removal.
        target: An optional suffix naming the list the step left, and any
            gate-scoped qualifier — e.g.
            ``' from phase_6.steps (execution_profile=minimal)'``. Empty when the
            gate spans more than one list and no single name applies.

    Returns:
        The full decision-log message, caller prefix included.
    """
    return f'{COMPOSE_CALLER} {_STATUS_TAG} {gate_name} {_DASH} {_DROP_VERB} {step}{target}: {reason}'


def dropped_record_pattern() -> re.Pattern[str]:
    """Return the gate-agnostic parser for :func:`format_dropped_record` lines.

    Captures ``gate`` (the attributing gate) and ``steps`` (the removed step
    reference). Deliberately gate-AGNOSTIC: every gate that reports a subtraction
    through this shape is recognised, including gates added after this pattern was
    written. A per-gate enumeration is what previously left ``decision_matrix``
    unrecognised while three hand-listed gates were matched, so the reader's
    coverage is now a property of the shape rather than of a list somebody has to
    remember to extend.

    ``step`` never contains whitespace (it is a step reference such as
    ``default:finalize-step-simplify``), so ``\\S+`` bounds it; the optional
    ``from …`` / parenthetical-qualifier segments are what ``target`` renders, and
    the reason follows the colon.
    """
    return re.compile(
        re.escape(f'{_STATUS_TAG} ')
        + r'(?P<gate>\S+)\s+'
        + re.escape(f'{_DASH} {_DROP_VERB} ')
        + r'(?P<steps>\S+)'
        + r'(?:\s+from\s+\S+)?'
        + r'(?:\s+\([^)]*\))?'
        + r':\s'
    )
