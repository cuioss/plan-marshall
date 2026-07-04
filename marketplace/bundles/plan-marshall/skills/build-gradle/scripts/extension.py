#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-gradle — the Gradle file-to-build map.

Owns Axis-B of the extension contract for the Gradle build system: the
``(pattern, role)`` build_map routes plus the ``classify_paths`` /
``classify_path_specificity`` lookups that the manage-execution-manifest
aggregator and the build_map seed consume. Subclasses
:class:`BuildExtensionBase` (file-to-build only); skill-loading (Axis-A) lives
on the Java domain extension that subclasses ``ExtensionBase``.

The Gradle build extension claims Java production / test sources under the
``src/main`` and ``src/test`` convention plus the Gradle build descriptors
(``build.gradle`` / ``build.gradle.kts`` / ``settings.gradle`` /
``settings.gradle.kts``). The ``pom.xml`` reactor descriptor is owned by the
sibling build-maven extension.
"""

import fnmatch

from extension_base import BuildExtensionBase


class BuildExtension(BuildExtensionBase):
    """Gradle build-system file-to-build extension."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The Gradle build system serves the ``java`` domain — the same key the
        ``pm-dev-java`` language extension declares. build-gradle and build-maven
        both serve ``java``; the route deriver MERGES their routes under that key.
        Applicability scoping gates on the language extension's
        ``applies_to_module``. Only the ``key`` is meaningful here.
        """
        return [{'domain': {'key': 'java', 'name': 'Java', 'description': 'Gradle build system'}, 'profiles': {}}]

    # Glob patterns ordered by specificity (highest first). Each tuple is
    # (glob, role, specificity) where specificity is the count of non-wildcard
    # path-segment tokens in the glob.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        ('**/src/main/**/*.java', 'production', 2),
        ('src/main/**/*.java', 'production', 2),
        ('**/src/test/**/*.java', 'test', 2),
        ('src/test/**/*.java', 'test', 2),
        ('**/build.gradle', 'config', 1),
        ('build.gradle', 'config', 1),
        ('**/build.gradle.kts', 'config', 1),
        ('build.gradle.kts', 'config', 1),
        ('**/settings.gradle', 'config', 1),
        ('settings.gradle', 'config', 1),
        ('**/settings.gradle.kts', 'config', 1),
        ('settings.gradle.kts', 'config', 1),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Gradle build system.

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
        """Return the Gradle build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with ``fnmatch.fnmatch`` by the downstream
        ``manage-execution-manifest`` consumer, where a single ``*`` spans ``/``,
        so the ``src/main`` / ``src/test`` Gradle convention splits production
        from test by location: ``*/src/main/*.java`` covers every production
        source under any subproject's ``src/main`` tree (the leading ``*/`` admits
        the nested-subproject layout) and ``src/main/*.java`` covers the repo-root
        single-project layout; the parallel ``src/test`` routes claim test
        sources. The Gradle build descriptors are claimed by exact basename under
        ``config``. See the base classify_globs() contract for the
        route-collection wiring.
        """
        return [
            ('*/src/main/*.java', 'production'),
            ('src/main/*.java', 'production'),
            ('*/src/test/*.java', 'test'),
            ('src/test/*.java', 'test'),
            ('build.gradle', 'config'),
            ('build.gradle.kts', 'config'),
            ('settings.gradle', 'config'),
            ('settings.gradle.kts', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
