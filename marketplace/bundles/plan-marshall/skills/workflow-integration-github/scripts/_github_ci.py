#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub CI/checks command handlers.

Holds the ``cmd_ci_*`` handler bodies plus the CI-only non-patched helpers
(head-SHA resolution, failing-check enrichment, log-filter loader). The pure
check-row classification/link helpers are imported from ``_github_checks``;
every network primitive and monkeypatch-sensitive helper (``run_gh``,
``check_auth``, ``poll_until``, ``format_checks_toon``,
``_fetch_pr_overall_ci_status``, ``_fetch_failed_run_log``, and the shared
``_resolve_pr_identifier``) lives in the entry module ``github_ops`` and is
reached via ATTRIBUTE access on the imported ``github_ops`` module at call
time — never ``from github_ops import <name>``, which would defeat a test's
``monkeypatch.setattr(github_ops, '<name>', ...)``.
"""

import argparse
import json
import time
from typing import Any

import github_ops
from _github_checks import (
    _build_failing_check_entry,
    _classify_check_buckets,
    _derive_overall_status,
    _extract_run_id_from_link,
)
from ci_base import (
    enrich_failing_checks_with_logs,
    make_error,
    make_simple_handler,
    record_wait_mechanism,
)


def _fetch_pr_head_sha(pr_number: int | str) -> str:
    """Resolve the head commit SHA for a PR via ``gh pr view``.

    Returns the SHA on success; on any failure path returns an empty string
    so callers can still emit the rest of the envelope without aborting. The
    head SHA is needed by deliverable 7 to key artifact persistence by run.
    """

    returncode, stdout, _stderr = github_ops.run_gh(['pr', 'view', str(pr_number), '--json', 'headRefOid'])
    if returncode != 0:
        return ''
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return ''
    return str(data.get('headRefOid') or '')


def fetch_pr_head_sha(pr_number: int | str) -> str:
    """Public wrapper over :func:`_fetch_pr_head_sha`.

    Exposes the PR HEAD-SHA resolution for the re-review strategy registry
    (``github_re_review.py``), which needs the current HEAD to match a fresh
    bot review against. Returns the SHA on success or an empty string on any
    failure path, mirroring the private helper's no-abort contract.
    """

    return _fetch_pr_head_sha(pr_number)


def _enrich_failing_checks(
    entries: list[dict],
    *,
    plan_id: str | None,
    error_style: str,
    head_sha: str,
    pr_number: int | str,
) -> list[dict]:
    """Inject per-run keys and run the shared download+filter+store hook.

    Seeds each entry with ``head_sha`` / ``pr_number`` so the persisted manifest
    is keyed correctly, then delegates to
    :func:`ci_base.enrich_failing_checks_with_logs` (per-entry graceful degrade).
    """
    for entry in entries:
        entry.setdefault('head_sha', head_sha)
        entry.setdefault('pr_number', pr_number)
    return enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=github_ops._fetch_failed_run_log,
        plan_id=plan_id,
        error_style=error_style,
    )


def cmd_ci_status(args: argparse.Namespace) -> dict:
    """Handle 'ci status' subcommand."""
    # Check auth
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('ci_status', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'ci_status')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    # Get checks (bucket field contains pass/fail result)
    returncode, stdout, stderr = github_ops.run_gh(
        ['pr', 'checks', identifier, '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
    )
    if returncode != 0:
        return make_error('ci_status', f'Failed to get CI status for PR {identifier}', stderr.strip())

    # Parse JSON
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('ci_status', 'Failed to parse gh output', stdout[:100])

    # Determine overall status via the canonical conclusion partition.
    # ``mixed`` is no longer a possible outcome — every input resolves to
    # ``pending | success | failure | none``.
    overall, failing_rows, _wait_rows = _derive_overall_status(checks)

    # Format checks table — ci_status has no caller-supplied duration ceiling,
    # so out-of-range aggregates are substituted with 0.
    check_dicts, total_elapsed = github_ops.format_checks_toon(checks, duration_ceiling=0)

    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'overall_status': overall,
        'check_count': len(checks),
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
    }

    # On failure, surface the per-check failing-checks table enriched with each
    # entry's downloaded raw + filtered log paths. Success/pending paths are
    # unchanged.
    if overall == 'failure':
        failing_entries = [_build_failing_check_entry(c) for c in failing_rows]
        head_sha = _fetch_pr_head_sha(identifier)
        result['failing_checks'] = _enrich_failing_checks(
            failing_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number if args.pr_number else identifier,
        )

    return result


#: Run-configuration command key under which the observed ``ci wait`` durations
#: are recorded (the p50 seed source for the adaptive first sleep). Mirrors the
#: ``ci:wait`` key ``ci_complete_precondition`` uses for the timeout ceiling.
_CI_WAIT_DURATION_KEY = 'ci:wait'


def _monotonic() -> float:
    """Monotonic wall-clock seam. Isolated so tests can supply a deterministic
    clock and observe the recorded wait duration in constant time."""
    return time.monotonic()


def _sleep_seed(seconds: int) -> None:
    """Sleep the p50-seeded first wait exactly once.

    Isolated as a seam so tests neutralise the sleep and run in constant time.
    A non-positive value is a no-op.
    """
    if seconds > 0:
        time.sleep(seconds)


def _read_ci_wait_p50_seed() -> int | float | None:
    """Read the p50 (median) seed for the ``ci:wait`` duration window.

    Private seam over the run-configuration ci-duration API so ``cmd_ci_wait``
    can seed its first sleep from history. Returns ``None`` on an empty/absent
    window or any failure, so the caller simply skips the seed. Test-mockable.
    """
    try:
        import run_config

        return run_config._p50_of(run_config._read_ci_duration_window(_CI_WAIT_DURATION_KEY))
    except Exception:
        return None


def _record_ci_wait_duration(duration: int) -> None:
    """Record an observed successful ``ci:wait`` duration into the p50 window.

    Private seam over the run-configuration ci-duration record API; best-effort —
    a failure never aborts the wait result. Test-mockable.
    """
    try:
        import run_config

        run_config._record_ci_duration(_CI_WAIT_DURATION_KEY, duration)
    except Exception:
        pass


def _watch_run(run_id: str, timeout: int) -> tuple[int, str, str]:
    """Private subprocess seam over ``gh run watch --exit-status``.

    Blocks until the given workflow run reaches a terminal conclusion — the
    purpose-built terminal-state watch verb, whose ETag/304-conditional polling
    is handled by ``gh`` itself, never a hand-rolled sleep loop. Exits non-zero
    when the run concludes in failure. Test-mockable via monkeypatch. Returns
    ``(returncode, stdout, stderr)``.

    A ``subprocess.TimeoutExpired`` (or any other watch failure) is caught and
    mapped to a non-zero return rather than propagating: the caller
    (``cmd_ci_wait``) treats a non-zero watch as "not terminal yet" and falls
    through to a fresh checks fetch, so a watch that hits its budget resolves to
    the ``deadline_exceeded`` envelope instead of crashing the command.
    """
    try:
        return github_ops.run_gh(['run', 'watch', str(run_id), '--exit-status', '--compact'], timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — any watch failure degrades to the checks-fetch fallback
        return 1, '', f'gh run watch failed or timed out: {exc}'


def _fetch_pr_checks(pr_number: int | str) -> tuple[bool, dict]:
    """Fetch the PR's check rows via ``gh pr checks``.

    Returns ``(True, {'checks': [...]})`` on success, or ``(False, {'error',
    'context'})`` on a fetch / parse failure — the same shape the retained
    ``poll_until`` fallback consumes.
    """
    returncode, stdout, stderr = github_ops.run_gh(
        ['pr', 'checks', str(pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
    )
    if returncode != 0:
        return False, {'error': f'Failed to get CI status for PR {pr_number}', 'context': stderr.strip()}
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse gh output', 'context': stdout[:100]}
    return True, {'checks': checks}


def cmd_ci_wait(args: argparse.Namespace) -> dict:
    """Handle 'ci wait' — p50-seeded first sleep, then terminal-state watch tail.

    Replaces the fixed-interval ``poll_until`` re-fetch of ``pr checks`` with a
    two-stage, detach-friendly wait:

    1. **p50-seeded first sleep** — sleep once for the historical p50 (median) of
       observed ``ci:wait`` durations (bounded by ``--timeout``, skipped on an
       empty window), so the known-busy window is not polled from second zero.
    2. **terminal-state watch tail** — delegate the tail to ``gh run watch
       --exit-status`` per in-progress run (the purpose-built watch verb, never a
       hand-rolled sleep loop), then re-snapshot the checks once.

    On a natural (non-timeout) SUCCESS completion the observed wall-clock
    duration is recorded back into the p50 window, closing the adaptive loop. The
    external return contract is preserved verbatim: ``final_status``,
    ``duration_sec``, ``failing_checks``, ``wait_outcome``, ``run_id``,
    ``head_sha``, plus the ``deadline_exceeded`` timeout envelope.

    The retained ``poll_until`` fallback covers the edge where CI has not yet
    registered any watchable run (empty checks, or wait-state checks whose links
    carry no resolvable run id) — preserving the pre-change "keep waiting until
    checks appear, then time out" behaviour for repos whose checks lag the wait.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('ci_wait', err)

    start = _monotonic()
    deadline = start + args.timeout
    # Which of the three internal paths actually resolved the wait. Starts at
    # ``seed_only`` — the post-seed snapshot being already terminal is the case
    # where neither the watch tail nor the poll fallback runs.
    mechanism = 'seed_only'

    # 1. p50-seeded first sleep (once, bounded by --timeout, skipped when empty).
    seed = _read_ci_wait_p50_seed()
    if seed is not None:
        _sleep_seed(min(int(seed), args.timeout))

    # 2. Snapshot the checks after the seed sleep.
    ok, data = _fetch_pr_checks(args.pr_number)
    if not ok:
        return make_error('ci_wait', data['error'], data.get('context', ''))
    checks = data['checks']

    # 3. Terminal-state tail. Resolve the still-running runs; when at least one is
    #    watchable, delegate the wait to ``gh run watch`` (one blocking call per
    #    run — NOT a hand-rolled sleep loop) and re-snapshot. Otherwise fall back
    #    to the sanctioned ``poll_until`` framework for the remaining budget.
    _f, wait_rows, _nf = _classify_check_buckets(checks)
    resolvable_run_ids = sorted(
        {
            _extract_run_id_from_link(c.get('link') or '')
            for c in wait_rows
            if _extract_run_id_from_link(c.get('link') or '')
        }
    )
    if wait_rows and resolvable_run_ids:
        for run_id in resolvable_run_ids:
            remaining = int(deadline - _monotonic())
            if remaining <= 0:
                break
            _watch_run(run_id, remaining)
            mechanism = 'watch_tail'
        ok, data = _fetch_pr_checks(args.pr_number)
        if not ok:
            return make_error('ci_wait', data['error'], data.get('context', ''))
        checks = data['checks']
    elif not checks or wait_rows:
        # No watchable run yet (checks empty, or wait-state checks with no
        # resolvable run id). Preserve the pre-change wait-for-checks behaviour
        # via the sanctioned poll_until framework, bounded by the remaining time.
        mechanism = 'poll_fallback'

        def _check_fn() -> tuple[bool, dict]:
            return _fetch_pr_checks(args.pr_number)

        def _is_complete_fn(inner: dict) -> bool:
            rows = inner.get('checks', [])
            if not rows:
                return False
            _fail, waiting, _nonfail = _classify_check_buckets(rows)
            return not waiting

        remaining = max(1, int(deadline - _monotonic()))
        poll_result = github_ops.poll_until(
            _check_fn, _is_complete_fn, timeout=remaining, interval=args.interval
        )
        if 'error' in poll_result:
            return make_error('ci_wait', poll_result['error'], poll_result['last_data'].get('context', ''))
        checks = poll_result['last_data'].get('checks', [])

    duration_sec = max(0, int(_monotonic() - start))
    head_sha = _fetch_pr_head_sha(args.pr_number)
    # ci_wait tracks its own wall-clock duration — use it as the clamp ceiling
    # so an out-of-range aggregate is substituted with the actual wait time.
    check_dicts, total_elapsed = github_ops.format_checks_toon(checks, duration_ceiling=duration_sec)

    # A remaining wait partition after the tail is a timeout: enumerate every
    # still-waiting check as a ``failing_checks`` entry so deliverables 6 and 7
    # can route the timeout into the ``ci-verify-timeout`` producer.
    _f2, wait_rows2, _nf2 = _classify_check_buckets(checks)
    if wait_rows2:
        wait_entries = [_build_failing_check_entry(c) for c in wait_rows2]
        run_ids = sorted({e['run_id'] for e in wait_entries if e['run_id']})
        wait_entries = _enrich_failing_checks(
            wait_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number,
        )
        error_data: dict[str, Any] = {
            'status': 'error',
            'operation': 'ci_wait',
            'error': 'Timeout waiting for CI',
            'pr_number': args.pr_number,
            'duration_sec': duration_sec,
            'last_status': 'pending',
            'wait_outcome': 'deadline_exceeded',
            'failing_checks': wait_entries,
            'run_id': run_ids[0] if run_ids else '',
            'head_sha': head_sha,
        }
        if check_dicts:
            error_data['elapsed_sec'] = total_elapsed
            error_data['checks'] = check_dicts
        record_wait_mechanism(
            plan_id=getattr(args, 'router_plan_id', None),
            consumer='ci-wait',
            wait_mechanism=mechanism,
            dispatch=getattr(args, 'dispatch', 'undeclared'),
            wait_target=f'pr#{args.pr_number}',
            outcome='deadline_exceeded',
        )
        return error_data

    # Natural completion — every check reached a terminal conclusion. Partition
    # and derive the final status; the ``mixed`` outcome no longer exists.
    final_status, failing_rows, _wait_rows = _derive_overall_status(checks)
    failing_checks_entries = [_build_failing_check_entry(c) for c in failing_rows]
    if final_status == 'failure':
        failing_checks_entries = _enrich_failing_checks(
            failing_checks_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number,
        )
    run_ids = sorted(
        {
            _extract_run_id_from_link(c.get('link') or '')
            for c in checks
            if _extract_run_id_from_link(c.get('link') or '')
        }
    )

    # Record the observed wall-clock duration into the p50 window only on a
    # natural SUCCESS completion — the window seeds the next wait's first sleep.
    if final_status == 'success' and duration_sec > 0:
        _record_ci_wait_duration(duration_sec)

    record_wait_mechanism(
        plan_id=getattr(args, 'router_plan_id', None),
        consumer='ci-wait',
        wait_mechanism=mechanism,
        dispatch=getattr(args, 'dispatch', 'undeclared'),
        wait_target=f'pr#{args.pr_number}',
        outcome=final_status,
    )
    return {
        'status': 'success',
        'operation': 'ci_wait',
        'pr_number': args.pr_number,
        'final_status': final_status,
        'duration_sec': duration_sec,
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
        'failing_checks': failing_checks_entries,
        'wait_outcome': 'completed',
        'run_id': run_ids[0] if run_ids else '',
        'head_sha': head_sha,
    }


