#!/usr/bin/env python3
"""Tests for pm-dev-python extension.py.

Tests the Python domain extension including:
- get_skill_domains() - Domain metadata
- discover_modules() - Runtime discovery from pyproject.toml
- _discover_aliases() - Alias parsing from pyproject.toml
- _map_to_canonical() - Command mapping
"""

import importlib.util
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import BuildContext

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-dev-python' / 'skills' / 'plan-marshall-plugin' / 'scripts' / 'extension.py'
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
    """get_skill_domains() returns domain metadata with profiles."""
    ext = Extension()
    domains = ext.get_skill_domains()

    # Check domain key
    assert 'domain' in domains
    assert domains['domain']['key'] == 'python'
    assert domains['domain']['name'] == 'Python Development'

    # Check profiles
    assert 'profiles' in domains
    profiles = domains['profiles']
    assert 'core' in profiles
    assert 'implementation' in profiles
    assert 'module_testing' in profiles
    assert 'quality' in profiles

    # Check core profile has default skill
    assert 'pm-dev-python:python-best-practices' in profiles['core']['defaults']


def test_provides_triage_returns_none():
    """provides_triage() returns None (no triage skill yet)."""
    ext = Extension()
    assert ext.provides_triage() is None


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
# Test: discover_modules() - pyproject.toml without pyprojectx
# =============================================================================


def test_discover_modules_returns_empty_when_no_pyprojectx():
    """discover_modules() returns [] when pyproject.toml has no pyprojectx section."""
    with BuildContext() as ctx:
        # Create pyproject.toml without pyprojectx section
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[project]
name = "my-project"
version = "1.0.0"
''')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))
        assert modules == []


# =============================================================================
# Test: discover_modules() - No wrapper
# =============================================================================


def test_discover_modules_returns_empty_when_no_wrapper():
    """discover_modules() returns [] when pyproject.toml exists but no ./pw wrapper."""
    with BuildContext() as ctx:
        # Create pyproject.toml with pyprojectx section but no ./pw wrapper
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[project]
name = "my-project"
version = "1.0.0"

[tool.pyprojectx.aliases]
verify = "echo verify"
''')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))
        assert modules == []


# =============================================================================
# Test: discover_modules() - Complete setup
# =============================================================================


def test_discover_modules_returns_module_with_complete_setup():
    """discover_modules() returns module when pyproject.toml and ./pw exist."""
    with BuildContext() as ctx:
        # Create pyproject.toml with pyprojectx section
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[project]
name = "my-project"
version = "1.0.0"

[tool.pyprojectx.aliases]
compile = "uv run python build.py compile"
module-tests = "uv run python build.py module-tests"
quality-gate = "uv run python build.py quality-gate"
verify = "uv run python build.py verify"
''')

        # Create ./pw wrapper (just needs to exist)
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\necho "pw wrapper"')
        pw.chmod(0o755)

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        module = modules[0]

        # Check module structure
        assert module['name'] == '.'
        assert module['build_systems'] == ['python']
        assert module['paths']['module'] == '.'
        assert module['paths']['descriptor'] == 'pyproject.toml'
        assert module['metadata']['build_tool'] == 'pyprojectx'
        assert module['metadata']['package_manager'] == 'uv'

        # Check commands
        commands = module['commands']
        assert 'compile' in commands
        assert 'module-tests' in commands
        assert 'quality-gate' in commands
        assert 'verify' in commands

        # Check command format
        assert 'python3 .plan/execute-script.py pm-dev-python:plan-marshall-plugin:python_build run' in commands['verify']


def test_discover_modules_maps_only_existing_aliases():
    """discover_modules() only maps aliases that exist in pyproject.toml."""
    with BuildContext() as ctx:
        # Create pyproject.toml with only some aliases
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[project]
name = "minimal-project"
version = "1.0.0"

[tool.pyprojectx.aliases]
verify = "echo verify"
clean = "rm -rf build"
''')

        # Create ./pw wrapper
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\necho "pw"')
        pw.chmod(0o755)

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        commands = modules[0]['commands']

        # Should have verify and clean
        assert 'verify' in commands
        assert 'clean' in commands

        # Should NOT have other commands
        assert 'compile' not in commands
        assert 'module-tests' not in commands
        assert 'quality-gate' not in commands


# =============================================================================
# Test: Source/Test Directory Discovery
# =============================================================================


def test_discover_modules_finds_source_directories():
    """discover_modules() detects source directories."""
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

        # Create source directories
        src_dir = ctx.temp_dir / 'src'
        src_dir.mkdir()
        (src_dir / 'main.py').write_text('print("hello")')

        marketplace_dir = ctx.temp_dir / 'marketplace' / 'bundles'
        marketplace_dir.mkdir(parents=True)
        (marketplace_dir / 'test.py').write_text('print("test")')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        paths = modules[0]['paths']
        assert 'src' in paths['sources']
        assert 'marketplace/bundles' in paths['sources']


def test_discover_modules_finds_test_directories():
    """discover_modules() detects test directories."""
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

        # Create test directory
        test_dir = ctx.temp_dir / 'test'
        test_dir.mkdir()
        (test_dir / 'test_main.py').write_text('def test_foo(): pass')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        paths = modules[0]['paths']
        assert 'test' in paths['tests']


def test_discover_modules_counts_python_files():
    """discover_modules() counts Python files in stats."""
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

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

        assert len(modules) == 1
        stats = modules[0]['stats']
        assert stats['source_files'] == 2
        assert stats['test_files'] == 1


def test_discover_modules_finds_readme():
    """discover_modules() detects README.md."""
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

        # Create README
        readme = ctx.temp_dir / 'README.md'
        readme.write_text('# My Project')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        assert len(modules) == 1
        paths = modules[0]['paths']
        assert paths.get('readme') == 'README.md'


# =============================================================================
# Test: Mutual Exclusivity with pm-plugin-development
# =============================================================================


def test_discover_modules_skips_plan_marshall_marketplace():
    """discover_modules() returns [] for plan-marshall marketplace.

    The plan-marshall marketplace is handled by pm-plugin-development,
    so pm-dev-python should skip it to avoid duplicate modules.
    """
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper (valid Python project)
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

        # Create marketplace.json with name=plan-marshall
        marketplace_dir = ctx.temp_dir / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        marketplace_json = marketplace_dir / 'marketplace.json'
        marketplace_json.write_text('{"name": "plan-marshall", "version": "1.0.0"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Should return empty - handled by pm-plugin-development
        assert modules == []


def test_discover_modules_handles_other_marketplaces():
    """discover_modules() works for non-plan-marshall marketplaces.

    Other code marketplaces with different names should be handled by pm-dev-python.
    """
    with BuildContext() as ctx:
        # Create pyproject.toml and wrapper (valid Python project)
        pyproject = ctx.temp_dir / 'pyproject.toml'
        pyproject.write_text('''
[tool.pyprojectx.aliases]
verify = "echo verify"
''')
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash')
        pw.chmod(0o755)

        # Create marketplace.json with different name
        marketplace_dir = ctx.temp_dir / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        marketplace_json = marketplace_dir / 'marketplace.json'
        marketplace_json.write_text('{"name": "other-marketplace", "version": "1.0.0"}')

        ext = Extension()
        modules = ext.discover_modules(str(ctx.temp_dir))

        # Should return module - NOT plan-marshall
        assert len(modules) == 1
        assert modules[0]['name'] == '.'
