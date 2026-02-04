#!/usr/bin/env python3
"""
Plan-level artifact storage for assessments and findings.

Provides JSONL-based storage for plan-scoped artifacts:
- assessments.jsonl: Component assessments from analysis agents
- findings.jsonl: Unified lessons + bugs (12 types, optionally promotable)

Stdlib-only - no external dependencies (except toon_parser for output).
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# Add toon_parser to path
_toon_parser_path = Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
if _toon_parser_path.exists():
    sys.path.insert(0, str(_toon_parser_path))
    from toon_parser import serialize_toon
else:
    # Fallback: simple dict-to-toon for basic cases
    def serialize_toon(data: dict[str, Any], indent: int = 0) -> str:
        lines = []
        prefix = '  ' * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{prefix}{key}:')
                lines.append(serialize_toon(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f'{prefix}{key}[{len(value)}]:')
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f'{prefix}  {",".join(str(v) for v in item.values())}')
                    else:
                        lines.append(f'{prefix}  - {item}')
            elif isinstance(value, bool):
                lines.append(f'{prefix}{key}: {"true" if value else "false"}')
            elif value is None:
                lines.append(f'{prefix}{key}: null')
            else:
                lines.append(f'{prefix}{key}: {value}')
        return '\n'.join(lines)


# Constants
ARTIFACT_TYPES = ['assessments', 'findings']

CERTAINTY_VALUES = ['CERTAIN_INCLUDE', 'CERTAIN_EXCLUDE', 'UNCERTAIN']

FINDING_TYPES = [
    # Lesson-like (knowledge)
    'bug', 'improvement', 'anti-pattern', 'triage',
    'tip', 'insight', 'best-practice',
    # Bug-like (issues)
    'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'pr-comment'
]

RESOLUTIONS = ['pending', 'fixed', 'suppressed', 'accepted']

SEVERITIES = ['error', 'warning', 'info']

# Types that default to manage-lessons promotion
LESSON_TYPES = {'bug', 'improvement', 'anti-pattern', 'triage'}

# Types that default to architecture promotion
ARCHITECTURE_TYPES = {'tip', 'insight', 'best-practice'}


def get_plan_root() -> Path:
    """Get the .plan directory root.

    Respects PLAN_BASE_DIR environment variable for testing.
    """
    import os
    base_dir = os.environ.get('PLAN_BASE_DIR')
    if base_dir:
        return Path(base_dir)
    return Path.cwd() / '.plan'


def get_artifacts_dir(plan_id: str) -> Path:
    """Returns .plan/plans/{plan_id}/artifacts/"""
    return get_plan_root() / 'plans' / plan_id / 'artifacts'


def get_artifact_path(plan_id: str, artifact_type: str) -> Path:
    """Returns .plan/plans/{plan_id}/artifacts/{type}.jsonl"""
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Invalid artifact type: {artifact_type}. Must be one of {ARTIFACT_TYPES}")
    return get_artifacts_dir(plan_id) / f'{artifact_type}.jsonl'


def generate_hash_id() -> str:
    """Generate a 6-char hex hash for artifact identification."""
    # Use timestamp + random bytes for uniqueness
    import secrets
    data = f"{datetime.now(UTC).isoformat()}{secrets.token_hex(8)}"
    return hashlib.sha256(data.encode()).hexdigest()[:6]


def _ensure_dir(path: Path) -> None:
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a JSON record to a JSONL file."""
    _ensure_dir(path)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _update_jsonl(path: Path, hash_id: str, updates: dict[str, Any]) -> bool:
    """Update a record in a JSONL file by hash_id."""
    if not path.exists():
        return False

    records = _read_jsonl(path)
    found = False
    for record in records:
        if record.get('hash_id') == hash_id:
            record.update(updates)
            found = True
            break

    if found:
        _ensure_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    return found


def _timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now(UTC).isoformat()


# --- Assessments ---

