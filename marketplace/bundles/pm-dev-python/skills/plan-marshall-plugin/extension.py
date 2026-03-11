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

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'python',
                'name': 'Python Development',
                'description': 'Modern Python with pyprojectx, ruff, mypy, pytest',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        'pm-dev-python:python-best-practices',
                        {
                            'skill': 'pm-dev-general:dev-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                    ],
                    'optionals': [],
                },
                'implementation': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-general:dev-code-documentation',
                            'description': 'Language-agnostic documentation principles (what/when/how to document)',
                        },
                    ],
                    'optionals': [],
                },
                'module_testing': {
                    'defaults': [
                        'pm-dev-python:python-best-practices',
                        {
                            'skill': 'pm-dev-general:dev-module-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                    ],
                    'optionals': [],
                },
                'quality': {
                    'defaults': ['pm-dev-python:python-best-practices'],
                    'optionals': [],
                },
            },
        }

    def applies_to_module(self, module_data: dict) -> dict:
        """Check if Python domain applies based on .py files in paths."""
        paths = module_data.get('paths', {})
        sources = paths.get('sources', [])
        tests = paths.get('tests', [])
        build_systems = module_data.get('build_systems', [])

        signals = []
        if 'python' in build_systems:
            signals.append('build_systems=python')
        all_paths = sources + tests
        py_paths = [p for p in all_paths if '.py' in str(p) or 'py' in str(p).lower()]
        if py_paths:
            signals.append(f'*.py in {",".join(py_paths[:3])}')

        if not signals:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        confidence = 'high' if 'python' in build_systems else 'medium'
        return self._build_applicable_result(confidence, signals)

    def provides_triage(self) -> str | None:
        """Return triage skill reference (future)."""
        return None  # ext-triage-python to be added later
