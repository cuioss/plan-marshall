#!/usr/bin/env python3
"""Public API for extension.py implementations.

This module is the single public interface for domain bundle extensions.
All extension needs are available through this module.

Provides:
    - ExtensionBase: Abstract base class for extensions
    - Module discovery utilities: discover_descriptors, build_module_base, find_readme
    - Canonical command constants: CMD_*, CANONICAL_COMMANDS, PROFILE_PATTERNS

Usage:
    from extension_base import ExtensionBase, discover_descriptors, build_module_base

    class Extension(ExtensionBase):
        def get_skill_domains(self) -> dict:
            return {"domain": {...}, "profiles": {...}}

        def discover_modules(self, project_root: str) -> list:
            descriptors = discover_descriptors(project_root, "pom.xml")
            modules = []
            for desc in descriptors:
                base = build_module_base(project_root, str(desc))
                modules.append(base.to_dict())
            return modules
"""

from abc import ABC, abstractmethod

# Re-export module discovery utilities from private implementation
from _build_discover import (  # noqa: F401
    EXCLUDE_DIRS,
    README_PATTERNS,
    ModuleBase,
    ModulePaths,
    build_module_base,
    discover_descriptors,
    find_readme,
)

# =============================================================================
# Canonical Command Constants
# =============================================================================

