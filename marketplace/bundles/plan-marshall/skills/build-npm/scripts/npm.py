#!/usr/bin/env python3
"""npm build operations - run command with auto-parse on failure.

Provides:
- execute_direct(): Foundation API for npm command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_command_type(): npm vs npx detection
- get_bash_timeout(): Moved to _build_shared module

Usage:
    from npm import execute_direct, cmd_run

    # Foundation API
    result = execute_direct(
        args="run test",
        command_key="npm:test",
        default_timeout=300
    )

    # Run subcommand (CLI entry point)
    cmd_run(args)  # args from argparse
"""

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

from _build_coverage_report import create_coverage_report_handler
from _build_execute import CaptureStrategy, execute_direct_base
from _build_parse import (
    Issue,
    UnitTestSummary,
)
from _build_result import (
    DirectCommandResult,
)
from _build_shared import cmd_run_common
from _npm_parse_errors import parse_log as parse_npm_errors
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap

# Import npm parsers from internal modules (underscore prefix = private)
from _npm_parse_typescript import parse_log as parse_typescript
from plan_logging import log_entry  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

# npm executable (no wrapper needed unlike Maven)
NPM_COMMAND = 'npm'

# Commands that should use npx instead of npm
NPX_COMMANDS = ['playwright', 'eslint', 'prettier', 'stylelint', 'tsc', 'jest', 'vitest']

# --- Tool-specific coverage configuration (inlined from former wrapper) ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage/coverage-summary.json', 'jest_json'),
        ('coverage/lcov.info', 'lcov'),
        ('dist/coverage/coverage-summary.json', 'jest_json'),
    ],
    not_found_message='No coverage report found. Run tests with coverage first.',
)



# =============================================================================
# API Functions (no argparse dependency)
# =============================================================================


def detect_command_type(args: str) -> str:
    """Detect whether to use npm or npx based on the command.

    Args:
        args: Command arguments.

    Returns:
        'npm' or 'npx'.
    """
    args_lower = args.lower().strip()
    for npx_cmd in NPX_COMMANDS:
        if args_lower.startswith(npx_cmd):
            return 'npx'
    return 'npm'


def _npm_scope_fn(args: str) -> str:
    """Extract scope from npm workspace or prefix arguments."""
    workspace_match = re.search(r'--workspace[=\s]+(\S+)', args)
    if workspace_match:
        return workspace_match.group(1)
    prefix_match = re.search(r'--prefix\s+(\S+)', args)
    if prefix_match:
        return prefix_match.group(1)
    return 'default'


