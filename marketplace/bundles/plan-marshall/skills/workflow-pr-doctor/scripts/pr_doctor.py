#!/usr/bin/env python3
"""
PR Doctor utilities - handoff parsing and diagnostic report generation.

Usage:
    pr_doctor.py parse-handoff --handoff <json>
    pr_doctor.py diagnose --build-status <status> [options]
    pr_doctor.py track-attempt --category <cat> --current <n>
    pr_doctor.py --help

Subcommands:
    parse-handoff    Parse and validate handoff JSON, merge with explicit params
    diagnose         Generate deterministic PR diagnostic report
    track-attempt    Check if a fix attempt should proceed

Examples:
    # Parse a handoff structure
    pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123},"decisions":{"auto_fix":true}}'

    # Diagnose PR issues
    pr_doctor.py diagnose --build-status failure --build-failures '[{"step":"test","message":"3 failed"}]'

    # Check attempt limit
    pr_doctor.py track-attempt --category build --current 0
"""

import sys
from typing import Any

from triage_helpers import (  # type: ignore[import-not-found]
    create_workflow_cli,
    load_skill_config,
    make_error,
    parse_json_arg,
    print_toon,
    safe_main,
)

# ============================================================================
# CONFIGURATION (loaded from pr-doctor-config.json)
# ============================================================================

_CONFIG = load_skill_config(__file__, 'pr-doctor-config.json')

# ============================================================================
# HANDOFF SCHEMA
# ============================================================================

VALID_CHECKS = set(_CONFIG.get('valid_checks', ['build', 'reviews', 'sonar', 'all']))
DEFAULT_MAX_FIX_ATTEMPTS = _CONFIG.get('default_max_fix_attempts', 3)

# Build step to severity mapping — compile/test failures block everything (high),
# lint/style failures are less urgent (medium). Unknown steps default to high.
BUILD_STEP_SEVERITY: dict[str, str] = _CONFIG.get('build_step_severity', {
    'compile': 'high', 'build': 'high', 'test': 'high',
    'lint': 'medium', 'style': 'medium', 'format': 'medium',
})


def validate_handoff(handoff: dict) -> list[str]:
    """Validate handoff JSON structure. Returns list of warnings (empty = valid)."""
    warnings = []

    # Check top-level structure
    valid_keys = {'artifacts', 'decisions', 'constraints'}
    unknown_keys = set(handoff.keys()) - valid_keys
    if unknown_keys:
        warnings.append(f'Unknown top-level keys: {", ".join(sorted(unknown_keys))}')

    # Validate artifacts
    artifacts = handoff.get('artifacts', {})
    if not isinstance(artifacts, dict):
        warnings.append('artifacts must be a dict')
    else:
        if 'pr_number' in artifacts:
            pr = artifacts['pr_number']
            if not isinstance(pr, int) or pr <= 0:
                warnings.append(f'artifacts.pr_number must be a positive integer, got: {pr}')

    # Validate decisions
    decisions = handoff.get('decisions', {})
    if not isinstance(decisions, dict):
        warnings.append('decisions must be a dict')
    else:
        if 'checks' in decisions:
            checks = decisions['checks']
            if checks not in VALID_CHECKS:
                warnings.append(f'decisions.checks must be one of {VALID_CHECKS}, got: {checks}')
        if 'auto_fix' in decisions and not isinstance(decisions['auto_fix'], bool):
            warnings.append(f'decisions.auto_fix must be bool, got: {type(decisions["auto_fix"]).__name__}')

    # Semantic consistency checks
    if isinstance(decisions, dict):
        if decisions.get('skip_sonar') and decisions.get('checks') == 'sonar':
            warnings.append("Contradiction: checks='sonar' with skip_sonar=true — Sonar will be skipped despite being the only requested check")

    # Validate constraints
    constraints = handoff.get('constraints', {})
    if not isinstance(constraints, dict):
        warnings.append('constraints must be a dict')
    else:
        if 'max_fix_attempts' in constraints:
            mfa = constraints['max_fix_attempts']
            if not isinstance(mfa, int) or mfa <= 0:
                warnings.append(f'constraints.max_fix_attempts must be a positive integer, got: {mfa}')
        if 'protected_files' in constraints:
            pf = constraints['protected_files']
            if not isinstance(pf, list) or not all(isinstance(f, str) for f in pf):
                warnings.append('constraints.protected_files must be a list of strings')

    return warnings


