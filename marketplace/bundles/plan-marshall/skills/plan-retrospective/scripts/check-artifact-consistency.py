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
  deliverable declares an ``Affected files`` section at all. When the footprint
  itself cannot be resolved the check reports ``inconclusive``: recall is
  unmeasurable, never a confident 0%.
- ``affected_files_exact_match`` — the declared set and the resolved footprint
  agree exactly. A both-empty comparison substantiates nothing and reports
  ``inconclusive``, never ``pass``; so does an unresolvable footprint, which
  likewise substantiates no comparison.
- ``metrics_generated`` — ``metrics.md`` exists. Absence is a ``fail`` only when
  the producing step has already had its turn: ``default:record-metrics`` is
  ordered AFTER the consuming retrospective, so on a correctly-functioning run
  the artifact does not exist yet and the check reports ``inconclusive`` naming
  the ordering. Both orders are resolved from discovery, never from an order
  literal.

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
from typing import Any, TypeGuard

from _plan_parsing import (
    extract_deliverable_headings,
    parse_document_sections,
    split_deliverable_blocks,
)
from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
    resolve_live_worktree,
)
from extension_discovery import find_implementors
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


#: Stated sentinel for a footprint that could NOT be resolved at all.
#:
#: Deliberately distinct from ``set()``, which states the opposite thing: the
#: footprint resolved and the plan genuinely touched no files. Collapsing both
#: outcomes to an empty set is what let a 21/21 exact footprint score a
#: confident "Recall 0%" after ``branch-cleanup`` deleted the worktree the
#: resolver measures — an unmeasurable input rendered as a measured zero.
FOOTPRINT_UNRESOLVED = None


def footprint_resolved(footprint: set[str] | None) -> TypeGuard[set[str]]:
    """The ONE named predicate callers use to read a footprint's resolution state.

    Per ADR-015, the absent identity is a stated sentinel
    (:data:`FOOTPRINT_UNRESOLVED`) and every presence guard goes through this
    named predicate rather than an inline truthiness check. ``not footprint`` is
    NOT equivalent: it is also true for a resolved-but-empty footprint, which is
    a measured result and must still yield a measured verdict.

    Typed as a ``TypeGuard`` so callers branch on the predicate positively and
    the resolved ``set[str]`` narrows for the type checker — no caller needs a
    separate ``is not None`` restatement that could drift from this definition.
    """
    return footprint is not FOOTPRINT_UNRESOLVED


def _resolve_footprint(plan_dir: Path, plan_id: str | None = None) -> set[str] | None:
    """Resolve the plan footprint for an archived (or live) plan.

    Three-tier resolution, in order:

    1. **Live diff** — when ``plan_id`` names a live plan whose worktree the ONE
       resolver (:func:`_references_core.resolve_live_worktree`) resolves to a
       directory on disk, derive the footprint via ``compute_plan_branch_diff``
       (``{base}...HEAD`` ∪ porcelain). This is the single source of truth for a
       plan whose worktree still exists. A ``CalledProcessError`` here reports
       UNRESOLVABLE rather than falling through to the legacy read: the worktree
       resolved but the diff failed, so the legacy key would answer a different
       question while presenting as the same measurement.
    2. **Legacy key** — ``references.modified_files`` when the key is PRESENT
       (archived plans created before the ledger was removed still carry it). A
       present-but-empty list is a resolved, genuinely-empty footprint.
    3. **Unresolvable** — when neither tier answers, return
       :data:`FOOTPRINT_UNRESOLVED`. Key absent and key present-but-empty are
       different answers and are reported differently.

    Archived mode passes ``plan_id=None`` and therefore skips tier 1 entirely:
    an archived plan's recorded worktree names a directory finalize has already
    removed. Tier 1 is reached through the resolver rather than by re-reading
    ``status.metadata.worktree_path`` here.

    Returns:
        A set of repo-relative path strings when the footprint resolved (possibly
        empty), or :data:`FOOTPRINT_UNRESOLVED` when it could not be resolved.
        Read the distinction through :func:`footprint_resolved`, never by
        testing emptiness.
    """
    refs = _load_references(plan_dir)

    worktree = resolve_live_worktree(plan_id)
    if worktree is not None:
        base_ref = resolve_base_ref(None, refs)
        try:
            return compute_plan_branch_diff(worktree, base_ref)
        except subprocess.CalledProcessError:
            return FOOTPRINT_UNRESOLVED

    legacy = refs.get('modified_files')
    if legacy is None:
        return FOOTPRINT_UNRESOLVED
    if isinstance(legacy, str):
        legacy = [legacy]
    if not isinstance(legacy, list):
        return FOOTPRINT_UNRESOLVED
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


