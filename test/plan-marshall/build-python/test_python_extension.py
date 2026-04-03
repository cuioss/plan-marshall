#!/usr/bin/env python3
"""Tests for plan-marshall extension.py (Python discovery).

Tests the Python domain extension including:
- get_skill_domains() - Domain metadata
- discover_modules() - Delegated to _python_cmd_discover.discover_python_modules()

Note: The extension.py delegates to build-python/scripts/_python_cmd_discover.py
which discovers modules based on directory structure (test/ or tests/ subdirs),
not pyprojectx alias detection.
"""

import importlib.util
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import BuildContext

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_python_extension():
    """Load Python Extension class avoiding conflicts."""
    spec = importlib.util.spec_from_file_location('python_extension', EXTENSION_FILE)
    python_ext = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(python_ext)
    return python_ext.Extension


Extension = _load_python_extension()


# =============================================================================
# Test: get_skill_domains()
# =============================================================================


def test_get_skill_domains_returns_expected_structure():
    """get_skill_domains() returns domain metadata for build domain."""
    ext = Extension()
    all_domains = ext.get_skill_domains()

    # Returns list of domains (build + general-dev)
    assert isinstance(all_domains, list)
    assert len(all_domains) >= 1

    # Check first domain (build)
    domains = all_domains[0]
    assert 'domain' in domains
    assert domains['domain']['key'] == 'build'
    assert domains['domain']['name'] == 'Build Systems'

    # Check profiles (build domain has empty profiles - domain bundles handle skill profiles)
    assert 'profiles' in domains


# =============================================================================
# Test: discover_modules() - No pyproject.toml
# =============================================================================


def test_discover_modules_returns_empty_when_no_pyproject():
    """discover_modules() returns [] when no pyproject.toml exists."""
    with BuildContext() as ctx:
        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))
        assert modules == []


# =============================================================================
# Test: discover_modules() - pyproject.toml without test dirs
# =============================================================================


def test_discover_modules_returns_empty_when_no_test_dirs():
    """discover_modules() returns [] when pyproject.toml exists but no test directories."""
    with BuildContext() as ctx:
        # Create pyproject.toml
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "my-project"
version = "1.0.0"
""")

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))
        assert modules == []


# =============================================================================
# Test: discover_modules() - Complete setup
# =============================================================================


def test_discover_modules_returns_module_with_complete_setup():
    """discover_modules() returns module when pyproject.toml and test dir exist.

    Delegated discovery detects modules by the presence of test/ or tests/
    subdirectories under the project root.
    """
    with BuildContext() as ctx:
        # Create pyproject.toml
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "my-project"
version = "1.0.0"
""")

        # Create test directory (triggers module detection)
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        # Create source directory
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'main.py').write_text('print("hello")')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        module = modules[0]

        # Check module structure
        assert module['name'] == 'default'
        assert module['build_systems'] == ['python']
        assert module['paths']['module'] == '.'
        assert module['paths']['descriptor'] == 'pyproject.toml'

        # Check commands (delegated discovery generates from module structure)
        commands = module['commands']
        assert 'verify' in commands
        assert 'quality-gate' in commands

        # Check command format
        assert (
            'python3 .plan/execute-script.py plan-marshall:build-python:python_build run' in commands['verify']
        )


def test_discover_modules_maps_only_existing_aliases():
    """discover_modules() generates commands based on module structure.

    Delegated discovery generates standard commands (verify, quality-gate, etc.)
    for all discovered modules, regardless of pyprojectx aliases.
    """
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "minimal-project"
version = "1.0.0"
""")

        # Create test dir to trigger discovery
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        commands = modules[0]['commands']

        # Delegated discovery always generates verify, quality-gate, compile, clean
        assert 'verify' in commands
        assert 'quality-gate' in commands


# =============================================================================
# Test: Source/Test Directory Discovery
# =============================================================================


def test_discover_modules_finds_source_directories():
    """discover_modules() detects source directories."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "test-project"
""")

        # Create source directory
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'main.py').write_text('print("hello")')

        # Create test directory (required for module detection)
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        paths = modules[0]['paths']
        sources = paths.get('sources') or []
        assert 'src' in sources


def test_discover_modules_finds_test_directories():
    """discover_modules() detects test directories."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "test-project"
""")

        # Create test directory
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        paths = modules[0]['paths']
        tests = paths.get('tests') or []
        assert 'test' in tests


def test_discover_modules_counts_python_files():
    """discover_modules() counts Python files in stats."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "test-project"
""")

        # Create source files
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'main.py').write_text('print("hello")')
        (src_dir / 'utils.py').write_text('print("utils")')

        # Create test files
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        stats = modules[0]['stats']
        assert stats['source_files'] == 2
        assert stats['test_files'] == 1


def test_discover_modules_finds_readme():
    """discover_modules() detects README.md."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "test-project"
""")

        # Create test dir and README
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')
        (ctx.temp_dir / 'README.md').write_text('# My Project')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        paths = modules[0]['paths']
        assert paths.get('readme') == 'README.md'


# =============================================================================
# Test: Mutual Exclusivity with pm-plugin-development
# =============================================================================


def test_discover_modules_works_for_plan_marshall_marketplace():
    """discover_modules() returns Python module for plan-marshall marketplace."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "plan-marshall"
""")

        # Create test dir (triggers module detection)
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        # Create marketplace.json
        marketplace_dir = ctx.temp_dir / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        (marketplace_dir / 'marketplace.json').write_text('{"name": "plan-marshall", "version": "1.0.0"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Should return Python root module
        assert len(modules) >= 1
        assert modules[0]['name'] == 'default'
        assert modules[0]['build_systems'] == ['python']


def test_discover_modules_handles_other_marketplaces():
    """discover_modules() works for non-plan-marshall marketplaces."""
    with BuildContext() as ctx:
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text("""
[project]
name = "other-project"
""")

        # Create test dir
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        # Create marketplace.json with different name
        marketplace_dir = ctx.temp_dir / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        (marketplace_dir / 'marketplace.json').write_text('{"name": "other-marketplace", "version": "1.0.0"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) >= 1
        assert modules[0]['name'] == 'default'
