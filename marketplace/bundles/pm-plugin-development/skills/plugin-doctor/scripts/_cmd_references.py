#!/usr/bin/env python3
"""References subcommand for validating plugin references in markdown files."""

import json
import re
import sys
from pathlib import Path


def detect_file_type(file_path: str) -> str:
    """Detect if file is agent, command, or skill."""
    if "/agents/" in file_path:
        return "agent"
    elif "/commands/" in file_path:
        return "command"
    elif "/skills/" in file_path:
        return "skill"
    return "unknown"


def pre_filter_documentation_lines(content: str) -> set[int]:
    """Pre-filter documentation lines to exclude from reference detection."""
    lines = content.split('\n')
    excluded = set()

    in_example = False
    in_workflow_step = False
    in_related = False
    example_level = 0

    for i, line in enumerate(lines):
        example_match = re.match(r'^(#{2,3})\s+(Example|Usage|Demonstration|USAGE|EXAMPLES)', line, re.IGNORECASE)
        if example_match:
            in_example = True
            example_level = len(example_match.group(1))
            excluded.add(i)
            continue

        if in_example:
            header_match = re.match(r'^(#{2,3})\s+', line)
            if header_match and len(header_match.group(1)) <= example_level:
                in_example = False
            else:
                excluded.add(i)
                continue

        workflow_match = re.match(r'^(#{2,3})\s+Step\s+\d+:', line)
        if workflow_match:
            in_workflow_step = True
            excluded.add(i)
            continue

        if in_workflow_step:
            header_match = re.match(r'^#{2,3}\s+', line)
            if header_match:
                in_workflow_step = False
            elif re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
                excluded.add(i)
                continue

        if re.search(r'caller can then invoke|invoke `/plugin-update', line, re.IGNORECASE):
            excluded.add(i)
            continue

        if re.match(r'^(Task|Agent|Command):$', line.strip()):
            excluded.add(i)
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].startswith((' ', '\t')):
                    excluded.add(j)
                elif lines[j].strip():
                    break
            continue

        if re.match(r'^#{2,3}\s+(RELATED|SEE ALSO|Related|See Also)', line, re.IGNORECASE):
            in_related = True
            excluded.add(i)
            continue

        if in_related:
            if re.match(r'^#{2,3}\s+', line):
                in_related = False
            else:
                excluded.add(i)
                continue

    return excluded


def extract_references(content: str, excluded_lines: set[int]) -> list[dict]:
    """Extract plugin references from content."""
    lines = content.split('\n')
    references = []

    slash_pattern = re.compile(r'SlashCommand:\s*/([a-z0-9:-]+)')
    task_pattern = re.compile(r'subagent_type[:\s]+["\']?([a-z0-9:-]+)["\']?')
    skill_pattern = re.compile(r'Skill:\s*([a-z0-9:-]+)')

    for i, line in enumerate(lines):
        if i in excluded_lines:
            continue

        for match in slash_pattern.finditer(line):
            references.append({
                "line": i + 1,
                "type": "SlashCommand",
                "reference": f"/{match.group(1)}",
                "raw_text": match.group(0)
            })

        for match in task_pattern.finditer(line):
            references.append({
                "line": i + 1,
                "type": "Task",
                "reference": match.group(1),
                "raw_text": match.group(0)
            })

        for match in skill_pattern.finditer(line):
            references.append({
                "line": i + 1,
                "type": "Skill",
                "reference": match.group(1),
                "raw_text": match.group(0)
            })

    return references


def cmd_references(args) -> int:
    """Validate plugin references in a markdown file."""
    file_path = Path(args.file)

    if not file_path.is_file():
        print(json.dumps({"error": f"File not found: {args.file}"}), file=sys.stderr)
        return 1

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(json.dumps({"error": f"Failed to read file: {str(e)}"}), file=sys.stderr)
        return 1

    file_type = detect_file_type(str(file_path))
    excluded_lines = pre_filter_documentation_lines(content)
    references = extract_references(content, excluded_lines)

    total_lines = len(content.split('\n'))
    excluded_count = len(excluded_lines)
    exclusion_rate = (excluded_count / total_lines * 100) if total_lines > 0 else 0.0

    result = {
        "file_path": str(file_path),
        "file_type": file_type,
        "total_lines": total_lines,
        "references": references,
        "pre_filter": {
            "excluded_lines_count": excluded_count,
            "exclusion_rate": round(exclusion_rate, 1)
        }
    }

    print(json.dumps(result, indent=2))
    return 0
