#!/usr/bin/env python3
"""Build extension for plan-marshall:build-pyproject — the Python file-to-build map.

Owns Axis-B of the extension contract for the Python build system: the
``(pattern, role)`` build_map routes plus the ``classify_paths`` /
``classify_path_specificity`` lookups that the manage-execution-manifest
aggregator and the build_map seed consume. Subclasses
:class:`BuildExtensionBase` (file-to-build only); skill-loading (Axis-A) lives
on the language domain extensions that subclass ``ExtensionBase``.

The Python build extension claims ``pyproject.toml`` as config but NOT
``uv.lock`` or ``marshal.json`` — neither lockfile nor marshal config triggers a
Python build, so neither is a build-map config route.
"""

import fnmatch

from extension_base import BuildExtensionBase  # type: ignore[import-not-found]


class BuildExtension(BuildExtensionBase):
    """Python build-system file-to-build extension."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The build_map aggregator keys each build extension's routes by its served
        domain key and resolves the owning extension's ``classify_build_class`` via
        the same key. The Python build system serves the ``python`` domain — the
        same key the ``pm-dev-python`` language extension declares, so applicability
        scoping (``applies_to_module`` on the language extension) gates this build
        system's routes. Only the ``key`` is meaningful here; build extensions own
        no skill profiles (that is Axis-A on the language extension).
        """
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Python build system'}, 'profiles': {}}]

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
        # Config files. The Python build extension claims pyproject.toml only —
        # uv.lock and marshal.json do NOT trigger a Python build, so neither is a
        # build-map config route.
        ('pyproject.toml', 'config', 1),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        """Return (role, specificity) for the first matching glob, or None.

        Patterns are evaluated in declaration order; the first match wins
        within this extension. The aggregator handles cross-extension overlap
        via classify_path_specificity().
        """
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Python build system.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract.
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
        """Return the Python build system's explicit ``(pattern, role)`` build_map routes.

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
        ``.py`` these routes forgot. The sole config route is ``pyproject.toml`` —
        ``uv.lock`` and ``marshal.json`` are deliberately NOT claimed, since
        neither triggers a Python build. See the base classify_globs() contract
        for the route-collection wiring.
        """
        return [
            ('build.py', 'production'),
            ('.claude/skills/*.py', 'production'),
            ('marketplace/bundles/*.py', 'production'),
            ('marketplace/targets/*.py', 'production'),
            ('test/*.py', 'test'),
            ('pyproject.toml', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
