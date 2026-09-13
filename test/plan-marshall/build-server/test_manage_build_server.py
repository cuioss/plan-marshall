#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage_build_server — the operator control surface.

Drive the control verbs directly, through the shared ``conftest.load_script_module``
loader. Every test isolates the machine-global home root by pointing
``PLAN_MARSHALL_HOME`` at a per-test ``tmp_path`` so no test touches the real
``~/.plan-marshall/`` tree. The OS seams (``_spawn_detached`` / ``_signal`` /
``_ping``) are monkeypatched so no real daemon is launched, no real signal is
sent, and no real socket is opened.

The ``config`` verbs (``get`` / ``set`` / ``migrate``) span TWO files — the
machine-global ``machine-config.json`` under the isolated home root, and the
caller repository's ``marshal.json`` under the autouse ``_plan_base_dir_sandbox``
— so every ``migrate`` outcome is asserted against a byte snapshot of BOTH.
That pairing is the point rather than a formality: the verb's central guarantee
is that it refuses instead of guessing, and a refusal is only a refusal if
neither file moved. ``migrated`` and ``removed_duplicate`` are asserted on parsed
content for ``marshal.json`` (``save_config`` canonicalises key order on every
write, so its bytes legitimately change) and on bytes for ``machine-config.json``,
which ``removed_duplicate`` must leave untouched.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import signal
from pathlib import Path
from typing import Any

import _build_server_registry as registry

# PLAIN import, matching how ``manage_build_server`` itself imports it: the source
# constants compared against the verb's output must be the SAME objects the verb
# closed over, not a second loaded copy of them.
import _machine_config as machine_config
import pytest
from toon_parser import parse_toon, serialize_toon

from conftest import load_script_module, parse_ns

_BUNDLE = 'plan-marshall'
_SKILL = 'manage-build-server'
_SCRIPT = 'manage_build_server.py'

mbs = load_script_module(_BUNDLE, _SKILL, _SCRIPT)


def _verb_args(*argv: str) -> argparse.Namespace:
    """The namespace ``manage_build_server.py``'s OWN parser yields for ``argv``.

    ``register=False`` so building one never publishes a second
    ``manage_build_server`` in ``sys.modules`` alongside the one the loader published above.
    """
    args: argparse.Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT, *argv, register=False)
    return args


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: One parser-derived namespace per control verb, hoisted to module scope because
#: ``parse_ns`` re-executes the script module on every call. Each carries the
#: ``command`` discriminator and the verb's real flag defaults — ``register``'s
#: ``--container``/``--notation`` and ``logs``' ``--limit`` among them — none of
#: which the hand-built namespaces they replace carried.
_REGISTER_ARGS = _verb_args('register')
_UNREGISTER_ARGS = _verb_args('unregister')
_START_ARGS = _verb_args('start')
_STOP_ARGS = _verb_args('stop')
_DRAIN_ARGS = _verb_args('drain')
_STATUS_ARGS = _verb_args('status')
_INSTALL_ARGS = _verb_args('install')
_UPGRADE_ARGS = _verb_args('upgrade')
_LOGS_ARGS = _verb_args('logs')
_CONFIG_GET_ARGS = _verb_args('config', 'get')
_CONFIG_MIGRATE_ARGS = _verb_args('config', 'migrate')
_CONFIG_SET_ARGS = _verb_args('config', 'set', '--max-slots', '7')


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def _audit_lines() -> list[dict]:
    path = registry.audit_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def _lifecycle_lines() -> list[dict]:
    path = mbs.marshalld.daemon_dir() / mbs._LIFECYCLE_AUDIT_FILENAME
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


# =============================================================================
# register / unregister
# =============================================================================


def test_register_round_trip_and_audit(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_register(
        _variant(
            _REGISTER_ARGS,
            root=str(root),
            container=[str(home / 'wts')],
            notation=['a:b:c'],
        )
    )

    assert result['status'] == 'success'
    assert result['action'] == 'register'
    assert result['canonical_root'] == registry.canonicalize_root(root)
    assert result['notation_allowlist'] == ['a:b:c']
    # Persisted to the machine-global registry.
    stored = registry.read_registry()['projects']
    assert result['canonical_root'] in stored
    # Registration appended exactly one audit line.
    lines = _audit_lines()
    assert len(lines) == 1
    assert lines[0]['action'] == registry.ACTION_REGISTER


def test_register_no_flags_populates_default_scope(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_register(_variant(_REGISTER_ARGS, root=str(root)))

    # Omitting --container / --notation now backfills canonical defaults rather
    # than storing empty scope (which left a registered project inert). Full
    # default-population / backfill coverage lives in test_register_defaults.py.
    assert result['notation_allowlist']
    assert result['worktree_containers'] == [str(Path(result['canonical_root']) / '.plan' / 'local' / 'worktrees')]


def test_unregister_round_trip_and_audit(home):
    root = home / 'proj'
    root.mkdir()
    mbs.run_register(_variant(_REGISTER_ARGS, root=str(root)))

    result = mbs.run_unregister(_variant(_UNREGISTER_ARGS, root=str(root)))

    assert result['status'] == 'success'
    assert result['removed'] is True
    assert registry.read_registry()['projects'] == {}
    actions = [entry['action'] for entry in _audit_lines()]
    assert actions == [registry.ACTION_REGISTER, registry.ACTION_UNREGISTER]


def test_unregister_absent_is_idempotent_noop(home):
    root = home / 'never'

    result = mbs.run_unregister(_variant(_UNREGISTER_ARGS, root=str(root)))

    assert result['status'] == 'success'
    assert result['removed'] is False
    assert _audit_lines() == []


# =============================================================================
# start / install — version pinning + audit
# =============================================================================


def test_start_pins_version_and_writes_audit(home, monkeypatch):
    spawned: list[list[str]] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: spawned.append(command))

    result = mbs.run_start(_START_ARGS)

    assert result['running'] is True
    assert result['already_running'] is False
    assert result['version'] == mbs.marshalld.VERSION
    # The pinned binary path is the marshalld copy co-located with this skill.
    expected_binary = str(Path(mbs.marshalld.__file__).resolve())
    assert result['binary_path'] == expected_binary
    # The spawned command launches that exact pinned binary.
    assert spawned and spawned[0][1] == expected_binary
    # Exactly one lifecycle audit line records the start with version + binary.
    lines = _lifecycle_lines()
    assert len(lines) == 1
    assert lines[0]['action'] == 'start'
    assert lines[0]['binary_path'] == expected_binary
    assert lines[0]['version'] == mbs.marshalld.VERSION


def test_start_refuses_second_daemon(home, monkeypatch):
    spawned: list[list[str]] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 4321)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: spawned.append(command))

    result = mbs.run_start(_START_ARGS)

    assert result['already_running'] is True
    assert result['pid'] == 4321
    # No spawn, no audit — an already-running daemon is a no-op.
    assert spawned == []
    assert _lifecycle_lines() == []


def test_install_is_idempotent_when_running(home, monkeypatch):
    monkeypatch.setattr(mbs, '_running_pid', lambda: 99)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: None)

    result = mbs.run_install(_INSTALL_ARGS)

    assert result['action'] == 'install'
    assert result['already_running'] is True


# =============================================================================
# stop — forced kill escalation
# =============================================================================


def test_stop_sigterm_then_cleanup_when_graceful(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 555)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)

    result = mbs.run_stop(_STOP_ARGS)

    assert result['was_running'] is True
    assert result['forced'] is False
    # Only SIGTERM — no SIGKILL escalation when it exited gracefully.
    assert sent == [signal.SIGTERM]
    assert _lifecycle_lines()[-1]['action'] == 'stop'


