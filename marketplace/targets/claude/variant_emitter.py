"""Variant emission for the Claude target.

Detects canonical agents that declare ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor``
in their YAML frontmatter and emits one variant agent file per ordinal
level (``level-1``, ``level-2``, ``level-3``, ``level-4``, ``level-5``,
``level-6``, ``level-7``) plus the canonical no-suffix file (with
``implements:`` and ``levels:`` stripped).

The level → ``(model, effort)`` primitive binding is the canonical
table from ``plan-marshall:plan-marshall/standards/effort-levels.md``.
The build-time guard reads
``marketplace/targets/opencode/mapping.json`` to decide whether the
resolved model alias accepts the level's effort. The guard fires for
any alias-capability-gated effort (those in ``ALIAS_GATED_EFFORTS`` —
``xhigh`` and ``max``); when the alias does not accept the requested
effort, that level's variant is skipped (the canonical falls back to
``inherit`` at runtime). Efforts that are universally available
(``medium``, ``high``, and the effort-less haiku tier) are never gated.

SESSION RESTART REQUIRED for emitted variants
---------------------------------------------

Claude Code's agent registry is **session-pinned at session start**: it
scans the plugin cache exactly once when the session boots and never
re-scans mid-session. Variants emitted by this module — for example
``execution-context-{level}`` files newly added to
``target/claude/{bundle}/agents/`` — are written to disk in real time,
but a Claude Code session that started **before** the emission has no
visibility into them. Dispatching ``Task: {bundle}:{base}-{level}``
against a freshly emitted variant from the same session fails with
``Agent type '{bundle}:{base}-{level}' not found`` even though the
file is present in the cache. The user (or downstream tooling) MUST
restart the Claude Code session before dispatching against any newly-
emitted variant. The same WHY rationale (registry is session-pinned at
startup) is documented at the sister surfaces — ``/sync-plugin-cache``,
``/marshall-steward``, and
``ext-point-dynamic-level-executor.md`` — and MUST stay convergent
across all four surfaces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

EXTENSION_POINT = 'plan-marshall:extension-api/standards/ext-point-dynamic-level-executor'

# Single source of truth: keep in lock-step with effort-levels.md.
LEVEL_TABLE: dict[str, dict[str, str | None]] = {
    'level-1': {'model': 'haiku', 'effort': None},
    'level-2': {'model': 'sonnet', 'effort': 'medium'},
    'level-3': {'model': 'sonnet', 'effort': 'high'},
    'level-4': {'model': 'opus', 'effort': 'medium'},
    'level-5': {'model': 'opus', 'effort': 'high'},
    'level-6': {'model': 'opus', 'effort': 'xhigh'},
    'level-7': {'model': 'fable', 'effort': 'max'},
}

# Effort values whose emission is gated by per-alias capability — a variant
# at one of these efforts is emitted only when the resolved model alias's
# ``supports_effort`` array (in ``mapping.json``) advertises the effort.
# Efforts outside this set (``medium``, ``high``, and the effort-less haiku
# tier) are universally available and never gated.
ALIAS_GATED_EFFORTS: frozenset[str] = frozenset({'xhigh', 'max'})

@dataclass(frozen=True)
class Frontmatter:
    """Parsed YAML frontmatter for an agent file.

    Only the fields the emitter cares about are typed; the remainder is
    preserved as a sequence of raw lines so other fields pass through
    the round-trip unchanged.
    """

    raw_lines: list[str]
    name: str | None
    implements: str | None
    levels: list[str] | None
    model: str | None
    effort: str | None


def parse_frontmatter(text: str) -> tuple[Frontmatter | None, str]:
    """Parse YAML frontmatter from an agent markdown file.

    Returns ``(frontmatter, body)`` where ``body`` is the post-frontmatter
    content (everything after the closing ``---``). Returns
    ``(None, text)`` when the file lacks a frontmatter block.

    The parser is intentionally narrow — it understands single-line
    string values, simple lists (``[a, b, c]``), and folded multi-line
    strings introduced with ``|``. This matches the surface area of the
    canonical agent files in the marketplace today; richer YAML constructs
    are not used.
    """
    if not text.startswith('---\n'):
        return None, text
    end = text.find('\n---\n', 4)
    if end == -1:
        # Tolerate trailing `---` without final newline.
        end_alt = text.rfind('\n---')
        if end_alt == -1 or end_alt <= 4:
            return None, text
        end = end_alt

    block = text[4:end]
    body = text[end + len('\n---\n') :]
    raw_lines = block.split('\n')

    name: str | None = None
    implements: str | None = None
    levels: list[str] | None = None
    model: str | None = None
    effort: str | None = None

    in_block_scalar_for: str | None = None  # field whose value is `|` block
    for line in raw_lines:
        if in_block_scalar_for is not None:
            # Block-scalar continuation: stop collecting once we hit a
            # non-indented top-level key. We don't capture block values
            # for any of the fields we care about; reset on top-level keys.
            if line and not line.startswith(' ') and not line.startswith('\t'):
                in_block_scalar_for = None
            else:
                continue

        # Top-level scalar key
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip()

        if value == '|':
            in_block_scalar_for = key
            continue

        if key == 'name':
            name = _unquote(value)
        elif key == 'implements':
            implements = _unquote(value)
        elif key == 'levels':
            levels = _parse_inline_list(value)
        elif key == 'model':
            model = _strip_inline_comment(_unquote(value))
        elif key == 'effort':
            effort = _strip_inline_comment(_unquote(value))

    return (
        Frontmatter(
            raw_lines=raw_lines,
            name=name,
            implements=implements,
            levels=levels,
            model=model,
            effort=effort,
        ),
        body,
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _strip_inline_comment(value: str) -> str:
    # Tolerate `model: opus  # rationale` shapes — strip everything from the first `#`.
    idx = value.find('#')
    if idx == -1:
        return value.strip()
    return value[:idx].strip()


def _parse_inline_list(value: str) -> list[str] | None:
    """Parse `[a, b, c]` style inline lists. Returns None on malformed input."""
    value = value.strip()
    if not (value.startswith('[') and value.endswith(']')):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(',') if item.strip()]


def is_role_eligible(frontmatter: Frontmatter | None) -> bool:
    return frontmatter is not None and frontmatter.implements == EXTENSION_POINT


def selected_levels(frontmatter: Frontmatter) -> list[str]:
    """Return the list of levels to emit for this canonical.

    When ``levels:`` is present, only listed levels are emitted (filtered
    against the known palette). When absent, all seven levels are emitted
    in canonical order (``level-1``, ``level-2``, ``level-3``,
    ``level-4``, ``level-5``, ``level-6``, ``level-7``).
    """
    if frontmatter.levels is None:
        return list(LEVEL_TABLE.keys())
    return [level for level in LEVEL_TABLE.keys() if level in frontmatter.levels]


class CanonicalValidationError(ValueError):
    """Raised when a canonical agent declares forbidden fields."""


def validate_canonical(frontmatter: Frontmatter, source: Path) -> None:
    """Enforce the no-model / no-effort invariant on canonicals.

    Canonicals declaring ``implements: ext-point-dynamic-level-executor``
    MUST NOT carry ``model:`` or ``effort:`` — the build target sets
    those on emitted variants and silent shadowing is prohibited. The
    plugin-doctor lint rule catches this at edit time; this function is
    the build-time backstop.
    """
    if frontmatter.model:
        raise CanonicalValidationError(
            f"{source}: canonical declares 'implements:' AND 'model: {frontmatter.model}' — "
            "remove 'model:' (the build target sets it on emitted variants)"
        )
    if frontmatter.effort:
        raise CanonicalValidationError(
            f"{source}: canonical declares 'implements:' AND 'effort: {frontmatter.effort}' — "
            "remove 'effort:' (the build target sets it on emitted variants)"
        )


def strip_role_fields(raw_lines: list[str]) -> list[str]:
    """Drop ``implements:`` and ``levels:`` lines from frontmatter.

    Used both for the emitted canonical no-suffix file and for variant
    files (variants declare neither field).
    """
    return [
        line
        for line in raw_lines
        if not _starts_with_key(line, 'implements')
        and not _starts_with_key(line, 'levels')
    ]


def _starts_with_key(line: str, key: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(f'{key}:') or stripped.startswith(f'{key} :')


def render_canonical(frontmatter: Frontmatter, body: str) -> str:
    """Render the canonical no-suffix file with role fields stripped."""
    new_lines = strip_role_fields(frontmatter.raw_lines)
    return _assemble(new_lines, body)


def render_variant(frontmatter: Frontmatter, body: str, level: str) -> str:
    """Render the variant file for ``level``.

    The variant ``name:`` is rewritten to ``{base}-{level}``; ``model:``
    and ``effort:`` are inserted (or replaced) per ``LEVEL_TABLE``;
    ``implements:`` and ``levels:`` are stripped.
    """
    primitive = LEVEL_TABLE[level]
    base_name = frontmatter.name or '<unknown>'
    variant_name = f'{base_name}-{level}'

    new_lines: list[str] = []
    name_replaced = False
    for line in strip_role_fields(frontmatter.raw_lines):
        if not name_replaced and _starts_with_key(line, 'name'):
            new_lines.append(f'name: {variant_name}')
            name_replaced = True
            continue
        # Drop pre-existing model/effort lines (canonicals must not have
        # them, but be defensive — strip any that slip through).
        if _starts_with_key(line, 'model') or _starts_with_key(line, 'effort'):
            continue
        new_lines.append(line)

    if not name_replaced:
        new_lines.insert(0, f'name: {variant_name}')

    # Append model and (optional) effort lines.
    new_lines.append(f'model: {primitive["model"]}')
    if primitive['effort'] is not None:
        new_lines.append(f'effort: {primitive["effort"]}')

    return _assemble(new_lines, body)


def _assemble(frontmatter_lines: list[str], body: str) -> str:
    block = '\n'.join(frontmatter_lines)
    return f'---\n{block}\n---\n{body}'


@lru_cache(maxsize=8)
def _load_mapping(mapping_path: Path) -> dict:
    """Cache parsed ``mapping.json`` content keyed by absolute path.

    Variant emission iterates per-agent and per-level; without caching, this
    file is re-read and re-parsed for every level of every role-eligible
    agent. The cache is keyed by ``Path`` (which is hashable). Use
    ``_load_mapping.cache_clear()`` between distinct mapping files in tests.
    Returns ``{}`` when the file is missing or malformed so the caller's
    conservative refuse-emit path is preserved.
    """
    if not mapping_path.exists():
        return {}
    try:
        parsed: dict = json.loads(mapping_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed


def supports_effort(model_alias: str, effort: str, mapping_path: Path) -> bool:
    """Read ``mapping.json::model_map`` and decide whether the alias accepts ``effort``.

    Inspects ``mapping.json::model_map[model_alias].supports_effort`` and
    returns ``True`` iff the array contains the requested ``effort`` value.
    When the mapping file is missing, malformed, or the alias is absent /
    lacks the ``supports_effort`` shape, returns ``False`` — the
    conservative refuse-emit so we never silently emit unsupported variants.
    """
    mapping = _load_mapping(mapping_path)
    model_map = mapping.get('model_map', {})
    entry = model_map.get(model_alias)
    if not isinstance(entry, dict):
        return False
    supported = entry.get('supports_effort', [])
    if not isinstance(supported, list):
        return False
    return effort in supported


@dataclass
class VariantEmissionResult:
    """Outcome of variant emission for a single canonical agent."""

    canonical_path: Path
    variants_emitted: list[str]
    variants_skipped: list[tuple[str, str]]  # (level, reason)


def emit_variants_for_agent(
    source: Path,
    canonical_dest: Path,
    mapping_path: Path,
) -> VariantEmissionResult | None:
    """Emit canonical + per-level variants for a single agent file.

    Returns ``None`` when the agent does not opt into variant emission
    (no ``implements:`` declaration, or absent frontmatter). Otherwise
    writes the canonical no-suffix file at ``canonical_dest`` and
    sibling ``{base}-{level}.md`` files in the same directory, then
    returns the emission summary.
    """
    text = source.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(text)
    if not is_role_eligible(frontmatter):
        return None
    assert frontmatter is not None  # for type narrowing

    validate_canonical(frontmatter, source)

    canonical_dest.parent.mkdir(parents=True, exist_ok=True)
    canonical_dest.write_text(render_canonical(frontmatter, body), encoding='utf-8')

    levels = selected_levels(frontmatter)
    base_name = frontmatter.name or canonical_dest.stem
    emitted: list[str] = []
    skipped: list[tuple[str, str]] = []

    for level in levels:
        primitive = LEVEL_TABLE[level]
        effort = primitive['effort']
        if effort in ALIAS_GATED_EFFORTS:
            alias = primitive['model']
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
        variant_path = canonical_dest.with_name(f'{base_name}-{level}.md')
        variant_path.write_text(render_variant(frontmatter, body, level), encoding='utf-8')
        emitted.append(level)

    return VariantEmissionResult(
        canonical_path=canonical_dest,
        variants_emitted=emitted,
        variants_skipped=skipped,
    )
