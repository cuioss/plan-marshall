#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The frozen success-criteria snapshot — shared read/write/diff seam.

Background
----------
Every OpenCode plan so far was graded against criteria it had rewritten. The
functional review's "verdict-currency freeze" compared the current outline with
itself (``phase-6-finalize/workflow/functional-review.md`` § "Verdict-currency
freeze — judge against outline approval"), so a criterion narrowed, reworded or
dropped after outline approval was graded as though the plan had delivered it,
and the review's own verdict file was rewritten in place with no record of what
the reviewer had actually written.

This module is the single deterministic seam that closes both halves:

* :func:`build_snapshot` / :func:`write_snapshot` freeze, at outline approval,
  the success criteria of every outline deliverable — together with the
  request's Done-when text and, when the request names a spec document, each
  spec deliverable's separate Done-when clause. Merging deliverables in a later
  refine or outline pass cannot collapse them: the spec clauses are frozen as
  their own rows, keyed by spec deliverable number.
* :func:`criteria_drift` compares the CURRENT outline against the frozen rows
  and reports every criterion the current outline no longer carries verbatim —
  ``deleted`` or ``rewritten`` — unless an operator decision authorizes that
  exact change (:func:`authorize_change`).
* :func:`open_criteria` answers the finalize question "is any frozen criterion
  still open?" from the snapshot plus the review's verdict file, so neither the
  finalize triage source nor the finalize completion gate can exit on an empty
  bot queue while a Done-when is unmet.

Layering
--------
This module lives with ``_plan_parsing`` and is imported BY the phase-6-finalize
scripts and by ``manage-status`` (the finalize completion gate). Nothing here
imports from those higher layers, so there is no import cycle.

Nothing in this module judges a plan. It reads documents, writes one JSON
artifact and reports named differences; the grading that consumes its output
stays in ``phase-6-finalize/scripts/_review_support_validate.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _plan_parsing import (
    extract_deliverables,
    parse_document_sections,
    split_deliverable_blocks,
)
from file_ops import atomic_write_file, base_path, cwd_checkout_root

#: Plan-relative path of the frozen snapshot artifact.
SNAPSHOT_FILE = 'work/criteria-snapshot.json'
#: The snapshot schema tag this module writes and the only one it reads.
SCHEMA = 'criteria-snapshot/1'
REQUEST_FILE = 'request.md'

#: The success-criteria bullet block inside one outline deliverable body.
_SUCCESS_CRITERIA_RE = re.compile(r'\*\*Success Criteria:\*\*\s*((?:- [^\n]+\n?)+)', re.IGNORECASE)
#: A numbered bold deliverable heading in a request-named spec document.
_SPEC_DELIVERABLE_RE = re.compile(r'^(\d+)\.\s+\*\*(.+?)\*\*', re.MULTILINE)
#: The Done-when sentence of a spec deliverable, in any of the three spellings.
_SPEC_DONE_WHEN_RE = re.compile(r'(?:\*Done[- ]when:\*|\*\*Done[- ]when:\*\*|Done[- ]when:)\s*(.+)', re.IGNORECASE)
#: A heading that introduces the request's own Done-when text.
_REQUEST_DONE_WHEN_RE = re.compile(r'^\s*(?:#+\s*)?(?:\*\*)?Done[- ]when(?:\*\*)?\s*:?\s*$', re.IGNORECASE)
#: A markdown path token in free request text (``.plan/x/PLAN-1.md``, ``doc/y.md``).
_MD_PATH_RE = re.compile(r'(?:^|\s)([\w./-]+\.md)(?=[\s,.;:)]|$)', re.MULTILINE)

DELETED = 'deleted'
REWRITTEN = 'rewritten'
#: A spec deliverable's own Done-when that no outline criterion covers.
SPEC_MISSING = 'spec_criterion_missing'


def normalize_criterion(text: Any) -> str:
    """Collapse internal whitespace so two spellings of one criterion compare equal."""
    return ' '.join(str(text or '').split())


def snapshot_path(plan_id: str) -> Path:
    """Return the absolute path of the plan's criteria snapshot artifact."""
    return base_path('plans', plan_id, SNAPSHOT_FILE)


def outline_deliverables(plan_id: str) -> list[dict[str, Any]] | None:
    """Return the outline deliverables, each with its ordered ``success_criteria``.

    ``None`` when the outline does not exist — the caller reports that, it never
    reads an absent outline as an outline with no deliverables. This is the one
    success-criteria parser in the tree; ``phase-6-finalize``'s attribution
    module delegates here rather than keeping a second copy that could drift.
    """
    path = base_path('plans', plan_id, 'solution_outline.md')
    if not path.is_file():
        return None
    section = parse_document_sections(path.read_text(encoding='utf-8')).get('deliverables', '')
    bodies = {block['number']: block['content'] for block in split_deliverable_blocks(section)}
    deliverables = extract_deliverables(section)
    for deliverable in deliverables:
        match = _SUCCESS_CRITERIA_RE.search(str(bodies.get(deliverable['number'], '')))
        bullets = match.group(1).splitlines() if match else []
        deliverable['success_criteria'] = [line[2:].strip() for line in bullets if line.startswith('- ')]
    return deliverables


def _request_text(plan_id: str) -> str:
    """Return the request's clarified-request text, or ``''`` when unreadable."""
    path = base_path('plans', plan_id, REQUEST_FILE)
    if not path.is_file():
        return ''
    sections = parse_document_sections(path.read_text(encoding='utf-8'))
    for key in ('clarified_request', 'original_input'):
        body = sections.get(key)
        if body and body.strip():
            return body
    return ''


def request_done_when(text: str) -> list[str]:
    """Extract the request's Done-when clauses (the paragraph after a Done-when heading)."""
    lines = text.splitlines()
    clauses: list[str] = []
    for index, line in enumerate(lines):
        if not _REQUEST_DONE_WHEN_RE.match(line):
            continue
        for following in lines[index + 1 :]:
            stripped = following.strip()
            if not stripped:
                if clauses:
                    break
                continue
            clauses.append(stripped.lstrip('-* ').strip())
            if not stripped.startswith(('-', '*')):
                break
    return [clause for clause in clauses if clause]


def _referenced_spec_path(plan_id: str, text: str) -> Path | None:
    """First existing ``.md`` path the request text names, or ``None``.

    Request text names the spec a plan implements (for a staged orchestrator plan
    that is the one-line ``.plan/orchestrator/.../PLAN-LB-NN-*.md`` pointer). The
    request document itself and the outline are never treated as the spec.
    """
    try:
        root = Path(cwd_checkout_root())
    except Exception:
        return None
    for match in _MD_PATH_RE.finditer(text):
        candidate = match.group(1).strip()
        if candidate.endswith(REQUEST_FILE) or candidate.endswith('solution_outline.md'):
            continue
        resolved = (root / candidate).resolve()
        if resolved.is_file():
            return resolved
    return None


def _spec_deliverables(spec_text: str) -> list[dict[str, Any]]:
    """Split a spec's Deliverables section into per-deliverable Done-when rows."""
    sections = parse_document_sections(spec_text)
    body = sections.get('deliverables', spec_text)
    matches = list(_SPEC_DELIVERABLE_RE.finditer(body))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        block = body[match.start() : end]
        done = _SPEC_DONE_WHEN_RE.search(block)
        rows.append(
            {
                'spec_deliverable': f'D{match.group(1)}',
                'title': match.group(2).strip(),
                'done_when': normalize_criterion(done.group(1)) if done else '',
            }
        )
    return rows


def build_snapshot(plan_id: str) -> dict[str, Any]:
    """Assemble the frozen criteria record for ``plan_id``.

    Returns either the ``status: error`` payload for an absent outline, or the
    snapshot object. The outline's criteria are frozen per deliverable in
    outline order; the request's Done-when text is recorded verbatim; and, when
    the request names a spec document, every spec deliverable's Done-when is
    frozen as its OWN row, so a later merge of spec deliverables into one
    outline deliverable cannot collapse two clauses into one criterion.
    """
    deliverables = outline_deliverables(plan_id)
    if deliverables is None:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'outline_not_found',
            'message': 'solution_outline.md is absent; nothing was frozen',
        }
    request_text = _request_text(plan_id)
    spec_path = _referenced_spec_path(plan_id, request_text)
    spec: dict[str, Any] | None = None
    if spec_path is not None:
        spec = {
            'path': str(spec_path),
            'digest': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            'deliverables': _spec_deliverables(spec_path.read_text(encoding='utf-8')),
        }
    return {
        'schema': SCHEMA,
        'plan_id': plan_id,
        'deliverables': [
            {
                'number': deliverable['number'],
                'title': deliverable.get('title', ''),
                'criteria': [normalize_criterion(text) for text in deliverable.get('success_criteria', [])],
            }
            for deliverable in deliverables
        ],
        'request': {
            'done_when': request_done_when(request_text),
            'source': 'clarified_request' if request_text else 'absent',
        },
        'spec': spec,
        'authorized_changes': [],
    }


