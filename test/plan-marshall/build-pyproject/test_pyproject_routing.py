#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for pyproject's daemon-routing integration.

pyproject supplies its one-shot ``.pyprojectx`` self-heal to
``create_execute_handlers(..., wrap_execute_fn=...)`` and uses the SHARED
factory ``cmd_run`` — the same daemon-routing seam Maven, Gradle, and npm use.
These tests drive that REAL ``cmd_run`` and pin the four behaviours the
re-threading is responsible for:

(a) a routable build reaches the daemon under the pyproject executor notation,
(b) an in-process fallback still runs the self-heal and names its degradation
    reason,
(c) a plan-less build stays a pure passthrough with zero queue interaction,
(d) ``execution_mode=daemon`` fails loud — both for a daemon-incompatible
    ``--env`` / ``--working-dir`` build and for a genuine unavailability —
    rather than silently falling back in-process.

The build-server client is faked at the ``_build_execute_factory._load_build_server``
seam (the pattern ``test_acceptance_fallback.py`` uses), so no daemon process
and no machine-global state is ever touched. Every constructed ``Namespace``
declares ``execution_mode`` explicitly, so no assertion depends on live daemon
state.
"""

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import _build_queue_slot as bqs
import pytest

from conftest import load_script_module

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))


_pyproject_execute_mod = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_execute.py', '_pyproject_execute'
)

cmd_run = _pyproject_execute_mod.cmd_run

import _build_execute_factory as _factory  # noqa: E402

PYPROJECT_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


class _FakeClient:
    """Scriptable build-server client installed over ``_load_build_server``.

    Records every preflight / submit / wait call so a test can assert that a
    non-routable build never even probed the daemon."""

    def __init__(self, preflight, submit=None, wait=None):
        self._preflight = preflight
        self._submit = submit
        self._wait = wait
        self.preflight_calls: list = []
        self.submit_calls: list = []
        self.wait_calls: list = []

    def run_preflight(self, args):
        self.preflight_calls.append(args)
        return self._preflight

    def run_submit(self, args):
        self.submit_calls.append(args)
        if self._submit is None:
            raise AssertionError('a not-ready project must never submit')
        return self._submit

    def run_wait(self, args):
        self.wait_calls.append(args)
        if self._wait is None:
            raise AssertionError('a build that never submitted must never wait')
        return self._wait

    @property
    def submitted_command(self) -> list[str]:
        """The executor-form command list the daemon would re-run."""
        return json.loads(self.submit_calls[0].command)


class _ExecRecorder:
    """Records in-process build invocations, returning scripted results.

    Installed at ``_factory.execute_direct_base`` — the seam the self-heal
    wrapper's closure ultimately calls — because both the wrapper and the
    routing ``cmd_run`` reach the build through closure variables that are not
    patchable as module attributes. With no scripted results it returns a
    success, so a single ``cmd_run`` maps to exactly one recorded call."""

    def __init__(self, results=None):
        self._results = list(results) if results else []
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self._results:
            return self._results.pop(0)
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0,
            'log_file': '',
            'command': 'pw verify',
        }

    @property
    def ran(self) -> bool:
        return len(self.calls) > 0


class _QueueSpy:
    """Records queue acquire/release so a passthrough can be proven inert."""

    def __init__(self):
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, str]] = []

    def acquire(self, plan_id: str) -> dict:
        self.acquire_calls.append(plan_id)
        return {'status': 'success', 'admission': 'admitted', 'id': f'{plan_id}:uuid-1'}

    def release(self, plan_id: str, admission_id: str) -> dict:
        self.release_calls.append((plan_id, admission_id))
        return {'status': 'success', 'action': 'released'}


@pytest.fixture(autouse=True)
def _isolated_routing(monkeypatch):
    """Neutralize every ambient influence on the routing decision.

    Clears the daemon-child re-entrancy env var, stubs the routing audit's
    work-log sink, and no-ops the rendering tail so the tests assert on the
    routing decision rather than on build-log rendering. The build-queue
    acquire/release seam is stubbed unconditionally so a test that reaches the
    in-process leg with a plan_id never touches the real machine-global queue;
    a test that needs to PROVE the queue was untouched installs its own spy on
    top of this stub."""
    monkeypatch.delenv(_factory.MARSHALLD_JOB_ENV, raising=False)
    monkeypatch.setattr(_factory, 'log_entry', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_factory, 'cmd_run_common', lambda **_kwargs: 0)
    monkeypatch.setattr(bqs.time, 'sleep', lambda _s: None)
    default_queue = _QueueSpy()
    monkeypatch.setattr(bqs, '_acquire', default_queue.acquire)
    monkeypatch.setattr(bqs, '_release_raw', default_queue.release)


@pytest.fixture
def resolutions(monkeypatch) -> list[tuple]:
    """Capture every ``_record_resolution`` call as a tuple."""
    recorded: list[tuple] = []

    def _spy(requested, resolved, reason, notation, plan_id):
        recorded.append((requested, resolved, reason, notation, plan_id))

    monkeypatch.setattr(_factory, '_record_resolution', _spy)
    return recorded


def _install_exec(monkeypatch, results=None) -> _ExecRecorder:
    recorder = _ExecRecorder(results)
    monkeypatch.setattr(_factory, 'execute_direct_base', recorder)
    return recorder


def _install_client(monkeypatch, client: _FakeClient) -> _FakeClient:
    monkeypatch.setattr(_factory, '_load_build_server', lambda: client)
    return client


def _make_log(tmp_path: Path, text: str) -> str:
    log_path = tmp_path / 'build.log'
    log_path.write_text(text)
    return str(log_path)


# ---------------------------------------------------------------------------
# (a) A routable pyproject build reaches the daemon
# ---------------------------------------------------------------------------


class TestPyprojectRoutesToDaemon:
    """A ready daemon receives the build under the pyproject executor notation,
    and the in-process executor never runs."""

    def test_ready_daemon_receives_build_under_pyproject_notation(
        self, tmp_path, monkeypatch, resolutions
    ):
        client = _install_client(
            monkeypatch,
            _FakeClient(
                preflight={'status': 'success', 'preflight': 'ready'},
                submit={'status': 'success', 'job_id': 'J1'},
                wait={
                    'status': 'success',
                    'job_status': 'success',
                    'exit_code': 0,
                    'duration_seconds': 3,
                    'log_file': '',
                },
            ),
        )
        exec_recorder = _install_exec(monkeypatch)

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify',
                plan_id='P',
                format='toon',
                execution_mode='auto',
                project_dir=str(tmp_path),
            )
        )

        assert rc == 0
        # Exactly one submit, carrying the pyproject executor notation the
        # daemon verifies against the project's notation_allowlist.
        assert len(client.submit_calls) == 1
        assert client.submitted_command[2] == PYPROJECT_NOTATION
        # The routed build is NOT also run in-process — a build takes exactly
        # one limiter path.
        assert exec_recorder.ran is False
        assert resolutions == [('auto', 'routed', None, PYPROJECT_NOTATION, 'P')]


# ---------------------------------------------------------------------------
# (b) In-process fallback still runs the self-heal
# ---------------------------------------------------------------------------


class TestPyprojectFallbackKeepsSelfHeal:
    """An unroutable build falls back in-process with the one-shot self-heal
    intact, and the degradation reason is recorded so the fallback is never
    silent."""

    def test_fallback_runs_self_heal_and_records_reason(self, tmp_path, monkeypatch, resolutions):
        (tmp_path / '.pyprojectx').mkdir()
        log_file = _make_log(tmp_path, '/bin/sh: uv: command not found\nexit 127')
        failure = {
            'status': 'error',
            'exit_code': 127,
            'log_file': log_file,
            'command': './pw verify',
            'error': '',
        }
        success = {
            'status': 'success',
            'exit_code': 0,
            'log_file': log_file,
            'command': './pw verify',
        }
        _install_client(monkeypatch, _FakeClient(preflight={'status': 'success', 'preflight': 'disabled'}))
        exec_recorder = _install_exec(monkeypatch, [failure, success])

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify',
                plan_id=None,
                format='toon',
                execution_mode='auto',
                project_dir=str(tmp_path),
            )
        )

        assert rc == 0
        # The self-heal rode the in-process leg: one rename aside, one retry.
        assert len(exec_recorder.calls) == 2
        assert (tmp_path / '.pyprojectx.broken').is_dir()
        assert not (tmp_path / '.pyprojectx').exists()
        # The fallback names WHY it degraded.
        assert resolutions == [('auto', 'in_process', 'disabled', PYPROJECT_NOTATION, None)]


# ---------------------------------------------------------------------------
# (c) Plan-less passthrough is unchanged
# ---------------------------------------------------------------------------


class TestPyprojectPlanlessPassthrough:
    """A plan-less in-process build runs with ZERO queue interaction — the
    backward-compatibility guarantee for builds outside a plan."""

    def test_planless_in_process_build_touches_no_queue(self, tmp_path, monkeypatch):
        spy = _QueueSpy()
        monkeypatch.setattr(bqs, '_acquire', spy.acquire)
        monkeypatch.setattr(bqs, '_release_raw', spy.release)
        exec_recorder = _install_exec(monkeypatch)

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify',
                format='toon',
                execution_mode='in_process',
                project_dir=str(tmp_path),
            )
        )

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert spy.acquire_calls == []
        assert spy.release_calls == []


# ---------------------------------------------------------------------------
# (d) execution_mode=daemon fails loud
# ---------------------------------------------------------------------------


class TestPyprojectDaemonModeFailsLoud:
    """In ``daemon`` mode an unroutable build is a HARD failure — never a silent
    in-process fallback."""

    @pytest.mark.parametrize(
        ('flag', 'value'),
        [('env', 'FOO=bar'), ('working_dir', '/tmp/elsewhere')],
    )
    def test_daemon_incompatible_override_fails_loud(
        self, tmp_path, monkeypatch, capsys, resolutions, flag, value
    ):
        """--env / --working-dir can never be honoured by the daemon's clean
        baseline env, so daemon mode refuses instead of falling back."""
        client = _install_client(monkeypatch, _FakeClient(preflight={'status': 'success', 'preflight': 'ready'}))
        exec_recorder = _install_exec(monkeypatch)

        namespace = argparse.Namespace(
            command_args='verify',
            plan_id='P',
            format='toon',
            execution_mode='daemon',
            project_dir=str(tmp_path),
        )
        setattr(namespace, flag, value)

        rc = cmd_run(namespace)

        assert rc == 1
        out = capsys.readouterr().out
        assert 'daemon_required' in out
        assert 'env_or_working_dir_set' in out
        # The daemon was never even probed, and the build never ran in-process.
        assert client.preflight_calls == []
        assert client.submit_calls == []
        assert exec_recorder.ran is False
        assert resolutions == [
            ('daemon', 'fail-loud', 'env_or_working_dir_set', PYPROJECT_NOTATION, 'P')
        ]

    def test_genuine_unavailability_fails_loud(self, tmp_path, monkeypatch, capsys, resolutions):
        """A daemon that is down is fatal in daemon mode — the build is NOT run
        in-process behind the caller's back."""
        client = _install_client(
            monkeypatch,
            _FakeClient(preflight={'status': 'success', 'preflight': 'down', 'reason': 'socket_absent'}),
        )
        exec_recorder = _install_exec(monkeypatch)

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify',
                plan_id='P',
                format='toon',
                execution_mode='daemon',
                project_dir=str(tmp_path),
            )
        )

        assert rc == 1
        out = capsys.readouterr().out
        assert 'daemon_required' in out
        assert 'socket_absent' in out
        assert client.submit_calls == []
        assert exec_recorder.ran is False
        assert resolutions == [('daemon', 'fail-loud', 'socket_absent', PYPROJECT_NOTATION, 'P')]

    def test_auto_with_env_never_routes_and_records_reason(
        self, tmp_path, monkeypatch, resolutions
    ):
        """The auto counterpart of the daemon-incompatible branch: same
        condition, but a recorded in-process degradation instead of a refusal."""
        client = _install_client(monkeypatch, _FakeClient(preflight={'status': 'success', 'preflight': 'ready'}))
        exec_recorder = _install_exec(monkeypatch)

        rc = cmd_run(
            argparse.Namespace(
                command_args='verify',
                plan_id='P',
                format='toon',
                execution_mode='auto',
                env='FOO=bar',
                project_dir=str(tmp_path),
            )
        )

        assert rc == 0
        # Never attempted to route, and said so.
        assert client.preflight_calls == []
        assert client.submit_calls == []
        assert len(exec_recorder.calls) == 1
        assert resolutions == [
            ('auto', 'in_process', 'env_or_working_dir_set', PYPROJECT_NOTATION, 'P')
        ]
        # The env override actually reached the build body.
        assert exec_recorder.calls[0]['env_vars'] == {'FOO': 'bar'}
