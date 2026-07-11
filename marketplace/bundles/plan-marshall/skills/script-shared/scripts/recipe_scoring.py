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

# =============================================================================
# Pre-diagnosed-change SHAPE signal (surgical-fix recipe only)
# =============================================================================
# A recipe request whose narrative describes a *pre-diagnosed surgical change*
# — a stated root cause co-occurring with an exact-change / file-path anchor —
# should clear the confidence floor for the ``recipe-surgical-fix`` recipe even
# when its keyword density is low (a request that narrates the *bug* rarely
# repeats the recipe's own vocabulary). This SHAPE signal is scored by
# ``_score_prediagnosed_shape`` and blended into ``score_recipe`` ONLY for the
# surgical-fix recipe; it never alters scoring for any other recipe.
#
# The concreteness anchors mirror ``_cmd_planning_lane``'s S5 machinery (a
# repo-relative file-path anchor, a fenced code block, a
# ``python3 .plan/execute-script.py`` CLI invocation, or an inline ``manage-*``
# notation) — defined locally so this shared core stays self-contained.
_SHAPE_PATH_RE = re.compile(r'[\w./-]+/[\w.-]+\.[A-Za-z0-9]+')
_SHAPE_FENCE_RE = re.compile(r'```')
_SHAPE_CLI_RE = re.compile(r'python3\s+\.plan/execute-script\.py')
_SHAPE_NOTATION_RE = re.compile(r'\bmanage-[a-z-]+\b')

# A stated root cause — the diagnosis half of the pre-diagnosed shape.
_SHAPE_ROOT_CAUSE_RE = re.compile(r'\broot[\s-]cause\b', re.IGNORECASE)
# An exact-change / completed-diagnosis marker — the request states the change
# is already known, not something to discover.
_SHAPE_PREDIAGNOSED_RE = re.compile(
    r'\broot[\s-]cause\s+known\b'
    r'|\bexact\s+change(?:\s+known)?\b'
    r'|\bexact\s+edit\b'
    r'|\bdiagnosis\s+is\s+complete\b'
    r'|\bthe\s+fix\s+is\b',
    re.IGNORECASE,
)
# Discovery-demand veto — a request that asks to REVIEW / RESTRUCTURE / INVESTIGATE
# a whole surface is not a pre-diagnosed surgical change, however well its root
# cause is stated. Any veto hit forces the shape score to zero so a broad
# consolidation/analysis request never auto-routes to the surgical micro-lane.
_SHAPE_DISCOVERY_VETO_RE = re.compile(
    r'\b(?:full\s+)?structural\s+review\b'
    r'|\bconsolidat(?:e|es|ed|ing|ion)\b'
    r'|\binto\s+a\s+coherent\b'
    r'|\banaly[sz]e\s+why\b'
    r'|\binvestigate\b'
    r'|\bfigure\s+out\s+why\b'
    r'|\bdiagnose\s+why\b'
    r'|\breview\s+the\s+(?:current\s+)?[\w-]+\s+surface\b',
    re.IGNORECASE,
)

# Shape-score bands. A strong pre-diagnosed shape (root cause AND an exact-change
# marker, with a concreteness anchor) clears the auto-route threshold; an
# exact-change-only shape sits at the threshold; a generic root-cause-plus-anchor
# shape clears only the minimum-confidence floor.
_SHAPE_STRONG = 0.75
_SHAPE_AUTO_ROUTE = 0.6
_SHAPE_FLOOR = 0.45


def _has_concrete_anchor(narrative: str) -> bool:
    """Return True when the narrative carries an exact-change / file anchor.

    Mirrors ``_cmd_planning_lane``'s S5 concreteness check: a repo-relative path,
    a fenced code block, a plan-marshall CLI invocation, or a ``manage-*``
    notation. Any one is sufficient.
    """
    return bool(
        _SHAPE_PATH_RE.search(narrative)
        or _SHAPE_FENCE_RE.search(narrative)
        or _SHAPE_CLI_RE.search(narrative)
        or _SHAPE_NOTATION_RE.search(narrative)
    )


