#!/usr/bin/env python3
"""Analysis functions for doctor-marketplace."""

import re
from pathlib import Path
from typing import Any

# Import from analyze.py
from _analyze import (
    analyze_markdown_file,
    analyze_skill_structure,
    analyze_tool_coverage,
)
from _analyze_markdown import check_forbidden_metadata, get_bloat_classification

# Subdirectories that may contain markdown sub-documents
SUBDOC_DIRS = ['references', 'standards', 'workflows', 'templates']


def analyze_component(component: dict) -> dict:
    """Analyze a single component and return issues."""
    component_type = component.get('type')
    path = component.get('path')

    issues: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}

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

        # Sub-document analysis (references/, standards/, workflows/, templates/)
        subdoc_results = analyze_subdocuments(skill_dir)
        if subdoc_results:
            analysis['subdocuments'] = subdoc_results
            issues.extend(extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir)))

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
    if rules.get('agent_task_tool_prohibited'):
        issues.append(
            {
                'type': 'agent-task-tool-prohibited',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent declares Task tool (agent-task-tool-prohibited)',
            }
        )
    if rules.get('agent_maven_restricted'):
        issues.append(
            {
                'type': 'agent-maven-restricted',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': 'Direct Maven usage outside builder (agent-maven-restricted)',
            }
        )
    if rules.get('workflow_hardcoded_script_path'):
        issues.append(
            {
                'type': 'workflow-hardcoded-script-path',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': 'Hardcoded script path - use executor notation instead (workflow-hardcoded-script-path)',
            }
        )
    if rules.get('agent_skill_tool_visibility'):
        issues.append(
            {
                'type': 'agent-skill-tool-visibility',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent tools missing Skill — invisible to Task dispatcher (agent-skill-tool-visibility)',
            }
        )
    for violation in rules.get('workflow_prose_param_violations', []):
        issues.append(
            {
                'type': 'workflow-prose-parameter-inconsistency',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': f'Prose-parameter inconsistency: {violation.get("issue", "")}',
                'details': violation,
            }
        )

    # Check CI rule
    ci = analysis.get('continuous_improvement_rule', {})
    if ci.get('format', {}).get('agent_lessons_via_skill'):
        issues.append(
            {
                'type': 'agent-lessons-via-skill',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent uses self-update pattern (agent-lessons-via-skill)',
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
    - agent-task-tool-prohibited (Task declared in agent frontmatter)
    - agent-maven-restricted (Maven calls outside builder)
    - Backup file patterns (quality issue)

    Tool usage analysis (missing/unused) is NOT done here - that requires
    semantic understanding and is delegated to LLM via tool-coverage-agent.
    """
    issues = []

    # Only extract deterministic violations
    violations = coverage.get('critical_violations', {})

    # agent-task-tool-prohibited: Agent declares Task tool (deterministic - check frontmatter only)
    if component_type == 'agent' and violations.get('has_task_declared'):
        issues.append(
            {
                'type': 'agent-task-tool-prohibited',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': 'Agent declares Task tool (agent-task-tool-prohibited)',
            }
        )

    # agent-maven-restricted: Maven calls outside builder (only flag if not in builder bundle)
    maven_calls = violations.get('maven_calls', [])
    if maven_calls and 'builder' not in file_path:
        issues.append(
            {
                'type': 'agent-maven-restricted',
                'file': file_path,
                'severity': 'warning',
                'fixable': False,
                'description': f'Direct Maven usage (agent-maven-restricted) - {len(maven_calls)} call(s)',
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


def analyze_subdocuments(skill_dir: Path) -> list[dict]:
    """Analyze markdown sub-documents in a skill directory.

    Checks references/, standards/, workflows/, templates/ for:
    - Line count and bloat classification
    - Forbidden metadata sections
    - Hardcoded script paths
    """
    results = []

    for subdir_name in SUBDOC_DIRS:
        subdir = skill_dir / subdir_name
        if not subdir.is_dir():
            continue

        for md_file in sorted(subdir.glob('*.md')):
            try:
                content = md_file.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue

            line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            bloat_class = get_bloat_classification(line_count, 'subdoc')
            has_forbidden, forbidden_sections = check_forbidden_metadata(content)

            entry: dict = {
                'path': str(md_file),
                'relative_path': f'{subdir_name}/{md_file.name}',
                'line_count': line_count,
                'bloat': bloat_class,
            }

            issues: list[dict] = []
            if bloat_class in ('CRITICAL', 'BLOATED'):
                issues.append({
                    'type': 'subdoc-bloat',
                    'classification': bloat_class,
                    'line_count': line_count,
                })
            if has_forbidden:
                issues.append({
                    'type': 'subdoc-forbidden-metadata',
                    'sections': forbidden_sections,
                })

            # Hardcoded script paths
            if re.search(r'python3 .*/scripts/|bash .*/scripts/|\{[^}]+\}/scripts/', content):
                if not re.search(r'Skill:.*script-runner', content):
                    issues.append({
                        'type': 'subdoc-hardcoded-script-path',
                    })

            if issues:
                entry['issues'] = issues

            results.append(entry)

    return results


def extract_issues_from_subdoc_analysis(subdoc_results: list[dict], skill_path: str) -> list[dict]:
    """Extract issues from sub-document analysis into the component issue list."""
    issues = []

    for subdoc in subdoc_results:
        for issue in subdoc.get('issues', []):
            file_path = subdoc['path']

            if issue['type'] == 'subdoc-bloat':
                issues.append({
                    'type': 'subdoc-bloat',
                    'file': file_path,
                    'severity': 'warning' if issue['classification'] == 'BLOATED' else 'error',
                    'fixable': False,
                    'classification': issue['classification'],
                    'line_count': issue['line_count'],
                    'description': f'Sub-document bloat ({issue["classification"]}, {issue["line_count"]} lines)',
                })
            elif issue['type'] == 'subdoc-forbidden-metadata':
                issues.append({
                    'type': 'subdoc-forbidden-metadata',
                    'file': file_path,
                    'severity': 'warning',
                    'fixable': True,
                    'description': f'Forbidden metadata sections: {issue["sections"]}',
                })
            elif issue['type'] == 'subdoc-hardcoded-script-path':
                issues.append({
                    'type': 'subdoc-hardcoded-script-path',
                    'file': file_path,
                    'severity': 'warning',
                    'fixable': False,
                    'description': 'Hardcoded script path in sub-document',
                })

    return issues
