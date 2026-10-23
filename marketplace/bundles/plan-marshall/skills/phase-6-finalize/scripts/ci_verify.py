#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic ``ci-verify`` finalize-step executor for phase-6-finalize.

This script replaces the former dispatched ``workflow/ci-verify.md``
execution-context body. The CI-check classification is a fixed taxonomy-table
lookup (see ``standards/ci-verify.md``), so the green pass-through pays no LLM
envelope and only a genuinely-red CI still routes to the LLM
``verification-feedback`` triage — extending the dispatch-granularity
"find the LLM core" model rather than contradicting it.

Responsibilities (all deterministic Python — no dispatch here):

* Read the settled CI run state. The run-level verdict (``final_status`` /
  ``wait_outcome`` / ``head_sha``) is threaded in from the dispatcher's
  ``consume-failures`` precondition envelope
  (``ci_complete_precondition resolve --mode consume-failures``); the full
  per-job ``checks[]`` array is fetched fresh via ``ci checks status`` so a
  green run still persists per-job evidence.
* Capture the full ``checks[]`` array to a ``.plan/temp/`` jobs file.
* Persist CI run artifacts via ``manage-ci-artifacts persist`` behind a
  required-field guard that verifies ALL required flags are non-empty
  (``--plan-id`` / ``--run-id`` / ``--head-sha`` / ``--pr-number`` /
  ``--provider``) AND constrains ``--wait-outcome`` to its
  ``{completed, deadline_exceeded}`` enum — never copying ``--final-status``'s
  value. This structurally eliminates the recurring
  ``manage-ci-artifacts persist`` argparse-drift class by moving the call to a
  validated Python site.
* Green (``final_status == success`` AND no failing checks) →
  ``mark-step-done --outcome done`` with ``--head-at-completion``, zero
  dispatch. The mark's own result decides what is reported: ``green`` when it
  returned success, ``green_unrecorded`` when it was refused.
* Non-green → file exactly ONE taxonomy finding per failing check (plus the
  ``ci_no_checks`` finding on ``final_status == none``) and return a
  needs-triage signal carrying the single :data:`PRODUCER` value so the
  dispatcher runs ``verification-feedback`` once (the sole LLM step, red-CI
  only). The per-row distinction rides each finding's subtype tag. The script
  does NOT mark the step done on the red path — the dispatcher marks it after
  the triage returns. Under ``wait_outcome == deadline_exceeded`` a still-running
  check is a failing check only when nothing has definitively failed: beside
  a real failure it is dropped and produces no finding.

``mark-step-done --step`` uses the bare manifest key ``ci-verify`` (NOT a
``default:``-prefixed key).

Return shape (CLI emits this as TOON; programmatic callers consume the dict
directly)::

    status: success | error
    plan_id: <echo>
    final_status: success | failure | none | timeout
    outcome: green | green_unrecorded | needs_triage
    run_id: <str>              # derived from checks[] run URLs; may be empty
    head_sha: <str>            # threaded from the precondition; may be empty
    persisted: true | false
    persist_skipped_reason: <field>   # present only when persisted == false
    findings_filed: <int>
    producers: [str, ...]      # present only when outcome == needs_triage
    step_marked_done: true | false    # true only when the mark returned success
    step_mark_error: <str>     # present only when outcome == green_unrecorded
    step_mark_message: <str>   # present only when outcome == green_unrecorded

``green_unrecorded`` is a green CI verdict whose ``mark-step-done`` write was
refused: CI passed, but the step record does not say so.

Subprocess seams (``_run_ci_checks_status``, ``_run_manage_ci_artifacts_persist``,
``_run_manage_findings_add``, ``_run_mark_step_done``, ``_run_git_rev_parse_head``)
are split out so the orchestration body is testable without a live CI provider,
a live git worktree, or live plan state.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_verify \\
      run --plan-id PLAN --pr-number N --worktree-path PATH --provider github \\
      --final-status success --wait-outcome completed --head-sha SHA

The executor injects ``PYTHONPATH`` for ``toon_parser`` and ``file_ops``, so no
in-script ``sys.path`` manipulation is required.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from file_ops import get_executor_path
from toon_parser import ToonParseError, parse_toon, serialize_toon

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Executor notations routed through the proxy.
_CI_NOTATION: str = 'plan-marshall:tools-integration-ci:ci'
_CI_ARTIFACTS_NOTATION: str = 'plan-marshall:manage-ci-artifacts:manage-ci-artifacts'
_FINDINGS_NOTATION: str = 'plan-marshall:manage-findings:manage-findings'
_STATUS_NOTATION: str = 'plan-marshall:manage-status:manage-status'

#: The bare manifest step key (NOT ``default:ci-verify``) that
#: ``mark-step-done --step`` records under.
_STEP_KEY: str = 'ci-verify'

#: The finalize phase key ``mark-step-done`` records against.
_PHASE_KEY: str = '6-finalize'

