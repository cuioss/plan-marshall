#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D3: the daemon reports the cap it is applying, and re-resolves it per submit.

Two failures shared one shape — a stale cap nobody could see — and this suite
pins both halves of the fix at the DAEMON level:

* **The running daemon reports its own cap, with its source.** ``ping`` carries
  ``max_slots`` AND ``max_slots_source``, because the VALUE alone is not a
  reportable fact: a cap that degraded to :data:`DEFAULT_MAX_SLOTS` is
  byte-identical to one an operator deliberately set to the same number. Only the
  source separates them, so every assertion here that reads a value is paired
  with one that reads the source, and the configured-vs-fallback pair is tested
  as a matched control rather than asserted one-sidedly.
* **The cap is re-resolved on every submit.** A machine-global daemon may serve
  other projects' builds for hours, so an operator's ``config set`` has to take
  effect without a restart. The re-resolve is bound to SUBMIT specifically, and
  the negative control for that binding is a ``ping`` taken after the config
  moved but before any submit: it must still report the OLD cap, or the test
  would pass just as well against a daemon that re-resolved on every request.

**Cap resolution itself is not under test here** — that contract lives in
``test_machine_config.py``, which owns the source partition and the cwd
independence of :func:`resolve_max_slots`. What this suite adds is the
daemon-level integration of it: the cwd-move control below asserts that the
daemon, which ``double_fork``s and ``chdir('/')``s away from every repository,
still reports the machine-global value — the exact path on which the cap once
degraded silently. Both directions are asserted (moved out, and from inside a
repository that sets a different cap of its own), because a cap that is
independent of the working directory is independent of it in both directions.

Every test drives the REAL resolver against a real machine-global config file
under an isolated ``PLAN_MARSHALL_HOME``; nothing is monkeypatched into the
resolution path. ``marshalld`` binds :func:`resolve_max_slots` by value at
import, so a patched module attribute would not reach it anyway — and a test
that patched it would stop exercising the file-reading behaviour that broke.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

# PLAIN imports, deliberately: the build-server suites annotate against
# ``marshalld.Daemon``, and only a plain import gives mypy the real module — the
# shared loader returns ``Any``, which turns every such annotation into an
# undefined name. ``_machine_config`` is imported plainly for the same reason
# ``marshalld`` imports it plainly: the constants compared here must be the SAME
# objects the daemon closed over, not a second loaded copy of them.
import _machine_config
import marshalld
import pytest
from _build_server_protocol import STATUS_QUEUED, make_job_spec
from _build_server_registry import canonicalize_root, register_project
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir.

    ``PLAN_MARSHALL_HOME`` is the documented override for
    :func:`marketplace_paths.home_root`, so no test here reads or writes the
    developer's real ``~/.plan-marshall`` tree under ``-n auto``.
    """
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def _config_path(home: Path) -> Path:
    """Return the machine-global config path under an isolated ``home``."""
    return home / 'marshalld' / 'machine-config.json'


def _write_raw(home: Path, text: str) -> Path:
    """Write raw text to the machine-config path, creating its parent."""
    path = _config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _write_cap(home: Path, value: object) -> Path:
    """Write a well-formed machine config carrying ``max_slots=value``."""
    return _write_raw(home, json.dumps({'version': 1, 'build': {'queue': {'max_slots': value}}}))


def _daemon(tmp_path: Path, *, max_slots: int, seed_resolution: bool = True) -> marshalld.Daemon:
    """Build a daemon whose scheduler cap is ``max_slots``.

    ``seed_resolution`` mirrors the two real construction paths: :func:`build_daemon`
    passes the SAME resolution it sized the scheduler from, while a
    hand-constructed daemon leaves it unset and the constructor resolves one
    itself. Both are exercised, because the reported cap must come from a real
    resolution on either path.
    """
    return marshalld.Daemon(
        scheduler=Scheduler(max_slots=max_slots),
        journal=Journal(),
        log_dir=tmp_path / 'job-logs',
        cap_resolution=_machine_config.resolve_max_slots() if seed_resolution else None,
    )


def _ping(daemon: marshalld.Daemon) -> dict:
    """Drive one ``ping`` through the daemon's real request dispatch."""
    response: dict = asyncio.run(daemon.handle_request({'op': 'ping'}))
    return response


def _register_and_spec(home: Path, tmp_path: Path):
    """Register a project and return a job spec the verifier will accept.

    A BARE ``python3``, matching what the routing seam actually submits: with no
    baseline pin the verifier requires a bare canonical interpreter name, so an
    absolute ``sys.executable`` would be refused before the scheduler — and
    before the cap re-resolve — was ever reached.
    """
    root = tmp_path / 'proj'
    (root / '.plan').mkdir(parents=True)
    (root / '.plan' / 'execute-script.py').write_text('print("ok")')
    canonical = canonicalize_root(root)
    register_project(canonical, notation_allowlist=[_NOTATION])
    return make_job_spec(
        command=['python3', str(root / '.plan' / 'execute-script.py'), _NOTATION, 'run'],
        exec_path=canonical,
        project_path=canonical,
        plan_id='p',
    )


