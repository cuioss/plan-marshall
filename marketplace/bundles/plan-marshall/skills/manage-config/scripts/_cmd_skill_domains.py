"""
Skill domains command handlers for manage-config.

Handles: skill-domains, resolve-domain-skills, list-recipes, resolve-recipe, list-finalize-steps

Domain discovery uses extension.py files in each bundle's plan-marshall-plugin skill.
Extension API functions:
- get_skill_domains() -> domain metadata with profiles
- provides_triage() -> triage skill reference or None
- provides_outline_skill() -> outline skill reference or None
- provides_verify_steps() -> list of verification step dicts
- provides_recipes() -> list of recipe definition dicts
- provides_finalize_steps() -> list of finalize step dicts
"""

import copy
import sys
from pathlib import Path

from _config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    error_exit,
    get_skill_description,
    is_nested_domain,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)
from _config_defaults import (
    DEFAULT_SYSTEM_DOMAIN,
)
from _config_detection import detect_domains

# Direct imports - PYTHONPATH set by executor
from extension_discovery import (  # type: ignore[import-not-found]
    discover_all_extensions,
    discover_extensions,
)


def _extract_skill_name(entry: str | dict) -> str:
    """Extract skill name from a skill entry.

    Skill entries can be plain strings or dicts with skill+description:
    - String: "pm-dev-java:java-core" -> "pm-dev-java:java-core"
    - Dict: {"skill": "pm-dev-java:java-core", "description": "..."} -> "pm-dev-java:java-core"

    Args:
        entry: Skill entry (string or dict)

    Returns:
        Skill name string
    """
    if isinstance(entry, dict):
        skill = entry.get('skill', '')
        return str(skill) if skill else ''
    return entry


def _extract_skill_description(entry: str | dict) -> str:
    """Extract description from a skill entry.

    Args:
        entry: Skill entry (string or dict)

    Returns:
        Description string (empty if not available)
    """
    if isinstance(entry, dict):
        desc = entry.get('description', '')
        return str(desc) if desc else ''
    return ''


def _extract_skill_names(entries: list) -> list[str]:
    """Extract skill names from a list of skill entries.

    Args:
        entries: List of skill entries (strings or dicts)

    Returns:
        List of skill name strings
    """
    return [_extract_skill_name(e) for e in entries]


def _build_skill_dict_with_descriptions(entries: list) -> dict[str, str]:
    """Build a dict mapping skill names to descriptions.

    For entries with embedded descriptions, use those.
    For string-only entries, fetch description from SKILL.md.

    Args:
        entries: List of skill entries (strings or dicts)

    Returns:
        Dict mapping skill names to descriptions
    """
    result = {}
    for entry in entries:
        skill_name = _extract_skill_name(entry)
        if not skill_name:
            continue
        # Use embedded description if available, otherwise fetch from SKILL.md
        desc = _extract_skill_description(entry)
        if not desc:
            desc = get_skill_description(skill_name)
        result[skill_name] = desc
    return result


