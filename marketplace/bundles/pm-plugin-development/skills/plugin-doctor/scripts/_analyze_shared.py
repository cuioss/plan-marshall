#!/usr/bin/env python3
"""Shared utilities for analyze subcommands."""

import re
from pathlib import Path


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from content."""
    if not content.startswith('---'):
        return False, ''

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        return True, match.group(1)
    return False, ''


def check_yaml_validity(frontmatter: str) -> bool:
    """Basic YAML validity check."""
    return bool(re.search(r'^[a-z_]*:', frontmatter, re.MULTILINE))


def count_lines(file_path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(file_path, encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def detect_component_type(file_path: str) -> str:
    """Detect component type from file path."""
    if '/commands/' in file_path:
        return 'command'
    elif '/agents/' in file_path:
        return 'agent'
    elif '/skills/' in file_path:
        return 'skill'
    return 'unknown'


def remove_code_blocks(content: str) -> str:
    """Remove code blocks from content."""
    result = []
    in_codeblock = False

    for line in content.split('\n'):
        if line.startswith('```'):
            in_codeblock = not in_codeblock
            continue
        if not in_codeblock:
            result.append(line)

    return '\n'.join(result)
