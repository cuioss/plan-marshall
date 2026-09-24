#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
Every success payload also carries ``firing_count`` — the record's
``firing_count`` field when present, else ``1`` for a terminal record written
before firing history existed, else ``None`` when no record matched. The
count lets a dispatcher tell a first firing's record from a re-fire's.

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
  — a truly-absent record. This is the original behavior, retained unchanged,
  except that the verdict now also carries reportable finding fields
  (``finding_type`` / ``finding_severity`` / ``finding_title`` /
  ``finding_detail``) so the dispatcher can file the absent yield to the
  Q-Gate findings store instead of merely logging an error — a missing yield
  surfaces as a finding, never as silence. The exit code stays ``0``: the
  post-dispatch guard branches on the TOON ``error`` field, not the process
  exit code.
"""

import argparse
from typing import Any

from _cmd_mark_step import VALID_OUTCOMES
from _status_core import require_status
from _step_key_canonical import canonicalize_step_key


def _terminal_outcome(entry: Any) -> str | None:
    """Return the terminal ``outcome`` of a phase-step entry, or ``None``."""
    if isinstance(entry, dict):
        candidate = entry.get('outcome')
        if isinstance(candidate, str) and candidate in VALID_OUTCOMES:
            return candidate
    return None


def _effective_firing_count(entry: Any) -> int | None:
    """Return the firing count a terminal record represents, or ``None``.

    A record carrying an integer ``firing_count`` reports it verbatim. A
    terminal record WITHOUT the field predates firing history — it is the
    first (and so far only) firing, so it counts as ``1``. A missing or
    non-terminal entry counts as nothing (``None``).
    """
    if not isinstance(entry, dict):
        return None
    if _terminal_outcome(entry) is None:
        return None
    raw = entry.get('firing_count')
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    return 1


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
    # Canonicalize the queried step via the shared resolver so a bare↔``default:``
    # variant reconciles to the same key the write side (mark-step-done) recorded
    # under — the read-side complement of the write-side canonicalization.
    step = canonicalize_step_key(args.step) if args.step else args.step
    if not phase or not step:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--phase and --step are required and must be non-empty',
        }
    min_firing_count = getattr(args, 'min_firing_count', None)
    if min_firing_count is not None and (not isinstance(min_firing_count, int) or min_firing_count < 1):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--min-firing-count must be a positive integer when supplied',
        }

    metadata: dict[str, Any] = status.get('metadata') or {}
    phase_steps: dict[str, Any] = metadata.get('phase_steps') or {}
    phase_entry: dict[str, Any] = phase_steps.get(phase) or {}

    # Prefer an exact match under the canonical key first so a fresher canonical
    # write always wins over a stale legacy (e.g. ``default:``-prefixed) entry that
    # a pre-migration run may have inserted earlier in the insertion-ordered dict.
    # Only when the exact key is absent do we fall back to the canonicalized scan,
    # which reconciles a ``default:``-prefixed stored key with a bare query (and
    # vice versa) as a canonical MATCH rather than a tolerated near-miss.
    matched_entry: Any = phase_entry.get(step)
    # SHIM(B): a pre-migration default:-prefixed phase_steps key (canonical form is the bare step key).
    # shim-owner: manage-status
    # shim-floor: the step-key canonicalization change (canonicalize_step_key) that made the bare step key canonical, superseding the default:-prefixed form
    # shim-remove-when: no status.json can still carry a default:-prefixed phase_steps key
    if matched_entry is None:
        for stored_key, stored_entry in phase_entry.items():
            if canonicalize_step_key(stored_key) == step:
                matched_entry = stored_entry
                break
    outcome = _terminal_outcome(matched_entry)
    recorded = outcome is not None
    firing_count = _effective_firing_count(matched_entry)
    # A re-fired step whose leaf returned WITHOUT marking leaves the PRIOR
    # firing's terminal record in place; a bare existence check would read
    # that stale record as proof the current firing yielded. When the caller
    # names the firing it is guarding (the pre-dispatch count + 1), a record
    # below that floor is the same absence wearing an older firing's clothes.
    stale_firing = min_firing_count is not None and (firing_count is None or firing_count < min_firing_count)

    if args.require_terminal and (not recorded or stale_firing):
        if recorded and stale_firing:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'step_record_missing',
                'phase': phase,
                'step': step,
                'recorded': False,
                'outcome': None,
                'expected_firing_count': min_firing_count,
                'observed_firing_count': firing_count,
                'finding_type': 'missing-yield',
                'finding_severity': 'error',
                'finding_title': (
                    f"Missing yield: step '{step}' in phase '{phase}' has no record "
                    f'from firing {min_firing_count} or later'
                ),
                'finding_detail': (
                    f'status.metadata.phase_steps[{phase}][{step!r}] carries '
                    f'{outcome!r} from firing {firing_count}, below the guarded '
                    f'minimum {min_firing_count} — the re-fired step returned '
                    'without recording a terminal outcome for the current firing.'
                ),
                'message': (
                    f'No terminal record from firing {min_firing_count} or later '
                    f'for step {step!r} in phase {phase!r}: the stored '
                    f'{outcome!r} belongs to firing {firing_count}.'
                ),
            }
        # Near-miss detection: scan the same phase for an orphan terminal record
        # under a *genuine* near-miss key before declaring the record truly absent.
        # Bare↔``default:`` variants already reconciled to a canonical MATCH above,
        # so this branch retains only genuine typographic edit-distance orphans.
        # Only keys that are bare/qualified variants of each other or within a
        # small edit distance of the queried step name qualify — scanning every
        # other terminal record regardless of name was overly permissive and
        # would falsely escalate in multi-step phases (e.g. 6-finalize with 13
        # steps: completing one step and querying a wholly different absent step
        # would trigger step_record_mismatched_key instead of step_record_missing).
        for other_key, other_entry in phase_entry.items():
            canonical_other = canonicalize_step_key(other_key)
            if canonical_other == step:
                continue
            if not _is_near_miss(step, canonical_other):
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
            'finding_type': 'missing-yield',
            'finding_severity': 'error',
            'finding_title': (f"Missing yield: step '{step}' in phase '{phase}' returned without a terminal record"),
            'finding_detail': (f'status.metadata.phase_steps[{phase}] has no terminal record for step {step!r}'),
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
        'recorded': recorded and not stale_firing,
        'outcome': outcome if not stale_firing else None,
        'firing_count': firing_count,
    }