def read_snapshot(plan_id: str) -> dict[str, Any] | None:
    """Return the frozen snapshot, or ``None`` when it is absent or unreadable.

    An absent snapshot is the legacy shape (a plan that predates the freeze);
    the caller reports it as "no snapshot", never as an empty freeze.
    """
    path = snapshot_path(plan_id)
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(parsed, dict) or parsed.get('schema') != SCHEMA:
        return None
    return parsed


def write_snapshot(plan_id: str) -> dict[str, Any]:
    """Freeze the current outline as the plan's criteria snapshot."""
    snapshot = build_snapshot(plan_id)
    if snapshot.get('status') == 'error':
        return snapshot
    path = snapshot_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': SNAPSHOT_FILE,
        'deliverable_count': len(snapshot['deliverables']),
        'criterion_count': sum(len(row['criteria']) for row in snapshot['deliverables']),
        'request_done_when_count': len(snapshot['request']['done_when']),
        'spec_deliverable_count': len(snapshot['spec']['deliverables']) if snapshot['spec'] else 0,
    }


def _authorization(snapshot: dict[str, Any], number: Any, criterion: str) -> bool:
    """True when an operator decision authorizes this exact criterion change."""
    wanted = normalize_criterion(criterion)
    for entry in snapshot.get('authorized_changes') or []:
        if not isinstance(entry, dict):
            continue
        if entry.get('deliverable') == number and normalize_criterion(entry.get('criterion')) == wanted:
            return True
    return False


