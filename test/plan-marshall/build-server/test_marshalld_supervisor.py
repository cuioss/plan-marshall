#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _marshalld_supervisor (clean env, classification, run_job).

Terminal classification carries one subtlety worth stating up front: the daemon's
build child is normally the build wrapper, which exits 0 even when the build
failed and reports its real verdict in the build-result TOON it emits. A zero
exit is therefore NECESSARY but not SUFFICIENT for ``success`` — the emitted
verdict must agree. The ``timeout`` and ``killed`` legs are never reclassified by
log content.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
import time
from pathlib import Path

import _build_server_protocol as protocol
import pytest

from conftest import load_script_module

supervisor = load_script_module('plan-marshall', 'manage-build-server', '_marshalld_supervisor.py')

# Child programs run through run_job. Each writes the shape of build-wrapper
# output the supervisor has to classify, then exits 0 (or is killed).
_EMIT_ERROR_TOON = "print('status: error'); print('exit_code: 3')"
_EMIT_SUCCESS_TOON = "print('status: success'); print('exit_code: 0')"
_EMIT_NO_TOON = "print('some build chatter with no build TOON at all')"
# The two NON-FINISHES the wrapper can observe first-hand and report at exit 0:
# its own outer bound fired, or its build child was signalled while it survived
# (the INNER kill — distinct from the outer kill the supervisor sees as a
# negative returncode of the wrapper itself).
_EMIT_KILLED_TOON = "print('status: killed'); print('exit_code: -9')"
_EMIT_TIMEOUT_TOON = "print('status: timeout'); print('exit_code: -1')"
# The fifth _build_result status: the wrapper could not establish an outcome at
# all. It is not a non-finish and not a failure, and it had no wire row until the
# translation table was made total.
_EMIT_INDETERMINATE_TOON = "print('status: indeterminate'); print('exit_code: -1')"
_EMIT_SUCCESS_THEN_HANG = "print('status: success', flush=True); import time; time.sleep(30)"
_EMIT_SUCCESS_THEN_SUICIDE = (
    "import os, signal; print('status: success', flush=True); os.kill(os.getpid(), signal.SIGKILL)"
)
# The two NON-FINISHES again, this time as a wrapper that also states the bound
# it applied and where that bound came from. 330 / learned are deliberately
# unlike any bound the supervisor is handed in these tests, so a payload that
# reported the supervisor's own bound instead is unmistakable.
_INNER_BOUND_SECONDS = 330
_INNER_BOUND_SOURCE = 'learned'
_INNER_BOUND_LINES = (
    f"print('timeout_used_seconds: {_INNER_BOUND_SECONDS}'); print('timeout_source: {_INNER_BOUND_SOURCE}')"
)
_EMIT_TIMEOUT_TOON_WITH_BOUND = f'{_EMIT_TIMEOUT_TOON}; {_INNER_BOUND_LINES}'
_EMIT_KILLED_TOON_WITH_BOUND = f'{_EMIT_KILLED_TOON}; {_INNER_BOUND_LINES}'


def _run(code: str, tmp_path: Path, *, timeout: int = 30, timeout_source: str | None = None) -> dict:
    """Run one trivial child through run_job and return its terminal payload."""
    log_file = tmp_path / 'job.log'
    return asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', code],
            str(tmp_path),
            timeout=timeout,
            timeout_source=timeout_source,
            log_file=str(log_file),
        )
    )


# =============================================================================
# classify_terminal
# =============================================================================


def test_classify_success():
    assert supervisor.classify_terminal(0, timed_out=False) == 'success'


def test_classify_failure():
    assert supervisor.classify_terminal(3, timed_out=False) == 'failure'


def test_classify_timeout_outranks_signal_exit():
    # A timeout kill leaves a negative returncode, but the timed_out flag wins.
    assert supervisor.classify_terminal(-9, timed_out=True) == 'timeout'


def test_classify_killed_is_not_failure():
    # A negative exit the supervisor did NOT cause is 'killed', never 'failure'.
    assert supervisor.classify_terminal(-9, timed_out=False) == 'killed'


def test_classify_none_returncode_is_killed():
    assert supervisor.classify_terminal(None, timed_out=False) == 'killed'


# =============================================================================
# build_baseline_env
# =============================================================================


