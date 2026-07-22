#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Manage the per-plan execution manifest (compose, read, validate).

The manifest is the single source of truth for which Phase 5 verification
steps and Phase 6 finalize steps fire for a given plan. Phases 5 and 6 read
the manifest and dispatch — they no longer carry per-doc skip logic.

Storage: TOON format at .plan/local/plans/{plan_id}/execution.toon
Output: TOON format for API responses

Usage:
    python3 manage-execution-manifest.py compose --plan-id EXAMPLE-PLAN \\
        --change-type bug_fix --track simple --scope-estimate surgical
    python3 manage-execution-manifest.py read --plan-id EXAMPLE-PLAN
    python3 manage-execution-manifest.py validate --plan-id EXAMPLE-PLAN
"""

import argparse
import functools
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Imported as a MODULE (not `from … import`) so the domain-seeded resolvability
# filter and the resolution gate's `_verify_canonicals_universe` both resolve
# `_domain_appended_canonicals` through the SAME module attribute at call time —
# a single test patch of `_manifest_validation._domain_appended_canonicals` keeps
# the filter's domain-seeded membership check and the resolution gate's universe
# in lock-step.
import _manifest_validation
from _manifest_core import (
    _CANONICAL_TO_ROLE,  # noqa: F401
    _CANONICAL_VERIFY_PREFIX,  # noqa: F401
    _DOC_SUFFIXES,  # noqa: F401
    DEFAULT_ENVELOPE_COUNT,  # noqa: F401
    DEFAULT_PHASE_5_STEPS,  # noqa: F401
    DEFAULT_PHASE_6_STEPS,  # noqa: F401
    EXECUTION_LOG_KEY,  # noqa: F401
    MANIFEST_FILENAME,  # noqa: F401
    MANIFEST_VERSION,  # noqa: F401
    VALID_CHANGE_TYPES,  # noqa: F401
    VALID_RECORD_OUTCOMES,  # noqa: F401
    VALID_RECORD_PHASES,  # noqa: F401
    VALID_SCOPE_ESTIMATES,  # noqa: F401
    VALID_TRACKS,  # noqa: F401
    _denormalize_step_params_for_write,  # noqa: F401
    _is_documentation_path,  # noqa: F401
    _normalize_step_params_block,  # noqa: F401
    _role_of,  # noqa: F401
    get_manifest_path,  # noqa: F401
    read_manifest,  # noqa: F401
    write_manifest,  # noqa: F401
)
from _manifest_decide import (
    _decide,  # noqa: F401
    _read_recipe_source,  # noqa: F401
    _read_task_queue_active,  # noqa: F401
    _split_csv,  # noqa: F401
)
from _manifest_lanes import (
    _CLASS_DEFAULT_TIER,  # noqa: F401
    _DEFAULT_COST_SIZE_TABLE,  # noqa: F401
    _IMMUNE_TO_OFF_CLASSES,  # noqa: F401
    _TIER_RANK,  # noqa: F401
    DEFAULT_EXECUTION_PROFILE,  # noqa: F401
    LANE_OVERRIDES,  # noqa: F401
    LANE_TIERS,  # noqa: F401
    _effective_lane_tier,  # noqa: F401
    _lane_keep_decision,  # noqa: F401
    _lane_override_for,  # noqa: F401
    _parse_cost_magnitude,  # noqa: F401
    _read_cost_size_token_table,  # noqa: F401
    _read_execution_profile,  # noqa: F401
    _read_frontmatter_lane,  # noqa: F401
)
from _manifest_rules import (
    _CEREMONY_FINALIZE_DEFAULT,  # noqa: F401
    _CEREMONY_FINALIZE_GATES,  # noqa: F401
    _CEREMONY_FINALIZE_STEP_MAP,  # noqa: F401
    _FOOTPRINT_GATED_CANONICAL_ROLES,  # noqa: F401
    _PRE_SUBMISSION_SELF_REVIEW_STEP,  # noqa: F401
    _SCOPE_GATED_OVERRIDE_DROP,  # noqa: F401
    _SCOPE_GATED_SINGLE_MODULE_DROP,  # noqa: F401
    _SCOPE_GATED_SURGICAL_DROP,  # noqa: F401
    _SECURITY_AUDIT_OWNER_STEP,  # noqa: F401
    _SIMPLIFY_CHANGE_TYPES,  # noqa: F401
    _SIMPLIFY_OWNER_STEP,  # noqa: F401
    _VERB_TO_PHASE_5_STEP,  # noqa: F401
    _apply_ceremony_finalize_selection,  # noqa: F401
    _apply_code_step_inactive,  # noqa: F401
    _apply_commit_push_disabled,  # noqa: F401
    _apply_scope_gated_finalize,  # noqa: F401
    _apply_security_audit_inactive,  # noqa: F401
    _apply_simplify_inactive,  # noqa: F401
    _apply_unresolved_ask_provider_drop,  # noqa: F401
    _ceremony_finalize_insert_index,  # noqa: F401
    _footprint_has_role,  # noqa: F401
    _parse_verification_command,  # noqa: F401
    _read_ci_provider,  # noqa: F401
    _read_drop_review_on_scope_gate,  # noqa: F401
    _read_finalize_gates,  # noqa: F401
    _read_marshal_phase_step_map,  # noqa: F401
    _read_sonar_provider,  # noqa: F401
    _read_step_owned_knob,  # noqa: F401
    _snapshot_step_params,  # noqa: F401
    _verb_to_phase_5_step,  # noqa: F401
)
from _manifest_validation import (
    _PHASE_6_SKILL_DIR,  # noqa: F401
    _PHASE_6_STANDARDS_DIR,  # noqa: F401
    _PHASE_6_WORKFLOW_DIR,  # noqa: F401
    _PHASE_TO_BODY_SECTION,  # noqa: F401
    _REPO_ROOT,  # noqa: F401
    _check_ascending_order,  # noqa: F401
    _check_step_loadable,  # noqa: F401
    _check_step_resolvable,  # noqa: F401
    _coerce_param_value,  # noqa: F401
    _is_external_step,  # noqa: F401
    _read_frontmatter_order,  # noqa: F401
    _render_standards_rel_path,  # noqa: F401
    _resolve_standards_path,  # noqa: F401
    _resolve_step_order,  # noqa: F401
    _sort_steps_by_frontmatter_order,  # noqa: F401
    check_build_verdict_consistent,
    check_emitted_steps_canonical,
    check_emitted_steps_resolvable,  # noqa: F401
    cmd_step_params_get,  # noqa: F401
    cmd_step_params_set,  # noqa: F401
    cmd_validate,  # noqa: F401
)
from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
)
from _step_key_canonical import canonicalize_step_key
from constants import FILE_REFERENCES, FILE_STATUS
from file_ops import (
    get_executor_path,
    get_marshal_path,
    get_plan_dir,
    output_toon,
    output_toon_error,
    read_json,
    safe_main,
)
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from marketplace_paths import (
    resolve_project_skill_path,
)
from toon_parser import parse_toon

# =============================================================================
# Decision Engine (six-row matrix from standards/decision-rules.md)
# =============================================================================


def _classify_paths_via_extensions(
    paths: list[str],
    plan_id: str | None = None,
    extensions: list[Any] | None = None,
) -> tuple[str, list[str]]:
    """Classify a path list into a plan-wide change-footprint bucket.

    Two-stage classifier:

    1. **Generic documentation recognition (extension-agnostic).** Any path
       ending in a :data:`_DOC_SUFFIXES` suffix (``.md`` / ``.adoc`` /
       ``.asciidoc``) is tagged with the ``documentation`` footprint role
       directly, BEFORE and independent of the build-extension iteration.
       Documentation has no build-system owner — it is not a buildable unit and
       not a build_map route role — so doc recognition is a pure file-suffix fact
       owned here, not a build-extension claim. Documentation paths are removed
       from the set handed to the build extensions, so a build extension never
       claims (or contests) a doc path and a doc path is never tagged
       ``unknown``.

    2. **Build-extension recognition (production / test / config).** The
       remaining non-doc paths flow to every discovered build extension (Axis-B:
       ``build-pyproject`` / ``build-maven`` / ``build-gradle`` / ``build-npm``)
       via ``classify_paths()``. Multi-extension overlap is resolved by
       longest-glob-wins (highest ``classify_path_specificity`` wins; alphabetical
       domain-key tie-break). Non-doc paths no build extension claims are tagged
       ``unknown`` and emit a ``[STATUS]`` decision-log warning.

    The per-path roles (the generic ``documentation`` tags plus the build
    extensions' production / test / config claims) are then collapsed into one of
    six plan-wide bucket values.

    File classification for production / test / config flows from the
    build-system-owned ``BuildExtensionBase`` subclasses, NOT the language domain
    extensions — the latter own Axis-A (skill-loading) only and expose no
    ``classify_paths``. Documentation recognition flows from neither: it is the
    generic suffix rule above.

    Args:
        paths: Plan-wide union of every deliverable's ``affected_files``.
        plan_id: When supplied AND at least one path is unclaimed, the
            aggregator emits a ``[STATUS]`` warning naming each unclaimed
            path under this plan id. Omit during unit tests.
        extensions: Optional pre-resolved list of build-extension instances. When
            ``None`` the aggregator calls
            :func:`extension_discovery.discover_build_extensions` and uses
            every loaded build-extension module. The override is intended for the
            fake-extension test fixture in
            ``test/plan-marshall/manage-execution-manifest/_fixtures.py``.

    Returns:
        A 2-tuple ``(bucket, unclaimed_paths)`` where ``bucket`` is one of
        the six plan-wide vocabulary values
        (``production_only`` / ``test_only`` / ``documentation_only`` /
        ``mixed_code`` / ``mixed_with_docs`` / ``unknown``) and
        ``unclaimed_paths`` is the list of paths no extension claimed (empty
        when bucket is anything other than ``unknown``).

    The aggregator returns ``documentation_only`` for an empty path list as
    the conservative default (no affected files means no holistic Python
    verification is needed).

    See ``manage-execution-manifest/standards/decision-rules.md`` §
    "Overlap resolution policy" and § "Unclaimed paths" for the full
    contract documentation. See
    ``extension-api/standards/extension-contract.md`` § classify_paths()
    for the per-extension contract.
    """
    if not paths:
        return 'documentation_only', []

    # Stage 1 — generic, extension-agnostic documentation recognition. Any path
    # ending in a documentation suffix is the ``documentation`` footprint role,
    # owned by nobody (no build owner for docs). These paths are split out so the
    # build extensions never see them: a doc path is never claimed/contested by
    # an extension and never tagged ``unknown``.
    per_path_role: dict[str, str] = {}
    code_paths: list[str] = []
    for path in paths:
        if _is_documentation_path(path):
            per_path_role[path] = 'documentation'
        else:
            code_paths.append(path)

    # Resolve the active extension set. The lazy import avoids a circular
    # dependency on extension_discovery during module import; the test
    # fixture passes ``extensions`` explicitly so we never hit this branch
    # during unit tests.
    if extensions is None:
        try:
            from extension_discovery import discover_build_extensions
        except ImportError:
            extensions = []
        else:
            discovered = discover_build_extensions()
            extensions = [ext.get('module') for ext in discovered if ext.get('module') is not None]

    # Stage 2 — build-extension recognition over the non-doc paths only. Collect
    # per-extension claims. Each entry is (extension_instance, domain_key, role,
    # path).
    Claim = tuple[Any, str, str, str]
    raw_claims: list[Claim] = []
    for ext in extensions:
        try:
            claims = ext.classify_paths(list(code_paths))
            domain_key = _safe_domain_key(ext)
            for role, claimed_paths in claims.items():
                for path in claimed_paths:
                    raw_claims.append((ext, domain_key, role, path))
        except Exception:
            continue

    # Resolve overlaps per-path: highest specificity wins; alphabetical
    # tie-break on domain_key.
    claims_by_path: dict[str, list[Claim]] = {}
    for claim in raw_claims:
        claims_by_path.setdefault(claim[3], []).append(claim)
    for path, path_claims in claims_by_path.items():
        scored: list[tuple[int, str, str]] = []
        for ext, domain_key, role, _ in path_claims:
            try:
                specificity = int(ext.classify_path_specificity(path, role))
            except Exception:
                specificity = 0
            scored.append((specificity, domain_key, role))
        # Sort by (-specificity, domain_key) — higher specificity first,
        # alphabetical tie-break.
        scored.sort(key=lambda item: (-item[0], item[1]))
        per_path_role[path] = scored[0][2]

    # Identify unclaimed paths (non-doc paths no build extension claimed) and
    # emit a warning when the caller passed plan_id.
    unclaimed = [p for p in code_paths if p not in per_path_role]
    if unclaimed:
        if plan_id:
            _emit_decision_log(
                plan_id,
                f'(plan-marshall:manage-execution-manifest:classify) '
                f'[STATUS] Unclaimed paths tagged unknown: {unclaimed}',
            )
        return 'unknown', unclaimed

    # Collapse per-path roles into the six-bucket plan-wide vocabulary.
    # config role does NOT influence the plan-wide bucket — config changes
    # ride with whatever production/test/docs surface they accompany.
    roles_present = {role for role in per_path_role.values() if role != 'config'}
    has_prod = 'production' in roles_present
    has_test = 'test' in roles_present
    has_docs = 'documentation' in roles_present

    if has_docs and (has_prod or has_test):
        return 'mixed_with_docs', []
    if has_prod and has_test:
        return 'mixed_code', []
    if has_prod:
        return 'production_only', []
    if has_test:
        return 'test_only', []
    if has_docs:
        return 'documentation_only', []
    # Only config claims (no production/test/docs) — treat as documentation_only
    # under the conservative default (config-only changes do not warrant
    # holistic Python verification).
    return 'documentation_only', []


def _safe_domain_key(ext: Any) -> str:
    """Return the extension's first domain key, or empty string on failure.

    Used as the alphabetical tie-breaker in overlap resolution. Failure to
    resolve the key produces an empty string so the tie-break degrades
    gracefully.
    """
    try:
        domains = ext.get_skill_domains()
        if domains:
            return str(domains[0].get('domain', {}).get('key', '') or '')
    except Exception:
        pass
    return ''


# =============================================================================
# Decision Logging
# =============================================================================


def _resolve_executor() -> Path | None:
    """Locate ``.plan/execute-script.py`` via the canonical cwd-relative resolver.

    Delegates to ``file_ops.get_executor_path`` (the ADR-002 uniform cwd rule:
    the executor lives under the ``.plan`` dir of whichever checkout the working
    directory is in) instead of walking up from ``__file__``. The composer is
    dispatched from the deployed-bundle cache, which lives OUTSIDE the project
    tree, so a ``__file__`` walk never found the
    executor — silently breaking the ``execution_tier`` routing that
    subprocesses ``architecture resolve`` through it. Returns ``None`` when the
    plan root is unresolvable or the executor file is absent (e.g. an exotic
    test fixture), which the caller treats as "non-build / unroutable".
    """
    try:
        executor = get_executor_path()
    except RuntimeError:
        return None
    return executor if executor.is_file() else None


def _emit_decision_log(plan_id: str, message: str) -> None:
    """Best-effort decision-log emission via a direct in-process write.

    Logging is non-load-bearing — manifest content is the contract — so any
    import or write error is swallowed silently.

    The entry is written through ``plan_logging.log_entry`` directly rather than
    shelling back out to ``.plan/execute-script.py``. The composer is dispatched
    from the deployed-bundle cache, which lives outside
    the project tree, so the former ``_resolve_executor`` walk up from
    ``__file__`` never resolved the executor and silently dropped every compose
    decision-log line — the ``unloggable`` regression the archived-plan audit
    surfaced. The direct write resolves the plan dir via the same
    ``file_ops.get_base_dir()`` the manifest write uses, so the line always
    lands in the plan's own ``logs/decision.log`` alongside ``execution.toon``.
    ``plan_logging`` is on ``PYTHONPATH`` (the executor injects every skill's
    scripts dir; the test conftest does the same).
    """
    try:
        from plan_logging import log_entry

        log_entry('decision', plan_id, 'INFO', message)
    except Exception:
        return


def _log_decision(plan_id: str, rule: str, body: dict[str, Any]) -> None:
    """Emit one ``decision.log`` entry for the rule that fired.

    The composer must produce one entry per applied rule per plan run, per the
    request example. We invoke ``manage-logging decision`` via the executor so
    the entry lands in the canonical decision log location.
    """
    phase_5 = body.get('phase_5', {})
    phase_6 = body.get('phase_6', {})
    p5_steps = phase_5.get('verification_steps', [])
    p6_steps = phase_6.get('steps', [])
    early = phase_5.get('early_terminate', False)
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
        f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
        f'phase_6.steps={p6_steps}'
    )
    _emit_decision_log(plan_id, message)


def _log_commit_push_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``commit_push_disabled`` pre-filter."""
    message = '(plan-marshall:manage-execution-manifest:compose) push omitted — commit_and_push=false'
    _emit_decision_log(plan_id, message)


def _log_candidate_source(plan_id: str, phase_key: str, source: str) -> None:
    """Emit a decision-log entry naming which input source produced the candidate list.

    ``source`` is either ``'marshal.json'`` (preferred path — full prefixes
    preserved) or ``'csv_fallback'`` (no marshal.json available; the
    composer fell back to the ``--phase-{5,6}-steps`` CSV).
    """
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) {phase_key} candidate source: {source}'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_push_quality_gate_omitted(plan_id: str, reason: str) -> None:
    """Emit the decision-log entry for the ``pre_push_quality_gate_inactive`` pre-filter.

    ``reason`` is the verdict's OWN ``reason`` text, threaded through from the
    ``build-decision`` consult. The emitter never composes a reason of its own —
    a hardcoded string can state a reason the verdict did not give.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — '
        f'{reason}'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_submission_self_review_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``pre_submission_self_review_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-submission-self-review omitted — empty footprint'
    )
    _emit_decision_log(plan_id, message)


def _log_prefilter_omitted(
    plan_id: str, step_name: str, change_type: str, affected_files_count: int
) -> None:
    """Emit the decision-log entry for an ``*_inactive`` pre-filter (simplify or security_audit)."""
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) {step_name} omitted — '
        f'change_type={change_type} affected_files_count={affected_files_count}'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# Pre-Filter Helpers
# =============================================================================


def _read_marshal_phase_steps(phase_key: str) -> list[str] | None:
    """Read the ordered step-id list for ``phase_key`` from marshal.json.

    Reads the normalized step map (see :func:`_read_marshal_phase_step_map`,
    which reads the canonical keyed-map on-disk form) and returns
    ``list(map.keys())`` preserving insertion order (= execution order), or
    ``None`` when the map is absent / malformed.

    The composer prefers this source over the agent-supplied
    ``--phase-{5,6}-steps`` CSV because marshal.json is the authoritative
    project-level declaration: it preserves ``default:`` / ``project:`` /
    ``bundle:skill`` prefixes that agent-built CSVs have historically
    stripped, producing manifests with bare names the dispatcher then mis-
    routed as built-in steps.
    """
    step_map = _read_marshal_phase_step_map(phase_key)
    if step_map is None:
        return None
    return list(step_map.keys())


def _resolve_footprint(plan_id: str) -> list[str]:
    """Derive the live plan footprint for ``plan_id`` on demand.

    Reads ``status.metadata.worktree_path`` to locate the worktree, then derives
    the footprint live via ``compute_plan_branch_diff`` (``{base}...HEAD`` ∪
    porcelain). Returns an empty list when no worktree is resolvable — which is
    the normal case during early compose at phase-4-plan, *before* phase-5
    materialises the worktree. The activation pre-filters treat an empty
    footprint as "no matches" and omit the gated step, preserving the prior
    behaviour where an absent/empty ledger omitted the self-review and
    pre-push-quality-gate steps.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return []
    status = read_json(status_path, default={})
    if not isinstance(status, dict):
        return []
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return []
    worktree_path = metadata.get('worktree_path', '')
    if not isinstance(worktree_path, str) or not worktree_path:
        return []
    worktree = Path(worktree_path)
    if not worktree.is_dir():
        return []

    refs_path = get_plan_dir(plan_id) / FILE_REFERENCES
    refs = read_json(refs_path, default={})
    if not isinstance(refs, dict):
        refs = {}
    base_ref = resolve_base_ref(None, refs)
    try:
        footprint = compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError:
        return []
    return sorted(footprint)


