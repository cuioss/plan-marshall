#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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
  dispatch.
* Non-green → file exactly ONE taxonomy finding per failing check (plus the
  ``ci_no_checks`` finding on ``final_status == none``) and return a
  per-producer needs-triage signal so the dispatcher runs
  ``verification-feedback`` (the sole LLM step, red-CI only). The script does
  NOT mark the step done on the red path — the dispatcher marks it after the
  triage returns.

``mark-step-done --step`` uses the bare manifest key ``ci-verify`` (NOT a
``default:``-prefixed key).

Return shape (CLI emits this as TOON; programmatic callers consume the dict
directly)::

    status: success | error
    plan_id: <echo>
    final_status: success | failure | none | timeout
    outcome: green | needs_triage
    run_id: <str>              # derived from checks[] run URLs; may be empty
    head_sha: <str>            # threaded from the precondition; may be empty
    persisted: true | false
    persist_skipped_reason: <field>   # present only when persisted == false
    findings_filed: <int>
    producers: [str, ...]      # present only when outcome == needs_triage
    step_marked_done: true | false    # true only on the green path

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
from toon_parser import parse_toon, serialize_toon

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

#: The architecture-resolved build-command canonical names. A CI check whose
#: ``workflow_name`` contains one of these tokens is a build-profile failure
#: (row b); everything else is a policy failure (row c). The match rule is
#: single-sourced here per ``standards/ci-verify.md``; projects whose CI labels
#: diverge override it via the architecture skill's config, not here.
_BUILD_PROFILE_NAMES: frozenset[str] = frozenset(
    {'verify', 'quality-gate', 'module-tests', 'coverage'}
)

#: The seven distinct producer strings the taxonomy classifier emits.
_PRODUCER_MISSING: str = 'ci-verify-missing'
_PRODUCER_BUILD: str = 'ci-verify-build'
_PRODUCER_POLICY: str = 'ci-verify-policy'
_PRODUCER_TIMEOUT: str = 'ci-verify-timeout'
_PRODUCER_CANCELLED: str = 'ci-verify-cancelled'
_PRODUCER_ACTION_REQUIRED: str = 'ci-verify-action-required'
_PRODUCER_STALE: str = 'ci-verify-stale'

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

#: Run-URL segment that precedes the numeric run id in a GitHub check link.
_RUN_ID_MARKER: str = '/actions/runs/'


# ---------------------------------------------------------------------------
# Pure helpers (side-effect-free — the classification core)
# ---------------------------------------------------------------------------


def _matches_build_profile(workflow_name: str) -> bool:
    """Return True when ``workflow_name`` names a build-profile workflow.

    A workflow name matches when any architecture-resolved build-command
    canonical token (:data:`_BUILD_PROFILE_NAMES`) appears in the lower-cased
    name. GitHub workflow names such as ``"verify / verify"`` therefore match
    the ``verify`` canonical; ``"license/cla"`` matches none and lands in the
    policy row.
    """
    lowered = (workflow_name or '').lower()
    return any(token in lowered for token in _BUILD_PROFILE_NAMES)