def _extract_bullets(block_content: str) -> list[str]:
    """Extract ``Affected files:`` bullets from a block of solution-outline content.

    Splits on each ``**Affected files:**`` heading occurrence and collects the
    bullets beneath it, stopping at the next bold field heading (e.g. the next
    deliverable field or the next deliverable's own heading).

    Both tolerated bullet forms yield the bare path: the canonical
    ``- `path` (intent)`` form contributes only the backtick-delimited span,
    and the bare ``- path`` form contributes the trimmed line body.

    Shared by :func:`extract_affected_files_per_deliverable` (aggregate, across
    the whole content) and :func:`_declaration_state_per_deliverable`
    (per-block) so the bullet-matching logic exists in exactly one place.
    """
    files: list[str] = []
    blocks = re.split(r'\*\*Affected files:\*\*', block_content)
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


def extract_affected_files_per_deliverable(content: str) -> list[str]:
    """Extract every ``Affected files:`` bullet item across all deliverables.

    Declared files are often listed as bullets beneath an ``**Affected files:**``
    heading inside each deliverable section. We collect all such bullets into
    a flat list for the recall check.
    """
    return _extract_bullets(content)


def _declaration_state_per_deliverable(solution_content: str) -> list[dict[str, Any]]:
    """Return the per-deliverable ``Affected files:`` declaration state.

    For each ``### N. Title`` block of the outline's Deliverables section,
    records whether that block's OWN content carries the ``**Affected files:**``
    heading and, when it does, the bullets :func:`_extract_bullets` extracts
    from it.

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
        states.append(
            {
                'number': block['number'],
                'title': block['title'],
                'heading_present': '**Affected files:**' in block['content'],
                'files': _extract_bullets(block['content']),
            }
        )
    return states


def check_affected_files_recall(
    solution_content: str,
    plan_dir: Path,
    deliverables: list[dict[str, str]],
    plan_id: str | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Return ``(status, message, details)`` for the affected-files recall check.

    Recall compares the outline's declared ``Affected files:`` against the live
    plan footprint resolved via :func:`_resolve_footprint` (live diff, then the
    legacy ``modified_files`` key for older archived plans, then unresolvable).
    A footprint that could not be resolved yields ``inconclusive``: recall is
    unmeasurable, never a confident 0%. A resolved-but-empty footprint is a
    measured input and still yields a measured verdict.

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

    actual = _resolve_footprint(plan_dir, plan_id)
    if footprint_resolved(actual):
        found = declared & actual
        missing = declared - actual
        # ``declared`` is guaranteed non-empty here — the empty case returned
        # ``skip`` above — so the division needs no zero guard.
        recall = len(found) / len(declared)

        details = {
            'declared': len(declared),
            'found': len(found),
            'missing': sorted(missing)[:10],
            'recall_pct': round(recall * 100.0, 1),
            'footprint_resolved': True,
        }
        if recall >= _RECALL_THRESHOLD:
            return 'pass', f'Recall {recall * 100:.0f}% meets threshold', details
        return (
            'fail',
            f'Recall {recall * 100:.0f}% below {int(_RECALL_THRESHOLD * 100)}% threshold',
            details,
        )

    return (
        'inconclusive',
        'Plan footprint could not be resolved (no live worktree diff and no '
        'modified_files key) — recall is unmeasurable, not 0%',
        {
            'declared': len(declared),
            'deliverables': len(deliverables),
            'footprint_resolved': False,
        },
    )


def check_affected_files_exact_match(
    outline_files: set[str], references_files: set[str] | None
) -> tuple[str, str, list[str], list[str]]:
    """Return ``(status, message, outline_only, references_only)`` for the exact-match check.

    Strict variant of the recall check: ``pass`` only when both sides are
    non-empty and agree exactly. Two comparisons substantiate no verdict and
    report ``inconclusive`` rather than a confident one:

    - an **unresolvable footprint** (:data:`FOOTPRINT_UNRESOLVED`) — there is no
      right-hand side to compare against, so a ``warn`` "Set mismatch" would be a
      confident claim of drift derived from an input that was never measured;
    - a **both-empty** comparison — two empty sets are trivially equal whether
      the plan really touched no files or the parser and the footprint resolver
      both failed, so ``pass`` would be vacuous.

    Reading the resolution state through :func:`footprint_resolved` keeps this
    peer symmetric with :func:`check_affected_files_recall`: both consume the
    same resolver and neither infers resolution state from set emptiness.

    Any drift — files declared in the outline but missing from references, or
    listed in references but not declared in the outline — produces a ``warn``
    with both sides surfaced for the retrospective synthesizer.
    """
    if footprint_resolved(references_files):
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

    return (
        'inconclusive',
        'Plan footprint could not be resolved (no live worktree diff and no '
        'modified_files key) — the comparison substantiates no verdict',
        [],
        [],
    )


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


#: Summary-bucket name for the three statuses whose bucket name differs from
#: the status itself. Every other status buckets under its own name, so a
#: status introduced later is counted without touching this map.
_SUMMARY_BUCKET_NAMES = {'pass': 'passed', 'fail': 'failed', 'skip': 'skipped'}


def summarize_checks(checks: list[dict[str, str]]) -> dict[str, int]:
    """Count every emitted check status into a named summary bucket.

    The buckets are derived from ``checks`` itself rather than from a hardcoded
    status list, so ``sum(summary.values()) == len(checks)`` holds for any
    status the checks emit — ``warn``, ``info`` and ``inconclusive`` included.
    A three-bucket summary counting only ``pass``/``fail``/``skip`` let every
    other verdict land in no bucket, which reads to a summary consumer as a
    check that does not exist: the same unmeasurable-rendered-as-absent shape
    the ``inconclusive`` footprint verdict exists to remove.

    The three legacy bucket names are seeded at zero so downstream consumers can
    read ``passed`` / ``failed`` / ``skipped`` unconditionally; zero buckets do
    not disturb the reconciliation.
    """
    summary = dict.fromkeys(_SUMMARY_BUCKET_NAMES.values(), 0)
    for check in checks:
        status = check['status']
        bucket = _SUMMARY_BUCKET_NAMES.get(status, status)
        summary[bucket] = summary.get(bucket, 0) + 1
    return summary


#: Finding severity per verdict for the checks that split a MEASURED failure
#: from an UNMEASURABLE one. Both verdicts must reach ``findings`` — a verdict
#: dropped by a ``fail``-only gate reads to the synthesizer as a check that
#: raised nothing — but they must reach it at DIFFERENT severities, because
#: collapsing them onto one severity erases the measured-vs-unmeasurable
#: distinction those checks exist to preserve.
_MEASURED_VERDICT_SEVERITY = {'fail': 'error', 'inconclusive': 'warning'}


def _route_measured_verdict(findings: list[dict[str, str]], status: str, message: str) -> None:
    """Append ``message`` to ``findings`` at the severity ``status`` maps to.

    Shared by ``affected_files_recall`` and ``metrics_generated``, which owe the
    identical measured-vs-unmeasurable split. One body means the two cannot drift
    onto different severity pairings while each still reads as correct in
    isolation. A status outside :data:`_MEASURED_VERDICT_SEVERITY` (``pass`` /
    ``skip``) raises no finding.
    """
    severity = _MEASURED_VERDICT_SEVERITY.get(status)
    if severity is not None:
        findings.append({'severity': severity, 'message': message})


#: The ext-point whose implementor records carry each finalize step's ``order``.
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The step that PRODUCES ``metrics.md``.
_METRICS_PRODUCER_STEP = 'default:record-metrics'

#: The step that CONSUMES it — the retrospective this check runs inside.
_METRICS_CONSUMER_STEP = 'plan-marshall:plan-retrospective'


def _resolve_step_order(step_id: str) -> int | None:
    """Return the discovered finalize-step ``order`` for ``step_id``.

    Read off the SAME registry path the finalize pipeline itself orders by —
    ``find_implementors`` over the finalize-step ext-point — never from an order
    literal. A hardcoded pair would have to be re-hardcoded for every further
    consumer of the same artifact, and would silently stop describing reality the
    moment a step is renumbered.

    Returns:
        The declared integer ``order``, or ``None`` when the step is not
        discoverable or declares no integer order. An unresolved ordering is an
        unmeasurable input; callers report it as such rather than inferring a
        position from its absence.
    """
    try:
        records = find_implementors(_FINALIZE_STEP_EXT_POINT)
    except Exception:
        return None
    for record in records:
        if record.get('name') == step_id:
            order = record.get('order')
            return order if isinstance(order, int) else None
    return None


def check_metrics_generated(plan_dir: Path) -> tuple[str, str]:
    """Return ``(status, message)`` for metrics.md presence.

    Presence is a ``pass``. ABSENCE only substantiates "the producing step did
    not run" once that step has had its turn. ``default:record-metrics`` is
    ordered AFTER ``plan-marshall:plan-retrospective``, so on a
    correctly-functioning run ``metrics.md`` does not exist yet when this check
    reads for it — a ``fail`` carrying that causal claim would be structurally
    guaranteed to be wrong. The not-yet-produced state is reported as
    ``inconclusive`` naming the ordering instead.

    The boundary is STRICT: only a producer ordered strictly later substantiates
    "has not had its turn". At an EQUAL order the run sequence is unconstrained,
    so the absence is not excused and falls to the measured ``fail`` branch —
    whose message therefore claims only that the producer is not ordered strictly
    after the consumer, never that it ran first.

    Both orders are resolved from discovery via :func:`_resolve_step_order`
    rather than from the order literals, so a renumbering moves the verdict with
    it and a second consumer of the same artifact needs no second hardcoded pair.
    An ordering that cannot be resolved is itself an unmeasurable input and
    yields ``inconclusive``, never a confident ``fail``.
    """
    metrics_path = plan_dir / 'metrics.md'
    if metrics_path.exists():
        return 'pass', 'metrics.md present'

    producer_order = _resolve_step_order(_METRICS_PRODUCER_STEP)
    consumer_order = _resolve_step_order(_METRICS_CONSUMER_STEP)

    if producer_order is None or consumer_order is None:
        return (
            'inconclusive',
            f'metrics.md absent and the ordering of {_METRICS_PRODUCER_STEP} against '
            f'{_METRICS_CONSUMER_STEP} could not be resolved from discovery — whether '
            'the producing step has had its turn is unmeasurable',
        )

    if producer_order > consumer_order:
        return (
            'inconclusive',
            f'metrics.md not produced yet — {_METRICS_PRODUCER_STEP} (order '
            f'{producer_order}) is ordered after {_METRICS_CONSUMER_STEP} (order '
            f'{consumer_order}), so it has not had its turn',
        )

    return (
        'fail',
        f'metrics.md missing — {_METRICS_PRODUCER_STEP} (order {producer_order}) is not '
        f'ordered strictly after {_METRICS_CONSUMER_STEP} (order {consumer_order}), so it '
        'is not guaranteed to run later and its absence is a genuine miss',
    )


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
    live_plan_id = args.plan_id if args.mode == 'live' else None
    rec_status, rec_message, rec_details = check_affected_files_recall(
        solution_content, plan_dir, deliverables, live_plan_id
    )
    checks.append({'name': 'affected_files_recall', 'status': rec_status, 'message': rec_message})
    details['affected_files_recall'] = rec_details
    # ``fail`` is a measured verdict (an Affected-files heading that parsed to no
    # bullet, an unreadable references.json, or a recall percentage below the
    # threshold); ``inconclusive`` is the unmeasurable case (the footprint could
    # not be resolved). Both reach ``findings``, at the severities
    # ``_route_measured_verdict`` owns.
    _route_measured_verdict(findings, rec_status, rec_message)

    # Affected-files exact-match (strict variant, peer to recall).
    # Resolves the same live plan footprint used by
    # ``check_affected_files_recall`` via ``_resolve_footprint`` — both checks
    # must agree on the source of truth (live diff, then the legacy
    # ``modified_files`` key for older archived plans, then unresolvable) AND on
    # how they read its resolution state (via ``footprint_resolved``).
    outline_files = set(extract_affected_files_per_deliverable(solution_content))
    references_files = _resolve_footprint(plan_dir, live_plan_id)
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
    # ``fail`` is the measured absence (the producer is not ordered strictly
    # later, so it had its turn); ``inconclusive`` is the unmeasurable case (the
    # producer runs later, or the ordering could not be resolved at all). Same
    # split, same owner as the recall peer above.
    _route_measured_verdict(findings, m_status, m_message)

    summary = summarize_checks(checks)

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
