#!/usr/bin/env python3
"""Tests for modules command in plan-marshall-config.

Tests modules command with new architecture:
- Module facts come from raw-project-data.json
- Command configuration uses module_config in marshal.json
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH, create_marshal_json


# =============================================================================
# modules Command Tests
# =============================================================================

def test_modules_list():
    """Test modules list reads from raw-project-data.json."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'modules', 'list')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'my-core' in result.stdout
        assert 'my-ui' in result.stdout


def test_modules_get():
    """Test modules get combines facts from raw-project-data with commands from module_config."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'modules', 'get', '--module', 'my-core')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'maven' in result.stdout.lower()  # build_systems from raw-project-data


def test_modules_get_build_systems():
    """Test modules get-build-systems reads from raw-project-data.json."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'modules', 'get-build-systems', '--module', 'my-ui')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'maven' in result.stdout.lower()
        assert 'npm' in result.stdout.lower()


def test_modules_get_command_from_default():
    """Test modules get-command falls back to default module_config."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'modules', 'get-command',
            '--module', 'my-core',
            '--label', 'verify'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'clean verify' in result.stdout
        assert 'default' in result.stdout  # source: default


def test_modules_get_command_from_module():
    """Test modules get-command returns module-specific command."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'modules', 'get-command',
            '--module', 'my-ui',
            '--label', 'test'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'npm' in result.stdout  # Contains npm in the command
        assert 'module' in result.stdout  # source: module


def test_modules_list_commands():
    """Test modules list-commands shows all available commands."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'modules', 'list-commands',
            '--module', 'my-ui'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'test' in result.stdout
        assert 'build' in result.stdout
        # Should also include default commands
        assert 'verify' in result.stdout


def test_modules_set_command():
    """Test modules set-command sets command in module_config."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'modules', 'set-command',
            '--module', 'my-core',
            '--label', 'custom',
            '--command', 'python3 .plan/execute-script.py plan-marshall:build-operations:maven run --targets "custom"'
        )

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify the command was set
        verify = run_script(
            SCRIPT_PATH, 'modules', 'get-command',
            '--module', 'my-core',
            '--label', 'custom'
        )
        assert 'custom' in verify.stdout
        assert 'module' in verify.stdout  # source: module


def test_modules_set_default_command():
    """Test modules set-default-command sets command for all modules."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'modules', 'set-default-command',
            '--label', 'new-default',
            '--command', 'echo "default command"'
        )

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify any module can use this default
        verify = run_script(
            SCRIPT_PATH, 'modules', 'get-command',
            '--module', 'my-core',
            '--label', 'new-default'
        )
        assert 'default command' in verify.stdout


def test_modules_get_unknown_module():
    """Test modules get with unknown module returns error."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'modules', 'get', '--module', 'nonexistent')

        assert 'error' in result.stdout.lower(), "Should report error"


def test_modules_infer_domains():
    """Test modules infer-domains populates domains from build_systems."""
    with PlanTestContext() as ctx:
        # Create marshal with module_config but no domains
        config = {
            "skill_domains": {"java": {"defaults": []}},
            "module_config": {}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        # Create raw-project-data.json with modules
        raw_data = {
            "project": {"name": "test"},
            "modules": [
                {"name": "java-module", "path": "java-module", "build_systems": ["maven"], "packaging": "jar"},
                {"name": "frontend-module", "path": "frontend", "build_systems": ["npm"], "packaging": None},
                {"name": "hybrid-module", "path": "hybrid", "build_systems": ["maven", "npm"], "packaging": "war"}
            ]
        }
        raw_data_path = ctx.fixture_dir / 'raw-project-data.json'
        raw_data_path.write_text(json.dumps(raw_data, indent=2))

        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'updated' in result.stdout
        assert 'java-module' in result.stdout
        assert 'frontend-module' in result.stdout
        assert 'hybrid-module' in result.stdout


def test_modules_infer_domains_skips_existing():
    """Test modules infer-domains skips modules with existing domains."""
    with PlanTestContext() as ctx:
        # Create marshal with module_config having existing domains
        config = {
            "skill_domains": {"java": {"defaults": []}},
            "module_config": {
                "has-domains": {"domains": ["java"]}
            }
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        # Create raw-project-data.json
        raw_data = {
            "project": {"name": "test"},
            "modules": [
                {"name": "has-domains", "path": "has-domains", "build_systems": ["maven"], "packaging": "jar"},
                {"name": "no-domains", "path": "no-domains", "build_systems": ["maven"], "packaging": "jar"}
            ]
        }
        raw_data_path = ctx.fixture_dir / 'raw-project-data.json'
        raw_data_path.write_text(json.dumps(raw_data, indent=2))

        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'skipped' in result.stdout
        assert 'has-domains' in result.stdout  # Should be in skipped


def test_modules_infer_domains_force():
    """Test modules infer-domains --force overwrites existing domains."""
    with PlanTestContext() as ctx:
        # Create marshal with module that already has domains
        config = {
            "skill_domains": {"java": {"defaults": []}},
            "module_config": {
                "has-domains": {"domains": ["old-domain"]}
            }
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        # Create raw-project-data.json
        raw_data = {
            "project": {"name": "test"},
            "modules": [
                {"name": "has-domains", "path": "has-domains", "build_systems": ["maven"], "packaging": "jar"}
            ]
        }
        raw_data_path = ctx.fixture_dir / 'raw-project-data.json'
        raw_data_path.write_text(json.dumps(raw_data, indent=2))

        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains', '--force')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'updated' in result.stdout
        assert 'has-domains' in result.stdout  # Should be in updated, not skipped


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_modules_list,
        test_modules_get,
        test_modules_get_build_systems,
        test_modules_get_command_from_default,
        test_modules_get_command_from_module,
        test_modules_list_commands,
        test_modules_set_command,
        test_modules_set_default_command,
        test_modules_get_unknown_module,
        test_modules_infer_domains,
        test_modules_infer_domains_skips_existing,
        test_modules_infer_domains_force,
    ])
    sys.exit(runner.run())
