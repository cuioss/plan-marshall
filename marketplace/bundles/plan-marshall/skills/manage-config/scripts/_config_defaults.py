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
# revalidation, qgate, self_review, simplify) takes one of these
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

# Built-in verify step names (dispatch table in phase-5-execute SKILL.md).
# Each step is a parameterized canonical-verify ID of the shape
# ``default:verify:{canonical}`` — the trailing canonical segment is the
# parameter phase-5-execute feeds to ``architecture resolve --command
# {canonical}``, and the composer derives the matrix role from it via
# ``manage-execution-manifest._CANONICAL_TO_ROLE``. There is one parameterized
# step backing every canonical; the legacy fixed-name IDs
# (``default:quality_check`` / ``default:build_verify`` / ``default:coverage_check``)
# are gone. See ``phase-5-execute/standards/canonical_verify.md``.
BUILT_IN_VERIFY_STEPS = [
    'default:verify:quality-gate',
    'default:verify:module-tests',
    'default:verify:coverage',
]

# Human-readable descriptions for built-in verify steps
BUILT_IN_VERIFY_STEP_DESCRIPTIONS = {
    'default:verify:quality-gate': 'Run quality-gate build command',
    'default:verify:module-tests': 'Run full test suite',
    'default:verify:coverage': 'Run coverage build and verify threshold',
}

# Canonical-verify step prefix. A ``per_deliverable_build`` list entry MUST be a
# ``default:verify:{canonical}`` ID; the prefix-strict validator rejects any
# other shape (including the retired ``per_deliverable_build`` enum strings).
_VERIFY_STEP_PREFIX = 'default:verify:'

# The retired ``per_deliverable_build`` enum vocabulary. These strings are no
# longer accepted — ``per_deliverable_build`` is now a LIST of
# ``default:verify:{canonical}`` step IDs. The validator names these explicitly
# so a config carrying an old enum value gets an actionable migration error
# rather than a generic "not a list" rejection.
RETIRED_PER_DELIVERABLE_BUILD_ENUM = ('off', 'compile-only', 'compile+scoped-test', 'full')


def validate_per_deliverable_build(value: object) -> None:
    """Validate that ``per_deliverable_build`` is a list of canonical-verify IDs.

    ``per_deliverable_build`` is a LIST of ``default:verify:{canonical}`` step
    IDs (e.g. ``['default:verify:compile', 'default:verify:module-tests']``)
    selecting which canonical-verify rungs phase-5-execute runs at each
    per-deliverable chain-tail point. The empty list is permitted (it disables
    the per-deliverable build, matching the retired ``off`` enum value).

    Raises:
        ValueError: If ``value`` is not a list, if any entry is not a
            ``default:verify:{canonical}`` string, or if a retired enum string
            (``off`` / ``compile-only`` / ``compile+scoped-test`` / ``full``)
            is supplied.
    """
    if isinstance(value, str) and value in RETIRED_PER_DELIVERABLE_BUILD_ENUM:
        raise ValueError(
            f"per_deliverable_build no longer accepts the enum value '{value}'. "
            f"It is now a list of '{_VERIFY_STEP_PREFIX}{{canonical}}' step IDs "
            "(e.g. ['default:verify:compile','default:verify:module-tests']; "
            "use [] to disable the per-deliverable build)."
        )
    if not isinstance(value, list):
        raise ValueError(
            f"Invalid per_deliverable_build {value!r}: expected a list of "
            f"'{_VERIFY_STEP_PREFIX}{{canonical}}' step IDs."
        )
    retired = [e for e in value if isinstance(e, str) and e in RETIRED_PER_DELIVERABLE_BUILD_ENUM]
    if retired:
        raise ValueError(
            f"per_deliverable_build no longer accepts the enum value '{retired[0]}'. "
            f"It is now a list of '{_VERIFY_STEP_PREFIX}{{canonical}}' step IDs "
            "(e.g. ['default:verify:compile','default:verify:module-tests']; "
            "use [] to disable the per-deliverable build)."
        )
    invalid = [e for e in value if not (isinstance(e, str) and e.startswith(_VERIFY_STEP_PREFIX))]
    if invalid:
        raise ValueError(
            f"Invalid per_deliverable_build entries {invalid!r}: every entry must be a "
            f"'{_VERIFY_STEP_PREFIX}{{canonical}}' step ID."
        )


# The exact key set the cost_size_token_table must carry — the four T-shirt
# sizes the cost-sizing rubric (phase-4-plan/standards/cost-sizing.md) maps a
# task to. The table value for each size is a human-friendly magnitude string
# (e.g. "25K") parsed back to an int via sensible_number.parse_sensible_int.
COST_SIZE_LABELS = ('S', 'M', 'L', 'XL')


