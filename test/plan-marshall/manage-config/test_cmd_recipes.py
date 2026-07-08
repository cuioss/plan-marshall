#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for list-recipes and resolve-recipe commands in manage-config.

Project recipes are discovered at runtime from `.claude/skills/recipe-*`
SKILL.md files. Discovery metadata (`recipe_domain` / `recipe_profile` /
`recipe_package_source`) is read from YAML frontmatter only — the markdown
body is never scanned for these keys (frontmatter is the sole source of
truth; see ext-point-recipe.md § Project Recipe Frontmatter).

Because `_discover_all_recipes()` resolves `.claude/skills` relative to the
process cwd, every test here builds an isolated temp `.claude/skills/` tree
and runs against it (chdir for in-process tests, `cwd=` for subprocess
tests). This keeps the tests independent of the live project recipe corpus,
whose migration to frontmatter lands in a separate deliverable.

Tier 2 (direct import) tests with Tier 3 subprocess tests for CLI plumbing.
"""

from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH

from conftest import load_script_module, run_script

_cmd_skill_resolution = load_script_module('plan-marshall', 'manage-config', '_cmd_skill_resolution.py')

cmd_list_recipes = _cmd_skill_resolution.cmd_list_recipes
cmd_resolve_recipe = _cmd_skill_resolution.cmd_resolve_recipe


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
    """Create a `.claude/skills/{name}/SKILL.md` with the given frontmatter+body.

    `frontmatter` keys are written verbatim as `key: value` lines inside the
    YAML frontmatter block. `body` is appended after the closing `---`.
    """
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


# A body that carries the legacy "shadow" shape: a prose line AND an
# Input-Parameters table row, each bearing a backticked recipe key followed by
# a *different* backticked token. Under the old body-table scraper this would
# overwrite the real value; under frontmatter parsing it is structurally inert.
_SHADOW_BODY = """# Recipe

Note: `recipe_domain` and `recipe_package_source` are discussed below.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |
| `recipe_domain` | `shadow-domain-from-body` |
| `recipe_profile` | `shadow-profile-from-body` |
| `recipe_package_source` | `shadow-source-from-body` |
"""


# =============================================================================
# list-recipes Tests (Tier 2 - direct import, isolated fixture)
# =============================================================================


def test_list_recipes_returns_success(plan_context, tmp_path, monkeypatch):
    """list-recipes returns success status with recipes + count keys."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    assert result['status'] == 'success'
    assert 'recipes' in result
    assert 'count' in result


def test_list_recipes_includes_project_recipe(plan_context, tmp_path, monkeypatch):
    """list-recipes discovers a project recipe-* skill from frontmatter."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'name': 'recipe-sample',
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
        body='# Sample\n',
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    assert result['status'] == 'success'
    keys = {r['key'] for r in result['recipes']}
    assert 'sample' in keys


def test_list_recipes_includes_domain(plan_context, tmp_path, monkeypatch):
    """list-recipes resolves the domain key from frontmatter."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    sample = next(r for r in result['recipes'] if r['key'] == 'sample')
    assert sample['domain'] == 'plan-marshall-plugin-dev'


# =============================================================================
# Frontmatter-channel Tests (Tier 2 - direct import, isolated fixture)
# =============================================================================


def test_domain_resolved_from_frontmatter_not_body(plan_context, tmp_path, monkeypatch):
    """The body is never scanned — frontmatter recipe_domain wins over a body shadow."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-shadowed',
        frontmatter={
            'description': 'Shadowed recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
        body=_SHADOW_BODY,
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='shadowed'))

    assert result['status'] == 'success'
    # The frontmatter value, not the body-table/prose `shadow-domain-from-body`.
    assert result['domain'] == 'plan-marshall-plugin-dev'


def test_profile_and_package_source_resolved_from_frontmatter(plan_context, tmp_path, monkeypatch):
    """recipe_profile and recipe_package_source resolve from frontmatter."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-full',
        frontmatter={
            'description': 'Full recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
            'recipe_profile': 'implementation',
            'recipe_package_source': 'packages',
        },
        body=_SHADOW_BODY,
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='full'))

    assert result['status'] == 'success'
    assert result['profile'] == 'implementation'
    assert result['package_source'] == 'packages'


def test_recipe_without_frontmatter_domain_is_skipped(plan_context, tmp_path, monkeypatch):
    """A recipe whose frontmatter omits recipe_domain is silently skipped."""
    skills_dir = _make_skills_root(tmp_path)
    # No recipe_domain in frontmatter — only a body-table row, which is inert.
    _write_recipe(
        skills_dir,
        'recipe-missing-domain',
        frontmatter={'description': 'No domain in frontmatter'},
        body=_SHADOW_BODY,
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    keys = {r['key'] for r in result['recipes']}
    assert 'missing-domain' not in keys


def test_profile_omitted_in_frontmatter_resolves_empty(plan_context, tmp_path, monkeypatch):
    """A recipe declaring only recipe_domain resolves profile/package_source empty.

    Regression for the legacy shadow defect where a prose `recipe_profile`
    mention resolved profile to the literal `recipe_package_source`.
    """
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-domain-only',
        frontmatter={
            'description': 'Domain only',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
        body=_SHADOW_BODY,
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='domain-only'))

    assert result['status'] == 'success'
    assert result['profile'] == ''
    assert result['package_source'] == ''


# =============================================================================
# Extension-recipe surfacing Tests (Tier 2 - live provides_recipes() source)
#
# The two audit recipes are registered through the plan-marshall extension's
# provides_recipes() (Source 1 of _discover_all_recipes), not the project-local
# .claude/skills scanner (Source 2). They therefore surface from the live
# bundle extension regardless of the temp fixture cwd. An isolated cwd keeps
# the project-recipe (Source 2) noise out so the assertions stay focused on the
# extension source.
# =============================================================================


