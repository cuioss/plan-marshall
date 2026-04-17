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
        super().__init__(
            f'phase_steps_complete failed for phase {phase!r}: '
            + ', '.join(parts)
        )


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
    candidate = (
        bundles
        / 'plan-marshall'
        / 'skills'
        / f'phase-{phase}'
        / 'standards'
        / 'required-steps.md'
    )
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
    tasks = parsed.get('tasks') or []
    if not isinstance(tasks, list):
        return None
    # Reduce each task to the fields that matter for drift detection.
    reduced = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
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
                'n': task.get('number'),
                's': str(task.get('status', '')),
                'o': step_outcomes,
                'd': sorted(str(d) for d in depends),
            }
        )
    reduced.sort(key=lambda x: x.get('n') or 0)
    return _hash_dict(reduced)


def _capture_qgate_open_count(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
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


def _capture_config_hash(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
    # Phase config keys use the `phase-{phase}` naming convention.
    stdout = _run_script(
        [
            'plan-marshall:manage-config:manage-config',
            'plan',
            f'phase-{phase}',
            'get',
            '--trace-plan-id',
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
    ('phase_steps_complete', _always, _capture_phase_steps_complete),
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
