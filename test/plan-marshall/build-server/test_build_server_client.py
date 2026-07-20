#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for build_server — the marshalld build-server consumption client.

Drive the client verbs directly by inserting the build-server-client scripts dir
on sys.path. The daemon-facing seams (``_handshake`` — the S3 owner + version
check, ``_call_daemon`` — the socket round-trip) are monkeypatched so no real
socket is opened and no daemon is required. The change-ledger is isolated by
pointing ``_ledger_core.resolve_ledger_path`` at a per-test ``tmp_path`` so no
test touches the real ledger, and ``PLAN_MARSHALL_HOME`` isolates the registry.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'build-server-client', 'build_server.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
_LOGGING_SCRIPTS_DIR = get_script_path('plan-marshall', 'manage-logging', 'plan_logging.py').parent

for _dir in (SCRIPTS_DIR, _LOGGING_SCRIPTS_DIR):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import _build_server_registry as registry  # noqa: E402
import _ledger_core as ledger_core  # noqa: E402
import build_server as client  # noqa: E402
import plan_logging  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


@pytest.fixture
def ledger(tmp_path, monkeypatch) -> Path:
    """Isolate the change-ledger at a per-test path (never the real ledger)."""
    ledger_path = Path(tmp_path) / 'change-ledger.jsonl'
    monkeypatch.setattr(ledger_core, 'resolve_ledger_path', lambda: ledger_path)
    # compute_worktree_sha would shell out to git; stub it deterministically.
    monkeypatch.setattr(client, 'compute_worktree_sha', lambda _path: 'test-sha')
    return ledger_path


@pytest.fixture
def captured_logs(monkeypatch) -> list[tuple[str, str, str, str]]:
    """Capture every ``plan_logging.log_entry`` call the client makes.

    ``build_server`` imported ``log_entry`` into its own namespace, so patching
    ``client.log_entry`` intercepts the ``_audit_log`` seam without opening any
    real log file. Each captured tuple is ``(log_type, plan_id, level, message)``.
    """
    calls: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        client,
        'log_entry',
        lambda log_type, plan_id, level, message: calls.append((log_type, plan_id, level, message)),
    )
    return calls


def _job_rows() -> list[dict]:
    return [e for e in ledger_core.read_entries() if e.get('kind') == ledger_core.KIND_JOB]


# =============================================================================
# preflight — the three-way F2 contract
# =============================================================================


def test_preflight_disabled_does_no_daemon_round_trip(home, monkeypatch):
    # An unregistered project must NEVER touch the socket.
    def _fail_handshake(_sock_path):
        raise AssertionError('preflight must not handshake an unregistered project')

    monkeypatch.setattr(client, '_handshake', _fail_handshake)

    result = client.run_preflight(Namespace(project_path=str(home / 'proj')))

    assert result['status'] == 'success'
    assert result['preflight'] == 'disabled'
    assert result['registered'] is False


def test_preflight_ready_when_registered_and_daemon_answers(home, monkeypatch):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1', 'pid': 42}, None))

    result = client.run_preflight(Namespace(project_path=str(root)))

    assert result['preflight'] == 'ready'
    assert result['registered'] is True
    assert result['version'] == '1'


def test_preflight_down_carries_named_reason(home, monkeypatch):
    root = home / 'proj'
    root.mkdir()
    registry.register_project(root)
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_UNREACHABLE))

    result = client.run_preflight(Namespace(project_path=str(root)))

    assert result['preflight'] == 'down'
    assert result['reason'] == client.REASON_UNREACHABLE


# =============================================================================
# submit — handshake, ledger write, refuse, fallback
# =============================================================================


def _submit_args(project_path: str, plan_id: str = 'p1') -> Namespace:
    command = f'["python3", "{project_path}/.plan/execute-script.py", "a:b:c", "run"]'
    return Namespace(
        command=command,
        exec_path=project_path,
        project_path=project_path,
        plan_id=plan_id,
    )


