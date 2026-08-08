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


# The workflow-run ``event`` value marking a run as triggered BY the pull request
# itself. A ``push`` run on the same SHA is NOT evidence the PR was reviewed: a
# branch push fires a workflow without any pull_request event existing, which is
# exactly the state a PR opened as a draft (or against a repo whose review bots
# are not installed) sits in.
_PULL_REQUEST_EVENT = 'pull_request'


def _is_pull_request_event_run(run: Any) -> bool:
    """Shape-validated test: is ``run`` a ``pull_request``-event workflow run?

    Every field read is guarded first, because the input is a decoded API
    response rather than a value this process constructed: a non-dict element, a
    missing ``event`` key, or a non-string ``event`` all resolve ``False`` rather
    than raising. Validating per element (not per list) keeps one malformed entry
    from discarding the well-formed entries beside it.

    The run's ``conclusion`` is deliberately NOT consulted. A ``pull_request``
    run that exists and concluded ``skipped`` means the workflow WAS triggered and
    then declined to do work — the bot was asked. Only the ABSENCE of any
    ``pull_request`` run means nothing ever asked it, so folding ``skipped`` into
    the negative would collapse two states whose remedies differ.
    """
    if not isinstance(run, dict):
        return False
    event = run.get('event')
    if not isinstance(event, str):
        return False
    return event == _PULL_REQUEST_EVENT


def _has_pull_request_event_run(runs: Any) -> bool:
    """True when ANY element of ``runs`` is a ``pull_request``-event workflow run.

    The PR-wide observable behind the ``not_triggered`` participation state, and
    an EXISTENCE predicate only: it never compares a timestamp against another,
    and never asks whether a run is recent, current, or newer than a review. A
    time comparison would make the answer depend on clock skew between the
    provider and this process, and the question being asked — "was anything ever
    triggered by this pull request?" — has no time component.

    A non-list input resolves ``False``, which is the fail-closed direction for
    this predicate's consumer: reporting "no pull_request run exists" from a
    malformed response would claim the bots were never triggered on evidence that
    was never actually read. The caller is responsible for distinguishing a failed
    fetch from a genuinely empty run list — see the calling handler, which reports
    a fetch failure rather than passing an empty list in.
    """
    if not isinstance(runs, list):
        return False
    return any(_is_pull_request_event_run(run) for run in runs)


def _run_names_a_different_pr(run: Any, pr_number: Any) -> bool:
    """True ONLY when ``run`` carries a reliable association naming a different PR.

    The run list is fetched branch-scoped (``actions/runs?branch=``), but a branch
    is not a PR boundary: a branch a closed PR already used, or two open PRs sharing
    one head branch against different bases, both carry ``pull_request`` runs
    belonging to another PR that would otherwise suppress ``not_triggered`` for a PR
    that genuinely never triggered anything.

    The association signal is a run's ``pull_requests`` array — and it is
    UNRELIABLE: GitHub routinely leaves it empty for fork-originated runs and does
    not guarantee it for same-repo runs. So this predicate is deliberately
    asymmetric and can only ever EXCLUDE, never admit: an absent array, a non-list
    array, an empty array, or an array carrying no usable ``number`` all resolve
    ``False`` — the run is kept and the branch-scoped answer stands. Only a
    populated, usable array that does NOT contain the requested PR excludes the
    run.

    That asymmetry is the whole safety argument. A strict filter would flip the
    observable to ``not_triggered: true`` whenever the array happened to be empty,
    manufacturing spurious "the reviewers were never asked" verdicts that block
    merges — a false positive in the more damaging direction than the narrower
    false negative being fixed. An unreliable association signal must never by
    itself produce ``not_triggered: true``.
    """
    if not isinstance(run, dict):
        return False
    associations = run.get('pull_requests')
    if not isinstance(associations, list):
        return False
    numbers = {
        assoc.get('number')
        for assoc in associations
        if isinstance(assoc, dict) and isinstance(assoc.get('number'), int)
    }
    if not numbers:
        return False
    try:
        requested = int(pr_number)
    except (TypeError, ValueError):
        return False
    return requested not in numbers


def _pull_request_event_runs_for_pr(runs: Any, pr_number: Any) -> list:
    """The ``pull_request``-event runs on this branch that are not another PR's.

    Composes the event-existence predicate with the fail-safe PR-boundary
    exclusion above, so the observable is bounded to the REQUESTED PR rather than
    to whatever else has ever used its head branch. Same shape tolerance as
    ``_has_pull_request_event_run``: a non-list input yields the empty list, and
    the caller is responsible for reporting a failed fetch as an error rather than
    passing an unread list in.

    The deliberate exclusions are unchanged and still apply: no ``mergeable_state``
    is read, no timestamp is compared, and a ``pull_request`` run that concluded
    ``skipped`` still counts as triggered.
    """
    if not isinstance(runs, list):
        return []
    return [
        run
        for run in runs
        if _is_pull_request_event_run(run) and not _run_names_a_different_pr(run, pr_number)
    ]


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
