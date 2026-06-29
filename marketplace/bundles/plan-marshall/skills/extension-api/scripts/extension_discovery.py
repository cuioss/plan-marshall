#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Extension discovery library with CLI for configuration operations.

Single source of truth for discovering and loading extension.py files
from domain bundles. Used by manage-config and project-structure.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Direct import - executor sets up PYTHONPATH for cross-skill imports
import resolve_project_dir as _routing  # type: ignore[import-not-found]
from marketplace_bundles import resolve_bundles_root, resolve_skills_root  # type: ignore[import-not-found]
from marketplace_paths import get_bundle_cache_roots  # type: ignore[import-not-found]
from plan_logging import log_entry
from toon_parser import serialize_toon  # type: ignore[import-not-found]


def get_plugin_cache_path() -> Path:
    """Get the deployed-bundle cache path from environment or the layout op.

    Honors an explicit ``PLUGIN_CACHE_PATH`` env override; otherwise routes
    through the platform-runtime ``layout bundle-cache-root`` op (memoised via
    ``marketplace_paths.get_bundle_cache_roots``) and returns the highest-priority
    root. On Claude this is ``~/.claude/plugins/cache/plan-marshall``; on OpenCode
    it is the highest-priority user-global skill root.

    Security: the env override is validated against known-safe bases before use.
    An unrecognized path is rejected with a warning and falls back to the
    platform-resolved cache, per the plugin-security Python Script Surface
    standard (env vars are an untrusted boundary; a filesystem Path must not be
    constructed from env input without a safe-base check — otherwise a CI/CD
    environment that sets PLUGIN_CACHE_PATH to an attacker-controlled directory
    could redirect dynamic module loading to arbitrary code).
    """
    env_path = os.environ.get('PLUGIN_CACHE_PATH')
    if env_path:
        candidate = Path(env_path).expanduser()
        # Resolve to an absolute path for the safe-base comparison. Use the
        # candidate as-is when it does not exist yet (a pre-creation path still
        # deserves the same validation).
        resolved = candidate.resolve() if candidate.exists() else candidate.expanduser().resolve()
        # Safe bases: the user's home directory (covers ~/.claude/...,
        # ~/.opencode/...) and the marketplace source tree (covers development
        # and CI runs that point at the source checkout).
        home = Path.home().resolve()
        try:
            marketplace_root = resolve_bundles_root(Path(__file__)).parent.resolve()
        except RuntimeError:
            marketplace_root = None
        is_under_home = str(resolved).startswith(str(home) + os.sep) or resolved == home
        is_under_marketplace = marketplace_root is not None and (
            str(resolved).startswith(str(marketplace_root) + os.sep) or resolved == marketplace_root
        )
        if is_under_home or is_under_marketplace:
            return resolved
        log_entry(
            'script',
            None,
            'WARNING',
            f'[EXTENSION] PLUGIN_CACHE_PATH={env_path!r} rejected: not under home '
            f'({home}) or marketplace source tree; falling back to platform-resolved cache path',
        )
    return Path(get_bundle_cache_roots()[0]).expanduser()


def get_marketplace_bundles_path() -> Path:
    """Get the path to marketplace bundles directory.

    Resolves via ``resolve_bundles_root`` (walks parents looking for a
    plan-marshall bundle ancestor). If no source-tree ancestor exists
    (e.g. running outside the marketplace checkout), falls back to the
    plugin cache.

    Returns:
        Path to bundles directory
    """
    try:
        return resolve_bundles_root(Path(__file__))
    except RuntimeError:
        cache_path = get_plugin_cache_path()
        if cache_path.is_dir():
            return cache_path
        raise


def get_extension_api_scripts_path() -> Path:
    """Get path to extension scripts directory (where extension_base.py lives).

    Extension base classes live in ``script-shared/scripts/extension/`` while
    this discovery script lives in ``extension-api/scripts/``. The owning
    bundle's ``skills`` directory is resolved via ``resolve_skills_root``
    (identity walk, no index arithmetic), then descended into the sibling
    ``script-shared`` skill.
    """
    return resolve_skills_root(Path(__file__)) / 'script-shared' / 'scripts' / 'extension'


# The build skills whose ``scripts/extension.py`` ships a ``BuildExtensionBase``
# subclass (Axis-B: the file-to-build map). These are sibling skills under the
# plan-marshall bundle's ``skills`` directory; each owns one build system's
# ``(pattern, role)`` routes. Discovery is name-driven (not a tree scan) so a
# build skill without an ``extension.py`` is silently skipped.
_BUILD_EXTENSION_SKILLS: tuple[str, ...] = (
    'build-pyproject',
    'build-maven',
    'build-gradle',
    'build-npm',
)


def get_build_extension_paths() -> list[Path]:
    """Return the existing ``scripts/extension.py`` paths for the build skills.

    Each build skill (``build-pyproject`` / ``build-maven`` / ``build-gradle`` /
    ``build-npm``) ships a ``BuildExtensionBase`` subclass under
    ``scripts/extension.py``. The skills directory is resolved via
    ``resolve_skills_root`` (identity walk, the same anchor
    :func:`get_extension_api_scripts_path` uses); each named build skill's
    ``scripts/extension.py`` is included only when it exists on disk.

    Returns:
        List of existing ``extension.py`` paths, one per build skill that ships
        one, in :data:`_BUILD_EXTENSION_SKILLS` order.
    """
    skills_root = resolve_skills_root(Path(__file__))
    paths: list[Path] = []
    for skill in _BUILD_EXTENSION_SKILLS:
        candidate = skills_root / skill / 'scripts' / 'extension.py'
        if candidate.is_file():
            paths.append(candidate)
    return paths


def load_extension_module(extension_path: Path, bundle_name: str):
    """Load an extension.py module and instantiate the Extension class.

    Args:
        extension_path: Path to extension.py file
        bundle_name: Name of the bundle for module naming

    Returns:
        Extension instance or None if failed
    """
    try:
        spec = importlib.util.spec_from_file_location(f'extension_{bundle_name}', extension_path)
        if spec is None or spec.loader is None:
            log_entry('script', None, 'WARNING', f'[EXTENSION] Failed to create spec for {bundle_name}')
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the Extension class and instantiate it
        if hasattr(module, 'Extension'):
            return module.Extension()

        log_entry('script', None, 'WARNING', f'[EXTENSION] No Extension class found in {bundle_name}')
        return None
    except Exception as e:
        log_entry('script', None, 'WARNING', f'[EXTENSION] Failed to load extension from {bundle_name}: {e}')
        return None


