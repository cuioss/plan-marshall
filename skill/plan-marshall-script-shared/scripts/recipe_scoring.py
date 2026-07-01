#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic recipe-scoring core — the single shared matcher.

Notation: imported as a module (PYTHONPATH) — ``from recipe_scoring import
tokenize, score_recipe, load_registry, read_recipe_lane_seed``. NOT an executor
entry point.

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
from pathlib import Path
from typing import Any

# Execution-profile postures a recipe may seed (the lowest-precedence default in
# the §4.9 precedence chain: recipe seed < operator posture < coverage-cell
# adversarial floor). The element-lane contract is owned by
# extension-api/standards/ext-point-lane-element.md.
_VALID_RECIPE_POSTURES = ('minimal', 'auto', 'full')
# Per-element override vocabulary a recipe seed may carry under ``steps:``.
_VALID_LANE_OVERRIDES = ('off', 'minimal', 'auto', 'full', 'ask')

# Confidence floor below which a recipe is dropped from the suggestion
# list — keeps the LLM dispatch fallback as the responsible path for
# weakly-matching plans.
MIN_CONFIDENCE = 0.35

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


def tokenize(text: str | None) -> set[str]:
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


def _parse_recipe_lane_block(text: str) -> dict[str, Any] | None:
    """Parse the recipe ``lane:`` seed block from a SKILL.md's frontmatter.

    The recipe seed block is DISTINCT from the per-element ``lane:`` block
    (``class`` / ``tier`` / ``cost_size``): it declares a ``profile`` posture and
    an optional ``steps`` map of per-element overrides, e.g.::

        lane:
          profile: auto
          steps:
            sonar-roundtrip: off

    Returns ``{'profile': ..., 'steps': {...}}`` (either key optional) or
    ``None`` when the file declares no leading-frontmatter ``lane:`` block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    seed: dict[str, Any] = {}
    steps: dict[str, str] = {}
    in_lane = False
    in_steps = False
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if not in_lane:
            if line.rstrip() == 'lane:':
                in_lane = True
            continue
        # A 4-space-indented entry under an open ``steps:`` mapping.
        if in_steps and line.startswith('    ') and ':' in line:
            key, _, value = line.strip().partition(':')
            steps[key.strip()] = value.strip().strip('"').strip("'")
            continue
        if line.startswith('  ') and ':' in line:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if stripped == 'steps:':
                in_steps = True
                continue
            in_steps = False
            key, _, value = stripped.partition(':')
            if key.strip() == 'profile':
                seed['profile'] = value.strip().strip('"').strip("'")
        else:
            # A dedented (column-0) line ends the lane block.
            break
    if steps:
        seed['steps'] = steps
    return seed or None


def _normalize_recipe_lane_seed(block: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate + normalize a recipe lane seed, dropping invalid entries.

    Returns a seed carrying a valid ``profile`` and/or a non-empty ``steps`` map
    of valid overrides, or ``None`` when nothing valid survives.
    """
    if not isinstance(block, dict):
        return None
    seed: dict[str, Any] = {}
    profile = block.get('profile')
    if profile in _VALID_RECIPE_POSTURES:
        seed['profile'] = profile
    raw_steps = block.get('steps')
    if isinstance(raw_steps, dict):
        steps = {
            str(step): str(override)
            for step, override in raw_steps.items()
            if str(override) in _VALID_LANE_OVERRIDES
        }
        if steps:
            seed['steps'] = steps
    return seed or None


def _recipe_skill_dir_candidates(recipe: dict[str, Any]) -> list[str]:
    """Derive candidate skill-directory names (``recipe-*``) for a recipe dict.

    Recipe registry identity varies by source (extension ``provides_recipes`` vs
    project discovery), so try the ``skill`` field, the ``name``, and
    ``recipe-{key}`` — each in both hyphen and underscore spellings — and keep
    only ``recipe-``-prefixed candidates in first-seen order.
    """
    raw: list[str] = []
    skill = recipe.get('skill')
    if isinstance(skill, str) and skill:
        raw.append(skill[len('project:') :] if skill.startswith('project:') else skill)
    name = recipe.get('name')
    if isinstance(name, str) and name:
        raw.append(name)
    key = recipe.get('key')
    if isinstance(key, str) and key:
        raw.append(f'recipe-{key}')

    candidates: list[str] = []
    for value in raw:
        for variant in (value, value.replace('_', '-'), value.replace('-', '_')):
            if variant.startswith('recipe-') and variant not in candidates:
                candidates.append(variant)
    return candidates


def _resolve_recipe_skill_md(recipe: dict[str, Any]) -> Path | None:
    """Resolve the matched recipe's SKILL.md path from its registry identity.

    Searches the marketplace bundle skill roots, then the project skill roots,
    for each candidate ``recipe-*`` directory name. Returns ``None`` when no
    SKILL.md is found.
    """
    candidates = _recipe_skill_dir_candidates(recipe)
    if not candidates:
        return None
    # Bundle recipes (extension-registered) live under the marketplace tree.
    try:
        from marketplace_bundles import resolve_bundles_root  # type: ignore[import-not-found]

        bundles_root: Path | None = resolve_bundles_root(Path(__file__))
    except (ImportError, ValueError, OSError):
        bundles_root = None
    if bundles_root is not None:
        for name in candidates:
            for candidate in sorted(bundles_root.glob(f'*/skills/{name}/SKILL.md')):
                if candidate.is_file():
                    return candidate
    # Project recipes live under the cwd-relative project skill roots (the same
    # cwd-relative discovery the registry uses — default base is Path.cwd()).
    try:
        from marketplace_paths import resolve_project_skill_path  # type: ignore[import-not-found]
    except ImportError:
        return None
    for name in candidates:
        try:
            project_candidate = resolve_project_skill_path(f'{name}/SKILL.md')
        except (ValueError, OSError):
            continue
        if project_candidate.is_file():
            return project_candidate
    return None


def read_recipe_lane_seed(recipe: dict[str, Any]) -> dict[str, Any] | None:
    """Return the recipe's execution-profile lane seed, or ``None`` when absent.

    The seed is the lowest-precedence input to the lane resolver (§4.9): a recipe
    declares a default posture (and optional per-element overrides) in its
    ``lane:`` frontmatter block, which the operator posture and the coverage-cell
    adversarial floor then override. A recipe dict that already carries a ``lane``
    mapping (extension-declared) is used directly; otherwise the recipe's SKILL.md
    is resolved and its ``lane:`` block parsed.
    """
    direct = recipe.get('lane')
    if isinstance(direct, dict):
        return _normalize_recipe_lane_seed(direct)
    skill_md = _resolve_recipe_skill_md(recipe)
    if skill_md is None:
        return None
    try:
        text = skill_md.read_text(encoding='utf-8')
    except OSError:
        return None
    return _normalize_recipe_lane_seed(_parse_recipe_lane_block(text))


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
