#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub check-row classification and link-parsing helpers.

Pure, side-effect-free helpers extracted from ``github_ops.py``: the canonical
conclusion partition tables, the ``gh pr checks`` conclusion normaliser, the
check-link segment extractors, the failing-check entry builder, the bucket
classifier, and the overall-status derivation. None of these touch the network
or any monkeypatched module global, so they are safe to live outside the entry
module and are re-exported from ``github_ops`` for callers and tests.
"""

import re
from typing import Any

# GitHub check ``conclusion`` (raw ``state`` from ``gh pr checks --json state``)
# partitioning. The raw conclusion vocabulary is upper-case
# ``SUCCESS | SKIPPED | NEUTRAL | FAILURE | TIMED_OUT | CANCELLED |
# ACTION_REQUIRED | STALE | STARTUP_FAILURE | IN_PROGRESS | QUEUED | PENDING |
# null``. The three partitions below carry the canonical conclusion → outcome
# mapping for ``cmd_ci_status``, ``cmd_ci_wait``, and
# ``_fetch_pr_overall_ci_status``.
_CONCLUSION_NON_FAILING: frozenset[str] = frozenset({'SUCCESS', 'SKIPPED', 'NEUTRAL'})
_CONCLUSION_FAILING: frozenset[str] = frozenset(
    {'FAILURE', 'TIMED_OUT', 'CANCELLED', 'ACTION_REQUIRED', 'STALE', 'STARTUP_FAILURE'}
)
_CONCLUSION_WAIT: frozenset[str] = frozenset({'IN_PROGRESS', 'QUEUED', 'PENDING', ''})

# GitHub ``bucket`` field (``gh pr checks --json bucket``) → canonical
# conclusion fallback. The ``bucket`` vocabulary is
# ``pass | fail | pending | skipping | cancel``. Only consulted when the raw
# ``state`` field is null/empty — a workflow-level check that has concluded
# (e.g. a skipped reusable workflow, or a timed-out/errored run) can arrive
# from ``gh pr checks`` carrying its outcome in ``bucket`` while ``state`` is
# null. ``pending`` maps to the empty string (genuine wait); an absent or
# unrecognised bucket also keeps the empty-string wait result.
_BUCKET_TO_CONCLUSION: dict[str, str] = {
    'pass': 'SUCCESS',
    'fail': 'FAILURE',
    'cancel': 'CANCELLED',
    'skipping': 'SKIPPED',
    'pending': '',
}


def _normalize_conclusion(check: dict) -> str:
    """Return the canonical upper-case conclusion for a check row.

    Reads the raw ``state`` field from ``gh pr checks --json state``. When
    ``state`` is null/empty, falls back to the ``bucket`` field (``gh pr
    checks --json bucket``), mapping it to a canonical conclusion via
    ``_BUCKET_TO_CONCLUSION`` (``pass`` → ``SUCCESS``, ``fail`` → ``FAILURE``,
    ``cancel`` → ``CANCELLED``, ``skipping`` → ``SKIPPED``, ``pending`` →
    ``''``). This corrects the spurious wait-state for checks whose outcome
    is carried only in ``bucket`` (a workflow-level skipped/timed-out run). An
    absent or unrecognised bucket keeps the empty string, which the partition
    table treats as a wait-state.
    """

    raw = check.get('state')
    if raw is not None and str(raw) != '':
        return str(raw).upper()
    bucket = check.get('bucket')
    if bucket is None:
        return ''
    return _BUCKET_TO_CONCLUSION.get(str(bucket).lower(), '')


def _extract_segment_from_link(link: str | None, marker: str, *, numeric_only: bool = False) -> str:
    """Extract a URL path segment that follows ``marker`` from a GitHub check link.

    GitHub check links follow the pattern
    ``https://github.com/<owner>/<repo>/actions/runs/<run_id>/job/<job_id>``.
    Returns the segment immediately after ``marker``, or an empty string when
    the marker is absent. When ``numeric_only=True``, non-numeric segments
    (e.g. a missing ``job_id``) return an empty string instead.
    """

    if not link:
        return ''
    idx = link.find(marker)
    if idx == -1:
        return ''
    tail = link[idx + len(marker):]
    segment = tail.split('/', 1)[0]
    if numeric_only and not re.match(r'^\d+$', segment):
        return ''
    return segment


def _extract_run_id_from_link(link: str | None) -> str:
    return _extract_segment_from_link(link, '/actions/runs/')


def _extract_job_id_from_link(link: str | None) -> str:
    return _extract_segment_from_link(link, '/job/', numeric_only=True)


def _build_failing_check_entry(check: dict) -> dict:
    """Build the transport-rich ``failing_checks[]`` entry for a single check.

    Includes the per-check fields downstream consumers (deliverables 6 and 7)
    need to classify failure modes and persist artifacts.
    """

    link = check.get('link') or ''
    entry: dict[str, Any] = {
        'name': check.get('name', 'unknown'),
        'conclusion': _normalize_conclusion(check) or 'PENDING',
        'workflow_name': check.get('workflow') or '',
        'job_name': check.get('name', '') or '',
        'started_at': check.get('startedAt') or '',
        'completed_at': check.get('completedAt') or '',
        'run_id': _extract_run_id_from_link(link),
        'job_id': _extract_job_id_from_link(link),
        'run_url': link,
    }
    return entry


def _classify_check_buckets(
    checks: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition GitHub check rows into ``(failing, wait, non_failing)``.

    The partition uses the raw ``state`` (conclusion) field per the canonical
    conclusion → outcome table. Conclusions not present in any partition table
    are treated as failing (defense in
    depth — an unknown conclusion is never silently accepted as success).
    """

    failing: list[dict] = []
    wait: list[dict] = []
    non_failing: list[dict] = []
    for check in checks:
        conclusion = _normalize_conclusion(check)
        if conclusion in _CONCLUSION_NON_FAILING:
            non_failing.append(check)
        elif conclusion in _CONCLUSION_WAIT:
            wait.append(check)
        else:
            # Includes _CONCLUSION_FAILING and any unknown future conclusion.
            failing.append(check)
    return failing, wait, non_failing


def _derive_overall_status(checks: list[dict]) -> tuple[str, list[dict], list[dict]]:
    """Derive ``overall | final_status`` plus failing-checks transport.

    Returns ``(status, failing_check_rows, wait_check_rows)`` where ``status``
    is one of ``pending | success | failure | none``. The ``mixed`` outcome
    is intentionally absent — every input resolves to one of the four
    canonical states.
    """

    if not checks:
        return 'none', [], []
    failing, wait, _non_failing = _classify_check_buckets(checks)
    if wait:
        return 'pending', [], wait
    if failing:
        return 'failure', failing, []
    return 'success', [], []
