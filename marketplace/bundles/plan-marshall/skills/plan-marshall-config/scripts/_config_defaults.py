"""
Default configurations for plan-marshall-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Reserved keys in nested domain config (not profile names)
# workflow_skills: System domain only - 5 workflow phases
# workflow_skill_extensions: Domain extensions (outline, triage)
# core: Core skills loaded for all profiles
RESERVED_DOMAIN_KEYS = ['workflow_skills', 'workflow_skill_extensions', 'core', 'defaults', 'optionals']

# Skill profiles for technical domains
# - implementation: execute phase (production code)
# - testing: execute phase (test code)
# - quality: finalize phase
DEFAULT_PROFILES = ['implementation', 'testing', 'quality']

# System workflow skills (always from system domain)
DEFAULT_SYSTEM_WORKFLOW_SKILLS = {
    "init": "pm-workflow:phase-init",
    "outline": "pm-workflow:phase-refine-outline",
    "plan": "pm-workflow:phase-refine-plan",
    "execute": "pm-workflow:phase-execute",
    "finalize": "pm-workflow:phase-finalize"
}

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN = {
    "defaults": ["plan-marshall:general-development-rules"],
    "optionals": ["plan-marshall:diagnostic-patterns"],
    "workflow_skills": DEFAULT_SYSTEM_WORKFLOW_SKILLS
}

# System retention defaults
DEFAULT_SYSTEM_RETENTION = {
    "logs_days": 1,
    "archived_plans_days": 5,
    "memory_days": 5,
    "temp_on_maintenance": True
}

# Plan defaults
DEFAULT_PLAN_DEFAULTS = {
    "compatibility": "breaking",
    "commit_strategy": "phase-specific",
    "create_pr": False,
    "verification_required": True,
    "branch_strategy": "direct"
}

# Build system defaults (detection reference only - commands are in modules)
BUILD_SYSTEM_DEFAULTS = {
    "maven": {
        "skill": "pm-dev-java:plan-marshall-plugin"
    },
    "gradle": {
        "skill": "pm-dev-java:plan-marshall-plugin"
    },
    "npm": {
        "skill": "pm-dev-frontend:plan-marshall-plugin"
    }
}

# NOTE: DOMAIN_TEMPLATES and BUILD_SYSTEM_TO_DOMAIN have been removed.
# Domain configuration is now discovered from bundle manifests via
# plan-marshall:domain-extension-api:discover_domains
#
# Each domain bundle contains skills/plan-marshall-plugin/plugin.json
# with domain configuration. See domain-extension-api skill for details.


def get_default_config() -> dict:
    """Get complete default marshal.json configuration.

    Returns a new dict each time to avoid mutation issues.

    NOTE:
    - build_systems is NOT included - determined at runtime via extension discovery
    - module_config contains command configuration only; module facts come from
      raw-project-data.json (see plan-marshall:project-structure)
    """
    import copy
    return {
        "skill_domains": {
            "system": copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)
        },
        "module_config": {},
        "system": {
            "retention": copy.deepcopy(DEFAULT_SYSTEM_RETENTION)
        },
        "plan": {
            "defaults": copy.deepcopy(DEFAULT_PLAN_DEFAULTS)
        }
    }
