#!/usr/bin/env python3
"""
Finding, Q-Gate, and assessment storage for plan-level artifacts.

Provides JSONL-based storage for:
- Plan-scoped findings (long-lived, promotable)
- Phase-scoped Q-Gate findings (per-phase, not promotable)
- Plan-scoped assessments (component evaluations with certainty/confidence)

Findings and Q-Gate share the same type taxonomy, resolution model, and severity values.
Assessments use a separate certainty/confidence model.

Storage:
- Plan findings: .plan/plans/{plan_id}/artifacts/findings.jsonl
- Q-Gate findings: .plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl
- Assessments: .plan/plans/{plan_id}/artifacts/assessments.jsonl

Stdlib-only - no external dependencies (except shared modules via PYTHONPATH).
"""

import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from constants import (  # type: ignore[import-not-found]
    ARCHITECTURE_TYPES,
    FINDING_SEVERITIES,
    FINDING_TYPES,
    LESSON_TYPES,
    QGATE_PHASES,
    QGATE_SOURCES,
    VALID_CERTAINTIES,
    VALID_RESOLUTIONS,
)
from input_validation import validate_plan_id  # type: ignore[import-not-found]
from jsonl_store import (  # type: ignore[import-not-found]
    append_jsonl,
    ensure_parent_dir,
    find_by_title,
    generate_hash_id,
    get_artifact_path,
    read_jsonl,
    timestamp,
    update_jsonl,
)


# --- Backward-compatible aliases (imported from constants) ---
# These names are re-exported for manage-findings.py and tests
SEVERITIES = FINDING_SEVERITIES
RESOLUTIONS = VALID_RESOLUTIONS
CERTAINTY_VALUES = VALID_CERTAINTIES


# --- Path Helpers ---


def get_findings_path(plan_id: str) -> 'Path':
    """Returns .plan/plans/{plan_id}/artifacts/findings.jsonl"""
    validate_plan_id(plan_id)
    return get_artifact_path(plan_id, 'findings.jsonl')


def get_qgate_path(plan_id: str, phase: str) -> 'Path':
    """Returns .plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl"""
    validate_plan_id(plan_id)
    if phase not in QGATE_PHASES:
        raise ValueError(f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}')
    return get_artifact_path(plan_id, f'qgate-{phase}.jsonl')


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
) -> dict[str, Any]:
    """Add a finding record."""
    if finding_type not in FINDING_TYPES:
        return {'status': 'error', 'message': f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}'}

    if severity and severity not in SEVERITIES:
        return {'status': 'error', 'message': f'Invalid severity: {severity}. Must be one of {SEVERITIES}'}

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

    append_jsonl(get_findings_path(plan_id), record)

    return {'status': 'success', 'hash_id': hash_id, 'type': finding_type}


def query_findings(
    plan_id: str,
    finding_type: str | None = None,
    resolution: str | None = None,
    promoted: bool | None = None,
    file_pattern: str | None = None,
) -> dict[str, Any]:
    """Query findings with filters."""
    path = get_findings_path(plan_id)
    records = read_jsonl(path)

    type_filter = {t.strip() for t in finding_type.split(',')} if finding_type else None
    filtered = _filter_records(
        records,
        exact_filters={'resolution': resolution},
        type_filter=type_filter,
        file_pattern=file_pattern,
        promoted=promoted,
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': len(records),
        'filtered_count': len(filtered),
        'findings': filtered,
        'file_paths': list({r.get('file_path') for r in filtered if r.get('file_path')}),
    }


def get_finding(plan_id: str, hash_id: str) -> dict[str, Any]:
    """Get a single finding by hash_id."""
    path = get_findings_path(plan_id)
    for record in read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record}
    return {'status': 'error', 'message': f'Finding not found: {hash_id}'}


