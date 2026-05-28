#!/usr/bin/env python3
"""Extension API for pm-dev-python bundle.

Slim domain registration providing skill domains, module applicability,
and triage for Python projects.

Build operations (pyproject_build) have moved to plan-marshall:build-pyproject.
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

    # =========================================================================
    # File-type classifier
    # =========================================================================

    # Glob patterns ordered by specificity (highest first). Each tuple is
    # (glob, role, specificity) where specificity is the count of non-wildcard
    # path-segment tokens in the glob. The aggregator resolves multi-extension
    # overlap by comparing specificity values across claiming extensions.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        # Production python under any scripts/ directory.
        ('**/scripts/**/*.py', 'production', 2),
        ('scripts/**/*.py', 'production', 1),
        ('scripts/*.py', 'production', 1),
        # Test python under top-level test/ or tests/.
        ('test/**/*.py', 'test', 1),
        ('tests/**/*.py', 'test', 1),
        ('test/*.py', 'test', 1),
        ('tests/*.py', 'test', 1),
        # Config files.
        ('pyproject.toml', 'config', 1),
        ('uv.lock', 'config', 1),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        """Return (role, specificity) for the first matching glob, or None.

        Patterns are evaluated in declaration order; the first match wins
        within this extension. The aggregator handles cross-extension overlap
        via classify_path_specificity().
        """
        import fnmatch
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Python domain.

        See standards/extension-contract.md § classify_paths() in the
        plan-marshall extension-api skill for the full contract.
        """
        claims: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for path in paths:
            match = self._match_classify(path)
            if match is not None:
                role, _ = match
                claims[role].append(path)
        return claims

    def classify_path_specificity(self, path: str, role: str) -> int:
        match = self._match_classify(path)
        if match is not None and match[0] == role:
            return match[1]
        return 0
