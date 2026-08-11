#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``_config_core`` write path.

Pins the truthful-signals fixes on the config write path:

- ``normalize_keys()`` names any top-level key it could not order and downgrades
  its status to ``warning`` (D2 / D10a), and stays byte-stable + clean on an
  already-canonical file (D10b — the guard against this becoming a reformatter).
- ``save_config()`` refuses to silently clobber a concurrent write, so two
  concurrent writers cannot silently drop one side's change (D4 / D10e).
"""

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _config_core  # noqa: E402


@pytest.fixture
def marshal(tmp_path, monkeypatch):
    """Redirect ``MARSHAL_PATH`` to a per-test tmp file and reset the write-guard state.

    Also points ``TRACKED_CONFIG_DIR`` at the tmp dir so ``require_initialized()``
    (called by ``normalize_keys``) is satisfied, and clears the module-level
    optimistic-concurrency fingerprint cache so one test's load never influences
    another's save.
    """
    path = tmp_path / 'marshal.json'
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', path)
    monkeypatch.setattr(_config_core, 'TRACKED_CONFIG_DIR', tmp_path)
    _config_core._CONFIG_FINGERPRINTS.clear()
    return path


# ============================================================================
# unrecognized_top_level_keys — the reporting sibling
# ============================================================================


def test_unrecognized_top_level_keys_lists_only_non_canonical():
    """Only top-level keys absent from CANONICAL_TOP_LEVEL_KEY_ORDER are returned,
    in the config's own insertion order (the order they are appended)."""
    config = {'plan': {}, 'weird': {}, 'system': {}, 'another': {}}

    assert _config_core.unrecognized_top_level_keys(config) == ['weird', 'another']


def test_unrecognized_top_level_keys_empty_when_all_canonical():
    config = {'plan': {}, 'system': {}, 'build': {}}

    assert _config_core.unrecognized_top_level_keys(config) == []


# ============================================================================
# normalize_keys — honest signal (D2 / D10a) and byte-stability (D10b)
# ============================================================================


def test_normalize_keys_names_unrecognized_top_level_key(marshal):
    """A config with a top-level key absent from CANONICAL_TOP_LEVEL_KEY_ORDER
    produces a non-clean signal NAMING that key — never a bare ``normalized``."""
    marshal.write_text(
        json.dumps({'plan': {}, 'zzz_consumer_block': {'x': 1}}, indent=2) + '\n',
        encoding='utf-8',
    )

    result = _config_core.normalize_keys()

    assert result['action'] == 'normalized'
    assert result['status'] == 'warning'
    assert result['unrecognized_keys'] == ['zzz_consumer_block']


def test_normalize_keys_clean_success_when_all_keys_canonical(marshal):
    """A config carrying only canonical top-level keys reports ``success`` with an
    empty ``unrecognized_keys`` — the clean signal is distinguishable from the warning."""
    marshal.write_text(json.dumps({'plan': {'a': 1}, 'system': {'b': 2}}, indent=2) + '\n', encoding='utf-8')

    result = _config_core.normalize_keys()

    assert result['status'] == 'success'
    assert result['unrecognized_keys'] == []
    assert result['action'] == 'normalized'


def test_normalize_keys_is_byte_stable_on_already_canonical_file(marshal):
    """An already-canonical file comes back byte-identical on a second pass — this
    fix is a canonicalizer, not a reformatter (D10b)."""
    # First pass canonicalizes (plan sorts before system) and settles the bytes.
    marshal.write_text(json.dumps({'system': {'b': 2}, 'plan': {'a': 1}}, indent=2) + '\n', encoding='utf-8')
    first = _config_core.normalize_keys()
    assert first['status'] == 'success'
    canonical_bytes = marshal.read_bytes()

    second = _config_core.normalize_keys()

    assert second['status'] == 'success'
    assert second['unrecognized_keys'] == []
    assert marshal.read_bytes() == canonical_bytes


# ============================================================================
# save_config — lost-update guard (D4 / D10e)
# ============================================================================


def test_save_config_refuses_a_concurrent_overwrite(marshal):
    """Two concurrent writers cannot silently drop one side's change: a save whose
    file changed on disk since it was loaded is refused, and the other writer's
    change survives."""
    marshal.write_text(json.dumps({'plan': {'v': 1}}, indent=2) + '\n', encoding='utf-8')

    config = _config_core.load_config()  # records the load-time fingerprint
    config['plan']['v'] = 2  # this writer's in-flight change

    # A concurrent writer commits a different change between our load and save.
    marshal.write_text(json.dumps({'plan': {'v': 99}}, indent=2) + '\n', encoding='utf-8')

    with pytest.raises(_config_core.ConcurrentConfigModificationError):
        _config_core.save_config(config)

    # The concurrent writer's change is still on disk — NOT silently clobbered.
    assert json.loads(marshal.read_text(encoding='utf-8'))['plan']['v'] == 99


def test_save_config_writes_when_no_concurrent_modification(marshal):
    """The normal load -> mutate -> save flow (no concurrent writer) still persists."""
    marshal.write_text(json.dumps({'plan': {'v': 1}}, indent=2) + '\n', encoding='utf-8')

    config = _config_core.load_config()
    config['plan']['v'] = 2
    _config_core.save_config(config)

    assert json.loads(marshal.read_text(encoding='utf-8'))['plan']['v'] == 2


def test_save_config_without_prior_load_is_unguarded(marshal):
    """A save with no recorded load for this path (e.g. ``init`` creating the file)
    proceeds — the guard protects the load->modify->save window, not a fresh write."""
    _config_core.save_config({'plan': {'v': 1}})

    assert marshal.exists()
    assert json.loads(marshal.read_text(encoding='utf-8'))['plan']['v'] == 1
