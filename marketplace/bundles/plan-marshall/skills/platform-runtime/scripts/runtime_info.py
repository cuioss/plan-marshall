#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Pure runtime-information collector owning the client.toon schema.

Client.toon entries are keyed by human-readable UTC datetime stamp; multiple
runs append a new timestamped entry instead of overwriting.

Collects the client.toon attributes — always-present `harness`, `transcripts`
and `harness_source`, plus optional (model, model type/version, effort level and
the bundle/executor version) — on a best-effort basis.
Attributes that scripts cannot read are dropped rather than estimated; where
script access is hard or strange an LLM fallback may fill the gap upstream —
this module never estimates.

Every value that CAN come from more than one place carries its source: `model`
and `effort` are tagged `self_reported` when a caller-supplied flag supplied
them and `measured` when a script-readable source did. On OpenCode the model is
measured rather than self-reported: it is read from the plan's session tree in
`opencode.db`, through the shared read-only session reader
(``_opencode_sessions``), which owns the database path, the schema gate and the
``parent_id`` walk — this module opens no database of its own. See
:func:`measure_opencode_model`.

Scope: concrete implementations exist for ``claude``, ``opencode``, and
``antigravity``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import _opencode_sessions
from toon_parser import serialize_toon

#: Schema version stamped into every client.toon payload this module renders.
CLIENT_TOON_SCHEMA_VERSION = 1

#: Key holding the timestamp-keyed run entries in every client.toon payload.
CLIENT_TOON_ENTRIES_KEY = 'entries'

#: Entry key a legacy flat client.toon migrates under on first append.
LEGACY_ENTRY_KEY = 'legacy'

#: Source tag for a value the executing LLM reported about itself (a CLI flag).
SOURCE_SELF_REPORTED = 'self_reported'

#: Source tag for a value read from a script-readable source — the environment
#: lists, or the OpenCode session database.
SOURCE_MEASURED = 'measured'

#: The value recorded when a source that SHOULD carry the value could not be
#: read. It asserts only that nothing was observed — never a real model.
VALUE_UNKNOWN = 'unknown'

#: The value recorded when a measured session tree ran more than one model or
#: variant. The distinct values are listed beside it — never averaged, and never
#: reduced to the root session's value.
MODEL_MIXED = 'mixed'

#: Harness identifier whose measured model source is the session database.
OPENCODE_HARNESS = 'opencode'

#: Environment variable naming the OpenCode session the plan's LLM runs under.
#: Resolved to its root through ``session_v2.parent_id`` before measurement.
OPENCODE_SESSION_ID_ENV = 'OPENCODE_SESSION_ID'

#: Human-readable UTC timestamp shape for entry keys. Colons are deliberately
#: absent: a TOON key ends at its first colon, so a ``HH:MM:SS`` stamp would
#: split the key during parsing.
TIMESTAMP_FORMAT = '%Y-%m-%d %H-%M-%S UTC'

#: Payload keys that never belong inside a run entry.
_NON_ENTRY_KEYS = frozenset({'status', 'operation', 'schema_version', 'entries'})

#: Operation name carried in the TOON envelope for runtime-info responses.
RUNTIME_INFO_OPERATION = 'runtime-info'

#: Harness identifiers with concrete providers.
SUPPORTED_HARNESSES: tuple[str, ...] = ('claude', 'opencode', 'antigravity')

#: Transcript-availability capability per harness. `full` means the harness
#: exposes a session transcript (and subagent transcripts) the normalized-tokens
#: operation can walk; `none` means it exposes nothing to walk, so every
#: unmeasured token figure on that harness reports `unknown` rather than zero.
#: The value is derived from the harness identifier alone — never estimated.
TRANSCRIPTS_FULL = 'full'
TRANSCRIPTS_NONE = 'none'
TRANSCRIPTS_CAPABILITIES: tuple[str, ...] = (TRANSCRIPTS_FULL, TRANSCRIPTS_NONE)

#: Harness identifiers whose transcript surface is walkable.
_TRANSCRIPTS_FULL_HARNESSES: frozenset[str] = frozenset({'claude'})

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


