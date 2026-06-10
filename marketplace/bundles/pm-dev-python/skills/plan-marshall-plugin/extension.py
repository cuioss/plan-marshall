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
        paths = module_data.get('paths') or {}
        sources = paths.get('sources') or []
        tests = paths.get('tests') or []
        build_systems = module_data.get('build_systems') or []

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
        # Production python under any scripts/ directory. Both `*/scripts/sub/foo.py`
        # (deep) and `*/scripts/foo.py` (direct child) variants must match — fnmatch's
        # `**/scripts/**/*.py` requires a subdirectory after `scripts/`, so the
        # direct-child pattern is needed alongside.
        ('**/scripts/**/*.py', 'production', 2),
        ('**/scripts/*.py', 'production', 2),
        ('scripts/**/*.py', 'production', 1),
        ('scripts/*.py', 'production', 1),
        # Test python under any test/ or tests/ directory (deep child + direct child).
        ('test/**/*.py', 'test', 1),
        ('tests/**/*.py', 'test', 1),
        ('test/*.py', 'test', 1),
        ('tests/*.py', 'test', 1),
        # Config files.
        ('pyproject.toml', 'config', 1),
        ('uv.lock', 'config', 1),
        ('.plan/marshal.json', 'config', 2),
        ('marshal.json', 'config', 1),
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

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return the python domain's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role
        (``production`` / ``test`` / ``config``). Patterns are matched with
        ``fnmatch.fnmatch`` by the downstream ``manage-execution-manifest``
        consumer, where a single ``*`` spans ``/`` — so ``marketplace/bundles/*.py``
        covers every production ``.py`` anywhere beneath ``marketplace/bundles/``
        and ``test/*.py`` covers every test module beneath ``test/``. The
        production routes enumerate the four roots a plan-marshall ``.py`` can live
        under (``build.py`` at the repo root, ``.claude/skills/``,
        ``marketplace/bundles/``, ``marketplace/targets/``); the git-tracked
        completeness validator (``validate_tree_completeness``) reports any tracked
        ``.py`` these routes forgot. Config files are claimed by exact basename.
        See the base classify_globs() contract for the route-collection wiring.
        """
        return [
            ('build.py', 'production'),
            ('.claude/skills/*.py', 'production'),
            ('marketplace/bundles/*.py', 'production'),
            ('marketplace/targets/*.py', 'production'),
            ('test/*.py', 'test'),
            ('pyproject.toml', 'config'),
            ('uv.lock', 'config'),
            ('marshal.json', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the ExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