def _command_free_build_verdict(plan_id: str) -> dict | None:
    """Return the COMMAND-FREE build-necessity verdict, or ``None`` when unobtainable.

    Thin read of the sole build/no-build authority for the compose-time
    consistency assertion. The question is plan-wide, so no canonical command is
    passed and none may be invented.

    ``None`` (rather than a synthesized verdict) is returned when the authority
    cannot be reached: the assertion's job is to prove a CONTRADICTION, and an
    absent verdict is no evidence of one. Degrading to a fabricated verdict in
    either direction would either fail composes spuriously or assert consistency
    that was never checked.
    """
    try:
        from extension_base import should_execute_build

        verdict = should_execute_build(None, plan_id)
    except Exception:  # noqa: BLE001 — an unobtainable verdict proves no contradiction
        return None
    return verdict if isinstance(verdict, dict) else None


def _apply_pre_push_quality_gate_inactive(
    phase_6_candidates: list[str], plan_id: str
) -> tuple[list[str], bool, str]:
    """Pre-filter: drop ``pre-push-quality-gate`` when the build decision says so.

    Activation is a pure CONSUMPTION of the sole build/no-build authority
    (``extension_base.should_execute_build``); this pre-filter derives nothing of
    its own. The question it asks is plan-wide — "does anything in this footprint
    need a build?" — so it consults the authority COMMAND-FREE and MUST NOT pick
    a representative command; the verdict does not vary by command, and choosing
    one is the retired anti-pattern ADR-004's amendment names.

    When the verdict is ``not_necessary``, ``pre-push-quality-gate`` is removed
    from ``phase_6_candidates``. The pre-filter is a no-op when
    ``pre-push-quality-gate`` is already absent (e.g., already filtered by
    ``_apply_commit_push_disabled``). Returns the filtered list, a flag
    indicating whether the pre-filter fired, and the verdict's own ``reason``
    (empty string when the pre-filter did not fire) so the caller's decision-log
    entry states the reason the verdict actually gave.
    """
    if 'pre-push-quality-gate' not in phase_6_candidates:
        return phase_6_candidates, False, ''

    from extension_base import should_execute_build

    verdict = should_execute_build(None, plan_id)
    if verdict.get('decision') != 'build':
        return (
            [s for s in phase_6_candidates if s != 'pre-push-quality-gate'],
            True,
            verdict.get('reason', ''),
        )

    # Build is necessary — keep the step.
    return phase_6_candidates, False, ''


def _apply_pre_submission_self_review_inactive(phase_6_candidates: list[str], plan_id: str) -> tuple[list[str], bool]:
    """Pre-filter: keep ``pre-submission-self-review`` through compose; self-gate at run time.

    Unlike ``pre-push-quality-gate`` (which gates on the ``build.map`` globs),
    this step has no glob gate — the four cognitive checks it targets (symmetric
    pairs, regex over-fit, wording, duplication) apply to any code or doc change.

    Safety against compose-time emptiness (mirroring
    ``_apply_canonical_verify_inactive``): during early compose (phase-4-plan,
    before the worktree is materialised) the live footprint is empty. An empty
    compose-time footprint is NOT evidence the step is inactive — it only means
    the worktree is not yet materialised — so the step SURVIVES phase-4 compose
    and self-gates at run time against the live footprint via the surfacing
    implementor's own empty-candidate success path. A non-empty footprint keeps
    the step too (there is no glob gate to fail), so this pre-filter never drops
    the step on footprint grounds and always reports ``omitted=False``.

    The step is still dropped upstream by ``_apply_commit_push_disabled`` when
    ``commit_and_push`` is false (this pre-filter is then a no-op because the
    step is already absent — that path is unaffected).

    Returns the candidate list unchanged plus ``False`` (the pre-filter never
    fires).
    """
    return phase_6_candidates, False


