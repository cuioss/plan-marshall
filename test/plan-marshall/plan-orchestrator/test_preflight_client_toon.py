#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-orchestrator pre-flight hook writing client.toon.

Covers hook invocation, the artifact write path, and best-effort
degradation where a collector failure never blocks plan start.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import platform_runtime
import pytest
import runtime_info
from runtime_base import toon_success
from toon_parser import parse_toon

from conftest import load_script_module

_orch = load_script_module('plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script')

cmd_preflight = _orch.cmd_preflight


def _ns(plan_id: str, model: str | None = None, effort: str | None = None) -> argparse.Namespace:
    """Build the argparse namespace the preflight handler receives."""
    return argparse.Namespace(plan_id=plan_id, model=model, effort=effort)


def test_preflight_writes_client_toon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook writes the runtime-info payload as client.toon."""
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    _runtime_info_fake(
        ['status: success\noperation: runtime-info\nharness: claude\n'],
        monkeypatch,
    )
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['status'] == 'success'
    assert result['artifact_written'] is True
    artifact = tmp_path / 'my-plan' / 'client.toon'
    assert artifact.is_file()
    assert 'harness:' in artifact.read_text(encoding='utf-8')


def test_preflight_carries_persisted_approval_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(c) The plan-start call carries the stale-approval report in its result."""
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    _runtime_info_fake(['status: success\noperation: runtime-info\nharness: opencode\n'], monkeypatch)
    report = {
        'checkable': True,
        'persisted_allow_count': 1,
        'contradictions': [{'pattern': 'ls', 'deny_pattern': 'ls *'}],
    }
    monkeypatch.setattr(_orch, '_persisted_approval_report', lambda: report)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))

    assert result['status'] == 'success'
    assert result['artifact_written'] is True
    assert result['persisted_approval'] == report


def test_preflight_failure_degrades_without_blocking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A collector failure degrades to success with no artifact."""
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError('collector down')

    monkeypatch.setattr(_orch.subprocess, 'run', _boom)
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['status'] == 'success'
    assert result['degraded'] is True
    assert result['artifact_written'] is False
    assert not (tmp_path / 'my-plan' / 'client.toon').exists()


def test_preflight_rejects_invalid_plan_id_without_error(tmp_path: Path) -> None:
    """An invalid plan id degrades rather than returning an error."""
    result: dict[str, Any] = cmd_preflight(_ns('not a plan id!'))
    assert result['status'] == 'success'
    assert result['degraded'] is True
    assert result['artifact_written'] is False


def _runtime_info_fake(payloads: list[str], monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Fake subprocess.run for the runtime-info call only.

    The hook also shells to the title-settling entry point; those calls pass
    through to the real runner so they never consume a queued payload.
    """
    real_run = _orch.subprocess.run
    calls = {'count': 0}

    def _fake_run(*args: Any, **kwargs: Any) -> Any:
        cmd = [str(part) for part in (args[0] if args else [])]
        # Exact argv-token match: a substring test misfires when the
        # interpreter path carries the plan slug (which itself contains
        # 'runtime-info'), swallowing the title-settling call's payload slot.
        if 'runtime-info' not in cmd:
            return real_run(*args, **kwargs)
        payload = payloads[min(calls['count'], len(payloads) - 1)]
        calls['count'] += 1
        return SimpleNamespace(returncode=0, stdout=payload)

    monkeypatch.setattr(_orch.subprocess, 'run', _fake_run)
    return calls


