#!/usr/bin/env python3
"""
plan-doctor: post-hoc plan-artifact diagnostics.

Walks ``.plan/local/plans/{plan_id}/tasks/TASK-*.json`` files for one plan or
every plan in the inventory, scans each task's ``title`` and ``description``
for lesson-ID-shaped tokens, and verifies them against the live
``manage-lessons list`` inventory. Tokens that resolve to non-existent
lessons become Q-Gate findings (phase ``5-execute``) and are also surfaced in
a TOON summary on stdout.

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

# Reason code stored on every finding (currently the only reason emitted).
REASON_PHANTOM = 'phantom_lesson_id'


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
    """
    # Local import — keeps the manage-findings dependency lazy so the
    # ``--no-emit`` path doesn't pay for it.
    from _findings_core import add_qgate_finding  # type: ignore[import-not-found]

    title = f'Phantom lesson-ID reference: {finding["token"]}'
    detail = (
        f'Task file {finding["task_file"]} references lesson-ID '
        f'{finding["token"]!r}, which is not present in the live '
        f'manage-lessons inventory.'
    )
    add_qgate_finding(
        plan_id=finding['plan_id'],
        phase=QGATE_PHASE,
        source='qgate',
        finding_type='bug',
        title=title,
        detail=detail,
        file_path=finding['task_file'],
        component='plan-marshall:plan-doctor',
        severity='warning',
        iteration=None,
    )


# ---------------------------------------------------------------------------
# Verb handlers
# ---------------------------------------------------------------------------


def _scan_plans(plan_ids: list[str], emit_to_qgate: bool) -> dict[str, Any]:
    """Scan every TASK file across ``plan_ids`` and return the TOON payload."""
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

    if emit_to_qgate:
        for finding in findings:
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

    try:
        payload = _scan_plans(plan_ids, emit_to_qgate=not args.no_emit)
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
