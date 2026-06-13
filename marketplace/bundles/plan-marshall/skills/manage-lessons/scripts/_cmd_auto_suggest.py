#!/usr/bin/env python3
"""Recipe-registry matcher for phase-1-init Step 5c.

Scans the marketplace recipe registry (`manage-config list-recipes`) and
returns up to N suggestions ordered by deterministic confidence. The
score blends keyword overlap (request narrative ∩ recipe description),
domain alignment (plan domain matches recipe domain), and scope
alignment (request scope hints match recipe scope). When no recipe
clears the minimum-confidence floor, the script returns an empty
``suggestions`` list and the caller dispatches the LLM
``research-best-practices`` workflow or proceeds with the standard
refine/outline flow.

The orchestrator (phase-1-init Step 5c) decides what to do with the
suggestions: persist the top suggestion to ``status.metadata.recipe_key``
when confidence clears the auto-accept floor, or surface the list for
user selection.
"""

from __future__ import annotations

import re
from typing import Any

from _findings_core import add_finding  # type: ignore[import-not-found]
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from _status_core import read_status  # type: ignore[import-not-found]
from file_ops import get_plan_dir  # type: ignore[import-not-found]

# Confidence floor below which a recipe is dropped from the suggestion
# list — keeps the LLM dispatch fallback as the responsible path for
# weakly-matching plans.
_MIN_CONFIDENCE = 0.35

# Maximum suggestions returned. The todo caps this at 3.
_DEFAULT_MAX_SUGGESTIONS = 3

# Stop-words removed from token sets before scoring. Keeps the score
# meaningful on short descriptions where filler words dominate the
# overlap.
_STOP_WORDS: frozenset[str] = frozenset({
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'have', 'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that',
    'the', 'this', 'to', 'was', 'were', 'will', 'with',
    # plan-marshall vocabulary that adds noise without distinguishing
    # one recipe from another
    'plan', 'plans', 'recipe', 'recipes', 'workflow', 'workflows',
    'standards', 'standard',
})

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z_-]+")


def _tokenize(text: str) -> set[str]:
    tokens = {m.group(0).lower() for m in _TOKEN_RE.finditer(text or '')}
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}


def _load_narrative(plan_id: str) -> tuple[str, str | None]:
    """Read the plan's request narrative for matching.

    Prefer the staged lesson body when present (lesson-derived plans),
    fall back to ``clarified_request`` / ``original_input`` in
    request.md. Returns ``(text, source_or_None)``.
    """
    plan_dir = get_plan_dir(plan_id)
    # Lesson-derived plans stage the body at lesson-{id}.md.
    for candidate in sorted(plan_dir.glob('lesson-*.md')):
        try:
            body = candidate.read_text(encoding='utf-8')
        except OSError:
            continue
        if body.strip():
            return body, f'lesson-body:{candidate.name}'

    request_path = plan_dir / 'request.md'
    if not request_path.exists():
        return '', None
    try:
        content = request_path.read_text(encoding='utf-8')
    except OSError:
        return '', None
    sections = parse_document_sections(content)
    for section in ('clarified_request', 'original_input'):
        section_body = sections.get(section)
        if isinstance(section_body, str) and section_body.strip():
            return section_body, section
    return '', None


def _load_plan_metadata(plan_id: str) -> dict[str, Any]:
    """Return a small subset of status.metadata for scoring.

    ``read_status`` raises ``FileNotFoundError`` on a missing status —
    we treat that as 'no metadata' rather than an error so the matcher
    can run on fresh plans before Step 4 has written the metadata
    fields.
    """
    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        return {}
    metadata = status.get('metadata', {}) if isinstance(status, dict) else {}
    return metadata if isinstance(metadata, dict) else {}


def _load_registry() -> list[dict[str, Any]]:
    """Return the live recipe registry via manage-config's discovery path."""
    try:
        from _cmd_skill_resolution import _discover_all_recipes  # type: ignore[import-not-found]
    except ImportError:
        return []
    try:
        recipes = _discover_all_recipes()
    except (FileNotFoundError, ValueError, OSError):
        return []
    return recipes if isinstance(recipes, list) else []


