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
imports from those higher layers, so there is no import cycle. The status record's
integrity block is written through ``_locks_core``'s guard — the SAME shared
coordination primitive ``manage-status`` commits ``status.json`` through — rather
than by importing the status writer upward.

Nothing in this module judges a plan. It reads documents, writes one JSON
artifact and reports named differences; the grading that consumes its output
stays in ``phase-6-finalize/scripts/_review_support_validate.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from _locks_core import _GUARD_SUFFIX, held_guard
from _plan_parsing import (
    extract_deliverables,
    parse_document_sections,
    split_deliverable_blocks,
)
from file_ops import atomic_write_bytes, atomic_write_file, base_path, cwd_checkout_root

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
#: The key INSIDE the integrity block that marks the snapshot as frozen.
SNAPSHOT_FROZEN_KEY = 'snapshot_frozen'
#: The status-record metadata list of heads at which an operator closed the
#: functional review. Its owning writer is ``manage-status loop-back close``; the
#: reader here and the protected-key guard in ``manage-status`` derive the name
#: from this one definition.
OVERRIDE_HEADS_KEY = 'functional_review_override_heads'
#: The status-record metadata keys whose only writers commit through their own
#: guarded read-modify-write. ``_status_core.write_status`` must carry them
#: forward from the live document, and a generic ``metadata --set`` must refuse
#: them. The MEMBERSHIP is defined here once, so the carry set and the protected
#: set cannot drift into covering different keys as a third owner-written key is
#: added.
PROTECTED_STATUS_METADATA_KEYS: tuple[str, ...] = (INTEGRITY_KEY, OVERRIDE_HEADS_KEY)

#: The key INSIDE the integrity block that carries the identity of the re-freeze
#: authorization this process set. A withdrawal is conditioned on it, so a failed
#: decision line removes only ITS OWN authorization and never a newer one another
#: call has since recorded and logged.
REFREEZE_TOKEN_KEY = 'refreeze_authorization_token'

#: Every outcome the two authorization writers can report for what became of an
#: authorization whose decision line could not be written. Single-sourced so the
#: documents that describe them — ``authorize_change``'s docstring and
#: ``phase-6-finalize/standards/review-rubric.md`` (the frozen-record finding) —
#: are checked against the code by a test instead of by a reader's memory:
#: ``test_the_authorization_outcome_vocabulary_matches_its_documents`` fails when a
#: term here is missing from either document or from this module's own source.
#:
#: Nothing here judges a plan; the terms describe the STATE the artifact and its
#: record were left in, which is what the operator needs to decide the repair.
AUTHORIZATION_OUTCOMES: tuple[str, ...] = (
    # authorize_refreeze: the withdrawal removed the authorization this call set.
    'withdrawn',
    'restored',
    # authorize_refreeze: a re-freeze consumed it first — that decision wins.
    'already_consumed',
    # authorize_refreeze: a newer authorization replaced ours; it survives.
    'superseded',
    # authorize_refreeze: the withdrawal itself could not be written.
    'not withdrawn',
    # _commit_authorization: the edit was undone and its binding restored.
    'rolled_back',
    # _commit_authorization: the edit was undone but its binding could not be
    # withdrawn, so the snapshot reads `tampered` — fail closed.
    'tamper_flagged',
    # _commit_authorization: the undo could not be completed at all.
    'inconsistent',
)


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


def _merge_integrity(plan_id: str, merge: Callable[[dict[str, Any]], None]) -> bool:
    """Merge into the status record's integrity block inside the status writers' guard.

    The guard is the SAME file-level ``O_EXCL`` guard ``manage-status`` commits
    ``status.json`` through (``_locks_core.rmw_json`` names it
    ``{status.json}.lock``), so this read-modify-write cannot interleave with a
    status writer's critical section: one of the two waits.

    Serialization alone does not make the block survive, because a status writer
    commits a WHOLE document assembled from a snapshot it read before the guard.
    The other half of the contract is on that side: ``_status_core.write_status``
    carries ``criteria_integrity`` forward from the document it reads inside the
    guard, so a writer holding a pre-merge snapshot cannot restore its stale copy
    over this merge. Neither half is sufficient alone.

    A plan with no readable status record is left untouched and reports ``False``;
    so does a guard that cannot be taken within its budget (``TimeoutError``) and
    a commit that fails. The caller never reads such a ``False`` as "recorded".
    """
    path = base_path('plans', plan_id, STATUS_FILE)
    try:
        with held_guard(path.with_name(f'{path.name}{_GUARD_SUFFIX}')):
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
            merge(block)
            try:
                atomic_write_file(path, json.dumps(status, indent=2, sort_keys=True) + '\n')
            except OSError:
                return False
    except OSError:
        return False
    return True


