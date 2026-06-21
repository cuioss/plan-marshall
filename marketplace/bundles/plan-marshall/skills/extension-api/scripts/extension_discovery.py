#!/usr/bin/env python3
"""
Extension discovery library.

Single source of truth for discovering and loading extension.py files
from domain bundles. Used by project-structure and manage-config.

Extension discovery library with CLI for configuration operations.
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
    """
    env_path = os.environ.get('PLUGIN_CACHE_PATH')
    if env_path:
        return Path(env_path)
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


def read_implements_field(skill_md_path: Path) -> str | None:
    """Read the ``implements:`` scalar from a SKILL.md's YAML frontmatter.

    The ``implements:`` field is the archetype-identification key. It is always
    a single scalar value (never a YAML list), so this reader extracts only the
    leading ``key: value`` frontmatter pair named ``implements`` and returns its
    trimmed value. Surrounding quotes are stripped so a quoted declaration
    resolves to the same value as an unquoted one.

    Args:
        skill_md_path: Path to a candidate ``SKILL.md`` file.

    Returns:
        The ``implements:`` value, or ``None`` when the file is unreadable, has
        no leading ``---`` frontmatter block, or declares no ``implements:`` key.
    """
    try:
        content = skill_md_path.read_text(encoding='utf-8')
    except OSError:
        return None

    if not content.startswith('---'):
        return None
    end = content.find('\n---', 3)
    if end == -1:
        return None
    fm_text = content[3:end]

    for raw_line in fm_text.split('\n'):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        if key.strip() == 'implements':
            return value.strip().strip('"').strip("'") or None

    return None


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
        if read_implements_field(skill_md) != _DOMAIN_BUNDLE_ARCHETYPE:
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

        try:
            verify_steps = module.provides_verify_steps()
            if verify_steps:
                ext_info['verify_steps'] = verify_steps
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
