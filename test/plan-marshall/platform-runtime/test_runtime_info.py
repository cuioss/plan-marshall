#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the runtime-info collector and its provider dispatch.

Covers the client.toon schema shape, best-effort drop semantics, the claude
and opencode provider dispatch, and the router unknown-target error path.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

import platform_runtime
import runtime_info
import target_context
from antigravity_runtime import AntigravityRuntime
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon

from conftest import get_script_path, run_script

_PLATFORM_SCRIPT = get_script_path('plan-marshall', 'platform-runtime', 'platform_runtime.py')


def _parse(output: str) -> dict[str, Any]:
    """Parse a TOON string and return the result dict."""
    return parse_toon(output)


def _clean_platform_env() -> dict[str, str]:
    """Env overrides that blank every signal :mod:`target_context` or the
    collector could read, so a subprocess resolves the fallback target and no
    model/effort value.
    """
    names = {
        *(name for name, _target in target_context.TARGET_ENV_SIGNALS),
        runtime_info.OPENCODE_SESSION_ID_ENV,
        *runtime_info._MODEL_NAME_ENV,
        *runtime_info._MODEL_TYPE_ENV,
        *runtime_info._MODEL_VERSION_ENV,
        *runtime_info._EFFORT_ENV,
    }
    return dict.fromkeys(names, '')


def _fixture_project(tmp_path: Path) -> Path:
    """A cwd with a ``.plan/marshal.json`` and no machine-local harness config.

    The router refuses to dispatch without a ``marshal.json``, and the
    presence of that file terminates the local-config walk (so no machine-local
    harness is picked up), leaving the target at the ``fallback`` tier.
    """
    project = tmp_path / 'project'
    plan_dir = project / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'claude'}}), encoding='utf-8')
    return project


def _write_local_harness(project: Path, harness: str) -> None:
    """Write a machine-local harness config naming *harness* for *project*."""
    harness_dir = project / '.plan' / 'local' / 'harness'
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / f'{harness}.json').write_text(
        json.dumps({'schema_version': 1, 'harness': harness}),
        encoding='utf-8',
    )


