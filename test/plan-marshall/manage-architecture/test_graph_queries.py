#!/usr/bin/env python3
"""Tests for graph-traversal verbs: path, neighbors, impact.

Uses the per-module on-disk layout: ``_project.json`` index plus per-module
``derived.json`` files written via ``save_project_meta`` and
``save_module_derived``.
"""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_client = _load_module('_cmd_client', '_cmd_client.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived

get_module_path = _cmd_client.get_module_path
get_module_neighbors = _cmd_client.get_module_neighbors
get_module_impact = _cmd_client.get_module_impact
cmd_path = _cmd_client.cmd_path
cmd_neighbors = _cmd_client.cmd_neighbors
cmd_impact = _cmd_client.cmd_impact
NEIGHBORS_DEPTH_CAP = _cmd_client.NEIGHBORS_DEPTH_CAP

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')


# =============================================================================
# Fixture helpers
# =============================================================================


def _seed_project(tmpdir: str, project_name: str, modules: dict[str, dict]) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files."""
    save_project_meta(
        {
            'name': project_name,
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


def _create_chain_graph(tmpdir: str) -> None:
    """Linear chain: alpha -> beta -> gamma."""
    _seed_project(
        tmpdir,
        'chain',
        {
            'alpha': {
                'name': 'alpha',
                'paths': {'module': 'alpha'},
                'internal_dependencies': ['beta'],
                'commands': {},
            },
            'beta': {
                'name': 'beta',
                'paths': {'module': 'beta'},
                'internal_dependencies': ['gamma'],
                'commands': {},
            },
            'gamma': {
                'name': 'gamma',
                'paths': {'module': 'gamma'},
                'internal_dependencies': [],
                'commands': {},
            },
        },
    )


def _create_disconnected_graph(tmpdir: str) -> None:
    """Two disconnected nodes: lefty and righty with no edges."""
    _seed_project(
        tmpdir,
        'disjoint',
        {
            'lefty': {
                'name': 'lefty',
                'paths': {'module': 'lefty'},
                'internal_dependencies': [],
                'commands': {},
            },
            'righty': {
                'name': 'righty',
                'paths': {'module': 'righty'},
                'internal_dependencies': [],
                'commands': {},
            },
        },
    )


def _create_cyclic_graph(tmpdir: str) -> None:
    """A cycle: alpha -> beta -> gamma -> alpha."""
    _seed_project(
        tmpdir,
        'cycle',
        {
            'alpha': {
                'name': 'alpha',
                'paths': {'module': 'alpha'},
                'internal_dependencies': ['beta'],
                'commands': {},
            },
            'beta': {
                'name': 'beta',
                'paths': {'module': 'beta'},
                'internal_dependencies': ['gamma'],
                'commands': {},
            },
            'gamma': {
                'name': 'gamma',
                'paths': {'module': 'gamma'},
                'internal_dependencies': ['alpha'],
                'commands': {},
            },
        },
    )


def _create_fan_out_graph(tmpdir: str) -> None:
    """Fan-out: hub -> a, b, c; a -> a-leaf; b -> b-leaf."""
    _seed_project(
        tmpdir,
        'fan',
        {
            'hub': {
                'name': 'hub',
                'paths': {'module': 'hub'},
                'internal_dependencies': ['a', 'b', 'c'],
                'commands': {},
            },
            'a': {
                'name': 'a',
                'paths': {'module': 'a'},
                'internal_dependencies': ['a-leaf'],
                'commands': {},
            },
            'b': {
                'name': 'b',
                'paths': {'module': 'b'},
                'internal_dependencies': ['b-leaf'],
                'commands': {},
            },
            'c': {
                'name': 'c',
                'paths': {'module': 'c'},
                'internal_dependencies': [],
                'commands': {},
            },
            'a-leaf': {
                'name': 'a-leaf',
                'paths': {'module': 'a-leaf'},
                'internal_dependencies': [],
                'commands': {},
            },
            'b-leaf': {
                'name': 'b-leaf',
                'paths': {'module': 'b-leaf'},
                'internal_dependencies': [],
                'commands': {},
            },
        },
    )


def _create_diamond_graph(tmpdir: str) -> None:
    """Diamond: app -> service -> {core, api}; core -> api."""
    _seed_project(
        tmpdir,
        'diamond',
        {
            'api': {
                'name': 'api',
                'paths': {'module': 'api'},
                'internal_dependencies': [],
                'commands': {},
            },
            'core': {
                'name': 'core',
                'paths': {'module': 'core'},
                'internal_dependencies': ['api'],
                'commands': {},
            },
            'service': {
                'name': 'service',
                'paths': {'module': 'service'},
                'internal_dependencies': ['core', 'api'],
                'commands': {},
            },
            'app': {
                'name': 'app',
                'paths': {'module': 'app'},
                'internal_dependencies': ['service'],
                'commands': {},
            },
        },
    )


# =============================================================================
# Tests for get_module_path
# =============================================================================


def test_path_happy_path_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        assert get_module_path('alpha', 'gamma', tmpdir) == ['alpha', 'beta', 'gamma']


def test_path_no_edge_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_disconnected_graph(tmpdir)
        assert get_module_path('lefty', 'righty', tmpdir) is None


def test_path_with_cycle_terminates():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_cyclic_graph(tmpdir)
        assert get_module_path('alpha', 'gamma', tmpdir) == ['alpha', 'beta', 'gamma']
        assert get_module_path('beta', 'alpha', tmpdir) == ['beta', 'gamma', 'alpha']


def test_path_self_loop_returns_singleton():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        assert get_module_path('alpha', 'alpha', tmpdir) == ['alpha']


def test_path_picks_shortest_in_diamond():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        assert get_module_path('service', 'api', tmpdir) == ['service', 'api']


def test_path_unknown_module_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        with pytest.raises(_architecture_core.ModuleNotFoundInProjectError):
            get_module_path('alpha', 'zzz', tmpdir)


# =============================================================================
# Tests for get_module_neighbors
# =============================================================================


def test_neighbors_depth_zero_is_singleton():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        assert get_module_neighbors('hub', 0, tmpdir) == ['hub']


def test_neighbors_depth_one_fan_out():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        assert get_module_neighbors('hub', 1, tmpdir) == ['a', 'b', 'c', 'hub']


def test_neighbors_depth_three_full_closure():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        assert get_module_neighbors('hub', 3, tmpdir) == ['a', 'a-leaf', 'b', 'b-leaf', 'c', 'hub']


def test_neighbors_depth_capped():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        result = get_module_neighbors('hub', 999, tmpdir)
        assert result == ['a', 'a-leaf', 'b', 'b-leaf', 'c', 'hub']


def test_neighbors_negative_depth_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        with pytest.raises(ValueError):
            get_module_neighbors('hub', -1, tmpdir)


def test_neighbors_unknown_module_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        with pytest.raises(_architecture_core.ModuleNotFoundInProjectError):
            get_module_neighbors('zzz', 1, tmpdir)


# =============================================================================
# Tests for get_module_impact
# =============================================================================


def test_impact_reverse_closure_diamond():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        assert get_module_impact('api', tmpdir) == ['app', 'core', 'service']


def test_impact_leaf_module_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        assert get_module_impact('app', tmpdir) == []


def test_impact_excludes_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_cyclic_graph(tmpdir)
        assert get_module_impact('alpha', tmpdir) == ['beta', 'gamma']


def test_impact_unknown_module_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        with pytest.raises(_architecture_core.ModuleNotFoundInProjectError):
            get_module_impact('zzz', tmpdir)


# =============================================================================
# CLI handler tests
# =============================================================================


def test_cmd_path_returns_toon_shape():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, source='alpha', target='gamma')
        result = cmd_path(args)
        assert result == {
            'status': 'success',
            'source': 'alpha',
            'target': 'gamma',
            'path': ['alpha', 'beta', 'gamma'],
        }


def test_cmd_path_unreachable_returns_null_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_disconnected_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, source='lefty', target='righty')
        result = cmd_path(args)
        assert result == {'status': 'success', 'source': 'lefty', 'target': 'righty', 'path': None}


def test_cmd_path_unknown_module_returns_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, source='alpha', target='zzz')
        result = cmd_path(args)
        assert result['status'] == 'error'
        assert result['module'] == 'zzz'
        assert set(result['available']) == {'alpha', 'beta', 'gamma'}


def test_cmd_neighbors_returns_shape():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, module='hub', depth=1)
        result = cmd_neighbors(args)
        assert result == {
            'status': 'success',
            'module': 'hub',
            'depth': 1,
            'neighbors': ['a', 'b', 'c', 'hub'],
        }


def test_cmd_neighbors_clamps_depth_in_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, module='hub', depth=42)
        result = cmd_neighbors(args)
        assert result['depth'] == NEIGHBORS_DEPTH_CAP


def test_cmd_impact_returns_shape():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        args = Namespace(project_dir=tmpdir, module='api')
        result = cmd_impact(args)
        assert result == {
            'status': 'success',
            'module': 'api',
            'impact': ['app', 'core', 'service'],
        }


# =============================================================================
# Argparse-wiring tests via subprocess (uses conftest.run_script for PYTHONPATH)
# =============================================================================


def test_argparse_wiring_path_subcommand():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'path', 'alpha', 'gamma')
        assert result.returncode == 0, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['source'] == 'alpha'
        assert data['target'] == 'gamma'
        assert data['path'] == ['alpha', 'beta', 'gamma']


def test_argparse_wiring_neighbors_subcommand_with_depth():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        result = run_script(
            SCRIPT_PATH, '--project-dir', tmpdir, 'neighbors', '--module', 'hub', '--depth', '1'
        )
        assert result.returncode == 0, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['module'] == 'hub'
        assert data['depth'] == 1
        assert data['neighbors'] == ['a', 'b', 'c', 'hub']


def test_argparse_wiring_impact_subcommand():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'impact', '--module', 'api')
        assert result.returncode == 0, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['module'] == 'api'
        assert data['impact'] == ['app', 'core', 'service']


def test_argparse_path_requires_two_positional_args():
    """architecture path alpha (missing target) must fail with non-zero exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_chain_graph(tmpdir)
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'path', 'alpha')
        assert result.returncode != 0


# =============================================================================
# Determinism tests
# =============================================================================


def test_path_deterministic_on_repeated_call():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        first = get_module_path('app', 'api', tmpdir)
        second = get_module_path('app', 'api', tmpdir)
        assert first == second


def test_neighbors_deterministic_sorted_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_fan_out_graph(tmpdir)
        first = get_module_neighbors('hub', 2, tmpdir)
        second = get_module_neighbors('hub', 2, tmpdir)
        assert first == second
        assert first == sorted(first)


def test_impact_deterministic_sorted_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_diamond_graph(tmpdir)
        first = get_module_impact('api', tmpdir)
        second = get_module_impact('api', tmpdir)
        assert first == second
        assert first == sorted(first)