def load_build_extension_module(extension_path: Path, skill_name: str):
    """Load a build skill's ``extension.py`` and instantiate its ``BuildExtension``.

    The Axis-B counterpart to :func:`load_extension_module`: build skills expose a
    ``BuildExtension`` class (subclassing ``BuildExtensionBase``) rather than the
    Axis-A ``Extension`` class. Returns the instantiated build extension, or
    ``None`` when the module cannot be loaded or carries no ``BuildExtension``.

    Args:
        extension_path: Path to the build skill's ``scripts/extension.py``.
        skill_name: Name of the owning build skill, used for module naming and
            warning context.

    Returns:
        A ``BuildExtension`` instance, or ``None`` on failure.
    """
    try:
        spec = importlib.util.spec_from_file_location(f'build_extension_{skill_name}', extension_path)
        if spec is None or spec.loader is None:
            log_entry('script', None, 'WARNING', f'[EXTENSION] Failed to create spec for build skill {skill_name}')
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'BuildExtension'):
            return module.BuildExtension()

        log_entry('script', None, 'WARNING', f'[EXTENSION] No BuildExtension class found in {skill_name}')
        return None
    except Exception as e:
        log_entry('script', None, 'WARNING', f'[EXTENSION] Failed to load build extension from {skill_name}: {e}')
        return None


def discover_build_extensions() -> list[dict[str, Any]]:
    """Discover every build skill's ``BuildExtensionBase`` subclass (Axis-B).

    The Axis-B counterpart to :func:`discover_all_extensions`. Where that function
    finds Axis-A ``ExtensionBase`` modules (the ``plan-marshall-plugin/extension.py``
    skill-loading extensions), this one loads each build skill's
    ``scripts/extension.py`` (``build-pyproject`` / ``build-maven`` /
    ``build-gradle`` / ``build-npm``) and returns the instantiated
    ``BuildExtension`` objects. These are the file-to-build route owners the
    build_map aggregator and the route deriver consume.

    Returns:
        List of dicts with build-extension info: ``{skill, path, module}``. A
        build skill without an ``extension.py`` or without a ``BuildExtension``
        class is silently omitted.
    """
    extensions: list[dict[str, Any]] = []
    for extension_path in get_build_extension_paths():
        skill_name = extension_path.parent.parent.name
        module = load_build_extension_module(extension_path, skill_name)
        if module:
            extensions.append({'skill': skill_name, 'path': str(extension_path), 'module': module})
    return extensions


# Canonical ``implements:`` declaration that identifies a domain-bundle manifest
# skill. See marketplace/bundles/plan-marshall/skills/extension-api/standards/
# ext-point-domain-bundle.md — the central standard owns the contract; this
# constant is the discovery key only.
_DOMAIN_BUNDLE_ARCHETYPE = 'plan-marshall:extension-api/standards/ext-point-domain-bundle'


def _strip_scalar_quotes(value: str) -> str:
    """Strip surrounding single/double quotes from a YAML scalar string."""
    return value.strip().strip('"').strip("'")


def read_implements_field(skill_md_path: Path) -> list[str]:
    """Read the ``implements:`` declaration(s) from a doc's YAML frontmatter.

    The ``implements:`` field is the archetype-identification key. A doc may
    declare it in either of two YAML shapes, and this reader normalizes both to
    a list of declared interface values:

    - **Inline scalar** — ``implements: bundle:skill/standards/ext-point-x`` —
      normalizes to a one-element list.
    - **Block sequence** — ``implements:`` on its own line followed by ``- value``
      item lines — returns each declared interface, in declaration order.

    A doc may legitimately declare more than one interface (e.g. a phase-6
    ``workflow/*.md`` step that implements both
    ``ext-point-execution-context-workflow`` and ``ext-point-finalize-step``);
    callers test membership against the returned list. Surrounding quotes are
    stripped so a quoted declaration resolves to the same value as an unquoted
    one.

    Args:
        skill_md_path: Path to a candidate doc with ``---``-fenced frontmatter.

    Returns:
        The list of declared ``implements:`` values (empty when the file is
        unreadable, has no leading ``---`` frontmatter block, declares no
        ``implements:`` key, or declares an empty block sequence).
    """
    try:
        content = skill_md_path.read_text(encoding='utf-8')
    except OSError:
        return []

    if not content.startswith('---'):
        return []
    end = content.find('\n---', 3)
    if end == -1:
        return []
    fm_lines = content[3:end].split('\n')

    for index, raw_line in enumerate(fm_lines):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        if key.strip() != 'implements':
            continue

        inline = _strip_scalar_quotes(value)
        if inline:
            # Inline-scalar form: implements: <value>
            return [inline]

        # Block-sequence form: collect the following ``- value`` item lines.
        values: list[str] = []
        for seq_raw in fm_lines[index + 1:]:
            seq = seq_raw.strip()
            if not seq or seq.startswith('#'):
                continue
            if not seq.startswith('- '):
                # The block sequence ended at the next non-item line.
                break
            item = _strip_scalar_quotes(seq[2:])
            if item:
                values.append(item)
        return values

    return []


def _scan_skills_root_for_manifest(skills_root: Path) -> Path | None:
    """Scan a ``skills/`` root for the manifest whose frontmatter declares the
    domain-bundle archetype and return its sibling ``extension.py``.

    Iterates each ``skills/*/SKILL.md`` candidate, reads the ``implements:``
    declaration, and selects the directory whose declaration matches
    :data:`_DOMAIN_BUNDLE_ARCHETYPE`. Returns the matched manifest's sibling
    ``extension.py`` only when that file exists; otherwise ``None``.

    Args:
        skills_root: Path to a bundle's ``skills/`` directory.

    Returns:
        Path to the matched manifest's sibling ``extension.py``, or ``None``.
    """
    if not skills_root.is_dir():
        return None

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        if _DOMAIN_BUNDLE_ARCHETYPE not in read_implements_field(skill_md):
            continue
        extension_path = skill_dir / 'extension.py'
        if extension_path.is_file():
            return extension_path

    return None