def _write_session_db(db_path: Path, rows: list[tuple[str, str | None, str]]) -> None:
    """Create a fixture ``session_v2`` table with ``(id, parent_id, model_json)`` rows."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT)')
        conn.executemany('INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, ?)', rows)
        conn.commit()
    finally:
        conn.close()


def _model_json(model_id: str, variant: str, provider: str = 'opencode') -> str:
    return json.dumps({'id': model_id, 'providerID': provider, 'variant': variant})


def test_collector_always_carries_harness() -> None:
    """The collector names the caller-supplied harness."""
    info = runtime_info.collect_runtime_info('claude', env={}, bundle_root=Path('/nonexistent'))
    assert info['harness'] == 'claude'


def test_collector_drops_unreadable_attributes() -> None:
    """Attributes with no readable source are absent rather than estimated."""
    info = runtime_info.collect_runtime_info('claude', env={}, bundle_root=Path('/nonexistent'))
    assert 'model' not in info
    assert 'model_type' not in info
    assert 'model_version' not in info
    assert 'effort' not in info
    assert 'bundle_version' not in info


def test_collector_reads_model_and_effort_from_env() -> None:
    """Explicit environment values surface under their schema keys."""
    env = {
        'CLAUDE_CODE_MODEL': 'claude-sonnet-4-5',
        'MODEL_TYPE': 'chat',
        'MODEL_VERSION': '2026-09-01',
        'PLAN_MARSHALL_EFFORT': 'standard',
    }
    info = runtime_info.collect_runtime_info('claude', env=env, bundle_root=Path('/nonexistent'))
    assert info['model'] == 'claude-sonnet-4-5'
    assert info['model_type'] == 'chat'
    assert info['model_version'] == '2026-09-01'
    assert info['effort'] == 'standard'


def test_collector_never_derives_type_from_name() -> None:
    """A model name alone never implies a type or version."""
    info = runtime_info.collect_runtime_info(
        'claude',
        env={'CLAUDE_CODE_MODEL': 'claude-sonnet-4-5'},
        bundle_root=Path('/nonexistent'),
    )
    assert info['model'] == 'claude-sonnet-4-5'
    assert 'model_type' not in info
    assert 'model_version' not in info


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
    monkeypatch.delenv('OPENCODE_SESSION_ID', raising=False)
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-model')
    monkeypatch.setenv('OPENCODE_MODEL', 'opencode-model')
    result = _parse(OpenCodeRuntime().runtime_info())
    assert result['model'] == 'opencode-model'


def test_claude_runtime_prefers_claude_env_over_opencode_env(monkeypatch: Any) -> None:
    """A Claude entry never carries OpenCode metadata from a mixed env."""
    monkeypatch.setenv('OPENCODE_MODEL', 'opencode-model')
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-model')
    result = _parse(ClaudeRuntime().runtime_info())
    assert result['model'] == 'claude-model'


def test_antigravity_runtime_never_carries_claude_or_opencode_env(monkeypatch: Any) -> None:
    """An Antigravity entry never carries Claude or OpenCode model metadata."""
    monkeypatch.delenv('MODEL_NAME', raising=False)
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-model')
    monkeypatch.setenv('OPENCODE_MODEL', 'opencode-model')
    result = _parse(AntigravityRuntime().runtime_info())
    assert result.get('model') is None


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


def test_custom_harness_is_an_example_harness_value_only() -> None:
    """The collector accepts arbitrary harness strings while the registry rejects unregistered ones."""
    info = runtime_info.collect_runtime_info(
        'custom-harness',
        env={},
        bundle_root=Path('/nonexistent'),
    )
    assert info['harness'] == 'custom-harness'
    assert 'custom-harness' not in platform_runtime._REGISTRY
    assert platform_runtime._make_runtime('custom-harness') is None


def test_router_rejects_unknown_target() -> None:
    """An unregistered runtime.target yields the unknown_target error path."""
    runtime = platform_runtime._make_runtime('no-such-target')
    assert runtime is None


# =============================================================================
# D1 — self-reported model/effort and per-value source tags
# =============================================================================


def test_self_reported_model_and_effort_carry_their_source() -> None:
    """A flag-supplied value is recorded with its ``self_reported`` source."""
    info = runtime_info.collect_runtime_info(
        'claude',
        env={},
        bundle_root=Path('/nonexistent'),
        model_name='claude-opus-5-5',
        effort='high',
    )
    assert info['model'] == 'claude-opus-5-5'
    assert info['model_source'] == runtime_info.SOURCE_SELF_REPORTED
    assert info['effort'] == 'high'
    assert info['effort_source'] == runtime_info.SOURCE_SELF_REPORTED


def test_script_readable_model_and_effort_are_measured() -> None:
    """A value read from the environment lists is recorded as ``measured``."""
    info = runtime_info.collect_runtime_info(
        'claude',
        env={'CLAUDE_CODE_MODEL': 'claude-sonnet-4-5', 'PLAN_MARSHALL_EFFORT': 'standard'},
        bundle_root=Path('/nonexistent'),
    )
    assert info['model'] == 'claude-sonnet-4-5'
    assert info['model_source'] == runtime_info.SOURCE_MEASURED
    assert info['effort'] == 'standard'
    assert info['effort_source'] == runtime_info.SOURCE_MEASURED


def test_absent_model_and_effort_carry_no_source() -> None:
    """Neither the value nor its source is emitted when nothing is readable."""
    info = runtime_info.collect_runtime_info('claude', env={}, bundle_root=Path('/nonexistent'))
    assert 'model' not in info
    assert 'model_source' not in info
    assert 'effort' not in info
    assert 'effort_source' not in info


def test_runtime_info_cli_accepts_self_reported_model_and_effort(tmp_path: Path) -> None:
    """The ``runtime-info`` CLI forwards ``--model`` / ``--effort`` to the collector."""
    project = _fixture_project(tmp_path)

    result = run_script(
        _PLATFORM_SCRIPT,
        'runtime-info',
        '--model',
        'claude-opus-5-5',
        '--effort',
        'high',
        cwd=project,
        env_overrides=_clean_platform_env(),
    )

    assert result.returncode == 0, result.stderr
    parsed = _parse(result.stdout)
    assert parsed['model'] == 'claude-opus-5-5'
    assert parsed['model_source'] == runtime_info.SOURCE_SELF_REPORTED
    assert parsed['effort'] == 'high'
    assert parsed['effort_source'] == runtime_info.SOURCE_SELF_REPORTED


def test_runtime_info_cli_without_flags_emits_neither_key(tmp_path: Path) -> None:
    """A flagless call with no readable source emits neither model nor effort."""
    project = _fixture_project(tmp_path)

    result = run_script(_PLATFORM_SCRIPT, 'runtime-info', cwd=project, env_overrides=_clean_platform_env())

    assert result.returncode == 0, result.stderr
    parsed = _parse(result.stdout)
    assert 'model' not in parsed
    assert 'effort' not in parsed


def test_opencode_model_is_measured_from_the_session_tree(tmp_path: Path) -> None:
    """A root and its sub-agents on one model/variant measure that model."""
    db_path = tmp_path / 'opencode.db'
    model = _model_json('deepseek-v4.1-flash', 'high')
    _write_session_db(
        db_path,
        [
            ('ses-root', None, model),
            ('ses-child-a', 'ses-root', model),
            ('ses-child-b', 'ses-root', model),
        ],
    )

    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        opencode_db_path=db_path,
        opencode_session_id='ses-child-a',
    )

    assert info['model'] == 'deepseek-v4.1-flash'
    assert info['variant'] == 'high'
    assert info['model_source'] == runtime_info.SOURCE_MEASURED


def test_opencode_split_model_tree_is_mixed(tmp_path: Path) -> None:
    """A tree that ran more than one model lists both rather than reducing to the root."""
    db_path = tmp_path / 'opencode.db'
    _write_session_db(
        db_path,
        [
            ('ses-root', None, _model_json('deepseek-v4.1-flash', 'high')),
            ('ses-child-a', 'ses-root', _model_json('deepseek-v4.1-flash', 'high')),
            ('ses-child-b', 'ses-root', _model_json('gpt-5', 'low')),
        ],
    )

    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        opencode_db_path=db_path,
        opencode_session_id='ses-root',
    )

    assert info['model'] == 'mixed'
    assert info['model_source'] == runtime_info.SOURCE_MEASURED
    listed = info['models']
    assert 'deepseek-v4.1-flash/high' in listed
    assert 'gpt-5/low' in listed


def test_opencode_split_providers_disambiguate_the_mixed_labels(tmp_path: Path) -> None:
    """Same id+variant on two providers lists BOTH models, not one label twice."""
    db_path = tmp_path / 'opencode.db'
    _write_session_db(
        db_path,
        [
            ('ses-root', None, _model_json('shared-model', 'high', provider='provider-a')),
            ('ses-child-a', 'ses-root', _model_json('shared-model', 'high', provider='provider-b')),
        ],
    )

    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        opencode_db_path=db_path,
        opencode_session_id='ses-root',
    )

    assert info['model'] == 'mixed'
    listed = info['models'].split(', ')
    assert listed == ['shared-model/high/provider-a', 'shared-model/high/provider-b']


def test_opencode_missing_database_records_unknown(tmp_path: Path) -> None:
    """An absent database records the model as unknown, never the flag value."""
    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        model_name='some-flag-value',
        opencode_db_path=tmp_path / 'absent.db',
        opencode_session_id='ses-root',
    )

    assert info['model'] == 'unknown'
    assert info['model'] != 'some-flag-value'


# =============================================================================
# D2 — the version is the installed bundle and executor, not the marketplace manifest
# =============================================================================


def _fixture_bundle(tmp_path: Path, version: str) -> Path:
    bundle = tmp_path / 'bundle'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(json.dumps({'name': 'fixture', 'version': version}))
    return bundle


def _fixture_executor(tmp_path: Path, content: str) -> Path:
    executor = tmp_path / 'execute-script.py'
    executor.write_text(content, encoding='utf-8')
    return executor


def test_bundle_and_executor_versions_come_from_their_fixtures(tmp_path: Path) -> None:
    """A fixture bundle and executor yield both version values."""
    bundle = _fixture_bundle(tmp_path, '0.1.1919')
    executor = _fixture_executor(tmp_path, "MARSHALL_VERSION = '0.1.1916'\n")

    info = runtime_info.collect_runtime_info(
        'claude',
        env={},
        bundle_root=bundle,
        executor_path=executor,
    )

    assert info['bundle_version'] == '0.1.1919'
    assert info['executor_version'] == '0.1.1916'


def test_unreadable_executor_yields_no_executor_version(tmp_path: Path) -> None:
    """An unreadable executor omits executor_version — never the manifest's 0.1."""
    bundle = _fixture_bundle(tmp_path, '0.1.1919')

    info = runtime_info.collect_runtime_info(
        'claude',
        env={},
        bundle_root=bundle,
        executor_path=tmp_path / 'absent-executor.py',
    )

    assert 'executor_version' not in info
    assert info.get('executor_version') != '0.1'


