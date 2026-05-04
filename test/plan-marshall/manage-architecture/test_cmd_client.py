#!/usr/bin/env python3
"""Tests for ``_cmd_client.py`` — read-side commands.

Pins the per-module on-disk layout: readers iterate ``_project.json``'s
``modules`` index and lazy-load per-module ``derived.json`` /
``enriched.json`` on demand. Legacy monolithic files are intentionally
absent from this surface.
"""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
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

cmd_modules = _cmd_client.cmd_modules
cmd_resolve = _cmd_client.cmd_resolve
cmd_files = _cmd_client.cmd_files
cmd_which_module = _cmd_client.cmd_which_module
cmd_find = _cmd_client.cmd_find
get_module_graph = _cmd_client.get_module_graph
get_modules_list = _cmd_client.get_modules_list
get_modules_with_command = _cmd_client.get_modules_with_command


# =============================================================================
# Helper Functions
# =============================================================================


def _seed_project(tmpdir: str, modules: dict[str, dict]) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files."""
    save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


def create_test_project(tmpdir: str) -> dict:
    """Three modules with varying command sets — used by cmd_modules tests."""
    modules = {
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
    }
    _seed_project(tmpdir, modules)
    return modules


# =============================================================================
# Tests for get_modules_list
# =============================================================================


def test_get_modules_list_returns_all():
    """get_modules_list returns every module name from ``_project.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_list(tmpdir)
        assert set(modules) == {'module-a', 'module-b', 'module-c'}


# =============================================================================
# Tests for get_modules_with_command
# =============================================================================


def test_get_modules_with_command_verify():
    """get_modules_with_command returns modules that declare 'verify'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_with_command('verify', tmpdir)
        assert set(modules) == {'module-a', 'module-b'}


def test_get_modules_with_command_module_tests():
    """get_modules_with_command returns modules with 'module-tests'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_with_command('module-tests', tmpdir)
        assert set(modules) == {'module-a', 'module-b'}


def test_get_modules_with_command_quality_gate_only_module_a():
    """get_modules_with_command returns only module-a for 'quality-gate'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_with_command('quality-gate', tmpdir)
        assert modules == ['module-a']


def test_get_modules_with_command_build_only_module_c():
    """get_modules_with_command returns only module-c for 'build'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_with_command('build', tmpdir)
        assert modules == ['module-c']


def test_get_modules_with_command_unknown_returns_empty():
    """get_modules_with_command returns [] for an unknown command name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)
        modules = get_modules_with_command('nonexistent-command', tmpdir)
        assert modules == []


# =============================================================================
# Tests for cmd_modules CLI handler
# =============================================================================


def test_cmd_modules_naming_collision_regression():
    """``architecture modules`` MUST list all modules, not filter on subparser dest.

    Argparse sets ``args.command='modules'`` from the subparser dest. The
    handler must read ``filter_command`` (not ``command``) so this collision
    cannot resurface.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            command='modules',  # subparser dest — must be ignored for filtering
            filter_command=None,
        )

        result = cmd_modules(args)

        assert result['status'] == 'success', f'Expected success, got {result}'
        assert len(result['modules']) == 3, (
            'BUG: naming collision! cmd_modules used args.command for filtering '
            f"but that holds the subparser dest 'modules'. Got: {result['modules']}"
        )
        assert {'module-a', 'module-b', 'module-c'} <= set(result['modules'])


def test_cmd_modules_without_filter_lists_all():
    """cmd_modules without --command filter returns every module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        args = Namespace(project_dir=tmpdir, command='modules', filter_command=None)
        result = cmd_modules(args)

        assert result['status'] == 'success'
        assert len(result['modules']) == 3
        assert {'module-a', 'module-b', 'module-c'} <= set(result['modules'])


def test_cmd_modules_with_filter_returns_matches():
    """cmd_modules --command verify returns only matching modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        args = Namespace(project_dir=tmpdir, command='modules', filter_command='verify')
        result = cmd_modules(args)

        assert result['status'] == 'success'
        assert result['command'] == 'verify'
        assert 'module-a' in result['modules']
        assert 'module-b' in result['modules']
        assert 'module-c' not in result['modules']


