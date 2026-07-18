# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Default configurations for manage-config.

Contains build system and domain default structures used during
project initialization and detection.
"""

import hashlib
import json

# Direct import - PYTHONPATH set by executor. The branch-prefix literals live
# in constants.py exactly once; this module imports them to build
# DEFAULT_PROJECT['working_prefixes'] (the fail-closed fallback seed).
from constants import (
    DEFAULT_BRANCH_PREFIX_WORKING,
)

# Reserved keys in nested domain config (not profile names)
# bundle: Reference to bundle providing this domain (e.g., 'pm-dev-java')
# workflow_skill_extensions: Domain extensions (outline, triage)
# defaults/optionals: System domain top-level skills
# always_on/file_globs: per-domain inclusion keys (bool / list[str]) — reserved so
#   profile iteration never treats them as profile names.
RESERVED_DOMAIN_KEYS = [
    'bundle',
    'workflow_skill_extensions',
    'defaults',
    'optionals',
    'always_on',
    'file_globs',
]

# Default system domain configuration
DEFAULT_SYSTEM_DOMAIN: dict[str, list[str]] = {
    'defaults': [],
    'optionals': [],
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


def validate_domain_inclusion(always_on: object, file_globs: object) -> None:
    """Validate the per-domain inclusion keys ``always_on`` / ``file_globs``.

    ``always_on`` (when provided) MUST be a ``bool``. Unlike the numeric
    validators (which reject ``bool`` because it is an ``int`` subclass), here a
    ``bool`` is exactly what is required — any non-bool (including an ``int``) is
    rejected. ``file_globs`` (when provided) MUST be a ``list`` whose members are
    all ``str``. A ``None`` value for either key means it is not being set on this
    call and is skipped (the ``set-inclusion`` verb sets each key independently).

    Args:
        always_on: The candidate ``always_on`` value, or ``None`` to skip.
        file_globs: The candidate ``file_globs`` value, or ``None`` to skip.

    Raises:
        ValueError: If ``always_on`` is provided and is not a bool, or
            ``file_globs`` is provided and is not a list of str.
    """
    if always_on is not None and not isinstance(always_on, bool):
        raise ValueError(f'Invalid always_on {always_on!r}: expected a bool.')
    if file_globs is not None:
        if not isinstance(file_globs, list) or not all(isinstance(g, str) for g in file_globs):
            raise ValueError(f'Invalid file_globs {file_globs!r}: expected a list of str.')


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
#
# `pr_strategy` (`compact` | `distinct`, default `compact`) and
# `pr_compact_max_changed_files` (int, default 150) are the PR-batching policy
# knobs. They govern whether follow-up / config-migration / ad-hoc changes ride
# an already-pending related PR (compact, when the changed-file count stays
# within the ceiling) or open a separate PR (distinct, or over-ceiling). The
# `manage-config project pr-decision --changed-files N` verb reads both knobs and
# returns a `ride|split` verdict; it is the documented consult surface every
# PR-opening guidance references. Both keys are seeded on `init` and back-filled
# into existing projects by `sync-defaults`' non-destructive deep-merge (the same
# mechanism `working_prefixes` relies on).
DEFAULT_PROJECT = {
    'default_base_branch': 'main',
    'working_prefixes': list(DEFAULT_BRANCH_PREFIX_WORKING),
    'pr_strategy': 'compact',
    'pr_compact_max_changed_files': 150,
}


# PR-batching strategy enum (`project.pr_strategy` in marshal.json).
#   - 'compact'  (default): ride an already-pending related PR when the changed-
#                           file count stays within pr_compact_max_changed_files.
#   - 'distinct':           always open a separate PR.
VALID_PR_STRATEGY = ('compact', 'distinct')


def validate_pr_strategy(value: object, field_name: str = 'pr_strategy') -> None:
    """Validate `pr_strategy` (``compact|distinct``).

    Args:
        value: The candidate strategy value.
        field_name: The ``project.pr_strategy`` path, used in the error message so
            a rejected value names the offending knob.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_PR_STRATEGY`.
    """
    if value not in VALID_PR_STRATEGY:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Allowed: {list(VALID_PR_STRATEGY)}"
        )


def validate_pr_compact_max_changed_files(
    value: object, field_name: str = 'pr_compact_max_changed_files'
) -> None:
    """Validate `pr_compact_max_changed_files` (int ``>= 0``).

    Booleans are rejected even though ``bool`` is an ``int`` subclass, mirroring
    the sibling numeric validators (:func:`validate_lane_prune_thresholds`).

    Args:
        value: The candidate ceiling value.
        field_name: The ``project.pr_compact_max_changed_files`` path, used in the
            error message so a rejected value names the offending knob.

    Raises:
        ValueError: If ``value`` is a bool, is not an int, or is negative.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"Invalid {field_name} {value!r}: expected an int >= 0."
        )


def pr_compact_rides_existing_pr(
    strategy: str, changed_file_count: int, max_changed_files: int
) -> bool:
    """Return whether a change rides an existing PR under the compact policy.

    This is an implementation detail backing the ``project pr-decision`` CLI verb,
    NOT the documented consult surface (that is the verb). A change rides an
    existing PR only under the ``compact`` strategy when its changed-file count
    stays within the ceiling; ``distinct`` always splits.

    Args:
        strategy: The resolved ``pr_strategy`` value.
        changed_file_count: The change's changed-file count.
        max_changed_files: The resolved ``pr_compact_max_changed_files`` ceiling.

    Returns:
        ``True`` when the change rides the existing PR; ``False`` when it splits.
    """
    return strategy == 'compact' and changed_file_count <= max_changed_files

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

# Plan-wide per-field byte cap for quarantined `raw_input.{field}` free-text in the
# findings ledger (`plan.finding_raw_input_max_bytes` in marshal.json). Every
# producer files untrusted free-text under the `raw_input.{field}` quarantine
# sub-namespace; the ledger caps each field at this many bytes and appends a
# `[truncated]` marker on overflow. 65536 (64 KiB) is corpus-grounded — across 399
# PR-comment findings p50 ≈ 2 KB, p99 ≈ 21 KB, max ≈ 68 KB — so 64 KiB retains the
# full body for effectively every real finding while bounding a hostile oversized
# payload. The seed is byte-identical to `manage-findings`'
# `DEFAULT_RAW_INPUT_MAX_BYTES`; it exists to make the cap operator-visible and
# editable in marshal.json (callers thread the resolved value into
# `manage-findings ... --raw-input-max-bytes`).
DEFAULT_FINDING_RAW_INPUT_MAX_BYTES = 65536

# Gate-mode enum. Governs ONLY the three planning gates `deep_lane` /
# `escalation` (phase-1-init) and `revalidation` (phase-2-refine): `auto` (the
# default) defers to the owning phase's decision machinery; `always` forces the
# gate's decision in; `never` forces it out. The four finalize ceremony gates
# (`qgate`, `self_review`, `simplify`, `security_audit`) do NOT ride this enum —
# each is governed by its owning step's `steps.<step>.lane` override
# (`off`/`minimal`/`auto`). Planning-time q-gate validation is governed by the
# distinct `q_gate_validation` knob (see :data:`VALID_Q_GATE_VALIDATION` below).
VALID_GATE_MODE = ('auto', 'always', 'never')


def validate_gate_mode(value: str, field_name: str) -> None:
    """Validate a gate_mode value (``auto|always|never``).

    Scoped to the three planning gates `deep_lane` / `escalation` /
    `revalidation`.

    Args:
        value: The candidate gate value.
        field_name: The dotted ``plan.<phase>.<knob>`` path, used in the error
            message so a rejected value names the offending knob.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_GATE_MODE`.
    """
    if value not in VALID_GATE_MODE:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Allowed: {list(VALID_GATE_MODE)}"
        )


# Planning-time q-gate validation enum. The `q_gate_validation` knob governs how
# the planning phases (phase-3-outline, phase-4-plan) run q-gate validation over
# the emerging plan artifacts:
#   - 'off':         skip q-gate validation entirely.
#   - 'once':        run a single validation pass; do not re-loop on findings
#                    (default).
#   - 'until_clean': re-run validation until it reports no blocking findings.
# This replaces the retired planning-time `qgate` run-at-all gate on the outline
# step; the finalize-time `qgate` gate now rides its owning step's
# `steps['pre-push-quality-gate'].lane` override, not this knob.
VALID_Q_GATE_VALIDATION = ('off', 'once', 'until_clean')


def validate_q_gate_validation(value: str, field_name: str) -> None:
    """Validate a q-gate-validation value (``off|once|until_clean``).

    Args:
        value: The candidate q-gate-validation value.
        field_name: The dotted ``plan.<phase>.q_gate_validation`` path, used in
            the error message so a rejected value names the offending knob.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_Q_GATE_VALIDATION`.
    """
    if value not in VALID_Q_GATE_VALIDATION:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Allowed: {list(VALID_Q_GATE_VALIDATION)}"
        )


# ---------------------------------------------------------------------------
# Lane / execution-profile selection config.
#
# Three operator-facing knobs governing the execution-profile lane mechanism.
# The per-element lane vocabulary (the closed `lane.class` enum), the
# class→default tier table, and the prune-predicate NAMES are owned by the
# central standard
# (`extension-api/standards/ext-point-lane-element.md`) — these knobs carry only
# the project-level posture / override / threshold config the manifest composer
# resolves OVER that contract; they do not restate the enforcement-critical
# enums.
# ---------------------------------------------------------------------------

# `lane_selection` (`plan.phase-1-init.lane_selection`) — whether init PROMPTS
# for the execution-profile posture or silently takes the computed `auto`
# posture.
#   - 'ask'  (default): surface the minimal/auto/full posture dialogue at init.
#   - 'auto':           skip the dialogue and take the `auto` projection silently.
# Mirrors the sibling deep_lane / finalize_without_asking ask/auto family.
VALID_LANE_SELECTION = ('ask', 'auto')


def validate_lane_selection(value: str) -> None:
    """Validate `lane_selection` (``ask|auto``).

    Args:
        value: The candidate lane-selection value.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_LANE_SELECTION`.
    """
    if value not in VALID_LANE_SELECTION:
        raise ValueError(
            f"Invalid lane_selection '{value}'. Allowed: {list(VALID_LANE_SELECTION)}"
        )


# Per-element lane override value set. Pins any lane-participating element
# (nested under `plan.<phase>.steps.<step>.lane` in marshal.json, the same
# channel finalize-step params use) to a fixed posture cutoff:
#   - 'off':     never run the element (drops even a core/derived-state floor
#                element — honored, but a derived-state weakening additionally
#                emits a correctness warning at compose time).
#   - 'minimal': force-keep in every posture (promote to the floor).
#   - 'auto' / 'full': pin the element's effective tier on the lattice.
#   - 'ask':     always surface the element individually in the init dialogue.
# The shipped per-element default lives in each element's frontmatter `lane:`
# block; this override is absent by default — marshal.json carries only the
# project / meta overrides.
VALID_LANE_OVERRIDE = ('off', 'minimal', 'auto', 'full', 'ask')


def validate_lane_override(value: str, field_name: str = 'lane') -> None:
    """Validate a per-element lane override (``off|minimal|auto|full|ask``).

    Args:
        value: The candidate override value.
        field_name: The dotted ``plan.<phase>.steps.<step>.lane`` path, used in
            the error message so a rejected value names the offending element.

    Raises:
        ValueError: If ``value`` is not in :data:`VALID_LANE_OVERRIDE`.
    """
    if value not in VALID_LANE_OVERRIDE:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Allowed: {list(VALID_LANE_OVERRIDE)}"
        )


# Prune-predicate thresholds (`plan.phase-1-init.lane_prune_thresholds`) — the
# tunable numeric thresholds the `auto` posture evaluates its prunable-element
# predicates against at manifest-compose time. The predicate NAMES are owned by
# the central standard's Prune-predicates table; only the numeric predicates
# carry a threshold here (`no_code_delta` / `footprint_no_lesson_component` are
# boolean and carry none):
#   - 'confidence_complete': prune `refine` when the post-init confidence proxy
#                            is >= this value (int 0-100; default 95, matching the
#                            phase-2-refine confidence_threshold).
#   - 'linear_change_max_deliverables': treat the plan as a `linear_change`
#                            (pruning the 4-plan decomposition element) when the
#                            deliverable count is <= this value (int >= 1; default
#                            1 — a single deliverable with no fan-out).
DEFAULT_LANE_PRUNE_THRESHOLDS = {
    'confidence_complete': 95,
    'linear_change_max_deliverables': 1,
}


def validate_lane_prune_thresholds(value: object) -> None:
    """Validate the ``lane_prune_thresholds`` numeric-threshold mapping.

    The key set must be exactly ``{confidence_complete,
    linear_change_max_deliverables}``. ``confidence_complete`` is an int in
    ``[0, 100]``; ``linear_change_max_deliverables`` is an int ``>= 1``. Booleans
    are rejected even though ``bool`` is an ``int`` subclass.

    Args:
        value: The candidate threshold mapping.

    Raises:
        ValueError: If ``value`` is not a dict, if its key set is not exactly the
            expected set, or if any value is out of range.
    """
    expected = set(DEFAULT_LANE_PRUNE_THRESHOLDS.keys())
    if not isinstance(value, dict):
        raise ValueError(
            f"Invalid lane_prune_thresholds {value!r}: expected a dict with keys "
            f"{sorted(expected)}."
        )
    keys = set(value.keys())
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise ValueError(
            f"Invalid lane_prune_thresholds keys {sorted(keys)}: expected exactly "
            f"{sorted(expected)} (missing={missing}, extra={extra})."
        )
    confidence = value['confidence_complete']
    if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 100:
        raise ValueError(
            f"Invalid lane_prune_thresholds.confidence_complete {confidence!r}: "
            "expected an int in [0, 100]."
        )
    max_deliverables = value['linear_change_max_deliverables']
    if isinstance(max_deliverables, bool) or not isinstance(max_deliverables, int) or max_deliverables < 1:
        raise ValueError(
            f"Invalid lane_prune_thresholds.linear_change_max_deliverables "
            f"{max_deliverables!r}: expected an int >= 1."
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
    # Auto-continue from 1-init to 2-refine. true = no gate (current behaviour);
    # false = stop after init and wait for the user. Mirrors the sibling
    # plan_without_asking / execute_without_asking review-gate pattern.
    'init_without_asking': True,
    # Deep-lane gate_mode gate (auto|always|never). Consumed by the
    # phase-1-init planning-lane router (_cmd_planning_lane.py): `always` forces
    # the deep lane, `never` forces light, `auto` (default) defers to the S1-S6
    # signal set. Validated by validate_gate_mode at set-time. Read via
    # `manage-config plan phase-1-init get --field deep_lane`.
    'deep_lane': 'auto',
    # Hard-escalation safety-ratchet gate_mode gate (auto|always|never). `auto`
    # keeps the DQ3 explosion / build-break / premise escalation ratchet live;
    # `never` is the explicit full-speed-full-risk opt-in. Validated by
    # validate_gate_mode at set-time. Read via
    # `manage-config plan phase-1-init get --field escalation`.
    'escalation': 'auto',
    # Tier 1 recipe-match auto-route gate. true (the default) ⇒ a high-confidence
    # recipe match (top confidence >= auto_route_recipe_threshold) auto-routes to
    # the matched recipe without prompting; false ⇒ the orchestrator proposes the
    # ranked matches via AskUserQuestion first. Mirrors the sibling
    # init_without_asking boolean-knob pattern. Read via
    # `manage-config plan phase-1-init get --field auto_route_recipe`.
    'auto_route_recipe': True,
    # Tier 1 recipe-match auto-route confidence threshold. A top match at or above
    # this confidence is a high-confidence match the orchestrator may auto-route
    # (when auto_route_recipe is true). Default 0.6: free-form requests carry no
    # plan domain/scope, so keyword-overlap-only confidence caps at 0.6 — the
    # threshold the recipe-match verb's `--threshold` default and the aspect
    # classifier share. Read via
    # `manage-config plan phase-1-init get --field auto_route_recipe_threshold`.
    'auto_route_recipe_threshold': 0.6,
    # Execution-profile lane prompt gate (ask|auto). `ask` (default) surfaces the
    # minimal/auto/full posture dialogue at init; `auto` takes the computed `auto`
    # projection silently. Validated by validate_lane_selection. Read via
    # `manage-config plan phase-1-init get --field lane_selection`.
    'lane_selection': 'ask',
    # Tunable numeric thresholds the `auto` posture evaluates its prunable-element
    # predicates against at manifest-compose time (confidence_complete confidence
    # floor; linear_change deliverable-count ceiling). Validated by
    # validate_lane_prune_thresholds. Read via
    # `manage-config plan phase-1-init get --field lane_prune_thresholds`.
    'lane_prune_thresholds': DEFAULT_LANE_PRUNE_THRESHOLDS,
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
    # Premise / narrative-vs-code safety-check gate_mode gate
    # (auto|always|never). Consumed by the light lane + deep refine
    # revalidation pass. Validated by validate_gate_mode at set-time. Read via
    # `manage-config plan phase-2-refine get --field revalidation`.
    'revalidation': 'auto',
}

DEFAULT_PLAN_OUTLINE = {
    'plan_without_asking': False,
    # Planning-time q-gate validation knob (off|once|until_clean). Consumed by
    # the deep-lane outline dispatch to decide how q-gate validation loops over
    # the emerging outline. Validated by validate_q_gate_validation. Read via
    # `manage-config plan phase-3-outline get --field q_gate_validation`.
    'q_gate_validation': 'once',
    # Per-phase effort default (seeded at init; balanced-preset baseline lifts
    # outline analysis to level-4).
    'effort': 'level-4',
}

DEFAULT_PLAN_PLAN = {
    'execute_without_asking': True,
    # Planning-time q-gate validation knob (off|once|until_clean). Consumed by
    # phase-4-plan to decide how q-gate validation loops over the emerging task
    # plan. Validated by validate_q_gate_validation. Read via
    # `manage-config plan phase-4-plan get --field q_gate_validation`.
    'q_gate_validation': 'once',
    # Per-phase effort default (seeded at init; balanced-preset baseline).
    'effort': 'level-3',
}

# Canonical ``implements:`` value that identifies a built-in verify-step doc. The
# built-in verify-step universe is no longer a hand-maintained list of module
# constants: membership is DECLARED on the parameterized canonical-verify doc via
# this ext-point and DISCOVERED through the reusable
# ``extension_discovery.find_implementors`` query (the seed and the discovery
# surface both consume that single query and expand each implementor's
# ``canonicals`` list into ``default:verify:{canonical}`` step IDs in list order).
# The contract — addressing surface, the per-step frontmatter fields
# (``name`` / ``order`` / ``canonicals`` / ``description``), the canonicals→step-ID
# expansion, and the supporting-doc exclusion list — lives in the central standard:
#   marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-build-verify-step.md
# This constant is the discovery key only.
BUILD_VERIFY_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-build-verify-step'


def _verify_step_ids() -> list[str]:
    """Enumerate the built-in verify-step IDs via extension discovery.

    Discovers every ``ext-point-build-verify-step`` implementor via the reusable
    ``extension_discovery.find_implementors`` query (the SOLE discovery path —
    there is no parallel constant list), filters to the built-in source, sorts
    by ``order``, and expands each implementor's ``canonicals`` list into the
    ordered step-ID set ``default:verify:{canonical}`` (list order is execution
    order). This is the single source of the built-in verify-step universe.

    The cross-bundle ``extension_discovery`` module is imported lazily (not at
    module top level) so importing ``_config_defaults`` never pulls in the
    extension-api parser — the IDs are only materialized when a seed runs.

    Returns:
        The ordered list of ``default:verify:{canonical}`` step IDs.
    """
    # Lazy import — executor sets PYTHONPATH for cross-skill imports.
    from extension_discovery import find_implementors

    implementors = sorted(
        (rec for rec in find_implementors(BUILD_VERIFY_STEP_EXT_POINT) if rec.get('source') == 'built-in'),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [
        f'{_VERIFY_STEP_PREFIX}{canonical}'
        for rec in implementors
        for canonical in rec.get('canonicals', [])
    ]


def _seed_verify_steps() -> dict:
    """Build the verify-step defaults seed in the canonical keyed-map form.

    Expands the discovered built-in verify-step IDs (see :func:`_verify_step_ids`)
    into the id-keyed map ``{step_id: {}}`` — the sole on-disk shape both read and
    written. Verification steps own no params, so every value is the empty object
    ``{}`` (config-less); key insertion order is the execution order.

    Returns:
        The keyed-map serial form: an id-keyed dict mapping each built-in
        verify-step ID to an empty param object, in execution order.
    """
    return {step_id: {} for step_id in _verify_step_ids()}


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


# The exact key set the cost_size_token_table must carry — the six T-shirt
# sizes the cost-sizing rubric (phase-4-plan/standards/cost-sizing.md) maps a
# task or lane-element to. The table value for each size is a human-friendly
# magnitude string (e.g. "25K") parsed back to an int via
# sensible_number.parse_sensible_int. XS and XXL widen the original S/M/L/XL
# scale at both ends (XS for deterministic ≈0-token bookkeeping; XXL for the
# heaviest elements); the four original magnitudes are unchanged so the
# manage-tasks derive-cost-size deriver and bin-packer are unaffected.
COST_SIZE_LABELS = ('XS', 'S', 'M', 'L', 'XL', 'XXL')


def validate_cost_size_token_table(value: object) -> None:
    """Validate the ``cost_size_token_table`` size→token mapping.

    ``cost_size_token_table`` maps each T-shirt size in
    :data:`COST_SIZE_LABELS` (``XS``/``S``/``M``/``L``/``XL``/``XXL``) to a
    predicted-token magnitude. The keys must be exactly that set (no missing, no
    extra), and every value must parse as a human-friendly sensible int
    (``"25K"`` → 25000) via :func:`sensible_number.parse_sensible_int`. The
    phase-4-plan bin-packer reads this table to map a task's derived
    ``cost_size`` to its ``predicted_cost_tokens``.

    Raises:
        ValueError: If ``value`` is not a dict, if its key set is not exactly
            ``{XS, S, M, L, XL, XXL}``, or if any value does not parse as a
            sensible int.
    """
    from sensible_number import parse_sensible_int

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
    # phase-6 push, pre-push-quality-gate, and pre-submission-self-review steps
    # are stripped by the manage-execution-manifest commit_push_disabled
    # pre-filter.
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
    # Size→token table mapping each T-shirt cost_size (XS/S/M/L/XL/XXL) to a
    # predicted token magnitude. Validated by validate_cost_size_token_table
    # (keys exactly XS/S/M/L/XL/XXL; every value parses via
    # sensible_number.parse_sensible_int). The phase-4-plan bin-packer
    # (_tasks_envelope.py, via manage-tasks pack-envelopes) reads this table at
    # PLAN time to map a task's derived cost_size to its predicted_cost_tokens.
    # The four original magnitudes (S≈25K / M≈60K / L≈130K / XL≈260K) are
    # unchanged and calibrated to the forensic 134K-392K per-dispatch range; XS≈5K
    # labels deterministic ≈0-token bookkeeping and XXL≈520K the heaviest elements
    # (lane-elements, execute on a substantial plan). These are the tunable
    # defaults; raise/lower them in marshal.json to recalibrate the size model
    # from observed post-return <usage>.
    'cost_size_token_table': {'XS': '5K', 'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K', 'XXL': '520K'},
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
    # Verification steps as the canonical keyed-map form: an id-keyed object
    # `{step_id: {params}}` whose key insertion order is the execution order.
    # Verification steps own no params, so every built-in verify step seeds with
    # an empty `{}` param object (config-less). The reader
    # (`_steps_map` / `_read_marshal_phase_step_map`) consumes this keyed map
    # directly — it is the sole on-disk shape both read and written.
    #
    # Seeded lazily by `_seed_verify_steps()` inside `get_default_config()` (the
    # discovery query cannot run at module import without a hard cross-bundle
    # dependency on the extension-api parser); this literal `None` placeholder is
    # replaced there. Mirrors the `DEFAULT_PLAN_FINALIZE['steps']` lazy-seed shape.
    'verification_steps': None,
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

# Canonical ``implements:`` value that identifies a finalize-step doc. The
# finalize-step registry is no longer a hand-maintained set of module constants:
# membership is DECLARED on each step doc via this ext-point and DISCOVERED
# through the reusable ``extension_discovery.find_implementors`` query (the seed,
# the discovery surface, and the preset builder all consume that single query).
# The contract — addressing surface, the per-step frontmatter fields
# (``name`` / ``order`` / ``default_on`` / ``presets`` / ``description``), and the
# supporting-doc exclusion list — lives in the central standard:
#   marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md
# This constant is the discovery key only.
FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

# The two adversarial infra-dependent finalize elements that seed with a
# `lane: ask` override. Their on/off/tier is answered by the operator at
# marshall-steward setup / update-config (which persists a resolved
# `off`/`auto`/`full`), and an UNRESOLVED `ask` (operator never answered) whose
# provider is absent is dropped at compose time by the drop-when-no-provider
# safety net. `ask` is seeded here rather than in each step's `configurable:`
# frontmatter because it is a project-provisioning posture, not a step param the
# step body reads.
_LANE_ASK_INFRA_STEPS = ('plan-marshall:automatic-review', 'default:sonar-roundtrip')

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
#   - plan-marshall:automatic-review      → review_bot_buffer_seconds,
#                                      review_completion_poll_timeout_seconds
#   - default:branch-cleanup        → pr_merge_strategy, final_merge_without_asking,
#                                      auto_rebase_threshold,
#                                      merge_queue_wait_budget_seconds,
#                                      pre_merge_comment_barrier,
#                                      admin_merge_on_stuck_state
#   - default:finalize-step-simplify → (config-less; the retired `simplify`
#                                      run-at-all param is gone — the step's
#                                      on/off is governed by its
#                                      `steps.<step>.lane` override)
#   - default:finalize-step-preference-emitter → preference_min_recurrence
#                                      (per-plan disposition recurrence threshold)
#   - default:pre-submission-self-review → drop_review_on_scope_gate (a default-on
#                                      built-in step, so the seed DOES include it
#                                      and its param — false — directly; the
#                                      retired `self_review` run-at-all param is
#                                      gone, replaced by the step's
#                                      `steps.<step>.lane` override)
# The four finalize ceremony gates (qgate, self_review, simplify, security_audit)
# no longer ride a run-at-all param: each is governed by its owning step's
# `steps.<step>.lane` override (`off`/`minimal`/`auto`). Phase-level knobs with no
# single owning step (checks_wait_timeout_seconds, max_iterations,
# finalize_without_asking, loop_back_without_asking, effort, …) stay flat siblings
# of `steps`.


def _seed_finalize_steps() -> dict:
    """Build the finalize-step defaults seed in the canonical keyed-map form.

    Discovers every finalize-step implementor via the reusable
    ``extension_discovery.find_implementors`` query (the SOLE discovery path —
    there is no parallel constant list), materializes EVERY built-in implementor
    (there is no ``default_on == true`` filter — exclusion is now expressed as a
    ``lane: off`` override, never as absence), sorts by ``order``, and delegates
    each step id to ``configurable_contract.resolve_step_defaults_optional``. A
    param-owning step resolves to its ``{param_key: default}`` object; an
    ownerless step resolves to ``None`` (no params), which is normalized to an
    empty ``{}`` object (config-less). The result is the id-keyed map
    ``{step_id: param-object}`` — the sole on-disk shape both read and written —
    with key insertion order as the execution order.

    Per-element ``lane`` overrides are folded into each step's param object:

    - The two adversarial infra elements (:data:`_LANE_ASK_INFRA_STEPS` —
      ``plan-marshall:automatic-review`` and ``default:sonar-roundtrip``) seed a
      ``lane: ask`` override so marshall-steward always prompts about them and a
      genuinely-unresolved ask with no provider is dropped at compose.
    - Every ``default_on: false`` step seeds a ``lane: off`` override so its
      exclusion is expressed as ``lane: off`` rather than absence from the seed.
    - Every ``default_on: true`` non-infra step carries no ``lane`` key (absent
      override resolves to the ``auto`` posture).

    The cross-bundle modules are imported lazily here (not at module top level) so
    importing ``_config_defaults`` never pulls in the extension-api parser — the
    seed is only materialized when :func:`get_default_config` runs.

    Returns:
        The keyed-map serial form: an id-keyed dict mapping each step id to its
        ``{param_key: default}`` object (``{}`` for config-less steps), with a
        folded-in ``lane`` override for the infra (``ask``) and ``default_on:
        false`` (``off``) steps, in execution order.
    """
    # Lazy imports — executor sets PYTHONPATH for cross-skill imports.
    from configurable_contract import (
        resolve_step_defaults_optional,
    )
    from extension_discovery import find_implementors

    implementors = find_implementors(FINALIZE_STEP_EXT_POINT)
    seed_records = sorted(
        (rec for rec in implementors if rec.get('source') == 'built-in'),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    seed: dict = {}
    for rec in seed_records:
        name = rec['name']
        params = dict(resolve_step_defaults_optional(name) or {})
        if name in _LANE_ASK_INFRA_STEPS:
            params['lane'] = 'ask'
        elif not rec.get('default_on'):
            params['lane'] = 'off'
        seed[name] = params
    return seed


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
    # The finalize `qgate` gate no longer lives here as a flat run-at-all sibling.
    # Finalize-qgate now rides `steps['pre-push-quality-gate'].lane` — the same
    # per-element `lane` override channel the other three ceremony gates
    # (`self_review`, `simplify`, `security_audit`) use — resolved by the
    # manifest ceremony transform (`off→never`, `minimal→always`, `auto/absent→auto`).
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
    # Finalize steps as the canonical keyed-map form: an id-keyed object
    # `{step_id: {params}}` whose key insertion order is the execution order. A
    # config-less (ownerless) step carries an empty `{}` param object.
    # Step-owned params (sonar params under `default:sonar-roundtrip`;
    # `review_bot_buffer_seconds` under `plan-marshall:automatic-review`;
    # `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold`
    # under `default:branch-cleanup`) live in the owning step's nested param
    # object. Each step's params are declared self-describingly in the step's
    # body-doc `configurable:` frontmatter and read by `configurable_contract.py`.
    # The four finalize ceremony gates (`qgate`, `self_review`, `simplify`,
    # `security_audit`) no longer ride a run-at-all param — each is governed by
    # its owning step's `steps.<step>.lane` override. `default:finalize-step-simplify`
    # and `default:finalize-step-security-audit` are now config-less; the
    # `default:pre-submission-self-review` step retains only its
    # `drop_review_on_scope_gate: false` param. ALL finalize-step implementors are
    # materialized into this map (exclusion is a `lane: off` override, never
    # absence); the two adversarial infra elements
    # (`plan-marshall:automatic-review`, `default:sonar-roundtrip`) seed a
    # `lane: ask` override. The reader
    # (`_steps_map` / `_read_marshal_phase_step_map`) consumes this keyed map
    # directly — it is the sole on-disk shape both read and written.
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
    # Self-validate the seeded project PR-batching knobs so a malformed default
    # fails loud at seed time rather than at first read.
    validate_pr_strategy(DEFAULT_PROJECT['pr_strategy'])
    validate_pr_compact_max_changed_files(DEFAULT_PROJECT['pr_compact_max_changed_files'])
    # Self-validate the seeded lane prune-threshold dict so a malformed default
    # fails loud at seed time rather than at first read. (`lane_selection` is an
    # enum string validated from the set path, mirroring validate_gate_mode /
    # validate_simplicity — not self-validated here.)
    validate_lane_prune_thresholds(DEFAULT_PLAN_INIT['lane_prune_thresholds'])
    # Materialize the finalize-step defaults seed lazily via the configurable-
    # contract parser (the `'steps': None` placeholder in DEFAULT_PLAN_FINALIZE is
    # replaced here). Done after the deepcopy below so the module-level constant
    # stays free of the cross-bundle parser dependency at import time.
    finalize_section = copy.deepcopy(DEFAULT_PLAN_FINALIZE)
    finalize_section['steps'] = _seed_finalize_steps()
    # Materialize the verify-step defaults seed lazily via the extension-discovery
    # query (the `'verification_steps': None` placeholder in DEFAULT_PLAN_EXECUTE is
    # replaced here). Done after the deepcopy below so the module-level constant
    # stays free of the cross-bundle parser dependency at import time.
    execute_section = copy.deepcopy(DEFAULT_PLAN_EXECUTE)
    execute_section['verification_steps'] = _seed_verify_steps()
    config = {
        'providers': [],
        'project': copy.deepcopy(DEFAULT_PROJECT),
        'skill_domains': {'system': system_domain},
        'build': {
            'queue': copy.deepcopy(DEFAULT_BUILD_QUEUE),
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
            # Per-field byte cap for quarantined raw_input free-text in the
            # findings ledger (64 KiB; `[truncated]` marker on overflow).
            'finding_raw_input_max_bytes': DEFAULT_FINDING_RAW_INPUT_MAX_BYTES,
            'phase-1-init': copy.deepcopy(DEFAULT_PLAN_INIT),
            'phase-2-refine': copy.deepcopy(DEFAULT_PLAN_REFINE),
            'phase-3-outline': copy.deepcopy(DEFAULT_PLAN_OUTLINE),
            'phase-4-plan': copy.deepcopy(DEFAULT_PLAN_PLAN),
            'phase-5-execute': execute_section,
            'phase-6-finalize': finalize_section,
        },
    }
    return config


def compute_config_seed_fingerprint() -> str:
    """Machine-portable fingerprint of the default config seed.

    Hashes the canonical JSON (``json.dumps(..., sort_keys=True)``) of
    :func:`get_default_config`. This is the SAME hash the target generator
    (``marketplace/targets/generate.py``) stamps as ``config_seed_fingerprint``
    in ``dist-manifest.json``, so the staleness check can compare the config a
    project was provisioned at against the currently-published default seed.

    The stamped ``system.provisioned_version`` / ``system.config_seed_fingerprint``
    fields are runtime-only — written into ``marshal.json`` by init / sync-defaults
    and deliberately NOT part of :func:`get_default_config`. The fingerprint is
    therefore stable under its own stamping: re-hashing after a project has been
    stamped yields the same value, so the config never appears to drift merely
    because it was fingerprinted.

    Returns:
        8-char hex fingerprint of the canonical default-config JSON (same width
        as the executor script-set fingerprint).
    """
    canonical = json.dumps(get_default_config(), sort_keys=True)
    return hashlib.md5(canonical.encode('utf-8'), usedforsecurity=False).hexdigest()[:8]


def read_provisioned_version() -> str:
    """Read the installed ``MARSHALL_VERSION`` to stamp as ``system.provisioned_version``.

    The version a project is provisioned at is the generated executor's embedded
    ``MARSHALL_VERSION`` (itself stamped from the installed ``dist-manifest.json``
    at generation time). Reads it from the tracked executor at
    ``.plan/execute-script.py``. Returns the empty string when the executor is
    absent or unstamped (fresh install) — an empty stamp, never an error.

    Returns:
        The embedded version string, or ``''`` on a fresh/unstamped install.
    """
    import re

    from file_ops import get_tracked_config_dir

    executor = get_tracked_config_dir() / 'execute-script.py'
    try:
        text = executor.read_text(encoding='utf-8')
    except (OSError, ValueError):
        return ''
    match = re.search(r"^MARSHALL_VERSION\s*=\s*'([^']*)'", text, re.MULTILINE)
    if match:
        return match.group(1)
    return ''


def stamp_provisioning_fields(config: dict) -> None:
    """Stamp ``system.provisioned_version`` / ``system.config_seed_fingerprint`` in place.

    Writes (or refreshes) the two runtime provisioning stamps into
    ``config['system']``, creating the ``system`` block if absent. Shared by the
    init seed path (:func:`_cmd_init.cmd_init`) and the sync-defaults reconcile
    path (:func:`_cmd_sync_defaults.cmd_sync_defaults`) so both stamp identically.

    The stamps are runtime-only and NOT part of :func:`get_default_config`, so
    stamping never perturbs :func:`compute_config_seed_fingerprint`.

    The ``provisioned_version`` stamp is **non-destructive on an empty read**:
    when :func:`read_provisioned_version` returns ``''`` (an unstamped or absent
    executor), any pre-existing ``system['provisioned_version']`` is left intact
    rather than blanked to the empty sentinel — a known-good version is never
    lost merely because the executor could not be read this run. A real,
    non-empty version still advances the stamp. The ``config_seed_fingerprint``
    stamp is unconditional.

    Args:
        config: The marshal.json config dict to stamp (mutated in place).
    """
    system = config.get('system')
    if not isinstance(system, dict):
        system = {}
        config['system'] = system
    provisioned_version = read_provisioned_version()
    if provisioned_version or 'provisioned_version' not in system:
        system['provisioned_version'] = provisioned_version
    # An empty read (unstamped/absent executor) preserves any existing stamp
    # instead of blanking a known-good provisioned_version.
    system['config_seed_fingerprint'] = compute_config_seed_fingerprint()