def _score_recipe(
    recipe: dict[str, Any],
    narrative_tokens: set[str],
    plan_domain: str | None,
    plan_scope: str | None,
) -> tuple[float, dict[str, Any]]:
    """Return ``(confidence, breakdown)`` for one recipe.

    Confidence is a blend in ``[0.0, 1.0]``:
      - ``keyword`` (weight 0.6): Jaccard-like overlap between narrative
        tokens and the recipe's description+name token set.
      - ``domain`` (weight 0.25): 1.0 when ``plan.metadata.domain``
        matches the recipe's domain (exact), 0.0 otherwise.
      - ``scope`` (weight 0.15): 1.0 when ``plan.metadata.scope_estimate``
        aligns with the recipe's scope (e.g., ``surgical`` plan ↔
        ``module`` recipe; ``broad`` plan ↔ ``codebase_wide`` recipe);
        0.0 otherwise.

    The breakdown dict records the matched tokens so the caller can
    surface them in findings / logs.
    """
    description = str(recipe.get('description', '')) + ' ' + str(recipe.get('name', ''))
    recipe_tokens = _tokenize(description)

    matched = narrative_tokens & recipe_tokens
    if recipe_tokens:
        keyword_score = len(matched) / max(len(recipe_tokens), 1)
    else:
        keyword_score = 0.0

    domain_score = 0.0
    recipe_domain = str(recipe.get('domain', '')).strip()
    if plan_domain and recipe_domain and plan_domain.strip().lower() == recipe_domain.lower():
        domain_score = 1.0

    scope_score = 0.0
    recipe_scope = str(recipe.get('scope', '')).strip().lower()
    if plan_scope:
        ps = plan_scope.strip().lower()
        if (ps in ('surgical', 'narrow', 'module', 'small')) and recipe_scope == 'module':
            scope_score = 1.0
        elif (ps in ('broad', 'wide', 'codebase', 'codebase_wide', 'large')) and recipe_scope == 'codebase_wide':
            scope_score = 1.0

    confidence = round(0.6 * keyword_score + 0.25 * domain_score + 0.15 * scope_score, 3)
    breakdown = {
        'keyword_score': round(keyword_score, 3),
        'domain_score': domain_score,
        'scope_score': scope_score,
        'matched_keywords': sorted(matched),
    }
    return confidence, breakdown


def _emit_finding(
    plan_id: str,
    recipe: dict[str, Any],
    confidence: float,
    breakdown: dict[str, Any],
    emit: bool,
) -> int:
    if not emit:
        return 0
    key = recipe.get('key', '?')
    detail = (
        f'Recipe {key!r} matches the plan narrative with confidence '
        f'{confidence}. Matched keywords: '
        f'{breakdown.get("matched_keywords") or "(domain/scope only)"}. '
        f'Run via: `/plan-marshall action=recipe --recipe {key}`, or set '
        f'``status.metadata.recipe_key={key}`` to auto-route at phase-3-outline.'
    )
    result = add_finding(
        plan_id=plan_id,
        finding_type='tip',
        title=f'auto-suggest: recipe {key!r} (confidence {confidence})',
        detail=detail,
        component='plan-marshall:manage-lessons:auto-suggest',
        rule=str(key),
        severity='info',
    )
    return 1 if result.get('status') == 'success' else 0


def cmd_auto_suggest(args) -> dict[str, Any]:
    """Return up to ``--max-suggestions`` recipes ranked by deterministic confidence.

    The caller (phase-1-init Step 5c) consumes the return TOON: when
    ``suggestions[0].confidence >= auto_accept_floor`` (caller-side
    threshold, typically 0.7), the orchestrator writes
    ``status.metadata.recipe_key = suggestions[0].key`` without
    prompting; otherwise the list is surfaced for user selection or
    the LLM fallback fires.
    """
    plan_id: str = args.plan_id
    emit: bool = not getattr(args, 'no_emit', False)
    max_suggestions: int = int(getattr(args, 'max_suggestions', _DEFAULT_MAX_SUGGESTIONS) or _DEFAULT_MAX_SUGGESTIONS)

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    narrative, narrative_source = _load_narrative(plan_id)
    if narrative_source is None:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'narrative_source': None,
            'suggestions': [],
            'count': 0,
            'findings_emitted': 0,
            'emit': emit,
            'reason': 'narrative_unavailable',
        }

    metadata = _load_plan_metadata(plan_id)
    plan_domain = metadata.get('domain') or metadata.get('plan_domain')
    plan_scope = metadata.get('scope_estimate')

    recipes = _load_registry()
    narrative_tokens = _tokenize(narrative)

    scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for recipe in recipes:
        confidence, breakdown = _score_recipe(
            recipe,
            narrative_tokens,
            plan_domain if isinstance(plan_domain, str) else None,
            plan_scope if isinstance(plan_scope, str) else None,
        )
        if confidence < _MIN_CONFIDENCE:
            continue
        scored.append((confidence, recipe, breakdown))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:max_suggestions]

    suggestions: list[dict[str, Any]] = []
    findings_emitted = 0
    for confidence, recipe, breakdown in top:
        suggestions.append(
            {
                'key': recipe.get('key'),
                'name': recipe.get('name'),
                'skill': recipe.get('skill'),
                'default_change_type': recipe.get('default_change_type'),
                'scope': recipe.get('scope'),
                'domain': recipe.get('domain'),
                'source': recipe.get('source'),
                'confidence': confidence,
                'breakdown': breakdown,
            }
        )
        findings_emitted += _emit_finding(plan_id, recipe, confidence, breakdown, emit)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'narrative_source': narrative_source,
        'plan_domain': plan_domain if isinstance(plan_domain, str) else None,
        'plan_scope': plan_scope if isinstance(plan_scope, str) else None,
        'recipes_evaluated': len(recipes),
        'suggestions': suggestions,
        'count': len(suggestions),
        'findings_emitted': findings_emitted,
        'emit': emit,
    }
