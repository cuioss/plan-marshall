#!/usr/bin/env python3
"""
Manage the per-plan execution manifest (compose, read, validate).

The manifest is the single source of truth for which Phase 5 verification
steps and Phase 6 finalize steps fire for a given plan. Phases 5 and 6 read
the manifest and dispatch — they no longer carry per-doc skip logic.

Storage: TOON format at .plan/local/plans/{plan_id}/execution.toon
Output: TOON format for API responses

Usage:
    python3 manage-execution-manifest.py compose --plan-id my-plan \\
        --change-type bug_fix --track simple --scope-estimate surgical
    python3 manage-execution-manifest.py read --plan-id my-plan
    python3 manage-execution-manifest.py validate --plan-id my-plan
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from constants import FILE_REFERENCES  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    get_marshal_path,
    get_plan_dir,
    output_toon,
    output_toon_error,
    read_json,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    require_valid_plan_id,
)
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

MANIFEST_FILENAME = 'execution.toon'
MANIFEST_VERSION = 1

VALID_CHANGE_TYPES = (
    'analysis',
    'feature',
    'enhancement',
    'bug_fix',
    'tech_debt',
    'verification',
)

VALID_SCOPE_ESTIMATES = (
    'none',
    'surgical',
    'single_module',
    'multi_module',
    'broad',
)

VALID_TRACKS = ('simple', 'complex')

VALID_COMMIT_STRATEGIES = ('per_plan', 'per_deliverable', 'none')
DEFAULT_COMMIT_STRATEGY = 'per_plan'

# Default candidate step sets when callers don't pass --phase-5-steps / --phase-6-steps.
DEFAULT_PHASE_5_STEPS = ('quality-gate', 'module-tests')
DEFAULT_PHASE_6_STEPS = (
    'commit-push',
    'create-pr',
    'automated-review',
    'sonar-roundtrip',
    'knowledge-capture',
    'lessons-capture',
    'branch-cleanup',
    'archive-plan',
)

# Bundle source globs evaluated by `bundle_self_modification`. A modified-file
# entry matching ANY of these triggers an early `sync-plugin-cache` insertion
# in `phase_6.steps`. Cached plugin definitions are the runtime source of truth
# for Task agent dispatch, so when the plan's diff edits these surfaces the
# in-flight finalize must publish the worktree to the cache before the first
# agent-dispatched step. See lesson 2026-04-26-23-003.
_BUNDLE_SOURCE_GLOBS = (
    'marketplace/bundles/*/agents/*',
    'marketplace/bundles/*/agents/**',
    'marketplace/bundles/*/commands/*',
    'marketplace/bundles/*/commands/**',
    'marketplace/bundles/*/skills/*',
    'marketplace/bundles/*/skills/**',
)

# Phase 6 steps that dispatch Task subagents loaded from the plugin cache. The
# bundle_self_modification rule inserts `sync-plugin-cache` immediately before
# the earliest occurrence of ANY entry in this set. Stored as bare names; the
# matcher normalizes the candidate-list step (which may arrive prefixed with
# `default:` from `marshal.json` or bare from the `DEFAULT_PHASE_6_STEPS`
# fallback) before checking membership, so both call paths fire correctly.
_AGENT_DISPATCHED_STEPS = frozenset({
    'create-pr',
    'automated-review',
    'sonar-roundtrip',
    'knowledge-capture',
    'lessons-capture',
})


def _strip_default_prefix(step: str) -> str:
    """Return the bare step name regardless of the optional ``default:`` prefix."""
    return step[len('default:'):] if step.startswith('default:') else step

_EARLY_SYNC_STEP = 'project:finalize-step-sync-plugin-cache'


# =============================================================================
# File Operations
# =============================================================================


def get_manifest_path(plan_id: str) -> Path:
    """Return the absolute path to the execution manifest for ``plan_id``."""
    return get_plan_dir(plan_id) / MANIFEST_FILENAME


def write_manifest(plan_id: str, manifest: dict[str, Any]) -> None:
    """Atomically write the manifest as TOON to its plan path."""
    path = get_manifest_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, serialize_toon(manifest))


def read_manifest(plan_id: str) -> dict[str, Any] | None:
    """Read and parse the manifest, returning ``None`` if missing."""
    path = get_manifest_path(plan_id)
    if not path.exists():
        return None
    return parse_toon(path.read_text(encoding='utf-8'))


# =============================================================================
# Decision Engine (seven-row matrix from standards/decision-rules.md)
# =============================================================================


def _split_csv(value: str | None, default: tuple[str, ...]) -> list[str]:
    if value is None or value == '':
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _decide(
    change_type: str,
    track: str,
    scope_estimate: str,
    recipe_key: str | None,
    affected_files_count: int,
    phase_5_candidates: list[str],
    phase_6_candidates: list[str],
) -> tuple[dict[str, Any], str]:
    """Apply the seven-row decision matrix.

    Returns the manifest body (under ``phase_5`` / ``phase_6`` keys) plus the
    name of the rule that fired (one of the seven rule keys defined in
    standards/decision-rules.md).
    """

    # Rule 1: early_terminate — analysis without affected files. Phase 5 is
    # skipped entirely; Phase 6 still runs lessons/knowledge capture so the
    # analysis doesn't leak insights silently.
    if change_type == 'analysis' and affected_files_count == 0:
        body = {
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates if _strip_default_prefix(s) in {'knowledge-capture', 'lessons-capture', 'archive-plan'}
                ],
            },
        }
        return body, 'early_terminate_analysis'

    # Rule 2: recipe path — recipe-driven plans get a slim manifest. The
    # recipe-lesson-cleanup recipe (deliverable 7) sets scope_estimate=surgical
    # so the surgical-style cascades still apply downstream; here we only need
    # to drop heavy steps.
    if recipe_key:
        phase_6_steps = [
            s for s in phase_6_candidates
            if _strip_default_prefix(s) not in {'automated-review', 'sonar-roundtrip', 'knowledge-capture'}
        ]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s in {'quality-gate', 'module-tests'}],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        return body, 'recipe'

    # Rule 3: docs-only — surgical scope plus no test/code expectations. Skip
    # build verification entirely; keep capture + commit + PR + branch cleanup.
    if scope_estimate in ('surgical', 'single_module') and change_type in ('tech_debt', 'enhancement') and affected_files_count > 0 and _looks_docs_only(phase_5_candidates):
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates
                    if _strip_default_prefix(s) not in {'sonar-roundtrip', 'automated-review'}
                ],
            },
        }
        return body, 'docs_only'

    # Rule 4: tests-only — verification change_type with affected files. Run
    # the module-tests step but skip quality-gate; full Phase 6.
    if change_type == 'verification' and affected_files_count > 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s == 'module-tests'],
            },
            'phase_6': {'steps': list(phase_6_candidates)},
        }
        return body, 'tests_only'

    # Rule 5: surgical + bug_fix / tech_debt — Q-Gate bypass already applies
    # at outline time (deliverable 4). Here we trim the manifest: no
    # automated-review, no sonar-roundtrip, no knowledge-capture (small,
    # focused changes). Keep lessons-capture + commit/PR/cleanup.
    if scope_estimate == 'surgical' and change_type in ('bug_fix', 'tech_debt'):
        phase_6_steps = [
            s for s in phase_6_candidates
            if _strip_default_prefix(s) not in {'automated-review', 'sonar-roundtrip', 'knowledge-capture'}
        ]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s in {'quality-gate', 'module-tests'}],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        rule = f'surgical_{change_type}'
        return body, rule

    # Rule 6: verification change_type without affected files — same shape as
    # rule 1's Phase 6 minimum, but Phase 5 still runs whatever was passed.
    if change_type == 'verification' and affected_files_count == 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': list(phase_5_candidates),
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates if _strip_default_prefix(s) in {'knowledge-capture', 'lessons-capture', 'archive-plan'}
                ],
            },
        }
        return body, 'verification_no_files'

    # Rule 7 (default): code-shaped feature / enhancement / large change. Full
    # verification + full finalize. This is the safe baseline the request
    # called the "default code-shaped feature" row.
    body = {
        'phase_5': {
            'early_terminate': False,
            'verification_steps': list(phase_5_candidates),
        },
        'phase_6': {'steps': list(phase_6_candidates)},
    }
    return body, 'default'


def _bundle_self_modification(modified_files: list[str]) -> bool:
    """Return True when any modified file matches a bundle source glob.

    Globs are evaluated with ``fnmatch.fnmatchcase`` (POSIX semantics, no regex).
    The triggering surfaces are bundled agents, commands, and skills — the
    runtime source of truth for Task dispatch. See lesson 2026-04-26-23-003.
    """
    return any(
        fnmatch.fnmatchcase(path, glob)
        for path in modified_files
        for glob in _BUNDLE_SOURCE_GLOBS
    )


def _read_bundle_change_paths(plan_id: str) -> list[str]:
    """Read the union of ``affected_files`` and ``modified_files`` from references.json.

    The composer runs from `phase-4-plan` Step 8b — at outline/plan time, BEFORE
    Phase 5 has committed any changes. ``modified_files`` is populated by
    ``manage-status transition`` on Phase 5 completion, so it is empty at compose
    time for normal plans (a re-compose after Phase 5 would see it populated).
    ``affected_files`` is populated at outline time from the solution outline
    deliverables and is the canonical pre-execute source.

    Reading both fields and unioning their entries closes that timing gap: the
    rule fires on the first compose (via ``affected_files``) AND on any later
    re-compose that includes execute-time additions (via ``modified_files``).
    Returns an empty list when the file is missing or malformed — the rule
    simply does not fire in that case.
    """
    references_path = get_plan_dir(plan_id) / 'references.json'
    if not references_path.exists():
        return []
    try:
        payload = json.loads(references_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return []

    seen: set[str] = set()
    union: list[str] = []
    for field in ('affected_files', 'modified_files'):
        entries = payload.get(field)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, str) and entry not in seen:
                seen.add(entry)
                union.append(entry)
    return union


def _apply_bundle_self_modification(
    plan_id: str, body: dict[str, Any], modified_files: list[str]
) -> str | None:
    """Insert an early ``sync-plugin-cache`` step when the rule fires.

    Mutates ``body['phase_6']['steps']`` in place and returns the inserting
    step name (the agent-dispatched step that the new entry was placed before)
    when the rule fires. Returns ``None`` when the rule does not fire — either
    because no bundle source matched or no agent-dispatched step is present in
    the resolved phase_6 list.

    Idempotent: if ``project:finalize-step-sync-plugin-cache`` already sits
    immediately before the first agent-dispatched step, no insertion occurs.
    The existing late-stage occurrence (if any) is preserved verbatim — the
    rule stacks an additional early occurrence rather than relocating.
    """
    if not _bundle_self_modification(modified_files):
        return None

    phase_6 = body.get('phase_6')
    if not isinstance(phase_6, dict):
        return None
    steps = phase_6.get('steps')
    if not isinstance(steps, list) or not steps:
        return None

    early_index: int | None = None
    for i, step in enumerate(steps):
        if not isinstance(step, str):
            continue
        # Normalize the candidate-list entry (may arrive prefixed with
        # `default:` from `marshal.json` or bare from `DEFAULT_PHASE_6_STEPS`)
        # before matching against the bare-name set.
        if _strip_default_prefix(step) in _AGENT_DISPATCHED_STEPS:
            early_index = i
            break
    if early_index is None:
        return None

    # Idempotency guard: already inserted immediately before the first agent step.
    if early_index > 0 and steps[early_index - 1] == _EARLY_SYNC_STEP:
        return None

    inserting_before = steps[early_index]
    if not isinstance(inserting_before, str):
        return None
    steps.insert(early_index, _EARLY_SYNC_STEP)
    phase_6['steps'] = steps
    return inserting_before


def _log_bundle_self_modification(plan_id: str, inserting_before: str) -> None:
    """Emit the decision-log entry for the ``bundle_self_modification`` rule."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) Rule bundle_self_modification fired — '
        f'inserted {_EARLY_SYNC_STEP} before {inserting_before}'
    )
    _emit_decision_log(plan_id, message)


