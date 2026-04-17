#!/usr/bin/env python3
"""Unit tests for inject_project_dir helper.

Covers the library function `inject_project_dir(command, worktree_path)` and
the CLI entrypoint exposed by `inject_project_dir.py`. The helper forwards
`--project-dir` to Bucket B executor invocations while leaving Bucket A
`manage-*` notations, non-executor commands, and already-flagged commands
untouched.
"""

from pathlib import Path

import pytest

# Cross-skill imports — PYTHONPATH is configured by the root test/conftest.py
# which adds every marketplace scripts/ directory, including
# marketplace/bundles/plan-marshall/skills/execute-task/scripts.
from inject_project_dir import inject_project_dir  # noqa: E402

from conftest import run_script  # noqa: E402

# Path to the script for CLI subprocess tests
SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
    / 'execute-task' / 'scripts' / 'inject_project_dir.py'
)

# Worktree path used across tests
WORKTREE = '/Users/test/worktrees/demo'

# The 8 Bucket B notations whitelisted by the helper
BUCKET_B_NOTATIONS = [
    'plan-marshall:build-maven:maven',
    'plan-marshall:build-gradle:gradle',
    'plan-marshall:build-npm:npm',
    'plan-marshall:build-python:python_build',
    'plan-marshall:tools-integration-ci:ci',
    'plan-marshall:workflow-integration-git:git',
    'plan-marshall:workflow-integration-sonar:sonar',
    'plan-marshall:workflow-pr-doctor:pr-doctor',
]

# Bucket A manage-* notations that MUST pass through unchanged
BUCKET_A_NOTATIONS = [
    'plan-marshall:manage-tasks:manage-tasks',
    'plan-marshall:manage-files:manage-files',
    'plan-marshall:manage-config:manage-config',
    'plan-marshall:manage-logging:manage-logging',
]


# =============================================================================
# (a) Injection for each Bucket B notation
# =============================================================================


