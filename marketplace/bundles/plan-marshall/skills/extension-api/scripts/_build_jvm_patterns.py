#!/usr/bin/env python3
"""Shared JVM error category patterns for Maven and Gradle parsers.

Extracts common Java/Kotlin/Groovy error patterns that both Maven and Gradle
use for issue categorization. Tool-specific patterns are merged in by each
parser module.

Usage:
    from _build_jvm_patterns import JVM_BASE_PATTERNS, merge_patterns
"""

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