def test_stop_escalates_to_sigkill_when_wedged(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 555)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: False)

    result = mbs.run_stop(_STOP_ARGS)

    assert result['forced'] is True
    assert sent == [signal.SIGTERM, signal.SIGKILL]


def test_stop_absent_daemon_is_noop(home, monkeypatch):
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_stop(_STOP_ARGS)

    assert result['was_running'] is False
    assert _lifecycle_lines() == []


# =============================================================================
# drain — graceful, never SIGKILL
# =============================================================================


def test_drain_sigterm_only_and_audits(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 777)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)

    result = mbs.run_drain(_DRAIN_ARGS)

    assert result['was_running'] is True
    assert result['exited'] is True
    # Graceful: SIGTERM only — drain NEVER escalates to SIGKILL.
    assert sent == [signal.SIGTERM]
    assert signal.SIGKILL not in sent
    assert _lifecycle_lines()[-1]['action'] == 'drain'


def test_drain_reports_non_exit_without_sigkill(home, monkeypatch):
    sent: list[int] = []
    monkeypatch.setattr(mbs, '_running_pid', lambda: 777)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: sent.append(sig))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: False)

    result = mbs.run_drain(_DRAIN_ARGS)

    # Even when the daemon does not exit in the grace window, drain does not kill.
    assert result['exited'] is False
    assert sent == [signal.SIGTERM]


# =============================================================================
# upgrade — drain then start
# =============================================================================


def test_upgrade_drains_then_starts(home, monkeypatch):
    calls: list[str] = []

    def fake_pid() -> int | None:
        # Running before drain, down after (so start proceeds).
        return 888 if not calls else None

    monkeypatch.setattr(mbs, '_running_pid', fake_pid)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: calls.append('signal'))
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: calls.append('spawn'))

    result = mbs.run_upgrade(_UPGRADE_ARGS)

    assert result['action'] == 'upgrade'
    assert result['drained'] is True
    assert result['running'] is True
    # Drain (signal) happened before the start (spawn).
    assert calls.index('signal') < calls.index('spawn')
    # The positive control for the failure guard below: a genuine upgrade reports
    # both fields in their success shape, so a `status: error` there is a real
    # signal rather than a value the verb always emits.
    assert result['drain_exited'] is True
    assert result['already_running'] is False
    assert result['status'] == 'success'
    assert 'reason' not in result
    # The error fields are set only on a failure branch — a payload that always
    # carried them would make them useless as a failure discriminator.
    assert 'error' not in result
    assert 'message' not in result


def test_upgrade_reports_a_failed_drain_instead_of_claiming_success(home, monkeypatch):
    # The daemon never exits its drain window, so the start half finds it still
    # up. `upgrade` must report BOTH facts and must NOT call that a success: it
    # once hard-coded `status: success` regardless of outcome, and its reconcile
    # caller cleared a reconcile-owed marker on that word alone.
    monkeypatch.setattr(mbs, '_running_pid', lambda: 888)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: None)
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: False)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: None)

    result = mbs.run_upgrade(_UPGRADE_ARGS)

    assert result['drain_exited'] is False
    assert result['already_running'] is True
    assert result['status'] != 'success'
    assert result['reason'] == 'drain_did_not_exit'
    # The shared error contract, not just `reason`: a consumer that decodes
    # `error`/`message` (manage-contract.md) receives a readable payload. The
    # result survives to one — `print_toon` exits 0, so reconcile_daemon's
    # `_invoke_executor` hands the whole dict on rather than discarding it.
    assert result['error'] == 'drain_did_not_exit'
    assert 'drain' in result['message']


def test_upgrade_reports_a_daemon_still_up_after_a_clean_drain(home, monkeypatch):
    # The SECOND failure branch, documented on the operator surface in SKILL.md
    # and previously unreached by any test. It is NOT the branch above: the drain
    # window closes cleanly (`drain_exited: True`), yet the start half still finds
    # a daemon up — so the old daemon was never actually replaced. A pid that
    # stays live across both halves is what separates the two branches.
    monkeypatch.setattr(mbs, '_running_pid', lambda: 999)
    monkeypatch.setattr(mbs, '_signal', lambda pid, sig: None)
    monkeypatch.setattr(mbs, '_wait_for_exit', lambda pid, grace: True)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: None)

    result = mbs.run_upgrade(_UPGRADE_ARGS)

    assert result['drain_exited'] is True
    assert result['already_running'] is True
    assert result['status'] != 'success'
    assert result['reason'] == 'already_running_after_drain'
    assert result['error'] == 'already_running_after_drain'
    assert 'never actually replaced' in result['message']


def test_upgrade_with_nothing_to_drain_stays_a_success(home, monkeypatch):
    # Nothing to drain is NOT a failed drain — there was no process that failed
    # to exit — so the upgrade reduces to a plain start and stays a success. This
    # is what stops the guard above from firing on every daemon-down upgrade.
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)
    monkeypatch.setattr(mbs, '_spawn_detached', lambda command, env: None)

    result = mbs.run_upgrade(_UPGRADE_ARGS)

    assert result['drain_exited'] is True
    assert result['already_running'] is False
    assert result['status'] == 'success'


# =============================================================================
# status — running / down, version + binary path
# =============================================================================


def _resolved_binary() -> str:
    """The resolve-now marshalld path status compares the running one against."""
    return str(Path(mbs.marshalld.__file__).resolve())


def _fake_ping(
    *,
    in_flight: int = 0,
    queued: int = 0,
    pid: int = 4242,
    max_slots: int = 5,
    max_slots_source: str = machine_config.SOURCE_MACHINE_CONFIG,
    max_slots_detail: str | None = None,
):
    """A verified-ping stand-in in the shape a CURRENT daemon answers with.

    Carries the version, the scheduler counts, and the cap resolution the running
    daemon is applying. It is deliberately the current shape rather than a
    reduced one: a stand-in that no real daemon version produces would let a
    status test pass against a payload the daemon never sends. The older shapes
    are staged explicitly by the ``_fake_ping_without_*`` builders below, so
    which daemon generation a test is about stays visible at the call site.

    ``max_slots_detail`` is included only when supplied, mirroring the daemon:
    it explains a non-nominal source and a ``machine_config`` resolution has
    nothing to explain.
    """
    payload: dict[str, Any] = {
        'status': 'ok',
        'pid': pid,
        'version': mbs.marshalld.VERSION,
        'in_flight': in_flight,
        'queued': queued,
        'max_slots': max_slots,
        'max_slots_source': max_slots_source,
    }
    if max_slots_detail is not None:
        payload['max_slots_detail'] = max_slots_detail
    return lambda timeout=mbs._PING_TIMEOUT_SECONDS: payload


def _argv_for(binary_path: str) -> list[str]:
    """A daemon launch argv whose marshalld token is ``binary_path``."""
    return ['/usr/bin/python3', binary_path, 'run']


def test_status_running_reports_running_provenance_when_current(home, monkeypatch):
    # A daemon executing the resolve-now binary is NOT stale: running provenance
    # equals the resolved path, and the divergence flag is false.
    monkeypatch.setattr(mbs, '_ping', _fake_ping())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running'] is True
    assert result['version'] == mbs.marshalld.VERSION
    assert result['pid'] == 4242
    # D4: the provenance is the binary the LIVE process runs, reported as such.
    assert result['running_binary_path'] == _resolved_binary()
    assert result['resolved_binary_path'] == _resolved_binary()
    assert result['binary_diverges'] is False
    assert 'note' not in result
    assert result['socket_path'] == str(mbs.marshalld.socket_path())