def discover_project_skills() -> list[dict]:
    """Discover project-level skills from .claude/skills/ directory.

    Scans for SKILL.md files and extracts name + description from frontmatter.

    Returns:
        List of dicts: [{notation: "project:{name}", name: str, description: str}]
    """
    claude_skills = Path('.claude/skills')
    if not claude_skills.is_dir():
        return []

    skills: list[dict] = []
    for skill_dir in sorted(claude_skills.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            continue

        notation = f'project:{skill_dir.name}'
        description = get_skill_description(notation)
        # If get_skill_description returns the notation itself, use the name as fallback
        if description == notation:
            description = skill_dir.name

        skills.append({
            'notation': notation,
            'name': skill_dir.name,
            'description': description,
        })

    return skills



def discover_available_domains(project_root: Path | None = None) -> dict:
    """Discover domains from extension.py files.

    Args:
        project_root: Optional project root for applicability check.
                     If provided, each domain gets an 'applicable' flag.

    Returns dict with 'domains' list. Each domain has:
        - key, name, description, bundle
        - has_triage, has_outline
        - applicable (bool) - True if domain applies to project (when project_root provided)
    """
    all_extensions = discover_all_extensions()

    # Get applicable bundles if project_root provided
    applicable_bundles = set()
    if project_root:
        applicable_extensions = discover_extensions(project_root)
        applicable_bundles = {ext['bundle'] for ext in applicable_extensions}

    domains = []

    for ext in all_extensions:
        module = ext.get('module')
        if not module:
            continue

        # Check for domain (has get_skill_domains with domain.key)
        if hasattr(module, 'get_skill_domains'):
            try:
                all_domains = module.get_skill_domains()
                for domain_info in all_domains:
                    if not domain_info or not isinstance(domain_info.get('domain'), dict):
                        continue
                    domain_data = domain_info['domain']
                    has_triage = False

                    # Check for extension functions
                    if hasattr(module, 'provides_triage'):
                        has_triage = module.provides_triage() is not None
                    has_outline_skill = False
                    if hasattr(module, 'provides_outline_skill'):
                        outline_skill = module.provides_outline_skill()
                        has_outline_skill = outline_skill is not None

                    has_recipes = False
                    if hasattr(module, 'provides_recipes'):
                        recipes = module.provides_recipes()
                        has_recipes = bool(recipes)

                    domain_entry = {
                        'key': domain_data.get('key', ''),
                        'name': domain_data.get('name', ''),
                        'description': domain_data.get('description', ''),
                        'bundle': ext['bundle'],
                        'has_triage': has_triage,
                        'has_outline_skill': has_outline_skill,
                        'has_recipes': has_recipes,
                    }

                    # Add applicability flag if project_root was provided
                    if project_root:
                        domain_entry['applicable'] = ext['bundle'] in applicable_bundles

                    domains.append(domain_entry)
            except Exception as e:
                print(f'Warning: Failed to get domains from {ext["bundle"]}: {e}', file=sys.stderr)

    return {'domains': domains}


def load_domain_config_from_bundle(domain_key: str) -> dict | None:
    """Load domain configuration from bundle's extension.py.

    Only returns bundle reference and workflow_skill_extensions.
    Profiles are NOT stored in marshal.json - read from extension.py at runtime.

    Args:
        domain_key: Domain key to look for (e.g., 'java', 'javascript')

    Returns:
        Domain config dict or None if not found
    """
    extensions = discover_all_extensions()

    for ext in extensions:
        module = ext.get('module')
        if not module or not hasattr(module, 'get_skill_domains'):
            continue

        try:
            # Check all domains (supports multi-domain extensions)
            all_domains = module.get_skill_domains()

            for domain_info in all_domains:
                if not domain_info:
                    continue
                domain_data = domain_info.get('domain', {})
                if isinstance(domain_data, dict) and domain_data.get('key') == domain_key:
                    return convert_extension_to_domain_config(module, domain_info, ext['bundle'])
        except Exception:
            continue

    return None


def convert_extension_to_domain_config(module, domain_info: dict, bundle_name: str) -> dict:
    """Convert extension.py data to skill_domains config format.

    Profiles are NOT copied - they're read from extension.py at runtime.
    Only bundle reference and workflow_skill_extensions are stored in marshal.json.

    Args:
        module: Loaded extension module
        domain_info: Result from get_skill_domains()
        bundle_name: Name of the bundle providing this domain

    Returns:
        Config dict compatible with marshal.json skill_domains
    """
    from typing import Any

    config: dict[str, Any] = {'bundle': bundle_name}

    # Extract extensions from dedicated functions
    if hasattr(module, 'provides_triage') or hasattr(module, 'provides_outline_skill'):
        extensions: dict[str, Any] = {}
        if hasattr(module, 'provides_outline_skill'):
            outline_skill = module.provides_outline_skill()
            if outline_skill:
                config['outline_skill'] = outline_skill
        if hasattr(module, 'provides_triage'):
            triage = module.provides_triage()
            if triage:
                extensions['triage'] = triage
        if extensions:
            config['workflow_skill_extensions'] = extensions

    return config


def load_profiles_from_bundle(bundle_name: str, domain_key: str | None = None) -> dict:
    """Load profiles directly from bundle's extension.py.

    Args:
        bundle_name: Bundle name (e.g., 'pm-dev-java')
        domain_key: Optional domain key to match for multi-domain bundles.
            If provided, finds the domain with this key. If not, uses first domain.

    Returns:
        Dict with 'profiles' containing core, implementation, etc.
        Returns empty dict if bundle not found or has no profiles.
    """
    extensions = discover_all_extensions()

    for ext in extensions:
        if ext.get('bundle') != bundle_name:
            continue

        module = ext.get('module')
        if not module or not hasattr(module, 'get_skill_domains'):
            continue

        try:
            all_domains = module.get_skill_domains()
            if not all_domains:
                continue
            # Match by domain_key if provided (for multi-domain bundles)
            if domain_key:
                for d in all_domains:
                    if d.get('domain', {}).get('key') == domain_key:
                        return {'profiles': d.get('profiles', {})}
            return {'profiles': all_domains[0].get('profiles', {})}
        except Exception:
            pass

    return {'profiles': {}}


def _collect_verify_steps(domain_key: str) -> list:
    """Collect verify steps from a domain's extension.py.

    Args:
        domain_key: Domain key (e.g., 'java', 'documentation')

    Returns:
        List of verify step dicts [{name, agent, description}] or empty list
    """
    extensions = discover_all_extensions()

    for ext in extensions:
        module = ext.get('module')
        if not module or not hasattr(module, 'get_skill_domains'):
            continue

        try:
            all_domains = module.get_skill_domains()
            for domain_info in all_domains:
                if not domain_info:
                    continue

                domain_data = domain_info.get('domain', {})
                if isinstance(domain_data, dict) and domain_data.get('key') == domain_key:
                    if hasattr(module, 'provides_verify_steps'):
                        steps: list = module.provides_verify_steps()
                        return steps
                    return []
        except Exception:
            continue

    return []


def _discover_all_verify_steps() -> list[dict]:
    """Discover all verify steps from built-in, project, and extension sources.

    Sources (in order):
    1. Built-in steps from _config_defaults.BUILT_IN_VERIFY_STEPS
    2. Project verify-step-* skills in .claude/skills/
    3. Extension provides_verify_steps()

    Returns:
        List of step dicts with name, description, type, source.
    """
    import re

    from _config_defaults import BUILT_IN_VERIFY_STEP_DESCRIPTIONS, BUILT_IN_VERIFY_STEPS

    all_steps: list[dict] = []

    # Source 1: Built-in steps
    for step_name in BUILT_IN_VERIFY_STEPS:
        all_steps.append({
            'name': step_name,
            'description': BUILT_IN_VERIFY_STEP_DESCRIPTIONS.get(step_name, step_name),
            'type': 'built-in',
            'source': 'built-in',
        })

    # Source 2: Project verify-step-* skills
    claude_skills = Path('.claude/skills')
    if claude_skills.is_dir():
        for skill_dir in sorted(claude_skills.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith('verify-step-'):
                continue
            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.exists():
                continue

            content = skill_md.read_text()
            description = ''
            fm_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
            if fm_match:
                description = fm_match.group(1).strip()

            step_ref = f'project:{skill_dir.name}'
            all_steps.append({
                'name': step_ref,
                'description': description or skill_dir.name,
                'type': 'project',
                'source': 'project',
            })

    # Source 3: Extension provides_verify_steps()
    extensions = discover_all_extensions()
    for ext in extensions:
        module = ext.get('module')
        if not module or not hasattr(module, 'provides_verify_steps'):
            continue
        try:
            steps = module.provides_verify_steps()
            if not steps:
                continue
            for step in steps:
                all_steps.append({
                    'name': step.get('name', ''),
                    'description': step.get('description', ''),
                    'type': 'skill',
                    'source': 'extension',
                })
        except Exception:
            pass

    return all_steps


def cmd_list_verify_steps(args) -> int:
    """List all available verify steps discovered at runtime.

    Sources: built-in + project verify-step-* skills + extension provides_verify_steps().
    """
    all_steps = _discover_all_verify_steps()
    return success_exit({'steps': all_steps, 'count': len(all_steps)})


def cmd_skill_domains(args) -> int:
    """Handle skill-domains noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()

    # Verbs that work without skill_domains existing
    if args.verb not in ('get-available', 'configure'):
        if 'skill_domains' not in config:
            return error_exit('skill_domains not configured. Run command /marshall-steward first')

    skill_domains = config.get('skill_domains', {})

    if args.verb == 'list':
        domains = list(skill_domains.keys())
        return success_exit({'domains': domains, 'count': len(domains)})

    elif args.verb == 'get':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]

        # Check if nested structure
        if is_nested_domain(domain_config):
            result = {'domain': domain}
            # Include bundle reference if present
            if 'bundle' in domain_config:
                result['bundle'] = domain_config['bundle']
            # Include task_executors if present
            if 'task_executors' in domain_config:
                result['task_executors'] = domain_config['task_executors']
            # Include workflow_skill_extensions if present
            if 'workflow_skill_extensions' in domain_config:
                result['workflow_skill_extensions'] = domain_config['workflow_skill_extensions']
            # Include top-level defaults/optionals if present (system domain)
            if 'defaults' in domain_config:
                result['defaults'] = domain_config['defaults']
            if 'optionals' in domain_config:
                result['optionals'] = domain_config['optionals']

            # Include project_skills if present
            if 'project_skills' in domain_config:
                result['project_skills'] = domain_config['project_skills']

            # Load profiles from extension.py if bundle is present
            bundle = domain_config.get('bundle')
            if bundle:
                ext_data = load_profiles_from_bundle(bundle, domain)
                profiles = ext_data.get('profiles', {})
                for profile_name in ['core', 'implementation', 'module_testing', 'integration_testing', 'quality']:
                    if profile_name in profiles:
                        result[profile_name] = profiles[profile_name]
            return success_exit(result)
        else:
            # Flat structure (non-nested domain config)
            return success_exit(
                {
                    'domain': domain,
                    'defaults': domain_config.get('defaults', []),
                    'optionals': domain_config.get('optionals', []),
                }
            )

    elif args.verb == 'get-defaults':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]
        # For nested structure, load core.defaults from extension.py
        if is_nested_domain(domain_config):
            bundle = domain_config.get('bundle')
            if bundle:
                ext_data = load_profiles_from_bundle(bundle, domain)
                defaults = ext_data.get('profiles', {}).get('core', {}).get('defaults', [])
            else:
                defaults = domain_config.get('defaults', [])
        else:
            defaults = domain_config.get('defaults', [])
        return success_exit({'domain': domain, 'defaults': defaults})

    elif args.verb == 'get-optionals':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]
        # For nested structure, load core.optionals from extension.py
        if is_nested_domain(domain_config):
            bundle = domain_config.get('bundle')
            if bundle:
                ext_data = load_profiles_from_bundle(bundle, domain)
                optionals = ext_data.get('profiles', {}).get('core', {}).get('optionals', [])
            else:
                optionals = domain_config.get('optionals', [])
        else:
            optionals = domain_config.get('optionals', [])
        return success_exit({'domain': domain, 'optionals': optionals})

    elif args.verb == 'set':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}. Use 'add' to create new domain.")

        domain_config = skill_domains[domain]
        profile = getattr(args, 'profile', None)

        if profile:
            # Profile modification not supported - profiles come from extension.py
            return error_exit(
                'Profile modification not supported. Profiles are defined in bundle extension.py '
                'and cannot be modified via marshal.json.'
            )
        else:
            # Flat structure update (system domain only)
            if args.defaults:
                skill_domains[domain]['defaults'] = args.defaults.split(',')
            if args.optionals is not None:
                skill_domains[domain]['optionals'] = args.optionals.split(',') if args.optionals else []

        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({'domain': domain, 'updated': skill_domains[domain]})

    elif args.verb == 'get-extensions':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]
        extensions = domain_config.get('workflow_skill_extensions', {})
        return success_exit({'domain': domain, 'extensions': extensions})

    elif args.verb == 'set-extensions':
        domain = args.domain
        ext_type = args.type
        skill = args.skill
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]
        if 'workflow_skill_extensions' not in domain_config:
            domain_config['workflow_skill_extensions'] = {}
        domain_config['workflow_skill_extensions'][ext_type] = skill
        skill_domains[domain] = domain_config
        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({'domain': domain, 'type': ext_type, 'skill': skill})

    elif args.verb == 'add':
        domain = args.domain
        if domain in skill_domains:
            return error_exit(f'Domain already exists: {domain}')
        defaults = args.defaults.split(',') if args.defaults else []
        optionals = args.optionals.split(',') if args.optionals else []
        skill_domains[domain] = {'defaults': defaults, 'optionals': optionals}
        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({'domain': domain, 'added': skill_domains[domain]})

    elif args.verb == 'validate':
        domain = args.domain
        skill = args.skill
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')
        domain_config = skill_domains[domain]

        # Handle nested structure
        if is_nested_domain(domain_config):
            # Load profiles from extension.py
            bundle = domain_config.get('bundle')
            if bundle:
                ext_data = load_profiles_from_bundle(bundle, domain)
                profiles = ext_data.get('profiles', {})

                # Collect all defaults and optionals across all profiles
                all_defaults = []
                all_optionals = []
                for key in ['core', 'implementation', 'module_testing', 'integration_testing', 'quality']:
                    if key in profiles:
                        all_defaults.extend(profiles[key].get('defaults', []))
                        all_optionals.extend(profiles[key].get('optionals', []))
                valid = skill in all_defaults or skill in all_optionals
                return success_exit(
                    {
                        'domain': domain,
                        'skill': skill,
                        'valid': valid,
                        'in_defaults': skill in all_defaults,
                        'in_optionals': skill in all_optionals,
                    }
                )
            else:
                # System domain with top-level defaults/optionals
                all_skills = domain_config.get('defaults', []) + domain_config.get('optionals', [])
                valid = skill in all_skills
                return success_exit(
                    {
                        'domain': domain,
                        'skill': skill,
                        'valid': valid,
                        'in_defaults': skill in domain_config.get('defaults', []),
                        'in_optionals': skill in domain_config.get('optionals', []),
                    }
                )
        else:
            # Flat structure
            all_skills = domain_config.get('defaults', []) + domain_config.get('optionals', [])
            valid = skill in all_skills
            return success_exit(
                {
                    'domain': domain,
                    'skill': skill,
                    'valid': valid,
                    'in_defaults': skill in domain_config.get('defaults', []),
                    'in_optionals': skill in domain_config.get('optionals', []),
                }
            )

    elif args.verb == 'detect':
        detected_keys = detect_domains()  # Returns list of domain keys
        # Load configs from discovery for detected domains
        for domain_key in detected_keys:
            if domain_key not in skill_domains:
                domain_config = load_domain_config_from_bundle(domain_key)
                if domain_config:
                    skill_domains[domain_key] = domain_config
        save_config(config)
        return success_exit(
            {
                'detected': detected_keys,
                'count': len(detected_keys),
                'message': f'Detected domains: {", ".join(detected_keys)}' if detected_keys else 'No domains detected',
            }
        )

    elif args.verb == 'get-available':
        # Use dynamic discovery to find available domains
        # Pass project root to get applicability flags
        project_root = Path('.').resolve()
        discovery = discover_available_domains(project_root)

        result = {'discovered_domains': discovery.get('domains', [])}
        if 'error' in discovery and discovery['error']:
            result['error'] = discovery['error']

        return success_exit(result)

    elif args.verb == 'configure':
        selected_domains = [d.strip() for d in args.domains.split(',') if d.strip()]

        # Preserve existing project_skills before clearing
        existing_project_skills: dict[str, list] = {}
        for domain_key, domain_config in skill_domains.items():
            if isinstance(domain_config, dict):
                if 'project_skills' in domain_config:
                    existing_project_skills[domain_key] = domain_config['project_skills']

        # Clear existing domains and start fresh with only selected ones
        skill_domains = {}

        # Always add system domain
        skill_domains['system'] = copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)

        # Apply domain config for each selected domain from bundle extension.py
        domains_configured = []
        domains_not_found = []
        extension_verify_steps: list = []

        for domain_key in selected_domains:
            # Load from bundle extension.py (returns converted config directly)
            domain_config = load_domain_config_from_bundle(domain_key)
            if domain_config:
                skill_domains[domain_key] = domain_config
                domains_configured.append(domain_key)

                # Collect verify steps from extension as flat references
                steps = _collect_verify_steps(domain_key)
                for step in steps:
                    step_ref = step.get('name', '')
                    if step_ref and step_ref not in extension_verify_steps:
                        extension_verify_steps.append(step_ref)
            else:
                domains_not_found.append(domain_key)

        # Restore project_skills to domains that still exist
        for domain_key, ps in existing_project_skills.items():
            if domain_key in skill_domains:
                skill_domains[domain_key]['project_skills'] = ps

        config['skill_domains'] = skill_domains

        # Persist verify steps to plan.phase-5-execute.steps
        # Build flat list: built-in steps + extension steps
        from _config_defaults import BUILT_IN_VERIFY_STEPS

        plan_config = config.get('plan', {})
        execute_section = plan_config.get('phase-5-execute', {})
        execute_section['steps'] = list(BUILT_IN_VERIFY_STEPS) + extension_verify_steps
        plan_config['phase-5-execute'] = execute_section
        config['plan'] = plan_config

        save_config(config)

        result = {
            'system_domain': 'configured',
            'domains_configured': len(domains_configured),
            'domains': ','.join(domains_configured),
        }
        if domains_not_found:
            result['domains_not_found'] = ','.join(domains_not_found)
        if extension_verify_steps:
            result['verify_steps'] = extension_verify_steps

        return success_exit(result)

    elif args.verb == 'discover-project':
        skills = discover_project_skills()
        return success_exit({
            'skills': skills,
            'count': len(skills),
        })

    elif args.verb == 'attach-project':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f'Unknown domain: {domain}')

        skills_input = [s.strip() for s in args.skills.split(',') if s.strip()]

        # Validate notation
        invalid = [s for s in skills_input if not s.startswith('project:')]
        if invalid:
            return error_exit(f'Invalid notation (must start with project:): {", ".join(invalid)}')

        domain_config = skill_domains[domain]
        existing = domain_config.get('project_skills', [])

        # Merge without duplicates, preserve order
        merged = list(existing)
        for skill in skills_input:
            if skill not in merged:
                merged.append(skill)

        domain_config['project_skills'] = merged
        skill_domains[domain] = domain_config
        config['skill_domains'] = skill_domains
        save_config(config)

        return success_exit({
            'domain': domain,
            'project_skills': merged,
            'added': len(merged) - len(existing),
        })

    elif args.verb == 'active-profiles':
        ap_verb = getattr(args, 'ap_verb', None)

        if ap_verb is None:
            # Show current active_profiles config
            ap_result: dict = {}
            if 'active_profiles' in skill_domains:
                ap_result['global'] = skill_domains['active_profiles']
            for dk, dc in skill_domains.items():
                if isinstance(dc, dict) and 'active_profiles' in dc:
                    ap_result[dk] = dc['active_profiles']
            if not ap_result:
                ap_result['status'] = 'not_configured'
            return success_exit(ap_result)

        elif ap_verb == 'set':
            profiles_list = [p.strip() for p in args.profiles.split(',') if p.strip()]
            domain = getattr(args, 'domain', None)
            if domain:
                if domain not in skill_domains:
                    return error_exit(f'Unknown domain: {domain}')
                if not isinstance(skill_domains[domain], dict):
                    return error_exit(f'Domain {domain} is not a dict')
                skill_domains[domain]['active_profiles'] = profiles_list
            else:
                skill_domains['active_profiles'] = profiles_list
            config['skill_domains'] = skill_domains
            save_config(config)
            return success_exit({
                'scope': domain or 'global',
                'active_profiles': profiles_list,
            })

        elif ap_verb == 'remove':
            domain = getattr(args, 'domain', None)
            if domain:
                if domain not in skill_domains:
                    return error_exit(f'Unknown domain: {domain}')
                if isinstance(skill_domains[domain], dict):
                    skill_domains[domain].pop('active_profiles', None)
            else:
                skill_domains.pop('active_profiles', None)
            config['skill_domains'] = skill_domains
            save_config(config)
            return success_exit({'scope': domain or 'global', 'removed': True})

    return EXIT_ERROR


### Resolution and discovery commands in _cmd_skill_resolution.py ###