def test_preflight_appends_second_run_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second hook run appends its entry while the first entry survives."""
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    _runtime_info_fake(
        [
            'status: success\noperation: runtime-info\nharness: claude\n',
            'status: success\noperation: runtime-info\nharness: opencode\n',
        ],
        monkeypatch,
    )
    first: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    second: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert first['artifact_written'] is True
    assert second['artifact_written'] is True
    text = (tmp_path / 'my-plan' / 'client.toon').read_text(encoding='utf-8')
    doc = parse_toon(text)
    assert len(doc['entries']) == 2
    assert sorted(entry['harness'] for entry in doc['entries'].values()) == ['claude', 'opencode']


def test_preflight_migrates_legacy_flat_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pre-timestamp flat artifact survives under the legacy entry key."""
    plan_dir = tmp_path / 'my-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'client.toon').write_text('schema_version: 1\nharness: claude\n', encoding='utf-8')
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    _runtime_info_fake(
        ['status: success\noperation: runtime-info\nharness: opencode\n'],
        monkeypatch,
    )
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['artifact_written'] is True
    doc = parse_toon((plan_dir / 'client.toon').read_text(encoding='utf-8'))
    assert doc['entries']['legacy'] == {'harness': 'claude'}
    assert any(entry.get('harness') == 'opencode' for entry in doc['entries'].values())


def test_preflight_verb_is_registered() -> None:
    """The orchestrator parser exposes the preflight verb."""
    parser = _orch._build_arg_parser()
    ns = parser.parse_args(['preflight', '--plan-id', 'my-plan'])
    assert ns.handler is cmd_preflight


def test_preflight_verb_accepts_model_and_effort() -> None:
    """The documented call exposes the LLM's self-report flags."""
    parser = _orch._build_arg_parser()
    ns = parser.parse_args(['preflight', '--plan-id', 'my-plan', '--model', 'm', '--effort', 'high'])
    assert ns.model == 'm'
    assert ns.effort == 'high'


def test_preflight_degrades_without_overwriting_unparseable_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing-but-unparseable artifact degrades instead of being replaced."""
    plan_dir = tmp_path / 'my-plan'
    plan_dir.mkdir(parents=True)
    before = 'schema_version: 1\nentries: [not, a, mapping]\n'
    (plan_dir / 'client.toon').write_text(before, encoding='utf-8')
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    real_parse = _orch.parse_toon

    def _fail_on_existing(text: str) -> Any:
        if 'not, a, mapping' in text:
            raise ValueError('unparseable artifact')
        return real_parse(text)

    monkeypatch.setattr(_orch, 'parse_toon', _fail_on_existing)
    _runtime_info_fake(
        ['status: success\noperation: runtime-info\nharness: claude\n'],
        monkeypatch,
    )
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['status'] == 'success'
    assert result['degraded'] is True
    assert result['artifact_written'] is False
    assert (plan_dir / 'client.toon').read_text(encoding='utf-8') == before


def test_preflight_degrades_without_overwriting_wrong_shaped_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An entries-present-but-not-mapping artifact is preserved, not migrated."""
    plan_dir = tmp_path / 'my-plan'
    plan_dir.mkdir(parents=True)
    before = 'schema_version: 1\nentries: [not, a, mapping]\n'
    (plan_dir / 'client.toon').write_text(before, encoding='utf-8')
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    _runtime_info_fake(
        ['status: success\noperation: runtime-info\nharness: claude\n'],
        monkeypatch,
    )
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['status'] == 'success'
    assert result['degraded'] is True
    assert result['artifact_written'] is False
    assert (plan_dir / 'client.toon').read_text(encoding='utf-8') == before


# =============================================================================
# D2 — the stamp is refreshed at landing time
# =============================================================================


def _refresh_ns(plan_id: str) -> argparse.Namespace:
    return argparse.Namespace(plan_id=plan_id)


