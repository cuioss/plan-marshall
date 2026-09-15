#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Pure runtime-information collector owning the client.toon schema.

Client.toon entries are keyed by human-readable UTC datetime stamp; multiple
runs append a new timestamped entry instead of overwriting.

Collects the client.toon attributes — one required (`harness`) plus five
optional (model name/type/version, effort level, and build-version) — on a
best-effort basis.
Attributes that scripts cannot read are dropped rather than estimated; where
script access is hard or strange an LLM fallback may fill the gap upstream —
this module never estimates.

Scope: concrete implementations exist for ``claude`` and ``opencode`` only.
``antigravity`` appears solely as an example harness value in documentation
and test vectors, never as an implementation target.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon

#: Schema version stamped into every client.toon payload this module renders.
CLIENT_TOON_SCHEMA_VERSION = 1

#: Key holding the timestamp-keyed run entries in every client.toon payload.
CLIENT_TOON_ENTRIES_KEY = 'entries'

#: Entry key a legacy flat client.toon migrates under on first append.
LEGACY_ENTRY_KEY = 'legacy'

#: Human-readable UTC timestamp shape for entry keys. Colons are deliberately
#: absent: a TOON key ends at its first colon, so a ``HH:MM:SS`` stamp would
#: split the key during parsing.
TIMESTAMP_FORMAT = '%Y-%m-%d %H-%M-%S UTC'

#: Payload keys that never belong inside a run entry.
_NON_ENTRY_KEYS = frozenset({'status', 'operation', 'schema_version', 'entries'})

#: Operation name carried in the TOON envelope for runtime-info responses.
RUNTIME_INFO_OPERATION = 'runtime-info'

#: Harness identifiers with concrete providers. Any other harness value —
#: ``antigravity`` included — is an example string for documentation and test
#: vectors only, never a registered runtime target.
SUPPORTED_HARNESSES: tuple[str, ...] = ('claude', 'opencode')

_MODEL_NAME_ENV: tuple[str, ...] = (
    'CLAUDE_CODE_MODEL',
    'CLAUDE_MODEL',
    'ANTHROPIC_MODEL',
    'OPENCODE_MODEL',
    'OPENCODE_MODEL_NAME',
    'MODEL_NAME',
)

_MODEL_TYPE_ENV: tuple[str, ...] = (
    'CLAUDE_MODEL_TYPE',
    'OPENCODE_MODEL_TYPE',
    'MODEL_TYPE',
)

_MODEL_VERSION_ENV: tuple[str, ...] = (
    'CLAUDE_MODEL_VERSION',
    'OPENCODE_MODEL_VERSION',
    'MODEL_VERSION',
)

_EFFORT_ENV: tuple[str, ...] = (
    'PLAN_MARSHALL_EFFORT',
    'MARSHALL_EFFORT',
    'EFFORT_LEVEL',
)

_BUILD_VERSION_ENV: tuple[str, ...] = (
    'PLAN_MARSHALL_BUILD_VERSION',
    'BUILD_VERSION',
)


def _first_env(names: tuple[str, ...], env: Mapping[str, str] | None = None) -> str | None:
    """Return the first non-empty value among *names*, or None.

    Args:
        names: Environment variable names in preference order.
        env: Explicit environment mapping for tests; defaults to ``os.environ``.

    Returns:
        The first non-blank value, stripped, or None when none is set.
    """
    source: Mapping[str, str] = env if env is not None else os.environ
    for name in names:
        value = source.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def read_model_name(env: Mapping[str, str] | None = None) -> str | None:
    """Read the model name from script-accessible sources.

    Best-effort: returns None when no source carries a value.
    """
    return _first_env(_MODEL_NAME_ENV, env)


def read_model_type(env: Mapping[str, str] | None = None) -> str | None:
    """Read the model type from script-accessible sources.

    Best-effort: returns None when no source carries a value. Never derived
    from the model name — derivation would be estimation.
    """
    return _first_env(_MODEL_TYPE_ENV, env)


def read_model_version(env: Mapping[str, str] | None = None) -> str | None:
    """Read the model version from script-accessible sources.

    Best-effort: returns None when no source carries a value. Never derived
    from the model name — derivation would be estimation.
    """
    return _first_env(_MODEL_VERSION_ENV, env)


def read_effort(env: Mapping[str, str] | None = None) -> str | None:
    """Read the effort level from script-accessible sources.

    Best-effort: returns None when no source carries a value.
    """
    return _first_env(_EFFORT_ENV, env)


