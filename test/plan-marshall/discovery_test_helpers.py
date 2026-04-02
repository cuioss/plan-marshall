#!/usr/bin/env python3
"""Shared test helpers for plan-marshall build module discovery tests.

Provides common assertion functions for validating module discovery output
across all build systems (Maven, Gradle, npm, Python). Ensures consistent
contract compliance checking without duplicating assertions in each test file.

Usage (add test/plan-marshall/ to sys.path first):
    from discovery_test_helpers import assert_valid_module, assert_module_paths
"""


def assert_valid_module(module: dict, *, build_system: str, expected_name: str | None = None) -> None:
    """Assert a module dict has valid top-level structure.

    Validates required fields per module-discovery.md contract.

    Args:
        module: Module dict to validate.
        build_system: Expected build system (e.g., 'maven', 'gradle', 'npm', 'python').
        expected_name: If provided, asserts module name matches.
    """
    assert 'name' in module, 'Module missing required field: name'
    assert 'build_systems' in module, 'Module missing required field: build_systems'
    assert module['build_systems'] == [build_system], (
        f"Expected build_systems=['{build_system}'], got {module['build_systems']}"
    )

    if expected_name is not None:
        assert module['name'] == expected_name, (
            f"Expected name='{expected_name}', got '{module['name']}'"
        )

    # Error modules have minimal structure
    if 'error' in module:
        return

    assert 'paths' in module, 'Module missing required field: paths'
    assert 'commands' in module, 'Module missing required field: commands'
    assert 'stats' in module, 'Module missing required field: stats'


def assert_module_paths(
    module: dict,
    *,
    expected_module_path: str | None = None,
    expect_descriptor: bool = True,
    expect_readme: bool | None = None,
) -> None:
    """Assert module paths structure is valid.

    Args:
        module: Module dict to validate.
        expected_module_path: If provided, asserts paths.module matches.
        expect_descriptor: Whether descriptor path should be present.
        expect_readme: If True, asserts readme is not None; if False, asserts None.
    """
    paths = module.get('paths', {})
    assert 'module' in paths, 'Module paths missing required field: module'

    if expected_module_path is not None:
        assert paths['module'] == expected_module_path, (
            f"Expected paths.module='{expected_module_path}', got '{paths['module']}'"
        )

    if expect_descriptor:
        assert 'descriptor' in paths, 'Module paths missing required field: descriptor'
        assert paths['descriptor'] is not None, 'descriptor should not be None'

    if expect_readme is True:
        assert paths.get('readme') is not None, 'Expected readme to be present'
    elif expect_readme is False:
        assert paths.get('readme') is None, f"Expected no readme, got '{paths.get('readme')}'"


def assert_module_stats(module: dict, *, min_source_files: int = 0, min_test_files: int = 0) -> None:
    """Assert module stats structure is valid.

    Args:
        module: Module dict to validate.
        min_source_files: Minimum expected source file count.
        min_test_files: Minimum expected test file count.
    """
    stats = module.get('stats', {})
    assert 'source_files' in stats, 'Module stats missing: source_files'
    assert 'test_files' in stats, 'Module stats missing: test_files'
    assert stats['source_files'] >= min_source_files, (
        f"Expected at least {min_source_files} source files, got {stats['source_files']}"
    )
    assert stats['test_files'] >= min_test_files, (
        f"Expected at least {min_test_files} test files, got {stats['test_files']}"
    )


def assert_module_commands(module: dict, *, expected_commands: list[str] | None = None) -> None:
    """Assert module commands structure is valid.

    Args:
        module: Module dict to validate.
        expected_commands: If provided, asserts all listed commands are present.
    """
    commands = module.get('commands', {})
    assert isinstance(commands, dict), f'Expected commands to be dict, got {type(commands)}'

    if expected_commands:
        for cmd in expected_commands:
            assert cmd in commands, f"Expected command '{cmd}' not found in {list(commands.keys())}"


def assert_command_uses_executor(module: dict, command_name: str, *, skill_notation: str) -> None:
    """Assert a specific command uses the correct executor invocation.

    Validates that the command string follows the pattern:
        python3 .plan/execute-script.py {skill_notation} run --command-args "..."

    Args:
        module: Module dict to validate.
        command_name: Name of the canonical command to check.
        skill_notation: Expected three-part skill notation.
    """
    commands = module.get('commands', {})
    assert command_name in commands, f"Command '{command_name}' not found"
    cmd = commands[command_name]

    expected_prefix = f'python3 .plan/execute-script.py {skill_notation} run --command-args "'
    assert cmd.startswith(expected_prefix), (
        f"Command '{command_name}' doesn't use expected executor.\n"
        f"Expected prefix: {expected_prefix}\n"
        f"Got: {cmd[:len(expected_prefix) + 20]}..."
    )


def assert_canonical_commands_present(module: dict, build_system: str) -> None:
    """Assert standard canonical commands are present based on build system.

    All build systems should have at minimum: clean, verify.
    Non-pom modules should also have compile and module-tests.

    Args:
        module: Module dict to validate.
        build_system: Build system name for context in error messages.
    """
    commands = module.get('commands', {})

    # All build systems should have at least clean and verify
    for cmd in ['clean', 'verify']:
        if cmd not in commands:
            # Some systems (npm) only generate commands for existing scripts
            pass
