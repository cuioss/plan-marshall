#!/usr/bin/env python3
"""Tests for command resolution in config_core.py.

Tests the get_module_command() and list_module_commands() functions
that resolve commands from module_config with fallback chain.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner

# Set up PLAN_BASE_DIR for tests BEFORE importing config_core
temp_dir = tempfile.mkdtemp()
os.environ['PLAN_BASE_DIR'] = temp_dir

# Import functions under test (PYTHONPATH set by conftest)
from _config_core import (
    get_module_command,
    list_module_commands,
    get_modules,
    get_module_by_name,
    load_raw_project_data,
    save_config,
    PLAN_BASE_DIR,
    MARSHAL_PATH,
    RAW_PROJECT_DATA_PATH,
)


def setup_marshal_config(config: dict):
    """Helper to write marshal.json for tests."""
    MARSHAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARSHAL_PATH.write_text(json.dumps(config, indent=2))


def setup_raw_project_data(data: dict):
    """Helper to write raw-project-data.json for tests."""
    RAW_PROJECT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PROJECT_DATA_PATH.write_text(json.dumps(data, indent=2))


def cleanup():
    """Remove test files."""
    if MARSHAL_PATH.exists():
        MARSHAL_PATH.unlink()
    if RAW_PROJECT_DATA_PATH.exists():
        RAW_PROJECT_DATA_PATH.unlink()


# ===========================================================================
# Test: get_module_command() - Default Fallback
# ===========================================================================

def test_get_module_command_default_fallback():
    """Test that default commands are used when module has no specific command."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "module-tests": "mvn -pl ${module} test",
                    "verify": "mvn -pl ${module} verify"
                }
            }
        }
    })

    result = get_module_command("my-module", "module-tests")

    assert result is not None, "Expected command result"
    assert result['command'] == "mvn -pl my-module test", f"Got: {result['command']}"
    assert result['source'] == "default"
    assert result['module'] == "my-module"
    assert result['label'] == "module-tests"

    cleanup()


def test_get_module_command_module_override():
    """Test that module-specific commands override defaults."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "module-tests": "mvn -pl ${module} test"
                }
            },
            "special-module": {
                "commands": {
                    "module-tests": "mvn -pl ${module} test -Pspecial"
                }
            }
        }
    })

    # Module-specific should be used
    result = get_module_command("special-module", "module-tests")
    assert result['source'] == "module"
    assert "-Pspecial" in result['command']

    # Other modules should use default
    result = get_module_command("other-module", "module-tests")
    assert result['source'] == "default"
    assert "-Pspecial" not in result['command']

    cleanup()


def test_get_module_command_not_found():
    """Test that None is returned when command not found."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "module-tests": "mvn test"
                }
            }
        }
    })

    result = get_module_command("my-module", "nonexistent-command")
    assert result is None, "Expected None for nonexistent command"

    cleanup()


def test_get_module_command_placeholder_substitution():
    """Test ${module} placeholder is substituted correctly."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"verify\" --module ${module}"
                }
            }
        }
    })

    result = get_module_command("oauth-sheriff-core", "verify")

    assert "${module}" not in result['command'], "Placeholder should be substituted"
    assert "--module oauth-sheriff-core" in result['command']

    cleanup()


# ===========================================================================
# Test: get_module_command() - Hybrid Modules
# ===========================================================================

def test_get_module_command_hybrid_specific_build_system():
    """Test hybrid module with specific build_system filter."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "nifi-cuioss-ui": {
                "commands": {
                    "module-tests": {
                        "maven": "mvn -pl ${module} test",
                        "npm": "npm --prefix ${module} test"
                    }
                }
            }
        }
    })

    # Request Maven command
    result = get_module_command("nifi-cuioss-ui", "module-tests", build_system="maven")
    assert result is not None
    assert "mvn" in result['command']
    assert result['build_system'] == "maven"

    # Request npm command
    result = get_module_command("nifi-cuioss-ui", "module-tests", build_system="npm")
    assert result is not None
    assert "npm" in result['command']
    assert result['build_system'] == "npm"

    cleanup()


def test_get_module_command_hybrid_no_filter():
    """Test hybrid module without build_system filter returns all."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "hybrid-module": {
                "commands": {
                    "module-tests": {
                        "maven": "mvn test",
                        "npm": "npm test"
                    }
                }
            }
        }
    })

    result = get_module_command("hybrid-module", "module-tests")

    assert result is not None
    assert result.get('multi_build_system') is True
    assert 'commands' in result
    assert 'maven' in result['commands']
    assert 'npm' in result['commands']

    cleanup()


def test_get_module_command_hybrid_unavailable_build_system():
    """Test hybrid module returns None for unavailable build_system."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "maven-only": {
                "commands": {
                    "module-tests": {
                        "maven": "mvn test"
                    }
                }
            }
        }
    })

    result = get_module_command("maven-only", "module-tests", build_system="npm")
    assert result is None, "Expected None for unavailable build_system"

    cleanup()


