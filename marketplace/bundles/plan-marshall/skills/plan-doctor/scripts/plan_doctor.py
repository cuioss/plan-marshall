#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
plan-doctor: post-hoc plan-artifact diagnostics.

Walks ``.plan/local/plans/{plan_id}/tasks/TASK-*.json`` files for one plan or
every plan in the inventory, scans each task's ``title`` and ``description``
for lesson-ID-shaped tokens, and verifies them against the live
``manage-lessons list`` inventory. Tokens that resolve to non-existent
lessons become Q-Gate findings (phase ``5-execute``) and are also surfaced in
a TOON summary on stdout.

In addition to the TASK-level lesson-ID sweep, the ``scan`` verb also runs
three plan-directory-shape diagnostics that surface state escaping the
artifact-bearing checks above:

* ``orphan-plan-directory`` — a subdirectory under ``.plan/local/plans/``
  that lacks ``status.json``, or whose ``status.json`` is present but no
  other plan artifacts (``request.md`` / ``references.json`` /
  ``solution_outline.md``) exist.
* ``stuck-low-confidence-archive`` — a subdirectory under
  ``.plan/local/archived-plans/`` whose ``status.json`` has
  ``metadata.confidence < 95`` AND every phase beyond ``2-refine`` is
  ``pending`` AND no ``metadata.archived_reason`` is recorded.
* ``dangling-worktree`` — a subdirectory under ``.plan/local/worktrees/``
  whose corresponding ``.plan/local/plans/{name}/`` is absent.

These three rules run only on ``--all`` sweeps and on the ``--plan-id``
form when the plan ID matches a worktree or archived plan; their findings
share the same TOON shape as the lesson-ID rows and are also emitted to
the plan-scoped Q-Gate store under phase ``5-execute`` unless ``--no-emit``
is passed.

The scanner helpers (``scan_lesson_id_tokens`` and ``verify_lesson_ids_exist``)
live in ``tools-input-validation`` and are reused verbatim — no duplication.
The live-anchor discipline mandated by lessons 2026-04-29-10-001 and
2026-05-03-21-002 is enforced via the typed exceptions
``LessonInventoryUnavailable`` / ``LessonRegexAnchoringError``: this script
never silently degrades to "no findings" when the inventory is unreachable.

Usage:
    python3 plan_doctor.py scan --plan-id <plan_id> [--no-emit]
    python3 plan_doctor.py scan --all [--no-emit]
    python3 plan_doctor.py scan-task-file --plan-id <plan_id> --task-file <path> [--no-emit]

Exit codes:
    0  success and findings_count == 0
    1  success and findings_count > 0  (or any fatal error)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow direct invocation and testing — executor sets PYTHONPATH for production.
sys.path.insert(0, str(Path(__file__).parent))

from file_ops import base_path, output_toon, output_toon_error, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    LessonInventoryUnavailable,
    LessonRegexAnchoringError,
    add_plan_id_arg,
    is_valid_plan_id,
    parse_args_with_toon_errors,
    scan_lesson_id_tokens,
    verify_lesson_ids_exist,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Phase the findings are recorded under. Phase 5-execute is the canonical
# triage point — see SKILL.md for the rationale.
QGATE_PHASE = '5-execute'

# Reason codes emitted on each finding. ``phantom_lesson_id`` is the
# original TASK-level reason; the remaining three are the plan-directory-
# shape diagnostics described in the module docstring.
REASON_PHANTOM = 'phantom_lesson_id'
REASON_ORPHAN = 'orphan_plan_directory'
REASON_STUCK_LOW_CONF = 'stuck_low_confidence_archive'
REASON_DANGLING_WT = 'dangling_worktree'

# Default confidence threshold. Mirrors ``manage-config`` /
# ``_config_defaults.py`` (``confidence_threshold: 95``). A plan-doctor
# finding fires when an archived plan reports ``metadata.confidence``
# strictly less than this value.
DEFAULT_CONFIDENCE_THRESHOLD = 95.0

# Phase that must be ``done`` before later phases can run. Rule 2 fires only
# when every phase AFTER this one is ``pending`` — i.e. the plan stalled at
# refine without ever reaching outline.
REFINE_PHASE = '2-refine'

# Artifact filenames that, when ANY are present alongside status.json,
# disqualify a plan-dir from Rule 1. Keeping the set explicit (and small)
# matches the request's "minimum-viable plan" contract.
PLAN_DEFINING_ARTIFACTS = ('request.md', 'references.json', 'solution_outline.md')


