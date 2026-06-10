# ruff: noqa: I001
#!/usr/bin/env python3
"""Tests for ``script-shared/scripts/build/_build_queue_slot.py`` (D6).

The build-queue slot wrapper is a pure concurrency limiter: it participates in
the cluster build queue ONLY when a ``plan_id`` is set, and writes no
terminal-title state. With no plan_id it is a pure no-op passthrough so plan-less
builds run completely unchanged. These tests cover:

* **No-op passthrough** — falsy plan_id yields immediately with ZERO queue
  interaction (the backward-compatibility guarantee).
* **Admit-immediately** — an ``admitted`` acquire runs the body and releases the
  slot in the ``finally``.
* **Block-then-admit** — a ``blocked`` acquire sleeps (mocked to 0), re-polls,
  and admits on a later poll.
* **Retries exhausted** — staying ``blocked`` past ``max_retries`` releases the
  queued id and raises :class:`BuildQueueTimeout`.
* **Always-release** — the slot is released even when the wrapped body raises.
* **No title-token machinery** — the queue exposes none of the
  ``_set_title_token`` / ``_clear_title_token`` / ``_push_title_token`` symbols.
* **max_retries resolution** — read from marshal.json with a 10 fallback.
* **_emit_queue_timeout** — renders a structured ``queue_saturated`` error.

The queue acquire/release seam (``_acquire`` / ``_release_raw``) is mocked
directly, so the tests are independent of whether the queue is reached by a
file-path import or the executor. Every wait-loop test patches ``time.sleep`` to
a no-op so the 60s wait is never slept.
"""

from __future__ import annotations

import argparse

import pytest

import _build_queue_slot as bqs
from _build_queue_slot import BuildQueueTimeout, build_queue_slot


class _QueueDouble:
    """Scriptable acquire/release double installed over the ``_acquire`` and
    ``_release_raw`` seams. Acquire responses are popped left-to-right (the last
    repeats); every release is recorded."""

    def __init__(self, acquire_responses: list[dict]):
        self._acquire_responses = list(acquire_responses)
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, str]] = []

    def acquire(self, plan_id: str) -> dict:
        self.acquire_calls.append(plan_id)
        if not self._acquire_responses:
            return {'status': 'error', 'error': 'no scripted acquire response'}
        return self._acquire_responses.pop(0) if len(self._acquire_responses) > 1 else self._acquire_responses[0]

    def release(self, plan_id: str, admission_id: str) -> dict:
        self.release_calls.append((plan_id, admission_id))
        return {'status': 'success', 'action': 'released'}

    @property
    def released_ids(self) -> list[str]:
        return [aid for _plan, aid in self.release_calls]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch):
    """Never actually sleep 60s in a unit test — patch time.sleep to a no-op."""
    monkeypatch.setattr(bqs.time, 'sleep', lambda _s: None)


def _install_queue(monkeypatch: pytest.MonkeyPatch, double: _QueueDouble) -> None:
    monkeypatch.setattr(bqs, '_acquire', double.acquire)
    monkeypatch.setattr(bqs, '_release_raw', double.release)


# =============================================================================
# No-op passthrough — the backward-compatibility guarantee
# =============================================================================


@pytest.mark.parametrize('plan_id', [None, ''])
def test_no_plan_id_is_pure_noop(monkeypatch, plan_id):
    """A falsy plan_id yields with ZERO queue interaction — plan-less builds run
    completely unchanged."""
    double = _QueueDouble([])
    _install_queue(monkeypatch, double)

    ran = False
    with build_queue_slot(plan_id):
        ran = True

    assert ran is True
    assert double.acquire_calls == []
    assert double.release_calls == []


# =============================================================================
# No title-token machinery — pure concurrency limiter
# =============================================================================


def test_queue_exposes_no_title_token_symbols():
    """The build queue is a pure concurrency limiter and writes no terminal-title
    state — none of the title-token seams exist on the module."""
    assert not hasattr(bqs, '_set_title_token')
    assert not hasattr(bqs, '_push_title_token')
    assert not hasattr(bqs, '_clear_title_token')


# =============================================================================
# Admit-immediately
# =============================================================================


def test_admitted_runs_body_and_releases(monkeypatch):
    """An ``admitted`` acquire runs the body, then releases the slot in the
    finally."""
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
    _install_queue(monkeypatch, double)

    ran = False
    with build_queue_slot('P'):
        ran = True

    assert ran is True
    assert 'P:uuid-1' in double.released_ids


