#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``script-shared/scripts/build/_machine_config.py``.

The machine-global cap home is the single reader/writer of
``<home_root>/marshalld/machine-config.json``, the ONE place the build-slot cap
lives. Contract under test:

* **Every source value is reachable and distinct** — ``machine_config`` for a
  valid positive int, ``default`` when the file or the key is absent,
  ``invalid`` when the key holds a value that cannot be a cap, ``unreadable``
  when the file exists but cannot be read or parsed. The partition matters more
  than the value: every non-nominal source falls back to the SAME
  ``DEFAULT_MAX_SLOTS``, so ``value`` alone cannot tell a configured 5 from a
  degraded 5 and only ``source`` can.
* **An unreadable or invalid file is never reported as ``machine_config`` or
  ``default``** — the success criterion that keeps a broken file audible instead
  of silently reading as "nothing configured".
* **Cwd independence** — resolution consults no working directory and no
  repository. This is the defect the module exists to fix: ``marshalld``
  double-forks and ``chdir('/')``, so a cwd-relative read walked up from ``/``,
  found no repository, and produced the default silently. The test pins it by
  running from a directory that DOES hold a ``.plan/marshal.json`` carrying a
  different cap and asserting that file is ignored.
* **``bool`` rejection** — ``True`` is an ``int`` subclass, so a stored ``true``
  would otherwise resolve to a cap of 1. It is rejected on both the read and the
  write path.
* **Write is atomic, ``0o600``, and preserves sibling keys** — the cap is one
  key in a file that may carry others, so a write that dropped them would lose
  unrelated machine-global state.
* **The state directory is ``0o700``** — machine-global state is not
  world-listable.