#: Finding component notation for every ci-verify finding.
_COMPONENT: str = 'plan-marshall:phase-6-finalize'

#: The single producer value the dispatcher hands to ``verification-feedback``.
#: ``verification-feedback`` accepts it in its one accept-set, and the per-row
#: distinction rides the finding's subtype tag (see :data:`_SUBTYPE_*`), never a
#: second producer string per taxonomy row.
PRODUCER: str = 'ci-verify'

#: The closed policy-workflow list. A failing check whose workflow or job name
#: matches one of these patterns is a policy failure; EVERY other failing check
#: is a build failure, so an unknown name fails toward a fix.
_POLICY_PROFILE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r'\blicen[cs]e\b',
        r'\bcla\b',
        r'\bdependency[- ]review\b',
        r'\bcodeql\b',
        r'\blabel(?:s|er)?\b',
        r'\btitles?\b',
    )
)

#: The sonar-maven-plugin marker that identifies a Sonar quality-gate failure
#: inside a Maven build job (sonar-plugin ``QUALITY GATE STATUS: FAILED``).
_SONAR_QUALITY_GATE_MARKER: str = 'QUALITY GATE STATUS: FAILED'

#: Finding subtype tags — the per-row distinction carried in the title.
_SUBTYPE_MISSING: str = 'ci_no_checks'
_SUBTYPE_BUILD: str = 'ci_build_failure'
_SUBTYPE_POLICY: str = 'ci_policy_failure'
_SUBTYPE_TIMEOUT: str = 'ci_timeout'
_SUBTYPE_CANCELLED: str = 'ci_cancelled'
_SUBTYPE_ACTION_REQUIRED: str = 'ci_action_required'
_SUBTYPE_STALE: str = 'ci_stale'
_SUBTYPE_SONAR_GATE: str = 'ci_sonar_gate'

#: The required-field set for the ``manage-ci-artifacts persist`` guard.
_REQUIRED_PERSIST_FIELDS: tuple[str, ...] = (
    'plan_id',
    'run_id',
    'head_sha',
    'pr_number',
    'provider',
)

#: The only two legal ``--wait-outcome`` enum values. The guard NEVER copies
#: ``--final-status``'s value into ``--wait-outcome``.
_WAIT_OUTCOME_ENUM: frozenset[str] = frozenset({'completed', 'deadline_exceeded'})

#: Conclusions that mean a check passed or did not need to run.
_PASSING_CONCLUSIONS: frozenset[str] = frozenset({'success', 'skipped', 'neutral'})

#: Conclusions that mean a check has not finished.
_RUNNING_CONCLUSIONS: frozenset[str] = frozenset({'pending', 'in_progress', 'queued', 'waiting'})

#: Conclusions that say the check itself ended badly — the definitive rows of
#: :func:`classify_check`. Lower-case; compared against a lower-cased
#: ``conclusion``. This is the one definition of the set:
#: ``ci_complete_precondition`` imports it for its pending verdict.
_DEFINITIVE_FAILING_CONCLUSIONS: frozenset[str] = frozenset(
    {'failure', 'failed', 'cancelled', 'canceled', 'action_required', 'stale', 'timed_out', 'timeout'}
)

#: Run-URL segment that precedes the numeric run id in a GitHub check link.
_RUN_ID_MARKER: str = '/actions/runs/'


# ---------------------------------------------------------------------------
# Pure helpers (side-effect-free — the classification core)
# ---------------------------------------------------------------------------


def _matches_policy_profile(workflow_name: str, job_name: str = '') -> bool:
    """Return True when the check names a policy workflow.

    The list is closed: licence/CLA, dependency review, CodeQL, and
    labels/title. Everything else — including a name this rule has never seen —
    is a build failure, so an unrecognised workflow fails toward a fix rather
    than toward an "accept".
    """
    haystack = f'{workflow_name or ""} {job_name or ""}'.lower()
    return any(pattern.search(haystack) for pattern in _POLICY_PROFILE_PATTERNS)


def _has_sonar_quality_gate_failure(job_log: str) -> bool:
    """Return True when a persisted job log carries the Sonar gate marker."""
    return bool(job_log) and _SONAR_QUALITY_GATE_MARKER in job_log