def clear_assessments(
    plan_id: str,
    agent: str | None = None,
) -> dict[str, Any]:
    """Clear assessment records, optionally filtered by agent.

    Args:
        plan_id: Plan identifier
        agent: If provided, only clear assessments from this agent.
               If None, clear ALL assessments.

    Returns:
        Dict with status, cleared count
    """
    path = get_artifact_path(plan_id, 'assessments')
    if not path.exists():
        return {'status': 'success', 'cleared': 0}

    records = _read_jsonl(path)
    original_count = len(records)

    if agent:
        remaining = [r for r in records if r.get('agent') != agent]
        cleared = original_count - len(remaining)
        _ensure_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            for record in remaining:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    else:
        cleared = original_count
        path.unlink()

    return {'status': 'success', 'cleared': cleared}


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

    Args:
        plan_id: Plan identifier
        file_path: Path to the assessed component
        certainty: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
        confidence: 0-100 percentage
        agent: Name of the analysis agent
        detail: Reasoning for the assessment
        evidence: Specific evidence supporting the assessment

    Returns:
        Dict with status, hash_id, file_path
    """
    if certainty not in CERTAINTY_VALUES:
        return {'status': 'error', 'message': f"Invalid certainty: {certainty}. Must be one of {CERTAINTY_VALUES}"}

    if not 0 <= confidence <= 100:
        return {'status': 'error', 'message': f"Invalid confidence: {confidence}. Must be 0-100"}

    hash_id = generate_hash_id()
    record = {
        'hash_id': hash_id,
        'timestamp': _timestamp(),
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

    _append_jsonl(get_artifact_path(plan_id, 'assessments'), record)

    return {'status': 'success', 'hash_id': hash_id, 'file_path': file_path}


def query_assessments(
    plan_id: str,
    certainty: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    file_pattern: str | None = None,
) -> dict[str, Any]:
    """Query assessments with filters.

    Args:
        plan_id: Plan identifier
        certainty: Filter by certainty value
        min_confidence: Minimum confidence (inclusive)
        max_confidence: Maximum confidence (inclusive)
        file_pattern: Glob pattern for file_path

    Returns:
        Dict with status, total_count, filtered_count, assessments list
    """
    path = get_artifact_path(plan_id, 'assessments')
    records = _read_jsonl(path)
    total_count = len(records)

    # Apply filters
    filtered = []
    for r in records:
        if certainty and r.get('certainty') != certainty:
            continue
        if min_confidence is not None and r.get('confidence', 0) < min_confidence:
            continue
        if max_confidence is not None and r.get('confidence', 100) > max_confidence:
            continue
        if file_pattern and not fnmatch(r.get('file_path', ''), file_pattern):
            continue
        filtered.append(r)

    # Build result
    result = {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': total_count,
        'filtered_count': len(filtered),
        'assessments': filtered,
        'file_paths': list({r.get('file_path') for r in filtered}),
    }

    return result


def get_assessment(plan_id: str, hash_id: str) -> dict[str, Any] | None:
    """Get a single assessment by hash_id."""
    path = get_artifact_path(plan_id, 'assessments')
    for record in _read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record}
    return {'status': 'error', 'message': f"Assessment not found: {hash_id}"}


# --- Findings ---

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
    """Add a finding record.

    Args:
        plan_id: Plan identifier
        finding_type: One of FINDING_TYPES
        title: Short title
        detail: Detailed description
        file_path: File path (for code-related findings)
        line: Line number (for code-related findings)
        component: Component reference (for knowledge findings)
        module: Module name (for architecture promotion)
        rule: Rule ID (for lint/sonar findings)
        severity: error, warning, or info

    Returns:
        Dict with status, hash_id, type
    """
    if finding_type not in FINDING_TYPES:
        return {'status': 'error', 'message': f"Invalid finding type: {finding_type}. Must be one of {FINDING_TYPES}"}

    if severity and severity not in SEVERITIES:
        return {'status': 'error', 'message': f"Invalid severity: {severity}. Must be one of {SEVERITIES}"}

    hash_id = generate_hash_id()
    record: dict[str, Any] = {
        'hash_id': hash_id,
        'timestamp': _timestamp(),
        'type': finding_type,
        'title': title,
        'detail': detail,
        'resolution': 'pending',
        'resolution_detail': None,
        'promoted': False,
        'promoted_to': None,
    }

    # Optional fields
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

    _append_jsonl(get_artifact_path(plan_id, 'findings'), record)

    return {'status': 'success', 'hash_id': hash_id, 'type': finding_type}


def query_findings(
    plan_id: str,
    finding_type: str | None = None,
    resolution: str | None = None,
    promoted: bool | None = None,
    file_pattern: str | None = None,
) -> dict[str, Any]:
    """Query findings with filters.

    Args:
        plan_id: Plan identifier
        finding_type: Filter by type (can be comma-separated for multiple)
        resolution: Filter by resolution status
        promoted: Filter by promoted status
        file_pattern: Glob pattern for file_path

    Returns:
        Dict with status, total_count, filtered_count, findings list
    """
    path = get_artifact_path(plan_id, 'findings')
    records = _read_jsonl(path)
    total_count = len(records)

    # Parse type filter (supports comma-separated)
    type_filter = None
    if finding_type:
        type_filter = {t.strip() for t in finding_type.split(',')}

    # Apply filters
    filtered = []
    for r in records:
        if type_filter and r.get('type') not in type_filter:
            continue
        if resolution and r.get('resolution') != resolution:
            continue
        if promoted is not None and r.get('promoted', False) != promoted:
            continue
        if file_pattern and not fnmatch(r.get('file_path', ''), file_pattern):
            continue
        filtered.append(r)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'total_count': total_count,
        'filtered_count': len(filtered),
        'findings': filtered,
        'file_paths': list({r.get('file_path') for r in filtered if r.get('file_path')}),
    }

    return result


def get_finding(plan_id: str, hash_id: str) -> dict[str, Any] | None:
    """Get a single finding by hash_id."""
    path = get_artifact_path(plan_id, 'findings')
    for record in _read_jsonl(path):
        if record.get('hash_id') == hash_id:
            return {'status': 'success', **record}
    return {'status': 'error', 'message': f"Finding not found: {hash_id}"}


def resolve_finding(
    plan_id: str,
    hash_id: str,
    resolution: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Resolve a finding (for bug-like types).

    Args:
        plan_id: Plan identifier
        hash_id: Finding hash ID
        resolution: fixed, suppressed, or accepted
        detail: Resolution detail/reasoning

    Returns:
        Dict with status
    """
    if resolution not in RESOLUTIONS:
        return {'status': 'error', 'message': f"Invalid resolution: {resolution}. Must be one of {RESOLUTIONS}"}

    path = get_artifact_path(plan_id, 'findings')
    updates: dict[str, Any] = {'resolution': resolution}
    if detail:
        updates['resolution_detail'] = detail

    if _update_jsonl(path, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, 'resolution': resolution}
    return {'status': 'error', 'message': f"Finding not found: {hash_id}"}


def promote_finding(
    plan_id: str,
    hash_id: str,
    promoted_to: str,
) -> dict[str, Any]:
    """Mark a finding as promoted.

    Args:
        plan_id: Plan identifier
        hash_id: Finding hash ID
        promoted_to: Target ID or "architecture"

    Returns:
        Dict with status
    """
    path = get_artifact_path(plan_id, 'findings')
    updates = {'promoted': True, 'promoted_to': promoted_to}

    if _update_jsonl(path, hash_id, updates):
        return {'status': 'success', 'hash_id': hash_id, 'promoted_to': promoted_to}
    return {'status': 'error', 'message': f"Finding not found: {hash_id}"}


# --- Output formatting ---

def format_output(data: dict[str, Any]) -> str:
    """Format output as TOON."""
    result: str = serialize_toon(data)
    return result


if __name__ == '__main__':
    # Quick self-test
    print('artifact_store.py - Plan-Level Artifact Storage')
    print('=' * 50)
    print(f'Artifact types: {ARTIFACT_TYPES}')
    print(f'Finding types: {FINDING_TYPES}')
    print(f'Certainty values: {CERTAINTY_VALUES}')
    print(f'Resolutions: {RESOLUTIONS}')
