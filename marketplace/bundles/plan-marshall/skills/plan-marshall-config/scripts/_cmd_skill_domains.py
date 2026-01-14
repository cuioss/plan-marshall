"""
Skill domains command handlers for plan-marshall-config.

Handles: skill-domains, resolve-domain-skills, get-workflow-skills

Domain discovery uses extension.py files in each bundle's plan-marshall-plugin skill.
Extension API functions:
- get_skill_domains() -> domain metadata with profiles
- provides_triage() -> triage skill reference or None
- provides_outline() -> outline skill reference or None
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
        applicable_bundles = {ext["bundle"] for ext in applicable_extensions}

    domains = []

    for ext in all_extensions:
        module = ext.get("module")
        if not module:
            continue

        # Check for domain (has get_skill_domains with domain.key)
        if hasattr(module, 'get_skill_domains'):
            try:
                domain_info = module.get_skill_domains()
                if domain_info and isinstance(domain_info.get("domain"), dict):
                    domain_data = domain_info["domain"]
                    has_triage = False
                    has_outline = False

                    # Check for extension functions
                    if hasattr(module, 'provides_triage'):
                        has_triage = module.provides_triage() is not None
                    if hasattr(module, 'provides_outline'):
                        has_outline = module.provides_outline() is not None

                    domain_entry = {
                        "key": domain_data.get("key", ""),
                        "name": domain_data.get("name", ""),
                        "description": domain_data.get("description", ""),
                        "bundle": ext["bundle"],
                        "has_triage": has_triage,
                        "has_outline": has_outline
                    }

                    # Add applicability flag if project_root was provided
                    if project_root:
                        domain_entry["applicable"] = ext["bundle"] in applicable_bundles

                    domains.append(domain_entry)
            except Exception as e:
                print(f"Warning: Failed to get domains from {ext['bundle']}: {e}", file=sys.stderr)

    return {"domains": domains}


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
        module = ext.get("module")
        if not module or not hasattr(module, 'get_skill_domains'):
            continue

        try:
            domain_info = module.get_skill_domains()
            if not domain_info:
                continue

            domain_data = domain_info.get("domain", {})
            if isinstance(domain_data, dict) and domain_data.get("key") == domain_key:
                return convert_extension_to_domain_config(module, domain_info, ext["bundle"])
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
    config: dict[str, Any] = {"bundle": bundle_name}

    # Extract extensions from dedicated functions
    if hasattr(module, 'provides_triage') or hasattr(module, 'provides_outline'):
        extensions: dict[str, str] = {}
        if hasattr(module, 'provides_outline'):
            outline = module.provides_outline()
            if outline:
                extensions["outline"] = outline
        if hasattr(module, 'provides_triage'):
            triage = module.provides_triage()
            if triage:
                extensions["triage"] = triage
        if extensions:
            config["workflow_skill_extensions"] = extensions

    return config


def load_profiles_from_bundle(bundle_name: str) -> dict:
    """Load profiles directly from bundle's extension.py.

    Args:
        bundle_name: Bundle name (e.g., 'pm-dev-java')

    Returns:
        Dict with 'profiles' containing core, implementation, etc.
        Returns empty dict if bundle not found or has no profiles.
    """
    extensions = discover_all_extensions()

    for ext in extensions:
        if ext.get("bundle") != bundle_name:
            continue

        module = ext.get("module")
        if not module or not hasattr(module, 'get_skill_domains'):
            continue

        try:
            domain_info = module.get_skill_domains()
            if domain_info:
                return {"profiles": domain_info.get("profiles", {})}
        except Exception:
            pass

    return {"profiles": {}}


def cmd_skill_domains(args) -> int:
    """Handle skill-domains noun."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()

    if "skill_domains" not in config:
        return error_exit("skill_domains not configured. Run command /marshall-steward first")

    skill_domains = config.get('skill_domains', {})

    if args.verb == 'list':
        domains = list(skill_domains.keys())
        return success_exit({"domains": domains, "count": len(domains)})

    elif args.verb == 'get':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]

        # Check if nested structure
        if is_nested_domain(domain_config):
            result = {"domain": domain}
            # Include bundle reference if present
            if "bundle" in domain_config:
                result["bundle"] = domain_config["bundle"]
            # Include workflow_skills if present
            if "workflow_skills" in domain_config:
                result["workflow_skills"] = domain_config["workflow_skills"]
            # Include task_executors if present
            if "task_executors" in domain_config:
                result["task_executors"] = domain_config["task_executors"]
            # Include workflow_skill_extensions if present
            if "workflow_skill_extensions" in domain_config:
                result["workflow_skill_extensions"] = domain_config["workflow_skill_extensions"]
            # Include top-level defaults/optionals if present (system domain)
            if "defaults" in domain_config:
                result["defaults"] = domain_config["defaults"]
            if "optionals" in domain_config:
                result["optionals"] = domain_config["optionals"]

            # Load profiles from extension.py if bundle is present
            bundle = domain_config.get("bundle")
            if bundle:
                ext_data = load_profiles_from_bundle(bundle)
                profiles = ext_data.get("profiles", {})
                for profile_name in ['core', 'implementation', 'module_testing', 'integration_testing', 'quality']:
                    if profile_name in profiles:
                        result[profile_name] = profiles[profile_name]
            return success_exit(result)
        else:
            # Flat structure (backward compatible)
            return success_exit({
                "domain": domain,
                "defaults": domain_config.get("defaults", []),
                "optionals": domain_config.get("optionals", [])
            })

    elif args.verb == 'get-defaults':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]
        # For nested structure, load core.defaults from extension.py
        if is_nested_domain(domain_config):
            bundle = domain_config.get("bundle")
            if bundle:
                ext_data = load_profiles_from_bundle(bundle)
                defaults = ext_data.get("profiles", {}).get("core", {}).get("defaults", [])
            else:
                defaults = domain_config.get("defaults", [])
        else:
            defaults = domain_config.get("defaults", [])
        return success_exit({"domain": domain, "defaults": defaults})

    elif args.verb == 'get-optionals':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]
        # For nested structure, load core.optionals from extension.py
        if is_nested_domain(domain_config):
            bundle = domain_config.get("bundle")
            if bundle:
                ext_data = load_profiles_from_bundle(bundle)
                optionals = ext_data.get("profiles", {}).get("core", {}).get("optionals", [])
            else:
                optionals = domain_config.get("optionals", [])
        else:
            optionals = domain_config.get("optionals", [])
        return success_exit({"domain": domain, "optionals": optionals})

    elif args.verb == 'set':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}. Use 'add' to create new domain.")

        domain_config = skill_domains[domain]
        profile = getattr(args, 'profile', None)

        if profile:
            # Profile modification not supported - profiles come from extension.py
            return error_exit(
                "Profile modification not supported. Profiles are defined in bundle extension.py "
                "and cannot be modified via marshal.json."
            )
        else:
            # Flat structure update (system domain only)
            if args.defaults:
                skill_domains[domain]["defaults"] = args.defaults.split(',')
            if args.optionals is not None:
                skill_domains[domain]["optionals"] = args.optionals.split(',') if args.optionals else []

        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({
            "domain": domain,
            "updated": skill_domains[domain]
        })

    elif args.verb == 'get-extensions':
        domain = args.domain
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]
        extensions = domain_config.get('workflow_skill_extensions', {})
        return success_exit({
            "domain": domain,
            "extensions": extensions
        })

    elif args.verb == 'set-extensions':
        domain = args.domain
        ext_type = args.type
        skill = args.skill
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]
        if 'workflow_skill_extensions' not in domain_config:
            domain_config['workflow_skill_extensions'] = {}
        domain_config['workflow_skill_extensions'][ext_type] = skill
        skill_domains[domain] = domain_config
        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({
            "domain": domain,
            "type": ext_type,
            "skill": skill
        })

    elif args.verb == 'add':
        domain = args.domain
        if domain in skill_domains:
            return error_exit(f"Domain already exists: {domain}")
        defaults = args.defaults.split(',') if args.defaults else []
        optionals = args.optionals.split(',') if args.optionals else []
        skill_domains[domain] = {"defaults": defaults, "optionals": optionals}
        config['skill_domains'] = skill_domains
        save_config(config)
        return success_exit({
            "domain": domain,
            "added": skill_domains[domain]
        })

    elif args.verb == 'validate':
        domain = args.domain
        skill = args.skill
        if domain not in skill_domains:
            return error_exit(f"Unknown domain: {domain}")
        domain_config = skill_domains[domain]

        # Handle nested structure
        if is_nested_domain(domain_config):
            # Load profiles from extension.py
            bundle = domain_config.get("bundle")
            if bundle:
                ext_data = load_profiles_from_bundle(bundle)
                profiles = ext_data.get("profiles", {})

                # Collect all defaults and optionals across all profiles
                all_defaults = []
                all_optionals = []
                for key in ['core', 'implementation', 'module_testing', 'integration_testing', 'quality']:
                    if key in profiles:
                        all_defaults.extend(profiles[key].get("defaults", []))
                        all_optionals.extend(profiles[key].get("optionals", []))
                valid = skill in all_defaults or skill in all_optionals
                return success_exit({
                    "domain": domain,
                    "skill": skill,
                    "valid": valid,
                    "in_defaults": skill in all_defaults,
                    "in_optionals": skill in all_optionals
                })
            else:
                # System domain with top-level defaults/optionals
                all_skills = domain_config.get("defaults", []) + domain_config.get("optionals", [])
                valid = skill in all_skills
                return success_exit({
                    "domain": domain,
                    "skill": skill,
                    "valid": valid,
                    "in_defaults": skill in domain_config.get("defaults", []),
                    "in_optionals": skill in domain_config.get("optionals", [])
                })
        else:
            # Flat structure
            all_skills = domain_config.get("defaults", []) + domain_config.get("optionals", [])
            valid = skill in all_skills
            return success_exit({
                "domain": domain,
                "skill": skill,
                "valid": valid,
                "in_defaults": skill in domain_config.get("defaults", []),
                "in_optionals": skill in domain_config.get("optionals", [])
            })

    elif args.verb == 'detect':
        detected_keys = detect_domains()  # Returns list of domain keys
        # Load configs from discovery for detected domains
        for domain_key in detected_keys:
            if domain_key not in skill_domains:
                domain_config = load_domain_config_from_bundle(domain_key)
                if domain_config:
                    skill_domains[domain_key] = domain_config
        save_config(config)
        return success_exit({
            "detected": detected_keys,
            "count": len(detected_keys),
            "message": f"Detected domains: {', '.join(detected_keys)}" if detected_keys else "No domains detected"
        })

    elif args.verb == 'get-available':
        # Use dynamic discovery to find available domains
        # Pass project root to get applicability flags
        project_root = Path('.').resolve()
        discovery = discover_available_domains(project_root)

        result = {
            'discovered_domains': discovery.get("domains", [])
        }
        if "error" in discovery and discovery["error"]:
            result['error'] = discovery["error"]

        return success_exit(result)

    elif args.verb == 'configure':
        selected_domains = [d.strip() for d in args.domains.split(',') if d.strip()]

        # Always add system domain with workflow_skills
        skill_domains['system'] = copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)

        # Apply domain config for each selected domain from bundle extension.py
        domains_configured = []
        domains_not_found = []

        for domain_key in selected_domains:
            # Load from bundle extension.py (returns converted config directly)
            domain_config = load_domain_config_from_bundle(domain_key)
            if domain_config:
                skill_domains[domain_key] = domain_config
                domains_configured.append(domain_key)
            else:
                domains_not_found.append(domain_key)

        config['skill_domains'] = skill_domains
        save_config(config)

        result = {
            'system_domain': 'configured',
            'domains_configured': len(domains_configured),
            'domains': ','.join(domains_configured)
        }
        if domains_not_found:
            result['domains_not_found'] = ','.join(domains_not_found)

        return success_exit(result)

    return EXIT_ERROR