def criteria_drift(plan_id: str, current: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return the frozen criteria the current outline no longer carries verbatim.

    One row per unauthorized difference, in snapshot order:

    * ``deleted`` — the frozen criterion's text appears nowhere in the current
      outline (a dropped clause), or the whole deliverable is gone.
    * ``rewritten`` — the frozen position is occupied by different text (the
      clause was narrowed or reworded in place).
    * ``spec_criterion_missing`` — a spec deliverable's own frozen Done-when that
      NO current outline criterion covers. This is the PLAN-LB-42 failure: four
      spec deliverables merged into one outline deliverable, three generic
      criteria graded, and the dropped clause's Done-when never graded at all.
      Because each spec clause is frozen as its own row, a merge cannot remove it
      from the record, and the row below is what makes its absence a finding.

    A criterion an operator decision authorizes the change of is not reported.
    An absent snapshot reports nothing — there is nothing to compare against.
    """
    snapshot = read_snapshot(plan_id)
    if snapshot is None:
        return []
    if current is None:
        current = outline_deliverables(plan_id)
    if current is None:
        return []
    by_number = {row['number']: row for row in current if isinstance(row, dict) and 'number' in row}
    drift: list[dict[str, Any]] = []
    for row in snapshot.get('deliverables') or []:
        if not isinstance(row, dict):
            continue
        number = row.get('number')
        frozen = [normalize_criterion(text) for text in row.get('criteria') or []]
        live_row = by_number.get(number)
        live = [normalize_criterion(text) for text in (live_row or {}).get('success_criteria') or []]
        for index, criterion in enumerate(frozen):
            if not criterion or _authorization(snapshot, number, criterion):
                continue
            if criterion in live:
                continue
            kind = REWRITTEN if index < len(live) else DELETED
            drift.append(
                {
                    'deliverable': number,
                    'kind': kind,
                    'criterion': criterion,
                    'current': live[index] if index < len(live) else '',
                }
            )
    drift.extend(_spec_clause_drift(snapshot, by_number))
    return drift


def _spec_clause_drift(snapshot: dict[str, Any], by_number: dict[Any, dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per spec deliverable Done-when no current outline criterion covers.

    Coverage is deliberately loose — either the clause contains the criterion or
    the criterion contains the clause, on normalized text — because the outline
    is expected to state the clause in its own words rather than to quote it. A
    clause nothing covers is not covered.
    """
    spec_rows = (snapshot.get('spec') or {}).get('deliverables') or []
    if not spec_rows:
        return []
    outline = [normalize_criterion(text) for row in by_number.values() for text in (row.get('success_criteria') or [])]
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(spec_rows, start=1):
        if not isinstance(row, dict):
            continue
        clause = normalize_criterion(row.get('done_when'))
        if not clause:
            continue
        if any(clause in candidate or candidate in clause for candidate in outline if candidate):
            continue
        rows.append(
            {
                'deliverable': None,
                'spec_deliverable': row.get('spec_deliverable') or f'D{index}',
                'kind': SPEC_MISSING,
                'criterion': clause,
                'current': '',
            }
        )
    return rows


def authorize_change(
    plan_id: str, number: int, criterion: str, decision: str, phase: str = '3-outline'
) -> dict[str, Any]:
    """Record an operator decision authorizing one criterion change.

    The authorization is written into the snapshot AND to the plan's decision
    log, because "requires a logged operator decision" is the rule: an
    authorization that reached only the snapshot would be an unlogged edit. When
    the decision log cannot be written the authorization is NOT recorded and the
    verb refuses, so a comparison can never be satisfied by a record no operator
    decision stands behind.
    """
    if not str(decision or '').strip():
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_required',
            'message': 'a criterion change is authorized only by a named operator decision',
        }
    snapshot = read_snapshot(plan_id)
    if snapshot is None:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_absent',
            'message': f'{SNAPSHOT_FILE} does not exist; nothing can be authorized against it',
        }
    wanted = normalize_criterion(criterion)
    known = {
        normalize_criterion(text)
        for row in snapshot.get('deliverables') or []
        if row.get('number') == number
        for text in row.get('criteria') or []
    }
    if wanted not in known:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'criterion_not_frozen',
            'message': f'deliverable {number} carries no frozen criterion {criterion!r}',
        }
    try:
        import plan_logging
    except ImportError as exc:  # pragma: no cover - import-time environment failure
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': f'plan_logging could not be imported ({exc}); the authorization was not recorded',
        }
    logged = plan_logging.log_decision(
        plan_id,
        f'(criteria-integrity) Operator decision authorizes changing frozen criterion '
        f'D{number}: {criterion!r} — {decision}',
        phase=phase,
    )
    if logged.get('status') != 'success':
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': f'the operator decision could not be logged ({logged.get("error", "unknown")})',
        }
    entries = [
        entry
        for entry in snapshot.get('authorized_changes') or []
        if not (
            isinstance(entry, dict)
            and entry.get('deliverable') == number
            and normalize_criterion(entry.get('criterion')) == wanted
        )
    ]
    entries.append({'deliverable': number, 'criterion': criterion, 'decision': decision, 'phase': phase})
    snapshot['authorized_changes'] = entries
    atomic_write_file(snapshot_path(plan_id), json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': SNAPSHOT_FILE,
        'deliverable': number,
        'criterion': criterion,
        'authorized_count': len(entries),
    }


