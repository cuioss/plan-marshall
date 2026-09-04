#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Finding, Q-Gate, and assessment storage for plan-level artifacts.

Provides JSONL-based storage for:
- Plan-scoped findings (long-lived, promotable) — split per type into findings/{type}.jsonl
- Phase-scoped Q-Gate findings (per-phase, not promotable) — findings/qgate-{phase}.jsonl
- Plan-scoped assessments (component evaluations with certainty/confidence) — findings/assessments.jsonl

Findings and Q-Gate share the same type taxonomy, resolution model, and severity values.
Assessments use a separate certainty/confidence model.

Storage:
- Plan findings: .plan/local/plans/{plan_id}/artifacts/findings/{type}.jsonl (one file per type)
- Q-Gate findings: .plan/local/plans/{plan_id}/artifacts/findings/qgate-{phase}.jsonl
- Assessments: .plan/local/plans/{plan_id}/artifacts/findings/assessments.jsonl

Every operation surface resolves that store through the explicit handle in
``_findings_store_state`` and reports the resulting ``store_resolution`` /
``store_path`` / ``findings_store_state`` / ``unresolved_store`` fields alongside
its own payload, so a count is never published without the substrate it was
computed from. A plan directory that is absent under the resolved root is
REFUSED (``error: findings_store_unresolved``) by every surface — read, write and
``add_`` alike — rather than answered with a clean zero or silently created.