def test_cmd_modules_with_filter_quality_gate():
    """cmd_modules --command quality-gate returns only module-a."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project(tmpdir)

        args = Namespace(project_dir=tmpdir, command='modules', filter_command='quality-gate')
        result = cmd_modules(args)

        assert result['status'] == 'success'
        assert 'module-a' in result['modules']
        assert 'module-b' not in result['modules']
        assert 'module-c' not in result['modules']


# =============================================================================
# Helper functions for graph tests
# =============================================================================


def create_test_project_with_deps(tmpdir: str) -> dict:
    """Linear dep chain api → core → service → app."""
    modules = {
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
    }
    _seed_project(tmpdir, modules)
    return modules


def create_test_project_no_deps(tmpdir: str) -> dict:
    """Two unrelated standalone modules."""
    modules = {
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
    }
    _seed_project(tmpdir, modules)
    return modules


def create_test_project_with_aggregator(tmpdir: str) -> dict:
    """Project containing an aggregator (pom-packaging) module."""
    modules = {
        'parent': {
            'name': 'parent',
            'build_systems': ['maven'],
            'paths': {'module': '.', 'sources': []},
            'metadata': {'packaging': 'pom'},
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
    }
    _seed_project(tmpdir, modules)
    return modules


# =============================================================================
# Tests for get_module_graph
# =============================================================================


def test_get_module_graph_basic_structure():
    """get_module_graph returns the expected structure keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert 'graph' in result
        assert 'nodes' in result
        assert 'edges' in result
        assert 'layers' in result
        assert 'roots' in result
        assert 'leaves' in result
        assert 'circular_dependencies' in result


def test_get_module_graph_node_count():
    """get_module_graph reports the right number of nodes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['graph']['node_count'] == 4
        assert len(result['nodes']) == 4


def test_get_module_graph_edge_count():
    """get_module_graph reports edges from declared internal_dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        # api->core, api->service, core->service, service->app = 4 edges
        assert result['graph']['edge_count'] == 4
        assert len(result['edges']) == 4


def test_get_module_graph_layers_topologically_sorted():
    """get_module_graph computes Kahn-style topological layers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert len(result['layers']) == 4
        layer_map = {layer['layer']: layer['modules'] for layer in result['layers']}
        assert layer_map[0] == ['api']
        assert layer_map[1] == ['core']
        assert layer_map[2] == ['service']
        assert layer_map[3] == ['app']


def test_get_module_graph_identifies_roots():
    """get_module_graph identifies the dependency roots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['roots'] == ['api']


def test_get_module_graph_identifies_leaves():
    """get_module_graph identifies the dependency leaves."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['leaves'] == ['app']


def test_get_module_graph_no_deps():
    """get_module_graph handles two standalone modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_no_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['graph']['node_count'] == 2
        assert result['graph']['edge_count'] == 0
        assert result['edges'] == []
        assert set(result['roots']) == {'standalone-a', 'standalone-b'}
        assert set(result['leaves']) == {'standalone-a', 'standalone-b'}
        assert len(result['layers']) == 1
        assert result['layers'][0]['layer'] == 0


def test_get_module_graph_no_circular_when_acyclic():
    """get_module_graph reports no circular deps when graph is acyclic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['circular_dependencies'] is None


def test_get_module_graph_node_layer_assignment():
    """Every node carries a layer index matching its topological position."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        node_layers = {n['name']: n['layer'] for n in result['nodes']}
        assert node_layers['api'] == 0
        assert node_layers['core'] == 1
        assert node_layers['service'] == 2
        assert node_layers['app'] == 3


def test_get_module_graph_filters_aggregator_by_default():
    """Aggregator (pom-packaging) modules are filtered out by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_aggregator(tmpdir)
        result = get_module_graph(tmpdir)

        node_names = [n['name'] for n in result['nodes']]
        assert 'parent' not in node_names
        assert 'api' in node_names
        assert 'core' in node_names
        assert result['graph']['node_count'] == 2
        assert result['filtered_out'] == ['parent']


def test_get_module_graph_includes_aggregator_with_full():
    """Aggregator modules are included when full=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_aggregator(tmpdir)
        result = get_module_graph(tmpdir, full=True)

        node_names = [n['name'] for n in result['nodes']]
        assert 'parent' in node_names
        assert 'api' in node_names
        assert 'core' in node_names
        assert result['graph']['node_count'] == 3
        assert result['filtered_out'] is None


