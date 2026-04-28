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


def _frontmatter_declares_glob_tool(frontmatter: str) -> bool:
    """Return True if YAML frontmatter ``tools:`` field includes ``Glob`` token.

    Handles both inline form ``tools: Read, Write, Glob`` and YAML block-list
    form (``tools:`` followed by ``  - Glob`` lines). Word-bounded match prevents
    substring false positives (e.g., "GlobalState" would not match).
    """
    inline_match = re.search(r'^tools:\s*(.+)$', frontmatter, re.MULTILINE)
    if inline_match:
        inline_value = inline_match.group(1).strip()
        # Inline form may still spill into block-list (e.g., "tools:" then "  - Glob")
        if inline_value:
            # Strip optional brackets and split on commas
            stripped = inline_value.strip('[]')
            tokens = [t.strip().strip('"').strip("'") for t in stripped.split(',')]
            if 'Glob' in tokens:
                return True

    # Block-list form: walk lines after ``tools:`` until indentation breaks
    lines = frontmatter.split('\n')
    in_tools_block = False
    for line in lines:
        if re.match(r'^tools:\s*$', line):
            in_tools_block = True
            continue
        if in_tools_block:
            # Block items are indented dash lists; stop on a top-level key
            if re.match(r'^\s*-\s*Glob\s*$', line):
                return True
            if re.match(r'^[A-Za-z_][A-Za-z0-9_-]*:', line):
                # New top-level field — block ended
                in_tools_block = False

    return False


def check_agent_glob_resolver_workaround(file_path: str, content: str) -> list:
    """Check agent-glob-resolver-workaround: agent declares Glob without exemption marker.

    Returns a list of finding dicts ``{line, message}``. Empty when the agent
    does not declare ``Glob`` or declares it together with a non-empty
    ``# resolver-glob-exempt: <justification>`` marker in the body.

    Detection scope is enforced by the caller (only ``agents/*.md`` files);
    this function inspects content unconditionally so it can be unit tested
    in isolation.
    """
    findings: list = []

    # Extract frontmatter; bail out if missing
    has_frontmatter, frontmatter = extract_frontmatter(content)
    if not has_frontmatter:
        return findings

    if not _frontmatter_declares_glob_tool(frontmatter):
        return findings

    # Body = content after the closing frontmatter delimiter
    body_match = re.match(r'^---\s*\n.*?\n---\s*\n?(.*)$', content, re.DOTALL)
    body = body_match.group(1) if body_match else ''

    # Look for `# resolver-glob-exempt: <non-empty>` on a single line.
    # Use [^\S\n] for "horizontal whitespace only" so `\s*` cannot eat newlines
    # and let an empty marker on one line accidentally bind to body text on
    # subsequent lines.
    exempt_match = re.search(
        r'^#[^\S\n]*resolver-glob-exempt[^\S\n]*:[^\S\n]*(\S[^\n]*)?$',
        body,
        re.MULTILINE,
    )
    if exempt_match and exempt_match.group(1):
        justification = exempt_match.group(1).strip()
        if justification:
            return findings

    findings.append(
        {
            'line': 1,  # Frontmatter declaration is the offense; anchor at top of file
            'message': (
                'Agent declares `Glob` in tools without `# resolver-glob-exempt: <justification>` '
                'marker in body (agent-glob-resolver-workaround)'
            ),
        }
    )
    return findings
