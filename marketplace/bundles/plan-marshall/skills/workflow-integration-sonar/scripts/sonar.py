#!/usr/bin/env python3
"""
Sonar workflow operations - producer-side fetch + pre-filter + per-finding store.

Producer-side flow: ``fetch-and-store`` fetches gate-blocking Sonar issues,
applies the keyword pre-filter from ``standards/sonar-rules.json`` (drops
issues already suppressable via NOSONAR / test-acceptable rules) and writes
one ``sonar-issue`` finding per surviving issue via ``manage-findings add``
(direct ``add_finding`` import). LLM consumers query via
``manage-findings query --type sonar-issue`` — the script-side triage and
triage-batch surfaces have been retired.

Usage:
    sonar.py fetch-and-store --plan-id <P> --project <key> [--pr <id>] [--severities <list>] [--types <list>]
    sonar.py --help
"""

import sys
from typing import Any

from ci_base import extract_project_dir, set_default_cwd  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    create_workflow_cli,
    is_test_file,
    load_skill_config,
    safe_main,
)

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
# FETCH-AND-STORE SUBCOMMAND (producer-side fetch + filter + store)
# ============================================================================


def _fetch_issues(project: str, pr: str | None, severities: str | None, types: str | None) -> dict[str, Any]:
    """Fetch issues via the Sonar REST client and return the parsed dict.

    Mirrors ``sonar_rest.cmd_search`` issue extraction so the producer-side
    flow does not depend on a subprocess call into another skill script.
    """
    from _providers_core import (  # type: ignore[import-not-found]
        RestClientError,
        get_authenticated_client,
    )

    client = get_authenticated_client('workflow-integration-sonar')
    params: dict[str, str] = {
        'projects': project,
        'ps': '500',
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


def cmd_fetch_and_store(args):
    """Producer-side: fetch + pre-filter + write one sonar-issue finding per surviving issue.

    Always-on storage: every surviving (non-suppressable) Sonar issue becomes
    a ``sonar-issue`` finding via ``add_finding``. ``count_fetched`` vs
    ``count_stored`` mismatches are recorded as a ``qgate`` finding with title
    prefix ``(producer-mismatch)``.
    """
    from _findings_core import (  # type: ignore[import-not-found]
        add_finding,
        add_qgate_finding,
    )

    plan_id: str = args.plan_id
    project: str = args.project
    pr: str | None = getattr(args, 'pr', None)

    fetch_result = _fetch_issues(project, pr, getattr(args, 'severities', None), getattr(args, 'types', None))
    if fetch_result.get('status') != 'success':
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
        detail_lines.append('')
        detail_lines.append('--- message ---')
        detail_lines.append(issue.get('message', ''))
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
            title=f'(producer-mismatch) sonar fetch-and-store project={project}',
            detail=mismatch_detail,
        )
        qgate_hash = qgate_result.get('hash_id')

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
    }


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    # Accept (and swallow) a top-level --project-dir for API uniformity with
    # the github/gitlab workflow scripts. The Sonar REST client does not use
    # cwd; the flag is preserved so future subprocess additions remain
    # configurable.
    project_dir, remaining = extract_project_dir(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = create_workflow_cli(
        description='Sonar workflow operations',
        epilog="""
Examples:
  sonar.py fetch-and-store --plan-id my-plan --project com.example:project
  sonar.py fetch-and-store --plan-id my-plan --project com.example:project --pr 123 --severities BLOCKER,CRITICAL
""",
        subcommands=[
            {
                'name': 'fetch-and-store',
                'help': 'Producer-side: fetch + pre-filter + store one sonar-issue finding per surviving issue',
                'handler': cmd_fetch_and_store,
                'args': [
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                    {'flags': ['--project'], 'required': True, 'help': 'SonarQube project key'},
                    {'flags': ['--pr'], 'help': 'Pull request ID'},
                    {'flags': ['--severities'], 'help': 'Filter by severity (comma-separated)'},
                    {'flags': ['--types'], 'help': 'Filter by type (comma-separated)'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon  # type: ignore[import-not-found]

    return _output_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