# ---------------------------------------------------------------------------
# Plan / file discovery
# ---------------------------------------------------------------------------


def _plans_root() -> Path:
    """Return the on-disk plans root: ``.plan/local/plans/`` (or the test override)."""
    return base_path('plans')


def _list_all_plan_ids() -> list[str]:
    """Return every plan ID under the plans root, sorted alphabetically.

    Skips entries that are not directories or whose name fails canonical
    plan-id validation — this avoids tripping on ``.DS_Store``-style noise
    and keeps the output deterministic.
    """
    root = _plans_root()
    if not root.exists():
        return []
    ids: list[str] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not is_valid_plan_id(entry.name):
            continue
        ids.append(entry.name)
    return sorted(ids)


def _task_files_for_plan(plan_id: str) -> list[Path]:
    """Return ``TASK-*.json`` files for ``plan_id`` in stable sort order.

    Returns an empty list when the plan directory exists but holds no tasks
    yet; raises ``FileNotFoundError`` when the plan directory does not exist.
    """
    plan_dir = _plans_root() / plan_id
    if not plan_dir.exists():
        raise FileNotFoundError(plan_id)
    tasks_dir = plan_dir / 'tasks'
    if not tasks_dir.exists():
        return []
    return sorted(tasks_dir.glob('TASK-*.json'))


# ---------------------------------------------------------------------------
# Scanning core
# ---------------------------------------------------------------------------


def _read_task_file(task_path: Path) -> tuple[str, str] | None:
    """Return ``(title, description)`` for a TASK file, or ``None`` on parse failure.

    Missing keys default to the empty string so a malformed task that lacks
    one of the fields still produces a reasonable scan rather than crashing.
    The caller is expected to handle ``None`` (typically by recording a
    ``task_file_unreadable`` warning rather than a finding).
    """
    try:
        raw = task_path.read_text(encoding='utf-8')
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    title = str(data.get('title', '') or '')
    description = str(data.get('description', '') or '')
    return title, description


def _findings_for_file(
    plan_id: str,
    task_path: Path,
    inventory_check: dict[str, bool],
    text: str,
) -> list[dict[str, Any]]:
    """Build phantom-lesson findings for a single file's text.

    ``inventory_check`` is the ``verify_lesson_ids_exist`` result; this
    helper only enumerates the tokens it found in ``text`` so each finding
    points at the exact occurrence (preserving order and duplicates).
    """
    findings: list[dict[str, Any]] = []
    for token in scan_lesson_id_tokens(text):
        if inventory_check.get(token, True):
            # Token is present in the live inventory — no finding.
            continue
        findings.append(
            {
                'plan_id': plan_id,
                'task_file': task_path.name,
                # The TASK-*.json files are JSON; per-line attribution is
                # best-effort. ``1`` is the agreed sentinel — see SKILL.md.
                'line': 1,
                'token': token,
                'rule': REASON_PHANTOM,
                'reason': REASON_PHANTOM,
            }
        )
    return findings


def _scan_one_file(plan_id: str, task_path: Path) -> tuple[bool, list[dict[str, Any]]]:
    """Scan ``task_path`` and return ``(was_readable, findings)``.

    ``was_readable`` distinguishes "file existed but failed to parse" from
    "file scanned cleanly". The summary uses this to count *checked* files
    accurately (an unreadable file is not "checked" in the verification
    sense even though it was visited).
    """
    parsed = _read_task_file(task_path)
    if parsed is None:
        return False, []

    title, description = parsed
    combined = f'{title}\n{description}'
    tokens = scan_lesson_id_tokens(combined)
    if not tokens:
        return True, []

    inventory_check = verify_lesson_ids_exist(tokens)
    findings = _findings_for_file(plan_id, task_path, inventory_check, combined)
    return True, findings


# ---------------------------------------------------------------------------
# Q-Gate emission
# ---------------------------------------------------------------------------


