#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Sonar workflow operations - two-verb provider contract: fetch_findings + post_responses.

The provider surface is exactly TWO pure, zero-LLM verbs — no triage judgment
lives here:

- ``fetch_findings`` is the single authority on new-code issue enumeration. It
  performs a synchronous bounded in-Python CE-readiness wait (poll the
  Compute-Engine task state until the PR analysis is DONE, or until the wait
  budget expires), then enumerates the PR-scoped new-code issues, applies the
  keyword pre-filter from ``standards/sonar-rules.json`` (drops issues already
  suppressable via NOSONAR / test-acceptable rules) and files one ``sonar-issue``
  finding per surviving issue. The untrusted Sonar ``message`` is quarantined
  under ``raw_input.{message}`` — never embedded raw in the top-level ``detail``
  — and promoted only by the batched ``manage-findings ingest`` pass.
- ``post_responses`` applies already-decided triage dispositions back to Sonar
  — a ``do_transition`` dismissal (``wontfix`` for ``suppressed``,
  ``falsepositive`` for ``rejected``) — keyed by each finding's own ``hash_id``.
  It makes NO triage decision.

Both verbs FAIL LOUD when Sonar is not configured: a typed ``unconfigured``
status, never a silent success.

The returned contract carries a verified ``new_code_issue_count`` and a
``count_status`` discriminator (``confirmed`` | ``undecidable``): a confirmed
CE-DONE run reports the real PR-scoped count; a CE-still-processing-at-timeout
or an auth/REST failure reports ``new_code_issue_count: null`` with
``count_status: undecidable`` and a ``count_status_reason`` — NEVER a false
``0``. Every fetch also writes one attestation row to
``artifacts/findings/sonar-scan-summary.jsonl`` (written even at count==0 and
on undecidable) so an absent file can never be confused with "not checked."

LLM consumers query findings via ``manage-findings query --type sonar-issue``.

Usage:
    sonar.py fetch_findings --plan-id <P> --project <key> [--pr <id>] [--severities <list>] [--types <list>] [--ce-wait-timeout <secs>]
    sonar.py post_responses --plan-id <P> --project <key>
    sonar.py --help
