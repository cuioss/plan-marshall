#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reconcile marshalld after a plugin-cache version bump (meta-project-only).

This meta-repository bumps the plugin-cache version at nearly every plan finalize.
``marshalld`` is version-pinned, so it keeps running the OLD pinned copy with
nothing reconciling it — drifting over time to ``registered``-but-``socket_absent``
(enrolled, believed available, actually dead), after which builds silently fall
back to in-process execution. The drift is a **meta-project phenomenon**: consumer
repositories do not regenerate the executor or bump the cache at finalize, so they
never accumulate the skew. That is why this reconcile lives in the project-local
``sync-plugin-cache`` surface (invoked by ``/sync-plugin-cache`` and the
``finalize-step-sync-plugin-cache`` step) rather than in the shared daemon: **it
changes no shared-daemon behaviour.**

After the sync bumps the cache version, this script queries ``manage-build-server
status`` (through the executor) and applies the D1 idle-conditional contract:

* **idle-and-stale** (running an older binary than the fresh pin, with nothing in
  flight or queued) → ``upgrade`` (drain-then-start-verified);
* **busy-and-stale** (something in flight or queued) → **defer**: leave the daemon
  running, record a readable ``reconcile-owed`` marker, and NEVER drain — the
  in-flight job must survive (draining a live build is the one outcome this gate
  exists to prevent);
* **provenance unknown** (the running binary cannot be determined) → **defer**,
  fail-closed: never drain on a guessed-idle signal;
* **counts unknown** (the daemon reported no in-flight / queued counts — a daemon
  pinned to a copy predating the counts extension omits them) → **defer**, the
  same fail-closed shape: an absent count is not a zero one, and reading it as
  idleness is what drains a live build;
* **already current** (running the fresh pin) → no-op;
* **down but enrolled** (``socket_absent`` / ``unreachable``) → ``start``: the
  daemon is already dead, so a plain start of the verified version, no drain;
* **not enrolled / status unavailable** → silent no-op, so a repository not using
  marshalld (or a session without the executor) is unaffected.

A reconcile verb that RAN is not a verb that WORKED. The result of ``upgrade`` /
``start`` is gated on the fields that can carry a failure — ``drain_exited`` and
``already_running`` — rather than on the verb's own ``status`` word, and only a
confirmed success clears the owed marker. A failed or unverifiable reconcile
writes the marker at ``reason='reconcile_failed'``, so a daemon that was never
actually replaced stays visible instead of being recorded as discharged.

The reconcile action verbs live in the shared ``manage-build-server`` control
skill; this script only READS ``status`` and CALLS ``upgrade`` / ``start`` — it
adds no daemon logic. Every external call is best-effort and fail-open: an absent
executor, a status read failure, or an unreachable control surface all resolve to
a silent no-op rather than aborting the sync.

Usage:
    python3 .claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py
    python3 .claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py --repo-root /path/to/repo
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Reconcile actions (the closed set decide() returns).
ACTION_UPGRADE = 'upgrade'
ACTION_START = 'start'
ACTION_DEFER = 'defer'
ACTION_NOOP = 'noop'

# The readable "reconcile-owed" marker a busy/deferred reconcile leaves behind so a
# daemon that stays stale across several busy syncs is visible without a log scan.
RECONCILE_MARKER_FILENAME = 'reconcile-owed.json'

_MANAGE_BUILD_SERVER = 'plan-marshall:manage-build-server:manage_build_server'
_EXECUTOR_TIMEOUT_SECONDS = 120


@dataclass
class ReconcileDecision:
    """The pure decision: which reconcile action to take and why."""

    action: str
    reason: str


def _count_or_none(value) -> int | None:
    """Return a reported job count as an ``int``, or ``None`` when unknown.

    ``status`` reaches this script as TOON, so a count legitimately arrives as
    either an ``int`` or its decimal string. Anything else — the key absent
    (``None``), the ``'unknown'`` sentinel a daemon-without-counts produces, or
    an unparseable value — is NOT a count, and is reported as such rather than
    coerced to ``0``. ``bool`` is rejected explicitly: it is an ``int`` subclass
    and would otherwise slip through as ``0`` / ``1``.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _as_bool(value) -> bool | None:
    """Return a reported boolean, or ``None`` when it was not reported.

    The mirror of :func:`_count_or_none` for the fields the reconcile gate reads
    off a verb result: a real ``bool`` passes through, a TOON ``'true'`` /
    ``'false'`` string is decoded, and anything else — most importantly an absent
    key — is ``None``, meaning *the verb did not tell us*. That is deliberately
    distinct from ``False``: one is a verb reporting success it can substantiate,
    the other is a verb that cannot.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ('true', 'false'):
        return value.strip().lower() == 'true'
    return None


