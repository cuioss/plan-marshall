#!/usr/bin/env python3
"""Shared JVM error category patterns for Maven and Gradle parsers.

Extracts common Java/Kotlin/Groovy error patterns that both Maven and Gradle
use for issue categorization. Tool-specific patterns are merged in by each
parser module.

Usage:
    from _build_jvm_patterns import JVM_BASE_PATTERNS, merge_patterns
"""

import re

from _build_parse import CategoryPatterns

# Shared JVM compilation error patterns recognized by both Maven and Gradle.
# Maven uses substring matching; Gradle uses regex. Each parser adapts
# these base patterns to its matching mode when merging.
JVM_BASE_PATTERNS: CategoryPatterns = {
    'compilation_error': [
        'cannot find symbol',
        'incompatible types',
        'illegal start',
        'class, interface, or enum expected',
        'unreported exception',
        'method does not override',
        'not a statement',
        'package does not exist',
        'cannot be applied',
    ],
    'test_failure': [
        'tests run:',
        'failure!',
        'test failure',
        'assertionfailed',
        'expected:',
    ],
    'dependency_error': [
        'could not resolve dependencies',
        'could not find artifact',
        'missing, no dependency',
        'artifact not found',
        'non-resolvable',
    ],
    'javadoc_warning': [
        'javadoc',
        'no @param',
        'no @return',
        '@param name',
        'missing @',
    ],
    'deprecation_warning': [
        '[deprecation]',
        'has been deprecated',
    ],
    'unchecked_warning': [
        '[unchecked]',
        'unchecked conversion',
    ],
    'openrewrite_info': [
        'org.openrewrite',
        'rewrite:',
    ],
}


def parse_jvm_file_location(line: str) -> dict[str, str | int | None]:
    """Extract file, line, and column from a JVM build error/warning line.

    Shared across Maven and Gradle parsers. Supports Java, Kotlin, Groovy,
    and Scala source file patterns.

    Patterns recognized (in priority order):
    1. file.java:[line,col] — Maven compiler output
    2. file.(java|kt|groovy|scala):line:col? — Gradle/generic compiler output
    3. file.java:line: — simpler line-only reference
    4. TestName.methodName:line — test failure reference

    Args:
        line: A single log line to parse.

    Returns:
        Dict with 'file', 'line', 'column' keys (values may be None).
        May also contain 'method' key for test failure patterns.
    """
    result: dict[str, str | int | None] = {'file': None, 'line': None, 'column': None}

    # Pattern 1: Maven style — file.java:[line,col]
    match = re.search(r'([^\s\[\]]+\.java):\[(\d+),(\d+)\]', line)
    if match:
        return {'file': match.group(1), 'line': int(match.group(2)), 'column': int(match.group(3))}

    # Pattern 2: Gradle/generic style — file.(java|kt|groovy|scala):line:col?
    match = re.search(r'([^\s:]+\.(java|kt|groovy|scala)):(\d+):?(\d+)?', line)
    if match:
        return {
            'file': match.group(1),
            'line': int(match.group(3)),
            'column': int(match.group(4)) if match.group(4) else None,
        }

    # Pattern 3: Simpler line-only — file.java:line:
    match = re.search(r'([^\s\[\]]+\.java):(\d+):', line)
    if match:
        return {'file': match.group(1), 'line': int(match.group(2)), 'column': None}

    # Pattern 4: Test failure — TestName.methodName:line
    match = re.search(r'(\w+Test)\.(\w+):(\d+)', line)
    if match:
        return {'file': f'{match.group(1)}.java', 'line': int(match.group(3)), 'column': None, 'method': match.group(2)}

    return result


def merge_patterns(base: CategoryPatterns, overrides: CategoryPatterns) -> CategoryPatterns:
    """Merge tool-specific patterns into base patterns.

    For each category:
    - If category exists in both, the override list REPLACES the base list
      (tool-specific patterns are intentionally curated per tool)
    - If category exists only in base, it's kept as-is
    - If category exists only in overrides, it's added

    Args:
        base: Base pattern dict (typically JVM_BASE_PATTERNS).
        overrides: Tool-specific overrides or additions.

    Returns:
        Merged CategoryPatterns dict.
    """
    merged = dict(base)
    merged.update(overrides)
    return merged