def record_integrity(plan_id: str, **fields: Any) -> bool:
    """Merge ``fields`` into the status record's integrity block; return success.

    The read, the merge and the write are one critical section on the guard the
    ``manage-status`` writers commit through, so a concurrent status write either
    lands before this merge (and is carried forward) or waits for it. The earlier
    design read the document and rewrote it outside any lock, so a status writer
    committing in that window lost the digest — the frozen artifact then had
    nothing binding it.

    A plan with no readable status record is left untouched and reports ``False``;
    the caller's artifact is rolled back rather than left only half-bound.
    """
    return _merge_integrity(plan_id, lambda block: block.update(fields))


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
    frozen = bool(info.get(SNAPSHOT_FROZEN_KEY))
    path = snapshot_path(plan_id)
    if path.is_file():
        recorded = info.get('snapshot_digest')
        if frozen and (not isinstance(recorded, str) or path_digest(path) != recorded):
            # A freeze with no digest string is not a binding: the record says the
            # snapshot is frozen but nothing can verify it, so it is treated as
            # tampered rather than trusted as 'frozen'.
            return 'tampered'
        return 'frozen' if frozen else 'present'
    return 'deleted' if frozen else 'absent'


def record_snapshot_digest(plan_id: str, *, consume_refreeze: bool = False) -> bool:
    """Record the frozen snapshot's digest in the status record, outside the file.

    ``consume_refreeze`` adds ``refreeze_authorized=False`` to the SAME guarded
    update. A re-freeze must consume its authorization atomically with the digest
    it authorizes: two writes would let a failed consumption leave the decision
    active, so the next call could re-freeze without a new decision.
    """
    path = snapshot_path(plan_id)
    if not path.is_file():
        return False
    try:
        digest = path_digest(path)
    except OSError:
        # The file existed a moment ago; a concurrent delete or a permission change
        # must report "not recorded" so the caller rolls its write back.
        return False
    fields: dict[str, Any] = {SNAPSHOT_FROZEN_KEY: True, 'snapshot_digest': digest}
    if consume_refreeze:
        fields['refreeze_authorized'] = False
    return record_integrity(plan_id, **fields)


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
    digest = canonical_digest(parsed)

    def _merge(block: dict[str, Any]) -> None:
        # The existing-verdicts read happens inside the critical section too, so a
        # functional and a code seal committed at the same time cannot each write
        # the other's entry away.
        existing = block.get('verdicts')
        verdicts = dict(existing) if isinstance(existing, dict) else {}
        verdicts[kind] = {'digest': digest, 'path': str(path)}
        block['verdicts'] = verdicts

    return _merge_integrity(plan_id, _merge)


def _log_failure_reason(logged: dict[str, Any]) -> str:
    """The most informative field of a failed decision-log result."""
    return str(logged.get('message') or logged.get('error') or 'unknown')


def authorize_refreeze(plan_id: str, decision: str, phase: str = '3-outline') -> dict[str, Any]:
    """Record an operator decision authorizing a re-freeze of the snapshot.

    The authorization is recorded in the plan's status record and logged through
    the same decision-log path ``criteria-authorize`` uses. The record commits
    FIRST — its prior value captured in the same guarded merge — and the decision
    line is written only for an authorization that landed: the line used to be
    written before the record, so a record failure left a log line for an
    authorization the status record does not carry.

    **The whole record-then-log sequence runs under the plan-scoped snapshot
    guard**, exactly as ``authorize_change`` does. Without it a ``write_snapshot``
    could start in the window between the record and the line, consume an
    authorization whose decision line is never written, and leave a snapshot
    re-frozen on a decision nobody recorded. With it, that ``write_snapshot``
    either waits for the guard or is refused as ``snapshot_busy``, and the
    withdraw-or-log decision below is made on state no other writer can change.
    The lock order is the one every caller of this module uses: snapshot guard →
    status guard.

    When the line cannot be written after a successful record, the authorization
    is withdrawn — **only its own**. The record carries a token this call set, and
    the withdrawal is conditioned on it, so an authorization another call has
    since recorded (and logged) survives: the result reports ``superseded`` rather
    than claiming an exact restore. The other reported states are ``withdrawn``
    (this call's authorization removed), ``restored`` (returned to the prior
    authorization this call found), ``already_consumed`` (a re-freeze used it
    first — that decision wins) and ``not withdrawn`` (the withdrawal itself could
    not be written).
    """
    if not str(decision or '').strip():
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_required',
            'message': 'a snapshot re-freeze is authorized only by a named operator decision',
        }
    try:
        with _snapshot_guard(plan_id):
            return _authorize_refreeze_locked(plan_id, decision, phase)
    except TimeoutError:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_busy',
            'message': 'another writer holds the criteria snapshot; the authorization was not recorded',
        }


