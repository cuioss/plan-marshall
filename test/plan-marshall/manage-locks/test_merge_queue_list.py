#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``merge_lock.py``'s ``queue-list`` verb and the blocked-reason split (D11).

The FIFO admission queue was real coordination state with **no read surface** —
``check``'s own contract is that it "never touches the FIFO queue" — so diagnosing
an ``admission: blocked`` meant opening ``merge-queue.json`` by hand. That hand-read
re-implemented the queue's semantics including holder liveness, got it wrong, and
pruned a live sibling plan's slot.

Two halves are pinned here:

* **``queue-list``** — the read-only inspection. Entries in FIFO (arrival) order,
  each with its holder's liveness resolved through ``locate-plan-checkout``, and
  **no mutation under any input**, asserted by a byte comparison of the store file.
* **The blocked-reason split** — two causes hid behind one ``blocked`` label and
  only one has a blocking plan to name, which is why ``blocking_plan_id: null``
  beside ``waiting_count: 2`` read as self-contradictory when it was merely
  unlabelled.

Isolation: every test runs against an isolated ``PLAN_BASE_DIR`` staged under
``tmp_path``, so the suite never contends for the real
``.plan/local/merge-queue.json`` under ``-n auto``. The only stubbed seam is
``_run_executor`` — the process hop into ``git-workflow`` — which stands in for
``locate-plan-checkout``'s documented ``{status, location}`` contract.
"""

from __future__ import annotations

import json
import shlex
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_fixtures import _make_live_plan, _write_lock

from conftest import get_skill_dir, load_script_module, parse_ns

merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_queue_list_under_test')

NOTATION = 'plan-marshall:manage-locks:merge_lock'
SKILL_MD = get_skill_dir('plan-marshall', 'manage-locks') / 'SKILL.md'
QUEUE_LIST_HEADING = '### merge_lock — queue-list'


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path (mirrors the sibling units)."""
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


def _seed_queue(queue_path: Path, waiting: list[dict], **siblings) -> None:
    """Write a merge-queue store carrying ``waiting`` (plus any co-tenant keys)."""
    queue_path.write_text(json.dumps({'waiting': waiting, **siblings}), encoding='utf-8')


def _stub_locator(monkeypatch: pytest.MonkeyPatch, locations: dict[str, object]) -> list[str]:
    """Stand in for the ``locate-plan-checkout`` process hop.

    ``locations`` maps a plan id to the payload the verb would return — either a
    ``location`` string, or ``None`` for a consult that did not answer. Returns the
    list of plan ids consulted, so a test can assert the verb was reached at all.
    """
    consulted: list[str] = []

    def fake(notation: str, *cli_args: str) -> dict:
        plan_id = cli_args[cli_args.index('--plan-id') + 1]
        consulted.append(plan_id)
        location = locations.get(plan_id)
        if location is None:
            return {'status': 'error', 'error': 'stubbed consult failure'}
        return {'status': 'success', 'plan_id': plan_id, 'location': location}

    monkeypatch.setattr(merge_lock, '_run_executor', fake)
    return consulted


def _queue_list() -> dict:
    result: dict = merge_lock.run_queue_list(Namespace())
    return result


def _acquire(plan_id: str) -> dict:
    """Drive ``acquire`` with the title-token surface suppressed (no subprocess)."""
    result: dict = merge_lock.run_acquire(Namespace(plan_id=plan_id, timeout=0.0, set_title_token=False))
    return result


def _documented_queue_list_argv() -> list[str]:
    """The argv the SKILL.md canonical block quotes for ``queue-list``.

    DERIVED from the shipped document rather than transcribed here: the point of
    the assertion below is that the documented spelling and the live parser agree,
    and a hand-copied argv would only ever assert that this file agrees with
    itself.
    """
    text = SKILL_MD.read_text(encoding='utf-8')
    assert QUEUE_LIST_HEADING in text, f'{SKILL_MD} carries no {QUEUE_LIST_HEADING!r} canonical block'
    after_heading = text.split(QUEUE_LIST_HEADING, 1)[1]
    fenced = after_heading.split('```bash', 1)[1].split('```', 1)[0]
    tokens = shlex.split(fenced.replace('\\\n', ' '))
    assert tokens[:3] == ['python3', '.plan/execute-script.py', NOTATION], (
        f'the canonical block does not open with the executor invocation: {tokens[:3]}'
    )
    return tokens[3:]


# =============================================================================
# queue-list — FIFO order, liveness, and the no-mutation guarantee
# =============================================================================