def _preflight_opencode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db_path: Path, rows: list[tuple[str, str | None, str]]
) -> Path:
    """Run a real OpenCode preflight over a fixture session tree, returning the plan dir."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.chdir(_router_project(tmp_path))
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    _write_session_db(db_path, rows)
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _runtime_info_via_router(monkeypatch)
    assert cmd_preflight(_ns('my-plan'))['metadata_stamped'] is True
    return plan_dir


def test_refresh_stamps_a_mixed_tree_after_a_model_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A session that gained a second model after plan start refresh to ``mixed``."""
    db_path = tmp_path / 'opencode.db'
    plan_dir = _preflight_opencode(
        tmp_path, monkeypatch, db_path, [('ses-root', None, _opencode_model_json('deepseek-v4.1-flash', 'high'))]
    )
    assert _status_metadata(plan_dir)['model'] == 'deepseek-v4.1-flash'

    _write_session_db(
        db_path,
        [
            ('ses-root', None, _opencode_model_json('deepseek-v4.1-flash', 'high')),
            ('ses-child', 'ses-root', _opencode_model_json('gpt-5', 'low')),
        ],
    )

    result = _orch.cmd_refresh_runtime_stamp(_refresh_ns('my-plan'))

    assert result['status'] == 'success'
    assert result['refreshed'] is True
    metadata = _status_metadata(plan_dir)
    assert metadata['model'] == 'mixed'
    assert 'deepseek-v4.1-flash/high' in metadata['models']
    assert 'gpt-5/low' in metadata['models']
    assert 'variant' not in metadata


def test_refresh_keeps_the_start_value_when_the_database_is_unreachable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A landing-time read that cannot reach the database marks the value start-time."""
    db_path = tmp_path / 'opencode.db'
    plan_dir = _preflight_opencode(
        tmp_path, monkeypatch, db_path, [('ses-root', None, _opencode_model_json('deepseek-v4.1-flash', 'high'))]
    )
    db_path.unlink()

    result = _orch.cmd_refresh_runtime_stamp(_refresh_ns('my-plan'))

    assert result['status'] == 'success'
    assert result['refreshed'] is False
    metadata = _status_metadata(plan_dir)
    assert metadata['model'] == 'deepseek-v4.1-flash'
    assert metadata['variant'] == 'high'
    assert metadata['model_source'] == 'measured_at_start'
    assert metadata['effort'] == 'high'
    assert metadata['effort_source'] == 'measured_at_start'


def test_refresh_over_an_unchanged_tree_keeps_the_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A tree unchanged since the start refreshes to the same measured value."""
    db_path = tmp_path / 'opencode.db'
    plan_dir = _preflight_opencode(
        tmp_path, monkeypatch, db_path, [('ses-root', None, _opencode_model_json('deepseek-v4.1-flash', 'high'))]
    )

    result = _orch.cmd_refresh_runtime_stamp(_refresh_ns('my-plan'))

    assert result['refreshed'] is True
    metadata = _status_metadata(plan_dir)
    assert metadata['model'] == 'deepseek-v4.1-flash'
    assert metadata['variant'] == 'high'
    assert metadata['model_source'] == 'measured'


# =============================================================================
# D3 — a failed preflight leaves no stale stamp, and a failed stamp is visible
# =============================================================================


def test_failed_collector_clears_a_previous_runtime_stamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A collector failure leaves the runtime keys absent, not the earlier run's values."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)
    assert cmd_preflight(_ns('my-plan', model='claude-opus-5-5', effort='high'))['metadata_stamped'] is True
    assert _status_metadata(plan_dir)['model'] == 'claude-opus-5-5'

    def _failed(*args: Any, **kwargs: Any) -> Any:
        cmd = [str(part) for part in (args[0] if args else [])]
        if 'runtime-info' in cmd:
            return SimpleNamespace(returncode=1, stdout='')
        return _orch.subprocess.run(*args, **kwargs)

    monkeypatch.setattr(_orch.subprocess, 'run', _failed)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))

    assert result['degraded'] is True
    metadata = _status_metadata(plan_dir)
    for key in ('harness', 'harness_source', 'model', 'models', 'variant', 'provider', 'model_source'):
        assert key not in metadata, key


def test_unstamped_metadata_without_degradation_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``metadata_stamped: false`` is visible even when nothing degraded."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / 'plans' / plan_id)
    _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', model='claude-opus-5-5'))

    assert result['degraded'] is False
    assert result['metadata_stamped'] is False