def test_the_marketplace_manifest_build_version_is_replaced() -> None:
    """A default collection reports bundle_version and no marketplace build_version."""
    info = runtime_info.collect_runtime_info('claude', env={})

    assert 'bundle_version' in info
    assert 'build_version' not in info


def test_read_bundle_version_reads_the_bundle_manifest(tmp_path: Path) -> None:
    """The reader takes the bundle's own plugin.json version, or nothing."""
    bundle = _fixture_bundle(tmp_path, '1.2.3')

    assert runtime_info.read_bundle_version(bundle) == '1.2.3'
    assert runtime_info.read_bundle_version(tmp_path / 'absent-bundle') is None


def test_opencode_without_a_session_emits_no_model_key() -> None:
    """With nothing to measure and nothing readable, OpenCode omits the model.

    The Done-when's "no flags and no environment variables returns neither key"
    clause therefore holds on OpenCode too: the flag is never substituted, and
    the ``unknown`` marker is reserved for a session whose tree could not be read.
    """
    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        model_name='a-flag-value',
        opencode_db_path=None,
        opencode_session_id=None,
    )

    assert 'model' not in info
    assert 'model_source' not in info


# =============================================================================
# D3 — the harness carries the tier that produced it, and a mismatch is reported
# =============================================================================


def _is_true(value: Any) -> bool:
    """TOON may render a boolean as ``true`` or as the string; accept either."""
    return value is True or value == 'true'


def test_harness_source_env_with_a_configured_mismatch(tmp_path: Path) -> None:
    """An env signal outranking a differently-configured local target is reported."""
    project = _fixture_project(tmp_path)
    _write_local_harness(project, 'claude')
    env = _clean_platform_env()
    env['OPENCODE'] = '1'

    result = run_script(_PLATFORM_SCRIPT, 'runtime-info', cwd=project, env_overrides=env)

    assert result.returncode == 0, result.stderr
    parsed = _parse(result.stdout)
    assert parsed['harness'] == 'opencode'
    assert parsed['harness_source'] == 'env'
    assert _is_true(parsed.get('harness_mismatch'))
    assert parsed['harness_configured'] == 'claude'


def test_harness_source_fallback_names_its_reason(tmp_path: Path) -> None:
    """With no signal at all the tier is fallback and its reason is carried."""
    project = _fixture_project(tmp_path)

    result = run_script(_PLATFORM_SCRIPT, 'runtime-info', cwd=project, env_overrides=_clean_platform_env())

    assert result.returncode == 0, result.stderr
    parsed = _parse(result.stdout)
    assert parsed['harness_source'] == 'fallback'
    assert parsed['reason'] == 'local_config_absent'
    assert 'harness_mismatch' not in parsed