def merge_handoff_with_params(
    handoff: dict,
    pr: int | None = None,
    checks: str | None = None,
    auto_fix: bool | None = None,
    max_fix_attempts: int | None = None,
    wait: bool | None = None,
) -> dict[str, Any]:
    """Merge handoff structure with explicit parameters. Explicit params take precedence."""
    artifacts = handoff.get('artifacts', {})
    decisions = handoff.get('decisions', {})
    constraints = handoff.get('constraints', {})

    result: dict[str, Any] = {
        'pr_number': pr if pr is not None else artifacts.get('pr_number'),
        'branch': artifacts.get('branch'),
        'commit_hash': artifacts.get('commit_hash'),
        'plan_id': artifacts.get('plan_id'),
        'checks': checks if checks is not None else decisions.get('checks', 'all'),
        'auto_fix': auto_fix if auto_fix is not None else decisions.get('auto_fix', False),
        'wait': wait if wait is not None else decisions.get('wait', True),
        'skip_sonar': decisions.get('skip_sonar', False),
        'automated_review': decisions.get('automated_review', False),
        'max_fix_attempts': (
            max_fix_attempts if max_fix_attempts is not None
            else constraints.get('max_fix_attempts', DEFAULT_MAX_FIX_ATTEMPTS)
        ),
        'protected_files': constraints.get('protected_files', []),
    }

    return result


# ============================================================================
# TRACK-ATTEMPT SUBCOMMAND
# ============================================================================


# Stateless attempt check — the caller tracks the current count and passes
# it in; the script returns whether to continue or stop.
def check_attempt(category: str, current: int, max_attempts: int) -> dict[str, Any]:
    """Check whether a fix attempt should proceed or stop.

    Args:
        category: Fix category (build, reviews, sonar).
        current: Current attempt number (0-based, pre-increment).
        max_attempts: Maximum allowed attempts.

    Returns:
        Dict with 'proceed' bool, 'attempt' (1-based), and 'remaining'.
    """
    attempt = current + 1
    proceed = attempt <= max_attempts
    return {
        'category': category,
        'attempt': attempt,
        'max_attempts': max_attempts,
        'remaining': max(0, max_attempts - attempt),
        'proceed': proceed,
        'reason': 'within limit' if proceed else f'reached max {max_attempts} attempts for {category}',
        'status': 'success',
    }


def cmd_track_attempt(args):
    """Handle track-attempt subcommand."""
    result = check_attempt(args.category, args.current, args.max_attempts)
    return print_toon(result)


# ============================================================================
# DIAGNOSE SUBCOMMAND
# ============================================================================


def diagnose_pr(
    build_status: str | None = None,
    build_failures: list[dict] | None = None,
    review_comments: list[dict] | None = None,
    sonar_issues: list[dict] | None = None,
) -> dict[str, Any]:
    """Aggregate PR diagnostic data into a deterministic report.

    Takes structured inputs from CI status, review comments, and Sonar
    issues and produces a consistent diagnostic report with categorized
    issues and recommended actions.

    Args:
        build_status: Overall build status ('success', 'failure', None for unknown).
        build_failures: List of build failure dicts with 'step', 'message' keys.
        review_comments: List of unresolved review comment dicts.
        sonar_issues: List of Sonar issue dicts with 'severity' key.
    """
    build_failures = build_failures or []
    review_comments = review_comments or []
    sonar_issues = sonar_issues or []

    issues: list[dict[str, Any]] = []
    actions: list[str] = []

    build_pass = build_status == 'success'
    if not build_pass and build_status is not None:
        for failure in build_failures:
            if not isinstance(failure, dict):
                print(f'WARNING: non-dict entry in build_failures: {type(failure).__name__}', file=sys.stderr)
                failure = {}
            step = failure.get('step', 'unknown')
            issues.append({
                'category': 'build',
                'severity': BUILD_STEP_SEVERITY.get(step, 'high'),
                'detail': failure.get('message', 'Build failure'),
                'step': step,
            })
        actions.append('Fix build failures before other issues')

    # Review diagnosis
    unresolved_count = len(review_comments)
    if unresolved_count > 0:
        # Determine highest priority from comments
        priority_map = {'high': 0, 'medium': 0, 'low': 0}
        for comment in review_comments:
            if not isinstance(comment, dict):
                continue
            p = comment.get('priority', 'low')
            if p in priority_map:
                priority_map[p] += 1
        issues.append({
            'category': 'reviews',
            'severity': 'high' if priority_map['high'] > 0 else 'medium',
            'detail': f'{unresolved_count} unresolved review comments',
            'breakdown': priority_map,
        })
        actions.append('Address review comments by priority')

    # Sonar diagnosis
    sonar_count = len(sonar_issues)
    if sonar_count > 0:
        severity_counts: dict[str, int] = {}
        for issue in sonar_issues:
            if not isinstance(issue, dict):
                continue
            sev = issue.get('severity', 'MAJOR')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        has_blockers = severity_counts.get('BLOCKER', 0) > 0
        has_critical = severity_counts.get('CRITICAL', 0) > 0
        issues.append({
            'category': 'sonar',
            'severity': 'high' if has_blockers or has_critical else 'medium',
            'detail': f'{sonar_count} Sonar issues',
            'breakdown': severity_counts,
        })
        actions.append('Fix Sonar issues (blockers and criticals first)')

    # Overall assessment
    overall = 'pass' if not issues else 'fail'

    return {
        'overall': overall,
        'build_status': 'PASS' if build_pass else ('FAIL' if build_status else 'UNKNOWN'),
        'review_comments': unresolved_count,
        'sonar_issues': sonar_count,
        'issues': issues,
        'recommended_actions': actions,
        'status': 'success',
    }


