"""Deterministic top-level ``marketplace.json`` generator for the Claude target.

The Claude target emits each source bundle into ``target/claude/{bundle}/``
(flat layout — no nested ``bundles/`` directory). For Claude Code to register
``target/claude/`` as a marketplace, a matching ``.claude-plugin/marketplace.json``
must live at the output root with ``plugins[].source`` paths pointing at the
flat bundle directories rather than the source layout's ``./bundles/{bundle}``.

This module reads the source ``marketplace/.claude-plugin/marketplace.json``
and rewrites the ``plugins[].source`` field for each plugin entry from
``./bundles/{name}`` to ``./{name}``. All other top-level fields and per-plugin
fields pass through unchanged. The output is deterministic so the equality
check can diff it for drift.

The full ``plugins[]`` list is preserved even when the caller filters the
emit run with ``--bundles`` — the emitted marketplace.json describes the
catalogue, not the artifact selection.
"""

from __future__ import annotations

import json
from pathlib import Path

_SOURCE_PREFIX = './bundles/'
_TARGET_PREFIX = './'


def _read_source_marketplace(marketplace_src: Path) -> dict:
    manifest = marketplace_src / '.claude-plugin' / 'marketplace.json'
    if not manifest.exists():
        raise FileNotFoundError(f'Source marketplace manifest not found: {manifest}')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'Marketplace manifest must be a JSON object: {manifest}')
    return data


def _rewrite_plugin_source(source_value: str, plugin_name: str) -> str:
    if not source_value.startswith(_SOURCE_PREFIX):
        raise ValueError(
            f'plugin {plugin_name!r}: expected source to start with {_SOURCE_PREFIX!r}, '
            f'got {source_value!r}'
        )
    bundle_name = source_value[len(_SOURCE_PREFIX):]
    return f'{_TARGET_PREFIX}{bundle_name}'


def build_marketplace_json(marketplace_src: Path) -> dict:
    """Compose the regenerated ``marketplace.json`` document.

    ``marketplace_src`` is the source marketplace root (the directory whose
    ``.claude-plugin/marketplace.json`` is the SOT). Returns a new dict with
    the same top-level fields and the same ``plugins[]`` list, but each
    plugin's ``source`` rewritten to the flat target layout.
    """
    source = _read_source_marketplace(marketplace_src)
    output: dict = {}
    for key, value in source.items():
        if key == 'plugins':
            continue
        output[key] = value

    rewritten_plugins: list[dict] = []
    for entry in source.get('plugins', []):
        rewritten = dict(entry)
        plugin_name = entry.get('name', '<unknown>')
        if 'source' in rewritten:
            rewritten['source'] = _rewrite_plugin_source(rewritten['source'], plugin_name)
        rewritten_plugins.append(rewritten)
    output['plugins'] = rewritten_plugins
    return output


def generate_marketplace_json(marketplace_src: Path) -> str:
    """Return the regenerated ``marketplace.json`` as a deterministic JSON string."""
    document = build_marketplace_json(marketplace_src)
    return json.dumps(document, indent=2, ensure_ascii=False) + '\n'
