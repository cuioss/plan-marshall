#!/usr/bin/env python3
"""Tests for discover_modules() in npm extension.

Tests the unified module discovery API for npm projects including
metadata extraction, dependency parsing, and stats.

Updated to test spec-compliant structure per build-project-structure.md:
- build_systems: ["npm"] (array)
- paths: {module, descriptor, sources, tests, readme}
- metadata: {type, description}
- packages: {} (object keyed by package name)
- dependencies: ["npm:name:scope", ...] (string format)
- stats: {source_files, test_files}
- commands: {} (canonical command mappings)
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import (
    TestRunner,
    BuildTestContext
)

# Use importlib to avoid module naming conflicts with other Extension classes
import importlib.util

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-dev-frontend' / 'skills' / 'plan-marshall-plugin' / 'extension.py'


def _load_npm_extension():
    """Load npm Extension class avoiding conflicts."""
    spec = importlib.util.spec_from_file_location("npm_extension", EXTENSION_FILE)
    npm_ext = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(npm_ext)
    return npm_ext.Extension


Extension = _load_npm_extension()


# =============================================================================
# Test: Basic Module Discovery
# =============================================================================

def test_discover_modules_single_module():
    """Test discover_modules with single npm project."""
    with BuildTestContext() as ctx:
        # Create a single-module npm project
        pkg = {
            "name": "my-app",
            "version": "1.0.0",
            "description": "My sample application",
            "type": "module"
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        # Create source directory
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'index.js').write_text('export default function() {}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        module = modules[0]

        # New structure assertions
        assert module['name'] == 'my-app'
        assert module['build_systems'] == ['npm']
        assert module['paths']['module'] == '.'
        assert module['paths']['descriptor'] == 'package.json'
        assert module['metadata']['description'] == 'My sample application'


def test_discover_modules_with_workspaces():
    """Test discover_modules with npm workspaces.

    Discovery returns ALL package.json files including root workspace container.
    Root module is returned first (at "."), followed by workspace packages.
    """
    with BuildTestContext() as ctx:
        # Create root package.json with workspaces
        root_pkg = {
            "name": "monorepo",
            "workspaces": ["packages/*"]
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(root_pkg))

        # Create packages directory
        packages_dir = ctx.temp_dir / 'packages'
        packages_dir.mkdir()

        # Create first workspace
        pkg_a_dir = packages_dir / 'pkg-a'
        pkg_a_dir.mkdir()
        (pkg_a_dir / 'package.json').write_text(json.dumps({
            "name": "@monorepo/pkg-a",
            "version": "1.0.0"
        }))

        # Create second workspace
        pkg_b_dir = packages_dir / 'pkg-b'
        pkg_b_dir.mkdir()
        (pkg_b_dir / 'package.json').write_text(json.dumps({
            "name": "@monorepo/pkg-b",
            "version": "2.0.0"
        }))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Discovery returns root + 2 workspace packages = 3 modules
        assert len(modules) == 3

        # Find modules by path (more reliable than name in test context)
        root = next(m for m in modules if m['paths']['module'] == '.')
        pkg_a = next(m for m in modules if m['paths']['module'] == 'packages/pkg-a')
        pkg_b = next(m for m in modules if m['paths']['module'] == 'packages/pkg-b')

        # Root module verification (name may be 'default' without npm installed)
        assert root['build_systems'] == ['npm']
        assert root['paths']['descriptor'] == 'package.json'

        # Workspace module verification
        assert pkg_a['name'] == 'pkg-a'
        assert pkg_b['name'] == 'pkg-b'
        assert pkg_a['build_systems'] == ['npm']
        assert pkg_b['build_systems'] == ['npm']


def test_discover_modules_no_package_json():
    """Test discover_modules with no package.json."""
    with BuildTestContext() as ctx:
        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 0


# =============================================================================
# Test: Metadata Extraction
# =============================================================================

def test_metadata_extraction():
    """Test metadata extraction from package.json.

    npm metadata includes planning-relevant fields: type, description.
    NOT Maven fields (artifact_id, group_id, parent, profiles).
    """
    with BuildTestContext() as ctx:
        pkg = {
            "name": "test-pkg",
            "version": "3.2.1",
            "description": "A test package",
            "type": "commonjs",
            "private": True,  # Not extracted - not useful for planning
            "main": "dist/index.js",  # Not extracted - runtime detail
            "license": "MIT",
            "exports": {".": "./dist/index.js"},
            "scripts": {"build": "tsc", "test": "jest"}
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        metadata = modules[0]['metadata']
        # Planning-relevant npm metadata
        assert metadata['type'] == 'commonjs'
        assert metadata['description'] == 'A test package'
        # Not extracted - not useful for planning
        assert 'version' not in metadata
        assert 'private' not in metadata
        assert 'main' not in metadata
        assert 'license' not in metadata
        assert 'exports' not in metadata
        assert 'scripts' not in metadata
        # Should NOT have Maven fields
        assert 'artifact_id' not in metadata
        assert 'group_id' not in metadata
        assert 'parent' not in metadata
        assert 'profiles' not in metadata
        assert 'packaging' not in metadata


# =============================================================================
# Test: Dependency Extraction
# =============================================================================

def test_extract_dependencies():
    """Test dependency extraction structure.

    Note: Dependencies are extracted via `npm ls --json --depth=0` which requires
    installed node_modules. In unit test context without npm install, dependencies
    will be empty. This test verifies the structure is correct (list type).

    Integration tests with real projects verify actual dependency extraction.
    """
    with BuildTestContext() as ctx:
        pkg = {
            "name": "test-pkg",
            "dependencies": {
                "lodash": "^4.17.21",
                "express": "^4.18.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "typescript": "^5.0.0"
            },
            "peerDependencies": {
                "react": "^18.0.0"
            }
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Dependencies is a list (empty without npm install, populated with real projects)
        deps = modules[0]['dependencies']
        assert isinstance(deps, list), "dependencies should be a list"

        # Without npm install, dependencies will be empty
        # Integration tests verify actual dependency extraction with real projects


# =============================================================================
# Test: Source Directory Discovery (via paths object)
# =============================================================================

def test_discover_sources_src():
    """Test source directory discovery with src."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        (ctx.temp_dir / 'src').mkdir()

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # New structure: paths.sources instead of sources
        paths = modules[0]['paths']
        assert 'src' in paths['sources']