def _authorize_refreeze_locked(plan_id: str, decision: str, phase: str) -> dict[str, Any]:
    """Record, log and (if the log fails) withdraw one authorization inside the guard."""
    try:
        import plan_logging
    except ImportError as exc:  # pragma: no cover - import-time environment failure
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': f'plan_logging could not be imported ({exc}); the authorization was not recorded',
        }
    already_authorized: dict[str, Any] = {}
    #: Identifies the authorization THIS call sets. A withdrawal compares it with
    #: the token on disk and removes only a match, so a newer authorization — and
    #: the decision line that went with it — survives an older call's failed log.
    token = uuid.uuid4().hex

    def _set_authorized(block: dict[str, Any]) -> None:
        # Capture the prior value in the SAME guarded merge that sets it, so a
        # withdrawal cannot restore a value read from an older document.
        already_authorized['previous'] = block.get('refreeze_authorized')
        already_authorized['previous_token'] = block.get(REFREEZE_TOKEN_KEY)
        block['refreeze_authorized'] = True
        block[REFREEZE_TOKEN_KEY] = token

    if not _merge_integrity(plan_id, _set_authorized):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'status_record_unavailable',
            'message': 'the plan status record could not be written, so the authorization was not recorded',
        }
    try:
        logged = plan_logging.log_decision(
            plan_id,
            f'(criteria-integrity) Operator decision authorizes re-freezing the criteria snapshot — {decision}',
            phase=phase,
        )
    except Exception as exc:  # a log call that raised is a failed log, not a reason to skip the withdrawal
        logged = {'status': 'error', 'error': type(exc).__name__, 'message': str(exc)}
    if logged.get('status') != 'success':
        outcome: dict[str, str] = {}

        def _withdraw(block: dict[str, Any]) -> None:
            # Best-effort undo of THIS call's authorization only. A newer
            # authorization carries a different token, so it is left standing with
            # its own decision line; a consumed one is gone and that decision wins.
            if block.get(REFREEZE_TOKEN_KEY) != token:
                outcome['state'] = 'superseded' if block.get('refreeze_authorized') is True else 'already_consumed'
                return
            if block.get('refreeze_authorized') is not True:
                # A re-freeze consumed THIS authorization; the re-freeze stands.
                block.pop(REFREEZE_TOKEN_KEY, None)
                outcome['state'] = 'already_consumed'
                return
            previous = already_authorized.get('previous')
            previous_token = already_authorized.get('previous_token')
            block.pop(REFREEZE_TOKEN_KEY, None)
            if previous is None:
                block.pop('refreeze_authorized', None)
                outcome['state'] = 'withdrawn'
            else:
                block['refreeze_authorized'] = previous
                if previous_token is not None:
                    block[REFREEZE_TOKEN_KEY] = previous_token
                outcome['state'] = 'restored' if previous else 'withdrawn'

        withdrawn = _merge_integrity(plan_id, _withdraw)
        if not withdrawn:
            effect = 'NOT withdrawn; the status record may still authorize it'
        elif outcome.get('state') == 'already_consumed':
            effect = 'not withdrawn: a concurrent re-freeze already consumed it'
        elif outcome.get('state') == 'superseded':
            effect = 'not withdrawn: a newer authorization replaced it, and that one stands'
        elif outcome.get('state') == 'restored':
            effect = 'withdrawn back to its prior authorization, so a re-freeze remains authorized'
        else:
            effect = 'withdrawn'
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': (
                f'the operator decision could not be logged ({_log_failure_reason(logged)}), so the '
                'authorization was ' + effect
            ),
        }
    return {'status': 'success', 'plan_id': plan_id, 'refreeze_authorized': True}


def plan_uses_worktree(plan_id: str) -> bool:
    """Whether the plan's status record declares an isolated worktree.

    Used to tell a plan that never had a worktree (graded against the main
    checkout) from one whose worktree is materialized but currently unresolvable
    (which must NOT be graded against a different tree).
    """
    status = _status_doc(plan_id)
    if status is None:
        return False
    metadata = status.get('metadata')
    return bool(metadata.get('use_worktree')) if isinstance(metadata, dict) else False


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
    heads = metadata.get(OVERRIDE_HEADS_KEY)
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


