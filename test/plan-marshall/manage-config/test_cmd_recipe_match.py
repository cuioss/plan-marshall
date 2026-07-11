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

_recipe_scoring_mod = load_script_module('plan-marshall', 'script-shared', 'recipe_scoring.py')
read_recipe_lane_seed = _recipe_scoring_mod.read_recipe_lane_seed
_parse_recipe_lane_block = _recipe_scoring_mod._parse_recipe_lane_block
_normalize_recipe_lane_seed = _recipe_scoring_mod._normalize_recipe_lane_seed


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


def _seed_surgical_fix_recipe(skills_dir: Path) -> None:
    """Seed the ``recipe-surgical-fix`` recipe with a realistic description.

    The description deliberately shares almost no vocabulary with a real
    pre-diagnosed request narrative (which describes the *bug*, not the recipe),
    so a keyword-only score floors below MIN_CONFIDENCE — the shape arm is what
    lifts it above the auto-route threshold.
    """
    _write_recipe(
        skills_dir,
        'recipe-surgical-fix',
        frontmatter={
            'name': 'recipe-surgical-fix',
            'description': 'Micro-lane recipe for a pre-diagnosed surgical fix bounded to a single module',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
        body='# Surgical Fix\n',
    )


# Real archived request narratives (lesson 2026-07-09-14-001) — a pre-diagnosed
# surgical request (PR #866, must MATCH) and a broad structural-review request
# (PR #856, must NOT match).
_REQ_PREDIAGNOSED_SURGICAL = (
    'Fix the owed CHECK_ERA era stamps in the audit skill (root cause known, '
    'exact change known, single file): in '
    '`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` update '
    "the CHECK_ERA registry — `lane-lever-effectiveness` and "
    "`track-selection-accuracy` from `'#854'` to `'#862'`, "
    "`merge-window-accounting` from `'#849'` to `'#863'` — and update the "
    'adjacent registry comments to match. Bounded footprint, no behavior change '
    'beyond era attribution.'
)

_REQ_BROAD_STRUCTURAL_REVIEW = (
    'Fix two independent defects in terminal-title handling and '
    'refactor/consolidate the title-handling surface into a coherent structure. '
    'Diagnosis is complete and evidence-backed. The plan MUST include a full '
    'structural review of the current title-handling surface and refactor it '
    'toward coherence.'
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
# Tie-breaker determinism — equal-confidence recipes resolve to a stable top_match
# =============================================================================


def test_tie_breaker_produces_stable_top_match(plan_context, tmp_path, monkeypatch):
    """Equal-confidence recipes always resolve to the same top_match via secondary sort keys.

    Without a stable tie-breaker the sort order depends on load_registry insertion
    order (filesystem/discovery), so equal-confidence recipes would produce
    nondeterministic auto-routing.  The fix adds secondary keys (recipe 'key', then
    'skill') so the winner is always the lexicographically earlier recipe key.
    """
    skills_dir = _make_skills_root(tmp_path)

    # Seed two recipes that share identical distinctive tokens — both will score
    # the same keyword confidence against the request text below.
    _write_recipe(
        skills_dir,
        'recipe-alpha',
        frontmatter={
            'name': 'recipe-alpha',
            'description': 'wombat xylitol',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
    )
    _write_recipe(
        skills_dir,
        'recipe-beta',
        frontmatter={
            'name': 'recipe-beta',
            'description': 'wombat xylitol',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
    )
    monkeypatch.chdir(tmp_path)

    # Request echoing the shared tokens — both recipes score equally.
    result = cmd_recipe_match(_ns('wombat xylitol'))

    assert result['status'] == 'success'
    assert result['count'] == 2
    # Both share the same confidence; the tie-breaker must resolve 'alpha' first.
    confidences = {m['key']: m['confidence'] for m in result['matches']}
    assert confidences['alpha'] == confidences['beta'], 'pre-condition: equal confidence'
    top = result['top_match']
    assert top is not None
    assert top['key'] == 'alpha', f'expected alpha to win tie-break; got {top["key"]}'
    # Verify ranking is stable: alpha must be first in matches[] too.
    assert result['matches'][0]['key'] == 'alpha'


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


# =============================================================================
# Pre-diagnosed-change SHAPE arm — surgical-fix auto-routing (end-to-end)
# =============================================================================


def test_prediagnosed_surgical_request_auto_routes_to_surgical_fix(plan_context, tmp_path, monkeypatch):
    """A real pre-diagnosed surgical request auto-routes to recipe-surgical-fix.

    The request narrates the bug (low keyword overlap with the recipe), so only
    the pre-diagnosed-change SHAPE arm can lift it — proving the arm flows
    through cmd_recipe_match into meets_auto_route_threshold and top_match.
    """
    skills_dir = _make_skills_root(tmp_path)
    _seed_surgical_fix_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns(_REQ_PREDIAGNOSED_SURGICAL))

    assert result['status'] == 'success'
    top = result['top_match']
    assert top is not None
    assert top['key'] == 'surgical-fix'
    assert result['meets_auto_route_threshold'] is True
    assert top['confidence'] >= 0.6
    assert top['breakdown']['shape_score'] == 0.75


def test_broad_structural_review_request_does_not_auto_route(plan_context, tmp_path, monkeypatch):
    """A broad structural-review request does NOT auto-route to surgical-fix.

    The discovery-demand veto forces the shape score to zero, and the low
    keyword overlap leaves the recipe below the auto-route threshold (typically
    below the MIN_CONFIDENCE floor entirely).
    """
    skills_dir = _make_skills_root(tmp_path)
    _seed_surgical_fix_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns(_REQ_BROAD_STRUCTURAL_REVIEW))

    assert result['status'] == 'success'
    assert result['meets_auto_route_threshold'] is False
    surgical = next((m for m in result['matches'] if m['key'] == 'surgical-fix'), None)
    if surgical is not None:
        assert surgical['breakdown']['shape_score'] == 0.0


def test_keyword_arm_unaffected_by_shape_for_non_surgical_recipe(plan_context, tmp_path, monkeypatch):
    """A non-surgical recipe still auto-routes purely on keyword overlap.

    The shape arm is surgical-fix-specific: a distinct keyword-matching recipe
    keeps its keyword-only score and lane-seed contract unchanged even when a
    surgical-fix recipe is also present in the registry.
    """
    skills_dir = _make_skills_root(tmp_path)
    _seed_surgical_fix_recipe(skills_dir)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird'))

    top = result['top_match']
    assert top is not None
    assert top['key'] == 'hummingbird'
    assert top['confidence'] == 0.6
    # A non-surgical recipe carries the pure 4-key breakdown (no shape_score).
    assert 'shape_score' not in top['breakdown']


# =============================================================================
# Recipe lane seed (deliverable 8)
# =============================================================================
#
# A recipe may declare an execution-profile lane seed in its SKILL.md frontmatter
# (a `profile` posture + optional per-element `steps` overrides) — the
# lowest-precedence input to the lane resolver. recipe-match surfaces it as
# `lane_seed` on each match.


def _write_recipe_with_lane(skills_dir: Path, name: str, *, description: str, lane_block: str) -> Path:
    """Seed a project recipe whose frontmatter carries a nested ``lane:`` seed block."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '---\n'
        f'name: {name}\n'
        f'description: {description}\n'
        'recipe_domain: plan-marshall-plugin-dev\n'
        f'{lane_block}'
        '---\n\n'
        f'# {name}\n'
    )
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text(content)
    return skill_md


# --- _parse_recipe_lane_block / _normalize_recipe_lane_seed (pure) -----------


def test_parse_recipe_lane_block_profile_and_steps():
    """The recipe lane block parser captures the profile posture and step overrides."""
    text = '---\nname: recipe-x\nlane:\n  profile: auto\n  steps:\n    sonar-roundtrip: off\n---\n'
    block = _parse_recipe_lane_block(text)
    assert block == {'profile': 'auto', 'steps': {'sonar-roundtrip': 'off'}}


def test_parse_recipe_lane_block_profile_only():
    """A recipe lane block may carry only a posture (no steps map)."""
    text = '---\nname: recipe-x\nlane:\n  profile: full\n---\n'
    assert _parse_recipe_lane_block(text) == {'profile': 'full'}


def test_parse_recipe_lane_block_absent_returns_none():
    """A SKILL.md with no lane: frontmatter block yields no seed."""
    text = '---\nname: recipe-x\ndescription: no lane here\n---\n'
    assert _parse_recipe_lane_block(text) is None


def test_normalize_recipe_lane_seed_drops_invalid_entries():
    """Invalid postures and overrides are dropped during normalization."""
    seed = _normalize_recipe_lane_seed({'profile': 'bogus', 'steps': {'a': 'off', 'b': 'nonsense'}})
    assert seed == {'steps': {'a': 'off'}}


def test_normalize_recipe_lane_seed_all_invalid_returns_none():
    """A seed with nothing valid normalizes to None."""
    assert _normalize_recipe_lane_seed({'profile': 'bogus'}) is None


def test_read_recipe_lane_seed_from_direct_lane_key():
    """An extension recipe carrying a `lane` dict directly is read without file resolution."""
    recipe = {'key': 'x', 'lane': {'profile': 'auto', 'steps': {'sonar-roundtrip': 'off'}}}
    assert read_recipe_lane_seed(recipe) == {'profile': 'auto', 'steps': {'sonar-roundtrip': 'off'}}


def test_read_recipe_lane_seed_absent_yields_none():
    """A recipe with neither a direct lane key nor a resolvable SKILL.md yields None."""
    assert read_recipe_lane_seed({'key': 'no-such-recipe-zzz'}) is None


# --- recipe-match integration ------------------------------------------------


def test_recipe_match_surfaces_lane_seed(plan_context, tmp_path, monkeypatch):
    """A matched recipe declaring a lane: seed surfaces it as `lane_seed` on the match."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe_with_lane(
        skills_dir,
        'recipe-pangolin',
        description='pangolin zephyr quokka',
        lane_block='lane:\n  profile: auto\n  steps:\n    sonar-roundtrip: off\n',
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('pangolin zephyr quokka recipe-pangolin'))

    match = next(m for m in result['matches'] if m['key'] == 'pangolin')
    assert match['lane_seed'] == {'profile': 'auto', 'steps': {'sonar-roundtrip': 'off'}}


def test_recipe_match_without_lane_seed_omits_key(plan_context, tmp_path, monkeypatch):
    """A recipe with no lane: block yields a match WITHOUT a lane_seed key."""
    skills_dir = _make_skills_root(tmp_path)
    _seed_full_overlap_recipe(skills_dir)
    monkeypatch.chdir(tmp_path)

    result = cmd_recipe_match(_ns('hummingbird zephyr quokka recipe-hummingbird'))

    match = next(m for m in result['matches'] if m['key'] == 'hummingbird')
    assert 'lane_seed' not in match
