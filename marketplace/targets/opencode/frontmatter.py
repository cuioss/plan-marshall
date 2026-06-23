# SPDX-License-Identifier: FSL-1.1-ALv2
"""Frontmatter transform engine for the OpenCode target.

Reads ``mapping.json`` (``tool_permissions``, ``model_map``) and
``frontmatter-rules.json`` (``required_fields``, ``optional_fields``) at
runtime; parses Claude Code-style YAML frontmatter; rewrites it into
OpenCode form (skill/agent/command).

``mapping.json::model_map`` entries are objects of shape
``{"id": "<unprefixed-model-id>", "supports_effort": ["medium", "high",
...]}``. The OpenCode emitter consumes ``id`` and prepends
``OPENCODE_MODEL_PREFIX``; the ``supports_effort`` array is consumed by
the Claude target's ``variant_emitter.supports_effort`` build-time
guard.

Validation contract:
  * If a frontmatter block is missing any field listed in
    ``required_fields``, raise ``UnmappedFrontmatterError`` so the CLI
    exits with code 2 (silent exclusion is prohibited).
  * If an agent declares a ``tools`` value that has no entry in
    ``tool_permissions``, raise ``UnmappedToolError`` so the CLI exits 2.

The body of the source markdown is returned untouched — body-text
transforms are owned by ``body-transforms.py`` in deliverable 4.
"""

from __future__ import annotations

import json
from pathlib import Path

# OpenCode provider prefix. ``mapping.json`` model_map entries are
# objects of shape ``{"id": "<unprefixed-model-id>", "supports_effort":
# ["medium", "high", ...]}``. The emitter prepends this prefix to the
# resolved ``id`` so the configured ``opencode.json`` references resolve
# through OpenCode's provider system. The ``supports_effort`` array is
# consumed by the Claude target's ``variant_emitter.supports_effort``
# guard — the OpenCode adapter itself only consumes ``id``.
OPENCODE_MODEL_PREFIX = 'anthropic/'

# Tools that fall back to a list-style permission entry rather than a
# single-permission grant. Currently every Claude tool maps to a single
# OpenCode permission category, so this stays empty by default.
LIST_PERMISSION_TOOLS: frozenset[str] = frozenset()


class UnmappedFrontmatterError(RuntimeError):
    """Raised when a required frontmatter field is missing from a source file."""


class UnmappedToolError(RuntimeError):
    """Raised when an agent's ``tools`` value references an unknown tool."""


def load_mapping(config_dir: Path) -> dict[str, dict]:
    """Load ``mapping.json`` from ``config_dir``.

    Returns a dict with two top-level keys: ``tool_permissions`` (Claude
    tool name → OpenCode permission) and ``model_map`` (Claude alias →
    ``{"id": "<unprefixed-model-id>", "supports_effort": [...]}`` object).
    The ``id`` is prefixed by the OpenCode emitter; the ``supports_effort``
    array is consumed by the Claude target's per-effort capability guard.
    """
    mapping_path = config_dir / 'mapping.json'
    if not mapping_path.exists():
        raise FileNotFoundError(f'OpenCode mapping config not found: {mapping_path}')
    data = json.loads(mapping_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'mapping.json must be a JSON object, got {type(data).__name__}')
    if 'tool_permissions' not in data or 'model_map' not in data:
        raise ValueError(
            f'mapping.json missing required keys (tool_permissions, model_map): {mapping_path}'
        )
    return data