def _apply_canonical_verify_inactive(
    phase_5_steps: list[str],
    plan_id: str,
    role_cache: dict[str, str | None],
) -> tuple[list[str], list[str]]:
    """Generic footprint pre-filter for ``default:verify:{canonical}`` steps.

    Drops a composed phase-5 canonical-verify step when its derived role is a
    footprint-gated role (``integration`` / ``e2e``) AND the live, non-empty
    footprint carries no path of that role. The gate is canonical-agnostic: it
    is driven entirely by the ``_CANONICAL_TO_ROLE`` derivation and the
    ``_FOOTPRINT_GATED_CANONICAL_ROLES`` membership table, with no per-canonical
    branch in the code path.

    Safety against compose-time emptiness: during early compose (phase-4-plan,
    before the worktree is materialised) the footprint is empty, so the
    pre-filter is a no-op and every canonical survives — the gate only fires
    against a NON-empty footprint that genuinely lacks the gating role's paths.
    Non-canonical-verify step IDs (``project:`` / ``bundle:skill`` steps) are
    passed through untouched.

    Returns ``(kept_steps, dropped_steps)``.
    """
    footprint = _resolve_footprint(plan_id)
    if not footprint:
        return phase_5_steps, []

    kept: list[str] = []
    dropped: list[str] = []
    for step in phase_5_steps:
        role = _role_of(step, role_cache)
        gating_markers = _FOOTPRINT_GATED_CANONICAL_ROLES.get(role) if role else None
        if gating_markers is not None and not _footprint_has_role(footprint, gating_markers):
            dropped.append(step)
            continue
        kept.append(step)
    return kept, dropped


def _apply_domain_seeded_step_resolvability(
    phase_5_steps: list[str],
    plan_id: str,
) -> tuple[list[str], list[str]]:
    """Resolvability filter for domain-seeded canonical-verify steps.

    A *domain-seeded* verify-step is a ``default:verify:{canonical}`` (bare
    ``verify:{canonical}``) step whose canonical is a LEGITIMATE domain-appended
    canonical — one in :func:`_manifest_validation._domain_appended_canonicals`
    (``arch-gate`` when an active domain declares a ``provides_arch_gate()`` tool).
    The canonical example is ``default:verify:arch-gate`` — appended by
    ``skill-domains configure`` for any project whose configured domains declare a
    ``provides_arch_gate()`` tool (the availability axis), independent of whether
    the plan's own footprint wires any in-scope module that resolves the
    ``arch-gate`` command. Gating on the domain-appended set is what separates a
    legitimate-but-unrunnable domain canonical (soft-skip here) from a genuinely
    unknown/typo'd canonical (``verify:bogus``), which is NOT domain-appended, is
    left untouched, and is hard-failed by the downstream compose-time resolution
    gate (``check_emitted_steps_resolvable``) — the two behaviours must not be
    conflated. The domain-appended set also seeds
    :func:`_manifest_validation._verify_canonicals_universe`, so a KEPT (resolvable)
    domain-seeded step passes that same resolution gate.

    For each domain-seeded step, probe ``architecture resolve --command
    {canonical}`` (reusing :func:`_invoke_architecture_resolve`, the same seam
    :func:`_resolve_step_execution_tier` uses). When it resolves (a status-success
    TOON) the step is KEPT; when it is unresolvable for the whole project footprint
    (``None``) the step is DROPPED. The caller emits a diagnosable ``[STATUS]``
    decision-log warning naming each dropped step — the ADR-010
    status-bearing-gate visibility semantic (a diagnosable skip, never a silent
    drop and never a hard compose block).

    Built-in always-resolvable gates (``quality-gate`` / ``module-tests`` / …) are
    never probed and never dropped; non-canonical-verify step IDs (``project:`` /
    ``bundle:skill`` external steps) and unknown canonicals pass through untouched.
    The filter is generalized over the domain-seeded step CLASS — the ``arch-gate``
    literal is never special-cased; any future domain-appended ``verify:{canonical}``
    the domain-appended set recognizes is filtered the same way.

    Returns ``(kept_steps, dropped_steps)``.
    """
    domain_appended = _manifest_validation._domain_appended_canonicals()
    kept: list[str] = []
    dropped: list[str] = []
    for step in phase_5_steps:
        bare = canonicalize_step_key(step)
        if bare.startswith(_CANONICAL_VERIFY_PREFIX):
            canonical = bare[len(_CANONICAL_VERIFY_PREFIX) :]
            # Domain-seeded == a domain-appended canonical (never a core built-in
            # in _CANONICAL_TO_ROLE). An unknown canonical is not domain-appended
            # and is left for the resolution gate to hard-fail.
            if canonical in domain_appended and canonical not in _CANONICAL_TO_ROLE:
                if _invoke_architecture_resolve(['--command', canonical], plan_id) is None:
                    dropped.append(step)
                    continue
        kept.append(step)
    return kept, dropped


def _log_scope_gated_finalize_subtraction(plan_id: str, scope_estimate: str, dropped_step: str) -> None:
    """Emit one decision-log entry per scope_gated_finalize subtraction."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction — '
        f'scope_estimate={scope_estimate}, dropped {dropped_step} from phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# plan.phase-6-finalize ceremony-gate selection (post-matrix transform)
# =============================================================================
#
# The four finalize ceremony gates drive a post-matrix transform that forces each
# gate's finalize step in (`always`), out (`never`), or defers to the existing
# decision machinery (`auto`, the default no-op). Each gate's effective decision
# is derived from its owning step's per-element `lane` override
# (`steps[<owner>].lane` — `off`→`never`, `minimal`→`always`, `auto`/absent→`auto`),
# NOT from a flat run-at-all sibling. Each gate maps to exactly one finalize step:
#
#   self_review    → default:pre-submission-self-review
#   qgate          → pre-push-quality-gate (the finalize blocking-findings re-capture)
#   simplify       → finalize-step-simplify (holistic post-implementation sweep)
#   security_audit → finalize-step-security-audit (proactive security sweep)
#
# `simplify` and `security_audit` are symmetric peers of the other gates: `auto`
# defers to the matching `*_inactive` pre-filter that already decided the step at
# matrix time, `always` re-adds it even when that pre-filter dropped it, and
# `never` forces it out.
#
# The transform NEVER touches `automatic-review`: the four ceremony gates are the
# only finalize steps this transform may add or drop. The `lane` override is
# validated at set time by `manage-config`'s `validate_lane_override`, and
# `_read_finalize_gates` maps it to the ceremony decision; the composer
# defensively treats any non-`{always,never}` value (including `auto` and a
# malformed value) as defer.
#
# Step IDs are matched against both the bare form and every prefixed form a
# candidate list may carry. Candidate lists are `default:`-namespace-normalized
# at intake (`canonicalize_step_key`), but `project:` / `bundle:skill` prefixes
# are preserved verbatim, so the match-sets below list every form. The `always`
# re-insertion uses the canonical BARE form for every gate (including
# pre-submission-self-review), matching the bare id the normal intake path emits,
# so a force-add never re-introduces a non-canonical `default:`-prefixed id that
# the compose-time canonical-step-key gate would reject.


def _log_ceremony_finalize_selection(
    plan_id: str,
    gate: str,
    value: str,
    step: str,
) -> None:
    """Emit one decision-log entry per ceremony-finalize forced in/out change."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
        f'finalize.{gate}={value}, {"added" if value == "always" else "dropped"} {step} '
        f'{"to" if value == "always" else "from"} phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# execution_tier Routing (per-task verification command classification)
# =============================================================================
#
# Each plan task carries a ``verification.commands`` list whose entries are
# already in resolved form — they are the exact strings dispatched at
# phase-5-execute time. The composer classifies each command via
# ``architecture resolve`` to obtain the four ``execution_tier`` fields
# emitted by that script:
#
# * ``execution_tier == 'orchestrator'`` — the command's adaptive bash
#   timeout has exceeded the host platform's 600s Bash-tool ceiling, so the
#   command MUST run from orchestrator tier rather than a sub-agent's Bash
#   call. The composer maps the build verb (``quality-gate`` / ``verify`` /
#   ``module-tests`` / ``coverage``) to the matching phase-5 step ID,
#   appends it (deduped) to ``phase_5.verification_steps``, and removes the
#   command from the task's verification list. The task may end up with an
#   empty ``verification.commands`` list if every command routed to
#   orchestrator — that is the correct outcome.
# * ``execution_tier == 'per_task'`` — the command fits inside the Bash
#   ceiling. The composer writes ``bash_timeout_seconds`` into the
#   verification entry alongside ``commands`` so the dispatched sub-agent
#   reads the numeric timeout directly. The command itself stays in the
#   task.
# * No ``execution_tier`` field in the resolve TOON — non-build executable
#   (raw shell, ``grep``, ``manage-*`` notation). Behave as today: leave
#   the command in the task, no ``bash_timeout_seconds`` annotation.
#
# Re-entrant by construction: every invocation re-derives the routing from
# the live ``architecture resolve`` output and rewrites both the manifest's
# ``phase_5.verification_steps`` (de-duped) and the task files (per-task
# ``bash_timeout_seconds`` re-written, orchestrator commands re-pruned).
# A previous compose that left a task with empty ``verification.commands``
# is re-noted but the empty state is the canonical "all orchestrator"
# signal.