def test_status_reports_in_flight_and_queued_counts(home, monkeypatch):
    # D1: the scheduler's in-flight / queued counts ride the status output so an
    # operator (and the reconcile) reads idleness from the daemon's own count.
    monkeypatch.setattr(mbs, '_ping', _fake_ping(in_flight=2, queued=3))
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['in_flight'] == 2
    assert result['queued'] == 3


def _fake_ping_without_counts(pid: int = 4242):
    """A ping from a daemon predating the counts extension — no count keys at all.

    It predates the cap fields too: the counts extension came first, so a daemon
    old enough to omit the counts is necessarily old enough to omit the cap. The
    reduced shape is therefore the only guaranteed one — ``status``, ``pid``,
    ``version`` — and both later extensions read as unreported against it.
    """
    return lambda timeout=mbs._PING_TIMEOUT_SECONDS: {
        'status': 'ok',
        'pid': pid,
        'version': mbs.marshalld.VERSION,
    }


def test_status_reports_unknown_counts_when_the_daemon_sent_none(home, monkeypatch):
    # A daemon pinned to a copy predating the counts extension omits both keys.
    # Reporting that absence as 0 makes it indistinguishable from a genuinely
    # idle daemon — which is exactly how a reconcile came to drain a live build.
    monkeypatch.setattr(mbs, '_ping', _fake_ping_without_counts())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['in_flight'] == mbs._UNREPORTED
    assert result['queued'] == mbs._UNREPORTED
    # The point of the sentinel: it is NOT the value that reads as idle.
    assert result['in_flight'] != 0
    assert result['queued'] != 0


def test_status_reports_a_genuine_zero_count_as_zero(home, monkeypatch):
    # The matched negative control for the sentinel above: a daemon that DID
    # report idleness still reports 0, so `unknown` marks "not told" rather than
    # replacing every count.
    monkeypatch.setattr(mbs, '_ping', _fake_ping(in_flight=0, queued=0))
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['in_flight'] == 0
    assert result['queued'] == 0


# =============================================================================
# status — the build-slot cap the RUNNING daemon is applying
# =============================================================================
# The cap is reported from the PING, never re-resolved here. The two questions
# differ: the ping answers "what is the running daemon admitting against", a
# local resolve answers "what would a fresh daemon apply". Substituting the
# second for the first is the same drift-hiding defect `running_binary_path`
# already refuses to commit for the binary path, so the tests below stage a
# machine-global config that DISAGREES with the daemon's report — a substituting
# implementation then has a distinct, nameable wrong answer to be caught on.


def test_status_reports_the_cap_and_source_the_daemon_sent(home, monkeypatch):
    monkeypatch.setattr(mbs, '_ping', _fake_ping(max_slots=3, max_slots_source=machine_config.SOURCE_MACHINE_CONFIG))
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['max_slots'] == 3
    assert result['max_slots_source'] == machine_config.SOURCE_MACHINE_CONFIG
    # A nominal source is not a fault, so no warning line is added.
    assert 'max_slots_warning' not in result


def test_status_reports_the_running_cap_not_what_a_fresh_daemon_would_apply(home, monkeypatch):
    # The host config says 11; the daemon running right now says 3. Status must
    # report 3 — the cap actually admitting builds — and never 11.
    _stage_machine_cap(home, 11)
    monkeypatch.setattr(mbs, '_ping', _fake_ping(max_slots=3))
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['max_slots'] == 3
    # The local resolve really does disagree, so the assertion above is a
    # discrimination rather than a coincidence.
    assert machine_config.resolve_max_slots().value == 11
    assert result['max_slots'] != 11


def test_status_reports_an_unreported_cap_as_unknown_never_a_local_resolve(home, monkeypatch):
    # A daemon predating the cap fields sends neither key. Both read as the
    # unreported sentinel — and specifically NOT as the value a local resolve
    # would produce, which is the substitution this fails closed against.
    _stage_machine_cap(home, 11)
    monkeypatch.setattr(mbs, '_ping', _fake_ping_without_counts())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['max_slots'] == mbs._UNREPORTED
    assert result['max_slots_source'] == mbs._UNREPORTED
    assert result['max_slots'] != 11
    assert machine_config.resolve_max_slots().value == 11
    # Nothing is known about the source, so no warning is claimed about it.
    assert 'max_slots_warning' not in result


@pytest.mark.parametrize(
    ('source', 'detail'),
    [
        (machine_config.SOURCE_INVALID, 'build.queue.max_slots is not a positive integer: 0'),
        (machine_config.SOURCE_UNREADABLE, 'cannot parse /host/machine-config.json: bad token'),
    ],
)
def test_status_warns_when_the_running_daemon_could_not_use_the_configured_cap(home, monkeypatch, source, detail):
    # A degraded cap source is VISIBLE in the source field, but an operator
    # scanning a status block reads a line that says WARNING long before they
    # read a provenance field — so the degradation gets one, carrying everything
    # needed to act: which source, what is actually being admitted against, why,
    # and the one command that repairs it.
    fallback = machine_config.DEFAULT_MAX_SLOTS
    monkeypatch.setattr(
        mbs,
        '_ping',
        _fake_ping(max_slots=fallback, max_slots_source=source, max_slots_detail=detail),
    )
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    warning = result['max_slots_warning']
    assert 'WARNING' in warning
    assert source in warning
    assert str(fallback) in warning
    assert detail in warning
    assert 'config set --max-slots' in warning
    # The structured fields still report the degraded state on their own; the
    # warning is an addition to them, not a replacement.
    assert result['max_slots'] == fallback
    assert result['max_slots_source'] == source


@pytest.mark.parametrize(
    'source',
    [machine_config.SOURCE_MACHINE_CONFIG, machine_config.SOURCE_DEFAULT],
)
def test_status_does_not_warn_about_a_source_that_is_not_a_fault(home, monkeypatch, source):
    # The matched negative controls for the warning above, and the reason the
    # warn-set is exactly two members rather than "anything but nominal":
    # `machine_config` is nominal, and `default` is a legitimate unconfigured
    # host. Warning on an unconfigured host would fire on every fresh machine and
    # train the operator to ignore the line — which is how a real degradation
    # then goes unread.
    monkeypatch.setattr(mbs, '_ping', _fake_ping(max_slots=machine_config.DEFAULT_MAX_SLOTS, max_slots_source=source))
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(_resolved_binary()))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['max_slots_source'] == source
    assert 'max_slots_warning' not in result


@pytest.mark.parametrize('sent', ['', 42, None, ['machine_config']])
def test_a_source_that_is_not_a_non_empty_string_reads_as_unreported(sent):
    # `max_slots_source` is a named member of a closed set. An empty string, a
    # number, and a list are none of them, so each is unreported rather than
    # rendered as itself — a status block showing `max_slots_source: 42` would
    # read as a reading the daemon never made.
    assert mbs._reported_text({'max_slots_source': sent}, 'max_slots_source') == mbs._UNREPORTED


def test_a_non_integer_reported_number_reads_as_unreported():
    # The integer counterpart: a present-but-unusable value is not a reading. The
    # matched positive control sits beside it, so this cannot pass against an
    # implementation that reports everything as unreported.
    assert mbs._reported_int({'max_slots': 'lots'}, 'max_slots') == mbs._UNREPORTED
    assert mbs._reported_int({'max_slots': 6}, 'max_slots') == 6


