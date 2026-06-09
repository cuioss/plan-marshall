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
# Build-Class Vocabulary
# =============================================================================
#
# The build_class is the deterministic per-(path, role) build classification a
# domain extension attaches to each path it claims via classify_paths(). It is
# the second leg of the file-to-build contract: classify_paths() maps a path to
# a file role; classify_build_class() maps the (path, role) pair to one of the
# closed values below. The build_class NAMES the canonical command directly —
# the closed set equals the verification-command vocabulary, so a build_class of
# 'compile' resolves to `architecture resolve --command compile` with no
# name-to-name indirection. Downstream consumers (manage-execution-manifest,
# phase-4-plan) read the build_class to derive the verification command set for
# a changed-artifact list without re-deriving the file type.

BUILD_CLASS_PROD_COMPILE = 'compile'
BUILD_CLASS_TEST_RUN = 'module-tests'
BUILD_CLASS_DOCS_VALIDATE = 'docs-validate'
BUILD_CLASS_BUILD_CONFIG_FULL = 'verify'
BUILD_CLASS_NONE = 'none'

BUILD_CLASSES = frozenset(
    {
        BUILD_CLASS_PROD_COMPILE,
        BUILD_CLASS_TEST_RUN,
        BUILD_CLASS_DOCS_VALIDATE,
        BUILD_CLASS_BUILD_CONFIG_FULL,
        BUILD_CLASS_NONE,
    }
)
"""Closed set of build_class values — equal to the canonical verification-command
vocabulary (`compile` / `module-tests` / `verify` / `docs-validate` / `none`).
The single source of truth shared by ExtensionBase.classify_build_class(),
domain extensions, and their tests."""


# =============================================================================
# build_map Vocabulary Role Heuristics
# =============================================================================
#
# The portable (suffix, role_heuristic) vocabulary an extension declares via
# classify_globs(). The role heuristic decides a matched file's role from WHERE
# it sits in the project tree (the *-by-location heuristics) or directly from its
# suffix (the suffix-direct heuristics). The base-lib tree-deriver
# (derive_globs_from_tree) owns the location predicates that turn a *-by-location
# heuristic into a concrete role for a given path. The resolved role is one of the
# same four file roles classify_paths() uses: production / test / documentation /
# config.

ROLE_HEURISTIC_PRODUCTION_BY_LOCATION = 'production-by-location'
ROLE_HEURISTIC_TEST_BY_LOCATION = 'test-by-location'
ROLE_HEURISTIC_DOCUMENTATION = 'documentation'
ROLE_HEURISTIC_CONFIG = 'config'

ROLE_HEURISTICS = frozenset(
    {
        ROLE_HEURISTIC_PRODUCTION_BY_LOCATION,
        ROLE_HEURISTIC_TEST_BY_LOCATION,
        ROLE_HEURISTIC_DOCUMENTATION,
        ROLE_HEURISTIC_CONFIG,
    }
)
"""Closed set of role-heuristic names. The single source of truth shared by
ExtensionBase.classify_globs() / derive_globs_from_tree(), the domain extension
vocabularies, and their tests."""

# Resolved role each heuristic maps to (the four classify_paths() roles).
HEURISTIC_TO_ROLE = {
    ROLE_HEURISTIC_PRODUCTION_BY_LOCATION: 'production',
    ROLE_HEURISTIC_TEST_BY_LOCATION: 'test',
    ROLE_HEURISTIC_DOCUMENTATION: 'documentation',
    ROLE_HEURISTIC_CONFIG: 'config',
}


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
            'e2e-tests',
            'acceptance',
            'end-to-end',
        ],
    },
    CMD_COVERAGE: {
        'aliases': ['coverage', 'jacoco'],
    },
    CMD_BENCHMARK: {
        'aliases': [
            'benchmark',
            'performance',
            'benchmarks',
            'jmh',
            'perf',
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