def test_submit_success_writes_job_id_to_ledger(home, ledger, monkeypatch):
    root = str(home / 'proj')
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'JOB-1', 'attached': False},
    )

    result = client.run_submit(_submit_args(root))

    assert result['status'] == 'success'
    assert result['job_id'] == 'JOB-1'
    rows = _job_rows()
    assert len(rows) == 1
    assert rows[0]['job_id'] == 'JOB-1'
    assert rows[0]['plan_id'] == 'p1'
    assert rows[0]['notation'] == 'a:b:c'


def test_submit_degraded_on_impostor_socket_writes_no_ledger(home, ledger, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_IMPOSTOR_SOCKET))

    result = client.run_submit(_submit_args(str(home / 'proj')))

    assert result['status'] == 'degraded'
    assert result['reason'] == client.REASON_IMPOSTOR_SOCKET
    assert result['fallback'] == 'in_process'
    assert _job_rows() == []


def test_submit_refused_passes_through_reason(home, ledger, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'refused', 'reason': 'not_registered'},
    )

    result = client.run_submit(_submit_args(str(home / 'proj')))

    assert result['status'] == 'refused'
    assert result['reason'] == 'not_registered'
    assert _job_rows() == []


def test_submit_rejects_non_json_command(home, ledger):
    result = client.run_submit(
        Namespace(command='not-json', exec_path=None, project_path=str(home), plan_id='p1')
    )

    assert result['status'] == 'error'


# =============================================================================
# wait — bound-expiry running-TOON, killed, re-attach
# =============================================================================


def test_wait_bound_expiry_returns_live_running_status(monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {
            'status': 'running',
            'job_id': 'JOB-1',
            'elapsed': 120,
            'eta': 300,
            'last_progress': 4,
        },
    )

    result = client.run_wait(Namespace(job_id='JOB-1', plan_id=None, bound=300))

    assert result['status'] == 'success'
    assert result['job_status'] == 'running'
    # The bound-expiry body is a full running status, never timeout-shaped.
    assert result['elapsed'] == 120
    assert result['eta'] == 300
    assert result['last_progress'] == 4
    assert 'timeout' not in result


def test_wait_killed_renders_no_blind_retry_message(monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'killed', 'job_id': 'JOB-1'},
    )

    result = client.run_wait(Namespace(job_id='JOB-1', plan_id=None, bound=1))

    assert result['job_status'] == 'killed'
    assert result['message'] == client._KILLED_MESSAGE


def test_wait_reattaches_via_ledger_when_no_job_id(home, ledger, monkeypatch):
    # Seed a kind=job row exactly as submit would have.
    ledger_core.append_entry(
        ledger_core.job_record(
            job_id='JOB-REATTACH',
            plan_id='p1',
            fingerprint='fp',
            notation='a:b:c',
            worktree_sha='test-sha',
        )
    )
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    captured: dict[str, object] = {}

    def _capture(request, timeout):
        captured['job_id'] = request['job_id']
        return {'status': 'success', 'job_id': request['job_id'], 'exit_code': 0}

    monkeypatch.setattr(client, '_call_daemon', _capture)

    result = client.run_wait(Namespace(job_id=None, plan_id='p1', bound=1))

    assert captured['job_id'] == 'JOB-REATTACH'
    assert result['job_status'] == 'success'


def test_wait_errors_when_no_job_id_and_no_ledger_row(home, ledger):
    result = client.run_wait(Namespace(job_id=None, plan_id='p1', bound=1))

    assert result['status'] == 'error'


def test_wait_degraded_when_daemon_unreachable(monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_SOCKET_ABSENT))

    result = client.run_wait(Namespace(job_id='JOB-1', plan_id=None, bound=1))

    assert result['status'] == 'degraded'
    assert result['reason'] == client.REASON_SOCKET_ABSENT


# =============================================================================
# ping — identity handshake
# =============================================================================


def test_ping_up_reports_version_and_pid(monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1', 'pid': 7}, None))

    result = client.run_ping(Namespace())

    assert result['daemon'] == 'up'
    assert result['version'] == '1'
    assert result['pid'] == 7


def test_ping_down_reports_reason(monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_VERSION_MISMATCH))

    result = client.run_ping(Namespace())

    assert result['daemon'] == 'down'
    assert result['reason'] == client.REASON_VERSION_MISMATCH


