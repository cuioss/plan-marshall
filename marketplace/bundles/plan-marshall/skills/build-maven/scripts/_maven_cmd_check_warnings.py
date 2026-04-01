#!/usr/bin/env python3
"""Check-warnings subcommand for Maven — delegates to shared base."""

from _build_check_warnings import cmd_check_warnings_base  # type: ignore[import-not-found]


def cmd_check_warnings(args) -> int:
    """Handle check-warnings subcommand."""
    return cmd_check_warnings_base(
        args,
        matcher='substring',
        filter_severity='WARNING',
        supports_patterns_arg=True,
    )