def test_status_stale_daemon_shows_divergence(home, monkeypatch):
    # D4 done-when: a deliberately-stale daemon (running an OLD pinned copy) makes
    # status show BOTH paths and flag the divergence — never one masquerading as
    # the other. The exact version numbers are leads; the divergence is the claim.
    stale_binary = '/cache/plan-marshall/0.1.1212/skills/manage-build-server/scripts/marshalld.py'
    monkeypatch.setattr(mbs, '_ping', _fake_ping())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: _argv_for(stale_binary))

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running'] is True
    # The RUNNING provenance is the old binary — the actually-executing one.
    assert result['running_binary_path'] == stale_binary
    # The resolve-now path is the current pin, distinct from what is running.
    assert result['resolved_binary_path'] == _resolved_binary()
    assert result['resolved_binary_path'] != stale_binary
    assert result['binary_diverges'] is True
    # The divergence is spelled out for a cold reader.
    assert 'STALE' in result['note']
    assert stale_binary in result['note']


def test_status_unknown_provenance_never_falls_back_to_resolved(home, monkeypatch):
    # D4 fail-closed (the mandatory `unknown` case): when the running binary cannot
    # be determined, status reports `unknown` and NEVER the resolved-now path —
    # that substitution is the exact defect this deliverable closes.
    monkeypatch.setattr(mbs, '_ping', _fake_ping())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: None)

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running'] is True
    assert result['running_binary_path'] == 'unknown'
    assert result['running_binary_path'] != result['resolved_binary_path']
    assert result['binary_diverges'] is False
    assert 'unknown' in result['note']


def test_status_unknown_when_argv_has_no_marshalld_token(home, monkeypatch):
    # An argv that carries no unambiguous marshalld entry is undeterminable — the
    # provenance fails closed to `unknown`, not the resolved path.
    monkeypatch.setattr(mbs, '_ping', _fake_ping())
    monkeypatch.setattr(mbs, '_read_process_argv', lambda pid: ['/usr/bin/python3', '-c', 'pass'])

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running_binary_path'] == 'unknown'
    assert result['binary_diverges'] is False


def test_read_process_argv_reads_this_process_from_proc(home):
    # Exercise the real /proc fast path against this very process (Linux). On a
    # platform with no /proc the branch falls to `ps`; skip rather than assert a
    # platform-specific shape.
    if not Path('/proc/self/cmdline').exists():
        pytest.skip('no /proc on this platform')

    argv = mbs._read_process_argv(os.getpid())

    assert argv is not None
    assert len(argv) >= 1
    # The interpreter (or the pytest launcher) is the first token — enough to
    # prove the NUL-split parse produced real argv tokens, not one glued string.
    assert '\x00' not in argv[0]


def test_status_down_reports_reason(home, monkeypatch):
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running'] is False
    assert result['reason'] == 'no_pidfile'
    # A down daemon reports only the resolve-now path, named as such — there is no
    # running process to read provenance from.
    assert result['resolved_binary_path'] == _resolved_binary()
    assert 'running_binary_path' not in result


def test_status_down_unreachable_when_pid_present(home, monkeypatch):
    # A recorded live pid but a socket that does not answer → unreachable.
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: 1234)

    result = mbs.run_status(_STATUS_ARGS)

    assert result['running'] is False
    assert result['reason'] == 'unreachable'


def test_status_reports_registration(home, monkeypatch):
    # Register the caller's main checkout, then assert status sees it registered.
    caller_root = mbs.canonicalize_root(mbs.main_checkout_root())
    registry.register_project(caller_root)
    monkeypatch.setattr(mbs, '_ping', lambda timeout=mbs._PING_TIMEOUT_SECONDS: None)
    monkeypatch.setattr(mbs, '_running_pid', lambda: None)

    result = mbs.run_status(_STATUS_ARGS)

    assert result['registered'] is True


# =============================================================================
# logs — read-only project-scoped interaction-audit view
# =============================================================================


def test_logs_filters_to_the_caller_project(home):
    root = home / 'proj'
    root.mkdir()
    caller = mbs.canonicalize_root(str(root))
    other = mbs.canonicalize_root(str(home))  # a distinct canonical root
    audit = mbs.InteractionAudit()
    audit.record('submit', caller, 'p1', 'JOB-A', 'queued')
    audit.record('submit', other, 'p2', 'JOB-B', 'queued')
    audit.record('wait', caller, '', 'JOB-A', 'success')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root)))

    assert result['status'] == 'success'
    assert result['action'] == 'logs'
    # Only the caller-project records — the other project's record is filtered out.
    assert result['count'] == 2
    assert all(record['project_root'] == caller for record in result['records'])
    assert [record['job_id'] for record in result['records']] == ['JOB-A', 'JOB-A']
    # Rendered shape: every row is labelled an interaction row, carries its
    # request-scoped status under a name that is not a job fate, and — with no
    # job-fate record written — an explicit unknown fate rather than a missing field.
    for record in result['records']:
        assert record['kind'] == 'interaction'
        assert 'outcome' not in record
        assert record['fate'] == 'unknown'
    assert [record['request_status'] for record in result['records']] == ['queued', 'success']


def test_logs_absent_log_fails_closed_with_reason(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root)))

    assert result['status'] == 'success'
    assert result['records'] == []
    assert result['count'] == 0
    assert result['reason'] == 'log_absent'


def test_logs_unreadable_log_fails_closed_with_reason(home):
    # A present-but-corrupt (non-UTF-8) log must fail closed to an explicit
    # log_unreadable reason — not crash, and not silently masquerade as an empty
    # readable log. Guards the contract the docstring promises (ADR-9).
    root = home / 'proj'
    root.mkdir()
    audit = mbs.InteractionAudit()
    audit.record('submit', mbs.canonicalize_root(str(root)), 'p1', 'JOB-A', 'queued')
    audit.path.write_bytes(b'\xff\xfe not valid utf-8 \x80\x81')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root)))

    assert result['status'] == 'success'
    assert result['records'] == []
    assert result['count'] == 0
    assert result['reason'] == 'log_unreadable'


def test_logs_limit_bounds_the_newest_tail(home):
    root = home / 'proj'
    root.mkdir()
    caller = mbs.canonicalize_root(str(root))
    audit = mbs.InteractionAudit()
    for index in range(5):
        audit.record('ping', caller, '', f'JOB-{index}', 'ok')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root), limit=2))

    assert result['count'] == 2
    assert result['total_matched'] == 5
    # The two newest records (the tail), oldest-first within the tail.
    assert [record['job_id'] for record in result['records']] == ['JOB-3', 'JOB-4']
    # Bounding the tail does not drop the rendering.
    assert all(record['kind'] == 'interaction' for record in result['records'])


def test_logs_performs_no_mutation(home):
    root = home / 'proj'
    root.mkdir()
    caller = mbs.canonicalize_root(str(root))
    audit = mbs.InteractionAudit()
    audit.record('submit', caller, 'p1', 'JOB-A', 'queued')
    before = audit.path.read_text(encoding='utf-8')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root), limit=1))

    after = mbs.InteractionAudit().path.read_text(encoding='utf-8')
    assert after == before
    # The rendering is a DERIVED view: the returned row is reshaped while the
    # on-disk bytes are byte-identical.
    assert result['records'][0]['kind'] == 'interaction'


