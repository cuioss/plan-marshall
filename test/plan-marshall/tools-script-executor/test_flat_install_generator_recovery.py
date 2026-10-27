# SPDX-License-Identifier: FSL-1.1-ALv2
"""The generator's ``recover`` verb in a marker-less FLAT install.

Two facts, and they are different facts:

* **A regression guard (passes at the base).** A flat-layout fixture — skill
  directories named ``plan-marshall-{skill}``, no bundle directory, no
  ``.claude-plugin/plugin.json`` — starts the generator, answers ``recover
  --help`` at exit 0, and recovers a fixture checkout's executor through the
  generator the flat tree carries (``recover`` selects the newest installed
  generator through the shared resolver, then re-runs it as a subprocess).
* **The defect (fails at the base).** The same fixture with the
  ``script-shared`` skill directory removed used to die on a bare
  ``ModuleNotFoundError`` naming whichever module the first import touched. The
  shared bootstrap reports the missing LIBRARY by name and by the paths it
  probed.

``PYTHONPATH`` is pinned EMPTY in both cases, and ``HOME`` is redirected to the
fixture, so nothing but the deployed tree can answer the library resolution.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from _flat_install_fixtures import build_flat_install, run_script_in_flat

GENERATOR_SCRIPT = ('plan-marshall', 'tools-script-executor', 'generate_executor.py')


def _flat_generator(root: Path) -> Path:
    bundle, skill, script = GENERATOR_SCRIPT
    return root / 'skills' / f'{bundle}-{skill}' / 'scripts' / script


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build a flat deploy at ``HOME/.config/opencode`` and return ``(home, root)``.

    The home-anchored location is the one a real OpenCode install occupies, so the
    shared deploy-root resolver finds it with no override: the generator's
    ``recover`` probes ``$HOME/.config/opencode/skills`` through
    ``deployed-layout.json`` exactly as it does on a machine.
    """
    home = tmp_path / 'home'
    root = build_flat_install(home / '.config' / 'opencode')
    return home, root


def _fixture_env(home: Path) -> dict[str, str]:
    """Pin the fixture's ``HOME`` and clear the config-dir overrides.

    Empty values are skipped by ``deployed_layout._expand_deploy_root``, so the
    home-anchored root is the only candidate — an ambient
    ``OPENCODE_CONFIG_DIR``/``XDG_CONFIG_HOME`` cannot decide this test.
    """
    return {'HOME': str(home), 'PYTHONPATH': '', 'XDG_CONFIG_HOME': '', 'OPENCODE_CONFIG_DIR': ''}


@pytest.fixture
def flat_home(tmp_path: Path) -> tuple[Path, Path, Path]:
    home, root = _fixture(tmp_path)
    checkout = tmp_path / 'checkout'
    (checkout / '.plan').mkdir(parents=True)
    return home, root, checkout


def test_recover_help_runs_in_a_flat_install(flat_home: tuple[Path, Path, Path], tmp_path: Path) -> None:
    """``recover --help`` is exit 0 from the deployed generator (regression guard)."""
    home, root, checkout = flat_home

    completed = run_script_in_flat(
        root,
        checkout,
        _flat_generator(root),
        'recover',
        '--help',
        env_overrides=_fixture_env(home),
    )

    assert completed.returncode == 0, completed.stderr
    assert 'recover' in completed.stdout.lower()


def test_recover_regenerates_a_fixture_checkout_from_a_flat_install(
    flat_home: tuple[Path, Path, Path],
) -> None:
    """A full ``recover`` run regenerates the checkout's executor for the target.

    The generator selected by ``recover`` is the one the flat tree carries, run as
    its own subprocess with ``PYTHONPATH`` removed — so this exercises the
    deployed bootstrap end to end, not the test process's imports.
    """
    home, root, checkout = flat_home
    executor = checkout / '.plan' / 'execute-script.py'

    completed = run_script_in_flat(
        root,
        checkout,
        _flat_generator(root),
        'recover',
        '--project-dir',
        str(checkout),
        '--target',
        'opencode',
        env_overrides=_fixture_env(home),
    )

    assert completed.returncode == 0, completed.stderr
    assert 'status: success' in completed.stdout, completed.stdout
    assert 'action: regenerated' in completed.stdout, completed.stdout
    assert 'target: opencode' in completed.stdout, completed.stdout
    assert executor.is_file(), 'recover reported success without writing the executor'
    assert 'GENERATED_FOR' in executor.read_text(encoding='utf-8')


def test_a_missing_library_names_the_library_and_its_path(tmp_path: Path) -> None:
    """Removing ``script-shared`` names the library and the probed paths.

    The failure this replaces is a bare ``ModuleNotFoundError`` from the first
    shared import — it names a module, not the install defect, and it never
    mentions the directory the reader has to restore.
    """
    home, root = _fixture(tmp_path)
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    shutil.rmtree(root / 'skills' / 'plan-marshall-script-shared')

    completed = run_script_in_flat(
        root,
        checkout,
        _flat_generator(root),
        'recover',
        '--help',
        env_overrides=_fixture_env(home),
    )

    assert completed.returncode != 0, completed.stdout
    assert 'plan-marshall bootstrap' in completed.stderr, completed.stderr
    assert 'script-shared' in completed.stderr, completed.stderr
    assert str(root / 'skills' / 'script-shared' / 'scripts') in completed.stderr, completed.stderr
    assert 'ModuleNotFoundError' not in completed.stderr, completed.stderr
