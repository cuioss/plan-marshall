#!/usr/bin/env python3
"""Analysis functions for doctor-marketplace."""

import ast
import re
from pathlib import Path
from typing import Any

# Import from analyze.py
from _analyze import (
    analyze_markdown_file,
    analyze_skill_structure,
    analyze_tool_coverage,
    analyze_verb_chains,
)
from _analyze_markdown import (
    check_checklist_patterns,
    check_display_detail_violations,
    check_forbidden_metadata,
    check_resolver_gap,
    get_bloat_classification,
)
from _analyze_shared import check_agent_glob_resolver_workaround

# Subdirectories that may contain markdown sub-documents
SUBDOC_DIRS = ['references', 'standards', 'workflows', 'templates']

# Constructors whose calls must include allow_abbrev=False to prevent prefix
# matching of retired flags. See rule-catalog.md (argparse_safety) and
# lesson 2026-04-17-012.
_ARGPARSE_SAFETY_CONSTRUCTORS = ('ArgumentParser', 'add_parser')


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

                # agent-glob-resolver-workaround: agents that declare Glob in
                # tools without an explicit `# resolver-glob-exempt:` marker.
                # Driving lesson 2026-04-27-18-005.
                if component_type == 'agent':
                    try:
                        agent_content = file_path.read_text(encoding='utf-8', errors='replace')
                    except OSError:
                        agent_content = ''
                    for finding in check_agent_glob_resolver_workaround(str(path), agent_content):
                        issues.append(
                            {
                                'type': 'agent-glob-resolver-workaround',
                                'rule_id': 'agent-glob-resolver-workaround',
                                'file': str(path),
                                'line': finding.get('line'),
                                'severity': 'error',
                                'fixable': False,
                                'description': finding.get(
                                    'message',
                                    'Agent declares Glob without resolver exemption marker '
                                    '(agent-glob-resolver-workaround)',
                                ),
                                'details': finding,
                            }
                        )

    elif component_type == 'skill':
        if path is None:
            return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}
        skill_dir = Path(path)
        skill_md_path = component.get('skill_md_path')

        # Structure analysis
        structure = analyze_skill_structure(skill_dir)
        analysis['structure'] = structure

        # Skill naming convention: forbid noun-suffix directory names
        noun_suffix = structure.get('noun_suffix', {})
        if noun_suffix.get('violation'):
            directory_name = noun_suffix.get('directory_name', skill_dir.name)
            suffix = noun_suffix.get('suffix', '')
            issues.append(
                {
                    'type': 'skill-naming-noun-suffix',
                    'file': str(skill_dir),
                    'severity': 'warning',
                    'fixable': False,
                    'description': (
                        f'Skill directory name `{directory_name}` ends with reserved noun suffix '
                        f'`{suffix}` — use a verb-first name (skill-naming-noun-suffix)'
                    ),
                    'details': noun_suffix,
                }
            )

        # Markdown analysis of SKILL.md
        if skill_md_path:
            md_path = Path(skill_md_path)
            if md_path.exists():
                md_analysis = analyze_markdown_file(md_path, 'skill')
                analysis['markdown'] = md_analysis
                issues.extend(extract_issues_from_markdown_analysis(md_analysis, skill_md_path, 'skill'))

                # Tool coverage analysis for skills
                coverage = analyze_tool_coverage(md_path)
                if 'error' not in coverage:
                    analysis['coverage'] = coverage
                    issues.extend(extract_issues_from_coverage_analysis(coverage, skill_md_path, 'skill'))

        # Sub-document analysis (references/, standards/, workflows/, templates/)
        subdoc_results = analyze_subdocuments(skill_dir)
        if subdoc_results:
            analysis['subdocuments'] = subdoc_results
            issues.extend(extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir)))

        # Prose verb-chain consistency scan (AST-based, per-skill scope).
        # Mirrors the argparse_safety integration pattern: lightweight static
        # analyzer whose findings merge into the main issue stream as
        # unfixable error-severity entries.
        issues.extend(extract_issues_from_verb_chain_analysis(analyze_verb_chains(skill_dir)))

    return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}


