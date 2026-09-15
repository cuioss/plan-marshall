#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-orchestrator pre-flight hook writing client.toon.

Covers hook invocation, the artifact write path, and best-effort
degradation where a collector failure never blocks plan start.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

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


def test_preflight_failure_degrades_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_preflight_verb_is_registered() -> None:
    """The orchestrator parser exposes the preflight verb."""
    parser = _orch._build_arg_parser()
    ns = parser.parse_args(['preflight', '--plan-id', 'my-plan'])
    assert ns.handler is cmd_preflight
