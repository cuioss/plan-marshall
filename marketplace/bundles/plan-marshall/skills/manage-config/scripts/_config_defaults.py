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
# Convention: profile X maps to plan-marshall:task-X
# These are defaults; marshall-steward auto-discovers from extension.py files
DEFAULT_TASK_EXECUTORS = {
    'implementation': 'plan-marshall:task-implementation',
    'module_testing': 'plan-marshall:task-module-testing',
    'integration_testing': 'plan-marshall:task-integration_testing',
    'verification': 'plan-marshall:task-verification',
}

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN = {
    'defaults': ['plan-marshall:dev-general-practices'],
    'optionals': ['plan-marshall:dev-general-practices'],
    'task_executors': DEFAULT_TASK_EXECUTORS,
}

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
BUILT_IN_VERIFY_STEPS = ['default:quality_check', 'default:build_verify']

# Human-readable descriptions for built-in verify steps
BUILT_IN_VERIFY_STEP_DESCRIPTIONS = {
    'default:quality_check': 'Run quality-gate build command',
    'default:build_verify': 'Run full test suite',
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
    'default:commit_push',
    'default:create_pr',
    'default:automated_review',
    'default:sonar_roundtrip',
    'default:knowledge_capture',
    'default:lessons_capture',
    'default:branch_cleanup',
    'default:archive',
]

# Human-readable descriptions for built-in finalize steps
BUILT_IN_FINALIZE_STEP_DESCRIPTIONS = {
    'default:commit_push': 'Commit and push changes',
    'default:create_pr': 'Create pull request',
    'default:automated_review': 'CI automated review',
    'default:sonar_roundtrip': 'Sonar analysis roundtrip',
    'default:knowledge_capture': 'Capture learnings to memory',
    'default:lessons_capture': 'Record lessons learned',
    'default:branch_cleanup': 'Merge PR (with --delete-branch) and pull latest',
    'default:archive': 'Archive the completed plan',
}

DEFAULT_PLAN_FINALIZE = {
    'max_iterations': 3,
    'review_bot_buffer_seconds': 300,
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

    return {
        'skill_domains': {'system': copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)},
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
