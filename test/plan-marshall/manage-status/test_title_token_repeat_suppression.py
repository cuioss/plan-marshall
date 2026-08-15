#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for repeat suppression on the ``title-token set`` work-log line.

``title-token set`` is driven by the ``PreToolUse:Bash`` render hook on every
build command, so a run with many build calls re-asserts the SAME
``(owner, state)`` pair over and over. Emitting the ``[MANAGE-STATUS] Title
token: …`` INFO line unconditionally turned that into repeated identical
work-log noise carrying no new information.

The rule these tests pin: the line is emitted only when the set CHANGES the
stored ``(owner, state)`` pair. A re-assertion of the pair already stored is a
silent no-op on the log — while still refreshing ``set_at`` in status.json, so
the aged-token staleness predicate keeps seeing a live token.

``set_at`` is deliberately NOT part of the comparison: it changes on every
call by construction, so including it would make every set "changed" and
suppress nothing.

The suppression decision is published on the return payload as ``changed`` so
a consumer can read it from the TOON rather than inferring it from log
side-effects.
"""

from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_ttrs_lifecycle'
)
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_ttrs_query')
_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_ttrs_core')

cmd_create = _lifecycle.cmd_create
cmd_title_token = _query.cmd_title_token
read_title_token = _core.read_title_token


class _LogSpy:
    """Capture ``log_entry`` calls made by the command under test."""

    def __init__(self):
        self.messages: list[str] = []

    def __call__(self, _channel, _plan_id, _level, message):
        self.messages.append(message)

    @property
    def title_token_lines(self) -> list[str]:
        return [m for m in self.messages if 'Title token:' in m]


def _spy(monkeypatch) -> _LogSpy:
    spy = _LogSpy()
    monkeypatch.setattr(_query, 'log_entry', spy)
    return spy


def _plan(plan_id):
    """Materialize ``plan_id`` so the title-token verbs have a status.json."""
    cmd_create(Namespace(plan_id=plan_id, title='T', phases='1-init', force=False))
    return plan_id


def _set(plan_id, state, owner='build-hook'):
    return cmd_title_token(
        Namespace(plan_id=plan_id, token_verb='set', state=state, owner=owner)
    )


def _clear(plan_id, owner='build-hook'):
    return cmd_title_token(Namespace(plan_id=plan_id, token_verb='clear', owner=owner))


class TestRepeatSuppression:
    def test_first_set_emits_the_line(self, plan_context, monkeypatch):
        plan_id = _plan('tt-first')
        spy = _spy(monkeypatch)
        result = _set(plan_id, 'build-busy')
        assert result is not None and result['status'] == 'success'
        assert result['changed'] is True
        assert len(spy.title_token_lines) == 1

    def test_repeated_identical_set_emits_no_further_line(self, plan_context, monkeypatch):
        """The defect: the build hook re-asserts the same pair on every build."""
        plan_id = _plan('tt-repeat')
        spy = _spy(monkeypatch)
        _set(plan_id, 'build-busy')
        for _ in range(4):
            result = _set(plan_id, 'build-busy')
            assert result['changed'] is False

        assert len(spy.title_token_lines) == 1, (
            'only the first set may log; a re-assertion of the stored '
            f'(owner, state) pair must stay silent, got {spy.title_token_lines}'
        )

    def test_state_change_emits_a_new_line(self, plan_context, monkeypatch):
        plan_id = _plan('tt-state')
        spy = _spy(monkeypatch)
        _set(plan_id, 'build-busy')
        result = _set(plan_id, 'lock-owned')
        assert result['changed'] is True
        assert len(spy.title_token_lines) == 2

    def test_owner_change_emits_a_new_line(self, plan_context, monkeypatch):
        """Same state, different owner — the record's owner is part of its value."""
        plan_id = _plan('tt-owner')
        spy = _spy(monkeypatch)
        _set(plan_id, 'build-busy', owner='build-hook')
        result = _set(plan_id, 'build-busy', owner='merge-lock')
        assert result['changed'] is True
        assert len(spy.title_token_lines) == 2

    def test_set_after_clear_emits_a_line_again(self, plan_context, monkeypatch):
        """A cleared token is absent, so the next set is a genuine change."""
        plan_id = _plan('tt-recycle')
        spy = _spy(monkeypatch)
        _set(plan_id, 'build-busy')
        _clear(plan_id)
        result = _set(plan_id, 'build-busy')
        assert result['changed'] is True
        assert len(spy.title_token_lines) == 2

    def test_set_after_the_token_aged_out_emits_a_line_again(
        self, plan_context, monkeypatch
    ):
        """An aged token READS as absent, so re-asserting it is a real change.

        Staleness is a read-side rule: a record past the threshold is invisible
        to every consumer, including the renderers. Comparing the raw stored
        field would report `changed: false` and stay silent about a token the
        renderers had already stopped honouring — so the comparison goes
        through the staleness-aware accessor.
        """
        plan_id = _plan('tt-aged')
        spy = _spy(monkeypatch)
        _set(plan_id, 'build-busy')
        _backdate(plan_context, plan_id, seconds=_core.TITLE_TOKEN_STALE_AFTER_SECONDS + 60)

        result = _set(plan_id, 'build-busy')
        assert result['changed'] is True, (
            'the stored record had aged past the staleness threshold, so it read '
            'as absent — re-asserting it is an absent→present change'
        )
        assert len(spy.title_token_lines) == 2


class TestSuppressionDoesNotWeakenTheRecord:
    def test_suppressed_set_still_refreshes_set_at(self, plan_context):
        """Suppressing the LOG must not suppress the WRITE.

        The aged-token staleness predicate reads ``set_at``; a re-assertion
        that skipped the write would let a live token age out mid-build.
        """
        plan_id = _plan('tt-refresh')
        _set(plan_id, 'build-busy')
        first = _read_token(plan_context, plan_id)['set_at']

        _backdate(plan_context, plan_id)
        aged = _read_token(plan_context, plan_id)['set_at']
        assert aged != first, 'fixture must actually backdate the record'

        result = _set(plan_id, 'build-busy')
        assert result['changed'] is False, 'same pair — the log line is suppressed'
        assert _read_token(plan_context, plan_id)['set_at'] != aged, (
            'a suppressed set must still refresh set_at'
        )

    def test_suppressed_set_still_returns_the_record(self, plan_context):
        plan_id = _plan('tt-payload')
        _set(plan_id, 'build-busy')
        result = _set(plan_id, 'build-busy')
        assert result['title_token']['state'] == 'build-busy'
        assert result['title_token']['owner'] == 'build-hook'


# =============================================================================
# Helpers that touch status.json directly
# =============================================================================


def _read_token(plan_context, plan_id):
    import json

    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    return json.loads(status_file.read_text(encoding='utf-8'))['title_token']


def _backdate(plan_context, plan_id, seconds: int = 30):
    import json
    from datetime import UTC, datetime, timedelta

    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8'))
    aged = datetime.now(UTC) - timedelta(seconds=seconds)
    status['title_token']['set_at'] = aged.strftime('%Y-%m-%dT%H:%M:%SZ')
    status_file.write_text(json.dumps(status), encoding='utf-8')
