#!/usr/bin/env python3
"""
Finding and Q-Gate storage for plan-level artifacts.

Provides JSONL-based storage for:
- Plan-scoped findings (long-lived, promotable)
- Phase-scoped Q-Gate findings (per-phase, not promotable)

Both share the same type taxonomy, resolution model, and severity values.

Storage:
- Plan findings: .plan/plans/{plan_id}/artifacts/findings.jsonl
- Q-Gate findings: .plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl

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
_toon_parser_path = (
    Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
)
if _toon_parser_path.exists():
    sys.path.insert(0, str(_toon_parser_path))
    from toon_parser import serialize_toon
else:
    # Fallback for standalone execution without executor PYTHONPATH setup.
    # Intentionally duplicates _serialize_value quoting logic from toon_parser.py
    # to ensure correct round-trip behavior even when the main parser is unreachable.
    def serialize_toon(data: dict[str, Any], indent: int = 0) -> str:
        import re as _re

        def _quote_if_ambiguous(val: str) -> str:
            if val in ('true', 'false', 'null', ''):
                return f'"{val}"'
            if _re.match(r'^-?\d+$', val) or _re.match(r'^-?\d+\.\d+$', val) or _re.match(r'^\d+%$', val):
                return f'"{val}"'
            return val

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
            elif isinstance(value, str):
                lines.append(f'{prefix}{key}: {_quote_if_ambiguous(value)}')
            else:
                lines.append(f'{prefix}{key}: {value}')
        return '\n'.join(lines)


# --- Shared Constants ---

FINDING_TYPES = [
    # Lesson-like (knowledge)
    'bug',
    'improvement',
    'anti-pattern',
    'triage',
    'tip',
    'insight',
    'best-practice',
    # Bug-like (issues)
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'pr-comment',
]

RESOLUTIONS = ['pending', 'fixed', 'suppressed', 'accepted', 'taken_into_account']

SEVERITIES = ['error', 'warning', 'info']

# Q-Gate phases (per-phase findings files)
QGATE_PHASES = ['2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']

# Valid Q-Gate finding sources
QGATE_SOURCES = ['qgate', 'user_review']

# Types that default to manage-lessons promotion
LESSON_TYPES = {'bug', 'improvement', 'anti-pattern', 'triage'}

# Types that default to architecture promotion
ARCHITECTURE_TYPES = {'tip', 'insight', 'best-practice'}


# --- JSONL Infrastructure ---


def get_plan_root() -> Path:
    """Get the .plan directory root."""
    import os

    base_dir = os.environ.get('PLAN_BASE_DIR')
    if base_dir:
        return Path(base_dir)
    return Path.cwd() / '.plan'


def get_findings_path(plan_id: str) -> Path:
    """Returns .plan/plans/{plan_id}/artifacts/findings.jsonl"""
    return get_plan_root() / 'plans' / plan_id / 'artifacts' / 'findings.jsonl'


def get_qgate_path(plan_id: str, phase: str) -> Path:
    """Returns .plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl"""
    if phase not in QGATE_PHASES:
        raise ValueError(f'Invalid Q-Gate phase: {phase}. Must be one of {QGATE_PHASES}')
    return get_plan_root() / 'plans' / plan_id / 'artifacts' / f'qgate-{phase}.jsonl'


def generate_hash_id() -> str:
    """Generate a 6-char hex hash for artifact identification."""
    import secrets

    data = f'{datetime.now(UTC).isoformat()}{secrets.token_hex(8)}'
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


def _find_by_title(path: Path, title: str) -> dict[str, Any] | None:
    """Find a record by title in a JSONL file. Returns first match or None."""
    for record in _read_jsonl(path):
        if record.get('title') == title:
            return record
    return None


def _timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.now(UTC).isoformat()


def format_output(data: dict[str, Any]) -> str:
    """Format output as TOON."""
    result: str = serialize_toon(data)
    return result


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
        'timestamp': _timestamp(),
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

    _append_jsonl(get_findings_path(plan_id), record)

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
    records = _read_jsonl(path)
    total_count = len(records)

    # Parse type filter (supports comma-separated)
    type_filter = None
    if finding_type:
        type_filter = {t.strip() for t in finding_type.split(',')}

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
    path = get_findings_path(plan_id)
    for record in _read_jsonl(path):
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

    if _update_jsonl(path, hash_id, updates):
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

    if _update_jsonl(path, hash_id, updates):
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
    existing = _find_by_title(qgate_path, title)
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
            _update_jsonl(qgate_path, existing['hash_id'], reopen_updates)
            return {'status': 'reopened', 'hash_id': existing['hash_id'], 'phase': phase}

    hash_id = generate_hash_id()
    record: dict[str, Any] = {
        'hash_id': hash_id,
        'timestamp': _timestamp(),
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

    _append_jsonl(qgate_path, record)

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
    records = _read_jsonl(path)
    total_count = len(records)

    filtered = []
    for r in records:
        if resolution and r.get('resolution') != resolution:
            continue
        if source and r.get('source') != source:
            continue
        if iteration is not None and r.get('iteration') != iteration:
            continue
        filtered.append(r)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'total_count': total_count,
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
        'resolution_timestamp': _timestamp(),
    }
    if detail:
        updates['resolution_detail'] = detail

    if _update_jsonl(path, hash_id, updates):
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

    records = _read_jsonl(path)
    cleared = len(records)
    path.unlink()

    return {'status': 'success', 'phase': phase, 'cleared': cleared}
