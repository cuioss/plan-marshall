#!/usr/bin/env python3
"""Issue parsing and warning filtering utilities.

Shared data structures for build issues and warning filtering across build systems.
Used by domain extensions (pm-dev-java, pm-dev-frontend) for consistent issue handling.

Usage:
    from build_parse import (
        Issue, UnitTestSummary, BuildParser, SEVERITY_ERROR, SEVERITY_WARNING,
        filter_warnings, partition_issues, load_acceptable_warnings
    )

    # Create issues
    error = Issue(file="src/Main.java", line=15, message="cannot find symbol",
                  severity=SEVERITY_ERROR, category="compilation")
    warning = Issue(file="pom.xml", line=None, message="deprecated version",
                    severity=SEVERITY_WARNING)

    # Filter warnings
    patterns = load_acceptable_warnings("/path/to/project", "maven")
    filtered = filter_warnings([warning], patterns, mode="actionable")
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# Plan directory configuration for test isolation
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# =============================================================================
# Constants
# =============================================================================

SEVERITY_ERROR = 'error'
"""Severity level for errors that fail the build."""

SEVERITY_WARNING = 'warning'
"""Severity level for warnings that don't fail the build."""

# Output modes
MODE_ACTIONABLE = 'actionable'
"""Filter out accepted warnings, show only actionable items."""

MODE_STRUCTURED = 'structured'
"""Keep all warnings, mark accepted ones with accepted=True."""

MODE_ERRORS = 'errors'
"""Only show errors, no warnings."""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Issue:
    """Represents a build issue (error or warning).

    Attributes:
        file: Path to the file containing the issue, or None if not file-specific.
        line: Line number in the file, or None if not line-specific.
        message: Human-readable description of the issue.
        severity: Issue severity (SEVERITY_ERROR or SEVERITY_WARNING).
        category: Optional category (e.g., "compilation", "test_failure", "deprecation").
        stack_trace: Optional stack trace for test failures.
        accepted: Whether this warning is accepted (for structured mode output).
    """

    file: str | None
    line: int | None
    message: str
    severity: str
    category: str | None = None
    stack_trace: str | None = None
    accepted: bool = field(default=False)

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization.

        Returns:
            Dict with all non-None fields. The 'accepted' field is only
            included if True (for structured mode compatibility).
        """
        result = {
            'file': self.file,
            'line': self.line,
            'message': self.message,
            'severity': self.severity,
        }

        if self.category is not None:
            result['category'] = self.category

        if self.stack_trace is not None:
            result['stack_trace'] = self.stack_trace

        if self.accepted:
            result['accepted'] = True

        return result


@dataclass
class UnitTestSummary:
    """Summary of test execution results.

    Attributes:
        passed: Number of tests that passed.
        failed: Number of tests that failed.
        skipped: Number of tests that were skipped.
        total: Total number of tests (should equal passed + failed + skipped).
    """

    passed: int
    failed: int
    skipped: int
    total: int

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization.

        Returns:
            Dict with passed, failed, skipped, and total fields.
        """
        return {
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'total': self.total,
        }


# =============================================================================
# Parser Protocol
# =============================================================================


