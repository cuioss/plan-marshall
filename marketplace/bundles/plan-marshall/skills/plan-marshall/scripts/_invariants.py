# ruff: noqa: I001
"""Pluggable invariant registry for phase_handshake.

Each invariant is a tuple ``(name, applies_fn, capture_fn)``.

- ``applies_fn(plan_id, status_metadata) -> bool`` gates applicability.
- ``capture_fn(plan_id, status_metadata, phase) -> Any | None`` returns the
  captured value (stringified when stored). Returning ``None`` means
  "not applicable" and the column is stored as an empty string.

Adding a new invariant: append one tuple to ``INVARIANTS``. Nothing else
in the handshake plumbing needs to change.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _git_helpers import git_dirty_count, git_head  # type: ignore[import-not-found]
from file_ops import get_base_dir  # type: ignore[import-not-found]
from marketplace_paths import find_marketplace_path  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


class PhaseStepsIncomplete(Exception):
    """Raised by the ``phase_steps_complete`` invariant capture when a phase
    declares ``required-steps.md`` but ``status.metadata.phase_steps[phase]``
    is missing required entries, has entries with ``outcome != 'done'``
    (``skipped`` counts as failure), or has entries stored in the legacy
    bare-string shape (drift — the caller must migrate to the dict shape
    produced by ``mark-step-done``).

    ``cmd_capture`` catches this and surfaces a structured error payload so
    phase skills cannot advance on silently skipped steps.
    """

    def __init__(
        self,
        phase: str,
        missing: list[str],
        not_done: list[dict[str, str]],
        legacy_format: list[str] | None = None,
    ):
        self.phase = phase
        self.missing = missing
        self.not_done = not_done
        self.legacy_format = legacy_format or []
        parts: list[str] = []
        if missing:
            parts.append(f'missing={missing}')
        if not_done:
            parts.append(f'not_done={not_done}')
        if self.legacy_format:
            parts.append(f'legacy_format={self.legacy_format}')
        super().__init__(f'phase_steps_complete failed for phase {phase!r}: ' + ', '.join(parts))


class BlockingFindingsPresent(Exception):
    """Raised by ``_capture_pending_findings_blocking_count`` when capturing
    at a guarded phase boundary while one or more *blocking-type* findings
    remain in ``pending`` resolution.

    The blocking-type partition is read from ``marshal.json`` at
    ``plan.phase-{phase}.blocking_finding_types`` (a list of finding-type
    strings). Resolutions counting as "resolved" are ``fixed``,
    ``suppressed``, ``accepted``, ``taken_into_account``; only ``pending``
    counts toward the block.

    Guarded boundaries (where this exception fires):

    - phase ``6-finalize`` capture (covers the ``5-execute → 6-finalize``
      transition; a phase-5-execute capture for the next phase persists
      first, and the marshal then issues a ``capture --phase 6-finalize``
      which surfaces this exception when blocking counts are non-zero).
    - The intra-finalize boundaries (``automated-review → branch-cleanup``
      and ``sonar-roundtrip → next``) are guarded by the phase-6-finalize
      orchestrator re-issuing ``phase_handshake capture --phase 6-finalize``
      at those checkpoints; the same exception fires.

    All other phase captures **read** the rows (so retrospective analysis
    sees pending counts at each handshake) but do **not** raise — see the
    early-return inside the capture function.

    ``cmd_capture`` translates this into a structured TOON error payload so
    callers cannot persist a row that legitimises a phase advance with
    pending blockers in flight.
    """

    def __init__(
        self,
        phase: str,
        blocking_count: int,
        per_type: dict[str, int],
        blocking_types: list[str],
    ):
        self.phase = phase
        self.blocking_count = blocking_count
        self.per_type = per_type
        self.blocking_types = blocking_types
        super().__init__(
            f'pending_findings_blocking_count failed for phase {phase!r}: '
            f'blocking_count={blocking_count}, blocking_types={blocking_types}, '
            f'per_type={per_type}'
        )


class TaskGraphInvalid(Exception):
    """Raised by the ``task_graph_valid`` invariant capture when the plan's
    task dependency graph has a cycle or a dangling reference (a
    ``depends_on`` entry that does not match any existing task number).

    Shaped like :class:`PhaseStepsIncomplete`: the constructor formats a
    descriptive message and keeps the structured fields (``cycle``,
    ``dangling``) as attributes so callers can surface a structured error
    payload and refuse to persist the handshake row — thereby blocking the
    phase transition on a broken task graph.
    """

    def __init__(
        self,
        cycle: list[str],
        dangling: list[dict[str, str]],
    ):
        self.cycle = cycle
        self.dangling = dangling
        parts: list[str] = []
        if cycle:
            parts.append(f'cycle={cycle}')
        if dangling:
            parts.append(f'dangling={dangling}')
        super().__init__('task_graph_valid failed: ' + ', '.join(parts))


AppliesFn = Callable[[str, dict[str, Any]], bool]
CaptureFn = Callable[[str, dict[str, Any], str], Any]


# --- helpers --------------------------------------------------------------


def _repo_root() -> Path:
    """Main git checkout root inferred from the plan-marshall base directory.

    ``get_base_dir()`` resolves to ``<root>/.plan/local`` in production, so the
    parent chain `.plan/local → .plan → root` identifies the main checkout.
    In tests, ``PLAN_BASE_DIR`` may point somewhere else; in that case we fall
    back to the current working directory.
    """
    try:
        base = get_base_dir()
    except RuntimeError:
        return Path.cwd()
    if base.name == 'local' and base.parent.name == '.plan':
        return base.parent.parent
    return Path.cwd()


def _worktree_applicable(_plan_id: str, metadata: dict[str, Any]) -> bool:
    return bool(metadata.get('worktree_path'))


def _always(_plan_id: str, _metadata: dict[str, Any]) -> bool:
    return True


def _run_script(args: list[str]) -> str | None:
    """Invoke ``execute-script.py`` with ``args`` and return stdout on success."""
    repo = _repo_root()
    executor = repo / '.plan' / 'execute-script.py'
    if not executor.exists():
        return None
    cmd = ['python3', str(executor), *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=60,
            env=os.environ.copy(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _hash_dict(payload: Any) -> str:
    """Stable SHA256 of a JSON-serializable payload (keys sorted recursively)."""
    blob = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


# --- phase required-steps resolution -------------------------------------


def _resolve_required_steps_path(phase: str) -> Path | None:
    """Return the ``required-steps.md`` path for a phase skill, if present.

    Resolution rule (documented in ``references/phase-handshake.md``):
    phase skills live at ``marketplace/bundles/plan-marshall/skills/phase-{phase}``
    by convention — where ``phase`` is the phase key such as ``6-finalize``.
    The required-steps declaration, if the phase opts in, is the sibling file
    ``standards/required-steps.md`` inside that skill directory. Returns
    ``None`` if the marketplace root cannot be located or the file is absent.
    """
    bundles = find_marketplace_path()
    if bundles is None:
        return None
    candidate = bundles / 'plan-marshall' / 'skills' / f'phase-{phase}' / 'standards' / 'required-steps.md'
    return candidate if candidate.is_file() else None


def _parse_required_steps(path: Path) -> list[str]:
    """Parse a ``required-steps.md`` file into an ordered list of step names.

    Format: markdown with one step per line in a bullet item, e.g.::

        - commit-push
        - create-pr
        - record-metrics

    Lines that do not start with ``- `` (after stripping whitespace) are
    ignored. Duplicates are preserved in declaration order; callers should
    treat the list as a set for the completeness check.
    """
    steps: list[str] = []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return steps
    for raw in content.splitlines():
        line = raw.strip()
        if not line.startswith('- '):
            continue
        name = line[2:].strip()
        # Trim inline backticks/formatting if present.
        if name.startswith('`') and name.endswith('`') and len(name) >= 2:
            name = name[1:-1]
        if name:
            steps.append(name)
    return steps


# --- capture functions ---------------------------------------------------


def _capture_main_sha(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    return git_head(_repo_root())


def _capture_main_dirty(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    return git_dirty_count(_repo_root())


def _capture_worktree_sha(_plan_id: str, metadata: dict[str, Any], _phase: str) -> Any:
    wt = metadata.get('worktree_path')
    if not wt:
        return None
    return git_head(wt)


def _capture_worktree_dirty(_plan_id: str, metadata: dict[str, Any], _phase: str) -> Any:
    wt = metadata.get('worktree_path')
    if not wt:
        return None
    return git_dirty_count(wt)


def _capture_task_state_hash(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Drift-detection hash over every task's status, depends_on, and step outcomes.

    ``manage-tasks list`` emits a *tabular* ``tasks_table`` whose reachable
    fields are only ``number, title, domain, profile, deliverable, status,
    progress`` — ``depends_on`` and ``sub_steps``/``steps`` are NOT on that
    table. To access the rich fields this hash depends on, we iterate the
    task numbers from the table and call ``manage-tasks read --task-number N`` per
    task (same pattern as :func:`_capture_task_graph_valid`).

    Returns ``None`` when ``list`` or any ``read`` cannot be parsed, matching
    the other capture functions' "not applicable" semantics. An empty plan
    yields the stable zero-task hash.
    """
    list_stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            plan_id,
        ]
    )
    if list_stdout is None:
        return None
    try:
        list_parsed = parse_toon(list_stdout)
    except Exception:
        return None
    tasks_table = list_parsed.get('tasks_table') or []
    if not isinstance(tasks_table, list):
        return None

    numbers: list[int] = []
    for row in tasks_table:
        if not isinstance(row, dict):
            continue
        n = _normalize_task_ref(row.get('number'))
        if n is not None:
            numbers.append(n)

    reduced: list[dict[str, Any]] = []
    for n in numbers:
        task_stdout = _run_script(
            [
                'plan-marshall:manage-tasks:manage-tasks',
                'read',
                '--plan-id',
                plan_id,
                '--task-number',
                str(n),
            ]
        )
        if task_stdout is None:
            return None
        try:
            task_parsed = parse_toon(task_stdout)
        except Exception:
            return None
        task = task_parsed.get('task')
        if not isinstance(task, dict):
            return None
        steps = task.get('steps') or []
        step_outcomes: list[str] = []
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    step_outcomes.append(str(step.get('status', '')))
        depends = task.get('depends_on') or []
        if not isinstance(depends, list):
            depends = []
        reduced.append(
            {
                'n': n,
                's': str(task.get('status', '')),
                'o': step_outcomes,
                'd': sorted(str(d) for d in depends),
            }
        )

    reduced.sort(key=lambda x: x.get('n') or 0)
    return _hash_dict(reduced)