def extract_issues_from_verb_chain_analysis(findings: list[dict]) -> list[dict]:
    """Translate ``analyze_verb_chains`` output into plugin-doctor issue dicts.

    The scanner returns findings with the native shape
    (``rule_id``/``file``/``line``/``script_notation``/``verb_chain``/
    ``first_unknown_segment``). Plugin-doctor's downstream categorizer keys
    on ``type``/``fixable`` (see ``categorize_all_issues``), so this helper
    adapts each finding to the same schema argparse_safety findings use —
    preserving the scanner's rule-specific fields under ``details``.
    """
    issues: list[dict] = []
    for finding in findings:
        unknown = finding.get('first_unknown_segment')
        notation = finding.get('script_notation', '')
        issues.append(
            {
                'type': 'prose-verb-chain-consistency',
                'rule_id': 'prose-verb-chain-consistency',
                'file': finding.get('file', ''),
                'line': finding.get('line'),
                'severity': 'error',
                'fixable': False,
                'description': (
                    f'Stale script verb `{unknown}` referenced for `{notation}` — '
                    'update prose to match the script\'s registered subparsers '
                    '(prose-verb-chain-consistency)'
                ),
                'script_notation': notation,
                'verb_chain': finding.get('verb_chain', []),
                'first_unknown_segment': unknown,
            }
        )
    return issues


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

        # Skill-specific field checks
        if component_type == 'skill':
            user_inv = required.get('user_invocable', {})
            # Check for unsupported allowed-tools field
            tools_info = required.get('tools', {})
            if tools_info.get('present'):
                issues.append(
                    {
                        'type': 'unsupported-skill-tools-field',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': f'Skill declares unsupported `{tools_info.get("field_type")}` field (not in plugin schema)',
                    }
                )
            # Check for misspelled user-invokable (should be user-invocable)
            if user_inv.get('misspelled') and not user_inv.get('present'):
                issues.append(
                    {
                        'type': 'misspelled-user-invocable',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': 'Skill uses `user-invokable` (misspelled) — should be `user-invocable`',
                    }
                )
            # Check for missing user-invocable entirely
            elif not user_inv.get('present') and not user_inv.get('misspelled'):
                issues.append(
                    {
                        'type': 'missing-user-invocable',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': 'Skill missing required `user-invocable` field',
                    }
                )

            # Check for invokable value vs content-mode mismatch
            content_mode = analysis.get('content_mode', {})
            if user_inv.get('present') and user_inv.get('value') is True and content_mode.get('is_reference'):
                issues.append(
                    {
                        'type': 'skill-invokable-mismatch',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': 'Skill declares REFERENCE MODE but has `user-invocable: true` — reference skills should be `false`',
                    }
                )

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

    # mark-step-done argument validation (phase-6 finalize step termination)
    _mark_step_done_descriptions = {
        'MARK_STEP_DONE_BAD_NOTATION': (
            'mark-step-done invocation uses hyphenated notation '
            '`manage-status:manage-status` instead of `manage-status:manage_status`'
        ),
        'MARK_STEP_DONE_MISSING_PHASE': 'mark-step-done invocation is missing required `--phase` argument',
        'MARK_STEP_DONE_MISSING_OUTCOME': 'mark-step-done invocation is missing required `--outcome` argument',
    }
    for violation in rules.get('mark_step_done_violations', []):
        code = violation.get('code', '')
        issues.append(
            {
                'type': code,
                'file': file_path,
                'line': violation.get('line'),
                'severity': 'error',
                'fixable': False,
                'description': _mark_step_done_descriptions.get(code, f'mark-step-done defect: {code}'),
                'details': violation,
            }
        )

    # skill-resolver-gap (warning) — LLM-Glob discovery prose without an
    # adjacent resolver call. Driven by the analyzer in _analyze_markdown.py,
    # surfaced here as standard issue dicts.
    for violation in rules.get('resolver_gap_violations', []):
        issues.append(
            {
                'type': 'skill-resolver-gap',
                'rule_id': 'skill-resolver-gap',
                'file': file_path,
                'line': violation.get('line'),
                'severity': 'warning',
                'fixable': False,
                'description': violation.get(
                    'message',
                    'LLM-Glob discovery prose without adjacent resolver call (skill-resolver-gap)',
                ),
                'details': violation,
            }
        )

    # --display-detail ASCII contract validation (phase-6 finalize renderer)
    _display_detail_descriptions = {
        'DISPLAY_DETAIL_NON_ASCII': '--display-detail value contains non-ASCII characters (chars > 0x7F)',
        'DISPLAY_DETAIL_TOO_LONG': '--display-detail value exceeds 80 characters',
        'DISPLAY_DETAIL_MULTILINE': '--display-detail value contains a newline (must be single-line)',
        'DISPLAY_DETAIL_TRAILING_PERIOD': '--display-detail value ends with a trailing period',
    }
    for violation in rules.get('display_detail_violations', []):
        code = violation.get('code', '')
        value = violation.get('value', '')
        base_desc = _display_detail_descriptions.get(code, f'--display-detail defect: {code}')
        issues.append(
            {
                'type': code,
                'file': file_path,
                'line': violation.get('line'),
                'severity': 'error',
                'fixable': False,
                'description': f'{base_desc}: "{value}"',
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

    # Check checklist patterns
    checklists = analysis.get('checklist_patterns', {})
    if checklists.get('has_checklists'):
        issues.append(
            {
                'type': 'checklist-pattern',
                'file': file_path,
                'severity': 'warning',
                'fixable': True,
                'description': f'Checkbox patterns in LLM-consumed file ({checklists["count"]} items)',
                'count': checklists['count'],
                'sections': checklists.get('sections', []),
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
                issues.append(
                    {
                        'type': 'subdoc-bloat',
                        'classification': bloat_class,
                        'line_count': line_count,
                    }
                )
            if has_forbidden:
                issues.append(
                    {
                        'type': 'subdoc-forbidden-metadata',
                        'sections': forbidden_sections,
                    }
                )

            # Hardcoded script paths
            if re.search(r'python3 .*/scripts/|bash .*/scripts/|\{[^}]+\}/scripts/', content):
                if not re.search(r'Skill:.*script-runner', content):
                    issues.append(
                        {
                            'type': 'subdoc-hardcoded-script-path',
                        }
                    )

            # Checklist patterns
            checklist_info = check_checklist_patterns(content, str(md_file))
            if checklist_info['has_checklists']:
                issues.append(
                    {
                        'type': 'subdoc-checklist-pattern',
                        'count': checklist_info['count'],
                        'sections': checklist_info.get('sections', []),
                    }
                )

            # skill-resolver-gap: LLM-Glob discovery prose without adjacent
            # resolver call. Restricted to standards/*.md per rule scope.
            if subdir_name == 'standards':
                resolver_gap_findings = check_resolver_gap(content, str(md_file))
                for finding in resolver_gap_findings:
                    issues.append(
                        {
                            'type': 'skill-resolver-gap',
                            'line': finding.get('line'),
                            'message': finding.get('message'),
                            'pattern': finding.get('pattern'),
                        }
                    )

            # --display-detail ASCII contract validation (phase-6 finalize renderer)
            for violation in check_display_detail_violations(content):
                issues.append(
                    {
                        'type': 'subdoc-display-detail-violation',
                        'code': violation.get('code'),
                        'line': violation.get('line'),
                        'value': violation.get('value', ''),
                    }
                )

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
                issues.append(
                    {
                        'type': 'subdoc-bloat',
                        'file': file_path,
                        'severity': 'warning' if issue['classification'] == 'BLOATED' else 'error',
                        'fixable': False,
                        'classification': issue['classification'],
                        'line_count': issue['line_count'],
                        'description': f'Sub-document bloat ({issue["classification"]}, {issue["line_count"]} lines)',
                    }
                )
            elif issue['type'] == 'subdoc-forbidden-metadata':
                issues.append(
                    {
                        'type': 'subdoc-forbidden-metadata',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': f'Forbidden metadata sections: {issue["sections"]}',
                    }
                )
            elif issue['type'] == 'subdoc-hardcoded-script-path':
                issues.append(
                    {
                        'type': 'subdoc-hardcoded-script-path',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': False,
                        'description': 'Hardcoded script path in sub-document',
                    }
                )
            elif issue['type'] == 'subdoc-checklist-pattern':
                issues.append(
                    {
                        'type': 'subdoc-checklist-pattern',
                        'file': file_path,
                        'severity': 'warning',
                        'fixable': True,
                        'description': f'Checkbox patterns in sub-document ({issue["count"]} items)',
                        'count': issue['count'],
                        'sections': issue.get('sections', []),
                    }
                )
            elif issue['type'] == 'skill-resolver-gap':
                issues.append(
                    {
                        'type': 'skill-resolver-gap',
                        'rule_id': 'skill-resolver-gap',
                        'file': file_path,
                        'line': issue.get('line'),
                        'severity': 'warning',
                        'fixable': False,
                        'description': issue.get(
                            'message',
                            'LLM-Glob discovery prose without adjacent resolver call (skill-resolver-gap)',
                        ),
                        'details': issue,
                    }
                )
            elif issue['type'] == 'subdoc-display-detail-violation':
                code = issue.get('code', '')
                value = issue.get('value', '')
                issues.append(
                    {
                        'type': code,
                        'file': file_path,
                        'line': issue.get('line'),
                        'severity': 'error',
                        'fixable': False,
                        'description': f'display_detail violation ({code}) at line {issue.get("line")}: "{value}"',
                    }
                )

    return issues


# =============================================================================
# argparse_safety rule (marketplace-wide static check)
# =============================================================================


def _is_test_path(path: Path) -> bool:
    """Return True if the path is a test file or lives under a test directory.

    Matches:
    - Any path component named ``test`` or ``tests``
    - Filenames matching ``test_*.py`` or ``*_test.py``
    """
    name = path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return True
    for part in path.parts:
        if part in ('test', 'tests'):
            return True
    return False


def _call_has_allow_abbrev_false(node: ast.Call) -> bool:
    """Return True if an ``ast.Call`` includes ``allow_abbrev=False``."""
    for kw in node.keywords:
        if kw.arg != 'allow_abbrev':
            continue
        value = kw.value
        if isinstance(value, ast.Constant) and value.value is False:
            return True
    return False


def _call_func_name(node: ast.Call) -> str | None:
    """Extract the callable's short name from an ``ast.Call``.

    Handles both ``ArgumentParser(...)`` (``ast.Name``) and
    ``argparse.ArgumentParser(...)`` / ``subparsers.add_parser(...)``
    (``ast.Attribute``) call shapes.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _scan_file_for_argparse_safety(file_path: Path) -> list[dict]:
    """Scan a single Python file for argparse calls missing ``allow_abbrev=False``.

    Returns a list of issue dicts (empty if the file has no violations, is
    unreadable, or fails to parse).
    """
    try:
        source = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    issues: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_func_name(node)
        if name not in _ARGPARSE_SAFETY_CONSTRUCTORS:
            continue
        if _call_has_allow_abbrev_false(node):
            continue
        issues.append(
            {
                'type': 'argparse_safety',
                'file': str(file_path),
                'line': node.lineno,
                'severity': 'error',
                'fixable': False,
                'description': 'Add allow_abbrev=False to this argparse call',
                'call': name,
            }
        )
    return issues


def _iter_argparse_safety_targets(marketplace_root: Path) -> list[Path]:
    """Enumerate Python files subject to the argparse_safety rule.

    Scope:
    - ``<marketplace_root>/*/skills/*/scripts/**/*.py`` (marketplace bundle scripts)
    - ``<marketplace_root>/../adapters/**/*.py`` (adapter tree)

    Tests (files under ``test/``/``tests/`` directories, or named
    ``test_*.py`` / ``*_test.py``) are excluded — they may intentionally
    exercise argparse default behavior.
    """
    targets: list[Path] = []

    # Marketplace bundle scripts
    if marketplace_root.is_dir():
        for py_file in marketplace_root.glob('*/skills/*/scripts/**/*.py'):
            if py_file.is_file() and not _is_test_path(py_file):
                targets.append(py_file)

    # Adapter tree (lives alongside bundles/)
    adapters_root = marketplace_root.parent / 'adapters'
    if adapters_root.is_dir():
        for py_file in adapters_root.rglob('*.py'):
            if py_file.is_file() and not _is_test_path(py_file):
                targets.append(py_file)

    return sorted(set(targets))


def scan_argparse_safety(marketplace_root: Path) -> list[dict]:
    """Static-scan the marketplace tree for argparse calls missing
    ``allow_abbrev=False``.

    Each finding is a dict with: ``type=argparse_safety``, ``file``,
    ``line``, ``severity=error``, ``fixable=False``, ``description``, and
    ``call`` (``ArgumentParser`` or ``add_parser``).

    See rule-catalog.md (argparse_safety) and lesson 2026-04-17-012 for
    rationale. The check is a lightweight AST walk — no parser is executed.
    """
    findings: list[dict] = []
    for target in _iter_argparse_safety_targets(marketplace_root):
        findings.extend(_scan_file_for_argparse_safety(target))
    return findings
