# SPDX-License-Identifier: FSL-1.1-ALv2
"""Frontmatter transform engine for the Antigravity target.

Reads ``mapping.json`` (``tool_permissions``, ``model_map``) and
``frontmatter-rules.json`` (``required_fields``, ``optional_fields``) at
runtime; parses Claude Code-style YAML frontmatter; rewrites it into
Antigravity form (skill/agent/command).

Validation contract:
  * If a frontmatter block is missing any field listed in
    ``required_fields``, raise ``UnmappedFrontmatterError`` so the CLI
    exits with code 2 (silent exclusion is prohibited).
  * If an agent declares a ``tools`` value that has no key in
    ``tool_permissions``, raise ``UnmappedToolError`` so the CLI exits 2.
  * If an agent declares a tool whose ``tool_permissions`` key is present
    with a ``null`` value, that is the target-absent sentinel: the Claude
    tool has no Antigravity analog and contributes no tool entry.

The body of the source markdown is returned untouched — body-text
transforms are owned by the target-shared ``body_transform_engine``.
"""

from __future__ import annotations

import json
from pathlib import Path

# Lookup sentinel distinguishing "key absent from tool_permissions" from
# "key present with a null value".
_TOOL_KEY_MISSING = object()


class UnmappedFrontmatterError(RuntimeError):
    """Raised when a required frontmatter field is missing from a source file."""


class UnmappedToolError(RuntimeError):
    """Raised when an agent's ``tools`` value references an unknown tool."""


def load_mapping(config_dir: Path) -> dict[str, dict]:
    """Load ``mapping.json`` from ``config_dir``."""
    mapping_path = config_dir / 'mapping.json'
    if not mapping_path.exists():
        raise FileNotFoundError(f'Antigravity mapping config not found: {mapping_path}')
    data = json.loads(mapping_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'mapping.json must be a JSON object, got {type(data).__name__}')
    if 'tool_permissions' not in data or 'model_map' not in data:
        raise ValueError(f'mapping.json missing required keys (tool_permissions, model_map): {mapping_path}')
    return data


