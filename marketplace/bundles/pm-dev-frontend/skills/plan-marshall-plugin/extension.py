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

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'javascript',
                'name': 'JavaScript Development',
                'description': 'Modern JavaScript, ESLint, Jest testing, npm builds',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-frontend:cui-javascript',
                            'description': 'Core JavaScript development standards covering ES modules, modern patterns, and code quality',
                        },
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-frontend:js-fix-jsdoc',
                            'description': 'Fix JSDoc errors and warnings from build/lint with content preservation',
                        },
                        {
                            'skill': 'pm-dev-frontend:cui-javascript-project',
                            'description': 'JavaScript project structure, package.json configuration, and Maven integration',
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
                            'skill': 'pm-dev-frontend:js-enforce-eslint',
                            'description': 'ESLint, Prettier, and Stylelint configuration and enforcement with systematic fixing',
                        },
                    ],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-module-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-frontend:cui-cypress',
                            'description': 'Cypress E2E testing standards including framework adaptations and best practices',
                        }
                    ],
                },
                'quality': {'defaults': [], 'optionals': []},
            },
        }

    def applies_to_module(self, module_data: dict) -> dict:
        """Check if JavaScript domain applies based on build systems."""
        build_systems = module_data.get('build_systems', [])
        if 'npm' not in build_systems:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        signals = ['build_systems=npm']
        result = self._build_applicable_result('high', signals)

        # Move cypress to optionals if no cypress dependency
        deps = module_data.get('dependencies', [])
        dep_strings = [d if isinstance(d, str) else '' for d in deps]
        has_cypress = any('cypress' in d for d in dep_strings)
        if not has_cypress:
            for profile in result['skills_by_profile'].values():
                cypress_entries = [e for e in profile.get('defaults', [])
                                   if isinstance(e, dict) and 'cypress' in e.get('skill', '')]
                for entry in cypress_entries:
                    profile['defaults'].remove(entry)
                    if entry not in profile['optionals']:
                        profile['optionals'].append(entry)

        return result

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-frontend:ext-triage-js'