def _npm_build_command_fn(command_type: str):
    """Create a build command function for the detected command type (npm or npx)."""

    def _build_command(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
        # wrapper is the command_type (npm or npx) for npm
        cmd_parts = [command_type] + args.split()
        command_str = ' '.join(cmd_parts)
        return cmd_parts, command_str

    return _build_command


def execute_direct(
    args: str,
    command_key: str,
    default_timeout: int = 300,
    project_dir: str = '.',
    working_dir: str | None = None,
    env_vars: str | None = None,
) -> DirectCommandResult:
    """Execute npm command with adaptive timeout learning.

    This is the foundation layer for all npm command execution.
    Uses run-config for timeout retrieval and learning.
    Conforms to R1 requirement: all output goes to log file, not memory.

    Args:
        args: Complete npm arguments with all routing embedded
              (e.g., "run test", "run test --workspace=pkg", "--prefix ./pkg run test")
        command_key: Command identifier for timeout learning (e.g., "npm:test")
        default_timeout: Default timeout in seconds if no learned value exists
        project_dir: Project root directory
        working_dir: Working directory for command execution (overrides project_dir for cwd)
        env_vars: Environment variables string (e.g., "NODE_ENV=test CI=true")

    Returns:
        DirectCommandResult with:
        - status: "success" | "error" | "timeout"
        - exit_code: int
        - duration_seconds: int
        - log_file: str (path to captured output)
        - command: str
        - timeout_used_seconds: int (optional)
        - command_type: str ("npm" or "npx")
        - error: str (on error/timeout only)
    """
    # Detect command type (npm or npx)
    command_type = detect_command_type(args)
    log_entry('script', 'global', 'INFO', f'[NPM] Executing: {command_type} {args}')

    # Parse env_vars string into dict
    parsed_env: dict[str, str] | None = None
    if env_vars:
        parsed_env = {}
        for env_pair in env_vars.split():
            if '=' in env_pair:
                key, value = env_pair.split('=', 1)
                parsed_env[key] = value

    return execute_direct_base(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        tool_name='npm',
        build_command_fn=_npm_build_command_fn(command_type),
        wrapper=command_type,  # npm or npx
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        scope_fn=_npm_scope_fn,
        env_vars=parsed_env,
        working_dir=working_dir,
        extra_result_fields={'command_type': command_type},
    )



# =============================================================================
# Tool Detection
# =============================================================================


def detect_tool_type(content: str, command: str) -> str:
    """Detect which tool produced the output.

    Args:
        content: Log file content.
        command: Original command string.

    Returns:
        Tool type: "typescript", "jest", "tap", "eslint", "npm_error", or "generic"
    """
    command_lower = command.lower()

    # Check command first
    if 'tsc' in command_lower or 'typescript' in command_lower:
        return 'typescript'
    if 'jest' in command_lower:
        return 'jest'
    if 'eslint' in command_lower:
        return 'eslint'

    # Check content patterns
    if 'npm ERR!' in content:
        return 'npm_error'
    if 'TAP version' in content or '# tests' in content:
        return 'tap'
    if 'error TS' in content or '): error TS' in content or ': error TS' in content:
        return 'typescript'
    if 'FAIL ' in content and ('Tests:' in content or 'Test Suites:' in content):
        return 'jest'
    if 'problem' in content.lower() and 'error' in content.lower():
        # Check for ESLint-style output
        if any(line.strip().endswith(')') for line in content.split('\n') if 'error' in line.lower()):
            return 'eslint'

    return 'generic'


def parse_with_detector(log_file: str, command: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse log file using appropriate tool-specific parser.

    Args:
        log_file: Path to the log file.
        command: Original command string.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    tool_type = detect_tool_type(content, command)

    try:
        if tool_type == 'typescript':
            return parse_typescript(log_file)
        elif tool_type == 'jest':
            return parse_jest(log_file)
        elif tool_type == 'tap':
            return parse_tap(log_file)
        elif tool_type == 'eslint':
            return parse_eslint(log_file)
        elif tool_type == 'npm_error':
            return parse_npm_errors(log_file)
        else:
            # Generic fallback - try each parser and use first with results
            parsers: list[Callable[[str], tuple[list[Issue], UnitTestSummary | None, str]]] = [
                parse_npm_errors,
                parse_typescript,
                parse_eslint,
                parse_jest,
                parse_tap,
            ]
            for parser in parsers:
                try:
                    issues, test_summary, build_status = parser(log_file)
                    if issues:
                        return issues, test_summary, build_status
                except Exception:
                    continue
            return [], None, 'FAILURE'
    except Exception:
        return [], None, 'FAILURE'


# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================


def cmd_run(args: argparse.Namespace) -> int:
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for execution and cmd_run_common() for result handling.
    """
    project_dir = getattr(args, 'project_dir', '.')

    # Build command key for timeout learning
    command_args = args.command_args
    args_key = command_args.split()[0].replace(' ', '_').replace('-', '_') if command_args else 'default'
    command_key = f'npm:{args_key}'

    # Execute via execute_direct foundation layer
    result = execute_direct(
        args=command_args,
        command_key=command_key,
        default_timeout=args.timeout,
        project_dir=project_dir,
        working_dir=args.working_dir,
        env_vars=args.env,
    )

    return cmd_run_common(
        result=result,
        parser_fn=parse_with_detector,
        tool_name='npm',
        output_format=getattr(args, 'format', 'toon'),
        mode=getattr(args, 'mode', 'actionable'),
        project_dir=project_dir,
        parser_needs_command=True,
    )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='npm/npx build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--command-args', dest='command_args',
        required=True,
        help="Complete npm command arguments (e.g., 'run test' or 'run test --workspace=pkg')",
    )
    run_parser.add_argument('--working-dir', dest='working_dir', help='Working directory for command execution')
    run_parser.add_argument('--env', help="Environment variables (e.g., 'NODE_ENV=test CI=true')")
    run_parser.add_argument('--timeout', type=int, default=120, help='Build timeout in seconds (default: 120 = 2 min)')
    run_parser.add_argument(
        '--mode', choices=['actionable', 'structured', 'errors'], default='actionable', help='Output mode'
    )
    run_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format')
    run_parser.add_argument('--project-dir', dest='project_dir', default='.', help='Project root directory')
    run_parser.set_defaults(func=cmd_run)

    # coverage-report subcommand
    cov_parser = subparsers.add_parser('coverage-report', help='Parse JavaScript coverage report')
    cov_parser.add_argument('--project-path', dest='project_path', help='Project directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage report path')
    cov_parser.add_argument('--threshold', type=int, default=80, help='Coverage threshold percent (default: 80)')
    cov_parser.set_defaults(func=cmd_coverage_report)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
