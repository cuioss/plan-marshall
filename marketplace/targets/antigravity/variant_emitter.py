# SPDX-License-Identifier: FSL-1.1-ALv2
"""Variant emission for the Antigravity target.

Mirrors ``marketplace/targets/opencode/variant_emitter.py`` for Antigravity
subagents. For any canonical agent declaring ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``,
writes one ``{base}-level-N`` variant per ordinal level.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marketplace.targets.antigravity.frontmatter import transform_agent_frontmatter
from marketplace.targets.claude.variant_emitter import EXTENSION_POINT


def _load_local_ladder(target: str = 'antigravity') -> dict[str, Any] | None:
    """Load ladder for target from .plan/local/effort-ladder.json if present."""
    candidates: list[Path] = []
    if 'PLAN_BASE_DIR' in os.environ:
        candidates.append(Path(os.environ['PLAN_BASE_DIR']) / 'effort-ladder.json')
    try:
        from marketplace_paths import resolve_main_anchored_path

        candidates.append(resolve_main_anchored_path('effort-ladder.json'))
    except Exception:
        pass
    cwd = Path.cwd().resolve()
    for p in (cwd, *cwd.parents):
        candidates.append(p / '.plan' / 'local' / 'effort-ladder.json')
    for cand in candidates:
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding='utf-8'))
                if isinstance(data, dict) and 'targets' in data and isinstance(data['targets'], dict):
                    if target in data['targets']:
                        return data['targets'][target]
            except Exception:
                pass
    return None


#: The canonical Option 1 ladder for Antigravity (Model Axis x Effort Axis).
DEFAULT_LADDER: dict[str, dict[str, str | None]] = {
    'level-1': {'model': 'flash', 'effort': 'low'},
    'level-2': {'model': 'flash', 'effort': 'low'},
    'level-3': {'model': 'flash', 'effort': 'medium'},
    'level-4': {'model': 'flash', 'effort': 'medium'},
    'level-5': {'model': 'flash', 'effort': 'high'},
    'level-6': {'model': 'pro', 'effort': 'low'},
    'level-7': {'model': 'pro', 'effort': 'high'},
}

#: Aliased for backwards compatibility with tests and callers expecting LEVEL_TABLE.
LEVEL_TABLE = DEFAULT_LADDER


class AntigravityCanonicalValidationError(ValueError):
    """Raised when a role-eligible canonical declares forbidden model/effort."""


def is_role_eligible(fm: dict[str, str]) -> bool:
    """True when the parsed frontmatter declares the dynamic-level-executor point."""
    return fm.get('implements') == EXTENSION_POINT


def selected_levels(fm: dict[str, str]) -> list[str]:
    """Return the levels to emit for this canonical, in canonical order."""
    raw = fm.get('levels')
    if not raw:
        return list(DEFAULT_LADDER.keys())
    normalized = raw.strip().lstrip('[').rstrip(']')
    listed = {token.strip().strip('\'"') for token in normalized.split(',') if token.strip()}
    return [level for level in DEFAULT_LADDER if level in listed]


def validate_canonical(fm: dict[str, str], source_label: str) -> None:
    """Validate that canonical agent declares neither model nor effort."""
    if fm.get('model'):
        raise AntigravityCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND 'model: {fm['model']}' — "
            'role-eligible canonicals must stay target-neutral'
        )
    if fm.get('effort'):
        raise AntigravityCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND 'effort: {fm['effort']}' — "
            'role-eligible canonicals must stay target-neutral'
        )


def render_variant_frontmatter(
    fm: dict[str, str],
    level: str,
    mapping: dict,
    rules: dict[str, list[str]],
    *,
    source_label: str,
    level_pin: dict[str, str | None] | str | None = None,
) -> str:
    """Render frontmatter for one level variant."""
    variant_fm = dict(fm)
    variant_fm.pop('implements', None)
    variant_fm.pop('levels', None)

    if isinstance(level_pin, dict):
        model = level_pin.get('model')
        effort = level_pin.get('effort')
        if model and model != 'inherit':
            variant_fm['model'] = model
        if effort and effort != 'inherit':
            variant_fm['effort'] = effort
    elif isinstance(level_pin, str) and level_pin != 'inherit':
        variant_fm['model'] = level_pin

    return transform_agent_frontmatter(variant_fm, mapping, rules, source_label=source_label)


@dataclass
class AntigravityVariantEmissionResult:
    """Outcome of variant emission for a single canonical agent."""

    canonical_id: str
    variants_emitted: list[str]
    variants_skipped: list[tuple[str, str]]


def emit_agent_variants(
    fm: dict[str, str],
    transformed_body: str,
    base_id: str,
    agent_dir: Path,
    mapping: dict,
    rules: dict[str, list[str]],
    *,
    source_label: str,
    level_pins: dict[str, Any] | None = None,
) -> AntigravityVariantEmissionResult | None:
    """Emit ``{base_id}-level-N.md`` variant files for a role-eligible agent."""
    if not is_role_eligible(fm):
        return None

    validate_canonical(fm, source_label)

    pins: dict[str, Any] = dict(DEFAULT_LADDER)
    if level_pins:
        unknown_keys = [level for level in level_pins if level not in DEFAULT_LADDER]
        if unknown_keys:
            raise ValueError(
                f'{source_label}: unknown level key(s) in pin map: '
                f'{", ".join(sorted(unknown_keys))} — a pin can only be applied to '
                f'its own configured level'
            )
        pins.update(level_pins)
    else:
        local_ladder = _load_local_ladder('antigravity')
        if local_ladder:
            pins.update(local_ladder)

    agent_dir.mkdir(parents=True, exist_ok=True)
    emitted: list[str] = []
    skipped: list[tuple[str, str]] = []

    for level in selected_levels(fm):
        block = render_variant_frontmatter(
            fm,
            level,
            mapping,
            rules,
            source_label=source_label,
            level_pin=pins.get(level),
        )
        variant_path = agent_dir / f'{base_id}-{level}.md'
        variant_path.write_text(block + '\n\n' + transformed_body, encoding='utf-8')
        emitted.append(level)

    return AntigravityVariantEmissionResult(
        canonical_id=base_id,
        variants_emitted=emitted,
        variants_skipped=skipped,
    )


__all__ = [
    'DEFAULT_LADDER',
    'LEVEL_TABLE',
    'AntigravityCanonicalValidationError',
    'AntigravityVariantEmissionResult',
    'emit_agent_variants',
    'is_role_eligible',
    'render_variant_frontmatter',
    'selected_levels',
    'validate_canonical',
]
