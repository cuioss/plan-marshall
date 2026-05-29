#!/usr/bin/env python3
"""Unit tests for inject_project_dir helper.

Covers the library function `inject_project_dir(command, plan_id)` and the CLI
entrypoint exposed by `inject_project_dir.py`. The helper forwards `--plan-id`
to Bucket B executor invocations — routing the executor's audit-log entry to
the plan-scoped `script-execution.log` and letting the Bucket B script
auto-resolve the worktree via its two-state contract — while leaving Bucket A
`manage-*` notations, non-executor commands, commands already carrying
`--plan-id`, and commands carrying a legacy explicit `--project-dir` untouched.
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
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'execute-task'
    / 'scripts'
    / 'inject_project_dir.py'
)

# Plan identifier used across tests
PLAN_ID = 'demo-plan-id'

# The 8 Bucket B notations whitelisted by the helper
BUCKET_B_NOTATIONS = [
    'plan-marshall:build-maven:maven',
    'plan-marshall:build-gradle:gradle',
    'plan-marshall:build-npm:npm',
    'plan-marshall:build-pyproject:pyproject_build',
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
def test_injects_plan_id_for_each_bucket_b_notation(notation):
    """Bucket B notation without --plan-id gets the flag injected after run."""
    # Arrange
    command = f'python3 .plan/execute-script.py {notation} run --command-args "verify"'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is True
    # --plan-id must appear immediately after `run` and before other args
    assert f'{notation} run --plan-id {PLAN_ID} --command-args verify' in rewritten
    # Original command-args payload must survive
    assert 'verify' in rewritten


# =============================================================================
# (b) No double-injection when --plan-id already present
# =============================================================================


def test_no_double_injection_when_plan_id_already_present():
    """A command that already carries --plan-id is returned unchanged."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        f'run --plan-id {PLAN_ID} --command-args "module-tests"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command


def test_no_double_injection_with_different_plan_id_value():
    """An existing --plan-id is preserved, even if it differs from the offered id."""
    # Arrange — existing flag points at a different plan id
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-maven:maven '
        'run --plan-id some-other-plan --command-args "verify"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert — helper must not override or duplicate the existing flag
    assert injected is False
    assert rewritten == command
    # Sanity: the plan id we offered is NOT inserted
    assert PLAN_ID not in rewritten


# =============================================================================
# (b2) Legacy explicit --project-dir override is respected (passed through)
# =============================================================================


def test_legacy_project_dir_override_passes_through():
    """A command carrying an explicit --project-dir is returned unchanged.

    The legacy explicit override is respected — the helper must not inject
    --plan-id on top of an existing --project-dir (the two are mutually
    exclusive on the target Bucket B script).
    """
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --project-dir /some/explicit/worktree --command-args "module-tests"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command
    # The offered plan id must NOT be inserted alongside the explicit override.
    assert PLAN_ID not in rewritten
    assert '--plan-id' not in rewritten


# =============================================================================
# (c) Bucket A manage-* pass-through
# =============================================================================


@pytest.mark.parametrize('notation', BUCKET_A_NOTATIONS)
def test_bucket_a_manage_commands_pass_through(notation):
    """Bucket A manage-* notations MUST NOT receive --plan-id injection."""
    # Arrange — distinct existing flag value so injection would be observable
    command = f'python3 .plan/execute-script.py {notation} list --plan-id existing-plan'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command
    # The offered plan id must not have been injected.
    assert PLAN_ID not in rewritten


# =============================================================================
# (f) Unknown/non-whitelisted notations pass through unchanged
# =============================================================================


def test_unknown_notation_passes_through():
    """A notation not in the Bucket B whitelist is returned unchanged."""
    # Arrange
    command = 'python3 .plan/execute-script.py plan-marshall:some-future-script:thing run --command-args "foo"'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command


def test_unknown_bundle_notation_passes_through():
    """A non-plan-marshall notation is returned unchanged."""
    # Arrange
    command = 'python3 .plan/execute-script.py pm-dev-java:java-core:compile run --command-args "compile"'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

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
    rewritten, injected = inject_project_dir(command, PLAN_ID)

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
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests plan-marshall"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is True
    # The payload value should appear as a single quoted token after shlex.join
    assert "'module-tests plan-marshall'" in rewritten or 'module-tests plan-marshall' in rewritten
    # Order: notation -> run -> --plan-id <plan_id> -> --command-args <payload>
    run_idx = rewritten.index(' run ')
    plan_id_idx = rewritten.index('--plan-id')
    command_args_idx = rewritten.index('--command-args')
    assert run_idx < plan_id_idx < command_args_idx


def test_command_args_passthrough_preserved_verbatim():
    """On pass-through (Bucket A), the command string is byte-identical."""
    # Arrange
    command = 'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get --plan-id foo --task 3'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert — exact string equality on pass-through
    assert injected is False
    assert rewritten == command


# =============================================================================
# (7) Empty / malformed commands
# =============================================================================


