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
                                'skill': 'plan-marshall:dev-general-code-quality',
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
                        'defaults': [
                            {
                                'skill': 'plan-marshall:dev-general-module-testing',
                                'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                            },
                            {
                                'skill': 'pm-dev-frontend:jest-testing',
                                'description': 'JavaScript unit testing with Jest, DOM testing, mocking, async patterns',
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
        result = self._build_applicable_result(
            'high', signals, module_data=module_data, active_profiles=active_profiles
        )

        return result

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-frontend:ext-triage-js'

    # =========================================================================
    # File-type classifier
    # =========================================================================

    # Test patterns are recognized via filename suffix `.spec.*` / `.test.*`.
    # Source patterns claim *.js, *.mjs, *.ts, *.tsx, *.jsx that are NOT test files.
    _SOURCE_SUFFIXES: tuple[str, ...] = ('.js', '.mjs', '.ts', '.tsx', '.jsx')
    _TEST_TOKENS: tuple[str, ...] = ('.spec.', '.test.')
    _CONFIG_FILES: tuple[str, ...] = (
        'package.json',
        'tsconfig.json',
    )
    _CONFIG_PREFIXES: tuple[str, ...] = ('eslint.config.',)

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        # Config files (highest specificity — exact filename match).
        filename = path.rsplit('/', 1)[-1]
        if filename in self._CONFIG_FILES:
            return 'config', 1
        for prefix in self._CONFIG_PREFIXES:
            if filename.startswith(prefix):
                return 'config', 1
        # Test patterns — *.spec.* / *.test.* with a JS/TS extension.
        if any(token in filename for token in self._TEST_TOKENS):
            for ext in self._SOURCE_SUFFIXES:
                if filename.endswith(ext):
                    return 'test', 1
        # Production source — JS/TS suffix and NOT a test file.
        for ext in self._SOURCE_SUFFIXES:
            if filename.endswith(ext):
                return 'production', 1
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the JavaScript / frontend domain.

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
        """Return the JS/TS domain's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with ``fnmatch.fnmatch`` by the downstream
        ``manage-execution-manifest`` consumer, where a single ``*`` spans ``/``.
        For each JS/TS suffix the domain declares a broad production route
        (e.g. ``*.js``) plus the more-specific colocated-test routes
        (``*.spec.js`` / ``*.test.js``); the seed aggregator's longest-glob-wins
        specificity comparison routes a ``.spec.`` / ``.test.`` file to ``test``
        even though the broad production glob also matches it. Config files are
        claimed by exact basename. See the base classify_globs() contract for the
        route-collection wiring.
        """
        routes: list[tuple[str, str]] = []
        # Production source — broad per-suffix route (a single ``*`` spans ``/``,
        # so ``*.js`` covers JS anywhere in the tree).
        for ext in self._SOURCE_SUFFIXES:
            routes.append((f'*{ext}', 'production'))
        # Test source — the colocated ``.spec.`` / ``.test.`` infix forms per
        # suffix (e.g. ``*.spec.js``). These are more specific than the broad
        # production glob, so the aggregator routes the overlap to ``test``.
        for ext in self._SOURCE_SUFFIXES:
            for token in self._TEST_TOKENS:
                routes.append((f'*{token}{ext.lstrip(".")}', 'test'))
        # Config — exact filenames the JS toolchain reads.
        for name in self._CONFIG_FILES:
            routes.append((name, 'config'))
        return routes

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the ExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
