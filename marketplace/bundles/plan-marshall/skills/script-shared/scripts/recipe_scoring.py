#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic recipe-scoring core — the single shared matcher.

Notation: imported as a module (PYTHONPATH) — ``from recipe_scoring import
tokenize, score_recipe, load_registry``. NOT an executor entry point.

This module is the ONE implementation of the keyword/intent-overlap scoring
used to match a request narrative against the marketplace recipe registry. It
is consumed by the lesson-auto-suggest path (``manage-lessons``'s
``_cmd_auto_suggest.py``) and by the generalized recipe-match verb
(``manage-config``'s ``_cmd_recipe_match.py``) so both score against a single
source rather than duplicating the logic.

The functions are pure with one exception: ``load_registry`` performs the same
registry read the auto-suggest path already performed (discovering the live
recipe registry via ``manage-config``'s discovery helper). There are no
plan-scoped reads — the caller supplies the narrative tokens and any plan
domain/scope signals.
"""

from __future__ import annotations

import re
from typing import Any

# Confidence floor below which a recipe is dropped from the suggestion
# list — keeps the LLM dispatch fallback as the responsible path for
# weakly-matching plans.
_MIN_CONFIDENCE = 0.35

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


def tokenize(text: str) -> set[str]:
    """Return the lower-cased, stop-word-filtered token set of ``text``.

    Tokens shorter than three characters and stop-words are dropped so the
    overlap score stays meaningful on short descriptions.
    """
    tokens = {m.group(0).lower() for m in _TOKEN_RE.finditer(text or '')}
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}


def load_registry() -> list[dict[str, Any]]:
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


def score_recipe(
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
    recipe_tokens = tokenize(description)

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