def resolve_finding(
    plan_id: str,
    hash_id: str,
    resolution: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Resolve a finding."""
    if resolution not in RESOLUTIONS:
        return {'status': 'error', 'message': f'Invalid resolution: {resolution}. Must be one of {RESOLUTIONS}'}

    path = get_findings_path(plan_id)
    updates: dict[str, Any] = {'resolution': resolution}
    if detail:
        updates['resolution_detail'] = detail

    if update_jsonl(path, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, 'resolution': resolution}
    return {'status': 'error', 'message': f'Finding not found: {hash_id}'}


def promote_finding(
    plan_id: str,
    hash_id: str,
    promoted_to: str,
) -> dict[str, Any]:
    """Mark a finding as promoted."""
    path = get_findings_path(plan_id)
    updates = {'promoted': True, 'promoted_to': promoted_to}

    if update_jsonl(path, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, 'promoted_to': promoted_to}
    return {'status': 'error', 'message': f'Finding not found: {hash_id}'}


# --- Q-Gate Findings ---


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
) -> dict[str, Any]:
    """Add a Q-Gate finding for a specific phase."""
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    if source not in QGATE_SOURCES:
        return {'status': 'error', 'message': f'Invalid Q-Gate source: {source}. Must be one of {QGATE_SOURCES}'}

    if finding_type not in FINDING_TYPES:
        return {'status': 'error', 'message': f'Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}'}

    if severity and severity not in SEVERITIES:
        return {'status': 'error', 'message': f'Invalid severity: {severity}. Must be one of {SEVERITIES}'}

    # Semantic dedup by title within phase
    qgate_path = get_qgate_path(plan_id, phase)
    existing = find_by_title(qgate_path, title)
    if existing:
        if existing['resolution'] == 'pending':
            return {'status': 'deduplicated', 'hash_id': existing['hash_id'], 'phase': phase}
        else:
            # Resolved but re-detected — reopen
            reopen_updates: dict[str, Any] = {
                'resolution': 'pending',
                'resolution_detail': None,
                'resolution_timestamp': None,
            }
            if iteration is not None:
                reopen_updates['iteration'] = iteration
            update_jsonl(qgate_path, existing['hash_id'], reopen_updates)
            return {'status': 'reopened', 'hash_id': existing['hash_id'], 'phase': phase}

    hash_id = generate_hash_id()
    record: dict[str, Any] = {
        'hash_id': hash_id,
        'timestamp': timestamp(),
        'phase': phase,
        'source': source,
        'type': finding_type,
        'title': title,
        'detail': detail,
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

    append_jsonl(qgate_path, record)

    return {'status': 'success', 'hash_id': hash_id, 'phase': phase}


def query_qgate_findings(
    plan_id: str,
    phase: str,
    resolution: str | None = None,
    source: str | None = None,
    iteration: int | None = None,
) -> dict[str, Any]:
    """Query Q-Gate findings for a specific phase."""
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    path = get_qgate_path(plan_id, phase)
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

    path = get_qgate_path(plan_id, phase)
    updates: dict[str, Any] = {
        'resolution': resolution,
        'resolution_timestamp': timestamp(),
    }
    if detail:
        updates['resolution_detail'] = detail

    if update_jsonl(path, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, 'phase': phase, 'resolution': resolution}
    return {'status': 'error', 'message': f'Q-Gate finding not found: {hash_id}'}


def clear_qgate_findings(
    plan_id: str,
    phase: str,
) -> dict[str, Any]:
    """Clear all Q-Gate findings for a specific phase."""
    if phase not in QGATE_PHASES:
        return {'status': 'error', 'message': f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}'}

    path = get_qgate_path(plan_id, phase)
    if not path.exists():
        return {'status': 'success', 'phase': phase, 'cleared': 0}

    records = read_jsonl(path)
    cleared = len(records)
    path.unlink()

    return {'status': 'success', 'phase': phase, 'cleared': cleared}


# --- Assessment Path Helper ---


def get_assessments_path(plan_id: str) -> 'Path':
    """Returns .plan/plans/{plan_id}/artifacts/assessments.jsonl"""
    validate_plan_id(plan_id)
    return get_artifact_path(plan_id, 'assessments.jsonl')


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
    """Add an assessment record."""
    if certainty not in CERTAINTY_VALUES:
        return {'status': 'error', 'message': f'Invalid certainty: {certainty}. Must be one of {CERTAINTY_VALUES}'}

    if not 0 <= confidence <= 100:
        return {'status': 'error', 'message': f'Invalid confidence: {confidence}. Must be 0-100'}

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

    append_jsonl(get_assessments_path(plan_id), record)

    return {'status': 'success', 'hash_id': hash_id, 'file_path': file_path}


def query_assessments(
    plan_id: str,
    certainty: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    file_pattern: str | None = None,
) -> dict[str, Any]:
    """Query assessments with filters."""
    path = get_assessments_path(plan_id)
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
    }


def get_assessment(plan_id: str, hash_id: str) -> dict[str, Any]:
    """Get a single assessment by hash_id."""
    path = get_assessments_path(plan_id)
    for record in read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record}
    return {'status': 'error', 'message': f'Assessment not found: {hash_id}'}


def clear_assessments(
    plan_id: str,
    agent: str | None = None,
) -> dict[str, Any]:
    """Clear assessment records, optionally filtered by agent."""
    path = get_assessments_path(plan_id)
    if not path.exists():
        return {'status': 'success', 'cleared': 0}

    records = read_jsonl(path)
    original_count = len(records)

    if agent:
        remaining = [r for r in records if r.get('agent') != agent]
        cleared = original_count - len(remaining)
        ensure_parent_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            for record in remaining:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    else:
        cleared = original_count
        path.unlink()

    return {'status': 'success', 'cleared': cleared}
