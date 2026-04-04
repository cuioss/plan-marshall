#!/usr/bin/env python3
"""Extension API for pm-dev-python bundle.

Slim domain registration providing skill domains, module applicability,
and triage for Python projects.

Build operations (python_build) have moved to plan-marshall:build-python.
Module discovery is in plan-marshall:plan-marshall-plugin.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Python domain extension for pm-dev-python bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'python',
                    'name': 'Python Development',
                    'description': 'Modern Python with pyprojectx, ruff, mypy, pytest',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
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
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
                            },
                            {
                                'skill': 'plan-marshall:dev-general-code-quality',
                                'description': 'Language-agnostic code quality, refactoring, and documentation principles',
                            },
                        ],
                        'optionals': [],
                    },
                    'module_testing': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:pytest-testing',
                                'description': 'Pytest standards — fixtures, isolation, mocking, assertions, coverage',
                            },
                            {
                                'skill': 'plan-marshall:dev-general-module-testing',
                                'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                            },
                        ],
                        'optionals': [],
                    },
                    'quality': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
                            },
                        ],
                        'optionals': [],
                    },
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if Python domain applies based on .py files in paths."""
        paths = module_data.get('paths', {})
        sources = paths.get('sources', [])
        tests = paths.get('tests', [])
        build_systems = module_data.get('build_systems', [])

        signals = []
        if 'python' in build_systems:
            signals.append('build_systems=python')
        all_paths = sources + tests
        py_paths = [p for p in all_paths if str(p).endswith('.py') or '/py/' in str(p) or str(p).endswith('/py')]
        if py_paths:
            signals.append(f'*.py in {",".join(py_paths[:3])}')

        if not signals:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        confidence = 'high' if 'python' in build_systems else 'medium'
        return self._build_applicable_result(
            confidence, signals, module_data=module_data, active_profiles=active_profiles
        )

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-python:ext-triage-python'
