#!/usr/bin/env python3
"""Check cross-artifact consistency for a plan.

Merges the novel structural checks from
``.claude/skills/verify-workflow/scripts/verify-structure.py`` into a single
retrospective aspect script.

Checks performed:
- ``solution_outline_sections`` — required sections (``summary``, ``overview``,
  ``deliverables``) present in ``solution_outline.md``.
- ``deliverable_count`` — deliverables extracted and counted.
- ``task_deliverable_match`` — each declared deliverable has a matching
  ``TASK-*.json`` whose ``deliverable`` field aligns with its index.
- ``affected_files_recall`` — files declared in the solution outline's
  ``Affected files:`` bullets appear in ``references.json`` ``affected_files``
  with >= 70% coverage.
- ``metrics_generated`` — ``metrics.md`` exists.

Usage:
    python3 check-artifact-consistency.py run --plan-id my-plan --mode live
    python3 check-artifact-consistency.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _plan_parsing import (  # type: ignore[import-not-found]
    extract_deliverable_headings,
    parse_document_sections,
)
from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

# Manifest filename — kept in sync with manage-execution-manifest.py.
# When the manifest exists, the affected_files_exact_match check defers to
# the new manifest-aware aspect (check-manifest-consistency.py) which compares
# the actual end-of-execute diff against manifest assumptions. The legacy
# exact-match warning is too strict in that world because the manifest already
# encodes the expected diff shape, so we downgrade ``warn`` to ``info`` and
# annotate the top-level result so the report renderer can route the reader
# to the manifest aspect.
_MANIFEST_FILENAME = 'execution.toon'

# Required sections in solution_outline.md. Keys are lowercased by
# ``parse_document_sections``.
_REQUIRED_SECTIONS = ('summary', 'overview', 'deliverables')

# Recall threshold: at least this fraction of declared affected files must
# be present in references.json for the check to pass.
_RECALL_THRESHOLD = 0.70

# Regex for ``Affected files:`` bullet lists in deliverable sections.
_AFFECTED_FILE_BULLET_RE = re.compile(r'^\s*-\s+`?([^`\n]+?)`?\s*$', re.MULTILINE)


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f"Unknown mode: {mode!r}")


def check_solution_outline_sections(content: str) -> tuple[str, str]:
    """Return ``(status, message)`` for the required-sections check."""
    sections = parse_document_sections(content)
    missing = [name for name in _REQUIRED_SECTIONS if name not in sections]
    if missing:
        return 'fail', f'Missing required sections: {", ".join(missing)}'
    return 'pass', 'All required sections present'


def check_deliverable_count(content: str) -> tuple[str, str, list[dict[str, str]]]:
    """Return ``(status, message, deliverables)`` for the deliverable count check."""
    sections = parse_document_sections(content)
    deliverables_section = sections.get('deliverables', '')
    if not deliverables_section:
        return 'fail', 'No Deliverables section present', []
    deliverables = extract_deliverable_headings(deliverables_section)
    if not deliverables:
        return 'fail', 'Deliverables section contains no headings', []
    return 'pass', f'{len(deliverables)} deliverables declared', deliverables


def extract_affected_files_per_deliverable(content: str) -> list[str]:
    """Extract every ``Affected files:`` bullet item across all deliverables.

    Declared files are often listed as bullets beneath an ``**Affected files:**``
    heading inside each deliverable section. We collect all such bullets into
    a flat list for the recall check.
    """
    files: list[str] = []
    # Iterate blocks that start with the Affected files heading.
    blocks = re.split(r'\*\*Affected files:\*\*', content)
    # First block is before any header, skip.
    for block in blocks[1:]:
        # Stop at the next bold heading (next deliverable field).
        chunk = re.split(r'\*\*[A-Z][^*]+:\*\*', block, maxsplit=1)[0]
        for match in _AFFECTED_FILE_BULLET_RE.finditer(chunk):
            path = match.group(1).strip()
            if path:
                files.append(path)
    return files


def check_affected_files_recall(
    solution_content: str, references_path: Path
) -> tuple[str, str, dict[str, Any]]:
    """Return ``(status, message, details)`` for the affected-files recall check."""
    declared = set(extract_affected_files_per_deliverable(solution_content))
    if not declared:
        return 'skip', 'No Affected files declared in solution outline', {'declared': 0}

    if not references_path.exists():
        return 'fail', 'references.json missing — cannot compute recall', {
            'declared': len(declared),
        }

    try:
        refs = json.loads(references_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        return 'fail', f'references.json unreadable: {e}', {'declared': len(declared)}

    actual_raw = refs.get('modified_files', [])
    if isinstance(actual_raw, str):
        actual_raw = [actual_raw]
    actual = {str(p).strip() for p in actual_raw if p}

    found = declared & actual
    missing = declared - actual
    recall = len(found) / len(declared) if declared else 0.0

    details = {
        'declared': len(declared),
        'found': len(found),
        'missing': sorted(missing)[:10],
        'recall_pct': round(recall * 100.0, 1),
    }
    if recall >= _RECALL_THRESHOLD:
        return 'pass', f'Recall {recall * 100:.0f}% meets threshold', details
    return 'fail', f'Recall {recall * 100:.0f}% below {int(_RECALL_THRESHOLD * 100)}% threshold', details


def check_affected_files_exact_match(
    outline_files: set[str], references_files: set[str]
) -> tuple[str, str, list[str], list[str]]:
    """Return ``(status, message, outline_only, references_only)`` for the exact-match check.

    Strict variant of the recall check: passes only when the outline and references
    sets agree exactly (including both empty). Any drift — files declared in the
    outline but missing from references, or listed in references but not declared
    in the outline — produces a ``warn`` with both sides surfaced for the
    retrospective synthesizer.
    """
    if outline_files == references_files:
        return 'pass', 'Outline and references agree exactly', [], []
    outline_only = sorted(outline_files - references_files)
    references_only = sorted(references_files - outline_files)
    return 'warn', 'Set mismatch', outline_only, references_only


def check_task_deliverable_match(
    deliverables: list[dict[str, str]], tasks_dir: Path
) -> tuple[str, str]:
    """Return ``(status, message)`` for the task-deliverable alignment check."""
    if not deliverables:
        return 'skip', 'No deliverables declared'
    if not tasks_dir.exists():
        return 'fail', 'tasks/ directory missing'
    task_files = sorted(tasks_dir.glob('TASK-*.json'))
    if not task_files:
        return 'fail', 'No TASK-*.json files present'
    covered: set[int] = set()
    for task_file in task_files:
        try:
            data = json.loads(task_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        deliverable = data.get('deliverable')
        if isinstance(deliverable, int):
            covered.add(deliverable)
    expected = set(range(1, len(deliverables) + 1))
    missing = expected - covered
    if missing:
        return 'fail', f'Deliverables without matching task: {sorted(missing)}'
    return 'pass', f'All {len(deliverables)} deliverables covered by tasks'


def check_metrics_generated(plan_dir: Path) -> tuple[str, str]:
    """Return ``(status, message)`` for metrics.md presence."""
    metrics_path = plan_dir / 'metrics.md'
    if metrics_path.exists():
        return 'pass', 'metrics.md present'
    return 'fail', 'metrics.md missing — record-metrics step did not run'


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    checks: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    details: dict[str, Any] = {}

    solution_path = plan_dir / 'solution_outline.md'
    if not solution_path.exists():
        checks.append({
            'name': 'solution_outline_present',
            'status': 'fail',
            'message': 'solution_outline.md missing',
        })
        findings.append({'severity': 'error', 'message': 'solution_outline.md missing'})
        deliverables: list[dict[str, str]] = []
        solution_content = ''
    else:
        solution_content = solution_path.read_text(encoding='utf-8')
        status, message = check_solution_outline_sections(solution_content)
        checks.append({'name': 'solution_outline_sections', 'status': status, 'message': message})
        if status == 'fail':
            findings.append({'severity': 'error', 'message': message})

        d_status, d_message, deliverables = check_deliverable_count(solution_content)
        checks.append({'name': 'deliverable_count', 'status': d_status, 'message': d_message})
        if d_status == 'fail':
            findings.append({'severity': 'error', 'message': d_message})

    # Task-deliverable match
    tm_status, tm_message = check_task_deliverable_match(deliverables, plan_dir / 'tasks')
    checks.append({'name': 'task_deliverable_match', 'status': tm_status, 'message': tm_message})
    if tm_status == 'fail':
        findings.append({'severity': 'error', 'message': tm_message})

    # Affected-files recall
    references_path = plan_dir / 'references.json'
    rec_status, rec_message, rec_details = check_affected_files_recall(
        solution_content, references_path
    )
    checks.append({'name': 'affected_files_recall', 'status': rec_status, 'message': rec_message})
    details['affected_files_recall'] = rec_details
    if rec_status == 'fail':
        findings.append({'severity': 'warning', 'message': rec_message})

    # Affected-files exact-match (strict variant, peer to recall).
    # Reads the same ``modified_files`` key used by
    # ``check_affected_files_recall`` — both checks must agree on the source
    # of truth in ``references.json``.
    outline_files = set(extract_affected_files_per_deliverable(solution_content))
    references_files: set[str] = set()
    if references_path.exists():
        try:
            refs_data = json.loads(references_path.read_text(encoding='utf-8'))
            if not isinstance(refs_data, dict):
                # ``references.json`` must be an object; a top-level ``null`` or
                # ``[]`` literal is treated as "no declared files".
                actual_raw: Any = []
            else:
                actual_raw = refs_data.get('modified_files', [])
            if isinstance(actual_raw, str):
                actual_raw = [actual_raw]
            if not isinstance(actual_raw, list):
                actual_raw = []
            references_files = {str(p).strip() for p in actual_raw if p}
        except (OSError, json.JSONDecodeError):
            references_files = set()
    exact_status, exact_message, outline_only, references_only = check_affected_files_exact_match(
        outline_files, references_files
    )

    # Manifest-aware mode: when execution.toon exists, the manifest aspect
    # (check-manifest-consistency.py) is the authoritative cross-check for
    # diff-vs-expectation drift. Downgrade the legacy exact_match ``warn`` to
    # ``info`` and forward the reader to the manifest aspect rather than
    # duplicating the warning. Pre-manifest plans keep today's ``warn``
    # behavior so existing tests remain green.
    manifest_present = (plan_dir / _MANIFEST_FILENAME).exists()
    forwarded_to_manifest = False
    if manifest_present and exact_status == 'warn':
        forwarded_to_manifest = True
        forwarded_message = (
            f'{exact_message} — deferred to manifest aspect '
            '(see check-manifest-consistency)'
        )
        checks.append({
            'name': 'affected_files_exact_match',
            'status': 'info',
            'message': forwarded_message,
        })
        # Surface as info rather than warning so the report renderer routes
        # the reader to the manifest section instead of double-counting drift.
        findings.append({'severity': 'info', 'message': forwarded_message})
    else:
        checks.append({
            'name': 'affected_files_exact_match',
            'status': exact_status,
            'message': exact_message,
        })
        if exact_status == 'warn':
            findings.append({'severity': 'warning', 'message': exact_message})

    # metrics.md presence
    m_status, m_message = check_metrics_generated(plan_dir)
    checks.append({'name': 'metrics_generated', 'status': m_status, 'message': m_message})
    if m_status == 'fail':
        findings.append({'severity': 'error', 'message': m_message})

    summary = {
        'passed': sum(1 for c in checks if c['status'] == 'pass'),
        'failed': sum(1 for c in checks if c['status'] == 'fail'),
        'skipped': sum(1 for c in checks if c['status'] == 'skip'),
    }

    return {
        'status': 'success',
        'aspect': 'artifact_consistency',
        'plan_id': args.plan_id or plan_dir.name,
        'plan_dir': str(plan_dir),
        'checks': checks,
        'findings': findings,
        'summary': summary,
        'details': details,
        'affected_files_exact_match': {
            'status': exact_status,
            'outline_only': outline_only,
            'references_only': references_only,
            'manifest_present': manifest_present,
            'forwarded_to_manifest': forwarded_to_manifest,
        },
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check cross-artifact consistency for a plan',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Run all checks', allow_abbrev=False)
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