#: The plan-relative path of the functional review's verdict file.
FUNCTIONAL_VERDICT_FILE = 'work/functional-review-verdict.json'


def open_criteria(plan_id: str, verdict_file: Path | None = None) -> dict[str, Any]:
    """Return the frozen criteria the plan has not yet graded ``met``.

    The standing source for both the finalize triage loop and the finalize
    completion gate: a plan whose criteria snapshot still holds an unmet clause
    has open work even when the findings store is empty.

    ``source`` is ``snapshot`` when a snapshot exists and ``none`` when it does
    not (the legacy shape — no frozen criteria, so nothing is reported open).
    A criterion is ``met`` only when the functional review's verdict grades it
    ``met``; a clause the verdict does not carry at all is ``ungraded``, because
    an ungraded clause is exactly as open as an unevidenced one.
    """
    snapshot = read_snapshot(plan_id)
    if snapshot is None:
        return {'source': 'none', 'open_count': 0, 'open': []}
    path = verdict_file if verdict_file is not None else base_path('plans', plan_id, FUNCTIONAL_VERDICT_FILE)
    verdict = _functional_verdict(path)
    rows: list[dict[str, Any]] = []
    for row in snapshot.get('deliverables') or []:
        if not isinstance(row, dict):
            continue
        number = row.get('number')
        graded = verdict.get(number, [])
        for index, criterion in enumerate(row.get('criteria') or [], start=1):
            status = _graded_status(graded, criterion, index)
            if status == 'met':
                continue
            rows.append(
                {
                    'deliverable': number,
                    'criterion': criterion,
                    'criterion_index': index,
                    'status': status,
                }
            )
    return {
        'source': 'snapshot',
        'snapshot_deliverables': len(snapshot.get('deliverables') or []),
        'open_count': len(rows),
        'open': rows,
    }


