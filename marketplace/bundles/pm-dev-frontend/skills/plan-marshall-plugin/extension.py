#!/usr/bin/env python3
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
        return [{
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
                            'description': 'Core JavaScript development standards covering ES modules, modern patterns, and code quality',
                        },
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                    ],
                    'optionals': [],
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
                            'skill': 'pm-dev-frontend:js-enforce-eslint',
                            'description': 'ESLint, Prettier, and Stylelint configuration and enforcement with systematic fixing',
                        },
                        {
                            'skill': 'pm-dev-frontend:css',
                            'description': 'Modern CSS standards covering essentials, responsive design, quality practices, and tooling',
                        },
                    ],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-module-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                        {
                            'skill': 'pm-dev-frontend:js-testing',
                            'description': 'JavaScript unit testing with Jest/Vitest, DOM testing, mocking, async patterns',
                        },
                    ],
                    'optionals': [],
                },
            },
        }]

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if JavaScript domain applies based on build systems."""
        build_systems = module_data.get('build_systems', [])
        if 'npm' not in build_systems:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        signals = ['build_systems=npm']
        result = self._build_applicable_result('high', signals,
                                                module_data=module_data,
                                                active_profiles=active_profiles)

        return result

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-frontend:ext-triage-js'