def _recipe_by_key(recipes, key):
    """Return the single recipe dict with the given key, or None."""
    matches = [r for r in recipes if r.get('key') == key]
    return matches[0] if matches else None


def test_list_recipes_surfaces_code_review_extension_recipe(plan_context, tmp_path, monkeypatch):
    """list-recipes surfaces the code-review recipe from provides_recipes()."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    assert result['status'] == 'success'
    recipe = _recipe_by_key(result['recipes'], 'code-review')
    assert recipe is not None, 'code-review must surface via list-recipes'
    assert recipe['skill'] == 'plan-marshall:recipe-code-review'
    assert recipe['source'] == 'extension'


def test_list_recipes_surfaces_security_audit_extension_recipe(plan_context, tmp_path, monkeypatch):
    """list-recipes surfaces the security-audit recipe from provides_recipes()."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    assert result['status'] == 'success'
    recipe = _recipe_by_key(result['recipes'], 'security-audit')
    assert recipe is not None, 'security-audit must surface via list-recipes'
    assert recipe['skill'] == 'plan-marshall:recipe-security-audit'
    assert recipe['source'] == 'extension'


def test_resolve_recipe_resolves_code_review(plan_context, tmp_path, monkeypatch):
    """resolve-recipe resolves the code-review extension recipe."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='code-review'))

    assert result['status'] == 'success'
    assert result['recipe_key'] == 'code-review'
    assert result['recipe_skill'] == 'plan-marshall:recipe-code-review'


def test_resolve_recipe_resolves_security_audit(plan_context, tmp_path, monkeypatch):
    """resolve-recipe resolves the security-audit extension recipe."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='security-audit'))

    assert result['status'] == 'success'
    assert result['recipe_key'] == 'security-audit'
    assert result['recipe_skill'] == 'plan-marshall:recipe-security-audit'


def test_list_recipes_surfaces_surgical_fix_extension_recipe(plan_context, tmp_path, monkeypatch):
    """list-recipes surfaces the surgical-fix recipe from provides_recipes()."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_list_recipes(Namespace())

    assert result['status'] == 'success'
    recipe = _recipe_by_key(result['recipes'], 'surgical-fix')
    assert recipe is not None, 'surgical-fix must surface via list-recipes'
    assert recipe['skill'] == 'plan-marshall:recipe-surgical-fix'
    assert recipe['source'] == 'extension'


def test_resolve_recipe_resolves_surgical_fix(plan_context, tmp_path, monkeypatch):
    """resolve-recipe resolves the surgical-fix extension recipe."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='surgical-fix'))

    assert result['status'] == 'success'
    assert result['recipe_key'] == 'surgical-fix'
    assert result['recipe_skill'] == 'plan-marshall:recipe-surgical-fix'


# =============================================================================
# resolve-recipe Tests (Tier 2 - direct import, isolated fixture)
# =============================================================================


def test_resolve_recipe_found(plan_context, tmp_path, monkeypatch):
    """resolve-recipe returns recipe metadata for a project recipe."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
            'recipe_profile': 'implementation',
        },
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='sample'))

    assert result['status'] == 'success'
    assert result['recipe_key'] == 'sample'
    assert 'project:recipe-sample' in result['recipe_skill']
    assert result['domain'] == 'plan-marshall-plugin-dev'


def test_resolve_recipe_returns_profile(plan_context, tmp_path, monkeypatch):
    """resolve-recipe returns profile from frontmatter metadata."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
            'recipe_profile': 'implementation',
        },
    )
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='sample'))

    assert result['status'] == 'success'
    assert result['profile'] == 'implementation'


def test_resolve_recipe_not_found(plan_context, tmp_path, monkeypatch):
    """resolve-recipe returns error for an unknown recipe."""
    _make_skills_root(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = cmd_resolve_recipe(Namespace(recipe='nonexistent-recipe'))

    assert result['status'] == 'error'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess, isolated fixture via cwd=)
# =============================================================================


def test_cli_list_recipes(plan_context, tmp_path):
    """CLI plumbing: list-recipes outputs TOON success."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
    )

    result = run_script(SCRIPT_PATH, 'list-recipes', cwd=tmp_path)

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'success' in result.stdout.lower()


def test_cli_resolve_recipe(plan_context, tmp_path):
    """CLI plumbing: resolve-recipe outputs the resolved recipe key."""
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-sample',
        frontmatter={
            'description': 'Sample recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
        },
    )

    result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'sample', cwd=tmp_path)

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'sample' in result.stdout


def test_cli_frontmatter_survives_body_shadow_end_to_end(plan_context, tmp_path):
    """End-to-end regression: frontmatter channel survives the body shadow shape.

    A recipe whose frontmatter declares recipe_domain/recipe_profile/
    recipe_package_source AND whose body carries the legacy shadow shape
    (prose + table rows with a backticked key followed by a *different*
    backticked token) must resolve to the FRONTMATTER values through the CLI,
    proving the body is never scanned end-to-end.
    """
    skills_dir = _make_skills_root(tmp_path)
    _write_recipe(
        skills_dir,
        'recipe-e2e',
        frontmatter={
            'description': 'End-to-end recipe',
            'recipe_domain': 'plan-marshall-plugin-dev',
            'recipe_profile': 'implementation',
            'recipe_package_source': 'packages',
        },
        body=_SHADOW_BODY,
    )

    result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'e2e', cwd=tmp_path)

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # Frontmatter values, never the body's `shadow-*-from-body` tokens.
    assert data['domain'] == 'plan-marshall-plugin-dev'
    assert data['profile'] == 'implementation'
    assert data['package_source'] == 'packages'
    assert 'shadow' not in result.stdout
