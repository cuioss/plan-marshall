#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: daemon-down / unregistered → in-process fallback with a recorded reason.

When preflight is not `ready`, the build-execute routing seam does NOT submit —
it signals the in-process fallback and names the degradation reason so the
fallback is never silent. A build takes exactly one limiter path.
"""

from __future__ import annotations

import pytest
from _build_extension_fixtures import build_scripts_dir, execute_config

build_scripts_dir()

import _build_execute_factory as factory  # noqa: E402
from _build_execute import CaptureStrategy  # noqa: E402


def _config(**overrides):
    return execute_config(factory, CaptureStrategy.TOOL_LOG_FLAG, **overrides)


class _FakeClient:
    def __init__(self, preflight):
        self._preflight = preflight
        self.submit_calls = []

    def run_preflight(self, _args):
        return self._preflight

    def run_submit(self, args):
        self.submit_calls.append(args)
        raise AssertionError('a not-ready project must never submit')


@pytest.fixture(autouse=True)
def _no_reentrancy(monkeypatch):
    monkeypatch.delenv('MARSHALLD_JOB', raising=False)


def test_unregistered_falls_back_and_names_reason(monkeypatch):
    client = _FakeClient({'status': 'success', 'preflight': 'disabled'})
    monkeypatch.setattr(factory, '_load_build_server', lambda: client)

    routed, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert routed is None  # no daemon route ⇒ in-process fallback
    assert reason == 'disabled'  # the recorded degradation reason
    assert client.submit_calls == []


def test_daemon_down_falls_back_and_names_reason(monkeypatch):
    client = _FakeClient({'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'})
    monkeypatch.setattr(factory, '_load_build_server', lambda: client)

    routed, reason = factory._route_to_daemon(_config(), '/tree', 'plan-x')

    assert routed is None
    assert reason == 'socket_absent'
    assert client.submit_calls == []