def decide(status: dict) -> ReconcileDecision:
    """Return the reconcile action for a ``manage-build-server status`` result.

    The pure D1 idle-conditional contract — no I/O. Fails closed toward NOT
    draining a busy or indeterminate daemon: a busy daemon, an unknown running
    provenance, unreported in-flight / queued counts, or an unreadable status all
    resolve to leave-it-running. Idleness must be *reported*, never inferred from
    an absent count — a daemon that never sent one is indistinguishable from an
    idle one, and only one of those is safe to drain.

    Args:
        status: The parsed ``manage-build-server status`` dict.

    Returns:
        The :class:`ReconcileDecision`.
    """
    if not isinstance(status, dict) or status.get('status') != 'success':
        return ReconcileDecision(ACTION_NOOP, 'status_unavailable')
    if not status.get('registered'):
        return ReconcileDecision(ACTION_NOOP, 'not_registered')

    if not bool(status.get('running')):
        # Enrolled but the daemon is down (socket_absent / unreachable): already
        # dead, so a plain start of the verified version — no drain, nothing in
        # flight.
        return ReconcileDecision(ACTION_START, str(status.get('reason') or 'socket_absent'))

    running_binary = str(status.get('running_binary_path', '') or '')
    if running_binary in ('', 'unknown'):
        # Fail-closed: staleness cannot be confirmed, so never drain on a guess.
        return ReconcileDecision(ACTION_DEFER, 'provenance_unknown')
    if not bool(status.get('binary_diverges')):
        return ReconcileDecision(ACTION_NOOP, 'already_current')

    in_flight = _count_or_none(status.get('in_flight'))
    queued = _count_or_none(status.get('queued'))
    if in_flight is None or queued is None:
        # Fail-closed, the same shape as `provenance_unknown` above: a daemon
        # pinned to a copy predating the counts extension omits these keys, and
        # an absent count is NOT a zero one. Reading it as idle is what drains a
        # live build, so a count we were never told defers.
        return ReconcileDecision(ACTION_DEFER, 'counts_unknown')
    if in_flight > 0 or queued > 0:
        # BUSY-and-stale: leave the daemon running; the in-flight job MUST survive.
        return ReconcileDecision(ACTION_DEFER, 'busy')
    return ReconcileDecision(ACTION_UPGRADE, 'idle_and_stale')


# ---------------------------------------------------------------------------
# Reconcile-owed marker (D3 — a deferral is observable, not silent)
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 ``...Z`` string."""
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def _daemon_state_dir() -> Path:
    """Return the machine-global marshalld state dir (mirrors ``home_root()``).

    Resolves ``$PLAN_MARSHALL_HOME`` (else ``~/.plan-marshall``) then ``marshalld``
    — the same resolution ``marketplace_paths.home_root()`` uses — without
    importing the marketplace tree (this is a standalone project-local script).
    """
    home = os.environ.get('PLAN_MARSHALL_HOME') or str(Path.home() / '.plan-marshall')
    return Path(home) / 'marshalld'


def marker_path() -> Path:
    """Return the reconcile-owed marker path."""
    return _daemon_state_dir() / RECONCILE_MARKER_FILENAME


def read_marker(path: Path) -> dict | None:
    """Read the reconcile-owed marker, or ``None`` when absent/unreadable."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_marker(path: Path, marker: dict) -> None:
    """Persist the reconcile-owed marker atomically (best-effort, fail-open).

    A per-pid temp file + ``os.replace`` so a reader never sees a torn document.
    The reconcile runs serially (once per sync), so there is no self-concurrency
    here — this is defence-in-depth hygiene consistent with the D5 streak writer.
    """
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(marker, indent=2), encoding='utf-8')
        os.replace(tmp, path)
    except OSError:
        pass


