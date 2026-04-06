"""Build vocabulary constants for canonical commands and profile patterns.

These constants define the canonical build command names, their aliases,
and profile classification patterns used across all build system integrations
(Maven, Gradle, npm, Python).

Separated from extension_base.py because they are build vocabulary,
not extension API.
"""

# =============================================================================
# Canonical Command Constants
# =============================================================================

CMD_CLEAN = 'clean'
CMD_COMPILE = 'compile'
CMD_TEST_COMPILE = 'test-compile'
CMD_MODULE_TESTS = 'module-tests'
CMD_INTEGRATION_TESTS = 'integration-tests'
CMD_E2E = 'e2e'
CMD_COVERAGE = 'coverage'
CMD_BENCHMARK = 'benchmark'
CMD_QUALITY_GATE = 'quality-gate'
CMD_VERIFY = 'verify'
CMD_INSTALL = 'install'
CMD_CLEAN_INSTALL = 'clean-install'
CMD_PACKAGE = 'package'

ALL_CANONICAL_COMMANDS = [
    CMD_CLEAN,
    CMD_COMPILE,
    CMD_TEST_COMPILE,
    CMD_MODULE_TESTS,
    CMD_INTEGRATION_TESTS,
    CMD_E2E,
    CMD_COVERAGE,
    CMD_BENCHMARK,
    CMD_QUALITY_GATE,
    CMD_VERIFY,
    CMD_INSTALL,
    CMD_CLEAN_INSTALL,
    CMD_PACKAGE,
]


# =============================================================================
# Canonical Command Metadata
# =============================================================================

CANONICAL_COMMANDS = {
    CMD_INTEGRATION_TESTS: {
        'aliases': [
            'integration-tests',
            'integration-test',
            'integrationTest',
            'it',
        ],
    },
    CMD_E2E: {
        'aliases': [
            'e2e',
            'acceptance',
            'end-to-end',
        ],
    },
    CMD_COVERAGE: {
        'aliases': ['coverage', 'jacoco'],
    },
    CMD_BENCHMARK: {
        'aliases': [
            'performance',
            'benchmarks',
            'jmh',
            'perf',
            'stress',
            'load',
        ],
    },
    CMD_QUALITY_GATE: {
        'aliases': [
            'pre-commit',
            'precommit',
            'sonar',
            'lint',
            'check',
            'quality',
        ],
    },
}


# =============================================================================
# Profile Classification Patterns (derived from CANONICAL_COMMANDS aliases)
# =============================================================================


def _build_profile_patterns() -> dict[str, str]:
    """Build PROFILE_PATTERNS from CANONICAL_COMMANDS aliases."""
    patterns: dict[str, str] = {}
    for cmd, meta in CANONICAL_COMMANDS.items():
        aliases: list[str] = meta.get('aliases', [])  # type: ignore[assignment]
        for alias in aliases:
            patterns[alias] = cmd
    return patterns


PROFILE_PATTERNS = _build_profile_patterns()

APPLICABLE_PROFILES = ('implementation', 'module_testing', 'integration_testing', 'quality', 'documentation')
"""Profile names iterated during _build_applicable_result(). Does not include 'core'
which is always merged into each profile."""
