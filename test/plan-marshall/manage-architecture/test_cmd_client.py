#!/usr/bin/env python3
"""Tests for _cmd_client.py module."""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

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

save_derived_data = _architecture_core.save_derived_data
cmd_modules = _cmd_client.cmd_modules
cmd_resolve = _cmd_client.cmd_resolve
get_module_graph = _cmd_client.get_module_graph
get_modules_list = _cmd_client.get_modules_list
get_modules_with_command = _cmd_client.get_modules_with_command

# =============================================================================
# Helper Functions
# =============================================================================


def create_test_derived_data(tmpdir: str) -> dict:
    """Create test derived-data.json and return the data."""
    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a'},
                'commands': {'module-tests': 'python3 ...', 'verify': 'python3 ...', 'quality-gate': 'python3 ...'},
            },
            'module-b': {
                'name': 'module-b',
                'build_systems': ['maven'],
                'paths': {'module': 'module-b'},
                'commands': {'module-tests': 'python3 ...', 'verify': 'python3 ...'},
            },
            'module-c': {
                'name': 'module-c',
                'build_systems': ['npm'],
                'paths': {'module': 'module-c'},
                'commands': {'build': 'npm run build'},
            },
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


# =============================================================================
# Tests for get_modules_list
# =============================================================================


def test_get_modules_list_returns_all():
    """get_modules_list returns all module names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_list(tmpdir)
        assert set(modules) == {'module-a', 'module-b', 'module-c'}


# =============================================================================
# Tests for get_modules_with_command
# =============================================================================


def test_get_modules_with_command_verify():
    """get_modules_with_command returns modules with verify command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_with_command('verify', tmpdir)
        assert set(modules) == {'module-a', 'module-b'}


def test_get_modules_with_command_module_tests():
    """get_modules_with_command returns modules with module-tests command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_with_command('module-tests', tmpdir)
        assert set(modules) == {'module-a', 'module-b'}


def test_get_modules_with_command_quality_gate():
    """get_modules_with_command returns only module-a for quality-gate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_with_command('quality-gate', tmpdir)
        assert modules == ['module-a']


def test_get_modules_with_command_build():
    """get_modules_with_command returns only module-c for build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_with_command('build', tmpdir)
        assert modules == ['module-c']


def test_get_modules_with_command_nonexistent():
    """get_modules_with_command returns empty list for unknown command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        modules = get_modules_with_command('nonexistent-command', tmpdir)
        assert modules == []


# =============================================================================
# Tests for cmd_modules CLI handler
# =============================================================================


def test_cmd_modules_bug_command_naming_collision():
    """REGRESSION TEST: Expose the naming collision bug.

    When running 'architecture modules' from CLI:
    - Argparse sets args.command = 'modules' (from subparser dest)
    - cmd_modules reads getattr(args, 'command', None) for filtering
    - This incorrectly filters by command='modules' instead of listing all

    This test simulates the BUGGY CLI behavior to document the bug.
    After fix, this test should still pass because the code should
    use filter_command instead of command.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate BUGGY args from 'architecture modules' (no --command filter)
        # The subparser sets args.command = 'modules', but this should NOT filter
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest - should be IGNORED for filtering
            filter_command=None,  # No filter - should list ALL modules
        )

        result = cmd_modules(args)

        assert result['status'] == 'success', f'Expected success, got {result}'
        # Should list all 3 modules, NOT filter by command='modules'
        assert len(result['modules']) == 3, (
            f'BUG: Naming collision! Code uses args.command for filtering '
            f"but that contains subparser dest 'modules'. "
            f"Expected 3 modules but got: {result['modules']}"
        )
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert 'module-c' in result['modules']


def test_cmd_modules_without_filter_lists_all_modules():
    """cmd_modules without --command filter lists all modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate args from 'architecture modules' (no --command filter)
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest (should be ignored for filtering)
            filter_command=None,  # No filter - should list all modules
        )

        result = cmd_modules(args)

        assert result['status'] == 'success', f'Expected success, got {result}'
        # Should list all 3 modules
        assert len(result['modules']) == 3, f"Expected 3 modules, got: {result['modules']}"
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert 'module-c' in result['modules']