def find_extension_path(bundle_dir: Path) -> Path | None:
    """Resolve a bundle's ``extension.py`` by frontmatter archetype declaration.

    Scans the bundle's candidate ``skills/*/SKILL.md`` files for the
    ``implements:`` declaration

        implements: plan-marshall:extension-api/standards/ext-point-domain-bundle

    and derives the sibling ``extension.py`` from the matched manifest's
    directory. There is no path heuristic: the scanner does NOT identify a
    manifest by the directory name ``plan-marshall-plugin`` and does NOT read the
    markdown body for a discovery signal. A manifest whose frontmatter omits the
    ``implements:`` declaration is not discovered. The contract lives in
    ext-point-domain-bundle.md — this function is the implementor.

    Both resolution branches are preserved:
    - Source: bundles/{bundle}/skills/{manifest}/extension.py
    - Versioned cache: {cache}/{bundle}/{version}/skills/{manifest}/extension.py

    Args:
        bundle_dir: Path to the bundle directory.

    Returns:
        Path to the matched manifest's sibling ``extension.py``, or ``None`` when
        no candidate SKILL.md declares the archetype or no sibling exists.
    """
    # Source structure: bundle_dir/skills/*/SKILL.md
    matched = _scan_skills_root_for_manifest(bundle_dir / 'skills')
    if matched is not None:
        return matched

    # Versioned cache structure: bundle_dir/{version}/skills/*/SKILL.md
    for version_dir in sorted(bundle_dir.iterdir()):
        if version_dir.is_dir() and not version_dir.name.startswith('.'):
            matched = _scan_skills_root_for_manifest(version_dir / 'skills')
            if matched is not None:
                return matched

    return None


def discover_all_extensions() -> list[dict[str, Any]]:
    """Discover all extension.py files in bundles — returns every extension regardless
    of whether it applies to the current project.

    Use this for configuration operations (skill domains, workflow extensions)
    where all extensions need to be queried. For project-specific discovery
    that filters by applicability, use discover_applicable_extensions() instead.

    Returns:
        List of dicts with extension info: {bundle, path, module}
    """
    extensions: list[dict[str, Any]] = []
    bundles_path = get_marketplace_bundles_path()

    if not bundles_path.is_dir():
        return extensions

    for bundle_dir in bundles_path.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        extension_path = find_extension_path(bundle_dir)
        if not extension_path:
            continue

        module = load_extension_module(extension_path, bundle_dir.name)
        if module:
            extensions.append({'bundle': bundle_dir.name, 'path': str(extension_path), 'module': module})

    return extensions


def discover_applicable_extensions(project_root: Path) -> list[dict[str, Any]]:
    """Discover extensions that apply to a specific project — filters by
    whether discover_modules() finds modules in the given project root.

    Use this for project-specific operations (module discovery, architecture).
    For querying all extensions regardless of applicability, use
    discover_all_extensions() instead.

    Args:
        project_root: Path to the project root

    Returns:
        List of dicts with extension info: {bundle, path, module, discovered_modules}
    """
    all_extensions = discover_all_extensions()
    applicable: list[dict[str, Any]] = []

    for ext in all_extensions:
        module = ext.get('module')
        if module:
            try:
                discovered = module.discover_modules(project_root)
                if discovered:  # Only include if modules were found
                    ext['discovered_modules'] = discovered
                    applicable.append(ext)
            except Exception as e:
                log_entry(
                    'script',
                    None,
                    'WARNING',
                    f'[EXTENSION] discover_modules() failed for {ext.get("bundle", "unknown")}: {e}',
                )

    return applicable