def cmd_resolve_domain_skills(args) -> int:
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
        return error_exit(f"Unknown domain: {domain}")

    domain_config = skill_domains[domain]

    # Get bundle reference - required for profile resolution
    bundle = domain_config.get('bundle')
    if not bundle:
        return error_exit(f"Domain '{domain}' has no bundle configured")

    # Load profiles from extension.py
    ext_data = load_profiles_from_bundle(bundle)
    profiles = ext_data.get('profiles', {})

    if not profiles:
        return error_exit(f"Bundle '{bundle}' has no profiles defined")

    # Validate profile exists
    if profile not in profiles and profile != 'core':
        available = [k for k in profiles.keys() if k != 'core']
        return error_exit(f"Unknown profile: {profile} for domain: {domain}. Available profiles: {', '.join(available)}")

    # Aggregate: core + profile skills
    core_config = profiles.get('core', {})
    profile_config = profiles.get(profile, {})

    defaults = core_config.get('defaults', []) + profile_config.get('defaults', [])
    optionals = core_config.get('optionals', []) + profile_config.get('optionals', [])

    # Build output with descriptions
    defaults_with_desc = {skill: get_skill_description(skill) for skill in defaults}
    optionals_with_desc = {skill: get_skill_description(skill) for skill in optionals}

    return success_exit({
        "domain": domain,
        "profile": profile,
        "defaults": defaults_with_desc,
        "optionals": optionals_with_desc
    })