# ===========================================================================
# Test: list_module_commands()
# ===========================================================================

def test_list_module_commands_default_only():
    """Test listing commands with only defaults."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "module-tests": "mvn test",
                    "verify": "mvn verify",
                    "quality-gate": "mvn verify -Ppre-commit"
                }
            }
        }
    })

    result = list_module_commands("any-module")

    assert result['module'] == "any-module"
    assert set(result['commands']) == {"module-tests", "verify", "quality-gate"}

    cleanup()


def test_list_module_commands_with_overrides():
    """Test listing commands merges defaults with overrides."""
    cleanup()
    setup_marshal_config({
        "module_config": {
            "default": {
                "commands": {
                    "module-tests": "mvn test",
                    "verify": "mvn verify"
                }
            },
            "special": {
                "commands": {
                    "integration-tests": "mvn verify -Pintegration"
                }
            }
        }
    })

    result = list_module_commands("special")

    # Should have both default and module-specific
    assert "module-tests" in result['commands']
    assert "verify" in result['commands']
    assert "integration-tests" in result['commands']

    cleanup()


# ===========================================================================
# Test: get_modules() from raw-project-data.json
# ===========================================================================

def test_get_modules_from_raw_data():
    """Test getting module list from raw-project-data.json."""
    cleanup()
    setup_raw_project_data({
        "project": {"name": "test"},
        "modules": [
            {"name": "module-a", "path": "module-a", "build_systems": ["maven"]},
            {"name": "module-b", "path": "module-b", "build_systems": ["npm"]}
        ]
    })

    modules = get_modules()

    assert len(modules) == 2
    assert modules[0]['name'] == "module-a"
    assert modules[1]['name'] == "module-b"

    cleanup()


def test_get_modules_no_file():
    """Test get_modules returns empty list when file doesn't exist."""
    cleanup()

    modules = get_modules()

    assert modules == []


def test_get_module_by_name_found():
    """Test getting specific module by name."""
    cleanup()
    setup_raw_project_data({
        "modules": [
            {"name": "module-a", "path": "module-a", "build_systems": ["maven"]},
            {"name": "module-b", "path": "nested/module-b", "build_systems": ["maven", "npm"]}
        ]
    })

    module = get_module_by_name("module-b")

    assert module is not None
    assert module['path'] == "nested/module-b"
    assert "npm" in module['build_systems']

    cleanup()


def test_get_module_by_name_not_found():
    """Test get_module_by_name returns None for unknown module."""
    cleanup()
    setup_raw_project_data({
        "modules": [
            {"name": "module-a", "path": "module-a", "build_systems": ["maven"]}
        ]
    })

    module = get_module_by_name("nonexistent")

    assert module is None

    cleanup()


# ===========================================================================
# Test: Empty/Missing Configuration
# ===========================================================================

def test_get_module_command_no_module_config():
    """Test command resolution with no module_config section."""
    cleanup()
    setup_marshal_config({
        "plan": {"defaults": {}}
    })

    result = get_module_command("my-module", "module-tests")
    assert result is None

    cleanup()


def test_list_module_commands_empty():
    """Test listing commands with no module_config."""
    cleanup()
    setup_marshal_config({})

    result = list_module_commands("any-module")

    assert result['commands'] == []

    cleanup()


# ===========================================================================
# Main
# ===========================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Default fallback tests
        test_get_module_command_default_fallback,
        test_get_module_command_module_override,
        test_get_module_command_not_found,
        test_get_module_command_placeholder_substitution,
        # Hybrid module tests
        test_get_module_command_hybrid_specific_build_system,
        test_get_module_command_hybrid_no_filter,
        test_get_module_command_hybrid_unavailable_build_system,
        # list_module_commands tests
        test_list_module_commands_default_only,
        test_list_module_commands_with_overrides,
        # get_modules tests
        test_get_modules_from_raw_data,
        test_get_modules_no_file,
        test_get_module_by_name_found,
        test_get_module_by_name_not_found,
        # Edge cases
        test_get_module_command_no_module_config,
        test_list_module_commands_empty,
    ])
    sys.exit(runner.run())