def clear_marker(path: Path) -> None:
    """Remove the reconcile-owed marker (best-effort, fail-open)."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def reconcile(*, status_reader, action_runner, marker: Path, now: str) -> dict:
    """Run one reconcile cycle and return a summary dict.

    Reads the current status, applies :func:`decide`, and either runs the
    reconcile verb, records a deferral marker, or no-ops — clearing the
    reconcile-owed marker when the daemon is proven current or reconciled, and
    LEAVING it untouched when the status could not be read (indeterminate).

    A verb that ran is not a verb that worked: its result is put through
    :func:`_reconcile_failure`, which reads the fields that can carry a failure
    (``drain_exited`` / ``already_running``) rather than the verb's ``status``
    word. Only a confirmed success clears the marker; a failed or unverifiable
    reconcile reports ``reconcile_result: failed`` and WRITES the marker at
    ``reason='reconcile_failed'``, so the still-stale daemon stays visible
    instead of being marked discharged.

    Args:
        status_reader: Zero-arg callable returning the parsed status dict (``{}``
            on any failure).
        action_runner: One-arg callable ``(action) -> dict`` that runs the
            reconcile verb and returns its parsed result (``{}`` on failure).
        marker: The reconcile-owed marker path.
        now: The current timestamp (injected for determinism).

    Returns:
        A summary dict with ``action``, ``reason``, and observability fields.
    """
    prior = read_marker(marker)
    status = status_reader() or {}
    decision = decide(status)

    summary: dict = {
        'status': 'success',
        'action': decision.action,
        'reason': decision.reason,
        'prior_owed': bool(prior),
    }

    if decision.action in (ACTION_UPGRADE, ACTION_START):
        result = action_runner(decision.action) or {}
        failure_reason = _reconcile_failure(decision.action, result)
        if failure_reason is None:
            summary['reconcile_result'] = str(result.get('status', 'unknown'))
            # The owed reconcile is discharged — and only now, against fields
            # that could have reported the failure.
            clear_marker(marker)
            summary['owed_cleared'] = bool(prior)
        else:
            # The verb did not verifiably reconcile the daemon. Record the debt
            # rather than clearing it: this marker is the only durable trace
            # that the daemon is still stale.
            defer_count = (int(prior.get('defer_count', 0) or 0) if prior else 0) + 1
            summary['reconcile_result'] = 'failed'
            summary['failure_reason'] = failure_reason
            summary['owed'] = True
            summary['defer_count'] = defer_count
            write_marker(
                marker,
                {
                    'owed': True,
                    'reason': 'reconcile_failed',
                    'since': (prior.get('since') if prior else now) or now,
                    'last_deferred': now,
                    'defer_count': defer_count,
                    'failed_action': decision.action,
                    'failure_reason': failure_reason,
                    'running_binary_path': status.get('running_binary_path'),
                    'resolved_binary_path': status.get('resolved_binary_path'),
                    'in_flight': status.get('in_flight'),
                    'queued': status.get('queued'),
                },
            )
    elif decision.action == ACTION_DEFER:
        defer_count = (int(prior.get('defer_count', 0) or 0) if prior else 0) + 1
        write_marker(
            marker,
            {
                'owed': True,
                'reason': decision.reason,
                'since': (prior.get('since') if prior else now) or now,
                'last_deferred': now,
                'defer_count': defer_count,
                'running_binary_path': status.get('running_binary_path'),
                'resolved_binary_path': status.get('resolved_binary_path'),
                'in_flight': status.get('in_flight'),
                'queued': status.get('queued'),
            },
        )
        summary['owed'] = True
        summary['defer_count'] = defer_count
    else:  # noop
        if decision.reason == 'status_unavailable':
            # Indeterminate — never discard a genuine owed marker on a blind read.
            summary['owed'] = bool(prior)
        elif prior:
            # Daemon is current / no longer enrolled — the owed reconcile is moot.
            clear_marker(marker)
            summary['owed_cleared'] = True

    summary['display_detail'] = _display_detail(summary)
    return summary


def _reconcile_failure(action: str, result: dict) -> str | None:
    """Return why the reconcile verb failed, or ``None`` when it verifiably succeeded.

    Gates on the fields that can actually CARRY a failure rather than on the
    verb's own ``status`` word, which ``upgrade`` once hard-coded to ``success``
    regardless of outcome:

    * ``already_running`` (both verbs) — the start half found a daemon still up.
      Neither verb may treat that as an idempotent no-op here: ``upgrade`` had
      just drained the daemon it found, and ``start`` was chosen only because the
      status said the daemon was **down**. Either way the world disagrees with
      the decision that was made, so the reconcile is not confirmed.
    * ``drain_exited`` (``upgrade`` only) — the old daemon never exited, so the
      process the upgrade meant to replace is still running.

    A verb reporting NEITHER field cannot substantiate its own success, and is
    treated as a failure: an unverifiable success is exactly the report this gate
    exists to stop.

    The fail-open ``{}`` an unreachable executor produces is caught EARLIER and
    by a different arm — it carries no ``status`` word, so the status check above
    rejects it as ``verb_reported_nothing`` before either field is consulted. The
    two are separate reasons, not one: reading them as a single case is what let
    the ``{}`` route go untested while a comment claimed it covered.

    Args:
        action: The reconcile action that was run (``upgrade`` or ``start``).
        result: The verb's parsed result dict (``{}`` when the call failed).

    Returns:
        A short failure reason, or ``None`` when the reconcile is confirmed.
    """
    status_word = str(result.get('status', '') or '')
    if status_word != 'success':
        return f'verb_reported_{status_word or "nothing"}'

    already_running = _as_bool(result.get('already_running'))
    if already_running is None:
        return 'already_running_absent'
    if already_running:
        return 'daemon_already_running'

    if action == ACTION_UPGRADE:
        drain_exited = _as_bool(result.get('drain_exited'))
        if drain_exited is None:
            return 'drain_exited_absent'
        if not drain_exited:
            return 'drain_did_not_exit'
    return None


def _display_detail(summary: dict) -> str:
    """Render a one-line operator detail from a reconcile summary."""
    action = summary['action']
    reason = summary['reason']
    if summary.get('reconcile_result') == 'failed':
        count = summary.get('defer_count', 1)
        return (
            f'reconcile FAILED ({summary.get("failure_reason", "unknown")}) running '
            f'{action} — daemon NOT confirmed reconciled; owed marker written (x{count})'
        )
    if action == ACTION_UPGRADE:
        return 'daemon idle-and-stale — reconciled via upgrade (drain-then-start-verified)'
    if action == ACTION_START:
        return f'daemon down but enrolled ({reason}) — started the verified version'
    if action == ACTION_DEFER:
        count = summary.get('defer_count', 1)
        return f'daemon {reason} — reconcile deferred (owed x{count}); daemon left running'
    return f'no reconcile needed ({reason})'


# ---------------------------------------------------------------------------
# Executor adapters (thin, fail-open) + TOON parsing
# ---------------------------------------------------------------------------


def _import_parse_toon():
    """Import the shared ``parse_toon`` helper from the marketplace tree, or None.

    Mirrors ``sync.py``'s path-hack import: this standalone script has no
    marketplace package on ``sys.path``, so the repo root is resolved from the
    script's own location (``.claude/skills/sync-plugin-cache/scripts`` → four
    parents up) and the ref-toon-format scripts dir is prepended before import.
    Returns ``None`` on any failure so the caller fails open.
    """
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[4]
    toon_scripts = (
        repo_root / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
        / 'ref-toon-format' / 'scripts'
    )
    if str(toon_scripts) not in sys.path:
        sys.path.insert(0, str(toon_scripts))
    try:
        from toon_parser import parse_toon  # noqa: E402

        return parse_toon
    except Exception:  # noqa: BLE001 — fail open: no parser → no reconcile
        return None


def _parse_status(text: str) -> dict:
    """Parse a ``manage-build-server`` TOON payload into a dict, or ``{}``."""
    parse_toon = _import_parse_toon()
    if parse_toon is None:
        return {}
    try:
        parsed = parse_toon(text)
    except Exception:  # noqa: BLE001 — unparseable output fails open to no-op
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _invoke_executor(verb: str, repo_root: Path) -> dict:
    """Run ``manage-build-server {verb}`` via the executor and parse its TOON.

    Fails open to ``{}`` when the executor is absent (a repository not using
    marshalld, or a session without a generated executor), the subprocess errors,
    or the output does not parse — so the reconcile is a silent no-op there.
    """
    executor = repo_root / '.plan' / 'execute-script.py'
    if not executor.is_file():
        return {}
    cmd = ['python3', str(executor), _MANAGE_BUILD_SERVER, verb]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=_EXECUTOR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if completed.returncode != 0:
        return {}
    return _parse_status(completed.stdout)


def _emit_toon(summary: dict) -> str:
    """Serialize the flat summary dict to a simple ``key: value`` TOON block."""
    lines = []
    for key, value in summary.items():
        if isinstance(value, bool):
            rendered = 'true' if value else 'false'
        else:
            rendered = str(value)
        lines.append(f'{key}: {rendered}')
    return '\n'.join(lines) + '\n'


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Reconcile marshalld after a plugin-cache version bump (meta-project-only).',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--repo-root',
        type=Path,
        default=None,
        help='Repository root holding .plan/execute-script.py (default: cwd).',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point — run one reconcile cycle and print its TOON summary."""
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = (args.repo_root or Path.cwd()).resolve()
    try:
        summary = reconcile(
            status_reader=lambda: _invoke_executor('status', repo_root),
            action_runner=lambda action: _invoke_executor(action, repo_root),
            marker=marker_path(),
            now=_utc_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001 — the reconcile must never abort the sync
        summary = {
            'status': 'success',
            'action': ACTION_NOOP,
            'reason': 'reconcile_error',
            'display_detail': f'reconcile skipped (non-fatal): {exc}',
        }
    sys.stdout.write(_emit_toon(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
