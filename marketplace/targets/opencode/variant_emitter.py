# SPDX-License-Identifier: FSL-1.1-ALv2
"""Variant emission for the OpenCode target.

Mirrors ``marketplace/targets/claude/variant_emitter.py`` for the OpenCode
output format. For any canonical agent that declares ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``,
the OpenCode emitter writes — in addition to the canonical no-suffix agent
file — one ``{base}-level-N`` variant per ordinal level. The level files keep
``manage-config effort resolve-target`` results like
``execution-context-level-3`` resolving to a concrete agent file at runtime;
how the level was selected (a configured ``marshal.json`` effort level, or
``inherit``) does not change the emitted shape.

Level palette
-------------
The ordinal level palette (``LEVEL_TABLE``) is the same target-neutral fact
the Claude target uses; it is imported from
``marketplace.targets.claude.variant_emitter`` so the two targets can never
drift. ``effort-levels.md`` remains the single documentary source of truth
for both (guarded by the lockstep tests).

Inherit-only emission (the OpenCode policy)
-------------------------------------------
Every OpenCode level variant is emitted **model-less**: it carries no
``model:`` and no ``reasoningEffort:`` frontmatter, so each subagent inherits
the session's model at dispatch time. The level variants therefore behave
identically no matter which one the effort-resolution seam picks — the seam
keeps returning ``{base}-level-N`` names and every such name dispatches on
the session model.

This deliberately deviates from the Claude target, whose variants pin
``model:`` (and ``effort:``) per ``effort-levels.md``. The OpenCode adapter
shares the level palette (``LEVEL_TABLE``) with Claude only so the level
*names* cannot drift; it does not consume the model/effort binding. The
alias-capability gate (``ALIAS_GATED_EFFORTS``, ``supports_effort``) is
therefore a Claude-only concern and is not imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marketplace.targets.claude.variant_emitter import EXTENSION_POINT, LEVEL_TABLE
from marketplace.targets.opencode.frontmatter import transform_agent_frontmatter


class OpenCodeCanonicalValidationError(ValueError):
    """Raised when a role-eligible canonical declares forbidden model/effort."""


def is_role_eligible(fm: dict[str, str]) -> bool:
    """True when the parsed frontmatter declares the dynamic-level-executor point."""
    return fm.get('implements') == EXTENSION_POINT


def selected_levels(fm: dict[str, str]) -> list[str]:
    """Return the levels to emit for this canonical, in canonical order.

    When ``levels:`` is present, only listed levels are emitted (filtered
    against the known palette). When absent, all seven levels are emitted.
    The OpenCode frontmatter parser flattens a YAML block list into a
    comma-separated string and leaves an inline ``[a, b]`` list bracketed, so
    both forms are normalised before splitting.
    """
    raw = fm.get('levels')
    if not raw:
        return list(LEVEL_TABLE.keys())
    normalized = raw.strip().lstrip('[').rstrip(']')
    listed = {token.strip().strip('\'"') for token in normalized.split(',') if token.strip()}
    return [level for level in LEVEL_TABLE if level in listed]


def validate_canonical(fm: dict[str, str], source_label: str) -> None:
    """Backstop the no-model / no-effort invariant on the OpenCode side too.

    Canonicals declaring ``implements: ext-point-dynamic-level-executor``
    MUST NOT carry ``model:`` or ``effort:`` — a role-eligible canonical must
    stay target-neutral. The Claude build target pins those fields on its
    emitted variants; the OpenCode variants must stay inherit. This mirrors
    the Claude target's ``validate_canonical`` build-time backstop.
    """
    if fm.get('model'):
        raise OpenCodeCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND "
            f"'model: {fm['model']}' — remove 'model:' (role-eligible "
            'canonicals must stay target-neutral: Claude pins it on emitted '
            'variants, OpenCode stays inherit)'
        )
    if fm.get('effort'):
        raise OpenCodeCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND "
            f"'effort: {fm['effort']}' — remove 'effort:' (role-eligible "
            'canonicals must stay target-neutral: Claude pins it on emitted '
            'variants, OpenCode stays inherit)'
        )


def render_variant_frontmatter(
    fm: dict[str, str],
    level: str,
    mapping: dict,
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> str:
    """Render the OpenCode frontmatter block for one level variant.

    The variant identity is carried by its filename (``{base}-{level}.md``),
    matching how the canonical agent id derives from its filename — no ``name:``
    line is emitted. ``implements:``/``levels:`` are dropped and NO ``model:``
    or ``reasoningEffort:`` is added, per the module docstring
    "Inherit-only emission": every level variant inherits the session model.
    ``level`` is not consulted in the block — the filename carries the level —
    but the parameter keeps the call site explicit about which variant is
    being rendered.
    """
    variant_fm = dict(fm)
    variant_fm.pop('implements', None)
    variant_fm.pop('levels', None)
    return transform_agent_frontmatter(variant_fm, mapping, rules, source_label=source_label)


@dataclass
class OpenCodeVariantEmissionResult:
    """Outcome of variant emission for a single canonical agent."""

    canonical_id: str
    variants_emitted: list[str]
    variants_skipped: list[tuple[str, str]]  # (level, reason)


def emit_agent_variants(
    fm: dict[str, str],
    transformed_body: str,
    base_id: str,
    agent_dir: Path,
    mapping: dict,
    rules: dict[str, list[str]],
    *,
    source_label: str,
) -> OpenCodeVariantEmissionResult | None:
    """Emit ``{base_id}-level-N.md`` variant files for a role-eligible agent.

    Returns ``None`` when the agent does not declare the dynamic-level-executor
    extension point — the caller performs its normal single-file emit only.

    When eligible, writes one variant file per selected level into
    ``agent_dir`` (reusing the caller's already-transformed ``transformed_body``
    verbatim) and returns the emission summary. Every variant is an
    inherit-only copy of the canonical frontmatter (no ``model:``, no
    ``reasoningEffort:``) — see the module docstring "Inherit-only emission".
    No variant is ever skipped: the alias-capability gate is a Claude-only
    concern, so ``variants_skipped`` is always empty. The canonical no-suffix
    file is NOT written here: the caller's normal emit path already produces
    it, and since the source carries no ``model:`` it is correct as-emitted.
    """
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

    return OpenCodeVariantEmissionResult(
        canonical_id=base_id,
        variants_emitted=emitted,
        variants_skipped=skipped,
    )


__all__ = [
    'OpenCodeCanonicalValidationError',
    'OpenCodeVariantEmissionResult',
    'emit_agent_variants',
    'is_role_eligible',
    'render_variant_frontmatter',
    'selected_levels',
    'validate_canonical',
]