# =============================================================================
# Block-then-admit
# =============================================================================


def test_blocked_then_admitted_polls_and_runs(monkeypatch):
    """A blocked acquire sleeps (mocked), re-polls WITHOUT releasing, and admits
    on the second poll."""
    double = _QueueDouble(
        [
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
            {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-B'},
        ]
    )
    _install_queue(monkeypatch, double)

    ran = False
    with build_queue_slot('P'):
        ran = True

    assert ran is True
    # The blocked id is NOT released before re-polling — re-poll is idempotent so
    # the plan keeps its FIFO position. Only the final admitted id is released in
    # the finally.
    assert 'P:uuid-A' not in double.released_ids
    assert double.released_ids == ['P:uuid-B']


def test_blocked_poll_loop_never_releases_to_preserve_fifo(monkeypatch):
    """FIFO-preservation across retries: while blocked, the wrapper re-polls
    acquire WITHOUT ever releasing the queued id, so the plan's waiting entry
    keeps its FIFO position. The release-in-loop (which shuffled the plan to the
    back of the queue on every poll) is gone — only the FINAL queued id is
    released, in the finally / exhaustion path."""
    double = _QueueDouble(
        [
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
            {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-A'},
        ]
    )
    _install_queue(monkeypatch, double)

    with build_queue_slot('P'):
        pass

    # Three blocked re-polls before admission, but ZERO releases happened inside
    # the loop — the plan never gave up its queue position. The only release is
    # the final cleanup of the admitted id in the finally.
    assert double.released_ids == ['P:uuid-A']
    # Four acquire calls total (initial + three retries) all for the same plan.
    assert double.acquire_calls == ['P', 'P', 'P', 'P']


def test_sleep_called_once_per_retry(monkeypatch):
    """time.sleep fires exactly once between each blocked poll and the re-poll."""
    sleeps: list[int] = []
    monkeypatch.setattr(bqs.time, 'sleep', lambda s: sleeps.append(s))
    double = _QueueDouble(
        [
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-B'},
            {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-C'},
        ]
    )
    _install_queue(monkeypatch, double)

    with build_queue_slot('P'):
        pass

    # Two blocked polls before admission → two sleeps, each the 60s constant.
    assert sleeps == [bqs._WAIT_SECONDS, bqs._WAIT_SECONDS]


# =============================================================================
# Retries exhausted
# =============================================================================


def test_retries_exhausted_raises_and_releases(monkeypatch):
    """Staying blocked past max_retries releases the queued id and raises
    BuildQueueTimeout — the body never runs."""
    monkeypatch.setattr(bqs, '_resolve_max_retries', lambda: 2)
    double = _QueueDouble([{'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-X'}])
    _install_queue(monkeypatch, double)

    ran = False
    with pytest.raises(BuildQueueTimeout) as excinfo:
        with build_queue_slot('P'):
            ran = True

    assert ran is False
    assert excinfo.value.plan_id == 'P'
    assert excinfo.value.max_retries == 2
    # The final queued id was released as cleanup.
    assert 'P:uuid-X' in double.released_ids


def test_acquire_error_is_hard_failure(monkeypatch):
    """An acquire that cannot reach the queue is a hard failure (not best-effort)
    — the build must never silently bypass the concurrency limiter."""
    double = _QueueDouble([{'status': 'error', 'error': 'queue unreachable'}])
    _install_queue(monkeypatch, double)

    with pytest.raises(RuntimeError, match='queue unreachable'):
        with build_queue_slot('P'):
            pass


def test_acquire_error_mid_wait_releases_queued_id(monkeypatch):
    """A hard acquire failure DURING the retry loop releases the already-queued
    admission id instead of leaking it. The wait runs OUTSIDE build_queue_slot's
    finally, so _wait_for_admission must release the queued waiting entry itself
    on any non-return exit — otherwise the slot leaks until reaped."""
    monkeypatch.setattr(bqs, '_resolve_max_retries', lambda: 3)
    double = _QueueDouble([
        {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-Q'},
        {'status': 'error', 'error': 'queue vanished mid-wait'},
    ])
    _install_queue(monkeypatch, double)

    with pytest.raises(RuntimeError, match='queue vanished mid-wait'):
        with build_queue_slot('P'):
            pass

    # The queued waiting entry from the initial blocked acquire was released as
    # cleanup before the RuntimeError propagated — no leaked waiting slot.
    assert 'P:uuid-Q' in double.released_ids


# =============================================================================
# Always-release on body exception
# =============================================================================


def test_body_exception_still_releases(monkeypatch):
    """A body that raises still releases the slot in the finally."""
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
    _install_queue(monkeypatch, double)

    with pytest.raises(ValueError, match='boom'):
        with build_queue_slot('P'):
            raise ValueError('boom')

    assert 'P:uuid-1' in double.released_ids


# =============================================================================
# Release best-effort behaviour
# =============================================================================


def test_release_failure_is_logged_not_raised(monkeypatch):
    """A release that fails is logged at WARNING but never raises — the build
    has already finished."""
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
    _install_queue(monkeypatch, double)
    # Override release to report an error.
    monkeypatch.setattr(bqs, '_release_raw', lambda _p, _i: {'status': 'error', 'error': 'queue gone'})

    # Should not raise despite the release error.
    with build_queue_slot('P'):
        pass


# =============================================================================
# max_retries resolution from marshal.json
# =============================================================================


class TestResolveMaxRetries:
    def test_default_when_block_absent(self, monkeypatch):
        monkeypatch.setattr(bqs, 'read_json', lambda *a, **k: {})
        assert bqs._resolve_max_retries() == bqs._DEFAULT_MAX_RETRIES

    def test_honors_configured_value(self, monkeypatch):
        monkeypatch.setattr(bqs, 'read_json', lambda *a, **k: {'build_queue': {'max_retries': 7}})
        assert bqs._resolve_max_retries() == 7

    def test_non_positive_falls_back(self, monkeypatch):
        monkeypatch.setattr(bqs, 'read_json', lambda *a, **k: {'build_queue': {'max_retries': 0}})
        assert bqs._resolve_max_retries() == bqs._DEFAULT_MAX_RETRIES

    def test_bool_value_falls_back(self, monkeypatch):
        # bool is an int subclass — must NOT be accepted as a retry count.
        monkeypatch.setattr(bqs, 'read_json', lambda *a, **k: {'build_queue': {'max_retries': True}})
        assert bqs._resolve_max_retries() == bqs._DEFAULT_MAX_RETRIES

    def test_non_dict_config_falls_back(self, monkeypatch):
        monkeypatch.setattr(bqs, 'read_json', lambda *a, **k: ['not', 'a', 'dict'])
        assert bqs._resolve_max_retries() == bqs._DEFAULT_MAX_RETRIES


# =============================================================================
# _emit_queue_timeout structured error
# =============================================================================


def test_emit_queue_timeout_renders_structured_error(capsys):
    """The factory's queue-timeout emitter prints a structured queue_saturated
    error and returns a non-zero exit code (the build did not run)."""
    from _build_execute_factory import ERROR_QUEUE_SATURATED, _emit_queue_timeout

    exc = BuildQueueTimeout('P', 10)
    rc = _emit_queue_timeout('python', 'module-tests plan-marshall', 'toon', exc)

    assert rc == 1
    out = capsys.readouterr().out
    assert ERROR_QUEUE_SATURATED in out
    assert 'try again later' in out
    assert 'P' in out


def test_factory_cmd_run_emits_timeout_on_saturation(monkeypatch, capsys):
    """End-to-end through the factory cmd_run: a saturated queue yields the
    structured queue_saturated error without ever running execute_direct."""
    import _build_execute_factory as factory
    from _build_execute import CaptureStrategy

    config = factory.ExecuteConfig(
        tool_name='python',
        unix_wrapper='pw',
        windows_wrapper='pw.bat',
        system_fallback='pwx',
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        build_command_fn=factory.default_build_command_fn,
        scope_fn=lambda a: 'default',
        command_key_fn=factory.default_command_key_fn,
    )

    def _fake_parse_log(_log):  # pragma: no cover - never reached on saturation
        return ([], None, 'SUCCESS')

    _execute_direct, cmd_run = factory.create_execute_handlers(config, _fake_parse_log)

    def _saturated(plan_id):
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            raise factory.BuildQueueTimeout(plan_id, 10)
            yield  # pragma: no cover

        return _cm()

    monkeypatch.setattr(factory, 'build_queue_slot', _saturated)

    args = argparse.Namespace(command_args='module-tests', plan_id='P', format='toon')
    rc = cmd_run(args)

    assert rc == 1
    assert factory.ERROR_QUEUE_SATURATED in capsys.readouterr().out