def test_cmd_modules_with_filter_filters_by_command():
    """cmd_modules with --command filter only returns matching modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate args from 'architecture modules --command verify'
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest
            filter_command='verify',  # Filter by 'verify' command
        )

        result = cmd_modules(args)

        assert result['status'] == 'success'
        assert result['command'] == 'verify'
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert 'module-c' not in result['modules']  # module-c has no 'verify'


def test_cmd_modules_with_filter_quality_gate():
    """cmd_modules with --command quality-gate returns only module-a."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest
            filter_command='quality-gate',
        )

        result = cmd_modules(args)

        assert result['status'] == 'success'
        assert 'module-a' in result['modules']
        assert 'module-b' not in result['modules']
        assert 'module-c' not in result['modules']


# =============================================================================
# Helper Functions for Graph Tests
# =============================================================================


def create_test_derived_data_with_deps(tmpdir: str) -> dict:
    """Create test derived-data.json with internal_dependencies."""
    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'api': {
                'name': 'api',
                'build_systems': ['maven'],
                'paths': {'module': 'api', 'sources': ['api/src/main/java']},
                'internal_dependencies': [],
                'commands': {},
            },
            'core': {
                'name': 'core',
                'build_systems': ['maven'],
                'paths': {'module': 'core', 'sources': ['core/src/main/java']},
                'internal_dependencies': ['api'],
                'commands': {},
            },
            'service': {
                'name': 'service',
                'build_systems': ['maven'],
                'paths': {'module': 'service', 'sources': ['service/src/main/java']},
                'internal_dependencies': ['core', 'api'],
                'commands': {},
            },
            'app': {
                'name': 'app',
                'build_systems': ['maven'],
                'paths': {'module': 'app', 'sources': ['app/src/main/java']},
                'internal_dependencies': ['service'],
                'commands': {},
            },
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


def create_test_derived_data_no_deps(tmpdir: str) -> dict:
    """Create test derived-data.json with no internal_dependencies."""
    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'standalone-a': {
                'name': 'standalone-a',
                'build_systems': ['maven'],
                'paths': {'module': 'standalone-a', 'sources': ['standalone-a/src/main/java']},
                'internal_dependencies': [],
                'commands': {},
            },
            'standalone-b': {
                'name': 'standalone-b',
                'build_systems': ['maven'],
                'paths': {'module': 'standalone-b', 'sources': ['standalone-b/src/main/java']},
                'internal_dependencies': [],
                'commands': {},
            },
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


def create_test_derived_data_with_aggregator(tmpdir: str) -> dict:
    """Create test derived-data.json with an aggregator (parent) module."""
    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'parent': {
                'name': 'parent',
                'build_systems': ['maven'],
                'paths': {'module': '.', 'sources': []},
                'metadata': {'packaging': 'pom'},  # pom packaging = aggregator
                'internal_dependencies': [],
                'commands': {},
            },
            'api': {
                'name': 'api',
                'build_systems': ['maven'],
                'paths': {'module': 'api', 'sources': ['api/src/main/java']},
                'metadata': {'packaging': 'jar'},
                'internal_dependencies': [],
                'commands': {},
            },
            'core': {
                'name': 'core',
                'build_systems': ['maven'],
                'paths': {'module': 'core', 'sources': ['core/src/main/java']},
                'metadata': {'packaging': 'jar'},
                'internal_dependencies': ['api'],
                'commands': {},
            },
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


# =============================================================================
# Tests for get_module_graph
# =============================================================================


