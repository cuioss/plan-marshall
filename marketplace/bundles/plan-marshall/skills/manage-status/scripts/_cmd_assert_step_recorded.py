#!/usr/bin/env python3
"""
assert-step-recorded command handler for manage-status.

Read-only verdict over ``status.metadata.phase_steps[phase][step]``: does a
terminal step record exist for the named phase step? A record counts as
*recorded* iff a dict entry with a terminal ``outcome`` in
``{done, skipped, loop_back, failed}`` is present. The verb performs zero
writes to ``status.json`` — it is the deterministic post-dispatch guard the
phase-6-finalize dispatcher calls after every dispatched-step return to detect
the silent "agent returned ``status: success`` but skipped its mandated
``mark-step-done`` side-effect" gap.

Without ``--require-terminal`` the verb always returns ``status: success`` and
reports the boolean ``recorded`` (plus the matched ``outcome`` or ``null``).

With ``--require-terminal`` a missing terminal record is escalated to an error
verdict the dispatcher can branch on directly. Two error branches are
distinguished by whether a *near-miss* orphan record exists in the same phase:

- ``step_record_mismatched_key``: the queried ``step`` key has no terminal
  record, BUT a *genuine near-miss* key in the same ``phase_entry`` carries a
  terminal ``outcome`` (a bare/mis-keyed orphan — e.g. a dispatched skill that
  recorded under its bare name instead of its fully-qualified manifest
  ``step_id``). Near-miss matching is restricted to bare/qualified name
  variants and close typographic errors (Levenshtein distance ≤2 for
  sufficiently long strings) — unrelated keys in the same phase do NOT trigger
  this branch. The verdict carries the ``orphan_key`` and its ``outcome`` so
  the dispatcher can report the mis-keying instead of an infinite "record under
  the wrong key, re-enter, record under the wrong key again" recovery loop.
- ``step_record_missing``: no terminal record exists under any key in the phase
  — a truly-absent record. This is the original behavior, retained unchanged.
"""

import argparse
from typing import Any

from _cmd_mark_step import VALID_OUTCOMES
from _status_core import require_status


def _terminal_outcome(entry: Any) -> str | None:
    """Return the terminal ``outcome`` of a phase-step entry, or ``None``."""
    if isinstance(entry, dict):
        candidate = entry.get('outcome')
        if isinstance(candidate, str) and candidate in VALID_OUTCOMES:
            return candidate
    return None


def _is_near_miss(s1: str, s2: str) -> bool:
    """Return True iff s1 and s2 are genuine near-misses.

    A genuine near-miss is one of:
    - Bare vs fully-qualified variant (the bare suffix of one equals the other
      or the other's bare suffix, e.g. ``plan-marshall:plan-retrospective`` vs
      ``plan-retrospective``).
    - Within Levenshtein edit distance 1 for strings ≥5 chars, or edit distance
      2 for strings ≥8 chars (close typographic errors).

    Wholly unrelated names (e.g. ``step-a`` vs ``step-missing``) do NOT
    qualify and return False.
    """
    b1 = s1.split(':')[-1]
    b2 = s2.split(':')[-1]
    # Bare/qualified match: same bare name, or one is the bare form of the other.
    if b1 == b2 or s1 == b2 or s2 == b1:
        return True
    m, n = len(s1), len(s2)
    # Reject if length difference alone rules out a meaningful edit distance.
    if abs(m - n) > 2:
        return False
    # Levenshtein distance (Wagner–Fischer DP).
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    dist = dp[m][n]
    if dist == 1:
        return m >= 5 and n >= 5
    if dist == 2:
        return m >= 8 and n >= 8
    return False


def cmd_assert_step_recorded(args: argparse.Namespace) -> dict | None:
    """Return a read-only verdict on whether a phase step has a terminal record."""
    status = require_status(args)
    if status is None:
        return None

    phase = args.phase
    step = args.step
    if not phase or not step:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--phase and --step are required and must be non-empty',
        }

    metadata: dict[str, Any] = status.get('metadata') or {}
    phase_steps: dict[str, Any] = metadata.get('phase_steps') or {}
    phase_entry: dict[str, Any] = phase_steps.get(phase) or {}

    outcome = _terminal_outcome(phase_entry.get(step))
    recorded = outcome is not None

    if args.require_terminal and not recorded:
        # Near-miss detection: scan the same phase for an orphan terminal record
        # under a *genuine* near-miss key before declaring the record truly absent.
        # Only keys that are bare/qualified variants of each other or within a
        # small edit distance of the queried step name qualify — scanning every
        # other terminal record regardless of name was overly permissive and
        # would falsely escalate in multi-step phases (e.g. 6-finalize with 13
        # steps: completing one step and querying a wholly different absent step
        # would trigger step_record_mismatched_key instead of step_record_missing).
        for other_key, other_entry in phase_entry.items():
            if other_key == step:
                continue
            if not _is_near_miss(step, other_key):
                continue
            orphan_outcome = _terminal_outcome(other_entry)
            if orphan_outcome is not None:
                return {
                    'status': 'error',
                    'plan_id': args.plan_id,
                    'error': 'step_record_mismatched_key',
                    'phase': phase,
                    'step': step,
                    'recorded': False,
                    'outcome': None,
                    'orphan_key': other_key,
                    'orphan_outcome': orphan_outcome,
                    'message': (
                        f'No terminal record for step {step!r} in phase {phase!r}, '
                        f'but a terminal record exists under the near-miss key '
                        f'{other_key!r} (outcome {orphan_outcome!r}). The dispatched '
                        'step recorded its mark-step-done outcome under the wrong '
                        f'key — expected the queried step name {step!r}.'
                    ),
                }

        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'step_record_missing',
            'phase': phase,
            'step': step,
            'recorded': False,
            'outcome': None,
            'message': (
                f'No terminal record for step {step!r} in phase {phase!r}: the '
                'dispatched step returned without recording a mark-step-done '
                f'outcome (expected one of {list(VALID_OUTCOMES)}).'
            ),
        }

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'recorded': recorded,
        'outcome': outcome,
    }
