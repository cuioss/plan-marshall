"""Deterministic ``plugin.json`` generator for the Claude target.

Reads a bundle directory, scans ``agents/*.md``, ``commands/*.md``, and
``skills/*/SKILL.md`` for component frontmatter, then produces a fully
populated ``plugin.json`` document. Top-level fields (``name``,
``version``, ``description``, ``author``, ``license``, ``homepage``,
``repository``, ``keywords``) pass through unchanged from the existing
committed ``plugin.json``; only the ``agents``, ``commands``, and
``skills`` arrays come from the frontmatter scan.

The output is deterministic — file paths within each component array are
sorted alphabetically — so the equality check in
``equality_check.py`` produces stable diffs across runs.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    return json.loads(plugin_json.read_text(encoding='utf-8'))


def _list_md_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_file() and p.suffix == '.md' and not p.name.startswith('.'))


def _list_skill_dirs(skills_dir: Path) -> list[str]:
    """Return skill subdirectory names (those with a SKILL.md)."""
    if not skills_dir.exists():
        return []
    found: list[str] = []
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / 'SKILL.md').exists():
            found.append(child.name)
    return found


def discover_components(bundle_dir: Path) -> dict[str, list[str]]:
    """Discover the agents, commands, and skills entries for ``bundle_dir``.

    Returns a dict with ``agents``, ``commands``, and ``skills`` keys, each
    mapped to a sorted list of paths relative to the bundle root (matching
    the schema used by the existing committed ``plugin.json`` files).
    """
    agents = [f'./agents/{name}' for name in _list_md_files(bundle_dir / 'agents')]
    commands = [f'./commands/{name}' for name in _list_md_files(bundle_dir / 'commands')]
    skills = [f'./skills/{name}' for name in _list_skill_dirs(bundle_dir / 'skills')]
    return {
        'agents': sorted(agents),
        'commands': sorted(commands),
        'skills': sorted(skills),
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
