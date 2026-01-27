"""
Default configurations for plan-marshall-config.

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
# Convention: profile X maps to pm-workflow:task-X
# These are defaults; marshall-steward auto-discovers from extension.py files
DEFAULT_TASK_EXECUTORS = {
    'implementation': 'pm-workflow:task-implementation',
    'module_testing': 'pm-workflow:task-module_testing',
    'integration_testing': 'pm-workflow:task-integration_testing',
}

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN = {
    'defaults': ['plan-marshall:ref-development-standards'],
    'optionals': ['plan-marshall:ref-development-standards'],
    'task_executors': DEFAULT_TASK_EXECUTORS,
}

# System retention defaults
DEFAULT_SYSTEM_RETENTION = {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}

# Phase-specific plan defaults
DEFAULT_PLAN_INIT = {
    'branch_strategy': 'direct',
}

DEFAULT_PLAN_REFINE = {
    'confidence_threshold': 95,
    'compatibility': 'breaking',
}

DEFAULT_PLAN_EXECUTE = {
    'commit_strategy': 'per_deliverable',
}

DEFAULT_PLAN_VERIFY = {
    'max_iterations': 5,
    '1_quality_check': True,
    '2_build_verify': True,
    'domain_steps': {},
}

DEFAULT_PLAN_FINALIZE = {
    'max_iterations': 3,
    '1_commit_push': True,
    '2_create_pr': True,
    '3_automated_review': True,
    '4_sonar_roundtrip': True,
    '5_knowledge_capture': True,
    '6_lessons_capture': True,
}

# Build system defaults (detection reference only - commands are in modules)
BUILD_SYSTEM_DEFAULTS = {
    'maven': {'skill': 'pm-dev-java:plan-marshall-plugin'},
    'gradle': {'skill': 'pm-dev-java:plan-marshall-plugin'},
    'npm': {'skill': 'pm-dev-frontend:plan-marshall-plugin'},
}


def get_default_config() -> dict:
    """Get complete default marshal.json configuration.

    Returns a new dict each time to avoid mutation issues.

    NOTE:
    - build_systems is NOT included - determined at runtime via extension discovery
    - Module facts come from derived-data.json (see plan-marshall:analyze-project-architecture)
    - domain_steps in phase-6-verify is auto-populated by skill-domains configure
    """
    import copy

    return {
        'skill_domains': {'system': copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)},
        'system': {'retention': copy.deepcopy(DEFAULT_SYSTEM_RETENTION)},
        'plan': {
            'phase-1-init': copy.deepcopy(DEFAULT_PLAN_INIT),
            'phase-2-refine': copy.deepcopy(DEFAULT_PLAN_REFINE),
            'phase-5-execute': copy.deepcopy(DEFAULT_PLAN_EXECUTE),
            'phase-6-verify': copy.deepcopy(DEFAULT_PLAN_VERIFY),
            'phase-7-finalize': copy.deepcopy(DEFAULT_PLAN_FINALIZE),
        },
    }
