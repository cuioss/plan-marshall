#!/usr/bin/env python3
"""Markdown analysis subcommand."""

import json
import re
import sys
from pathlib import Path

from _analyze_shared import check_yaml_validity, detect_component_type, extract_frontmatter


def check_frontmatter_fields(frontmatter: str) -> dict:
    """Check required fields in frontmatter."""
    has_name = bool(re.search(r'^name:', frontmatter, re.MULTILINE))
    has_desc = bool(re.search(r'^description:', frontmatter, re.MULTILINE))

    has_tools = False
    tools_field_type = 'none'

    if re.search(r'^tools:', frontmatter, re.MULTILINE):
        has_tools = True
        tools_field_type = 'tools'
    elif re.search(r'^allowed-tools:', frontmatter, re.MULTILINE):
        has_tools = True
        tools_field_type = 'allowed-tools'

    return {
        'name': {'present': has_name},
        'description': {'present': has_desc},
        'tools': {'present': has_tools, 'field_type': tools_field_type},
    }


def check_continuous_improvement(content: str, component_type: str) -> dict:
    """Check CONTINUOUS IMPROVEMENT RULE presence and pattern."""
    ci_present = bool(re.search(r'CONTINUOUS IMPROVEMENT', content, re.IGNORECASE))
    ci_pattern = 'none'
    pattern_22_violation = False

    if ci_present:
        if re.search(r'/plugin-update-command|/plugin-update-agent', content):
            ci_pattern = 'self-update'
        elif re.search(r'REPORT.*improvement|report.*to.*caller', content, re.IGNORECASE):
            ci_pattern = 'caller-reporting'

        if component_type == 'agent' and ci_pattern == 'self-update':
            pattern_22_violation = True

    return {'present': ci_present, 'format': {'pattern': ci_pattern, 'pattern_22_violation': pattern_22_violation}}


def get_bloat_classification(line_count: int, component_type: str) -> str:
    """Get bloat classification based on line count and component type."""
    if component_type == 'command':
        if line_count > 200:
            return 'CRITICAL'
        elif line_count > 150:
            return 'BLOATED'
        elif line_count > 100:
            return 'LARGE'
    elif component_type == 'skill':
        if line_count > 1200:
            return 'CRITICAL'
        elif line_count > 800:
            return 'BLOATED'
        elif line_count > 400:
            return 'LARGE'
    else:
        if line_count > 800:
            return 'CRITICAL'
        elif line_count > 500:
            return 'BLOATED'
        elif line_count > 300:
            return 'LARGE'

    return 'NORMAL'


def check_execution_patterns(content: str) -> dict:
    """Check for execution patterns in content."""
    return {
        'has_execution_mode': bool(re.search(r'EXECUTION MODE', content, re.IGNORECASE)),
        'has_workflow_tree': bool(re.search(r'Workflow Decision Tree', content, re.IGNORECASE)),
        'mandatory_marker_count': len(re.findall(r'\*\*MANDATORY\*\*', content)),
        'has_handoff_rules': bool(re.search(r'CRITICAL HANDOFF', content, re.IGNORECASE)),
    }


def check_rule_9_violations(content: str) -> list:
    """Check for Rule 9 violations: workflow steps with action verbs but no explicit script calls."""
    violations = []

    action_verbs = [
        'read the',
        'write the',
        'display the',
        'check the',
        'validate the',
        'get the',
        'list the',
        'create the',
        'update the',
        'delete the',
        'read config',
        'read status',
        'read solution',
        'read task',
        'display solution',
        'display status',
        'display config',
    ]

    exempt_patterns = [
        r'Task:',
        r'Skill:',
        r'Read:',
        r'Glob:',
        r'Grep:',
        r'AskUserQuestion',
    ]

    step_pattern = re.compile(r'^###?\s+Step\s+\d+[a-z]?[:\s].*$', re.MULTILINE | re.IGNORECASE)
    step_matches = list(step_pattern.finditer(content))

    for i, match in enumerate(step_matches):
        step_header = match.group(0)
        step_start = match.end()
        step_end = step_matches[i + 1].start() if i + 1 < len(step_matches) else len(content)
        step_content = content[step_start:step_end]

        has_action_verb = False
        found_verb = None
        for verb in action_verbs:
            if verb.lower() in step_content.lower():
                has_action_verb = True
                found_verb = verb
                break

        if not has_action_verb:
            continue

        is_exempt = False
        for pattern in exempt_patterns:
            if re.search(pattern, step_content):
                is_exempt = True
                break

        if is_exempt:
            continue

        has_script_call = bool(re.search(r'execute-script\.py', step_content))

        if not has_script_call:
            violations.append(
                {
                    'step': step_header.strip(),
                    'action_verb': found_verb,
                    'issue': 'Missing explicit script call (execute-script.py) for action verb',
                }
            )

    return violations