def test_baseline_env_filters_to_whitelist():
    source = {'PATH': '/bin', 'HOME': '/home/u', 'SECRET_TOKEN': 'nope', 'AWS_KEY': 'nope'}

    env = supervisor.build_baseline_env(source)

    assert env == {'PATH': '/bin', 'HOME': '/home/u'}
    assert 'SECRET_TOKEN' not in env
    assert 'AWS_KEY' not in env


def test_baseline_env_omits_missing_keys():
    env = supervisor.build_baseline_env({'PATH': '/bin'})

    assert env == {'PATH': '/bin'}


# =============================================================================
# JobProgress
# =============================================================================


def test_job_progress_mark_resets_idle():
    progress = supervisor.JobProgress()
    before = progress.last_activity
    progress.mark()

    assert progress.last_activity >= before
    assert progress.elapsed() >= 0
    assert progress.idle_seconds() >= 0


# =============================================================================
# run_job (real subprocess)
# =============================================================================


def test_run_job_success(tmp_path):
    log_file = str(tmp_path / 'ok.log')

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', 'print("hello")'],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'success'
    assert payload['exit_code'] == 0
    assert payload['log_file'] == log_file


def test_run_job_failure(tmp_path):
    log_file = str(tmp_path / 'fail.log')

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', 'import sys; sys.exit(3)'],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'failure'
    assert payload['exit_code'] == 3


def test_run_job_timeout(tmp_path):
    log_file = str(tmp_path / 'to.log')

    payload = asyncio.run(
        supervisor.run_job(
            # Block indefinitely on signal.pause() rather than sleeping a fixed
            # 10 s: the child is killed by the supervisor's timeout=1, so the
            # test never depends on a wall-clock duration outrunning the timeout.
            [sys.executable, '-c', 'import signal; signal.pause()'],
            str(tmp_path),
            timeout=1,
            log_file=log_file,
        )
    )

    assert payload['status'] == 'timeout'


# The grandchild ignores SIGTERM, announces that the handler is installed, and
# blocks. Its output is detached from the job's pipes so a survivor cannot hold
# the supervisor's log pumps open — the assertion is about the PROCESS, and a
# hang would hide it.
_GRANDCHILD_CODE = (
    'import signal, sys\n'
    'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
    "open(sys.argv[1], 'w').close()\n"
    'while True:\n'
    '    signal.pause()\n'
)

# The job child spawns that grandchild, publishes its pid once the grandchild is
# ready, and blocks until the supervisor's timeout stops it.
_SPAWN_GRANDCHILD_THEN_BLOCK = (
    'import os, signal, subprocess, sys, time\n'
    'ready, pid_file = sys.argv[1], sys.argv[2]\n'
    'grandchild = subprocess.Popen(\n'
    '    [sys.executable, "-c", sys.argv[3], ready],\n'
    '    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n'
    ')\n'
    'while not os.path.exists(ready):\n'
    '    time.sleep(0.01)\n'
    "with open(pid_file + '.tmp', 'w') as handle:\n"
    '    handle.write(str(grandchild.pid))\n'
    "os.replace(pid_file + '.tmp', pid_file)\n"
    'signal.pause()\n'
)

_GRANDCHILD_EXIT_DEADLINE_SECONDS = 10


def _pid_is_gone(pid: int, *, deadline_seconds: float) -> bool:
    """Report whether ``pid`` stops existing before the deadline passes."""
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        # A zombie still answers signal 0: it has exited and only awaits reaping.
        # Without procfs (macOS) the signal probe above is the whole check.
        with contextlib.suppress(OSError), open(f'/proc/{pid}/stat') as handle:
            if handle.read().rpartition(')')[2].split()[0] == 'Z':
                return True
        time.sleep(0.05)
    return False


# Module-level on purpose: pytest rejects a class-scoped fixture declared as an
# instance method. The class scope still shares one run between both tests of
# the class that requests it.
@pytest.fixture(scope='class')
def timed_out_run(tmp_path_factory):
    """Run the grandchild-spawning job to its timeout once for the requesting class."""
    tmp_path = tmp_path_factory.mktemp('tree-kill')
    pid_file = tmp_path / 'grandchild.pid'
    payload = asyncio.run(
        supervisor.run_job(
            [
                sys.executable,
                '-c',
                _SPAWN_GRANDCHILD_THEN_BLOCK,
                str(tmp_path / 'grandchild.ready'),
                str(pid_file),
                _GRANDCHILD_CODE,
            ],
            str(tmp_path),
            timeout=3,
            log_file=str(tmp_path / 'job.log'),
        )
    )
    assert pid_file.exists(), 'the job child never published its grandchild pid before the timeout'
    grandchild_pid = int(pid_file.read_text())
    yield payload, grandchild_pid
    # A grandchild that survived (the defect) must not outlive the test run.
    with contextlib.suppress(ProcessLookupError):
        os.kill(grandchild_pid, signal.SIGKILL)