def classify_check(
    check: dict,
    wait_outcome: str,
    *,
    sonar_roundtrip_enabled: bool = False,
    job_log: str = '',
) -> tuple[str, str]:
    """Classify a single failing check into ``(producer, subtype)``.

    The rows are evaluated in the exact order of the taxonomy table in
    ``standards/ci-verify.md`` so a check that concluded ``failure`` before a
    wait deadline is still a build/policy failure, while a still-pending check
    under ``wait_outcome == deadline_exceeded`` falls through to the timeout
    row.

    Args:
        check: A normalized check entry (see :func:`_normalize_check_entry`).
            Reads ``conclusion`` (lower-cased), ``workflow_name`` and
            ``job_name``.
        wait_outcome: The run-level wait outcome — ``completed`` or
            ``deadline_exceeded``. ``deadline_exceeded`` routes any check
            without a definitive failure/cancel/action/stale conclusion into
            the timeout row.
        sonar_roundtrip_enabled: True only when the plan's execution manifest
            carries the ``sonar-roundtrip`` step, so the Sonar deferral has an
            owner in this run.
        job_log: The persisted log of the failing check. A log carrying the
            Sonar quality-gate marker is row (a): a deferral to
            ``sonar-roundtrip``, filed with the ``ci_sonar_gate`` subtype.

    Returns:
        A ``(producer_string, subtype_tag)`` pair. The producer is always the
        single :data:`PRODUCER` value; the subtype tag carries the row. Callers
        wrap the tag as ``[subtype]``.
    """
    conclusion = (check.get('conclusion') or '').strip().lower()

    if conclusion in ('failure', 'failed'):
        if sonar_roundtrip_enabled and _has_sonar_quality_gate_failure(job_log):
            return PRODUCER, _SUBTYPE_SONAR_GATE
        if _matches_policy_profile(check.get('workflow_name') or '', check.get('job_name') or ''):
            return PRODUCER, _SUBTYPE_POLICY
        return PRODUCER, _SUBTYPE_BUILD
    # A definitive cancelled / action_required / stale conclusion wins over the
    # run-level deadline_exceeded fallback below: only a check WITHOUT a
    # definitive failure/cancel/action/stale conclusion (e.g. still pending)
    # should be routed to the timeout row when the wait hit its deadline.
    if conclusion in ('cancelled', 'canceled'):
        return PRODUCER, _SUBTYPE_CANCELLED
    if conclusion == 'action_required':
        return PRODUCER, _SUBTYPE_ACTION_REQUIRED
    if conclusion == 'stale':
        return PRODUCER, _SUBTYPE_STALE
    if conclusion in ('timed_out', 'timeout') or wait_outcome == 'deadline_exceeded':
        return PRODUCER, _SUBTYPE_TIMEOUT
    # Defense in depth: an unrecognised non-success conclusion is a build
    # failure — the fail-toward-a-fix direction, never an "accept".
    return PRODUCER, _SUBTYPE_BUILD


def _extract_run_id_from_url(url: str | None) -> str:
    """Return the numeric run id embedded in a GitHub check ``url``.

    GitHub check links follow ``.../actions/runs/<run_id>/job/<job_id>``.
    Returns the segment immediately after ``/actions/runs/``, or an empty
    string when the marker is absent (e.g. a GitLab link or a bare check).
    """
    if not url:
        return ''
    idx = url.find(_RUN_ID_MARKER)
    if idx == -1:
        return ''
    tail = url[idx + len(_RUN_ID_MARKER) :]
    segment = tail.split('/', 1)[0]
    return segment if re.match(r'^\d+$', segment) else ''


def _normalize_check_entry(check: dict) -> dict:
    """Normalize a check dict from either upstream shape into one schema.

    Two upstream shapes are accepted:

    * The rich ``failing_checks[]`` entry built by the CI provider
      (``name``, ``conclusion``, ``workflow_name``, ``job_name``,
      ``started_at``, ``completed_at``, ``run_id``, ``run_url``).
    * The compact ``checks[]`` row from ``ci checks status``
      (``name``, ``status`` = state, ``result`` = bucket, ``url`` = link,
      ``workflow``).

    Returns a dict carrying the union schema the classifier and the persist
    jobs file both consume: ``name``, ``conclusion``, ``workflow_name``,
    ``job_name``, ``started_at``, ``completed_at``, ``run_url``, ``run_id``,
    plus the persisted ``log_file`` / ``filtered_log_file`` pointers when the
    provider reported them.
    """
    name = check.get('name') or check.get('job_name') or 'unknown'
    conclusion = check.get('conclusion') or check.get('status') or check.get('state') or check.get('result') or ''
    workflow_name = check.get('workflow_name') or check.get('workflow') or ''
    run_url = check.get('run_url') or check.get('url') or check.get('link') or ''
    run_id = check.get('run_id') or _extract_run_id_from_url(run_url)
    return {
        'name': name,
        'conclusion': str(conclusion),
        'workflow_name': workflow_name,
        'job_name': check.get('job_name') or name,
        'started_at': check.get('started_at') or check.get('startedAt') or '',
        'completed_at': check.get('completed_at') or check.get('completedAt') or '',
        'run_url': run_url,
        'run_id': run_id,
        'log_file': check.get('log_file') or '',
        'filtered_log_file': check.get('filtered_log_file') or '',
    }


