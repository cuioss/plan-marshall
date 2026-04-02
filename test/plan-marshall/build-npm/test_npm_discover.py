#!/usr/bin/env python3
"""Tests for _npm_cmd_discover.py module discovery.

Tests the discover_npm_modules() function directly, covering single-package
projects, workspaces, and command generation.
"""

import json
import sys
from pathlib import Path

# Shared test helpers (test/plan-marshall/conftest.py adds parent to sys.path)
from conftest import BuildContext
from discovery_test_helpers import (
    assert_command_uses_executor,
    assert_module_commands,
    assert_module_paths,
    assert_module_stats,
    assert_valid_module,
)

# Import module under test (PYTHONPATH set by conftest)
from _npm_cmd_discover import discover_npm_modules


# =============================================================================
# Test: Single Package Discovery
# =============================================================================


def test_discover_single_package():
    """Test discovery of a single npm package."""
    with BuildContext() as ctx:
        pkg = {'name': 'my-app', 'version': '1.0.0', 'description': 'A sample app'}
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        modules = discover_npm_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        module = modules[0]
        assert_valid_module(module, build_system='npm', expected_name='my-app')
        assert_module_paths(module, expected_module_path='.', expect_descriptor=True)
        assert module['metadata']['description'] == 'A sample app'


def test_discover_no_package_json():
    """Test discovery with no package.json returns empty list."""
    with BuildContext() as ctx:
        modules = discover_npm_modules(str(ctx.temp_dir))
        assert modules == []


def test_discover_single_package_default_name():
    """Test discovery assigns 'default' name to root without name field."""
    with BuildContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{}')

        modules = discover_npm_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        assert modules[0]['name'] == 'default'


# =============================================================================
# Test: Workspace Discovery
# =============================================================================


def test_discover_workspaces_array():
    """Test discovery with workspaces as array of glob patterns."""
    with BuildContext() as ctx:
        root_pkg = {'name': 'monorepo', 'workspaces': ['packages/*']}
        (ctx.temp_dir / 'package.json').write_text(json.dumps(root_pkg))

        packages_dir = ctx.temp_dir / 'packages'
        packages_dir.mkdir()

        pkg_a = packages_dir / 'pkg-a'
        pkg_a.mkdir()
        (pkg_a / 'package.json').write_text(json.dumps({'name': '@mono/pkg-a', 'version': '1.0.0'}))

        pkg_b = packages_dir / 'pkg-b'
        pkg_b.mkdir()
        (pkg_b / 'package.json').write_text(json.dumps({'name': '@mono/pkg-b', 'version': '2.0.0'}))

        modules = discover_npm_modules(str(ctx.temp_dir))

        # Root + 2 workspaces
        assert len(modules) == 3
        names = {m['name'] for m in modules}
        assert 'monorepo' in names
        assert '@mono/pkg-a' in names
        assert '@mono/pkg-b' in names


def test_discover_workspaces_object_format():
    """Test discovery with workspaces as object with packages key."""
    with BuildContext() as ctx:
        root_pkg = {'name': 'monorepo', 'workspaces': {'packages': ['packages/*']}}
        (ctx.temp_dir / 'package.json').write_text(json.dumps(root_pkg))

        packages_dir = ctx.temp_dir / 'packages'
        packages_dir.mkdir()

        pkg_dir = packages_dir / 'my-pkg'
        pkg_dir.mkdir()
        (pkg_dir / 'package.json').write_text(json.dumps({'name': 'my-pkg'}))

        modules = discover_npm_modules(str(ctx.temp_dir))

        # Root + 1 workspace
        assert len(modules) == 2
        ws_module = next(m for m in modules if m['name'] == 'my-pkg')
        assert_valid_module(ws_module, build_system='npm', expected_name='my-pkg')
        assert_module_paths(ws_module, expected_module_path='packages/my-pkg')


# =============================================================================
# Test: Command Generation
# =============================================================================


def test_commands_from_scripts():
    """Test command generation from package.json scripts."""
    with BuildContext() as ctx:
        pkg = {
            'name': 'test-app',
            'scripts': {'build': 'tsc', 'test': 'jest', 'lint': 'eslint src/', 'clean': 'rimraf dist'},
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        modules = discover_npm_modules(str(ctx.temp_dir))
        assert_module_commands(
            modules[0],
            expected_commands=['compile', 'module-tests', 'quality-gate', 'verify', 'clean'],
        )
        assert_command_uses_executor(modules[0], 'compile', skill_notation='plan-marshall:build-npm:npm')


def test_commands_minimal():
    """Test commands with only test script."""
    with BuildContext() as ctx:
        pkg = {'name': 'test-app', 'scripts': {'test': 'jest'}}
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        modules = discover_npm_modules(str(ctx.temp_dir))
        commands = modules[0]['commands']

        assert 'module-tests' in commands
        assert 'verify' in commands
        assert 'compile' not in commands
        assert 'clean' not in commands


def test_commands_no_scripts():
    """Test commands with no scripts — install is always available."""
    with BuildContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text(json.dumps({'name': 'bare'}))

        modules = discover_npm_modules(str(ctx.temp_dir))
        commands = modules[0]['commands']

        # install is always generated even without scripts
        assert 'install' in commands
        # No script-dependent commands should be present
        assert 'compile' not in commands
        assert 'module-tests' not in commands
        assert 'quality-gate' not in commands


def test_commands_workspace_scoping():
    """Test that workspace module commands include --workspace flag."""
    with BuildContext() as ctx:
        root_pkg = {'name': 'monorepo', 'workspaces': ['packages/*']}
        (ctx.temp_dir / 'package.json').write_text(json.dumps(root_pkg))

        packages_dir = ctx.temp_dir / 'packages'
        packages_dir.mkdir()
        pkg_dir = packages_dir / 'my-pkg'
        pkg_dir.mkdir()
        (pkg_dir / 'package.json').write_text(
            json.dumps({'name': 'my-pkg', 'scripts': {'test': 'jest'}})
        )

        modules = discover_npm_modules(str(ctx.temp_dir))
        ws_module = next(m for m in modules if m['name'] == 'my-pkg')

        assert '--workspace=my-pkg' in ws_module['commands']['module-tests']


# =============================================================================
# Test: Dependencies
# =============================================================================


def test_dependencies_extraction():
    """Test dependency extraction from package.json."""
    with BuildContext() as ctx:
        pkg = {
            'name': 'test-app',
            'dependencies': {'express': '^4.18.0', 'lodash': '^4.17.21'},
            'devDependencies': {'jest': '^29.0.0'},
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        modules = discover_npm_modules(str(ctx.temp_dir))
        deps = modules[0]['dependencies']

        assert isinstance(deps, list)
        assert 'express:runtime' in deps
        assert 'lodash:runtime' in deps
        assert 'jest:dev' in deps


# =============================================================================
# Test: README Detection
# =============================================================================


def test_readme_detection():
    """Test README file detection in paths."""
    with BuildContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text(json.dumps({'name': 'test'}))
        (ctx.temp_dir / 'README.md').write_text('# Test')

        modules = discover_npm_modules(str(ctx.temp_dir))

        assert modules[0]['paths']['readme'] == 'README.md'


def test_no_readme():
    """Test paths.readme is None when no README exists."""
    with BuildContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text(json.dumps({'name': 'test'}))

        modules = discover_npm_modules(str(ctx.temp_dir))

        assert modules[0]['paths']['readme'] is None