def _emit_finding_to_qgate(finding: dict[str, Any]) -> None:
    """Append a single finding to the plan-scoped Q-Gate store.

    Done in-process via the same ``_findings_core`` API that
    ``manage-findings qgate add`` calls — keeps the data path identical to
    the production write path without spawning a subprocess per finding
    (which would explode runtime on large plans).

    Routes by ``finding['reason']`` so the four rules each produce a
    title/detail that is meaningful in the Q-Gate triage UI without
    forcing the caller to pre-format.
    """
    # Local import — keeps the manage-findings dependency lazy so the
    # ``--no-emit`` path doesn't pay for it.
    from _findings_core import add_qgate_finding  # type: ignore[import-not-found]

    reason = finding.get('reason')
    severity: str = 'warning'
    file_path: str | None = None

    if reason == REASON_PHANTOM:
        title = f'Phantom lesson-ID reference: {finding["token"]}'
        detail = (
            f'Task file {finding["task_file"]} references lesson-ID '
            f'{finding["token"]!r}, which is not present in the live '
            f'manage-lessons inventory.'
        )
        file_path = finding['task_file']
    elif reason == REASON_ORPHAN:
        title = f'Orphan plan directory: {finding["plan_id"]}'
        detail = (
            f'Plan directory {finding["plan_id"]!r} lacks the minimum-viable '
            f'plan artifacts (status.json + at least one of request.md / '
            f'references.json / solution_outline.md). Remediation: '
            f'{finding.get("remediation", "investigate")}.'
        )
    elif reason == REASON_STUCK_LOW_CONF:
        # Information-level only — the archive is a record of an operator
        # decision; surface it for audit but do not auto-remediate.
        severity = 'info'
        title = f'Stuck-low-confidence archive: {finding["plan_id"]}'
        detail = (
            f'Archived plan {finding["plan_id"]!r} reached confidence '
            f'{finding.get("confidence")!s} (threshold '
            f'{finding.get("threshold")!s}), never advanced past '
            f'{REFINE_PHASE}, and carries no archived_reason.'
        )
    elif reason == REASON_DANGLING_WT:
        title = f'Dangling worktree: {finding["plan_id"]}'
        detail = (
            f'Worktree directory {finding["plan_id"]!r} has no corresponding '
            f'plan under .plan/local/plans/. Likely a cleanup race or '
            f'worktree-remove failure on a prior finalize.'
        )
    else:
        # Defensive — unknown reasons still get emitted so they can be
        # triaged manually, but with a clearly synthetic title.
        title = f'plan-doctor finding ({reason}): {finding.get("plan_id", "<unknown>")}'
        detail = str(finding)

    add_qgate_finding(
        plan_id=finding['plan_id'],
        phase=QGATE_PHASE,
        source='qgate',
        finding_type='bug',
        title=title,
        detail=detail,
        file_path=file_path,
        component='plan-marshall:plan-doctor',
        severity=severity,
        iteration=None,
    )


# ---------------------------------------------------------------------------
# Plan-directory-shape diagnostics
# ---------------------------------------------------------------------------


def _read_status_json(plan_dir: Path) -> dict[str, Any] | None:
    """Load and parse ``plan_dir/status.json`` or return ``None``.

    A parse failure is treated identically to a missing file — callers
    that distinguish "missing" from "unreadable" inspect ``status.json``
    existence directly before calling this helper.
    """
    status_path = plan_dir / 'status.json'
    if not status_path.is_file():
        return None
    try:
        data: dict[str, Any] = json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    return data


def _has_any_artifact(plan_dir: Path) -> bool:
    """Return ``True`` if any plan-defining artifact lives in ``plan_dir``."""
    return any((plan_dir / name).is_file() for name in PLAN_DEFINING_ARTIFACTS)


def _logs_has_content(plan_dir: Path) -> bool:
    """Return ``True`` if ``plan_dir/logs/`` contains any files.

    Distinguishes the "rm -rf safe" remediation (no logs) from the
    "archive with reason" remediation (logs present — the partial run
    produced audit trails worth keeping).
    """
    logs = plan_dir / 'logs'
    if not logs.is_dir():
        return False
    return any(logs.iterdir())


def _orphan_remediation(plan_dir: Path, status: dict[str, Any] | None) -> str:
    """Return the suggested remediation token for an orphan plan-dir.

    Three cases (per the lesson body):
      * ``status.json`` present but claims ``current_phase == 6-finalize``
        with no artifacts: ``operator_review`` (stuck finalize on a shell).
      * ``logs/`` has content: ``archive_with_reason``.
      * Otherwise (no logs, no artifacts): ``rm_rf``.
    """
    if status is not None and status.get('current_phase') == '6-finalize':
        return 'operator_review'
    if _logs_has_content(plan_dir):
        return 'archive_with_reason'
    return 'rm_rf'


