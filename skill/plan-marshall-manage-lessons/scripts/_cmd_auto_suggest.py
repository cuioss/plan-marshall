#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

from typing import Any

from _findings_core import add_finding
from _plan_parsing import parse_document_sections
from _status_core import read_status
from file_ops import get_plan_dir
from recipe_scoring import (
    MIN_CONFIDENCE,
    load_registry,
    score_recipe,
    tokenize,
)

# Maximum suggestions returned. The todo caps this at 3.
_DEFAULT_MAX_SUGGESTIONS = 3


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

    recipes = load_registry()
    narrative_tokens = tokenize(narrative)

    scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for recipe in recipes:
        confidence, breakdown = score_recipe(
            recipe,
            narrative_tokens,
            plan_domain if isinstance(plan_domain, str) else None,
            plan_scope if isinstance(plan_scope, str) else None,
        )
        if confidence < MIN_CONFIDENCE:
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
