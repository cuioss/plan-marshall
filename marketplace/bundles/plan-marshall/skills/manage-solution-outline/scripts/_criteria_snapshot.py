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
#:
#: The clause runs from its marker to the NEXT deliverable heading (``N. **``) or
#: section heading, so a Done-when written as wrapped prose — or as a bullet list —
#: is captured whole. The retired ``(.+)`` captured one line, which truncated
#: every wrapped clause to its first line and read an outline that paraphrased the
#: rest as a missing criterion.
_SPEC_DONE_WHEN_RE = re.compile(
    r'(?:\*Done[- ]when:\*|\*\*Done[- ]when:\*\*|Done[- ]when:)\s*(.+?)(?=\n\s*(?:\d+\.\s+\*\*|#{1,6}\s)|\Z)',
    re.IGNORECASE | re.DOTALL,
)
#: A heading that introduces the request's own Done-when text.
_REQUEST_DONE_WHEN_RE = re.compile(r'^\s*(?:#+\s*)?(?:\*\*)?Done[- ]when(?:\*\*)?\s*:?\s*$', re.IGNORECASE)
#: A markdown path token in free request text (``.plan/x/PLAN-1.md``, ``doc/y.md``).
_MD_PATH_RE = re.compile(r'(?:^|\s)([\w./-]+\.md)(?=[\s,.;:)]|$)', re.MULTILINE)

DELETED = 'deleted'
REWRITTEN = 'rewritten'
#: The functional verdict that retires a deliverable: its criteria are not open.
SUPERSEDED = 'superseded'
#: A spec deliverable's own Done-when that no outline criterion covers.
SPEC_MISSING = 'spec_criterion_missing'
#: The request's own Done-when that no outline criterion covers.
REQUEST_MISSING = 'request_criterion_missing'

#: The authorship marker the review's own script verb stamps onto a verdict file.
AUTHORED_KEY = 'authored'
AUTHORSHIP_SCHEMA = 'review-verdict-authorship/1'
AUTHORSHIP_VERB = 'review_support author-verdict'

#: The plan-relative file of the plan's status record — where the seal and the
#: snapshot digest are bound outside the artifacts they protect.
STATUS_FILE = 'status.json'
#: The status-record metadata key holding those digests.
INTEGRITY_KEY = 'criteria_integrity'


def _status_doc(plan_id: str) -> dict[str, Any] | None:
    """Return the plan's parsed status record, or ``None`` when it cannot be read."""
    path = base_path('plans', plan_id, STATUS_FILE)
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def integrity_record(plan_id: str) -> dict[str, Any]:
    """Return the status record's criteria-integrity block, or ``{}`` when absent.

    The block is the OUTSIDE-the-artifact half of the seal: the snapshot digest
    and the verdict digests are recorded in the plan's status record — a DIFFERENT
    FILE from the artifact — so a digest recomputed inside a rewritten artifact
    does not reproduce the recorded one. An absent status record yields ``{}`` —
    the legacy shape — never an empty freeze.
    """
    status = _status_doc(plan_id)
    if status is None:
        return {}
    metadata = status.get('metadata')
    block = metadata.get(INTEGRITY_KEY) if isinstance(metadata, dict) else None
    return block if isinstance(block, dict) else {}


def record_integrity(plan_id: str, **fields: Any) -> bool:
    """Merge ``fields`` into the status record's integrity block; return success.

    Written by re-reading the live status document immediately before the write, so
    the merge carries the sibling fields it reads. The write is not serialized
    against another writer's critical section, so a concurrent status write can
    still race it — a narrow window the callers accept rather than importing the
    status writer upward. A plan with no readable status record is left untouched
    and reports ``False``; the caller's artifact is still written, it is simply not
    bound outside itself.
    """
    status = _status_doc(plan_id)
    if status is None:
        return False
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        metadata = {}
        status['metadata'] = metadata
    block = metadata.get(INTEGRITY_KEY)
    if not isinstance(block, dict):
        block = {}
        metadata[INTEGRITY_KEY] = block
    block.update(fields)
    try:
        atomic_write_file(base_path('plans', plan_id, STATUS_FILE), json.dumps(status, indent=2, sort_keys=True) + '\n')
    except OSError:
        return False
    return True


