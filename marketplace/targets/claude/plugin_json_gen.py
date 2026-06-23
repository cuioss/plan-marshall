# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic ``plugin.json`` generator for the Claude target.

Reads a bundle directory, scans ``agents/*.md`` and ``commands/*.md``
for component frontmatter, then produces a fully populated
``plugin.json`` document. Top-level fields (``name``, ``version``,
``description``, ``author``, ``license``, ``homepage``, ``repository``,
``keywords``) pass through unchanged from the existing committed
``plugin.json``; the ``agents`` and ``commands`` arrays come from the
filesystem scan.

The emitted ``skills`` array is always empty. Per the Claude Code plugin
spec, declaring a ``skills`` array ADDS to the default ``skills/`` folder
scan rather than replacing it; bundles whose skills live entirely in the
default location would therefore double-load every skill if it were
explicitly declared. Emitting ``skills: []`` lets the runtime perform the
default folder scan once and produce the correct, non-doubled inventory.
``agents`` and ``commands`` follow the opposite rule (the explicit list
REPLACES the default scan), so they are still emitted with full entries.

Agents declaring ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``
expand into multiple entries in the ``agents`` array — one per emitted
level plus the canonical no-suffix entry that serves the ``inherit``
resolution case. Non-eligible agents emit a single entry as before.

The output is deterministic — file paths within each component array are
sorted alphabetically — so the equality check in
``equality_check.py`` produces stable diffs across runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from marketplace.targets.claude.variant_emitter import (
    ALIAS_GATED_EFFORTS,
    LEVEL_TABLE,
    is_role_eligible,
    parse_frontmatter,
    selected_levels,
    supports_effort,
)

# Top-level fields that are preserved verbatim from the committed plugin.json.
PASSTHROUGH_FIELDS = (
    'name',
    'version',
    'description',
    'author',
    'license',
    'homepage',
    'repository',
    'keywords',
)


def _read_committed(bundle_dir: Path) -> dict:
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        raise FileNotFoundError(f'Bundle missing plugin.json: {plugin_json}')
    parsed: dict = json.loads(plugin_json.read_text(encoding='utf-8'))
    return parsed


_OPENCODE_MAPPING = Path(__file__).resolve().parent.parent / 'opencode' / 'mapping.json'


def _list_md_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_file() and p.suffix == '.md' and not p.name.startswith('.'))


def _expanded_agent_entries(agents_dir: Path, mapping_path: Path = _OPENCODE_MAPPING) -> list[str]:
    """Return the agents array for ``plugin.json`` with variant expansion.

    For each agent file:
    - If the file declares the dynamic-level-executor extension point,
      emit one entry per selected level plus the canonical no-suffix
      entry. A level whose effort is alias-capability-gated (any effort
      in ``ALIAS_GATED_EFFORTS``) is suppressed when the resolved alias
      cannot accept that effort (mirrors the build-time skip in
      ``variant_emitter``).
    - Otherwise, emit a single entry for the agent's filename.

    Entries are absolute-from-bundle paths (``./agents/{name}.md``) and
    the returned list is sorted alphabetically for deterministic output.
    """
    if not agents_dir.exists():
        return []
    entries: list[str] = []
    for path in sorted(agents_dir.iterdir()):
        if not (path.is_file() and path.suffix == '.md' and not path.name.startswith('.')):
            continue
        text = path.read_text(encoding='utf-8')
        frontmatter, _body = parse_frontmatter(text)
        if not is_role_eligible(frontmatter):
            entries.append(f'./agents/{path.name}')
            continue
        assert frontmatter is not None
        base_name = frontmatter.name or path.stem
        # Canonical (inherit) entry.
        entries.append(f'./agents/{base_name}.md')
        # Per-level variants (with per-alias-effort guard — see
        # ALIAS_GATED_EFFORTS; mirrors variant_emitter.emit_variants_for_agent).
        for level in selected_levels(frontmatter):
            primitive = LEVEL_TABLE[level]
            effort = primitive['effort']
            if effort in ALIAS_GATED_EFFORTS:
                alias = primitive['model']
                assert alias is not None
                assert effort is not None
                if not supports_effort(alias, effort, mapping_path):
                    continue
            entries.append(f'./agents/{base_name}-{level}.md')
    return sorted(entries)


def discover_components(bundle_dir: Path) -> dict[str, list[str]]:
    """Discover the agents and commands entries for ``bundle_dir``.

    Returns a dict with ``agents``, ``commands``, and ``skills`` keys.
    ``agents`` and ``commands`` are sorted lists of paths relative to the
    bundle root. ``skills`` is always an empty list — the runtime scans the
    default ``skills/`` folder and adding to that scan via plugin.json
    causes every skill to load twice. See the module docstring for the
    spec citation.
    """
    agents = _expanded_agent_entries(bundle_dir / 'agents')
    commands = [f'./commands/{name}' for name in _list_md_files(bundle_dir / 'commands')]
    return {
        'agents': sorted(agents),
        'commands': sorted(commands),
        'skills': [],
    }


def build_plugin_json(bundle_dir: Path) -> dict:
    """Compose the regenerated ``plugin.json`` document for ``bundle_dir``."""
    committed = _read_committed(bundle_dir)
    discovered = discover_components(bundle_dir)

    output: dict = {}
    for field in PASSTHROUGH_FIELDS:
        if field in committed:
            output[field] = committed[field]

    output['agents'] = discovered['agents']
    output['commands'] = discovered['commands']
    output['skills'] = discovered['skills']

    return output


def generate_plugin_json(bundle_dir: Path) -> str:
    """Return the regenerated ``plugin.json`` as a deterministic JSON string.

    The output uses two-space indentation, sorts component arrays, and
    preserves the top-level field order documented in
    ``PASSTHROUGH_FIELDS``.
    """
    document = build_plugin_json(bundle_dir)
    return json.dumps(document, indent=2, ensure_ascii=False) + '\n'
