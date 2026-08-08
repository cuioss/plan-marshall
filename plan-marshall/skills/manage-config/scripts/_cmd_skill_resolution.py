# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Skill resolution and discovery command handlers for manage-config.

Handles: resolve-domain-skills, resolve-workflow-skill-extension, get-skills-by-profile,
         resolve-outline-skill, list-recipes, resolve-recipe, list-verify-steps,
         list-finalize-steps
"""

import re

from _cmd_skill_domains import (
    _build_skill_dict_with_descriptions,
    load_profiles_from_bundle,
)
from _config_core import (
    MarshalNotInitializedError,
    error_exit,
    get_skill_description,
    load_config,
    require_initialized,
    success_exit,
)

# Direct imports - PYTHONPATH set by executor
from extension_discovery import (
    discover_all_extensions,
)
from marketplace_paths import (
    iter_project_skill_dirs,
)


def cmd_resolve_domain_skills(args) -> dict:
    """Handle resolve-domain-skills command.

    Loads profiles from extension.py via bundle reference, then aggregates
    core + profile skills with descriptions.
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    domain = args.domain
    profile = args.profile

    # Validate domain exists
    if domain not in skill_domains:
        return error_exit(f'Unknown domain: {domain}')

    domain_config = skill_domains[domain]

    # Get bundle reference - required for profile resolution
    bundle = domain_config.get('bundle')
    if not bundle:
        return error_exit(f"Domain '{domain}' has no bundle configured")

    # Load profiles from extension.py
    ext_data = load_profiles_from_bundle(bundle, domain)
    profiles = ext_data.get('profiles', {})

    if not profiles:
        return error_exit(f"Bundle '{bundle}' has no profiles defined")

    # Validate profile exists
    if profile not in profiles and profile != 'core':
        available = [k for k in profiles.keys() if k != 'core']
        return error_exit(
            f'Unknown profile: {profile} for domain: {domain}. Available profiles: {", ".join(available)}'
        )

    # Aggregate: core + profile skills
    core_config = profiles.get('core', {})
    profile_config = profiles.get(profile, {})

    defaults = core_config.get('defaults', []) + profile_config.get('defaults', [])
    optionals = core_config.get('optionals', []) + profile_config.get('optionals', [])

    # Build output with descriptions
    defaults_with_desc = _build_skill_dict_with_descriptions(defaults)
    optionals_with_desc = _build_skill_dict_with_descriptions(optionals)

    # Include project_skills if attached to this domain
    project_skills = domain_config.get('project_skills', [])
    project_skills_with_desc = {s: get_skill_description(s) for s in project_skills}

    result: dict = {
        'domain': domain,
        'profile': profile,
        'defaults': defaults_with_desc,
        'optionals': optionals_with_desc,
    }

    # Surface the resolved profile's declared package_source — the manage-architecture
    # module --full field this profile iterates (implementation: packages,
    # module_testing: test_packages). This is the data-driven source the built-in
    # recipe selection flow reads to derive recipe_package_source for an arbitrary
    # profile, replacing the hardcoded profile->source switch. Profiles that declare
    # no package_source (core/quality) omit the key.
    package_source = profile_config.get('package_source')
    if package_source is not None:
        result['package_source'] = package_source

    if project_skills_with_desc:
        result['project_skills'] = project_skills_with_desc

    return success_exit(result)


