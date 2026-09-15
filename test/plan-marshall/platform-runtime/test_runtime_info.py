#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the runtime-info collector and its provider dispatch.

Covers the client.toon schema shape, best-effort drop semantics, the claude
and opencode provider dispatch, and the router unknown-target error path.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

import platform_runtime
import runtime_info
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    """Parse a TOON string and return the result dict."""
    return parse_toon(output)


def test_collector_always_carries_harness() -> None:
    """The collector names the caller-supplied harness."""
    info = runtime_info.collect_runtime_info('claude', env={}, marketplace_root=Path('/nonexistent'))
    assert info['harness'] == 'claude'


def test_collector_drops_unreadable_attributes() -> None:
    """Attributes with no readable source are absent rather than estimated."""
    info = runtime_info.collect_runtime_info('claude', env={}, marketplace_root=Path('/nonexistent'))
    assert 'model_name' not in info
    assert 'model_type' not in info
    assert 'model_version' not in info
    assert 'effort' not in info
    assert 'build_version' not in info


def test_collector_reads_model_and_effort_from_env() -> None:
    """Explicit environment values surface under their schema keys."""
    env = {
        'CLAUDE_CODE_MODEL': 'claude-sonnet-4-5',
        'MODEL_TYPE': 'chat',
        'MODEL_VERSION': '2026-09-01',
        'PLAN_MARSHALL_EFFORT': 'standard',
    }
    info = runtime_info.collect_runtime_info('claude', env=env, marketplace_root=Path('/nonexistent'))
    assert info['model_name'] == 'claude-sonnet-4-5'
    assert info['model_type'] == 'chat'
    assert info['model_version'] == '2026-09-01'
    assert info['effort'] == 'standard'


def test_collector_never_derives_type_from_name() -> None:
    """A model name alone never implies a type or version."""
    info = runtime_info.collect_runtime_info(
        'claude',
        env={'CLAUDE_CODE_MODEL': 'claude-sonnet-4-5'},
        marketplace_root=Path('/nonexistent'),
    )
    assert info['model_name'] == 'claude-sonnet-4-5'
    assert 'model_type' not in info
    assert 'model_version' not in info


def test_collector_reads_build_version_from_manifest(tmp_path: Path) -> None:
    """The marketplace manifest version is a readable build-version source."""
    manifest_dir = tmp_path / '.claude-plugin'
    manifest_dir.mkdir(parents=True)
    (manifest_dir / 'marketplace.json').write_text(
        json.dumps({'metadata': {'version': '9.9'}}),
        encoding='utf-8',
    )
    assert runtime_info.read_build_version(env={}, marketplace_root=tmp_path) == '9.9'


def test_client_toon_carries_schema_version() -> None:
    """The rendered client.toon document states its schema version."""
    rendered = runtime_info.to_client_toon({'harness': 'claude'})
    assert _parse(rendered)['schema_version'] == runtime_info.CLIENT_TOON_SCHEMA_VERSION


def test_timestamp_key_is_human_readable_without_colons() -> None:
    """The timestamp key reads as a UTC datetime and stays TOON-safe."""
    moment = datetime(2026, 9, 15, 7, 0, 0, tzinfo=UTC)
    assert runtime_info.format_timestamp_key(moment) == '2026-09-15 07-00-00 UTC'
    assert ':' not in runtime_info.format_timestamp_key(moment)


def test_client_toon_wraps_single_entry_under_timestamp_key() -> None:
    """The rendered document keys the run's attributes by its timestamp."""
    rendered = runtime_info.to_client_toon(
        {'harness': 'claude'},
        timestamp_key='2026-09-15 07-00-00 UTC',
    )
    doc = _parse(rendered)
    assert doc['entries']['2026-09-15 07-00-00 UTC']['harness'] == 'claude'


def test_append_preserves_prior_entries_across_runs() -> None:
    """A second run appends its entry while the first entry stays intact."""
    first = runtime_info.append_client_entry(
        None,
        {'harness': 'claude'},
        timestamp_key='2026-09-15 07-00-00 UTC',
    )
    second = runtime_info.append_client_entry(
        first,
        {'harness': 'opencode'},
        timestamp_key='2026-09-15 08-00-00 UTC',
    )
    assert second['entries']['2026-09-15 07-00-00 UTC'] == {'harness': 'claude'}
    assert second['entries']['2026-09-15 08-00-00 UTC'] == {'harness': 'opencode'}