def test_opencode_without_a_session_reports_the_omission_reason() -> None:
    """No session id is reported as a reason, not a silent omission."""
    info = runtime_info.collect_runtime_info(
        'opencode',
        env={},
        opencode_db_path=None,
        opencode_session_id=None,
    )

    assert 'model' not in info
    assert info['model_omission_reason'] == runtime_info.OMISSION_NO_SESSION_ID


# =============================================================================
# D4 — the database reader is robust, and the tests that guard the stamp can fail
# =============================================================================


#: A runtime-info payload shaped as the collector emits it for a
#: self-reported call: every version and the source tags present.
_SELF_REPORTED_PAYLOAD = (
    'status: success\n'
    'operation: runtime-info\n'
    'harness: claude\n'
    'harness_source: fallback\n'
    'transcripts: full\n'
    'model: claude-opus-5-5\n'
    'model_source: self_reported\n'
    'effort: high\n'
    'effort_source: self_reported\n'
    'bundle_version: 0.1.1919\n'
    'executor_version: 0.1.1916\n'
)

#: A payload with no model/effort at all — the flagless call.
_BARE_PAYLOAD = (
    'status: success\n'
    'operation: runtime-info\n'
    'harness: opencode\n'
    'harness_source: env\n'
    'transcripts: none\n'
    'bundle_version: 0.1.1919\n'
)


def _plan_with_status(tmp_path: Path, plan_id: str) -> Path:
    """Create a plan directory holding a status.json, and point the store at it."""
    plan_dir = tmp_path / 'plans' / plan_id
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'harness': 'stale'}}),
        encoding='utf-8',
    )
    return plan_dir


def _capture_runtime_info_argv(payloads: list[str], monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Fake ``subprocess.run`` for the runtime-info call, recording its argv."""
    real_run = _orch.subprocess.run
    seen: list[list[str]] = []
    state = {'count': 0}

    def _fake_run(*args: Any, **kwargs: Any) -> Any:
        cmd = [str(part) for part in (args[0] if args else [])]
        if 'runtime-info' not in cmd:
            return real_run(*args, **kwargs)
        seen.append(cmd)
        payload = payloads[min(state['count'], len(payloads) - 1)]
        state['count'] += 1
        return SimpleNamespace(returncode=0, stdout=payload)

    monkeypatch.setattr(_orch.subprocess, 'run', _fake_run)
    return seen


def _status_metadata(plan_dir: Path) -> dict[str, Any]:
    document = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    return cast('dict[str, Any]', document['metadata'])


# =============================================================================
# D1 — the measured variant, and effort measured where the harness measures it
# =============================================================================


def _router_project(tmp_path: Path) -> Path:
    """A cwd the runtime-info router accepts: a ``.plan/marshal.json``."""
    project = tmp_path / 'project'
    (project / '.plan').mkdir(parents=True)
    (project / '.plan' / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8')
    return project


def _write_session_db(db_path: Path, rows: list[tuple[str, str | None, str]]) -> None:
    """Create a fixture ``session_v2`` table with ``(id, parent_id, model_json)`` rows."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('DROP TABLE IF EXISTS session_v2')
        conn.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT)')
        conn.executemany('INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, ?)', rows)
        conn.commit()
    finally:
        conn.close()


def _opencode_model_json(model_id: str, variant: str) -> str:
    return json.dumps({'id': model_id, 'providerID': 'opencode-go', 'variant': variant})


