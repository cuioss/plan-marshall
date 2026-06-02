"""
Default configurations for manage-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Direct import - PYTHONPATH set by executor. The branch-prefix literals live
# in constants.py exactly once; this module imports them to build
# DEFAULT_PROJECT['branch_naming'] (the fail-closed fallback seed).
from constants import (  # type: ignore[import-not-found]
    DEFAULT_BRANCH_PREFIX_WORKING,
    DEFAULT_CI_BRANCH_ALLOWLIST,
)

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
    'lessons_superseded_days': 0,
    'temp_on_maintenance': True,
}

# Project-level defaults (`project.*` in marshal.json).
#
# `default_base_branch` is the project's canonical base branch. Consumer
# projects override this at first-run via `marshall-steward`, which prompts
# for the value and writes it through `manage-config project set --field
# default_base_branch --value {answer}`. The wizard's default suggestion is
# derived from `git symbolic-ref refs/remotes/origin/HEAD` (parsed as
# `refs/remotes/origin/{branch}`), with `main` as the last-resort fallback
# when `origin/HEAD` is unset. `phase-1-init` reads this value as the seed
# for `references.base_branch`; operators may still override per-plan via
# `manage-references set --field base_branch` after init.
#
# `branch_naming` is the transparent, operator-editable source of truth for the
# canonical branch-prefix sets. It is seeded on `init` and back-filled into
# existing projects by `sync-defaults` (the deep-merge path that seeds every
# DEFAULT_PROJECT key non-destructively). The two sub-lists are stored as JSON
# arrays so they are visible and editable directly in marshal.json:
#   - working_prefixes: the closed set of allowed working-branch prefixes;
#     `manage-status create` validates `--worktree-branch` against this set.
#   - ci_allowlist: the full CI push-trigger allowlist (glob form) that a
#     structural test pins against `.github/workflows/python-verify.yml`.
# The literals live in constants.py (DEFAULT_BRANCH_PREFIX_WORKING /
# DEFAULT_CI_BRANCH_ALLOWLIST) as the fail-closed fallback; this block is the
# only place that materialises them into the default marshal.json config.
DEFAULT_PROJECT = {
    'default_base_branch': 'main',
    'branch_naming': {
        'working_prefixes': list(DEFAULT_BRANCH_PREFIX_WORKING),
        'ci_allowlist': list(DEFAULT_CI_BRANCH_ALLOWLIST),
    },
}

# open-in-ide gate default (`plan.open_in_ide` in marshal.json — flat bool).
# Default `true` preserves the current always-attempt-to-open behaviour.
# A missing key is also treated as `true` by `manage-files open-in-ide`.
DEFAULT_OPEN_IN_IDE = True

# Plan-wide coverage default (`plan.coverage` in marshal.json — two-dial cell).
# The `inherit` seed is byte-identical to the resolver's implicit fallback; it
# exists only to make the plan-wide coverage knob operator-visible. The
# per-invocation identifier + expanded instruction are gathered into status.json
# metadata per the coverage-gathering contract — there are NO per-phase coverage
# seeds.
DEFAULT_PLAN_COVERAGE = {'thoroughness': 'inherit', 'scope': 'inherit'}

# Phase-specific plan defaults
DEFAULT_PLAN_INIT = {
    'branch_strategy': 'feature',
    'use_worktree': True,
    # Auto-continue from 1-init to 2-refine. true = no gate (current behaviour);
    # false = stop after init and wait for the user. Mirrors the sibling
    # plan_without_asking / execute_without_asking review-gate pattern.
    'init_without_asking': True,
}

# Valid values for phase-2-refine.simplicity — enum controlling how aggressively
# the implementation favours the minimum viable surface over speculative structure.
# Mirrors the sibling `compatibility` knob.
#   - 'lean':       implement the strict minimum; remove/inline surplus structure (default)
#   - 'pragmatic':  prefer minimal, but keep low-risk structure that aids readability
#   - 'defensive':  retain belt-and-suspenders structure (guards, seams) where uncertain
VALID_SIMPLICITY_LEVELS = ('lean', 'pragmatic', 'defensive')


def validate_simplicity(value: str) -> None:
    """Validate that `simplicity` is one of the allowed enum values.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_SIMPLICITY_LEVELS`.
    """
    if value not in VALID_SIMPLICITY_LEVELS:
        raise ValueError(f"Invalid simplicity '{value}'. Allowed: {list(VALID_SIMPLICITY_LEVELS)}")


DEFAULT_PLAN_REFINE = {
    'confidence_threshold': 95,
    'compatibility': 'breaking',
    'simplicity': 'lean',
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


# Valid values for phase-5-execute.per_deliverable_build — enum controlling the
# build depth phase-5-execute runs at each per-deliverable chain-tail point.
#   - 'off':                 skip the per-deliverable build entirely (end-of-phase sweep is the only build)
#   - 'compile-only':        resolve the changed module and run compile only
#   - 'compile+scoped-test': compile + scoped module-tests for the changed module (default)
#   - 'full':                whole-tree quality-gate per deliverable (legacy behavior; opt-in only)
VALID_PER_DELIVERABLE_BUILD = ('off', 'compile-only', 'compile+scoped-test', 'full')


def validate_per_deliverable_build(value: str) -> None:
    """Validate that `per_deliverable_build` is one of the allowed enum values.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_PER_DELIVERABLE_BUILD`.
    """
    if value not in VALID_PER_DELIVERABLE_BUILD:
        raise ValueError(
            f"Invalid per_deliverable_build '{value}'. Allowed: {list(VALID_PER_DELIVERABLE_BUILD)}"
        )


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
    # Per-deliverable build depth gating phase-5-execute's chain-tail focused
    # build (Step 10). Enum: see VALID_PER_DELIVERABLE_BUILD /
    # validate_per_deliverable_build. Default 'compile+scoped-test' resolves the
    # changed module and runs compile + scoped module-tests, keeping mid-execute
    # builds focused; the whole-tree quality sweep stays once at end-of-phase.
    'per_deliverable_build': 'compile+scoped-test',
    # Per-task budget reserve (tokens) gating the phase-5-execute continue-vs-yield
    # sentinel. phase-5-execute reads this via
    # `manage-config plan phase-5-execute get --field per_task_budget_reserve`;
    # the workflow's documented fallback when the knob is absent is 50000.
    # Registering it here makes the reserve operator-visible in marshal.json.
    'per_task_budget_reserve': 50000,
    'steps': list(BUILT_IN_VERIFY_STEPS),
}

# Built-in finalize step names (dispatch table in phase-6-finalize SKILL.md)
# Prefixed with 'default:' to distinguish from project: and fully-qualified skill steps
BUILT_IN_FINALIZE_STEPS = [
    'default:pre-push-quality-gate',
    'default:finalize-step-simplify',
    'default:commit-push',
    'default:create-pr',
    'default:ci-verify',
    'default:automated-review',
    'default:sonar-roundtrip',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:record-metrics',
    'default:finalize-step-print-phase-breakdown',
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
    'default:finalize-step-simplify': 'Holistic post-implementation simplification sweep — collapse accidental complexity introduced across the plan diff',
    'default:commit-push': 'Commit and push changes',
    'default:create-pr': 'Create pull request',
    'default:ci-verify': 'Classify CI run failures into the multi-failure-mode taxonomy and emit one structured triage finding per failing check (requires: [ci-complete] in consume-failures mode)',
    'default:automated-review': 'CI automated review (CI completion is a dispatcher-resolved precondition declared via requires: [ci-complete] on this step; triage-only 900 s budget)',
    'default:sonar-roundtrip': 'Sonar analysis roundtrip (requires: [ci-complete] in consume-failures mode)',
    'default:lessons-capture': 'Capture lessons from triage findings and PR-review escalations (skipped when qgate_findings=0, pr_comments_promoted=0, and script_failure_clusters=0)',
    'default:branch-cleanup': 'Clean up post-merge branch state — merges the PR with --delete-branch when create-pr is in the manifest; otherwise prunes local + remote branches directly',
    'default:record-metrics': 'Record final plan metrics before archive',
    'default:finalize-step-print-phase-breakdown': 'Optional finalize-summary supplement that captures the Phase Breakdown table from metrics.md and appends it after the per-step [OK] list',
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
    # Symmetric counterpart to phase-5-execute's `finalize_without_asking=True`
    # default. When False (default), the dispatcher halts at every loop_back
    # outcome from a phase-6-finalize step (FIX disposition, pr-comment-overflow,
    # or sonar-roundtrip FIX) and returns control to the user — the conservative
    # interactive shape. Set to True to opt into the full unattended cycle where
    # a loop_back outcome re-dispatches the execute pipeline inline (execute-task
    # → mark done → transition 5-execute → 6-finalize via finalize_without_asking)
    # and re-enters the finalize loop, capped by max_iterations.
    'loop_back_without_asking': False,
    # Gates the final `pr merge --delete-branch` step in the branch-cleanup
    # workflow independently of the pre-rebase auto-proceed gate (driven by
    # `auto_rebase_threshold` in branch-cleanup.md). Default True is
    # auto-merge after CI, coordinated via the cross-plan merge-lock so
    # concurrent plans serialize safely on the merge-to-main critical section
    # (the lock is precisely what makes auto-merge a safe default). Set False
    # to opt into the conservative interactive shape — after CI passes, the
    # operator is prompted before merging. The auto-merge fallback path
    # (`pr merge` -> `pr auto-merge` on branch-protection error) is unaffected
    # when an explicit "Yes, merge" consent (or the `auto_merge_after_ci == true`
    # bypass) was given; it does NOT activate on a deferred "No, skip merge".
    # This flag is a plain boolean — NOT a tri-state.
    'auto_merge_after_ci': True,
    # Threshold gating the pre-rebase auto-proceed decision in branch-cleanup.md,
    # orthogonal to `auto_merge_after_ci` (which gates the post-CI merge). The
    # value `no_overlap_only` permits the auto-rebase to proceed only when the
    # rebase would touch a disjoint file set; any overlap defers to the operator.
    # branch-cleanup.md reads this row via
    # `manage-config plan phase-6-finalize get --field auto_rebase_threshold`,
    # so registering it here makes the threshold operator-visible in marshal.json.
    'auto_rebase_threshold': 'no_overlap_only',
    # Pre-push-quality-gate activation config. The manifest composer
    # (manage-execution-manifest.py) reads
    # `plan.phase-6-finalize.pre_push_quality_gate.activation_globs` to decide
    # whether the `default:pre-push-quality-gate` finalize step is active; an
    # empty list (the default) leaves the step inactive. Registering the block
    # here makes the activation_globs knob operator-visible in marshal.json.
    'pre_push_quality_gate': {
        'activation_globs': [],
    },
    # Escape hatch for the manifest composer's `scope_gated_finalize` pre-filter
    # (manage-execution-manifest.py). The implicit scope gate drops the three
    # non-guarded heavyweight phase-6 steps (plan-retrospective,
    # pre-submission-self-review, plugin-doctor) on `surgical` plans and
    # `plan-retrospective` on `single_module` plans, but NEVER drops
    # `automated-review` — the bot-enforcement guard re-adds it on GitHub/GitLab
    # plans, so an implicit drop would be a silently-undone no-op. Set this to
    # True to explicitly opt into additionally dropping `automated-review` on
    # scope-gated plans (the only path that suppresses the bot-review gate). The
    # default False keeps the bot-review invariant intact.
    'lightweight_track_override': False,
    'steps': list(BUILT_IN_FINALIZE_STEPS),
}

# CI integration defaults (consumed by tools-integration-ci/scripts/ci_base.py).
#
# `checks_wait_timeout_seconds` controls the default timeout for the polling
# commands that wait for CI run completion (`ci checks wait`, `ci pr wait-for-comments`,
# `ci checks wait-for-status-flip`, and the two `issue wait-for-*` polls).
# Resolution precedence inside ci_base.py:
#   1. Explicit `--timeout` CLI flag (always wins when supplied).
#   2. `ci.checks_wait_timeout_seconds` in marshal.json (project-level override).
#   3. The 600-second fallback baked into the resolver — covers callers running
#      outside a plan-marshall project where marshal.json is absent.
# The default was raised from the prior hard-coded 300s after observing verify
# jobs taking 318s + on hot CI runners; 600s gives headroom without hiding a
# genuinely stuck pipeline behind an excessive ceiling.
DEFAULT_CI = {
    'checks_wait_timeout_seconds': 600,
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
        'project': copy.deepcopy(DEFAULT_PROJECT),
        'skill_domains': {'system': system_domain},
        'system': {'retention': copy.deepcopy(DEFAULT_SYSTEM_RETENTION)},
        'ci': copy.deepcopy(DEFAULT_CI),
        'plan': {
            'open_in_ide': DEFAULT_OPEN_IN_IDE,
            'coverage': copy.deepcopy(DEFAULT_PLAN_COVERAGE),
            'phase-1-init': copy.deepcopy(DEFAULT_PLAN_INIT),
            'phase-2-refine': copy.deepcopy(DEFAULT_PLAN_REFINE),
            'phase-3-outline': copy.deepcopy(DEFAULT_PLAN_OUTLINE),
            'phase-4-plan': copy.deepcopy(DEFAULT_PLAN_PLAN),
            'phase-5-execute': copy.deepcopy(DEFAULT_PLAN_EXECUTE),
            'phase-6-finalize': copy.deepcopy(DEFAULT_PLAN_FINALIZE),
        },
    }