@functools.cache
def _invoke_architecture_resolve_cached(argv_extra: tuple[str, ...], plan_id: str) -> dict[str, Any] | None:
    """Cached core of :func:`_invoke_architecture_resolve` — one subprocess per distinct key.

    Keyed by ``(argv_extra, plan_id)`` where ``argv_extra`` is the hashable tuple
    form of the resolve argv tail. ``functools.cache`` requires hashable arguments,
    which is why the public wrapper passes a tuple rather than the caller's list. The
    cache is reset per compose by :func:`cmd_compose` (``.cache_clear()``), so it is
    effectively compose-scoped — a re-compose in the same process re-derives from
    the live architecture state rather than a stale prior-compose result. The cached
    dict is only ever read by callers (never mutated), so sharing one instance
    across cache hits is safe.
    """
    executor = _resolve_executor()
    if executor is None:
        return None
    argv: list[str] = [
        sys.executable,
        str(executor),
        'plan-marshall:manage-architecture:architecture',
        'resolve',
        *argv_extra,
        '--audit-plan-id',
        plan_id,
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        parsed_toon = parse_toon(proc.stdout)
    except Exception:
        return None
    if not isinstance(parsed_toon, dict) or parsed_toon.get('status') != 'success':
        return None
    return parsed_toon


def _invoke_architecture_resolve(argv_extra: list[str], plan_id: str) -> dict[str, Any] | None:
    """Subprocess ``architecture resolve`` and return the parsed status-success TOON dict.

    Shared by ``_resolve_command_tier`` (per-command, may add ``--module``),
    ``_resolve_step_execution_tier`` (whole-tree phase-5 steps, never adds
    ``--module``), and ``_apply_domain_seeded_step_resolvability`` (domain-seeded
    verify-step probe). Calls the executor with ``--audit-plan-id`` so resolve runs
    in the correct project_dir context. Returns ``None`` on any failure —
    unresolvable executor, subprocess error, non-zero exit, empty stdout,
    unparseable TOON, or a non-``success`` status; callers apply their own
    safe default on ``None``.

    The composer subprocesses ``architecture resolve`` rather than
    importing its internals because the resolve flow is the canonical
    cross-bundle entry point per the "Build commands: resolve via
    architecture" hard rule, and the augmented TOON shape (the
    ``execution_tier`` / ``bash_timeout_seconds`` fields) is exactly the
    resolve script's contract — re-deriving them here would duplicate logic.

    Compose-scoped memoization: the actual subprocess lives in
    :func:`_invoke_architecture_resolve_cached`, keyed by ``(tuple(argv_extra),
    plan_id)``. A repeated identical resolve within one compose — e.g. the same
    ``default:verify:arch-gate`` canonical probed by
    :func:`_apply_domain_seeded_step_resolvability` and again by
    :func:`_resolve_step_execution_tier` when the step survives — reuses the first
    result instead of re-spawning the subprocess. This wrapper adapts the caller's
    list argument to the cache's hashable tuple key.
    """
    return _invoke_architecture_resolve_cached(tuple(argv_extra), plan_id)


def _resolve_command_tier(cmd: str, plan_id: str) -> dict[str, Any] | None:
    """Resolve a verification command's verb via ``architecture resolve``.

    Returns the resolve dict, or ``None`` on any failure — the composer
    treats ``None`` as "non-build / unresolvable" and leaves the command
    unrouted. See :func:`_invoke_architecture_resolve` for the shared
    subprocess/parse contract.
    """
    parsed = _parse_verification_command(cmd)
    if parsed is None:
        return None
    verb, command_args = parsed
    # Module: second whitespace-separated token of command_args, when present.
    parts = command_args.strip().split()
    module = parts[1] if len(parts) >= 2 else None
    argv_extra = ['--command', verb]
    if module:
        argv_extra.extend(['--module', module])
    return _invoke_architecture_resolve(argv_extra, plan_id)


def _route_task_verification_commands(
    plan_id: str, body: dict[str, Any]
) -> tuple[int, list[tuple[Path, str]]]:
    """Walk plan tasks; route verification commands by ``execution_tier``.

    For each ``TASK-*.json`` under ``{plan_dir}/tasks/``:

    - Skip the task when it has no ``verification.commands`` list.
    - Classify each command via ``_resolve_command_tier``.
    - ``orchestrator`` → map the verb to its phase-5 step ID (canonical map
      first; unmapped verbs generalize to the bare ``verify:{verb}`` step,
      logged per routed verb), append (de-duped) to
      ``body['phase_5']['verification_steps']``, and drop the command from
      the task's ``verification.commands`` — no leaf ever runs an
      orchestrator-tier command inline. Only the defensive raw-shell /
      non-``plan-marshall:build-`` fall-through (verb unparseable) leaves
      an orchestrator-tier command in place.
    - ``per_task`` → set ``verification.bash_timeout_seconds`` on the task
      (overwriting any prior value so re-compose is deterministic). When
      multiple ``per_task`` commands share a task, the maximum
      ``bash_timeout_seconds`` wins — the dispatched sub-agent honours the
      most-demanding command.
    - No tier (non-build / unresolvable) → leave the command in place, no
      annotation.

    The function mutates ``body`` in place but STAGES (does not persist) each
    task's JSON rewrite. Returns ``(mutated_tasks, pending_writes)`` where
    ``mutated_tasks`` is the count of tasks whose verification dict changed
    (for downstream logging) and ``pending_writes`` is the list of
    ``(task_path, serialized_json)`` rewrites the caller commits via
    ``_persist_task_rewrites`` only AFTER the compose-time resolution gate
    passes. Deferring the persistence closes a data-loss bug: an unresolvable
    routed ``verify:{verb}`` step fails compose after the task files would
    otherwise already have been rewritten, silently dropping the original
    verification command from disk.
    """
    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    if not tasks_dir.is_dir():
        return 0, []

    phase_5 = body.setdefault('phase_5', {})
    verification_steps = phase_5.setdefault('verification_steps', [])
    if not isinstance(verification_steps, list):
        verification_steps = list(verification_steps)
        phase_5['verification_steps'] = verification_steps
    # De-dup helper: track membership for O(1) lookup while preserving order.
    seen_steps: set[str] = set(verification_steps)

    mutated_tasks = 0
    pending_writes: list[tuple[Path, str]] = []
    for task_path in sorted(tasks_dir.glob('TASK-*.json')):
        try:
            task = read_json(task_path, default=None)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(task, dict):
            continue
        verification = task.get('verification')
        if not isinstance(verification, dict):
            continue
        commands = verification.get('commands')
        if not isinstance(commands, list) or not commands:
            continue

        kept_commands: list[Any] = []
        per_task_timeout: int | None = None
        changed = False
        for raw in commands:
            if not isinstance(raw, str):
                kept_commands.append(raw)
                continue
            resolve_toon = _resolve_command_tier(raw, plan_id)
            tier = resolve_toon.get('execution_tier') if isinstance(resolve_toon, dict) else None
            if tier == 'orchestrator':
                parsed = _parse_verification_command(raw)
                if parsed is None:
                    # Defensive: classifier said orchestrator but we cannot
                    # extract the verb. Leave the command in place so the
                    # mapping mismatch is observable in the next compose.
                    kept_commands.append(raw)
                    continue
                verb, _ = parsed
                step_id = _verb_to_phase_5_step(verb)
                if step_id is None:
                    # Non-canonical verb (e.g. a custom build target) on an
                    # orchestrator-tier command: route to the generalized bare
                    # ``verify:{verb}`` step ID (boundary-normalization
                    # contract — bare, no ``default:`` prefix) so no leaf ever
                    # runs an orchestrator-tier command inline. Name the routed
                    # verb in the decision log — the canonical map did not
                    # cover it, and a silent route would be unobservable.
                    step_id = f'verify:{verb}'
                    _emit_decision_log(
                        plan_id,
                        '(plan-marshall:manage-execution-manifest:compose) '
                        'execution_tier routing — routed non-canonical '
                        f'orchestrator-tier verb {verb!r} to phase-5 step '
                        f'{step_id!r}',
                    )
                if step_id not in seen_steps:
                    verification_steps.append(step_id)
                    seen_steps.add(step_id)
                changed = True
                continue
            if tier == 'per_task':
                bash_timeout = resolve_toon.get('bash_timeout_seconds') if isinstance(resolve_toon, dict) else None
                if isinstance(bash_timeout, int):
                    if per_task_timeout is None or bash_timeout > per_task_timeout:
                        per_task_timeout = bash_timeout
                kept_commands.append(raw)
                continue
            # No tier or unresolvable → leave the command in place.
            kept_commands.append(raw)

        if kept_commands != commands:
            verification['commands'] = kept_commands
            changed = True
        # Always write the timeout when at least one per_task command was
        # classified — repeat composes converge on the same value.
        existing_timeout = verification.get('bash_timeout_seconds')
        if per_task_timeout is not None:
            if existing_timeout != per_task_timeout:
                verification['bash_timeout_seconds'] = per_task_timeout
                changed = True
        else:
            # No per_task commands survived: strip any stale annotation so
            # re-composes after a tier shift do not leave the field behind.
            if 'bash_timeout_seconds' in verification:
                del verification['bash_timeout_seconds']
                changed = True

        if changed:
            task['verification'] = verification
            # STAGE the rewrite — do NOT persist it here. Committing the task
            # rewrite mid-routing is a data-loss bug: the later compose-time
            # resolution gate (``check_emitted_steps_resolvable``) can still fail
            # the whole compose with ``unresolvable_step`` when a routed
            # ``verify:{verb}`` canonical is not in ``_verify_canonicals_universe()``.
            # On that failure path ``write_manifest`` is never reached, but a
            # command already dropped from disk is gone. The caller persists these
            # staged writes only AFTER the resolution gate passes.
            pending_writes.append((task_path, json.dumps(task, indent=2) + '\n'))
            mutated_tasks += 1

    return mutated_tasks, pending_writes


def _persist_task_rewrites(pending_writes: list[tuple[Path, str]]) -> None:
    """Commit the staged task-file rewrites accumulated by routing.

    Called by ``cmd_compose`` only AFTER the compose-time step-resolution gate
    (``check_emitted_steps_resolvable``) passes, so a compose that fails
    ``unresolvable_step`` never mutates task files on disk — the original
    verification commands survive for the retry.
    """
    for task_path, payload in pending_writes:
        task_path.write_text(payload, encoding='utf-8')


def _log_execution_tier_routing(plan_id: str, mutated_tasks: int, phase_5_steps: list[str]) -> None:
    """Emit one decision-log entry summarising the execution_tier routing pass.

    Logged regardless of whether any task was mutated so the routing is
    observable from ``decision.log`` for every compose call. The entry
    names both the count of touched tasks and the final phase-5 step list
    so retrospective audits can correlate manifest content with task-file
    mutations.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) execution_tier routing — '
        f'mutated_tasks={mutated_tasks}, phase_5.verification_steps={phase_5_steps}'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# Per-step execution_tier stamping (compose-time ADVISORY snapshot)
# =============================================================================
#
# The command-level ``_route_task_verification_commands`` pass above routes each
# TASK's verification COMMANDS by tier. The stamping pass below is the peer for
# the whole-tree phase-5 verification STEPS: it records every entry of the FINAL
# ``phase_5.verification_steps`` list with the ``execution_tier``
# (``per_task`` | ``orchestrator``) that ``architecture resolve`` reports AT
# COMPOSE TIME.
#
# The stamp is ADVISORY, not authoritative. The tier is derived from
# ``bash_timeout_seconds``, which ``_cmd_client_build._lookup_bash_timeout``
# computes from ``timeout_get(command_key, ...)`` — the ADAPTIVE learned build
# duration persisted in run-config. That quantity moves every time the command
# runs, so a step whose learned duration sits near the 600s Bash ceiling can and
# does cross the ceiling between compose and execute: the same compose, over the
# same plan, with no code change, has stamped ``verify:coverage=per_task`` and
# then ``verify:coverage=orchestrator`` after a single intervening build. A
# compose-time snapshot of a moving quantity cannot be a durable routing fact.
#
# The ROUTING AUTHORITY is therefore the LIVE ``architecture resolve`` the leaf
# performs when it runs the step — see
# ``phase-5-execute/standards/canonical_verify.md`` § Workflow steps 1-2. The
# leaf honours the tier that resolve returns AT EXECUTE TIME and never routes a
# build on the stamp alone. The stamp's job is planning and observability: it
# tells the orchestrator how many orchestrator-tier steps to expect and records
# what the tier looked like when the plan was composed.
#
# See ``ref-workflow-architecture/standards/agents.md`` § "Leaf cannot reap a
# backgrounded build" and ``standards/decision-rules.md`` § "execution_tier
# Stamping".


def _resolve_step_execution_tier(canonical: str, plan_id: str) -> str:
    """Resolve a phase-5 canonical-verify step's compose-time ``execution_tier``.

    Subprocesses the whole-tree ``architecture resolve --command {canonical}``
    (no ``--module`` — phase-5 verification steps are whole-tree gates; see
    :func:`_invoke_architecture_resolve` for the shared subprocess/parse
    contract) and reads the ``execution_tier`` field the resolve TOON emits.
    Returns ``'orchestrator'`` or ``'per_task'``. Any failure — unresolvable
    executor, non-zero exit, unparseable TOON, non-success status, or an
    absent/unknown tier — defaults to ``'per_task'`` so the composer never
    emits an unresolved tier into the advisory record list.

    ``per_task`` is the PERMISSIVE default, NOT a safe floor: it is the value
    that would put a long build inline, where the host platform auto-backgrounds
    it past the Bash ceiling and a leaf cannot reap it. It is acceptable here
    only because the stamp is advisory — the leaf re-resolves the tier live when
    it runs the step and routes on THAT verdict, so a wrong compose-time default
    cannot send a long build inline on its own.
    """
    parsed_toon = _invoke_architecture_resolve(['--command', canonical], plan_id)
    if parsed_toon is None:
        return 'per_task'
    tier = parsed_toon.get('execution_tier')
    return tier if tier in ('per_task', 'orchestrator') else 'per_task'


def _stamp_phase_5_step_execution_tier(plan_id: str, verification_steps: list[str]) -> list[dict[str, str]]:
    """Record the ADVISORY per-step ``execution_tier`` list for the final phase-5 verification steps.

    Returns a uniform-array record list — one ``{'step_id': <in-manifest step id>,
    'tier': <execution_tier>}`` object per selected phase-5 verification step, in
    list order. Each tier is the value ``architecture resolve`` reported AT
    COMPOSE TIME; because that value is derived from the adaptive learned build
    duration, it is a snapshot, not a durable fact, and the leaf re-resolves it
    live at execute time (see the module comment above and
    ``phase-5-execute/standards/canonical_verify.md`` § Workflow).
    The record-list form (rather than a keyed map) is dictated by the
    TOON storage format: a phase-5 step id (``verify:quality-gate``) contains a
    colon, and a colon-bearing TOON object KEY does not round-trip through
    ``parse_toon`` (it mis-splits on the first colon), whereas a QUOTED string
    VALUE inside a uniform array round-trips exactly. A built-in canonical-verify
    step (``verify:{canonical}``) resolves its tier via
    :func:`_resolve_step_execution_tier`; every other step id (an external
    ``project:`` / ``bundle:skill`` step, or a ``verify:{canonical}`` whose
    canonical is unresolvable) defaults to ``'per_task'``. The list is total over
    ``verification_steps`` — every selected phase-5 verification step carries a
    resolved tier and the composer never emits an unresolved tier.
    """
    records: list[dict[str, str]] = []
    for step in verification_steps:
        bare = canonicalize_step_key(step)
        if bare.startswith(_CANONICAL_VERIFY_PREFIX):
            canonical = bare[len(_CANONICAL_VERIFY_PREFIX) :]
            tier = _resolve_step_execution_tier(canonical, plan_id)
        else:
            tier = 'per_task'
        records.append({'step_id': step, 'tier': tier})
    return records


def _log_step_execution_tier_stamping(plan_id: str, records: list[dict[str, str]]) -> None:
    """Emit one decision-log entry summarising the per-step execution_tier stamping.

    Names each step id and the tier resolved at compose time so a retrospective
    can read the snapshot from ``decision.log`` without re-parsing the manifest.
    The line labels the record ``advisory`` because the stamped tier is derived
    from the adaptive learned build duration and the leaf routes on its own live
    re-resolve — a retrospective that finds the manifest disagreeing with an
    execute-time tier is reading expected behaviour, not a defect.
    """
    rendered = ', '.join(f'{r["step_id"]}={r["tier"]}' for r in records)
    message = (
        '(plan-marshall:manage-execution-manifest:compose) step_execution_tier stamping '
        '(advisory snapshot — leaf re-resolves live at execute time) — '
        f'{rendered}'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# Command Handlers
# =============================================================================


# =============================================================================
# Execution-profile lane resolution
# =============================================================================
#
# Every lane-participating phase-6 element self-declares a ``lane:`` frontmatter
# block (``class`` / ``tier`` / ``prunable_when`` / ``cost_size``). The operator
# postures ``minimal`` / ``auto`` / ``full`` are cutoffs over those
# self-classifying elements on the lattice ``minimal ⊏ auto ⊏ full``. The closed
# enums, the class→default-tier table, and the resolution rules are owned by
# ``extension-api/standards/ext-point-lane-element.md`` — this composer is the
# single resolver that reads each element's block and applies the posture cutoff.


def _resolve_element_lane(step_id: str) -> dict[str, str] | None:
    """Resolve a phase-6 element's ``lane:`` block from its source doc.

    Built-in steps (bare or ``default:``-prefixed) resolve via the standards /
    workflow doc; ``project:`` steps resolve via the project-local
    ``{bare}/SKILL.md``. Other ``bundle:skill`` external steps have no
    project-local source and return ``None`` (not lane-participating here).
    """
    if step_id.startswith('project:'):
        bare = step_id[len('project:') :]
        skill_path = resolve_project_skill_path(f'{bare}/SKILL.md', base=_REPO_ROOT)
        return _read_frontmatter_lane(skill_path)
    if _is_external_step(step_id):
        return None
    return _read_frontmatter_lane(_resolve_standards_path(step_id))


def _apply_lane_resolution(
    phase_6_steps: list[str],
    posture: str,
    marshal_phase_6_map: dict[str, dict] | None,
    plan_id: str,
) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    """Resolve the phase-6 step list under ``posture`` — returns (kept, dropped, warnings).

    ``full`` is a no-op (keep everything). For ``minimal`` / ``auto`` each
    lane-participating element is kept iff ``effective_tier ⊑ posture``; an
    element with no ``lane:`` block is not lane-participating and is always kept.
    The q-gate is never a phase-6 finalize step, so it is never reached here.
    ``automatic-review`` participates in this pass like any other lane element —
    its keep/drop is governed purely by its configured ``lane`` and lane tier,
    with no separate downstream force-add guard.
    """
    if posture == 'full':
        return list(phase_6_steps), [], []
    kept: list[str] = []
    dropped: list[str] = []
    warnings: list[tuple[str, str]] = []
    for step in phase_6_steps:
        lane = _resolve_element_lane(step)
        if not lane or 'class' not in lane:
            kept.append(step)
            continue
        override = _lane_override_for(step, marshal_phase_6_map)
        keep, warning = _lane_keep_decision(lane, override, posture)
        if warning is not None:
            warnings.append((step, warning))
        (kept if keep else dropped).append(step)
    return kept, dropped, warnings


def _ceremony_prefilter_warnings(
    fired_steps: tuple[tuple[str, bool], ...],
    final_phase_6_steps: list[str],
    posture: str,
    marshal_phase_6_map: dict[str, dict] | None,
) -> list[tuple[str, str]]:
    """Warnings for ceremony pre-filter drops the operator's posture/lane would have kept.

    Second producer on the ``lane_warnings`` channel (peer of
    :func:`_apply_lane_resolution`, same ``(step, warning)`` tuple shape): when
    the ``simplify_inactive`` / ``security_audit_inactive`` ceremony pre-filter
    fired for a step (the change_type + affected_files_count activation gate
    failed) AND the operator's selected posture/lane would have included the
    step AND the ceremony ``always`` gate did not force it back into the final
    step list, the drop would otherwise be silent from the operator's
    perspective — the lane said "keep", yet the step vanished. One entry per
    such drop names the ceremony pre-filter — not the lane — as the remover.

    Read-only with respect to the lane machinery: no keep/drop decision is
    changed here; the same resolvers (:func:`_resolve_element_lane`,
    :func:`_lane_override_for`, :func:`_lane_keep_decision`) are consulted
    purely to answer "would the lane have kept it?". An explicit ``off``
    override means the operator opted the step out (ceremony ``never``), so no
    warning is emitted for it.
    """
    warnings: list[tuple[str, str]] = []
    for step, fired in fired_steps:
        if not fired or step in final_phase_6_steps:
            continue
        override = _lane_override_for(step, marshal_phase_6_map)
        if override == 'off':
            # Operator explicitly opted the step out — not operator-selected.
            continue
        if posture != 'full':
            lane = _resolve_element_lane(step)
            if lane and 'class' in lane:
                keep, _ = _lane_keep_decision(lane, override, posture)
                if not keep:
                    # The lane itself would have dropped the step under this
                    # posture — the ceremony pre-filter changed nothing.
                    continue
        warnings.append(
            (
                step,
                'ceremony pre-filter (change_type/affected_files gate) removed this '
                'operator-selected step — the lane did not drop it',
            )
        )
    return warnings


def _sum_lane_cost(steps: list[str], table: dict[str, str]) -> int:
    """Sum each element's ``cost_size`` through the token table (§4.6 cost preview)."""
    total = 0
    for step in steps:
        lane = _resolve_element_lane(step)
        if not lane:
            continue
        size = lane.get('cost_size')
        if size in table:
            total += _parse_cost_magnitude(str(table[size]))
    return total


def cmd_lanes_preview(args: argparse.Namespace) -> dict[str, Any] | None:
    """Resolve all three posture step sets + cost sums in ONE TOON.

    The preview is the same lane projection ``compose`` applies, so the init
    dialogue preview and the executed flow cannot diverge: ``full``/``minimal``
    are pure config projections (the lane cutoff over the configured phase-6
    candidate list); ``auto`` additionally drops every ``full``-tier element. The
    cost sum for each posture is ``Σ(resolved element cost_size → table)``.
    """
    plan_id = require_valid_plan_id(args)

    marshal_phase_6 = _read_marshal_phase_steps('phase-6-finalize')
    if marshal_phase_6 is not None:
        candidates = list(marshal_phase_6)
    else:
        candidates = _split_csv(getattr(args, 'phase_6_steps', None), DEFAULT_PHASE_6_STEPS)
    candidates = [canonicalize_step_key(s) for s in candidates]
    marshal_phase_6_map = _read_marshal_phase_step_map('phase-6-finalize')
    table = _read_cost_size_token_table()

    lanes: dict[str, Any] = {}
    for posture in LANE_TIERS:
        kept, _dropped, _warnings = _apply_lane_resolution(candidates, posture, marshal_phase_6_map, plan_id)
        lanes[posture] = {
            'phase_6_steps': kept,
            'phase_6_steps_count': len(kept),
            'cost_sum_tokens': _sum_lane_cost(kept, table),
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'lanes': lanes,
    }


def cmd_compose(args: argparse.Namespace) -> dict[str, Any] | None:
    """Compose and write the execution manifest."""
    plan_id = require_valid_plan_id(args)

    # Bound the architecture-resolve memo to a single compose: a re-compose in the
    # same process (and each unit test) re-derives from the live architecture state
    # rather than a stale prior-compose result.
    _invoke_architecture_resolve_cached.cache_clear()
    # Same single-compose bound for the domain-appended-canonicals memo: it is an
    # @lru_cache(maxsize=1) over discover_all_extensions(), so a re-compose in a
    # long-lived process (the marshalld build daemon) whose active domains/extensions
    # changed between composes would otherwise keep a stale domain-seeded canonical
    # set and mis-filter D5 domain-seeded verify steps.
    _manifest_validation._domain_appended_canonicals.cache_clear()

    if args.change_type not in VALID_CHANGE_TYPES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_change_type',
            'message': f'Invalid change_type: {args.change_type!r}. Must be one of {list(VALID_CHANGE_TYPES)}',
        }
    if args.scope_estimate not in VALID_SCOPE_ESTIMATES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_scope_estimate',
            'message': f'Invalid scope_estimate: {args.scope_estimate!r}. Must be one of {list(VALID_SCOPE_ESTIMATES)}',
        }
    if args.track not in VALID_TRACKS:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_track',
            'message': f'Invalid track: {args.track!r}. Must be one of {list(VALID_TRACKS)}',
        }

    raw_commit_and_push = getattr(args, 'commit_and_push', None)
    if raw_commit_and_push is None:
        commit_and_push = True
    elif isinstance(raw_commit_and_push, bool):
        commit_and_push = raw_commit_and_push
    elif str(raw_commit_and_push).lower() in ('true', 'false'):
        commit_and_push = str(raw_commit_and_push).lower() == 'true'
    else:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_commit_and_push',
            'message': f'Invalid commit_and_push: {raw_commit_and_push!r}. Must be one of [true, false]',
        }

    # Source of truth for the candidate step lists: marshal.json
    # ``plan.phase-{5,6}-{execute,finalize}.steps``. The agent-supplied
    # ``--phase-{5,6}-steps`` CSV is a fallback for callers without a
    # marshal.json (notably tests). marshal.json is preferred because the
    # agent has historically built CSVs that strip ``project:`` and
    # ``bundle:skill`` prefixes, producing manifests with bare names that
    # the phase-6-finalize dispatcher then mis-routes as built-in steps.
    # See lesson reference in ``_read_marshal_phase_steps``.
    marshal_phase_5 = _read_marshal_phase_steps('phase-5-execute')
    marshal_phase_6 = _read_marshal_phase_steps('phase-6-finalize')
    # Keyed-map reads carrying the per-step params — used at compose end to
    # snapshot each selected step's resolved params into the manifest body.
    marshal_phase_5_map = _read_marshal_phase_step_map('phase-5-execute')
    marshal_phase_6_map = _read_marshal_phase_step_map('phase-6-finalize')
    phase_5_source = 'marshal.json' if marshal_phase_5 is not None else 'csv_fallback'
    phase_6_source = 'marshal.json' if marshal_phase_6 is not None else 'csv_fallback'
    if marshal_phase_5 is not None:
        phase_5_candidates = list(marshal_phase_5)
    else:
        phase_5_candidates = _split_csv(args.phase_5_steps, DEFAULT_PHASE_5_STEPS)
    if marshal_phase_6 is not None:
        phase_6_candidates = list(marshal_phase_6)
    else:
        phase_6_candidates = _split_csv(args.phase_6_steps, DEFAULT_PHASE_6_STEPS)

    # Boundary normalization: callers (notably marshal.json) may pass step IDs
    # with the optional ``default:`` prefix; the six-row matrix, the pre-filter
    # helpers, and the bundle-self-modification matcher all compare against bare
    # names. Normalize once at the boundary so
    # every downstream site can use plain `s in {...}` / `s == 'foo'` checks
    # without per-site `canonicalize_step_key` calls. Normalizing at the
    # boundary covers every comparison site, not just the cascade-rule sites.
    # External step prefixes (``project:``, ``bundle:skill``) are preserved
    # verbatim so the dispatcher can route them as PROJECT / SKILL steps.
    phase_5_candidates = [canonicalize_step_key(s) for s in phase_5_candidates]
    phase_6_candidates = [canonicalize_step_key(s) for s in phase_6_candidates]

    # Pre-filters run before the six-row matrix. They are orthogonal to the
    # row matrix's change-type / scope / recipe inputs and operate on the
    # candidate list. The order is fixed and documented in
    # standards/decision-rules.md:
    #   1. commit_push_disabled — drop push (and pre-push-quality-gate
    #      and pre-submission-self-review) when no push will occur.
    #   2. pre_push_quality_gate_inactive — drop pre-push-quality-gate when
    #      build.map carries no globs or no live-footprint entry
    #      matches a build_map glob.
    #   3. pre_submission_self_review_inactive — drop pre-submission-self-review
    #      when the live footprint is empty.
    #   4. simplify_inactive — drop finalize-step-simplify when
    #      change_type ∉ {feature, bug_fix, tech_debt, enhancement}
    #      OR affected_files_count == 0.
    #   4b. security_audit_inactive — drop finalize-step-security-audit on the
    #      same change_type + affected_files_count gate as simplify_inactive.
    #   5. scope_gated_finalize — drop heavyweight phase-6 review/audit steps by
    #      scope_estimate; automatic-review suppressed ONLY via the explicit
    #      drop_review_on_scope_gate opt-in.
    # Each pre-filter returns (filtered_candidates, fired_flag); we log a
    # dedicated decision-log line per fired pre-filter in addition to the row
    # log line emitted by _log_decision below.
    phase_6_candidates, commit_push_omitted = _apply_commit_push_disabled(phase_6_candidates, commit_and_push)
    (
        phase_6_candidates,
        pre_push_quality_gate_omitted,
        pre_push_quality_gate_reason,
    ) = _apply_pre_push_quality_gate_inactive(phase_6_candidates, plan_id)
    phase_6_candidates, pre_submission_self_review_omitted = _apply_pre_submission_self_review_inactive(
        phase_6_candidates, plan_id
    )

    affected_files_count = max(0, int(args.affected_files_count or 0))
    # Recipe / lesson provenance: an explicit --recipe-key wins; otherwise read
    # status.metadata.plan_source directly so lesson/recipe-derived plans fire
    # Row 2 even when the phase-4-plan agent omitted the flag. See
    # _read_recipe_source and standards/decision-rules.md § Row 2.
    recipe_key = args.recipe_key or _read_recipe_source(plan_id)
    task_queue_active = _read_task_queue_active(plan_id)

    # Pre-filter 4 (simplify_inactive) consults change_type + affected_files_count,
    # both resolved above; it runs after the three candidate-narrowing pre-filters
    # and before the six-row matrix per standards/decision-rules.md.
    phase_6_candidates, simplify_omitted = _apply_simplify_inactive(
        phase_6_candidates, args.change_type, affected_files_count
    )

    # Pre-filter 4b (security_audit_inactive) is the symmetric peer of
    # simplify_inactive — same change_type + affected_files_count gate, dropping
    # finalize-step-security-audit when the plan has no code-touching change
    # surface to audit. See standards/decision-rules.md § Pre-Filter:
    # security_audit_inactive.
    phase_6_candidates, security_audit_omitted = _apply_security_audit_inactive(
        phase_6_candidates, args.change_type, affected_files_count
    )

    # Pre-filter 5 (scope_gated_finalize) drops heavyweight phase-6 review/audit
    # steps by scope: surgical drops the three review/audit steps, single_module
    # drops only plan-retrospective, and the drop_review_on_scope_gate escape
    # hatch additionally drops automatic-review. It runs after the other
    # pre-filters and before the six-row matrix, so it only ever narrows the
    # candidate list. automatic-review is dropped ONLY via the explicit override —
    # never by the implicit scope gate — so the bot-review invariant stays intact
    # by default. See standards/decision-rules.md § Pre-Filter: scope_gated_finalize.
    drop_review_on_scope_gate = _read_drop_review_on_scope_gate()
    phase_6_candidates, scope_gated_dropped = _apply_scope_gated_finalize(
        phase_6_candidates, args.scope_estimate, drop_review_on_scope_gate
    )

    # Pre-filter 6 (unresolved_ask_provider_drop, D6): drop an UNRESOLVED
    # lane:ask infra element (automatic-review / sonar-roundtrip) when its
    # provider is genuinely absent. Both infra elements seed lane:ask; a
    # steward-persisted answer overwrites the override to off/auto/full, so an
    # effective tier still equal to ``ask`` at compose means the operator never
    # answered. When the corresponding provider is also absent
    # (_read_ci_provider() is None for automatic-review; _read_sonar_provider()
    # is None for sonar-roundtrip) the element is dropped. A RESOLVED ask
    # (off/auto/full) and a provider-configured ask both survive; the
    # off-override-on-floor-step immunity semantic — a weakening off on a
    # core / derived-state floor element is ignored, not dropped (owned by the
    # later lane-resolution pass) — is untouched. Runs at the candidate-narrowing
    # stage so it only ever narrows the candidate list. See
    # standards/decision-rules.md § Pre-Filter: unresolved_ask_provider_drop.
    ci_provider = _read_ci_provider()
    sonar_provider = _read_sonar_provider()
    phase_6_candidates, unresolved_ask_dropped = _apply_unresolved_ask_provider_drop(
        phase_6_candidates, marshal_phase_6_map, ci_provider, sonar_provider
    )

    body, rule = _decide(
        change_type=args.change_type,
        track=args.track,
        scope_estimate=args.scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_candidates=phase_5_candidates,
        phase_6_candidates=phase_6_candidates,
        task_queue_active=task_queue_active,
    )

    # Persist the phase-5 envelope count into the phase_5 block. This is the
    # orchestrator's read-side signal for how many phase-5 execution-context
    # envelopes to plan for. The value is an optional compose input
    # (``--envelope-count``); when absent it defaults to ``DEFAULT_ENVELOPE_COUNT``
    # (``1``), reproducing the single-envelope behaviour, so existing callers
    # that omit the flag are unaffected and a manifest read back without the key
    # is interpreted by every reader as this same default. A non-positive value
    # is clamped to the default — the orchestrator must always dispatch at least
    # one envelope. The field is written across every decision-matrix rule
    # (including ``early_terminate``) so the phase_5 block always carries it.
    raw_envelope_count = getattr(args, 'envelope_count', None)
    if raw_envelope_count is None:
        envelope_count = DEFAULT_ENVELOPE_COUNT
    else:
        envelope_count = max(1, int(raw_envelope_count))
    body['phase_5']['envelope_count'] = envelope_count

    # execution_tier routing runs AFTER the six-row matrix and BEFORE
    # lane resolution. It walks plan tasks, classifies each
    # ``verification.commands`` entry via ``architecture resolve``, and
    # branches on ``execution_tier``:
    #
    # * ``orchestrator`` → append the mapped phase-5 step ID to
    #   ``body['phase_5']['verification_steps']`` (de-duped) and drop the
    #   command from the task's verification list.
    # * ``per_task`` → write ``bash_timeout_seconds`` into the task's
    #   verification dict alongside ``commands``.
    #
    # Non-build / unresolvable commands pass through unchanged. The pass is
    # idempotent across re-composes — every call rewrites both the manifest
    # and the touched task files from the live ``architecture resolve``
    # output. The adaptive-timeout infrastructure design carries the
    # recurrence signature and orchestrator-tier rationale.
    mutated_tasks, pending_task_rewrites = _route_task_verification_commands(plan_id, body)
    _log_execution_tier_routing(plan_id, mutated_tasks, list(body['phase_5'].get('verification_steps', [])))

    # Generic footprint pre-filter for canonical-verify steps. Runs AFTER the
    # six-row matrix and execution_tier routing have produced the final
    # phase-5 verification list, so it sees every canonical-verify step that
    # will be persisted (including any appended by orchestrator-tier routing).
    # It drops a ``default:verify:{canonical}`` step whose derived role is a
    # footprint-gated whole-tree role (integration / e2e) when the live,
    # non-empty footprint carries no path of that role — canonical-agnostic,
    # driven entirely by ``_CANONICAL_TO_ROLE`` + the membership table. A no-op
    # when the footprint is empty (early compose) or no canonical-verify step is
    # footprint-gated. See standards/decision-rules.md § Generic footprint
    # pre-filter and phase-5-execute/standards/canonical_verify.md.
    canonical_verify_role_cache: dict[str, str | None] = {}
    body['phase_5']['verification_steps'], canonical_verify_dropped = _apply_canonical_verify_inactive(
        list(body['phase_5'].get('verification_steps', [])),
        plan_id,
        canonical_verify_role_cache,
    )
    if canonical_verify_dropped:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) canonical_verify_inactive — '
            f'dropped {canonical_verify_dropped} from phase_5.verification_steps (no matching footprint role)',
        )

    # Domain-seeded verify-step resolvability filter. Runs AFTER the canonical-verify
    # footprint pre-filter, and BEFORE per-step tier stamping, over
    # the FINAL phase-5 verification list. A domain-seeded canonical-verify step (a
    # verify:{canonical} whose canonical is NOT a core built-in in _CANONICAL_TO_ROLE —
    # e.g. default:verify:arch-gate, appended by skill-domains configure on the
    # availability axis when a configured domain declares a provides_arch_gate() tool)
    # is DROPPED with a diagnosable [STATUS] warning when architecture resolve --command
    # {canonical} is unresolvable for the whole project footprint (the domain is active
    # but no in-scope module wires the command). This is the ADR-010 status-bearing-gate
    # visibility semantic — a diagnosable skip, never a silent drop and never a hard
    # compose block. Built-in always-resolvable gates (quality-gate / module-tests) are
    # never probed and never dropped; the filter is generalized over the domain-seeded
    # step class, not special-cased to the arch-gate id. The paired seed helper in
    # manage-config (_configured_domains_provide_arch_gate) is left intact — it correctly
    # records the availability-axis signal; the per-footprint resolvability is knowable
    # only here at compose.
    body['phase_5']['verification_steps'], domain_seeded_dropped = _apply_domain_seeded_step_resolvability(
        list(body['phase_5'].get('verification_steps', [])),
        plan_id,
    )
    if domain_seeded_dropped:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) [STATUS] domain_seeded_step_unresolvable — '
            f'dropped {domain_seeded_dropped} from phase_5.verification_steps '
            '(domain active but no in-scope module wires the command)',
        )

    # Per-step execution_tier stamping. Runs AFTER the final phase-5 verification
    # list is settled (six-row matrix, execution_tier COMMAND routing, and the
    # canonical-verify footprint pre-filter) so every step
    # that will be persisted carries a resolved tier. Each selected phase-5
    # verification step is resolved to a deterministic ``execution_tier``
    # (``per_task`` | ``orchestrator``) via ``architecture resolve`` and recorded
    # in ``phase_5.step_execution_tier`` (a uniform-array record list keyed by
    # step id — see _stamp_phase_5_step_execution_tier for why a record list
    # rather than a TOON map). The record is ADVISORY: the tier derives from the
    # adaptive learned build duration, so it drifts between compose and execute,
    # and phase-5-execute re-resolves it live before running each step. The
    # leaf-no-background-build invariant is unchanged (only ``per_task`` steps run
    # inline; every ``orchestrator``-tier step yields to the orchestrator's
    # await-long-running seam) — it is the LIVE tier that enforces it. The list is
    # total — every step carries a resolved tier, defaulting absent/unresolved
    # entries to ``per_task``. See standards/decision-rules.md § "execution_tier
    # Stamping".
    step_execution_tier = _stamp_phase_5_step_execution_tier(
        plan_id, list(body['phase_5'].get('verification_steps', []))
    )
    body['phase_5']['step_execution_tier'] = step_execution_tier
    _log_step_execution_tier_stamping(plan_id, step_execution_tier)

    # plan.phase-6-finalize ceremony-gate selection runs AFTER the six-row
    # matrix (and execution_tier routing). It forces each of the four finalize
    # ceremony gates' steps in (`always`) or out (`never`) on the matrix-produced
    # `phase_6.steps`, deferring to the existing machinery on `auto` (the
    # default). `always` is the only path that can re-add a step the
    # scope_gated_finalize pre-filter dropped — which is the point: the
    # operator-set `always` overrides the implicit scope gate. The transform never
    # touches `automatic-review`, leaving the bot-review invariant intact. Each
    # gate's decision is derived from its owning step's per-element `lane` override
    # (`steps[<owner>].lane` — `off`→`never`, `minimal`→`always`, `auto`/absent→
    # `auto`), not a flat phase-level sibling. See
    # standards/decision-rules.md § plan.phase-6-finalize Selection.
    ceremony_finalize_gates = _read_finalize_gates()
    ceremony_forced_in, ceremony_forced_out = _apply_ceremony_finalize_selection(
        body['phase_6']['steps'], ceremony_finalize_gates
    )

    # Execution-profile lane resolution runs AFTER the change-type / scope
    # pre-filters and ceremony selection. The posture is read from
    # status.metadata.execution_profile (absent → full → no pruning, preserving
    # the pre-lane composition path). Each element's ``lane:`` block (class / tier
    # / cost_size — owned by extension-api/standards/ext-point-lane-element.md)
    # plus its per-element marshal.json ``lane`` override resolves keep/drop under
    # the posture cutoff: ``minimal`` keeps only the tier-minimal floor, ``auto``
    # additionally keeps tier-auto elements and drops tier-full ones, ``full``
    # keeps everything. A weakening ``off`` override of a derived-state / core
    # floor element is IMMUNE — the ``off`` is ignored, the element is KEPT at its
    # class-default tier, and an informational warning records the neutralized
    # override (the mandatory finalize floor cannot be weakened). An ``off`` on an
    # ``adversarial`` / ``prunable`` element is a real opt-out that drops it
    # cleanly. ``automatic-review`` is governed
    # purely by its configured ``lane`` (seeded ``ask`` → resolved by
    # marshall-steward) and its lane tier — there is no separate force-add guard.
    # The q-gate is never a phase-6 finalize step, so it is never lane-pruned here.
    execution_profile = _read_execution_profile(plan_id)
    lane_kept, lane_dropped, lane_warnings = _apply_lane_resolution(
        body['phase_6']['steps'], execution_profile, marshal_phase_6_map, plan_id
    )
    body['phase_6']['steps'] = lane_kept

    # Ceremony pre-filter warnings ride the same lane_warnings channel as lane
    # resolution (second producer, same (step, warning) shape). When the
    # simplify / security-audit ceremony pre-filter fired but the operator's
    # selected posture/lane would have included the step — and the ceremony
    # `always` gate did not force it back in — the entry names the ceremony
    # pre-filter (not the lane) as the remover, so the drop is never silent.
    lane_warnings.extend(
        _ceremony_prefilter_warnings(
            (
                ('finalize-step-simplify', simplify_omitted),
                ('finalize-step-security-audit', security_audit_omitted),
            ),
            body['phase_6']['steps'],
            execution_profile,
            marshal_phase_6_map,
        )
    )

    # Enforce ascending frontmatter-order emission on the FINAL phase_6.steps.
    # cmd_compose never re-sorted the marshal.json ``phase_6.steps`` map by
    # frontmatter order, so ``manage-config sync-defaults`` back-filling a
    # missing default-on step by APPENDING it landed the new step after
    # ``archive-plan`` (order 1000) regardless of its own order (e.g.
    # ``finalize-step-preference-emitter``, order 80). Sorting here makes
    # ``archive-plan`` sort last among order-resolvable steps automatically —
    # every finalize step's order is below 1000 (nearest tail: record-metrics
    # 998, finalize-step-print-phase-breakdown 999). Steps whose order resolves
    # to ``None`` (external ``bundle:skill`` steps) keep their original index.
    # This sort is the sole ordering authority — ``automatic-review`` (order 30)
    # is placed deterministically before the plan-mutating tail by its
    # frontmatter order, so no separate placement validator is needed. Rebind
    # ``final_phase_6_steps``.
    final_phase_6_steps = body['phase_6']['steps']
    body['phase_6']['steps'] = _sort_steps_by_frontmatter_order(final_phase_6_steps)
    final_phase_6_steps = body['phase_6']['steps']

    # Compose-time step-resolution gate (fail-loud): every FINAL emitted phase-5/6
    # step id MUST resolve to a real built-in doc, project-local skill, or bundle
    # discovery-registry entry. An unresolvable id — a built-in doc deleted
    # without sweeping marshal.json, a renamed/removed project skill, or a
    # never-existed bundle:skill key — fails the compose loud, naming the
    # offending ORIGINAL marshal.json key and the phase (mapped back from the
    # boundary-normalized emitted id via marshal_phase_{5,6}_map). The gate runs
    # here, on the FINAL step lists AFTER the sort + placement validator, so only
    # steps that will actually be persisted are checked. See
    # _manifest_validation.check_emitted_steps_resolvable and SKILL.md §
    # "Compose-time step-resolution gate".
    resolution_error = check_emitted_steps_resolvable(
        list(body['phase_5'].get('verification_steps', [])),
        list(body['phase_6'].get('steps', [])),
        marshal_phase_5_map,
        marshal_phase_6_map,
    )
    if resolution_error is not None:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) unresolvable_step — '
            f'{resolution_error["message"]}',
        )
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'unresolvable_step',
            'message': resolution_error['message'],
            'phase': resolution_error['phase'],
            'step_id': resolution_error['step_id'],
            'marshal_key': resolution_error['marshal_key'],
        }

    # Canonical-step-key structural gate (fail-loud): a sibling of the resolution
    # gate above, run on the SAME FINAL emitted step lists. Every emitted phase-5/6
    # step id MUST be in canonical form (``canonicalize_step_key(step_id) ==
    # step_id`` — no leading ``default:`` prefix, no promoted-alias bundle
    # spelling). A non-canonical emitted id is a structural defect (a mis-keyed
    # prefixed step that slipped past the intake boundary normalization); the gate
    # fails the compose loud, naming the offending id and phase, and — like the
    # resolution gate — never writes a partial manifest (returns before the
    # step-params snapshot and ``write_manifest``). See
    # _manifest_validation.check_emitted_steps_canonical and SKILL.md §
    # "Compose-time step-resolution gate".
    canonical_error = check_emitted_steps_canonical(
        list(body['phase_5'].get('verification_steps', [])),
        list(body['phase_6'].get('steps', [])),
    )
    if canonical_error is not None:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) non_canonical_step — '
            f'{canonical_error["message"]}',
        )
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'non_canonical_step',
            'message': canonical_error['message'],
            'phase': canonical_error['phase'],
            'step_id': canonical_error['step_id'],
            'canonical': canonical_error['canonical'],
        }

    # Build-verdict consistency assertion (fail-loud): the third sibling of the
    # two structural gates above, run on the SAME FINAL emitted step lists. It
    # rejects a manifest that CONTRADICTS the sole build/no-build authority —
    # a composed step that can only pass by producing build evidence while
    # build-decision has ruled a build not_necessary for this footprint. Unlike
    # the pre-filters, this narrows nothing; it is an assertion that some
    # consumer decided build necessity from a signal other than the authority.
    #
    # The assertion is deliberately fed the live footprint so it can enforce its
    # non-empty-footprint precondition: at early compose the footprint is always
    # empty and the verdict is therefore always not_necessary, so an unguarded
    # assertion would fire on every plan (see check_build_verdict_consistent's
    # docstring — the empty-footprint trap).
    verdict_error = check_build_verdict_consistent(
        list(body['phase_5'].get('verification_steps', [])),
        list(body['phase_6'].get('steps', [])),
        _resolve_footprint(plan_id),
        _command_free_build_verdict(plan_id),
    )
    if verdict_error is not None:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) build_verdict_contradiction — '
            f'{verdict_error["message"]}',
        )
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'build_verdict_contradiction',
            'message': verdict_error['message'],
            'phase': verdict_error['phase'],
            'step_id': verdict_error['step_id'],
            'reason': verdict_error['reason'],
        }

    # Resolution gate passed — NOW commit the staged task-file rewrites from the
    # execution_tier routing pass. Persisting here (rather than inside the routing
    # walk) guarantees that a compose which fails ``unresolvable_step`` above never
    # dropped a task's original verification command from disk.
    _persist_task_rewrites(pending_task_rewrites)

    # Snapshot the resolved per-step params for the FINAL selected steps into the
    # manifest body (write-time snapshot — the same model that governs the step
    # list). Phase-5/6 runtime consumers read params from this plan-local snapshot
    # via the ``step-params get`` verb rather than re-reading marshal.json. Only
    # the steps that survived selection are snapshotted; the in-manifest step ids
    # are bare, matched against the (possibly ``default:``-prefixed) marshal keys.
    body['phase_5']['step_params'] = _snapshot_step_params(
        list(body['phase_5'].get('verification_steps', [])), marshal_phase_5_map
    )
    body['phase_6']['step_params'] = _snapshot_step_params(
        list(body['phase_6'].get('steps', [])), marshal_phase_6_map
    )

    manifest = {
        'manifest_version': MANIFEST_VERSION,
        'plan_id': plan_id,
        **body,
    }
    write_manifest(plan_id, manifest)
    _log_candidate_source(plan_id, 'phase-5-execute', phase_5_source)
    _log_candidate_source(plan_id, 'phase-6-finalize', phase_6_source)
    if commit_push_omitted:
        _log_commit_push_omitted(plan_id)
    if pre_push_quality_gate_omitted:
        _log_pre_push_quality_gate_omitted(plan_id, pre_push_quality_gate_reason)
    if pre_submission_self_review_omitted:
        _log_pre_submission_self_review_omitted(plan_id)
    if simplify_omitted:
        _log_prefilter_omitted(plan_id, 'finalize-step-simplify', args.change_type, affected_files_count)
    if security_audit_omitted:
        _log_prefilter_omitted(plan_id, 'finalize-step-security-audit', args.change_type, affected_files_count)
    for dropped_step in scope_gated_dropped:
        _log_scope_gated_finalize_subtraction(plan_id, args.scope_estimate, dropped_step)
    for dropped_step in unresolved_ask_dropped:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) unresolved_ask_provider_drop — '
            f'dropped {dropped_step} from phase_6.steps (unresolved lane:ask, provider absent)',
        )
    for change in ceremony_forced_in:
        _log_ceremony_finalize_selection(plan_id, change['gate'], 'always', change['step'])
    for change in ceremony_forced_out:
        _log_ceremony_finalize_selection(plan_id, change['gate'], 'never', change['step'])
    if execution_profile != 'full' and lane_dropped:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) lane_resolution — '
            f'execution_profile={execution_profile}, dropped {lane_dropped} from phase_6.steps '
            '(tier above posture cutoff)',
        )
    for warned_step, warning in lane_warnings:
        _emit_decision_log(
            plan_id,
            '(plan-marshall:manage-execution-manifest:compose) lane_resolution warning — '
            f'{warned_step}: {warning}',
        )
    _log_decision(plan_id, rule, body)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'created': True,
        'manifest_version': MANIFEST_VERSION,
        'phase_5': {
            'early_terminate': body['phase_5']['early_terminate'],
            'verification_steps_count': len(body['phase_5']['verification_steps']),
            'envelope_count': body['phase_5']['envelope_count'],
            'step_execution_tier': body['phase_5']['step_execution_tier'],
        },
        'phase_6': {
            'steps_count': len(body['phase_6']['steps']),
        },
        'rule_fired': rule,
        'commit_and_push': commit_and_push,
        'commit_push_omitted': commit_push_omitted,
        'pre_push_quality_gate_omitted': pre_push_quality_gate_omitted,
        'pre_submission_self_review_omitted': pre_submission_self_review_omitted,
        'simplify_omitted': simplify_omitted,
        'security_audit_omitted': security_audit_omitted,
        'scope_gated_finalize_dropped': scope_gated_dropped,
        'unresolved_ask_provider_dropped': unresolved_ask_dropped,
        'drop_review_on_scope_gate': drop_review_on_scope_gate,
        'ceremony_finalize_gates': ceremony_finalize_gates,
        'ceremony_finalize_forced_in': [c['step'] for c in ceremony_forced_in],
        'ceremony_finalize_forced_out': [c['step'] for c in ceremony_forced_out],
        'execution_profile': execution_profile,
        'lane_dropped': lane_dropped,
        'lane_warnings': [{'step': s, 'warning': w} for s, w in lane_warnings],
    }