def path_digest(path: Path) -> str:
    """Return the SHA-256 of a file's exact bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_state(plan_id: str) -> str:
    """Classify the frozen snapshot's binding outside itself.

    * ``present`` — a snapshot file exists with no recorded freeze (legacy).
    * ``frozen`` — a snapshot file exists and its recorded digest matches.
    * ``tampered`` — the status record froze a snapshot whose bytes no longer
      match the recorded digest (edited in place).
    * ``deleted`` — the status record froze a snapshot and the file is gone. The
      deleted snapshot is the sharpest failure the old design allowed: every check
      that reads a missing snapshot silently took the legacy path.
    * ``absent`` — never frozen and no file (the legacy shape, no bindings).
    """
    info = integrity_record(plan_id)
    frozen = bool(info.get('snapshot_frozen'))
    path = snapshot_path(plan_id)
    if path.is_file():
        recorded = info.get('snapshot_digest')
        if frozen and isinstance(recorded, str) and path_digest(path) != recorded:
            return 'tampered'
        return 'frozen' if frozen else 'present'
    return 'deleted' if frozen else 'absent'


def record_snapshot_digest(plan_id: str) -> bool:
    """Record the frozen snapshot's digest in the status record, outside the file."""
    path = snapshot_path(plan_id)
    if not path.is_file():
        return False
    return record_integrity(plan_id, snapshot_frozen=True, snapshot_digest=path_digest(path))


def record_verdict_digest(plan_id: str, kind: str, verdict_file: str | Path) -> bool:
    """Record a sealed verdict's CONTENT digest in the status record, outside the file.

    The value stored is :func:`canonical_digest` of the parsed verdict — the same
    digest ``authorship_problem`` compares against — never the digest of the file's
    exact bytes, which would be a different number for the same verdict and would
    make every correctly sealed verdict read as modified.
    """
    path = Path(verdict_file)
    if not path.is_file():
        return False
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    if not isinstance(parsed, dict):
        return False
    existing = integrity_record(plan_id).get('verdicts')
    verdicts = dict(existing) if isinstance(existing, dict) else {}
    verdicts[kind] = {'digest': canonical_digest(parsed), 'path': str(path)}
    return record_integrity(plan_id, verdicts=verdicts)


def authorize_refreeze(plan_id: str, decision: str, phase: str = '3-outline') -> dict[str, Any]:
    """Record an operator decision authorizing a re-freeze of the snapshot.

    The decision is logged through the same decision-log path ``criteria-authorize``
    uses, and the authorization is recorded in the plan's status record so the next
    ``write_snapshot`` sees it. Logging and recording are one operation: an
    authorization that reached only one of the two is not a decision the record can
    stand behind, so a failure of either refuses.
    """
    if not str(decision or '').strip():
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_required',
            'message': 'a snapshot re-freeze is authorized only by a named operator decision',
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
        f'(criteria-integrity) Operator decision authorizes re-freezing the criteria snapshot — {decision}',
        phase=phase,
    )
    if logged.get('status') != 'success':
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': f'the operator decision could not be logged ({logged.get("error", "unknown")})',
        }
    if not record_integrity(plan_id, refreeze_authorized=True):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'status_record_unavailable',
            'message': 'the plan status record could not be written, so the authorization was not recorded',
        }
    return {'status': 'success', 'plan_id': plan_id, 'refreeze_authorized': True}


def _review_closed_reason(plan_id: str) -> str | None:
    """Return why the operator closed the functional review, or ``None``.

    The rubric's round-cap override (§ 8) closes the HEAD the operator judged and
    is recorded on the plan's status record — either as the override-head list or
    as the review step's ``may_close: operator_override`` fact. A closed review's
    criteria are not open: the operator decided the head ships unreviewed, so the
    gate must not read the ungraded criteria as outstanding work.
    """
    status = _status_doc(plan_id)
    if status is None:
        return None
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        return None
    heads = metadata.get('functional_review_override_heads')
    if isinstance(heads, list) and [head for head in heads if str(head).strip()]:
        return 'the operator closed the functional review past its round cap'
    phase_steps = metadata.get('phase_steps')
    review = None
    if isinstance(phase_steps, dict):
        finalize = phase_steps.get('6-finalize')
        if isinstance(finalize, dict):
            review = finalize.get('functional-review')
    facts = review.get('facts') if isinstance(review, dict) else None
    if isinstance(facts, dict) and facts.get('may_close') == 'operator_override':
        return 'the operator closed the functional review past its round cap'
    return None