def check_rule_violations(content: str, frontmatter: str, component_type: str, has_tools: bool, file_path: str) -> dict:
    """Check for rule violations."""
    rule_6_violation = False
    if component_type == 'agent' and has_tools:
        if re.search(r'^  - Task$|Task,|Task$', frontmatter, re.MULTILINE):
            rule_6_violation = True

    rule_7_violation = False
    if re.search(r'mvn |maven |./mvnw ', content):
        if 'builder-maven' not in file_path:
            pattern = r'^Bash:.*mvn|^Bash:.*maven|^Bash:.*\./mvnw|`.*mvn |`.*\./mvnw |^\s+mvn |^\s+\./mvnw '
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if 'Rule 7' not in match and 'should use' not in match and 'instead of' not in match:
                    rule_7_violation = True
                    break

    rule_8_violation = False
    if re.search(r'python3 .*/scripts/|bash .*/scripts/|\{[^}]+\}/scripts/', content):
        if not re.search(r'Skill:.*script-runner', content):
            rule_8_violation = True

    rule_9_violations = []
    if component_type == 'skill':
        rule_9_violations = check_rule_9_violations(content)

    return {
        'rule_6_violation': rule_6_violation,
        'rule_7_violation': rule_7_violation,
        'rule_8_violation': rule_8_violation,
        'rule_9_violations': rule_9_violations,
    }


def check_forbidden_metadata(content: str) -> tuple[bool, str]:
    """Check for forbidden metadata sections."""
    forbidden_pattern = r'^## (Version|Version History|License|Changelog|Change Log|Author|Revision History)$'
    matches = re.findall(forbidden_pattern, content, re.MULTILINE)

    if matches:
        return True, ','.join(matches)
    return False, ''


def analyze_markdown_file(file_path: Path, component_type: str) -> dict:
    """Analyze markdown file and return results."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'error': f'Failed to read file: {e}'}

    line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)

    if component_type == 'auto':
        component_type = detect_component_type(str(file_path))

    frontmatter_present, frontmatter = extract_frontmatter(content)
    yaml_valid = check_yaml_validity(frontmatter) if frontmatter_present else False
    required_fields = (
        check_frontmatter_fields(frontmatter)
        if frontmatter_present
        else {
            'name': {'present': False},
            'description': {'present': False},
            'tools': {'present': False, 'field_type': 'none'},
        }
    )

    section_count = len(re.findall(r'^## ', content, re.MULTILINE))
    has_param_section = bool(re.search(r'^## PARAMETERS|^### Parameters', content, re.MULTILINE | re.IGNORECASE))
    ci_rule = check_continuous_improvement(content, component_type)
    bloat_class = get_bloat_classification(line_count, component_type)
    exec_patterns = check_execution_patterns(content)
    rules = check_rule_violations(
        content, frontmatter, component_type, required_fields['tools']['present'], str(file_path)
    )
    has_forbidden, forbidden_sections = check_forbidden_metadata(content)

    return {
        'file_path': str(file_path),
        'file_type': {'type': component_type},
        'metrics': {'line_count': line_count},
        'frontmatter': {'present': frontmatter_present, 'yaml_valid': yaml_valid, 'required_fields': required_fields},
        'structure': {'section_count': section_count},
        'parameters': {'has_section': has_param_section},
        'continuous_improvement_rule': ci_rule,
        'bloat': {'classification': bloat_class},
        'execution_patterns': exec_patterns,
        'rules': rules,
        'quality': {'has_forbidden_metadata': has_forbidden, 'forbidden_sections': forbidden_sections},
    }


def cmd_markdown(args) -> int:
    """Analyze markdown file structure and compliance."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(json.dumps({'error': f'File not found: {args.file}'}), file=sys.stderr)
        return 1

    if not file_path.is_file():
        print(json.dumps({'error': f'Not a file: {args.file}'}), file=sys.stderr)
        return 1

    result = analyze_markdown_file(file_path, args.type)

    if 'error' in result:
        print(json.dumps(result), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0