def cmd_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read and return the manifest as TOON-friendly dict."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    return {
        'status': 'success',
        'plan_id': plan_id,
        **manifest,
    }


def _log_record_step(plan_id: str, entry: dict[str, Any]) -> None:
    """Emit one decision-log line per recorded execution-log row.

    Written in-process via ``_emit_decision_log`` (the same helper the
    composer uses), so the line lands in the plan's own ``logs/decision.log``
    alongside ``execution.toon``. The line names the step, phase, outcome,
    and the token-attribution triple so a retrospective can correlate
    per-step execution metadata with the manifest without re-parsing the
    ``execution_log`` section.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:record-step) '
        f'Recorded {entry["step_id"]} phase={entry["phase"]} outcome={entry["outcome"]} — '
        f'total_tokens={entry["total_tokens"]}, tool_uses={entry["tool_uses"]}, '
        f'duration_ms={entry["duration_ms"]}'
    )
    _emit_decision_log(plan_id, message)


def cmd_record_step(args: argparse.Namespace) -> dict[str, Any] | None:
    """Append a per-step execution-log row to the manifest.

    Records per-step execution outcome plus token attribution into the
    manifest's ``execution_log[]`` section (created on first record). Each
    invocation appends exactly one row — re-invocation appends another row
    deterministically (the section is an ordered append log, not a keyed
    map), so repeated dispatch of the same step records every attempt. The
    manifest is written atomically and one decision-log line is emitted per
    record.

    Token-attribution fields (``total_tokens`` / ``tool_uses`` /
    ``duration_ms``) default to ``0`` when the caller omits them — a skipped
    step legitimately consumes no tokens, and a step dispatched without a
    ``<usage>`` tag reports zeros rather than a missing column.
    """
    plan_id = require_valid_plan_id(args)

    if args.phase not in VALID_RECORD_PHASES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase!r}. Must be one of {list(VALID_RECORD_PHASES)}',
        }
    if args.outcome not in VALID_RECORD_OUTCOMES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_outcome',
            'message': f'Invalid outcome: {args.outcome!r}. Must be one of {list(VALID_RECORD_OUTCOMES)}',
        }

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    # Canonicalize the step id via the shared resolver before appending the
    # execution_log[] row so execution-log keys reconcile with the manifest's
    # phase_steps keys (a bare↔``default:`` / promoted-alias variant records
    # under the same canonical key the phase step list carries).
    entry = {
        'step_id': canonicalize_step_key(args.step_id),
        'phase': args.phase,
        'outcome': args.outcome,
        'total_tokens': max(0, int(args.total_tokens or 0)),
        'tool_uses': max(0, int(args.tool_uses or 0)),
        'duration_ms': max(0, int(args.duration_ms or 0)),
        'timestamp': datetime.now(UTC).isoformat(),
    }

    execution_log = manifest.get(EXECUTION_LOG_KEY)
    if not isinstance(execution_log, list):
        execution_log = []
    execution_log.append(entry)
    manifest[EXECUTION_LOG_KEY] = execution_log
    write_manifest(plan_id, manifest)

    _log_record_step(plan_id, entry)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'recorded': True,
        'step_id': entry['step_id'],
        'phase': entry['phase'],
        'outcome': entry['outcome'],
        'total_tokens': entry['total_tokens'],
        'tool_uses': entry['tool_uses'],
        'duration_ms': entry['duration_ms'],
        'timestamp': entry['timestamp'],
        'execution_log_count': len(execution_log),
    }


# =============================================================================
# Loadability Check (validate-loadable)
# =============================================================================


def cmd_validate_loadable(args: argparse.Namespace) -> dict[str, Any] | None:
    """Verify standards-file loadability for `phase_6.steps` entries.

    Three modes (mutually exclusive):

    - ``--step-id ID``: validate one step. Returns the per-step dict directly.
    - ``--all``: walk every entry in ``manifest.phase_6.steps`` and return a
      ``results[]`` table plus ``unloadable_count``. Loadability of the
      standards file is the only hard error on this path — the composed
      ``phase_6.steps`` array is authoritative for execution order (the D4
      array-authority contract), so a disagreement between the array order
      and a step's frontmatter ``order:`` is NOT a failure here.
    - ``--check-seed``: read ``plan.phase-6-finalize.steps`` directly from
      ``marshal.json`` (independent of the composed ``execution.toon``) and run
      the ascending-order guard against the seed. Catches a seed-order
      inversion before manifest composition.

    Seed/array authority split: the ascending-order guard fires only on the
    pre-composition SEED (``--check-seed``); once the manifest is composed,
    the runtime array — not the frontmatter ``order:`` — is authoritative, so
    ``--all`` does not re-assert ascending order against frontmatter.

    Built-in steps resolve to ``phase-6-finalize/standards/{name}.md`` in the
    marketplace source tree (the cache layout is a deployment concern;
    resolving against the source tree keeps tests and production on the same
    code path). External steps short-circuit to ``loadable: true``.
    """
    plan_id = require_valid_plan_id(args)

    step_id = getattr(args, 'step_id', None)
    use_all = bool(getattr(args, 'all', False))
    check_seed = bool(getattr(args, 'check_seed', False))

    selected = [bool(step_id is not None), use_all, check_seed]
    if sum(selected) != 1:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_arguments',
            'message': (
                'validate-loadable requires exactly one of '
                '--step-id, --all, or --check-seed'
            ),
        }

    if check_seed:
        seed_steps = _read_marshal_phase_steps('phase-6-finalize')
        if seed_steps is None:
            return {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'seed_unreadable',
                'message': (
                    'could not read plan.phase-6-finalize.steps from marshal.json '
                    f'({get_marshal_path()})'
                ),
            }
        order_message = _check_ascending_order(seed_steps)
        if order_message is not None:
            return {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'seed_order_inversion',
                'message': order_message,
                'step_count': len(seed_steps),
            }
        return {
            'status': 'success',
            'plan_id': plan_id,
            'step_count': len(seed_steps),
        }

    if step_id is not None:
        result = _check_step_loadable(step_id)
        return {
            'status': 'success',
            'plan_id': plan_id,
            **result,
        }

    # --all path: read manifest, walk phase_6.steps.
    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_6, dict):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': 'phase_6 section missing or not a mapping',
        }
    steps = phase_6.get('steps', [])
    if not isinstance(steps, list):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': 'phase_6.steps must be a list',
        }

    results: list[dict[str, Any]] = []
    for entry in steps:
        if isinstance(entry, str):
            results.append(_check_step_loadable(entry))
            continue
        # Non-string manifest entries are corruption — surface them as
        # unloadable so the caller sees them in `results[]` and the
        # `unloadable_count` totals the defect, instead of silently
        # dropping the entry from validation.
        offending_type = type(entry).__name__
        results.append({
            'step_id': str(entry),
            'standards_path': '',
            'loadable': False,
            'message': (
                f'manifest step entry has non-string type `{offending_type}` '
                f'(value: {entry!r}) — manifest is corrupt; only str step IDs are valid'
            ),
        })
    unloadable_count = sum(1 for r in results if not r['loadable'])

    # Per the D4 array-authority contract, the composed ``phase_6.steps`` array
    # is authoritative for execution order. The ascending-order guard against
    # frontmatter ``order:`` belongs to the pre-composition SEED check only
    # (``--check-seed``); re-asserting it here would let an in-plan change to a
    # step's ``order:`` frontmatter retroactively invalidate an already-composed
    # manifest the array says is still correct. Loadability of the standards
    # file is therefore the only hard error on the ``--all`` path.
    return {
        'status': 'success',
        'plan_id': plan_id,
        'unloadable_count': unloadable_count,
        'results': results,
    }


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Manage the per-plan execution manifest', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    compose_parser = subparsers.add_parser('compose', help='Compose and write execution.toon', allow_abbrev=False)
    add_plan_id_arg(compose_parser)
    compose_parser.add_argument('--change-type', required=True, help='Change type (one of VALID_CHANGE_TYPES)')
    compose_parser.add_argument('--track', required=True, help='Outline track: simple|complex')
    compose_parser.add_argument(
        '--scope-estimate', required=True, help='scope_estimate (none|surgical|single_module|multi_module|broad)'
    )
    compose_parser.add_argument('--recipe-key', default=None, help='Recipe key (e.g. lesson_cleanup) when applicable')
    compose_parser.add_argument(
        '--affected-files-count', type=int, default=0, help='Count of affected files from the outline'
    )
    compose_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated candidate Phase 5 step IDs')
    compose_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated candidate Phase 6 step IDs')
    compose_parser.add_argument(
        '--envelope-count',
        type=int,
        default=None,
        help='Number of phase-5 execution-context envelopes the orchestrator should plan for. '
        'Optional; defaults to 1 (single budget-bounded envelope) when omitted. A non-positive '
        'value is clamped to 1. Persisted into the manifest phase_5 block as envelope_count.',
    )
    compose_parser.add_argument(
        '--commit-and-push',
        default=None,
        help='Resolved commit_and_push from phase-5-execute config (true|false). '
        'When omitted defaults to true. When false, push (and pre-push-quality-gate '
        'and pre-submission-self-review) is omitted from phase_6.steps.',
    )

    read_parser = subparsers.add_parser('read', help='Read execution.toon as TOON', allow_abbrev=False)
    add_plan_id_arg(read_parser)

    # lanes preview — resolve all three posture step sets + cost sums in one TOON.
    lanes_parser = subparsers.add_parser(
        'lanes',
        help='Execution-profile lane resolver (preview)',
        allow_abbrev=False,
    )
    lanes_sub = lanes_parser.add_subparsers(dest='lanes_verb', required=True, help='lanes operation')
    lanes_preview = lanes_sub.add_parser(
        'preview',
        help='Resolve minimal/auto/full phase-6 step sets + cost sums in one TOON',
        allow_abbrev=False,
    )
    add_plan_id_arg(lanes_preview)
    lanes_preview.add_argument(
        '--phase-6-steps',
        default=None,
        help='Comma-separated candidate Phase 6 step IDs (fallback when marshal.json carries none)',
    )

    record_step_parser = subparsers.add_parser(
        'record-step',
        help='Append a per-step execution-log row (outcome + token attribution) to execution.toon',
        allow_abbrev=False,
    )
    add_plan_id_arg(record_step_parser)
    record_step_parser.add_argument('--step-id', required=True, help='Step identifier being recorded')
    record_step_parser.add_argument(
        '--phase', required=True, help='Phase the step ran in (one of VALID_RECORD_PHASES: 5-execute|6-finalize)'
    )
    record_step_parser.add_argument(
        '--outcome', required=True, help='Execution outcome (one of VALID_RECORD_OUTCOMES: executed|skipped|error)'
    )
    record_step_parser.add_argument('--total-tokens', type=int, default=0, help='Total tokens attributed to the step')
    record_step_parser.add_argument('--tool-uses', type=int, default=0, help='Tool-use count attributed to the step')
    record_step_parser.add_argument('--duration-ms', type=int, default=0, help='Wall-clock duration in milliseconds')

    validate_parser = subparsers.add_parser('validate', help='Validate execution.toon', allow_abbrev=False)
    add_plan_id_arg(validate_parser)
    validate_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated allowed Phase 5 step IDs')
    validate_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated allowed Phase 6 step IDs')

    validate_loadable_parser = subparsers.add_parser(
        'validate-loadable',
        help='Verify standards-file presence for phase_6.steps entries',
        allow_abbrev=False,
    )
    add_plan_id_arg(validate_loadable_parser)
    validate_loadable_group = validate_loadable_parser.add_mutually_exclusive_group(required=True)
    validate_loadable_group.add_argument(
        '--step-id',
        default=None,
        help='Validate a single step (bare name or default:-prefixed)',
    )
    validate_loadable_group.add_argument(
        '--all',
        action='store_true',
        help='Validate every entry in manifest.phase_6.steps',
    )
    validate_loadable_group.add_argument(
        '--check-seed',
        action='store_true',
        help=(
            'Read plan.phase-6-finalize.steps directly from marshal.json and '
            'assert ascending frontmatter order (detects seed-order inversion '
            'before manifest composition)'
        ),
    )

    # step-params get / step-params set — plan-local reads/overrides of the
    # compose-time snapshot under body[phase].step_params.
    step_params_parser = subparsers.add_parser(
        'step-params',
        help="Get/set a step's snapshotted params from the plan-local manifest",
        allow_abbrev=False,
    )
    step_params_sub = step_params_parser.add_subparsers(
        dest='step_params_verb', required=True, help='step-params operation'
    )

    sp_get = step_params_sub.add_parser(
        'get', help='Get a step\'s snapshotted param object from the manifest', allow_abbrev=False
    )
    add_plan_id_arg(sp_get)
    sp_get.add_argument('--phase', required=True, help='Phase: 5-execute or 6-finalize')
    sp_get.add_argument('--step-id', required=True, help='Step id (e.g., default:sonar-roundtrip)')

    sp_set = step_params_sub.add_parser(
        'set', help='Write a per-plan param override into the manifest snapshot', allow_abbrev=False
    )
    add_plan_id_arg(sp_set)
    sp_set.add_argument('--phase', required=True, help='Phase: 5-execute or 6-finalize')
    sp_set.add_argument('--step-id', required=True, help='Step id (e.g., default:branch-cleanup)')
    sp_set.add_argument('--param', required=True, help='Param key (e.g., pr_merge_strategy)')
    sp_set.add_argument('--value', required=True, help='Param value (coerced bool/int/str)')

    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)

    handlers = {
        'compose': cmd_compose,
        'read': cmd_read,
        'record-step': cmd_record_step,
        'validate': cmd_validate,
        'validate-loadable': cmd_validate_loadable,
    }
    if args.command == 'step-params':
        step_params_handlers = {
            'get': cmd_step_params_get,
            'set': cmd_step_params_set,
        }
        result = step_params_handlers[args.step_params_verb](args)
    elif args.command == 'lanes':
        lanes_handlers = {
            'preview': cmd_lanes_preview,
        }
        result = lanes_handlers[args.lanes_verb](args)
    else:
        handler = handlers[args.command]
        result = handler(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
