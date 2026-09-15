#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-orchestrator pre-flight hook writing client.toon.

Covers hook invocation, the artifact write path, and best-effort
degradation where a collector failure never blocks plan start.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from toon_parser import parse_toon

from conftest import load_script_module

_orch = load_script_module('plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script')

cmd_preflight = _orch.cmd_preflight


def _ns(plan_id: str) -> argparse.Namespace:
    """Build the argparse namespace the preflight handler receives."""
    return argparse.Namespace(plan_id=plan_id)


def test_preflight_writes_client_toon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook writes the runtime-info payload as client.toon."""
    monkeypatch.setattr(_orch, 'get_store_dir', lambda store, plan_id: tmp_path / plan_id)
    result: dict[str, Any] = cmd_preflight(_ns('my-plan'))
    assert result['status'] == 'success'
    assert result['artifact_written'] is True
    artifact = tmp_path / 'my-plan' / 'client.toon'
    assert artifact.is_file()
    assert 'harness:' in artifact.read_text(encoding='utf-8')


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