def _score_prediagnosed_shape(narrative: str | None) -> float:
    """Score the pre-diagnosed-change SHAPE of a request narrative in ``[0, 1]``.

    The shape is a stated root cause co-occurring with an exact-change / file
    anchor. A request that instead demands discovery — a structural review,
    consolidation, or investigation of a whole surface — is vetoed to ``0.0``
    however well its root cause is stated, because it is not a pre-diagnosed
    surgical change. Returns:

    - ``0.0`` — no narrative, a discovery-demand veto hit, no concreteness
      anchor, or no diagnosis signal at all;
    - ``0.45`` — a generic root-cause statement plus an anchor (clears the
      minimum-confidence floor, below the auto-route threshold);
    - ``0.6`` — an exact-change marker plus an anchor (at the auto-route floor);
    - ``0.75`` — a stated root cause AND an exact-change marker plus an anchor
      (a strong pre-diagnosed shape, clears the auto-route floor).
    """
    if not narrative:
        return 0.0
    if _SHAPE_DISCOVERY_VETO_RE.search(narrative):
        return 0.0
    if not _has_concrete_anchor(narrative):
        return 0.0
    root_cause = bool(_SHAPE_ROOT_CAUSE_RE.search(narrative))
    prediagnosed = bool(_SHAPE_PREDIAGNOSED_RE.search(narrative))
    if not (root_cause or prediagnosed):
        return 0.0
    if root_cause and prediagnosed:
        return _SHAPE_STRONG
    if prediagnosed:
        return _SHAPE_AUTO_ROUTE
    return _SHAPE_FLOOR


def _is_surgical_fix_recipe(recipe: dict[str, Any]) -> bool:
    """Return True when the recipe's registry identity is ``recipe-surgical-fix``.

    Reuses ``_recipe_skill_dir_candidates`` (which normalizes the ``skill`` /
    ``name`` / ``key`` identity across registry sources into ``recipe-*``
    directory-name candidates) so the shape signal is keyed to the surgical-fix
    recipe regardless of which identity field the registry populated.
    """
    return 'recipe-surgical-fix' in _recipe_skill_dir_candidates(recipe)


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
        from _cmd_skill_resolution import _discover_all_recipes
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

    The ``skill`` field carries a notation prefix that varies by source — a
    bundle-notation ``{bundle}:{skill}`` for extension-registered recipes (e.g.
    ``plan-marshall:recipe-surgical-fix``) or a ``project:{skill}`` for
    project-discovered ones — so its final ``:``-delimited segment is taken as
    the candidate skill-directory name. A bare (unprefixed) skill name is
    unchanged.
    """
    raw: list[str] = []
    skill = recipe.get('skill')
    if isinstance(skill, str) and skill:
        # Drop ANY leading ``{prefix}:`` notation segment (bundle- or project-
        # notation) so the bare ``recipe-*`` directory name survives the
        # ``recipe-``-prefix filter below.
        raw.append(skill.rsplit(':', 1)[-1])
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
        from marketplace_bundles import resolve_bundles_root

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
        from marketplace_paths import resolve_project_skill_path
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
    narrative_text: str | None = None,
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

    For the ``recipe-surgical-fix`` recipe ONLY, the raw ``narrative_text`` (when
    supplied) is additionally scored for the pre-diagnosed-change SHAPE
    (``_score_prediagnosed_shape``) and blended as ``max(keyword-blend,
    shape-score)`` — so a textbook pre-diagnosed surgical request whose narrative
    describes the *bug* rather than repeating the recipe's own vocabulary still
    clears the confidence floor (and, for a strong shape match, the auto-route
    threshold) independent of keyword density. The shape signal is
    surgical-fix-specific and NEVER alters scoring for any other recipe; when
    ``narrative_text`` is omitted the behavior is byte-identical to the pure blend.

    The breakdown dict records the matched tokens so the caller can
    surface them in findings / logs; for the surgical-fix recipe it additionally
    carries the ``shape_score``.
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

    # Surgical-fix-specific SHAPE arm: blend the pre-diagnosed-change shape score
    # as max(keyword-blend, shape-score). Applied ONLY for the surgical-fix
    # recipe, so scoring for every other recipe is byte-identical to the pure
    # blend above.
    if narrative_text is not None and _is_surgical_fix_recipe(recipe):
        shape_score = _score_prediagnosed_shape(narrative_text)
        breakdown['shape_score'] = round(shape_score, 3)
        if shape_score > confidence:
            confidence = round(shape_score, 3)

    return confidence, breakdown