def classify_check(check: dict, wait_outcome: str) -> tuple[str, str]:
    """Classify a single failing check into ``(producer, subtype)``.

    The rows are evaluated in the exact order of the taxonomy table in
    ``standards/ci-verify.md`` so a check that concluded ``failure`` before a
    wait deadline is still a build/policy failure, while a still-pending check
    under ``wait_outcome == deadline_exceeded`` falls through to the timeout
    row.

    Args:
        check: A normalized check entry (see :func:`_normalize_check_entry`).
            Reads ``conclusion`` (lower-cased) and ``workflow_name``.
        wait_outcome: The run-level wait outcome — ``completed`` or
            ``deadline_exceeded``. ``deadline_exceeded`` routes any check
            without a definitive failure/cancel/action/stale conclusion into
            the timeout row.

    Returns:
        A ``(producer_string, subtype_tag)`` pair. The subtype tag is carried
        verbatim (without brackets) — callers wrap it as ``[subtype]``.
    """
    conclusion = (check.get('conclusion') or '').strip().lower()

    if conclusion in ('failure', 'failed'):
        if _matches_build_profile(check.get('workflow_name') or ''):
            return _PRODUCER_BUILD, 'ci_build_failure'
        return _PRODUCER_POLICY, 'ci_policy_failure'
    if conclusion in ('timed_out', 'timeout') or wait_outcome == 'deadline_exceeded':
        return _PRODUCER_TIMEOUT, 'ci_timeout'
    if conclusion in ('cancelled', 'canceled'):
        return _PRODUCER_CANCELLED, 'ci_cancelled'
    if conclusion == 'action_required':
        return _PRODUCER_ACTION_REQUIRED, 'ci_action_required'
    if conclusion == 'stale':
        return _PRODUCER_STALE, 'ci_stale'
    # Defense in depth: an unknown non-success conclusion is a policy failure,
    # never silently accepted as green.
    return _PRODUCER_POLICY, 'ci_policy_failure'


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
    tail = url[idx + len(_RUN_ID_MARKER):]
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
    ``job_name``, ``started_at``, ``completed_at``, ``run_url``, ``run_id``.
    """
    name = check.get('name') or check.get('job_name') or 'unknown'
    conclusion = (
        check.get('conclusion')
        or check.get('status')
        or check.get('state')
        or check.get('result')
        or ''
    )
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
    }


def _derive_run_id(normalized_checks: list[dict]) -> str:
    """Return the first non-empty run id across the normalized checks."""
    for entry in normalized_checks:
        if entry.get('run_id'):
            return str(entry['run_id'])
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
                f'no output (exit_code={completed.returncode}): '
                f'{(completed.stderr or "").strip() or "no stderr"}'
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
    string; ``mark-step-done`` still records the terminal outcome (the SHA is
    only consulted by the resumable HEAD-advance check).
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
    jobs_path.write_text(
        json.dumps(normalized_checks, indent=2), encoding='utf-8'
    )
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
    (never legal) is caught as an empty value.
    """
    values = {
        'plan_id': str(plan_id or '').strip(),
        'run_id': str(run_id or '').strip(),
        'head_sha': str(head_sha or '').strip(),
        'pr_number': str(pr_number or '').strip(),
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
    envelope = status_fn(plan_id, pr_number, worktree_path)
    raw_checks = envelope.get('checks') if isinstance(envelope, dict) else None
    raw_checks = raw_checks if isinstance(raw_checks, list) else []
    normalized_all = [_normalize_check_entry(c) for c in raw_checks]

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
        persisted = (
            isinstance(persist_result, dict)
            and persist_result.get('status') == 'success'
        )
        if not persisted:
            persist_skipped_reason = 'persist_failed'

    # ----- Green early return -------------------------------------------
    if final_status == 'success' and not (failing_checks or []):
        sha = head_fn(worktree_path)
        mark_done_fn(
            plan_id=plan_id,
            display_detail='ci-verify: all checks green',
            head_at_completion=sha,
            worktree_path=worktree_path,
        )
        return {
            'status': 'success',
            'plan_id': plan_id,
            'final_status': final_status,
            'outcome': 'green',
            'run_id': run_id,
            'head_sha': head_sha,
            'persisted': persisted,
            **({'persist_skipped_reason': persist_skipped_reason}
               if persist_skipped_reason else {}),
            'findings_filed': 0,
            'step_marked_done': True,
        }

    # ----- No-checks case ------------------------------------------------
    findings_filed = 0
    producers: list[str] = []
    if final_status == 'none':
        findings_fn(
            plan_id=plan_id,
            title='[ci_no_checks] CI run produced zero checks',
            detail=(
                f'[ci_no_checks] CI run produced zero checks for PR '
                f'{pr_number} at HEAD {head_sha}'
            ),
            file_path=f'artifacts/ci-runs/{run_id}/manifest.toon',
            worktree_path=worktree_path,
        )
        findings_filed = 1
        producers = [_PRODUCER_MISSING]
        return {
            'status': 'success',
            'plan_id': plan_id,
            'final_status': final_status,
            'outcome': 'needs_triage',
            'run_id': run_id,
            'head_sha': head_sha,
            'persisted': persisted,
            **({'persist_skipped_reason': persist_skipped_reason}
               if persist_skipped_reason else {}),
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
    for check in failing_set:
        producer, subtype = classify_check(check, wait_outcome)
        check_name = check.get('name') or 'unknown'
        job_name = check.get('job_name') or check_name
        findings_fn(
            plan_id=plan_id,
            title=f'[{subtype}] {check_name} failed',
            detail=(
                f'[{subtype}] {check_name} failed on PR {pr_number} '
                f'at HEAD {head_sha}'
            ),
            file_path=f'artifacts/ci-runs/{run_id}/{job_name}.log',
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
        **({'persist_skipped_reason': persist_skipped_reason}
           if persist_skipped_reason else {}),
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
       the still-pending checks are retained so they classify as ``ci_timeout``.
    """
    if threaded:
        return [_normalize_check_entry(c) for c in threaded]

    passing = {'success', 'skipped', 'neutral', ''}
    failing_set: list[dict] = []
    for entry in normalized_all:
        conclusion = (entry.get('conclusion') or '').strip().lower()
        is_pending = conclusion in ('pending', 'in_progress', 'queued', 'waiting')
        if wait_outcome == 'deadline_exceeded':
            # Retain everything not clearly green — pending checks are the
            # timed-out ones.
            if conclusion not in ('success', 'skipped', 'neutral'):
                failing_set.append(entry)
            continue
        if conclusion in passing or is_pending:
            continue
        failing_set.append(entry)
    return failing_set


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
                        'error': (
                            f'failing-checks-file unreadable '
                            f'({args.failing_checks_file}): {exc}'
                        ),
                    }
                )
            )
            return 1

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
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``run`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Deterministic ci-verify finalize-step executor. Classifies CI '
            'run failures into the multi-failure-mode taxonomy, persists CI '
            'run artifacts, marks the step done on green, and returns a '
            'per-producer needs-triage signal on red CI.'
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
    run_parser.add_argument(
        '--pr-number', required=True, dest='pr_number', type=int
    )
    run_parser.add_argument(
        '--worktree-path', required=True, dest='worktree_path'
    )
    run_parser.add_argument(
        '--provider', required=True, choices=('github', 'gitlab')
    )
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
        help=(
            'Wait outcome threaded from the precondition. NEVER derived from '
            '--final-status.'
        ),
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
