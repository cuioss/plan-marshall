#!/usr/bin/env python3
"""npm build operations - run command with auto-parse on failure.

Provides:
- execute_direct(): Foundation API for npm command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_command_type(): npm vs npx detection
- get_bash_timeout(): Bash tool timeout calculation

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
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Cross-skill imports (PYTHONPATH set by executor)
from run_config import timeout_get, timeout_set  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from _build_result import (
    DirectCommandResult,
    create_log_file,
    success_result,
    error_result,
    timeout_result,
    ERROR_BUILD_FAILED,
    ERROR_LOG_FILE_FAILED,
    ERROR_EXECUTION_FAILED,
)
from _build_format import format_toon, format_json
from _build_parse import (
    Issue,
    UnitTestSummary,
    filter_warnings,
    load_acceptable_warnings,
    partition_issues,
)

# Import npm parsers from internal modules (underscore prefix = private)
from _npm_parse_typescript import parse_log as parse_typescript
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_errors import parse_log as parse_npm_errors


# =============================================================================
# Constants
# =============================================================================

# npm executable (no wrapper needed unlike Maven)
NPM_COMMAND = 'npm'

# Commands that should use npx instead of npm
NPX_COMMANDS = ['playwright', 'eslint', 'prettier', 'stylelint', 'tsc', 'jest', 'vitest']

# Bash tool outer timeout buffer (seconds) - ensures outer > inner
OUTER_TIMEOUT_BUFFER = 30


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


def execute_direct(
    args: str,
    command_key: str,
    default_timeout: int = 300,
    project_dir: str = '.',
    working_dir: str = None,
    env_vars: str = None
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
    import os
    import re

    # Step 1: Detect command type (npm or npx)
    command_type = detect_command_type(args)
    log_entry('script', 'global', 'INFO', f'[NPM] Executing: {command_type} {args}')

    # Step 2: Get timeout from run-config (with safety margin)
    timeout_seconds = timeout_get(command_key, default_timeout, project_dir)

    # Step 3: Build command (args is complete and self-contained)
    cmd_parts = [command_type] + args.split()
    command_str = ' '.join(cmd_parts)

    # Step 4: Determine scope for log file (extract from embedded routing)
    scope = "default"
    workspace_match = re.search(r'--workspace[=\s]+(\S+)', args)
    if workspace_match:
        scope = workspace_match.group(1)
    else:
        prefix_match = re.search(r'--prefix\s+(\S+)', args)
        if prefix_match:
            scope = prefix_match.group(1)

    # Step 5: Create log file for output (R1 requirement)
    log_file = create_log_file("npm", scope, project_dir)
    if not log_file:
        return {
            "status": "error",
            "exit_code": -1,
            "duration_seconds": 0,
            "log_file": "",
            "command": command_str,
            "command_type": command_type,
            "error": "Failed to create log file"
        }

    # Step 6: Prepare environment
    env = os.environ.copy()
    if env_vars:
        for env_pair in env_vars.split():
            if '=' in env_pair:
                key, value = env_pair.split('=', 1)
                env[key] = value

    # Step 7: Determine working directory
    cwd = working_dir if working_dir else project_dir

    # Step 8: Execute with output to log file
    start_time = time.time()

    try:
        with open(log_file, 'w') as log:
            result = subprocess.run(
                cmd_parts,
                timeout=timeout_seconds,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env
            )
        duration_seconds = int(time.time() - start_time)

        # Step 6: Record duration for adaptive learning (only on completion)
        timeout_set(command_key, duration_seconds, project_dir)

        # Step 7: Return structured result
        if result.returncode == 0:
            log_entry('script', 'global', 'INFO', f'[NPM] Completed in {duration_seconds}s')
            return {
                "status": "success",
                "exit_code": 0,
                "duration_seconds": duration_seconds,
                "log_file": log_file,
                "command": command_str,
                "timeout_used_seconds": timeout_seconds,
                "command_type": command_type
            }
        else:
            log_entry('script', 'global', 'ERROR', f'[NPM] Failed with exit code {result.returncode}')
            return {
                "status": "error",
                "exit_code": result.returncode,
                "duration_seconds": duration_seconds,
                "log_file": log_file,
                "command": command_str,
                "timeout_used_seconds": timeout_seconds,
                "command_type": command_type,
                "error": f"Build failed with exit code {result.returncode}"
            }

    except subprocess.TimeoutExpired:
        duration_seconds = int(time.time() - start_time)
        log_entry('script', 'global', 'ERROR', f'[NPM] Timeout after {timeout_seconds}s')
        return {
            "status": "timeout",
            "exit_code": -1,
            "duration_seconds": duration_seconds,
            "log_file": log_file,
            "command": command_str,
            "timeout_used_seconds": timeout_seconds,
            "command_type": command_type,
            "error": f"Command timed out after {timeout_seconds} seconds"
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "exit_code": -1,
            "duration_seconds": 0,
            "log_file": log_file,
            "command": command_str,
            "timeout_used_seconds": timeout_seconds,
            "command_type": command_type,
            "error": f"Command not found: {command_type}"
        }

    except OSError as e:
        return {
            "status": "error",
            "exit_code": -1,
            "duration_seconds": 0,
            "log_file": log_file,
            "command": command_str,
            "timeout_used_seconds": timeout_seconds,
            "command_type": command_type,
            "error": str(e)
        }


def get_bash_timeout(inner_timeout_seconds: int) -> int:
    """Calculate Bash tool timeout with buffer.

    The Bash tool has a default 120-second timeout. For long-running builds,
    we need to set the outer timeout higher than the inner (shell) timeout.

    Args:
        inner_timeout_seconds: The shell timeout in seconds.

    Returns:
        Bash tool timeout in seconds (inner + buffer).
    """
    return inner_timeout_seconds + OUTER_TIMEOUT_BUFFER


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
    if "tsc" in command_lower or "typescript" in command_lower:
        return "typescript"
    if "jest" in command_lower:
        return "jest"
    if "eslint" in command_lower:
        return "eslint"

    # Check content patterns
    if "npm ERR!" in content:
        return "npm_error"
    if "TAP version" in content or "# tests" in content:
        return "tap"
    if "error TS" in content or "): error TS" in content or ": error TS" in content:
        return "typescript"
    if "FAIL " in content and ("Tests:" in content or "Test Suites:" in content):
        return "jest"
    if "problem" in content.lower() and "error" in content.lower():
        # Check for ESLint-style output
        if any(line.strip().endswith(")") for line in content.split("\n") if "error" in line.lower()):
            return "eslint"

    return "generic"


def parse_with_detector(log_file: str, command: str) -> Tuple[List[Issue], Optional[UnitTestSummary], str]:
    """Parse log file using appropriate tool-specific parser.

    Args:
        log_file: Path to the log file.
        command: Original command string.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    content = Path(log_file).read_text(encoding="utf-8", errors="replace")
    tool_type = detect_tool_type(content, command)

    try:
        if tool_type == "typescript":
            return parse_typescript(log_file)
        elif tool_type == "jest":
            return parse_jest(log_file)
        elif tool_type == "tap":
            return parse_tap(log_file)
        elif tool_type == "eslint":
            return parse_eslint(log_file)
        elif tool_type == "npm_error":
            return parse_npm_errors(log_file)
        else:
            # Generic fallback - try each parser and use first with results
            parsers = [parse_npm_errors, parse_typescript, parse_eslint, parse_jest, parse_tap]
            for parser in parsers:
                try:
                    issues, test_summary, build_status = parser(log_file)
                    if issues:
                        return issues, test_summary, build_status
                except Exception:
                    continue
            return [], None, "FAILURE"
    except Exception:
        return [], None, "FAILURE"


