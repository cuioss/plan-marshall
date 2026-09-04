#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Acceptance: the init preflight is ONE call over disabled | ready | down+reason.

An unregistered project returns `disabled` with NO daemon round-trip; a
registered project completes a verified handshake and returns `ready` or `down`
+ a named reason. One deterministic call the init workflow only branches on.
"""

from __future__ import annotations

import argparse
import copy
from typing import Any

import pytest
from _build_server_registry import canonicalize_root, register_project

from conftest import load_script_module, parse_ns

_BUNDLE = 'plan-marshall'
_SKILL = 'build-server-client'
_SCRIPT = 'build_server.py'

#: ``register=False`` because only the returned module is used here. Publishing
#: ``build_server`` into ``sys.modules`` would collide with the sibling modules
#: that import it plainly.
client = load_script_module(_BUNDLE, _SKILL, _SCRIPT, register=False)


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``preflight`` namespace ``build_server.py``'s OWN parser yields, hoisted to
#: module scope because ``parse_ns`` re-executes the script module on every call.
#: ``register=False`` so it never publishes a second ``build_server`` in
#: ``sys.modules`` alongside the one the loader published above.
_PREFLIGHT_ARGS = parse_ns(_BUNDLE, _SKILL, _SCRIPT, 'preflight', register=False)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def test_preflight_disabled_makes_no_daemon_round_trip(home, monkeypatch):
    def _fail(_sock_path):
        raise AssertionError('an unregistered project must never handshake the daemon')

    monkeypatch.setattr(client, '_handshake', _fail)

    result = client.run_preflight(
        _variant(_PREFLIGHT_ARGS, project_path=str(home / 'unregistered'))
    )

    assert result['preflight'] == 'disabled'
    assert result['registered'] is False


def test_preflight_ready_on_a_verified_handshake(home, monkeypatch):
    root = canonicalize_root(home / 'proj')
    register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))

    result = client.run_preflight(_variant(_PREFLIGHT_ARGS, project_path=root))

    assert result['preflight'] == 'ready'
    assert result['registered'] is True
    assert result['version'] == '1'


def test_preflight_down_carries_a_named_reason(home, monkeypatch):
    root = canonicalize_root(home / 'proj')
    register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_SOCKET_ABSENT))

    result = client.run_preflight(_variant(_PREFLIGHT_ARGS, project_path=root))

    assert result['preflight'] == 'down'
    assert result['registered'] is True
    assert result['reason'] == client.REASON_SOCKET_ABSENT