def cmd_resolve_workflow_skill_extension(args) -> dict:
    """Resolve workflow skill extension for a domain and type."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    domain = args.domain
    ext_type = args.type

    # Return null extension if domain doesn't exist (not an error)
    if domain not in skill_domains:
        return success_exit({'domain': domain, 'type': ext_type, 'extension': None})

    domain_config = skill_domains[domain]
    extensions = domain_config.get('workflow_skill_extensions', {})
    extension = extensions.get(ext_type)  # None if not present

    return success_exit({'domain': domain, 'type': ext_type, 'extension': extension})


def cmd_get_skills_by_profile(args) -> dict:
    """Get skills organized by profile for a domain.

    Returns all skills grouped by profile name, with core skills merged into each.
    Uses extension.py as the source for profile data (not marshal.json).
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    domain = args.domain
    if domain not in skill_domains:
        return error_exit(f'Unknown domain: {domain}')

    domain_config = skill_domains[domain]

    # Get bundle reference
    bundle = domain_config.get('bundle')
    if not bundle:
        # System domain or flat domain - return top-level defaults
        defaults = domain_config.get('defaults', [])
        optionals = domain_config.get('optionals', [])
        return success_exit(
            {
                'domain': domain,
                'skills_by_profile': {'core': defaults + optionals},
            }
        )

    # Load profiles from extension.py
    ext_data = load_profiles_from_bundle(bundle, domain)
    profiles = ext_data.get('profiles', {})

    if not profiles:
        return error_exit(f"Bundle '{bundle}' has no profiles defined")

    # Build skills_by_profile: for each profile, merge core + profile skills
    core_skills = profiles.get('core', {}).get('defaults', []) + profiles.get('core', {}).get('optionals', [])
    # Extract just skill names
    from _cmd_skill_domains import _extract_skill_names

    core_skill_names = _extract_skill_names(core_skills)

    skills_by_profile: dict[str, list[str]] = {}
    for profile_name, profile_data in profiles.items():
        if profile_name == 'core':
            continue

        # Start with core skills
        combined = list(core_skill_names)
        seen = set(core_skill_names)

        # Add profile-specific skills
        profile_skills = profile_data.get('defaults', []) + profile_data.get('optionals', [])
        for entry in profile_skills:
            skill = _extract_skill_names([entry])[0] if isinstance(entry, (str, dict)) else str(entry)
            if skill and skill not in seen:
                combined.append(skill)
                seen.add(skill)

        # Add integration_testing skills to module_testing (heuristic for test profiles)
        if profile_name == 'module_testing':
            integration = profiles.get('integration_testing', {})
            for entry in integration.get('defaults', []) + integration.get('optionals', []):
                skill = _extract_skill_names([entry])[0] if isinstance(entry, (str, dict)) else str(entry)
                if skill and 'integration' in skill.lower() and skill not in seen:
                    combined.append(skill)
                    seen.add(skill)

        skills_by_profile[profile_name] = combined

    return success_exit({'domain': domain, 'skills_by_profile': skills_by_profile})


# =============================================================================
# Recipe Discovery
# =============================================================================