def test_logs_joins_the_job_fate_onto_the_interaction_row(home):
    """A terminalized job's fate is rendered on its interaction row.

    The fate lives in its own ``kind='job_fate'`` record; the operator view joins
    it by ``job_id`` so "what happened to this job?" is answerable from the submit
    row itself — which is the whole point of emitting the fate into this 7-day
    store instead of joining against the hour-retained journal.
    """
    root = home / 'proj'
    root.mkdir()
    caller = mbs.canonicalize_root(str(root))
    audit = mbs.InteractionAudit()
    audit.record('submit', caller, 'p1', 'JOB-DONE', 'queued')
    audit.record('submit', caller, 'p1', 'JOB-LOST', 'queued')
    audit.record_job_fate('JOB-DONE', 'success', caller, 'p1')
    audit.record_job_fate('JOB-LOST', 'killed', caller, 'p1')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root)))

    interactions = [r for r in result['records'] if r['kind'] == 'interaction']
    fates = {r['job_id']: r['fate'] for r in interactions}
    # A completed job and an abandoned job are distinguishable — the defect this
    # closes rendered BOTH permanently as `outcome: queued`.
    assert fates == {'JOB-DONE': 'success', 'JOB-LOST': 'killed'}
    # Both still report the truthful request-scoped status, which really was queued.
    assert {r['request_status'] for r in interactions} == {'queued'}
    # The fate rows themselves are rendered with their own explicit kind label.
    fate_rows = [r for r in result['records'] if r['kind'] == 'job_fate']
    assert {r['fate'] for r in fate_rows} == {'success', 'killed'}


def test_logs_renders_legacy_row_fail_closed_with_unknown_fate(home):
    """A row predating the kind/request_status fields renders fail-closed.

    It is labelled an interaction row and carries an explicit ``unknown`` for both
    the request status and the fate — never a silently missing field (ADR-009).
    """
    root = home / 'proj'
    root.mkdir()
    caller = mbs.canonicalize_root(str(root))
    audit = mbs.InteractionAudit()
    audit.record('submit', caller, 'p1', 'JOB-OLD', 'queued')  # materialise the log
    legacy = {
        'op': 'submit',
        'project_root': caller,
        'plan_id': 'p1',
        'job_id': 'JOB-LEGACY',
        'outcome': 'queued',
        'timestamp': '2000-01-01T00:00:00Z',
    }
    with open(audit.path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(legacy) + '\n')

    result = mbs.run_logs(_variant(_LOGS_ARGS, root=str(root)))

    rendered = next(r for r in result['records'] if r['job_id'] == 'JOB-LEGACY')
    assert rendered['kind'] == 'interaction'
    assert rendered['request_status'] == 'unknown'
    assert rendered['fate'] == 'unknown'
    assert 'outcome' not in rendered


# =============================================================================
# config get / set / migrate — the machine-global build-slot cap
# =============================================================================


def _machine_config_path(home: Path) -> Path:
    """The machine-global cap file under the isolated home root."""
    return home / 'marshalld' / 'machine-config.json'


def _stage_machine_cap(home: Path, value: object) -> Path:
    """Stage a well-formed machine config carrying ``max_slots=value``."""
    path = _machine_config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'version': 1, 'build': {'queue': {'max_slots': value}}}), encoding='utf-8')
    return path


def _stage_machine_raw(home: Path, text: str) -> Path:
    """Stage raw bytes at the machine-config path (for the unreadable case)."""
    path = _machine_config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _repo_marshal_path() -> Path:
    """The caller repository's marshal.json, as the verbs themselves resolve it.

    Resolved through the production resolver rather than rebuilt from the
    fixture, so the test writes to the exact path ``config get`` / ``config
    migrate`` read. Under the autouse ``_plan_base_dir_sandbox`` this is the
    per-test sandbox, and ``_config_core.MARSHAL_PATH`` is patched to the same
    file — so the reader and the writer agree.
    """
    return Path(mbs.get_marshal_path())


def _stage_repo_marshal(queue_block: dict | None, **extra: Any) -> Path:
    """Stage a repository marshal.json carrying ``build.queue = queue_block``."""
    path = _repo_marshal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = dict(extra)
    if queue_block is not None:
        payload.setdefault('build', {})['queue'] = queue_block
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return path


def _snapshot(*paths: Path) -> dict[str, bytes | None]:
    """Capture each path's exact bytes, or ``None`` when it does not exist.

    ``None`` for a missing file is load-bearing: "both files unchanged" has to
    cover "and the one that did not exist still does not", which a bytes-only
    snapshot could not express.
    """
    return {str(p): (p.read_bytes() if p.exists() else None) for p in paths}


def _both_files(home: Path) -> tuple[Path, Path]:
    """The two files every migrate outcome is asserted against."""
    return _machine_config_path(home), _repo_marshal_path()


# --- config get --------------------------------------------------------------


def test_config_get_reports_the_machine_cap_with_its_source_and_path(home):
    """The cap is reported WITH its provenance, never as a bare number.

    ``max_slots`` alone cannot distinguish a configured 5 from a fallback 5, so
    an operator reading only the value cannot tell whether anyone ever set it.
    """
    _stage_machine_cap(home, 9)

    result = mbs.run_config_get(_CONFIG_GET_ARGS)

    assert result['status'] == 'success'
    assert result['max_slots'] == 9
    assert result['max_slots_source'] == 'machine_config'
    assert result['path'] == str(_machine_config_path(home))


def test_config_get_reports_an_unconfigured_host_as_default(home):
    """An unconfigured host says ``default``, not silence."""
    result = mbs.run_config_get(_CONFIG_GET_ARGS)

    assert result['max_slots'] == 5
    assert result['max_slots_source'] == 'default'


def test_config_get_reports_a_broken_machine_config_as_unreadable(home):
    """A broken file is named, never smoothed into "nothing configured"."""
    _stage_machine_raw(home, '{broken')

    result = mbs.run_config_get(_CONFIG_GET_ARGS)

    assert result['max_slots_source'] == 'unreadable'
    assert result['max_slots_detail'] is not None


def test_config_get_reports_an_absent_per_repo_key_as_absent(home):
    """``absent`` is stated explicitly rather than left as a missing key."""
    _stage_repo_marshal({'max_retries': 10})

    result = mbs.run_config_get(_CONFIG_GET_ARGS)

    assert result['per_repo_max_slots'] == 'absent'


def test_config_get_reports_a_present_per_repo_key_as_not_in_effect(home):
    """The demoted key is echoed with ``in_effect: False`` spelled out.

    Reporting the value without that flag would let a reader mistake it for the
    cap actually in force — which is the entire confusion the demotion creates.
    """
    _stage_machine_cap(home, 9)
    _stage_repo_marshal({'max_slots': 1, 'max_retries': 10})

    result = mbs.run_config_get(_CONFIG_GET_ARGS)

    assert result['per_repo_max_slots'] == {'value': 1, 'in_effect': False}
    assert result['max_slots'] == 9


def test_config_get_writes_neither_file(home):
    """``get`` is read-only — it must not materialise the machine config."""
    _stage_repo_marshal({'max_slots': 1})
    before = _snapshot(*_both_files(home))

    mbs.run_config_get(_CONFIG_GET_ARGS)

    assert _snapshot(*_both_files(home)) == before


# --- config set --------------------------------------------------------------


def test_config_set_round_trips_through_get(home):
    """What ``set`` writes is what ``get`` reads back, with source ``machine_config``."""
    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert result['status'] == 'success'
    assert result['max_slots'] == 7
    assert result['max_slots_source'] == 'machine_config'
    assert mbs.run_config_get(_CONFIG_GET_ARGS)['max_slots'] == 7


def test_config_set_notes_that_a_running_daemon_needs_no_restart(home):
    """The operator is told the daemon picks it up, so they do not restart it."""
    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert 'next submit' in result['note']