def canonical_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 of a verdict's content, independent of key order and whitespace.

    The digest covers the verdict WITHOUT its authorship marker, so re-serialising
    the same verdict anywhere reproduces it, while any edit to a graded value does
    not. It lives here, not in the review layer, because the finalize completion
    gate reads the same verdict file and must apply the same rule.
    """
    body = {key: value for key, value in payload.items() if key != AUTHORED_KEY}
    encoded = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def seal_verdict(payload: dict[str, Any], kind: str) -> dict[str, Any]:
    """Return ``payload`` carrying its authorship marker (the marker last)."""
    sealed = {key: value for key, value in payload.items() if key != AUTHORED_KEY}
    sealed[AUTHORED_KEY] = {
        'schema': AUTHORSHIP_SCHEMA,
        'kind': kind,
        'verb': AUTHORSHIP_VERB,
        'digest': canonical_digest(payload),
    }
    return sealed


def authorship_problem(verdict: dict[str, Any], plan_id: str | None = None) -> str | None:
    """Return why the verdict does not match the reviewer's recorded output, or ``None``.

    A verdict the review's own script verb did not write has no marker; a verdict
    edited after the verb wrote it has a marker whose digest no longer matches the
    content. The failure is ``python3 -c`` editing the verdict file in place, and a
    rewritten criterion graded in the author's own words reads as clean without
    this check. The finalize completion gate applies it too, because an unsealed
    verdict must not release a plan.

    When ``plan_id`` names a plan whose status record holds a recorded verdict
    digest, that OUTSIDE-the-file digest is authoritative: recomputing the marker
    digest inside a rewritten verdict does not reproduce the recorded one, so an
    edit-then-re-seal is refused. Without a recorded digest the check falls back to
    the in-file marker digest (the legacy shape).
    """
    marker = verdict.get(AUTHORED_KEY)
    if not isinstance(marker, dict) or marker.get('schema') != AUTHORSHIP_SCHEMA:
        return f'the verdict was not written by {AUTHORSHIP_VERB}'
    digest = canonical_digest(verdict)
    recorded: Any = None
    kind = marker.get('kind')
    if plan_id and isinstance(kind, str):
        entry = (integrity_record(plan_id).get('verdicts') or {}).get(kind)
        recorded = entry.get('digest') if isinstance(entry, dict) else None
    if isinstance(recorded, str):
        if marker.get('digest') != recorded or digest != recorded:
            return 'the verdict was modified after the reviewer wrote it'
        return None
    if not isinstance(marker.get('digest'), str) or marker['digest'] != digest:
        return 'the verdict was modified after the reviewer wrote it'
    return None


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

    The path is constrained to the checkout: request text is untrusted input, and
    an absolute path or a ``..`` traversal would otherwise let it name a file
    outside the repository for this reader to open. A candidate that resolves
    outside the checkout root is skipped exactly as a non-existent one is.
    """
    try:
        root = Path(cwd_checkout_root()).resolve()
    except Exception:
        return None
    for match in _MD_PATH_RE.finditer(text):
        candidate = match.group(1).strip()
        if candidate.endswith(REQUEST_FILE) or candidate.endswith('solution_outline.md'):
            continue
        resolved = (root / candidate).resolve()
        if not resolved.is_relative_to(root):
            continue
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
    """Freeze the current outline as the plan's criteria snapshot.

    The FIRST freeze is unconditional: there is nothing to replace. A RE-freeze
    requires an operator decision logged through ``criteria-refreeze-authorize``
    (:func:`authorize_refreeze`), which records that decision in the plan's status
    record. A phase rollback alone is not such a decision — the retired check let
    ``set-phase 3-outline`` re-open the write, which let a plan re-freeze the
    criteria it was failing. The authorization is consumed by the re-freeze it
    permits, so one decision authorizes exactly one re-freeze.
    """
    existing = read_snapshot(plan_id)
    info = integrity_record(plan_id)
    authorized = bool(info.get('refreeze_authorized'))
    # The status record is the gate, not the file: deleting or corrupting the
    # snapshot file makes read_snapshot return None, and `existing is not None`
    # would then treat the call as a first freeze and leak a re-freeze without a
    # decision. `snapshot_frozen` lives outside the file, so it still says "frozen".
    previously_frozen = existing is not None or bool(info.get('snapshot_frozen'))
    if previously_frozen and not authorized:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'refreeze_requires_decision',
            'message': (
                f'{SNAPSHOT_FILE} was frozen at outline approval; re-freezing it requires an operator '
                f'decision logged through criteria-refreeze-authorize, not a phase rollback alone'
            ),
        }
    snapshot = build_snapshot(plan_id)
    if snapshot.get('status') == 'error':
        return snapshot
    if existing is not None:
        # An operator decision authorizes a criterion change; a re-freeze must not
        # silently revoke it.
        snapshot['authorized_changes'] = list(existing.get('authorized_changes') or [])
    path = snapshot_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
    # Bind the freeze OUTSIDE the file it protects: the status record (a different
    # file) holds the digest, so editing or deleting the snapshot
    # afterwards is detectable rather than silently read as the legacy shape.
    record_snapshot_digest(plan_id)
    if previously_frozen and authorized:
        # One decision authorizes one re-freeze: consume it so the next write is
        # gated again.
        record_integrity(plan_id, refreeze_authorized=False)
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': SNAPSHOT_FILE,
        'deliverable_count': len(snapshot['deliverables']),
        'criterion_count': sum(len(row['criteria']) for row in snapshot['deliverables']),
        'request_done_when_count': len(snapshot['request']['done_when']),
        'spec_deliverable_count': len(snapshot['spec']['deliverables']) if snapshot['spec'] else 0,
        'preserved_authorizations': len(snapshot['authorized_changes']),
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
    drift.extend(_request_clause_drift(snapshot, by_number))
    return drift


