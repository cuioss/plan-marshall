#!/usr/bin/env python3
"""Shared canonical command generation for build system discovery.

Provides build_canonical_commands() which generates the script invocation
strings for canonical command names (clean, compile, verify, etc.).

All four build skills (Maven, Gradle, npm, Python) use this to avoid
duplicating the command string construction pattern.

Usage:
    from _build_commands import build_canonical_commands

    commands = build_canonical_commands(
        skill_notation='plan-marshall:build-maven:maven',
        command_map={
            'clean': 'clean -pl my-module',
            'verify': 'verify -pl my-module',
            'compile': 'compile -pl my-module',
        },
    )
    # -> {'clean': 'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "clean -pl my-module"', ...}
"""

EXECUTOR_PREFIX = 'python3 .plan/execute-script.py'
"""Base executor command shared by all build skills."""


def build_canonical_commands(
    skill_notation: str,
    command_map: dict[str, str],
) -> dict[str, str]:
    """Generate canonical command invocation strings.

    Each entry in command_map maps a canonical command name to its
    tool-specific arguments. This function wraps each with the
    standard executor invocation.

    Args:
        skill_notation: Three-part skill notation (e.g., 'plan-marshall:build-maven:maven').
        command_map: Dict mapping canonical name -> tool-specific command args.
            Example: {'clean': 'clean -pl core', 'verify': 'verify -pl core'}

    Returns:
        Dict mapping canonical name -> full executor command string.
    """
    base = f'{EXECUTOR_PREFIX} {skill_notation} run'
    return {
        name: f'{base} --command-args "{args}"'
        for name, args in command_map.items()
    }


def build_chained_commands(
    skill_notation: str,
    command_list: list[str],
) -> str:
    """Generate a chained command string (cmd1 && cmd2).

    Used by npm's verify command which chains build + test.

    Args:
        skill_notation: Three-part skill notation.
        command_list: List of tool-specific command args to chain.

    Returns:
        Chained command string with ' && ' between each invocation.
    """
    base = f'{EXECUTOR_PREFIX} {skill_notation} run'
    parts = [f'{base} --command-args "{args}"' for args in command_list]
    return ' && '.join(parts)