@pytest.mark.skipif(os.name == 'nt', reason='process groups and os.killpg are POSIX-only')
class TestRunJobTimeoutStopsTheWholeProcessTree:
    """A supervisor timeout stops the job's process group, not only the job child.

    The job child is the first link of a chain, so stopping its pid alone leaves
    the rest of the build running. The grandchild here ignores SIGTERM, so it
    also proves the group SIGKILL follows the group SIGTERM.
    """

    def test_grandchild_is_gone_after_the_timeout(self, timed_out_run):
        _payload, grandchild_pid = timed_out_run

        gone = _pid_is_gone(grandchild_pid, deadline_seconds=_GRANDCHILD_EXIT_DEADLINE_SECONDS)

        assert gone, f'grandchild {grandchild_pid} outlived the supervisor timeout'

    def test_group_kill_is_still_classified_as_timeout(self, timed_out_run):
        payload, _grandchild_pid = timed_out_run

        assert payload['status'] == 'timeout'


# The job leader keeps the default SIGTERM disposition, so it exits at once. It
# starts the wrapper in the same process group, with output detached from the
# job's pipes.
_LEADER_THEN_WRAPPER = (
    'import signal, subprocess, sys\n'
    'subprocess.Popen(\n'
    '    [sys.executable, "-c", sys.argv[1], sys.argv[2], sys.argv[3]],\n'
    '    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n'
    ')\n'
    'signal.pause()\n'
)

# The wrapper runs the build through the shipped ``_run_bounded``.
_WRAPPER_RUNS_BUILD = (
    'import subprocess, sys\n'
    'from _build_execute import _run_bounded\n'
    '_run_bounded(\n'
    '    [sys.executable, "-c", sys.argv[2], sys.argv[1]],\n'
    '    timeout_seconds=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n'
    '    cwd=".", env=None, log_prefix="test", command_str="build",\n'
    ')\n'
)

# The build ignores SIGTERM and publishes its own pid once the handler is set.
_BUILD_IGNORES_SIGTERM = (
    'import os, signal, sys\n'
    'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
    "with open(sys.argv[1] + '.tmp', 'w') as handle:\n"
    '    handle.write(str(os.getpid()))\n'
    "os.replace(sys.argv[1] + '.tmp', sys.argv[1])\n"
    'while True:\n'
    '    signal.pause()\n'
)


@pytest.fixture
def build_pid_after_timeout(tmp_path):
    """Run the leader/wrapper/build chain to the supervisor timeout; yield the build's pid."""
    pid_file = tmp_path / 'build.pid'
    asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', _LEADER_THEN_WRAPPER, _WRAPPER_RUNS_BUILD, str(pid_file), _BUILD_IGNORES_SIGTERM],
            str(tmp_path),
            timeout=3,
            log_file=str(tmp_path / 'job.log'),
            env={
                **supervisor.build_baseline_env(),
                'PYTHONPATH': os.pathsep.join(sys.path),
                'PLAN_BASE_DIR': str(tmp_path / 'plan'),
            },
        )
    )
    assert pid_file.exists(), 'the build never published its pid before the timeout'
    build_pid = int(pid_file.read_text())
    yield build_pid
    with contextlib.suppress(ProcessLookupError):
        os.kill(build_pid, signal.SIGKILL)


@pytest.mark.skipif(os.name == 'nt', reason='process groups and os.killpg are POSIX-only')
def test_timeout_lets_the_wrapper_stop_a_build_that_ignores_sigterm(build_pid_after_timeout):
    gone = _pid_is_gone(build_pid_after_timeout, deadline_seconds=_GRANDCHILD_EXIT_DEADLINE_SECONDS)

    assert gone, f'build {build_pid_after_timeout} outlived the supervisor timeout'