def _functional_verdict(path: Path) -> dict[Any, list[Any]]:
    """Return ``{deliverable_number: [criterion rows]}`` from a verdict file.

    An absent or unreadable verdict yields an empty map, so every frozen
    criterion reads ``ungraded`` — which is open, the fail-closed direction.
    """
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    rows = parsed.get('deliverables') if isinstance(parsed, dict) else None
    result: dict[Any, list[Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        number = row.get('number')
        if isinstance(number, str) and number.strip().isdigit():
            number = int(number.strip())
        criteria = row.get('criteria')
        result[number] = list(criteria) if isinstance(criteria, list) else []
    return result


def _graded_status(criteria: list[Any], criterion: str, index: int) -> str:
    """Status the verdict gives one frozen criterion: text first, position second."""
    wanted = normalize_criterion(criterion)
    for row in criteria:
        if isinstance(row, dict) and normalize_criterion(row.get('criterion')) == wanted:
            return str(row.get('status') or 'ungraded')
    if index <= len(criteria):
        row = criteria[index - 1]
        if isinstance(row, dict):
            return str(row.get('status') or 'ungraded')
    return 'ungraded'


__all__ = [
    'DELETED',
    'FUNCTIONAL_VERDICT_FILE',
    'REQUEST_FILE',
    'REWRITTEN',
    'SCHEMA',
    'SNAPSHOT_FILE',
    'SPEC_MISSING',
    'authorize_change',
    'build_snapshot',
    'criteria_drift',
    'normalize_criterion',
    'open_criteria',
    'outline_deliverables',
    'read_snapshot',
    'request_done_when',
    'snapshot_path',
    'write_snapshot',
]
