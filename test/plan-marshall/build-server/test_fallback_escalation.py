#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""D5: a sustained run of daemon-unreachable fallbacks escalates once, not N times.

A one-off in-process fallback and a daemon gone all run are indistinguishable when
the N+1st fallback is logged exactly like the first. ``_update_fallback_streak``
counts CONSECUTIVE daemon-unreachable fallbacks per plan and, once the count
crosses ``_FALLBACK_WARN_STREAK``, returns ONE ERROR naming the transition in
place of the repeated WARNING; a routed build resets the streak. These tests pin
the state machine directly and the emission integration through
``_record_resolution``.
"""

from __future__ import annotations

import pytest
from _build_extension_fixtures import build_scripts_dir

build_scripts_dir()

import _build_execute_factory as factory

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Isolate the machine-global home so the streak state stays in tmp."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))


def _fallback(plan_id: str = 'p', reason: str = 'socket_absent'):
    return factory._update_fallback_streak('in_process', reason, plan_id)


# =============================================================================
# _update_fallback_streak — the state machine
# =============================================================================


def test_streak_below_threshold_never_escalates():
    # The first _FALLBACK_WARN_STREAK fallbacks each keep the per-build WARNING.
    for _ in range(factory._FALLBACK_WARN_STREAK):
        message, suppress = _fallback()
        assert message is None
        assert suppress is False


def test_crossing_the_threshold_escalates_exactly_once():
    for _ in range(factory._FALLBACK_WARN_STREAK):
        _fallback()

    # The fallback that crosses the threshold returns the one-time transition
    # message AND suppresses that build's WARNING (the ERROR replaces it).
    message, suppress = _fallback()
    assert message is not None
    assert suppress is True

    # Every further consecutive fallback is suppressed with NO new ERROR.
    for _ in range(3):
        again, again_suppress = _fallback()
        assert again is None
        assert again_suppress is True


def test_transition_message_names_the_reachable_unreachable_transition():
    # A routed build first records reachability, then the daemon goes unreachable.
    factory._update_fallback_streak('routed', None, 'p')
    message = None
    for _ in range(factory._FALLBACK_WARN_STREAK + 1):
        message, _suppress = _fallback()

    assert message is not None
    assert 'last reachable at' in message
    assert 'unreachable since' in message
    # The count of degraded builds is named (crossing at threshold + 1).
    assert f'{factory._FALLBACK_WARN_STREAK + 1} builds degraded' in message
    assert 'suppressed until the daemon is reachable again' in message


def test_routed_build_resets_the_streak():
    for _ in range(factory._FALLBACK_WARN_STREAK + 2):
        _fallback()  # escalate

    # A routed build resets — the daemon is reachable again.
    factory._update_fallback_streak('routed', None, 'p')

    # The next fallback starts a fresh streak: a per-build WARNING, not a repeat
    # suppression, and no immediate re-escalation.
    message, suppress = _fallback()
    assert message is None
    assert suppress is False


def test_streak_is_per_plan():
    # Escalate plan a; plan b's independent streak is unaffected.
    for _ in range(factory._FALLBACK_WARN_STREAK + 1):
        _fallback(plan_id='a')
    message, suppress = _fallback(plan_id='b')
    assert message is None
    assert suppress is False


def test_disabled_reason_does_not_count_toward_the_streak():
    # A by-design in-process routing (unregistered project) is not a degradation.
    for _ in range(factory._FALLBACK_WARN_STREAK + 5):
        message, suppress = _fallback(reason='disabled')
        assert message is None
        assert suppress is False


def test_state_io_failure_is_fail_open(monkeypatch):
    # A broken state read must never abort a build — it degrades to no-escalation.
    def _boom():
        raise OSError('disk gone')

    monkeypatch.setattr(factory, '_read_fallback_state', _boom)

    message, suppress = _fallback()
    assert message is None
    assert suppress is False


# =============================================================================
# _record_resolution — emission integration
# =============================================================================


@pytest.fixture
def captured(monkeypatch) -> list[tuple[str, str | None, str, str]]:
    calls: list[tuple[str, str | None, str, str]] = []
    monkeypatch.setattr(
        factory,
        'log_entry',
        lambda log_type, plan_id, level, message: calls.append((log_type, plan_id, level, message)),
    )
    return calls


def _record_fallback(plan_id: str = 'p'):
    factory._record_resolution('auto', 'in_process', 'socket_absent', _NOTATION, plan_id)


def test_record_resolution_escalates_to_one_error_after_the_streak(captured, capsys):
    # The first N fallbacks capture a per-build WARNING each.
    for _ in range(factory._FALLBACK_WARN_STREAK):
        _record_fallback()
    warnings = [c for c in captured if c[2] == 'WARNING']
    assert len(warnings) == factory._FALLBACK_WARN_STREAK
    assert all('resolved=in_process' in c[3] for c in warnings)
    # Every fallback names its serialization state from the first one — a
    # down daemon never reads as a normally-scheduled build.
    assert all('serialization=fallback-slot' in c[3] for c in warnings)

    captured.clear()
    # The crossing fallback captures ONE ERROR transition — not another WARNING.
    _record_fallback()
    assert len(captured) == 1
    log_type, plan_id, level, message = captured[0]
    assert (log_type, plan_id, level) == ('work', 'p', 'ERROR')
    assert 'marshalld unreachable' in message
    # The one-time transition names the accurate failure model: daemon
    # scheduling unavailable, fallback-slot serialization active for plan
    # builds, plan-less builds unserialized — and the OOM risk of running
    # concurrent suites without serialization.
    assert 'fallback slot' in message
    assert 'unserialized' in message
    assert 'OOM' in message
    # The stderr parity line is still present for THIS build.
    assert '[BUILD-SERVER] resolved build' in capsys.readouterr().err

    captured.clear()
    # A further fallback logs NOTHING to the work log (the repeat is suppressed),
    # yet the stderr parity line still fires.
    _record_fallback()
    assert captured == []
    assert '[BUILD-SERVER] resolved build' in capsys.readouterr().err


def test_record_resolution_stderr_parity_line_always_emitted(captured, capsys):
    # Even deep into a suppressed outage, the per-build stderr line is emitted so a
    # local console still shows this build fell back.
    for _ in range(factory._FALLBACK_WARN_STREAK + 5):
        _record_fallback()
    err = capsys.readouterr().err
    assert err.count('[BUILD-SERVER] resolved build') == factory._FALLBACK_WARN_STREAK + 5


def test_plan_less_escalation_reaches_stderr_only(captured, capsys):
    # A plan-less build has no work log; the transition still reaches stderr but
    # captures nothing.
    for _ in range(factory._FALLBACK_WARN_STREAK + 1):
        factory._record_resolution('auto', 'in_process', 'socket_absent', _NOTATION, None)
    assert captured == []
    err = capsys.readouterr().err
    assert 'marshalld unreachable' in err


def test_routed_build_names_daemon_scheduling(captured, capsys):
    """A daemon-routed build names `serialization=daemon-scheduled`.

    Pairs with the fallback assertion above: without it, a resolution line
    carrying no serialization token would satisfy the fallback pin while a
    routed build stayed indistinguishable from it.
    """
    factory._record_resolution('auto', 'routed', None, _NOTATION, 'p')

    assert len(captured) == 1
    _log_type, _plan_id, level, message = captured[0]
    assert level == 'INFO'
    assert 'serialization=daemon-scheduled' in message
    assert 'serialization=fallback-slot' not in message
    err = capsys.readouterr().err
    assert 'serialization=daemon-scheduled' in err


def test_plan_less_fallback_is_labeled_unserialized(captured, capsys):
    """A plan-less in-process build bypasses the fallback slot, so it must
    not be labeled `fallback-slot`.

    Without this control, a label derived from `resolved` alone would report
    a serialized lane for a build that ran with no serialization at all —
    the exact failure model the OOM escalation warns about.
    """
    factory._record_resolution('auto', 'in_process', 'socket_absent', _NOTATION, None)

    assert captured == []
    err = capsys.readouterr().err
    assert 'serialization=unserialized' in err
    assert 'serialization=fallback-slot' not in err


def test_unknown_routing_outcome_is_labeled_unknown(captured, capsys):
    """An unrecognized `resolved` value reports `unknown`, never a lane.

    A `.get()` default of a real lane would silently bless whatever new
    routing branch added a value without extending the map — false
    serialization metadata. `unknown` fails closed with an explicit state.
    """
    factory._record_resolution('auto', 'mystery-lane', None, _NOTATION, 'p')

    assert len(captured) == 1
    _log_type, _plan_id, _level, message = captured[0]
    assert 'serialization=unknown' in message
    err = capsys.readouterr().err
    assert 'serialization=unknown' in err
