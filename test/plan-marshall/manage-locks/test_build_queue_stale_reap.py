#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Scope: reaping a stale active entry on the next acquire or release, the
``active_since`` stamp every admission path must leave, and the adaptive staleness
threshold — now a TOP-LEVEL ``upper_limit_seconds`` field of the machine-global
``build-queue.json`` itself rather than a per-repo ``run-configuration.json`` key.

The threshold's move is what these tests pin: it is seeded IN the queue state, read
by the reaper from the state it is already mutating, recomputed by ``release``
inside that same mutation, and read/written by the ``limit get`` / ``limit set``
verbs. A per-repo value surviving in ``run-configuration.json`` is REPORTED by
``limit get`` and never honoured.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from _build_queue_fixtures import (
    _FRESH_AGE_SECONDS,
    _STALE_AGE_SECONDS,
    _init_git_repo,
    _make_live_plan,
    _read_lock_log,
    _read_queue,
    _seed_active_entry,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)

# The threshold's home: a top-level field of the queue's own state. Read off the
# module under test rather than restated, so a rename cannot leave these tests
# asserting a key nothing writes.
_FIELD = build_queue.UPPER_LIMIT_FIELD
_FLOOR = build_queue.UPPER_LIMIT_FLOOR_SECONDS
_CEILING = build_queue.UPPER_LIMIT_CEILING_SECONDS
_QUEUE_STATE = build_queue.SOURCE_QUEUE_STATE
_DEFAULT_FLOOR = build_queue.SOURCE_DEFAULT_FLOOR


def _seed_state(
    queue_path: Path,
    *,
    upper_limit: object = None,
    active: list[dict] | None = None,
    waiting: list[dict] | None = None,
) -> None:
    """Seed the queue state, optionally carrying the top-level threshold field.

    ``upper_limit=None`` writes NO ``upper_limit_seconds`` key — the unconfigured
    case, which must resolve to the floor under ``default_floor`` rather than read
    as a configured floor. Written here rather than through
    ``_build_queue_fixtures._seed_active_entry`` because the threshold is a
    top-level field of the state, not a property of an entry.
    """
    state: dict = {'active': active or [], 'waiting': waiting or [], 'run_log': []}
    if upper_limit is not None:
        state[_FIELD] = upper_limit
    _write_queue(queue_path, state)


def _stored_limit(queue_path: Path) -> object:
    """The persisted threshold field, or ``None`` when it was never materialised."""
    return _read_queue(queue_path).get(_FIELD)


def _active_entry(entry_id: str, plan_id: str, *, held_seconds: float) -> dict:
    """An active entry whose ``active_since`` puts it ``held_seconds`` in the past."""
    import time

    return {'id': entry_id, 'plan_id': plan_id, 'ts': 0.0, 'active_since': time.time() - held_seconds}