@pytest.mark.parametrize(
    'bad',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param(True, id='bool-true'),
        pytest.param(2.5, id='float'),
        pytest.param('8', id='string'),
    ],
)
def test_config_set_rejects_a_value_that_cannot_be_a_cap(home, bad):
    """An unusable cap is refused at the handler and never reaches disk.

    ``True`` is here deliberately: ``bool`` is an ``int`` subclass, so without an
    explicit guard a stored ``true`` would become a cap of 1 and serialize every
    build on the host. The float and string rows cover an in-process caller,
    which does not pass through argparse's ``type=int``.
    """
    result = mbs.run_config_set(_variant(_CONFIG_SET_ARGS, max_slots=bad))

    assert result['status'] == 'error'
    assert not _machine_config_path(home).exists()


@pytest.mark.parametrize(
    'raw',
    [
        pytest.param('true', id='bool-literal'),
        pytest.param('8.5', id='float-literal'),
        pytest.param('lots', id='word'),
    ],
)
def test_config_set_rejects_a_non_integer_at_the_cli_boundary(home, raw):
    """argparse's ``type=int`` refuses these before the handler ever runs.

    Asserted separately from the handler-level rejection above because the two
    are different boundaries: a CLI caller is stopped by the parser, an
    in-process caller by the writer's own validation. Testing only one would
    leave the other able to regress unnoticed.
    """
    with pytest.raises(SystemExit):
        _verb_args('config', 'set', '--max-slots', raw)


def test_config_set_repairs_an_invalid_machine_value(home):
    """``set`` is the UNCONDITIONAL writer, so it is the repair path.

    ``migrate`` refuses on an invalid machine value precisely because it must not
    overwrite; something has to be able to fix it, and this is that verb.
    """
    _stage_machine_cap(home, -3)

    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert result['max_slots'] == 7
    assert result['max_slots_source'] == 'machine_config'


def test_config_set_replaces_an_unreadable_machine_config(home):
    """The same repair path covers a corrupt file, which nothing else can fix."""
    _stage_machine_raw(home, '{not json')

    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert result['max_slots'] == 7
    assert result['max_slots_source'] == 'machine_config'


def test_config_set_does_not_touch_the_repo_marshal_json(home):
    """Setting the machine cap is not a migration — the repo file is untouched."""
    _stage_repo_marshal({'max_slots': 1, 'max_retries': 10})
    before = _snapshot(_repo_marshal_path())

    mbs.run_config_set(_CONFIG_SET_ARGS)

    assert _snapshot(_repo_marshal_path()) == before


# --- config migrate: nothing_to_migrate --------------------------------------


def test_migrate_with_no_per_repo_key_is_nothing_to_migrate(home):
    """A repo that carries no cap key has nothing to move, and writes nothing."""
    _stage_repo_marshal({'max_retries': 10})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'nothing_to_migrate'
    assert result['machine_config_modified'] is False
    assert result['marshal_json_modified'] is False
    assert _snapshot(*_both_files(home)) == before


def test_migrate_with_no_marshal_json_at_all_is_nothing_to_migrate(home):
    """An un-initialised project is a no-op success, not a crash."""
    assert not _repo_marshal_path().exists()
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'nothing_to_migrate'
    assert _snapshot(*_both_files(home)) == before


# --- config migrate: migrated ------------------------------------------------


def test_migrate_moves_the_value_when_nothing_is_set_machine_wide(home):
    """The happy path: the value lands machine-wide and the repo key goes."""
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'migrated'
    assert result['machine_config_modified'] is True
    assert result['marshal_json_modified'] is True
    assert result['max_slots'] == 12
    assert result['max_slots_source'] == 'machine_config'


def test_migrate_removes_only_the_cap_key_and_keeps_every_other(home):
    """Exactly ONE key goes — ``max_retries``, the block, and siblings survive.

    Asserted on parsed content rather than bytes because ``save_config``
    canonicalises key order and formatting on every write; the contract is which
    KEYS survive, not the file's byte layout.
    """
    _stage_repo_marshal(
        {'max_slots': 12, 'max_retries': 10, 'upper_limit_seconds': 600},
        project={'user_language': 'auto'},
    )

    mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    payload = json.loads(_repo_marshal_path().read_text(encoding='utf-8'))
    assert 'max_slots' not in payload['build']['queue']
    assert payload['build']['queue']['max_retries'] == 10
    assert payload['build']['queue']['upper_limit_seconds'] == 600
    assert payload['project'] == {'user_language': 'auto'}


def test_migrate_writes_the_value_into_the_machine_config(home):
    """The machine-global file gains the repo's value, source ``machine_config``."""
    _stage_repo_marshal({'max_slots': 12})

    mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    payload = json.loads(_machine_config_path(home).read_text(encoding='utf-8'))
    assert payload['build']['queue']['max_slots'] == 12
    assert mbs.run_config_get(_CONFIG_GET_ARGS)['max_slots_source'] == 'machine_config'


def test_a_second_migrate_after_a_migration_is_nothing_to_migrate(home):
    """Idempotence: the verb converges and does not keep reporting work."""
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['outcome'] == 'nothing_to_migrate'


# --- config migrate: removed_duplicate ---------------------------------------


def test_migrate_with_an_equal_machine_value_removes_only_the_duplicate(home):
    """Equal values need no copy — only the redundant repo key is removed."""
    _stage_machine_cap(home, 12)
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    machine_before = _snapshot(_machine_config_path(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'removed_duplicate'
    assert result['machine_config_modified'] is False
    assert result['marshal_json_modified'] is True
    # The machine-global file is byte-identical: there was nothing to write.
    assert _snapshot(_machine_config_path(home)) == machine_before
    assert 'max_slots' not in json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']


# --- config migrate: refused (both files byte-identical) ---------------------


def test_migrate_refuses_when_the_values_differ_and_changes_neither_file(home):
    """The central guarantee: a disagreement is reported, never resolved.

    Picking a winner is exactly what this verb must not do — a per-caller cap
    over one shared queue is the disagreement the queue itself reports, so
    silently choosing would install a cap the operator never chose.
    """
    _stage_machine_cap(home, 4)
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'values_differ'
    assert result['machine_config_modified'] is False
    assert result['marshal_json_modified'] is False
    assert _snapshot(*_both_files(home)) == before


def test_the_values_differ_refusal_names_both_values_and_both_ways_out(home):
    """A refusal the operator cannot act on is only half a refusal."""
    _stage_machine_cap(home, 4)
    _stage_repo_marshal({'max_slots': 12})

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['per_repo_max_slots'] == 12
    assert result['machine_max_slots'] == 4
    assert 'config set --max-slots 12' in result['error']
    assert str(_repo_marshal_path()) in result['error']


@pytest.mark.parametrize(
    ('staged', 'reason'),
    [
        pytest.param(0, 'machine_config_invalid', id='invalid-zero'),
        pytest.param(-1, 'machine_config_invalid', id='invalid-negative'),
        pytest.param(True, 'machine_config_invalid', id='invalid-bool'),
    ],
)
def test_migrate_refuses_an_invalid_machine_value_byte_identically(home, staged, reason):
    """An invalid machine value is NOT "unset" — the file exists and holds it.

    Copying over it could discard a cap that is merely mistyped, so migrate
    refuses and ``config set`` remains the repair path.
    """
    _stage_machine_cap(home, staged)
    _stage_repo_marshal({'max_slots': 12})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == reason
    assert _snapshot(*_both_files(home)) == before


def test_migrate_refuses_an_unreadable_machine_config_byte_identically(home):
    """The sharpest refusal: a cap may be configured in there and unreachable."""
    _stage_machine_raw(home, '{broken')
    _stage_repo_marshal({'max_slots': 12})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'machine_config_unreadable'
    assert _snapshot(*_both_files(home)) == before


@pytest.mark.parametrize(
    'bad',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param('8', id='string'),
        pytest.param(True, id='bool-true'),
    ],
)
def test_migrate_refuses_an_invalid_per_repo_value_byte_identically(home, bad):
    """Copying a value that could never be a cap would install a broken cap.

    The refusal is checked BEFORE the machine side is consulted, so the operator
    is told about their own bad value rather than about a comparison made
    against it.
    """
    _stage_repo_marshal({'max_slots': bad, 'max_retries': 10})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'per_repo_value_invalid'
    assert _snapshot(*_both_files(home)) == before


# --- config migrate: partial -------------------------------------------------


def test_migrate_reports_partial_when_the_repo_edit_does_not_commit(home, monkeypatch):
    """The machine write lands first, so a failed repo edit is RECOVERABLE.

    The ordering is deliberate: the reverse order would delete the operator's
    only record of the value before it was stored anywhere. ``partial`` names
    exactly what happened rather than reporting a success or a clean refusal.
    """
    import _config_core

    def _refuse(_config):
        raise _config_core.ConcurrentConfigModificationError('marshal.json changed on disk')

    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    monkeypatch.setattr(_config_core, 'save_config', _refuse)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'partial'
    assert result['machine_config_modified'] is True
    assert result['marshal_json_modified'] is False
    # The machine side IS settled, and the repo key IS still there.
    assert json.loads(_machine_config_path(home).read_text(encoding='utf-8'))['build']['queue']['max_slots'] == 12
    assert json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']['max_slots'] == 12


def test_a_re_run_after_partial_converges_to_removed_duplicate(home, monkeypatch):
    """The recovery path the ``partial`` report promises actually works.

    Without this the ``partial`` message would be an unverified claim — it tells
    the operator to re-run, so the re-run has to converge.
    """
    import _config_core

    real_save = _config_core.save_config

    def _refuse(_config):
        raise _config_core.ConcurrentConfigModificationError('marshal.json changed on disk')

    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    monkeypatch.setattr(_config_core, 'save_config', _refuse)
    assert mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)['outcome'] == 'partial'

    monkeypatch.setattr(_config_core, 'save_config', real_save)
    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'removed_duplicate'
    assert 'max_slots' not in json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']


