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
# build_map File Roles
# =============================================================================
#
# The closed set of file roles a classify_globs() explicit route may carry. An
# extension declares (pattern, role) routes directly: a glob pattern paired with
# one of these four resolved roles. The role is the same vocabulary
# classify_paths() and classify_build_class() use, so a route's role maps
# straight through to a build_class with no name-to-name indirection.

ROLE_PRODUCTION = 'production'
ROLE_TEST = 'test'
ROLE_DOCUMENTATION = 'documentation'
ROLE_CONFIG = 'config'

BUILD_MAP_ROLES = frozenset(
    {
        ROLE_PRODUCTION,
        ROLE_TEST,
        ROLE_DOCUMENTATION,
        ROLE_CONFIG,
    }
)
"""Closed set of file-role names a classify_globs() explicit route may declare.
The single source of truth shared by ExtensionBase.classify_globs() /
derive_globs_from_tree(), the domain extension route declarations, and their
tests."""


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
