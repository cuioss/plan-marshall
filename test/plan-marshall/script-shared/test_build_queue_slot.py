# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
#!/usr/bin/env python3
"""Tests for ``script-shared/scripts/build/_build_queue_slot.py`` (D6).

The build-queue slot wrapper is a pure concurrency limiter: it participates in
the cluster build queue ONLY when ``plan_id`` names a REAL plan, and writes no
terminal-title state. For a plan-less id — falsy OR the ``NO_PLAN`` sentinel —
it is a pure no-op passthrough so plan-less builds run completely unchanged.
These tests cover:

* **No-op passthrough** — a falsy plan_id AND the truthy ``NO_PLAN`` sentinel
  each yield immediately with ZERO queue interaction (the
  backward-compatibility guarantee), while a real plan id still acquires.
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
* **Queue warnings reach BOTH sinks, exactly once per invocation** — each
  ``acquire`` warning is surfaced to stderr AND the plan work log, deduplicated
  by ``code`` across the blocked re-polls, so a build that waits does not repeat
  the identical warning once per poll. Two distinct codes are both surfaced (the
  matched control proving the collapse is per-code, not "at most one"), an empty
  or absent ``warnings`` key surfaces nothing, a plan-less build writes no
  work-log line, a malformed entry is skipped rather than raised on, and a
  warning never blocks the build.

The queue acquire/release seam (``_acquire`` / ``_release_raw``) is mocked
directly, so the tests are independent of whether the queue is reached by a
file-path import or the executor. Every wait-loop test patches ``time.sleep`` to
a no-op so the 60s wait is never slept.

The end-to-end ``cmd_run`` saturation case leaves ``execution_mode`` at its
``auto`` default and depends on the autouse ``_neutralize_daemon_routing``
fixture in ``test/conftest.py`` to hold the D5 ``_route_to_daemon`` seam at its
non-routing outcome — without it, a host with marshalld registered and ready
would route the build away before ``build_queue_slot`` is ever reached.
"""

from __future__ import annotations

import argparse

import pytest

import _build_queue_slot as bqs
from _build_queue_slot import BuildQueueTimeout, build_queue_slot
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL


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


#: The three shapes a plan-less build's ``plan_id`` arrives in. The ids are
#: stated rather than left to pytest: the empty-string row generates no readable
#: id of its own, so the report would name it only by position.
_PLAN_LESS_PLAN_IDS = [None, '', NO_PLAN_SENTINEL]

_PLAN_LESS_PLAN_ID_IDS = [
    'no-plan-id-attribute-value-at-all',
    'an-empty-plan-id',
    'the-explicit-no-plan-sentinel',
]


@pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
def test_no_plan_id_is_pure_noop(monkeypatch, plan_id):
    """A plan-less id yields with ZERO queue interaction — plan-less builds run
    completely unchanged.

    ``NO_PLAN`` is the case that matters and the reason "falsy is the only
    no-op" is no longer the rule: ``build_main`` now resolves every absent
    ``--plan-id`` to that sentinel, and the sentinel is TRUTHY. A falsiness-only
    guard would therefore enrol every ad-hoc CLI build in the shared
    machine-global queue and serialize work that has always run free.
    """
    double = _QueueDouble([])
    _install_queue(monkeypatch, double)

    ran = False
    with build_queue_slot(plan_id):
        ran = True

    assert ran is True
    assert double.acquire_calls == []
    assert double.release_calls == []


def test_a_real_plan_id_still_acquires_a_slot(monkeypatch):
    """The sentinel carve-out is narrow: a REAL plan id still queues.

    Without this counter-case a guard that skipped the queue unconditionally
    would satisfy every no-op assertion above while silently disabling the
    concurrency limiter for every plan-scoped build.
    """
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-real'}])
    _install_queue(monkeypatch, double)

    with build_queue_slot('a-real-plan'):
        pass

    assert double.acquire_calls == ['a-real-plan']
    assert double.released_ids == ['P:uuid-real']