def _roll_back_snapshot(path: Path, previous: bytes | None, *, expected: bytes | None = None) -> bool:
    """Undo one snapshot write: restore the prior bytes, or remove a first freeze.

    The prior content is carried as BYTES, not text: a corrupt snapshot that does
    not decode must still be restorable, and decoding it would fail before the
    digest is even recorded. Restoring goes through an atomic write-and-replace,
    so a failure injected during the restore leaves the target holding its prior
    contents rather than a truncated prefix.

    ``expected`` makes the restore CONDITIONAL: it proceeds only when the target
    still holds exactly those bytes. A writer whose log call outlived the guard's
    stale threshold can find another writer has committed behind it; an
    unconditional restore would then erase that newer authorization. A mismatch
    returns ``False`` and changes nothing.

    Returns ``False`` when the rollback itself failed or was refused, so the
    caller reports that the artifact may still be on disk or hold another
    writer's commit rather than claiming it was removed.
    """
    try:
        if expected is not None and (not path.is_file() or path.read_bytes() != expected):
            return False
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write_bytes(path, previous)
    except OSError:
        return False
    return True


@contextmanager
def _snapshot_guard(plan_id: str) -> Iterator[None]:
    """Serialize every rewrite of one plan's snapshot artifact.

    The status guard protects the digest merge, but the authorization check and
    the snapshot write happen BEFORE it. Two concurrent re-freezes could both read
    ``refreeze_authorized: true`` and each write a snapshot on one decision. This
    plan-scoped guard covers the whole check-write-record sequence; the status
    guard is still taken inside it for the integrity record, so the lock order is
    always snapshot guard → status guard.
    """
    path = snapshot_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with held_guard(path.with_name(f'{path.name}{_GUARD_SUFFIX}')):
        yield


def write_snapshot(plan_id: str) -> dict[str, Any]:
    """Freeze the current outline as the plan's criteria snapshot.

    Serialized per plan against every other snapshot rewrite, so a single
    re-freeze authorization admits exactly one re-freeze.
    """
    try:
        with _snapshot_guard(plan_id):
            return _write_snapshot_locked(plan_id)
    except TimeoutError:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_busy',
            'message': 'another writer holds the criteria snapshot; nothing was written',
        }


def _write_snapshot_locked(plan_id: str) -> dict[str, Any]:
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
    previously_frozen = existing is not None or bool(info.get(SNAPSHOT_FROZEN_KEY))
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
    previous = path.read_bytes() if path.is_file() else None
    written_text = json.dumps(snapshot, indent=2, sort_keys=True) + '\n'
    atomic_write_file(path, written_text)
    # Bind the freeze OUTSIDE the file it protects: the status record (a different
    # file) holds the digest, so editing or deleting the snapshot
    # afterwards is detectable rather than silently read as the legacy shape.
    # A permitted re-freeze consumes its authorization in the SAME guarded update.
    consume_refreeze = previously_frozen and authorized
    if not record_snapshot_digest(plan_id, consume_refreeze=consume_refreeze):
        # No record, no freeze. A snapshot left behind here would be read as the
        # legacy "present" shape and its digest could never be checked again, so
        # the write is rolled back: the prior bytes when this was a re-freeze, and
        # nothing at all on a first freeze.
        rolled_back = _roll_back_snapshot(path, previous, expected=written_text.encode('utf-8'))
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_integrity_unrecorded',
            'message': (
                'the snapshot digest could not be recorded in the plan status record, so no frozen '
                'snapshot was kept' + ('' if rolled_back else ' (the partial snapshot could not be removed)')
            ),
        }
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
    log, because "requires a logged operator decision" is the rule. The read, the
    tamper check, the commit and the log line run under ONE plan-scoped snapshot
    guard: a re-freeze that commits in the window would otherwise be rewritten
    from the stale copy this function read before it took the guard, silently
    reverting it. The decision line is written only after the commit succeeds, so
    a ``snapshot_busy`` refusal — which is taken at the guard, before any read —
    writes no line for an authorization that never happened. When the line still
    cannot be written after a successful commit, the authorization is rolled back
    rather than left as an unlogged edit — ``rolled_back``. A rollback whose
    recorded digest cannot be withdrawn fails CLOSED (``tamper_flagged``: the edit
    is gone, the record still binds it, so the snapshot reads ``tampered`` and is
    refused until repaired) instead of keeping the edit standing with no decision
    line, and a rollback that cannot be completed at all reports ``inconsistent``.
    The whole vocabulary both authorization writers report is declared once in
    :data:`AUTHORIZATION_OUTCOMES` and held to these docstrings by
    ``test_the_authorization_outcome_vocabulary_matches_its_documents``.
    """
    if not str(decision or '').strip():
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_required',
            'message': 'a criterion change is authorized only by a named operator decision',
        }
    try:
        with _snapshot_guard(plan_id):
            return _authorize_change_locked(plan_id, number, criterion, decision, phase)
    except TimeoutError:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_busy',
            'message': 'another writer holds the criteria snapshot; the authorization was not recorded',
        }


def _authorize_change_locked(plan_id: str, number: int, criterion: str, decision: str, phase: str) -> dict[str, Any]:
    """Read, check and commit one authorization inside the caller's snapshot guard."""
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
    return _commit_authorization(plan_id, snapshot, number, criterion, decision, phase, plan_logging.log_decision)


