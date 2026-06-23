#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-npm — the npm/JS file-to-build map.

Owns Axis-B of the extension contract for the npm build system: the
``(pattern, role)`` build_map routes plus the ``classify_paths`` /
``classify_path_specificity`` lookups that the manage-execution-manifest
aggregator and the build_map seed consume. Subclasses
:class:`BuildExtensionBase` (file-to-build only); skill-loading (Axis-A) lives
on the JavaScript domain extension that subclasses ``ExtensionBase``.

The npm build extension claims JS/TS production / test sources (recognising
``.spec.`` / ``.test.`` colocated test files) plus the npm toolchain config
files (``package.json`` / ``tsconfig.json``).
"""

from extension_base import BuildExtensionBase  # type: ignore[import-not-found]


class BuildExtension(BuildExtensionBase):
    """npm/JS build-system file-to-build extension."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The npm build system serves the ``javascript`` domain — the same key the
        ``pm-dev-frontend`` language extension declares, so applicability scoping
        (``applies_to_module`` on the language extension) gates this build system's
        routes. Only the ``key`` is meaningful here; build extensions own no skill
        profiles (that is Axis-A on the language extension).
        """
        return [
            {'domain': {'key': 'javascript', 'name': 'JavaScript', 'description': 'npm build system'}, 'profiles': {}}
        ]

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
        """Classify paths for the npm / JavaScript build system.

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
        """Return the npm build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with ``fnmatch.fnmatch`` by the downstream
        ``manage-execution-manifest`` consumer, where a single ``*`` spans ``/``.
        For each JS/TS suffix the extension declares a broad production route
        (e.g. ``*.js``) plus the more-specific colocated-test routes
        (``*.spec.js`` / ``*.test.js``); the seed aggregator's longest-glob-wins
        specificity comparison routes a ``.spec.`` / ``.test.`` file to ``test``
        even though the broad production glob also matches it. Config files are
        bare-basename routes that match the file at any tree depth (basename
        anywhere), so a ``package.json`` / ``tsconfig.json`` living only in a
        subdirectory is still kept in the seed and matched at build-decision time,
        not only a repo-root instance. See the base classify_globs() contract for
        the route-collection wiring.
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
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