def resolve_harness_attribution(cwd: Path | None = None) -> dict[str, Any]:
    """Resolve the harness and the cascade tier that produced it.

    The router already resolves the target through ``target_context``; this
    reader reports the SAME verdict as client.toon fields, so a fallback
    ``claude`` is never confusable with a detected one:

    - ``harness`` — the resolved identifier;
    - ``harness_source`` — ``env`` / ``local_config`` / ``fallback``;
    - ``reason`` — the fallback tier's own reason for falling through;
    - ``harness_configured`` / ``harness_mismatch`` — present only when the
      AMBIENT tier and the machine-local configuration name DIFFERENT targets,
      which is a real disagreement between two tiers rather than a stale config.

    Args:
        cwd: Directory the machine-local config walk starts from. Defaults to
            ``Path.cwd()``.

    Returns:
        The client.toon harness fields.
    """
    import target_context

    resolved = target_context.resolve_target(cwd)
    fields: dict[str, Any] = {
        'harness': resolved['target'],
        'harness_source': resolved['target_source'],
    }
    if resolved['target_source'] == target_context.SOURCE_FALLBACK and resolved['reason']:
        fields['reason'] = resolved['reason']
    if resolved['target_source'] == target_context.SOURCE_ENV:
        configured = target_context.read_configured_target(cwd)
        if configured and configured != resolved['target']:
            fields['harness_configured'] = configured
            fields['harness_mismatch'] = True
    return fields


def _parse_opencode_model(raw: object) -> dict[str, str] | None:
    """Parse one ``session_v2.model`` cell into its id/provider/variant parts.

    The column holds a JSON object shaped
    ``{"id": ..., "providerID": ..., "variant": ...}``. A cell that is absent,
    not JSON, or not an object carrying a non-blank ``id`` yields ``None`` —
    the cell is dropped rather than guessed at.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    model_id = parsed.get('id')
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    fields: dict[str, str] = {'id': model_id.strip()}
    for key, column in (('provider', 'providerID'), ('variant', 'variant')):
        value = parsed.get(column)
        if isinstance(value, str) and value.strip():
            fields[key] = value.strip()
    return fields


def _format_model_key(fields: Mapping[str, str]) -> str:
    """Render one measured model as ``id`` or ``id/variant`` for the mixed list."""
    variant = fields.get('variant')
    return f'{fields["id"]}/{variant}' if variant else fields['id']


def _mixed_model_labels(distinct: Mapping[tuple[str, str, str], Mapping[str, str]]) -> list[str]:
    """Render the distinct models of a MIXED tree as one label each, sorted.

    The plain ``id/variant`` form is what the payload spec documents, so it is
    used whenever the labels are distinct. Two DIFFERENT models — same id and
    variant, different provider — would render the same label, which would make
    the recorded list claim one model where the tree ran two; in that case the
    provider is appended to every label (``id/variant/provider``) so the list
    identifies both, consistently within the entry.
    """
    rendered = {key: _format_model_key(fields) for key, fields in distinct.items()}
    labels = list(rendered.values())
    if len(set(labels)) != len(labels):
        labels = [f'{rendered[key]}/{key[1]}' if key[1] else rendered[key] for key in distinct]
    return sorted(labels)


def measure_opencode_model(
    db_path: Path | None,
    session_id: str | None,
) -> dict[str, Any] | None:
    """Measure the model the OpenCode session tree ran under.

    Resolves *session_id* to its root and walks the tree through the shared
    read-only session reader (``_opencode_sessions``), which owns the database
    path resolution, the schema gate and the ``parent_id`` walk. The measurement
    needs tier 1 only — ``session_v2(id, parent_id, model)`` — so a database
    carrying no message table or token columns still measures its model.

    A tree that ran exactly one model/variant records that model, its variant
    and its provider as :data:`SOURCE_MEASURED`. A tree that ran more than one
    records ``model: mixed`` with the distinct ``id/variant`` values listed —
    never averaged and never reduced to the root's value;
    :func:`_mixed_model_labels` appends the provider when two providers would
    otherwise render the same label.

    Args:
        db_path: The ``opencode.db`` to read, or ``None``.
        session_id: The session the plan's LLM runs under, or ``None`` when no
            session is in scope — the caller then has nothing to measure.

    Returns:
        The measured model fields, ``{'model': unknown, 'model_source:
        'measured'}`` when the tree could not be read, or ``None`` when no
        *session_id* is in scope (the caller falls back to its own sources).
    """
    if not session_id:
        return None
    unknown = {'model': VALUE_UNKNOWN, 'model_source': SOURCE_MEASURED}
    if db_path is None:
        return dict(unknown)
    reading = _opencode_sessions.read_session_rows(db_path)
    if not reading['ok']:
        return dict(unknown)
    rows = reading['rows']
    root = _opencode_sessions.session_root(session_id, rows)
    if root is None:
        return dict(unknown)
    distinct: dict[tuple[str, str, str], dict[str, str]] = {}
    for member in _opencode_sessions.session_tree(root, rows):
        fields = _parse_opencode_model(rows[member][1])
        if fields is None:
            continue
        distinct[(fields['id'], fields.get('provider', ''), fields.get('variant', ''))] = fields
    if not distinct:
        return dict(unknown)
    if len(distinct) == 1:
        only = next(iter(distinct.values()))
        measured: dict[str, Any] = {'model': only['id'], 'model_source': SOURCE_MEASURED}
        if 'variant' in only:
            measured['variant'] = only['variant']
        if 'provider' in only:
            measured['provider'] = only['provider']
        return measured
    listed = ', '.join(_mixed_model_labels(distinct))
    return {'model': MODEL_MIXED, 'models': listed, 'model_source': SOURCE_MEASURED}


def _resolve_model_fields(
    harness: str,
    env: Mapping[str, str] | None,
    model_name: str | None,
    opencode_db_path: Path | None,
    opencode_session_id: str | None,
) -> dict[str, Any]:
    """Resolve the ``model`` / ``model_source`` pair for one collection.

    On OpenCode the model is MEASURED, never self-reported: the session database
    is authoritative and wins over a flag. When a session id is in scope the
    measurement's answer stands (``unknown`` included); with no session id in
    scope there is nothing to measure, so the script-readable environment lists
    are measured and a still-unreadable value is OMITTED — the flag is never
    consulted, on either path.

    Everywhere else a caller-supplied flag wins and is tagged
    :data:`SOURCE_SELF_REPORTED`; otherwise the environment lists are measured.
    A value with no readable source is omitted entirely.
    """
    if harness == OPENCODE_HARNESS:
        measured = measure_opencode_model(opencode_db_path, opencode_session_id)
        if measured is not None:
            return measured
        from_env = read_model_name(env)
        if from_env:
            return {'model': from_env, 'model_source': SOURCE_MEASURED}
        return {}

    if model_name:
        return {'model': model_name, 'model_source': SOURCE_SELF_REPORTED}
    from_env = read_model_name(env)
    if from_env:
        return {'model': from_env, 'model_source': SOURCE_MEASURED}
    return {}


def _resolve_effort_fields(
    env: Mapping[str, str] | None,
    effort: str | None,
) -> dict[str, Any]:
    """Resolve the ``effort`` / ``effort_source`` pair for one collection.

    A caller-supplied flag wins and is tagged :data:`SOURCE_SELF_REPORTED`;
    otherwise the environment lists are measured. A value with no readable
    source is omitted entirely. Nothing is ever estimated.
    """
    if effort:
        return {'effort': effort, 'effort_source': SOURCE_SELF_REPORTED}
    from_env = read_effort(env)
    if from_env:
        return {'effort': from_env, 'effort_source': SOURCE_MEASURED}
    return {}


def _find_bundle_root() -> Path | None:
    """Locate the bundle this module runs from via the ancestor walk.

    The root is the first ancestor holding ``.claude-plugin/plugin.json`` — the
    bundle manifest, so an INSTALLED bundle (whose ancestor chain carries no
    marketplace manifest) resolves its own version.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
    return None


