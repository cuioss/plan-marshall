"""
Default configurations for manage-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Reserved keys in nested domain config (not profile names)
# bundle: Reference to bundle providing this domain (e.g., 'pm-dev-java')
# execute_task_skills: System domain only - profile to execute-task skill mapping
# workflow_skill_extensions: Domain extensions (outline, triage)
# defaults/optionals: System domain top-level skills
RESERVED_DOMAIN_KEYS = [
    'bundle',
    'execute_task_skills',
    'workflow_skill_extensions',
    'defaults',
    'optionals',
]

# Execute-task skills map profile -> workflow skill
# All profiles use the unified execute-task skill which handles profile dispatch internally.
# Keys align with constants.VALID_PROFILES (source of truth for profile names)
# These are defaults; marshall-steward auto-discovers from extension.py files
DEFAULT_EXECUTE_TASK_SKILLS = {
    'implementation': 'plan-marshall:execute-task',
    'module_testing': 'plan-marshall:execute-task',
    'integration_testing': 'plan-marshall:execute-task',
    'verification': 'plan-marshall:execute-task',
}

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN = {
    'defaults': [],
    'optionals': [],
    'execute_task_skills': DEFAULT_EXECUTE_TASK_SKILLS,
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
        raise ValueError(f'Skills must not appear in both defaults and optionals: {sorted(overlap)}')


# System retention defaults
DEFAULT_SYSTEM_RETENTION = {
    'logs_days': 1,
    'archived_plans_days': 5,
    'memory_days': 5,
    'lessons_superseded_days': 0,
    'temp_on_maintenance': True,
}

# Phase-specific plan defaults
DEFAULT_PLAN_INIT = {
    'branch_strategy': 'feature',
    'use_worktree': True,
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

# Valid values for phase-5-execute.rebase_strategy — enum controlling how the
# worktree syncs against origin/{base_branch} at execute start.
#   - 'rebase': git rebase origin/{base} (rewrites history; requires force-push when PR is open)
#   - 'merge':  git merge --no-edit origin/{base} (no history rewrite; PR-safe; default)
VALID_REBASE_STRATEGIES = ('rebase', 'merge')


def validate_rebase_strategy(value: str) -> None:
    """Validate that `rebase_strategy` is one of the allowed enum values.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_REBASE_STRATEGIES`.
    """
    if value not in VALID_REBASE_STRATEGIES:
        raise ValueError(f"Invalid rebase_strategy '{value}'. Allowed: {list(VALID_REBASE_STRATEGIES)}")


DEFAULT_PLAN_EXECUTE = {
    'commit_strategy': 'per_plan',
    'finalize_without_asking': True,
    'verification_max_iterations': 5,
    # When True, phase-5-execute runs a sync step against origin/{base_branch}
    # at phase start (primary drift-sync point). When False, phase-6-finalize's
    # `pr update-branch` remains the only sync point.
    'rebase_on_execute_start': True,
    # Enum: see VALID_REBASE_STRATEGIES / validate_rebase_strategy.
    'rebase_strategy': 'merge',
    'steps': list(BUILT_IN_VERIFY_STEPS),
}

# Built-in finalize step names (dispatch table in phase-6-finalize SKILL.md)
# Prefixed with 'default:' to distinguish from project: and fully-qualified skill steps
BUILT_IN_FINALIZE_STEPS = [
    'default:pre-push-quality-gate',
    'default:commit-push',
    'default:create-pr',
    'default:automated-review',
    'default:sonar-roundtrip',
    'default:knowledge-capture',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:record-metrics',
    'default:archive-plan',
]

# Optional bundle-provided finalize steps (opt-in)
# These appear in `list-finalize-steps` output but are intentionally omitted from
# DEFAULT_PLAN_FINALIZE['steps'], so projects must explicitly add them to
# marshal.json to activate. Each entry is a fully-qualified `bundle:skill` reference.
OPTIONAL_BUNDLE_FINALIZE_STEPS = [
    'plan-marshall:plan-retrospective',
]

# Human-readable descriptions for built-in finalize steps
BUILT_IN_FINALIZE_STEP_DESCRIPTIONS = {
    'default:pre-push-quality-gate': 'Run quality-gate per affected bundle as the last gate before push',
    'default:commit-push': 'Commit and push changes',
    'default:create-pr': 'Create pull request',
    'default:automated-review': 'CI automated review',
    'default:sonar-roundtrip': 'Sonar analysis roundtrip',
    'default:knowledge-capture': 'Capture learnings to memory',
    'default:lessons-capture': 'Record lessons learned',
    'default:branch-cleanup': 'Merge PR (with --delete-branch) and pull latest',
    'default:record-metrics': 'Record final plan metrics before archive',
    'default:archive-plan': 'Archive the completed plan',
}

# Human-readable descriptions for optional bundle-provided finalize steps
# Used as a fallback when the skill's SKILL.md frontmatter cannot be parsed for
# a description; surfaced through `list-finalize-steps`.
OPTIONAL_BUNDLE_FINALIZE_STEP_DESCRIPTIONS = {
    'plan-marshall:plan-retrospective': 'Capture a structured retrospective of the completed plan',
}

DEFAULT_PLAN_FINALIZE = {
    'max_iterations': 3,
    'review_bot_buffer_seconds': 180,
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
    - Module facts come from per-module derived.json/enriched.json under
      .plan/architecture/<module>/, with the module set canonicalised by
      .plan/architecture/_project.json["modules"] (see plan-marshall:manage-architecture)
    - Extension verify steps in phase-5-execute.steps are appended by skill-domains configure
    """
    import copy

    system_domain = copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)
    validate_domain_invariants(system_domain)
    return {
        'providers': [],
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
