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
"""

from __future__ import annotations

import json
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