def get_skill_domains_from_extensions(extensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get skill domains from extensions.

    Each extension's get_skill_domains() returns a list of domain dicts,
    supporting both single-domain and multi-domain extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        List of domain info dicts: {domain, profiles, bundle}
    """
    domains: list[dict[str, Any]] = []

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        try:
            all_domains = module.get_skill_domains()
            for domain_info in all_domains:
                if domain_info and domain_info.get('domain'):
                    # Copy to avoid mutating the extension's data
                    entry = dict(domain_info)
                    entry['bundle'] = ext['bundle']
                    domains.append(entry)
        except Exception as e:
            log_entry('script', None, 'WARNING', f'[EXTENSION] get_skill_domains() failed for {ext["bundle"]}: {e}')

    return domains


def derive_build_map_globs(
    project_root: Path, extensions: list[dict[str, Any]] | None = None
) -> dict[str, list[tuple[str, str]]]:
    """Collect each domain's explicit ``(pattern, role)`` build_map routes.

    Bridges build-extension discovery to the ``script-shared`` base-lib route
    collector (``derive_globs_from_tree``). Each build skill's
    ``BuildExtensionBase`` subclass declares its build_map as explicit
    ``(pattern, role)`` routes via ``classify_globs()`` — an fnmatch-style glob
    (e.g. ``marketplace/bundles/*.py``) paired with one of the four resolved roles
    (``production`` / ``test`` / ``documentation`` / ``config``). The collector
    gathers those declared routes verbatim, keyed by each build extension's served
    domain key (from ``get_skill_domains()``); it no longer scans the
    ``project_root`` tree to enumerate one glob per directory (``project_root`` is
    accepted for signature parity only). When two build extensions serve the same
    domain key (e.g. build-maven and build-gradle both serving ``java``), their
    routes are MERGED under that key — the collector unions the route sets.

    Tree completeness is a SEPARATE concern handled by
    ``validate_tree_completeness``, which reports any git-tracked source file no
    declared route covers. The build_map seed aggregator (``manage-config``)
    consumes this output to stamp each entry's canonical-named ``build_class``.

    Args:
        project_root: Project root (accepted for signature parity with the
            completeness validator; route collection does not read the tree).
        extensions: Optional pre-discovered extension list (from
            ``discover_build_extensions()``). When omitted, the build extensions
            are discovered here. Each entry's ``module`` is a
            ``BuildExtensionBase`` instance.

    Returns:
        A dict keyed by domain-key with a list of de-duplicated ``(pattern, role)``
        tuples. Domains that declare no routes are omitted.
    """
    from extension_base import derive_globs_from_tree  # type: ignore[import-not-found]

    discovered = extensions if extensions is not None else discover_build_extensions()
    modules = [ext['module'] for ext in discovered if ext.get('module') is not None]
    return derive_globs_from_tree(str(project_root), modules)


def get_workflow_extensions_from_extensions(extensions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Get workflow extensions (triage, outline_skill) from extensions.

    Args:
        extensions: List of extension info dicts

    Returns:
        Dict mapping bundle to {triage: skill_ref, outline_skill: skill_ref}
    """
    workflow_extensions: dict[str, dict[str, Any]] = {}

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        ext_info: dict[str, Any] = {}

        try:
            triage = module.provides_triage()
            if triage:
                ext_info['triage'] = triage
        except Exception:
            pass

        try:
            outline_skill = module.provides_outline_skill()
            if outline_skill:
                ext_info['outline_skill'] = outline_skill
        except Exception:
            pass

        if ext_info:
            workflow_extensions[ext['bundle']] = ext_info

    return workflow_extensions


def get_retrospective_aspects_from_extensions(extensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get domain-contributed retrospective aspects from extensions.

    Each extension's provides_retrospective_aspects() returns a list of
    aspect dicts. plan-retrospective merges only the aspects whose ``domain``
    matches the audited plan's domain; this helper returns every declared
    aspect across all extensions so the caller can apply the domain filter.

    Args:
        extensions: List of extension info dicts

    Returns:
        List of aspect dicts: {aspect, domain, script, reference, description,
        order, bundle}. The ``bundle`` field is added so callers can attribute
        each aspect to its contributing bundle.
    """
    aspects: list[dict[str, Any]] = []

    for ext in extensions:
        module = ext.get('module')
        if not module:
            continue

        try:
            declared = module.provides_retrospective_aspects()
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] provides_retrospective_aspects() failed for {ext.get("bundle", "unknown")}: {e}',
            )
            continue

        for aspect_info in declared:
            if aspect_info and aspect_info.get('aspect'):
                entry = dict(aspect_info)
                entry['bundle'] = ext.get('bundle', 'unknown')
                aspects.append(entry)

    return aspects


def apply_config_defaults(project_root: Path, pre_discovered: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Apply config_defaults() callback for applicable extensions only.

    Called during initialization to let extensions set project-specific
    defaults in marshal.json. Only extensions whose discover_modules()
    finds modules in the project are called, preventing non-applicable extensions
    from writing config (e.g., Maven settings in non-Java projects).

    Args:
        project_root: Path to the project root
        pre_discovered: Optional list of already-discovered extensions
            (from discover_applicable_extensions()). Avoids expensive double discovery.

    Returns:
        Dict with results: {
            "extensions_called": int,
            "extensions_skipped": int,
            "errors": list[str]
        }
    """
    if pre_discovered is not None:
        # Use pre-discovered extensions (already filtered by applicability)
        extensions = pre_discovered
    else:
        extensions = discover_all_extensions()

    results: dict[str, Any] = {'extensions_called': 0, 'extensions_skipped': 0, 'errors': []}

    for ext in extensions:
        module = ext.get('module')
        bundle = ext.get('bundle', 'unknown')

        if not module:
            results['extensions_skipped'] += 1
            continue

        # When using pre-discovered extensions, skip applicability check
        # (they were already filtered). Otherwise, check discover_modules.
        if pre_discovered is None and hasattr(module, 'discover_modules'):
            try:
                discovered = module.discover_modules(project_root)
                if not discovered:
                    results['extensions_skipped'] += 1
                    continue
            except Exception:
                results['extensions_skipped'] += 1
                continue

        if hasattr(module, 'config_defaults'):
            try:
                module.config_defaults(str(project_root))
                results['extensions_called'] += 1
            except Exception as e:
                results['errors'].append(f'{bundle}: {e}')
        else:
            results['extensions_skipped'] += 1

    return results


# =============================================================================
# Module Discovery and Merging (thin wrapper)
# =============================================================================


def discover_project_modules(project_root: Path) -> dict[str, Any]:
    """Discover all modules and split multi-technology paths into virtual modules.

    Delegates to _module_aggregation.discover_project_modules() which:
    - Calls discover_modules() on each applicable extension
    - Splits directories with multiple build systems into virtual modules
      (e.g., a dir with both pom.xml and package.json becomes two modules)
    - Returns a deduplicated, sorted module dict

    Args:
        project_root: Path to project root

    Returns:
        Dict with 'modules' (name -> module dict) and 'extensions_used' (list of bundle names).
    """
    from _module_aggregation import discover_project_modules as _discover_project_modules

    return _discover_project_modules(project_root, discover_applicable_extensions)


# =============================================================================
# Reusable ext-point implementor discovery
# =============================================================================

# The frontmatter keys a finalize-step (and other ext-point) implementor doc
# declares alongside ``implements:``. The contract for these fields lives in the
# central standards — see marketplace/bundles/plan-marshall/skills/extension-api/
# standards/ext-point-finalize-step.md (``name`` / ``order`` / ``default_on`` /
# ``presets`` / ``description``), ext-point-build-verify-step.md (the verify-step
# ``canonicals`` list), and ext-point-verify.md (the producer-declared
# ``verification_profile``). This list is the union parse target across
# ext-points, not the per-ext-point contract definition: a finalize-step doc
# declares no ``canonicals`` (defaults to ``[]``), a verify-step doc declares no
# ``default_on`` / ``presets`` (default to ``False`` / ``[]``), and most docs
# declare no ``verification_profile`` (its ABSENCE is the signal that the
# producer does not participate in the verify stage — see
# :func:`_build_implementor_record` for why it is the one field NOT defaulted).
_IMPLEMENTOR_FRONTMATTER_KEYS: tuple[str, ...] = (
    'name',
    'order',
    'default_on',
    'presets',
    'description',
    'canonicals',
    'verification_profile',
)


def _read_frontmatter_fields(doc_path: Path, keys: tuple[str, ...]) -> dict[str, Any]:
    """Read the named top-level frontmatter scalars/lists from ``doc_path``.

    Reuses the cache-aware ``configurable_contract`` primitives
    (``_extract_frontmatter_lines`` + ``_coerce_scalar``) so the same parser
    drives both the configurable block and the implementor-record fields. Each
    requested key is read as either an inline scalar (``key: value``) or a YAML
    block sequence (``key:`` followed by ``- item`` lines, used for ``presets``).
    Keys absent from the frontmatter are simply omitted from the result.

    A requested key may also be declared one level deep under the ``metadata:``
    mapping (``metadata:`` followed by indented ``key: value`` lines, as
    ``recipe-security-audit`` declares ``metadata.verification_profile``). Such a
    nested declaration is surfaced under the bare key name, so the implementor
    record sees ``verification_profile`` whether the producer declared it at the
    top level or inside the ``metadata:`` block. A top-level declaration always
    wins over a ``metadata:``-nested one of the same name; other indented blocks
    (e.g. a per-parameter ``configurable:`` mapping) are still skipped.

    Args:
        doc_path: Path to the doc whose ``---``-fenced frontmatter is read.
        keys: The frontmatter keys to extract (each read at the top level or from
            the ``metadata:`` block).

    Returns:
        A dict mapping each present key to its coerced scalar value, or to a
        ``list`` when the key is declared as a block sequence.
    """
    from configurable_contract import _coerce_scalar, _extract_frontmatter_lines  # type: ignore[import-not-found]

    try:
        text = doc_path.read_text(encoding='utf-8')
    except OSError:
        return {}

    fm_lines = _extract_frontmatter_lines(text)
    if fm_lines is None:
        return {}

    fields: dict[str, Any] = {}
    metadata_fields: dict[str, Any] = {}
    index = 0
    while index < len(fm_lines):
        raw_line = fm_lines[index]
        line = raw_line.strip()
        index += 1
        # Only TOP-LEVEL keys (zero indentation) are implementor-record fields. A
        # nested mapping such as the per-parameter ``configurable:`` block carries
        # its own indented ``key:`` / ``default:`` / ``description:`` lines; those
        # must NOT shadow the step's top-level ``description`` (or ``name`` etc.).
        if raw_line[:1] in (' ', '\t'):
            continue
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()

        # The ``metadata:`` mapping carries one-level-deep declarations such as
        # ``metadata.verification_profile``. Descend into its indented ``key:
        # value`` lines and record any REQUESTED key found there. The block ends
        # at the next non-indented line (or end of frontmatter). Nested values are
        # surfaced under the bare key, but only as a fallback — a top-level
        # declaration of the same key wins (applied after the scan completes).
        if key == 'metadata' and not value.strip():
            # ``metadata:`` keys are one level deep ONLY. Track the indentation of
            # the first child line; any subsequent line indented MORE deeply belongs
            # to a nested block (e.g. ``metadata.some_block.verification_profile``)
            # and must NOT be surfaced as a top-level metadata opt-in. Such deeper
            # lines are skipped while the block continues.
            child_indent: int | None = None
            while index < len(fm_lines):
                meta_raw = fm_lines[index]
                if meta_raw[:1] not in (' ', '\t'):
                    break
                index += 1
                meta_line = meta_raw.strip()
                if not meta_line or meta_line.startswith('#') or ':' not in meta_line:
                    continue
                meta_indent = len(meta_raw) - len(meta_raw.lstrip(' \t'))
                if child_indent is None:
                    child_indent = meta_indent
                elif meta_indent > child_indent:
                    # Deeper than the first child → nested sub-block; skip it.
                    continue
                meta_key, _, meta_value = meta_line.partition(':')
                meta_key = meta_key.strip()
                if meta_key not in keys:
                    continue
                meta_inline = meta_value.strip()
                if meta_inline:
                    metadata_fields[meta_key] = (
                        [] if meta_inline == '[]' else _coerce_scalar(meta_inline)
                    )
            continue

        if key not in keys:
            continue

        inline = value.strip()
        if inline:
            # Inline empty-list literal (``key: []``) is the empty block sequence,
            # not the string ``'[]'`` — normalize it so list-valued keys such as
            # ``presets: []`` resolve to ``[]`` rather than ``['[]']``.
            if inline == '[]':
                fields[key] = []
            else:
                fields[key] = _coerce_scalar(inline)
            continue

        # Block-sequence form: collect the following ``- item`` lines.
        items: list[Any] = []
        while index < len(fm_lines):
            seq = fm_lines[index].strip()
            if not seq or seq.startswith('#'):
                index += 1
                continue
            if not seq.startswith('- '):
                break
            items.append(_coerce_scalar(seq[2:]))
            index += 1
        fields[key] = items

    # Surface ``metadata:``-nested declarations under the bare key, but never let
    # them shadow a top-level declaration of the same name.
    for meta_key, meta_val in metadata_fields.items():
        fields.setdefault(meta_key, meta_val)

    return fields


def _build_implementor_record(doc_path: Path, source: str, name_override: str | None = None) -> dict[str, Any]:
    """Build a per-implementor record from a matching doc's frontmatter.

    Args:
        doc_path: Path to the implementor doc (already confirmed to declare the
            target ext-point via :func:`read_implements_field`).
        source: The implementor's origin — ``built-in`` / ``bundle-optional`` /
            ``project``.
        name_override: When supplied, the step id used for the record's ``name``
            instead of the frontmatter ``name``. Project steps derive their id
            from the path (``project:{skill-dir}``) — not from the SKILL.md
            registration ``name`` — so the registration ``name`` (a plain skill
            name, no ``project:`` prefix) and the discovery step id stay distinct.

    Returns:
        A record carrying ``name`` / ``order`` / ``default_on`` / ``presets`` /
        ``canonicals`` / ``description`` / ``source`` / ``path``. Missing
        frontmatter fields default to safe empty values (``name`` to the empty
        string, ``order`` to ``0``, ``default_on`` to ``False``, ``presets`` to
        ``[]``, ``canonicals`` to ``[]``, ``description`` to the empty string).
        ``presets`` is the finalize-step membership list; ``canonicals`` is the
        verify-step list the discovery consumer expands into
        ``default:verify:{canonical}`` step ids. A doc that declares one archetype
        leaves the other archetype's list at its empty default.

        ``verification_profile`` (the ext-point-verify producer declaration) is
        the one field NOT defaulted: it is present in the record ONLY when the
        doc declares it. Its ABSENCE is the contract signal that the producer
        does not participate in the verify stage — see ext-point-verify.md
        § "Hook API". A consumer enumerates participating producers by testing
        ``'verification_profile' in record`` rather than checking a sentinel
        value.
    """
    fields = _read_frontmatter_fields(doc_path, _IMPLEMENTOR_FRONTMATTER_KEYS)
    presets = fields.get('presets', [])
    if not isinstance(presets, list):
        presets = [presets]
    canonicals = fields.get('canonicals', [])
    if not isinstance(canonicals, list):
        canonicals = [canonicals]
    record: dict[str, Any] = {
        'name': name_override if name_override is not None else fields.get('name', ''),
        'order': fields.get('order', 0),
        'default_on': bool(fields.get('default_on', False)),
        'presets': presets,
        'canonicals': canonicals,
        'description': fields.get('description', ''),
        'source': source,
        'path': str(doc_path),
    }
    # ``verification_profile`` is surfaced ONLY when declared with a non-null,
    # non-empty value — its absence (or a null/empty declaration) is the
    # ext-point-verify signal that the producer does not participate in the verify
    # stage (ext-point-verify.md § "Hook API"). A bare ``verification_profile:``
    # with no value coerces to ``None`` and MUST NOT register the producer, so the
    # membership test guards on the coerced value rather than mere key presence.
    vp = fields.get('verification_profile')
    vp_nonempty = vp.strip() != '' if isinstance(vp, str) else bool(vp)
    if vp_nonempty:
        record['verification_profile'] = vp
    return record


def _scan_skills_roots_for_implementors(ext_point: str) -> list[dict[str, Any]]:
    """Scan every bundle's ``skills/*/SKILL.md`` for ``ext_point`` implementors.

    Resolves the marketplace bundles root and the plugin cache roots so the scan
    works both in the source checkout and in a consumer project that has only the
    installed plugin cache. A SKILL.md that lives under the ``plan-marshall``
    bundle's ``phase-6-finalize`` skill is NOT scanned here — phase-6 built-in
    steps are body docs under ``workflow/`` / ``standards/``, surfaced by
    :func:`_scan_phase6_for_implementors`. Bundle SKILL.md implementors are the
    opt-in ``{bundle}:{skill}`` steps (e.g. ``plan-marshall:plan-retrospective``).

    Returns:
        One ``bundle-optional`` record per matching ``skills/*/SKILL.md``.
    """
    records: list[dict[str, Any]] = []
    seen_step_ids: set[str] = set()

    roots: list[Path] = []
    bundles_path = get_marketplace_bundles_path()
    if bundles_path.is_dir():
        roots.append(bundles_path)
    for cache_root in get_bundle_cache_roots():
        cache_path = Path(cache_root).expanduser()
        if cache_path.is_dir() and cache_path not in roots:
            roots.append(cache_path)

    for root in roots:
        try:
            bundle_dirs = sorted(root.iterdir())
        except OSError:
            continue
        for bundle_dir in bundle_dirs:
            if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
                continue
            skills_root = bundle_dir / 'skills'
            if not skills_root.is_dir():
                continue
            try:
                skill_dirs = sorted(skills_root.iterdir())
            except OSError:
                continue
            for skill_dir in skill_dirs:
                if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
                    continue
                if skill_dir.name == 'phase-6-finalize':
                    continue
                skill_md = skill_dir / 'SKILL.md'
                if not skill_md.is_file():
                    continue
                # Bundle-optional step ids are PATH-derived (``{bundle}:{skill}``),
                # not the SKILL.md registration ``name`` (a plain skill name).
                step_id = f'{bundle_dir.name}:{skill_dir.name}'
                # Deduplicate by LOGICAL identity (step_id), not filesystem path:
                # the same ``bundle:skill`` resolves through both the source tree
                # and the plugin cache roots, so a path-keyed set would emit it
                # twice. First occurrence (source tree, scanned first) wins.
                if step_id in seen_step_ids:
                    continue
                if ext_point not in read_implements_field(skill_md):
                    continue
                seen_step_ids.add(step_id)
                records.append(
                    _build_implementor_record(skill_md, 'bundle-optional', name_override=step_id)
                )

    return records


def _scan_phase6_for_implementors(ext_point: str) -> list[dict[str, Any]]:
    """Scan the phase-6-finalize step docs for ``ext_point`` implementors.

    Scans ``phase-6-finalize/workflow/*.md`` and ``phase-6-finalize/standards/*.md``
    for the declaration, applying ``workflow/`` precedence on a bare-name
    collision (a step that has both a ``workflow/{name}.md`` and a
    ``standards/{name}.md`` is represented by the ``workflow/`` doc only — mirroring
    ``configurable_contract.resolve_step_doc_path``).

    Returns:
        One ``built-in`` record per matching step doc, de-duplicated by bare name
        with ``workflow/`` winning.
    """
    from configurable_contract import _phase_6_skill_dir  # type: ignore[import-not-found]

    skill_dir = _phase_6_skill_dir()
    records: list[dict[str, Any]] = []
    seen_bare: set[str] = set()

    for subdir in ('workflow', 'standards'):
        docs_dir = skill_dir / subdir
        if not docs_dir.is_dir():
            continue
        try:
            doc_paths = sorted(docs_dir.glob('*.md'))
        except OSError:
            continue
        for doc_path in doc_paths:
            bare = doc_path.stem
            if bare in seen_bare:
                # workflow/ scanned first wins on a name collision.
                continue
            if ext_point not in read_implements_field(doc_path):
                continue
            seen_bare.add(bare)
            records.append(_build_implementor_record(doc_path, 'built-in'))

    return records


def _scan_phase5_for_implementors(ext_point: str) -> list[dict[str, Any]]:
    """Scan the phase-5-execute standards docs for ``ext_point`` implementors.

    The verify-step counterpart to :func:`_scan_phase6_for_implementors`. Verify
    steps are built-in body docs under ``phase-5-execute/standards/*.md`` (there
    is no ``workflow/`` surface for verify steps, so no precedence rule applies).
    The sole built-in verify-step implementor is ``canonical_verify.md``, whose
    ``canonicals:`` list the discovery consumer expands into
    ``default:verify:{canonical}`` step ids. The contract lives in the central
    standard — see marketplace/bundles/plan-marshall/skills/extension-api/
    standards/ext-point-build-verify-step.md.

    The phase-5-execute skill dir is resolved from ``__file__`` via the same
    ``resolve_skills_root`` identity walk the phase-6 scan and the build-skill
    discovery use, so the surface stays stable regardless of the process working
    directory. Returns nothing when the standards dir is absent (a consumer
    project resolving through a cache layout without the phase-5 standards docs).

    Returns:
        One ``built-in`` record per matching ``phase-5-execute/standards/*.md``.
    """
    docs_dir = resolve_skills_root(Path(__file__)) / 'phase-5-execute' / 'standards'
    if not docs_dir.is_dir():
        return []

    records: list[dict[str, Any]] = []
    try:
        doc_paths = sorted(docs_dir.glob('*.md'))
    except OSError:
        return []
    for doc_path in doc_paths:
        if ext_point not in read_implements_field(doc_path):
            continue
        records.append(_build_implementor_record(doc_path, 'built-in'))

    return records


def _scan_project_for_implementors(ext_point: str) -> list[dict[str, Any]]:
    """Scan project-local ``.claude/skills/finalize-step-*/SKILL.md`` implementors.

    Project-local finalize steps live under the PROJECT root's ``.claude/skills/``.
    Only directories matching ``finalize-step-*`` are scanned. Returns nothing
    when there is no resolvable project root, or no ``.claude/skills/`` root (a
    consumer project without the meta-project's project-local steps).

    Discovery is PROJECT-ROOT-anchored, resolved cwd-relatively by the uniform
    cwd rule (ADR-002): the project root is the nearest ancestor of the current
    working directory containing ``.plan/local`` (with a git-toplevel fallback for
    clean checkouts), via ``file_ops._resolve_plan_root`` — the same resolver
    ``file_ops.get_executor_path`` is built on. It is deliberately NOT anchored on
    the running script's ``__file__``: project-local steps are a property of the
    PROJECT, not of the marketplace tree the scripts ship from. When the scanning
    code ships from the plugin cache tree, a ``__file__``-derived anchor (the
    former ``configurable_contract._repo_root()``) resolves into the cache tree
    where ``.claude/skills/`` does not exist, so every ``project:finalize-step-*``
    implementor is silently missed. Anchoring on the project root makes discovery
    correct from BOTH a source-tree and a cache-tree execution context.

    Returns:
        One ``project`` record per matching ``finalize-step-*/SKILL.md``.
    """
    from file_ops import _resolve_plan_root  # type: ignore[import-not-found]

    project_root = _resolve_plan_root()
    if project_root is None:
        return []

    skills_root = project_root / '.claude' / 'skills'
    if not skills_root.is_dir():
        return []

    records: list[dict[str, Any]] = []
    try:
        skill_dirs = sorted(skills_root.glob('finalize-step-*'))
    except OSError:
        return []
    for skill_dir in skill_dirs:
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        if ext_point not in read_implements_field(skill_md):
            continue
        # Project step ids are PATH-derived (``project:{skill-dir}``), matching
        # the existing _discover_all_finalize_steps contract — not the SKILL.md
        # registration ``name`` (a plain skill name with no ``project:`` prefix).
        step_id = f'project:{skill_dir.name}'
        records.append(_build_implementor_record(skill_md, 'project', name_override=step_id))

    return records


def find_implementors(ext_point: str) -> list[dict[str, Any]]:
    """Enumerate every component that declares ``implements: {ext_point}``.

    The reusable, first-class discovery query for "who implements ext-point X".
    It is the SOLE discovery path for both the finalize-step registry and the
    verify-step registry (each registry's seed and discovery surface consume it);
    there is no parallel glob. The per-ext-point ``implements:`` match keeps the
    surfaces disjoint — a finalize-step ext-point query never matches the phase-5
    verify-step doc, and a verify-step query never matches the phase-6 docs — so
    the union of scan surfaces below does not cross-contaminate results. The
    contracts — addressing surface, frontmatter fields, and the supporting-doc
    exclusion list — live in the central standards at
    marketplace/bundles/plan-marshall/skills/extension-api/standards/
    ext-point-finalize-step.md and ext-point-build-verify-step.md.

    Scans four surfaces:

    - every bundle's ``skills/*/SKILL.md`` (opt-in ``bundle-optional`` steps),
      across both the source bundles root and the plugin cache roots, so a
      consumer project with no ``marketplace/`` tree resolves through the cache;
    - ``phase-6-finalize/workflow/*.md`` + ``standards/*.md`` (finalize ``built-in``
      steps, ``workflow/`` winning on a bare-name collision);
    - ``phase-5-execute/standards/*.md`` (verify ``built-in`` steps);
    - project-local ``.claude/skills/finalize-step-*/SKILL.md`` (``project`` steps).

    Each surface reuses the cache-aware ``configurable_contract`` primitives for
    doc-root resolution and frontmatter parsing.

    Args:
        ext_point: The canonical ext-point value, e.g.
            ``plan-marshall:extension-api/standards/ext-point-finalize-step`` or
            ``plan-marshall:extension-api/standards/ext-point-build-verify-step``.

    Returns:
        A list of per-implementor records, sorted by ``order`` then ``name``.
        Each record carries ``name`` / ``order`` / ``default_on`` / ``presets`` /
        ``canonicals`` / ``description`` / ``source`` / ``path``.
    """
    records: list[dict[str, Any]] = []
    records.extend(_scan_phase6_for_implementors(ext_point))
    records.extend(_scan_phase5_for_implementors(ext_point))
    records.extend(_scan_skills_roots_for_implementors(ext_point))
    records.extend(_scan_project_for_implementors(ext_point))
    records.sort(key=lambda rec: (rec.get('order', 0), rec.get('name', '')))
    return records


# =============================================================================
# CLI Interface
# =============================================================================


def cmd_apply_config_defaults(args) -> int:
    """CLI handler for apply-config-defaults command."""
    project_root = Path(args.project_dir).resolve()

    if not project_root.exists():
        log_entry('script', None, 'ERROR', f'[EXTENSION] Project directory not found: {project_root}')
        print(serialize_toon({'status': 'error', 'error': f'Project directory not found: {project_root}'}))
        return 0

    results = apply_config_defaults(project_root)

    # Emit via the shared TOON serializer for parity with the error path above
    # and cmd_list_retrospective_aspects below (the former hand-rolled
    # tab-delimited rows were not valid `key: value` TOON).
    print(
        serialize_toon(
            {
                'status': 'success' if not results['errors'] else 'error',
                'extensions_called': results['extensions_called'],
                'extensions_skipped': results['extensions_skipped'],
                'errors_count': len(results['errors']),
                'errors': results['errors'],
            }
        )
    )

    return 0 if not results['errors'] else 1


def cmd_list_retrospective_aspects(args) -> int:
    """CLI handler for list-retrospective-aspects command.

    Emits one TOON row per domain-contributed retrospective aspect across all
    discovered extensions. plan-retrospective consumes this list and filters by
    the audited plan's domain before merging aspects into its dispatch.
    """
    del args  # No arguments — discovery is global across all extensions.
    extensions = discover_all_extensions()
    aspects = get_retrospective_aspects_from_extensions(extensions)

    rows: list[dict[str, Any]] = [
        {
            'aspect': a.get('aspect', ''),
            'domain': a.get('domain', ''),
            'script': a.get('script', ''),
            'reference': a.get('reference', ''),
            'description': a.get('description', ''),
            'order': a.get('order', 0),
            'bundle': a.get('bundle', ''),
        }
        for a in aspects
    ]

    print(serialize_toon({'status': 'success', 'count': len(rows), 'aspects': rows}))
    return 0


def cmd_implementors(args) -> int:
    """CLI handler for the implementors command.

    Emits one TOON row per component that declares
    ``implements: {--ext-point}``. Global discovery across every bundle's
    ``skills/*/SKILL.md``, the phase-6-finalize step docs, and the project-local
    ``finalize-step-*`` skills — no project-dir / plan-id routing (mirrors
    :func:`cmd_list_retrospective_aspects`).
    """
    records = find_implementors(args.ext_point)
    rows: list[dict[str, Any]] = []
    for rec in records:
        row: dict[str, Any] = {
            'name': rec.get('name', ''),
            'order': rec.get('order', 0),
            'default_on': rec.get('default_on', False),
            'presets': rec.get('presets', []),
            'canonicals': rec.get('canonicals', []),
            'description': rec.get('description', ''),
            'source': rec.get('source', ''),
            'path': rec.get('path', ''),
        }
        # Surfaced only when the producer declared it (absence is the
        # ext-point-verify non-participation signal) — keep the record's
        # present/absent semantics in the emitted row.
        if 'verification_profile' in rec:
            row['verification_profile'] = rec['verification_profile']
        rows.append(row)
    print(
        serialize_toon(
            {
                'status': 'success',
                'ext_point': args.ext_point,
                'count': len(rows),
                'implementors': rows,
            }
        )
    )
    return 0


def main() -> int:
    """CLI entry point for extension discovery operations."""
    import argparse

    parser = argparse.ArgumentParser(description='Extension discovery and configuration operations', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # apply-config-defaults subcommand
    defaults_parser = subparsers.add_parser(
        'apply-config-defaults',
        help='Apply config_defaults() callback for all extensions',
        allow_abbrev=False,
    )
    defaults_parser.add_argument(
        '--project-dir',
        default='.',
        help='Project directory (default: current directory). Mutually exclusive with --plan-id.',
    )
    _routing.add_plan_id_arg(defaults_parser)
    defaults_parser.set_defaults(func=cmd_apply_config_defaults)

    # list-retrospective-aspects subcommand
    aspects_parser = subparsers.add_parser(
        'list-retrospective-aspects',
        help='List domain-contributed retrospective aspects (all extensions)',
        allow_abbrev=False,
    )
    aspects_parser.set_defaults(func=cmd_list_retrospective_aspects)

    # implementors subcommand — reusable "who implements ext-point X" query.
    implementors_parser = subparsers.add_parser(
        'implementors',
        help='Enumerate components implementing the given extension point',
        allow_abbrev=False,
    )
    implementors_parser.add_argument(
        '--ext-point',
        required=True,
        help='Canonical extension-point value (e.g. '
        'plan-marshall:extension-api/standards/ext-point-finalize-step)',
    )
    implementors_parser.set_defaults(func=cmd_implementors)

    args = parser.parse_args()

    # Two-state routing applies only to subcommands that declare --project-dir
    # (apply-config-defaults). Global-discovery subcommands such as
    # list-retrospective-aspects scan every bundle from the marketplace tree and
    # take no project-dir / plan-id routing.
    if hasattr(args, 'project_dir'):
        # Two-state routing: --plan-id auto-resolves; --project-dir is the
        # explicit override; both together is a hard error.
        try:
            args.project_dir = _routing.resolve_project_dir(
                getattr(args, 'plan_id', None), args.project_dir, default='.'
            )
        except _routing.MutuallyExclusiveArgsError:
            print(
                serialize_toon(
                    _routing.emit_mutually_exclusive_error(getattr(args, 'plan_id', None), args.project_dir)
                )
            )
            return 2
        except _routing.WorktreeResolutionError as exc:
            print(serialize_toon(_routing.emit_worktree_error(args.plan_id, exc)))
            return 2

    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())
