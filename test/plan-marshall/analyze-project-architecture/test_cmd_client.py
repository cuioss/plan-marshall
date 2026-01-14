#!/usr/bin/env python3
"""Tests for _cmd_client.py module."""

import sys
import tempfile
from argparse import Namespace

from _architecture_core import (
    save_derived_data,
)

# Import modules under test (PYTHONPATH set by conftest)
from _cmd_client import (
    cmd_modules,
    get_module_graph,
    get_modules_list,
    get_modules_with_command,
)

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
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate BUGGY args from 'architecture modules' (no --command filter)
        # The subparser sets args.command = 'modules', but this should NOT filter
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest - should be IGNORED for filtering
            filter_command=None,  # No filter - should list ALL modules
        )

        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_modules(args)

        assert result == 0, f'Expected return code 0, got {result}'
        output = stdout_capture.getvalue()
        # Should list all 3 modules, NOT filter by command='modules'
        assert 'modules[3]:' in output, (
            f'BUG: Naming collision! Code uses args.command for filtering '
            f"but that contains subparser dest 'modules'. "
            f"Expected 'modules[3]:' but got: {output}"
        )
        assert 'module-a' in output
        assert 'module-b' in output
        assert 'module-c' in output


def test_cmd_modules_without_filter_lists_all_modules():
    """cmd_modules without --command filter lists all modules."""
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate args from 'architecture modules' (no --command filter)
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest (should be ignored for filtering)
            filter_command=None,  # No filter - should list all modules
        )

        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_modules(args)

        assert result == 0, f'Expected return code 0, got {result}'
        output = stdout_capture.getvalue()
        # Should list all 3 modules
        assert 'modules[3]:' in output, f"Expected 'modules[3]:' in output, got: {output}"
        assert 'module-a' in output
        assert 'module-b' in output
        assert 'module-c' in output


def test_cmd_modules_with_filter_filters_by_command():
    """cmd_modules with --command filter only returns matching modules."""
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        # Simulate args from 'architecture modules --command verify'
        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest
            filter_command='verify',  # Filter by 'verify' command
        )

        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_modules(args)

        assert result == 0
        output = stdout_capture.getvalue()
        # Should list only modules with 'verify' command
        assert 'command: verify' in output, f"Expected 'command: verify' in output, got: {output}"
        assert 'module-a' in output
        assert 'module-b' in output
        assert 'module-c' not in output  # module-c has no 'verify'


def test_cmd_modules_with_filter_quality_gate():
    """cmd_modules with --command quality-gate returns only module-a."""
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # Subparser dest
            filter_command='quality-gate',
        )

        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = cmd_modules(args)

        assert result == 0
        output = stdout_capture.getvalue()
        assert 'module-a' in output
        assert 'module-b' not in output
        assert 'module-c' not in output


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