class TestQueueListOrder:
    def test_entries_are_in_arrival_order_not_sorted_by_any_other_key(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The stored list order IS the FIFO order. This seed makes arrival order
        # disagree with BOTH rival orderings at once — sorting by `ts` or by
        # `plan_id` would yield alpha, mid, zeta — so a re-sort on either key is
        # caught rather than hidden by a coincidentally-matching fixture.
        _seed_queue(
            isolated_base['queue_path'],
            [
                {'plan_id': 'zeta', 'ts': 300.0},
                {'plan_id': 'alpha', 'ts': 100.0},
                {'plan_id': 'mid', 'ts': 200.0},
            ],
        )
        _stub_locator(monkeypatch, {'zeta': 'worktree', 'alpha': 'current', 'mid': 'not_found'})

        result = _queue_list()

        assert [entry['plan_id'] for entry in result['entries']] == ['zeta', 'alpha', 'mid']
        assert [entry['position'] for entry in result['entries']] == [0, 1, 2]
        assert result['waiting_count'] == 3

    def test_liveness_is_resolved_through_locate_plan_checkout(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_queue(
            isolated_base['queue_path'],
            [
                {'plan_id': 'on-current', 'ts': 1.0},
                {'plan_id': 'in-worktree', 'ts': 2.0},
                {'plan_id': 'gone', 'ts': 3.0},
            ],
        )
        consulted = _stub_locator(
            monkeypatch,
            {'on-current': 'current', 'in-worktree': 'worktree', 'gone': 'not_found'},
        )

        entries = _queue_list()['entries']

        assert consulted == ['on-current', 'in-worktree', 'gone']
        assert [(e['liveness'], e['location']) for e in entries] == [
            ('live', 'current'),
            ('live', 'worktree'),
            ('not_live', 'not_found'),
        ]

    def test_an_unanswerable_consult_is_unknown_not_dead(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # ⛔ Reading an unanswerable consult as "dead" is the inference that pruned
        # a live sibling plan's slot. `unknown` must stay distinct from `not_live`.
        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'unreachable', 'ts': 1.0}])
        _stub_locator(monkeypatch, {'unreachable': None})

        entry = _queue_list()['entries'][0]

        assert entry['liveness'] == merge_lock.LIVENESS_UNKNOWN
        assert entry['liveness'] != merge_lock.LIVENESS_NOT_LIVE
        assert entry['location'] is None

    def test_every_reported_liveness_is_in_the_declared_vocabulary(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_queue(
            isolated_base['queue_path'],
            [
                {'plan_id': 'a', 'ts': 1.0},
                {'plan_id': 'b', 'ts': 2.0},
                {'plan_id': 'c', 'ts': 3.0},
            ],
        )
        _stub_locator(monkeypatch, {'a': 'current', 'b': 'not_found', 'c': None})

        emitted = {entry['liveness'] for entry in _queue_list()['entries']}

        assert emitted <= merge_lock.QUEUE_LIVENESS_STATES
        # Anti-vacuity: all three members are actually reachable, so the subset
        # assertion above is not passing over a one-value population.
        assert emitted == merge_lock.QUEUE_LIVENESS_STATES


class TestQueueListMutatesNothing:
    def test_a_not_live_front_entry_is_reported_and_not_removed(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The front holder has no live checkout. Reporting that is the answer;
        # removing it belongs to acquire/release under their own serialization.
        queue_path: Path = isolated_base['queue_path']
        _seed_queue(
            queue_path,
            [{'plan_id': 'dead-front', 'ts': 1.0}, {'plan_id': 'live-next', 'ts': 2.0}],
            rate_windows={'coderabbit': {'holder': 'someone', 'expires_at': 0.0, 'attempts': 3}},
        )
        before = queue_path.read_bytes()
        _stub_locator(monkeypatch, {'dead-front': 'not_found', 'live-next': 'worktree'})

        result = _queue_list()

        assert result['entries'][0] == {
            'position': 0,
            'plan_id': 'dead-front',
            'ts': 1.0,
            'liveness': merge_lock.LIVENESS_NOT_LIVE,
            'location': 'not_found',
        }
        assert result['waiting_count'] == 2
        assert queue_path.read_bytes() == before, 'queue-list mutated merge-queue.json'

    def test_an_absent_store_is_reported_as_empty_and_is_not_created(self, isolated_base: dict) -> None:
        queue_path: Path = isolated_base['queue_path']
        assert not queue_path.exists()

        result = _queue_list()

        assert result['status'] == 'success'
        assert result['waiting_count'] == 0
        assert result['entries'] == []
        assert not queue_path.exists(), 'queue-list created merge-queue.json'

    def test_the_payload_declares_itself_a_point_in_time_snapshot(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The read is deliberately unguarded, so the payload has to say that a
        # caller acting on what it saw is acting on a snapshot.
        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'a', 'ts': 1.0}])
        _stub_locator(monkeypatch, {'a': 'current'})

        assert _queue_list()['snapshot'] == 'point_in_time'

    def test_the_lock_holder_is_reported_beside_the_queue(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_lock(isolated_base['lock_path'], 'holder-plan')
        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'waiter', 'ts': 1.0}])
        _stub_locator(monkeypatch, {'waiter': 'current'})

        result = _queue_list()

        assert result['lock_held'] is True
        assert result['lock_holder'] == 'holder-plan'

    def test_a_free_lock_is_reported_without_a_holder(self, isolated_base: dict) -> None:
        result = _queue_list()

        assert result['lock_held'] is False
        assert result['lock_holder'] is None