def _attach_log_pointers(normalized_checks: list[dict], envelope: dict) -> None:
    """Copy the failing checks' persisted log pointers onto their normalized rows.

    ``ci checks status`` reports ``failing_checks[]`` with the downloaded
    ``log_file`` plus the compact ``checks[]`` array without it. The executor
    classifies from ``checks[]``, so the pointer is matched back by
    ``(run_id, job_name)`` — the pair that identifies one check in one run.
    """
    rows = envelope.get('failing_checks')
    if not isinstance(rows, list):
        return
    pointers: dict[tuple[str, str], str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (str(row.get('run_id') or ''), str(row.get('job_name') or row.get('name') or ''))
        pointers[key] = str(row.get('log_file') or '')
    if not pointers:
        return
    for entry in normalized_checks:
        if entry.get('log_file'):
            continue
        key = (str(entry.get('run_id') or ''), str(entry.get('job_name') or ''))
        entry['log_file'] = pointers.get(key, entry.get('log_file') or '')


def _derive_run_id(normalized_checks: list[dict]) -> str:
    """Return the first non-empty run id across the normalized checks."""
    for entry in normalized_checks:
        if entry.get('run_id'):
            return str(entry['run_id'])
    return ''


def _plan_artifact_root(plan_id: str, worktree_path: str) -> Path:
    """Return the plan directory the persisted CI artifacts live under.

    ``manage-ci-artifacts`` writes to ``.plan/local/plans/{plan_id}/`` and
    reports its paths relative to that plan directory. The persist call runs
    with the worktree as its cwd, so its root is the nearest ancestor of the
    worktree holding ``.plan/local`` — mirrored here rather than assumed to be
    the worktree root, so the reader and the writer resolve the same directory.
    """
    start = Path(worktree_path or '.').resolve()
    for candidate in (start, *start.parents):
        if (candidate / '.plan' / 'local').is_dir():
            return candidate / '.plan' / 'local' / 'plans' / plan_id
    return start / '.plan' / 'local' / 'plans' / plan_id


def _sonar_roundtrip_in_manifest(plan_id: str, worktree_path: str) -> bool:
    """Return True when the plan's execution manifest carries ``sonar-roundtrip``.

    The deferral in :func:`classify_check` only applies when the run has an
    owner for it. An unreadable or absent manifest is not an owner: the check
    stays a build failure rather than being handed to a step this plan never
    selected.
    """
    manifest_path = _plan_artifact_root(plan_id, worktree_path) / 'execution.toon'
    try:
        body = parse_toon(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ToonParseError, ValueError):
        return False
    phase_6 = body.get('phase_6') if isinstance(body, dict) else None
    steps = phase_6.get('steps') if isinstance(phase_6, dict) else None
    return isinstance(steps, list) and 'sonar-roundtrip' in steps


def _read_persisted_job_log(plan_id: str, log_file: str, worktree_path: str) -> str:
    """Return a persisted check log's text, or ``''`` when it cannot be read."""
    if not log_file:
        return ''
    try:
        return (_plan_artifact_root(plan_id, worktree_path) / log_file).read_text(encoding='utf-8')
    except (OSError, ValueError):
        return ''


# ---------------------------------------------------------------------------
# Subprocess seams (overridable in tests)
# ---------------------------------------------------------------------------


def _proxy_cmd(notation: str, *args: str) -> list[str]:
    """Build an executor-proxy argv for ``notation`` plus trailing args."""
    executor = get_executor_path()
    return [sys.executable, str(executor), notation, *args]


def _run_proxy(cmd: list[str], worktree_path: str, *, timeout: int = 120) -> dict:
    """Run an executor-proxy command and parse its TOON stdout.

    Returns the parsed dict, or a synthetic ``{'status': 'error', ...}`` dict
    on any subprocess/parse failure so callers never see an exception escape.
    """
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            cwd=worktree_path or None,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {'status': 'error', 'error': f'subprocess failed: {exc}'}
    stdout = completed.stdout or ''
    if not stdout.strip():
        return {
            'status': 'error',
            'error': (
                f'no output (exit_code={completed.returncode}): {(completed.stderr or "").strip() or "no stderr"}'
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {'status': 'error', 'error': f'unparseable TOON: {exc}', 'raw': stdout}


def _run_ci_checks_status(plan_id: str, pr_number: int, worktree_path: str) -> dict:
    """Fetch the settled CI checks envelope via ``ci checks status``.

    Returns the parsed TOON envelope (``checks[]``, ``overall_status``, and —
    on the failure path — ``failing_checks[]``). On any error the returned
    dict carries ``status: error`` and the caller degrades to threaded inputs.
    """
    cmd = _proxy_cmd(
        _CI_NOTATION,
        '--plan-id',
        plan_id,
        'checks',
        'status',
        '--pr-number',
        str(pr_number),
    )
    return _run_proxy(cmd, worktree_path)


def _run_manage_ci_artifacts_persist(
    *,
    plan_id: str,
    run_id: str,
    head_sha: str,
    pr_number: int,
    provider: str,
    wait_outcome: str,
    final_status: str,
    jobs_file: str,
    worktree_path: str,
) -> dict:
    """Invoke ``manage-ci-artifacts persist`` with all required flags.

    The caller has already run the required-field guard; this seam performs no
    validation of its own beyond passing the arguments through verbatim.
    """
    cmd = _proxy_cmd(
        _CI_ARTIFACTS_NOTATION,
        'persist',
        '--plan-id',
        plan_id,
        '--run-id',
        run_id,
        '--head-sha',
        head_sha,
        '--pr-number',
        str(pr_number),
        '--provider',
        provider,
        '--wait-outcome',
        wait_outcome,
        '--final-status',
        final_status,
        '--jobs-file',
        jobs_file,
    )
    return _run_proxy(cmd, worktree_path)


def _run_manage_findings_add(
    *,
    plan_id: str,
    title: str,
    detail: str,
    file_path: str,
    worktree_path: str,
) -> dict:
    """File one ``triage`` finding via ``manage-findings add``."""
    cmd = _proxy_cmd(
        _FINDINGS_NOTATION,
        'add',
        '--plan-id',
        plan_id,
        '--type',
        'triage',
        '--severity',
        'warning',
        '--component',
        _COMPONENT,
        '--title',
        title,
        '--detail',
        detail,
        '--file-path',
        file_path,
    )
    return _run_proxy(cmd, worktree_path)


def _run_mark_step_done(
    *,
    plan_id: str,
    display_detail: str,
    head_at_completion: str,
    worktree_path: str,
) -> dict:
    """Mark the ci-verify step ``done`` under the bare manifest key.

    Only the green path calls this seam; the red path leaves the terminal
    mark to the dispatcher (after ``verification-feedback`` returns).
    """
    cmd = _proxy_cmd(
        _STATUS_NOTATION,
        'mark-step-done',
        '--plan-id',
        plan_id,
        '--phase',
        _PHASE_KEY,
        '--step',
        _STEP_KEY,
        '--outcome',
        'done',
        '--display-detail',
        display_detail,
        '--head-at-completion',
        head_at_completion,
    )
    return _run_proxy(cmd, worktree_path)


def _run_git_rev_parse_head(worktree_path: str) -> str:
    """Return the worktree HEAD SHA, or an empty string on any failure.

    A missing HEAD SHA degrades the green ``--head-at-completion`` to an empty
    string. Whether ``mark-step-done`` then records the outcome is the mark's
    own decision, not this helper's: :func:`verify` reads the mark's returned
    ``status`` and reports ``outcome: green_unrecorded`` when it refused.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', worktree_path or '.', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return ''
    if completed.returncode != 0:
        return ''
    return completed.stdout.strip()


# ---------------------------------------------------------------------------
# Jobs-file capture
# ---------------------------------------------------------------------------


def _write_jobs_file(
    plan_id: str,
    run_id: str,
    normalized_checks: list[dict],
    worktree_path: str,
) -> str:
    """Write the normalized checks array to a ``.plan/temp/`` jobs file.

    Returns the absolute path of the written file. An empty ``normalized_checks``
    list writes ``[]`` — the persist layer then records a ``jobs_source: empty``
    manifest deliberately.
    """
    base = Path(worktree_path) if worktree_path else Path.cwd()
    temp_dir = base / '.plan' / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = run_id or 'no-run-id'
    jobs_path = temp_dir / f'{plan_id}-ci-jobs-{suffix}.json'
    jobs_path.write_text(json.dumps(normalized_checks, indent=2), encoding='utf-8')
    return str(jobs_path)


# ---------------------------------------------------------------------------
# Required-field guard
# ---------------------------------------------------------------------------


def _first_missing_required_field(
    *,
    plan_id: str,
    run_id: str,
    head_sha: str,
    pr_number: int | str,
    provider: str,
) -> str | None:
    """Return the name of the first empty required persist field, else None.

    ``pr_number`` is stringified before the emptiness test so a ``0`` PR number
    (never legal) is caught as an empty value — both the falsy int ``0`` and the
    truthy string ``'0'`` normalize to empty so the guard is consistent.
    """
    pr_str = str(pr_number or '').strip()
    if pr_str == '0':
        pr_str = ''
    values = {
        'plan_id': str(plan_id or '').strip(),
        'run_id': str(run_id or '').strip(),
        'head_sha': str(head_sha or '').strip(),
        'pr_number': pr_str,
        'provider': str(provider or '').strip(),
    }
    for field in _REQUIRED_PERSIST_FIELDS:
        if not values[field]:
            return field
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def verify(
    *,
    plan_id: str,
    pr_number: int,
    worktree_path: str,
    provider: str,
    final_status: str,
    wait_outcome: str,
    head_sha: str = '',
    failing_checks: list[dict] | None = None,
    ci_status_runner=None,
    persist_runner=None,
    findings_runner=None,
    mark_done_runner=None,
    git_head_resolver=None,
) -> dict:
    """Run the deterministic ci-verify classification and side effects.

    Args:
        plan_id: Plan identifier (echoed; keys every side-effect call).
        pr_number: PR number the CI run belongs to.
        worktree_path: Active git worktree root (subprocess cwd; jobs-file base;
            green ``--head-at-completion`` source). Empty for main-checkout plans.
        provider: ``github`` or ``gitlab`` — forwarded to the persist call.
        final_status: The settled run-level verdict threaded from the
            ``consume-failures`` precondition — ``success`` / ``failure`` /
            ``none`` / ``timeout`` (the dispatcher maps the precondition's
            ``no_checks`` to ``none``).
        wait_outcome: ``completed`` or ``deadline_exceeded`` — threaded from the
            precondition. NEVER derived from ``final_status``. Constrained to
            :data:`_WAIT_OUTCOME_ENUM`; an out-of-enum value clamps to
            ``completed`` so the persist ``--wait-outcome`` flag is always legal.
        head_sha: HEAD SHA threaded from the precondition. May be empty (the
            required-field guard then skips persist).
        failing_checks: Optional rich failing-check entries threaded from the
            precondition. When ``None``, the failing set is derived from the
            fresh ``ci checks status`` fetch (on the ``failure`` path) or from
            the wait-state checks (on the ``timeout`` path).
        ci_status_runner: Test seam for :func:`_run_ci_checks_status` —
            ``(plan_id, pr_number, worktree_path) -> dict``.
        persist_runner: Test seam for :func:`_run_manage_ci_artifacts_persist`.
        findings_runner: Test seam for :func:`_run_manage_findings_add`.
        mark_done_runner: Test seam for :func:`_run_mark_step_done`.
        git_head_resolver: Test seam for :func:`_run_git_rev_parse_head` —
            ``(worktree_path) -> str``.

    Returns:
        The result dict documented in the module docstring.
    """
    status_fn = ci_status_runner or _run_ci_checks_status
    persist_fn = persist_runner or _run_manage_ci_artifacts_persist
    findings_fn = findings_runner or _run_manage_findings_add
    mark_done_fn = mark_done_runner or _run_mark_step_done
    head_fn = git_head_resolver or _run_git_rev_parse_head

    # Constrain wait_outcome to its enum — NEVER copy final_status here.
    if wait_outcome not in _WAIT_OUTCOME_ENUM:
        wait_outcome = 'completed'

    # Fetch the full checks[] array for the jobs file (green + red evidence).
    # status_fn's own boundary wraps subprocess/parse failures into a synthetic
    # error dict, so envelope is contractually a dict — no isinstance guard is
    # needed. A genuine status_fn error carries status == 'error' and no usable
    # checks; short-circuit to an empty set rather than silently reading a
    # missing 'checks' key as if the run had legitimately zero checks.
    envelope = status_fn(plan_id, pr_number, worktree_path)
    raw_checks: list
    if envelope.get('status') == 'error':
        raw_checks = []
    else:
        candidate = envelope.get('checks')
        raw_checks = candidate if isinstance(candidate, list) else []
    # A partially-corrupt checks entry (non-dict element) would raise inside
    # _normalize_check_entry — surface it as a structured error instead of an
    # uncaught traceback.
    try:
        normalized_all = [_normalize_check_entry(c) for c in raw_checks]
    except (TypeError, ValueError, AttributeError) as exc:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': f'Malformed checks structure: {exc}',
        }
    _attach_log_pointers(normalized_all, envelope)

    # Resolve run_id from the normalized checks (first non-empty run URL).
    run_id = _derive_run_id(normalized_all)

    # Capture the jobs file (always — including green, for retrospective audit).
    jobs_file = _write_jobs_file(plan_id, run_id, normalized_all, worktree_path)

    # Persist artifacts behind the required-field guard.
    persisted = False
    persist_skipped_reason: str | None = None
    missing = _first_missing_required_field(
        plan_id=plan_id,
        run_id=run_id,
        head_sha=head_sha,
        pr_number=pr_number,
        provider=provider,
    )
    if missing is not None:
        persist_skipped_reason = missing
    else:
        persist_result = persist_fn(
            plan_id=plan_id,
            run_id=run_id,
            head_sha=head_sha,
            pr_number=pr_number,
            provider=provider,
            wait_outcome=wait_outcome,
            final_status=final_status,
            jobs_file=jobs_file,
            worktree_path=worktree_path,
        )
        # persist_fn shares the same contractually-dict _run_proxy boundary as
        # status_fn, so no isinstance guard is needed here.
        persisted = persist_result.get('status') == 'success'
        if not persisted:
            persist_skipped_reason = 'persist_failed'

    # ----- Green early return -------------------------------------------
    if final_status == 'success' and not (failing_checks or []):
        sha = head_fn(worktree_path)
        mark_result = mark_done_fn(
            plan_id=plan_id,
            display_detail='ci-verify: all checks green',
            head_at_completion=sha,
            worktree_path=worktree_path,
        )
        # The mark is a write that can be refused; report what it returned
        # rather than that it was attempted. mark_done_fn shares the
        # contractually-dict _run_proxy boundary, so no isinstance guard.
        step_marked_done = mark_result.get('status') == 'success'
        green_result = {
            'status': 'success',
            'plan_id': plan_id,
            'final_status': final_status,
            'outcome': 'green' if step_marked_done else 'green_unrecorded',
            'run_id': run_id,
            'head_sha': head_sha,
            'persisted': persisted,
            **({'persist_skipped_reason': persist_skipped_reason} if persist_skipped_reason else {}),
            'findings_filed': 0,
            'step_marked_done': step_marked_done,
        }
        if not step_marked_done:
            green_result['step_mark_error'] = str(mark_result.get('error') or '')
            green_result['step_mark_message'] = str(mark_result.get('message') or '')
        return green_result

    # ----- No-checks case ------------------------------------------------
    findings_filed = 0
    producers: list[str] = []
    if final_status == 'none':
        findings_fn(
            plan_id=plan_id,
            title=f'[{_SUBTYPE_MISSING}] CI run produced zero checks',
            detail=(f'[{_SUBTYPE_MISSING}] CI run produced zero checks for PR {pr_number} at HEAD {head_sha}'),
            file_path=f'artifacts/ci-runs/{run_id}/manifest.toon',
            worktree_path=worktree_path,
        )
        findings_filed = 1
        producers = [PRODUCER]
        return {
            'status': 'success',
            'plan_id': plan_id,
            'final_status': final_status,
            'outcome': 'needs_triage',
            'run_id': run_id,
            'head_sha': head_sha,
            'persisted': persisted,
            **({'persist_skipped_reason': persist_skipped_reason} if persist_skipped_reason else {}),
            'findings_filed': findings_filed,
            'producers': producers,
            'step_marked_done': False,
        }

    # ----- Failing / timeout partition ----------------------------------
    failing_set = _resolve_failing_set(
        threaded=failing_checks,
        normalized_all=normalized_all,
        final_status=final_status,
        wait_outcome=wait_outcome,
    )

    seen_producers: list[str] = []
    sonar_roundtrip_enabled = _sonar_roundtrip_in_manifest(plan_id, worktree_path)
    for check in failing_set:
        job_log = ''
        if sonar_roundtrip_enabled:
            job_log = _read_persisted_job_log(plan_id, str(check.get('log_file') or ''), worktree_path)
        producer, subtype = classify_check(
            check,
            wait_outcome,
            sonar_roundtrip_enabled=sonar_roundtrip_enabled,
            job_log=job_log,
        )
        check_name = check.get('name') or 'unknown'
        job_name = check.get('job_name') or check_name
        # Key the artifact path on the run THIS check belongs to: two failing
        # runs at one head then file under two directories instead of the first
        # run's directory twice.
        check_run_id = str(check.get('run_id') or '') or run_id or 'no-run-id'
        detail = f'[{subtype}] {check_name} failed on PR {pr_number} at HEAD {head_sha}'
        if subtype == _SUBTYPE_SONAR_GATE:
            detail += ' — deferred to sonar-roundtrip, which owns the Sonar quality gate'
        findings_fn(
            plan_id=plan_id,
            title=f'[{subtype}] {check_name} failed',
            detail=detail,
            file_path=f'artifacts/ci-runs/{check_run_id}/{job_name}.log',
            worktree_path=worktree_path,
        )
        findings_filed += 1
        if producer not in seen_producers:
            seen_producers.append(producer)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'final_status': final_status,
        'outcome': 'needs_triage',
        'run_id': run_id,
        'head_sha': head_sha,
        'persisted': persisted,
        **({'persist_skipped_reason': persist_skipped_reason} if persist_skipped_reason else {}),
        'findings_filed': findings_filed,
        'producers': seen_producers,
        'step_marked_done': False,
    }


def _resolve_failing_set(
    *,
    threaded: list[dict] | None,
    normalized_all: list[dict],
    final_status: str,
    wait_outcome: str,
) -> list[dict]:
    """Return the normalized failing-check set to classify.

    Preference order:

    1. Rich ``failing_checks[]`` threaded from the precondition (authoritative).
    2. The ``failing_checks[]`` sub-array of the fresh ``ci checks status``
       envelope is already folded into ``normalized_all`` by the caller when
       present; here we derive the failing set from ``normalized_all`` by
       dropping every check whose conclusion is a success/skip/neutral/pending
       state. On the ``timeout`` path (``wait_outcome == deadline_exceeded``)
       the still-pending checks are retained at this point.

    Either set then passes through :func:`_drop_running_beside_failures`, so a
    still-running check is classified only when nothing has definitively
    failed.
    """
    if threaded:
        return _drop_running_beside_failures([_normalize_check_entry(c) for c in threaded], wait_outcome)

    # An empty/unknown conclusion is NOT passing — it must fall through to the
    # classifier's ci_policy_failure defense-in-depth row (fail-closed).
    failing_set: list[dict] = []
    for entry in normalized_all:
        conclusion = (entry.get('conclusion') or '').strip().lower()
        if wait_outcome == 'deadline_exceeded':
            # Retain everything not clearly green — pending checks are the
            # timed-out ones.
            if conclusion not in _PASSING_CONCLUSIONS:
                failing_set.append(entry)
            continue
        if conclusion in _PASSING_CONCLUSIONS or conclusion in _RUNNING_CONCLUSIONS:
            continue
        failing_set.append(entry)
    return _drop_running_beside_failures(failing_set, wait_outcome)


def _drop_running_beside_failures(failing_set: list[dict], wait_outcome: str) -> list[dict]:
    """Drop still-running checks when a check has definitively failed.

    Applies only under ``wait_outcome == deadline_exceeded``. When at least one
    check carries a definitive failing conclusion, the still-running checks are
    removed: they have not failed, and a ``ci_timeout`` finding beside the real
    failure would report a check that is merely not finished. When no check
    carries one, the set is returned unchanged and each running check is a
    ``ci_timeout``. A check whose own conclusion is ``timed_out`` is definitive
    and is never dropped.

    Still running means a conclusion in :data:`_RUNNING_CONCLUSIONS`, or no
    conclusion at all: a check that has not finished at a wait deadline has
    none yet. A conclusion that is present but unrecognised is kept.
    """
    if wait_outcome != 'deadline_exceeded':
        return failing_set
    conclusions = [(entry.get('conclusion') or '').strip().lower() for entry in failing_set]
    if not any(conclusion in _DEFINITIVE_FAILING_CONCLUSIONS for conclusion in conclusions):
        return failing_set
    return [
        entry
        for entry, conclusion in zip(failing_set, conclusions, strict=True)
        if conclusion and conclusion not in _RUNNING_CONCLUSIONS
    ]


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`verify` — emits TOON, returns exit 0/1."""
    threaded_failing: list[dict] | None = None
    if getattr(args, 'failing_checks_file', None):
        try:
            content = Path(args.failing_checks_file).read_text(encoding='utf-8')
            parsed = json.loads(content) if content.strip() else []
            threaded_failing = parsed if isinstance(parsed, list) else None
        except (OSError, json.JSONDecodeError) as exc:
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': (f'failing-checks-file unreadable ({args.failing_checks_file}): {exc}'),
                    }
                )
            )
            return 1

    try:
        result = verify(
            plan_id=args.plan_id,
            pr_number=args.pr_number,
            worktree_path=args.worktree_path,
            provider=args.provider,
            final_status=args.final_status,
            wait_outcome=args.wait_outcome,
            head_sha=args.head_sha or '',
            failing_checks=threaded_failing,
        )
    except OSError as exc:
        # Guard every I/O boundary inside verify() (jobs-file mkdir/write,
        # subprocess side effects) so a filesystem failure surfaces as the
        # documented status:error TOON envelope rather than an uncaught
        # traceback — mirroring the failing-checks-file read guard above.
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': f'ci-verify I/O failure: {exc}',
                }
            )
        )
        return 1
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``run`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Deterministic ci-verify finalize-step executor. Classifies CI '
            'run failures into the multi-failure-mode taxonomy, persists CI '
            'run artifacts, marks the step done on green, and returns the '
            'single `ci-verify` producer needs-triage signal on red CI.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    run_parser = sub.add_parser(
        'run',
        help='Run ci-verify classification for the current CI run',
        allow_abbrev=False,
    )
    run_parser.add_argument('--plan-id', required=True, dest='plan_id')
    run_parser.add_argument('--pr-number', required=True, dest='pr_number', type=int)
    run_parser.add_argument('--worktree-path', required=True, dest='worktree_path')
    run_parser.add_argument('--provider', required=True, choices=('github', 'gitlab'))
    run_parser.add_argument(
        '--final-status',
        required=True,
        dest='final_status',
        choices=('success', 'failure', 'none', 'timeout'),
        help=(
            'Settled run-level verdict threaded from the consume-failures '
            'precondition (the dispatcher maps no_checks -> none).'
        ),
    )
    run_parser.add_argument(
        '--wait-outcome',
        required=True,
        dest='wait_outcome',
        choices=('completed', 'deadline_exceeded'),
        help=('Wait outcome threaded from the precondition. NEVER derived from --final-status.'),
    )
    run_parser.add_argument(
        '--head-sha',
        default='',
        dest='head_sha',
        help='HEAD SHA threaded from the precondition (may be empty).',
    )
    run_parser.add_argument(
        '--failing-checks-file',
        default=None,
        dest='failing_checks_file',
        help=(
            'Optional path to a JSON array of rich failing-check entries '
            'threaded from the precondition envelope. When omitted, the '
            'failing set is derived from the fresh ci checks status fetch.'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'classify_check',
    'verify',
]