def _find_workflow_skill(workflow_skills: dict[str, str], phase: str) -> str:
    """Find workflow skill by phase, handling numbered keys (e.g., '1-init' for 'init').

    Looks for exact match first, then key ending with '-{phase}'.
    """
    # Exact match first
    if phase in workflow_skills:
        result: str = workflow_skills[phase]
        return result

    # Look for numbered key pattern (e.g., "1-init" for "init")
    for key, value in workflow_skills.items():
        if key.endswith(f"-{phase}"):
            return value

    return ""


def cmd_get_workflow_skills(args) -> int:
    """Handle get-workflow-skills command.

    Returns all workflow skills from the system domain (5-phase model).
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    # Get workflow_skills from system domain
    if 'system' not in skill_domains:
        return error_exit("System domain not configured. Run /marshall-steward to initialize.")

    system_config = skill_domains['system']
    workflow_skills = system_config.get('workflow_skills', {})

    if not workflow_skills:
        return error_exit("System domain has no workflow_skills configured")

    return success_exit({
        "init": _find_workflow_skill(workflow_skills, "init"),
        "outline": _find_workflow_skill(workflow_skills, "outline"),
        "plan": _find_workflow_skill(workflow_skills, "plan"),
        "execute": _find_workflow_skill(workflow_skills, "execute"),
        "finalize": _find_workflow_skill(workflow_skills, "finalize")
    })


def cmd_resolve_workflow_skill(args) -> int:
    """Resolve system workflow skill for a phase.

    Always returns the system workflow skill from skill_domains.system.workflow_skills.{phase}.
    Domain-specific behavior is provided by extensions loaded via resolve-workflow-skill-extension.

    Phases: init, outline, plan, execute, finalize
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    phase = args.phase

    # Always use system domain for workflow skills
    if 'system' not in skill_domains:
        return error_exit("System domain not configured. Run /marshall-steward to initialize.")

    system_config = skill_domains['system']
    workflow_skills = system_config.get('workflow_skills', {})

    if not workflow_skills:
        return error_exit("System domain has no workflow_skills configured")

    skill = _find_workflow_skill(workflow_skills, phase)
    if not skill:
        available = [k.split('-')[-1] if '-' in k else k for k in workflow_skills.keys()]
        return error_exit(f"Unknown phase: {phase}. Available: {', '.join(available)}")

    return success_exit({
        "phase": phase,
        "workflow_skill": skill
    })


