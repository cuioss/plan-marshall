#!/usr/bin/env python3
"""Shared utilities for maintain subcommands."""

import json
from typing import Any

EXIT_SUCCESS = 0
EXIT_ERROR = 1


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from content. Returns (frontmatter_dict, body)."""
    if not content.startswith('---'):
        return None, content

    # Find closing ---
    lines = content.split('\n')
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break

    if end_idx == -1:
        return None, content

    # Parse YAML (simple key: value parsing)
    frontmatter: dict[str, Any] = {}
    for line in lines[1:end_idx]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            # Detect array syntax
            if value.startswith('[') and value.endswith(']'):
                frontmatter[key] = {'value': value, 'is_array': True}
            else:
                frontmatter[key] = value

    body = '\n'.join(lines[end_idx + 1:])
    return frontmatter, body


def output_json(data: dict) -> None:
    """Output JSON result to stdout."""
    print(json.dumps(data, indent=2))