"""

import re
import sys
from datetime import UTC, datetime
from typing import Any

from ci_base import (
    extract_routing_args,
    poll_until,
    register_subcommands,
    set_default_cwd,
)
from triage_helpers import (
    create_workflow_cli,
    is_test_file,
    load_skill_config,
    safe_main,
)

# Register this script's top-level subcommand tokens so that extract_routing_args
# correctly identifies the subcommand boundary when sonar.py is the entry point
# (i.e., does not consume a subcommand-level --plan-id as a router flag).
register_subcommands({'fetch_findings', 'post_responses'})

# Sonar skill name used to resolve the credential/config store.
_SONAR_SKILL = 'workflow-integration-sonar'

# Terminal triage dispositions that map to a Sonar dismissal, and the transition
# each applies via /api/issues/do_transition. `fixed`/`accepted`/
# `taken_into_account` intentionally have NO Sonar action — the issue is fixed in
# code (cleared on the next scan) or accepted, not dismissed.
_SONAR_DISMISS_TRANSITIONS = {'suppressed': 'wontfix', 'rejected': 'falsepositive'}

# ============================================================================
# PRE-FILTER CONFIGURATION (loaded from sonar-rules.json)
# ============================================================================
#
# sonar-rules.json is a PRE-FILTER for the producer-side ``fetch-and-store``
# flow. Suppressable rules and test-acceptable rules are dropped before
# findings are written so the per-type store contains only issues the LLM
# needs to act on. Severity priority and type-boost mappings are retained as
# Python-internal helpers used to derive the finding ``severity`` field.

_RULES_CONFIG = load_skill_config(__file__, 'sonar-rules.json')

SUPPRESSABLE_RULES: dict[str, str] = _RULES_CONFIG.get('suppressable_rules', {})
SEVERITY_PRIORITY: dict[str, str] = _RULES_CONFIG.get('severity_priority', {})
_TEST_ACCEPTABLE_RULES: set[str] = set(_RULES_CONFIG.get('test_acceptable_rules', []))
_ALWAYS_FIX_TYPES: dict[str, str] = _RULES_CONFIG.get('always_fix_types', {})

# CE-readiness wait defaults. The budget is resolved per-call from the
# plan-local manifest step-params snapshot for ``default:sonar-roundtrip`` (the
# prefix-stripped ``ce_wait_timeout_seconds`` param; default 600, the direct
# sibling of ``checks_wait_timeout_seconds``), overridable by an explicit
# ``--ce-wait-timeout`` flag. The poll interval mirrors the CI poll cadence used
# by ``tools-integration-ci`` (DEFAULT_CI_INTERVAL = 30s).
_CE_WAIT_DEFAULT_TIMEOUT = 600
_CE_WAIT_INTERVAL = 30

# In-manifest (bare) step id for the Sonar roundtrip step. The composer strips
# the ``default:`` prefix at the compose boundary, so the manifest snapshot is
# keyed by the bare name.
_SONAR_ROUNDTRIP_STEP_ID = 'sonar-roundtrip'


def _read_manifest_sonar_params(plan_id: str) -> dict[str, Any]:
    """Read the ``default:sonar-roundtrip`` step's snapshotted params from the manifest.

    Reads the plan-local execution manifest (``.plan/local/plans/{plan_id}/
    execution.toon``) and returns the prefix-stripped param object snapshotted
    under ``phase_6.step_params['sonar-roundtrip']`` — the single one-stop read
    for the Sonar roundtrip's ``touched_file_cleanup`` / ``do_transition`` /
    ``ce_wait_timeout_seconds`` params. Returns an empty dict when the manifest is
    missing, malformed, or carries no snapshot for the step. Never raises — a
    missing manifest falls back to defaults so the CLI stays usable outside a
    composed plan.
    """
    try:
        from file_ops import get_plan_dir
        from toon_parser import parse_toon
    except Exception:
        return {}
    try:
        manifest_path = get_plan_dir(plan_id) / 'execution.toon'
        if not manifest_path.exists():
            return {}
        manifest = parse_toon(manifest_path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    if not isinstance(manifest, dict):
        return {}
    phase_6 = manifest.get('phase_6', {})
    step_params = phase_6.get('step_params', {}) if isinstance(phase_6, dict) else {}
    if not isinstance(step_params, dict):
        return {}
    params = step_params.get(_SONAR_ROUNDTRIP_STEP_ID, {})
    return params if isinstance(params, dict) else {}

# CE task states that mean "analysis has settled" (the issue store on the
# server is now consistent for the PR). PENDING / IN_PROGRESS mean the engine
# is still processing and the issue set may be incomplete.
_CE_DONE_STATES = {'SUCCESS', 'FAILED', 'CANCELED'}


# ============================================================================
# PRE-FILTER (Python-internal helper)
# ============================================================================


def _is_suppressable(rule: str, file: str, issue_type: str) -> bool:
    """Pre-filter: True if the issue is one we already know how to suppress.

    Drops:
    - Rules listed in ``suppressable_rules`` (already documented as suppressable).
    - Test-file issues whose rule appears in ``test_acceptable_rules``.

    Always-fix types (VULNERABILITY, SECURITY_HOTSPOT, BLOCKER severity) are
    NEVER suppressed at the pre-filter stage — they always pass through to
    the finding store regardless of rule.
    """
    if issue_type in _ALWAYS_FIX_TYPES:
        return False
    if rule in SUPPRESSABLE_RULES:
        return True
    if is_test_file(file) and rule in _TEST_ACCEPTABLE_RULES:
        return True
    return False


def _map_severity(sonar_severity: str) -> str | None:
    """Map a Sonar issue severity (BLOCKER/CRITICAL/...) to the finding store's
    severity vocabulary (``error``/``warning``/``info``).

    BLOCKER/CRITICAL/MAJOR -> error, MINOR -> warning, INFO -> info. Unknown
    severities map to None so the finding is written without a severity field.
    """
    s = (sonar_severity or '').upper()
    if s in ('BLOCKER', 'CRITICAL', 'MAJOR'):
        return 'error'
    if s == 'MINOR':
        return 'warning'
    if s == 'INFO':
        return 'info'
    return None


# ============================================================================
# CE-READINESS WAIT (synchronous, bounded, in-Python — NOT a shell loop)
# ============================================================================


def _resolve_ce_wait_timeout(args, sonar_params: dict[str, Any] | None = None) -> int:
    """Resolve the CE-readiness wait budget in seconds.

    Resolution order (first match wins):
    1. Explicit ``--ce-wait-timeout`` flag (argparse-supplied, always wins).
    2. The prefix-stripped ``ce_wait_timeout_seconds`` param from the plan-local
       manifest step-params snapshot for ``default:sonar-roundtrip`` (read once
       by the caller and passed in via ``sonar_params``).
    3. The conservative 600s fallback.

    Never raises — a missing / malformed snapshot falls back to 600s so the CLI
    remains usable outside a composed plan (mirrors ci_base's
    ``_resolve_ci_timeout``).
    """
    explicit = getattr(args, 'ce_wait_timeout', None)
    if isinstance(explicit, int) and explicit > 0:
        return explicit

    params = sonar_params or {}
    value = params.get('ce_wait_timeout_seconds')
    if isinstance(value, int) and value > 0:
        return value
    return _CE_WAIT_DEFAULT_TIMEOUT


def _poll_ce_status(project: str, pr: str | None) -> tuple[bool, dict[str, Any]]:
    """One CE-status poll against ``/api/ce/component`` (+ ``/api/ce/activity``).

    Returns ``(ok, data)`` for the ``poll_until`` framework. ``ok`` is False on
    a REST/auth failure (poll_until propagates the error immediately). On
    success ``data`` carries ``ce_state`` (the current task status string) and
    ``queue_length`` (number of still-queued tasks for the component).
    """
    from _providers_core import (
        RestClientError,
        get_authenticated_client,
    )

    client = get_authenticated_client('workflow-integration-sonar')
    component_params: dict[str, str] = {'component': project}
    if pr:
        component_params['pullRequest'] = pr
    try:
        component = client.get('/api/ce/component', params=component_params)
        client.close()
    except RestClientError as e:
        return False, {'error': f'Sonar API error: HTTP {e.status}'}

    current = component.get('current', {}) or {}
    queue = component.get('queue', []) or []
    return True, {
        'ce_state': (current.get('status', '') or '').upper(),
        'queue_length': len(queue),
    }


def _wait_for_ce_ready(project: str, pr: str | None, timeout: int) -> dict[str, Any]:
    """Synchronous bounded CE-readiness wait.

    Polls ``/api/ce/component`` via the ``poll_until`` framework until the
    component's current CE task reaches a settled state (SUCCESS / FAILED /
    CANCELED) AND no tasks remain queued, or the budget expires.

    Returns a dict carrying:
    - ``count_status``: ``confirmed`` when CE settled in budget; ``undecidable``
      when the wait timed out or a REST/auth failure occurred.
    - ``count_status_reason``: human-readable reason, present only on
      ``undecidable``.
    """

    def _check() -> tuple[bool, dict[str, Any]]:
        return _poll_ce_status(project, pr)

    def _is_ready(data: dict[str, Any]) -> bool:
        return data.get('ce_state') in _CE_DONE_STATES and data.get('queue_length', 0) == 0

    result = poll_until(_check, _is_ready, timeout=timeout, interval=_CE_WAIT_INTERVAL)

    if result.get('error'):
        return {
            'count_status': 'undecidable',
            'count_status_reason': f'CE-status poll failed: {result["error"]}',
        }
    if result.get('timed_out'):
        last = result.get('last_data', {}) or {}
        ce_state = last.get('ce_state') or 'unknown'
        return {
            'count_status': 'undecidable',
            'count_status_reason': (
                f'CE analysis not DONE within {timeout}s '
                f'(last state={ce_state}, queue={last.get("queue_length", "?")})'
            ),
        }
    return {'count_status': 'confirmed'}


# ============================================================================
# SCAN-SUMMARY MARKER (verified-scan attestation, D5 producer side)
# ============================================================================


def _resolve_scanned_sha() -> str:
    """Best-effort resolve the worktree HEAD SHA the scan attests to.

    Returns the empty string when the SHA cannot be resolved (not a git tree,
    git unavailable) — the marker row is still written; ``scanned_sha`` is
    simply blank.
    """
    import subprocess

    try:
        out = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return ''


def _write_scan_summary(
    plan_id: str,
    project: str,
    pr: str | None,
    count_status: str,
    new_code_issue_count: int | None,
    count_status_reason: str | None,
) -> str:
    """Append one attestation row to ``artifacts/findings/sonar-scan-summary.jsonl``.

    Written unconditionally for every fetch — including at count==0 and on
    ``undecidable`` — so a verified zero is a positive on-disk fact and an
    absent file unambiguously means "not checked." Reuses the shared
    findings-dir resolver (``_findings_core.get_findings_dir``) so the file
    lands in the same archive-surviving directory as ``pr-comment.jsonl``.

    Returns the absolute path of the written file, or an empty string when a
    filesystem failure (full disk, permission error) prevents the write — the
    graceful-degradation path so the caller's verified-scan gate fails closed
    instead of crashing the fetch.
    """
    import json

    from _findings_core import get_findings_dir

    row: dict[str, Any] = {
        'count_status': count_status,
        'new_code_issue_count': new_code_issue_count,
        'pr': pr,
        'project': project,
        'scanned_sha': _resolve_scanned_sha(),
        'ts': datetime.now(UTC).isoformat(),
    }
    if count_status_reason:
        row['count_status_reason'] = count_status_reason

    # Marker-write I/O failure (full disk, permission error) MUST degrade
    # gracefully: returning '' signals "marker not written" so the
    # sonar-roundtrip caller's verified-scan gate fails closed rather than
    # crashing cmd_fetch_and_store with an unhandled exception (which the
    # caller would misroute as "Sonar not configured").
    try:
        findings_dir = get_findings_dir(plan_id)
        findings_dir.mkdir(parents=True, exist_ok=True)
        marker_path = findings_dir / 'sonar-scan-summary.jsonl'
        with marker_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(row) + '\n')
    except OSError:
        return ''

    return str(marker_path)


# ============================================================================
# FAIL-LOUD CONFIG GUARD (shared by fetch_findings + post_responses)
# ============================================================================


def _sonar_unconfigured(operation: str, detail: str) -> dict[str, Any]:
    """Build the typed ``unconfigured`` fail-loud signal for a Sonar verb.

    Returned when no Sonar credential is configured, so a caller can distinguish
    "Sonar not set up" from a genuine zero-findings success instead of a silent no-op.
    """
    return {
        'status': 'unconfigured',
        'operation': operation,
        'provider': 'sonar',
        'detail': detail,
    }


def _sonar_credential_missing() -> str:
    """Return a fail-loud reason string when no Sonar credential is configured, else ''.

    Never raises — a resolver/import failure is treated as "configured" so the
    downstream REST call surfaces the real error rather than a false unconfigured.
    """
    try:
        from _providers_core import load_credential

        credential = load_credential(_SONAR_SKILL, 'auto')
    except Exception:
        return ''
    if not credential:
        return f'No credentials configured for {_SONAR_SKILL}. Run: credentials configure --skill {_SONAR_SKILL}'
    return ''


# ============================================================================
# FETCH_FINDINGS SUBCOMMAND (producer-side fetch + filter + file to ledger)
# ============================================================================


def _fetch_issues(project: str, pr: str | None, severities: str | None, types: str | None) -> dict[str, Any]:
    """Fetch PR-scoped new-code issues via the Sonar REST client.

    Mirrors ``sonar_rest.cmd_search`` issue extraction so the producer-side
    flow does not depend on a subprocess call into another skill script. When
    ``pr`` is set the query is PR-decoration-scoped and ``inNewCodePeriod=true``
    enumerates only the new-code issues, so a reported ``0`` is a confirmed
    PR-scoped zero rather than an inferred one.
    """
    from _providers_core import (
        RestClientError,
        get_authenticated_client,
    )

    client = get_authenticated_client('workflow-integration-sonar')
    params: dict[str, str] = {
        'projects': project,
        'ps': '500',
        'inNewCodePeriod': 'true',
        'resolved': 'false',
    }
    if pr:
        params['pullRequest'] = pr
    if severities:
        params['severities'] = severities
    if types:
        params['types'] = types

    try:
        result = client.get('/api/issues/search', params=params)
        client.close()
    except RestClientError as e:
        return {'status': 'error', 'message': f'Sonar API error: HTTP {e.status}'}

    issues = result.get('issues', [])
    formatted: list[dict[str, Any]] = []
    for issue in issues:
        formatted.append(
            {
                'key': issue.get('key', ''),
                'type': issue.get('type', ''),
                'severity': issue.get('severity', ''),
                'file': issue.get('component', '').split(':')[-1],
                'line': issue.get('line', 0),
                'rule': issue.get('rule', ''),
                'message': issue.get('message', ''),
                'component': issue.get('component', ''),
            }
        )

    return {'status': 'success', 'issues': formatted}


def cmd_fetch_findings(args):
    """Producer-side FIND verb: PR-scoped new-code issue enumeration → ledger.

    Flow:
    1. Synchronous bounded CE-readiness wait (poll ``ce-status`` until DONE or
       ``ce_wait_timeout_seconds`` expiry) — confirms the server's issue
       set is consistent for the PR before enumerating.
    2. Fetch the PR-scoped new-code issues and pre-filter the suppressable ones.
    3. File one ``sonar-issue`` finding per surviving issue — the untrusted
       Sonar ``message`` quarantined under ``raw_input.{message}``, the trusted
       structured metadata in ``detail``.
    4. Compute the verified ``new_code_issue_count`` and the ``count_status``
       discriminator (``confirmed`` | ``undecidable``).
    5. Write one ``sonar-scan-summary.jsonl`` attestation row (unconditional).

    Fail-loud: returns a typed ``unconfigured`` status when no Sonar credential
    is configured. On CE-timeout OR auth/REST failure the returned dict carries
    ``new_code_issue_count: null`` and ``count_status: undecidable`` with a
    ``count_status_reason`` — NEVER a false ``0``.
    """
    from _findings_core import (
        add_finding,
        add_qgate_finding,
    )

    plan_id: str = args.plan_id
    project: str = args.project
    pr: str | None = getattr(args, 'pr', None)

    # Fail-loud config guard — an unconfigured provider must NOT report a silent
    # zero-findings success.
    missing = _sonar_credential_missing()
    if missing:
        return _sonar_unconfigured('fetch_findings', missing)

    # Read the default:sonar-roundtrip step's params from the plan-local manifest
    # snapshot in a single one-stop call.
    sonar_params = _read_manifest_sonar_params(plan_id)

    # 1. Synchronous CE-readiness wait — gate the count on a settled analysis.
    ce_timeout = _resolve_ce_wait_timeout(args, sonar_params)
    ce_result = _wait_for_ce_ready(project, pr, ce_timeout)

    if ce_result['count_status'] == 'undecidable':
        # CE never settled (timeout) or the poll failed (auth/REST). Do NOT
        # enumerate — a count taken against an in-flight analysis would be
        # unreliable. Report undecidable and write the attestation marker.
        reason = ce_result.get('count_status_reason')
        marker_path = _write_scan_summary(
            plan_id=plan_id,
            project=project,
            pr=pr,
            count_status='undecidable',
            new_code_issue_count=None,
            count_status_reason=reason,
        )
        return {
            'status': 'success',
            'plan_id': plan_id,
            'project': project,
            'pull_request': pr or 'none',
            'count_fetched': 0,
            'count_skipped_suppressable': 0,
            'count_stored': 0,
            'stored_hash_ids': [],
            'producer_mismatch_hash_id': None,
            'new_code_issue_count': None,
            'count_status': 'undecidable',
            'count_status_reason': reason,
            'scan_summary_path': marker_path,
        }

    # 2. Fetch PR-scoped new-code issues.
    fetch_result = _fetch_issues(project, pr, getattr(args, 'severities', None), getattr(args, 'types', None))
    if fetch_result.get('status') != 'success':
        # Auth/REST failure during fetch — undecidable, never a false 0.
        reason = fetch_result.get('message', 'Sonar issue fetch failed')
        marker_path = _write_scan_summary(
            plan_id=plan_id,
            project=project,
            pr=pr,
            count_status='undecidable',
            new_code_issue_count=None,
            count_status_reason=reason,
        )
        fetch_result['new_code_issue_count'] = None
        fetch_result['count_status'] = 'undecidable'
        fetch_result['count_status_reason'] = reason
        fetch_result['scan_summary_path'] = marker_path
        return fetch_result

    raw_issues: list[dict[str, Any]] = fetch_result.get('issues', []) or []
    count_fetched = len(raw_issues)

    stored_hashes: list[str] = []
    skipped_suppressable = 0
    store_failures: list[str] = []

    for issue in raw_issues:
        rule = issue.get('rule', '')
        file_path = issue.get('file', '') or None
        issue_type = issue.get('type', 'CODE_SMELL')

        if _is_suppressable(rule, file_path or '', issue_type):
            skipped_suppressable += 1
            continue

        severity = _map_severity(issue.get('severity', ''))
        component = issue.get('component') or None
        line = issue.get('line') or None
        line_arg: int | None = None
        if isinstance(line, int) and line > 0:
            line_arg = line

        title = f'Sonar {rule} in {file_path or "(unknown)"} (key={issue.get("key", "")})'

        # Only trusted, producer-built structured metadata goes in ``detail``;
        # the untrusted Sonar ``message`` is quarantined under
        # ``raw_input.{message}`` so the triage read surface never sees
        # un-validated free-text until the batched ingestion pass promotes it.
        detail_lines = [
            f'key: {issue.get("key", "")}',
            f'rule: {rule}',
            f'sonar_severity: {issue.get("severity", "")}',
            f'sonar_type: {issue_type}',
            f'project: {project}',
        ]
        if pr:
            detail_lines.append(f'pull_request: {pr}')
        if component:
            detail_lines.append(f'component: {component}')
        if file_path:
            detail_lines.append(f'file: {file_path}')
        if line_arg:
            detail_lines.append(f'line: {line_arg}')
        detail = '\n'.join(detail_lines)

        add_result = add_finding(
            plan_id=plan_id,
            finding_type='sonar-issue',
            title=title,
            detail=detail,
            file_path=file_path,
            line=line_arg,
            component=component,
            module=project,
            rule=rule,
            severity=severity,
            raw_input={'message': issue.get('message', '')},
        )
        if add_result.get('status') == 'success':
            stored_hashes.append(add_result.get('hash_id', ''))
        else:
            store_failures.append(issue.get('key', ''))

    count_stored = len(stored_hashes)
    expected_stored = count_fetched - skipped_suppressable

    qgate_hash: str | None = None
    if count_stored != expected_stored:
        mismatch_detail = (
            f'count_fetched={count_fetched}, '
            f'count_skipped_suppressable={skipped_suppressable}, '
            f'count_stored={count_stored}, '
            f'expected_stored={expected_stored}, '
            f'failed_issue_keys={store_failures}'
        )
        qgate_result = add_qgate_finding(
            plan_id=plan_id,
            phase='5-execute',
            source='qgate',
            finding_type='sonar-issue',
            title=f'(producer-mismatch) sonar fetch_findings project={project}',
            detail=mismatch_detail,
        )
        qgate_hash = qgate_result.get('hash_id')

    # 4. Verified count: the confirmed PR-scoped new-code issue total. The
    #    authoritative count is over the fetched new-code issues (the REST
    #    query already scopes to PR + inNewCodePeriod + unresolved), so a
    #    reported 0 here is a confirmed PR-scoped zero.
    new_code_issue_count = count_fetched

    # 5. Write the verified-scan attestation marker (unconditional, even at 0).
    marker_path = _write_scan_summary(
        plan_id=plan_id,
        project=project,
        pr=pr,
        count_status='confirmed',
        new_code_issue_count=new_code_issue_count,
        count_status_reason=None,
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'project': project,
        'pull_request': pr or 'none',
        'count_fetched': count_fetched,
        'count_skipped_suppressable': skipped_suppressable,
        'count_stored': count_stored,
        'stored_hash_ids': stored_hashes,
        'producer_mismatch_hash_id': qgate_hash,
        'new_code_issue_count': new_code_issue_count,
        'count_status': 'confirmed',
        'scan_summary_path': marker_path,
    }


# ============================================================================
# POST_RESPONSES SUBCOMMAND (apply triaged dispositions back to Sonar)
# ============================================================================

_ISSUE_KEY_DETAIL = re.compile(r'^key:[ \t]*(?P<key>\S[^\n]*?)[ \t]*$', re.MULTILINE)


def _issue_key_from_detail(detail: str | None) -> str:
    """Extract the Sonar issue ``key`` from a sonar-issue finding's detail block."""
    match = _ISSUE_KEY_DETAIL.search(detail or '')
    return match.group('key') if match else ''


