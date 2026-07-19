#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for manage_build_server — the operator control surface.

Drive the control verbs directly by inserting the manage-build-server scripts dir
on sys.path. Every test isolates the machine-global home root by pointing
``PLAN_MARSHALL_HOME`` at a per-test ``tmp_path`` so no test touches the real
``~/.plan-marshall/`` tree. The OS seams (``_spawn_detached`` / ``_signal`` /
``_ping``) are monkeypatched so no real daemon is launched, no real signal is
sent, and no real socket is opened.
"""

from __future__ import annotations

import json
import signal
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'manage_build_server.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_server_registry as registry  # noqa: E402
import manage_build_server as mbs  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def _audit_lines() -> list[dict]:
    path = registry.audit_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def _lifecycle_lines() -> list[dict]:
    path = mbs.marshalld.daemon_dir() / mbs._LIFECYCLE_AUDIT_FILENAME
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


# =============================================================================
# register / unregister
# =============================================================================


def test_register_round_trip_and_audit(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_register(
        Namespace(root=str(root), container=[str(home / 'wts')], notation=['a:b:c'])
    )

    assert result['status'] == 'success'
    assert result['action'] == 'register'
    assert result['canonical_root'] == registry.canonicalize_root(root)
    assert result['notation_allowlist'] == ['a:b:c']
    # Persisted to the machine-global registry.
    stored = registry.read_registry()['projects']
    assert result['canonical_root'] in stored
    # Registration appended exactly one audit line.
    lines = _audit_lines()
    assert len(lines) == 1
    assert lines[0]['action'] == registry.ACTION_REGISTER


def test_register_no_flags_populates_default_scope(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_register(Namespace(root=str(root), container=None, notation=None))

    # Omitting --container / --notation now backfills canonical defaults rather
    # than storing empty scope (which left a registered project inert). Full
    # default-population / backfill coverage lives in test_register_defaults.py.
    assert result['notation_allowlist']
    assert result['worktree_containers'] == [
        str(Path(result['canonical_root']) / '.plan' / 'local' / 'worktrees')
    ]


def test_unregister_round_trip_and_audit(home):
    root = home / 'proj'
    root.mkdir()
    mbs.run_register(Namespace(root=str(root), container=None, notation=None))

    result = mbs.run_unregister(Namespace(root=str(root)))

    assert result['status'] == 'success'
    assert result['removed'] is True
    assert registry.read_registry()['projects'] == {}
    actions = [entry['action'] for entry in _audit_lines()]
    assert actions == [registry.ACTION_REGISTER, registry.ACTION_UNREGISTER]


def test_unregister_absent_is_idempotent_noop(home):
    root = home / 'never'

    result = mbs.run_unregister(Namespace(root=str(root)))

    assert result['status'] == 'success'
    assert result['removed'] is False
    assert _audit_lines() == []


# =============================================================================
# start / install — version pinning + audit
# =============================================================================


def test_start_pins_version_and_writes_audit(home, monkeypatch):
    spawned: list[list[str]] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: spawned.append(command))

    result = mbs.run_start(Namespace())

    assert result['running'] is True
    assert result['already_running'] is False
    assert result['version'] == mbs.marshalld.VERSION
    # The pinned binary path is the marshalld copy co-located with this skill.
    expected_binary = str(Path(mbs.marshalld.__file__).resolve())
    assert result['binary_path'] == expected_binary
    # The spawned command launches that exact pinned binary.
    assert spawned and spawned[0][1] == expected_binary
    # Exactly one lifecycle audit line records the start with version + binary.
    lines = _lifecycle_lines()
    assert len(lines) == 1
    assert lines[0]['action'] == 'start'
    assert lines[0]['binary_path'] == expected_binary
    assert lines[0]['version'] == mbs.marshalld.VERSION


def test_start_refuses_second_daemon(home, monkeypatch):
    spawned: list[list[str]] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 4321)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: spawned.append(command))

    result = mbs.run_start(Namespace())

    assert result['already_running'] is True
    assert result['pid'] == 4321
    # No spawn, no audit — an already-running daemon is a no-op.
    assert spawned == []
    assert _lifecycle_lines() == []


def test_install_is_idempotent_when_running(home, monkeypatch):
    monkeypatch.setattr(mbs, '_running_pid', lambda: 99)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: None)

    result = mbs.run_install(Namespace())

    assert result['action'] == 'install'
    assert result['already_running'] is True


# =============================================================================
# stop — forced kill escalation
# =============================================================================


def test_stop_sigterm_then_cleanup_when_graceful(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 555)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)

    result = mbs.run_stop(Namespace())

    assert result['was_running'] is True
    assert result['forced'] is False
    # Only SIGTERM — no SIGKILL escalation when it exited gracefully.
    assert sent == [signal.SIGTERM]
    assert _lifecycle_lines()[-1]['action'] == 'stop'


def test_stop_escalates_to_sigkill_when_wedged(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 555)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: False)

    result = mbs.run_stop(Namespace())

    assert result['forced'] is True
    assert sent == [signal.SIGTERM, signal.SIGKILL]


def test_stop_absent_daemon_is_noop(home, monkeypatch):
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_stop(Namespace())

    assert result['was_running'] is False
    assert _lifecycle_lines() == []


# =============================================================================
# drain — graceful, never SIGKILL
# =============================================================================


def test_drain_sigterm_only_and_audits(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 777)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)

    result = mbs.run_drain(Namespace())

    assert result['was_running'] is True
    assert result['exited'] is True
    # Graceful: SIGTERM only — drain NEVER escalates to SIGKILL.
    assert sent == [signal.SIGTERM]
    assert signal.SIGKILL not in sent
    assert _lifecycle_lines()[-1]['action'] == 'drain'


def test_drain_reports_non_exit_without_sigkill(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 777)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: False)

    result = mbs.run_drain(Namespace())

    # Even when the daemon does not exit in the grace window, drain does not kill.
    assert result['exited'] is False
    assert sent == [signal.SIGTERM]


# =============================================================================
# upgrade — drain then start
# =============================================================================


def test_upgrade_drains_then_starts(home, monkeypatch):
    calls: list[str] = []

    def fake_pid() -> int | None:
        # Running before drain, down after (so start proceeds).
        return 888 if not calls else None

    monkeypatch.setattr(mbs, '_running_pid', fake_pid)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: calls.append('signal'))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: calls.append('spawn'))

    result = mbs.run_upgrade(Namespace())

    assert result['action'] == 'upgrade'
    assert result['drained'] is True
    assert result['running'] is True
    # Drain (signal) happened before the start (spawn).
    assert calls.index('signal') < calls.index('spawn')


# =============================================================================
# status — running / down, version + binary path
# =============================================================================


def test_status_running_reports_version_and_binary(home, monkeypatch):
    monkeypatch.setattr(
        mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: {
            'status': 'ok',
            'pid': 4242,
            'version': mbs.marshalld.VERSION,
        }
    )

    result = mbs.run_status(Namespace())

    assert result['running'] is True
    assert result['version'] == mbs.marshalld.VERSION
    assert result['pid'] == 4242
    assert result['binary_path'] == str(Path(mbs.marshalld.__file__).resolve())
    assert result['socket_path'] == str(mbs.marshalld.socket_path())


def test_status_down_reports_reason(home, monkeypatch):
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_status(Namespace())

    assert result['running'] is False
    assert result['reason'] == 'no_pidfile'


def test_status_down_unreachable_when_pid_present(home, monkeypatch):
    # A recorded live pid but a socket that does not answer → unreachable.
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: 1234)

    result = mbs.run_status(Namespace())

    assert result['running'] is False
    assert result['reason'] == 'unreachable'


def test_status_reports_registration(home, monkeypatch):
    # Register the caller's main checkout, then assert status sees it registered.
    caller_root = mbs.canonicalize_root(mbs.main_checkout_root())
    registry.register_project(caller_root)
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_status(Namespace())

    assert result['registered'] is True
