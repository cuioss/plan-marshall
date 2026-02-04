#!/usr/bin/env python3
"""Analysis functions for doctor-marketplace."""

from pathlib import Path

# Import from analyze.py
from _analyze import (
    analyze_markdown_file,
    analyze_skill_structure,
    analyze_tool_coverage,
)


def analyze_component(component: dict) -> dict:
    """Analyze a single component and return issues."""
    component_type = component.get('type')
    path = component.get('path')

    issues = []
    analysis = {}

    if component_type in ('agent', 'command'):
        # Markdown analysis
        if path is not None:
            file_path = Path(path)
            if file_path.exists():
                md_analysis = analyze_markdown_file(file_path, component_type)
                analysis['markdown'] = md_analysis

                # Extract issues from analysis
                issues.extend(extract_issues_from_markdown_analysis(md_analysis, str(path), component_type))

                # Tool coverage analysis
                coverage = analyze_tool_coverage(file_path)
                if 'error' not in coverage:
                    analysis['coverage'] = coverage
                    issues.extend(extract_issues_from_coverage_analysis(coverage, str(path), component_type))

    elif component_type == 'skill':
        if path is None:
            return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}
        skill_dir = Path(path)
        skill_md_path = component.get('skill_md_path')

        # Structure analysis
        structure = analyze_skill_structure(skill_dir)
        analysis['structure'] = structure

        # Markdown analysis of SKILL.md
        if skill_md_path:
            md_path = Path(skill_md_path)
            if md_path.exists():
                md_analysis = analyze_markdown_file(md_path, 'skill')
                analysis['markdown'] = md_analysis
                issues.extend(extract_issues_from_markdown_analysis(md_analysis, skill_md_path, 'skill'))

    return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}


def extract_issues_from_markdown_analysis(analysis: dict, file_path: str, component_type: str) -> list[dict]:
    """Extract fixable issues from markdown analysis."""
    issues = []

    # Check frontmatter
    fm = analysis.get('frontmatter', {})
    if not fm.get('present'):
        issues.append({'type': 'missing-frontmatter', 'file': file_path, 'severity': 'error', 'fixable': True})
    elif not fm.get('yaml_valid'):
        issues.append({'type': 'invalid-yaml', 'file': file_path, 'severity': 'error', 'fixable': True})
    else:
        required = fm.get('required_fields', {})
        if not required.get('name', {}).get('present'):
            issues.append({'type': 'missing-name-field', 'file': file_path, 'severity': 'error', 'fixable': True})
        if not required.get('description', {}).get('present'):
            issues.append(
                {'type': 'missing-description-field', 'file': file_path, 'severity': 'warning', 'fixable': True}
            )
        if component_type in ('agent', 'command') and not required.get('tools', {}).get('present'):
            issues.append({'type': 'missing-tools-field', 'file': file_path, 'severity': 'warning', 'fixable': True})

    # Check rule violations
    rules = analysis.get('rules', {})
    if rules.get('rule_6_violation'):
        issues.append(
            {
                'type': 'rule-6-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent declares Task tool (Rule 6)',
            }
        )
    if rules.get('rule_7_violation'):
        issues.append(
            {
                'type': 'rule-7-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': 'Direct Maven usage outside builder (Rule 7)',
            }
        )
    if rules.get('rule_8_violation'):
        issues.append(
            {
                'type': 'rule-8-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': 'Hardcoded script path - use executor notation instead (Rule 8)',
            }
        )
    if rules.get('rule_11_violation'):
        issues.append(
            {
                'type': 'rule-11-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent tools missing Skill — invisible to Task dispatcher (Rule 11)',
            }
        )
    for violation in rules.get('rule_12_violations', []):
        issues.append(
            {
                'type': 'rule-12-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': f"Prose-parameter inconsistency (Rule 12): {violation.get('issue', '')}",
                'details': violation,
            }
        )

    # Check CI rule
    ci = analysis.get('continuous_improvement_rule', {})
    if ci.get('format', {}).get('pattern_22_violation'):
        issues.append(
            {
                'type': 'pattern-22-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent uses self-update pattern (Pattern 22)',
            }
        )

    # Check bloat
    bloat = analysis.get('bloat', {}).get('classification', 'NORMAL')
    if bloat in ('CRITICAL', 'BLOATED'):
        issues.append(
            {
                'type': 'file-bloat',
                'file': file_path,
                'severity': 'warning' if bloat == 'BLOATED' else 'error',
                'fixable': False,
                'classification': bloat,
                'line_count': analysis.get('metrics', {}).get('line_count', 0),
            }
        )

    return issues


def extract_issues_from_coverage_analysis(coverage: dict, file_path: str, component_type: str = '') -> list[dict]:
    """Extract deterministic issues from tool coverage analysis.

    NOTE: This function extracts issues that can be determined structurally:
    - Rule 6 violations (Task declared in agent frontmatter)
    - Rule 7 violations (Maven calls outside builder)
    - Backup file patterns (quality issue)

    Tool usage analysis (missing/unused) is NOT done here - that requires
    semantic understanding and is delegated to LLM via tool-coverage-agent.
    """
    issues = []

    # Only extract deterministic violations
    violations = coverage.get('critical_violations', {})

    # Rule 6: Agent declares Task tool (deterministic - check frontmatter only)
    if component_type == 'agent' and violations.get('has_task_declared'):
        issues.append(
            {
                'type': 'rule-6-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent declares Task tool (Rule 6)',
            }
        )

    # Rule 7: Maven calls outside builder (only flag if not in builder bundle)
    maven_calls = violations.get('maven_calls', [])
    if maven_calls and 'builder' not in file_path:
        issues.append(
            {
                'type': 'rule-7-violation',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': f'Direct Maven usage (Rule 7) - {len(maven_calls)} call(s)',
                'details': {'maven_calls': maven_calls},
            }
        )

    # Backup file patterns (quality issue)
    backup_patterns = violations.get('backup_file_patterns', [])
    if backup_patterns:
        issues.append(
            {
                'type': 'backup-pattern',
                'file': file_path,
                'severity': 'info',
                'fixable': False,
                'description': f'Backup file patterns found - {len(backup_patterns)} occurrence(s)',
                'details': {'patterns': backup_patterns},
            }
        )

    return issues
