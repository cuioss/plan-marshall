#!/usr/bin/env python3
"""Extension API for pm-dev-java bundle.

Slim domain registration providing skill domains, module applicability,
triage, verification steps, and recipe definitions for Java projects.

Build operations (Maven/Gradle) have moved to plan-marshall:build-maven
and plan-marshall:build-gradle. Module discovery is in
plan-marshall:plan-marshall-plugin.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Java domain extension for pm-dev-java bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
            'domain': {
                'key': 'java',
                'name': 'Java Development',
                'description': 'Java code patterns, CDI, JUnit testing, Maven/Gradle builds',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:java-core',
                            'description': 'Core Java patterns including modern features and performance optimization',
                        },
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:java-null-safety',
                            'description': 'JSpecify null safety annotations with @NullMarked, @Nullable, and package-level configuration',
                        },
                        {
                            'skill': 'pm-dev-java:java-lombok',
                            'description': 'Lombok patterns including @Delegate, @Builder, @Value, @UtilityClass for reducing boilerplate',
                        },
                    ],
                },
                'implementation': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-code-documentation',
                            'description': 'Language-agnostic documentation principles (what/when/how to document)',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:java-cdi',
                            'description': 'CDI patterns including constructor injection, scopes, producers, and Quarkus configuration',
                        },
                        {
                            'skill': 'pm-dev-java:java-maintenance',
                            'description': 'Java code maintenance standards including prioritization, refactoring triggers, and compliance',
                        },
                    ],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:junit-core',
                            'description': 'JUnit 5 testing patterns with AAA structure, coverage analysis, and assertion standards',
                        },
                        {
                            'skill': 'plan-marshall:dev-general-module-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:junit-integration',
                            'description': 'Maven integration testing with Failsafe plugin, IT naming conventions, and profiles',
                        }
                    ],
                },
                'quality': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:javadoc',
                            'description': 'JavaDoc documentation standards including class, method, and code example patterns',
                        }
                    ],
                    'optionals': [],
                },
            },
        }]

    def _detect_applicable_profiles(self, profiles: dict,
                                     module_data: dict | None) -> set[str] | None:
        """Detect applicable profiles based on Maven/Gradle module signals."""
        if module_data is None:
            return None

        applicable = {'implementation', 'module_testing', 'quality'}

        # Check for integration test signals
        metadata = module_data.get('metadata', {})
        maven_profiles = metadata.get('profiles', [])
        module_name = module_data.get('name', '')
        deps = module_data.get('dependencies', [])
        dep_strings = [d if isinstance(d, str) else '' for d in deps]

        has_it_signals = (
            any('integration' in p.lower() for p in maven_profiles)
            or any('failsafe' in d for d in dep_strings)
            or any('testcontainers' in d for d in dep_strings)
            or 'integration' in module_name.lower()
        )
        if has_it_signals and 'integration_testing' in profiles:
            applicable.add('integration_testing')

        return applicable

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if Java domain applies based on build systems."""
        build_systems = module_data.get('build_systems', [])
        if 'maven' not in build_systems and 'gradle' not in build_systems:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        signals = [f'build_systems={",".join(build_systems)}']
        result = self._build_applicable_result('high', signals,
                                                module_data=module_data,
                                                active_profiles=active_profiles)

        # Module-level customization: move CDI/Lombok to optionals based on deps
        deps = module_data.get('dependencies', [])
        dep_strings = [d if isinstance(d, str) else '' for d in deps]
        has_cdi = any('jakarta.enterprise' in d or 'javax.enterprise' in d for d in dep_strings)
        has_lombok = any('lombok' in d for d in dep_strings)

        for profile in result['skills_by_profile'].values():
            if not has_cdi:
                cdi_entries = [e for e in profile.get('defaults', [])
                               if isinstance(e, dict) and 'java-cdi' in e.get('skill', '')]
                for entry in cdi_entries:
                    profile['defaults'].remove(entry)
                    if entry not in profile['optionals']:
                        profile['optionals'].append(entry)
            if not has_lombok:
                lombok_entries = [e for e in profile.get('defaults', [])
                                  if isinstance(e, dict) and 'java-lombok' in e.get('skill', '')]
                for entry in lombok_entries:
                    profile['defaults'].remove(entry)
                    if entry not in profile['optionals']:
                        profile['optionals'].append(entry)

        return result

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'

    def provides_verify_steps(self) -> list[dict]:
        """Return Java-specific verification steps."""
        return [
            {
                'name': 'pm-dev-java:java-coverage-agent',
                'skill': 'pm-dev-java:java-coverage-agent',
                'description': 'Verify test coverage meets thresholds',
            },
        ]