def test_queue_exposes_no_title_token_symbols():
    """The build queue is a pure concurrency limiter and writes no terminal-title
    state — none of the title-token seams exist on the module."""
    assert not hasattr(bqs, '_set_title_token')
    assert not hasattr(bqs, '_push_title_token')
    assert not hasattr(bqs, '_clear_title_token')


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
    double = _QueueDouble(
        [
            {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-Q'},
            {'status': 'error', 'error': 'queue vanished mid-wait'},
        ]
    )
    _install_queue(monkeypatch, double)

    with pytest.raises(RuntimeError, match='queue vanished mid-wait'):
        with build_queue_slot('P'):
            pass

    # The queued waiting entry from the initial blocked acquire was released as
    # cleanup before the RuntimeError propagated — no leaked waiting slot.
    assert 'P:uuid-Q' in double.released_ids


def test_body_exception_still_releases(monkeypatch):
    """A body that raises still releases the slot in the finally."""
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
    _install_queue(monkeypatch, double)

    with pytest.raises(ValueError, match='boom'):
        with build_queue_slot('P'):
            raise ValueError('boom')

    assert 'P:uuid-1' in double.released_ids


def test_release_failure_is_logged_not_raised(monkeypatch):
    """A release that fails is logged at WARNING but never raises — the build
    has already finished."""
    double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
    _install_queue(monkeypatch, double)
    monkeypatch.setattr(bqs, '_release_raw', lambda _p, _i: {'status': 'error', 'error': 'queue gone'})

    # The release error is logged at WARNING, never raised — entering and exiting
    # the slot without an exception is the assertion.
    with build_queue_slot('P'):
        pass


# =============================================================================
# Queue warnings reach BOTH sinks, exactly once per invocation
# =============================================================================

#: The demoted-key warning the queue attaches to every acquire result while the
#: caller's marshal.json still carries the inert key.
_DEMOTION_WARNING = {
    'code': 'per_repo_max_slots_not_in_effect',
    'message': 'marshal.json sets build.queue.max_slots=1, which is NOT in effect',
}

_OTHER_WARNING = {'code': 'some_other_condition', 'message': 'a different condition entirely'}


def _admitted(warnings: list[dict] | None = None, entry_id: str = 'P:uuid-1') -> dict:
    """Build an ``admitted`` acquire result, optionally carrying ``warnings``."""
    result: dict = {'status': 'success', 'admission': 'admitted', 'id': entry_id}
    if warnings is not None:
        result['warnings'] = warnings
    return result


def _blocked(warnings: list[dict] | None = None, entry_id: str = 'P:uuid-1') -> dict:
    """Build a ``blocked`` acquire result, optionally carrying ``warnings``."""
    result: dict = {'status': 'success', 'admission': 'blocked', 'id': entry_id}
    if warnings is not None:
        result['warnings'] = warnings
    return result


@pytest.fixture
def work_log(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Capture ``log_entry`` calls instead of writing to a real plan work log."""
    calls: list[tuple] = []
    monkeypatch.setattr(bqs, 'log_entry', lambda *args: calls.append(args))
    return calls


def test_a_warning_reaches_stderr_and_the_work_log(monkeypatch, capsys, work_log):
    """Both sinks, because neither alone is sufficient.

    stderr is the only sink a build subprocess has without a configured logging
    handler; the work log is the PERSISTENT record a later "why was my cap
    ignored?" scan reads. Emitting to one only would either lose the warning
    from the live run or lose it from the audit trail.
    """
    _install_queue(monkeypatch, _QueueDouble([_admitted([_DEMOTION_WARNING])]))

    with build_queue_slot('P'):
        pass

    assert _DEMOTION_WARNING['message'] in capsys.readouterr().err
    assert len(work_log) == 1
    assert work_log[0][0] == 'work'
    assert work_log[0][1] == 'P'
    assert work_log[0][2] == 'WARNING'
    assert _DEMOTION_WARNING['message'] in work_log[0][3]


def test_a_warning_is_surfaced_exactly_once_across_blocked_re_polls(monkeypatch, capsys, work_log):
    """Four acquires carrying the SAME warning produce ONE line in each sink.

    This is the deduplication assertion and the reason it is keyed on ``code``:
    a blocked build re-polls once per wait interval, so a per-acquire emission
    would repeat the identical warning for the whole wait and bury the rest of
    the build output under it.
    """
    monkeypatch.setattr(bqs, '_resolve_max_retries', lambda: 5)
    _install_queue(
        monkeypatch,
        _QueueDouble(
            [
                _blocked([_DEMOTION_WARNING]),
                _blocked([_DEMOTION_WARNING]),
                _blocked([_DEMOTION_WARNING]),
                _admitted([_DEMOTION_WARNING]),
            ]
        ),
    )

    with build_queue_slot('P'):
        pass

    assert capsys.readouterr().err.count(_DEMOTION_WARNING['message']) == 1
    assert len(work_log) == 1


def test_two_distinct_codes_are_both_surfaced(monkeypatch, capsys, work_log):
    """The matched control for the dedup test: it collapses by CODE, not to one.

    Without this, the assertion above would pass equally against an
    implementation that emitted at most one warning ever — which would silently
    swallow every condition after the first.
    """
    _install_queue(monkeypatch, _QueueDouble([_admitted([_DEMOTION_WARNING, _OTHER_WARNING])]))

    with build_queue_slot('P'):
        pass

    err = capsys.readouterr().err
    assert _DEMOTION_WARNING['message'] in err
    assert _OTHER_WARNING['message'] in err
    assert len(work_log) == 2


def test_an_empty_warnings_list_surfaces_nothing(monkeypatch, capsys, work_log):
    """A migrated repository gets no noise — the common case must stay silent."""
    _install_queue(monkeypatch, _QueueDouble([_admitted([])]))

    with build_queue_slot('P'):
        pass

    assert capsys.readouterr().err == ''
    assert work_log == []


def test_an_absent_warnings_key_surfaces_nothing(monkeypatch, capsys, work_log):
    """A result predating the ``warnings`` field must not crash the build.

    The queue always sends the key now, so this is the defensive boundary for a
    stale in-process copy — a warning is a report, and failing a legitimately
    admitted build over a missing report field would be the wrong trade.
    """
    _install_queue(monkeypatch, _QueueDouble([_admitted()]))

    with build_queue_slot('P'):
        pass

    assert capsys.readouterr().err == ''
    assert work_log == []


@pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
def test_a_plan_less_build_writes_no_work_log_line(monkeypatch, capsys, work_log, plan_id):
    """A plan-less build has no plan work log to write to, and writes none.

    It never reaches the queue at all (the no-op passthrough), so there is no
    acquire result to carry a warning — the backward-compatibility guarantee
    covers the reporting surface too, not just the slot.
    """
    _install_queue(monkeypatch, _QueueDouble([_admitted([_DEMOTION_WARNING])]))

    with build_queue_slot(plan_id):
        pass

    assert work_log == []
    assert capsys.readouterr().err == ''


def test_a_warning_never_blocks_the_build(monkeypatch, work_log):
    """Reporting is not gating: the body still runs and the slot still releases."""
    double = _QueueDouble([_admitted([_DEMOTION_WARNING])])
    _install_queue(monkeypatch, double)

    ran = False
    with build_queue_slot('P'):
        ran = True

    assert ran is True
    assert double.released_ids == ['P:uuid-1']


@pytest.mark.parametrize(
    'malformed',
    [
        pytest.param(['not-a-dict'], id='entry-is-not-a-mapping'),
        pytest.param([{'message': 'no code'}], id='entry-has-no-code'),
        pytest.param([{'code': 'no_message'}], id='entry-has-no-message'),
        pytest.param([{'code': 1, 'message': 2}], id='entry-fields-are-not-strings'),
    ],
)
def test_a_malformed_warning_entry_is_skipped_not_raised(monkeypatch, capsys, work_log, malformed):
    """A queue result that fails to describe itself must not fail the build."""
    _install_queue(monkeypatch, _QueueDouble([_admitted(malformed)]))

    ran = False
    with build_queue_slot('P'):
        ran = True

    assert ran is True
    assert work_log == []


#: ``(the marshal.json body ``read_json`` returns, resolved max_retries)``. Only
#: one row configures a usable value; every other shape — a missing block, a
#: non-positive count, a bool (an int SUBCLASS, so it would pass a naive
#: isinstance check), and two non-mapping bodies — must resolve to the default
#: rather than to whatever the malformed value happens to coerce to.
_MAX_RETRIES_CASES = [
    ({}, bqs._DEFAULT_MAX_RETRIES),
    ({'build': {'queue': {'max_retries': 7}}}, 7),
    ({'build': {'queue': {'max_retries': 0}}}, bqs._DEFAULT_MAX_RETRIES),
    ({'build': {'queue': {'max_retries': True}}}, bqs._DEFAULT_MAX_RETRIES),
    (['not', 'a', 'dict'], bqs._DEFAULT_MAX_RETRIES),
    ({'build': 'not-a-dict'}, bqs._DEFAULT_MAX_RETRIES),
]

_MAX_RETRIES_IDS = [
    'no-build-block-at-all',
    'configured-positive-count',
    'non-positive-count',
    'bool-is-not-a-count',
    'config-body-is-not-a-mapping',
    'build-block-is-not-a-mapping',
]


class TestResolveMaxRetries:
    @pytest.mark.parametrize('config,expected', _MAX_RETRIES_CASES, ids=_MAX_RETRIES_IDS)
    def test_max_retries_resolution(self, monkeypatch, config, expected):
        monkeypatch.setattr(bqs, 'read_json', lambda *_a, **_k: config)

        assert bqs._resolve_max_retries() == expected


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
