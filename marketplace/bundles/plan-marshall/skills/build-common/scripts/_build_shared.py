#!/usr/bin/env python3
"""Shared utilities for build-* skills.

Provides common functions used across Maven, Gradle, npm, and Python build skills
to avoid duplication.
"""

import re

# Buffer added to inner timeout for Bash tool timeout calculation.
# The Bash tool has a default 120-second timeout. For long-running builds,
# the outer timeout must be higher than the inner (shell) timeout.
OUTER_TIMEOUT_BUFFER = 30


def get_bash_timeout(inner_timeout_seconds: int) -> int:
    """Calculate Bash tool timeout with buffer.

    Args:
        inner_timeout_seconds: The shell timeout in seconds.

    Returns:
        Bash tool timeout in seconds (inner + buffer).
    """
    return inner_timeout_seconds + OUTER_TIMEOUT_BUFFER


def extract_log_scope(args: str, build_tool: str) -> str:
    """Extract log scope from build command arguments.

    Each build tool embeds module/workspace targeting differently in its arguments.
    This function extracts the appropriate scope for log file naming.

    Args:
        args: Complete command arguments string.
        build_tool: Build tool identifier ('maven', 'gradle', 'npm', 'python').

    Returns:
        Scope string for log file naming. Returns 'default' if no scope found.
    """
    if build_tool == 'maven':
        # Maven uses -pl for module targeting
        if '-pl ' in args:
            try:
                pl_idx = args.index('-pl ') + 4
                return args[pl_idx:].split()[0]
            except (ValueError, IndexError):
                pass

    elif build_tool == 'gradle':
        # Gradle uses :module:task prefix format
        if args.startswith(':'):
            parts = args.split(':')
            if len(parts) >= 2:
                return parts[1]

    elif build_tool == 'npm':
        # npm uses --workspace or --prefix for targeting
        workspace_match = re.search(r'--workspace[=\s]+(\S+)', args)
        if workspace_match:
            return workspace_match.group(1)
        prefix_match = re.search(r'--prefix\s+(\S+)', args)
        if prefix_match:
            return prefix_match.group(1)

    # Python and fallback: no scope extraction
    return 'default'