class TestStaleReap:
    def test_stale_active_entry_is_reaped_on_next_acquire(self, isolated_base: dict) -> None:
        """An active entry whose active_since is older than 2 × upper_limit is
        reaped on the next acquire (slot freed), and a WARN [LOCK] reaped-stale
        event with the reaped id + held duration is emitted."""
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        # The reaped holder's plan dir exists → it is LIVE (so the dead-holder
        # prune does NOT clear it; only the time-based reaper does).
        _make_live_plan(base, 'plan-stale')
        stale_id = 'plan-stale:stale-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=stale_id,
            plan_id='plan-stale',
            active_since=time.time() - _STALE_AGE_SECONDS,
        )

        _make_live_plan(base, 'plan-new')
        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        # The stale slot was reaped, freeing the single slot → plan-new admitted.
        assert result['admission'] == 'admitted'
        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert stale_id not in active_ids
        assert [e['plan_id'] for e in state['active']] == ['plan-new']

        # A WARN reaped-stale [LOCK] event was emitted for the reaped id.
        content = _read_lock_log()
        assert f'[LOCK] (build:reaped-stale) {stale_id}' in content
        assert 'WARNING' in content
        assert 'held:' in content
        assert 'threshold: 1200' in content  # 2 × 600 default

    def test_stale_active_entry_is_reaped_on_next_release(self, isolated_base: dict) -> None:
        """validate_lock_queue also runs on release: a stale active entry is reaped
        when an UNRELATED id is released (the release of an absent id is a no-op,
        but the implicit reaper still fires inside the same mutation)."""
        import time

        base = isolated_base['base']
        _make_live_plan(base, 'plan-stale')
        stale_id = 'plan-stale:stale-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=stale_id,
            plan_id='plan-stale',
            active_since=time.time() - _STALE_AGE_SECONDS,
        )

        # Release an absent id — the release itself is a no-op, but the implicit
        # reaper runs and clears the stale entry.
        build_queue.run_release(Namespace(plan_id='plan-other', id='plan-other:ghost'))

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == []
        content = _read_lock_log()
        assert f'[LOCK] (build:reaped-stale) {stale_id}' in content

    def test_fresh_active_entry_is_not_reaped(self, isolated_base: dict) -> None:
        """An active entry whose active_since is within 2 × upper_limit is NOT
        reaped — only over-age entries are reclaimed."""
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 2)
        _make_live_plan(base, 'plan-fresh')
        fresh_id = 'plan-fresh:fresh-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=fresh_id,
            plan_id='plan-fresh',
            active_since=time.time() - _FRESH_AGE_SECONDS,
        )

        _make_live_plan(base, 'plan-new')
        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert fresh_id in active_ids  # the fresh holder survived
        content = _read_lock_log()
        assert 'reaped-stale' not in content

    def test_entry_without_active_since_is_not_reaped_on_first_contact(self, isolated_base: dict) -> None:
        """An active entry written before D5 shipped (NO active_since key) is
        treated as `now` and is therefore never reaped on first contact."""
        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 2)
        _make_live_plan(base, 'plan-legacy')
        legacy_id = 'plan-legacy:legacy-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=legacy_id,
            plan_id='plan-legacy',
            active_since=None,  # pre-existing entry, no active_since
        )

        _make_live_plan(base, 'plan-new')
        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert legacy_id in active_ids
        assert 'reaped-stale' not in _read_lock_log()

    def test_reaped_slot_fifo_promotes_waiter_with_fresh_active_since(self, isolated_base: dict) -> None:
        """When a stale entry is reaped and a waiter exists, the waiter is
        FIFO-promoted into the freed slot and gets a fresh active_since."""
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        _make_live_plan(base, 'plan-stale')
        _make_live_plan(base, 'plan-wait')
        stale_id = 'plan-stale:stale-uuid'
        wait_id = 'plan-wait:wait-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': stale_id,
                        'plan_id': 'plan-stale',
                        'ts': 0.0,
                        'active_since': time.time() - _STALE_AGE_SECONDS,
                    }
                ],
                'waiting': [{'id': wait_id, 'plan_id': 'plan-wait', 'ts': 1.0}],
                'run_log': [],
            },
        )

        # plan-wait re-polls acquire: the reaper clears the stale slot and
        # promotes plan-wait (the FIFO head) into it.
        result = build_queue.run_acquire(Namespace(plan_id='plan-wait'))
        assert result['admission'] == 'admitted'
        assert result['id'] == wait_id

        state = _read_queue(isolated_base['queue_path'])
        active = state['active']
        assert [e['id'] for e in active] == [wait_id]
        assert state['waiting'] == []
        # The promoted waiter has a fresh active_since (it is only now active).
        assert 'active_since' in active[0]
        assert active[0]['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_first_acquire(self, isolated_base: dict) -> None:
        """active_since is stamped on a first-acquire admit."""
        import time

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'
        state = _read_queue(isolated_base['queue_path'])
        entry = state['active'][0]
        assert 'active_since' in entry
        assert entry['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_idempotent_waiting_promotion(self, isolated_base: dict) -> None:
        """active_since is stamped when a blocked plan re-polls and is promoted."""
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert w1['admission'] == 'blocked'

        # Release the holder so a slot frees, then plan-w1 re-polls → promoted.
        build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        re_w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert re_w1['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        promoted = next(e for e in state['active'] if e['id'] == w1['id'])
        assert 'active_since' in promoted
        assert promoted['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_release_fifo_promote(self, isolated_base: dict) -> None:
        """active_since is stamped on a release FIFO-promote."""
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert w1['admission'] == 'blocked'

        rel = build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        assert rel['promoted'] == w1['id']

        state = _read_queue(isolated_base['queue_path'])
        promoted = next(e for e in state['active'] if e['id'] == w1['id'])
        assert 'active_since' in promoted
        assert promoted['active_since'] >= time.time() - _FRESH_AGE_SECONDS


class TestThresholdResolution:
    """``upper_limit_seconds`` resolves from the QUEUE STATE, naming its source.

    The source partition is the whole point: the fallback IS the floor, so a
    returned 600 cannot otherwise be told apart from a configured 600.
    """

    def test_unconfigured_state_resolves_to_the_floor_as_default_floor(self, isolated_base: dict) -> None:
        """An absent field resolves to the floor under ``default_floor``."""
        _seed_state(isolated_base['queue_path'])

        got = build_queue.run_limit_get(Namespace())

        assert got['value'] == _FLOOR
        assert got['source'] == _DEFAULT_FLOOR
        assert got['reap_threshold_seconds'] == 2 * _FLOOR
        # The read must not materialise the field — that would turn every later
        # read from `default_floor` into `queue_state`.
        assert _stored_limit(isolated_base['queue_path']) is None

    def test_configured_state_resolves_as_queue_state(self, isolated_base: dict) -> None:
        """A valid positive int resolves under ``queue_state``, reap = 2 x value."""
        _seed_state(isolated_base['queue_path'], upper_limit=1800)

        got = build_queue.run_limit_get(Namespace())

        assert got['value'] == 1800
        assert got['source'] == _QUEUE_STATE
        assert got['reap_threshold_seconds'] == 3600

    def test_below_floor_stored_value_clamps_up_but_stays_configured(self, isolated_base: dict) -> None:
        """A configured-but-too-low value clamps to the floor, source ``queue_state``.

        The value matches the unconfigured case exactly; only the SOURCE separates
        them, which is why the source is asserted rather than the value alone.
        """
        _seed_state(isolated_base['queue_path'], upper_limit=100)

        got = build_queue.run_limit_get(Namespace())

        assert got['value'] == _FLOOR
        assert got['source'] == _QUEUE_STATE

    def test_unusable_stored_values_read_as_the_floor(self, isolated_base: dict) -> None:
        """A bool, a non-positive int and a string all resolve to ``default_floor``.

        ``True`` is the load-bearing case: it is an ``int`` subclass, so an
        unguarded read would apply a ONE-SECOND reap threshold and reclaim every
        live holder on sight.
        """
        for unusable in (True, 0, -1, '1800', 1800.5, None):
            _seed_state(isolated_base['queue_path'])
            state = _read_queue(isolated_base['queue_path'])
            state[_FIELD] = unusable
            _write_queue(isolated_base['queue_path'], state)

            got = build_queue.run_limit_get(Namespace())

            assert got['value'] == _FLOOR, f'{unusable!r} should read as the floor'
            assert got['source'] == _DEFAULT_FLOOR, f'{unusable!r} should be unusable'


class TestReaperReadsTheQueueStateThreshold:
    """The reaper takes the threshold from the state it is already mutating."""

    def test_configured_threshold_spares_an_entry_the_floor_would_reap(self, isolated_base: dict) -> None:
        """A 2000 s hold survives under a configured 1800 s threshold.

        Under the unconfigured floor the reap threshold is 1200 s and this entry
        would be reclaimed, so the survival is attributable to the configured
        value and to nothing else.
        """
        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 2)
        _make_live_plan(base, 'plan-long')
        _make_live_plan(base, 'plan-new')
        long_id = 'plan-long:long-uuid'
        _seed_state(
            isolated_base['queue_path'],
            upper_limit=1800,  # reap threshold 3600 s
            active=[_active_entry(long_id, 'plan-long', held_seconds=2000.0)],
        )

        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        assert long_id in [e['id'] for e in state['active']]
        assert 'reaped-stale' not in _read_lock_log()

    def test_reaped_event_names_the_configured_threshold_applied(self, isolated_base: dict) -> None:
        """The ``[LOCK]`` reaped-stale event carries the threshold actually applied.

        The threshold is resolved INSIDE the mutation now, so the emission site
        has no other way to name the value the reap was judged against.
        """
        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 2)
        _make_live_plan(base, 'plan-stale')
        _make_live_plan(base, 'plan-new')
        stale_id = 'plan-stale:stale-uuid'
        _seed_state(
            isolated_base['queue_path'],
            upper_limit=700,  # reap threshold 1400 s
            active=[_active_entry(stale_id, 'plan-stale', held_seconds=5000.0)],
        )

        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        content = _read_lock_log()
        assert f'[LOCK] (build:reaped-stale) {stale_id}' in content
        assert 'threshold: 1400' in content  # 2 x the CONFIGURED 700, not 2 x 600


class TestAdaptiveThresholdRecompute:
    """``release`` recomputes ``max(current, held)`` clamped, INSIDE the mutation."""

    def test_release_grows_the_threshold_in_the_queue_state(self, isolated_base: dict) -> None:
        """A hold longer than the resolved threshold persists it into the state."""
        base = isolated_base['base']
        _make_live_plan(base, 'plan-mid')
        mid_id = 'plan-mid:mid-uuid'
        # Unconfigured → threshold 1200 s, so a 1000 s hold is not reaped first.
        _seed_state(
            isolated_base['queue_path'],
            active=[_active_entry(mid_id, 'plan-mid', held_seconds=1000.0)],
        )

        rel = build_queue.run_release(Namespace(plan_id='plan-mid', id=mid_id))
        assert rel['action'] == 'released'

        stored = _stored_limit(isolated_base['queue_path'])
        assert isinstance(stored, int)
        assert stored >= 1000
        assert build_queue.run_limit_get(Namespace())['source'] == _QUEUE_STATE

    def test_release_recompute_clamps_to_the_ceiling(self, isolated_base: dict) -> None:
        """An over-ceiling observation persists the ceiling exactly, never higher.

        Seeded at 2000 s (reap threshold 4000 s) so the 3900 s hold is not reaped
        before the release can recompute — and so the stored value MOVES, which is
        what makes the clamp observable rather than a coincidence of the seed.
        """
        base = isolated_base['base']
        _make_live_plan(base, 'plan-long')
        long_id = 'plan-long:long-uuid'
        _seed_state(
            isolated_base['queue_path'],
            upper_limit=2000,
            active=[_active_entry(long_id, 'plan-long', held_seconds=3900.0)],
        )

        rel = build_queue.run_release(Namespace(plan_id='plan-long', id=long_id))
        assert rel['action'] == 'released'

        assert _stored_limit(isolated_base['queue_path']) == _CEILING

    def test_release_never_lowers_a_configured_threshold(self, isolated_base: dict) -> None:
        """The threshold is monotonic-up: a short hold leaves a higher value alone."""
        base = isolated_base['base']
        _make_live_plan(base, 'plan-short')
        _seed_state(isolated_base['queue_path'], upper_limit=1800)

        acq = build_queue.run_acquire(Namespace(plan_id='plan-short'))
        build_queue.run_release(Namespace(plan_id='plan-short', id=acq['id']))

        assert _stored_limit(isolated_base['queue_path']) == 1800

    def test_short_hold_does_not_materialise_an_unconfigured_field(self, isolated_base: dict) -> None:
        """A recompute that does not MOVE the value writes nothing at all.

        Writing an unchanged floor would materialise the field and turn every
        later read from ``default_floor`` into ``queue_state`` — destroying the one
        distinction that source partition exists to make.
        """
        base = isolated_base['base']
        _make_live_plan(base, 'plan-short')
        _seed_state(isolated_base['queue_path'])

        acq = build_queue.run_acquire(Namespace(plan_id='plan-short'))
        build_queue.run_release(Namespace(plan_id='plan-short', id=acq['id']))

        assert _stored_limit(isolated_base['queue_path']) is None
        assert build_queue.run_limit_get(Namespace())['source'] == _DEFAULT_FLOOR

    def test_threshold_survives_an_acquire(self, isolated_base: dict) -> None:
        """An acquire carries the top-level field over rather than dropping it.

        The commit path replaces the three entry lists and spreads the rest of the
        read state; a hand-built three-key return would silently delete the
        threshold on the next build, so a configured value would survive exactly
        until then and read as ``default_floor`` again.
        """
        base = isolated_base['base']
        _make_live_plan(base, 'plan-a')
        _seed_state(isolated_base['queue_path'], upper_limit=1800)

        build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert _stored_limit(isolated_base['queue_path']) == 1800

    def test_threshold_survives_a_noop_release(self, isolated_base: dict) -> None:
        """A no-op release of an absent id also preserves the field."""
        _seed_state(isolated_base['queue_path'], upper_limit=1800)

        build_queue.run_release(Namespace(plan_id='plan-ghost', id='plan-ghost:absent'))

        assert _stored_limit(isolated_base['queue_path']) == 1800


class TestLimitVerbs:
    """``limit get`` / ``limit set`` — the operator surface over the queue state."""

    def test_limit_set_persists_through_the_queue_mutation(self, isolated_base: dict) -> None:
        """``limit set`` writes the field and ``limit get`` reads it straight back."""
        _seed_state(isolated_base['queue_path'])

        result = build_queue.run_limit_set(Namespace(value=1800))

        assert result['status'] == 'success'
        assert result['field'] == _FIELD
        assert result['value'] == 1800
        assert result['requested'] == 1800
        assert result['clamped'] is False
        assert result['source'] == _QUEUE_STATE
        assert result['reap_threshold_seconds'] == 3600
        assert _stored_limit(isolated_base['queue_path']) == 1800
        assert build_queue.run_limit_get(Namespace())['value'] == 1800

    def test_limit_set_clamps_below_the_floor(self, isolated_base: dict) -> None:
        """A sub-floor request clamps up and reports that it was clamped."""
        _seed_state(isolated_base['queue_path'])

        result = build_queue.run_limit_set(Namespace(value=1))

        assert result['value'] == _FLOOR
        assert result['requested'] == 1
        assert result['clamped'] is True
        assert _stored_limit(isolated_base['queue_path']) == _FLOOR

    def test_limit_set_clamps_above_the_ceiling(self, isolated_base: dict) -> None:
        """An over-ceiling request clamps down to the ceiling, never higher."""
        _seed_state(isolated_base['queue_path'])

        result = build_queue.run_limit_set(Namespace(value=99999))

        assert result['value'] == _CEILING
        assert result['clamped'] is True
        assert _stored_limit(isolated_base['queue_path']) == _CEILING

    def test_limit_set_rejects_a_non_positive_or_bool_value(self, isolated_base: dict) -> None:
        """``0`` / negative / ``True`` are refused, and nothing is written.

        ``True`` is refused although it is an ``int`` subclass — the same guard
        the state read applies, checked here at the write boundary too.
        """
        for rejected in (0, -1, True):
            _seed_state(isolated_base['queue_path'])

            result = build_queue.run_limit_set(Namespace(value=rejected))

            assert result['status'] == 'error', f'{rejected!r} should be refused'
            assert _stored_limit(isolated_base['queue_path']) is None

    def test_limit_set_preserves_the_entry_lists(self, isolated_base: dict) -> None:
        """Setting the threshold leaves active/waiting entries untouched."""
        base = isolated_base['base']
        _make_live_plan(base, 'plan-held')
        held = _active_entry('plan-held:held-uuid', 'plan-held', held_seconds=5.0)
        _seed_state(
            isolated_base['queue_path'],
            active=[held],
            waiting=[{'id': 'plan-w:w-uuid', 'plan_id': 'plan-w', 'ts': 1.0}],
        )

        build_queue.run_limit_set(Namespace(value=1800))

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == ['plan-held:held-uuid']
        assert [e['id'] for e in state['waiting']] == ['plan-w:w-uuid']
        assert state[_FIELD] == 1800

    def test_limit_get_reports_a_surviving_per_repo_value_as_not_in_effect(
        self, isolated_base: dict, tmp_path: Path, monkeypatch
    ) -> None:
        """A retired per-repo key is REPORTED, never honoured.

        The applied threshold stays the machine-global one; the per-repo value
        rides the result solely so an operator whose config still sets the old key
        learns it does nothing.
        """
        per_repo = tmp_path / 'run-configuration.json'
        per_repo.write_text(
            json.dumps({'version': 1, 'build': {'queue': {_FIELD: 2400}}}),
            encoding='utf-8',
        )
        monkeypatch.setattr(build_queue, 'get_run_config_path', lambda: per_repo)
        _seed_state(isolated_base['queue_path'], upper_limit=1800)

        got = build_queue.run_limit_get(Namespace())

        assert got['per_repo_value'] == {'value': 2400, 'in_effect': False}
        # The retired value never reaches the applied threshold.
        assert got['value'] == 1800
        assert got['source'] == _QUEUE_STATE

    def test_limit_get_reports_an_unusable_per_repo_value_verbatim(
        self, isolated_base: dict, tmp_path: Path, monkeypatch
    ) -> None:
        """The report echoes back what is actually written, unvalidated.

        A report saying "your config sets this and it does nothing" must name the
        value the operator will find in their file, including one that could never
        have been usable.
        """
        per_repo = tmp_path / 'run-configuration.json'
        per_repo.write_text(json.dumps({'build': {'queue': {_FIELD: 'nonsense'}}}), encoding='utf-8')
        monkeypatch.setattr(build_queue, 'get_run_config_path', lambda: per_repo)
        _seed_state(isolated_base['queue_path'])

        got = build_queue.run_limit_get(Namespace())

        assert got['per_repo_value'] == {'value': 'nonsense', 'in_effect': False}
        assert got['value'] == _FLOOR

    def test_limit_get_omits_per_repo_value_when_no_key_survives(
        self, isolated_base: dict, tmp_path: Path, monkeypatch
    ) -> None:
        """An absent file / absent key yields NO ``per_repo_value`` key at all.

        Omission rather than a ``None`` placeholder: there is no retired key to
        report, and a present-but-empty key would read as one.
        """
        # Bound ONCE outside the loop: the path is the same every iteration, and a
        # lambda closing over a loop variable is a late-binding trap (ruff B023).
        per_repo = tmp_path / 'run-configuration.json'
        monkeypatch.setattr(build_queue, 'get_run_config_path', lambda: per_repo)
        payloads: tuple[dict | None, ...] = (None, {}, {'build': {}}, {'build': {'queue': {}}})
        for payload in payloads:
            if payload is None:
                per_repo.unlink(missing_ok=True)
            else:
                per_repo.write_text(json.dumps(payload), encoding='utf-8')
            _seed_state(isolated_base['queue_path'])

            got = build_queue.run_limit_get(Namespace())

            assert 'per_repo_value' not in got, f'{payload!r} should report no per-repo key'