def cmd_resolve_workflow_skill_extension(args) -> int:
    """Resolve workflow skill extension for a domain and type.

    Returns the extension skill from skill_domains.{domain}.workflow_skill_extensions.{type}.
    Returns null for extension field if domain has no extension of that type.

    Extension types: outline (for solution-outline phase), triage (for plan-finalize phase)
    """
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
        return success_exit({
            "domain": domain,
            "type": ext_type,
            "extension": None
        })

    domain_config = skill_domains[domain]
    extensions = domain_config.get('workflow_skill_extensions', {})
    extension = extensions.get(ext_type)  # None if not present

    return success_exit({
        "domain": domain,
        "type": ext_type,
        "extension": extension
    })


def cmd_get_skills_by_profile(args) -> int:
    """Get skills organized by profile for a domain.

    Loads profiles from extension.py via bundle reference, then returns
    skills_by_profile structure for use in architecture enrichment.
    Each profile aggregates: core.defaults + core.optionals + profile.defaults + profile.optionals

    Profiles: implementation, module_testing, integration_testing, documentation
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    domain = args.domain

    if domain not in skill_domains:
        return error_exit(f"Unknown domain: {domain}")

    domain_config = skill_domains[domain]

    # Get bundle reference - required for profile resolution
    bundle = domain_config.get('bundle')
    if not bundle:
        return error_exit(f"Domain '{domain}' has no bundle configured")

    # Load profiles from extension.py
    ext_data = load_profiles_from_bundle(bundle)
    profiles = ext_data.get('profiles', {})

    if not profiles:
        return error_exit(f"Bundle '{bundle}' has no profiles defined")

    # Get core skills (always included)
    core_config = profiles.get('core', {})
    core_defaults = core_config.get('defaults', [])
    core_optionals = core_config.get('optionals', [])
    core_all = core_defaults + core_optionals

    # Build skills_by_profile from available profiles in extension
    skills_by_profile = {}

    for profile_name in ['implementation', 'module_testing', 'integration_testing', 'documentation']:
        profile_config = profiles.get(profile_name, {})
        profile_defaults = profile_config.get('defaults', [])
        profile_optionals = profile_config.get('optionals', [])

        # Combine: core + profile skills (remove duplicates, preserve order)
        combined = []
        seen = set()
        for skill in core_all + profile_defaults + profile_optionals:
            if skill not in seen:
                combined.append(skill)
                seen.add(skill)

        # For integration_testing, also include junit-integration if available
        if profile_name == 'integration_testing':
            for skill in profile_optionals:
                if 'integration' in skill.lower() and skill not in seen:
                    combined.append(skill)
                    seen.add(skill)

        skills_by_profile[profile_name] = combined

    return success_exit({
        "domain": domain,
        "skills_by_profile": skills_by_profile
    })


def cmd_configure_task_executors(args) -> int:
    """Configure task executors from discovered profiles.

    Auto-discovers profiles from configured domains and registers task executors
    using convention: profile X → skill pm-workflow:task-X

    Task executors map profile values to workflow skills that execute tasks.
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    skill_domains = config.get('skill_domains', {})

    # Ensure system domain exists
    if 'system' not in skill_domains:
        return error_exit("System domain not configured. Run skill-domains configure first.")

    # Discover all unique profiles from configured domains
    # Now loads profiles from extension.py via bundle reference
    discovered_profiles = set()

    for domain_key, domain_config in skill_domains.items():
        if domain_key == 'system':
            continue
        if not is_nested_domain(domain_config):
            continue

        # Load profiles from extension.py
        bundle = domain_config.get("bundle")
        if bundle:
            ext_data = load_profiles_from_bundle(bundle)
            profiles = ext_data.get("profiles", {})
            # Collect profile keys (exclude 'core' which is not an executable profile)
            for key in profiles.keys():
                if key != 'core':
                    discovered_profiles.add(key)

    # Build task_executors mapping using convention: profile X → pm-workflow:task-X
    task_executors = {}
    for profile in sorted(discovered_profiles):
        # Skip quality profile - it's handled by finalize phase, not task execution
        if profile == 'quality':
            continue
        task_executors[profile] = f"pm-workflow:task-{profile}"

    # Update system domain with task_executors
    system_config = skill_domains['system']
    system_config['task_executors'] = task_executors
    skill_domains['system'] = system_config

    config['skill_domains'] = skill_domains
    save_config(config)

    return success_exit({
        "status": "success",
        "task_executors_configured": len(task_executors),
        "executors": task_executors
    })


def cmd_resolve_task_executor(args) -> int:
    """Resolve task executor skill for a given profile.

    Looks up the task executor mapping in marshal.json:
    skill_domains.system.task_executors.{profile}

    Args:
        args.profile: Profile name (e.g., 'implementation', 'module_testing')

    Returns:
        TOON output with resolved task_executor skill reference
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    profile = args.profile
    config = load_config()
    skill_domains = config.get('skill_domains', {})
    system_config = skill_domains.get('system', {})
    task_executors = system_config.get('task_executors', {})

    if not task_executors:
        return error_exit(
            "No task_executors configured. Run configure-task-executors first."
        )

    if profile not in task_executors:
        available = sorted(task_executors.keys())
        return error_exit(
            f"Unknown profile '{profile}'. Available profiles: {', '.join(available)}"
        )

    task_executor = task_executors[profile]

    return success_exit({
        "profile": profile,
        "task_executor": task_executor
    })