def _runtime_info_via_router(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Dispatch the preflight's runtime-info argv into the REAL router in-process.

    The argv is the exact list ``cmd_preflight`` built, and the router parses it
    with its own argparse before the collector runs, so a renamed flag, a wrong
    position or a drifted payload key fails here instead of passing a canned
    string through a monkeypatched ``subprocess.run``.
    """
    real_run = _orch.subprocess.run
    seen: list[list[str]] = []

    def _fake_run(*args: Any, **kwargs: Any) -> Any:
        cmd = [str(part) for part in (args[0] if args else [])]
        if 'runtime-info' not in cmd:
            return real_run(*args, **kwargs)
        seen.append(cmd)
        remaining = cmd[3:]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = platform_runtime.main(remaining)
        return SimpleNamespace(returncode=code, stdout=buffer.getvalue())

    monkeypatch.setattr(_orch.subprocess, 'run', _fake_run)
    return seen


def test_preflight_stamps_variant_and_measured_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A single-model OpenCode tree stamps its variant and measures effort from it."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.chdir(_router_project(tmp_path))
    monkeypatch.setenv('OPENCODE', '1')
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    db_path = tmp_path / 'opencode.db'
    _write_session_db(db_path, [('ses-root', None, _opencode_model_json('deepseek-v4.1-flash', 'high'))])
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    seen = _runtime_info_via_router(monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', effort='low'))

    assert seen, 'the preflight built no runtime-info argv'
    assert result['metadata_stamped'] is True
    metadata = _status_metadata(plan_dir)
    assert metadata['model'] == 'deepseek-v4.1-flash'
    assert metadata['variant'] == 'high'
    assert metadata['provider'] == 'opencode-go'
    assert metadata['effort'] == 'high'
    assert metadata['effort_source'] == 'measured'


def test_preflight_forwards_the_self_report_and_stamps_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The documented call records client.toon AND the plan's runtime metadata."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    seen = _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', model='claude-opus-5-5', effort='high'))

    assert result['status'] == 'success'
    assert result['artifact_written'] is True
    # The self-report rides the runtime-info subprocess argv.
    assert seen, 'the runtime-info call was not observed'
    assert '--model' in seen[0] and 'claude-opus-5-5' in seen[0]
    assert '--effort' in seen[0] and 'high' in seen[0]
    assert (plan_dir / 'client.toon').is_file()

    metadata = _status_metadata(plan_dir)
    assert metadata['harness'] == 'claude'
    assert metadata['harness_source'] == 'fallback'
    assert metadata['model'] == 'claude-opus-5-5'
    assert metadata['model_source'] == 'self_reported'
    assert metadata['effort'] == 'high'
    assert metadata['effort_source'] == 'self_reported'
    assert metadata['bundle_version'] == '0.1.1919'
    assert metadata['executor_version'] == '0.1.1916'


def test_preflight_without_flags_still_writes_the_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A flagless call writes the entry with the model and effort keys absent."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _capture_runtime_info_argv([_BARE_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))

    assert result['artifact_written'] is True
    visible = parse_toon((plan_dir / 'client.toon').read_text(encoding='utf-8'))
    assert any(entry.get('harness') == 'opencode' for entry in visible['entries'].values())

    metadata = _status_metadata(plan_dir)
    assert metadata['harness'] == 'opencode'
    assert metadata['harness_source'] == 'env'
    assert metadata['bundle_version'] == '0.1.1919'
    assert 'model' not in metadata
    assert 'effort' not in metadata


def test_preflight_metadata_stamp_is_best_effort_without_a_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plan with no status.json still gets its client.toon, and never blocks."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / 'plans' / plan_id)
    _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', model='claude-opus-5-5'))

    assert result['status'] == 'success'
    assert result['artifact_written'] is True


#: A payload from a MIXED OpenCode session tree: the distinct labels ride
#: ``models`` beside ``model: mixed``.
_MIXED_MODEL_PAYLOAD = (
    'status: success\n'
    'operation: runtime-info\n'
    'harness: opencode\n'
    'harness_source: env\n'
    'transcripts: none\n'
    'model: mixed\n'
    'models: deepseek-v4.1-flash/high, gpt-5/low\n'
    'model_source: measured\n'
    'bundle_version: 0.1.1919\n'
)


def test_preflight_stamps_the_mixed_model_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mixed session tree keeps the distinct labels in the plan metadata."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _capture_runtime_info_argv([_MIXED_MODEL_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))

    assert result['metadata_stamped'] is True
    metadata = _status_metadata(plan_dir)
    assert metadata['model'] == 'mixed'
    assert metadata['models'] == 'deepseek-v4.1-flash/high, gpt-5/low'


def test_preflight_stamps_metadata_even_when_the_artifact_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed client.toon write does not lose the collected attributes."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    before = 'schema_version: 1\nentries: [not, a, mapping]\n'
    (plan_dir / 'client.toon').write_text(before, encoding='utf-8')
    real_parse = _orch.parse_toon

    def _fail_on_existing(text: str) -> Any:
        if 'not, a, mapping' in text:
            raise ValueError('unparseable artifact')
        return real_parse(text)

    monkeypatch.setattr(_orch, 'parse_toon', _fail_on_existing)
    _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', model='claude-opus-5-5', effort='high'))

    assert result['degraded'] is True
    assert result['artifact_written'] is False
    assert result['metadata_stamped'] is True
    assert _status_metadata(plan_dir)['model'] == 'claude-opus-5-5'


def _real_collector_payload(tmp_path: Path) -> str:
    """A runtime-info payload produced by the REAL collector, not a fixture string.

    The metadata stamp reads keys the collector emits; building the payload here
    from :func:`runtime_info.collect_runtime_info` is what proves the two ends
    agree, rather than asserting against a hand-written block that could carry
    keys the collector never produces.
    """
    bundle = tmp_path / 'bundle'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(json.dumps({'version': '0.1.1919'}), encoding='utf-8')
    executor = tmp_path / 'execute-script.py'
    executor.write_text("MARSHALL_VERSION = '0.1.1916'\n", encoding='utf-8')
    info = runtime_info.collect_runtime_info(
        'claude',
        env={},
        bundle_root=bundle,
        executor_path=executor,
        model_name='claude-opus-5-5',
        effort='high',
        harness_attribution={'harness': 'claude', 'harness_source': 'env'},
    )
    return toon_success(runtime_info.RUNTIME_INFO_OPERATION, info)


def test_preflight_clears_a_stale_runtime_stamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A later unreadable field does NOT keep the earlier run's value."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _capture_runtime_info_argv([_SELF_REPORTED_PAYLOAD], monkeypatch)

    assert cmd_preflight(_ns('my-plan', model='claude-opus-5-5', effort='high'))['metadata_stamped'] is True
    assert _status_metadata(plan_dir)['model'] == 'claude-opus-5-5'

    _capture_runtime_info_argv([_BARE_PAYLOAD], monkeypatch)

    assert cmd_preflight(_ns('my-plan'))['metadata_stamped'] is True
    metadata = _status_metadata(plan_dir)
    assert 'model' not in metadata
    assert 'effort' not in metadata
    assert metadata['harness'] == 'opencode'


def test_preflight_stamps_the_real_collector_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The collector's own output is what the plan metadata ends up carrying."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = _plan_with_status(tmp_path, 'my-plan')
    _capture_runtime_info_argv([_real_collector_payload(tmp_path)], monkeypatch)

    result: dict[str, Any] = cmd_preflight(_ns('my-plan', model='claude-opus-5-5', effort='high'))

    assert result['metadata_stamped'] is True
    metadata = _status_metadata(plan_dir)
    assert metadata['harness'] == 'claude'
    assert metadata['harness_source'] == 'env'
    assert metadata['model'] == 'claude-opus-5-5'
    assert metadata['model_source'] == 'self_reported'
    assert metadata['effort'] == 'high'
    assert metadata['effort_source'] == 'self_reported'
    assert metadata['bundle_version'] == '0.1.1919'
    assert metadata['executor_version'] == '0.1.1916'
