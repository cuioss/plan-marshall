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


def _frontmatter_declares_forwards_tool_capabilities(frontmatter: str) -> bool:
    """Return True if YAML frontmatter declares ``forwards_tool_capabilities: true``.

    Matches a top-level key on its own line, case-sensitive value ``true``
    (unquoted, as per YAML boolean convention). Quoted forms (``"true"`` or
    ``'true'``) and ``True``/``yes`` are NOT accepted — the canonical form
    enforced by plugin-doctor is the lowercase YAML boolean.
    """
    return bool(
        re.search(
            r'^forwards_tool_capabilities\s*:\s*true\s*$',
            frontmatter,
            re.MULTILINE,
        )
    )


def check_agent_glob_resolver_workaround(file_path: str, content: str) -> list:
    """Check agent-glob-resolver-workaround: agent declares Glob without exemption flag.

    Returns a list of finding dicts ``{line, message}``. Empty when the agent
    does not declare ``Glob`` or declares it together with
    ``forwards_tool_capabilities: true`` in the YAML frontmatter.

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

    # Exemption is declared in the frontmatter as a typed boolean flag
    # `forwards_tool_capabilities: true`. No body scanning — the structural
    # intent is captured by the typed field, not by free-form prose.
    if _frontmatter_declares_forwards_tool_capabilities(frontmatter):
        return findings

    findings.append(
        {
            'line': 1,  # Frontmatter declaration is the offense; anchor at top of file
            'message': (
                'Agent declares `Glob` in tools without `forwards_tool_capabilities: true` '
                'in frontmatter (agent-glob-resolver-workaround)'
            ),
        }
    )
    return findings
