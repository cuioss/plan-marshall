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

A component declaring a ``targets:`` frontmatter scope that omits the
generating target contributes NO entry — the same filter the verbatim
emitter applies to the file itself (see ``component_targets.py``).
Dropping the entry and the file in lock-step is what lets the equality
check read a scoped-out component as deliberately absent rather than as
drift.

The output is deterministic — file paths within each component array are
sorted alphabetically — so the equality check in
``equality_check.py`` produces stable diffs across runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from marketplace.targets.claude.emitter import CLAUDE_TARGET_NAME
from marketplace.targets.claude.variant_emitter import (
    ALIAS_GATED_EFFORTS,
    LEVEL_TABLE,
    is_role_eligible,
    parse_frontmatter,
    selected_levels,
    supports_effort,
)
from marketplace.targets.component_targets import emits_to

# Top-level fields that are preserved verbatim from the committed plugin.json.
#
# ⛔ This is an ALLOWLIST, and a key absent from it is DISCARDED at build with no
# error: the emitter excludes the source manifest from its verbatim mirror, and
# the equality check compares regenerated against emitted (both missing the key),
# so a dropped key is invisible to every gate. A manifest key that governs runtime
# behaviour must therefore be added here explicitly. The worked example:
# `lspServers` was declared in a committed manifest and silently never reached the
# deployed artifact, so the server it declared was never started by any client.
# That declaration was subsequently withdrawn for unrelated reasons, so no bundle
# currently ships one — the entry is kept deliberately, because the defect is in
# the allowlist mechanism rather than in any one key, and because a declaration
# added back into a bundle manifest would need it again.
PASSTHROUGH_FIELDS = (
    'name',
    'version',
    'description',
    'author',
    'license',
    'homepage',
    'repository',
    'keywords',
    'lspServers',
)


def _read_committed(bundle_dir: Path) -> dict:
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        raise FileNotFoundError(f'Bundle missing plugin.json: {plugin_json}')
    parsed: dict = json.loads(plugin_json.read_text(encoding='utf-8'))
    return parsed


_OPENCODE_MAPPING = Path(__file__).resolve().parent.parent / 'opencode' / 'mapping.json'


def _list_md_files(directory: Path, target_name: str) -> list[str]:
    if not directory.exists():
        return []
    return sorted(
        p.name
        for p in directory.iterdir()
        if p.is_file()
        and p.suffix == '.md'
        and not p.name.startswith('.')
        and emits_to(p, target_name)
    )


def _expanded_agent_entries(
    agents_dir: Path,
    target_name: str,
    mapping_path: Path = _OPENCODE_MAPPING,
) -> list[str]:
    """Return the agents array for ``plugin.json`` with variant expansion.

    For each agent file:
    - An agent whose ``targets:`` scope omits ``target_name`` contributes
      no entry at all — neither canonical nor variant.
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
        if not emits_to(path, target_name):
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


def discover_components(
    bundle_dir: Path,
    *,
    target_name: str = CLAUDE_TARGET_NAME,
) -> dict[str, list[str]]:
    """Discover the agents and commands entries for ``bundle_dir``.

    Returns a dict with ``agents``, ``commands``, and ``skills`` keys.
    ``agents`` and ``commands`` are sorted lists of paths relative to the
    bundle root, each filtered by the component's ``targets:`` scope.
    ``skills`` is always an empty list — the runtime scans the default
    ``skills/`` folder and adding to that scan via plugin.json causes
    every skill to load twice. See the module docstring for the spec
    citation. A skill scoped away from this target is therefore excluded
    by the emitter's directory-level skip alone; there is no manifest
    entry to drop.
    """
    agents = _expanded_agent_entries(bundle_dir / 'agents', target_name)
    commands = [
        f'./commands/{name}' for name in _list_md_files(bundle_dir / 'commands', target_name)
    ]
    return {
        'agents': sorted(agents),
        'commands': sorted(commands),
        'skills': [],
    }


def build_plugin_json(bundle_dir: Path, *, target_name: str = CLAUDE_TARGET_NAME) -> dict:
    """Compose the regenerated ``plugin.json`` document for ``bundle_dir``."""
    committed = _read_committed(bundle_dir)
    discovered = discover_components(bundle_dir, target_name=target_name)

    output: dict = {}
    for field in PASSTHROUGH_FIELDS:
        if field in committed:
            output[field] = committed[field]

    output['agents'] = discovered['agents']
    output['commands'] = discovered['commands']
    output['skills'] = discovered['skills']

    return output


def generate_plugin_json(bundle_dir: Path, *, target_name: str = CLAUDE_TARGET_NAME) -> str:
    """Return the regenerated ``plugin.json`` as a deterministic JSON string.

    The output uses two-space indentation, sorts component arrays, and
    preserves the top-level field order documented in
    ``PASSTHROUGH_FIELDS``.
    """
    document = build_plugin_json(bundle_dir, target_name=target_name)
    return json.dumps(document, indent=2, ensure_ascii=False) + '\n'