# =============================================================================
# _handshake — the S3 owner + version gate (real logic, stubbed socket call)
# =============================================================================


def test_handshake_rejects_impostor_socket(home, monkeypatch):
    sock_path = client._socket_path()
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    sock_path.write_text('', encoding='utf-8')
    # Force the owner check to see a foreign uid.
    monkeypatch.setattr(client, '_socket_owner_reason', lambda _p: client.REASON_IMPOSTOR_SOCKET)

    response, reason = client._handshake(sock_path)

    assert response is None
    assert reason == client.REASON_IMPOSTOR_SOCKET


def test_handshake_rejects_version_mismatch(home, monkeypatch):
    monkeypatch.setattr(client, '_socket_owner_reason', lambda _p: None)
    monkeypatch.setattr(
        client, '_call_daemon', lambda _req, timeout: {'status': 'ok', 'version': '999'}
    )

    response, reason = client._handshake(client._socket_path())

    assert response is None
    assert reason == client.REASON_VERSION_MISMATCH


def test_handshake_accepts_matching_version(home, monkeypatch):
    monkeypatch.setattr(client, '_socket_owner_reason', lambda _p: None)
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'ok', 'version': client.PROTOCOL_VERSION, 'pid': 3},
    )

    response, reason = client._handshake(client._socket_path())

    assert reason is None
    assert response is not None
    assert response['pid'] == 3


# =============================================================================
# interaction audit logging — non-silent outcomes, correlated by job_id, secrets
# =============================================================================


def test_submit_success_logs_captured_entry_with_job_id(home, ledger, captured_logs, monkeypatch):
    root = str(home / 'proj')
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'JOB-1', 'attached': False},
    )

    client.run_submit(_submit_args(root))

    work_entries = [c for c in captured_logs if c[0] == 'work']
    assert work_entries, 'a successful submit must not be silent'
    _log_type, plan_id, level, message = work_entries[-1]
    assert plan_id == 'p1'
    assert level == 'INFO'
    assert 'JOB-1' in message


def test_submit_degraded_fallback_logs_warning(home, ledger, captured_logs, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_IMPOSTOR_SOCKET))

    client.run_submit(_submit_args(str(home / 'proj')))

    assert any(
        level == 'WARNING' and client.REASON_IMPOSTOR_SOCKET in message
        for _t, _p, level, message in captured_logs
    ), 'a degraded fallback must produce a captured WARNING entry'


def test_submit_refused_logs_warning(home, ledger, captured_logs, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'refused', 'reason': 'not_registered'},
    )

    client.run_submit(_submit_args(str(home / 'proj')))

    assert any(
        level == 'WARNING' and 'not_registered' in message
        for _t, _p, level, message in captured_logs
    ), 'a refused submit must produce a captured WARNING entry'


def test_wait_logs_result_entry_with_job_id(captured_logs, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'success', 'job_id': 'JOB-1', 'exit_code': 0},
    )

    client.run_wait(Namespace(job_id='JOB-1', plan_id='p1', bound=1))

    info_entries = [c for c in captured_logs if c[0] == 'work' and c[2] == 'INFO']
    assert info_entries, 'a wait must log its result'
    assert any('JOB-1' in message for _t, _p, _l, message in info_entries)


def test_wait_with_control_char_job_id_never_forges_a_log_header(captured_logs, monkeypatch):
    # CWE-117 regression guard for the wait path: `--job-id` is client-supplied,
    # so a crafted job_id carrying a newline must never split the work-log INFO
    # message into a second, independently-parseable log-entry line — the same
    # invariant already proven for the submit-notation path.
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    forged_header = '[2000-01-01T00:00:00Z] [ERROR] [abcdef] forged entry'
    injected_job_id = 'JOB-1\n' + forged_header
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'success', 'job_id': 'JOB-1', 'exit_code': 0},
    )

    client.run_wait(Namespace(job_id=injected_job_id, plan_id='p1', bound=1))

    work_entries = [c for c in captured_logs if c[0] == 'work']
    assert work_entries, 'a wait must log (otherwise this test is vacuous)'
    for _t, _p, level, message in work_entries:
        assert '\n' not in message
        formatted = plan_logging.format_log_entry(level, message)
        assert len(plan_logging.HEADER_PATTERN.findall(formatted)) == 1