def _looks_docs_only(phase_5_candidates: list[str]) -> bool:
    """Heuristic: docs-only plans don't request module-tests or coverage.

    The composer treats any candidate set that lacks ``module-tests`` AND
    ``coverage`` as a docs-only signal. Real code-shaped plans always include
    at least ``module-tests`` in their candidate set.
    """
    return 'module-tests' not in phase_5_candidates and 'coverage' not in phase_5_candidates


# =============================================================================
# Decision Logging
# =============================================================================


def _resolve_executor() -> Path | None:
    """Locate ``.plan/execute-script.py`` by walking up from this script.

    Mirrors the bootstrap pattern in ``file_ops.py``. Returns ``None`` if no
    executor sibling is found (e.g. running under an exotic test fixture).
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / '.plan' / 'execute-script.py'
        if candidate.is_file():
            return candidate
    return None


def _emit_decision_log(plan_id: str, message: str) -> None:
    """Best-effort decision-log emission via the executor.

    Logging is non-load-bearing — manifest content is the contract — so any
    executor lookup miss or subprocess error is swallowed silently.
    """
    executor = _resolve_executor()
    if executor is None:
        return
    try:
        subprocess.run(
            [
                sys.executable,
                str(executor),
                'plan-marshall:manage-logging:manage-logging',
                'decision',
                '--plan-id',
                plan_id,
                '--level',
                'INFO',
                '--message',
                message,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
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
    """Emit the decision-log entry for the ``commit_strategy_none`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) commit-push omitted — commit_strategy=none'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_push_quality_gate_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``pre_push_quality_gate_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — '
        'activation_globs empty or no modified_files match'
    )
    _emit_decision_log(plan_id, message)


def _log_pre_submission_self_review_omitted(plan_id: str) -> None:
    """Emit the decision-log entry for the ``pre_submission_self_review_inactive`` pre-filter."""
    message = (
        '(plan-marshall:manage-execution-manifest:compose) pre-submission-self-review omitted — '
        'empty modified_files'
    )
    _emit_decision_log(plan_id, message)


def _log_bot_enforcement_guard_fired(plan_id: str, provider: str) -> None:
    """Emit the decision-log entry for the ``bot_enforcement_guard`` violation.

    Logged before the composition error is raised so the violation is recorded
    even though the manifest was not persisted.
    """
    message = (
        '(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard fired — '
        f'ci_provider={provider}, automated-review missing from phase_6.steps'
    )
    _emit_decision_log(plan_id, message)


# =============================================================================
# Pre-Filter Helpers
# =============================================================================


def _read_activation_globs() -> list[str]:
    """Read ``plan.phase-6-finalize.pre_push_quality_gate.activation_globs`` from marshal.json.

    Returns an empty list when the file is missing, the keys are absent, or the
    value is not a list. The pre-filter treats any of these conditions as
    "inactive" and removes ``default:pre-push-quality-gate``.
    """
    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return []
    data = read_json(marshal_path, default={})
    if not isinstance(data, dict):
        return []
    plan = data.get('plan')
    if not isinstance(plan, dict):
        return []
    phase_6 = plan.get('phase-6-finalize')
    if not isinstance(phase_6, dict):
        return []
    pre_push = phase_6.get('pre_push_quality_gate')
    if not isinstance(pre_push, dict):
        return []
    globs = pre_push.get('activation_globs')
    if not isinstance(globs, list):
        return []
    return [g for g in globs if isinstance(g, str) and g]


def _read_modified_files(plan_id: str) -> list[str]:
    """Read ``references.json::modified_files`` for ``plan_id``.

    Returns an empty list when the file is missing or the field is absent / not
    a list. The pre-filter treats absence as "no matches" and removes the step.
    """
    refs_path = get_plan_dir(plan_id) / FILE_REFERENCES
    if not refs_path.exists():
        return []
    data = read_json(refs_path, default={})
    if not isinstance(data, dict):
        return []
    files = data.get('modified_files')
    if not isinstance(files, list):
        return []
    return [f for f in files if isinstance(f, str) and f]


def _any_glob_matches(paths: list[str], globs: list[str]) -> bool:
    """Return ``True`` iff at least one ``path`` matches at least one ``glob``."""
    for path in paths:
        for glob in globs:
            if fnmatch.fnmatch(path, glob):
                return True
    return False


def _apply_commit_strategy_none(
    phase_6_candidates: list[str], commit_strategy: str
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``commit-push`` when ``commit_strategy == none``.

    Also drops ``pre-push-quality-gate`` and ``pre-submission-self-review``
    because both gates are only meaningful when a downstream push exists.
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired.
    """
    if commit_strategy != 'none':
        return phase_6_candidates, False
    fired = False
    filtered: list[str] = []
    for step in phase_6_candidates:
        if step in {'commit-push', 'pre-push-quality-gate', 'pre-submission-self-review'}:
            fired = True
            continue
        filtered.append(step)
    return filtered, fired


def _apply_pre_push_quality_gate_inactive(
    phase_6_candidates: list[str], plan_id: str
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``pre-push-quality-gate`` when activation conditions fail.

    Activation requires BOTH:

    1. ``plan.phase-6-finalize.pre_push_quality_gate.activation_globs`` in
       ``marshal.json`` is non-empty.
    2. At least one entry in ``references.json::modified_files`` matches one of
       the configured globs (using ``fnmatch.fnmatch``).

    When either condition fails, ``pre-push-quality-gate`` is removed from
    ``phase_6_candidates``. The pre-filter is a no-op when ``pre-push-quality-gate``
    is already absent (e.g., already filtered by ``_apply_commit_strategy_none``).
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired (i.e., the step was active in the input but inactive after the
    check).
    """
    if 'pre-push-quality-gate' not in phase_6_candidates:
        return phase_6_candidates, False

    globs = _read_activation_globs()
    if not globs:
        return [s for s in phase_6_candidates if s != 'pre-push-quality-gate'], True

    modified_files = _read_modified_files(plan_id)
    if not modified_files:
        return [s for s in phase_6_candidates if s != 'pre-push-quality-gate'], True

    if not _any_glob_matches(modified_files, globs):
        return [s for s in phase_6_candidates if s != 'pre-push-quality-gate'], True

    # All activation conditions satisfied — keep the step.
    return phase_6_candidates, False


def _apply_pre_submission_self_review_inactive(
    phase_6_candidates: list[str], plan_id: str
) -> tuple[list[str], bool]:
    """Pre-filter: drop ``pre-submission-self-review`` when activation conditions fail.

    Activation requires ``references.json::modified_files`` to be non-empty.
    There is no ``activation_globs`` knob — the four cognitive checks the step
    targets (symmetric pairs, regex over-fit, wording, duplication) apply to
    any code or doc change.

    The pre-filter is a no-op when ``pre-submission-self-review`` is already
    absent (e.g., already filtered by ``_apply_commit_strategy_none``).
    Returns the filtered list plus a flag indicating whether the pre-filter
    fired.
    """
    if 'pre-submission-self-review' not in phase_6_candidates:
        return phase_6_candidates, False

    modified_files = _read_modified_files(plan_id)
    if not modified_files:
        return [s for s in phase_6_candidates if s != 'pre-submission-self-review'], True

    return phase_6_candidates, False


def _read_ci_provider() -> str | None:
    """Return the CI provider identifier (``github``, ``gitlab``) from marshal.json.

    Resolution order (first match wins):

    1. ``ci.provider`` — short identifier set explicitly by the project.
    2. ``providers[]`` entry where ``category == 'ci'``, mapping skill name to
       a short identifier:

       * ``plan-marshall:workflow-integration-github`` -> ``github``
       * ``plan-marshall:workflow-integration-gitlab`` -> ``gitlab``

    Returns ``None`` when the marshal file is missing, no CI provider is
    declared, or the resolved value is neither ``github`` nor ``gitlab``.
    """
    marshal_path = get_marshal_path()
    if marshal_path is None or not marshal_path.is_file():
        return None
    try:
        data = read_json(marshal_path)
    except (OSError, json.JSONDecodeError):
        return None
    ci_block = data.get('ci')
    if isinstance(ci_block, dict):
        provider = ci_block.get('provider')
        if isinstance(provider, str) and provider in {'github', 'gitlab'}:
            return provider
    providers = data.get('providers')
    if not isinstance(providers, list):
        return None
    for entry in providers:
        if not isinstance(entry, dict):
            continue
        if entry.get('category') != 'ci':
            continue
        skill_name = entry.get('skill_name', '')
        if not isinstance(skill_name, str):
            continue
        if skill_name == 'plan-marshall:workflow-integration-github':
            return 'github'
        if skill_name == 'plan-marshall:workflow-integration-gitlab':
            return 'gitlab'
    return None


def _apply_bot_enforcement_guard(
    phase_6_steps: list[str], plan_id: str
) -> str | None:
    """Composition-time guard: ``automated-review`` must remain on GitHub/GitLab plans.

    Lesson ``2026-04-27-18-003`` requires PR-review bots to be effectively
    mandatory whenever the plan finalizes through GitHub or GitLab. If the
    seven-row matrix or any pre-filter has dropped ``automated-review`` AND
    the project's CI provider is GitHub or GitLab, raise the violation.

    Returns ``None`` when the guard is a no-op (non-GitHub/GitLab CI, or
    ``automated-review`` is present), otherwise returns the offending CI
    provider identifier (``github`` or ``gitlab``) so the caller can include
    it in the error TOON and decision-log line.
    """
    provider = _read_ci_provider()
    if provider not in {'github', 'gitlab'}:
        return None
    if 'automated-review' in phase_6_steps:
        return None
    return provider


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_compose(args: argparse.Namespace) -> dict[str, Any] | None:
    """Compose and write the execution manifest."""
    plan_id = require_valid_plan_id(args)

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

    commit_strategy = args.commit_strategy if args.commit_strategy is not None else DEFAULT_COMMIT_STRATEGY
    if commit_strategy not in VALID_COMMIT_STRATEGIES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_commit_strategy',
            'message': f'Invalid commit_strategy: {commit_strategy!r}. Must be one of {list(VALID_COMMIT_STRATEGIES)}',
        }

    phase_5_candidates = _split_csv(args.phase_5_steps, DEFAULT_PHASE_5_STEPS)
    phase_6_candidates = _split_csv(args.phase_6_steps, DEFAULT_PHASE_6_STEPS)

    # Pre-filters run before the seven-row matrix. They are orthogonal to the
    # row matrix's change-type / scope / recipe inputs and operate on the
    # candidate list. The order is fixed and documented in
    # standards/decision-rules.md:
    #   1. commit_strategy_none — drop commit-push (and pre-push-quality-gate
    #      and pre-submission-self-review) when no push will occur.
    #   2. pre_push_quality_gate_inactive — drop pre-push-quality-gate when
    #      activation_globs is empty or no modified_files match.
    #   3. pre_submission_self_review_inactive — drop pre-submission-self-review
    #      when modified_files is empty.
    # Each pre-filter returns (filtered_candidates, fired_flag); we log a
    # dedicated decision-log line per fired pre-filter in addition to the row
    # log line emitted by _log_decision below.
    phase_6_candidates, commit_push_omitted = _apply_commit_strategy_none(
        phase_6_candidates, commit_strategy
    )
    phase_6_candidates, pre_push_quality_gate_omitted = _apply_pre_push_quality_gate_inactive(
        phase_6_candidates, plan_id
    )
    phase_6_candidates, pre_submission_self_review_omitted = (
        _apply_pre_submission_self_review_inactive(phase_6_candidates, plan_id)
    )

    affected_files_count = max(0, int(args.affected_files_count or 0))
    recipe_key = args.recipe_key or None

    body, rule = _decide(
        change_type=args.change_type,
        track=args.track,
        scope_estimate=args.scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_candidates=phase_5_candidates,
        phase_6_candidates=phase_6_candidates,
    )

    # Bundle self-modification rule (stacks on top of the seven-row matrix):
    # when the plan's diff edits cached agent/command/skill sources, prepend
    # an early `sync-plugin-cache` step before the first agent-dispatched
    # finalize step so Phase 6 agent dispatches see the worktree's definition,
    # not the stale cache. See lesson 2026-04-26-23-003.
    bundle_change_paths = _read_bundle_change_paths(plan_id)
    bundle_rule_inserted_before = _apply_bundle_self_modification(plan_id, body, bundle_change_paths)

    # Bot-enforcement guard runs AFTER the seven-row matrix and BEFORE manifest
    # persistence. When the project's CI provider is GitHub or GitLab and the
    # final phase_6.steps does not contain `automated-review`, the guard logs the
    # violation and returns an error TOON without writing the manifest.
    final_phase_6_steps = body['phase_6']['steps']
    bot_guard_fired_provider = _apply_bot_enforcement_guard(final_phase_6_steps, plan_id)
    if bot_guard_fired_provider is not None:
        _log_bot_enforcement_guard_fired(plan_id, bot_guard_fired_provider)
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'bot_enforcement_violation',
            'message': (
                'automated-review must remain in the manifest for GitHub/GitLab plans — '
                'review which pre-filter dropped it'
            ),
            'ci_provider': bot_guard_fired_provider,
        }

    manifest = {
        'manifest_version': MANIFEST_VERSION,
        'plan_id': plan_id,
        **body,
    }
    write_manifest(plan_id, manifest)
    if commit_push_omitted:
        _log_commit_push_omitted(plan_id)
    if pre_push_quality_gate_omitted:
        _log_pre_push_quality_gate_omitted(plan_id)
    if pre_submission_self_review_omitted:
        _log_pre_submission_self_review_omitted(plan_id)
    _log_decision(plan_id, rule, body)
    if bundle_rule_inserted_before is not None:
        _log_bundle_self_modification(plan_id, bundle_rule_inserted_before)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'created': True,
        'manifest_version': MANIFEST_VERSION,
        'phase_5': {
            'early_terminate': body['phase_5']['early_terminate'],
            'verification_steps_count': len(body['phase_5']['verification_steps']),
        },
        'phase_6': {
            'steps_count': len(body['phase_6']['steps']),
        },
        'rule_fired': rule,
        'commit_strategy': commit_strategy,
        'commit_push_omitted': commit_push_omitted,
        'pre_push_quality_gate_omitted': pre_push_quality_gate_omitted,
        'pre_submission_self_review_omitted': pre_submission_self_review_omitted,
        'bundle_self_modification_inserted_before': bundle_rule_inserted_before or '',
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


def cmd_validate(args: argparse.Namespace) -> dict[str, Any] | None:
    """Validate manifest schema and (optionally) step IDs against candidate sets."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    errors: list[str] = []

    # Schema checks.
    if manifest.get('manifest_version') != MANIFEST_VERSION:
        errors.append(
            f'manifest_version mismatch: expected {MANIFEST_VERSION}, got {manifest.get("manifest_version")!r}'
        )
    if manifest.get('plan_id') != plan_id:
        errors.append(f'plan_id mismatch: expected {plan_id!r}, got {manifest.get("plan_id")!r}')

    phase_5 = manifest.get('phase_5')
    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_5, dict):
        errors.append('phase_5 section missing or not a mapping')
        phase_5 = {}
    if not isinstance(phase_6, dict):
        errors.append('phase_6 section missing or not a mapping')
        phase_6 = {}

    if 'early_terminate' not in phase_5 or not isinstance(phase_5.get('early_terminate'), bool):
        errors.append('phase_5.early_terminate missing or not a bool')
    p5_steps = phase_5.get('verification_steps', [])
    if not isinstance(p5_steps, list):
        errors.append('phase_5.verification_steps must be a list')
        p5_steps = []
    p6_steps = phase_6.get('steps', [])
    if not isinstance(p6_steps, list):
        errors.append('phase_6.steps must be a list')
        p6_steps = []

    # Step-ID checks (only when caller passes candidate sets).
    p5_unknown: list[str] = []
    p6_unknown: list[str] = []
    if args.phase_5_steps is not None:
        allowed_5 = set(_split_csv(args.phase_5_steps, ()))
        p5_unknown = [s for s in p5_steps if s not in allowed_5]
        if p5_unknown:
            errors.append(f'phase_5.verification_steps contains unknown IDs: {p5_unknown}')
    if args.phase_6_steps is not None:
        allowed_6 = set(_split_csv(args.phase_6_steps, ()))
        p6_unknown = [s for s in p6_steps if s not in allowed_6]
        if p6_unknown:
            errors.append(f'phase_6.steps contains unknown IDs: {p6_unknown}')

    if errors:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': '; '.join(errors),
            'phase_5_unknown_steps_count': len(p5_unknown),
            'phase_5_unknown_steps': p5_unknown,
            'phase_6_unknown_steps_count': len(p6_unknown),
            'phase_6_unknown_steps': p6_unknown,
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'valid': True,
        'phase_5_unknown_steps_count': 0,
        'phase_6_unknown_steps_count': 0,
    }


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Manage the per-plan execution manifest', allow_abbrev=False
    )
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
        '--commit-strategy',
        default=None,
        help='Resolved commit_strategy from phase-5-execute config (per_plan|per_deliverable|none). '
        'When omitted defaults to per_plan. When set to none, commit-push is omitted from phase_6.steps.',
    )

    read_parser = subparsers.add_parser('read', help='Read execution.toon as TOON', allow_abbrev=False)
    add_plan_id_arg(read_parser)

    validate_parser = subparsers.add_parser('validate', help='Validate execution.toon', allow_abbrev=False)
    add_plan_id_arg(validate_parser)
    validate_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated allowed Phase 5 step IDs')
    validate_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated allowed Phase 6 step IDs')

    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    handlers = {
        'compose': cmd_compose,
        'read': cmd_read,
        'validate': cmd_validate,
    }
    handler = handlers[args.command]
    result = handler(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