def load_rules(config_dir: Path) -> dict[str, list[str]]:
    """Load ``frontmatter-rules.json`` from ``config_dir``."""
    rules_path = config_dir / 'frontmatter-rules.json'
    if not rules_path.exists():
        raise FileNotFoundError(f'Antigravity rules config not found: {rules_path}')
    data = json.loads(rules_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'frontmatter-rules.json must be a JSON object, got {type(data).__name__}')
    if 'required_fields' not in data:
        raise ValueError(f'frontmatter-rules.json missing required_fields: {rules_path}')
    return data


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from ``content``.

    Returns ``(fm_dict, body)``. The fm_dict maps each key to a string —
    list-valued fields (``tools``, ``keywords``) are flattened to a
    comma-separated string. Returns ``({}, content)`` when no frontmatter is found.
    """
    if not content.startswith('---\n'):
        return {}, content
    end = content.find('\n---\n', 4)
    if end != -1:
        fm_text = content[4:end].strip()
        body = content[end + len('\n---\n') :].lstrip('\n')
    elif content.endswith('\n---'):
        fm_text = content[4 : len(content) - len('\n---')].strip()
        body = ''
    else:
        return {}, content

    fm: dict[str, str] = {}
    current_key = ''
    current_value = ''
    in_multiline = False
    list_items: list[str] = []
    in_list = False

    for line in fm_text.split('\n'):
        stripped = line.strip()

        if stripped.startswith('- ') and in_list:
            list_items.append(stripped[2:])
            continue

        if in_list and not stripped.startswith('- '):
            fm[current_key] = ', '.join(list_items)
            in_list = False
            list_items = []

        if in_multiline:
            if ':' in stripped and not line.startswith(' ') and not stripped.startswith('-'):
                fm[current_key] = current_value.strip()
                in_multiline = False
            else:
                current_value += '\n' + line
                continue

        if ':' not in stripped:
            continue

        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip()

        if not value:
            current_key = key
            in_list = True
            list_items = []
            continue

        if value == '|':
            current_key = key
            current_value = ''
            in_multiline = True
            continue

        fm[key] = value

    if in_multiline:
        fm[current_key] = current_value.strip()
    if in_list and list_items:
        fm[current_key] = ', '.join(list_items)

    return fm, body


def _ensure_required(fm: dict[str, str], rules: dict[str, list[str]], source: str) -> None:
    missing = [field for field in rules.get('required_fields', []) if not fm.get(field)]
    if missing:
        raise UnmappedFrontmatterError(f'{source}: missing required frontmatter field(s): {", ".join(missing)}')


def _resolve_model(value: str, model_map: dict[str, dict]) -> str | None:
    """Resolve a Claude model alias to an Antigravity model identifier."""
    if not value:
        return None
    entry = model_map.get(value)
    if entry is None:
        return value
    if not isinstance(entry, dict) or 'id' not in entry:
        return value
    return str(entry['id'])


def _split_tools(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(',') if token.strip()]


def _yaml_quote(value: str) -> str:
    """Safely quote a string for inclusion as a YAML scalar value."""
    if not value:
        return '""'
    if any(c in value for c in (':', '"', "'", '#', '\n', '@', '`', '*', '&', '{', '}', '[', ']')) or value.startswith(('-', '?', ':', ' ')):
        return json.dumps(value)
    return value


def transform_skill_frontmatter(
    fm: dict[str, str],
    bundle: str,
    skill_name: str,
    rules: dict[str, list[str]],
    *,
    source_label: str | None = None,
) -> str:
    """Transform Claude skill frontmatter into Antigravity form."""
    label = source_label or f'{bundle}/{skill_name}'
    _ensure_required(fm, rules, label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = [
        '---',
        f'name: {bundle}-{skill_name}',
        f'description: {_yaml_quote(desc)}',
        'compatibility: Adapted from plan-marshall marketplace (Claude Code native)',
        '---',
    ]
    return '\n'.join(lines)


def transform_agent_frontmatter(
    fm: dict[str, str],
    mapping: dict[str, dict],
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> str:
    """Transform Claude agent frontmatter into Antigravity form."""
    _ensure_required(fm, rules, source_label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = ['---', f'description: {_yaml_quote(desc)}', 'mode: subagent']

    model_value = fm.get('model', '')
    if model_value:
        resolved = _resolve_model(model_value, mapping['model_map'])
        if resolved:
            lines.append(f'model: {resolved}')

    effort_value = fm.get('effort', '')
    if effort_value:
        lines.append(f'effort: {effort_value}')

    tools_raw = fm.get('tools', '')
    if tools_raw:
        tools: list[str] = []
        unknown: list[str] = []
        seen: set[str] = set()
        for tool in _split_tools(tools_raw):
            mapped = mapping['tool_permissions'].get(tool, _TOOL_KEY_MISSING)
            if mapped is _TOOL_KEY_MISSING:
                unknown.append(tool)
                continue
            if mapped is None:
                continue
            if mapped in seen:
                continue
            seen.add(mapped)
            tools.append(mapped)
        if unknown:
            raise UnmappedToolError(f'{source_label}: unmapped tool(s) in frontmatter: {", ".join(unknown)}')
        if tools:
            lines.append('tools:')
            for t in sorted(tools):
                lines.append(f'  - {t}')

    lines.append('---')
    return '\n'.join(lines)


def transform_command_frontmatter(
    fm: dict[str, str],
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> str:
    """Transform Claude command frontmatter into Antigravity form."""
    _ensure_required(fm, rules, source_label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = ['---', f'description: {desc}', '---']
    return '\n'.join(lines)


__all__ = [
    'UnmappedFrontmatterError',
    'UnmappedToolError',
    'load_mapping',
    'load_rules',
    'parse_frontmatter',
    'transform_agent_frontmatter',
    'transform_command_frontmatter',
    'transform_skill_frontmatter',
]
