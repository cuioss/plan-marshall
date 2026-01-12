#!/usr/bin/env python3
"""Tool coverage analysis subcommand."""

import json
import re
import sys
from pathlib import Path

from _analyze_shared import extract_frontmatter


def extract_content_after_frontmatter(content: str) -> str:
    """Extract content after frontmatter."""
    match = re.match(r'^---\s*\n.*?\n---\s*\n?(.*)', content, re.DOTALL)
    if match:
        return match.group(1)
    return content


def parse_declared_tools(frontmatter: str) -> list[str]:
    """Parse tools from frontmatter.

    Handles both 'tools:' and 'allowed-tools:' field names,
    and both inline (comma-separated) and YAML list (- item) formats.
    """
    tools_match = re.search(r'^(?:tools|allowed-tools):[ \t]*(.*)$', frontmatter, re.MULTILINE)
    if not tools_match:
        return []

    tools_line = tools_match.group(1).strip()

    # If inline format (tools: Read, Write, Edit)
    if tools_line:
        return [t.strip() for t in tools_line.replace(',', ' ').split() if t.strip()]

    # Otherwise check for YAML list format (- Read\n- Write)
    lines = frontmatter.split('\n')
    tools = []
    in_tools_section = False
    for line in lines:
        if re.match(r'^(?:tools|allowed-tools):', line):
            in_tools_section = True
            continue
        if in_tools_section:
            list_match = re.match(r'^\s+-\s*(.+)$', line)
            if list_match:
                tools.append(list_match.group(1).strip())
            elif line.strip() and not line.startswith(' '):
                break
    return tools


def find_maven_calls(content: str) -> list[dict]:
    """Find Maven call patterns in content."""
    maven_calls = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        if re.search(r'Bash.*mvn|Bash.*./mvnw|Bash.*maven', line, re.IGNORECASE):
            maven_calls.append({'line': i, 'text': line.strip()})

    return maven_calls


def find_backup_patterns(content: str) -> list[dict]:
    """Find backup file patterns in content."""
    backup_patterns = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        if re.search(r'\.backup|\.bak|\.old|\.orig', line):
            backup_patterns.append({'line': i, 'pattern': line.strip()})

    return backup_patterns


def analyze_tool_coverage(file_path: Path) -> dict:
    """Analyze tool declarations in file (deterministic only).

    NOTE: This function only extracts declared tools from frontmatter.
    Semantic analysis of tool USAGE (missing/unused detection) is delegated
    to the LLM via tool-coverage-agent for accurate context understanding.

    Returns declared tools and structural info for LLM analysis.
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except (OSError, IOError) as e:
        return {'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)
    if not frontmatter_present:
        return {'error': 'No frontmatter found'}

    declared_tools = parse_declared_tools(frontmatter)
    declared_count = len(declared_tools)

    # Rule 6 check: Task in agent frontmatter (deterministic - just check declaration)
    has_task_declared = 'Task' in declared_tools or 'task' in [t.lower() for t in declared_tools]

    # Structural checks only (no semantic tool usage detection)
    maven_calls = find_maven_calls(content)
    backup_patterns = find_backup_patterns(content)

    return {
        'file_path': str(file_path),
        'tool_coverage': {
            'declared_count': declared_count,
            'declared_tools': declared_tools,
            'needs_llm_analysis': True
        },
        'critical_violations': {
            'has_task_declared': has_task_declared,
            'maven_calls': maven_calls,
            'backup_file_patterns': backup_patterns
        }
    }


def cmd_coverage(args) -> int:
    """Analyze tool coverage in file."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(json.dumps({'error': f'File not found: {args.file}'}), file=sys.stderr)
        return 1

    if not file_path.is_file():
        print(json.dumps({'error': f'Not a file: {args.file}'}), file=sys.stderr)
        return 1

    result = analyze_tool_coverage(file_path)

    if 'error' in result:
        print(json.dumps(result), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0
