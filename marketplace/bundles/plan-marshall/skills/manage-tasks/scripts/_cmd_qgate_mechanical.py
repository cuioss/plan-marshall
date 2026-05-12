#!/usr/bin/env python3
"""Q-Gate mechanical checks for phase-4-plan Step 9.

Pure regex + graph + filesystem deterministic checks over the just-written
tasks and parent deliverables. Each failure becomes a Q-Gate finding under
``--source qgate`` so phase-4-plan's existing aggregate loop consumes it
without modification; the script's return TOON reports per-check counts
and an ``ambiguous`` flag the caller uses to decide whether the LLM
``cross.q-gate-validation`` dispatch still needs to fire.

Six checks:
  1. coverage              — every deliverable has >= 1 task; tasks reference real deliverables
  2. skill_resolution      — every non-verification task has domain + valid ``bundle:skill`` shape
  3. acyclic               — depends_on graph is a DAG (Kahn-style topological pass)
  4. files_exist           — every step.target on non-verification tasks resolves on disk
  5. keyword_drift         — planning-domain keywords in description absent from deliverable haystack
  6. structural_token_drift — TASK-NNN numbering monotonic starting at 001 with no gaps
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from _findings_core import add_qgate_finding  # type: ignore[import-not-found]
from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverables,
    parse_document_sections,
)
from _tasks_core import get_all_tasks, get_tasks_dir
from constants import FILE_SOLUTION_OUTLINE  # type: ignore[import-not-found]
from file_ops import get_plan_dir  # type: ignore[import-not-found]
from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]

_PHASE = '4-plan'
_QGATE_SOURCE = 'qgate'
_FINDING_TYPE = 'triage'

# Planning-domain keywords whose presence in a task.description but absence
# from the parent deliverable haystack indicates compound-word drift
# (PR review / CI etc. is planning vocabulary leaking into task narrative).
# Mirrors the existing inline Step 9 prose in phase-4-plan/SKILL.md.
_PLANNING_KEYWORDS: tuple[str, ...] = (
    'PR review',
    'CI',
    'merge comments',
    'pipeline',
    'automated review',
    'build check',
    'review comments',
)

_SKILL_SHAPE_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*:[a-zA-Z0-9][a-zA-Z0-9_.-]*$')
_TASK_FILENAME_RE = re.compile(r'^TASK-(\d{3})\.json$')


def _emit_finding(
    plan_id: str,
    title: str,
    detail: str,
    file_path: str | None = None,
    emit: bool = True,
) -> int:
    """Emit one Q-Gate finding via the shared add_qgate_finding API.

    Returns 1 when a record is appended (status: success), 0 when the call
    is a no-op (dedup, or --no-emit).
    """
    if not emit:
        return 0
    result = add_qgate_finding(
        plan_id=plan_id,
        phase=_PHASE,
        source=_QGATE_SOURCE,
        finding_type=_FINDING_TYPE,
        title=title,
        detail=detail,
        file_path=file_path,
        component='plan-marshall:manage-tasks:qgate-mechanical-checks',
        severity='warning',
        iteration=None,
    )
    return 1 if result.get('status') == 'success' else 0


def _load_deliverables(plan_id: str) -> tuple[list[dict[str, Any]], bool]:
    """Read solution_outline.md and extract deliverables.

    Returns ``(deliverables, parseable)`` — ``parseable`` is False when the
    outline is missing or its Deliverables section can't be located, in
    which case the caller flips ``ambiguous=true`` so the LLM dispatch
    re-evaluates rather than the mechanical script declaring victory.
    """
    outline_path = get_plan_dir(plan_id) / FILE_SOLUTION_OUTLINE
    if not outline_path.exists():
        return [], False
    try:
        content = outline_path.read_text(encoding='utf-8')
    except OSError:
        return [], False
    sections = parse_document_sections(content)
    deliverables_section = sections.get('deliverables')
    if not isinstance(deliverables_section, str) or not deliverables_section.strip():
        return [], False
    try:
        return extract_deliverables(deliverables_section), True
    except (ValueError, AttributeError):
        return [], False


def _check_coverage(
    plan_id: str,
    tasks: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
    emit: bool,
) -> tuple[int, int]:
    """Coverage: every deliverable has >= 1 task; tasks reference real deliverables.

    Returns ``(failed_count, findings_emitted)``.
    """
    failed = 0
    emitted = 0

    deliverable_numbers = {int(d['number']) for d in deliverables}
    task_deliverables: set[int] = {
        int(t.get('deliverable', 0)) for t in tasks if int(t.get('deliverable', 0)) > 0
    }

    for d in sorted(deliverable_numbers):
        if d not in task_deliverables:
            failed += 1
            emitted += _emit_finding(
                plan_id,
                title=f'coverage: deliverable {d} has no tasks',
                detail=(
                    f'Deliverable {d} from solution_outline.md has no associated '
                    f'tasks. Phase-4-plan must create at least one task per '
                    f'deliverable (multi-profile deliverables produce N tasks).'
                ),
                emit=emit,
            )

    for t in tasks:
        deliverable = int(t.get('deliverable', 0))
        # deliverable=0 is the holistic-task sentinel; do not flag as orphan.
        if deliverable == 0:
            continue
        if deliverable not in deliverable_numbers:
            failed += 1
            emitted += _emit_finding(
                plan_id,
                title=f'coverage: TASK-{t["number"]:03d} references unknown deliverable {deliverable}',
                detail=(
                    f'TASK-{t["number"]:03d} {t.get("title", "?")!r} carries '
                    f'deliverable={deliverable}, but the solution outline has no '
                    f'such deliverable. Either fix the task\'s deliverable field '
                    f'or add the missing deliverable to solution_outline.md.'
                ),
                emit=emit,
            )

    return failed, emitted


def _check_skill_resolution(
    plan_id: str,
    tasks: list[dict[str, Any]],
    emit: bool,
) -> tuple[int, int]:
    """Skill resolution: non-verification tasks have ``domain`` + ``bundle:skill`` shape.

    Empty ``skills`` is allowed (Step 5 records its own Q-Gate finding for
    missing skills_by_profile entries), so this check focuses on shape
    integrity for entries that are present.
    """
    failed = 0
    emitted = 0
    for t in tasks:
        profile = (t.get('profile') or '').strip()
        number = t['number']
        domain = (t.get('domain') or '').strip()
        if profile != 'verification' and not domain:
            failed += 1
            emitted += _emit_finding(
                plan_id,
                title=f'skill_resolution: TASK-{number:03d} missing domain',
                detail=(
                    f'TASK-{number:03d} {t.get("title", "?")!r} (profile={profile!r}) '
                    f'has no domain. Domain is required for non-verification tasks '
                    f'so the executor can resolve workflow skills.'
                ),
                emit=emit,
            )

        for skill in t.get('skills', []) or []:
            if isinstance(skill, str) and not _SKILL_SHAPE_RE.match(skill):
                failed += 1
                emitted += _emit_finding(
                    plan_id,
                    title=f'skill_resolution: TASK-{number:03d} skill {skill!r} not in bundle:skill shape',
                    detail=(
                        f'TASK-{number:03d} {t.get("title", "?")!r} declares skill '
                        f'{skill!r}, which does not match the required '
                        f'``bundle:skill`` form (alphanumeric + dashes/underscores '
                        f'around a single colon). Fix the task definition or '
                        f'rename the skill before phase-5-execute consumes it.'
                    ),
                    emit=emit,
                )

    return failed, emitted


def _check_acyclic(
    plan_id: str,
    tasks: list[dict[str, Any]],
    emit: bool,
) -> tuple[int, int]:
    """Acyclic: depends_on across all tasks forms a DAG.

    Uses Kahn's algorithm — any node with non-zero remaining in-degree
    after processing belongs to a cycle. One finding per cycle root keeps
    the noise bounded for chained-cycle cases.
    """
    failed = 0
    emitted = 0

    by_id: dict[str, dict[str, Any]] = {}
    for t in tasks:
        n = int(t['number'])
        by_id[f'TASK-{n}'] = t
        by_id[f'TASK-{n:03d}'] = t

    in_degree: dict[int, int] = {int(t['number']): 0 for t in tasks}
    graph: dict[int, list[int]] = defaultdict(list)
    for t in tasks:
        for dep in t.get('depends_on', []) or []:
            dep_task = by_id.get(dep)
            if dep_task is None:
                # Missing dependency surfaces under coverage / other checks;
                # do not double-report here.
                continue
            dep_n = int(dep_task['number'])
            graph[dep_n].append(int(t['number']))
            in_degree[int(t['number'])] += 1

    queue = [n for n, d in in_degree.items() if d == 0]
    visited = 0
    while queue:
        n = queue.pop()
        visited += 1
        for m in graph[n]:
            in_degree[m] -= 1
            if in_degree[m] == 0:
                queue.append(m)

    if visited < len(tasks):
        cycle_members = sorted(n for n, d in in_degree.items() if d > 0)
        failed = 1
        emitted += _emit_finding(
            plan_id,
            title=f'acyclic: depends_on graph contains a cycle ({len(cycle_members)} tasks)',
            detail=(
                f'Tasks {", ".join(f"TASK-{n:03d}" for n in cycle_members)} '
                f'participate in a depends_on cycle. Phase-5-execute would loop '
                f'indefinitely; break the cycle in task definitions before '
                f'phase-4 transitions.'
            ),
            emit=emit,
        )

    return failed, emitted


def _check_files_exist(
    plan_id: str,
    tasks: list[dict[str, Any]],
    repo_root: Path,
    emit: bool,
) -> tuple[int, int]:
    """Files exist: every step.target on non-verification tasks resolves on disk."""
    failed = 0
    emitted = 0
    for t in tasks:
        if (t.get('profile') or '').strip() == 'verification':
            continue
        number = t['number']
        for step in t.get('steps', []) or []:
            if not isinstance(step, dict):
                continue
            target = (step.get('target') or '').strip()
            if not target:
                continue
            candidate = repo_root / target if not target.startswith('/') else Path(target)
            if not candidate.exists():
                failed += 1
                emitted += _emit_finding(
                    plan_id,
                    title=f'files_exist: TASK-{number:03d} step.target {target!r} does not exist',
                    detail=(
                        f'TASK-{number:03d} {t.get("title", "?")!r} declares step '
                        f'target {target!r}, which is not present on disk. '
                        f'Phase-4-plan steps must list paths from the deliverable\'s '
                        f'Affected files section; create the file or correct the '
                        f'path before phase-5-execute reads it.'
                    ),
                    file_path=target,
                    emit=emit,
                )

    return failed, emitted


def _build_haystack(deliverable: dict[str, Any]) -> str:
    """Concatenate a deliverable's fields into one plain-text haystack.

    Mirrors the existing Step 9 keyword-drift recipe in phase-4-plan/SKILL.md.
    """
    parts: list[str] = []
    title = deliverable.get('title')
    if isinstance(title, str):
        parts.append(title)
    metadata = deliverable.get('metadata')
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            parts.append(f'{key}: {value}')
    profiles = deliverable.get('profiles')
    if isinstance(profiles, list):
        parts.extend(str(p) for p in profiles)
    affected = deliverable.get('affected_files')
    if isinstance(affected, list):
        parts.extend(str(f) for f in affected)
    verification = deliverable.get('verification')
    if isinstance(verification, dict):
        for value in verification.values():
            parts.append(str(value))
    return ' '.join(parts)


def _check_keyword_drift(
    plan_id: str,
    tasks: list[dict[str, Any]],
    deliverables: list[dict[str, Any]],
    emit: bool,
) -> tuple[int, int]:
    """Keyword drift: planning-domain keywords appear in description but not in haystack."""
    failed = 0
    emitted = 0
    by_number: dict[int, dict[str, Any]] = {int(d['number']): d for d in deliverables}

    for t in tasks:
        description = (t.get('description') or '').strip()
        if not description:
            continue
        deliverable = by_number.get(int(t.get('deliverable', 0)))
        if deliverable is None:
            continue
        haystack = _build_haystack(deliverable)
        for keyword in _PLANNING_KEYWORDS:
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            if pattern.search(description) and not pattern.search(haystack):
                failed += 1
                excerpt = description[:120].replace('\n', ' ')
                emitted += _emit_finding(
                    plan_id,
                    title=(
                        f'keyword_drift: TASK-{t["number"]:03d} uses '
                        f'{keyword!r} not present in deliverable outline'
                    ),
                    detail=(
                        f'{excerpt}; deliverable {deliverable["number"]} '
                        f'outline does not mention {keyword!r}'
                    ),
                    emit=emit,
                )

    return failed, emitted


def _check_structural_token_drift(
    plan_id: str,
    task_dir: Path,
    emit: bool,
) -> tuple[int, int]:
    """Structural token drift: TASK-NNN file numbering monotonic, no gaps."""
    failed = 0
    emitted = 0

    numbers: list[int] = []
    if task_dir.exists():
        for f in sorted(task_dir.glob('TASK-*.json')):
            match = _TASK_FILENAME_RE.match(f.name)
            if match:
                numbers.append(int(match.group(1)))

    if not numbers:
        return 0, 0

    numbers.sort()
    expected = list(range(1, numbers[-1] + 1))
    missing = [n for n in expected if n not in numbers]
    if missing:
        failed = len(missing)
        emitted += _emit_finding(
            plan_id,
            title=f'structural_token_drift: TASK numbering has {len(missing)} gap(s)',
            detail=(
                f'Existing task files {", ".join(f"TASK-{n:03d}" for n in numbers)} '
                f'leave gap(s) at {", ".join(f"TASK-{n:03d}" for n in missing)}. '
                f'TASK numbering must be monotonic with no gaps so consumers can '
                f'iterate the directory deterministically.'
            ),
            emit=emit,
        )
    if numbers[0] != 1:
        failed += 1
        emitted += _emit_finding(
            plan_id,
            title='structural_token_drift: TASK numbering does not start at 001',
            detail=(
                f'Lowest task file is TASK-{numbers[0]:03d}; numbering must start '
                f'at TASK-001 so phase-5-execute and phase-6-finalize iteration '
                f'remains deterministic.'
            ),
            emit=emit,
        )

    return failed, emitted


def cmd_qgate_mechanical(args) -> dict[str, Any]:
    """Run the six mechanical Q-Gate checks for a plan.

    Returns a TOON-shaped dict with per-check counts and overall pass/fail
    aggregate so the caller can decide whether the LLM ``cross.q-gate-validation``
    dispatch still needs to fire (only when ``ambiguous=true`` or another
    judgement-side validator is in scope).
    """
    plan_id: str = args.plan_id
    emit: bool = not getattr(args, 'no_emit', False)

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    repo_root = git_main_checkout_root() or plan_dir.resolve().parent.parent.parent

    task_dir = get_tasks_dir(plan_id)
    all_tasks = [task for _path, task in get_all_tasks(task_dir)]
    deliverables, parseable = _load_deliverables(plan_id)

    findings_emitted = 0
    checks: dict[str, dict[str, int]] = {}

    coverage_failed, e = _check_coverage(plan_id, all_tasks, deliverables, emit=emit)
    findings_emitted += e
    checks['coverage'] = {'failed': coverage_failed}

    skill_failed, e = _check_skill_resolution(plan_id, all_tasks, emit=emit)
    findings_emitted += e
    checks['skill_resolution'] = {'failed': skill_failed}

    acyclic_failed, e = _check_acyclic(plan_id, all_tasks, emit=emit)
    findings_emitted += e
    checks['acyclic'] = {'failed': acyclic_failed}

    files_failed, e = _check_files_exist(plan_id, all_tasks, repo_root, emit=emit)
    findings_emitted += e
    checks['files_exist'] = {'failed': files_failed}

    keyword_failed, e = _check_keyword_drift(plan_id, all_tasks, deliverables, emit=emit)
    findings_emitted += e
    checks['keyword_drift'] = {'failed': keyword_failed}

    structural_failed, e = _check_structural_token_drift(plan_id, task_dir, emit=emit)
    findings_emitted += e
    checks['structural_token_drift'] = {'failed': structural_failed}

    total_failed = sum(c['failed'] for c in checks.values())

    # ``ambiguous`` flips when the script could not evaluate a check that
    # depended on parseable inputs — coverage and keyword_drift both fall
    # silent when solution_outline.md is missing or malformed, so the
    # caller must re-run the LLM judgement instead of trusting the zero.
    ambiguous = not parseable

    return {
        'status': 'success',
        'plan_id': plan_id,
        'tasks_scanned': len(all_tasks),
        'deliverables_scanned': len(deliverables),
        'checks': checks,
        'total_failed': total_failed,
        'findings_emitted': findings_emitted,
        'ambiguous': ambiguous,
        'emit': emit,
    }