@pytest.mark.skipif(os.name == 'nt', reason='process groups and os.killpg are POSIX-only')
def test_timeout_with_an_unsignallable_group_is_still_classified_as_timeout(tmp_path, monkeypatch):
    """A group this process may not probe or kill leaves the job a timeout."""
    real_killpg = os.killpg

    def _killpg(pgid: int, signum: int) -> None:
        if signum in (0, signal.SIGKILL):
            raise PermissionError
        real_killpg(pgid, signum)

    monkeypatch.setattr(os, 'killpg', _killpg)

    payload = _run('import signal; signal.pause()', tmp_path, timeout=1)

    assert payload['status'] == 'timeout'


def test_run_job_clean_env_excludes_secret(tmp_path):
    log_file = str(tmp_path / 'env.log')
    # SECRET_TOKEN is NOT in the whitelist, so build_baseline_env drops it: the
    # child prints an empty string for it.
    code = 'import os; print("SECRET=" + os.environ.get("SECRET_TOKEN", ""))'

    payload = asyncio.run(
        supervisor.run_job(
            [sys.executable, '-c', code],
            str(tmp_path),
            timeout=30,
            log_file=log_file,
            env=supervisor.build_baseline_env({'PATH': '/usr/bin:/bin', 'SECRET_TOKEN': 'leak'}),
        )
    )

    assert payload['status'] == 'success'
    captured = (tmp_path / 'env.log').read_text()
    assert 'SECRET=leak' not in captured
    assert 'SECRET=' in captured  # the var resolved to empty, proving it was dropped


# =============================================================================
# run_job — exit 0 is necessary but not sufficient
# =============================================================================
# The pure ``read_log_verdict`` reader is relocated to ``_build_server_protocol``
# and its unit coverage lives in ``test_build_server_protocol.py``. The supervisor
# still re-exports the reader (``supervisor.read_log_verdict``), and the
# narrowing-behaviour tests below assert ``run_job`` consumes it unchanged.


def test_supervisor_reexports_relocated_reader():
    # The reader moved to the shared protocol module; the supervisor imports it
    # from there, so both the module attribute and the shared source are one
    # object — proving there is no duplicate reader left behind.
    import _build_server_protocol as protocol

    assert supervisor.read_log_verdict is protocol.read_log_verdict


class TestRunJobTruthfulStatus:
    """Exit 0 is necessary but no longer sufficient for a ``success`` status."""

    def test_exit_zero_with_error_toon_is_failure_carrying_the_toon_exit_code(self, tmp_path):
        # The regression anchor: the wrapper exits 0 while reporting a failed
        # build, and the daemon must NOT render that as success.
        payload = _run(_EMIT_ERROR_TOON, tmp_path)

        assert payload['status'] == 'failure'
        assert payload['exit_code'] == 3

    def test_exit_zero_with_success_toon_is_success(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_TOON, tmp_path)

        assert payload['status'] == 'success'
        assert payload['exit_code'] == 0

    def test_exit_zero_without_a_build_toon_is_success(self, tmp_path):
        # A non-wrapper command run through the daemon keeps the exit-code verdict.
        payload = _run(_EMIT_NO_TOON, tmp_path)

        assert payload['status'] == 'success'
        assert payload['exit_code'] == 0

    def test_timeout_outranks_a_contradicting_toon(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_THEN_HANG, tmp_path, timeout=1)

        assert payload['status'] == 'timeout'

    def test_signal_kill_outranks_a_contradicting_toon(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_THEN_SUICIDE, tmp_path)

        assert payload['status'] == 'killed'

    def test_exit_zero_with_indeterminate_toon_is_a_terminal_wire_status(self, tmp_path):
        """A routed ``indeterminate`` reaches the wire as a TERMINAL status.

        It previously had no wire row, so the narrowing published the literal
        string ``indeterminate`` — absent from ``TERMINAL_STATUSES`` — and a
        client waiting for a terminal status re-polled forever. Driven through
        the real ``run_job`` against a real child, so the assertion is about what
        the daemon publishes rather than about a translation composed in the test.
        """
        payload = _run(_EMIT_INDETERMINATE_TOON, tmp_path)

        assert payload['status'] in protocol.TERMINAL_STATUSES
        assert payload['status'] == protocol.STATUS_FAILURE


