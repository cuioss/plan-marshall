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
        build_systems = module_data.get('build_systems', [])
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
        """Return an explicit (glob, role) inventory synthesized from the rules.

        Hand-rolled extension (no _CLASSIFY_PATTERNS tuple): _match_classify uses
        filename / suffix / token checks, so there is no tuple to derive from.
        The globs below mirror that body exactly — config files (exact names +
        eslint.config.* prefix), test files (*.spec.* / *.test.* paired with each
        JS/TS suffix), then production source (each JS/TS suffix). See the base
        classify_globs() contract.
        """
        globs: list[tuple[str, str]] = []
        # Config — exact filenames and the eslint.config.* prefix family.
        for name in self._CONFIG_FILES:
            globs.append((name, 'config'))
        for prefix in self._CONFIG_PREFIXES:
            globs.append((f'{prefix}*', 'config'))
        # Test — *.spec.* / *.test.* paired with each JS/TS suffix.
        for token in self._TEST_TOKENS:
            for ext in self._SOURCE_SUFFIXES:
                globs.append((f'*{token}*{ext}', 'test'))
        # Production source — each JS/TS suffix not matched as a test/config file.
        for ext in self._SOURCE_SUFFIXES:
            globs.append((f'*{ext}', 'production'))
        return globs

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the ExtensionBase defaults
    # (``production → prod-compile``, ``test → test-run``,
    # ``config → build-config-full``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