# =============================================================================
# Run Subcommand (execute + auto-parse on failure)
# =============================================================================

def cmd_run(args):
    """Handle run subcommand - execute + auto-parse on failure.

    Delegates to execute_direct() for all npm execution.

    Supports:
    - --format toon (default) or --format json
    - --mode actionable (default), structured, or errors
    """
    project_dir = getattr(args, 'project_dir', '.')
    output_format = getattr(args, 'format', 'toon')
    mode = getattr(args, 'mode', 'actionable')

    # Select formatter based on output format
    formatter = format_json if output_format == 'json' else format_toon

    # Build command key for timeout learning
    # commandArgs is complete and self-contained (includes --workspace or --prefix if needed)
    command_args = args.commandArgs
    args_key = command_args.split()[0].replace(' ', '_').replace('-', '_') if command_args else "default"
    command_key = f"npm:{args_key}"

    # Execute via execute_direct foundation layer
    # commandArgs is complete and self-contained (includes workspace routing)
    result = execute_direct(
        args=command_args,
        command_key=command_key,
        default_timeout=args.timeout,
        project_dir=project_dir,
        working_dir=args.working_dir,
        env_vars=args.env
    )

    log_file = result['log_file']
    command_str = result['command']
    print(f"[EXEC] {command_str}", file=sys.stderr)

    # Handle execution errors (npm not found, log file creation failed)
    if result['status'] == 'error' and result['exit_code'] == -1:
        error_type = ERROR_EXECUTION_FAILED
        if 'log file' in result.get('error', '').lower():
            error_type = ERROR_LOG_FILE_FAILED

        output = error_result(
            error=error_type,
            exit_code=-1,
            duration_seconds=0,
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 1

    # Handle timeout
    if result['status'] == 'timeout':
        output = timeout_result(
            timeout_used_seconds=result['timeout_used_seconds'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 1

    # Success case
    if result['status'] == 'success':
        output = success_result(
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))
        return 0

    # Build failed - parse the log file for errors
    try:
        issues, test_summary, build_status = parse_with_detector(log_file, command_str)

        # Partition issues into errors and warnings
        errors, warnings = partition_issues(issues)

        # Load acceptable warnings and filter based on mode
        patterns = load_acceptable_warnings(project_dir, "npm")
        filtered_warnings = filter_warnings(warnings, patterns, mode)

        # Build result dict
        output = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )

        # Add errors if present
        if errors:
            output["errors"] = errors[:20]

        # Add warnings if present (mode != errors already handled by filter_warnings)
        if filtered_warnings:
            output["warnings"] = filtered_warnings[:10]

        # Add test summary if present
        if test_summary:
            output["tests"] = test_summary

        print(formatter(output))

    except Exception:
        # If parsing fails, still return the build failure
        output = error_result(
            error=ERROR_BUILD_FAILED,
            exit_code=result['exit_code'],
            duration_seconds=result['duration_seconds'],
            log_file=log_file,
            command=command_str,
        )
        print(formatter(output))

    return 1


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="npm/npx build operations", formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run subcommand (primary API)
    run_parser = subparsers.add_parser("run", help="Execute build and auto-parse on failure (primary API)")
    run_parser.add_argument("--commandArgs", required=True, help="Complete npm command arguments (e.g., 'run test' or 'run test --workspace=pkg')")
    run_parser.add_argument("--working-dir", dest="working_dir", help="Working directory for command execution")
    run_parser.add_argument("--env", help="Environment variables (e.g., 'NODE_ENV=test CI=true')")
    run_parser.add_argument("--timeout", type=int, default=120, help="Build timeout in seconds (default: 120 = 2 min)")
    run_parser.add_argument("--mode", choices=["actionable", "structured", "errors"], default="actionable", help="Output mode")
    run_parser.add_argument("--format", choices=["toon", "json"], default="toon", help="Output format")
    run_parser.add_argument("--project-dir", dest="project_dir", default=".", help="Project root directory")
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