# =============================================================================
# The blocked-reason split — two causes, one label no longer
# =============================================================================


class TestBlockedReasonSplit:
    def test_a_non_front_block_names_its_reason_and_has_no_blocking_plan(self, isolated_base: dict) -> None:
        # The observed incident's exact shape: blocking_plan_id null beside
        # waiting_count > 0. It is not a contradiction — it is what
        # `not_fifo_front` looks like, and the reason is what says so.
        base: Path = isolated_base['base']
        _make_live_plan(base, 'front-plan')
        _make_live_plan(base, 'mine')
        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'front-plan', 'ts': 1.0}])

        result = _acquire('mine')

        assert result['admission'] == 'blocked'
        assert result['blocked_reason'] == merge_lock.BLOCKED_NOT_FIFO_FRONT
        assert result['blocking_plan_id'] is None
        assert result['waiting_count'] == 2
        assert not isolated_base['lock_path'].exists()

    def test_a_lock_contended_block_names_the_live_holder(self, isolated_base: dict) -> None:
        base: Path = isolated_base['base']
        _make_live_plan(base, 'holder-plan')
        _make_live_plan(base, 'mine')
        _write_lock(isolated_base['lock_path'], 'holder-plan')

        result = _acquire('mine')

        assert result['admission'] == 'blocked'
        assert result['blocked_reason'] == merge_lock.BLOCKED_LOCK_HELD_BY_LIVE_HOLDER
        assert result['blocking_plan_id'] == 'holder-plan'

    def test_the_two_causes_do_not_share_a_label(self, isolated_base: dict) -> None:
        # Collapsing the split back to one label reddens here: the whole point is
        # that a consumer can tell the two apart from the payload alone.
        base: Path = isolated_base['base']
        _make_live_plan(base, 'holder-plan')
        _make_live_plan(base, 'mine')
        _write_lock(isolated_base['lock_path'], 'holder-plan')
        contended = _acquire('mine')

        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'holder-plan', 'ts': 1.0}])
        not_front = _acquire('mine')

        assert contended['blocked_reason'] != not_front['blocked_reason']
        assert {contended['blocked_reason'], not_front['blocked_reason']} <= merge_lock.BLOCKED_REASONS

    def test_every_blocked_payload_carries_a_declared_reason(self, isolated_base: dict) -> None:
        # The vocabulary is TOTAL over the blocked branch — a payload that could
        # omit the reason would reinstate the undifferentiated label.
        base: Path = isolated_base['base']
        _make_live_plan(base, 'holder-plan')
        _make_live_plan(base, 'mine')
        _write_lock(isolated_base['lock_path'], 'holder-plan')

        blocked = [_acquire('mine')]
        _seed_queue(isolated_base['queue_path'], [{'plan_id': 'holder-plan', 'ts': 1.0}])
        blocked.append(_acquire('mine'))

        assert blocked, 'no blocked payload was produced, so the assertion below is vacuous'
        for payload in blocked:
            assert payload['blocked_reason'] in merge_lock.BLOCKED_REASONS

    def test_an_admitted_acquire_carries_no_blocked_reason(self, isolated_base: dict) -> None:
        # NEGATIVE control: the field belongs to the blocked branch only, so its
        # presence is not something every acquire payload carries regardless.
        _make_live_plan(isolated_base['base'], 'mine')

        result = _acquire('mine')

        assert result['admission'] == 'admitted'
        assert 'blocked_reason' not in result


# =============================================================================
# The documented spelling is the one the live parser accepts
# =============================================================================


class TestDocumentedInvocationIsAccepted:
    def test_the_skill_md_canonical_block_is_accepted_by_the_live_parser(self) -> None:
        argv = _documented_queue_list_argv()
        assert argv == ['queue-list'], f'the documented argv drifted from the verb under test: {argv}'

        namespace = parse_ns('plan-marshall', 'manage-locks', 'merge_lock.py', *argv, register=False)

        # Compared by NAME, not identity: parse_ns loads its own unregistered copy
        # of the script, so its handler is a different object than this module's.
        assert namespace.func.__name__ == 'run_queue_list'

    def test_the_verb_declares_no_plan_id(self) -> None:
        # The doc states that appending --plan-id is an unrecognized-arguments
        # rejection; a verb that quietly accepted it would make the doc wrong.
        with pytest.raises(SystemExit):
            parse_ns(
                'plan-marshall',
                'manage-locks',
                'merge_lock.py',
                'queue-list',
                '--plan-id',
                'some-plan',
                register=False,
            )