def _normalize_task_ref(raw: Any) -> int | None:
    """Normalize a ``depends_on`` entry to an integer task number.

    Accepts integers directly and strings of the shape ``TASK-1`` or
    ``TASK-001`` (the two formats produced by ``_build_done_set``).
    Returns ``None`` when the value cannot be parsed so the caller can
    surface it as a dangling reference.
    """
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith('TASK-'):
            text = text[len('TASK-') :]
        if text.isdigit():
            return int(text)
    return None


def _capture_task_graph_valid(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Validate the plan's task dependency graph.

    Loads every task via ``manage-tasks list`` (for the full number set)
    and then ``manage-tasks read`` (for each task's ``depends_on``), builds
    the adjacency graph, and checks two properties:

    - **No cycles** — DFS with WHITE/GRAY/BLACK coloring; a GRAY-hit edge
      closes a cycle and the GRAY stack from entry to hit is captured as
      the cycle path (formatted as ``TASK-{n}`` strings).
    - **No dangling references** — every ``depends_on`` entry must resolve
      to an existing task number.

    On success returns ``_hash_dict(sorted_edges)`` where edges are
    ``(src, dst)`` integer tuples — a stable 16-char hex SHA256 prefix
    matching the pattern used by the other hash invariants. An empty task
    list yields the zero-edge hash (stable, non-raising).

    On failure raises :class:`TaskGraphInvalid` so ``cmd_capture`` refuses
    to persist the handshake row and blocks the phase transition.

    Returns ``None`` if the tasks cannot be loaded (e.g. executor missing
    during a unit-test harness that doesn't provide the plan directory).
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    tasks_table = parsed.get('tasks_table') or parsed.get('tasks') or []
    if not isinstance(tasks_table, list):
        return None

    # Collect task numbers from the list; an empty list is valid (zero-edge).
    numbers: list[int] = []
    for row in tasks_table:
        if not isinstance(row, dict):
            continue
        n = _normalize_task_ref(row.get('number'))
        if n is not None:
            numbers.append(n)

    # Pull depends_on per task via ``read`` — ``list`` does not surface it.
    adjacency: dict[int, list[int | None]] = {n: [] for n in numbers}
    dangling: list[dict[str, str]] = []
    for n in numbers:
        task_stdout = _run_script(
            [
                'plan-marshall:manage-tasks:manage-tasks',
                'read',
                '--plan-id',
                plan_id,
                '--task-number',
                str(n),
            ]
        )
        if task_stdout is None:
            continue
        try:
            task_parsed = parse_toon(task_stdout)
        except Exception:
            continue
        task = task_parsed.get('task') or {}
        if not isinstance(task, dict):
            continue
        deps = task.get('depends_on') or []
        if not isinstance(deps, list):
            continue
        for raw in deps:
            target = _normalize_task_ref(raw)
            if target is None or target not in adjacency:
                dangling.append({'task': f'TASK-{n}', 'missing': str(raw)})
                continue
            adjacency[n].append(target)

    # DFS cycle detection (WHITE=0, GRAY=1, BLACK=2). Capture the first cycle
    # found, formatted as TASK-{n} strings from entry node through closing edge.
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[int, int] = dict.fromkeys(adjacency, WHITE)
    cycle_path: list[str] = []

    def _dfs(start: int) -> bool:
        stack: list[tuple[int, int]] = [(start, 0)]
        path: list[int] = []
        color[start] = GRAY
        path.append(start)
        while stack:
            node, idx = stack[-1]
            neighbors = adjacency.get(node, [])
            if idx >= len(neighbors):
                color[node] = BLACK
                stack.pop()
                if path:
                    path.pop()
                continue
            # Advance pointer for this stack frame before recursing.
            stack[-1] = (node, idx + 1)
            nxt = neighbors[idx]
            if nxt is None:
                continue
            state = color.get(nxt, WHITE)
            if state == GRAY:
                # Close the cycle from the first occurrence of nxt in path.
                try:
                    cut = path.index(nxt)
                except ValueError:
                    cut = 0
                cycle_nodes = path[cut:] + [nxt]
                cycle_path.extend(f'TASK-{m}' for m in cycle_nodes)
                return True
            if state == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append((nxt, 0))
        return False

    for start in sorted(adjacency.keys()):
        if color[start] == WHITE:
            if _dfs(start):
                break

    if cycle_path or dangling:
        raise TaskGraphInvalid(cycle=cycle_path, dangling=dangling)

    edges: list[tuple[int, int]] = []
    for src in sorted(adjacency.keys()):
        for dst in adjacency[src]:
            if dst is None:
                continue
            edges.append((src, dst))
    edges.sort()
    # JSON serialization turns tuples into lists; normalize up front for
    # deterministic hashing across Python versions.
    return _hash_dict([list(edge) for edge in edges])


def _capture_pending_tasks_count(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Count of tasks currently in ``status: pending`` for this plan.

    Drives the phase-5-execute transition guard: if tasks remain pending when
    the orchestrator tries to transition to ``6-finalize``, the guard refuses.
    Captured every phase so retrospective analysis sees the queue size at each
    boundary; non-zero values at later phases indicate orphaned fix tasks.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'list',
            '--status',
            'pending',
            '--plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    rows = parsed.get('tasks_table') or parsed.get('tasks') or []
    if not isinstance(rows, list):
        return None
    return len(rows)


def _capture_qgate_open_count(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
    if phase == '1-init':
        # Q-Gate findings are scoped to phases 2-refine onward; manage-findings
        # rejects --phase 1-init, so short-circuit to a trivially-zero result.
        return 0
    stdout = _run_script(
        [
            'plan-marshall:manage-findings:manage-findings',
            'qgate',
            'query',
            '--plan-id',
            plan_id,
            '--phase',
            phase,
            '--resolution',
            'pending',
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    count = parsed.get('filtered_count')
    if isinstance(count, int):
        return count
    if isinstance(count, str) and count.isdigit():
        return int(count)
    return None


# --- pending-finding invariants ------------------------------------------

# All finding types tracked by ``manage-findings`` (mirrors the taxonomy in
# ``tools-file-ops/scripts/constants.py``). Kept inline so the invariant
# capture has no run-time dependency on the constants module beyond the
# existing executor hop, and so the row contract stays stable when new
# types are added centrally (the registry simply reads the per-phase config
# slot to decide which types block).
_PENDING_FINDING_TYPES: tuple[str, ...] = (
    'bug',
    'improvement',
    'anti-pattern',
    'triage',
    'tip',
    'insight',
    'best-practice',
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'pr-comment',
)

# Phases at which a non-zero ``pending_findings_blocking_count`` raises
# :class:`BlockingFindingsPresent` to refuse the capture. Other phases
# capture the row passively (read-only — see capture function).
_BLOCKING_BOUNDARIES: frozenset[str] = frozenset({'6-finalize'})


def _query_pending_count_for_type(plan_id: str, finding_type: str) -> int | None:
    """Return the count of ``pending`` findings for ``finding_type``.

    Drives both the per-type breakdown and the blocking-count summary.
    Routes through ``manage-findings query --type T --resolution pending``
    so it picks up the per-type JSONL split introduced in TASK-1 without
    duplicating the query logic.

    Returns ``None`` when the executor cannot be reached or the output is
    unparseable so the calling capture can surface "not applicable" via the
    existing capture-returns-None contract.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-findings:manage-findings',
            'query',
            '--plan-id',
            plan_id,
            '--type',
            finding_type,
            '--resolution',
            'pending',
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    count = parsed.get('filtered_count')
    if isinstance(count, int):
        return count
    if isinstance(count, str) and count.isdigit():
        return int(count)
    # Some manage-findings paths emit ``count`` instead of ``filtered_count``.
    alt = parsed.get('count')
    if isinstance(alt, int):
        return alt
    if isinstance(alt, str) and alt.isdigit():
        return int(alt)
    return None


def _read_blocking_finding_types(plan_id: str, phase: str) -> list[str] | None:
    """Read ``plan.phase-{phase}.blocking_finding_types`` from ``marshal.json``.

    Uses ``manage-config plan phase-{phase} get --field blocking_finding_types``.
    Returns ``None`` when the field is absent or cannot be parsed — callers
    treat ``None`` as "no blocking partition configured for this phase, so
    nothing blocks". An empty list explicitly configures "no blocking
    types" and is returned as ``[]``.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-config:manage-config',
            'plan',
            f'phase-{phase}',
            'get',
            '--field',
            'blocking_finding_types',
            '--audit-plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    raw = parsed.get('value')
    if raw is None:
        return None
    # ``manage-config`` serializes lists as TOON arrays which ``parse_toon``
    # decodes to Python lists. Tolerate the comma-separated string fallback
    # for robustness.
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    if isinstance(raw, str):
        items = [item.strip() for item in raw.split(',') if item.strip()]
        return items
    return None


def _capture_pending_findings_by_type(
    plan_id: str,
    _metadata: dict[str, Any],
    _phase: str,
) -> Any:
    """Per-type breakdown of pending findings, captured at every boundary.

    Returns a stable, sorted compact summary of the form
    ``"bug=N,build-error=N,..."`` covering every type the project knows
    about. Returns ``None`` when no per-type query succeeds — callers
    interpret ``None`` as "not applicable" and skip the column.

    This row is always passive: it never raises. Retrospective analysis
    reads it to see the queue at each phase boundary; the blocking
    decision is the sole responsibility of
    :func:`_capture_pending_findings_blocking_count`.
    """
    parts: list[str] = []
    any_value = False
    for finding_type in _PENDING_FINDING_TYPES:
        count = _query_pending_count_for_type(plan_id, finding_type)
        if count is None:
            # Skip silently — partial visibility is acceptable for the
            # passive row; the blocking row enforces correctness.
            continue
        any_value = True
        parts.append(f'{finding_type}={count}')
    if not any_value:
        return None
    return ','.join(parts)


def _capture_pending_findings_blocking_count(
    plan_id: str,
    _metadata: dict[str, Any],
    phase: str,
) -> Any:
    """Sum of pending findings whose type is *blocking* for ``phase``.

    Reads the per-phase ``blocking_finding_types`` partition from
    ``marshal.json``; if the slot is unset, no types are considered
    blocking for that phase and the count is ``0``. Otherwise, sums the
    pending counts across every configured blocking type.

    At a *guarded boundary* (``phase`` in :data:`_BLOCKING_BOUNDARIES`),
    a non-zero count raises :class:`BlockingFindingsPresent` so
    ``cmd_capture`` refuses to persist the handshake row — that gates the
    phase transition. At every other phase the count is returned as an int
    so retrospective analysis sees the queue size at each boundary; the
    transition itself is not blocked.

    Returns ``None`` when the executor cannot be reached for any of the
    underlying queries — matches the other captures' "not applicable"
    contract and keeps the column empty in stored rows.
    """
    blocking_types = _read_blocking_finding_types(plan_id, phase)
    if blocking_types is None:
        # No partition configured for this phase → nothing blocks; record 0.
        return 0
    if not blocking_types:
        return 0

    per_type: dict[str, int] = {}
    total = 0
    for finding_type in blocking_types:
        count = _query_pending_count_for_type(plan_id, finding_type)
        if count is None:
            # Partial query failure — fall back to "not applicable" rather
            # than under-counting and silently letting a transition
            # advance.
            return None
        per_type[finding_type] = count
        total += count

    if total > 0 and phase in _BLOCKING_BOUNDARIES:
        raise BlockingFindingsPresent(
            phase=phase,
            blocking_count=total,
            per_type=per_type,
            blocking_types=list(blocking_types),
        )
    return total


def _capture_config_hash(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
    # Phase config keys use the `phase-{phase}` naming convention.
    stdout = _run_script(
        [
            'plan-marshall:manage-config:manage-config',
            'plan',
            f'phase-{phase}',
            'get',
            '--audit-plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return _hash_dict(stdout.strip())
    return _hash_dict(parsed)


def _capture_phase_steps_complete(
    _plan_id: str,
    metadata: dict[str, Any],
    phase: str,
) -> Any:
    """Verify that every step in the phase's ``required-steps.md`` is marked
    ``done`` inside ``status.metadata.phase_steps[phase]``.

    - If the phase has no ``required-steps.md``, returns ``None`` (no-op —
      the column stays empty and is ignored during verify).
    - On success, returns the SHA256 of the stable-key required step list so
      drift verify can still detect a changed required set between capture
      and verify.
    - On failure (any required step missing, recorded with outcome !=
      ``done``, or stored in the legacy bare-string shape), raises
      ``PhaseStepsIncomplete`` so ``cmd_capture`` can surface a structured
      error and refuse to persist the row.

    ``skipped`` explicitly counts as failure per the cwd handshake spec —
    only ``done`` passes. Bare-string entries are rejected as legacy drift:
    ``mark-step-done`` now stores dicts of shape
    ``{"outcome": ..., "display_detail": ...}`` and there is no automatic
    migration for the old shape.
    """
    required_path = _resolve_required_steps_path(phase)
    if required_path is None:
        return None
    required = _parse_required_steps(required_path)
    if not required:
        return None

    phase_steps = metadata.get('phase_steps') or {}
    phase_entry: dict[str, Any] = {}
    if isinstance(phase_steps, dict):
        entry = phase_steps.get(phase)
        if isinstance(entry, dict):
            phase_entry = entry

    missing: list[str] = []
    not_done: list[dict[str, str]] = []
    legacy_format: list[str] = []
    for step in required:
        if step not in phase_entry:
            missing.append(step)
            continue
        raw = phase_entry.get(step)
        if isinstance(raw, str):
            legacy_format.append(step)
            continue
        outcome = raw.get('outcome') if isinstance(raw, dict) else None
        if outcome != 'done':
            not_done.append({'step': step, 'outcome': str(outcome or '')})

    if missing or not_done or legacy_format:
        raise PhaseStepsIncomplete(phase, missing, not_done, legacy_format)

    # Deterministic hash of the required step set for drift detection. We
    # hash the sorted list so registering a new required step (which also
    # requires a new capture) shows up as drift on verify of an older row.
    return _hash_dict(sorted(required))


# --- registry ------------------------------------------------------------

INVARIANTS: list[tuple[str, AppliesFn, CaptureFn]] = [
    ('main_sha', _always, _capture_main_sha),
    ('main_dirty', _always, _capture_main_dirty),
    ('worktree_sha', _worktree_applicable, _capture_worktree_sha),
    ('worktree_dirty', _worktree_applicable, _capture_worktree_dirty),
    ('task_state_hash', _always, _capture_task_state_hash),
    ('qgate_open_count', _always, _capture_qgate_open_count),
    ('config_hash', _always, _capture_config_hash),
    ('pending_tasks_count', _always, _capture_pending_tasks_count),
    ('phase_steps_complete', _always, _capture_phase_steps_complete),
    ('task_graph_valid', _always, _capture_task_graph_valid),
    ('pending_findings_by_type', _always, _capture_pending_findings_by_type),
    ('pending_findings_blocking_count', _always, _capture_pending_findings_blocking_count),
]


def capture_all(plan_id: str, metadata: dict[str, Any], phase: str) -> dict[str, Any]:
    """Run every applicable invariant and return name -> captured value.

    Non-applicable invariants are omitted from the return dict so callers can
    store empty strings or skip comparison during verify.
    """
    captured: dict[str, Any] = {}
    for name, applies_fn, capture_fn in INVARIANTS:
        if not applies_fn(plan_id, metadata):
            continue
        value = capture_fn(plan_id, metadata, phase)
        if value is None:
            continue
        captured[name] = value
    return captured