def validate_cost_size_token_table(value: object) -> None:
    """Validate the ``cost_size_token_table`` size→token mapping.

    ``cost_size_token_table`` maps each T-shirt size in
    :data:`COST_SIZE_LABELS` (``S``/``M``/``L``/``XL``) to a predicted-token
    magnitude. The keys must be exactly that set (no missing, no extra), and
    every value must parse as a human-friendly sensible int (``"25K"`` →
    25000) via :func:`sensible_number.parse_sensible_int`. The phase-4-plan
    bin-packer reads this table to map a task's derived ``cost_size`` to its
    ``predicted_cost_tokens``.

    Raises:
        ValueError: If ``value`` is not a dict, if its key set is not exactly
            ``{S, M, L, XL}``, or if any value does not parse as a sensible
            int.
    """
    from sensible_number import parse_sensible_int  # type: ignore[import-not-found]

    if not isinstance(value, dict):
        raise ValueError(
            f"Invalid cost_size_token_table {value!r}: expected a dict mapping "
            f"{list(COST_SIZE_LABELS)} to token magnitudes."
        )
    keys = set(value.keys())
    expected = set(COST_SIZE_LABELS)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise ValueError(
            f"Invalid cost_size_token_table keys {sorted(keys)}: expected exactly "
            f"{list(COST_SIZE_LABELS)} (missing={missing}, extra={extra})."
        )
    for size, magnitude in value.items():
        try:
            parse_sensible_int(magnitude)
        except ValueError as exc:
            raise ValueError(
                f"Invalid cost_size_token_table value for '{size}': {magnitude!r} "
                f"is not a parseable token magnitude ({exc})."
            ) from exc


