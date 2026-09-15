#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the runtime-info collector and its provider dispatch.

Covers the client.toon schema shape, best-effort drop semantics, the claude
and opencode provider dispatch, and the router unknown-target error path.
"""

from __future__ import annotations

import json
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