def test_get_module_graph_no_filtered_when_no_aggregators():
    """filtered_out is None when there are no aggregator modules to drop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_deps(tmpdir)
        result = get_module_graph(tmpdir)

        assert result['filtered_out'] is None


# =============================================================================
# Helper Functions for Resolve Tests
# =============================================================================


def create_test_project_with_root(tmpdir: str) -> dict:
    """Project with a root module (paths.module=='.') plus a child module."""
    modules = {
        'root': {
            'name': 'root',
            'build_systems': ['maven'],
            'paths': {'module': '.'},
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
    }
    _seed_project(tmpdir, modules)
    return modules


# =============================================================================
# Tests for cmd_resolve CLI handler
# =============================================================================


def test_cmd_resolve_with_module_returns_executable():
    """cmd_resolve returns the executable for the given --module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_root(tmpdir)

        args = Namespace(project_dir=tmpdir, resolve_command='module-tests', module='module-a')
        result = cmd_resolve(args)

        assert result['status'] == 'success'
        assert result['module'] == 'module-a'
        assert result['command'] == 'module-tests'
        assert result['executable'] == 'python3 .plan/execute-script.py module-a tests'
        assert result['resolution_level'] == 'module'


def test_cmd_resolve_without_module_uses_root():
    """cmd_resolve falls back to the root module when --module is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_root(tmpdir)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

        assert result['status'] == 'success'
        assert result['module'] == 'root'
        assert result['command'] == 'verify'
        assert result['resolution_level'] == 'module'


def test_cmd_resolve_cascades_to_root_when_command_missing_at_module():
    """cmd_resolve cascades up to root when command is absent at requested module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_root(tmpdir)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module='module-a')
        result = cmd_resolve(args)

        assert result['status'] == 'success'
        assert result['module'] == 'root'
        assert result['command'] == 'verify'
        assert result['resolution_level'] == 'root'


def test_cmd_resolve_unknown_module_returns_error():
    """cmd_resolve returns error_result when --module does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_root(tmpdir)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module='nonexistent-module')
        result = cmd_resolve(args)

        assert result['status'] == 'error'


def test_cmd_resolve_unknown_command_returns_error():
    """cmd_resolve returns error_result when the command cannot be resolved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_project_with_root(tmpdir)

        args = Namespace(project_dir=tmpdir, resolve_command='nonexistent-command', module='module-a')
        result = cmd_resolve(args)

        assert result['status'] == 'error'


# =============================================================================
# Files Inventory Readers (cmd_files / cmd_which_module / cmd_find)
# =============================================================================


def _seed_inventory_project(tmpdir: str) -> None:
    """Two modules with hand-crafted ``files`` blocks for inventory readers."""
    modules = {
        'pm-dev-java': {
            'name': 'pm-dev-java',
            'paths': {'module': 'marketplace/bundles/pm-dev-java'},
            'files': {
                'skill': [
                    'marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md',
                    'marketplace/bundles/pm-dev-java/skills/lombok/SKILL.md',
                ],
                'agent': ['marketplace/bundles/pm-dev-java/agents/reviewer.md'],
                'build_file': ['marketplace/bundles/pm-dev-java/plugin.json'],
            },
        },
        'plan-marshall': {
            'name': 'plan-marshall',
            'paths': {'module': 'marketplace/bundles/plan-marshall'},
            'files': {
                'skill': [
                    'marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md',
                ],
                'test': ['test/plan-marshall/manage-architecture/test_files_inventory.py'],
            },
        },
        'default': {
            'name': 'default',
            'paths': {'module': '.'},
            'files': {
                'doc': ['README.md'],
                # Shared path with a deeper-prefix module (tie-breaker check):
                'skill': ['marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md'],
            },
        },
    }
    _seed_project(tmpdir, modules)


def test_cmd_files_returns_full_inventory():
    """cmd_files without --category returns the whole files block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, module='pm-dev-java', category=None)
        result = cmd_files(args)

        assert result['status'] == 'success'
        assert result['module'] == 'pm-dev-java'
        assert 'skill' in result['files']
        assert 'agent' in result['files']


def test_cmd_files_with_category_filters():
    """cmd_files with --category narrows to a single bucket."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, module='pm-dev-java', category='skill')
        result = cmd_files(args)

        assert result['status'] == 'success'
        assert result['category'] == 'skill'
        assert result['files'] == [
            'marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md',
            'marketplace/bundles/pm-dev-java/skills/lombok/SKILL.md',
        ]


def test_cmd_files_unknown_category_returns_empty_list():
    """cmd_files with a category that has no entries returns empty results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, module='pm-dev-java', category='template')
        result = cmd_files(args)

        assert result['status'] == 'success'
        assert result['files'] == []


def test_cmd_files_passes_through_elision_shape():
    """A capped category preserves the ``{elided, sample}`` shape verbatim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        elided = {'elided': 750, 'sample': ['a', 'b', 'c']}
        modules = {
            'big': {
                'name': 'big',
                'paths': {'module': 'big'},
                'files': {'source': elided},
            },
        }
        _seed_project(tmpdir, modules)

        args = Namespace(project_dir=tmpdir, module='big', category='source')
        result = cmd_files(args)

        assert result['status'] == 'success'
        assert result['files'] == elided


