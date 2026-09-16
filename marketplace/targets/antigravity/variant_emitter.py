# SPDX-License-Identifier: FSL-1.1-ALv2
"""Variant emission for the Antigravity target.

Mirrors ``marketplace/targets/opencode/variant_emitter.py`` for Antigravity
subagents. For any canonical agent declaring ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``,
writes one ``{base}-level-N`` variant per ordinal level.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marketplace.targets.antigravity.frontmatter import transform_agent_frontmatter
from marketplace.targets.claude.variant_emitter import EXTENSION_POINT, LEVEL_TABLE


class AntigravityCanonicalValidationError(ValueError):
    """Raised when a role-eligible canonical declares forbidden model/effort."""


def is_role_eligible(fm: dict[str, str]) -> bool:
    """True when the parsed frontmatter declares the dynamic-level-executor point."""
    return fm.get('implements') == EXTENSION_POINT


def selected_levels(fm: dict[str, str]) -> list[str]:
    """Return the levels to emit for this canonical, in canonical order."""
    raw = fm.get('levels')
    if not raw:
        return list(LEVEL_TABLE.keys())
    normalized = raw.strip().lstrip('[').rstrip(']')
    listed = {token.strip().strip('\'"') for token in normalized.split(',') if token.strip()}
    return [level for level in LEVEL_TABLE if level in listed]


def validate_canonical(fm: dict[str, str], source_label: str) -> None:
    """Validate that canonical agent declares neither model nor effort."""
    if fm.get('model'):
        raise AntigravityCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND 'model: {fm['model']}' — "
            "role-eligible canonicals must stay target-neutral"
        )
    if fm.get('effort'):
        raise AntigravityCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND 'effort: {fm['effort']}' — "
            "role-eligible canonicals must stay target-neutral"
        )


def render_variant_frontmatter(
    fm: dict[str, str],
    level: str,
    mapping: dict,
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> str:
    """Render frontmatter for one level variant."""
    variant_fm = dict(fm)
    variant_fm.pop('implements', None)
    variant_fm.pop('levels', None)
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
) -> AntigravityVariantEmissionResult | None:
    """Emit ``{base_id}-level-N.md`` variant files for a role-eligible agent."""
    if not is_role_eligible(fm):
        return None

    validate_canonical(fm, source_label)

    agent_dir.mkdir(parents=True, exist_ok=True)
    emitted: list[str] = []
    skipped: list[tuple[str, str]] = []

    for level in selected_levels(fm):
        block = render_variant_frontmatter(fm, level, mapping, rules, source_label=source_label)
        variant_path = agent_dir / f'{base_id}-{level}.md'
        variant_path.write_text(block + '\n\n' + transformed_body, encoding='utf-8')
        emitted.append(level)

    return AntigravityVariantEmissionResult(
        canonical_id=base_id,
        variants_emitted=emitted,
        variants_skipped=skipped,
    )


__all__ = [
    'AntigravityCanonicalValidationError',
    'AntigravityVariantEmissionResult',
    'emit_agent_variants',
    'is_role_eligible',
    'render_variant_frontmatter',
    'selected_levels',
    'validate_canonical',
]
