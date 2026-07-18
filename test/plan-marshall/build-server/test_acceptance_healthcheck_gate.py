#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: a self-resolvable health condition does NOT block the start path.

A stale socket (its recorded owner is dead) is self-resolvable: the start path
cleans it and proceeds, and the daemon's socket takeover unlinks it rather than
refusing. A genuinely live daemon is NOT self-resolvable and blocks. The status
gate names its reason so the operator sees WHY the daemon is unreachable.
"""

from __future__ import annotations

import sys
from argparse import Namespace

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
if str(_DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(_DAEMON_DIR))

import manage_build_server as control  # noqa: E402
import marshalld  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def test_stale_socket_is_self_resolved_by_takeover(home):
    marshalld.ensure_daemon_dir()
    sock = marshalld.socket_path()
    sock.write_text('')  # a leftover socket file
    marshalld.write_pid(marshalld.pidfile_path(), 999_999_999)  # a dead owner

    # A stale socket (dead owner) is self-resolvable: takeover unlinks it and
    # does NOT refuse — the start path is not blocked.
    marshalld.stale_socket_takeover(sock, marshalld.pidfile_path())

    assert not sock.exists()


def test_live_daemon_is_not_self_resolvable_and_blocks(home):
    marshalld.ensure_daemon_dir()
    sock = marshalld.socket_path()
    sock.write_text('')
    marshalld.write_pid(marshalld.pidfile_path(), marshalld.os.getpid())  # a LIVE owner

    with pytest.raises(marshalld.DaemonAlreadyRunning):
        marshalld.stale_socket_takeover(sock, marshalld.pidfile_path())


def test_start_proceeds_past_a_stale_socket(home, monkeypatch):
    marshalld.ensure_daemon_dir()
    sock = marshalld.socket_path()
    sock.write_text('')
    marshalld.write_pid(marshalld.pidfile_path(), 999_999_999)  # stale

    monkeypatch.setattr(control, '_running_pid', lambda: None)  # nothing live
    monkeypatch.setattr(control, '_spawn_detached', lambda *a, **k: None)  # do not actually launch
    monkeypatch.setattr(control, '_append_lifecycle_audit', lambda *a, **k: None)

    result = control._start_daemon()

    assert result['status'] == 'success'
    assert result['already_running'] is False  # a stale socket did not block the start
    assert not sock.exists()  # the self-resolvable condition was cleaned


def test_status_gate_names_its_reason_when_down(home, monkeypatch):
    monkeypatch.setattr(control, '_ping', lambda *a, **k: None)
    monkeypatch.setattr(control, '_running_pid', lambda: None)

    result = control.run_status(Namespace())

    assert result['running'] is False
    assert result['reason'] == 'no_pidfile'  # the gate names WHY it is down