def cmd_diagnose(args):
    """Handle diagnose subcommand."""
    # Parse optional JSON inputs
    build_failures = None
    review_comments = None
    sonar_issues = None

    if args.build_failures:
        build_failures, rc = parse_json_arg(args.build_failures, '--build-failures')
        if rc:
            return rc

    if args.review_comments:
        review_comments, rc = parse_json_arg(args.review_comments, '--review-comments')
        if rc:
            return rc

    if args.sonar_issues:
        sonar_issues, rc = parse_json_arg(args.sonar_issues, '--sonar-issues')
        if rc:
            return rc

    result = diagnose_pr(
        build_status=args.build_status,
        build_failures=build_failures,
        review_comments=review_comments,
        sonar_issues=sonar_issues,
    )
    return print_toon(result)


# ============================================================================
# PARSE-HANDOFF SUBCOMMAND
# ============================================================================


def cmd_parse_handoff(args):
    """Handle parse-handoff subcommand."""
    handoff, rc = parse_json_arg(args.handoff, '--handoff')
    if rc:
        return rc

    if not isinstance(handoff, dict):
        return print_toon(make_error('Handoff must be a JSON object'))

    # Validate
    warnings = validate_handoff(handoff)

    # Resolve wait flag: --no-wait takes precedence, then --wait, then handoff
    wait_override = None
    if getattr(args, 'no_wait', False):
        wait_override = False
    elif getattr(args, 'wait', None) is not None:
        wait_override = args.wait

    # Merge with explicit params
    merged = merge_handoff_with_params(
        handoff,
        pr=args.pr,
        checks=args.checks,
        auto_fix=args.auto_fix,
        max_fix_attempts=args.max_fix_attempts,
        wait=wait_override,
    )

    result: dict[str, Any] = {
        'merged': merged,
        'validation': {
            'valid': len(warnings) == 0,
            'warnings': warnings,
        },
        'status': 'success',
    }

    return print_toon(result)


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = create_workflow_cli(
        description='PR Doctor utilities',
        epilog="""
Examples:
  pr_doctor.py diagnose --build-status failure --build-failures '[{"step":"test","message":"3 tests failed"}]'
  pr_doctor.py diagnose --review-comments '[{"priority":"high"}]' --sonar-issues '[{"severity":"BLOCKER"}]'
  pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123}}'
  pr_doctor.py track-attempt --category build --current 0
""",
        subcommands=[
            {
                'name': 'track-attempt',
                'help': 'Check if a fix attempt should proceed',
                'handler': cmd_track_attempt,
                'args': [
                    {'flags': ['--category'], 'required': True, 'choices': ['build', 'reviews', 'sonar'], 'help': 'Fix category'},
                    {'flags': ['--current'], 'type': int, 'required': True, 'help': 'Current attempt count (0-based)'},
                    {'flags': ['--max-attempts'], 'type': int, 'default': DEFAULT_MAX_FIX_ATTEMPTS, 'help': 'Maximum attempts'},
                ],
            },
            {
                'name': 'diagnose',
                'help': 'Generate deterministic PR diagnostic report',
                'handler': cmd_diagnose,
                'args': [
                    {'flags': ['--build-status'], 'choices': ['success', 'failure'], 'help': 'Overall build status'},
                    {'flags': ['--build-failures'], 'help': 'JSON array of build failure objects'},
                    {'flags': ['--review-comments'], 'help': 'JSON array of unresolved review comments'},
                    {'flags': ['--sonar-issues'], 'help': 'JSON array of Sonar issues'},
                ],
            },
            {
                'name': 'parse-handoff',
                'help': 'Parse and validate handoff JSON',
                'handler': cmd_parse_handoff,
                'args': [
                    {'flags': ['--handoff'], 'required': True, 'help': 'Handoff JSON string'},
                    {'flags': ['--pr'], 'type': int, 'help': 'Override PR number'},
                    {'flags': ['--checks'], 'choices': ['build', 'reviews', 'sonar', 'all'], 'help': 'Override checks'},
                    {'flags': ['--auto-fix'], 'action': 'store_true', 'default': None, 'help': 'Override auto-fix'},
                    {'flags': ['--wait'], 'action': 'store_true', 'default': None, 'help': 'Override wait for CI checks'},
                    {'flags': ['--no-wait'], 'action': 'store_true', 'default': False, 'help': 'Skip waiting for CI checks'},
                    {'flags': ['--max-fix-attempts'], 'type': int, 'help': 'Override max fix attempts'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