def _scan_orphan_plan_dirs() -> list[dict[str, Any]]:
    """Return findings for every orphan plan dir under ``.plan/local/plans/``.

    An orphan is a direct child of the plans root that either:
      * has no ``status.json``, or
      * has ``status.json`` but none of ``request.md`` / ``references.json``
        / ``solution_outline.md``.
    """
    root = _plans_root()
    if not root.is_dir():
        return []

    findings: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if not is_valid_plan_id(entry.name):
            continue

        status = _read_status_json(entry)
        if status is None:
            # Missing/unreadable status.json — definite orphan.
            findings.append(
                {
                    'plan_id': entry.name,
                    'rule': REASON_ORPHAN,
                    'reason': REASON_ORPHAN,
                    'remediation': _orphan_remediation(entry, None),
                }
            )
            continue

        if not _has_any_artifact(entry):
            # status.json present but no plan-defining artifacts — the
            # init flow produced a shell and stopped.
            findings.append(
                {
                    'plan_id': entry.name,
                    'rule': REASON_ORPHAN,
                    'reason': REASON_ORPHAN,
                    'remediation': _orphan_remediation(entry, status),
                }
            )
    return findings


def _archived_plans_root() -> Path:
    """Return the on-disk archived-plans root (or test override)."""
    return base_path('archived-plans')