def test_discover_sources_test():
    """Test test directory discovery."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        (ctx.temp_dir / 'test').mkdir()
        (ctx.temp_dir / '__tests__').mkdir()

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # New structure: paths.tests
        paths = modules[0]['paths']
        assert 'test' in paths['tests']
        assert '__tests__' in paths['tests']


def test_discover_sources_no_resources_in_paths():
    """Test that resources are not included in paths (not in spec)."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        (ctx.temp_dir / 'public').mkdir()
        (ctx.temp_dir / 'static').mkdir()

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # resources is not part of spec - paths only has module, descriptor, sources, tests, readme
        paths = modules[0]['paths']
        assert 'resources' not in paths


# =============================================================================
# Test: Stats
# =============================================================================

def test_stats_file_counts():
    """Test source and test file counting."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')

        # Create source files
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'index.js').write_text('export default {}')
        (src_dir / 'utils.ts').write_text('export const x = 1')
        (src_dir / 'component.tsx').write_text('export default () => null')

        # Create test files
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'index.test.js').write_text('test("x", () => {})')
        (test_dir / 'utils.test.ts').write_text('test("y", () => {})')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        stats = modules[0]['stats']
        assert stats['source_files'] == 3
        assert stats['test_files'] == 2


def test_readme_in_paths():
    """Test README detection returns path in paths.readme."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        (ctx.temp_dir / 'README.md').write_text('# My Project')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # New structure: paths.readme instead of stats.has_readme
        assert modules[0]['paths']['readme'] == 'README.md'


