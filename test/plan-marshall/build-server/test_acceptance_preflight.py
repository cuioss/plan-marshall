#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: the init preflight is ONE call over disabled | ready | down+reason.

An unregistered project returns `disabled` with NO daemon round-trip; a
registered project completes a verified handshake and returns `ready` or `down`
+ a named reason. One deterministic call the init workflow only branches on.
"""

from __future__ import annotations

import sys
from argparse import Namespace

import pytest
from conftest import get_script_path

_CLIENT_DIR = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
if str(_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CLIENT_DIR))

import build_server as client  # noqa: E402
from _build_server_registry import canonicalize_root, register_project  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def test_preflight_disabled_makes_no_daemon_round_trip(home, monkeypatch):
    def _fail(_sock_path):
        raise AssertionError('an unregistered project must never handshake the daemon')

    monkeypatch.setattr(client, '_handshake', _fail)

    result = client.run_preflight(Namespace(project_path=str(home / 'unregistered')))

    assert result['preflight'] == 'disabled'
    assert result['registered'] is False


def test_preflight_ready_on_a_verified_handshake(home, monkeypatch):
    root = canonicalize_root(home / 'proj')
    register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))

    result = client.run_preflight(Namespace(project_path=root))

    assert result['preflight'] == 'ready'
    assert result['registered'] is True
    assert result['version'] == '1'


def test_preflight_down_carries_a_named_reason(home, monkeypatch):
    root = canonicalize_root(home / 'proj')
    register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_SOCKET_ABSENT))

    result = client.run_preflight(Namespace(project_path=root))

    assert result['preflight'] == 'down'
    assert result['registered'] is True
    assert result['reason'] == client.REASON_SOCKET_ABSENT
