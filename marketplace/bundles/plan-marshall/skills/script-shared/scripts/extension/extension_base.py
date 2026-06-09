#!/usr/bin/env python3
"""Public API for extension.py implementations.

This module is the single public interface for domain bundle extensions.

Provides:
    - ExtensionBase: Abstract base class for extensions
    - Canonical command constants (re-exported from _extension_constants):
      CMD_*, CANONICAL_COMMANDS, PROFILE_PATTERNS, APPLICABLE_PROFILES
    - Build-class vocabulary (re-exported from _extension_constants):
      BUILD_CLASSES, BUILD_CLASS_*

Module discovery utilities (discover_descriptors, build_module_base, find_readme,
count_source_files, discover_packages, discover_js_sources, discover_sources,
ModuleBase, ModulePaths) are available via direct import from _build_discover.
"""

import os
from abc import ABC, abstractmethod

# Re-export build vocabulary constants from private implementation.
from _extension_constants import (  # noqa: F401 — re-exported for backward compat
    ALL_CANONICAL_COMMANDS,
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_DOCS_VALIDATE,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    CANONICAL_COMMANDS,
    CMD_BENCHMARK,
    CMD_CLEAN,
    CMD_CLEAN_INSTALL,
    CMD_COMPILE,
    CMD_COVERAGE,
    CMD_INSTALL,
    CMD_INTEGRATION_TESTS,
    CMD_MODULE_TESTS,
    CMD_PACKAGE,
    CMD_QUALITY_GATE,
    CMD_TEST_COMPILE,
    CMD_VERIFY,
    HEURISTIC_TO_ROLE,
    PROFILE_PATTERNS,
    ROLE_HEURISTIC_CONFIG,
    ROLE_HEURISTIC_DOCUMENTATION,
    ROLE_HEURISTIC_PRODUCTION_BY_LOCATION,
    ROLE_HEURISTIC_TEST_BY_LOCATION,
    ROLE_HEURISTICS,
)
from _extension_constants import (
    APPLICABLE_PROFILES as _APPLICABLE_PROFILES,
)

# Directories the tree-deriver never descends into when scanning for build_map
# globs — VCS metadata, plan state, build/dependency output, and caches. These
# hold no production / test source that should seed a build_class.
_DERIVE_PRUNED_DIRS: frozenset[str] = frozenset(
    {
        '.git',
        '.plan',
        '.venv',
        'venv',
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'target',
        'dist',
        'build',
        '.idea',
        '.tox',
    }
)

# Path segments that mark a file as living under a test root. A file whose
# repo-relative path contains any of these segments resolves to the ``test``
# role under the ``*-by-location`` heuristics.
_TEST_ROOT_SEGMENTS: frozenset[str] = frozenset({'test', 'tests'})

# Filename infixes that mark a file as a test by naming convention (the JS / TS
# ``*.spec.*`` / ``*.test.*`` convention) regardless of directory. A file
# carrying one of these infixes resolves to the ``test`` role even when it sits
# beside the production source it covers.
_TEST_FILENAME_INFIXES: tuple[str, ...] = ('.spec.', '.test.')


def _is_test_file(rel_path: str) -> bool:
    """Return True when a repo-relative path is a test file by location or naming.

    The location/naming predicate behind the ``*-by-location`` role heuristics. A
    path is a test file when EITHER:

    - any of its segments is ``test`` or ``tests`` (case-insensitive) — the
      directory-root convention (``src/test/java/Foo.java``, ``test/foo_test.py``,
      ``a/tests/b/c.py``); OR
    - its basename carries a ``.spec.`` / ``.test.`` infix — the colocated
      naming convention (``Button.spec.js``, ``util.test.ts``).

    ``scripts/testing_util.py`` is NOT a test file (``testing_util`` is neither a
    bare ``test`` segment nor a ``.spec.`` / ``.test.`` infix).

    Args:
        rel_path: Repo-relative, forward-slash-separated path.

    Returns:
        True when the path is a test file, else False.
    """
    if any(segment.lower() in _TEST_ROOT_SEGMENTS for segment in rel_path.split('/')):
        return True
    basename = rel_path.rsplit('/', 1)[-1]
    return any(infix in basename for infix in _TEST_FILENAME_INFIXES)