def load_rules(config_dir: Path) -> dict[str, list[str]]:
    """Load ``frontmatter-rules.json`` from ``config_dir``.

    Returns a dict with two top-level keys: ``required_fields`` and
    ``optional_fields``.
    """
    rules_path = config_dir / 'frontmatter-rules.json'
    if not rules_path.exists():
        raise FileNotFoundError(f'OpenCode rules config not found: {rules_path}')
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
    comma-separated string so callers do not need to special-case YAML
    list parsing. Returns ``({}, content)`` when no frontmatter is found.
    """
    if not content.startswith('---'):
        return {}, content
    end = content.find('---', 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip('\n')

    fm: dict[str, str] = {}
    current_key = ''
    current_value = ''
    in_multiline = False
    list_items: list[str] = []
    in_list = False

    for line in fm_text.split('\n'):
        stripped = line.strip()

        # Continue a list when the next line is still a list item.
        if stripped.startswith('- ') and in_list:
            list_items.append(stripped[2:])
            continue

        # Close out a list when we hit a non-list line.
        if in_list and not stripped.startswith('- '):
            fm[current_key] = ', '.join(list_items)
            in_list = False
            list_items = []

        # Continue a `|` multiline block until the next top-level key.
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

    # Flush any pending list / multiline value.
    if in_multiline:
        fm[current_key] = current_value.strip()
    if in_list and list_items:
        fm[current_key] = ', '.join(list_items)

    return fm, body


def _ensure_required(fm: dict[str, str], rules: dict[str, list[str]], source: str) -> None:
    missing = [field for field in rules.get('required_fields', []) if not fm.get(field)]
    if missing:
        raise UnmappedFrontmatterError(
            f'{source}: missing required frontmatter field(s): {", ".join(missing)}'
        )


def _resolve_model(value: str, model_map: dict[str, dict]) -> str | None:
    """Resolve a Claude model alias to an OpenCode-prefixed model id.

    ``model_map`` is the ``{alias: {id, supports_effort}}`` shape loaded
    from ``mapping.json``. The function extracts the ``.id`` from the
    matched entry and prefixes it with ``OPENCODE_MODEL_PREFIX``.
    Unmapped values (e.g., already-qualified ``anthropic/...`` strings,
    or a custom override) pass through unchanged.
    """
    if not value:
        return None
    entry = model_map.get(value)
    if entry is None:
        return value
    if not isinstance(entry, dict) or 'id' not in entry:
        return value
    return f'{OPENCODE_MODEL_PREFIX}{entry["id"]}'


def _split_tools(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(',') if token.strip()]


def transform_skill_frontmatter(
    fm: dict[str, str],
    bundle: str,
    skill_name: str,
    rules: dict[str, list[str]],
    *,
    source_label: str | None = None,
) -> str:
    """Transform Claude skill frontmatter into OpenCode form.

    Output keys per the Agent Skills spec: ``name`` (``{bundle}-{skill}``),
    ``description`` (passed through, single line), and an explicit
    ``compatibility`` annotation noting the source.
    """
    label = source_label or f'{bundle}/{skill_name}'
    _ensure_required(fm, rules, label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = [
        '---',
        f'name: {bundle}-{skill_name}',
        f'description: {desc}',
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
    """Transform Claude agent frontmatter into OpenCode form.

    Maps Claude ``tools`` declarations into an OpenCode ``permission``
    block via ``mapping['tool_permissions']``. Unmapped tools raise
    ``UnmappedToolError`` so the CLI exits with code 2.
    """
    _ensure_required(fm, rules, source_label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = ['---', f'description: {desc}', 'mode: subagent']

    model_value = fm.get('model', '')
    if model_value:
        resolved = _resolve_model(model_value, mapping['model_map'])
        if resolved:
            lines.append(f'model: {resolved}')

    tools_raw = fm.get('tools', '')
    if tools_raw:
        permissions: list[str] = []
        unknown: list[str] = []
        seen: set[str] = set()
        for tool in _split_tools(tools_raw):
            mapped = mapping['tool_permissions'].get(tool)
            if mapped is None:
                unknown.append(tool)
                continue
            if mapped in seen:
                continue
            seen.add(mapped)
            permissions.append(mapped)
        if unknown:
            raise UnmappedToolError(
                f'{source_label}: unmapped tool(s) in frontmatter: {", ".join(unknown)}'
            )
        if permissions:
            lines.append('permission:')
            for perm in sorted(permissions):
                lines.append(f'  {perm}: allow')

    lines.append('---')
    return '\n'.join(lines)


def transform_command_frontmatter(
    fm: dict[str, str],
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> str:
    """Transform Claude command frontmatter into OpenCode form."""
    _ensure_required(fm, rules, source_label)

    desc = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    lines = ['---', f'description: {desc}', '---']
    return '\n'.join(lines)


__all__ = [
    'OPENCODE_MODEL_PREFIX',
    'UnmappedFrontmatterError',
    'UnmappedToolError',
    'load_mapping',
    'load_rules',
    'parse_frontmatter',
    'transform_agent_frontmatter',
    'transform_command_frontmatter',
    'transform_skill_frontmatter',
]
