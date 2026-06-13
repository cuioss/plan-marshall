"""
Skill resolution and discovery command handlers for manage-config.

Handles: resolve-domain-skills, resolve-workflow-skill-extension, get-skills-by-profile,
         configure-execute-task-skills, resolve-execute-task-skill, resolve-outline-skill,
         list-recipes, resolve-recipe, list-verify-steps, list-finalize-steps
"""

import re
from pathlib import Path

from _cmd_skill_domains import (
    _build_skill_dict_with_descriptions,
    _read_frontmatter_order,
    load_profiles_from_bundle,
)
from _config_core import (
    BUNDLES_DIR,
    MarshalNotInitializedError,
    error_exit,
    get_skill_description,
    is_nested_domain,
    load_config,
    require_initialized,
    resolve_bundle_path,
    save_config,
    success_exit,
)

# Direct imports - PYTHONPATH set by executor
from extension_discovery import (  # type: ignore[import-not-found]
    discover_all_extensions,
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


def cmd_configure_execute_task_skills(args) -> dict:
    """Configure execute-task skills from discovered profiles."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    # Ensure system domain exists
    if 'system' not in skill_domains:
        return error_exit('System domain not configured. Run skill-domains configure first.')

    # Discover all unique profiles from configured domains
    discovered_profiles = set()

    for domain_key, domain_config in skill_domains.items():
        if domain_key == 'system':
            continue
        if not is_nested_domain(domain_config):
            continue

        # Load profiles from extension.py
        bundle = domain_config.get('bundle')
        if bundle:
            ext_data = load_profiles_from_bundle(bundle, domain_key)
            profiles = ext_data.get('profiles', {})
            for key in profiles.keys():
                if key != 'core':
                    discovered_profiles.add(key)

    # Build execute_task_skills mapping: every profile maps to the unified
    # plan-marshall:execute-task skill (the lone skill that exists; there are no
    # per-profile execute-task-{profile} skills). This matches the
    # DEFAULT_EXECUTE_TASK_SKILLS seed and the phase-5 resolve-execute-task-skill
    # consumer.
    execute_task_skills = {}
    for profile in sorted(discovered_profiles):
        # Skip quality profile - it's handled by verify phase, not task execution
        if profile == 'quality':
            continue
        execute_task_skills[profile] = 'plan-marshall:execute-task'

    # Update system domain with execute_task_skills
    system_config = skill_domains['system']
    system_config['execute_task_skills'] = execute_task_skills
    skill_domains['system'] = system_config

    config['skill_domains'] = skill_domains
    save_config(config)

    return success_exit(
        {
            'status': 'success',
            'execute_task_skills_configured': len(execute_task_skills),
            'skills': execute_task_skills,
        }
    )


def cmd_resolve_execute_task_skill(args) -> dict:
    """Resolve execute-task skill for a given profile."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    profile = args.profile
    config = load_config()
    skill_domains = config.get('skill_domains', {})
    system_config = skill_domains.get('system', {})
    execute_task_skills = system_config.get('execute_task_skills', {})

    if not execute_task_skills:
        return error_exit('No execute_task_skills configured. Run configure-execute-task-skills first.')

    if profile not in execute_task_skills:
        available = sorted(execute_task_skills.keys())
        return error_exit(f"Unknown profile '{profile}'. Available profiles: {', '.join(available)}")

    execute_task_skill = execute_task_skills[profile]

    return success_exit({'profile': profile, 'execute_task_skill': execute_task_skill})


# =============================================================================
# Recipe Discovery
# =============================================================================


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

    # Source 2: Project recipe-* skills
    claude_skills = Path('.claude/skills')
    if claude_skills.is_dir():
        for skill_dir in sorted(claude_skills.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith('recipe-'):
                continue
            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.exists():
                continue

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
            domain_match = re.search(r'^recipe_domain:\s*(.+)$', content, re.MULTILINE)
            domain = domain_match.group(1).strip() if domain_match else ''
            profile_match = re.search(r'^recipe_profile:\s*(.+)$', content, re.MULTILINE)
            profile = profile_match.group(1).strip() if profile_match else ''
            package_source_match = re.search(r'^recipe_package_source:\s*(.+)$', content, re.MULTILINE)
            package_source = package_source_match.group(1).strip() if package_source_match else ''

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


def _discover_all_finalize_steps() -> list[dict]:
    """Discover all finalize steps from built-in, project, and extension sources.

    Each result dict includes an `order` field (int) or `None` when the source
    authoritative file/return dict does not declare one. Sorting and collision
    handling are the caller's responsibility (marshall-steward).
    """
    from _config_defaults import (
        BUILT_IN_FINALIZE_STEP_DESCRIPTIONS,
        BUILT_IN_FINALIZE_STEPS,
        OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS,
        OPTIONAL_BUNDLE_FINALIZE_STEPS,
    )

    all_steps: list[dict] = []
    claude_skills = Path('.claude/skills')

    # Source 1: Built-in steps — read order from workflow/{name}.md or
    # standards/{name}.md frontmatter (workflow/ takes precedence). Resolve the
    # concrete doc path per step via resolve_bundle_path so the versioned
    # plugin-cache layout is handled (directory-level probing is brittle there).
    for step_name in BUILT_IN_FINALIZE_STEPS:
        bare = step_name.split(':', 1)[1] if ':' in step_name else step_name
        workflow_path = resolve_bundle_path(
            BUNDLES_DIR, 'plan-marshall', f'skills/phase-6-finalize/workflow/{bare}.md'
        )
        doc_path = (
            workflow_path
            if workflow_path.is_file()
            else resolve_bundle_path(BUNDLES_DIR, 'plan-marshall', f'skills/phase-6-finalize/standards/{bare}.md')
        )
        all_steps.append(
            {
                'name': step_name,
                'description': BUILT_IN_FINALIZE_STEP_DESCRIPTIONS.get(step_name, step_name),
                'type': 'built-in',
                'source': 'built-in',
                'order': _read_frontmatter_order(doc_path),
            }
        )

    # Source 2: Project finalize-step-* skills (e.g. plugin-doctor, regenerate-executor)
    if claude_skills.is_dir():
        for skill_dir in sorted(claude_skills.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith('finalize-step-'):
                continue
            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.exists():
                continue

            step_ref = f'project:{skill_dir.name}'
            all_steps.append(
                {
                    'name': step_ref,
                    'description': get_skill_description(step_ref),
                    'type': 'project',
                    'source': 'project',
                    'order': _read_frontmatter_order(skill_md),
                }
            )

    # Source 4: Bundle-optional finalize steps (opt-in via OPTIONAL_BUNDLE_FINALIZE_STEPS)
    # These appear in list-finalize-steps but are absent from DEFAULT_PLAN_FINALIZE,
    # so projects must explicitly add them to marshal.json to activate. Each entry
    # is a fully-qualified `bundle:skill` reference; we resolve to the SKILL.md path
    # under BUNDLES_DIR (marketplace layout) and parse frontmatter for order +
    # description.
    #
    # Source ordering: emitted before Source 3 (extension) so that the existing
    # contract — every non-extension step precedes every extension step — is
    # preserved. De-duplication against earlier sources mirrors the project-skill
    # filter above.
    seen_names = {entry['name'] for entry in all_steps}
    for step_ref in OPTIONAL_BUNDLE_FINALIZE_STEPS:
        if step_ref in seen_names:
            continue
        if ':' not in step_ref:
            continue
        bundle, skill = step_ref.split(':', 1)
        skill_md = resolve_bundle_path(BUNDLES_DIR, bundle, f'skills/{skill}/SKILL.md')
        description = get_skill_description(step_ref)
        # Fall back to the curated description map when SKILL.md is missing or
        # has no description field (get_skill_description returns the bare
        # notation in that case).
        if description == step_ref:
            description = OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS.get(step_ref, step_ref)
        all_steps.append(
            {
                'name': step_ref,
                'description': description,
                'type': 'skill',
                'source': 'bundle-optional',
                'order': _read_frontmatter_order(skill_md),
            }
        )
        seen_names.add(step_ref)

    # Source 3: Extension provides_finalize_steps()
    extensions = discover_all_extensions()
    for ext in extensions:
        module = ext.get('module')
        if not module or not hasattr(module, 'provides_finalize_steps'):
            continue
        try:
            steps = module.provides_finalize_steps()
            if not steps:
                continue
            for step in steps:
                order_value = step.get('order')
                all_steps.append(
                    {
                        'name': step.get('name', step.get('skill', '')),
                        'description': step.get('description', ''),
                        'type': 'skill',
                        'source': 'extension',
                        'order': int(order_value) if isinstance(order_value, int) else None,
                    }
                )
        except Exception:
            pass

    return all_steps


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