def _heuristic_keeps_file(role_heuristic: str, suffix: str, rel_path: str) -> bool:
    """Return True when a tree file is claimed by a (suffix, role_heuristic) entry.

    Couples the suffix predicate with the location/naming predicate the heuristic
    implies:

    - ``production-by-location``: matching suffix AND NOT a test file.
    - ``test-by-location``: matching suffix AND a test file.
    - ``documentation`` / ``config``: matching suffix regardless of location.

    "Test file" is resolved by :func:`_is_test_file` — either under a ``test`` /
    ``tests`` root or carrying a ``.spec.`` / ``.test.`` filename infix.

    Args:
        role_heuristic: One of the four ``ROLE_HEURISTICS`` names.
        suffix: The vocabulary suffix (e.g. ``.py``) or an exact basename
            (e.g. ``pyproject.toml``) the entry claims.
        rel_path: Repo-relative path of the candidate file.

    Returns:
        True when the file is claimed by this entry, else False.
    """
    basename = rel_path.rsplit('/', 1)[-1]
    suffix_matches = basename == suffix or basename.endswith(suffix)
    if not suffix_matches:
        return False
    if role_heuristic == ROLE_HEURISTIC_PRODUCTION_BY_LOCATION:
        return not _is_test_file(rel_path)
    if role_heuristic == ROLE_HEURISTIC_TEST_BY_LOCATION:
        return _is_test_file(rel_path)
    # documentation / config heuristics are location-agnostic.
    return True


def _scan_tree_files(project_root: str) -> list[str]:
    """Return every non-pruned repo-relative file path under ``project_root``.

    Walks the tree once, pruning the directories in ``_DERIVE_PRUNED_DIRS``, and
    returns forward-slash-separated repo-relative paths. The single tree walk is
    shared across all extensions' vocabularies by ``derive_globs_from_tree``.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Sorted list of repo-relative file paths.
    """
    rel_paths: list[str] = []
    root = os.path.abspath(project_root)
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune in place so os.walk does not descend into excluded dirs.
        dirnames[:] = [d for d in dirnames if d not in _DERIVE_PRUNED_DIRS]
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel = os.path.relpath(abs_path, root).replace(os.sep, '/')
            rel_paths.append(rel)
    return sorted(rel_paths)


def derive_globs_from_tree(
    project_root: str, extensions: list
) -> dict[str, list[tuple[str, str]]]:
    """Derive concrete, complete-by-construction ``(glob, role)`` globs per domain.

    The shared base-lib deriver behind the build_map seed. It scans the actual
    project tree ONCE and, for every registered extension's portable
    ``(suffix, role_heuristic)`` vocabulary (``classify_globs()``), emits the
    concrete globs that cover EVERY matching file in the tree. Because the globs
    come from the real tree rather than an author's assumed layout, production
    ``.py`` files outside ``scripts/`` (e.g. ``marketplace/targets/generate.py``
    and every ``*/skills/plan-marshall-plugin/extension.py``) are caught — they
    exist in the tree, not because an author guessed a glob. The seed is
    therefore complete-by-construction.

    The emitted globs are conservative: for each claimed file the deriver emits a
    ``{directory}/*{suffix}`` glob anchored at the file's parent directory (or
    ``{basename}`` for an exact-name config entry). Such a glob matches only files
    of the claimed suffix directly inside that directory, so the derived set
    never over-claims a sibling file the vocabulary did not match. Globs are
    de-duplicated and emitted in deterministic sorted order.

    Args:
        project_root: Absolute path to the project root to scan.
        extensions: List of extension instances (objects exposing
            ``classify_globs()`` and ``get_skill_domains()``). Extensions whose
            ``classify_globs()`` returns an empty vocabulary contribute nothing.

    Returns:
        A dict keyed by domain-key with a list of de-duplicated ``(glob, role)``
        tuples as values. Domains contributing no globs are omitted entirely.
    """
    tree_files = _scan_tree_files(project_root)
    derived: dict[str, list[tuple[str, str]]] = {}

    for ext in extensions:
        try:
            vocabulary = ext.classify_globs()
        except Exception:
            continue
        if not vocabulary:
            continue

        domain_key = ''
        try:
            domains = ext.get_skill_domains()
            if domains:
                domain_key = str(domains[0].get('domain', {}).get('key', '') or '')
        except Exception:
            domain_key = ''
        if not domain_key:
            continue

        # role -> set of derived globs, so multiple vocabulary entries that
        # resolve to the same (glob, role) collapse to one entry.
        role_globs: dict[str, set[str]] = {}
        for suffix, role_heuristic in vocabulary:
            if role_heuristic not in ROLE_HEURISTICS:
                continue
            role = HEURISTIC_TO_ROLE[role_heuristic]
            for rel_path in tree_files:
                if not _heuristic_keeps_file(role_heuristic, suffix, rel_path):
                    continue
                glob = _glob_for_file(rel_path, suffix)
                role_globs.setdefault(role, set()).add(glob)

        entries = sorted(
            ((glob, role) for role, globs in role_globs.items() for glob in globs)
        )
        if entries:
            derived[domain_key] = entries

    return derived