def test_no_readme_in_paths():
    """Test README key is omitted when none exists (null values filtered)."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # readme key should be omitted, not set to None
        assert 'readme' not in modules[0]['paths']


# =============================================================================
# Test: build_systems field (array)
# =============================================================================

def test_build_systems_is_array():
    """Test that build_systems is an array, not a string."""
    with BuildTestContext() as ctx:
        # Create npm project
        (ctx.temp_dir / 'package.json').write_text('{"name": "frontend", "version": "1.0.0"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        # build_systems should be ["npm"] (list), not "npm" (string)
        assert modules[0]['build_systems'] == ['npm']
        assert isinstance(modules[0]['build_systems'], list)


# =============================================================================
# Test: Workspaces with object format
# =============================================================================

def test_workspaces_object_format():
    """Test workspaces with object format (packages key)."""
    with BuildTestContext() as ctx:
        # Create root package.json with object workspaces
        root_pkg = {
            "name": "monorepo",
            "workspaces": {
                "packages": ["packages/*"]
            }
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(root_pkg))

        # Create packages directory
        packages_dir = ctx.temp_dir / 'packages'
        packages_dir.mkdir()

        # Create workspace
        pkg_dir = packages_dir / 'my-pkg'
        pkg_dir.mkdir()
        (pkg_dir / 'package.json').write_text(json.dumps({
            "name": "my-pkg",
            "version": "1.0.0"
        }))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        assert modules[0]['name'] == 'my-pkg'


# =============================================================================
# Test: Paths structure (replaces descriptors)
# =============================================================================

def test_paths_structure():
    """Test that paths has correct structure."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        (ctx.temp_dir / 'README.md').write_text('# Test')  # Create README

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        paths = modules[0]['paths']
        # Required fields per spec (readme only present when exists)
        assert 'module' in paths
        assert 'descriptor' in paths
        assert 'sources' in paths
        assert 'tests' in paths
        assert paths['readme'] == 'README.md'  # Present because we created it
        # Values
        assert paths['descriptor'] == 'package.json'
        assert paths['module'] == '.'


# =============================================================================
# Test: Packages (object, not array)
# =============================================================================

def test_packages_is_object():
    """Test that packages is an object, not an array."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # packages should be {} (object), not [] (array)
        assert isinstance(modules[0]['packages'], dict)


def test_packages_from_exports():
    """Test package discovery from exports field."""
    with BuildTestContext() as ctx:
        pkg = {
            "name": "my-lib",
            "exports": {
                ".": "./dist/index.js",
                "./utils": "./dist/utils.js",
                "./helpers": "./dist/helpers.js"
            }
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        packages = modules[0]['packages']
        assert 'utils' in packages
        assert 'helpers' in packages
        # Should include exports key
        assert packages['utils'].get('exports') == './utils'


def test_packages_from_directories():
    """Test package discovery from src subdirectories."""
    with BuildTestContext() as ctx:
        (ctx.temp_dir / 'package.json').write_text('{"name": "test"}')
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'components').mkdir()
        (src_dir / 'hooks').mkdir()

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        packages = modules[0]['packages']
        assert 'components' in packages
        assert 'hooks' in packages
        assert packages['components']['path'] == 'src/components'


# =============================================================================
# Test: Commands
# =============================================================================

def test_commands_from_scripts():
    """Test command generation from package.json scripts."""
    with BuildTestContext() as ctx:
        pkg = {
            "name": "test",
            "scripts": {
                "build": "tsc",
                "test": "jest",
                "lint": "eslint src/"
            }
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        commands = modules[0]['commands']
        assert 'compile' in commands  # from build script
        assert 'module-tests' in commands  # from test script
        assert 'quality-gate' in commands  # from lint script
        assert 'verify' in commands  # combined build + test


def test_commands_minimal():
    """Test commands with minimal scripts."""
    with BuildTestContext() as ctx:
        pkg = {
            "name": "test",
            "scripts": {
                "test": "jest"
            }
        }
        (ctx.temp_dir / 'package.json').write_text(json.dumps(pkg))

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        commands = modules[0]['commands']
        assert 'module-tests' in commands
        assert 'verify' in commands  # test-only verify
        assert 'compile' not in commands  # no build script


# =============================================================================
# Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Basic module discovery
        test_discover_modules_single_module,
        test_discover_modules_with_workspaces,
        test_discover_modules_no_package_json,

        # Metadata extraction
        test_metadata_extraction,

        # Dependency extraction
        test_extract_dependencies,

        # Source directory discovery
        test_discover_sources_src,
        test_discover_sources_test,
        test_discover_sources_no_resources_in_paths,

        # Stats
        test_stats_file_counts,
        test_readme_in_paths,
        test_no_readme_in_paths,

        # build_systems field
        test_build_systems_is_array,

        # Workspaces object format
        test_workspaces_object_format,

        # Paths structure
        test_paths_structure,

        # Packages
        test_packages_is_object,
        test_packages_from_exports,
        test_packages_from_directories,

        # Commands
        test_commands_from_scripts,
        test_commands_minimal,
    ])
    sys.exit(runner.run())