* **A demoted per-repo key is read to REPORT it, never to resolve a cap** —
  ``read_per_repo_max_slots`` returns the repository's value raw and
  unvalidated (an unusable value included, because the report has to echo what
  the operator's own file says), and ``per_repo_max_slots_warning`` renders the
  audible not-in-effect message: both values, the machine-global source, both
  paths, and both ways out.
* **The conditional migration writer refuses rather than overwrites** —
  ``write_max_slots_if_unset`` writes ONLY on ``default``. ``machine_config``,
  ``invalid`` and ``unreadable`` all leave the file byte-identical, because each
  means the file exists and holds something a copy would destroy. Its unset test
  runs INSIDE the write guard, so a value committed by a racing writer is
  observed and preserved — the ordering assertion is what stops a caller
  deleting its repository key on a stale "unset".
* **One guard serializes BOTH writers, and a stale guard is reclaimed** — tested
  over both entry points, since a guard only one writer respected would
  serialize nothing. Each blocking / reclaiming assertion is paired with its
  matched control, so neither passes against an implementation that never
  reclaims or always reclaims.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from conftest import load_script_module

# The loader-contract guard enumerates the arguments this call is made with
# across the test tree statically, so the three resolution arguments are
# module-level string constants passed POSITIONALLY. A star-unpacked tuple would
# be invisible to that guard.
_BUNDLE = 'plan-marshall'
_SKILL = 'script-shared'
_SCRIPT = 'build/_machine_config.py'

# An explicit module name, never the ``_machine_config`` stem: ``build_queue``
# imports that module plainly, so registering under the stem would DISPLACE the
# instance ``build_queue`` closed over and leave two coexisting copies.
machine_config = load_script_module(_BUNDLE, _SKILL, _SCRIPT, 'machine_config_under_test')


# =============================================================================
# Fixtures and helpers
# =============================================================================


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stage an isolated machine-global home root under ``tmp_path``.

    ``PLAN_MARSHALL_HOME`` is the documented override for
    :func:`marketplace_paths.home_root`, so the suite never touches the
    developer's real ``~/.plan-marshall`` under ``-n auto``.
    """
    home_dir = tmp_path / 'home'
    home_dir.mkdir()
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home_dir))
    return home_dir


def _config_path(home: Path) -> Path:
    """Return the machine-config path under an isolated ``home``."""
    return home / 'marshalld' / 'machine-config.json'


def _write_raw(home: Path, text: str) -> Path:
    """Write raw bytes to the machine-config path, creating its parent."""
    path = _config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _write_cap(home: Path, value: object, **siblings: object) -> Path:
    """Write a well-formed machine config carrying ``max_slots=value``."""
    payload: dict = {'version': 1, 'build': {'queue': {'max_slots': value}}}
    payload.update(siblings)
    return _write_raw(home, json.dumps(payload))


# =============================================================================
# Path resolution
# =============================================================================


def test_machine_config_path_sits_beside_the_registry_under_the_home_root(home: Path) -> None:
    """The config is a machine-global file in the marshalld state dir."""
    assert machine_config.machine_config_path() == _config_path(home)
    assert machine_config.machine_config_dir() == home / 'marshalld'


# =============================================================================
# source: machine_config
# =============================================================================


def test_valid_positive_int_resolves_as_machine_config(home: Path) -> None:
    """A configured positive int is reported as configured, with no detail."""
    _write_cap(home, 9)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == 9
    assert resolution.source == machine_config.SOURCE_MACHINE_CONFIG
    assert resolution.path == str(_config_path(home))
    assert resolution.detail is None


# =============================================================================
# source: default
# =============================================================================


def test_absent_file_resolves_as_default(home: Path) -> None:
    """No file at all is a legitimate unconfigured state, not an error."""
    assert not _config_path(home).exists()

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_DEFAULT
    assert resolution.detail is None


def test_absent_key_resolves_as_default(home: Path) -> None:
    """A readable file that simply does not set the cap is unconfigured."""
    _write_raw(home, json.dumps({'version': 1, 'build': {'queue': {}}}))

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_DEFAULT


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param({'version': 1}, id='no-build-block'),
        pytest.param({'build': {}}, id='no-queue-block'),
        pytest.param({'build': 'not-a-block'}, id='build-not-a-dict'),
        pytest.param({'build': {'queue': 'not-a-block'}}, id='queue-not-a-dict'),
    ],
)
def test_unreachable_key_resolves_as_default(home: Path, payload: dict) -> None:
    """A block that puts the key out of reach reads as the key being absent."""
    _write_raw(home, json.dumps(payload))

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_DEFAULT


# =============================================================================
# source: invalid
# =============================================================================


@pytest.mark.parametrize(
    'stored',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param('5', id='string'),
        pytest.param(2.5, id='float'),
        pytest.param(None, id='null'),
        pytest.param([5], id='list'),
        pytest.param(True, id='bool-true'),
        pytest.param(False, id='bool-false'),
    ],
)
def test_unusable_value_resolves_as_invalid_and_names_it(home: Path, stored: object) -> None:
    """A present-but-unusable cap falls back, is flagged, and names the value.

    ``True`` / ``False`` are in this set deliberately: ``bool`` is an ``int``
    subclass, so without an explicit guard a stored ``true`` would resolve to a
    cap of 1 and silently serialize every build on the host.
    """
    _write_cap(home, stored)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_INVALID
    assert resolution.detail is not None
    assert repr(stored) in resolution.detail


# =============================================================================
# source: unreadable
# =============================================================================


def test_unparseable_file_resolves_as_unreadable(home: Path) -> None:
    """Broken JSON is its own state — a cap may be in there and unreachable."""
    _write_raw(home, '{not json at all')

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_UNREADABLE
    assert resolution.detail is not None


@pytest.mark.parametrize(
    'text',
    [
        pytest.param('[]', id='list'),
        pytest.param('"a string"', id='string'),
        pytest.param('7', id='bare-int'),
        pytest.param('null', id='null'),
    ],
)
def test_non_object_payload_resolves_as_unreadable(home: Path, text: str) -> None:
    """Valid JSON that is not an object cannot hold the key path."""
    _write_raw(home, text)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_UNREADABLE
    assert resolution.detail is not None


def test_unopenable_path_resolves_as_unreadable(home: Path) -> None:
    """A path that exists but cannot be opened as a file is ``unreadable``.

    Staged as a DIRECTORY at the config path rather than via ``chmod 0o000``,
    because a permission-based fixture does not hold when the suite runs as a
    user that bypasses the mode (notably root in a container).
    """
    _config_path(home).mkdir(parents=True)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_UNREADABLE
    assert resolution.detail is not None


def test_broken_file_is_never_reported_as_configured_or_unconfigured(home: Path) -> None:
    """The success criterion, asserted as one statement over both broken shapes.

    ``value`` is identical to a configured 5 in each case, so the ONLY thing
    separating a degraded read from a healthy one is ``source`` — a caller that
    saw ``default`` here would conclude nothing was ever configured.
    """
    _write_raw(home, '{broken')
    assert machine_config.resolve_max_slots().source not in (
        machine_config.SOURCE_MACHINE_CONFIG,
        machine_config.SOURCE_DEFAULT,
    )

    _write_cap(home, -3)
    assert machine_config.resolve_max_slots().source not in (
        machine_config.SOURCE_MACHINE_CONFIG,
        machine_config.SOURCE_DEFAULT,
    )


# =============================================================================
# Cwd independence (the defect this module exists to remove)
# =============================================================================


def test_resolution_ignores_a_per_repo_marshal_json_in_the_cwd(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository's own cap in the cwd does not influence the machine cap."""
    repo = tmp_path / 'repo'
    (repo / '.plan').mkdir(parents=True)
    (repo / '.plan' / 'marshal.json').write_text(json.dumps({'build': {'queue': {'max_slots': 99}}}), encoding='utf-8')
    _write_cap(home, 7)
    monkeypatch.chdir(repo)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == 7
    assert resolution.source == machine_config.SOURCE_MACHINE_CONFIG


def test_absent_machine_config_defaults_even_when_the_cwd_repo_configures_a_cap(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-repo key is not a fallback — with no machine cap, the default wins.

    The sharper half of cwd independence: reading 99 here would mean the repo
    file is still consulted, and reporting ``machine_config`` would mean a
    per-repo value had been laundered into a machine-global answer.
    """
    repo = tmp_path / 'repo'
    (repo / '.plan').mkdir(parents=True)
    (repo / '.plan' / 'marshal.json').write_text(json.dumps({'build': {'queue': {'max_slots': 99}}}), encoding='utf-8')
    assert not _config_path(home).exists()
    monkeypatch.chdir(repo)

    resolution = machine_config.resolve_max_slots()

    assert resolution.value == machine_config.DEFAULT_MAX_SLOTS
    assert resolution.source == machine_config.SOURCE_DEFAULT


def test_default_cap_is_five(home: Path) -> None:
    """The default is pinned: the interim operator guidance is 5."""
    assert machine_config.DEFAULT_MAX_SLOTS == 5


# =============================================================================
# write_max_slots
# =============================================================================


def test_write_creates_the_state_dir_0700_and_the_file_0600(home: Path) -> None:
    """Machine-global state is owner-only, directory and file alike."""
    machine_config.write_max_slots(6)

    config_path = _config_path(home)
    assert (config_path.parent.stat().st_mode & 0o777) == 0o700
    assert (config_path.stat().st_mode & 0o777) == 0o600


def test_write_round_trips_through_resolution(home: Path) -> None:
    """The write reports the post-state it actually persisted."""
    written = machine_config.write_max_slots(11)

    assert written.value == 11
    assert written.source == machine_config.SOURCE_MACHINE_CONFIG
    assert machine_config.resolve_max_slots().value == 11


def test_write_stamps_the_schema_version(home: Path) -> None:
    """A freshly-written config carries the schema version."""
    machine_config.write_max_slots(4)

    payload = json.loads(_config_path(home).read_text(encoding='utf-8'))
    assert payload['version'] == machine_config.MACHINE_CONFIG_VERSION
    assert payload['build']['queue']['max_slots'] == 4


def test_write_preserves_sibling_keys(home: Path) -> None:
    """Only the cap is replaced — unrelated machine-global state survives.

    Siblings are staged at all three levels the write walks (top level, inside
    ``build``, and beside the cap inside ``queue``), because a rewrite that
    rebuilt any one of those dicts from scratch would drop that level's keys
    while leaving the other two intact.
    """
    _write_raw(
        home,
        json.dumps(
            {
                'version': 1,
                'top_level_sibling': 'keep-me',
                'build': {
                    'build_sibling': 'keep-me-too',
                    'queue': {'max_slots': 3, 'queue_sibling': 'keep-me-three'},
                },
            }
        ),
    )

    machine_config.write_max_slots(8)

    payload = json.loads(_config_path(home).read_text(encoding='utf-8'))
    assert payload['build']['queue']['max_slots'] == 8
    assert payload['top_level_sibling'] == 'keep-me'
    assert payload['build']['build_sibling'] == 'keep-me-too'
    assert payload['build']['queue']['queue_sibling'] == 'keep-me-three'


def test_write_replaces_an_unparseable_file(home: Path) -> None:
    """There is no readable prior state to merge, so the write repairs the file.

    Refusing here would leave a corrupt machine config unfixable through the
    only code path that writes it.
    """
    _write_raw(home, '{not json')

    written = machine_config.write_max_slots(5)

    assert written.source == machine_config.SOURCE_MACHINE_CONFIG
    assert json.loads(_config_path(home).read_text(encoding='utf-8'))['build']['queue']['max_slots'] == 5


def test_written_file_is_complete_json(home: Path) -> None:
    """The atomic write leaves a fully-parseable file, never a torn prefix."""
    machine_config.write_max_slots(12)

    # A torn write (a partial prefix of the payload) would not parse; a complete
    # atomic replace always does.
    payload = json.loads(_config_path(home).read_text(encoding='utf-8'))
    assert payload['build']['queue']['max_slots'] == 12


@pytest.mark.parametrize(
    'bad',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param('5', id='string'),
        pytest.param(2.5, id='float'),
        pytest.param(None, id='null'),
        pytest.param(True, id='bool-true'),
        pytest.param(False, id='bool-false'),
    ],
)
def test_write_rejects_a_value_that_cannot_be_a_cap(home: Path, bad: object) -> None:
    """Validation is on the write path too, so a bad cap never reaches disk."""
    with pytest.raises(ValueError):
        machine_config.write_max_slots(bad)

    assert not _config_path(home).exists()


def test_rejected_write_leaves_an_existing_file_untouched(home: Path) -> None:
    """A refused write is inert — it does not clobber the configured cap."""
    _write_cap(home, 6)
    before = _config_path(home).read_bytes()

    with pytest.raises(ValueError):
        machine_config.write_max_slots(0)

    assert _config_path(home).read_bytes() == before
    assert machine_config.resolve_max_slots().value == 6


# =============================================================================
# read_per_repo_max_slots — the demoted key, read to REPORT it only
# =============================================================================


def _write_marshal(tmp_path: Path, payload: object) -> Path:
    """Stage a repository ``marshal.json`` carrying ``payload`` and return its path."""
    marshal = tmp_path / 'repo' / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    marshal.write_text(json.dumps(payload), encoding='utf-8')
    return marshal


def test_per_repo_reader_returns_the_raw_configured_value(tmp_path: Path) -> None:
    """A present key is returned so a caller can report what the repo actually says."""
    marshal = _write_marshal(tmp_path, {'build': {'queue': {'max_slots': 12}}})

    assert machine_config.read_per_repo_max_slots(marshal) == 12


def test_per_repo_reader_returns_an_absent_key_as_none(tmp_path: Path) -> None:
    """``None`` means "there is no key to report", distinct from any value."""
    marshal = _write_marshal(tmp_path, {'build': {'queue': {'max_retries': 10}}})

    assert machine_config.read_per_repo_max_slots(marshal) is None


def test_per_repo_reader_returns_none_for_a_missing_file(tmp_path: Path) -> None:
    """A repository with no marshal.json has no key to report."""
    assert machine_config.read_per_repo_max_slots(tmp_path / 'nope' / 'marshal.json') is None


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param({}, id='empty-object'),
        pytest.param({'build': {}}, id='no-queue-block'),
        pytest.param({'build': 'not-a-block'}, id='build-not-a-dict'),
        pytest.param({'build': {'queue': 'not-a-block'}}, id='queue-not-a-dict'),
        pytest.param([1, 2, 3], id='not-an-object'),
    ],
)
def test_per_repo_reader_returns_none_when_the_key_is_unreachable(tmp_path: Path, payload: object) -> None:
    """Any shape that puts the key out of reach reads as "no key to report"."""
    marshal = _write_marshal(tmp_path, payload)

    assert machine_config.read_per_repo_max_slots(marshal) is None


def test_per_repo_reader_returns_none_for_an_unparseable_file(tmp_path: Path) -> None:
    """A broken repo config is not a reportable key, and does not raise.

    This reader sits on the build admission path, so it degrades rather than
    failing a build over a repository config it only wanted to describe.
    """
    marshal = tmp_path / 'repo' / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True)
    marshal.write_text('{not json', encoding='utf-8')

    assert machine_config.read_per_repo_max_slots(marshal) is None


@pytest.mark.parametrize(
    'stored',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param('8', id='string'),
        pytest.param(True, id='bool-true'),
    ],
)
def test_per_repo_reader_returns_an_invalid_value_raw_and_unvalidated(tmp_path: Path, stored: object) -> None:
    """A value that could never be a cap is still returned VERBATIM.

    Validation deliberately does not live in this reader: a report saying "your
    marshal.json sets this and it does nothing" has to echo what is actually
    written there. Coercing or dropping an unusable value would make the report
    describe a key the operator cannot find in their own file.
    """
    marshal = _write_marshal(tmp_path, {'build': {'queue': {'max_slots': stored}}})

    assert machine_config.read_per_repo_max_slots(marshal) == stored


# =============================================================================
# per_repo_max_slots_warning — the audible not-in-effect report
# =============================================================================


def test_warning_carries_the_deduplication_code(home: Path) -> None:
    """``code`` is the stable identity consumers deduplicate on, not the text."""
    warning = machine_config.per_repo_max_slots_warning(
        '/repo/.plan/marshal.json', 9, machine_config.resolve_max_slots()
    )

    assert warning['code'] == machine_config.WARNING_PER_REPO_MAX_SLOTS_NOT_IN_EFFECT


def test_warning_names_both_values_the_source_and_both_paths(home: Path) -> None:
    """The message is self-sufficient: what the repo says, and what is in effect.

    The machine-global SOURCE is named as well as the value, because a cap value
    alone cannot distinguish a configured 5 from a fallback 5 — an operator told
    only "the cap is 5" cannot tell whether anyone set it.
    """
    _write_cap(home, 7)
    cap = machine_config.resolve_max_slots()

    message = machine_config.per_repo_max_slots_warning('/repo/.plan/marshal.json', 9, cap)['message']

    assert '/repo/.plan/marshal.json' in message
    assert '9' in message
    assert '7' in message
    assert machine_config.SOURCE_MACHINE_CONFIG in message
    assert str(_config_path(home)) in message


def test_warning_gives_the_one_step_fix_and_the_alternative(home: Path) -> None:
    """Both ways out are named, so the operator never has to go look them up."""
    message = machine_config.per_repo_max_slots_warning(
        '/repo/.plan/marshal.json', 9, machine_config.resolve_max_slots()
    )['message']

    assert machine_config.MIGRATE_COMMAND in message
    assert 'config migrate' in message
    assert 'config set --max-slots' in message


def test_warning_reports_a_degraded_machine_source_rather_than_hiding_it(home: Path) -> None:
    """A broken machine config is named in the warning, not smoothed into a value."""
    _write_raw(home, '{broken')

    message = machine_config.per_repo_max_slots_warning(
        '/repo/.plan/marshal.json', 9, machine_config.resolve_max_slots()
    )['message']

    assert machine_config.SOURCE_UNREADABLE in message


# =============================================================================
# write_max_slots_if_unset — the conditional migration writer
# =============================================================================


def test_conditional_write_writes_when_no_file_exists(home: Path) -> None:
    """An absent file is genuinely unset, so the migration value lands."""
    assert not _config_path(home).exists()

    resolution, wrote = machine_config.write_max_slots_if_unset(7)

    assert wrote is True
    assert resolution.value == 7
    assert resolution.source == machine_config.SOURCE_MACHINE_CONFIG
    assert machine_config.resolve_max_slots().value == 7


def test_conditional_write_writes_when_the_key_is_absent_and_keeps_siblings(home: Path) -> None:
    """A readable file without the key is unset — and its other keys survive."""
    _write_raw(
        home,
        json.dumps(
            {
                'version': 1,
                'top_level_sibling': 'keep-me',
                'build': {'build_sibling': 'keep-me-too', 'queue': {'queue_sibling': 'keep-me-three'}},
            }
        ),
    )

    resolution, wrote = machine_config.write_max_slots_if_unset(4)

    assert wrote is True
    assert resolution.value == 4
    payload = json.loads(_config_path(home).read_text(encoding='utf-8'))
    assert payload['build']['queue']['max_slots'] == 4
    assert payload['top_level_sibling'] == 'keep-me'
    assert payload['build']['build_sibling'] == 'keep-me-too'
    assert payload['build']['queue']['queue_sibling'] == 'keep-me-three'


@pytest.mark.parametrize(
    ('staged', 'expected_source'),
    [
        pytest.param(6, 'machine_config', id='configured'),
        pytest.param(0, 'invalid', id='invalid'),
        pytest.param(True, 'invalid', id='bool'),
    ],
)
def test_conditional_write_refuses_and_leaves_the_file_byte_identical(
    home: Path, staged: object, expected_source: str
) -> None:
    """Anything already on the machine side is NOT unset, so nothing is written.

    ``invalid`` is in this set deliberately: the file exists and holds something,
    so a cap may well be configured there and merely mistyped. Overwriting it
    would silently discard an operator's setting, which is why only
    :data:`SOURCE_DEFAULT` counts as unset.
    """
    _write_cap(home, staged)
    before = _config_path(home).read_bytes()

    resolution, wrote = machine_config.write_max_slots_if_unset(7)

    assert wrote is False
    assert resolution.source == expected_source
    assert _config_path(home).read_bytes() == before


def test_conditional_write_refuses_an_unreadable_file_byte_identically(home: Path) -> None:
    """An unreadable file is the sharpest refusal: a cap may be in there.

    ``_locks_core.rmw_json`` would read this file as ``{}`` and let the write
    through, which is exactly why the conditional writer does not use it.
    """
    _write_raw(home, '{broken')
    before = _config_path(home).read_bytes()

    resolution, wrote = machine_config.write_max_slots_if_unset(7)

    assert wrote is False
    assert resolution.source == machine_config.SOURCE_UNREADABLE
    assert _config_path(home).read_bytes() == before


def test_conditional_write_sees_a_concurrent_value_that_lands_inside_the_guard(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unset test runs INSIDE the guard, so a racing writer is not overwritten.

    This is the ordering assertion, and it is the whole point of the guard. The
    competing value is injected by wrapping :func:`_acquire_guard`, so it lands
    strictly AFTER the guard is taken — meaning only a re-resolve performed
    inside the guarded section can observe it. A function that tested "is it
    unset?" before acquiring would still see the absent file, write over the
    racing value, and report a migration whose value had already been replaced;
    the caller would then delete its repository key on that stale answer.
    """
    real_acquire = machine_config._acquire_guard

    def _acquire_then_race(guard_path: Path) -> int:
        # Annotated local: ``machine_config`` is a dynamically loaded module, so
        # its members are typed ``Any`` and returning one directly would be an
        # implicit Any-return.
        fd: int = real_acquire(guard_path)
        _write_cap(home, 6)  # a concurrent `config set` commits here
        return fd

    monkeypatch.setattr(machine_config, '_acquire_guard', _acquire_then_race)
    assert not _config_path(home).exists()

    resolution, wrote = machine_config.write_max_slots_if_unset(7)

    assert wrote is False
    assert resolution.value == 6
    assert resolution.source == machine_config.SOURCE_MACHINE_CONFIG
    assert machine_config.resolve_max_slots().value == 6


# =============================================================================
# The write guard (serialization + stale reclaim)
# =============================================================================


def _guard_path(home: Path) -> Path:
    """Return the write-guard path beside the machine config."""
    config = _config_path(home)
    return config.with_name(f'{config.name}.lock')


@pytest.mark.parametrize(
    'writer',
    [
        pytest.param('write_max_slots', id='unconditional'),
        pytest.param('write_max_slots_if_unset', id='conditional'),
    ],
)
def test_a_held_guard_blocks_the_other_writer(home: Path, monkeypatch: pytest.MonkeyPatch, writer: str) -> None:
    """A guard held by another writer serializes BOTH writers, not just one.

    Parametrized over both entry points because they share ONE guard: a guard
    that only the conditional writer respected would serialize nothing, since
    the unconditional writer could still land between the conditional writer's
    re-resolve and its write.

    The timeout is shortened so the negative control is fast and deterministic;
    the matched positive control is the sibling test below, where the same call
    succeeds once the guard is gone.
    """
    machine_config.ensure_machine_config_dir()
    guard = _guard_path(home)
    guard.write_text('held', encoding='utf-8')
    monkeypatch.setattr(machine_config, '_GUARD_TIMEOUT_SECONDS', 0.05)

    with pytest.raises(TimeoutError):
        getattr(machine_config, writer)(7)

    assert not _config_path(home).exists()


@pytest.mark.parametrize(
    'writer',
    [
        pytest.param('write_max_slots', id='unconditional'),
        pytest.param('write_max_slots_if_unset', id='conditional'),
    ],
)
def test_a_free_guard_lets_the_writer_through(home: Path, monkeypatch: pytest.MonkeyPatch, writer: str) -> None:
    """The matched positive control for the blocked case above.

    Same shortened timeout, same call, no guard held — so the ``TimeoutError``
    in the sibling test is attributable to the held guard and not to the
    tightened budget.
    """
    monkeypatch.setattr(machine_config, '_GUARD_TIMEOUT_SECONDS', 0.05)

    getattr(machine_config, writer)(7)

    assert machine_config.resolve_max_slots().value == 7


def test_a_stale_guard_is_reclaimed(home: Path) -> None:
    """A crashed writer's abandoned guard must not wedge the file forever."""
    machine_config.ensure_machine_config_dir()
    guard = _guard_path(home)
    guard.write_text('abandoned', encoding='utf-8')
    stale = time.time() - (machine_config._GUARD_STALE_SECONDS + 30)
    os.utime(guard, (stale, stale))

    written = machine_config.write_max_slots(7)

    assert written.value == 7
    assert machine_config.resolve_max_slots().value == 7


def test_a_fresh_guard_is_not_reclaimed(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The matched negative control for the stale reclaim above.

    Without this pairing, the reclaim test would pass just as well against an
    implementation that reclaimed EVERY guard, stale or not — which would defeat
    the serialization entirely.
    """
    machine_config.ensure_machine_config_dir()
    guard = _guard_path(home)
    guard.write_text('held', encoding='utf-8')
    monkeypatch.setattr(machine_config, '_GUARD_TIMEOUT_SECONDS', 0.05)

    with pytest.raises(TimeoutError):
        machine_config.write_max_slots(7)


def test_the_guard_is_removed_after_a_successful_write(home: Path) -> None:
    """The guard is released in a ``finally``, so it never leaks to the next writer."""
    machine_config.write_max_slots(7)

    assert not _guard_path(home).exists()


def test_the_guard_is_removed_after_a_refused_conditional_write(home: Path) -> None:
    """A refusal releases the guard too — the refusing path also runs the ``finally``."""
    _write_cap(home, 6)

    _resolution, wrote = machine_config.write_max_slots_if_unset(7)

    assert wrote is False
    assert not _guard_path(home).exists()


@pytest.mark.parametrize(
    'bad',
    [
        pytest.param(0, id='zero'),
        pytest.param(-1, id='negative'),
        pytest.param('5', id='string'),
        pytest.param(None, id='null'),
        pytest.param(True, id='bool-true'),
    ],
)
def test_conditional_write_rejects_a_value_that_cannot_be_a_cap(home: Path, bad: object) -> None:
    """The conditional writer validates too — a bad cap never reaches disk."""
    with pytest.raises(ValueError):
        machine_config.write_max_slots_if_unset(bad)

    assert not _config_path(home).exists()


# =============================================================================
# report_safe — the emission-boundary sanitiser
# =============================================================================
#
# The readers above return a foreign config value RAW on purpose, so the bytes
# that cannot survive a single-line TOON field are removed at the point of
# emission instead. Until these tests the function had no direct coverage at all:
# every caller-side test passed integers, which no sanitiser can affect, so
# deleting `report_safe` outright left the suite green. These are the unit-level
# half of the pin; the end-to-end half lives with the two call sites
# (`test_manage_build_server.py`, `test_build_queue.py`).


def test_report_safe_strips_every_c0_control_character_and_del() -> None:
    """Derived over the WHOLE forbidden range, not a hand-picked sample.

    The set that must go is exactly C0 (U+0000-U+001F) plus DEL (U+007F).
    Enumerating the range here rather than spot-checking a newline is what makes
    this a statement ABOUT the range: a pattern that happened to miss the
    vertical tab or the form feed would sail through a newline-only test, and a
    single surviving control character is all an injected line needs.
    """
    forbidden = [chr(code) for code in range(0x20)] + [chr(0x7F)]

    for char in forbidden:
        assert machine_config.report_safe(f'a{char}b') == 'ab', f'{char!r} survived the sanitiser'


def test_report_safe_leaves_a_clean_string_byte_identical() -> None:
    """The matched positive control: ONLY the forbidden bytes go.

    Printable text survives untouched — including the characters that merely look
    structural to TOON, a colon and a comma, which the canonical serializer quotes
    rather than needing stripped. Without this control the range test above would
    pass equally against a function that returned ``''`` for every string, which
    would silently destroy the report the field exists to produce.
    """
    clean = 'max_slots: 8, set by hand (~/repo)'

    assert machine_config.report_safe(clean) == clean


def test_report_safe_strips_only_the_control_characters_from_a_mixed_value() -> None:
    """A realistic planted value keeps its text and loses its line breaks.

    This is the shape a real injected value has: usable-looking text carrying a
    newline and a TOON-shaped second line. The surrounding text must still be
    reported so the operator can find the key in their own file.
    """
    assert machine_config.report_safe('8\nstatus: success') == '8status: success'


@pytest.mark.parametrize(
    'value',
    [
        pytest.param(8, id='int'),
        pytest.param(8.5, id='float'),
        pytest.param(True, id='bool'),
        pytest.param(None, id='none'),
        pytest.param([1, 2], id='list'),
        pytest.param({'a': 1}, id='dict'),
    ],
)
def test_report_safe_returns_a_non_string_unchanged(value: object) -> None:
    """Only a ``str`` can carry a control character; every other type passes through.

    Asserted on IDENTITY rather than equality, because the contract is
    pass-through: coercing an ``int`` to its string form would change the shape of
    every reported field, and an equality assertion would not notice.
    """
    assert machine_config.report_safe(value) is value