CMD_CLEAN = 'clean'
CMD_COMPILE = 'compile'
CMD_TEST_COMPILE = 'test-compile'
CMD_MODULE_TESTS = 'module-tests'
CMD_INTEGRATION_TESTS = 'integration-tests'
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
    # Clean phase
    CMD_CLEAN: {
        'phase': 'clean',
        'description': 'Remove build artifacts and generated files',
        'required': False,
    },
    # Build phase
    CMD_COMPILE: {
        'phase': 'build',
        'description': 'Compile production sources only',
        'required': False,
    },
    CMD_TEST_COMPILE: {
        'phase': 'build',
        'description': 'Compile production and test sources',
        'required': False,
    },
    # Test phase
    CMD_MODULE_TESTS: {
        'phase': 'test',
        'description': 'Unit tests for the module (JUnit, Jest, pytest)',
        'required': True,
    },
    CMD_INTEGRATION_TESTS: {
        'phase': 'test',
        'description': 'Integration tests (containers, external services)',
        'required': False,
        'aliases': [
            'integration-tests',
            'integration-test',
            'integrationTest',
            'it',
            'e2e',
            'acceptance',
        ],
    },
    CMD_COVERAGE: {
        'phase': 'test',
        'description': 'Test execution with coverage measurement',
        'required': False,
        'aliases': ['coverage', 'jacoco'],
    },
    CMD_BENCHMARK: {
        'phase': 'test',
        'description': 'Benchmark/performance tests (JMH, k6, wrk)',
        'required': False,
        'aliases': [
            'performance',
            'benchmarks',
            'jmh',
            'perf',
            'stress',
            'load',
        ],
    },
    # Quality phase
    CMD_QUALITY_GATE: {
        'phase': 'quality',
        'description': 'Static analysis, linting, formatting checks',
        'required': True,
        'aliases': [
            'pre-commit',
            'precommit',
            'sonar',
            'lint',
            'check',
            'quality',
        ],
    },
    # Verify phase
    CMD_VERIFY: {
        'phase': 'verify',
        'description': 'Full verification (compile + test + quality)',
        'required': True,
    },
    # Deploy phase
    CMD_INSTALL: {
        'phase': 'deploy',
        'description': 'Install artifact to local repository',
        'required': False,
    },
    CMD_CLEAN_INSTALL: {
        'phase': 'deploy',
        'description': 'Clean build artifacts then install to local repository',
        'required': False,
    },
    CMD_PACKAGE: {
        'phase': 'deploy',
        'description': 'Create deployable artifact (jar, war, native)',
        'required': False,
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


class ExtensionBase(ABC):
    """Abstract base class for domain bundle extensions.

    Subclasses must implement:
        - get_skill_domains: Domain metadata and skill profiles

    All other methods have sensible defaults.
    Build bundles should override discover_modules() for module discovery.
    """

    # =========================================================================
    # Required Methods (must be implemented)
    # =========================================================================

    @abstractmethod
    def get_skill_domains(self) -> dict:
        """Return domain metadata for skill loading.

        Returns:
            Dict with domain identity and profile-based skill organization:
            {
                "domain": {
                    "key": str,          # Unique domain identifier
                    "name": str,         # Human-readable name
                    "description": str   # Domain description
                },
                "profiles": {
                    "core": {"defaults": [...], "optionals": [...]},
                    "implementation": {"defaults": [...], "optionals": [...]},
                    "module_testing": {"defaults": [...], "optionals": [...]},
                    "quality": {"defaults": [...], "optionals": [...]},
                    "documentation": {"defaults": [...], "optionals": [...]}  # Optional
                }
            }

        Standard Profiles:
            - core: Skills loaded for all profiles (foundation skills)
            - implementation: Code implementation skills
            - module_testing: Unit/module test skills
            - integration_testing: Integration test skills
            - quality: Quality/lint/format skills

        Cross-Domain Profile:
            - documentation: Documentation task skills (AsciiDoc, ADRs, interfaces).
              This profile is detected per-module during architecture enrichment
              when module has doc/*.adoc files. It represents a separate task type
              (like testing), not a variant of implementation.
        """
        pass

    # =========================================================================
    # Module Discovery Methods (override for build bundles)
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules with complete metadata.

        This is the primary API for module discovery. Returns comprehensive
        module information including metadata, dependencies, packages, and stats.

        Args:
            project_root: Absolute path to project root.

        Returns:
            List of module dicts. See build-project-structure.md for complete
            contract including:
            - name, build_systems (array)
            - paths: {module, descriptor, sources, tests, readme}
            - metadata: snake_case fields (artifact_id, group_id, parent as string)
            - packages: object keyed by package name
            - dependencies: strings "groupId:artifactId:scope"
            - stats: {source_files, test_files}
            - commands: resolved canonical command strings

        Notes:
            - Override in build bundles to provide build-system-specific discovery
            - Default implementation returns empty list
            - Delegate to scripts in scripts/ directory for implementation
        """
        return []

    # =========================================================================
    # Configuration Callback (override to set project defaults)
    # =========================================================================

    def config_defaults(self, project_root: str) -> None:  # noqa: B027
        """Configure project-specific defaults in run-configuration.json.

        Called by marshall-steward during initialization, after extension loading
        but before workflow logic accesses configuration. This is the hook for
        extensions to set domain-specific defaults.

        Args:
            project_root: Absolute path to project root directory.

        Returns:
            None (void method)

        Contract:
            - MUST only write values if they don't already exist
            - MUST NOT override user-defined configuration
            - SHOULD use direct import from _config_core module
            - MAY skip silently if no defaults are needed

        Example:
            def config_defaults(self, project_root: str) -> None:
                from _config_core import ext_defaults_set_default
                # set_default returns True if set, False if key already existed
                ext_defaults_set_default("my_bundle.skip_profiles", "itest,native", project_root)

        See standards/config-callback.md for complete documentation.
        """
        pass  # Default no-op implementation

    # =========================================================================
    # Workflow Extension Methods
    # =========================================================================

    def provides_triage(self) -> str | None:
        """Return triage skill reference if available.

        Returns:
            Skill reference as 'bundle:skill' (e.g., 'pm-dev-java:ext-triage-java')
            or None if no triage capability.

        Purpose:
            Triage skills categorize and prioritize findings during
            the plan-finalize phase.
        """
        return None

    def provides_outline_skill(self) -> str | None:
        """Return the domain-specific outline skill reference, or None.

        Returns:
            Skill reference as 'bundle:skill' (e.g.,
            'pm-plugin-development:ext-outline-workflow') or None.

            The skill's standards/change-{type}.md files contain
            domain-specific discovery, analysis, and deliverable
            creation logic. The change_type is passed to the skill
            for internal routing.

        Purpose:
            Loaded by the outline-change-type skill (via
            solution-outline-agent). Provides domain-specific outline
            instructions instead of generic pm-workflow:outline-change-type
            standards.

        Fallback:
            If a domain returns None, generic instructions from
            pm-workflow:outline-change-type/standards/change-{type}.md
            are used.
        """
        return None

    def provides_verify_steps(self) -> list[dict]:
        """Return domain-specific verification steps for phase-5-execute.

        Each step declares a verification agent that can be enabled during
        project configuration via /marshall-steward. Steps are persisted in
        marshal.json under plan.phase-5-execute.verification_domain_steps.{domain_key}.

        Returns:
            List of step dicts, each containing:
            - name: Step identifier (e.g., 'technical_impl')
            - agent: Fully-qualified agent reference (e.g., 'pm-dev-java:java-verify-agent')
            - description: Human-readable description for wizard presentation

        Default implementation returns empty list (no domain-specific verify steps).
        """
        return []
