#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Check cross-artifact consistency for a plan.

Runs the structural consistency checks for a single retrospective aspect.

Checks performed:
- ``solution_outline_sections`` — required sections (``summary``, ``overview``,
  ``deliverables``) present in ``solution_outline.md``.
- ``deliverable_count`` — deliverables extracted and counted.
- ``task_deliverable_match`` — each declared deliverable has a matching
  ``TASK-*.json`` whose ``deliverable`` field aligns with its index.
- ``affected_files_recall`` — files declared in the solution outline's
  ``Affected files:`` bullets appear in the resolved plan footprint with
  >= 70% coverage. The declaration state is read **per deliverable**: any
  deliverable whose own content carries the ``Affected files:`` heading but
  from which no bullet could be parsed reports ``fail``, naming that
  deliverable — even when sibling deliverables declared files and the
  aggregate declared set is non-empty. ``skip`` is retained only when no
  deliverable declares an ``Affected files`` section at all.
- ``affected_files_exact_match`` — the declared set and the resolved footprint
  agree exactly. A both-empty comparison substantiates nothing and reports
  ``inconclusive``, never ``pass``.
- ``metrics_generated`` — ``metrics.md`` exists.

Usage:
    python3 check-artifact-consistency.py run --plan-id EXAMPLE-PLAN --mode live
    python3 check-artifact-consistency.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from _plan_parsing import (
    extract_deliverable_headings,
    parse_document_sections,
    split_deliverable_blocks,
)
from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
)
from file_ops import base_path, output_toon, safe_main
from input_validation import (
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
#
# Two tolerated bullet forms, in alternation order:
#   1. Backtick-delimited, optionally annotated — ``- `path/to/file` (intent)``.
#      Group ``quoted`` captures only the span between the backticks; anything
#      following the closing backtick (the intent annotation) is discarded.
#   2. Bare, un-backticked, un-annotated — ``- path/to/file``. Group ``bare``
#      captures the whole trimmed line body. The class excludes backticks so a
#      backticked line can never fall through to this branch.
_AFFECTED_FILE_BULLET_RE = re.compile(
    r'^[ \t]*-[ \t]+(?:`(?P<quoted>[^`\n]+)`[^\n]*|(?P<bare>[^`\n]+?))[ \t]*$',
    re.MULTILINE,
)


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def _load_references(plan_dir: Path) -> dict[str, Any]:
    """Read references.json from ``plan_dir``; return ``{}`` on any error."""
    refs_path = plan_dir / 'references.json'
    if not refs_path.exists():
        return {}
    try:
        data = json.loads(refs_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_footprint(plan_dir: Path) -> set[str]:
    """Resolve the plan footprint for an archived (or live) plan.

    Three-tier resolution, in order:

    1. **Live diff** — when ``status.metadata.worktree_path`` resolves to a git
       worktree on disk, derive the footprint via ``compute_plan_branch_diff``
       (``{base}...HEAD`` ∪ porcelain). This is the single source of truth for a
       plan whose worktree still exists.
    2. **Legacy key** — fall back to ``references.modified_files`` when present
       (archived plans created before the ledger was removed still carry it).
    3. **Empty** — when neither resolves, treat the footprint as empty.

    Returns a set of repo-relative path strings.
    """
    refs = _load_references(plan_dir)

    status_path = plan_dir / 'status.json'
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            status = {}
        if isinstance(status, dict):
            metadata = status.get('metadata', {})
            if isinstance(metadata, dict):
                worktree_path = metadata.get('worktree_path', '')
                if isinstance(worktree_path, str) and worktree_path:
                    worktree = Path(worktree_path)
                    if worktree.is_dir():
                        base_ref = resolve_base_ref(None, refs)
                        try:
                            return compute_plan_branch_diff(worktree, base_ref)
                        except subprocess.CalledProcessError:
                            pass  # fall through to the legacy-key read

    legacy = refs.get('modified_files', [])
    if isinstance(legacy, str):
        legacy = [legacy]
    if not isinstance(legacy, list):
        return set()
    return {str(p).strip() for p in legacy if p}


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

    Both tolerated bullet forms yield the bare path: the canonical
    ``- `path` (intent)`` form contributes only the backtick-delimited span,
    and the bare ``- path`` form contributes the trimmed line body.
    """
    files: list[str] = []
    # Iterate blocks that start with the Affected files heading.
    blocks = re.split(r'\*\*Affected files:\*\*', content)
    # First block is before any header, skip.
    for block in blocks[1:]:
        # Stop at the next bold heading (next deliverable field).
        chunk = re.split(r'\*\*[A-Z][^*]+:\*\*', block, maxsplit=1)[0]
        for match in _AFFECTED_FILE_BULLET_RE.finditer(chunk):
            raw = match.group('quoted') or match.group('bare') or ''
            path = raw.strip()
            if path:
                files.append(path)
    return files


def _declaration_state_per_deliverable(solution_content: str) -> list[dict[str, Any]]:
    """Return the per-deliverable ``Affected files:`` declaration state.

    For each ``### N. Title`` block of the outline's Deliverables section,
    records whether that block's OWN content carries the ``**Affected files:**``
    heading and, when it does, the bullets :data:`_AFFECTED_FILE_BULLET_RE`
    extracts from it — truncated at the next ``**Field:**`` heading exactly as
    :func:`extract_affected_files_per_deliverable` does for the aggregate.

    Attribution is per deliverable so a heading that parses to zero bullets is
    detectable even when sibling deliverables declared files, which the
    aggregate (flattened) view cannot express.

    Returns:
        List of dicts with 'number', 'title', 'heading_present', 'files' keys,
        in document order.
    """
    sections = parse_document_sections(solution_content)
    deliverables_section = sections.get('deliverables', '')

    states: list[dict[str, Any]] = []
    for block in split_deliverable_blocks(deliverables_section):
        blocks = re.split(r'\*\*Affected files:\*\*', block['content'])
        files: list[str] = []
        for chunk_source in blocks[1:]:
            chunk = re.split(r'\*\*[A-Z][^*]+:\*\*', chunk_source, maxsplit=1)[0]
            for match in _AFFECTED_FILE_BULLET_RE.finditer(chunk):
                raw = match.group('quoted') or match.group('bare') or ''
                path = raw.strip()
                if path:
                    files.append(path)
        states.append(
            {
                'number': block['number'],
                'title': block['title'],
                'heading_present': len(blocks) > 1,
                'files': files,
            }
        )
    return states


def check_affected_files_recall(
    solution_content: str, plan_dir: Path, deliverables: list[dict[str, str]]
) -> tuple[str, str, dict[str, Any]]:
    """Return ``(status, message, details)`` for the affected-files recall check.

    Recall compares the outline's declared ``Affected files:`` against the live
    plan footprint resolved via :func:`_resolve_footprint` (live diff, then the
    legacy ``modified_files`` key for older archived plans, then empty).

    The skip-vs-fail head reads the declaration state **per deliverable** (via
    :func:`_declaration_state_per_deliverable`) rather than off the flattened
    aggregate, in this order:

    - any deliverable whose own content carries the ``Affected files:`` heading
      yet yields no parsed bullet is a ``fail`` naming that deliverable — this
      fires even when sibling deliverables declared files and the aggregate
      declared set is non-empty, which the aggregate view cannot detect;
    - otherwise, an empty aggregate declared set means no deliverable declares
      an ``Affected files`` section at all, so ``skip`` is substantiated;
    - otherwise the recall comparison proceeds.

    ``deliverables`` is the already-extracted deliverable list from
    :func:`check_deliverable_count`; it remains the deliverable count reported
    in ``details``.

    A present-but-unreadable ``references.json`` is surfaced distinctly as a
    recall failure (the retrospective must flag corrupt plan state rather than
    silently treating it as "no footprint").
    """
    declared = set(extract_affected_files_per_deliverable(solution_content))

    unparseable = [
        state
        for state in _declaration_state_per_deliverable(solution_content)
        if state['heading_present'] and not state['files']
    ]
    if unparseable:
        named = ', '.join(f'{state["number"]}. {state["title"]}' for state in unparseable)
        return (
            'fail',
            f'Affected files heading present but no bullet parsed for deliverable(s): {named}',
            {
                'declared': len(declared),
                'deliverables': len(deliverables),
                'unparseable_deliverables': [state['number'] for state in unparseable],
            },
        )

    if not declared:
        return (
            'skip',
            'No deliverable declares an Affected files section — nothing to compare',
            {'declared': 0, 'deliverables': len(deliverables)},
        )

    references_path = plan_dir / 'references.json'
    if references_path.exists():
        try:
            json.loads(references_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            return 'fail', f'references.json unreadable: {e}', {'declared': len(declared)}

    actual = _resolve_footprint(plan_dir)

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

    Strict variant of the recall check: ``pass`` only when both sides are
    non-empty and agree exactly. A both-empty comparison substantiates nothing —
    two empty sets are trivially equal whether the plan really touched no files
    or the parser and the footprint resolver both failed — so it reports
    ``inconclusive`` rather than a vacuous ``pass``. Any drift — files declared
    in the outline but missing from references, or listed in references but not
    declared in the outline — produces a ``warn`` with both sides surfaced for
    the retrospective synthesizer.
    """
    if not outline_files and not references_files:
        return (
            'inconclusive',
            'Both the declared set and the resolved footprint are empty — '
            'the comparison substantiates no verdict',
            [],
            [],
        )
    if outline_files == references_files:
        return 'pass', 'Outline and references agree exactly', [], []
    outline_only = sorted(outline_files - references_files)
    references_only = sorted(references_files - outline_files)
    return 'warn', 'Set mismatch', outline_only, references_only


def check_task_deliverable_match(deliverables: list[dict[str, str]], tasks_dir: Path) -> tuple[str, str]:
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
    deliverables: list[dict[str, str]] = []
    solution_content = ''
    if not solution_path.exists():
        checks.append(
            {
                'name': 'solution_outline_present',
                'status': 'fail',
                'message': 'solution_outline.md missing',
            }
        )
        findings.append({'severity': 'error', 'message': 'solution_outline.md missing'})
    else:
        try:
            solution_content = solution_path.read_text(encoding='utf-8')
        except OSError as e:
            # Fail closed: a file that passed .exists() but raises on read
            # (permission denied, the path resolves to a directory, a mid-read
            # deletion race) must surface as a structured verdict, never an
            # uncaught exception that crashes the consistency gate. Degrade
            # solution_content to '' so the remaining checks run against the
            # fail-closed state.
            checks.append(
                {
                    'name': 'solution_outline_present',
                    'status': 'fail',
                    'message': f'solution_outline.md read_failed: {e}',
                }
            )
            findings.append(
                {'severity': 'error', 'message': f'solution_outline.md read_failed: {e}'}
            )
        else:
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
    rec_status, rec_message, rec_details = check_affected_files_recall(
        solution_content, plan_dir, deliverables
    )
    checks.append({'name': 'affected_files_recall', 'status': rec_status, 'message': rec_message})
    details['affected_files_recall'] = rec_details
    if rec_status == 'fail':
        findings.append({'severity': 'warning', 'message': rec_message})

    # Affected-files exact-match (strict variant, peer to recall).
    # Resolves the same live plan footprint used by
    # ``check_affected_files_recall`` via ``_resolve_footprint`` — both checks
    # must agree on the source of truth (live diff, then the legacy
    # ``modified_files`` key for older archived plans, then empty).
    outline_files = set(extract_affected_files_per_deliverable(solution_content))
    references_files = _resolve_footprint(plan_dir)
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
        forwarded_message = f'{exact_message} — deferred to manifest aspect (see check-manifest-consistency)'
        checks.append(
            {
                'name': 'affected_files_exact_match',
                'status': 'info',
                'message': forwarded_message,
            }
        )
        # Surface as info rather than warning so the report renderer routes
        # the reader to the manifest section instead of double-counting drift.
        findings.append({'severity': 'info', 'message': forwarded_message})
    else:
        checks.append(
            {
                'name': 'affected_files_exact_match',
                'status': exact_status,
                'message': exact_message,
            }
        )
        if exact_status in ('warn', 'inconclusive'):
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
    main()