def test_empty_command_returns_false():
    """Empty command string returns (command, False) without raising."""
    # Act
    rewritten, injected = inject_project_dir('', PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == ''


def test_whitespace_only_command_returns_false():
    """Whitespace-only command returns (command, False) without raising."""
    # Act
    rewritten, injected = inject_project_dir('   ', PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == '   '


def test_malformed_quoting_returns_false():
    """A command with unbalanced quotes passes through without raising."""
    # Arrange — unbalanced single quote trips shlex.split
    command = "python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args 'module-tests"

    # Act — must NOT raise
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command


def test_executor_without_notation_returns_false():
    """Executor invoked without a notation token passes through."""
    # Arrange — `.plan/execute-script.py` is the last token (no notation)
    command = 'python3 .plan/execute-script.py'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is False
    assert rewritten == command


def test_executor_with_notation_but_no_run_subcommand_passes_through():
    """Bucket B notation without `run` subcommand is not rewritten."""
    # Arrange — `help` instead of `run`
    command = 'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build help'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert — out of scope for injection
    assert injected is False
    assert rewritten == command


# =============================================================================
# (8) CLI entrypoint integration (TOON output contract)
# =============================================================================


def _parse_toon_output(stdout: str) -> dict:
    """Parse the TOON output emitted by cmd_run.

    Parsed via the shared toon_parser so the test locks in the real contract
    rather than re-implementing a brittle inline parser.
    """
    from toon_parser import parse_toon  # imported lazily to keep stdlib top

    return parse_toon(stdout)


def test_cli_entrypoint_emits_toon_on_injection(tmp_path):
    """CLI emits TOON with injected=true and the rewritten command on injection."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"'
    )
    expected_rewritten, injected = inject_project_dir(command, PLAN_ID)
    assert injected is True  # sanity — the scenario should trigger injection

    # Act — invoke the script as a subprocess (tmp_path used as isolated cwd)
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command',
        command,
        '--plan-id',
        PLAN_ID,
        cwd=tmp_path,
    )

    # Assert — structured TOON contract
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_toon_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is True
    assert parsed['rewritten_command'] == expected_rewritten


def test_cli_entrypoint_emits_toon_on_passthrough(tmp_path):
    """CLI pass-through (Bucket A) emits injected=false with original command."""
    # Arrange
    command = 'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get --plan-id my-plan --task 1'
    expected_rewritten, injected = inject_project_dir(command, PLAN_ID)
    assert injected is False  # sanity — Bucket A must not trigger injection

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command',
        command,
        '--plan-id',
        PLAN_ID,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_toon_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is False
    assert parsed['rewritten_command'] == expected_rewritten


def test_cli_entrypoint_emits_toon_on_non_executor(tmp_path):
    """CLI pass-through for non-executor commands emits injected=false."""
    # Arrange
    command = 'git status'
    expected_rewritten, injected = inject_project_dir(command, PLAN_ID)
    assert injected is False

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command',
        command,
        '--plan-id',
        PLAN_ID,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_toon_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is False
    assert parsed['rewritten_command'] == expected_rewritten


# =============================================================================
# (9) Two-state interaction — commands with --plan-id skip injection
# =============================================================================
#
# When a command already supplies ``--plan-id`` (router-level), the target
# Bucket B script auto-resolves the worktree path via the shared
# ``resolve_project_dir`` contract. Injecting a second ``--plan-id`` (or a
# conflicting ``--project-dir``) would be wrong, so the helper MUST skip
# injection in that case — this is now the natural no-double-injection guard.


@pytest.mark.parametrize('notation', BUCKET_B_NOTATIONS)
def test_skips_injection_when_plan_id_already_present(notation):
    """A Bucket B command carrying --plan-id must not get a second --plan-id."""
    # Arrange — router-level --plan-id is supplied by the caller.
    command = f'python3 .plan/execute-script.py {notation} run --plan-id task-routing-canonical --command-args "verify"'

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert — the helper recognises --plan-id and leaves the command alone.
    assert injected is False, (
        f'inject_project_dir must NOT inject when --plan-id is already present; '
        f'got rewritten={rewritten!r}'
    )
    # The original --plan-id must survive intact.
    assert '--plan-id task-routing-canonical' in rewritten
    # And the offered plan id was NOT injected on top.
    assert PLAN_ID not in rewritten


def test_skips_injection_with_plan_id_equals_form():
    """``--plan-id=ID`` (equals form) must also be detected as routing intent."""
    # Arrange — equals-form router-level --plan-id.
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --plan-id=task-routing-canonical --command-args "verify"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert — both detection forms must trigger the skip.
    assert injected is False
    assert '--plan-id=task-routing-canonical' in rewritten
    assert PLAN_ID not in rewritten


def test_injects_when_neither_plan_id_nor_project_dir_present():
    """Sanity: the only path that triggers injection is "neither flag present"."""
    # Arrange — Bucket B command without either routing flag.
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests"'
    )

    # Act
    rewritten, injected = inject_project_dir(command, PLAN_ID)

    # Assert
    assert injected is True
    assert f'--plan-id {PLAN_ID}' in rewritten


def test_cli_entrypoint_emits_toon_on_plan_id_present_passthrough(tmp_path):
    """CLI surfaces injected=false + original command when --plan-id is present."""
    # Arrange
    command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --plan-id task-routing-canonical --command-args "module-tests"'
    )
    expected_rewritten, injected = inject_project_dir(command, PLAN_ID)
    assert injected is False  # sanity — --plan-id triggers the skip

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command',
        command,
        '--plan-id',
        PLAN_ID,
        cwd=tmp_path,
    )

    # Assert
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_toon_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is False
    assert parsed['rewritten_command'] == expected_rewritten
