#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
        return [
            {
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
                                'skill': 'plan-marshall:ref-code-quality',
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
                                'description': 'Lombok patterns including @Delegate, @Builder, @Value, @Data, @UtilityClass for reducing boilerplate',
                                'requires': 'lombok',
                            },
                            {
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus-specific CDI standards with testing, native image support, and GraalVM reflection configuration',
                                'requires': 'cdi',
                            },
                        ],
                    },
                    'implementation': {
                        'package_source': 'packages',
                        'defaults': [
                            {
                                'skill': 'plan-marshall:ref-code-quality',
                                'description': 'Language-agnostic code quality, refactoring, and documentation principles',
                            },
                        ],
                        'optionals': [
                            {
                                'skill': 'pm-dev-java:java-cdi',
                                'description': 'CDI patterns including constructor injection, scopes, producers, and Quarkus configuration',
                                'requires': 'cdi',
                            },
                            {
                                'skill': 'pm-dev-java:java-maintenance',
                                'description': 'Java code maintenance standards including prioritization, refactoring triggers, and compliance',
                            },
                            {
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus CDI and configuration patterns — use when module uses Quarkus framework',
                                'requires': 'cdi',
                            },
                        ],
                    },
                    'module_testing': {
                        'package_source': 'test_packages',
                        'defaults': [
                            {
                                'skill': 'pm-dev-java:junit-core',
                                'description': 'JUnit 5 testing patterns with AAA structure, coverage analysis, and assertion standards',
                            },
                            {
                                'skill': 'plan-marshall:persona-module-tester',
                                'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                            },
                        ],
                        'optionals': [
                            {
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus-specific CDI standards with testing, native image support, and GraalVM reflection configuration',
                                'requires': 'cdi',
                            },
                            {
                                'skill': 'pm-dev-java:junit-integration',
                                'description': 'Maven integration testing with Failsafe plugin, IT naming conventions, and profiles',
                            },
                            {
                                'skill': 'pm-dev-java:junit-weld-testing',
                                'description': 'Weld Testing standards for CDI unit testing with @EnableAutoWeld and auto-discovery patterns',
                                'requires': 'cdi',
                            },
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
                    'security': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-java:java-security',
                                'description': 'Java application security — inbound input validation, secure logging, secrets handling, and security anti-patterns',
                            }
                        ],
                        'optionals': [],
                    },
                },
            }
        ]

    def _detect_applicable_profiles(self, profiles: dict, module_data: dict | None) -> set[str] | None:
        """Detect applicable profiles based on Maven/Gradle module signals."""
        if module_data is None:
            return None

        applicable = {'implementation', 'module_testing', 'quality'}

        # Check for integration test signals
        metadata = module_data.get('metadata') or {}
        raw_profiles = metadata.get('profiles') or []
        # Profiles may be dicts ({"id": "...", "canonical": "..."}) or strings
        maven_profiles = [
            p.get('id', '') if isinstance(p, dict) else (p if isinstance(p, str) else '') for p in raw_profiles
        ]
        module_name = module_data.get('name', '')
        deps = module_data.get('dependencies') or []
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

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if Java domain applies based on build systems."""
        build_systems = module_data.get('build_systems') or []
        if 'maven' not in build_systems and 'gradle' not in build_systems:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        signals = [f'build_systems={",".join(build_systems)}']
        result = self._build_applicable_result(
            'high', signals, module_data=module_data, active_profiles=active_profiles
        )

        # Module-level customization: conditionally default CDI/Lombok based on deps.
        # java-cdi/java-lombok are statically declared in optionals (the dep-absent
        # baseline). When the corresponding dependency is present, promote the skill
        # from optionals to defaults so it always loads; when absent, demote any
        # default occurrence back to optionals (keeping the two paths symmetric).
        has_cdi, has_lombok = self._module_dependency_flags(module_data)

        for profile in result['skills_by_profile'].values():
            self._apply_conditional_default(profile, 'java-cdi', present=has_cdi)
            self._apply_conditional_default(profile, 'java-lombok', present=has_lombok)

        return result

    @staticmethod
    def _module_dependency_flags(module_data: dict) -> tuple[bool, bool]:
        """Return ``(has_cdi, has_lombok)`` for the module's declared dependencies.

        Reads the resolved ``dependencies`` list when present (the enrich path)
        and otherwise the cheap crawl's ``declared_dependencies``. Entries may be
        strings (``group:artifact``) or the parser's ``{group_id, artifact_id}``
        dicts. ``io.quarkus:quarkus-arc`` is CDI on its own — Quarkus ArC is the
        CDI implementation — without implying CDI for every ``io.quarkus``
        artifact.
        """
        raw = module_data.get('dependencies') or module_data.get('declared_dependencies') or []
        dep_strings: list[str] = []
        for dep in raw:
            if isinstance(dep, str):
                dep_strings.append(dep)
            elif isinstance(dep, dict):
                dep_strings.append(f'{dep.get("group_id") or ""}:{dep.get("artifact_id") or ""}')
        has_quarkus_arc = any(d.split(':', 2)[:2] == ['io.quarkus', 'quarkus-arc'] for d in dep_strings)
        has_cdi = has_quarkus_arc or any('jakarta.enterprise' in d or 'javax.enterprise' in d for d in dep_strings)
        has_lombok = any('lombok' in d for d in dep_strings)
        return has_cdi, has_lombok

    def _declared_requirement(self, skill: str) -> str | None:
        """Return the ``requires`` marker a skill declaration carries, if any.

        The CDI/Lombok-gated optionals declare ``'requires': 'cdi'`` /
        ``'requires': 'lombok'`` on their ``get_skill_domains()`` entries, so the
        gated set is derived from the declarations rather than duplicated in a
        hand-maintained list.
        """
        for domain_info in self.get_skill_domains():
            for profile_data in (domain_info.get('profiles') or {}).values():
                entries = list(profile_data.get('defaults', [])) + list(profile_data.get('optionals', []))
                for entry in entries:
                    if isinstance(entry, dict) and entry.get('skill') == skill and entry.get('requires'):
                        return str(entry['requires'])
        return None

    def qualifies_optional(self, profile: str, skill: str, module_data: dict) -> bool:
        """Qualify an optional through the ``requires`` marker on its declaration.

        Skills declaring ``requires: cdi`` apply only to a module carrying a CDI
        signal; ``requires: lombok`` only to a Lombok module. Every optional
        without a marker is module-agnostic and stays applicable.
        """
        requirement = self._declared_requirement(skill)
        if requirement is None:
            return True
        has_cdi, has_lombok = self._module_dependency_flags(module_data)
        if requirement == 'cdi':
            return has_cdi
        if requirement == 'lombok':
            return has_lombok
        return True

    @staticmethod
    def _apply_conditional_default(profile: dict, skill_marker: str, present: bool) -> None:
        """Promote a skill to defaults when its dependency is present, else demote it.

        Both directions are no-ops when the entry is already in the target list.
        """
        defaults = profile.setdefault('defaults', [])
        optionals = profile.setdefault('optionals', [])
        source, target = (optionals, defaults) if present else (defaults, optionals)
        moved = [e for e in source if isinstance(e, dict) and skill_marker in e.get('skill', '')]
        for entry in moved:
            source.remove(entry)
            if entry not in target:
                target.append(entry)

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'

    def provides_arch_gate(self) -> dict | None:
        """ArchUnit: Java arch-gate tool. Binding: pm-dev-java:arch-gate-java."""
        return {'tool': 'archunit'}

    def provides_file_globs(self) -> list[str]:
        """Declare the Java source glob — the file type this domain owns.

        Java source is the whole of this domain's file-type identity: its skills are
        Java-language standards, so a plan touching a ``.java`` file wants them and a
        plan touching nothing else does not. The build descriptors this domain's
        modules also carry (``pom.xml`` / ``build.gradle``) are deliberately absent:
        they belong to the Maven and Gradle build systems under ADR-004, and
        claiming them here would union the Java domain into every build-config
        change. Written in the ``file_globs`` dialect, where a leading ``**/``
        matches zero or more path segments.
        """
        return ['**/*.java']