def test_get_module_graph_basic_structure():
    """get_module_graph returns expected structure keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert 'graph' in result
        assert 'nodes' in result
        assert 'edges' in result
        assert 'layers' in result
        assert 'roots' in result
        assert 'leaves' in result
        assert 'circular_dependencies' in result


def test_get_module_graph_node_count():
    """get_module_graph returns correct node count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['graph']['node_count'] == 4
        assert len(result['nodes']) == 4


def test_get_module_graph_edge_count():
    """get_module_graph returns correct edge count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # api->core, api->service, core->service, service->app = 4 edges
        assert result['graph']['edge_count'] == 4
        assert len(result['edges']) == 4


def test_get_module_graph_layers():
    """get_module_graph computes topological layers correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # Expected layers:
        # 0: api (no deps)
        # 1: core (depends on api)
        # 2: service (depends on core, api)
        # 3: app (depends on service)
        layers = result['layers']
        assert len(layers) == 4

        layer_map = {layer['layer']: layer['modules'] for layer in layers}
        assert layer_map[0] == ['api']
        assert layer_map[1] == ['core']
        assert layer_map[2] == ['service']
        assert layer_map[3] == ['app']


def test_get_module_graph_roots():
    """get_module_graph identifies roots correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # Only api has no dependencies
        assert result['roots'] == ['api']


def test_get_module_graph_leaves():
    """get_module_graph identifies leaves correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # Only app has nothing depending on it
        assert result['leaves'] == ['app']


def test_get_module_graph_no_deps():
    """get_module_graph handles modules with no dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_no_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['graph']['node_count'] == 2
        assert result['graph']['edge_count'] == 0
        assert result['edges'] == []
        # All are roots and leaves when no deps
        assert set(result['roots']) == {'standalone-a', 'standalone-b'}
        assert set(result['leaves']) == {'standalone-a', 'standalone-b'}
        # All in layer 0
        assert len(result['layers']) == 1
        assert result['layers'][0]['layer'] == 0


def test_get_module_graph_no_circular():
    """get_module_graph reports no circular dependencies when none exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['circular_dependencies'] is None


def test_get_module_graph_node_layer_assignment():
    """get_module_graph assigns correct layer to each node."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        node_layers = {n['name']: n['layer'] for n in result['nodes']}
        assert node_layers['api'] == 0
        assert node_layers['core'] == 1
        assert node_layers['service'] == 2
        assert node_layers['app'] == 3


def test_get_module_graph_filters_aggregator_by_default():
    """get_module_graph filters out aggregator modules by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_aggregator(tmpdir)
        result = get_module_graph(tmpdir)

        # Parent should be filtered out (no sources)
        node_names = [n['name'] for n in result['nodes']]
        assert 'parent' not in node_names
        assert 'api' in node_names
        assert 'core' in node_names
        assert result['graph']['node_count'] == 2
        assert result['filtered_out'] == ['parent']


def test_get_module_graph_includes_aggregator_with_full():
    """get_module_graph includes aggregator modules with full=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_aggregator(tmpdir)
        result = get_module_graph(tmpdir, full=True)

        # Parent should be included when full=True
        node_names = [n['name'] for n in result['nodes']]
        assert 'parent' in node_names
        assert 'api' in node_names
        assert 'core' in node_names
        assert result['graph']['node_count'] == 3
        assert result['filtered_out'] is None


def test_get_module_graph_no_filtered_when_no_aggregators():
    """get_module_graph returns None for filtered_out when no aggregators exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # No aggregators in this test data
        assert result['filtered_out'] is None


# =============================================================================
# Helper Functions for Resolve Tests
# =============================================================================


def create_test_derived_data_with_root(tmpdir: str) -> dict:
    """Create test derived-data.json with a root module and child modules.

    Used by cmd_resolve tests to exercise both the direct-module path and the
    cascading fallback to the root module.
    """
    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'root': {
                'name': 'root',
                'build_systems': ['maven'],
                'paths': {'module': '.'},  # '.' marks the root module
                'commands': {
                    'verify': 'python3 .plan/execute-script.py root verify',
                    'compile': 'python3 .plan/execute-script.py root compile',
                },
            },
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a'},
                'commands': {
                    'module-tests': 'python3 .plan/execute-script.py module-a tests',
                },
            },
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