def read_bundle_version(bundle_root: Path | None = None) -> str | None:
    """Read the ``version`` of the bundle manifest the collector runs from.

    The value is the ``version`` in ``.claude-plugin/plugin.json`` of the bundle
    at *bundle_root* (default: the bundle this module runs from). It replaces the
    marketplace manifest's ``metadata.version``: the marketplace manifest
    describes the aggregate project, not the bundle that is loaded. Never
    estimated.

    Args:
        bundle_root: Directory holding ``.claude-plugin/plugin.json``. When
            None, the ancestor walk from this file locates it.

    Returns:
        The bundle version string, or None when unreadable.
    """
    root = bundle_root if bundle_root is not None else _find_bundle_root()
    if root is None:
        return None
    manifest = root / '.claude-plugin' / 'plugin.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    version = data.get('version')
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def read_executor_version(executor_path: Path | None = None) -> str | None:
    """Read the executor's ``MARSHALL_VERSION`` through the shared registry reader.

    Reuses ``plugin_registry.read_executor_version`` rather than re-parsing the
    assignment, so the version's grammar has one definition. An executor that is
    absent, unreadable or carries no usable assignment yields None — never a
    substituted version.

    Args:
        executor_path: The generated executor to read. When None, the executor
            of the current project (``{cwd}/.plan/execute-script.py``) is read.

    Returns:
        The executor version string, or None when it could not be read.
    """
    import plugin_registry

    path = executor_path if executor_path is not None else plugin_registry.default_executor_path(Path.cwd())
    state, version = plugin_registry.read_executor_version(Path(path))
    if state == plugin_registry.EXECUTOR_VERSION_FOUND:
        return version
    return None