def _leading_frontmatter_block(content: str) -> str:
    """Return the leading ``---``...``---`` YAML frontmatter block of *content*.

    Mirrors the leading-frontmatter delimiting logic in
    ``_read_frontmatter_order``: the block is recognized only when the first
    line is ``---`` and a closing ``---`` follows. Returns the text between the
    delimiters, or an empty string when no leading frontmatter block is present.
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return ''
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i])
    return ''


def _discover_all_recipes() -> list[dict]:
    """Discover all recipes at runtime from extensions and project skills."""
    all_recipes: list[dict] = []

    # Source 1: Extension provides_recipes()
    extensions = discover_all_extensions()
    for ext in extensions:
        module = ext.get('module')
        if not module or not hasattr(module, 'provides_recipes'):
            continue
        try:
            recipes = module.provides_recipes()
            if not recipes:
                continue
            all_domains = module.get_skill_domains()
            domain_key = all_domains[0].get('domain', {}).get('key', '') if all_domains else ''
            for recipe in recipes:
                entry = dict(recipe)
                entry['domain'] = domain_key
                entry['source'] = 'extension'
                all_recipes.append(entry)
        except Exception:
            pass

    # Source 2: Project recipe-* skills (across the target's layout roots)
    seen_recipe: set[str] = set()
    for skill_dir in iter_project_skill_dirs():
        if not skill_dir.name.startswith('recipe-') or skill_dir.name in seen_recipe:
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            continue

        seen_recipe.add(skill_dir.name)
        content = skill_md.read_text()

        # Extract frontmatter description
        description = ''
        fm_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
        if fm_match:
            description = fm_match.group(1).strip()

        # Extract recipe discovery metadata from frontmatter keys — the
        # structured project-recipe counterpart to provides_recipes(). The
        # markdown body is NOT scanned for these keys; frontmatter is the
        # sole source of truth (see ext-point-recipe.md § Project Recipe
        # Frontmatter). recipe_domain is required; a recipe whose frontmatter
        # omits it is silently skipped (intentional discovery containment).
        frontmatter = _leading_frontmatter_block(content)
        if not frontmatter:
            continue
        domain_match = re.search(r'^recipe_domain:\s*(.+)$', frontmatter, re.MULTILINE)
        domain = domain_match.group(1).strip().strip("'\"") if domain_match else ''
        profile_match = re.search(r'^recipe_profile:\s*(.+)$', frontmatter, re.MULTILINE)
        profile = profile_match.group(1).strip().strip("'\"") if profile_match else ''
        package_source_match = re.search(r'^recipe_package_source:\s*(.+)$', frontmatter, re.MULTILINE)
        package_source = package_source_match.group(1).strip().strip("'\"") if package_source_match else ''

        if not domain:
            continue

        key = skill_dir.name[len('recipe-') :]
        all_recipes.append(
            {
                'key': key,
                'name': description or skill_dir.name,
                'description': description,
                'skill': f'project:{skill_dir.name}',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
                'domain': domain,
                'profile': profile,
                'package_source': package_source,
                'source': 'project',
            }
        )

    return all_recipes


def cmd_list_recipes(args) -> dict:
    """List all available recipes discovered at runtime."""
    all_recipes = _discover_all_recipes()
    return success_exit({'recipes': all_recipes, 'count': len(all_recipes)})


def cmd_resolve_recipe(args) -> dict:
    """Resolve a specific recipe by key."""
    recipe_key = args.recipe
    all_recipes = _discover_all_recipes()

    for recipe in all_recipes:
        if recipe.get('key') == recipe_key:
            return success_exit(
                {
                    'recipe_key': recipe['key'],
                    'recipe_name': recipe.get('name', ''),
                    'recipe_skill': recipe.get('skill', ''),
                    'default_change_type': recipe.get('default_change_type', ''),
                    'scope': recipe.get('scope', ''),
                    'domain': recipe.get('domain', ''),
                    'profile': recipe.get('profile', ''),
                    'package_source': recipe.get('package_source', ''),
                }
            )

    return error_exit(f'Recipe not found: {recipe_key}')


# =============================================================================
# Finalize Step Discovery
# =============================================================================


# Maps the discovery query's `source` field to the legacy `type` field surfaced
# in `list-finalize-steps`. The discovery query is the single source of truth for
# the source classification; `type` is the public output column derived from it.
_SOURCE_TO_TYPE = {
    'built-in': 'built-in',
    'bundle-optional': 'skill',
    'project': 'project',
}


def _discover_all_finalize_steps() -> list[dict]:
    """Discover all finalize steps via the reusable extension-discovery query.

    Built-in (``default:*``), bundle-optional (e.g. ``plan-marshall:plan-retrospective``),
    and project (``project:finalize-step-*``) finalize steps ALL flow from the
    single ``extension_discovery.find_implementors`` query — membership is declared
    on each step doc via ``implements: ...ext-point-finalize-step`` and discovered
    by the query; there is no parallel per-source glob. The contract lives in the
    central standard (``ext-point-finalize-step.md``).

    Each result dict carries `name` / `description` / `type` / `source` / `order`,
    preserving the historical `list-finalize-steps` output columns. The `type`
    column is derived from the query's `source` via :data:`_SOURCE_TO_TYPE`.
    Sorting and collision handling beyond the query's own (`order`, `name`) sort
    are the caller's responsibility (marshall-steward).
    """
    from _config_defaults import FINALIZE_STEP_EXT_POINT
    from extension_discovery import find_implementors

    return [
        {
            'name': rec['name'],
            'description': rec.get('description', ''),
            'type': _SOURCE_TO_TYPE.get(rec.get('source', ''), rec.get('source', '')),
            'source': rec.get('source', ''),
            'order': rec.get('order', 0),
        }
        for rec in find_implementors(FINALIZE_STEP_EXT_POINT)
    ]


def cmd_list_finalize_steps(args) -> dict:
    """List all available finalize steps discovered at runtime."""
    all_steps = _discover_all_finalize_steps()
    return success_exit({'steps': all_steps, 'count': len(all_steps)})


def cmd_resolve_outline_skill(args) -> dict:
    """Resolve outline skill for a domain."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    domain = args.domain

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    # Check for domain-specific outline skill
    if domain in skill_domains:
        domain_config = skill_domains[domain]
        outline_skill = domain_config.get('outline_skill')
        if outline_skill:
            return success_exit({'domain': domain, 'skill': outline_skill, 'source': 'domain_specific'})

    # No domain override — generic instructions will be used
    return success_exit({'domain': domain, 'skill': 'none', 'source': 'generic'})