DEFAULT_PLAN_EXECUTE = {
    # When true (the default), the execute loop commits per-deliverable on the
    # feature branch and phase-6-finalize pushes + opens a PR. When false, the
    # run is local-only: per-deliverable commits are still made, but the
    # phase-6 commit-push/push/PR steps are stripped by the manage-execution-
    # manifest commit_push_disabled pre-filter.
    'commit_and_push': True,
    'max_iterations': 5,
    # Per-deliverable build gating phase-5-execute's chain-tail focused build
    # (Step 10). A LIST of 'default:verify:{canonical}' step IDs (validated by
    # validate_per_deliverable_build); each entry is a canonical-verify rung the
    # chain-tail runs for the changed module. The default
    # ['default:verify:compile','default:verify:module-tests'] preserves the
    # former 'compile+scoped-test' behaviour — compile + scoped module-tests for
    # the changed module — keeping mid-execute builds focused while the
    # whole-tree quality sweep stays once at end-of-phase. Use [] to disable the
    # per-deliverable build (the former 'off' enum value).
    'per_deliverable_build': ['default:verify:compile', 'default:verify:module-tests'],
    # Size→token table mapping each T-shirt cost_size (S/M/L/XL) to a predicted
    # token magnitude. Validated by validate_cost_size_token_table (keys exactly
    # S/M/L/XL; every value parses via sensible_number.parse_sensible_int). The
    # phase-4-plan bin-packer (_tasks_envelope.py, via manage-tasks pack-envelopes)
    # reads this table at PLAN time to map a task's derived cost_size to its
    # predicted_cost_tokens. The default magnitudes (S≈25K / M≈60K / L≈130K /
    # XL≈260K) are calibrated to the forensic 134K–392K per-dispatch range and
    # are the tunable defaults; raise/lower them in marshal.json to recalibrate
    # the size model from observed post-return <usage>.
    'cost_size_token_table': {'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K'},
    # Per-envelope packing budget — the token ceiling the phase-4-plan bin-packer
    # accumulates predicted_cost_tokens against before opening a new envelope
    # group. The `_tokens` suffix names the unit (tokens); the value is the
    # human-friendly magnitude string "400K", parsed to an int via
    # sensible_number.parse_sensible_int. This is consumed at PLAN time by the
    # bin-packer (manage-tasks pack-envelopes), NOT a runtime comparand — the
    # continue-vs-yield decision is fully pre-computed into envelope_id groups at
    # plan time. The 400K default leaves headroom below a typical context window.
    # Registering it here makes the packing budget operator-visible in marshal.json.
    'per_envelope_budget_tokens': '400K',
    # Verification steps as an id-keyed map: each key is a built-in verify step
    # id, each value is that step's nested param object. Verification steps own
    # no params, so an ownerless step maps to `None` (serialized as `null`) — no
    # noisy empty `{}` object is written. The read path coerces every absent /
    # null / `{}` / TOON-`''` representation back to an empty dict. Key insertion
    # order is the execution order. The keyed-map shape (not a flat list) is the
    # single on-disk schema — readers iterate `.keys()` for the ordered step ids
    # and read the per-step param object (coerced to `{}` for ownerless steps)
    # from the value.
    'verification_steps': dict.fromkeys(BUILT_IN_VERIFY_STEPS),
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

# Valid values for the `default:sonar-roundtrip` step's nested `touched_file_cleanup`
# param — enum controlling which surface the Sonar roundtrip's success criterion
# covers.
#   - 'new_code_only':      success requires only new-code issues == 0 (default, lean)
#   - 'touched_files_zero': success additionally sweeps pre-existing issues on touched files
VALID_SONAR_TOUCHED_FILE_CLEANUP = ('new_code_only', 'touched_files_zero')


def validate_sonar_touched_file_cleanup(value: str) -> None:
    """Validate the `default:sonar-roundtrip` step's `touched_file_cleanup` param.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_SONAR_TOUCHED_FILE_CLEANUP`.
    """
    if value not in VALID_SONAR_TOUCHED_FILE_CLEANUP:
        raise ValueError(
            f"Invalid touched_file_cleanup '{value}'. "
            f"Allowed: {list(VALID_SONAR_TOUCHED_FILE_CLEANUP)}"
        )


# Step-owned params are no longer held in a centralized constant. Each
# param-owning finalize step declares its own params self-describingly in the
# `configurable:` block of its body-doc frontmatter; the single fail-loud reader
# is `extension-api/scripts/configurable_contract.py`. The finalize-step defaults
# seed (`DEFAULT_PLAN_FINALIZE['steps']`) is built by delegating each built-in
# step id through `configurable_contract.resolve_step_defaults_optional`, which
# folds a param-owning step to its `{param_key: default}` map and an ownerless
# step to `None` (serialized as `null`). The seed is computed lazily inside
# `get_default_config()` rather than at module import so `_config_defaults.py`
# does not take a hard module-import dependency on the cross-bundle parser
# (mirroring the lazy `extension_discovery` import in manage-execution-manifest).
#
# Param ownership (for reference; the declarations themselves are authoritative):
#   - default:sonar-roundtrip       → touched_file_cleanup, do_transition,
#                                      ce_wait_timeout_seconds
#   - default:automated-review      → review_bot_buffer_seconds
#   - default:branch-cleanup        → pr_merge_strategy, final_merge_without_asking,
#                                      auto_rebase_threshold
#   - default:finalize-step-simplify → simplify (run-at-all gate)
#   - project:finalize-step-pre-submission-self-review → self_review,
#                                      drop_review_on_scope_gate (NOT a built-in
#                                      step, so the seed does not include it; its
#                                      defaults are supplied by the reader's
#                                      default-merge when the project step is
#                                      absent from marshal.json)
# Phase-level knobs with no single owning step (checks_wait_timeout_seconds,
# max_iterations, finalize_without_asking, loop_back_without_asking, qgate,
# effort, …) stay flat siblings of `steps`.


def _seed_finalize_steps() -> dict[str, object]:
    """Build the finalize-step defaults seed via the configurable-contract parser.

    Iterates :data:`BUILT_IN_FINALIZE_STEPS` in order, delegating each step id to
    ``configurable_contract.resolve_step_defaults_optional``. A param-owning step
    maps to its ``{param_key: default}`` object; an ownerless step maps to
    ``None`` (serialized as ``null`` so no noisy empty ``{}`` is written). Key
    insertion order is the execution order.

    The cross-bundle parser is imported lazily here (not at module top level) so
    importing ``_config_defaults`` never pulls in the extension-api parser — the
    seed is only materialized when :func:`get_default_config` runs.

    Returns:
        The ordered keyed-map ``{step_id: {param_key: default} | None}``.
    """
    # Lazy import — executor sets PYTHONPATH for cross-skill imports.
    from configurable_contract import (  # type: ignore[import-not-found]
        resolve_step_defaults_optional,
    )

    return {
        step_id: resolve_step_defaults_optional(step_id)
        for step_id in BUILT_IN_FINALIZE_STEPS
    }


DEFAULT_PLAN_FINALIZE = {
    'max_iterations': 3,
    # Automation knobs — once a finalize gate has run, proceed without asking?
    # finalize_without_asking gates the auto-continue from execute into the
    # finalize pipeline; loop_back_without_asking gates the auto-loop-back on a
    # finalize-driven fix. (final_merge_without_asking, which gates the post-CI
    # auto-merge, is a step-owned param under `default:branch-cleanup` — declared
    # in that step's `configurable:` frontmatter and read via
    # `configurable_contract.py`.) Read via
    # `manage-config plan phase-6-finalize get --field <knob>`.
    'finalize_without_asking': True,
    'loop_back_without_asking': False,
    # qgate is the one finalize run-at-all gate that stays a flat phase-level
    # sibling (auto|always|never): it maps to pre-push-quality-gate (the finalize
    # blocking-findings re-capture) but is consumed by the decision machinery as a
    # phase-level run-at-all gate, not as a param the step body reads. `auto`
    # (default) defers to the existing decision machinery; `always`/`never` force
    # the step in/out. Read via
    # `manage-config plan phase-6-finalize get --field qgate`. The two other
    # run-at-all gates (`simplify`, `self_review`) and the
    # `drop_review_on_scope_gate` escape hatch each own exactly one finalize step,
    # so they fold into that step's nested param object under `steps` (declared in
    # the owning step's `configurable:` frontmatter, read by
    # `configurable_contract.py`) rather than remaining flat siblings.
    'qgate': 'auto',
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
    # Finalize steps as an id-keyed map: each key is a built-in finalize step id,
    # each value is that step's nested param object — or `None` (serialized as
    # `null`) for an ownerless step, so no noisy empty `{}` is written. Step-owned
    # params (sonar params under `default:sonar-roundtrip`; `review_bot_buffer_seconds`
    # under `default:automated-review`; `pr_merge_strategy` /
    # `final_merge_without_asking` / `auto_rebase_threshold` under
    # `default:branch-cleanup`; `simplify` under `default:finalize-step-simplify`)
    # fold under their owning built-in step. Each step's params are now declared
    # self-describingly in the step's body-doc `configurable:` frontmatter and read
    # by `configurable_contract.py`; the `self_review` / `drop_review_on_scope_gate`
    # knobs own the opt-in `project:finalize-step-pre-submission-self-review` step,
    # which is NOT a built-in candidate (not in BUILT_IN_FINALIZE_STEPS /
    # DEFAULT_PHASE_6_STEPS), so the default seed does NOT include it — a fresh
    # project's candidate list is unchanged. Their defaults (`auto` / `False`) are
    # supplied by the reader's default-merge when the project step is absent from
    # marshal.json. Key insertion order is the execution order. The keyed-map shape
    # (not a flat list) is the single on-disk schema — readers iterate `.keys()`
    # for the ordered step ids and read the per-step param object (coerced to `{}`
    # for ownerless steps) from the value.
    #
    # Seeded lazily by `_seed_finalize_steps()` inside `get_default_config()` (the
    # parser delegation cannot run at module import without a hard cross-bundle
    # dependency); this literal `None` placeholder is replaced there.
    'steps': None,
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

# Per-build-system wrapper-policy defaults. Each block lives under the top-level
# `build` block (peer to `build.queue` / `build.map`) because wrapper policy is a
# project-wide, per-build-system resource. The value is the operator escape valve
# consumed by `_build_execute_factory._read_require_wrapper_override`: a consumer
# repo genuinely lacking a checked-in wrapper sets `build.{tool}.require_wrapper`
# to false WITHOUT editing marketplace code. Defaults match the per-build-system
# static `ExecuteConfig.require_wrapper` values — True for maven/gradle/pyproject
# (the wrapper is required, no silent system-binary fallback), False for npm
# (no wrapper concept).
DEFAULT_BUILD_REQUIRE_WRAPPER = {
    'maven': {'require_wrapper': True},
    'gradle': {'require_wrapper': True},
    'pyproject': {'require_wrapper': True},
    'npm': {'require_wrapper': False},
}


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
    - Extension verify steps in phase-5-execute.verification_steps are appended by skill-domains configure
    """
    import copy

    system_domain = copy.deepcopy(DEFAULT_SYSTEM_DOMAIN)
    validate_domain_invariants(system_domain)
    # Self-validate the seeded phase-5-execute list/table defaults so a malformed
    # default shape fails loud at seed time rather than at first read.
    validate_per_deliverable_build(DEFAULT_PLAN_EXECUTE['per_deliverable_build'])
    validate_cost_size_token_table(DEFAULT_PLAN_EXECUTE['cost_size_token_table'])
    # Materialize the finalize-step defaults seed lazily via the configurable-
    # contract parser (the `'steps': None` placeholder in DEFAULT_PLAN_FINALIZE is
    # replaced here). Done after the deepcopy below so the module-level constant
    # stays free of the cross-bundle parser dependency at import time.
    finalize_section = copy.deepcopy(DEFAULT_PLAN_FINALIZE)
    finalize_section['steps'] = _seed_finalize_steps()
    config = {
        'providers': [],
        'project': copy.deepcopy(DEFAULT_PROJECT),
        'skill_domains': {'system': system_domain},
        'build': {
            'queue': copy.deepcopy(DEFAULT_BUILD_QUEUE),
            **copy.deepcopy(DEFAULT_BUILD_REQUIRE_WRAPPER),
        },
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
            'phase-6-finalize': finalize_section,
        },
    }
    return config
