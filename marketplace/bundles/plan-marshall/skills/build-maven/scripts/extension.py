#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-maven — the Maven file-to-build map.

Owns Axis-B of the extension contract for the Maven build system: the
``(pattern, role)`` build_map routes plus the ``classify_paths`` /
``classify_path_specificity`` lookups that the manage-execution-manifest
aggregator and the build_map seed consume. Subclasses
:class:`BuildExtensionBase` (file-to-build only); skill-loading (Axis-A) lives
on the Java domain extension that subclasses ``ExtensionBase``.

The Maven build extension claims Java production / test sources under the
``src/main`` and ``src/test`` convention, the Maven-standard resource trees
(``src/main/resources`` → production, ``src/test/resources`` → test, whatever
the resource's extension), shell scripts by bare basename (``*.sh`` → config),
plus the ``pom.xml`` reactor descriptor. Gradle descriptors are owned by the
sibling build-gradle extension.
"""

import fnmatch

from extension_base import BuildExtensionBase


class BuildExtension(BuildExtensionBase):
    """Maven build-system file-to-build extension."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The Maven build system serves the ``java`` domain — the same key the
        ``pm-dev-java`` language extension declares. build-maven and build-gradle
        both serve ``java``; the route deriver MERGES their routes under that key.
        Applicability scoping gates on the language extension's
        ``applies_to_module``. Only the ``key`` is meaningful here.
        """
        return [{'domain': {'key': 'java', 'name': 'Java', 'description': 'Maven build system'}, 'profiles': {}}]

    # Glob patterns ordered by specificity (highest first). Each tuple is
    # (glob, role, specificity) where specificity is the count of non-wildcard
    # path-segment tokens in the glob. Matching is first-match-wins, so row
    # order carries the routing: the Maven-standard resource trees
    # (specificity 3) sit ABOVE the ``src/main`` / ``src/test`` java rows
    # (specificity 2), claiming every file under ``src/main/resources`` as
    # production and under ``src/test/resources`` as test regardless of
    # extension. The bare-basename ``*.sh`` config route is the FINAL row
    # (specificity 0) — below the ``pom.xml`` descriptor rows — so a shell
    # script inside a resource tree (``src/main/resources/bin/run.sh``) still
    # resolves to that tree's role, and only a script outside any claimed tree
    # (``build.sh``, ``scripts/release.sh``) falls through to config.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        ('**/src/main/resources/**', 'production', 3),
        ('src/main/resources/**', 'production', 3),
        ('**/src/test/resources/**', 'test', 3),
        ('src/test/resources/**', 'test', 3),
        ('**/src/main/**/*.java', 'production', 2),
        ('src/main/**/*.java', 'production', 2),
        ('**/src/test/**/*.java', 'test', 2),
        ('src/test/**/*.java', 'test', 2),
        ('**/pom.xml', 'config', 1),
        ('pom.xml', 'config', 1),
        ('*.sh', 'config', 0),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Maven build system.

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
        """Return the Maven build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with ``fnmatch.fnmatch`` by the downstream
        ``manage-execution-manifest`` consumer, where a single ``*`` spans ``/``,
        so the ``src/main`` / ``src/test`` Maven convention splits production from
        test by location: ``*/src/main/*.java`` covers every production source
        under any module's ``src/main`` tree (the leading ``*/`` admits the
        nested-module layout) and ``src/main/*.java`` covers the repo-root
        single-module layout; the parallel ``src/test`` routes claim test
        sources. The Maven-standard resource trees are routed the same way and
        listed first: ``*/src/main/resources/*`` and ``src/main/resources/*``
        claim resources under ``production``, the parallel ``src/test/resources``
        routes claim them under ``test`` — extension-independent, since a
        resource's role follows its tree, not its suffix. The bare ``pom.xml``
        reactor descriptor is a basename-only route under ``config``: it matches
        the descriptor at any tree depth (every module's ``pom.xml``), not only a
        repo-root instance. The bare-basename ``*.sh`` route claims shell scripts
        under ``config`` and is listed LAST so a script inside a resource tree
        keeps that tree's role. See the base classify_globs() contract for the
        route-collection wiring.
        """
        return [
            ('*/src/main/resources/*', 'production'),
            ('src/main/resources/*', 'production'),
            ('*/src/test/resources/*', 'test'),
            ('src/test/resources/*', 'test'),
            ('*/src/main/*.java', 'production'),
            ('src/main/*.java', 'production'),
            ('*/src/test/*.java', 'test'),
            ('src/test/*.java', 'test'),
            ('pom.xml', 'config'),
            ('*.sh', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