@pytest.mark.parametrize('notation', BUCKET_B_NOTATIONS)
def test_injects_project_dir_for_each_bucket_b_notation(notation):
    """Bucket B notation without --project-dir gets the flag injected after run."""
    # Arrange
    command = (
        f'python3 .plan/execute-script.py {notation} run '
        f'--command-args "verify"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is True
    # --project-dir must appear immediately after `run` and before other args
    assert f'{notation} run --project-dir {WORKTREE} --command-args verify' in rewritten
    # Original command-args payload must survive
    assert 'verify' in rewritten


# =============================================================================
# (b) No double-injection when --project-dir already present
# =============================================================================


def test_no_double_injection_when_project_dir_already_present():
    """A command that already carries --project-dir is returned unchanged."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        f'run --project-dir {WORKTREE} --command-args "module-tests"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


def test_no_double_injection_with_different_project_dir_value():
    """An existing --project-dir is preserved, even if it points elsewhere."""
    # Arrange — existing flag points at a different path
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-maven:maven '
        'run --project-dir /some/other/path --command-args "verify"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert — helper must not override or duplicate the existing flag
    assert injected is False
    assert rewritten == command
    # Sanity: worktree path we offered is NOT inserted
    assert WORKTREE not in rewritten


# =============================================================================
# (c) Bucket A manage-* pass-through
# =============================================================================


@pytest.mark.parametrize('notation', BUCKET_A_NOTATIONS)
def test_bucket_a_manage_commands_pass_through(notation):
    """Bucket A manage-* notations MUST NOT receive --project-dir."""
    # Arrange
    command = (
        f'python3 .plan/execute-script.py {notation} list '
        '--plan-id my-plan'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command
    assert '--project-dir' not in rewritten


# =============================================================================
# (f) Unknown/non-whitelisted notations pass through unchanged
# =============================================================================


def test_unknown_notation_passes_through():
    """A notation not in the Bucket B whitelist is returned unchanged."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:some-future-script:thing '
        'run --command-args "foo"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


def test_unknown_bundle_notation_passes_through():
    """A non-plan-marshall notation is returned unchanged."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py pm-dev-java:java-core:compile '
        'run --command-args "compile"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


# =============================================================================
# (g) Non-executor commands pass through unchanged
# =============================================================================


@pytest.mark.parametrize(
    'command',
    [
        './pw verify',
        'npm install',
        'git status',
        'mvn clean verify',
        'pytest test/plan-marshall',
        'ls -la',
    ],
)
def test_non_executor_commands_pass_through(command):
    """Raw build tools, git, and other non-executor commands pass through."""
    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


# =============================================================================
# (6) Original --command-args payload preserved verbatim
# =============================================================================


def test_command_args_payload_preserved_on_injection():
    """The payload after --command-args must survive injection untouched."""
    # Arrange — multi-token payload with spaces
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        'run --command-args "module-tests plan-marshall"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is True
    # The payload value should appear as a single quoted token after shlex.join
    assert "'module-tests plan-marshall'" in rewritten or 'module-tests plan-marshall' in rewritten
    # Order: notation -> run -> --project-dir <worktree> -> --command-args <payload>
    run_idx = rewritten.index(' run ')
    project_dir_idx = rewritten.index('--project-dir')
    command_args_idx = rewritten.index('--command-args')
    assert run_idx < project_dir_idx < command_args_idx


def test_command_args_passthrough_preserved_verbatim():
    """On pass-through (Bucket A), the command string is byte-identical."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks '
        'get --plan-id foo --number 3'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert — exact string equality on pass-through
    assert injected is False
    assert rewritten == command


# =============================================================================
# (7) Empty / malformed commands
# =============================================================================


def test_empty_command_returns_false():
    """Empty command string returns (command, False) without raising."""
    # Act
    rewritten, injected = inject_project_dir('', WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == ''


def test_whitespace_only_command_returns_false():
    """Whitespace-only command returns (command, False) without raising."""
    # Act
    rewritten, injected = inject_project_dir('   ', WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == '   '


def test_malformed_quoting_returns_false():
    """A command with unbalanced quotes passes through without raising."""
    # Arrange — unbalanced single quote trips shlex.split
    command = (
        "python3 .plan/execute-script.py plan-marshall:build-python:python_build "
        "run --command-args 'module-tests"
    )

    # Act — must NOT raise
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


def test_executor_without_notation_returns_false():
    """Executor invoked without a notation token passes through."""
    # Arrange — `.plan/execute-script.py` is the last token (no notation)
    command = 'python3 .plan/execute-script.py'

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert
    assert injected is False
    assert rewritten == command


def test_executor_with_notation_but_no_run_subcommand_passes_through():
    """Bucket B notation without `run` subcommand is not rewritten."""
    # Arrange — `help` instead of `run`
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        'help'
    )

    # Act
    rewritten, injected = inject_project_dir(command, WORKTREE)

    # Assert — out of scope for injection
    assert injected is False
    assert rewritten == command


# =============================================================================
# (8) CLI entrypoint integration
# =============================================================================


def test_cli_entrypoint_matches_library_output_on_injection(tmp_path):
    """CLI invocation via subprocess produces the same output as the library."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        'run --command-args "module-tests"'
    )
    expected, injected = inject_project_dir(command, WORKTREE)
    assert injected is True  # sanity — the scenario should trigger injection

    # Act — invoke the script as a subprocess (tmp_path used as isolated cwd)
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command', command,
        '--worktree-path', WORKTREE,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    assert result.stdout.strip() == expected.strip()


def test_cli_entrypoint_matches_library_output_on_passthrough(tmp_path):
    """CLI pass-through (Bucket A) matches library output byte-for-byte."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks '
        'get --plan-id my-plan --number 1'
    )
    expected, injected = inject_project_dir(command, WORKTREE)
    assert injected is False  # sanity — Bucket A must not trigger injection

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command', command,
        '--worktree-path', WORKTREE,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    assert result.stdout.strip() == expected.strip()


def test_cli_entrypoint_matches_library_output_on_non_executor(tmp_path):
    """CLI pass-through for non-executor commands matches the library."""
    # Arrange
    command = 'git status'
    expected, injected = inject_project_dir(command, WORKTREE)
    assert injected is False

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command', command,
        '--worktree-path', WORKTREE,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    assert result.stdout.strip() == expected.strip()