# --- config migrate: the concurrent-writer race ------------------------------


def test_migrate_reclassifies_an_equal_value_that_lands_inside_the_guard(home, monkeypatch):
    """A racing writer that set the SAME value converges to removed_duplicate.

    Staged by having the conditional writer report "I did not write, and the
    post-state holds 12" — which is what it returns when a concurrent
    ``config set`` committed between the caller's resolve and the guarded write.
    The repo key is then removed on the basis of the POST state, not the stale
    pre-state.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    racing = mbs.CapResolution(value=12, source='machine_config', path=str(_machine_config_path(home)))
    monkeypatch.setattr(mbs, 'write_max_slots_if_unset', lambda _v: (racing, False))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'removed_duplicate'
    assert result['machine_config_modified'] is False
    assert 'max_slots' not in json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']


def test_migrate_refuses_a_different_value_that_lands_inside_the_guard(home, monkeypatch):
    """A racing writer that set a DIFFERENT value refuses, keeping the repo key.

    This is the data-loss case the guarded re-resolve exists to prevent: on a
    stale "unset" the verb would delete the repository's key while its value had
    already been replaced by the racing writer, losing it entirely.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    before = _snapshot(_repo_marshal_path())
    racing = mbs.CapResolution(value=4, source='machine_config', path=str(_machine_config_path(home)))
    monkeypatch.setattr(mbs, 'write_max_slots_if_unset', lambda _v: (racing, False))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'values_differ'
    assert result['marshal_json_modified'] is False
    assert _snapshot(_repo_marshal_path()) == before


# --- config set / migrate: a failed filesystem write is REPORTED --------------
#
# Both machine-config writers touch the filesystem at four points (the 0o700
# state-dir mkdir, the O_EXCL guard, the atomic temp-file replace, the chmod), so
# a read-only home root, a permission change under the state dir, or a full disk
# raises OSError. Callers on this surface read the outcome from the payload
# `status`, never from the exit code, so an uncaught OSError is a CONTRACT BREAK
# rather than a louder failure — the operator gets a traceback where the envelope
# was promised.


def test_config_set_reports_a_failed_write_as_an_error_envelope(home, monkeypatch):
    """An ``OSError`` from the writer becomes the envelope, not a traceback."""

    def _raise(_value):
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(mbs, 'write_max_slots', _raise)

    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert result['status'] == 'error'
    assert result['action'] == 'config set'
    assert result['reason'] == 'machine_config_write_failed'
    assert 'No space left on device' in result['error']


def test_config_set_still_reports_a_guard_timeout_under_its_own_code(home, monkeypatch):
    """The matched control for the OSError arm's ORDERING, not for its presence.

    ``TimeoutError`` is an ``OSError`` SUBCLASS, so an OSError arm placed ahead of
    it would swallow every write-guard timeout and relabel it a write failure —
    losing the ``TIMEOUT`` code that routes it. Without this control the test
    above would pass equally against that broken ordering.
    """

    def _raise(_value):
        raise TimeoutError('could not acquire machine-config write guard')

    monkeypatch.setattr(mbs, 'write_max_slots', _raise)

    result = mbs.run_config_set(_CONFIG_SET_ARGS)

    assert result['status'] == 'error'
    assert result['error_code'] == mbs.ErrorCode.TIMEOUT
    assert result.get('reason') != 'machine_config_write_failed'


def test_migrate_refuses_byte_identically_when_the_machine_write_raises_oserror(home, monkeypatch):
    """A write that raises BEFORE the replace refuses with BOTH files untouched.

    The refusal is the load-bearing part: it is what tells the operator nothing
    was half-migrated. An uncaught ``OSError`` here left them with a traceback and
    no statement about either file's state.

    The "before the replace" half of that sentence is load-bearing since the
    verb re-reads the machine side on this path: patching the writer raises
    ahead of every filesystem operation, so nothing committed and the refusal is
    TRUE. Its counterpart below injects the failure AFTER the replace, where the
    same refusal would be false — this test is what keeps that correction from
    weakening the genuine refusal into a blanket ``partial``.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    before = _snapshot(*_both_files(home))

    def _raise(_value):
        raise OSError(13, 'Permission denied')

    monkeypatch.setattr(mbs, 'write_max_slots_if_unset', _raise)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'machine_config_write_failed'
    assert result['machine_config_modified'] is False
    assert result['marshal_json_modified'] is False
    assert _snapshot(*_both_files(home)) == before


# --- config migrate: the write raised AFTER the atomic replace ----------------
#
# The machine-global write is not all-or-nothing from this verb's point of view.
# ``_write_cap_unguarded`` commits the atomic replace and THEN stats and chmods
# the committed file, so an OSError from either of those arrives with the
# migrated cap ALREADY on disk — where the refusal above ("Neither file was
# changed") is simply false. Which side of the replace the failure fell on is
# therefore read back rather than assumed.


def _fail_the_cap_chmod(home: Path, patcher: pytest.MonkeyPatch) -> None:
    """Make the POST-REPLACE chmod in ``_write_cap_unguarded`` raise.

    Two patches, both inside ``_machine_config``'s own namespace, and both
    needed:

    * ``_FILE_MODE`` is redirected because the post-replace chmod is otherwise
      never executed: ``atomic_write_file`` writes through
      ``tempfile.mkstemp``, which creates the temp file ``0o600`` and whose mode
      ``os.replace`` carries over — so the committed file already carries the
      target mode and the ``!=`` test skips the call. Pointing the target mode
      somewhere the fresh file is NOT makes the real post-replace call run.
    * ``os.chmod`` then raises, but ONLY for the cap file's own path. The same
      write also chmods the ``0o700`` state directory, and the guard file is
      created under it, so a blanket failure would abort the write somewhere
      ahead of the replace and re-create the very nothing-committed state these
      tests exist to tell apart.

    The failure is deliberately NOT injected by patching the writer: that raises
    before any filesystem operation, which is exactly why the sibling refusal
    test could never reach a committed-then-failed state.
    """
    cap_path = _machine_config_path(home)
    real_chmod = machine_config.os.chmod

    def _chmod(path, mode, *args, **kwargs):
        if str(path) == str(cap_path):
            raise OSError(13, 'Permission denied')
        return real_chmod(path, mode, *args, **kwargs)

    patcher.setattr(machine_config, '_FILE_MODE', 0o640)
    patcher.setattr(machine_config.os, 'chmod', _chmod)


def test_migrate_reports_partial_when_the_write_fails_after_the_atomic_replace(home, monkeypatch):
    """A post-replace failure cannot report a refusal — the cap is on disk.

    This is the inverse of the false-success class: the old report actively
    asserted a state that did not hold, telling the operator both files were
    untouched while ``machine-config.json`` already held the migrated cap. The
    machine side landing is asserted FIRST, because it is the fact the report
    then has to be consistent with.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    _fail_the_cap_chmod(home, monkeypatch)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert json.loads(_machine_config_path(home).read_text(encoding='utf-8'))['build']['queue']['max_slots'] == 12
    assert result['status'] == 'error'
    assert result['outcome'] == 'partial'
    assert result['reason'] == 'machine_config_write_failed_after_commit'
    assert result['machine_config_modified'] is True
    assert result['marshal_json_modified'] is False
    assert 'Neither file was changed' not in result['detail']
    # The per-repo key is still present — that is the half a re-run has to finish.
    assert json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']['max_slots'] == 12


