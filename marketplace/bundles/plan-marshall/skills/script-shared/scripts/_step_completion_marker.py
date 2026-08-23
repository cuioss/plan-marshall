#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ONE shape of the per-step completion marker, shared by producer and consumers.

``manage-status mark-step-done`` emits a ``[STEP] … Completed step: …`` work-log
line as a fused side effect of every finalize terminal write, and several
components downstream read or describe that line:

* ``manage-status/scripts/_cmd_mark_step.py`` — the PRODUCER, which formats it.
* ``manage-status/scripts/manage-status.py`` — the ``--no-completion-log`` help
  string, which describes the line the flag suppresses.
* ``plan-retrospective/scripts/check-dispatch-audit.py`` — the CONSUMER, whose
  D3 ``completion_count`` is the number of these lines in the work log.

Each of those used to carry its own copy of the marker's wording, so widening
the line meant editing a literal in three places and hoping none was missed — a
producer-without-consumer shape where nothing fails when the copies disagree.
This module is the single source those three bind to, following the same
cross-skill sharing pattern as ``_step_key_canonical``.

**The consumer pattern deliberately treats ``(outcome=…)`` as OPTIONAL.** A
retrospective reads work logs written by earlier runs, and every line recorded
before the outcome was carried has no such suffix. A pattern that required it
would silently stop counting historical completions — reporting a
``completion_count`` of zero for an entire past corpus and grading D3's
dispatch/completion ratio against it — which is precisely the class of silent
under-count this marker's own audit exists to detect.
"""

from __future__ import annotations

import re

#: The literal that identifies a completion line, independent of what follows the
#: step name. Kept separate so a doc or help string can quote the stable part
#: without embedding the whole template.
COMPLETION_MARKER_PHRASE = 'Completed step:'

#: The emitted shape. ``phase`` is the phase key (``6-finalize``), ``step`` the
#: canonical step key, ``outcome`` the terminal outcome already validated by the
#: producer against ``VALID_OUTCOMES``.
COMPLETION_MARKER_TEMPLATE = (
    '[STEP] (plan-marshall:phase-{phase}) Completed step: {step} (outcome={outcome})'
)

#: The read pattern. Prefix-anchored and NOT anchored on the line end: ``\S+``
#: stops at the space before the ``(outcome=…)`` suffix, so this matches a
#: pre-widening line and a widened one alike, capturing the same ``step`` from
#: both. ``outcome`` is ``None`` on a historical line that carried none.
COMPLETION_MARKER_RE = re.compile(
    r'\[STEP\].*?Completed step:\s*(?P<step>\S+)'
    r'(?:\s*\(outcome=(?P<outcome>[A-Za-z_]+)\))?'
)


def format_completion_marker(phase: str, step: str, outcome: str) -> str:
    """Render the completion marker for one terminal step recording."""
    return COMPLETION_MARKER_TEMPLATE.format(phase=phase, step=step, outcome=outcome)
