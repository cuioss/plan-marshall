#!/usr/bin/env python3
"""
Shared JSONL storage infrastructure for plan-scoped artifacts.

Provides common JSONL operations (append, read, update, find), hash ID generation,
and timestamps used by manage-assessments and manage-findings.

Usage:
    from jsonl_store import (
        get_artifact_path,
        generate_hash_id,
        ensure_parent_dir,
        append_jsonl,
        read_jsonl,
        update_jsonl,
        find_by_title,
        timestamp,
    )
"""

import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from constants import HASH_ID_LENGTH  # type: ignore[import-not-found]
from file_ops import base_path  # type: ignore[import-not-found]


def get_artifact_path(plan_id: str, filename: str) -> Path:
    """Get path to a plan artifact file: .plan/plans/{plan_id}/artifacts/{filename}."""
    return base_path('plans', plan_id, 'artifacts', filename)


def generate_hash_id() -> str:
    """Generate a 6-char hex hash for artifact identification."""
    data = f'{datetime.now(UTC).isoformat()}{secrets.token_hex(8)}'
    return hashlib.sha256(data.encode()).hexdigest()[:HASH_ID_LENGTH]


def ensure_parent_dir(path: Path) -> None:
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a JSON record to a JSONL file."""
    ensure_parent_dir(path)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def update_jsonl(path: Path, hash_id: str, updates: dict[str, Any]) -> bool:
    """Update a record in a JSONL file by hash_id."""
    if not path.exists():
        return False

    records = read_jsonl(path)
    found = False
    for record in records:
        if record.get('hash_id') == hash_id:
            record.update(updates)
            found = True
            break

    if found:
        ensure_parent_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    return found


def find_by_title(path: Path, title: str) -> dict[str, Any] | None:
    """Find a record by title in a JSONL file. Returns first match or None."""
    for record in read_jsonl(path):
        if record.get('title') == title:
            return record
    return None


def timestamp() -> str:
    """Get current ISO timestamp."""
    from file_ops import now_utc_iso
    return now_utc_iso()