Stdlib-only - no external dependencies (except shared modules via PYTHONPATH).
"""

import hashlib
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, NamedTuple

from _findings_store_state import (
    FindingsStore,
    resolve_findings_store,
    store_state_fields,
    store_unreached,
    unresolved_store_error,
)
from _preference_admissibility import (
    PREFERENCE_BASIS_PRESENCE_ONLY,
    PREFERENCE_BASIS_RECOGNIZED,
)
from _preference_admissibility import (
    preference_admissible as _preference_admissible,
)
from _preference_admissibility import (
    recognized_bot_kinds as _recognized_bot_kinds,
)
from bot_registry import bot_kinds as _registry_bot_kinds
from constants import (
    FILE_FINDINGS_DIR,
    FINDING_SEVERITIES,
    FINDING_TYPES,
    HASH_ID_LENGTH,
    QGATE_PHASES,
    QGATE_SOURCES,
    VALID_CERTAINTIES,
    VALID_RESOLUTIONS,
)
from input_validation import validate_plan_id
from jsonl_store import (
    append_jsonl,
    ensure_parent_dir,
    generate_hash_id,
    get_artifact_path,
    read_jsonl,
    read_jsonl_merge,
    timestamp,
    update_jsonl,
)

# --- Backward-compatible aliases (imported from constants) ---
# These names are re-exported for manage-findings.py and tests
SEVERITIES = FINDING_SEVERITIES
RESOLUTIONS = VALID_RESOLUTIONS
CERTAINTY_VALUES = VALID_CERTAINTIES

# The published partition of ``add_qgate_finding``'s four-valued ``status`` into
# "the record is in the store" versus "the record was rejected".
#
# ``success`` (freshly appended), ``deduplicated`` (an identical pending record
# already exists) and ``reopened`` (a matching resolved record was returned to
# pending) all mean the finding IS in the store. The remaining value, ``error``,
# means it is NOT — and callers MUST NOT fold it into the two benign no-op
# outcomes. Every caller consults this set rather than re-deriving the partition
# inline with ``status == 'success'``.
QGATE_PERSIST_OK = frozenset({'success', 'deduplicated', 'reopened'})

# Valid kind discriminator values for pr-comment findings.
PR_COMMENT_KINDS = ['inline', 'review_body', 'issue_comment']

# Valid reviewer-bot identity values for pr-comment findings (derived from author).
#
# Data-not-code: the bot-kind set is DERIVED at import time from the per-bot
# registry docs (``automatic-review/standards/{bot_kind}.md``) via
# ``bot_registry.bot_kinds()`` rather than hard-coded here. ``BOT_KINDS`` stays a
# stable importable module-level name — ``manage-findings.py`` uses it as an
# argparse ``choices=`` list and ``add_finding`` validates ``bot_kind`` against
# it — so adding a bot is a pure standards-doc edit with no change to this file.
BOT_KINDS = _registry_bot_kinds()

# ``PREFERENCE_BASIS_RECOGNIZED`` / ``PREFERENCE_BASIS_PRESENCE_ONLY`` are imported
# above from ``_preference_admissibility``, which owns the rule whose two paths they
# name. The field is published on every payload the narrowing produced — the
# three-value house pattern already used by ``notation_cross_check`` and Sonar's
# ``count_status``.

# Default per-field byte cap for quarantined raw_input free-text (64 KiB).
# The `finding_raw_input_max_bytes` config knob (seeded by manage-config) overrides
# this default; callers thread the resolved value in via `raw_input_max_bytes`.
DEFAULT_RAW_INPUT_MAX_BYTES = 65536

# Marker appended to a raw_input value that exceeded the per-field byte cap.
RAW_INPUT_TRUNCATION_MARKER = '[truncated]'


# --- Untrusted free-text quarantine ---


def _quarantine_raw_input(
    raw_input: dict[str, Any] | None,
    max_bytes: int = DEFAULT_RAW_INPUT_MAX_BYTES,
) -> dict[str, str] | None:
    """Store untrusted free-text under a quarantined `raw_input.{field}` namespace.

    Each field's value is stringified, UTF-8 encoded, and capped at ``max_bytes``.
    A value that overflows the cap is truncated to the byte budget (decoding
    defensively so a multi-byte character split at the boundary never raises) and
    the ``RAW_INPUT_TRUNCATION_MARKER`` is appended so downstream readers can tell
    the value was clipped. Returns ``None`` for an empty/absent mapping so callers
    omit the key entirely.
    """
    if not raw_input:
        return None

    # Clamp the cap to a non-negative budget: a misconfigured non-positive
    # `max_bytes` would otherwise make `encoded[:max_bytes]` slice from the end
    # (Python negative-index semantics) and silently bypass the byte cap. A zero
    # budget truncates the value to just the marker.
    safe_max_bytes = max(max_bytes, 0)

    quarantined: dict[str, str] = {}
    for field, value in raw_input.items():
        text = value if isinstance(value, str) else str(value)
        encoded = text.encode('utf-8')
        if len(encoded) > safe_max_bytes:
            text = encoded[:safe_max_bytes].decode('utf-8', errors='ignore') + RAW_INPUT_TRUNCATION_MARKER
        quarantined[field] = text
    return quarantined


def _content_discriminator(
    detail: str | None,
    file_path: str | None,
    rule: str | None,
) -> str:
    """Stable content hash over (detail, file_path, rule) used as a dedup discriminator.

    Folded into the Q-Gate dedup key so that a bare title collision alone can NEVER
    reopen an unrelated resolved finding of the same class,
    while an intended same-defect merge across iterations (same title AND same
    discriminator) still collapses. The NUL separator prevents field-boundary
    ambiguity (e.g. `detail='a', file='b'` vs `detail='a\\x00b', file=''`).
    """
    basis = f'{detail or ""}\x00{file_path or ""}\x00{rule or ""}'
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()[:HASH_ID_LENGTH]


# --- Path Helpers ---


def get_findings_dir(plan_id: str) -> Path:
    """Returns .plan/local/plans/{plan_id}/artifacts/findings/"""
    validate_plan_id(plan_id)
    return get_artifact_path(plan_id, FILE_FINDINGS_DIR)


def get_findings_path(plan_id: str, finding_type: str) -> Path:
    """Returns .plan/local/plans/{plan_id}/artifacts/findings/{type}.jsonl

    Per-type splitting: each finding type lives in its own JSONL file under the
    findings/ subdirectory. Cross-type queries merge results across files via
    `read_jsonl_merge` over `get_findings_dir(plan_id)`.
    """
    if finding_type not in FINDING_TYPES:
        raise ValueError(f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}')
    return get_findings_dir(plan_id) / f'{finding_type}.jsonl'


def get_qgate_path(plan_id: str, phase: str) -> Path:
    """Returns .plan/local/plans/{plan_id}/artifacts/findings/qgate-{phase}.jsonl"""
    if phase not in QGATE_PHASES:
        raise ValueError(f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}')
    return get_findings_dir(plan_id) / f'qgate-{phase}.jsonl'


# --- Store-scoped path helpers ---
#
# The four public path helpers above compose from the CWD-resolved root. Every
# operation surface instead composes from its own resolved
# :class:`FindingsStore`, because the store is the thing that knows whether it
# was reached at all — and, under ``--any-checkout``, it may legitimately be the
# store of a DIFFERENT checkout than the one the cwd resolves to.


def _store_findings_path(store: FindingsStore, finding_type: str) -> Path:
    """Return ``{store}/{type}.jsonl`` for a validated finding type."""
    if finding_type not in FINDING_TYPES:
        raise ValueError(f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}')
    return _store_dir(store) / f'{finding_type}.jsonl'


def _store_qgate_path(store: FindingsStore, phase: str) -> Path:
    """Return ``{store}/qgate-{phase}.jsonl`` for a validated Q-Gate phase."""
    if phase not in QGATE_PHASES:
        raise ValueError(f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}')
    return _store_dir(store) / f'qgate-{phase}.jsonl'


def _store_assessments_path(store: FindingsStore) -> Path:
    """Return ``{store}/assessments.jsonl``."""
    return _store_dir(store) / 'assessments.jsonl'


def _store_dir(store: FindingsStore) -> Path:
    """Return the store's findings directory, asserting it was actually reached.

    Every caller has already refused on :func:`store_unreached`, so a ``None``
    path here is a programming error rather than a runtime condition — raising
    is correct, and is what keeps a composed-from-``None`` path from ever
    reaching the filesystem.
    """
    if store.path is None:
        raise ValueError(f'findings store was not reached ({store.state}): {store.detail}')
    return store.path


def _list_finding_files_in(store: FindingsStore) -> list[Path]:
    """List the per-type finding JSONL files under ``store``.

    This is the PLAN-FINDINGS file set: ``qgate-*.jsonl`` and
    ``assessments.jsonl`` are deliberately excluded. It bounds BOTH the read
    (:func:`get_finding`) and the write (:func:`_update_in_finding_files`), so
    the two can no longer disagree about which records a verb may touch. A hash
    that lives in one of the excluded files is REPORTED by
    :func:`_identify_in_other_store` rather than silently missed or silently
    written.
    """
    findings_dir = store.path
    if findings_dir is None or not findings_dir.is_dir():
        return []
    return [
        findings_dir / f'{t}.jsonl'
        for t in FINDING_TYPES
        if (findings_dir / f'{t}.jsonl').exists()
    ]


def _update_in_finding_files(store: FindingsStore, hash_id: str, updates: dict[str, Any]) -> bool:
    """Update a record by ``hash_id`` across the PLAN-FINDINGS file set only.

    The write set is enumerated, never globbed. A directory-wide glob over the
    findings directory also reaches ``qgate-*.jsonl`` and ``assessments.jsonl``
    — stores whose records carry a different field set and a different resolver
    — so a Q-Gate or assessment hash handed to a plan-findings write verb would
    be stamped with fields its record kind does not carry. Iterating
    :func:`_list_finding_files_in` makes the write set identical to the read set
    by construction. Stops at the first match and rewrites only that file;
    returns ``False`` when no plan-findings file holds the hash.
    """
    for path in _list_finding_files_in(store):
        if update_jsonl(path, hash_id, updates):
            return True
    return False


def _identify_in_other_store(store: FindingsStore, hash_id: str) -> dict[str, str] | None:
    """Identify — never resolve — a hash that lives in a sibling store.

    The plan-findings verbs (``get``, ``resolve``, ``promote``,
    ``mark_finding_responded``) are scoped to the plan-findings file set, so a
    Q-Gate or assessment hash is legitimately not-found for them. Reporting a
    bare ``Finding not found`` for a hash that demonstrably exists one file over
    is the false negative this scan removes.

    It is an IDENTIFICATION scan only: the sibling record is never read into a
    return value and never written. Widening the verbs to resolve it would be
    wrong on the merits — a Q-Gate record carries ``resolution_timestamp`` that
    ``resolve_finding`` does not write, and its resolution is phase-scoped — so
    the answer is the name of the store and of the verb that owns it.

    Returns ``{'store', 'verb'}`` on a hit, or ``None`` when the hash is in no
    sibling store either.
    """
    findings_dir = store.path
    if findings_dir is None or not findings_dir.is_dir():
        return None

    for phase in QGATE_PHASES:
        path = findings_dir / f'qgate-{phase}.jsonl'
        if any(record.get('hash_id') == hash_id for record in read_jsonl(path)):
            return {
                'store': f'the Q-Gate store for phase {phase}',
                'verb': f'qgate resolve --phase {phase}',
            }

    assessments = findings_dir / 'assessments.jsonl'
    if any(record.get('hash_id') == hash_id for record in read_jsonl(assessments)):
        return {'store': 'the assessment store', 'verb': 'assessment get'}
    return None


def _not_found(
    plan_id: str,
    store: FindingsStore,
    hash_id: str,
    label: str,
) -> dict[str, Any]:
    """Build the not-found payload for ``hash_id``, distinguishing a sibling store.

    A hash absent from the plan-findings file set but present in a sibling store
    returns ``error: finding_in_other_store`` naming that store and the verb that
    owns it; a hash absent everywhere returns the plain not-found message. Both
    carry the store-state fields, so the answer always states which substrate it
    was computed against.
    """
    elsewhere = _identify_in_other_store(store, hash_id)
    if elsewhere is not None:
        return {
            'status': 'error',
            'error': 'finding_in_other_store',
            'plan_id': plan_id,
            'hash_id': hash_id,
            'found_in': elsewhere['store'],
            'use_verb': elsewhere['verb'],
            'message': (
                f'{label} not found in the plan-findings store: {hash_id} exists in '
                f"{elsewhere['store']}, which this verb does not own — use "
                f"`{elsewhere['verb']}` instead"
            ),
            **store_state_fields(store),
        }
    return {
        'status': 'error',
        'message': f'{label} not found: {hash_id}',
        **store_state_fields(store),
    }


# --- Shared Query Helper ---


def _filter_records(
    records: list[dict[str, Any]],
    exact_filters: dict[str, Any] | None = None,
    type_filter: set[str] | None = None,
    file_pattern: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    promoted: bool | None = None,
) -> list[dict[str, Any]]:
    """Filter records by common criteria.

    Args:
        records: List of record dicts to filter
        exact_filters: Dict of field_name → required_value for exact match
        type_filter: Set of allowed type values (for comma-separated type filters)
        file_pattern: Glob pattern for file_path field
        min_confidence: Minimum confidence value (inclusive)
        max_confidence: Maximum confidence value (inclusive)
        promoted: If set, filter by promoted boolean

    Returns:
        Filtered list of records
    """
    filtered = []
    for r in records:
        if type_filter and r.get('type') not in type_filter:
            continue
        if exact_filters:
            skip = False
            for field, value in exact_filters.items():
                if value is not None and r.get(field) != value:
                    skip = True
                    break
            if skip:
                continue
        if promoted is not None and r.get('promoted', False) != promoted:
            continue
        if file_pattern and not fnmatch(r.get('file_path', ''), file_pattern):
            continue
        if min_confidence is not None and r.get('confidence', 0) < min_confidence:
            continue
        if max_confidence is not None and r.get('confidence', 100) > max_confidence:
            continue
        filtered.append(r)
    return filtered


class PreferenceAdmissibility(NamedTuple):
    """The once-per-query resolution of the authorship gate, plus its disclosure.

    ``recognized`` is the resolved reviewer-identity set, or ``None`` when the
    registry could not be resolved — the value :func:`_preference_admissible`
    reads to take its documented degrade-to-presence-only path. ``basis`` is the
    two-valued disclosure of WHICH path the narrowing ran on, and is ``None``
    exactly when the narrowing is off (so nothing is disclosed about a gate that
    never ran).
    """

    enabled: bool
    recognized: frozenset[str] | None
    basis: str | None


def _resolve_preference_admissibility(enabled: bool) -> PreferenceAdmissibility:
    """Resolve the recognized reviewer set ONCE and record which basis it yields.

    Private on purpose. It is an internal helper of the two query surfaces, not a
    findings OPERATION: it resolves no store and publishes none of the four
    store-state fields every operation payload carries. The operation roster in
    ``test_findings_store_resolution.py`` is derived from this module's PUBLIC
    functions, so a public name here would be pulled into a store-state contract
    this helper cannot satisfy.

    The gate degrades to a presence-only check when the live registry cannot be
    resolved (see :mod:`_preference_admissibility` § Degrade-to-presence-only).
    That degrade is deliberate — over-excluding every bot-attributed comment
    would hand preference learning a clean zero over an unread population — but
    it MUST NOT be silent, so the basis it ran on travels with the result and is
    published as ``preference_admissibility_basis`` on every payload the flag
    narrowed.

    Args:
        enabled: Whether the caller asked for the authorship narrowing at all.

    Returns:
        The resolution context. When ``enabled`` is False nothing is resolved and
        ``basis`` is ``None``, so no disclosure field is emitted for a gate that
        did not run.
    """
    if not enabled:
        return PreferenceAdmissibility(enabled=False, recognized=None, basis=None)
    recognized = _recognized_bot_kinds()
    basis = (
        PREFERENCE_BASIS_PRESENCE_ONLY if recognized is None else PREFERENCE_BASIS_RECOGNIZED
    )
    return PreferenceAdmissibility(enabled=True, recognized=recognized, basis=basis)


def _narrow_to_preference_admissible(
    records: list[dict[str, Any]],
    admissibility: PreferenceAdmissibility,
) -> list[dict[str, Any]]:
    """Apply the shared authorship-admissibility rule when it is enabled.

    The rule itself lives in :mod:`_preference_admissibility` and is applied
    here, never re-derived; the recognized-set resolution (and the ``None``
    pass-through that selects the degrade path) is owned by
    :func:`_resolve_preference_admissibility`, so a single query resolves the
    registry once no matter how many record slices it narrows. Returns
    ``records`` untouched when the narrowing is off, which is what keeps the
    default-OFF flag free of any cost for callers that never ask for it.
    """
    if not admissibility.enabled:
        return records
    return [r for r in records if _preference_admissible(r, admissibility.recognized)]


def _preference_basis_fields(admissibility: PreferenceAdmissibility) -> dict[str, str]:
    """Return the disclosure field, or nothing when the narrowing was off.

    Emitting ``preference_admissibility_basis`` on a payload the gate never
    touched would assert something about a check that did not run, so the field
    is present exactly when the caller asked for the narrowing.
    """
    if admissibility.basis is None:
        return {}
    return {'preference_admissibility_basis': admissibility.basis}


# --- Plan Findings ---


def add_finding(
    plan_id: str,
    finding_type: str,
    title: str,
    detail: str,
    file_path: str | None = None,
    line: int | None = None,
    component: str | None = None,
    module: str | None = None,
    rule: str | None = None,
    severity: str | None = None,
    author: str | None = None,
    kind: str | None = None,
    reviewed_commit_sha: str | None = None,
    bot_kind: str | None = None,
    raw_input: dict[str, Any] | None = None,
    raw_input_max_bytes: int = DEFAULT_RAW_INPUT_MAX_BYTES,
) -> dict[str, Any]:
    """Add a finding record.

    Untrusted free-text supplied via ``raw_input`` is stored under a quarantined
    ``raw_input.{field}`` sub-object (per-field byte cap ``raw_input_max_bytes``);
    top-level fields stay clean-by-construction until the batched ingestion pass
    promotes validated values.

    REFUSES against an absent plan directory. The terminal write is
    ``append_jsonl``, whose ``ensure_parent_dir`` mkdirs the whole chain, so an
    add for a ``plan_id`` with no directory under the resolved root would
    MANUFACTURE the very phantom store the read surfaces exist to surface. The
    guard keys on ``plans/{plan_id}/``, never on ``artifacts/findings/``, so a
    real plan's first-ever finding still creates its findings directory.
    """
    if finding_type not in FINDING_TYPES:
        return {'status': 'error', 'message': f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}'}

    if severity and severity not in SEVERITIES:
        return {'status': 'error', 'message': f'Invalid severity: {severity}. Must be one of {SEVERITIES}'}

    if kind and kind not in PR_COMMENT_KINDS:
        return {'status': 'error', 'message': f'Invalid kind: {kind}. Must be one of {PR_COMMENT_KINDS}'}

    if bot_kind and bot_kind not in BOT_KINDS:
        return {'status': 'error', 'message': f'Invalid bot_kind: {bot_kind}. Must be one of {BOT_KINDS}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    hash_id = generate_hash_id()
    record: dict[str, Any] = {
        'hash_id': hash_id,
        'timestamp': timestamp(),
        'type': finding_type,
        'title': title,
        'detail': detail,
        'resolution': 'pending',
        'resolution_detail': None,
        'promoted': False,
        'promoted_to': None,
    }

    if file_path:
        record['file_path'] = file_path
    if line is not None:
        record['line'] = line
    if component:
        record['component'] = component
    if module:
        record['module'] = module
    if rule:
        record['rule'] = rule
    if severity:
        record['severity'] = severity
    if author:
        record['author'] = author
    if kind:
        record['kind'] = kind
    if reviewed_commit_sha:
        record['reviewed_commit_sha'] = reviewed_commit_sha
    if bot_kind:
        record['bot_kind'] = bot_kind

    quarantined = _quarantine_raw_input(raw_input, raw_input_max_bytes)
    if quarantined:
        record['raw_input'] = quarantined

    append_jsonl(_store_findings_path(store, finding_type), record)

    return {
        'status': 'success',
        'hash_id': hash_id,
        'type': finding_type,
        **store_state_fields(store),
    }


def query_findings(
    plan_id: str,
    finding_type: str | None = None,
    resolution: str | None = None,
    promoted: bool | None = None,
    file_pattern: str | None = None,
    author: str | None = None,
    kind: str | None = None,
    bot_kind: str | None = None,
    any_checkout: bool = False,
    *,
    preference_admissible: bool = False,
) -> dict[str, Any]:
    """Query findings across all per-type files, merging results.

    Storage is split into findings/{type}.jsonl. The full record set across all
    per-type files is always loaded (in canonical FINDING_TYPES order) so
    `total_count` reflects the entire store; type/resolution/file_pattern/promoted
    filters then narrow the result to `filtered_count`. This preserves the
    CLI-surface semantics from the pre-split single-file layout.

    ``preference_admissible`` is an opt-in narrowing (default OFF, so every
    existing caller is unchanged) that applies the shared authorship-admissibility
    rule from :mod:`_preference_admissibility` — the SAME predicate the cross-plan
    auditor delegates to, not a second copy of it. It composes with the other
    filters by acting on the already-filtered slice, exactly as they do, so
    ``total_count`` keeps spanning the whole store and ``filtered_count`` reports
    the post-narrowing result. It is KEYWORD-ONLY: both this function and
    :func:`query_findings_unified` are consumed across skills, and two adjacent
    booleans that a positional call could silently swap is a binding hazard no
    caller should have to notice.

    When the narrowing is on, the return carries
    ``preference_admissibility_basis`` — ``recognized`` when the live reviewer
    registry resolved, ``presence_only`` when it did not and the gate degraded to
    admitting any present ``bot_kind``. The recognized reviewer set is resolved
    ONCE per query rather than per record, mirroring the auditor's
    once-per-corpus-walk resolution.

    Every return states which store the counts were computed from. A plan
    directory that is absent under the resolved root is REFUSED
    (``error: findings_store_unresolved``) rather than reported as a clean zero;
    a resolved plan directory holding no findings keeps returning
    ``status: success`` / ``total_count: 0`` with ``findings_store_state:
    missing``.
    """
    return _query_findings(
        plan_id,
        finding_type=finding_type,
        resolution=resolution,
        promoted=promoted,
        file_pattern=file_pattern,
        author=author,
        kind=kind,
        bot_kind=bot_kind,
        any_checkout=any_checkout,
        admissibility=_resolve_preference_admissibility(preference_admissible),
    )


def _query_findings(
    plan_id: str,
    *,
    finding_type: str | None,
    resolution: str | None,
    promoted: bool | None,
    file_pattern: str | None,
    author: str | None,
    kind: str | None,
    bot_kind: str | None,
    any_checkout: bool,
    admissibility: PreferenceAdmissibility,
) -> dict[str, Any]:
    """Query the per-plan store against an ALREADY-RESOLVED admissibility context.

    Split out of :func:`query_findings` so :func:`query_findings_unified` can
    narrow both of its slices against one resolution of the reviewer registry —
    a single query then reports a single ``preference_admissibility_basis``,
    instead of two independent resolutions that could disagree.
    """
    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    paths = [_store_findings_path(store, t) for t in FINDING_TYPES]
    records = read_jsonl_merge(paths)

    type_filter = {t.strip() for t in finding_type.split(',')} if finding_type else None
    filtered = _filter_records(
        records,
        exact_filters={'resolution': resolution, 'author': author, 'kind': kind, 'bot_kind': bot_kind},
        type_filter=type_filter,
        file_pattern=file_pattern,
        promoted=promoted,
    )
    filtered = _narrow_to_preference_admissible(filtered, admissibility)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': len(records),
        'filtered_count': len(filtered),
        'findings': filtered,
        'file_paths': list({r.get('file_path') for r in filtered if r.get('file_path')}),
        **_preference_basis_fields(admissibility),
        **store_state_fields(store),
    }


def query_findings_unified(
    plan_id: str,
    finding_type: str | None = None,
    resolution: str | None = None,
    promoted: bool | None = None,
    file_pattern: str | None = None,
    author: str | None = None,
    kind: str | None = None,
    bot_kind: str | None = None,
    any_checkout: bool = False,
    *,
    preference_admissible: bool = False,
) -> dict[str, Any]:
    """Query the per-plan findings store merged with pending per-phase Q-Gate findings.

    Returns the union of:
    - the per-PLAN findings (via `query_findings`, honouring the same
      type/resolution/promoted/file_pattern/author/kind/bot_kind filters), and
    - the PENDING Q-Gate findings across every phase in `QGATE_PHASES`, with the
      same `finding_type` / `file_pattern` / `author` / `kind` / `bot_kind` filters applied for parity.

    ``preference_admissible`` narrows BOTH slices, not just the per-plan one. The
    flag is a single opt-in on one read verb, so applying it to only half of what
    that verb returns would make it silently partial — the caller would still be
    handed the very pipeline-authored comments it asked to exclude, with nothing
    in the payload to say so. It is KEYWORD-ONLY for the same binding-hazard
    reason as on :func:`query_findings`. The reviewer registry is resolved ONCE
    for the whole query and both slices narrow against that one resolution, so
    the single ``preference_admissibility_basis`` the return carries
    (``recognized`` / ``presence_only``) describes both.

    Only Q-Gate records whose `resolution == 'pending'` are merged — resolved
    Q-Gate findings are never surfaced through this read. The per-plan slice keeps
    its own `resolution` filter semantics (the caller's `resolution` arg passes
    through to `query_findings`).

    The result is TOON-friendly and shape-compatible with `query_findings` plus
    provenance markers: `qgate_included: true`, `plan_count`, and `qgate_count`.
    """
    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    admissibility = _resolve_preference_admissibility(preference_admissible)

    plan_result = _query_findings(
        plan_id,
        finding_type=finding_type,
        resolution=resolution,
        promoted=promoted,
        file_pattern=file_pattern,
        author=author,
        kind=kind,
        bot_kind=bot_kind,
        any_checkout=any_checkout,
        admissibility=admissibility,
    )
    plan_findings = plan_result['findings']

    type_filter = {t.strip() for t in finding_type.split(',')} if finding_type else None

    qgate_findings: list[dict[str, Any]] = []
    qgate_total = 0
    for phase in QGATE_PHASES:
        records = query_qgate_findings(
            plan_id, phase, resolution='pending', any_checkout=any_checkout
        )['findings']
        qgate_total += len(records)
        qgate_findings.extend(
            _narrow_to_preference_admissible(
                _filter_records(
                    records,
                    exact_filters={'author': author, 'kind': kind, 'bot_kind': bot_kind},
                    type_filter=type_filter,
                    file_pattern=file_pattern,
                ),
                admissibility,
            )
        )

    merged = plan_findings + qgate_findings

    # `total_count` spans the full universe of both slices symmetrically: the
    # entire per-plan store (`plan_result['total_count']`, pre-narrowing) plus
    # every pending Q-Gate record across phases (`qgate_total`, before the
    # type/file_pattern narrowing). `filtered_count` is the post-narrowing union.
    # Counting only the filtered Q-Gate slice into `total_count` would mix the
    # plan slice's unfiltered total with the Q-Gate slice's filtered count.
    return {
        'status': 'success',
        'plan_id': plan_id,
        'qgate_included': True,
        'plan_count': len(plan_findings),
        'qgate_count': len(qgate_findings),
        'total_count': plan_result['total_count'] + qgate_total,
        'filtered_count': len(merged),
        'findings': merged,
        'file_paths': list({r.get('file_path') for r in merged if r.get('file_path')}),
        **_preference_basis_fields(admissibility),
        **store_state_fields(store),
    }


def get_finding(plan_id: str, hash_id: str, any_checkout: bool = False) -> dict[str, Any]:
    """Get a single finding by hash_id, scanning the plan-findings file set.

    A hash that is absent from that file set but present in a sibling store
    (``qgate-*.jsonl`` / ``assessments.jsonl``) returns
    ``error: finding_in_other_store`` naming the store and the verb that owns it,
    rather than a bare not-found for a record that demonstrably exists.
    """
    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    for path in _list_finding_files_in(store):
        for record in read_jsonl(path):
            if record.get('hash_id') == hash_id:
                return {'status': 'success', **record, **store_state_fields(store)}
    return _not_found(plan_id, store, hash_id, 'Finding')


def resolve_finding(
    plan_id: str,
    hash_id: str,
    resolution: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Resolve a finding (locates the per-type file by hash_id).

    Relational integrity backstop: a ``resolution_detail``
    is only ever written keyed to a ``hash_id`` that resolves to an existing parent
    record. The parent's existence is asserted BEFORE any write, so a mis-keyed detail
    can never be attached to — or silently create — a phantom record. The subsequent
    :func:`_update_in_finding_files` pass matches solely on ``hash_id`` within the
    plan-findings file set, so the resolution fields and the detail land on the same
    first-class record together — and, because that file set is the SAME one the
    ``get_finding`` precondition scans, the write can no longer reach a record the
    precondition never checked.

    The check-then-act window across the two file reads is unchanged in width by
    this narrowing: it neither opens nor closes it. See the TOCTOU mitigation menu
    in ``ref-code-quality/standards/code-organization.md``.
    """
    if resolution not in RESOLUTIONS:
        return {'status': 'error', 'message': f'Invalid resolution: {resolution}. Must be one of {RESOLUTIONS}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    parent = get_finding(plan_id, hash_id)
    if not parent or parent.get('status') != 'success':
        return _not_found(plan_id, store, hash_id, 'Finding')

    updates: dict[str, Any] = {'resolution': resolution}
    if detail:
        updates['resolution_detail'] = detail

    # Invalidate a stale provider-transmission marker. A finding that was already
    # transmitted to its provider carries ``responded`` (see
    # ``mark_finding_responded``). Re-resolving it to a DIFFERENT disposition — a new
    # resolution, or a new reply body — means the reviewer was told the OLD decision,
    # so the new one must be transmittable again; clear the marker in the same write
    # that changes the disposition. An unchanged re-resolve (an idempotent no-op)
    # leaves the marker intact, so an already-sent reply is not needlessly re-sent.
    # This is what makes the RESPOND idempotency a per-(finding, disposition) key
    # rather than a permanent suppression, and it holds for every provider that reads
    # the marker (GitHub, Sonar) without either provider re-implementing it.
    if parent.get('responded'):
        resolution_changed = parent.get('resolution') != resolution
        detail_changed = bool(detail) and parent.get('resolution_detail') != detail
        if resolution_changed or detail_changed:
            updates['responded'] = False
            updates['responded_at'] = None

    if _update_in_finding_files(store, hash_id, updates):
        return {
            'status': 'success',
            'hash_id': hash_id,
            'resolution': resolution,
            **store_state_fields(store),
        }
    return _not_found(plan_id, store, hash_id, 'Finding')


def resolve_findings_by_type(
    plan_id: str,
    finding_types: tuple[str, ...] | list[str],
    to_resolution: str,
    detail: str | None = None,
    from_resolution: str = 'pending',
) -> dict[str, Any]:
    """Bulk-resolve all findings of the given types in a single call.

    Selects every plan-scoped finding whose ``type`` is in ``finding_types`` AND
    whose current ``resolution`` equals ``from_resolution``, then resolves each to
    ``to_resolution`` (optionally stamping ``resolution_detail`` with ``detail``).
    This is the typed bulk counterpart of the hash-id-scoped ``resolve_finding``.

    Returns ``{'status': 'success', 'resolved_count': N, 'hash_ids': [...]}`` on
    success, or the canonical ``{'status': 'error', 'message': ...}`` shape when
    ``to_resolution`` is not a valid resolution value.
    """
    if to_resolution not in RESOLUTIONS:
        return {'status': 'error', 'message': f'Invalid resolution: {to_resolution}. Must be one of {RESOLUTIONS}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    type_set = set(finding_types)
    records = query_findings(plan_id)['findings']
    matched = [
        r for r in records
        if r.get('type') in type_set and r.get('resolution') == from_resolution
    ]

    base_updates: dict[str, Any] = {'resolution': to_resolution}
    if detail:
        base_updates['resolution_detail'] = detail
    # A bulk resolve re-decides dispositions just as ``resolve_finding`` does, so it
    # must invalidate a stale provider-transmission marker on the SAME terms — the
    # ``(finding, disposition)`` idempotency key must hold no matter which resolve
    # entry point re-decided the finding. ``resolution`` changes uniformly (matched
    # records all carry ``from_resolution``); the reply body is compared per record.
    resolution_changed = to_resolution != from_resolution
    resolved_hash_ids: list[str] = []
    for record in matched:
        hash_id = record['hash_id']
        updates = dict(base_updates)
        if record.get('responded'):
            detail_changed = bool(detail) and record.get('resolution_detail') != detail
            if resolution_changed or detail_changed:
                updates['responded'] = False
                updates['responded_at'] = None
        path = _store_findings_path(store, record['type'])
        if update_jsonl(path, hash_id, updates):
            resolved_hash_ids.append(hash_id)

    return {
        'status': 'success',
        'resolved_count': len(resolved_hash_ids),
        'hash_ids': resolved_hash_ids,
        **store_state_fields(store),
    }


def promote_finding(
    plan_id: str,
    hash_id: str,
    promoted_to: str,
) -> dict[str, Any]:
    """Mark a finding as promoted (locates the per-type file by hash_id).

    Scoped to the PLAN-FINDINGS file set. It previously wrote through a
    directory-wide glob, so a Q-Gate or assessment hash was silently stamped with
    ``promoted`` / ``promoted_to`` — fields those record kinds do not carry — and
    reported ``status: success``. Such a hash is now identified and refused with
    ``error: finding_in_other_store``, leaving the target record byte-identical.
    """
    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    updates = {'promoted': True, 'promoted_to': promoted_to}

    if _update_in_finding_files(store, hash_id, updates):
        return {
            'status': 'success',
            'hash_id': hash_id,
            'promoted_to': promoted_to,
            **store_state_fields(store),
        }
    return _not_found(plan_id, store, hash_id, 'Finding')


def mark_finding_responded(
    plan_id: str,
    hash_id: str,
) -> dict[str, Any]:
    """Stamp a finding as having had its provider response transmitted.

    Idempotency marker for the RESPOND verb across every provider's
    ``post_responses`` (``sonar.py`` server-side dismissal, ``github_pr.py`` PR
    thread-reply / batched comment): after a successful transmission, record
    ``responded=True`` plus a ``responded_at`` UTC timestamp keyed to the finding's
    ``hash_id``. A subsequent ``post_responses`` pass observes the marker and skips
    the finding instead of re-transmitting the same disposition. The marker is
    cleared by ``resolve_finding`` when the finding's disposition changes, so a
    re-decided disposition is transmittable again — the guard is a per-``(finding,
    disposition)`` key, not a permanent suppression. Locates the per-type file by
    ``hash_id`` within the PLAN-FINDINGS file set, so a Q-Gate or assessment hash
    is identified and refused rather than stamped with a marker its record kind
    does not carry.
    """
    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    updates: dict[str, Any] = {'responded': True, 'responded_at': timestamp()}

    if _update_in_finding_files(store, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, **store_state_fields(store)}
    return _not_found(plan_id, store, hash_id, 'Finding')


# --- Q-Gate Findings ---


def _find_by_title_and_discriminator(
    path: Path,
    title: str,
    discriminator: str,
) -> dict[str, Any] | None:
    """Find a Q-Gate record matching BOTH title AND content discriminator.

    The dedup key is the (title, discriminator) pair — never the title alone — so a
    same-class-different-subject finding (same bare-``defect_class`` title, different
    content) is treated as a distinct finding and can never reopen an unrelated
    resolved record.
    """
    for record in read_jsonl(path):
        if record.get('title') == title and record.get('content_discriminator') == discriminator:
            return record
    return None


def add_qgate_finding(
    plan_id: str,
    phase: str,
    source: str,
    finding_type: str,
    title: str,
    detail: str,
    file_path: str | None = None,
    component: str | None = None,
    severity: str | None = None,
    iteration: int | None = None,
    rule: str | None = None,
    raw_input: dict[str, Any] | None = None,
    raw_input_max_bytes: int = DEFAULT_RAW_INPUT_MAX_BYTES,
) -> dict[str, Any]:
    """Add a Q-Gate finding for a specific phase.

    Dedup folds a content discriminator (a stable hash of ``detail`` + ``file_path`` +
    ``rule``) into the key so a bare-``defect_class`` title collision alone can never
    reopen an unrelated resolved finding, while an intended same-defect merge across
    iterations (same title AND same discriminator) still collapses. Untrusted free-text
    supplied via ``raw_input`` is quarantined under ``raw_input.{field}`` with a per-field
    byte cap.

    Returns a dict whose ``status`` is one of ``success``, ``deduplicated``,
    ``reopened`` or ``error``. A ``status`` outside :data:`QGATE_PERSIST_OK` (i.e.
    ``error``) means **the record is not in the store** and MUST NOT be conflated
    with the two benign no-op outcomes ``deduplicated`` and ``reopened``, both of
    which do leave the finding present. Callers test membership in
    :data:`QGATE_PERSIST_OK`, never ``status == 'success'``.

    REFUSES against an absent plan directory, for the same reason
    :func:`add_finding` does: the terminal ``append_jsonl`` would mkdir the whole
    chain and manufacture a phantom store. The refusal is an ``error``, which
    :data:`QGATE_PERSIST_OK` already excludes, so every caller that tests
    membership in that set treats it as not-in-store with no change at the call
    site.
    """
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    if source not in QGATE_SOURCES:
        return {'status': 'error', 'message': f'Invalid Q-Gate source: {source}. Must be one of {QGATE_SOURCES}'}

    if finding_type not in FINDING_TYPES:
        return {'status': 'error', 'message': f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}'}

    if severity and severity not in SEVERITIES:
        return {'status': 'error', 'message': f'Invalid severity: {severity}. Must be one of {SEVERITIES}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    # Semantic dedup by (title, content discriminator) within phase.
    discriminator = _content_discriminator(detail, file_path, rule)
    qgate_path = _store_qgate_path(store, phase)
    existing = _find_by_title_and_discriminator(qgate_path, title, discriminator)
    if existing:
        if existing['resolution'] == 'pending':
            return {
                'status': 'deduplicated',
                'hash_id': existing['hash_id'],
                'phase': phase,
                **store_state_fields(store),
            }
        else:
            # Same title AND same content — a genuine re-detection of the resolved
            # finding — reopen. A same-title-different-content finding never lands
            # here (it fails the discriminator match above) and is filed fresh.
            reopen_updates: dict[str, Any] = {
                'resolution': 'pending',
                'resolution_detail': None,
                'resolution_timestamp': None,
            }
            if iteration is not None:
                reopen_updates['iteration'] = iteration
            update_jsonl(qgate_path, existing['hash_id'], reopen_updates)
            return {
                'status': 'reopened',
                'hash_id': existing['hash_id'],
                'phase': phase,
                **store_state_fields(store),
            }

    hash_id = generate_hash_id()
    record: dict[str, Any] = {
        'hash_id': hash_id,
        'timestamp': timestamp(),
        'phase': phase,
        'source': source,
        'type': finding_type,
        'title': title,
        'detail': detail,
        'content_discriminator': discriminator,
        'resolution': 'pending',
        'resolution_detail': None,
        'resolution_timestamp': None,
    }

    if iteration is not None:
        record['iteration'] = iteration
    if file_path:
        record['file_path'] = file_path
    if component:
        record['component'] = component
    if severity:
        record['severity'] = severity
    if rule:
        record['rule'] = rule

    quarantined = _quarantine_raw_input(raw_input, raw_input_max_bytes)
    if quarantined:
        record['raw_input'] = quarantined

    append_jsonl(qgate_path, record)

    return {'status': 'success', 'hash_id': hash_id, 'phase': phase, **store_state_fields(store)}


def add_qgate_finding_checked(
    plan_id: str,
    phase: str,
    source: str,
    finding_type: str,
    title: str,
    detail: str,
    **kwargs: Any,
) -> tuple[str | None, dict[str, str] | None]:
    """Call :func:`add_qgate_finding` and partition its outcome for a caller whose
    finding IS the primary output — one that must never fold a rejected persist
    into a benign-looking zero.

    Every ``fetch_findings`` producer (``github_pr``, ``gitlab_pr``, ``sonar``)
    files a producer-mismatch finding through this exact shape: call, then check
    membership in :data:`QGATE_PERSIST_OK`, then build a ``{title, detail,
    message}`` descriptor on rejection. Centralizing that check here removes the
    duplicated branch from each of the three callers.

    Returns ``(hash_id, None)`` when the finding reached the store, and
    ``(None, failure)`` when the primitive REJECTED it, where ``failure`` is
    ``{'title', 'detail', 'message'}`` carrying the finding's own content plus
    the primitive's rejection message.

    Carries no store guard of its own: it delegates to :func:`add_qgate_finding`,
    whose absent-plan-directory refusal is an ``error`` — already outside
    :data:`QGATE_PERSIST_OK` — so the refusal arrives here through the existing
    rejection path with the store's own message attached.
    """
    result = add_qgate_finding(
        plan_id, phase, source, finding_type, title, detail, **kwargs
    )
    if result.get('status') not in QGATE_PERSIST_OK:
        return None, {'title': title, 'detail': detail, 'message': str(result.get('message', ''))}
    return result.get('hash_id'), None


def query_qgate_findings(
    plan_id: str,
    phase: str,
    resolution: str | None = None,
    source: str | None = None,
    iteration: int | None = None,
    any_checkout: bool = False,
) -> dict[str, Any]:
    """Query Q-Gate findings for a specific phase.

    States which store the counts were computed from; an absent plan directory
    is refused rather than reported as ``total_count: 0``.
    """
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_qgate_path(store, phase)
    records = read_jsonl(path)

    filtered = _filter_records(
        records,
        exact_filters={'resolution': resolution, 'source': source, 'iteration': iteration},
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'total_count': len(records),
        'filtered_count': len(filtered),
        'findings': filtered,
        **store_state_fields(store),
    }


def resolve_qgate_finding(
    plan_id: str,
    phase: str,
    hash_id: str,
    resolution: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Resolve a Q-Gate finding."""
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    if resolution not in RESOLUTIONS:
        return {'status': 'error', 'message': f'Invalid resolution: {resolution}. Must be one of {RESOLUTIONS}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_qgate_path(store, phase)
    updates: dict[str, Any] = {
        'resolution': resolution,
        'resolution_timestamp': timestamp(),
    }
    if detail:
        updates['resolution_detail'] = detail

    if update_jsonl(path, hash_id, updates):
        return {
            'status': 'success',
            'hash_id': hash_id,
            'phase': phase,
            'resolution': resolution,
            **store_state_fields(store),
        }
    return {
        'status': 'error',
        'message': f'Q-Gate finding not found: {hash_id}',
        **store_state_fields(store),
    }


def resolve_qgate_findings_by_evidence(
    plan_id: str,
    phase: str,
    changed_paths: list[str],
    evidence_sha: str | None = None,
) -> dict[str, Any]:
    """Resolve pending Q-Gate findings whose file a landed fix actually touched.

    Evidence-gated self-review loop-back resolution (D3). The self-review step
    files a Q-Gate finding per structural defect but never resolves its own
    findings, so a plan whose fixes genuinely landed could still merge with the
    finding RECORDS stuck at ``pending``. This transitions a pending Q-Gate
    finding to ``fixed`` ONLY when its ``file_path`` is in ``changed_paths`` — the
    set of files a landed fix (a commit that advanced HEAD) actually touched.

    A finding whose ``file_path`` is NOT in ``changed_paths`` — or that carries no
    ``file_path`` at all — is LEFT ``pending``. This is the important direction: a
    finding marked ``fixed`` without a landed change touching its file is strictly
    worse than one left pending, so the unevidenced case is never auto-resolved.

    ``changed_paths`` is the evidence the CALLER computes and passes in (e.g.
    ``git diff --name-only {prior_anchor}..HEAD`` — the loop-back fix's own edits).
    A premature resolution — the fix touched the file but did not remove the defect
    — is self-correcting: the next self-review round re-surfaces the defect and
    :func:`add_qgate_finding` REOPENS the resolved record back to ``pending``.

    Returns ``{status, plan_id, phase, resolved[], left_pending[]}`` where each
    list carries ``{hash_id, file_path}`` entries, so the caller can report exactly
    which findings its fix evidenced and which it left for a later round.
    """
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    changed = {p for p in changed_paths if p}
    path = _store_qgate_path(store, phase)
    records = read_jsonl(path)
    detail_sha = evidence_sha or 'HEAD'

    resolved: list[dict[str, str]] = []
    left_pending: list[dict[str, str]] = []
    for record in records:
        if record.get('resolution') != 'pending':
            continue
        file_path = record.get('file_path')
        entry = {'hash_id': str(record.get('hash_id', '')), 'file_path': str(file_path or '')}
        if file_path and file_path in changed:
            updated = update_jsonl(
                path,
                record['hash_id'],
                {
                    'resolution': 'fixed',
                    'resolution_timestamp': timestamp(),
                    'resolution_detail': f'evidenced by landed change {detail_sha} touching {file_path}',
                },
            )
            # Only claim ``fixed`` when the write actually took. A failed
            # ``update_jsonl`` (the record vanished between the read above and this
            # write) leaves the finding ``pending`` — reporting it in ``resolved``
            # would tell the caller a resolution the store never recorded, the
            # fail-open this evidence gate exists to prevent. Report it as still
            # pending instead.
            (resolved if updated else left_pending).append(entry)
        else:
            left_pending.append(entry)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'resolved': resolved,
        'left_pending': left_pending,
        **store_state_fields(store),
    }


def clear_qgate_findings(
    plan_id: str,
    phase: str,
) -> dict[str, Any]:
    """Clear all Q-Gate findings for a specific phase.

    A ``cleared: 0`` is only meaningful for a store that was reached, so an
    absent plan directory is refused rather than reported as a clean zero.
    """
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_qgate_path(store, phase)
    if not path.exists():
        return {'status': 'success', 'phase': phase, 'cleared': 0, **store_state_fields(store)}

    records = read_jsonl(path)
    cleared = len(records)
    path.unlink()

    return {'status': 'success', 'phase': phase, 'cleared': cleared, **store_state_fields(store)}


# --- Assessment Path Helper ---


def get_assessments_path(plan_id: str) -> Path:
    """Returns .plan/local/plans/{plan_id}/artifacts/findings/assessments.jsonl"""
    return get_findings_dir(plan_id) / 'assessments.jsonl'


# --- Assessment Operations ---


def add_assessment(
    plan_id: str,
    file_path: str,
    certainty: str,
    confidence: int,
    agent: str | None = None,
    detail: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    """Add an assessment record.

    REFUSES against an absent plan directory, on the same guard as the other two
    ``add_`` surfaces: ``append_jsonl`` would otherwise mkdir the whole chain for
    a plan that exists in no checkout.
    """
    if certainty not in CERTAINTY_VALUES:
        return {'status': 'error', 'message': f'Invalid certainty: {certainty}. Must be one of {CERTAINTY_VALUES}'}

    if not 0 <= confidence <= 100:
        return {'status': 'error', 'message': f'Invalid confidence: {confidence}. Must be 0-100'}

    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    hash_id = generate_hash_id()
    record = {
        'hash_id': hash_id,
        'timestamp': timestamp(),
        'file_path': file_path,
        'certainty': certainty,
        'confidence': confidence,
    }
    if agent:
        record['agent'] = agent
    if detail:
        record['detail'] = detail
    if evidence:
        record['evidence'] = evidence

    append_jsonl(_store_assessments_path(store), record)

    return {
        'status': 'success',
        'hash_id': hash_id,
        'file_path': file_path,
        **store_state_fields(store),
    }


def query_assessments(
    plan_id: str,
    certainty: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    file_pattern: str | None = None,
    any_checkout: bool = False,
) -> dict[str, Any]:
    """Query assessments with filters.

    States which store the counts were computed from; an absent plan directory
    is refused rather than reported as ``total_count: 0``.
    """
    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_assessments_path(store)
    records = read_jsonl(path)

    filtered = _filter_records(
        records,
        exact_filters={'certainty': certainty},
        file_pattern=file_pattern,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': len(records),
        'filtered_count': len(filtered),
        'assessments': filtered,
        'file_paths': list({r.get('file_path') for r in filtered}),
        **store_state_fields(store),
    }


def get_assessment(plan_id: str, hash_id: str, any_checkout: bool = False) -> dict[str, Any]:
    """Get a single assessment by hash_id."""
    store = resolve_findings_store(plan_id, any_checkout=any_checkout)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_assessments_path(store)
    for record in read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record, **store_state_fields(store)}
    return {
        'status': 'error',
        'message': f'Assessment not found: {hash_id}',
        **store_state_fields(store),
    }


def clear_assessments(
    plan_id: str,
    agent: str | None = None,
) -> dict[str, Any]:
    """Clear assessment records, optionally filtered by agent.

    A ``cleared: 0`` is only meaningful for a store that was reached, so an
    absent plan directory is refused rather than reported as a clean zero.
    """
    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    path = _store_assessments_path(store)
    if not path.exists():
        return {'status': 'success', 'cleared': 0, **store_state_fields(store)}

    records = read_jsonl(path)
    original_count = len(records)

    if agent:
        remaining = [r for r in records if r.get('agent') != agent]
        cleared = original_count - len(remaining)
        ensure_parent_dir(path)
        with path.open('w', encoding='utf-8') as f:
            for record in remaining:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    else:
        cleared = original_count
        path.unlink()

    return {'status': 'success', 'cleared': cleared, **store_state_fields(store)}