def test_a_re_run_after_a_post_replace_partial_converges_to_removed_duplicate(home):
    """The recovery the ``partial`` detail names actually converges.

    The report tells the operator to re-run, so the re-run has to complete the
    migration — otherwise the correction would have replaced a false refusal
    with an unverified instruction. The second run reaches the equal-values
    branch and removes the now-redundant per-repo key.

    The failure injection is scoped to its own ``MonkeyPatch`` context rather
    than undone on the test's fixture-shared instance: ``home`` redirects
    ``PLAN_MARSHALL_HOME`` through that same instance, so a blanket ``undo()``
    would point the re-run at the developer's real ``~/.plan-marshall``.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})
    with pytest.MonkeyPatch.context() as failing:
        _fail_the_cap_chmod(home, failing)
        assert mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)['outcome'] == 'partial'

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'success'
    assert result['outcome'] == 'removed_duplicate'
    assert 'max_slots' not in json.loads(_repo_marshal_path().read_text(encoding='utf-8'))['build']['queue']


def test_migrate_reports_undetermined_when_the_machine_state_cannot_be_established(home, monkeypatch):
    """Fail-closed: an unreadable machine side claims NEITHER partial nor untouched.

    The re-read is what distinguishes ``partial`` from ``refused``, so a re-read
    that cannot classify must not pick either — asserting ``partial`` would claim
    a migration that may never have happened, and asserting the refusal would
    claim both files untouched over a file nobody can read. Both modification
    fields are OMITTED rather than sent as ``false``: ``false`` there IS the
    refusal's both-files-untouched guarantee.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})

    def _corrupt_then_raise(_value):
        _stage_machine_raw(home, '{ not json')
        raise OSError(5, 'Input/output error')

    monkeypatch.setattr(mbs, 'write_max_slots_if_unset', _corrupt_then_raise)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['status'] == 'error'
    assert result['outcome'] == 'undetermined'
    assert result['reason'] == 'machine_config_state_undetermined'
    assert 'machine_config_modified' not in result
    assert 'marshal_json_modified' not in result
    assert 'Neither file was changed' not in result['detail']


def test_a_configured_but_different_cap_after_the_raise_is_undetermined_not_partial(home, monkeypatch):
    """The matched control: ``partial`` is gated on the VALUE, not on "something is set".

    A raise that leaves a cap which is not this repository's value did not land
    this migration, so reporting ``partial`` would trade the old false refusal
    for a false partial in the other direction. Without this pair, the partial
    test above would pass equally against a branch that fired on any configured
    machine side at all.
    """
    _stage_repo_marshal({'max_slots': 12, 'max_retries': 10})

    def _set_a_foreign_cap_then_raise(_value):
        _stage_machine_cap(home, 4)
        raise OSError(5, 'Input/output error')

    monkeypatch.setattr(mbs, 'write_max_slots_if_unset', _set_a_foreign_cap_then_raise)

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['outcome'] == 'undetermined'
    assert 'machine_config_modified' not in result


# --- the reported per-repo value is TOON-injection safe -----------------------
#
# `read_per_repo_max_slots` returns the repository's value raw and unvalidated by
# design, so it can be a string carrying control characters. Every pre-existing
# test over these two reporting surfaces passes only INTEGERS, and the
# invalid-migration tests never assert the reported field at all — so deleting
# `report_safe` from either site left the whole suite green. These tests fail
# when it is removed, which is the only thing that makes them a pin.

#: A raw per-repo value whose later lines are TOON-shaped sibling keys. The two
#: planted keys are exactly the pair the sanitiser's own docstring names: they
#: would reparse a `refused` migration (both files deliberately untouched) as a
#: completed one.
_CONTROL_BEARING_PER_REPO = '1\x00\x1f\x7f\nstatus: success\noutcome: migrated'


def test_config_get_strips_control_characters_from_the_per_repo_report(home):
    """``config get``'s report echoes the value MINUS the unemittable bytes."""
    _stage_repo_marshal({'max_slots': _CONTROL_BEARING_PER_REPO})

    reported = mbs.run_config_get(_CONFIG_GET_ARGS)['per_repo_max_slots']['value']

    assert reported == '1status: successoutcome: migrated'
    for forbidden in ('\n', '\x00', '\x1f', '\x7f'):
        assert forbidden not in reported


def test_an_invalid_migrate_refusal_cannot_reparse_as_a_completed_migration(home):
    """The severity of the class, asserted end to end rather than described.

    The planted value carries ``status: success`` / ``outcome: migrated``. Left
    unsanitised those lines land at column zero of this refusal's own TOON, where
    a consumer reparsing the envelope reads them as its keys — reporting a
    completed migration for a run that deliberately changed neither file.
    """
    _stage_repo_marshal({'max_slots': _CONTROL_BEARING_PER_REPO})
    before = _snapshot(*_both_files(home))

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)
    assert result['status'] == 'error'
    assert result['outcome'] == 'refused'
    assert result['reason'] == 'per_repo_value_invalid'

    reparsed = parse_toon(serialize_toon(result))

    assert reparsed['status'] == 'error'
    assert reparsed['outcome'] == 'refused'
    # And the refusal's central guarantee still holds.
    assert _snapshot(*_both_files(home)) == before


def test_a_clean_invalid_per_repo_value_is_still_reported_verbatim(home):
    """The matched positive control: sanitising is not blanking the report.

    Without this, the two tests above would pass equally against an
    implementation that reported an empty string for every foreign value — which
    would strip the operator of the one thing the refusal exists to tell them,
    namely which value in their own file to go and fix.
    """
    _stage_repo_marshal({'max_slots': 'eight'})

    result = mbs.run_config_migrate(_CONFIG_MIGRATE_ARGS)

    assert result['reason'] == 'per_repo_value_invalid'
    assert result['per_repo_max_slots'] == 'eight'