# =============================================================================
# ping reports the cap the RUNNING daemon is applying, and its source
# =============================================================================


def test_ping_reports_a_configured_cap_as_machine_config_with_no_detail(home, tmp_path):
    # The nominal case: a cap read from the machine-global config needs no
    # explanation, so `max_slots_detail` is absent rather than present-and-None.
    _write_cap(home, 9)

    response = _ping(_daemon(tmp_path, max_slots=9))

    assert response['max_slots'] == 9
    assert response['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    assert 'max_slots_detail' not in response


def test_ping_reports_an_unconfigured_cap_as_the_default_source(home, tmp_path):
    # No config file at all is a legitimate unconfigured state. The value is the
    # fallback, and the source says so — which is the whole point, since the
    # value is indistinguishable from a configured one (see the matched pair
    # below).
    assert not _config_path(home).exists()

    response = _ping(_daemon(tmp_path, max_slots=_machine_config.DEFAULT_MAX_SLOTS, seed_resolution=False))

    assert response['max_slots'] == _machine_config.DEFAULT_MAX_SLOTS
    assert response['max_slots_source'] == _machine_config.SOURCE_DEFAULT
    # `detail` rides along for every non-nominal source, carrying None when there
    # is nothing to explain. Its PRESENCE is what distinguishes this shape from
    # the machine_config one above.
    assert 'max_slots_detail' in response
    assert response['max_slots_detail'] is None


def test_a_configured_cap_and_a_fallback_of_the_same_value_differ_only_in_source(home, tmp_path):
    # The claim the source field exists for, asserted as a matched pair rather
    # than one-sidedly: a cap deliberately SET to the default number reports the
    # identical value as an unconfigured one, so a reader consulting `max_slots`
    # alone cannot tell a deliberate choice from a degradation. Only the source
    # separates them.
    unconfigured = _ping(_daemon(tmp_path, max_slots=_machine_config.DEFAULT_MAX_SLOTS, seed_resolution=False))
    _write_cap(home, _machine_config.DEFAULT_MAX_SLOTS)
    configured = _ping(_daemon(tmp_path, max_slots=_machine_config.DEFAULT_MAX_SLOTS))

    assert configured['max_slots'] == unconfigured['max_slots']
    assert configured['max_slots_source'] != unconfigured['max_slots_source']
    assert configured['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    assert unconfigured['max_slots_source'] == _machine_config.SOURCE_DEFAULT


def test_ping_reports_an_invalid_cap_with_the_offending_value_in_the_detail(home, tmp_path):
    # A key that cannot be a cap is its own state, never collapsed into
    # `default`: the file exists and holds something, and the detail names what.
    _write_cap(home, 0)

    response = _ping(_daemon(tmp_path, max_slots=_machine_config.DEFAULT_MAX_SLOTS, seed_resolution=False))

    assert response['max_slots'] == _machine_config.DEFAULT_MAX_SLOTS
    assert response['max_slots_source'] == _machine_config.SOURCE_INVALID
    assert '0' in response['max_slots_detail']


def test_ping_reports_an_unreadable_config_as_unreadable_with_a_detail(home, tmp_path):
    # An unparseable file may well carry a configured cap that is merely
    # unreachable, so it is reported as its own state with the parse error — never
    # as `default`, which would read as "nothing is configured".
    _write_raw(home, 'not json at all')

    response = _ping(_daemon(tmp_path, max_slots=_machine_config.DEFAULT_MAX_SLOTS, seed_resolution=False))

    assert response['max_slots'] == _machine_config.DEFAULT_MAX_SLOTS
    assert response['max_slots_source'] == _machine_config.SOURCE_UNREADABLE
    assert response['max_slots_detail']


# That the cap fields are ADDITIVE — they ride alongside the in-flight / queued
# counts rather than displacing them — is asserted where the ping payload's shape
# is owned: ``test_daemon_ping_counts.py``.


# =============================================================================
# build_daemon seeds ONE resolution into both the scheduler and the report
# =============================================================================


def test_build_daemon_sizes_the_scheduler_and_the_report_from_one_resolution(home):
    # Two consumers of one resolution: the cap admission applies and the cap
    # `ping` reports. Resolving twice would let them start out disagreeing, and
    # the disagreement would be invisible — both numbers look plausible.
    _write_cap(home, 3)

    daemon = marshalld.build_daemon()
    response = _ping(daemon)

    assert response['max_slots'] == 3
    assert response['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    # Reading the scheduler's own cap is what makes this "both", not just "the
    # report": a seed that reached only the report would satisfy the assertions
    # above. The suite already reaches for daemon internals (`_tasks`) where the
    # claim is about wiring rather than protocol.
    assert daemon._scheduler.max_slots == 3


# =============================================================================
# the cap is re-resolved per submit (a live `config set` needs no restart)
# =============================================================================


def test_submit_re_resolves_the_cap_so_a_live_config_set_takes_effect(home, tmp_path):
    # The deliverable's central claim. The daemon starts on a cap of 1, an
    # operator raises it to 7 under the running process, and the NEXT submit is
    # what picks it up — in both the reported resolution and the scheduler's
    # admission cap, which must move together or the daemon reports one cap while
    # admitting against another.
    _write_cap(home, 1)
    spec = _register_and_spec(home, tmp_path)

    async def _drive():
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=1),
            journal=Journal(),
            log_dir=tmp_path / 'job-logs',
            cap_resolution=_machine_config.resolve_max_slots(),
        )
        before = await daemon.handle_request({'op': 'ping'})
        _write_cap(home, 7)
        # The matched negative control for the binding: the config has ALREADY
        # moved, but no submit has happened. A daemon that re-resolved on every
        # request would report 7 here, and the assertion below would not
        # distinguish per-submit re-resolution from per-request re-resolution.
        unchanged = await daemon.handle_request({'op': 'ping'})
        submitted = await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})
        after = await daemon.handle_request({'op': 'ping'})
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return before, unchanged, submitted, after, daemon

    before, unchanged, submitted, after, daemon = asyncio.run(_drive())

    assert submitted['status'] == STATUS_QUEUED
    assert before['max_slots'] == 1
    assert unchanged['max_slots'] == 1
    assert after['max_slots'] == 7
    assert after['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    assert daemon._scheduler.max_slots == 7


def test_a_config_broken_under_a_live_daemon_degrades_audibly_on_the_next_submit(home, tmp_path):
    # The other direction of the same seam: the re-resolve must not assume it
    # will find something usable. A config that becomes unreadable while the
    # daemon runs degrades to the reported fallback — audibly, via the source —
    # rather than raising on the admission path of a build or wedging the cap.
    _write_cap(home, 6)
    spec = _register_and_spec(home, tmp_path)

    async def _drive():
        daemon = marshalld.Daemon(
            scheduler=Scheduler(max_slots=6),
            journal=Journal(),
            log_dir=tmp_path / 'job-logs',
            cap_resolution=_machine_config.resolve_max_slots(),
        )
        before = await daemon.handle_request({'op': 'ping'})
        _write_raw(home, '{ truncated')
        submitted = await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})
        after = await daemon.handle_request({'op': 'ping'})
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        return before, submitted, after, daemon

    before, submitted, after, daemon = asyncio.run(_drive())

    assert submitted['status'] == STATUS_QUEUED
    assert before['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    assert after['max_slots'] == _machine_config.DEFAULT_MAX_SLOTS
    assert after['max_slots_source'] == _machine_config.SOURCE_UNREADABLE
    assert daemon._scheduler.max_slots == _machine_config.DEFAULT_MAX_SLOTS


# =============================================================================
# cwd-move regression control (the post-double_fork `chdir('/')` defect)
# =============================================================================


def _repo_with_its_own_cap(tmp_path: Path, value: int) -> Path:
    """Create a repository whose own ``marshal.json`` sets a different cap."""
    repo = tmp_path / 'repo'
    (repo / '.plan').mkdir(parents=True)
    (repo / '.plan' / 'marshal.json').write_text(
        json.dumps({'build': {'queue': {'max_slots': value}}}), encoding='utf-8'
    )
    return repo


def test_the_daemon_reports_the_machine_global_cap_from_outside_every_repository(home, tmp_path, monkeypatch):
    # THE regression control. `marshalld` double-forks and `chdir('/')`s, so the
    # previous cwd-relative read walked up from a directory inside no repository,
    # found nothing, and produced the default — indistinguishable from a
    # deliberately configured 5. Both conditions are staged together here: a
    # repository that sets its own different cap, and a cwd moved out of it.
    _write_cap(home, 8)
    _repo_with_its_own_cap(tmp_path, 2)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    response = _ping(_daemon(tmp_path, max_slots=8, seed_resolution=False))

    assert response['max_slots'] == 8
    assert response['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    # Both wrong answers are named, so the assertion cannot pass by coincidence:
    # 8 is neither the silent degradation nor the per-repo key.
    assert response['max_slots'] != _machine_config.DEFAULT_MAX_SLOTS
    assert response['max_slots'] != 2


def test_the_daemon_reports_the_same_cap_from_inside_that_repository(home, tmp_path, monkeypatch):
    # The matched positive control: a cap that is independent of the working
    # directory is independent of it in BOTH directions. Without this, the test
    # above would also pass against a resolver that happened to read the
    # machine-global file only when no repository was in reach.
    _write_cap(home, 8)
    repo = _repo_with_its_own_cap(tmp_path, 2)
    monkeypatch.chdir(repo)

    response = _ping(_daemon(tmp_path, max_slots=8, seed_resolution=False))

    assert response['max_slots'] == 8
    assert response['max_slots_source'] == _machine_config.SOURCE_MACHINE_CONFIG
    assert response['max_slots'] != 2
