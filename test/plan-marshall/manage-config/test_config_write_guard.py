#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``_config_core`` write path.

Pins the truthful-signals fixes on the config write path:

- ``normalize_keys()`` names any top-level key it could not order and downgrades
  its status to ``warning`` (D2 / D10a), and stays byte-stable + clean on an
  already-canonical file (D10b — the guard against this becoming a reformatter).
- ``save_config()`` refuses to silently clobber a concurrent write, so two
  concurrent writers cannot silently drop one side's change (D4 / D10e).
- ``normalize_keys()`` reports the product's OWN platform-runtime seed as
  recognized, exercised through the real two-step seeding order — ``manage-config
  init`` and then ``platform_runtime project initial-setup``.
"""

import json
from argparse import Namespace

import _config_core
import pytest
from claude_runtime import ClaudeRuntime
from toon_parser import parse_toon

from conftest import load_script_module

# Loaded under a test-local name rather than imported plainly: several sibling
# modules load this same script, and a plain `import _cmd_init` would contend
# with them over the `sys.modules` entry. The module resolves `save_config` /
# `is_initialized` from the canonical `_config_core` above either way, so the
# fixtures' monkeypatching of that module still governs where it writes.
_cmd_init_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_init.py', module_name='_cmd_init_for_write_guard_test'
)


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


# ============================================================================
# normalize_keys over the product's own platform-runtime seed
# ============================================================================
#
# `platform_runtime project initial-setup` writes `runtime` and `project_dir`
# with a plain `json.dumps` — one of the documented BYPASS writers that does not
# route through `order_config_keys`. Both keys therefore arrive appended at
# end-of-object, and until they were listed in CANONICAL_TOP_LEVEL_KEY_ORDER,
# `normalize-keys` reported plan-marshall's own seed as unrecognized: a warning
# naming keys the operator could not act on, because the product itself wrote
# them.


@pytest.fixture
def seeded_project(tmp_path, monkeypatch):
    """A project dir where BOTH marshal.json writers resolve the same file.

    ``cmd_init`` writes through ``_config_core.MARSHAL_PATH``, while the
    platform-runtime seed derives ``{project_dir}/.plan/marshal.json`` from its
    own argument. The two only meet when the module constants point at that
    nested path, so this fixture pins them there rather than at the bare tmp
    root the ``marshal`` fixture above uses. ``TRACKED_CONFIG_DIR`` follows for
    ``require_initialized()``, and the fingerprint cache is cleared so a prior
    test's load never influences this one's save.

    Returns:
        The project directory — the argument ``project_initial_setup`` takes.
    """
    project_dir = tmp_path / 'proj'
    plan_dir = project_dir / '.plan'
    plan_dir.mkdir(parents=True)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', plan_dir / 'marshal.json')
    monkeypatch.setattr(_config_core, 'TRACKED_CONFIG_DIR', plan_dir)
    _config_core._CONFIG_FINGERPRINTS.clear()
    return project_dir


def _canonical_projection(keys: list) -> list:
    """Project ``keys`` onto CANONICAL_TOP_LEVEL_KEY_ORDER, preserving that order.

    The expected result of ordering a document whose keys are ALL recognized: the
    canonical order filtered to the keys actually present. A document carrying an
    unrecognized key cannot equal its own projection, because
    ``order_config_keys`` appends that key after the canonical run.
    """
    present = set(keys)
    return [key for key in _config_core.CANONICAL_TOP_LEVEL_KEY_ORDER if key in present]


def test_normalize_keys_is_clean_after_init_then_platform_runtime_seed(seeded_project):
    """The real two-step seeding order leaves nothing for the operator to act on.

    The order is ``manage-config init`` FIRST and ``platform_runtime project
    initial-setup`` SECOND — the sequence a project actually performs, and the
    only one that reaches this state: ``init`` refuses an existing marshal.json
    without ``--force``, so running the seed first would leave ``init`` unable to
    write the defaults at all.

    Three things are asserted together because each rules out a different way of
    passing vacuously: the seed's keys really did arrive out of canonical order
    (otherwise there is no reordering to verify), the ``init`` blocks survived the
    seed's read-modify-write (otherwise ``normalize-keys`` would be reporting on a
    two-key document), and the settled order is exactly the canonical projection
    with nothing appended as unrecognized.
    """
    init_result = _cmd_init_mod.cmd_init(Namespace(force=False))
    assert init_result['status'] == 'success'

    after_init = list(json.loads(_config_core.MARSHAL_PATH.read_text(encoding='utf-8')))
    assert 'runtime' not in after_init
    assert 'project_dir' not in after_init

    setup = parse_toon(ClaudeRuntime().project_initial_setup(str(seeded_project), 'claude'))
    assert setup['status'] == 'success'

    # The bypass writer appended both keys at end-of-object, in the order it set
    # them — so there IS a canonical reordering for normalize_keys to perform.
    after_seed = list(json.loads(_config_core.MARSHAL_PATH.read_text(encoding='utf-8')))
    assert after_seed[-2:] == ['runtime', 'project_dir']
    assert after_seed != _canonical_projection(after_seed)

    result = _config_core.normalize_keys()

    assert result['status'] == 'success'
    assert result['unrecognized_keys'] == []

    settled = list(json.loads(_config_core.MARSHAL_PATH.read_text(encoding='utf-8')))
    # Not a two-key document: the seed merged into the init config rather than
    # replacing it, so the clean signal is over the whole seeded schema.
    assert 'plan' in settled
    assert settled == _canonical_projection(settled)
    assert settled.index('project_dir') < settled.index('runtime')


def test_normalize_keys_still_warns_on_a_stray_key_beside_the_seed(seeded_project):
    """Matched negative control: recognizing the seed did not disarm the warning.

    Adding ``project_dir`` / ``runtime`` to the canonical order could have been
    done by making the reporter permissive instead — every top-level key accepted,
    no warning ever. This stages the same seeded document plus one genuinely
    foreign block and requires the warning to still name it, and only it.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    ClaudeRuntime().project_initial_setup(str(seeded_project), 'claude')

    config = json.loads(_config_core.MARSHAL_PATH.read_text(encoding='utf-8'))
    config['zzz_consumer_block'] = {'x': 1}
    _config_core.MARSHAL_PATH.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')

    result = _config_core.normalize_keys()

    assert result['status'] == 'warning'
    assert result['unrecognized_keys'] == ['zzz_consumer_block']