def _commit_authorization(
    plan_id: str,
    snapshot: dict[str, Any],
    number: int,
    criterion: str,
    decision: str,
    phase: str,
    log_decision: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Rewrite the snapshot with one authorization, re-record its digest, then log it.

    The decision line is written only after the commit lands, and a failed line
    undoes the commit. The outcome vocabulary this can report is the one
    :data:`AUTHORIZATION_OUTCOMES` declares for this path — ``rolled_back`` when
    the edit was undone and its binding restored, ``tamper_flagged`` when the edit
    was undone but the binding could not be withdrawn (the snapshot then reads
    ``tampered`` and is refused until repaired: fail closed, because the retired
    alternative left the edit standing with no decision line), and
    ``inconsistent`` when the undo itself could not be completed — the snapshot or
    its record may still hold the edit.
    """
    wanted = normalize_criterion(criterion)
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
    path = snapshot_path(plan_id)
    previous = path.read_bytes() if path.is_file() else None
    committed_text = json.dumps(snapshot, indent=2, sort_keys=True) + '\n'
    committed = committed_text.encode('utf-8')
    atomic_write_file(path, committed_text)
    # Re-record the digest: the authorization rewrites the snapshot file, and a
    # recorded digest left on the pre-authorization bytes would read as tampering.
    # When it cannot be recorded the authorization is rolled back — the same
    # no-snapshot-without-its-binding rule write_snapshot applies. The rollback is
    # conditional on the file still holding THIS commit: a log call that outlived
    # the guard's stale threshold can let another writer commit behind us, and
    # restoring our prior bytes would erase that newer authorization.
    if not record_snapshot_digest(plan_id):
        rolled_back = _roll_back_snapshot(path, previous, expected=committed)
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'snapshot_integrity_unrecorded',
            'message': (
                'the rewritten snapshot digest could not be recorded, so the authorization was '
                + ('rolled back' if rolled_back else 'NOT fully rolled back; the snapshot may hold the edit')
            ),
        }
    # Only an authorization that LANDED gets a decision line. A line written
    # before the commit claimed an authorization a later refusal had discarded.
    try:
        logged = log_decision(
            plan_id,
            f'(criteria-integrity) Operator decision authorizes changing frozen criterion '
            f'D{number}: {criterion!r} — {decision}',
            phase=phase,
        )
    except Exception as exc:  # a log call that raised is a failed log, not a reason to skip the withdrawal
        logged = {'status': 'error', 'error': type(exc).__name__, 'message': str(exc)}
    if logged.get('status') != 'success':
        rolled_back = _roll_back_snapshot(path, previous, expected=committed)
        if not rolled_back:
            outcome = 'inconsistent'
        elif record_snapshot_digest(plan_id):
            outcome = 'rolled_back'
        else:
            # Fail closed. The edit is gone, but the status record still binds the
            # COMMITTED bytes' digest, so the snapshot reads ``tampered`` and every
            # consumer refuses it until an operator repairs the record. The retired
            # branch re-committed the edit instead (``kept``) so the record matched
            # its bytes — which left an authorization standing with no decision
            # line, the fail-open this closes.
            outcome = 'tamper_flagged'
        message = {
            'rolled_back': 'the authorization was rolled back',
            'tamper_flagged': (
                'the authorization was rolled back but its recorded digest could not be withdrawn, so the '
                'snapshot now reads tampered and must be repaired before it is used again'
            ),
            'inconsistent': 'the authorization was NOT fully rolled back; the snapshot or its record may hold the edit',
        }[outcome]
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'decision_log_unavailable',
            'message': (f'the operator decision could not be logged ({_log_failure_reason(logged)}), so {message}'),
        }
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
    * the row is matched by an explicit ``criterion_id`` or by EXACT normalised
      text. Position alone is never a match: a paraphrased row without its id
      leaves the criterion ungraded and open.

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
            status = _graded_status(graded, text, index, number)
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


_CRITERION_ID_RE = re.compile(r'(?:[Dd](\d+)\.)?[Cc](\d+)')


def criterion_id_parts(criterion_id: Any) -> tuple[int | None, int | None]:
    """Return ``(deliverable number, criterion position)`` named by a verdict id.

    Both the bare ``C3`` and the deliverable-qualified ``D2.C3`` spellings are
    accepted. ``(None, None)`` means the value names no frozen criterion at all —
    a malformed id is not a match, and the caller reports it rather than guessing.
    """
    match = _CRITERION_ID_RE.fullmatch(str(criterion_id or '').strip())
    if match is None:
        return None, None
    deliverable = int(match.group(1)) if match.group(1) else None
    return deliverable, int(match.group(2))


def verdict_row_matches(row: Any, criterion: str, index: int, deliverable: Any = None) -> bool:
    """Whether a verdict row answers the frozen criterion at ``index``.

    The stable id is tried first, then the exact normalised text. Position alone is
    never a match: the positional fallback released a criterion the reviewer had
    graded something else, which is the failure this predicate exists to close. A
    deliverable-qualified id (``D2.C1``) answers only inside deliverable 2 when
    ``deliverable`` is supplied.
    """
    if not isinstance(row, dict):
        return False
    named_deliverable, named_position = criterion_id_parts(row.get('criterion_id'))
    if named_deliverable is not None and deliverable is not None and named_deliverable != deliverable:
        return False
    if named_position == index:
        return True
    return normalize_criterion(row.get('criterion')) == normalize_criterion(criterion)


def _graded_status(criteria: list[Any], criterion: str, index: int, deliverable: Any = None) -> str:
    """Status a sealed verdict gives one frozen criterion, matched by stable id or text.

    A row carrying a parseable ``criterion_id`` wins and answers ONLY the criterion
    that id names. Exact text is tried next, but only for rows that name no
    criterion by a parseable id: a row graded ``C2`` whose text happens to equal
    criterion 1's frozen text does not grade criterion 1. Otherwise the criterion
    is ``ungraded``. There is no positional fallback: a verdict row that answers
    something else is not evidence for this criterion, and its position mere
    adjacency. A ``met`` row with no evidence is ``unevidenced`` here for the same
    reason the validator treats it so.
    """
    wanted = normalize_criterion(criterion)
    row: dict[str, Any] | None = None
    for candidate in criteria:
        if (
            isinstance(candidate, dict)
            and criterion_id_parts(candidate.get('criterion_id'))[1] == index
            and verdict_row_matches(candidate, criterion, index, deliverable)
        ):
            row = candidate
            break
    if row is None:
        for candidate in criteria:
            if not isinstance(candidate, dict):
                continue
            if criterion_id_parts(candidate.get('criterion_id'))[1] is not None:
                # An explicit id is the row's whole claim to a criterion. Matching
                # it by text after the id arm refused it (another position, or a
                # qualified id for another deliverable) would let a row graded
                # against one criterion close a different one.
                continue
            if normalize_criterion(candidate.get('criterion')) == wanted:
                row = candidate
                break

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
    'OVERRIDE_HEADS_KEY',
    'PROTECTED_STATUS_METADATA_KEYS',
    'REQUEST_FILE',
    'REWRITTEN',
    'SCHEMA',
    'SNAPSHOT_FILE',
    'SNAPSHOT_FROZEN_KEY',
    'SPEC_MISSING',
    'STATUS_FILE',
    'SUPERSEDED',
    'authorize_change',
    'authorize_refreeze',
    'build_snapshot',
    'criterion_id_parts',
    'criteria_drift',
    'integrity_record',
    'normalize_criterion',
    'open_criteria',
    'outline_deliverables',
    'path_digest',
    'plan_uses_worktree',
    'read_snapshot',
    'record_integrity',
    'record_snapshot_digest',
    'record_verdict_digest',
    'request_done_when',
    'snapshot_path',
    'snapshot_state',
    'verdict_row_matches',
    'write_snapshot',
]