class BuildParser(Protocol):
    """Protocol for build log parsers.

    All parsers must implement parse_log() with this signature.
    Structural typing - no inheritance required.

    Example:
        def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
            content = Path(log_file).read_text()
            issues = _extract_issues(content)
            test_summary = _extract_test_summary(content)
            build_status = _detect_build_status(content)
            return issues, test_summary, build_status
    """

    def parse_log(self, log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
        """Parse build log file.

        Args:
            log_file: Path to the log file (from build_result.create_log_file())

        Returns:
            Tuple of (issues, test_summary, build_status):
            - issues: list[Issue] - all errors and warnings found
            - test_summary: UnitTestSummary | None - test counts if tests ran
            - build_status: "SUCCESS" | "FAILURE"

        Raises:
            FileNotFoundError: If log file doesn't exist
        """
        ...


# =============================================================================
# Warning Acceptance
# =============================================================================


def load_acceptable_warnings(project_dir: str, build_system: str) -> list[str]:
    """Load acceptable warning patterns from run-configuration.json.

    Reads patterns from the build-system-specific section of the configuration.

    Args:
        project_dir: Project root directory.
        build_system: Build system key (maven, gradle, npm).

    Returns:
        List of acceptable warning patterns. Empty list if config not found
        or section missing.

    Config location:
        .plan/run-configuration.json under {build_system}.acceptable_warnings

    Example config:
        {
            "maven": {
                "acceptable_warnings": [
                    "uses unchecked or unsafe operations",
                    "^.*deprecated.*$"
                ]
            }
        }
    """
    config_path = Path(project_dir) / _PLAN_DIR_NAME / 'run-configuration.json'

    if not config_path.exists():
        return []

    try:
        config = json.loads(config_path.read_text())
        build_config = config.get(build_system, {})
        warnings: list[str] = build_config.get('acceptable_warnings', [])
        return warnings
    except (OSError, json.JSONDecodeError):
        return []


def is_warning_accepted(warning: Issue, patterns: list[str]) -> bool:
    """Check if a warning matches an acceptable pattern.

    Supports two matching modes:
    - Substring matching: pattern is checked as substring of message
    - Regex matching: patterns starting with ^ are treated as regex

    Args:
        warning: The warning Issue to check.
        patterns: List of acceptable warning patterns.

    Returns:
        True if the warning matches any pattern, False otherwise.

    Example:
        >>> warning = Issue(None, None, "uses unchecked operations", SEVERITY_WARNING)
        >>> is_warning_accepted(warning, ["unchecked"])
        True
        >>> is_warning_accepted(warning, ["^.*unchecked.*$"])
        True
    """
    if not patterns:
        return False

    message = warning.message

    for pattern in patterns:
        if pattern.startswith('^'):
            # Regex pattern
            try:
                if re.match(pattern, message, re.IGNORECASE):
                    return True
            except re.error:
                # Invalid regex, skip
                continue
        else:
            # Substring match (case-insensitive)
            if pattern.lower() in message.lower():
                return True

    return False


def filter_warnings(warnings: list[Issue], patterns: list[str], mode: str = MODE_ACTIONABLE) -> list[Issue]:
    """Filter warnings based on mode.

    Args:
        warnings: List of warning Issues to filter.
        patterns: List of acceptable warning patterns.
        mode: Filtering mode:
            - "actionable": Remove accepted warnings, return only actionable
            - "structured": Keep all, set accepted=True on matching
            - "errors": Return empty list (no warnings in output)

    Returns:
        Filtered list of warnings based on mode.

    Example:
        >>> warnings = [Issue(None, None, "deprecated API", SEVERITY_WARNING)]
        >>> patterns = ["deprecated"]
        >>> filter_warnings(warnings, patterns, "actionable")
        []
        >>> result = filter_warnings(warnings, patterns, "structured")
        >>> result[0].accepted
        True
    """
    if mode == MODE_ERRORS:
        return []

    if mode == MODE_STRUCTURED:
        # Keep all, mark accepted ones
        result = []
        for warning in warnings:
            # Create copy with accepted flag set
            accepted = is_warning_accepted(warning, patterns)
            result.append(
                Issue(
                    file=warning.file,
                    line=warning.line,
                    message=warning.message,
                    severity=warning.severity,
                    category=warning.category,
                    stack_trace=warning.stack_trace,
                    accepted=accepted,
                )
            )
        return result

    # MODE_ACTIONABLE (default): filter out accepted
    return [w for w in warnings if not is_warning_accepted(w, patterns)]


def partition_issues(issues: list[Issue]) -> tuple[list[Issue], list[Issue]]:
    """Partition issues into errors and warnings by severity.

    Args:
        issues: List of Issues to partition.

    Returns:
        Tuple of (errors, warnings) where errors have SEVERITY_ERROR
        and warnings have SEVERITY_WARNING.

    Example:
        >>> issues = [
        ...     Issue(None, None, "error msg", SEVERITY_ERROR),
        ...     Issue(None, None, "warning msg", SEVERITY_WARNING),
        ... ]
        >>> errors, warnings = partition_issues(issues)
        >>> len(errors)
        1
        >>> len(warnings)
        1
    """
    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    return errors, warnings