# =============================================================================
# Tests for cmd_resolve CLI handler (--module argument)
# =============================================================================


def test_cmd_resolve_with_module_returns_executable():
    """cmd_resolve resolves a command at the specified --module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_root(tmpdir)

        # Simulate args from 'architecture resolve --command module-tests --module module-a'
        args = Namespace(
            project_dir=tmpdir,
            resolve_command='module-tests',
            module='module-a',
        )

        result = cmd_resolve(args)

        assert result['status'] == 'success', f'Expected success, got {result}'
        assert result['module'] == 'module-a'
        assert result['command'] == 'module-tests'
        assert result['executable'] == 'python3 .plan/execute-script.py module-a tests'
        assert result['resolution_level'] == 'module'


def test_cmd_resolve_without_module_uses_root():
    """cmd_resolve defaults to root module when --module is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_root(tmpdir)

        # Simulate args from 'architecture resolve --command verify' (no --module)
        args = Namespace(
            project_dir=tmpdir,
            resolve_command='verify',
            module=None,
        )

        result = cmd_resolve(args)

        assert result['status'] == 'success'
        assert result['module'] == 'root'
        assert result['command'] == 'verify'
        assert result['resolution_level'] == 'module'


def test_cmd_resolve_cascades_to_root_when_missing_at_module():
    """cmd_resolve falls back to root when command absent at requested --module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_root(tmpdir)

        # 'verify' lives on root, not on module-a — should cascade up
        args = Namespace(
            project_dir=tmpdir,
            resolve_command='verify',
            module='module-a',
        )

        result = cmd_resolve(args)

        assert result['status'] == 'success'
        assert result['module'] == 'root'
        assert result['command'] == 'verify'
        assert result['resolution_level'] == 'root'


def test_cmd_resolve_unknown_module_returns_error():
    """cmd_resolve returns error_result when --module does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_root(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            resolve_command='verify',
            module='nonexistent-module',
        )

        result = cmd_resolve(args)

        assert result['status'] == 'error'


def test_cmd_resolve_unknown_command_returns_error():
    """cmd_resolve returns error_result when --command cannot be resolved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data_with_root(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            resolve_command='nonexistent-command',
            module='module-a',
        )

        result = cmd_resolve(args)

        assert result['status'] == 'error'


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    import traceback

    tests = [
        test_get_modules_list_returns_all,
        test_get_modules_with_command_verify,
        test_get_modules_with_command_module_tests,
        test_get_modules_with_command_quality_gate,
        test_get_modules_with_command_build,
        test_get_modules_with_command_nonexistent,
        # cmd_modules CLI handler tests
        test_cmd_modules_bug_command_naming_collision,
        test_cmd_modules_without_filter_lists_all_modules,
        test_cmd_modules_with_filter_filters_by_command,
        test_cmd_modules_with_filter_quality_gate,
        # cmd_resolve tests (--module argument)
        test_cmd_resolve_with_module_returns_executable,
        test_cmd_resolve_without_module_uses_root,
        test_cmd_resolve_cascades_to_root_when_missing_at_module,
        test_cmd_resolve_unknown_module_returns_error,
        test_cmd_resolve_unknown_command_returns_error,
        test_get_module_graph_basic_structure,
        test_get_module_graph_node_count,
        test_get_module_graph_edge_count,
        test_get_module_graph_layers,
        test_get_module_graph_roots,
        test_get_module_graph_leaves,
        test_get_module_graph_no_deps,
        test_get_module_graph_no_circular,
        test_get_module_graph_node_layer_assignment,
        test_get_module_graph_filters_aggregator_by_default,
        test_get_module_graph_includes_aggregator_with_full,
        test_get_module_graph_no_filtered_when_no_aggregators,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f'PASSED: {test.__name__}')
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)