def _covered_by_outline(clause: str, outline: list[str]) -> bool:
    """Whether some outline criterion covers ``clause`` (loose containment either way)."""
    return any(clause in candidate or candidate in clause for candidate in outline if candidate)


def _outline_text(by_number: dict[Any, dict[str, Any]]) -> list[str]:
    return [normalize_criterion(text) for row in by_number.values() for text in (row.get('success_criteria') or [])]


def _request_clause_drift(snapshot: dict[str, Any], by_number: dict[Any, dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per request Done-when clause no current outline criterion covers.

    The request's Done-when is frozen for the same reason the spec's clauses are:
    it is part of what the plan was asked to deliver, and a plan graded only
    against its own outline can quietly deliver something else.
    """
    clauses = (snapshot.get('request') or {}).get('done_when') or []
    if not clauses:
        return []
    outline = _outline_text(by_number)
    return [
        {
            'deliverable': None,
            'spec_deliverable': f'request:{index}',
            'kind': REQUEST_MISSING,
            'criterion': normalize_criterion(clause),
            'current': '',
        }
        for index, clause in enumerate(clauses, start=1)
        if normalize_criterion(clause) and not _covered_by_outline(normalize_criterion(clause), outline)
    ]


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
    outline = _outline_text(by_number)
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(spec_rows, start=1):
        if not isinstance(row, dict):
            continue
        clause = normalize_criterion(row.get('done_when'))
        if not clause:
            continue
        if _covered_by_outline(clause, outline):
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
    if snapshot_state(plan_id) == 'tampered':
        # Authorizing against an edited snapshot would record the edited bytes as
        # the new frozen baseline and silently retire the tamper detection.
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_tampered',
            'message': f'{SNAPSHOT_FILE} no longer matches its recorded digest; nothing can be authorized against it',
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
    # Re-record the digest: the authorization rewrites the snapshot file, and a
    # recorded digest left on the pre-authorization bytes would read as tampering.
    record_snapshot_digest(plan_id)
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

    A criterion counts as ``met`` only under three conditions, all of which the
    validator would also enforce and none of which this reader may skip, because
    the completion gate never runs the validator:

    * the verdict carries the review's authorship seal and its digest matches, so
      a file rewritten in place does not release the plan;
    * the row's status is ``met`` AND it carries non-empty evidence;
    * the row is matched by a STABLE id — an explicit ``criterion_id`` wins, exact
      text is tried next, and the row's position within the deliverable is the last
      resort — so a verdict row that paraphrases the frozen criterion still answers
      for it.

    Anything else is open, which is the fail-closed direction. Four deliberate
    states additionally close criteria rather than reading them as open work:

    * an operator decision authorizes the exact change (``authorized_changes``);
    * the deliverable's verdict is ``superseded``;
    * the operator closed the review past its round cap (:func:`_review_closed_reason`);
    * ``state`` reports a snapshot the status record froze but which is now deleted
      or edited — the snapshot's own absence is the open criterion, and every check
      refuses rather than falling back to the legacy path.
    """
    state = snapshot_state(plan_id)
    if state in ('deleted', 'tampered'):
        return {
            'source': f'frozen_{state}',
            'verdict_state': 'absent',
            'open_count': 1,
            'open': [
                {
                    'deliverable': None,
                    'criterion': f'<the frozen criteria snapshot is {state}>',
                    'criterion_index': 1,
                    'status': 'ungraded',
                }
            ],
        }
    snapshot = read_snapshot(plan_id)
    if snapshot is None:
        return {'source': 'none', 'open_count': 0, 'open': []}
    # The operator's round-cap override closes the review FOR THE COMPLETION GATE:
    # its criteria are not outstanding work. Head-specificity (rubric § 8) governs
    # the REVIEW LOOP, which re-fires a delta round on a later head; the gate's job
    # is only to stop reading an operator-closed review as open work.
    closed_reason = _review_closed_reason(plan_id)
    if closed_reason is not None:
        return {'source': 'review_closed', 'closed_reason': closed_reason, 'open_count': 0, 'open': []}
    path = verdict_file if verdict_file is not None else base_path('plans', plan_id, FUNCTIONAL_VERDICT_FILE)
    verdict, verdict_state = _checked_verdict(path, plan_id)
    rows: list[dict[str, Any]] = []
    for row in snapshot.get('deliverables') or []:
        if not isinstance(row, dict):
            continue
        number = row.get('number')
        graded_row = verdict.get(number) or {}
        if str(graded_row.get('verdict') or '') == SUPERSEDED:
            continue
        graded = graded_row.get('criteria') or []
        for index, criterion in enumerate(row.get('criteria') or [], start=1):
            raw = criterion.get('text') if isinstance(criterion, dict) else criterion
            text = normalize_criterion(raw)
            if _authorization(snapshot, number, text):
                continue
            status = _graded_status(graded, text, index)
            if status == 'met':
                continue
            rows.append(
                {
                    'deliverable': number,
                    'criterion': text,
                    'criterion_index': index,
                    'status': status,
                }
            )
    return {
        'source': 'snapshot',
        'verdict_state': verdict_state,
        'snapshot_deliverables': len(snapshot.get('deliverables') or []),
        'open_count': len(rows),
        'open': rows,
    }


def _checked_verdict(path: Path, plan_id: str | None = None) -> tuple[dict[Any, dict[str, Any]], str]:
    """Return ``({deliverable: row}, state)`` for a verdict the gate may trust.

    ``state`` is ``sealed`` when the authorship marker matches, ``unsealed`` when
    the marker is absent or its digest does not match, and ``absent`` when there is
    no readable verdict. Only a sealed verdict is returned; every other state
    returns an empty map, so every frozen criterion reads ``ungraded`` — open.
    """
    if not path.is_file():
        return {}, 'absent'
    try:
        parsed = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}, 'unreadable'
    if not isinstance(parsed, dict) or authorship_problem(parsed, plan_id) is not None:
        return {}, 'unsealed'
    rows = parsed.get('deliverables')
    result: dict[Any, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        number = row.get('number')
        if isinstance(number, str) and number.strip().isdigit():
            number = int(number.strip())
        result[number] = row
    return result, 'sealed'


def _graded_status(criteria: list[Any], criterion: str, index: int) -> str:
    """Status a sealed verdict gives one frozen criterion, matched by stable id.

    A row carrying an explicit ``criterion_id`` wins; exact text is tried next; and
    the frozen criterion's own position (the stable id ``C{index}``) is the last
    resort, so a verdict row that paraphrases the criterion still answers for it.
    Every row is stored under its deliverable, so its position is the criterion
    index the author graded. A ``met`` row with no evidence is ``unevidenced`` here
    for the same reason the validator treats it so.
    """
    wanted = normalize_criterion(criterion)
    stable = f'C{index}'
    row: dict[str, Any] | None = None
    for candidate in criteria:
        if not isinstance(candidate, dict):
            continue
        cid = str(candidate.get('criterion_id') or '')
        if cid and cid.split('.')[-1] == stable:
            row = candidate
            break
    if row is None:
        for candidate in criteria:
            if isinstance(candidate, dict) and normalize_criterion(candidate.get('criterion')) == wanted:
                row = candidate
                break
    if row is None and 0 <= index - 1 < len(criteria) and isinstance(criteria[index - 1], dict):
        row = criteria[index - 1]
    if row is None:
        return 'ungraded'
    status = str(row.get('status') or 'ungraded')
    evidence = row.get('evidence')
    if status == 'met' and (not isinstance(evidence, list) or not [item for item in evidence if str(item).strip()]):
        return 'unevidenced'
    return status


__all__ = [
    'DELETED',
    'FUNCTIONAL_VERDICT_FILE',
    'INTEGRITY_KEY',
    'REQUEST_FILE',
    'REWRITTEN',
    'SCHEMA',
    'SNAPSHOT_FILE',
    'SPEC_MISSING',
    'STATUS_FILE',
    'SUPERSEDED',
    'authorize_change',
    'authorize_refreeze',
    'build_snapshot',
    'criteria_drift',
    'integrity_record',
    'normalize_criterion',
    'open_criteria',
    'outline_deliverables',
    'path_digest',
    'read_snapshot',
    'record_integrity',
    'record_snapshot_digest',
    'record_verdict_digest',
    'request_done_when',
    'snapshot_path',
    'snapshot_state',
    'write_snapshot',
]
