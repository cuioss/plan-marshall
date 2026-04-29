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
"""

import argparse
import sys

from _providers_core import RestClientError, get_authenticated_client  # type: ignore[import-not-found]
from ci_base import extract_project_dir, set_default_cwd  # type: ignore[import-not-found]
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
        output_toon({
            'status': 'error',
            'message': f'Sonar API error: HTTP {e.status}',
        })
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

    output_toon({
        'status': 'success',
        'project_key': args.project,
        'pull_request_id': args.pr or 'none',
        'issues': formatted,
        'statistics': {
            'total_issues_fetched': len(formatted),
            'by_severity': by_severity,
            'by_type': by_type,
        },
    })
    return 0


def cmd_transition(args) -> int:
    """Change Sonar issue status."""
    client = get_authenticated_client(SKILL_NAME)

    try:
        client.post('/api/issues/do_transition', body={
            'issue': args.issue_key,
            'transition': args.transition,
        })
        client.close()
    except RestClientError as e:
        output_toon({
            'status': 'error',
            'message': f'Sonar API error: HTTP {e.status}',
            'issue_key': args.issue_key,
        })
        return 0

    output_toon({
        'status': 'success',
        'issue_key': args.issue_key,
        'transition': args.transition,
    })
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
        output_toon({
            'status': 'error',
            'message': f'Sonar API error: HTTP {e.status}',
        })
        return 0

    component = result.get('component', {})
    measures = {}
    for measure in component.get('measures', []):
        measures[measure.get('metric', '')] = measure.get('value', '')

    output_toon({
        'status': 'success',
        'project_key': args.project,
        'component': args.component,
        'measures': measures,
    })
    return 0


@safe_main
def main() -> int:
    # Accept (and swallow) a top-level --project-dir for API uniformity with
    # the github/gitlab workflow scripts. All Sonar operations here go over
    # HTTP through RestClient, so cwd has no functional effect on API calls;
    # the flag is accepted as a no-op rather than rejected by argparse.
    project_dir, remaining = extract_project_dir(sys.argv[1:])
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
    transition_parser.add_argument('--transition', required=True,
                                   choices=['accept', 'falsepositive', 'wontfix'],
                                   help='Transition to apply')

    # metrics
    metrics_parser = subparsers.add_parser('metrics', help='Get component metrics', allow_abbrev=False)
    metrics_parser.add_argument('--project', required=True, help='SonarQube project key')
    add_component_arg(metrics_parser)
    metrics_parser.add_argument('--metrics', help='Comma-separated metric keys')

    args = parse_args_with_toon_errors(parser)

    if args.command == 'search':
        return cmd_search(args)
    elif args.command == 'transition':
        return cmd_transition(args)
    elif args.command == 'metrics':
        return cmd_metrics(args)

    output_toon({'status': 'error', 'error': f'Unknown command: {args.command}'})
    return 0


if __name__ == '__main__':
    sys.exit(main())
