#!/usr/bin/env python3
"""Tests for the ``diff-modules`` reader verb in ``_cmd_client.py``.

Pins the four-bucket classification contract (added/removed/changed/unchanged)
of ``cmd_diff_modules`` plus its ``snapshot_not_found`` error contract and
the argparse wiring on ``architecture.py``. The comparison surface is
intentionally narrow — only ``derived.json`` shas matter; differences in
``enriched.json`` never produce a ``changed`` classification.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    _REPO_ROOT
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_client = _load_module('_cmd_client', '_cmd_client.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
get_data_dir = _architecture_core.get_data_dir
cmd_diff_modules = _cmd_client.cmd_diff_modules


# =============================================================================
# Fixture helpers
# =============================================================================


def _seed_project(project_dir: str, modules: dict[str, dict]) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files."""
    save_project_meta(
        {
            'name': 'diff-modules-test',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        project_dir,
    )
    for name, derived in modules.items():
        save_module_derived(name, derived, project_dir)


def _snapshot_data_dir(project_dir: str, snapshot_root: str) -> Path:
    """Copy the live ``project-architecture/`` tree into ``snapshot_root``.

    Returns the snapshot directory containing ``_project.json`` directly.
    """
    src = get_data_dir(project_dir)
    dst = Path(snapshot_root) / 'project-architecture'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def _make_module(name: str) -> dict:
    return {
        'name': name,
        'build_systems': ['python'],
        'paths': {'module': name},
        'commands': {},
    }


# =============================================================================
# Bucket classification
# =============================================================================


def test_unchanged_tree_classifies_every_module_as_unchanged():
    """When snapshot equals current, all modules land in ``unchanged``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a'), 'mod-b': _make_module('mod-b')})

        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == []
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a', 'mod-b']


def test_byte_modified_derived_classifies_as_changed():
    """A single module's ``derived.json`` byte-modified between snapshot and current → ``changed``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a'), 'mod-b': _make_module('mod-b')})
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Mutate mod-b's derived.json in the live tree (simulating a re-discover).
        save_module_derived('mod-b', {**_make_module('mod-b'), 'note': 'mutated'}, str(project))

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == []
        assert result['changed'] == ['mod-b']
        assert result['unchanged'] == ['mod-a']


def test_added_module_classifies_as_added():
    """A module present in current but not in snapshot → ``added``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Add mod-new to the live tree, re-write _project.json index.
        _seed_project(
            str(project),
            {'mod-a': _make_module('mod-a'), 'mod-new': _make_module('mod-new')},
        )

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == ['mod-new']
        assert result['removed'] == []
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


def test_removed_module_classifies_as_removed():
    """A module present in snapshot but not in current → ``removed``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(
            str(project),
            {'mod-a': _make_module('mod-a'), 'mod-gone': _make_module('mod-gone')},
        )
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Remove mod-gone from the live tree by re-writing only mod-a.
        shutil.rmtree(get_data_dir(str(project)))
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == ['mod-gone']
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


# =============================================================================
# Error contract
# =============================================================================


def test_missing_snapshot_directory_returns_snapshot_not_found():
    """A non-existent ``--pre`` path returns ``error: snapshot_not_found``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        missing = Path(tmp) / 'no-such-snapshot'

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(missing)))

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(missing)


def test_snapshot_dir_present_but_project_meta_missing_returns_error():
    """An existing directory without ``_project.json`` is also ``snapshot_not_found``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        # Create the snapshot directory but do not populate it with _project.json.
        empty_snapshot = Path(tmp) / 'empty-snapshot'
        empty_snapshot.mkdir()

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(empty_snapshot)))

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(empty_snapshot)


# =============================================================================
# Comparison surface — derived-only
# =============================================================================


def test_enriched_only_diff_does_not_produce_changed():
    """A diff confined to ``enriched.json`` does NOT classify the module as changed."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})
        # Seed an initial enriched.json on both sides.
        save_module_enriched('mod-a', {'responsibility': 'before'}, str(project))
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Mutate ONLY enriched.json on the current side.
        save_module_enriched('mod-a', {'responsibility': 'after'}, str(project))

        result = cmd_diff_modules(Namespace(project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


# =============================================================================
# Argparse wiring
# =============================================================================


def test_argparse_registers_diff_modules_subcommand():
    """``architecture diff-modules --pre <path>`` is a registered subcommand.

    Invokes ``architecture.py --help`` and ``architecture.py diff-modules
    --help`` as a subprocess so the assertion exercises the real argparse
    wiring rather than internal dispatch tables.
    """
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    cmd_help = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert cmd_help.returncode == 0, f'--help failed: {cmd_help.stderr}'
    assert 'diff-modules' in cmd_help.stdout

    sub_help = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), 'diff-modules', '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert sub_help.returncode == 0, f'diff-modules --help failed: {sub_help.stderr}'
    assert '--pre' in sub_help.stdout
