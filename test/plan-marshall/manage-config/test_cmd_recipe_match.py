#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the recipe-match command in manage-config.

The recipe-match verb (Tier 1 routing) scores free-form request text against
the live recipe registry via the shared ``recipe_scoring`` core. It is
heuristic-first: no LLM call, no plan-scoped read — keyword overlap against the
recipe descriptions is the sole signal (request text carries no plan
domain/scope). It returns the ranked ``matches[]``, a ``top_match``, and a
``meets_auto_route_threshold`` boolean (top confidence ``>= --threshold``,
default ``0.6``).

Scoring note (load-bearing for the assertions below): ``score_recipe`` blends
``0.6 * keyword + 0.25 * domain + 0.15 * scope``. A free-form request carries
no plan domain/scope, so ``domain_score == scope_score == 0`` and the blended
confidence is exactly ``0.6 * keyword_score`` — capped at ``0.6`` even on a
perfect keyword match. The default ``--threshold`` is therefore set to ``0.6``
so a perfect keyword match exactly meets the auto-route bar (``>=`` comparison);
the tests exercise the ``--threshold`` boundary across that ``[0, 0.6]`` band.

Because ``recipe_scoring.load_registry`` resolves project recipes relative to
the process cwd, every test seeds an isolated temp ``.claude/skills/`` tree and
runs against it (``monkeypatch.chdir`` for in-process Tier-2 tests, ``cwd=``
for the Tier-3 subprocess argv-boundary test). This keeps the assertions
independent of the live project recipe corpus.

Tier 2 (direct import) tests with a Tier 3 subprocess test for CLI plumbing /
constructed-argv assertion at the argparse boundary.
"""

from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH

from conftest import load_script_module, run_script

_cmd_recipe_match_mod = load_script_module('plan-marshall', 'manage-config', '_cmd_recipe_match.py')
cmd_recipe_match = _cmd_recipe_match_mod.cmd_recipe_match


# =============================================================================
# Fixture builders
# =============================================================================


def _write_recipe(
    skills_dir: Path,
    name: str,
    *,
    frontmatter: dict[str, str] | None = None,
    body: str = '',
) -> Path:
    """Create a `.claude/skills/{name}/SKILL.md` with the given frontmatter+body."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = ['---']
    for key, value in (frontmatter or {}).items():
        fm_lines.append(f'{key}: {value}')
    fm_lines.append('---')
    content = '\n'.join(fm_lines) + '\n\n' + body
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text(content)
    return skill_md