class TestRunJobFailsClosedOnAnUntranslatableLogStatus:
    """ADR-009 at the log-verdict seam: never crash the job over a translation gap.

    ``wire_status_from_result`` raises on a ``_build_result`` status the wire
    table cannot translate — a deliberate totality guard on a value that normally
    comes from code in this tree. The status here did not: it was read off a JOB
    LOG, so a version-skewed wrapper binary can emit one this daemon's protocol
    module predates. Letting the raise escape would abort ``run_job`` and lose the
    whole result, converting a vocabulary gap into a daemon crash.
    """

    def test_an_untranslatable_log_status_becomes_indeterminate_not_a_crash(self, monkeypatch):
        """The gap resolves to ``indeterminate``'s wire status, and the call returns."""
        narrowed = dict(protocol._RESULT_STATUS_TO_WIRE)
        narrowed.pop('error')
        monkeypatch.setattr(protocol, '_RESULT_STATUS_TO_WIRE', narrowed)

        translated = supervisor._wire_status_from_log_verdict('error')

        assert translated == protocol.wire_status_from_result('indeterminate')
        assert translated in protocol.TERMINAL_STATUSES

    def test_control_a_translatable_status_is_not_diverted(self):
        """CONTROL: the fallback only fires on the gap.

        Without it, a helper that returned ``indeterminate``'s wire status
        unconditionally would satisfy the case above while destroying every
        non-finish the narrowing exists to preserve.
        """
        assert supervisor._wire_status_from_log_verdict('killed') == protocol.STATUS_KILLED
        assert supervisor._wire_status_from_log_verdict('timeout') == protocol.STATUS_TIMEOUT
        assert supervisor._wire_status_from_log_verdict('error') == protocol.STATUS_FAILURE

    def test_a_status_outside_both_vocabularies_still_passes_through(self):
        """The OTHER unrecognised class keeps its existing route.

        A truncated or foreign log yielding arbitrary text never reaches the
        fallback: it passes through the translator unchanged and
        ``_terminal_payload`` renders it verbatim for the client to map. Both
        unrecognised classes end at ``indeterminate``, by two different routes,
        and neither aborts the job — which is why the fallback is scoped to the
        raise rather than to everything unfamiliar.
        """
        assert supervisor._wire_status_from_log_verdict('speculative') == 'speculative'


class TestRunJobNarrowingPreservesTheNonFinish:
    """The narrowing must keep WHICH non-green the wrapper reported.

    The wrapper exits 0 for all three of its non-green outcomes, so
    ``classify_terminal`` says ``success`` and the narrowing alone decides the
    wire status. Downgrading to a hard-coded ``failure`` re-collapses at the
    daemon exactly what the wrapper took care to distinguish: a routed timeout
    and a routed INNER kill both reach every downstream gate as a red build.

    These cases drive the REAL :func:`run_job` against a real child process.
    Asserting the composition ``wire_status_from_result(verdict.status)`` in the
    test instead would re-implement the very line under test, and would stay
    green if that line were reverted to ``status = 'failure'`` — a test that
    cannot fail for the defect it names is the same false signal this whole
    change exists to remove.
    """

    def test_exit_zero_with_killed_toon_is_wire_killed_not_failure(self, tmp_path):
        payload = _run(_EMIT_KILLED_TOON, tmp_path)

        assert payload['status'] == 'killed'
        assert payload['status'] != 'failure'
        assert payload['exit_code'] == -9

    def test_exit_zero_with_timeout_toon_is_wire_timeout_not_failure(self, tmp_path):
        payload = _run(_EMIT_TIMEOUT_TOON, tmp_path)

        assert payload['status'] == 'timeout'
        assert payload['status'] != 'failure'

    # --- matched control ---------------------------------------------------

    def test_control_exit_zero_with_error_toon_is_still_wire_failure(self, tmp_path):
        """CONTROL: a build that ran and failed still narrows to ``failure``.

        Without this, a change that stopped narrowing altogether would satisfy
        both cases above while reinstating the false-green the narrowing exists
        to prevent.
        """
        payload = _run(_EMIT_ERROR_TOON, tmp_path)

        assert payload['status'] == 'failure'
        assert payload['exit_code'] == 3


#: The supervisory bound and origin the daemon hands ``run_job`` in the cases
#: below. Neither coincides with the inner wrapper's 330 / ``learned``.
_DAEMON_BOUND_SOURCE = 'daemon_default'


