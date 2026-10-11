#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the ``merge_lock dequeue`` CLI verb — the dequeue-only cleanup for an
acquire that took no lock.

Contract under test:

* **Queue entry only** — ``dequeue --plan-id P`` removes P's FIFO entry and never
  reads, creates or removes ``merge.lock``, so a lock whose recorded holder IS P
  (a concurrent same-plan session admitted after the refused attempt) survives.
* **Idempotent** — dequeuing an absent entry is ``status: success`` with
  ``action: noop`` and creates no lock file.
* **Discoverable** — the verb is listed by the script's ``--help`` and requires
  ``--plan-id``.

The behaviour of the underlying ``run_dequeue`` is asserted in-process in
``test_manage_locks_merge_lock_release.py``; the cases here cover the CLI plumbing.
"""

from __future__ import annotations

import json
from argparse import Namespace

from _manage_locks_merge_lock_fixtures import (
    SCRIPT_PATH,
    _make_live_plan,
    _stub_title_tokens,
    _waiting_plan_ids,
    isolated_base,
    merge_lock,
)
from toon_parser import parse_toon

from conftest import run_script


def _env(isolated_base: dict) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(isolated_base['base'])}


class TestDequeueCli:
    def test_removes_the_entry_and_leaves_a_same_plan_lock_intact(self, isolated_base: dict) -> None:
        """The recorded holder is the dequeued plan itself — the case ``release``
        would delete — and the lock file is still there afterwards."""
        base = isolated_base['base']
        for name in ('plan-a', 'plan-b'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [{'plan_id': 'plan-a', 'ts': 1.0}, {'plan_id': 'plan-b', 'ts': 2.0}]}),
            encoding='utf-8',
        )
        isolated_base['lock_path'].write_text('plan-a\n', encoding='utf-8')

        result = run_script(SCRIPT_PATH, 'dequeue', '--plan-id', 'plan-a', env_overrides=_env(isolated_base))

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success', parsed
        assert parsed['action'] == 'dequeued', parsed
        assert parsed['waiting_count'] == 1, parsed
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['plan-b']
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_absent_entry_is_a_noop_success(self, isolated_base: dict) -> None:
        result = run_script(SCRIPT_PATH, 'dequeue', '--plan-id', 'never-queued', env_overrides=_env(isolated_base))

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success', parsed
        assert parsed['action'] == 'noop', parsed
        assert parsed['waiting_count'] == 0, parsed
        assert not isolated_base['lock_path'].exists()

    def test_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'dequeue')

        assert result.returncode == 2
        assert '--plan-id' in result.stderr

    def test_help_lists_the_verb(self) -> None:
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0, result.stderr
        assert 'dequeue' in result.stdout

    def test_handler_is_the_in_process_dequeue(self, isolated_base: dict) -> None:
        """The CLI handler routes to ``run_dequeue`` with the parsed ``--plan-id``."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))

        result = merge_lock.run_dequeue_cli(Namespace(plan_id='plan-a'))

        assert result == {'status': 'success', 'plan_id': 'plan-a', 'action': 'dequeued', 'waiting_count': 0}
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'