def cmd_post_responses(args):
    """RESPOND verb: apply already-decided triage dispositions back to Sonar.

    Reads every ``sonar-issue`` finding whose ``resolution`` maps to a Sonar
    dismissal (``suppressed`` → ``wontfix``, ``rejected`` → ``falsepositive``)
    and — keyed by each finding's own issue ``key`` (parsed from its structured
    ``detail``; relational, never positional) — POSTs ``/api/issues/do_transition``.
    Findings resolved to ``fixed`` / ``accepted`` / ``taken_into_account`` get NO
    Sonar action (the issue is fixed in code or accepted). This verb makes NO
    triage decision.

    Fail-loud: returns a typed ``unconfigured`` status when no Sonar credential
    is configured.
    """
    from _findings_core import query_findings

    plan_id: str = args.plan_id

    missing = _sonar_credential_missing()
    if missing:
        return _sonar_unconfigured('post_responses', missing)

    from _providers_core import (
        RestClientError,
        get_authenticated_client,
    )

    findings = query_findings(plan_id, finding_type='sonar-issue').get('findings') or []

    responded: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    client = get_authenticated_client(_SONAR_SKILL)
    try:
        for finding in findings:
            hash_id = finding.get('hash_id', '')
            transition = _SONAR_DISMISS_TRANSITIONS.get(finding.get('resolution', ''))
            if transition is None:
                continue

            issue_key = _issue_key_from_detail(finding.get('detail'))
            if not issue_key:
                skipped.append({'hash_id': hash_id, 'reason': 'no issue key in detail'})
                continue

            try:
                client.post('/api/issues/do_transition', body={'issue': issue_key, 'transition': transition})
            except RestClientError as exc:
                failures.append({'hash_id': hash_id, 'issue_key': issue_key, 'error': f'HTTP {exc.status}'})
                continue
            responded.append({'hash_id': hash_id, 'issue_key': issue_key, 'transition': transition})
    finally:
        client.close()

    return {
        'status': 'success',
        'operation': 'post_responses',
        'provider': 'sonar',
        'plan_id': plan_id,
        'count_responded': len(responded),
        'count_skipped': len(skipped),
        'count_failed': len(failures),
        'responded': responded,
        'skipped': skipped,
        'failures': failures,
    }


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    # Accept (and swallow) a top-level --plan-id / --project-dir pair for API
    # uniformity with the github/gitlab workflow scripts. The Sonar REST
    # client does not use cwd; the routing is preserved so future subprocess
    # additions remain configurable. Two-state contract: --plan-id auto-
    # resolves via manage-status; --project-dir is the explicit override;
    # both together is a hard error.
    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = create_workflow_cli(
        description='Sonar workflow operations',
        epilog="""
Examples:
  sonar.py fetch_findings --plan-id EXAMPLE-PLAN --project com.example:project
  sonar.py fetch_findings --plan-id EXAMPLE-PLAN --project com.example:project --pr 123 --severities BLOCKER,CRITICAL
  sonar.py fetch_findings --plan-id EXAMPLE-PLAN --project com.example:project --pr 123 --ce-wait-timeout 300
  sonar.py post_responses --plan-id EXAMPLE-PLAN --project com.example:project
""",
        subcommands=[
            {
                'name': 'fetch_findings',
                'help': 'FIND: CE-readiness wait + fetch + pre-filter + file one sonar-issue finding per surviving issue (message quarantined under raw_input)',
                'handler': cmd_fetch_findings,
                'args': [
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                    {'flags': ['--project'], 'required': True, 'help': 'SonarQube project key'},
                    {'flags': ['--pr'], 'help': 'Pull request ID — scopes the CE-status lookup and new-code enumeration'},
                    {'flags': ['--severities'], 'help': 'Filter by severity (comma-separated)'},
                    {'flags': ['--types'], 'help': 'Filter by type (comma-separated)'},
                    {
                        'flags': ['--ce-wait-timeout'],
                        'dest': 'ce_wait_timeout',
                        'type': int,
                        'help': 'Override the CE-readiness wait budget in seconds (default: the '
                        'manifest step-params snapshot ce_wait_timeout_seconds for '
                        'default:sonar-roundtrip, else 600)',
                    },
                ],
            },
            {
                'name': 'post_responses',
                'help': 'RESPOND: apply triaged dismissals (wontfix/falsepositive) back to Sonar, keyed by hash_id',
                'handler': cmd_post_responses,
                'args': [
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                    {'flags': ['--project'], 'required': False, 'help': 'SonarQube project key (accepted for API uniformity)'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon

    return _output_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