def _scan_stuck_low_confidence_archives(
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Return findings for archived plans stuck below the confidence threshold.

    Trigger conditions (all must hold):
      * archived plan has parseable ``status.json``,
      * every phase AFTER ``2-refine`` is ``pending``,
      * ``metadata.confidence`` is a number strictly less than ``threshold``,
      * ``metadata.archived_reason`` is missing or empty.
    """
    root = _archived_plans_root()
    if not root.is_dir():
        return []

    findings: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        status = _read_status_json(entry)
        if status is None:
            # Archived plan without status.json is itself a defect, but
            # Rule 2 only fires on the specific stuck-low-confidence
            # shape. Skip silently here; the archived inventory has its
            # own consistency checks.
            continue

        metadata = status.get('metadata') or {}
        confidence_raw = metadata.get('confidence')
        if confidence_raw is None:
            continue
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            continue
        if confidence >= threshold:
            continue

        archived_reason = metadata.get('archived_reason')
        if archived_reason:
            # Operator documented the abandonment — Rule 2 is satisfied.
            continue

        phases = status.get('phases') or []
        if not _all_post_refine_pending(phases):
            continue

        findings.append(
            {
                'plan_id': entry.name,
                'rule': REASON_STUCK_LOW_CONF,
                'reason': REASON_STUCK_LOW_CONF,
                'confidence': confidence,
                'threshold': threshold,
            }
        )
    return findings


def _all_post_refine_pending(phases: list[dict[str, Any]]) -> bool:
    """Return ``True`` when every phase after ``2-refine`` is ``pending``.

    Handles the canonical 6-phase shape and any future extension by
    locating ``2-refine`` in the list and inspecting the tail. If
    ``2-refine`` is absent (non-canonical plan), returns ``False`` — Rule 2
    is anchored to the refine-stall pattern and should not fire on
    arbitrary archived plans.
    """
    refine_idx: int | None = None
    for idx, phase in enumerate(phases):
        if phase.get('name') == REFINE_PHASE:
            refine_idx = idx
            break
    if refine_idx is None:
        return False
    tail = phases[refine_idx + 1 :]
    if not tail:
        return False
    return all(p.get('status') == 'pending' for p in tail)


def _worktrees_root() -> Path:
    """Return the on-disk worktrees root (or test override).

    Resolved against the same ``base_path()`` anchor as the plans and
    archived-plans roots so the ``PLAN_BASE_DIR`` test override
    propagates cleanly. This is intentionally distinct from
    ``file_ops.get_worktree_root()``, which resolves against the live
    git checkout — plan-doctor needs the env-overridable form so tests
    can seed a fixture worktree tree under ``tmp_path``.
    """
    return base_path('worktrees')


def _scan_dangling_worktrees() -> list[dict[str, Any]]:
    """Return findings for worktree dirs whose plan-dir is absent.

    Each direct child of the worktree root is checked against
    ``.plan/local/plans/{name}/``. When the corresponding plan dir does
    not exist, the worktree is dangling. Archived plans are NOT a
    rescue — a worktree that survived an archive is still dangling
    because finalize should have removed it.
    """
    root = _worktrees_root()
    if not root.is_dir():
        return []

    plans_root = _plans_root()
    findings: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        # Worktree directory names mirror plan IDs by construction. Skip
        # entries that fail plan-id validation so we don't flag stray
        # operator scratch dirs.
        if not is_valid_plan_id(entry.name):
            continue

        plan_dir = plans_root / entry.name
        if plan_dir.is_dir():
            continue

        findings.append(
            {
                'plan_id': entry.name,
                'rule': REASON_DANGLING_WT,
                'reason': REASON_DANGLING_WT,
            }
        )
    return findings


# ---------------------------------------------------------------------------
# Verb handlers
# ---------------------------------------------------------------------------


def _scan_plans(
    plan_ids: list[str],
    emit_to_qgate: bool,
    run_directory_rules: bool = False,
) -> dict[str, Any]:
    """Scan every TASK file across ``plan_ids`` and return the TOON payload.

    When ``run_directory_rules`` is ``True``, the three plan-directory-shape
    diagnostics (orphan, stuck-low-confidence, dangling-worktree) also
    execute and contribute their findings to the same payload. The
    inventory-shape rules are inventory-wide by nature so they only run
    once per call, regardless of the ``plan_ids`` list length.

    Q-Gate emission for the directory rules requires a valid plan-id under
    ``.plan/local/plans/``. Findings whose ``plan_id`` does not have a
    live plan-dir (the dangling-worktree case and the stuck-low-confidence-
    archive case) are surfaced in the TOON payload but skipped on the
    Q-Gate write path — there is no destination phase store to write to.
    Callers parse the TOON to remediate; Q-Gate emission stays consistent
    with the manage-findings contract.
    """
    checked_files = 0
    findings: list[dict[str, Any]] = []
    plans_scanned = 0

    for plan_id in plan_ids:
        try:
            task_files = _task_files_for_plan(plan_id)
        except FileNotFoundError:
            # Skip plans whose directory disappeared between listing and read
            # rather than crashing the whole sweep — a missing plan is a
            # data-integrity defect in its own right but not the one
            # plan-doctor reports on.
            continue
        plans_scanned += 1
        for task_path in task_files:
            was_readable, file_findings = _scan_one_file(plan_id, task_path)
            if was_readable:
                checked_files += 1
            findings.extend(file_findings)

    if run_directory_rules:
        findings.extend(_scan_orphan_plan_dirs())
        findings.extend(_scan_stuck_low_confidence_archives())
        findings.extend(_scan_dangling_worktrees())

    if emit_to_qgate:
        plans_root = _plans_root()
        for finding in findings:
            # Q-Gate writes require a live plan-dir; skip rule-2/rule-3
            # findings whose plan does not exist under plans/.
            finding_plan_id = finding.get('plan_id')
            if finding_plan_id and (plans_root / finding_plan_id).is_dir():
                _emit_finding_to_qgate(finding)

    return _build_summary(
        checked_files=checked_files,
        plans_scanned=plans_scanned,
        findings=findings,
        emit_to_qgate=emit_to_qgate,
    )


def _scan_single_file(plan_id: str, task_file: Path, emit_to_qgate: bool) -> dict[str, Any]:
    """Scan one explicit TASK file and return the TOON payload."""
    was_readable, findings = _scan_one_file(plan_id, task_file)
    checked_files = 1 if was_readable else 0

    if emit_to_qgate:
        for finding in findings:
            _emit_finding_to_qgate(finding)

    return _build_summary(
        checked_files=checked_files,
        plans_scanned=1,
        findings=findings,
        emit_to_qgate=emit_to_qgate,
    )


def _build_summary(
    *,
    checked_files: int,
    plans_scanned: int,
    findings: list[dict[str, Any]],
    emit_to_qgate: bool,
) -> dict[str, Any]:
    """Assemble the canonical TOON-shaped summary dict."""
    return {
        'status': 'success',
        'checked_files': checked_files,
        'findings_count': len(findings),
        'findings': findings,
        'summary': {
            'plans_scanned': plans_scanned,
            'emit_to_qgate': emit_to_qgate,
        },
    }


# ---------------------------------------------------------------------------
# Argparse handlers
# ---------------------------------------------------------------------------


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle: scan --plan-id <id> | --all"""
    if args.all and args.plan_id:
        output_toon_error(
            'mutually_exclusive',
            'Pass --plan-id OR --all, not both',
        )
        return 1
    if not args.all and not args.plan_id:
        output_toon_error(
            'mutually_exclusive',
            'One of --plan-id or --all is required',
        )
        return 1

    if args.all:
        plan_ids = _list_all_plan_ids()
    else:
        plan_id = args.plan_id
        plan_dir = _plans_root() / plan_id
        if not plan_dir.exists():
            output_toon_error(
                'plan_not_found',
                f'Plan directory does not exist: {plan_id}',
                plan_id=plan_id,
            )
            return 1
        plan_ids = [plan_id]

    # Directory-shape rules (orphan / stuck-low-confidence / dangling-worktree)
    # run only on the ``--all`` form. On a single-plan ``--plan-id`` call
    # the user is targeting one plan's TASK files; sweeping the inventory
    # at the same time would surprise the caller. Operators who want the
    # directory checks against a single plan can pass ``--all`` and grep.
    try:
        payload = _scan_plans(
            plan_ids,
            emit_to_qgate=not args.no_emit,
            run_directory_rules=bool(args.all),
        )
    except LessonInventoryUnavailable as exc:
        output_toon_error('lesson_inventory_unavailable', str(exc))
        return 1
    except LessonRegexAnchoringError as exc:
        output_toon_error('lesson_regex_anchored_to_drifted_inventory', str(exc))
        return 1

    output_toon(payload)
    return 1 if payload['findings_count'] > 0 else 0


def cmd_scan_task_file(args: argparse.Namespace) -> int:
    """Handle: scan-task-file --plan-id <id> --task-file <path>"""
    task_file = Path(args.task_file)
    if not task_file.is_absolute():
        # Resolve relative paths against the current working directory so
        # callers can pass a project-relative path conveniently. We do NOT
        # resolve against the plan root because the file may legitimately
        # live in ``.plan/temp/`` rather than under the plan directory.
        task_file = Path.cwd() / task_file

    if not task_file.exists():
        output_toon_error(
            'task_file_not_found',
            f'Task file does not exist: {task_file}',
            task_file=str(task_file),
        )
        return 1
    if _read_task_file(task_file) is None:
        output_toon_error(
            'task_file_unreadable',
            f'Task file exists but is not parseable JSON: {task_file}',
            task_file=str(task_file),
        )
        return 1

    try:
        payload = _scan_single_file(
            plan_id=args.plan_id,
            task_file=task_file,
            emit_to_qgate=not args.no_emit,
        )
    except LessonInventoryUnavailable as exc:
        output_toon_error('lesson_inventory_unavailable', str(exc))
        return 1
    except LessonRegexAnchoringError as exc:
        output_toon_error('lesson_regex_anchored_to_drifted_inventory', str(exc))
        return 1

    output_toon(payload)
    return 1 if payload['findings_count'] > 0 else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Diagnose plan artifacts (TASK-*.json) for unresolved lesson-ID references',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # scan
    scan_parser = subparsers.add_parser(
        'scan',
        help='Scan TASK-*.json files for one plan or all plans',
        allow_abbrev=False,
    )
    # --plan-id and --all are mutually exclusive but we don't use argparse's
    # mutex group because both are nominally optional and we want to emit a
    # canonical TOON error when neither is supplied (argparse's default
    # message would land on stderr with exit code 2).
    add_plan_id_arg(scan_parser, required=False)
    scan_parser.add_argument(
        '--all',
        action='store_true',
        help='Scan every plan under .plan/local/plans/',
    )
    scan_parser.add_argument(
        '--no-emit',
        action='store_true',
        help='Skip emitting findings to the Q-Gate store; print summary only',
    )
    scan_parser.set_defaults(func=cmd_scan)

    # scan-task-file
    scan_file_parser = subparsers.add_parser(
        'scan-task-file',
        help='Scan a single explicit TASK-*.json file',
        allow_abbrev=False,
    )
    add_plan_id_arg(scan_file_parser)
    scan_file_parser.add_argument(
        '--task-file',
        required=True,
        dest='task_file',
        help='Path to a TASK-*.json file (absolute or cwd-relative)',
    )
    scan_file_parser.add_argument(
        '--no-emit',
        action='store_true',
        help='Skip emitting findings to the Q-Gate store; print summary only',
    )
    scan_file_parser.set_defaults(func=cmd_scan_task_file)

    args = parse_args_with_toon_errors(parser)

    if hasattr(args, 'func'):
        return int(args.func(args))

    parser.print_help()
    return 1


if __name__ == '__main__':
    main()
