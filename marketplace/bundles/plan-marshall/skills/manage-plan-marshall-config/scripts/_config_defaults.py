"""
Default configurations for plan-marshall-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Reserved keys in nested domain config (not profile names)
# bundle: Reference to bundle providing this domain (e.g., 'pm-dev-java')
# workflow_skills: System domain only - 7 workflow phases
# task_executors: System domain only - profile to task skill mapping
# workflow_skill_extensions: Domain extensions (outline, triage)
# defaults/optionals: System domain top-level skills
RESERVED_DOMAIN_KEYS = [
    'bundle',
    'workflow_skills',
    'task_executors',
    'workflow_skill_extensions',
    'defaults',
    'optionals',
]

# System workflow skills (always from system domain)
DEFAULT_SYSTEM_WORKFLOW_SKILLS = {
    '1-init': 'pm-workflow:phase-1-init',
    '2-refine': 'pm-workflow:phase-2-refine',
    '3-outline': 'pm-workflow:phase-3-outline',
    '4-plan': 'pm-workflow:phase-4-plan',
    '5-execute': 'pm-workflow:phase-5-execute',
    '6-verify': 'pm-workflow:phase-6-verify',
    '7-finalize': 'pm-workflow:phase-7-finalize',
}

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
    'workflow_skills': DEFAULT_SYSTEM_WORKFLOW_SKILLS,
    'task_executors': DEFAULT_TASK_EXECUTORS,
}

# System retention defaults
DEFAULT_SYSTEM_RETENTION = {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}

# Plan defaults
DEFAULT_PLAN_DEFAULTS = {
    'compatibility': 'breaking',
    'commit_strategy': 'per_deliverable',
    'create_pr': False,
    'verification_required': True,
    'branch_strategy': 'direct',
    'refine_confidence_threshold': 95,
}

# Plan finalize settings
DEFAULT_PLAN_FINALIZE = {
    'commit': True,
}

# Default max iterations for verification and finalize phases
DEFAULT_VERIFICATION_MAX_ITERATIONS = 5
DEFAULT_FINALIZE_MAX_ITERATIONS = 3

# Default verification pipeline steps (6-verify phase)
# Used by phase-6-verify when marshal.json has no 'verification' override.
# ${domain} placeholders are resolved via skill_domains.{domain}.capabilities
DEFAULT_VERIFICATION_STEPS = [
    {'name': 'quality_check', 'skill': '${domain}:quality-gate', 'type': 'build'},
    {'name': 'build_verify', 'skill': '${domain}:build-verify', 'type': 'build'},
    {'name': 'technical_impl', 'skill': '${domain}:impl-verify', 'type': 'agent'},
    {'name': 'technical_test', 'skill': '${domain}:test-verify', 'type': 'agent'},
    {'name': 'doc_sync', 'skill': 'pm-documents:doc-verify', 'type': 'advisory'},
    {'name': 'formal_spec', 'skill': 'pm-requirements:spec-verify', 'type': 'advisory'},
]

# Default finalize pipeline steps (7-finalize phase)
# Used by phase-7-finalize when marshal.json has no 'finalize' override.
DEFAULT_FINALIZE_STEPS = [
    {'name': 'commit_push', 'skill': 'pm-workflow:workflow-integration-git', 'type': 'action'},
    {'name': 'create_pr', 'skill': 'pm-workflow:workflow-integration-git', 'type': 'action'},
    {'name': 'automated_review', 'skill': 'pm-workflow:workflow-integration-ci', 'type': 'api'},
    {'name': 'sonar_roundtrip', 'skill': 'pm-workflow:workflow-integration-sonar', 'type': 'api'},
    {'name': 'knowledge_capture', 'skill': 'plan-marshall:manage-memories', 'type': 'advisory'},
    {'name': 'lessons_capture', 'skill': 'plan-marshall:manage-lessons', 'type': 'advisory'},
]

# Build system defaults (detection reference only - commands are in modules)
BUILD_SYSTEM_DEFAULTS = {
    'maven': {'skill': 'pm-dev-java:plan-marshall-plugin'},
    'gradle': {'skill': 'pm-dev-java:plan-marshall-plugin'},
    'npm': {'skill': 'pm-dev-frontend:plan-marshall-plugin'},
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
    - Module facts come from derived-data.json (see plan-marshall:analyze-project-architecture)
    """
    import copy

    return {
        'extension_defaults': {},
        'skill_domains': {'system': copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)},
        'system': {'retention': copy.deepcopy(DEFAULT_SYSTEM_RETENTION)},
        'plan': {
            'defaults': copy.deepcopy(DEFAULT_PLAN_DEFAULTS),
            'finalize': copy.deepcopy(DEFAULT_PLAN_FINALIZE),
        },
        'verification': {
            'max_iterations': DEFAULT_VERIFICATION_MAX_ITERATIONS,
            'steps': copy.deepcopy(DEFAULT_VERIFICATION_STEPS),
        },
        'finalize': {
            'max_iterations': DEFAULT_FINALIZE_MAX_ITERATIONS,
            'steps': copy.deepcopy(DEFAULT_FINALIZE_STEPS),
        },
    }
