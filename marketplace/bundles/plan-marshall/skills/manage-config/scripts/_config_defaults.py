"""
Default configurations for manage-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Reserved keys in nested domain config (not profile names)
# bundle: Reference to bundle providing this domain (e.g., 'pm-dev-java')
# task_executors: System domain only - profile to task skill mapping
# workflow_skill_extensions: Domain extensions (outline, triage)
# defaults/optionals: System domain top-level skills
RESERVED_DOMAIN_KEYS = [
    'bundle',
    'task_executors',
    'workflow_skill_extensions',
    'defaults',
    'optionals',
]

# Task executors map profile -> workflow skill
# All profiles use the unified task-executor skill which handles profile dispatch internally.
# Keys align with constants.VALID_PROFILES (source of truth for profile names)
# These are defaults; marshall-steward auto-discovers from extension.py files
DEFAULT_TASK_EXECUTORS = {
    'implementation': 'plan-marshall:task-executor',
    'module_testing': 'plan-marshall:task-executor',
    'integration_testing': 'plan-marshall:task-executor',
    'verification': 'plan-marshall:task-executor',
}

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN = {
    'defaults': [],
    'optionals': [],
    'task_executors': DEFAULT_TASK_EXECUTORS,
}


def validate_domain_invariants(domain: dict) -> None:
    """Validate that defaults and optionals have no overlap.

    A skill in defaults (always loaded) must never also appear in optionals
    (selectively loaded). Overlap indicates a configuration error.

    Raises:
        ValueError: If any skill appears in both defaults and optionals.
    """
    defaults = set(domain.get('defaults', []))
    optionals = set(domain.get('optionals', []))
    overlap = defaults & optionals
    if overlap:
        raise ValueError(
            f"Skills must not appear in both defaults and optionals: {sorted(overlap)}"
        )

# System retention defaults
DEFAULT_SYSTEM_RETENTION = {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}

# Phase-specific plan defaults
DEFAULT_PLAN_INIT = {
    'branch_strategy': 'feature',
}

DEFAULT_PLAN_REFINE = {
    'confidence_threshold': 95,
    'compatibility': 'breaking',
}

DEFAULT_PLAN_OUTLINE = {
    'plan_without_asking': False,
}

DEFAULT_PLAN_PLAN = {
    'execute_without_asking': True,
}

# Built-in verify step names (dispatch table in phase-5-execute SKILL.md)
# Prefixed with 'default:' to distinguish from project: and fully-qualified skill steps
BUILT_IN_VERIFY_STEPS = ['default:quality_check', 'default:build_verify', 'default:coverage_check']

# Human-readable descriptions for built-in verify steps
BUILT_IN_VERIFY_STEP_DESCRIPTIONS = {
    'default:quality_check': 'Run quality-gate build command',
    'default:build_verify': 'Run full test suite',
    'default:coverage_check': 'Run coverage build and verify threshold',
}

DEFAULT_PLAN_EXECUTE = {
    'commit_strategy': 'per_plan',
    'finalize_without_asking': True,
    'verification_max_iterations': 5,
    'steps': list(BUILT_IN_VERIFY_STEPS),
}

# Built-in finalize step names (dispatch table in phase-6-finalize SKILL.md)
# Prefixed with 'default:' to distinguish from project: and fully-qualified skill steps
BUILT_IN_FINALIZE_STEPS = [
    'default:commit-push',
    'default:create-pr',
    'default:automated-review',
    'default:sonar-roundtrip',
    'default:knowledge-capture',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:archive-plan',
]

# Human-readable descriptions for built-in finalize steps
BUILT_IN_FINALIZE_STEP_DESCRIPTIONS = {
    'default:commit-push': 'Commit and push changes',
    'default:create-pr': 'Create pull request',
    'default:automated-review': 'CI automated review',
    'default:sonar-roundtrip': 'Sonar analysis roundtrip',
    'default:knowledge-capture': 'Capture learnings to memory',
    'default:lessons-capture': 'Record lessons learned',
    'default:branch-cleanup': 'Merge PR (with --delete-branch) and pull latest',
    'default:archive-plan': 'Archive the completed plan',
}

DEFAULT_PLAN_FINALIZE = {
    'max_iterations': 3,
    'review_bot_buffer_seconds': 300,
    'pr_merge_strategy': 'squash',
    'steps': list(BUILT_IN_FINALIZE_STEPS),
}

# Build system defaults (detection reference only - commands are in modules)
BUILD_SYSTEM_DEFAULTS = {
    'maven': {'skill': 'plan-marshall:plan-marshall-plugin'},
    'gradle': {'skill': 'plan-marshall:plan-marshall-plugin'},
    'npm': {'skill': 'plan-marshall:plan-marshall-plugin'},
}


def get_default_config() -> dict:
    """Get complete default marshal.json configuration.

    Returns a new dict each time to avoid mutation issues.

    NOTE:
    - build_systems is NOT included - determined at runtime via extension discovery
    - Module facts come from derived-data.json (see plan-marshall:manage-architecture)
    - Extension verify steps in phase-5-execute.steps are appended by skill-domains configure
    """
    import copy

    system_domain = copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)
    validate_domain_invariants(system_domain)
    return {
        'skill_domains': {'system': system_domain},
        'system': {'retention': copy.deepcopy(DEFAULT_SYSTEM_RETENTION)},
        'plan': {
            'phase-1-init': copy.deepcopy(DEFAULT_PLAN_INIT),
            'phase-2-refine': copy.deepcopy(DEFAULT_PLAN_REFINE),
            'phase-3-outline': copy.deepcopy(DEFAULT_PLAN_OUTLINE),
            'phase-4-plan': copy.deepcopy(DEFAULT_PLAN_PLAN),
            'phase-5-execute': copy.deepcopy(DEFAULT_PLAN_EXECUTE),
            'phase-6-finalize': copy.deepcopy(DEFAULT_PLAN_FINALIZE),
        },
    }
