#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Seven-row decision-matrix core for the execution manifest.

Extracted verbatim from ``manage-execution-manifest.py``: the pure candidate
CSV splitter, the seven-row :func:`_decide` matrix, and the status-metadata
reads (:func:`_read_task_queue_active`, :func:`_read_recipe_source`) plus the
docs-only heuristic. None of these functions log or call a test-patched name.
"""

import json
from typing import Any

from _manifest_core import _role_of
from constants import FILE_STATUS
from file_ops import get_plan_dir, read_json


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
    task_queue_active: bool = False,
) -> tuple[dict[str, Any], str]:
    """Apply the seven-row decision matrix.

    Returns the manifest body (under ``phase_5`` / ``phase_6`` keys) plus the
    name of the rule that fired (one of the seven rule keys defined in
    standards/decision-rules.md).

    Rows 2, 3, 5, 6 intersect phase-5 candidates by each candidate's matrix
    ``role:`` rather than by literal step ID. The intersection mechanism is
    structural: each candidate's role is resolved in-code by ``_role_of`` (via
    the ``_CANONICAL_TO_ROLE`` table, keyed on the trailing canonical segment)
    and the matrix matches against a set of role names. See ``_role_of`` and
    ``standards/decision-rules.md`` § Role-Field Intersection.

    Rule 1's ``early_terminate`` predicate also requires ``task_queue_active``
    to be ``False``. When the implementation task queue carries any pending or
    in-progress task, Rule 1 falls through to Rule 7 (default) so phase-5
    iterates the queue normally. Without this guard, an analysis-only plan
    that produces zero affected files but still queues at least one
    deliverable task would short-circuit before TASK-001 runs and skip the
    Step 2.5 worktree materialization as a cascade.
    """

    # Per-compose role-lookup cache: avoid re-reading a candidate's source file
    # when it appears in multiple intersection sites.
    role_cache: dict[str, str | None] = {}

    # Rule 1: early_terminate — analysis without affected files AND no pending
    # / in-progress tasks. Phase 5 is skipped entirely; Phase 6 still runs
    # lessons capture so the analysis doesn't leak insights silently. When the
    # task queue is non-empty, fall through to Rule 7 (default) so phase-5
    # iterates the queue normally — see ``task_queue_active`` rationale above.
    if change_type == 'analysis' and affected_files_count == 0 and not task_queue_active:
        body = {
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [s for s in phase_6_candidates if s in {'lessons-capture', 'adr-propose', 'archive-plan'}],
            },
        }
        return body, 'early_terminate_analysis'

    # Rule 2: recipe path — recipe-driven plans get a slim manifest. The
    # recipe-lesson-cleanup recipe (deliverable 7) sets scope_estimate=surgical
    # so the surgical-style cascades still apply downstream; here we only need
    # to drop the legacy ``ci-wait`` step ID (defensively, against project
    # marshal.json files that still list it as a candidate). Review gates a
    # project opted into (``automated-review`` / ``sonar-roundtrip``) are
    # NEVER silently suppressed by the planner — the recipe label is exactly
    # the case where the bots' job is to catch what humans miss.
    if recipe_key:
        phase_6_steps = [s for s in phase_6_candidates if s not in {'ci-wait'}]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [
                    s for s in phase_5_candidates if _role_of(s, role_cache) in {'quality-gate', 'module-tests'}
                ],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        return body, 'recipe'

    # Rule 3: docs-only — surgical scope plus no test/code expectations. Skip
    # build verification entirely; keep capture + commit + PR + branch cleanup.
    # Only the legacy ``ci-wait`` step ID is subtracted (defensively, against
    # project marshal.json files that still list it). Review gates a project
    # opted into are NEVER silently suppressed by the planner.
    if (
        scope_estimate in ('surgical', 'single_module')
        and change_type in ('tech_debt', 'enhancement')
        and affected_files_count > 0
        and _looks_docs_only(phase_5_candidates, role_cache)
    ):
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [s for s in phase_6_candidates if s not in {'ci-wait'}],
            },
        }
        return body, 'docs_only'

    # Rule 4: tests-only — verification change_type with affected files. Run
    # the module-tests step but skip quality-gate; full Phase 6.
    if change_type == 'verification' and affected_files_count > 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if _role_of(s, role_cache) == 'module-tests'],
            },
            'phase_6': {'steps': list(phase_6_candidates)},
        }
        return body, 'tests_only'

    # Rule 5: surgical + bug_fix / tech_debt — Q-Gate bypass already applies
    # at outline time (deliverable 4). Here the only subtraction is the
    # legacy ``ci-wait`` step ID (defensively, against project marshal.json
    # files that still list it). Review gates a project opted into
    # (``automated-review`` / ``sonar-roundtrip``) are NEVER silently
    # suppressed by the planner — surgical bug_fix / tech_debt is exactly
    # the case where the bots' job is to catch what humans miss.
    if scope_estimate == 'surgical' and change_type in ('bug_fix', 'tech_debt'):
        phase_6_steps = [s for s in phase_6_candidates if s not in {'ci-wait'}]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [
                    s for s in phase_5_candidates if _role_of(s, role_cache) in {'quality-gate', 'module-tests'}
                ],
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
                'steps': [s for s in phase_6_candidates if s in {'lessons-capture', 'adr-propose', 'archive-plan'}],
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


def _read_task_queue_active(plan_id: str) -> bool:
    """Return ``True`` when the plan has at least one pending or in-progress task.

    Reads ``TASK-*.json`` files from ``get_plan_dir(plan_id) / 'tasks'`` and
    checks the ``status`` field on each. The check is intentionally direct
    file I/O — invoking ``manage-tasks list`` as a subprocess would couple
    composer behaviour to the executor and would add cross-script logging
    noise. Returns ``False`` when the tasks directory is missing (no plan
    structure yet) or contains no parseable task files; the composer treats
    that as "no work queued, the analysis-only short-circuit is safe to
    fire". This predicate is the gate that keeps Rule 1 from short-circuiting
    plans where deliverables exist but affected_files happens to be empty at
    compose time.
    """
    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    if not tasks_dir.is_dir():
        return False
    active_statuses = {'pending', 'in_progress'}
    for task_path in tasks_dir.glob('TASK-*.json'):
        try:
            data = read_json(task_path, default=None)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        status = data.get('status')
        if isinstance(status, str) and status in active_statuses:
            return True
    return False


def _read_recipe_source(plan_id: str) -> str | None:
    """Resolve the recipe / lesson provenance surrogate from status metadata.

    ``phase-1-init`` seeds ``status.metadata.plan_source`` with the raw lesson
    id for lesson-derived plans (Step 5b.5) or the literal string ``"recipe"``
    for recipe-routed plans (Step 5c, which also sets ``recipe_key``). Either
    value is the Row 2 recipe signal.

    The composer reads this surrogate directly so recipe / lesson provenance no
    longer depends on the ``phase-4-plan`` agent remembering to forward
    ``--recipe-key`` from ``manage-status read`` — the gap the archived-plan
    audit surfaced as recipe→default drift (lesson/recipe plans composing the
    ``default`` rule because the flag was omitted). This mirrors the audit's own
    surrogate (``audit-archived-plan-retrospectives/scripts/audit.py``
    ``collect_inputs``: a non-empty ``plan_source`` is treated as ``recipe_key``
    for matrix purposes). An explicit ``--recipe-key`` argument still takes
    precedence at the call site in :func:`cmd_compose`.

    Returns the trimmed provenance string, or ``None`` when ``status.json`` is
    absent or its metadata carries no ``plan_source`` / ``recipe_key``.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return None
    # Best-effort: a malformed status.json must degrade to "no provenance"
    # rather than crash compose. read_json returns its default only for a
    # missing file, so a corrupt-but-present file raises here — mirror the
    # OSError / JSONDecodeError guard used by _read_task_queue_active and
    # _read_ci_provider in this module.
    try:
        status = read_json(status_path, default={})
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(status, dict):
        return None
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return None
    for field in ('plan_source', 'recipe_key'):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_request_aspect(plan_id: str) -> str | None:
    """Resolve the request-aspect classification from status metadata.

    ``phase-1-init`` seeds ``status.metadata.request_aspect`` with the aspect
    the ``manage-config aspect-classify`` verb assigned to the request
    (``analysis`` / ``planning`` / ``implementation``). The composer reads this
    surrogate directly so aspect-driven step dropping no longer depends on the
    ``phase-4-plan`` agent remembering to forward ``--aspect`` from
    ``manage-status read`` — the gap that let an ``analysis`` / ``planning``
    request compose the full build/test verification list because the flag was
    omitted. An explicit ``--aspect`` argument still takes precedence at the
    call site in :func:`cmd_compose`, exactly mirroring how ``--recipe-key``
    wins over :func:`_read_recipe_source`.

    Returns the trimmed aspect string, or ``None`` when ``status.json`` is
    absent or its metadata carries no ``request_aspect``.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return None
    # Best-effort: a malformed status.json must degrade to "no aspect" rather
    # than crash compose. read_json returns its default only for a missing
    # file, so a corrupt-but-present file raises here — mirror the OSError /
    # JSONDecodeError guard used by _read_recipe_source in this module.
    try:
        status = read_json(status_path, default={})
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(status, dict):
        return None
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return None
    value = metadata.get('request_aspect')
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _looks_docs_only(phase_5_candidates: list[str], role_cache: dict[str, str | None]) -> bool:
    """Heuristic: docs-only plans don't request module-tests or coverage.

    The composer treats any candidate set whose declared roles include
    neither ``module-tests`` nor ``coverage`` as a docs-only signal. Real
    code-shaped plans always include at least one candidate whose derived role
    is ``module-tests`` (typically ``default:verify:module-tests``).

    Uses the per-compose role cache to avoid re-resolving the same step.
    """
    roles = {_role_of(s, role_cache) for s in phase_5_candidates}
    return 'module-tests' not in roles and 'coverage' not in roles
