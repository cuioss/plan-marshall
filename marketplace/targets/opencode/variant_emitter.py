# SPDX-License-Identifier: FSL-1.1-ALv2
"""Variant emission for the OpenCode target.

Mirrors ``marketplace/targets/claude/variant_emitter.py`` for the OpenCode
output format. For any canonical agent that declares ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``,
the OpenCode emitter writes — in addition to the canonical no-suffix agent
file — one ``{base}-level-N`` variant per ordinal level with a concrete,
provider-qualified ``model:`` line resolved from ``LEVEL_TABLE`` +
``mapping.json::model_map``.

Shared level/effort tables
--------------------------
The ordinal ``level -> (model alias, effort)`` binding (``LEVEL_TABLE``) and
the alias-capability gate set (``ALIAS_GATED_EFFORTS``) are the *same*
target-neutral facts the Claude target uses; they are imported from
``marketplace.targets.claude.variant_emitter`` so the two targets can never
drift. ``effort-levels.md`` remains the single documentary source of truth
for both (guarded by the lockstep tests). The Claude target already reaches
into ``opencode/mapping.json`` for its capability guard, so the cross-target
reuse is bidirectional and deliberate.

Model pinning
-------------
Each level's model alias is resolved through the OpenCode
``mapping.json::model_map`` and prefixed with ``OPENCODE_MODEL_PREFIX``
(``anthropic/``), reusing the exact ``_resolve_model`` path the OpenCode
frontmatter transformer already uses (so ``opus`` ->
``anthropic/claude-opus-4-8``). Setting the alias on a per-level copy of the
source frontmatter and running it back through ``transform_agent_frontmatter``
keeps the permission-block and model-resolution logic in one place.

Effort expression (the one fidelity caveat)
--------------------------------------------
OpenCode has no first-class ``effort:`` field. ``LEVEL_TABLE`` distinguishes
several tiers by effort *alone* while sharing a model alias
(``level-2``/``level-3`` are both ``sonnet``; ``level-4``/``level-5``/``level-6``
are all ``opus``). To keep those tiers distinct instead of collapsing to
byte-identical files, each variant carries its effort as a
provider-passthrough frontmatter key, ``reasoningEffort: <effort>`` — OpenCode
forwards unrecognised top-level agent keys to the provider. The value is the
plan-marshall effort keyword (``medium``/``high``/``xhigh``/``max``) verbatim.
``level-1`` (haiku) carries no effort key, matching the effort-less haiku tier.

**Caveat.** This passthrough is not validated against a live OpenCode runtime
(the marketplace tests only Claude Code as a runtime — see the top-level
``CLAUDE.md`` "Multi-Assistant Support" note). If a downstream OpenCode /
provider stack ignores ``reasoningEffort``, the same-model tiers collapse to
equivalent behaviour at runtime — but the emitted files remain distinct and
independently resolvable, which is what verification check 2.2d (``level-N``
variant resolution) requires. The decision to carry the effort rather than let
the tiers collapse is recorded in ``transforms.md`` and doc 06 open-work item 1.

Alias-capability gating
------------------------
The gate is identical to the Claude side: a variant whose effort is in
``ALIAS_GATED_EFFORTS`` (``xhigh``/``max``) is emitted only when the resolved
alias's ``supports_effort`` array in ``mapping.json`` advertises it; otherwise
the level is skipped and the dispatch falls back to the canonical at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marketplace.targets.claude.variant_emitter import (
    ALIAS_GATED_EFFORTS,
    EXTENSION_POINT,
    LEVEL_TABLE,
    supports_effort,
)
from marketplace.targets.opencode.frontmatter import transform_agent_frontmatter

# Provider-passthrough key carrying each variant's plan-marshall effort
# keyword. See the module docstring "Effort expression" caveat.
EFFORT_PASSTHROUGH_KEY = 'reasoningEffort'


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
    listed = {
        token.strip().strip('\'"')
        for token in normalized.split(',')
        if token.strip()
    }
    return [level for level in LEVEL_TABLE if level in listed]


def validate_canonical(fm: dict[str, str], source_label: str) -> None:
    """Backstop the no-model / no-effort invariant on the OpenCode side too.

    Canonicals declaring ``implements: ext-point-dynamic-level-executor``
    MUST NOT carry ``model:`` or ``effort:`` — the build target sets those on
    emitted variants and silent shadowing is prohibited. This mirrors the
    Claude target's ``validate_canonical`` build-time backstop.
    """
    if fm.get('model'):
        raise OpenCodeCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND "
            f"'model: {fm['model']}' — remove 'model:' (the build target sets "
            'it on emitted variants)'
        )
    if fm.get('effort'):
        raise OpenCodeCanonicalValidationError(
            f"{source_label}: canonical declares 'implements:' AND "
            f"'effort: {fm['effort']}' — remove 'effort:' (the build target sets "
            'it on emitted variants)'
        )


def _inject_effort(frontmatter_block: str, effort: str) -> str:
    """Insert the effort passthrough line just before the closing ``---``.

    ``transform_agent_frontmatter`` returns a block whose last line is a bare
    ``---``. The effort key is a top-level scalar, so inserting it before that
    closing fence (after any indented ``permission:`` children) is valid YAML.
    """
    lines = frontmatter_block.split('\n')
    # Stop before index 0 so the opening fence is never matched — a malformed
    # block missing its closing '---' leaves the frontmatter untouched rather
    # than inserting above the opening fence.
    for idx in range(len(lines) - 1, 0, -1):
        if lines[idx].strip() == '---':
            lines.insert(idx, f'{EFFORT_PASSTHROUGH_KEY}: {effort}')
            break
    return '\n'.join(lines)


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
    line is emitted. ``model:`` resolves the level's alias through
    ``model_map`` -> ``anthropic/<id>``; ``implements:``/``levels:`` are dropped;
    the effort (when present) is carried as a provider-passthrough key.
    """
    primitive = LEVEL_TABLE[level]
    alias = primitive['model']
    effort = primitive['effort']
    assert alias is not None  # every ordinal level binds a concrete alias

    variant_fm = dict(fm)
    variant_fm.pop('implements', None)
    variant_fm.pop('levels', None)
    # Set the alias so transform_agent_frontmatter resolves it through
    # model_map -> anthropic/<id> via the shared _resolve_model path.
    variant_fm['model'] = alias

    block = transform_agent_frontmatter(variant_fm, mapping, rules, source_label=source_label)
    if effort is not None:
        block = _inject_effort(block, effort)
    return block


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
    mapping_path: Path,
) -> OpenCodeVariantEmissionResult | None:
    """Emit ``{base_id}-level-N.md`` variant files for a role-eligible agent.

    Returns ``None`` when the agent does not declare the dynamic-level-executor
    extension point — the caller performs its normal single-file emit only.

    When eligible, writes one variant file per non-skipped level into
    ``agent_dir`` (reusing the caller's already-transformed ``transformed_body``
    verbatim) and returns the emission summary. The canonical no-suffix file is
    NOT written here: the caller's normal emit path already produces it, and the
    source carries no ``model:``, so the canonical is correct as-emitted.
    """
    if not is_role_eligible(fm):
        return None

    validate_canonical(fm, source_label)

    agent_dir.mkdir(parents=True, exist_ok=True)
    emitted: list[str] = []
    skipped: list[tuple[str, str]] = []

    for level in selected_levels(fm):
        primitive = LEVEL_TABLE[level]
        effort = primitive['effort']
        alias = primitive['model']
        if effort in ALIAS_GATED_EFFORTS:
            assert alias is not None
            assert effort is not None
            if not supports_effort(alias, effort, mapping_path):
                skipped.append(
                    (
                        level,
                        f"alias '{alias}' does not accept effort: {effort} — "
                        'falling back to canonical (inherit) at runtime',
                    )
                )
                continue
        block = render_variant_frontmatter(
            fm, level, mapping, rules, source_label=source_label
        )
        variant_path = agent_dir / f'{base_id}-{level}.md'
        variant_path.write_text(block + '\n\n' + transformed_body, encoding='utf-8')
        emitted.append(level)

    return OpenCodeVariantEmissionResult(
        canonical_id=base_id,
        variants_emitted=emitted,
        variants_skipped=skipped,
    )


__all__ = [
    'EFFORT_PASSTHROUGH_KEY',
    'OpenCodeCanonicalValidationError',
    'OpenCodeVariantEmissionResult',
    'emit_agent_variants',
    'is_role_eligible',
    'render_variant_frontmatter',
    'selected_levels',
    'validate_canonical',
]