def test_cmd_files_unknown_module_returns_error():
    """cmd_files returns error_result when --module is not in the index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, module='nope', category=None)
        result = cmd_files(args)

        assert result['status'] == 'error'


def test_cmd_which_module_resolves_unique_path():
    """cmd_which_module returns the single owning module for a unique path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(
            project_dir=tmpdir,
            path='marketplace/bundles/pm-dev-java/agents/reviewer.md',
        )
        result = cmd_which_module(args)

        assert result['status'] == 'success'
        assert result['module'] == 'pm-dev-java'


def test_cmd_which_module_tie_breaks_by_longest_prefix():
    """When multiple modules list the same path, the longest paths.module wins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        # The path appears in both ``default`` (paths.module = '.') and
        # ``pm-dev-java`` (paths.module = 'marketplace/bundles/pm-dev-java').
        # The longer prefix wins.
        args = Namespace(
            project_dir=tmpdir,
            path='marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md',
        )
        result = cmd_which_module(args)

        assert result['status'] == 'success'
        assert result['module'] == 'pm-dev-java'


def test_cmd_which_module_no_match_returns_null():
    """cmd_which_module returns ``module: None`` when no inventory matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, path='nope/missing.md')
        result = cmd_which_module(args)

        assert result['status'] == 'success'
        assert result['module'] is None


def test_cmd_find_aggregates_across_modules():
    """cmd_find returns matches from every module that has a hit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, pattern='*SKILL.md', category=None)
        result = cmd_find(args)

        assert result['status'] == 'success'
        # pm-dev-java contributes 2 SKILL.md files, plan-marshall contributes 1,
        # default contributes 1 (the cross-listed path) — 4 total.
        modules_in_results = {r['module'] for r in result['results']}
        assert {'pm-dev-java', 'plan-marshall', 'default'}.issubset(modules_in_results)
        assert all(r['path'].endswith('SKILL.md') for r in result['results'])


def test_cmd_find_with_category_filter():
    """cmd_find narrows results to the requested category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, pattern='*', category='agent')
        result = cmd_find(args)

        assert result['status'] == 'success'
        assert all(r['category'] == 'agent' for r in result['results'])
        assert any(r['path'].endswith('reviewer.md') for r in result['results'])


def test_cmd_find_no_matches_returns_empty_results():
    """cmd_find with a non-matching pattern returns count=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_inventory_project(tmpdir)

        args = Namespace(project_dir=tmpdir, pattern='*.nonexistent', category=None)
        result = cmd_find(args)

        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['results'] == []


def test_cmd_find_searches_elided_sample_paths():
    """Elided buckets contribute their ``sample`` paths to find results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        modules = {
            'big': {
                'name': 'big',
                'paths': {'module': 'big'},
                'files': {
                    'source': {'elided': 9999, 'sample': ['big/a.py', 'big/b.py']},
                },
            },
        }
        _seed_project(tmpdir, modules)

        args = Namespace(project_dir=tmpdir, pattern='big/a.py', category=None)
        result = cmd_find(args)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == 'big/a.py'


# =============================================================================
# Argparse wiring assertion (catches subcommand-registration regressions)
# =============================================================================


def test_architecture_argparse_registers_files_inventory_subcommands():
    """Loading ``architecture.py``'s ``--help`` exposes the three new verbs.

    A unit-level guard against accidentally dropping subparser registration
    in ``architecture.py``. Invokes the script with ``--help`` and parses
    the output for the verb names — this is identical to how a user would
    discover the commands.
    """
    import os
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f'--help failed: {proc.stderr}'
    help_text = proc.stdout
    assert 'files' in help_text
    assert 'which-module' in help_text
    assert 'find' in help_text


def test_architecture_argparse_files_subcommand_accepts_module_and_category():
    """``files --module X --category Y`` is a valid argument combination."""
    import os
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), 'files', '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    assert '--module' in proc.stdout
    assert '--category' in proc.stdout


def test_architecture_argparse_which_module_subcommand_accepts_path():
    """``which-module --path P`` is a valid argument combination."""
    import os
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), 'which-module', '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    assert '--path' in proc.stdout


def test_architecture_argparse_find_subcommand_accepts_pattern_and_category():
    """``find --pattern P --category Y`` is a valid argument combination."""
    import os
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / 'architecture.py'), 'find', '--help'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0
    assert '--pattern' in proc.stdout
    assert '--category' in proc.stdout