def test_wait_degraded_logs_warning(captured_logs, monkeypatch):
    monkeypatch.setattr(client, '_handshake', lambda _p: (None, client.REASON_SOCKET_ABSENT))

    client.run_wait(Namespace(job_id='JOB-1', plan_id='p1', bound=1))

    assert any(
        level == 'WARNING' and client.REASON_SOCKET_ABSENT in message
        for _t, _p, level, message in captured_logs
    ), 'a degraded wait must produce a captured WARNING entry'


def test_plan_less_submit_is_silent(home, ledger, captured_logs, monkeypatch):
    # With no plan_id there is no per-plan work log to write to — logging no-ops.
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'JOB-1', 'attached': False},
    )

    client.run_submit(_submit_args(str(home / 'proj'), plan_id=''))

    assert captured_logs == []


def test_no_logged_message_contains_raw_command_argv(home, ledger, captured_logs, monkeypatch):
    root = str(home / 'proj')
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'JOB-1', 'attached': False},
    )

    client.run_submit(_submit_args(root))

    assert captured_logs, 'submit must log (otherwise this test is vacuous)'
    for _t, _p, _l, message in captured_logs:
        assert '.plan/execute-script.py' not in message
        assert 'python3' not in message
        assert root not in message


def test_notation_from_command_strips_control_chars():
    # CWE-117 regression guard: a crafted notation token (command[2]) must never
    # carry a raw newline/control char into a free-text log message — the
    # plan-scoped work log is plain-text/line-oriented, not JSON-escaped, so an
    # embedded newline could otherwise forge a fake log-entry header line.
    injected = 'a:b:c\n[2000-01-01T00:00:00Z] [ERROR] [abcdef] forged entry'

    sanitized = client._notation_from_command(['python3', '/tree/.plan/execute-script.py', injected, 'run'])

    assert '\n' not in sanitized
    assert sanitized == 'a:b:c[2000-01-01T00:00:00Z] [ERROR] [abcdef] forged entry'


def test_submit_with_control_char_notation_never_forges_a_log_header(home, ledger, captured_logs, monkeypatch):
    root = str(home / 'proj')
    monkeypatch.setattr(client, '_handshake', lambda _p: ({'version': '1'}, None))
    monkeypatch.setattr(
        client,
        '_call_daemon',
        lambda _req, timeout: {'status': 'queued', 'job_id': 'JOB-1', 'attached': False},
    )
    forged_header = '[2000-01-01T00:00:00Z] [ERROR] [abcdef] forged entry'
    command = (
        '["python3", "' + root + '/.plan/execute-script.py", '
        '"a:b:c\\n' + forged_header + '", "run"]'
    )

    client.run_submit(
        Namespace(command=command, exec_path=root, project_path=root, plan_id='p1')
    )

    work_entries = [c for c in captured_logs if c[0] == 'work']
    assert work_entries, 'submit must log (otherwise this test is vacuous)'
    for _t, _p, level, message in work_entries:
        # The forged header's non-control-character text may still appear as
        # inert trailing text on the SAME line (that is expected and harmless);
        # what matters is that no newline ever splits it into a second,
        # independently-parseable log-entry line.
        assert '\n' not in message
        # Prove the real invariant end-to-end: running the message through the
        # actual plan_logging formatter/parser yields exactly ONE entry — the
        # forged header text never becomes a second, independently-recognized
        # log-entry line.
        formatted = plan_logging.format_log_entry(level, message)
        assert len(plan_logging.HEADER_PATTERN.findall(formatted)) == 1
