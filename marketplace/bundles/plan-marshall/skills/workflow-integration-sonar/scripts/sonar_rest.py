#!/usr/bin/env python3
"""
Sonar REST API client.

Replaces MCP tool calls with direct HTTP requests via RestClient.
Credentials are loaded via get_authenticated_client() and never
appear in stdout/TOON output.

Usage:
    sonar_rest.py search --project <key> [--pr <id>] [--severities BLOCKER,CRITICAL] [--types BUG,VULNERABILITY]
    sonar_rest.py transition --issue-key <key> --transition <accept|falsepositive|wontfix>
    sonar_rest.py metrics --project <key> --component <key> [--metrics <comma-separated>]
    sonar_rest.py gate-status --project <key> [--branch <name> | --pr <id>]
    sonar_rest.py ce-status --project <key> [--branch <name>]
    sonar_rest.py hotspots --project <key> [--branch <name> | --pr <id>]
"""

import argparse
import sys

from _providers_core import RestClientError, get_authenticated_client  # type: ignore[import-not-found]
from ci_base import extract_routing_args, set_default_cwd  # type: ignore[import-not-found]
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_component_arg,
    parse_args_with_toon_errors,
)

SKILL_NAME = 'workflow-integration-sonar'


def cmd_search(args) -> int:
    """Search for Sonar issues."""
    client = get_authenticated_client(SKILL_NAME)

    params: dict = {
        'projects': args.project,
        'ps': '500',  # page size
    }
    if args.pr:
        params['pullRequest'] = args.pr
    if args.severities:
        params['severities'] = args.severities
    if args.types:
        params['types'] = args.types

    try:
        result = client.get('/api/issues/search', params=params)
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
            }
        )
        return 0

    issues = result.get('issues', [])
    formatted = []
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}

    for issue in issues:
        entry = {
            'key': issue.get('key', ''),
            'type': issue.get('type', ''),
            'severity': issue.get('severity', ''),
            'file': issue.get('component', '').split(':')[-1],
            'line': issue.get('line', 0),
            'rule': issue.get('rule', ''),
            'message': issue.get('message', ''),
        }
        formatted.append(entry)

        sev = entry['severity']
        by_severity[sev] = by_severity.get(sev, 0) + 1
        typ = entry['type']
        by_type[typ] = by_type.get(typ, 0) + 1

    output_toon(
        {
            'status': 'success',
            'project_key': args.project,
            'pull_request_id': args.pr or 'none',
            'issues': formatted,
            'statistics': {
                'total_issues_fetched': len(formatted),
                'by_severity': by_severity,
                'by_type': by_type,
            },
        }
    )
    return 0


def cmd_transition(args) -> int:
    """Change Sonar issue status."""
    client = get_authenticated_client(SKILL_NAME)

    try:
        client.post(
            '/api/issues/do_transition',
            body={
                'issue': args.issue_key,
                'transition': args.transition,
            },
        )
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
                'issue_key': args.issue_key,
            }
        )
        return 0

    output_toon(
        {
            'status': 'success',
            'issue_key': args.issue_key,
            'transition': args.transition,
        }
    )
    return 0


def cmd_metrics(args) -> int:
    """Get Sonar metrics for a component."""
    client = get_authenticated_client(SKILL_NAME)

    metrics = args.metrics or 'coverage,duplicated_lines_density,ncloc,bugs,vulnerabilities,code_smells'

    params: dict = {
        'component': args.component,
        'metricKeys': metrics,
    }

    try:
        result = client.get('/api/measures/component', params=params)
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
            }
        )
        return 0

    component = result.get('component', {})
    measures = {}
    for measure in component.get('measures', []):
        measures[measure.get('metric', '')] = measure.get('value', '')

    output_toon(
        {
            'status': 'success',
            'project_key': args.project,
            'component': args.component,
            'measures': measures,
        }
    )
    return 0


def cmd_gate_status(args) -> int:
    """Get the authoritative quality-gate verdict for a project.

    Calls GET /api/qualitygates/project_status and returns the overall
    gate status plus one entry per condition (the exact verdict the Maven
    sonar plugin gates on).
    """
    client = get_authenticated_client(SKILL_NAME)

    params: dict = {'projectKey': args.project}
    if args.branch:
        params['branch'] = args.branch
    elif args.pr:
        params['pullRequest'] = args.pr

    try:
        result = client.get('/api/qualitygates/project_status', params=params)
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
            }
        )
        return 0

    project_status = result.get('projectStatus', {})
    conditions = []
    for condition in project_status.get('conditions', []):
        conditions.append(
            {
                'metricKey': condition.get('metricKey', ''),
                'comparator': condition.get('comparator', ''),
                'errorThreshold': condition.get('errorThreshold', ''),
                'actualValue': condition.get('actualValue', ''),
                'status': condition.get('status', ''),
            }
        )

    output_toon(
        {
            'status': 'success',
            'project_key': args.project,
            'branch': args.branch or 'none',
            'pull_request_id': args.pr or 'none',
            'gate_status': project_status.get('status', ''),
            'conditions': conditions,
        }
    )
    return 0


