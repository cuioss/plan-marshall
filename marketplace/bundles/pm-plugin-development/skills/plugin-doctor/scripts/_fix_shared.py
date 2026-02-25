#!/usr/bin/env python3
"""Shared constants and functions for fix subcommands."""

import json
import re
import sys

# =============================================================================
# Constants
# =============================================================================

# Issue types that can be fixed automatically or with user confirmation
FIXABLE_ISSUE_TYPES = {
    # Safe fixes (auto-applicable)
    'missing-frontmatter',
    'invalid-yaml',
    'missing-name-field',
    'missing-description-field',
    'missing-tools-field',
    'array-syntax-tools',
    'trailing-whitespace',
    'improper-indentation',
    'missing-blank-line-before-list',
    'agent-skill-tool-visibility',
    'subdoc-forbidden-metadata',
    # Risky fixes (require confirmation)
    'unused-tool-declared',
    'tool-not-declared',
    'agent-task-tool-prohibited',
    'agent-maven-restricted',
    'agent-lessons-via-skill',
    'backup-file-pattern',
    'ci-rule-self-update',
}

# Safe fix types - can be auto-applied without user confirmation
SAFE_FIX_TYPES = {
    'missing-frontmatter',
    'invalid-yaml',
    'missing-name-field',
    'missing-description-field',
    'missing-tools-field',
    'array-syntax-tools',
    'trailing-whitespace',
    'improper-indentation',
    'missing-blank-line-before-list',
    'agent-skill-tool-visibility',
    'subdoc-forbidden-metadata',
}

# Risky fix types - require user confirmation
RISKY_FIX_TYPES = {
    'unused-tool-declared',
    'tool-not-declared',
    'agent-task-tool-prohibited',
    'agent-maven-restricted',
    'agent-lessons-via-skill',
    'backup-file-pattern',
    'ci-rule-self-update',

    'subdoc-hardcoded-script-path',
}

# Backward-compatibility aliases: old identifier → new identifier.
# Allows external consumers to use old names during migration.
RULE_ID_ALIASES = {
    'rule-6-violation': 'agent-task-tool-prohibited',
    'rule-7-violation': 'agent-maven-restricted',
    'rule-8-violation': 'workflow-hardcoded-script-path',
    'rule-11-violation': 'agent-skill-tool-visibility',
    'rule-12-violation': 'workflow-prose-parameter-inconsistency',
    'pattern-22-violation': 'agent-lessons-via-skill',
}


def resolve_issue_type(issue_type: str) -> str:
    """Resolve an issue type, accepting old aliases for backward compatibility."""
    return RULE_ID_ALIASES.get(issue_type, issue_type)


# =============================================================================
# Shared Functions
# =============================================================================


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from content."""
    if not content.startswith('---'):
        return False, ''

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        return True, match.group(1)
    return False, ''


def read_json_input(input_file: str) -> tuple[dict | None, str | None]:
    """Read and parse JSON from file or stdin."""
    try:
        if input_file == '-':
            content = sys.stdin.read()
        else:
            with open(input_file, encoding='utf-8') as f:
                content = f.read()

        if not content.strip():
            return {}, None

        return json.loads(content), None
    except FileNotFoundError:
        return None, f'File not found: {input_file}'
    except json.JSONDecodeError as e:
        return None, f'Invalid JSON: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'
