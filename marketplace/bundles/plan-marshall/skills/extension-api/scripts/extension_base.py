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
        def get_skill_domains(self) -> list[dict]:
            return [{"domain": {...}, "profiles": {...}}]

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
    def get_skill_domains(self) -> list[dict]:
        """Return all skill domains this extension provides.

        Returns:
            List of domain dicts. Each dict has domain identity and
            profile-based skill organization:
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

        Most extensions return a single-element list. Multi-domain extensions
        (e.g., plan-marshall providing both 'build' and 'general-dev') return
        multiple elements.

        Skill Reference Format:
            Each skill entry in defaults/optionals can be either:
            - Object format (preferred): {"skill": "bundle:skill", "description": "..."}
            - String format (legacy): "bundle:skill"

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
            List of module dicts. See module-discovery.md for complete
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
        """Configure project-specific defaults in marshal.json.

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

        See standards/extension-contract.md for complete documentation.
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
            Loaded by the workflow-outline-change-type skill (via
            phase-3-outline skill). Provides domain-specific outline
            instructions instead of generic plan-marshall:workflow-outline-change-type
            standards.

        Fallback:
            If a domain returns None, generic instructions from
            plan-marshall:workflow-outline-change-type/standards/change-{type}.md
            are used.
        """
        return None

    def provides_recipes(self) -> list[dict]:
        """Return recipe definitions this extension provides.

        Recipes are predefined, repeatable transformations that bypass
        change-type detection and provide their own discovery, analysis,
        and deliverable patterns.

        Returns:
            List of recipe dicts, each containing:
            - key: str — Unique recipe identifier (e.g., 'refactor-to-profile-standards')
            - name: str — Human-readable display name
            - description: str — Description for recipe selection UI
            - skill: str — Fully-qualified skill reference (e.g., 'bundle:recipe-skill')
            - default_change_type: str — Change type for outline phase (e.g., 'tech_debt')
            - scope: str — Scope indicator (e.g., 'codebase_wide', 'module')

            Optional fields (set by user at plan creation time if omitted):
            - profile: str — Target profile (e.g., 'implementation', 'module_testing')
            - package_source: str — Package source (e.g., 'packages', 'test_packages')

        Notes:
            - The domain is auto-assigned from get_skill_domains() first entry
            - The source is auto-assigned as 'extension'
            - Default implementation returns empty list (no recipes)
        """
        return []

    def provides_verify_steps(self) -> list[dict]:
        """Return domain-specific verification steps for phase-5-execute.

        Each step declares a verification agent that is appended to the
        steps list in marshal.json under plan.phase-5-execute.steps during
        project configuration via /marshall-steward.

        Returns:
            List of step dicts, each containing:
            - name: str — Fully-qualified agent reference used in the steps list
              (e.g., 'pm-dev-java:java-verify-agent')
            - skill: str — Same as name (the fully-qualified agent reference)
            - description: str — Human-readable description for wizard presentation

        Default implementation returns empty list (no domain-specific verify steps).
        """
        return []

    def provides_finalize_steps(self) -> list[dict]:
        """Return domain-specific finalize steps for phase-6-finalize.

        Each step declares a skill that executes during the finalize pipeline.
        Steps are discovered by marshall-steward and added to the user's
        selected steps in marshal.json under plan.phase-6-finalize.steps.

        Returns:
            List of step dicts, each containing:
            - name: str — Step identifier used in the steps list
              (fully-qualified skill notation, e.g., 'pm-dev-java:java-post-pr')
            - skill: str — Same as name (the fully-qualified skill reference)
            - description: str — Human-readable description for wizard presentation

        The step's skill receives --plan-id and --iteration as arguments.

        Default implementation returns empty list (no domain-specific finalize steps).
        """
        return []

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if this domain applies to a specific module and return resolved skills.

        Called during architecture enrichment to determine which skill domains
        apply to a module and what skills they provide. Each extension decides
        based on signals in the module's derived data and can customize which
        skills are defaults vs optionals per module.

        Args:
            module_data: Module dict from derived-data.json containing:
                build_systems, paths, dependencies, packages, metadata, stats
            active_profiles: Optional positive list of profiles to include.
                Overrides signal detection when provided (Layer 2/3).

        Returns:
            {
                'applicable': bool,
                'confidence': 'high' | 'medium' | 'low' | 'none',
                'signals': list[str],
                'additive_to': str | None,  # parent domain key (e.g., 'java')
                'skills_by_profile': {      # only when applicable
                    'implementation': {
                        'defaults': [{'skill': str, 'description': str}],
                        'optionals': [{'skill': str, 'description': str}]
                    },
                    ...
                }
            }

        Default returns not applicable. Override in extensions.
        Implementations typically call self.get_skill_domains() for base profiles,
        then adjust defaults/optionals based on module_data signals.
        """
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }

    def _detect_applicable_profiles(self, profiles: dict,
                                     module_data: dict | None) -> set[str] | None:
        """Detect which profiles are applicable based on module signals.

        Returns set of applicable profile names, or None for no filtering
        (all defined profiles are included). Override in domain extensions
        for signal-based detection.

        Args:
            profiles: Dict of profile definitions from get_skill_domains()
            module_data: Module dict from derived-data.json, or None

        Returns:
            Set of applicable profile names, or None for no filtering.
        """
        return None

    def _build_applicable_result(self, confidence: str, signals: list[str],
                                  additive_to: str | None = None,
                                  module_data: dict | None = None,
                                  active_profiles: set[str] | None = None) -> dict:
        """Helper: build applicable result from own get_skill_domains() profiles.

        Note: Uses first domain entry only. Designed for single-domain extensions.
        Multi-domain extensions (e.g., plan-marshall) should implement applies_to_module
        directly with explicit domain selection.

        Merges 'core' profile into each non-core profile to produce a flat
        skills_by_profile dict ready for consumption.

        Profile filtering (three-layer resolution):
        1. active_profiles (explicit override from config or CLI) wins
        2. _detect_applicable_profiles() (signal-based detection) if no override
        3. All defined profiles if detection returns None

        Args:
            confidence: 'high', 'medium', or 'low'
            signals: List of signal strings explaining why applicable
            additive_to: Parent domain key if this is an additive domain
            module_data: Module dict for signal-based profile detection
            active_profiles: Explicit positive list of profiles to include

        Returns:
            Full applies_to_module result dict with applicable=True
        """
        all_domains = self.get_skill_domains()
        domains = all_domains[0] if all_domains else {}
        profiles = domains.get('profiles', {})
        core = profiles.get('core', {})
        core_defaults = core.get('defaults', [])
        core_optionals = core.get('optionals', [])

        # Determine which profiles are active (three-layer resolution)
        profile_filter: set[str] | None
        if active_profiles is not None:
            profile_filter = active_profiles
        else:
            profile_filter = self._detect_applicable_profiles(profiles, module_data)

        skills_by_profile: dict[str, dict] = {}
        for profile_name in ['implementation', 'module_testing', 'integration_testing',
                             'quality', 'documentation']:
            if profile_name not in profiles:
                continue
            if profile_filter is not None and profile_name not in profile_filter:
                continue
            profile = profiles[profile_name]
            merged_defaults = list(core_defaults) + list(profile.get('defaults', []))
            merged_optionals = list(core_optionals) + list(profile.get('optionals', []))
            if merged_defaults or merged_optionals:
                skills_by_profile[profile_name] = {
                    'defaults': merged_defaults,
                    'optionals': merged_optionals,
                }
        return {
            'applicable': True,
            'confidence': confidence,
            'signals': signals,
            'additive_to': additive_to,
            'skills_by_profile': skills_by_profile,
        }