def read_build_version(
    env: Mapping[str, str] | None = None,
    marketplace_root: Path | None = None,
) -> str | None:
    """Read the build version from script-accessible sources.

    Preference order: explicit environment override, then the marketplace
    manifest version, otherwise None. Never estimated.

    Args:
        env: Explicit environment mapping for tests; defaults to ``os.environ``.
        marketplace_root: Directory holding ``.claude-plugin/marketplace.json``.
            When None, the ancestor walk from this file locates it.

    Returns:
        The build version string, or None when unreadable.
    """
    override = _first_env(_BUILD_VERSION_ENV, env)
    if override:
        return override
    root = marketplace_root
    if root is None:
        root = _find_marketplace_root()
    if root is None:
        return None
    manifest = root / '.claude-plugin' / 'marketplace.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    metadata = data.get('metadata')
    if not isinstance(metadata, dict):
        return None
    version = metadata.get('version')
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def _find_marketplace_root() -> Path | None:
    """Locate the marketplace root via the ancestor walk.

    The root is the first ancestor holding ``.claude-plugin/marketplace.json``.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / '.claude-plugin' / 'marketplace.json').is_file():
            return ancestor
    return None


def collect_runtime_info(
    harness: str,
    env: Mapping[str, str] | None = None,
    marketplace_root: Path | None = None,
    model_name: str | None = None,
    model_type: str | None = None,
    model_version: str | None = None,
    effort: str | None = None,
    build_version: str | None = None,
) -> dict[str, Any]:
    """Collect the client.toon attribute dict on a best-effort basis.

    The harness identifier is caller-supplied and always present. Every other
    attribute resolves from its explicit override first, then from
    script-accessible sources; attributes with no readable value are dropped
    rather than estimated.

    Args:
        harness: Harness identifier — ``claude`` or ``opencode`` in production.
        env: Explicit environment mapping for tests; defaults to ``os.environ``.
        marketplace_root: Override for build-version manifest lookup.
        model_name: Explicit model name override; auto-read when None.
        model_type: Explicit model type override; auto-read when None.
        model_version: Explicit model version override; auto-read when None.
        effort: Explicit effort override; auto-read when None.
        build_version: Explicit build-version override; auto-read when None.

    Returns:
        Attribute dict carrying ``harness`` plus whichever of ``model_name``,
        ``model_type``, ``model_version``, ``effort``, and ``build_version``
        were readable.
    """
    info: dict[str, Any] = {'harness': harness}
    resolved_name = model_name if model_name else read_model_name(env)
    if resolved_name:
        info['model_name'] = resolved_name
    resolved_type = model_type if model_type else read_model_type(env)
    if resolved_type:
        info['model_type'] = resolved_type
    resolved_version = model_version if model_version else read_model_version(env)
    if resolved_version:
        info['model_version'] = resolved_version
    resolved_effort = effort if effort else read_effort(env)
    if resolved_effort:
        info['effort'] = resolved_effort
    resolved_build = build_version if build_version else read_build_version(env, marketplace_root)
    if resolved_build:
        info['build_version'] = resolved_build
    return info


def format_timestamp_key(moment: datetime | None = None) -> str:
    """Format a human-readable UTC datetime stamp for a client.toon entry key.

    The stamp is sortable and TOON-safe: it carries no colon, because a TOON
    key ends at its first colon and a ``HH:MM:SS`` stamp would split the key
    during parsing.

    Args:
        moment: Timestamp to format; defaults to the current UTC time. Naive
            datetimes are read as UTC.

    Returns:
        Stamp shaped ``YYYY-MM-DD HH-MM-SS UTC``.
    """
    current = moment if moment is not None else datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def _unique_entry_key(entries: Mapping[str, Any], base: str) -> str:
    """Return a key for *base* that never overwrites an existing entry.

    Args:
        entries: Entry map collected so far.
        base: Preferred timestamp key.

    Returns:
        *base* itself when free, else *base* with a `` (N)`` suffix.
    """
    if base not in entries:
        return base
    suffix = 2
    while f'{base} ({suffix})' in entries:
        suffix += 1
    return f'{base} ({suffix})'


def _strip_to_entry(info: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a parsed payload to the attribute dict that belongs in an entry."""
    return {key: value for key, value in dict(info).items() if key not in _NON_ENTRY_KEYS}


def append_client_entry(
    existing: Mapping[str, Any] | None,
    info: Mapping[str, Any],
    timestamp_key: str | None = None,
) -> dict[str, Any]:
    """Merge one run's attributes into a timestamp-keyed client.toon document.

    Multiple runs append a new timestamped entry instead of overwriting: an
    existing timestamp key is suffixed, never replaced. A legacy flat document
    (attributes beside ``schema_version``, as written before timestamp keys)
    migrates under the ``legacy`` entry key so its data survives the upgrade.
    A document whose ``entries`` key is present but not a mapping is REJECTED
    with ``ValueError``: migrating it would silently discard the wrong-shaped
    value, violating append-never-overwrite.

    Args:
        existing: Parsed client.toon document, or None for a fresh document.
        info: Attribute dict as returned by :func:`collect_runtime_info`; a
            parsed runtime-info payload is accepted too (envelope keys are
            stripped).
        timestamp_key: Entry key for this run; defaults to the current UTC
            stamp from :func:`format_timestamp_key`.

    Returns:
        New document carrying ``schema_version`` plus the ``entries`` map.

    Raises:
        ValueError: When *existing* carries an ``entries`` key that is not a
            mapping — the caller must degrade without writing.
    """
    base = timestamp_key if timestamp_key else format_timestamp_key()
    entries: dict[str, Any] = {}
    if isinstance(existing, Mapping):
        current_entries = existing.get(CLIENT_TOON_ENTRIES_KEY)
        if current_entries is None and CLIENT_TOON_ENTRIES_KEY not in existing:
            legacy = _strip_to_entry(existing)
            if legacy:
                entries[_unique_entry_key(entries, LEGACY_ENTRY_KEY)] = legacy
        elif isinstance(current_entries, Mapping):
            for key, value in current_entries.items():
                entries[str(key)] = dict(value) if isinstance(value, Mapping) else value
        else:
            raise ValueError('existing client.toon has a non-mapping entries value; refusing to overwrite')
    key = _unique_entry_key(entries, base)
    entries[key] = _strip_to_entry(info)
    return {'schema_version': CLIENT_TOON_SCHEMA_VERSION, CLIENT_TOON_ENTRIES_KEY: entries}


def to_client_toon(info: Mapping[str, Any], timestamp_key: str | None = None) -> str:
    """Serialize an attribute dict to the timestamp-keyed client.toon document.

    Args:
        info: Attribute dict as returned by :func:`collect_runtime_info`.
        timestamp_key: Entry key for this run; defaults to the current UTC
            stamp from :func:`format_timestamp_key`.

    Returns:
        Serialized TOON string carrying the schema version plus the
        timestamp-keyed ``entries`` map with this run's attributes.
    """
    return serialize_toon(append_client_entry(None, info, timestamp_key))