cmd_ci_rerun = make_simple_handler(
    'ci_rerun',
    lambda args: ['run', 'rerun', str(args.run_id)],
    github_ops.run_gh,
    github_ops.check_auth,
    result_extras=lambda args: {'run_id': args.run_id},
)


def cmd_ci_wait_for_status_flip(args: argparse.Namespace) -> dict:
    """Handle 'ci wait-for-status-flip' — poll until PR CI status flips from pending or timeout.

    Replaces the blocking shell ``sleep`` previously used by workflow-pr-doctor's
    Automated Review Lifecycle. Snapshots the current CI status, then polls on
    the standard CI interval and exits as soon as the status differs from the
    baseline and is no longer ``pending`` (optionally constrained via
    ``--expected`` to ``success`` or ``failure``). Reuses the same ``poll_until``
    helper that powers ``ci wait``.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('ci_wait_for_status_flip', err)

    ok, initial = github_ops._fetch_pr_overall_ci_status(args.pr_number)
    if not ok:
        return make_error(
            'ci_wait_for_status_flip',
            initial.get('error', f'Initial CI status fetch failed for PR {args.pr_number}'),
            initial.get('context', ''),
        )
    baseline = initial

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = github_ops._fetch_pr_overall_ci_status(args.pr_number)
        if not inner_ok:
            return False, data
        return True, {'status': data}

    def is_complete_fn(data: dict) -> bool:
        fresh = data.get('status')
        if fresh == baseline or fresh == 'pending':
            return False
        if args.expected != 'any' and fresh != args.expected:
            return False
        return True

    result = github_ops.poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'ci_wait_for_status_flip',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_status = result['last_data'].get('status', baseline)
    return {
        'status': 'success',
        'operation': 'ci_wait_for_status_flip',
        'pr_number': args.pr_number,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_status': baseline,
        'final_status': final_status,
    }


def _load_filter_log():
    """Lazily import ``filter_log`` from the sibling ``_ci_log_filter`` module.

    Mirrors :func:`ci_base._load_log_filter` so the generic error-context
    heuristic stays stdlib-only and the import is deferred until a failed-run
    log is actually fetched. Returns the ``filter_log`` callable, or ``None``
    when the module is unavailable (caller degrades to the raw stdout).
    """
    try:
        from _ci_log_filter import filter_log
    except ImportError:
        return None
    return filter_log


def cmd_ci_logs(args: argparse.Namespace) -> dict:
    """Handle 'ci logs' subcommand - get failed run logs.

    ``gh run view --log-failed`` already returns failure-only output, but a
    head window drops the failure tail for long logs (runner-setup lines fill
    the first N lines). Route the raw stdout through the generic error-context
    filter (the same ERROR/FAIL/Exception/Traceback context-window heuristic the
    download path uses) so the failure tail is always surfaced.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('ci_logs', err)

    returncode, stdout, stderr = github_ops.run_gh(['run', 'view', str(args.run_id), '--log-failed'], timeout=120)
    if returncode != 0:
        return make_error('ci_logs', f'Failed to get logs for run {args.run_id}', stderr.strip())

    filter_log = _load_filter_log()
    if filter_log is not None:
        filtered = filter_log(stdout, 'generic')
    else:
        filtered = stdout
    filtered_lines = filtered.splitlines()
    content = '\n'.join(filtered_lines).replace(chr(10), '\\n')

    return {
        'status': 'success',
        'operation': 'ci_logs',
        'run_id': args.run_id,
        'log_lines': len(filtered_lines),
        'content': content,
    }
