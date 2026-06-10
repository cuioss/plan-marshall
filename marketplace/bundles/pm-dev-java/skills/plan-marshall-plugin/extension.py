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
                            {
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus-specific CDI standards with testing, native image support, and GraalVM reflection configuration',
                            },
                        ],
                    },
                    'implementation': {
                        'defaults': [
                            {
                                'skill': 'plan-marshall:dev-general-code-quality',
                                'description': 'Language-agnostic code quality, refactoring, and documentation principles',
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
                            {
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus CDI and configuration patterns — use when module uses Quarkus framework',
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
                                'skill': 'pm-dev-java:java-quarkus',
                                'description': 'Quarkus-specific CDI standards with testing, native image support, and GraalVM reflection configuration',
                            },
                            {
                                'skill': 'pm-dev-java:junit-integration',
                                'description': 'Maven integration testing with Failsafe plugin, IT naming conventions, and profiles',
                            },
                            {
                                'skill': 'pm-dev-java:junit-weld-testing',
                                'description': 'Weld Testing standards for CDI unit testing with @EnableAutoWeld and auto-discovery patterns',
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

        # Module-level customization: move CDI/Lombok to optionals based on deps
        deps = module_data.get('dependencies') or []
        dep_strings = [d if isinstance(d, str) else '' for d in deps]
        has_cdi = any('jakarta.enterprise' in d or 'javax.enterprise' in d for d in dep_strings)
        has_lombok = any('lombok' in d for d in dep_strings)

        for profile in result['skills_by_profile'].values():
            if not has_cdi:
                cdi_entries = [
                    e for e in profile.get('defaults', []) if isinstance(e, dict) and 'java-cdi' in e.get('skill', '')
                ]
                for entry in cdi_entries:
                    profile['defaults'].remove(entry)
                    if entry not in profile['optionals']:
                        profile['optionals'].append(entry)
            if not has_lombok:
                lombok_entries = [
                    e
                    for e in profile.get('defaults', [])
                    if isinstance(e, dict) and 'java-lombok' in e.get('skill', '')
                ]
                for entry in lombok_entries:
                    profile['defaults'].remove(entry)
                    if entry not in profile['optionals']:
                        profile['optionals'].append(entry)

        return result

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'

    # =========================================================================
    # File-type classifier
    # =========================================================================

    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        ('**/src/main/**/*.java', 'production', 2),
        ('src/main/**/*.java', 'production', 2),
        ('**/src/test/**/*.java', 'test', 2),
        ('src/test/**/*.java', 'test', 2),
        ('**/pom.xml', 'config', 1),
        ('pom.xml', 'config', 1),
        ('**/build.gradle', 'config', 1),
        ('build.gradle', 'config', 1),
        ('**/build.gradle.kts', 'config', 1),
        ('build.gradle.kts', 'config', 1),
        ('**/settings.gradle', 'config', 1),
        ('settings.gradle', 'config', 1),
        ('**/settings.gradle.kts', 'config', 1),
        ('settings.gradle.kts', 'config', 1),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        import fnmatch
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Java domain.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract.
        """
        claims: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for path in paths:
            match = self._match_classify(path)
            if match is not None:
                claims[match[0]].append(path)
        return claims

    def classify_path_specificity(self, path: str, role: str) -> int:
        match = self._match_classify(path)
        if match is not None and match[0] == role:
            return match[1]
        return 0

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return the Java domain's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with ``fnmatch.fnmatch`` by the downstream
        ``manage-execution-manifest`` consumer, where a single ``*`` spans ``/``,
        so the ``src/main`` / ``src/test`` Maven-Gradle convention splits
        production from test by location: ``*/src/main/*.java`` covers every
        production source under any module's ``src/main`` tree (the leading
        ``*/`` admits the nested-module layout) and ``src/main/*.java`` covers the
        repo-root single-module layout; the parallel ``src/test`` routes claim
        test sources. The Maven / Gradle build descriptors are claimed by exact
        basename under ``config``. See the base classify_globs() contract for the
        route-collection wiring.
        """
        return [
            ('*/src/main/*.java', 'production'),
            ('src/main/*.java', 'production'),
            ('*/src/test/*.java', 'test'),
            ('src/test/*.java', 'test'),
            ('pom.xml', 'config'),
            ('build.gradle', 'config'),
            ('build.gradle.kts', 'config'),
            ('settings.gradle', 'config'),
            ('settings.gradle.kts', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the ExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