def _make_skills_root(tmp_path: Path) -> Path:
    """Create an isolated `<tmp>/.claude/skills` directory and return it."""
    skills_dir = tmp_path / '.claude' / 'skills'
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def _seed_full_overlap_recipe(skills_dir: Path) -> None:
    """Seed a recipe whose tokens a request can match in full.

    description ``hummingbird zephyr quokka`` + name ``recipe-hummingbird``
    tokenizes to four recipe tokens: ``hummingbird``, ``zephyr``, ``quokka``,
    ``recipe-hummingbird`` (the hyphenated name token survives; the bare
    stop-word ``recipe`` does not). A request echoing all four reaches the
    keyword ceiling (1.0 → confidence 0.6).
    """
    _write_recipe(
        skills_dir,
        'recipe-hummingbird',
        frontmatter={
            'name': 'recipe-hummingbird',
            'description': 'hummingbird zephyr quokka',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
        body='# Hummingbird\n',
    )


def _ns(request_text: str, threshold: float = 0.6) -> Namespace:
    return Namespace(request_text=request_text, threshold=threshold)


# =============================================================================
# Matching behavior — Tier 2
# =============================================================================


def test_keyword_overlap_produces_ranked_match(plan_context, tmp_path, monkeypatch):
    """A request echoing a recipe's distinctive tokens produces a ranked match."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    # Echo the full description + name token so keyword overlap is total.
    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird'))

    assert result['status'] == 'success'
    assert result['count'] >= 1
    top = result['top_match']
    assert top is not None
    assert top['key'] == 'hummingbird'
    # Full keyword overlap with no domain/scope signal caps confidence at 0.6.
    assert top['confidence'] == 0.6


def test_top_match_surfaces_recipe_fields(plan_context, tmp_path, monkeypatch):
    """The ranked match carries the recipe key, name, skill, domain, and breakdown."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka'))

    match = next(m for m in result['matches'] if m['key'] == 'hummingbird')
    assert match['skill'] == 'project:recipe-hummingbird'
    assert match['domain'] == 'plan-marshall-plugin-dev'
    assert 'confidence' in match
    assert 'breakdown' in match


# =============================================================================
# Below-floor request (empty matches) — Tier 2
# =============================================================================


def test_below_floor_request_returns_empty_matches(plan_context, tmp_path, monkeypatch):
    """A request that overlaps no recipe returns empty matches and no top match."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    # No token overlap with the seeded 'hummingbird zephyr quokka' recipe.
    result = cmd_recipe_match(_ns('xylophone marmalade obsidian'))

    assert result['status'] == 'success'
    assert result['count'] == 0
    assert result['matches'] == []
    assert result['top_match'] is None
    assert result['meets_auto_route_threshold'] is False


# =============================================================================
# meets_auto_route_threshold boundary (custom thresholds across the band) — Tier 2
# =============================================================================


def test_default_threshold_met_by_perfect_keyword_match(plan_context, tmp_path, monkeypatch):
    """A perfect keyword match meets the default 0.6 auto-route threshold.

    With no plan domain/scope, confidence is capped at 0.6 (the keyword weight).
    The default ``--threshold`` is 0.6, so a perfect keyword match scoring exactly
    0.6 clears the auto-route bar via the ``>=`` comparison — auto-route is
    reachable from request text alone for an unambiguous match.
    """
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird'))

    top = result['top_match']
    assert top is not None
    assert top['confidence'] == 0.6
    assert result['threshold'] == 0.6
    assert result['meets_auto_route_threshold'] is True


def test_custom_threshold_at_top_confidence_meets(plan_context, tmp_path, monkeypatch):
    """A custom --threshold at exactly the top confidence flips the boolean true (>=)."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    # Full overlap → 0.6; a 0.6 threshold meets via the >= comparison.
    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird', threshold=0.6))

    top = result['top_match']
    assert top is not None
    assert top['confidence'] == 0.6
    assert result['threshold'] == 0.6
    assert result['meets_auto_route_threshold'] is True


def test_custom_threshold_above_top_confidence_does_not_meet(plan_context, tmp_path, monkeypatch):
    """A custom --threshold just above the top confidence flips the boolean false."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird', threshold=0.61))

    top = result['top_match']
    assert top is not None
    assert top['confidence'] < 0.61
    assert result['meets_auto_route_threshold'] is False


def test_custom_threshold_below_top_confidence_meets(plan_context, tmp_path, monkeypatch):
    """A low custom --threshold below the top confidence flips the boolean true."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka', threshold=0.3))

    top = result['top_match']
    assert top is not None
    assert top['confidence'] >= 0.3
    assert result['threshold'] == 0.3
    assert result['meets_auto_route_threshold'] is True


# =============================================================================
# CLI plumbing — constructed-argv assertion at the argparse boundary (Tier 3)
# =============================================================================


def test_cli_recipe_match_argv_boundary(plan_context, tmp_path):
    """Constructed-argv: recipe-match runs end-to-end through argparse and emits TOON."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)

    result = run_script(
        SCRIPT_PATH,
        'recipe-match',
        '--request-text',
        'hummingbird zephyr quokka recipe-hummingbird',
        cwd=tmp_path,
    )

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    # Default 0.6 threshold is met by a perfect keyword match (0.6 >= 0.6).
    assert data['threshold'] == 0.6
    assert data['meets_auto_route_threshold'] is True


def test_cli_recipe_match_custom_threshold_argv(plan_context, tmp_path):
    """Constructed-argv: --threshold parses as a float and flows into the result."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)

    result = run_script(
        SCRIPT_PATH,
        'recipe-match',
        '--request-text',
        'hummingbird zephyr quokka recipe-hummingbird',
        '--threshold',
        '0.6',
        cwd=tmp_path,
    )

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data['threshold'] == 0.6
    assert data['meets_auto_route_threshold'] is True


def test_cli_recipe_match_missing_request_text_rejected(plan_context, tmp_path):
    """Constructed-argv: omitting the required --request-text is an argparse rejection."""
    result = run_script(SCRIPT_PATH, 'recipe-match', cwd=tmp_path)

    # argparse rejects the missing required flag with exit code 2.
    assert result.returncode == 2