def cmd_ce_status(args) -> int:
    """Get recent Compute-Engine analysis-task status for a project.

    Calls GET /api/ce/activity and GET /api/ce/component so an infra
    processing failure (errorType/errorMessage) is distinguishable from a
    real gate failure.
    """
    client = get_authenticated_client(SKILL_NAME)

    activity_params: dict = {
        'component': args.project,
        'ps': '25',  # page size, bounded as cmd_search does
    }
    if args.branch:
        activity_params['branch'] = args.branch

    try:
        activity = client.get('/api/ce/activity', params=activity_params)
        component = client.get('/api/ce/component', params={'component': args.project})
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
            }
        )
        return 0

    tasks = []
    for task in activity.get('tasks', []):
        tasks.append(
            {
                'id': task.get('id', ''),
                'status': task.get('status', ''),
                'branch': task.get('branch', ''),
                'submittedAt': task.get('submittedAt', ''),
                'executedAt': task.get('executedAt', ''),
                'errorType': task.get('errorType', ''),
                'errorMessage': task.get('errorMessage', ''),
            }
        )

    current = component.get('current', {})
    queue = component.get('queue', [])

    output_toon(
        {
            'status': 'success',
            'project_key': args.project,
            'branch': args.branch or 'none',
            'current_status': current.get('status', 'none'),
            'queue_length': len(queue),
            'tasks': tasks,
        }
    )
    return 0


def cmd_hotspots(args) -> int:
    """Get security hotspots for a project.

    Calls GET /api/hotspots/search. Hotspots drive
    new_security_hotspots_reviewed and are NOT returned by the search
    issues verb.
    """
    client = get_authenticated_client(SKILL_NAME)

    params: dict = {'projectKey': args.project}
    if args.branch:
        params['branch'] = args.branch
    elif args.pr:
        params['pullRequest'] = args.pr

    try:
        result = client.get('/api/hotspots/search', params=params)
        client.close()
    except RestClientError as e:
        output_toon(
            {
                'status': 'error',
                'message': f'Sonar API error: HTTP {e.status}',
            }
        )
        return 0

    hotspots = []
    by_probability: dict[str, int] = {}
    for hotspot in result.get('hotspots', []):
        entry = {
            'key': hotspot.get('key', ''),
            'status': hotspot.get('status', ''),
            'vulnerabilityProbability': hotspot.get('vulnerabilityProbability', ''),
            'securityCategory': hotspot.get('securityCategory', ''),
            'component': hotspot.get('component', '').split(':')[-1],
            'line': hotspot.get('line', 0),
            'message': hotspot.get('message', ''),
        }
        hotspots.append(entry)
        prob = entry['vulnerabilityProbability']
        by_probability[prob] = by_probability.get(prob, 0) + 1

    output_toon(
        {
            'status': 'success',
            'project_key': args.project,
            'branch': args.branch or 'none',
            'pull_request_id': args.pr or 'none',
            'hotspots': hotspots,
            'statistics': {
                'total_hotspots_fetched': len(hotspots),
                'by_vulnerability_probability': by_probability,
            },
        }
    )
    return 0


@safe_main
def main() -> int:
    # Accept (and swallow) a top-level --plan-id / --project-dir pair for API
    # uniformity with the github/gitlab workflow scripts. All Sonar operations
    # here go over HTTP through RestClient, so cwd has no functional effect
    # on API calls; the routing is accepted as a no-op rather than rejected
    # by argparse. Two-state contract enforced by extract_routing_args.
    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = argparse.ArgumentParser(description='Sonar REST API client', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # search
    search_parser = subparsers.add_parser('search', help='Search for Sonar issues', allow_abbrev=False)
    search_parser.add_argument('--project', required=True, help='SonarQube project key')
    search_parser.add_argument('--pr', help='Pull request ID')
    search_parser.add_argument('--severities', help='Filter by severity (comma-separated)')
    search_parser.add_argument('--types', help='Filter by type (comma-separated)')

    # transition
    transition_parser = subparsers.add_parser('transition', help='Change issue status', allow_abbrev=False)
    transition_parser.add_argument('--issue-key', required=True, help='Sonar issue key')
    transition_parser.add_argument(
        '--transition', required=True, choices=['accept', 'falsepositive', 'wontfix'], help='Transition to apply'
    )

    # metrics
    metrics_parser = subparsers.add_parser('metrics', help='Get component metrics', allow_abbrev=False)
    metrics_parser.add_argument('--project', required=True, help='SonarQube project key')
    add_component_arg(metrics_parser)
    metrics_parser.add_argument('--metrics', help='Comma-separated metric keys')

    # gate-status
    gate_parser = subparsers.add_parser(
        'gate-status', help='Get authoritative quality-gate verdict', allow_abbrev=False
    )
    gate_parser.add_argument('--project', required=True, help='SonarQube project key')
    gate_parser.add_argument('--branch', help='Branch name')
    gate_parser.add_argument('--pr', help='Pull request ID')

    # ce-status
    ce_parser = subparsers.add_parser(
        'ce-status', help='Get Compute-Engine analysis-task status', allow_abbrev=False
    )
    ce_parser.add_argument('--project', required=True, help='SonarQube project key')
    ce_parser.add_argument('--branch', help='Branch name')

    # hotspots
    hotspots_parser = subparsers.add_parser('hotspots', help='Get security hotspots', allow_abbrev=False)
    hotspots_parser.add_argument('--project', required=True, help='SonarQube project key')
    hotspots_parser.add_argument('--branch', help='Branch name')
    hotspots_parser.add_argument('--pr', help='Pull request ID')

    args = parse_args_with_toon_errors(parser)

    if args.command == 'search':
        return cmd_search(args)
    elif args.command == 'transition':
        return cmd_transition(args)
    elif args.command == 'metrics':
        return cmd_metrics(args)
    elif args.command == 'gate-status':
        return cmd_gate_status(args)
    elif args.command == 'ce-status':
        return cmd_ce_status(args)
    elif args.command == 'hotspots':
        return cmd_hotspots(args)

    output_toon({'status': 'error', 'error': f'Unknown command: {args.command}'})
    return 0


if __name__ == '__main__':
    sys.exit(main())
