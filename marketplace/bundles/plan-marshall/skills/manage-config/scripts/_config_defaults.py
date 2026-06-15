"""
Default configurations for manage-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

# Direct import - PYTHONPATH set by executor. The branch-prefix literals live
# in constants.py exactly once; this module imports them to build
# DEFAULT_PROJECT['working_prefixes'] (the fail-closed fallback seed).
from constants import (  # type: ignore[import-not-found]
    DEFAULT_BRANCH_PREFIX_WORKING,
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
# `working_prefixes` is the transparent, operator-editable source of truth for
# the closed set of allowed working-branch prefixes for plan feature branches
# (e.g. `feature/`), enforced by the branch-prefix validation in
# `marshall-steward`. It is seeded on `init` and back-filled into existing
# projects by `sync-defaults` (the deep-merge path that seeds every
# DEFAULT_PROJECT key non-destructively). It is stored as a JSON array so it is
# visible and editable directly in marshal.json. The literals live in
# constants.py (DEFAULT_BRANCH_PREFIX_WORKING) as the fail-closed fallback; this
# block is the only place that materialises them into the default marshal.json
# config.
DEFAULT_PROJECT = {
    'default_base_branch': 'main',
    'working_prefixes': list(DEFAULT_BRANCH_PREFIX_WORKING),
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

# Run-at-all gate enum. Each distributed gate knob (deep_lane, escalation,
# revalidation, qgate, self_review, plugin_doctor, simplify) takes one of these
# values. `auto` (the default) defers to the owning phase's decision machinery;
# `always` forces the gate's step/lane in; `never` forces it out.
VALID_RUN_AT_ALL = ('auto', 'always', 'never')


def validate_run_at_all(value: str, field_name: str) -> None:
    """Validate a run-at-all gate value (``auto|always|never``).

    Args:
        value: The candidate gate value.
        field_name: The dotted ``plan.<phase>.<knob>`` path, used in the error
            message so a rejected value names the offending knob.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_RUN_AT_ALL`.
    """
    if value not in VALID_RUN_AT_ALL:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Allowed: {list(VALID_RUN_AT_ALL)}"
        )


# Plan-wide effort fallback (`plan.effort` in marshal.json — single string).
#
# Per-phase effort defaults are seeded at init so a fresh project gets per-phase
# model tuning out of the box and `effort resolve-target` resolves a concrete
# `execution-context-{level}` rather than silently falling back to
# `level: inherit, source: implicit_default`. The seeded values mirror the
# `balanced` named preset's expanded per-phase shape (the middle-of-the-road
# tuning) — see `plan-marshall:plan-marshall` `effort_presets.py::EffortPresets.BALANCED`.
# The canonical level palette, the resolver chain, and the role registry are
# owned by the effort standards — see
# `plan-marshall:plan-marshall/standards/effort-variants.md`,
# `effort-levels.md`, and `effort-roles.md`; this module only seeds the
# operator-visible per-phase defaults. The post-wizard Effort menu
# (`apply-preset` / per-phase edit) still tunes these after init.
DEFAULT_PLAN_EFFORT = 'level-3'

# Phase-specific plan defaults
DEFAULT_PLAN_INIT = {
    'branch_strategy': 'feature',
    'use_worktree': True,
    # Per-phase effort default (seeded at init; balanced-preset baseline). The
    # phase-1-init role group has only the `default` subkey, so a string
    # shorthand is the canonical on-disk shape. Read via
    # `manage-config plan phase-1-init get --field effort` / `effort read --role phase-1-init`.
    'effort': 'level-3',
    # Auto-continue from 1-init to 2-refine. true = no gate (current behaviour);
    # false = stop after init and wait for the user. Mirrors the sibling
    # plan_without_asking / execute_without_asking review-gate pattern.
    'init_without_asking': True,
    # Deep-lane run-at-all gate (auto|always|never). Consumed by the
    # phase-1-init planning-lane router (_cmd_planning_lane.py): `always` forces
    # the deep lane, `never` forces light, `auto` (default) defers to the S1-S6
    # signal set. Read via
    # `manage-config plan phase-1-init get --field deep_lane`.
    'deep_lane': 'auto',
    # Hard-escalation safety-ratchet gate (auto|always|never). `auto` keeps the
    # DQ3 explosion / build-break / premise escalation ratchet live; `never` is
    # the explicit full-speed-full-risk opt-in. Read via
    # `manage-config plan phase-1-init get --field escalation`.
    'escalation': 'auto',
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
    # Per-phase effort default (seeded at init; balanced-preset baseline).
    'effort': 'level-3',
    # Premise / narrative-vs-code safety-check run-at-all gate
    # (auto|always|never). Consumed by the light lane + deep refine
    # revalidation pass. Read via
    # `manage-config plan phase-2-refine get --field revalidation`.
    'revalidation': 'auto',
}

DEFAULT_PLAN_OUTLINE = {
    'plan_without_asking': False,
    # Planning-time q-gate validation run-at-all gate (auto|always|never).
    # Consumed by the deep-lane outline dispatch. Read via
    # `manage-config plan phase-3-outline get --field qgate`.
    'qgate': 'auto',
    # Per-phase effort default (seeded at init; balanced-preset baseline lifts
    # outline analysis to level-4).
    'effort': 'level-4',
}

DEFAULT_PLAN_PLAN = {
    'execute_without_asking': True,
    # Per-phase effort default (seeded at init; balanced-preset baseline).
    'effort': 'level-3',
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
    # When true (the default), the execute loop commits per-deliverable on the
    # feature branch and phase-6-finalize pushes + opens a PR. When false, the
    # run is local-only: per-deliverable commits are still made, but the
    # phase-6 commit-push/push/PR steps are stripped by the manage-execution-
    # manifest commit_push_disabled pre-filter.
    'commit_and_push': True,
    'max_iterations': 5,
    # Per-deliverable build depth gating phase-5-execute's chain-tail focused
    # build (Step 10). Enum: see VALID_PER_DELIVERABLE_BUILD /
    # validate_per_deliverable_build. Default 'compile+scoped-test' resolves the
    # changed module and runs compile + scoped module-tests, keeping mid-execute
    # builds focused; the whole-tree quality sweep stays once at end-of-phase.
    'per_deliverable_build': 'compile+scoped-test',
    # Per-task budget reserve gating the phase-5-execute continue-vs-yield
    # sentinel. The `_tokens` suffix names the unit (tokens); the value is the
    # human-friendly magnitude string "50K", parsed back to the int 50000 by the
    # phase-5-execute consumer via `sensible_number.parse_sensible_int`.
    # phase-5-execute reads this via
    # `manage-config plan phase-5-execute get --field per_task_budget_reserve_tokens`;
    # the workflow's documented fallback when the knob is absent is 50000.
    # Registering it here makes the reserve operator-visible in marshal.json.
    'per_task_budget_reserve_tokens': '50K',
    'steps': list(BUILT_IN_VERIFY_STEPS),
    # Per-phase effort default (seeded at init; balanced-preset baseline). The
    # phase-5-execute role group has the `default` (per-task implementation) and
    # `verification-feedback` (build-runner triage) subkeys, so the on-disk shape
    # is an object. balanced lifts the per-task tier to level-4 and keeps triage
    # at level-3. Read via
    # `manage-config plan phase-5-execute get --field effort` or
    # `effort resolve-target --phase phase-5-execute --role <subkey>`.
    'effort': {
        'default': 'level-4',
        'verification-feedback': 'level-3',
    },
}

# Built-in finalize step names (dispatch table in phase-6-finalize SKILL.md)
# Prefixed with 'default:' to distinguish from project: and fully-qualified skill steps
BUILT_IN_FINALIZE_STEPS = [
    'default:pre-push-quality-gate',
    'default:finalize-step-whole-tree-gate',
    'default:commit-push',
    'default:finalize-step-simplify',
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
    'default:finalize-step-whole-tree-gate': 'Whole-tree completeness gate for clean-slate/breaking plans — greps the entire marketplace tree (not the diff) for surviving references to symbols/contracts the plan deleted and flags request-mandate items absent from the diff; runs pre-commit so a survivor BLOCKS the push',
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
    # Automation knobs — once a finalize gate has run, proceed without asking?
    # finalize_without_asking gates the auto-continue from execute into the
    # finalize pipeline; loop_back_without_asking gates the auto-loop-back on a
    # finalize-driven fix; auto_merge_after_ci gates the post-CI auto-merge.
    # Historical defaults preserved. Read via
    # `manage-config plan phase-6-finalize get --field <knob>`.
    'finalize_without_asking': True,
    'loop_back_without_asking': False,
    'auto_merge_after_ci': True,
    # Finalize run-at-all gates (auto|always|never), consumed by the manifest
    # composer's finalize step-selection (manage-execution-manifest.py). Each
    # gate maps to exactly one finalize step: self_review ->
    # finalize-step-pre-submission-self-review; qgate -> pre-push-quality-gate
    # (finalize blocking-findings re-capture); plugin_doctor ->
    # finalize-step-plugin-doctor; simplify -> finalize-step-simplify. `auto`
    # (default) defers to the existing decision machinery; `always`/`never`
    # force the step in/out. Read via
    # `manage-config plan phase-6-finalize get --field <gate>`.
    'self_review': 'auto',
    'qgate': 'auto',
    'plugin_doctor': 'auto',
    'simplify': 'auto',
    # Default timeout (seconds) for the CI-completion polling commands consumed
    # by tools-integration-ci/scripts/ci_base.py (`ci checks wait`,
    # `ci pr wait-for-comments`, `ci checks wait-for-status-flip`, and the two
    # `issue wait-for-*` polls). This is a finalize wait-policy, not CI
    # configuration, so it lives under the owning phase. Resolution precedence
    # inside ci_base.py:
    #   1. Explicit `--timeout` CLI flag (always wins when supplied).
    #   2. `plan.phase-6-finalize.checks_wait_timeout_seconds` in marshal.json.
    #   3. The 600-second fallback baked into the resolver — covers callers
    #      running outside a plan-marshall project where marshal.json is absent.
    # 600s gives headroom over verify jobs observed taking 318s+ on hot CI
    # runners without hiding a genuinely stuck pipeline behind an excessive
    # ceiling.
    'checks_wait_timeout_seconds': 600,
    # Threshold gating the pre-rebase auto-proceed decision in branch-cleanup.md,
    # orthogonal to `plan.phase-6-finalize.auto_merge_after_ci` (which gates
    # the post-CI merge). The
    # value `no_overlap_only` permits the auto-rebase to proceed only when the
    # rebase would touch a disjoint file set; any overlap defers to the operator.
    # branch-cleanup.md reads this row via
    # `manage-config plan phase-6-finalize get --field auto_rebase_threshold`,
    # so registering it here makes the threshold operator-visible in marshal.json.
    'auto_rebase_threshold': 'no_overlap_only',
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
    'drop_review_on_scope_gate': False,
    'steps': list(BUILT_IN_FINALIZE_STEPS),
    # Per-phase effort default (seeded at init; balanced-preset baseline). The
    # phase-6-finalize role group has `default`, `verification-feedback`
    # (sonar / pr-comment / plugin-doctor / pr-state triage), and
    # `post-run-review` subkeys, so the on-disk shape is an object. balanced
    # lifts post-run-review to level-4 and keeps default + verification-feedback
    # at level-3. Read via
    # `manage-config plan phase-6-finalize get --field effort` or
    # `effort resolve-target --phase phase-6-finalize --role <subkey>`.
    'effort': {
        'default': 'level-3',
        'verification-feedback': 'level-3',
        'post-run-review': 'level-4',
    },
}

# Build system defaults (detection reference only - commands are in modules)
BUILD_SYSTEM_DEFAULTS = {
    'maven': {'skill': 'plan-marshall:plan-marshall-plugin'},
    'gradle': {'skill': 'plan-marshall:plan-marshall-plugin'},
    'npm': {'skill': 'plan-marshall:plan-marshall-plugin'},
}

# Build-queue defaults (`build.queue.*` in marshal.json — under the top-level
# `build` block, peer to `build.map`).
# `max_slots` is the number of concurrent build admissions the cross-session
# build queue grants before enqueuing further requests; the build-queue
# admission primitive (`plan-marshall:manage-locks:build_queue`) reads it via
# `build.queue.max_slots`, falling back to 5 when the block or key is absent.
# `max_retries` is the number of times the build wrapper re-polls a `blocked`
# admission before giving up. `upper_limit_seconds` is the adaptive stale-reclaim
# ceiling — the per-build held-duration bound the self-healing reaper measures
# against; it is seeded at the 600 s floor (the same value
# `manage-run-config._read_build_queue_upper_limit` falls back to) inside the
# clamped `[600, 3600]` range, so the key is operator-visible instead of
# fallback-only. All three keys live under the marshal.json top-level `build`
# block (not under `plan.*`) because the build queue is a project-wide,
# cross-plan resource. Registering them here makes the queue bounds
# operator-visible and editable directly in marshal.json.
DEFAULT_BUILD_QUEUE = {'max_slots': 5, 'max_retries': 10, 'upper_limit_seconds': 600}


def get_default_config() -> dict:
    """Get complete default marshal.json configuration.

    Returns a new dict each time to avoid mutation issues.

    The ``build.map`` block is NOT seeded here: build_map is never
    populated at init time. Step 8b of the marshall-steward wizard (``build-map
    seed``) is the sole authoritative seed point, gated on completed architecture
    discovery so applicability scoping has discovered modules to work with. The
    write-once guard in :func:`_config_core.seed_build_map_into` ensures the first
    explicit seed wins and subsequent seedings without ``--force`` are no-ops.

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
    config = {
        'providers': [],
        'project': copy.deepcopy(DEFAULT_PROJECT),
        'skill_domains': {'system': system_domain},
        'build': {'queue': copy.deepcopy(DEFAULT_BUILD_QUEUE)},
        'system': {'retention': copy.deepcopy(DEFAULT_SYSTEM_RETENTION)},
        'plan': {
            # Plan-wide effort fallback (string at plan.effort). Resolves a
            # concrete level for any role whose per-phase effort is absent, so
            # `effort resolve-target --default` never falls back to inherit on a
            # freshly-seeded config.
            'effort': DEFAULT_PLAN_EFFORT,
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
    return config
