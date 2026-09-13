#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
from _build_queue_fixtures import (
    SCRIPT_PATH,
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)
from toon_parser import parse_toon, serialize_toon

# =============================================================================
# Corrupt / missing file resilience
# =============================================================================


class TestCorruptFileAsEmpty:
    def test_missing_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        # No queue file exists yet — the first acquire builds it from scratch.
        assert not isolated_base['queue_path'].exists()
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert isolated_base['queue_path'].is_file()

    def test_corrupt_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text('{ not json', encoding='utf-8')
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1


# =============================================================================
# Dead-holder reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestDeadHolderReclamation:
    def test_dead_active_holder_is_pruned_freeing_a_slot(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['home'], 1)
        # plan-dead acquires the only slot but its plan dir is NEVER created → dead.
        build_queue.run_acquire(Namespace(plan_id='plan-dead'))

        # plan-live acquires: the dead holder is pruned, freeing the slot → admitted.
        _make_live_plan(isolated_base['base'], 'plan-live')
        result = build_queue.run_acquire(Namespace(plan_id='plan-live'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert [e['plan_id'] for e in state['active']] == ['plan-live']

    def test_live_active_holder_is_not_pruned(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['home'], 1)
        _make_live_plan(isolated_base['base'], 'plan-live')
        build_queue.run_acquire(Namespace(plan_id='plan-live'))

        # A second live plan finds the slot occupied by a LIVE holder → blocked.
        _make_live_plan(isolated_base['base'], 'plan-b')
        result = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert result['admission'] == 'blocked'


# =============================================================================
# Foreign-project holder pruning (machine-global project_root stamping)
# =============================================================================
#
# The machine-global queue records holders from multiple checkouts. Each active
# entry's stamped project_root judges its liveness against the checkout it
# originated in, so a foreign project's LIVE holder is never reclaimed by a
# session running in a different repo, while a foreign DEAD holder still is.


class TestForeignProjectHolderPrune:
    def test_foreign_project_live_holder_is_not_pruned(self, isolated_base: dict, tmp_path: Path) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)

        # A holder recorded by project A, LIVE under A's checkout (a DIFFERENT
        # checkout than this session's isolated_base['main_repo']).
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans' / 'foreign-holder').mkdir(parents=True)
        foreign_id = 'foreign-holder:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': foreign_id,
                        'plan_id': 'foreign-holder',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # A local plan acquires: the foreign holder is judged against ITS
        # project_root (where it is live) → NOT pruned → the single slot stays
        # held → local plan is blocked.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'blocked'

        state = _read_queue(isolated_base['queue_path'])
        assert foreign_id in [e['id'] for e in state['active']]

    def test_foreign_project_dead_holder_is_pruned(self, isolated_base: dict, tmp_path: Path) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(isolated_base['home'], 1)

        # A holder recorded by project A but ABSENT under A's checkout → dead.
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans').mkdir(parents=True)  # no holder dir
        dead_id = 'foreign-dead:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': dead_id,
                        'plan_id': 'foreign-dead',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # The dead foreign holder is pruned against its own project_root, freeing
        # the slot for the local acquirer.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        assert dead_id not in [e['id'] for e in state['active']]


# =============================================================================
# Shared-core delegation guard — no re-implemented liveness / resolution
# =============================================================================


class TestSharedCoreDelegation:
    def test_imports_shared_liveness_predicate(self) -> None:
        assert hasattr(build_queue, 'holder_is_dead')

    def test_imports_shared_rmw(self) -> None:
        assert hasattr(build_queue, 'rmw_json')

    def test_imports_shared_resolvers(self) -> None:
        # Resolution is delegated to the shared marketplace_paths resolvers —
        # the hardened machine-global home-root creator and the public
        # main-checkout resolver — never re-implemented here.
        assert hasattr(build_queue, 'ensure_home_root')
        assert hasattr(build_queue, 'main_checkout_root')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src


# =============================================================================
# Machine-global resolution — the host-wide home-root tier (cwd-independent)
# =============================================================================


class TestMachineGlobalResolution:
    def test_queue_resolves_under_home_root_ignoring_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The queue lives under the machine-global home root, NOT PLAN_BASE_DIR.
        # Pinning cwd into a worktree does not redirect it — home_root() is
        # host-wide and cwd-independent.
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = build_queue._resolve_queue_path()
        assert resolved == home / 'build-queue.json'
        assert worktree / '.plan' / 'local' / 'build-queue.json' != resolved

    def test_acquire_writes_to_home_root_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_repo = tmp_path / 'main'
        base = main_repo / '.plan' / 'local'
        (base / 'plans').mkdir(parents=True)
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
        monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        # The queue landed under the machine-global home root, not the worktree.
        assert (home / 'build-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'build-queue.json').exists()


# =============================================================================
# Machine-global CAP resolution — the per-repo key is not in effect
# =============================================================================


class TestMachineGlobalCap:
    def test_per_repo_marshal_json_cap_does_not_change_the_admitted_cap(self, isolated_base: dict) -> None:
        """A surviving per-repo ``build.queue.max_slots`` is not in effect.

        The cap is machine-global, so a single repository cannot change how many
        slots the SHARED queue admits. Staging the per-repo key at a DIFFERENT
        value from the machine-global one is what makes this discriminating:
        reading 1 here would prove the repo file is still consulted.
        """
        _set_max_slots(isolated_base['home'], 4)
        (isolated_base['base'] / 'marshal.json').write_text(
            json.dumps({'build': {'queue': {'max_slots': 1}}}), encoding='utf-8'
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['max_slots'] == 4
        assert result['max_slots_source'] == 'machine_config'
        # A nominal resolution has nothing to explain, so no detail rides along.
        assert 'max_slots_detail' not in result

    def test_release_reports_the_cap_source_too(self, isolated_base: dict) -> None:
        """Both admission surfaces report provenance, not just acquire."""
        _set_max_slots(isolated_base['home'], 3)
        acquired = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        released = build_queue.run_release(Namespace(plan_id='plan-a', id=acquired['id']))

        assert released['max_slots'] == 3
        assert released['max_slots_source'] == 'machine_config'

    def test_absent_machine_config_admits_the_default_and_says_it_fell_back(self, isolated_base: dict) -> None:
        """An unconfigured host admits 5 and reports ``default``, not silence.

        ``max_slots`` alone cannot carry this: a fallback 5 and a configured 5
        are the same number, so only the reported source distinguishes them.
        """
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['max_slots'] == 5
        assert result['max_slots_source'] == 'default'
        assert result['max_slots_detail'] is None

    def test_unusable_machine_config_value_is_reported_as_invalid(self, isolated_base: dict) -> None:
        """A broken cap still admits, but never reports itself as configured."""
        config_dir = isolated_base['home'] / 'marshalld'
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / 'machine-config.json').write_text(
            json.dumps({'build': {'queue': {'max_slots': -2}}}), encoding='utf-8'
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['max_slots'] == 5
        assert result['max_slots_source'] == 'invalid'
        assert result['max_slots_detail'] is not None


# =============================================================================
# The demoted per-repo key is REPORTED on every queued build
# =============================================================================


class TestPerRepoDemotionReport:
    """The audible half of the demotion: the key does nothing AND says so.

    The cap-is-unchanged half is asserted by :class:`TestMachineGlobalCap`
    above. These tests assert the reporting half — without it the demotion is
    silent, and an operator whose repository still sets the key would keep
    believing a cap they do not have.
    """

    def _write_per_repo_cap(self, isolated_base: dict, value: object) -> None:
        """Stage a per-repo ``build.queue.max_slots`` where the caller resolves it.

        ``PLAN_BASE_DIR`` is what ``file_ops.get_tracked_config_dir`` returns
        under this fixture, so this is the exact path ``run_acquire``'s
        cwd-relative ``get_marshal_path()`` reads.
        """
        (isolated_base['base'] / 'marshal.json').write_text(
            json.dumps({'build': {'queue': {'max_slots': value, 'max_retries': 10}}}), encoding='utf-8'
        )

    def test_a_present_per_repo_key_is_reported_as_not_in_effect(self, isolated_base: dict) -> None:
        """The value is echoed back, explicitly flagged as inoperative."""
        _set_max_slots(isolated_base['home'], 4)
        self._write_per_repo_cap(isolated_base, 1)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['per_repo_max_slots'] == {'value': 1, 'in_effect': False}

    def test_a_present_per_repo_key_yields_exactly_one_warning(self, isolated_base: dict) -> None:
        """One warning, not zero and not several.

        The cardinality is the assertion: the wrapper deduplicates by ``code``
        across re-polls, so a queue emitting the same condition twice per
        acquire would make that deduplication load-bearing for correctness
        rather than for noise.
        """
        _set_max_slots(isolated_base['home'], 4)
        self._write_per_repo_cap(isolated_base, 1)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert len(result['warnings']) == 1
        assert result['warnings'][0]['code'] == 'per_repo_max_slots_not_in_effect'

    def test_the_warning_names_the_repo_value_and_the_cap_in_effect(self, isolated_base: dict) -> None:
        """Both numbers appear, so the operator can see which one won."""
        _set_max_slots(isolated_base['home'], 4)
        self._write_per_repo_cap(isolated_base, 1)

        message = build_queue.run_acquire(Namespace(plan_id='plan-a'))['warnings'][0]['message']

        assert str(isolated_base['base'] / 'marshal.json') in message
        assert 'config migrate' in message

    def test_no_per_repo_key_yields_an_empty_warnings_list(self, isolated_base: dict) -> None:
        """``warnings`` is ALWAYS present — absent means nothing to say, not no key.

        An optional key would let a consumer branch on presence and forget to
        look; an always-present empty list is iterated unconditionally.
        """
        _set_max_slots(isolated_base['home'], 4)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['warnings'] == []
        assert 'per_repo_max_slots' not in result

    def test_a_per_repo_key_is_reported_even_with_no_machine_config_at_all(self, isolated_base: dict) -> None:
        """The commonest real case: a legacy repo key on an unconfigured host.

        The cap in effect is the fallback 5, and the warning must still fire —
        reporting only when a machine-global value happens to be set would leave
        exactly the repositories that never migrated in silence.
        """
        self._write_per_repo_cap(isolated_base, 1)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['max_slots'] == 5
        assert result['max_slots_source'] == 'default'
        assert result['per_repo_max_slots'] == {'value': 1, 'in_effect': False}
        assert len(result['warnings']) == 1

    def test_an_unusable_per_repo_value_is_still_reported_verbatim(self, isolated_base: dict) -> None:
        """A value that could never be a cap is echoed as written, not corrected.

        The report has to name what is in the operator's own file, or they
        cannot find the key it is telling them about.
        """
        self._write_per_repo_cap(isolated_base, 0)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['per_repo_max_slots'] == {'value': 0, 'in_effect': False}
        assert len(result['warnings']) == 1

    def test_a_repo_carrying_only_max_retries_yields_no_warning(self, isolated_base: dict) -> None:
        """The matched negative control: ``max_retries`` is a LEGITIMATE per-repo key.

        Without this, the tests above would pass equally against an
        implementation that warned about any ``build.queue`` block at all — which
        would fire on every correctly-migrated repository.
        """
        (isolated_base['base'] / 'marshal.json').write_text(
            json.dumps({'build': {'queue': {'max_retries': 10, 'upper_limit_seconds': 600}}}), encoding='utf-8'
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['warnings'] == []
        assert 'per_repo_max_slots' not in result


# =============================================================================
# Foreign-config reports are TOON-injection safe AT THE EMISSION BOUNDARY
# =============================================================================


class TestForeignValueReportsAreInjectionSafe:
    """Every foreign-sourced value this module REPORTS is sanitised as it is emitted.

    Two readers return a foreign config value raw and unvalidated by design —
    ``_read_per_repo_upper_limit`` (a ``run-configuration.json``) and
    ``_machine_config.read_per_repo_max_slots`` (a ``marshal.json``) — because a
    report saying "your config sets this and it does nothing" must echo back what
    is actually written there. Raw is right for the READ and wrong for the
    EMISSION: ``serialize_toon`` quotes a string containing a newline but escapes
    nothing inside the quotes, so the value's second and later lines land in the
    document at column zero, where ``parse_toon`` reads them as SIBLING KEYS of
    the envelope. A planted ``status:`` line does not merely get lost — it
    OVERWRITES the envelope's own status.

    These tests drive the REAL emission path end to end (resolve → serialize →
    reparse) rather than asserting on ``report_safe`` in isolation, because the
    whole point is that they FAIL if the sanitiser is dropped from a call site.
    A test that would pass with the sanitiser removed does not pin it, and every
    pre-existing test over these two surfaces passes only integers — so until
    these, the guard was revertible in silence.
    """

    #: A raw value whose later lines are TOON-shaped sibling keys. The displaced
    #: key is the load-bearing part: overwriting an outcome field turns a report
    #: into a different result, which is the severity of this class.
    _INJECTING_STATUS = '2400\nstatus: error\nin_effect: true'

    def _report_via_limit_get(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: object) -> dict:
        """Run ``limit get`` against a planted per-repo ``run-configuration.json``."""
        per_repo = tmp_path / 'run-configuration.json'
        per_repo.write_text(
            json.dumps({'build': {'queue': {build_queue.UPPER_LIMIT_FIELD: raw}}}),
            encoding='utf-8',
        )
        monkeypatch.setattr(build_queue, 'get_run_config_path', lambda: per_repo)
        return build_queue.run_limit_get(Namespace())

    def test_limit_get_strips_control_characters_from_the_reported_value(
        self, isolated_base: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The C0/DEL bytes that cannot survive a single-line field are removed."""
        reported = self._report_via_limit_get(tmp_path, monkeypatch, '24\x0000\x1f\x7f\nstatus: error')[
            'per_repo_value'
        ]['value']

        assert reported == '2400status: error'
        for forbidden in ('\n', '\x00', '\x1f', '\x7f'):
            assert forbidden not in reported

    def test_limit_get_report_cannot_displace_the_envelope_status(
        self, isolated_base: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A planted ``status: error`` line never reparses as the envelope's status."""
        result = self._report_via_limit_get(tmp_path, monkeypatch, self._INJECTING_STATUS)
        assert result['status'] == 'success'

        reparsed = parse_toon(serialize_toon(result))

        assert reparsed['status'] == 'success'

    def test_acquire_per_repo_report_cannot_displace_the_admission(self, isolated_base: dict) -> None:
        """The same guard on this module's OTHER foreign-value emission boundary.

        ``_demotion_fields`` reads the caller's own ``marshal.json`` raw, so it is
        fed by foreign text exactly as ``limit get`` is. The planted line names
        ``blocked`` while the real admission is ``admitted``, so an unsanitised
        emission is observable as a CHANGED OUTCOME rather than as noise.
        """
        (isolated_base['base'] / 'marshal.json').write_text(
            json.dumps({'build': {'queue': {'max_slots': '1\nadmission: blocked'}}}),
            encoding='utf-8',
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert '\n' not in result['per_repo_max_slots']['value']

        reparsed = parse_toon(serialize_toon(result))

        assert reparsed['admission'] == 'admitted'

    def test_a_clean_foreign_value_is_still_reported_verbatim(
        self, isolated_base: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The matched positive control: sanitising is not silently blanking.

        Without this, the assertions above would pass equally against an
        implementation that reported an empty string for every foreign value —
        which would destroy the report the field exists to produce.
        """
        result = self._report_via_limit_get(tmp_path, monkeypatch, 'nonsense')

        assert result['per_repo_value'] == {'value': 'nonsense', 'in_effect': False}

    def test_a_non_string_foreign_value_is_reported_unchanged(
        self, isolated_base: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only a ``str`` can carry a control character; every other type passes through.

        Pins the type-preservation half: an ``int`` must stay an ``int`` rather
        than arrive as its string form, or the sanitiser would be changing the
        shape of what the operator reads.
        """
        result = self._report_via_limit_get(tmp_path, monkeypatch, 2400)

        assert result['per_repo_value'] == {'value': 2400, 'in_effect': False}