class TestRunJobNamesTheBoundItMeasuredAgainst:
    """A ``timeout`` or ``killed`` payload names the bound that actually applied.

    Two bounds exist on a routed build — the supervisor's own and the inner
    wrapper's — and a non-finish was measured against exactly one of them. The
    supervisor's own timeout and an external kill of the child ran under the
    supervisor's bound; a non-finish narrowed from the job log ran under the
    inner wrapper's, which is the smaller one and the one that fired. Every case
    drives the REAL :func:`run_job` against a real child process.
    """

    def test_own_timeout_carries_the_supervisors_bound_and_its_source(self, tmp_path):
        payload = _run(_EMIT_SUCCESS_THEN_HANG, tmp_path, timeout=1, timeout_source=_DAEMON_BOUND_SOURCE)

        assert payload['status'] == 'timeout'
        assert payload['timeout_used_seconds'] == 1
        assert payload['timeout_source'] == _DAEMON_BOUND_SOURCE

    def test_own_timeout_without_a_stated_source_carries_the_bound_alone(self, tmp_path):
        """A caller that names no origin gets none invented for it."""
        payload = _run(_EMIT_SUCCESS_THEN_HANG, tmp_path, timeout=1)

        assert payload['status'] == 'timeout'
        assert payload['timeout_used_seconds'] == 1
        assert 'timeout_source' not in payload

    def test_external_kill_carries_the_bound_that_did_not_fire(self, tmp_path):
        """The kill was not the bound firing, but the bound is still what applied."""
        payload = _run(_EMIT_SUCCESS_THEN_SUICIDE, tmp_path, timeout=30, timeout_source=_DAEMON_BOUND_SOURCE)

        assert payload['status'] == 'killed'
        assert payload['timeout_used_seconds'] == 30
        assert payload['timeout_source'] == _DAEMON_BOUND_SOURCE

    @pytest.mark.parametrize(
        ('code', 'expected_status'),
        [(_EMIT_TIMEOUT_TOON_WITH_BOUND, 'timeout'), (_EMIT_KILLED_TOON_WITH_BOUND, 'killed')],
        ids=['narrowed-timeout', 'narrowed-kill'],
    )
    def test_narrowed_non_finish_carries_the_inner_wrappers_bound(self, tmp_path, code, expected_status):
        """A payload narrowed from the job log reports the INNER bound and source.

        The supervisor was handed 30 s / ``daemon_default``; the wrapper it ran
        reported a non-finish under 330 s / ``learned``. The payload names the
        wrapper's pair, because the supervisor's bound never came into it.
        """
        payload = _run(code, tmp_path, timeout=30, timeout_source=_DAEMON_BOUND_SOURCE)

        assert payload['status'] == expected_status
        assert payload['timeout_used_seconds'] == _INNER_BOUND_SECONDS
        assert payload['timeout_source'] == _INNER_BOUND_SOURCE

    @pytest.mark.parametrize(
        ('code', 'expected_status'),
        [(_EMIT_TIMEOUT_TOON, 'timeout'), (_EMIT_KILLED_TOON, 'killed')],
        ids=['narrowed-timeout', 'narrowed-kill'],
    )
    def test_narrowed_non_finish_without_a_logged_bound_carries_none(self, tmp_path, code, expected_status):
        """A log that states no bound yields none — not the supervisor's own.

        Reporting the supervisor's 30 s here would name a bound that did not
        apply to the run the wrapper described.
        """
        payload = _run(code, tmp_path, timeout=30, timeout_source=_DAEMON_BOUND_SOURCE)

        assert payload['status'] == expected_status
        assert 'timeout_used_seconds' not in payload
        assert 'timeout_source' not in payload

    # --- matched control ---------------------------------------------------

    @pytest.mark.parametrize('code', [_EMIT_SUCCESS_TOON, _EMIT_ERROR_TOON], ids=['success', 'failure'])
    def test_control_a_finished_job_carries_no_bound(self, tmp_path, code):
        """CONTROL: the bound is a non-finish field, not stamped on every payload."""
        payload = _run(code, tmp_path, timeout=30, timeout_source=_DAEMON_BOUND_SOURCE)

        assert 'timeout_used_seconds' not in payload
        assert 'timeout_source' not in payload