def read_transcripts_capability(harness: str) -> str:
    """Return the transcript-availability capability for *harness*.

    Args:
        harness: Harness identifier — ``claude``, ``opencode``, or
            ``antigravity``.

    Returns:
        ``full`` when the harness exposes a walkable session transcript,
        ``none`` otherwise. An unrecognised harness reads as ``none`` —
        fail-closed, so no transcript is ever claimed where none exists.
    """
    return TRANSCRIPTS_FULL if harness in _TRANSCRIPTS_FULL_HARNESSES else TRANSCRIPTS_NONE


def collect_runtime_info(
    harness: str,
    env: Mapping[str, str] | None = None,
    bundle_root: Path | None = None,
    model_name: str | None = None,
    model_type: str | None = None,
    model_version: str | None = None,
    effort: str | None = None,
    bundle_version: str | None = None,
    *,
    harness_attribution: Mapping[str, Any] | None = None,
    executor_path: Path | None = None,
    opencode_db_path: Path | None = None,
    opencode_session_id: str | None = None,
) -> dict[str, Any]:
    """Collect the client.toon attribute dict on a best-effort basis.

    The harness identifier is caller-supplied and always present. Every other
    attribute resolves from its explicit override first, then from
    script-accessible sources; attributes with no readable value are dropped
    rather than estimated. ``model`` and ``effort`` additionally carry their
    source tag, and on OpenCode the model is measured from the session database
    rather than taken from a flag (see :func:`_resolve_model_fields`).

    Args:
        harness: Harness identifier — ``claude``, ``opencode``, or ``antigravity``.
        env: Explicit environment mapping for tests; defaults to ``os.environ``.
        bundle_root: Bundle whose ``.claude-plugin/plugin.json`` carries the
            reported ``bundle_version``; auto-located when None.
        model_name: Explicit model name override; auto-read when None.
        model_type: Explicit model type override; auto-read when None.
        model_version: Explicit model version override; auto-read when None.
        effort: Explicit effort override; auto-read when None.
        bundle_version: Explicit bundle-version override; auto-read when None.
        harness_attribution: The ``target_context`` verdict fields to report;
            resolved by the ancestor/cwd walk when None.
        executor_path: The executor whose ``MARSHALL_VERSION`` is reported as
            ``executor_version``; the current project's when None.
        opencode_db_path: The ``opencode.db`` to measure the OpenCode model
            from; only consulted when *harness* is ``opencode``.
        opencode_session_id: The session whose tree the OpenCode model is
            measured over; only consulted when *harness* is ``opencode``.

    Returns:
        Attribute dict carrying ``harness``, ``transcripts`` and
        ``harness_source`` plus whichever of
        ``model`` (with ``model_source``), ``model_type``, ``model_version``,
        ``effort`` (with ``effort_source``), ``bundle_version`` and
        ``executor_version`` were readable, plus the fallback ``reason`` or the
        mismatch fields when they apply.
    """
    attribution = dict(harness_attribution) if harness_attribution is not None else resolve_harness_attribution()
    info: dict[str, Any] = {'harness': harness, 'transcripts': read_transcripts_capability(harness)}
    source = attribution.get('harness_source')
    if isinstance(source, str) and source:
        info['harness_source'] = source
    if attribution.get('reason'):
        info['reason'] = attribution['reason']
    if attribution.get('harness_configured'):
        info['harness_configured'] = attribution['harness_configured']
    if attribution.get('harness_mismatch'):
        info['harness_mismatch'] = True
    info.update(_resolve_model_fields(harness, env, model_name, opencode_db_path, opencode_session_id))
    resolved_type = model_type if model_type else read_model_type(env)
    if resolved_type:
        info['model_type'] = resolved_type
    resolved_version = model_version if model_version else read_model_version(env)
    if resolved_version:
        info['model_version'] = resolved_version
    info.update(_resolve_effort_fields(env, effort))
    resolved_bundle = bundle_version if bundle_version else read_bundle_version(bundle_root)
    if resolved_bundle:
        info['bundle_version'] = resolved_bundle
    resolved_executor = read_executor_version(executor_path)
    if resolved_executor:
        info['executor_version'] = resolved_executor
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