def test_append_suffixes_colliding_timestamp_instead_of_overwriting() -> None:
    """A repeated timestamp key gains a suffix so no entry is overwritten."""
    first = runtime_info.append_client_entry(
        None,
        {'harness': 'claude'},
        timestamp_key='2026-09-15 07-00-00 UTC',
    )
    second = runtime_info.append_client_entry(
        first,
        {'harness': 'opencode'},
        timestamp_key='2026-09-15 07-00-00 UTC',
    )
    assert second['entries']['2026-09-15 07-00-00 UTC'] == {'harness': 'claude'}
    assert second['entries']['2026-09-15 07-00-00 UTC (2)'] == {'harness': 'opencode'}


def test_append_migrates_legacy_flat_document() -> None:
    """A pre-timestamp flat document survives under the legacy entry key."""
    legacy = {'schema_version': 1, 'harness': 'claude', 'effort': 'standard'}
    merged = runtime_info.append_client_entry(
        legacy,
        {'harness': 'opencode'},
        timestamp_key='2026-09-15 08-00-00 UTC',
    )
    assert merged['entries']['legacy'] == {'harness': 'claude', 'effort': 'standard'}
    assert merged['entries']['2026-09-15 08-00-00 UTC'] == {'harness': 'opencode'}


def test_append_strips_envelope_keys_from_entries() -> None:
    """Envelope keys never leak into a run entry."""
    merged = runtime_info.append_client_entry(
        None,
        {'status': 'success', 'operation': 'runtime-info', 'harness': 'claude'},
        timestamp_key='2026-09-15 07-00-00 UTC',
    )
    entry = merged['entries']['2026-09-15 07-00-00 UTC']
    assert entry == {'harness': 'claude'}


def test_append_rejects_non_mapping_entries_value() -> None:
    """A present-but-wrong-shaped entries value refuses instead of migrating."""
    import pytest

    with pytest.raises(ValueError):
        runtime_info.append_client_entry(
            {'schema_version': 1, 'entries': ['not', 'a', 'mapping']},
            {'harness': 'claude'},
            timestamp_key='2026-09-15 07-00-00 UTC',
        )


def test_opencode_runtime_prefers_opencode_env_over_claude_env(monkeypatch: Any) -> None:
    """An OpenCode entry never carries Claude metadata from a mixed env."""
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-model')
    monkeypatch.setenv('OPENCODE_MODEL', 'opencode-model')
    result = _parse(OpenCodeRuntime().runtime_info())
    assert result['model_name'] == 'opencode-model'


def test_claude_runtime_prefers_claude_env_over_opencode_env(monkeypatch: Any) -> None:
    """A Claude entry never carries OpenCode metadata from a mixed env."""
    monkeypatch.setenv('OPENCODE_MODEL', 'opencode-model')
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-model')
    result = _parse(ClaudeRuntime().runtime_info())
    assert result['model_name'] == 'claude-model'


def test_claude_provider_reports_claude_harness() -> None:
    """ClaudeRuntime answers runtime-info with the claude harness."""
    result = _parse(ClaudeRuntime().runtime_info())
    assert result['status'] == 'success'
    assert result['operation'] == 'runtime-info'
    assert result['harness'] == 'claude'


def test_opencode_provider_reports_opencode_harness() -> None:
    """OpenCodeRuntime answers runtime-info with the opencode harness."""
    result = _parse(OpenCodeRuntime().runtime_info())
    assert result['status'] == 'success'
    assert result['operation'] == 'runtime-info'
    assert result['harness'] == 'opencode'


def test_antigravity_is_an_example_harness_value_only() -> None:
    """The collector accepts antigravity as a string while the registry rejects it."""
    info = runtime_info.collect_runtime_info(
        'antigravity',
        env={},
        marketplace_root=Path('/nonexistent'),
    )
    assert info['harness'] == 'antigravity'
    assert 'antigravity' not in platform_runtime._REGISTRY
    assert platform_runtime._make_runtime('antigravity') is None


def test_router_rejects_unknown_target() -> None:
    """An unregistered runtime.target yields the unknown_target error path."""
    runtime = platform_runtime._make_runtime('no-such-target')
    assert runtime is None
