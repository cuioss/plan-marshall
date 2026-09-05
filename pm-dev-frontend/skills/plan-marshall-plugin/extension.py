#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-dev-frontend bundle.

Slim domain registration providing skill domains, module applicability,
and triage for JavaScript projects.

Build operations (npm) have moved to plan-marshall:build-npm.
Module discovery is in plan-marshall:plan-marshall-plugin.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """JavaScript domain extension for pm-dev-frontend bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'javascript',
                    'name': 'JavaScript Development',
                    'description': 'Modern JavaScript, ESLint, Jest testing, npm builds',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-frontend:javascript',
                                'description': 'Core JavaScript development standards covering ES modules, modern patterns, web component patterns, DOM trust boundaries / XSS prevention, and code quality',
                            },
                            {
                                'skill': 'plan-marshall:ref-code-quality',
                                'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                            },
                        ],
                        'optionals': [],
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
                                'skill': 'pm-dev-frontend:lint-config',
                                'description': 'ESLint, Prettier, and Stylelint configuration and enforcement with systematic fixing',
                            },
                            {
                                'skill': 'pm-dev-frontend:css',
                                'description': 'Modern CSS standards covering essentials, responsive design, quality practices, and tooling',
                            },
                        ],
                    },
                    'module_testing': {
                        'package_source': 'test_packages',
                        'defaults': [
                            {
                                'skill': 'plan-marshall:persona-module-tester',
                                'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                            },
                            {
                                'skill': 'pm-dev-frontend:jest-testing',
                                'description': 'JavaScript unit testing with Jest, DOM testing, mocking, async patterns',
                            },
                        ],
                        'optionals': [],
                    },
                    'security': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-frontend:javascript-security',
                                'description': 'JavaScript security — DOM trust boundaries, XSS sinks, sanitization, and Trusted Types',
                            },
                        ],
                        'optionals': [],
                    },
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if JavaScript domain applies based on build systems."""
        build_systems = module_data.get('build_systems') or []
        if 'npm' not in build_systems:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        signals = ['build_systems=npm']
        return self._build_applicable_result(
            'high', signals, module_data=module_data, active_profiles=active_profiles
        )

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-frontend:ext-triage-js'

    def provides_arch_gate(self) -> dict | None:
        """dependency-cruiser: JS arch-gate tool. Binding: pm-dev-frontend:arch-gate-js."""
        return {'tool': 'dependency-cruiser'}

    def provides_file_globs(self) -> list[str]:
        """Declare the JavaScript and CSS source globs this domain owns.

        The bundle's skills cover JavaScript (ES modules, web components, DOM trust
        boundaries) and CSS, so those two file types are its file-type identity.
        TypeScript suffixes are deliberately absent — the npm build system claims
        them for Axis-B routing, but this bundle ships no TypeScript standards, so
        declaring them here would union the domain into plans it has nothing to say
        about. The npm toolchain descriptors (``package.json`` / ``tsconfig.json``)
        are likewise absent: they belong to the npm build system under ADR-004.
        Written in the ``file_globs`` dialect, where a leading ``**/`` matches zero
        or more path segments.
        """
        return ['**/*.js', '**/*.mjs', '**/*.jsx', '**/*.css']
