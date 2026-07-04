# SPDX-License-Identifier: FSL-1.1-ALv2
"""recipe-match command handler for manage-config.

Generalizes the lesson-only recipe matcher (phase-1-init Step 5c, via
``manage-lessons auto-suggest``) into a registry-wide, request-text-driven
recipe scorer. Given free-form ``--request-text``, it tokenizes the text,
scores every recipe in the live registry via the shared ``recipe_scoring``
core, filters by the minimum-confidence floor, and returns the ranked
``matches[]`` plus a ``top_match`` and a ``meets_auto_route_threshold``
boolean (top confidence ``>=`` the auto-route threshold, default ``0.6``).

Heuristic-first contract: this verb performs NO LLM call and NO plan-scoped
read. The bounded LLM fallback for ambiguous matches is the orchestrator's
responsibility (phase-1-init), mirroring how ``change-type-heuristic`` and
``planning-lane route`` keep the LLM out of the script body. Because the
request is free-form (no plan domain/scope available), keyword overlap is the
sole scoring signal — ``plan_domain`` and ``plan_scope`` are passed as
``None``.
"""

from __future__ import annotations

from typing import Any

from recipe_scoring import (
    MIN_CONFIDENCE,
    load_registry,
    read_recipe_lane_seed,
    score_recipe,
    tokenize,
)

# Default auto-route threshold: a top match at or above this confidence is
# a high-confidence match the orchestrator may auto-route without prompting.
# Set to 0.6 to match the keyword-only scoring ceiling for free-form requests
# (plan_domain=plan_scope=None, keyword weight 0.6): a perfect keyword match
# scores 0.6, so the floor must be 0.6 for auto-route to be reachable.
_DEFAULT_THRESHOLD = 0.6


def cmd_recipe_match(args) -> dict[str, Any]:
    """Return recipes ranked by deterministic confidence against request text.

    The caller (phase-1-init Tier 1 recipe-match) consumes the return TOON:
    when ``meets_auto_route_threshold`` is ``true`` and
    ``auto_route_recipe == true``, the orchestrator routes to
    ``top_match.skill`` without prompting; otherwise it proposes the ranked
    ``matches`` via ``AskUserQuestion`` or falls through to the standard
    refine/outline flow.
    """
    request_text: str = args.request_text
    threshold: float = getattr(args, 'threshold', _DEFAULT_THRESHOLD)

    narrative_tokens = tokenize(request_text)
    recipes = load_registry()

    scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for recipe in recipes:
        # Free-form request text — no plan domain/scope available, so keyword
        # overlap is the sole signal (pass None for both).
        confidence, breakdown = score_recipe(recipe, narrative_tokens, None, None)
        if confidence < MIN_CONFIDENCE:
            continue
        scored.append((confidence, recipe, breakdown))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].get('key') or '',
            item[1].get('skill') or '',
        ),
    )

    matches: list[dict[str, Any]] = []
    for confidence, recipe, breakdown in scored:
        # Surface the recipe's execution-profile lane seed (§4.9 lowest-precedence
        # default). The orchestrator (phase-1-init) feeds it into the posture
        # dialogue as the recipe-recommended default, which the operator posture
        # and the coverage-cell adversarial floor then override. ``None`` when the
        # recipe declares no ``lane:`` block.
        lane_seed = read_recipe_lane_seed(recipe)
        match: dict[str, Any] = {
            'key': recipe.get('key'),
            'name': recipe.get('name'),
            'skill': recipe.get('skill'),
            'domain': recipe.get('domain'),
            'scope': recipe.get('scope'),
            'source': recipe.get('source'),
            'confidence': confidence,
            'breakdown': breakdown,
        }
        if lane_seed is not None:
            match['lane_seed'] = lane_seed
        matches.append(match)

    top_match = matches[0] if matches else None
    meets_auto_route_threshold = bool(top_match and top_match['confidence'] >= threshold)

    return {
        'status': 'success',
        'request_tokens': sorted(narrative_tokens),
        'recipes_evaluated': len(recipes),
        'threshold': threshold,
        'matches': matches,
        'count': len(matches),
        'top_match': top_match,
        'meets_auto_route_threshold': meets_auto_route_threshold,
    }
