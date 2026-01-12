#!/usr/bin/env python3
"""Analyze subcommand for component quality analysis."""

import re
from pathlib import Path

from _maintain_shared import EXIT_SUCCESS, EXIT_ERROR, parse_frontmatter, output_json


def detect_component_type(path: Path) -> str:
    """Detect component type from path."""
    path_str = str(path)
    if '/agents/' in path_str:
        return 'agent'
    elif '/commands/' in path_str:
        return 'command'
    elif '/skills/' in path_str or path.name == 'SKILL.md':
        return 'skill'
    return 'unknown'


def check_sections(body: str) -> dict:
    """Check for required and recommended sections."""
    missing_sections = []

    # Count markdown headers
    headers = re.findall(r'^#{1,4}\s+(.+)$', body, re.MULTILINE)
    sections_found = [h.lower() for h in headers]

    # Recommended sections for agents/commands
    recommended = ['purpose', 'workflow', 'examples', 'error handling', 'critical rules']
    for section in recommended:
        if not any(section in s for s in sections_found):
            missing_sections.append(section)

    return {
        'sections_found': len(headers),
        'missing_sections': missing_sections
    }


def check_bloat(body: str, total_lines: int) -> list:
    """Check for bloat indicators."""
    issues = []

    if total_lines > 800:
        issues.append({
            'type': 'bloat',
            'severity': 'high',
            'message': f'Component has {total_lines} lines (>800 threshold)',
            'location': 'entire file'
        })
    elif total_lines > 500:
        issues.append({
            'type': 'bloat',
            'severity': 'medium',
            'message': f'Component has {total_lines} lines (approaching 800 threshold)',
            'location': 'entire file'
        })

    # Check for duplicate content patterns
    paragraphs = re.split(r'\n\n+', body)
    seen_content = set()
    for i, para in enumerate(paragraphs):
        para_clean = ' '.join(para.split()).lower()
        if len(para_clean) > 100:  # Only check substantial paragraphs
            if para_clean in seen_content:
                issues.append({
                    'type': 'duplicate-content',
                    'severity': 'medium',
                    'message': 'Duplicate paragraph detected',
                    'location': f'paragraph {i+1}'
                })
            seen_content.add(para_clean)

    return issues


def check_tool_compliance(frontmatter: dict | None, body: str) -> list:
    """Check for tool compliance issues."""
    issues = []

    if frontmatter is None:
        return issues

    tools_raw = frontmatter.get('tools', '')

    # Check for array syntax
    if isinstance(tools_raw, dict) and tools_raw.get('is_array'):
        issues.append({
            'type': 'tool-compliance',
            'severity': 'medium',
            'message': 'Tools use array syntax instead of comma-separated',
            'location': 'frontmatter'
        })
        tools_str = tools_raw.get('value', '')[1:-1]  # Remove []
    else:
        tools_str = str(tools_raw)

    tools = [t.strip() for t in tools_str.split(',') if t.strip()]

    # Rule 6: Agents should not use Task tool
    if 'Task' in tools:
        issues.append({
            'type': 'rule-6-violation',
            'severity': 'high',
            'message': 'Agent declares Task tool (Rule 6 violation)',
            'location': 'frontmatter tools'
        })

    return issues


def calculate_quality_score(frontmatter: dict | None, body: str, issues: list) -> int:
    """Calculate quality score 0-100."""
    score = 100

    # No frontmatter is critical
    if frontmatter is None:
        score -= 30
    else:
        # Missing required fields
        if 'name' not in frontmatter:
            score -= 10
        if 'description' not in frontmatter:
            score -= 10

    # Deduct for issues
    for issue in issues:
        if issue['severity'] == 'high':
            score -= 15
        elif issue['severity'] == 'medium':
            score -= 8
        elif issue['severity'] == 'low':
            score -= 3

    return max(0, min(100, score))


def generate_suggestions(frontmatter: dict | None, body: str, issues: list, section_info: dict) -> list:
    """Generate improvement suggestions."""
    suggestions = []

    if frontmatter is None:
        suggestions.append('Add YAML frontmatter with name, description, and tools fields')

    for section in section_info.get('missing_sections', []):
        suggestions.append(f'Add missing {section} section')

    for issue in issues:
        if issue['type'] == 'bloat':
            suggestions.append('Consider splitting into smaller components or extracting to skill')
        elif issue['type'] == 'rule-6-violation':
            suggestions.append('Remove Task tool from agent - agents should be self-contained')
        elif issue['type'] == 'duplicate-content':
            suggestions.append('Remove duplicate content to reduce bloat')

    return list(set(suggestions))  # Deduplicate


def analyze_component(component_path: str) -> dict:
    """Main analysis function."""
    path = Path(component_path)

    if not path.exists():
        return {
            'error': f'File not found: {component_path}',
            'component_path': component_path
        }

    content = path.read_text()
    lines = content.split('\n')
    total_lines = len(lines)

    frontmatter, body = parse_frontmatter(content)
    component_type = detect_component_type(path)

    # Calculate frontmatter lines
    fm_lines = 0
    if frontmatter is not None:
        for i, line in enumerate(lines):
            if i > 0 and line.strip() == '---':
                fm_lines = i + 1
                break

    # Perform checks
    issues = []

    if frontmatter is None:
        issues.append({
            'type': 'missing-frontmatter',
            'severity': 'high',
            'message': 'Component is missing YAML frontmatter',
            'location': 'file start'
        })

    section_info = check_sections(body)
    issues.extend(check_bloat(body, total_lines))
    issues.extend(check_tool_compliance(frontmatter, body))

    quality_score = calculate_quality_score(frontmatter, body, issues)
    suggestions = generate_suggestions(frontmatter, body, issues, section_info)

    return {
        'component_path': component_path,
        'component_type': component_type,
        'quality_score': quality_score,
        'issues': issues,
        'suggestions': suggestions,
        'stats': {
            'total_lines': total_lines,
            'frontmatter_lines': fm_lines,
            'body_lines': total_lines - fm_lines,
            'sections': section_info['sections_found']
        }
    }


def cmd_analyze(args) -> int:
    """Handle analyze subcommand."""
    result = analyze_component(args.component)
    output_json(result)
    return EXIT_SUCCESS if 'error' not in result else EXIT_ERROR