def _glob_for_file(rel_path: str, suffix: str) -> str:
    """Return the conservative glob covering ``rel_path`` for ``suffix``.

    An exact-name config entry (the vocabulary suffix equals the file's
    basename) derives the basename glob verbatim — e.g. ``pyproject.toml`` →
    ``**/pyproject.toml`` is intentionally NOT used; the exact path is emitted so
    only that file is claimed. A suffix entry derives the
    ``{parent_dir}/*{suffix}`` glob anchored at the file's parent directory,
    which matches only same-suffix files directly inside that directory.

    Args:
        rel_path: Repo-relative path of a claimed file.
        suffix: The vocabulary suffix or exact basename that claimed the file.

    Returns:
        A glob string that covers ``rel_path`` and no file the vocabulary did
        not match.
    """
    basename = rel_path.rsplit('/', 1)[-1]
    if basename == suffix:
        # Exact-name entry (config file like pyproject.toml): claim the exact path.
        return rel_path
    parent = rel_path.rsplit('/', 1)[0] if '/' in rel_path else ''
    pattern = f'*{suffix}'
    return f'{parent}/{pattern}' if parent else pattern


class ExtensionBase(ABC):
    """Abstract base class for domain bundle extensions.

    Subclasses must implement:
        - get_skill_domains: Domain metadata and skill profiles

    All other methods have sensible defaults.
    Build bundles should override discover_modules() for module discovery.
    """

    # =========================================================================
    # Required Methods (must be implemented)
    # =========================================================================

    APPLICABLE_PROFILES = _APPLICABLE_PROFILES
    """Profile names iterated during _build_applicable_result(). Does not include 'core'
    which is always merged into each profile."""

    @abstractmethod
    def get_skill_domains(self) -> list[dict]:
        """Return all skill domains this extension provides.

        Returns:
            List of domain dicts. Each dict has domain identity and
            profile-based skill organization:
            {
                "domain": {
                    "key": str,          # Unique domain identifier
                    "name": str,         # Human-readable name
                    "description": str   # Domain description
                },
                "profiles": {
                    "core": {"defaults": [...], "optionals": [...]},
                    "implementation": {"defaults": [...], "optionals": [...]},
                    "module_testing": {"defaults": [...], "optionals": [...]},
                    "quality": {"defaults": [...], "optionals": [...]},
                    "documentation": {"defaults": [...], "optionals": [...]}  # Optional
                }
            }

        Most extensions return a single-element list. Multi-domain extensions
        (e.g., plan-marshall providing both 'build' and 'general-dev') return
        multiple elements.

        Skill Reference Format:
            Each skill entry in defaults/optionals can be either:
            - Object format (preferred): {"skill": "bundle:skill", "description": "..."}
            - String format: "bundle:skill"

        Standard Profiles:
            - core: Skills loaded for all profiles (foundation skills)
            - implementation: Code implementation skills
            - module_testing: Unit/module test skills
            - integration_testing: Integration test skills
            - quality: Quality/lint/format skills

        Cross-Domain Profile:
            - documentation: Documentation task skills (AsciiDoc, ADRs, interfaces).
              This profile is detected per-module during architecture enrichment
              when module has doc/*.adoc files. It represents a separate task type
              (like testing), not a variant of implementation.
        """
        pass

    # =========================================================================
    # Module Discovery Methods (override for build bundles)
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules with complete metadata.

        This is the primary API for module discovery. Returns comprehensive
        module information including metadata, dependencies, packages, and stats.

        Args:
            project_root: Absolute path to project root.

        Returns:
            List of module dicts. See module-discovery.md for complete
            contract including:
            - name, build_systems (array)
            - paths: {module, descriptor, sources, tests, readme}
            - metadata: snake_case fields (artifact_id, group_id, parent as string)
            - packages: object keyed by package name
            - dependencies: strings "groupId:artifactId:scope"
            - stats: {source_files, test_files}
            - commands: resolved canonical command strings

        Notes:
            - Override in build bundles to provide build-system-specific discovery
            - Default implementation returns empty list
            - Delegate to scripts in scripts/ directory for implementation
        """
        return []

    # =========================================================================
    # Configuration Callback (override to set project defaults)
    # =========================================================================

    def config_defaults(self, project_root: str) -> None:  # noqa: B027
        """Configure project-specific defaults in marshal.json.

        Called during project initialization, after extension loading but
        before workflow logic accesses configuration. This is the hook for
        extensions to set domain-specific defaults.

        Args:
            project_root: Absolute path to project root directory.

        Returns:
            None (void method)

        Contract:
            - MUST only write values if they don't already exist
            - MUST NOT override user-defined configuration
            - SHOULD use direct import from _config_core module
            - MAY skip silently if no defaults are needed

        Example:
            def config_defaults(self, project_root: str) -> None:
                from _config_core import ext_defaults_set_default
                # set_default returns True if set, False if key already existed
                ext_defaults_set_default("my_bundle.skip_profiles", "itest,native", project_root)

        See standards/extension-contract.md for complete documentation.
        """
        pass  # Default no-op implementation

    # =========================================================================
    # Workflow Extension Methods
    # =========================================================================

    def provides_triage(self) -> str | None:
        """Return triage skill reference if available.

        Returns:
            Skill reference as 'bundle:skill' (e.g., 'pm-dev-java:ext-triage-java')
            or None if no triage capability.

        Purpose:
            Triage skills categorize and prioritize findings during
            the plan-finalize phase.
        """
        return None

    def provides_outline_skill(self) -> str | None:
        """Return the domain-specific outline skill reference, or None.

        Returns:
            Skill reference as 'bundle:skill' (e.g.,
            'pm-plugin-development:ext-outline-workflow') or None.

            The skill's standards/change-{type}.md files contain
            domain-specific discovery, analysis, and deliverable
            creation logic. The change_type is passed to the skill
            for internal routing.

        Purpose:
            Loaded by the phase-3-outline skill. Provides domain-specific
            outline instructions instead of generic plan-marshall:phase-3-outline
            standards.

        Fallback:
            If a domain returns None, generic instructions from
            plan-marshall:phase-3-outline/standards/change-{type}.md
            are used.
        """
        return None

    def provides_recipes(self) -> list[dict]:
        """Return recipe definitions this extension provides.

        Recipes are predefined, repeatable transformations that bypass
        change-type detection and provide their own discovery, analysis,
        and deliverable patterns.

        Returns:
            List of recipe dicts, each containing:
            - key: str — Unique recipe identifier (e.g., 'refactor-to-profile-standards')
            - name: str — Human-readable display name
            - description: str — Description for recipe selection UI
            - skill: str — Fully-qualified skill reference (e.g., 'bundle:recipe-skill')
            - default_change_type: str — Change type for outline phase (e.g., 'tech_debt')
            - scope: str — Scope indicator (e.g., 'codebase_wide', 'module')

            Optional fields (set by user at plan creation time if omitted):
            - profile: str — Target profile (e.g., 'implementation', 'module_testing')
            - package_source: str — Package source (e.g., 'packages', 'test_packages')

        Notes:
            - The domain is auto-assigned from get_skill_domains() first entry
            - The source is auto-assigned as 'extension'
            - Default implementation returns empty list (no recipes)
        """
        return []

    def provides_verify_steps(self) -> list[dict]:
        """Return domain-specific verification steps for phase-5-execute.

        Each step declares a verification agent that is appended to the
        steps list in marshal.json under plan.phase-5-execute.steps during
        project configuration.

        Returns:
            List of step dicts, each containing:
            - name: str — Fully-qualified skill reference used in the steps list
              (e.g., 'my-bundle:my-verify-step')
            - skill: str — Same as name (the fully-qualified skill reference)
            - description: str — Human-readable description for wizard presentation

        Default implementation returns empty list (no domain-specific verify steps).
        """
        return []

    def provides_retrospective_aspects(self) -> list[dict]:
        """Return domain-specific retrospective aspects for plan-retrospective.

        Each aspect declares a deterministic, script-backed analysis fragment
        that plan-retrospective merges into its aspect dispatch (Step 3) when
        the audited plan belongs to the aspect's declared domain. Domain-
        invariant aspects ship with the generic retrospective; this hook lets a
        domain bundle attach checks that are only meaningful for plans authored
        against its domain.

        Returns:
            List of aspect dicts, each containing:
            - aspect: str — Short aspect name used as the fragment key and the
              --aspect value passed to collect-fragments add (e.g.,
              'wrapper-tangle').
            - domain: str — Domain key gating the aspect. The retrospective
              merges the aspect only when the audited plan's domain matches
              (e.g., 'plan-marshall-plugin-dev').
            - script: str — Fully-qualified executor notation for the aspect's
              deterministic fragment producer.
            - reference: str — Skill-relative reference doc path documenting the
              aspect's detection contract and finding schema.
            - description: str — Human-readable description for report context.
            - order: int — Relative sort key used when merging domain aspects
              into the aspect table. Not enforced at runtime.

        See extension-api/standards/ext-point-retrospective.md for the full
        contract. Default implementation returns empty list (no domain-specific
        retrospective aspects).
        """
        return []

    def provides_finalize_steps(self) -> list[dict]:
        """Return domain-specific finalize steps for phase-6-finalize.

        Each step declares a skill that executes during the finalize pipeline.
        Steps are discovered during project configuration and added to the
        user's selected steps in marshal.json under plan.phase-6-finalize.steps.

        Returns:
            List of step dicts, each containing:
            - name: str — Step identifier used in the steps list
              (fully-qualified skill notation, e.g., 'pm-dev-java:java-post-pr')
            - skill: str — Same as name (the fully-qualified skill reference)
            - description: str — Human-readable description for wizard presentation

        The step's skill receives --plan-id and --iteration as arguments.

        Default implementation returns empty list (no domain-specific finalize steps).
        """
        return []

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify each path into a file-role bucket owned by this extension.

        Extensions own the predicates that decide which paths they claim and
        the role each claimed path plays (production / test / documentation /
        config). The default implementation is a no-op — extensions that do
        not own any file types simply do not override this method.

        Args:
            paths: List of repo-relative path strings to classify. The
                aggregator passes every path under the plan's
                `references.affected_files` union. Extensions are free to
                ignore paths their globs do not match.

        Returns:
            A dict keyed by file-role with list-of-claimed-paths values.
            The four roles are fixed by contract:

            - ``production``: source code that ships to production (e.g.,
              ``scripts/foo.py``, ``src/main/java/Foo.java``).
            - ``test``: test source code (e.g., ``test/foo_test.py``,
              ``src/test/java/FooIT.java``).
            - ``documentation``: human-readable documentation (e.g.,
              ``README.md``, ``standards/foo.md``, ``docs/foo.adoc``).
            - ``config``: build / lint / packaging configuration (e.g.,
              ``pom.xml``, ``pyproject.toml``, ``package.json``).

            Default returns the empty four-role dict
            ``{'production': [], 'test': [], 'documentation': [], 'config': []}``;
            the aggregator interprets this as "this extension claims
            nothing". The default is intentionally NOT
            ``NotImplementedError`` — extensions opting out is the common
            case.

        Aggregator responsibility (NOT this method's responsibility):

        - **Longest-glob-wins overlap resolution.** When two extensions claim
          the same path under different roles or different glob patterns,
          the aggregator (`manage-execution-manifest._classify_paths_via_extensions`)
          counts non-wildcard path-segment tokens in each extension's matched
          glob and the longest-glob wins. Ties break alphabetically on the
          extension's domain key.
        - **Unclaimed-path handling.** Paths no extension claims are tagged
          ``unknown`` by the aggregator and surface as a ``[STATUS]``
          warning. The aggregator never silently falls back to
          ``documentation_only``.
        - **Plan-wide bucket collapse.** The aggregator collapses per-path
          claims into one of six plan-wide bucket values: ``production_only``,
          ``test_only``, ``documentation_only``, ``mixed_code``,
          ``mixed_with_docs``, ``unknown``.

        Example (override in a domain extension)::

            def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
                claims: dict[str, list[str]] = {
                    'production': [], 'test': [], 'documentation': [], 'config': []
                }
                for path in paths:
                    if path.endswith('.py') and path.startswith('scripts/'):
                        claims['production'].append(path)
                    elif path.endswith('.py') and (
                        path.startswith('test/') or path.startswith('tests/')
                    ):
                        claims['test'].append(path)
                    elif path in ('pyproject.toml', 'uv.lock'):
                        claims['config'].append(path)
                return claims

        See ``extension-api/standards/extension-contract.md`` § classify_paths()
        for the complete contract documentation.
        """
        return {'production': [], 'test': [], 'documentation': [], 'config': []}

    def classify_path_specificity(self, path: str, role: str) -> int:
        """Return the non-wildcard segment count of this extension's matched glob.

        Called by the manage-execution-manifest aggregator when more than one
        extension claims the same path. The aggregator uses the returned value
        to apply longest-glob-wins overlap resolution: the extension with the
        highest specificity score wins the path under its declared role.

        Args:
            path: The path that this extension claimed (in any role).
            role: The role under which this extension claimed the path
                (one of ``production`` / ``test`` / ``documentation`` /
                ``config``).

        Returns:
            Non-negative integer specificity score. Higher wins. The default
            returns ``0`` — extensions that override ``classify_paths()`` are
            expected to override this method as well, returning the count of
            non-wildcard path-segment tokens in the glob that matched ``path``
            for ``role``.

        Example::

            # An extension whose glob ``marketplace/bundles/*/skills/*/SKILL.md``
            # claimed the path ``marketplace/bundles/foo/skills/bar/SKILL.md``
            # for the ``documentation`` role returns 4 (the four explicit
            # segments: ``marketplace``, ``bundles``, ``skills``, ``SKILL.md``).
            def classify_path_specificity(self, path: str, role: str) -> int:
                if role == 'documentation' and path.endswith('SKILL.md'):
                    return 4
                return 0
        """
        return 0

    def classify_build_class(self, path: str, role: str) -> str:
        """Return the deterministic build_class for a (path, role) pair.

        The second leg of the file-to-build contract. Where ``classify_paths()``
        maps a path to a file role, this method maps the resulting (path, role)
        pair to a build_class — the deterministic classification a downstream
        consumer (``manage-execution-manifest``, ``phase-4-plan``) reads to derive
        the verification command set for a changed-artifact list without
        re-deriving the file type. This method is exactly parallel to
        ``classify_path_specificity`` (a separate per-(path, role) lookup, NOT a
        change to the four-role ``classify_paths()`` return shape).

        Args:
            path: The path this extension claimed (in any role). Supplied so a
                domain may discriminate the build_class on the path itself when
                the role default is wrong for that domain; the default
                implementation ignores it.
            role: The role under which this extension claimed the path — one of
                ``production`` / ``test`` / ``documentation`` / ``config``.

        Returns:
            A member of the closed 5-value enum ``BUILD_CLASSES`` — each value
            NAMES the canonical command directly (no name-to-name indirection):

            - ``compile``: production source — resolves a ``compile``.
            - ``module-tests``: test source — resolves ``test-compile`` +
              ``module-tests``.
            - ``docs-validate``: documentation — derives a doc validation gate.
            - ``verify``: build/lint/packaging config — resolves a full reactor
              ``verify`` for the affected module.
            - ``none``: no build derives from this (path, role) pair.

            The default maps roles deterministically:
            ``production → compile``, ``test → module-tests``,
            ``documentation → docs-validate``, ``config → verify``,
            and any unmatched role → ``none``. Domains that override
            ``classify_paths()`` inherit this default and override
            ``classify_build_class`` ONLY where the role→build_class default is
            wrong for the domain (e.g. a generated file whose path should derive
            ``none`` despite a ``production`` role).

        See ``extension-api/standards/extension-contract.md`` § classify_paths()
        for the complete contract documentation.
        """
        default_by_role = {
            'production': BUILD_CLASS_PROD_COMPILE,
            'test': BUILD_CLASS_TEST_RUN,
            'documentation': BUILD_CLASS_DOCS_VALIDATE,
            'config': BUILD_CLASS_BUILD_CONFIG_FULL,
        }
        return default_by_role.get(role, BUILD_CLASS_NONE)

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return this extension's portable ``(suffix, role_heuristic)`` vocabulary.

        Each tuple is ``(suffix, role_heuristic)`` — a file-extension suffix (or
        an exact config basename) paired with a location-role heuristic name. The
        vocabulary is portable: it encodes the file types this domain owns WITHOUT
        encoding the author's assumed directory layout. The build_map seed
        aggregator hands every registered extension's vocabulary to the
        ``script-shared`` tree-deriver (``derive_globs_from_tree``), which scans
        the actual project tree and emits one flat ``{parent_dir}/*{suffix}``
        glob per directory that contains a matched file (never a recursive
        ``**`` form) — so production files outside the assumed location (e.g.
        ``marketplace/targets/*.py``, and every
        ``marketplace/bundles/<bundle>/skills/plan-marshall-plugin/*.py``) are
        caught because they exist in the tree, not because an author guessed a
        glob.

        Returns:
            A list of ``(suffix, role_heuristic)`` tuples. ``suffix`` is a file
            suffix (e.g. ``.py``) or an exact basename for a config file (e.g.
            ``pyproject.toml``). ``role_heuristic`` is one of the four
            ``ROLE_HEURISTICS`` names — ``production-by-location`` /
            ``test-by-location`` / ``documentation`` / ``config`` — each of which
            resolves (via the deriver's location predicates) to one of the four
            ``classify_paths()`` roles. The default implementation returns an
            empty list: extensions that own no buildable file types contribute no
            vocabulary. Example for the python domain:
            ``[('.py', 'production-by-location'), ('.py', 'test-by-location')]``.

        This accessor is exactly parallel to ``classify_build_class`` and
        ``classify_path_specificity``: a per-extension lookup the aggregator
        consumes, NOT a change to the ``classify_paths()`` return shape.

        See ``extension-api/standards/extension-contract.md`` § classify_globs()
        for the complete contract documentation.
        """
        return []

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if this domain applies to a specific module and return resolved skills.

        Called during architecture enrichment to determine which skill domains
        apply to a module and what skills they provide. Each extension decides
        based on signals in the module's derived data and can customize which
        skills are defaults vs optionals per module.

        Args:
            module_data: Module dict from the module's derived.json
                (.plan/architecture/<module>/derived.json; the canonical
                module set lives in _project.json["modules"]) containing:
                build_systems, paths, dependencies, packages, metadata, stats
            active_profiles: Optional positive list of profiles to include.
                Overrides signal detection when provided (Layer 2/3).

        Returns:
            {
                'applicable': bool,
                'confidence': 'high' | 'medium' | 'low' | 'none',
                'signals': list[str],
                'additive_to': str | None,  # parent domain key (e.g., 'java')
                'skills_by_profile': {      # only when applicable
                    'implementation': {
                        'defaults': [{'skill': str, 'description': str}],
                        'optionals': [{'skill': str, 'description': str}]
                    },
                    ...
                }
            }

        Default returns not applicable. Override in extensions.
        Implementations typically call self.get_skill_domains() for base profiles,
        then adjust defaults/optionals based on module_data signals.
        """
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }

    def _detect_applicable_profiles(self, profiles: dict, module_data: dict | None) -> set[str] | None:
        """Detect which profiles are applicable based on module signals.

        Returns set of applicable profile names, or None for no filtering
        (all defined profiles are included). Override in domain extensions
        for signal-based detection.

        Args:
            profiles: Dict of profile definitions from get_skill_domains()
            module_data: Module dict from the module's derived.json
                (.plan/architecture/<module>/derived.json), or None

        Returns:
            Set of applicable profile names, or None for no filtering.
        """
        return None

    def _build_applicable_result(
        self,
        confidence: str,
        signals: list[str],
        additive_to: str | None = None,
        module_data: dict | None = None,
        active_profiles: set[str] | None = None,
        domain_key: str | None = None,
    ) -> dict:
        """Build applicable result from own get_skill_domains() profiles.

        Note: Despite the underscore prefix, this is part of the public API
        for extension implementations. All extensions call this from applies_to_module().

        Merges 'core' profile into each non-core profile to produce a flat
        skills_by_profile dict ready for consumption.

        Domain selection: By default uses the first domain entry from
        get_skill_domains(). Multi-domain extensions can pass domain_key
        to select a specific domain (e.g., 'general-dev' instead of 'build').

        Profile filtering (three-layer resolution):
        1. active_profiles (explicit override from config or CLI) wins
        2. _detect_applicable_profiles() (signal-based detection) if no override
        3. All defined profiles if detection returns None

        Args:
            confidence: 'high', 'medium', or 'low'
            signals: List of signal strings explaining why applicable
            additive_to: Parent domain key if this is an additive domain
            module_data: Module dict for signal-based profile detection
            active_profiles: Explicit positive list of profiles to include
            domain_key: Select a specific domain by key instead of using
                the first entry. Required for multi-domain extensions.

        Returns:
            Full applies_to_module result dict with applicable=True
        """
        all_domains = self.get_skill_domains()
        if domain_key:
            domains = next(
                (d for d in all_domains if d.get('domain', {}).get('key') == domain_key),
                all_domains[0] if all_domains else {},
            )
        else:
            domains = all_domains[0] if all_domains else {}
        profiles = domains.get('profiles', {})
        core = profiles.get('core', {})
        core_defaults = core.get('defaults', [])
        core_optionals = core.get('optionals', [])

        # Determine which profiles are active (three-layer resolution)
        profile_filter: set[str] | None
        if active_profiles is not None:
            profile_filter = active_profiles
        else:
            profile_filter = self._detect_applicable_profiles(profiles, module_data)

        skills_by_profile: dict[str, dict] = {}
        for profile_name in self.APPLICABLE_PROFILES:
            if profile_name not in profiles:
                continue
            if profile_filter is not None and profile_name not in profile_filter:
                continue
            profile = profiles[profile_name]
            merged_defaults = list(core_defaults) + list(profile.get('defaults', []))
            merged_optionals = list(core_optionals) + list(profile.get('optionals', []))
            if merged_defaults or merged_optionals:
                skills_by_profile[profile_name] = {
                    'defaults': merged_defaults,
                    'optionals': merged_optionals,
                }
        return {
            'applicable': True,
            'confidence': confidence,
            'signals': signals,
            'additive_to': additive_to,
            'skills_by_profile': skills_by_profile,
        }
