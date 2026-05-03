#!/usr/bin/env python3
"""Manage command handlers for architecture script.

Handles: discover, init, derived, derived-module

Persistence model: per-module on-disk layout under
``.plan/project-architecture/`` consisting of a top-level ``_project.json``
plus per-module ``derived.json``/``enriched.json`` files.
``api_discover()`` writes via the tmp+swap protocol so an interrupted
discover run never leaves a half-written tree behind.
"""

import re
import shutil
from pathlib import Path

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    _write_json,
    error_result_module_not_found,
    get_data_dir,
    get_module_derived_path,
    get_module_enriched_path,
    get_project_meta_path,
    get_tmp_data_dir,
    iter_modules,
    load_module_derived,
    load_module_enriched,
    load_module_enriched_or_empty,
    load_project_meta,
    require_project_meta_result,
    save_module_derived,
    save_module_enriched,
    save_project_meta,
    swap_data_dir,
)
from constants import (  # type: ignore[import-not-found]
    DIR_PER_MODULE_DERIVED,
    DIR_PER_MODULE_ENRICHED,
    FILE_PROJECT_META,
)

# =============================================================================
# Files-Inventory Post-Processor
# =============================================================================

# Per-category cap. Above this number, a category list is replaced by the
# elision shape ``{"elided": <count>, "sample": [first 100 paths]}`` so
# callers know they must fall back to Glob/find.
_FILES_CATEGORY_CAP = 500
_FILES_ELISION_SAMPLE_SIZE = 100

# Universal ignore set — directory names that are never useful in an
# inventory regardless of whether the project ships a ``.gitignore``.
_FILES_ALWAYS_IGNORED_DIRS = frozenset(
    {
        '.git',
        '__pycache__',
        'node_modules',
        'target',
        '.venv',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        '.idea',
        '.pyprojectx',
        'htmlcov',
    }
)

# Hidden files allowed in the inventory despite the dotfile-skip rule.
_FILES_DOTFILE_ALLOWLIST = frozenset({'.gitignore', '.editorconfig'})

# Marketplace-specific category list. Modules outside ``marketplace/bundles/``
# fall back to the generic set (``source``, ``test``, ``build_file``, ``doc``,
# ``config``).
_FILES_BUILD_FILES = frozenset({'pyproject.toml', 'package.json', 'pom.xml', 'plugin.json'})
_FILES_GENERIC_SOURCE_EXTS = frozenset(
    {'.py', '.java', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.kt', '.c', '.cpp', '.h', '.hpp', '.cs'}
)
_FILES_GENERIC_SCRIPT_EXTS = frozenset({'.sh', '.bash', '.zsh'})

_MARKETPLACE_BUNDLE_PREFIX = 'marketplace/bundles/'


def _gitignore_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile one ``.gitignore`` pattern to a regex that matches POSIX-style paths.

    The matcher is intentionally minimal — enough to handle the patterns the
    repo's own ``.gitignore`` and typical bundle ``.gitignore`` files use:
    leading ``/`` anchors to the gitignore file's directory, ``**/`` matches
    any number of intermediate path segments, ``*`` matches within a segment,
    ``?`` matches one non-separator char, trailing ``/`` is handled by the
    caller (dir-only flag).
    """
    anchored = pattern.startswith('/')
    if anchored:
        pattern = pattern[1:]
    has_slash = '/' in pattern  # mid-pattern slash also anchors

    parts: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == '*':
            if i + 1 < n and pattern[i + 1] == '*':
                # `**` — match across path separators.
                if i + 2 < n and pattern[i + 2] == '/':
                    parts.append('(?:.*/)?')
                    i += 3
                else:
                    parts.append('.*')
                    i += 2
            else:
                parts.append('[^/]*')
                i += 1
        elif c == '?':
            parts.append('[^/]')
            i += 1
        else:
            parts.append(re.escape(c))
            i += 1
    body = ''.join(parts)
    if anchored or has_slash:
        regex = f'^{body}(?:/.*)?$'
    else:
        regex = f'(?:^|.*/){body}(?:/.*)?$'
    return re.compile(regex)


def _load_gitignore(path: Path) -> list[tuple[re.Pattern[str], bool, bool]]:
    """Read one ``.gitignore`` file into ``(regex, is_negation, dir_only)`` tuples."""
    if not path.exists() or path.is_symlink():
        return []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return []
    rules: list[tuple[re.Pattern[str], bool, bool]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        is_neg = line.startswith('!')
        if is_neg:
            line = line[1:]
        dir_only = line.endswith('/')
        if dir_only:
            line = line[:-1]
        if not line:
            continue
        try:
            regex = _gitignore_pattern_to_regex(line)
        except re.error:
            continue
        rules.append((regex, is_neg, dir_only))
    return rules


def _is_ignored_by_rules(
    rel_path: str,
    is_dir: bool,
    rules: list[tuple[re.Pattern[str], bool, bool]],
) -> bool:
    """Apply ``.gitignore`` rules with last-match-wins semantics."""
    ignored = False
    for regex, is_neg, dir_only in rules:
        if dir_only and not is_dir:
            continue
        if regex.match(rel_path):
            ignored = not is_neg
    return ignored


def _is_marketplace_bundle_module(module_data: dict, project_path: Path) -> bool:
    """Decide whether a module's paths.module sits under ``marketplace/bundles/``.

    Marketplace-specific categories (``skill``/``agent``/``command``/...) only
    apply when the module's root is inside a marketplace bundle directory.
    """
    paths = module_data.get('paths') or {}
    module_rel = paths.get('module') or ''
    if not module_rel:
        return False
    # Normalise the path string — strip leading ``./`` and use POSIX separators.
    rel = Path(module_rel).as_posix().lstrip('./')
    return rel.startswith(_MARKETPLACE_BUNDLE_PREFIX) or rel == _MARKETPLACE_BUNDLE_PREFIX.rstrip('/')


def _classify_marketplace(rel_from_module: str, basename: str) -> str | None:
    """Return the marketplace category for ``rel_from_module`` or None to skip.

    ``rel_from_module`` is the file path relative to the module root, in POSIX
    form. ``basename`` is the final path component.
    """
    parts = rel_from_module.split('/')

    # skills/<skill>/SKILL.md
    if (
        len(parts) >= 3
        and parts[0] == 'skills'
        and basename == 'SKILL.md'
    ):
        return 'skill'

    # skills/<skill>/scripts/**/*.{py,sh}
    if (
        len(parts) >= 4
        and parts[0] == 'skills'
        and parts[2] == 'scripts'
        and (basename.endswith('.py') or basename.endswith('.sh'))
    ):
        return 'script'

    # skills/<skill>/standards/**/*.md
    if (
        len(parts) >= 4
        and parts[0] == 'skills'
        and parts[2] == 'standards'
        and basename.endswith('.md')
    ):
        return 'standard'

    # skills/<skill>/templates/**/*
    if len(parts) >= 4 and parts[0] == 'skills' and parts[2] == 'templates':
        return 'template'

    # agents/<name>.md (immediate child)
    if len(parts) == 2 and parts[0] == 'agents' and basename.endswith('.md'):
        return 'agent'

    # commands/<name>.md (immediate child)
    if len(parts) == 2 and parts[0] == 'commands' and basename.endswith('.md'):
        return 'command'

    # build files anywhere
    if basename in _FILES_BUILD_FILES:
        return 'build_file'

    # doc files anywhere
    if basename.startswith('README') or basename.startswith('CHANGELOG'):
        return 'doc'

    return None


def _classify_generic(rel_from_module: str, basename: str) -> str | None:
    """Return the generic category for ``rel_from_module`` or None to skip."""
    if basename in _FILES_BUILD_FILES:
        return 'build_file'

    if basename.startswith('README') or basename.startswith('CHANGELOG'):
        return 'doc'

    suffix = Path(basename).suffix.lower()
    if suffix in _FILES_GENERIC_SCRIPT_EXTS:
        return 'script'
    if suffix in _FILES_GENERIC_SOURCE_EXTS:
        # Decide test-vs-source from path conventions.
        parts = rel_from_module.split('/')
        if any(p in {'test', 'tests', '__tests__'} for p in parts[:-1]):
            return 'test'
        if basename.startswith('test_') or basename.endswith('_test.py') or '.test.' in basename:
            return 'test'
        return 'source'
    return None


def _join_rel_path(parent: str, name: str) -> str:
    """Join a parent project-relative path with a child name.

    Returns POSIX-style paths so the regex matcher always sees ``a/b/c``
    regardless of host OS. Treats ``''`` and ``'.'`` as project-root
    sentinels — the join collapses to just ``name`` instead of ``./name``.
    """
    if parent in {'', '.'}:
        return name
    return (Path(parent) / name).as_posix()


def _walk_module_root(
    module_root: Path,
    project_path: Path,
    project_root_rules: list[tuple[re.Pattern[str], bool, bool]],
) -> list[tuple[str, str]]:
    """Walk ``module_root`` honouring gitignore. Return ``(rel_from_module, basename)``.

    Symlinks are skipped (both files and dirs). Dotfiles are skipped except
    for the allowlist (``.gitignore``, ``.editorconfig``). Always-ignored
    directories are skipped unconditionally. Per-directory ``.gitignore``
    files contribute additional rules below their owning directory.
    """
    if not module_root.exists() or not module_root.is_dir() or module_root.is_symlink():
        return []

    results: list[tuple[str, str]] = []

    # Stack of (current_dir, rules_in_effect, rel_from_project, rel_from_module).
    # Rules are accumulated as we descend so a child .gitignore augments the
    # parent set without mutating it. ``module_root`` and ``project_path`` are
    # already resolved by the caller (``_post_process_files``); resolving them
    # again here would be redundant.
    initial_rel = module_root.relative_to(project_path).as_posix()
    stack: list[tuple[Path, list[tuple[re.Pattern[str], bool, bool]], str]] = [
        (module_root, list(project_root_rules), initial_rel)
    ]

    while stack:
        current, rules_in, rel_from_project = stack.pop()
        # Augment rules with the current directory's .gitignore (if any).
        local_rules = _load_gitignore(current / '.gitignore')
        rules = rules_in + local_rules if local_rules else rules_in

        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue

        for entry in entries:
            name = entry.name
            if entry.is_symlink():
                continue
            if name.startswith('.') and name not in _FILES_DOTFILE_ALLOWLIST:
                # Hidden files/dirs — skip unless explicitly allowed.
                if name in _FILES_ALWAYS_IGNORED_DIRS:
                    continue
                # Generic dotfile — skip silently.
                if entry.is_dir():
                    continue
                continue
            if entry.is_dir():
                if name in _FILES_ALWAYS_IGNORED_DIRS:
                    continue
                child_rel_from_project = _join_rel_path(rel_from_project, name)
                if _is_ignored_by_rules(child_rel_from_project, True, rules):
                    continue
                stack.append((entry, rules, child_rel_from_project))
                continue
            # File entry.
            child_rel_from_project = _join_rel_path(rel_from_project, name)
            if _is_ignored_by_rules(child_rel_from_project, False, rules):
                continue
            try:
                rel_from_module = entry.relative_to(module_root).as_posix()
            except ValueError:
                # Symlink-like indirection escaped the module — skip defensively.
                continue
            results.append((rel_from_module, name))

    return results


def _apply_category_cap(paths: list[str]) -> list[str] | dict:
    """Apply the per-category cap. Below the cap return ``paths`` verbatim."""
    if len(paths) <= _FILES_CATEGORY_CAP:
        return paths
    return {
        'elided': len(paths),
        'sample': paths[:_FILES_ELISION_SAMPLE_SIZE],
    }


def _post_process_files(modules: dict, project_dir: str = '.') -> None:
    """Populate ``module['files']`` for every module in-place.

    Walks each module's ``paths.module`` (and any additional ``paths.tests``
    that fall outside the module root for marketplace bundles), classifies
    every non-ignored file, and writes the categorised inventory back into
    the module dict. The project-wide marketplace-vs-generic decision is
    made per-module: a module under ``marketplace/bundles/`` uses the
    marketplace classification table, every other module uses the generic
    set. Sorting is byte-wise so output is byte-identical across OSes.
    """
    project_path = Path(project_dir).resolve()
    project_root_rules = _load_gitignore(project_path / '.gitignore')

    for _module_name, module_data in modules.items():
        paths = module_data.get('paths') or {}
        module_rel = paths.get('module') or ''
        if not module_rel:
            module_data['files'] = {}
            continue

        is_marketplace = _is_marketplace_bundle_module(module_data, project_path)

        # Resolve the module root and (if outside the root) any extra test dirs.
        module_root = (project_path / module_rel).resolve()
        roots: list[tuple[Path, bool]] = [(module_root, False)]
        seen_roots: set[Path] = {module_root}
        for tests_rel in paths.get('tests') or []:
            tests_path = (project_path / tests_rel).resolve()
            if tests_path in seen_roots:
                continue
            try:
                tests_path.relative_to(module_root)
                continue  # Already covered by walking module_root.
            except ValueError:
                pass
            roots.append((tests_path, True))
            seen_roots.add(tests_path)

        categorised: dict[str, list[str]] = {}
        for root, is_tests_root in roots:
            entries = _walk_module_root(root, project_path, project_root_rules)
            for rel_from_module, basename in entries:
                category: str
                inventory_path: str
                if is_tests_root:
                    # Files reached via paths.tests outside the module root
                    # are unconditionally tests, regardless of mode.
                    category = 'test'
                    # Use the project-relative path so callers can locate the
                    # file unambiguously when it sits outside paths.module.
                    inventory_path = root.relative_to(project_path).as_posix() + '/' + rel_from_module
                else:
                    classified = (
                        _classify_marketplace(rel_from_module, basename)
                        if is_marketplace
                        else _classify_generic(rel_from_module, basename)
                    )
                    if classified is None:
                        continue
                    category = classified
                    inventory_path = (
                        Path(module_rel).as_posix().rstrip('/') + '/' + rel_from_module
                        if module_rel not in {'', '.'}
                        else rel_from_module
                    )
                categorised.setdefault(category, []).append(inventory_path)

        # Sort each list deterministically and apply the per-category cap.
        files_block: dict[str, list[str] | dict] = {}
        for category in sorted(categorised.keys()):
            files_block[category] = _apply_category_cap(sorted(categorised[category]))
        module_data['files'] = files_block


# =============================================================================
# API Functions
# =============================================================================


def _empty_module_enrichment() -> dict:
    """Return the canonical empty-module enrichment dict.

    Shared between ``api_discover`` (which seeds per-module ``enriched.json``
    stubs at discovery time) and ``api_init`` (which fills in the same shape
    for legacy callers).
    """
    return {
        'responsibility': '',
        'responsibility_reasoning': '',
        'purpose': '',
        'purpose_reasoning': '',
        'key_packages': {},
        'internal_dependencies': [],
        'key_dependencies': [],
        'key_dependencies_reasoning': '',
        'skills_by_profile': {},
        'skills_by_profile_reasoning': '',
        'tips': [],
        'insights': [],
        'best_practices': [],
    }


def api_discover(project_dir: str = '.', force: bool = False) -> dict:
    """Run extension API discovery and persist results per-module.

    Writes the entire layout into ``.plan/project-architecture.tmp/`` first,
    then atomically replaces ``.plan/project-architecture/`` with it via
    ``os.replace``. This is the single point of fan-out for the per-module
    layout. ``_project.json`` is the single source of truth for "which modules
    exist"; per-module ``derived.json`` holds the discovery output and
    ``enriched.json`` is seeded as an empty stub so downstream readers can
    treat it as present-by-default.

    Args:
        project_dir: Project directory path
        force: Overwrite existing ``project-architecture/`` tree

    Returns:
        Dict with status, modules_discovered, output_file (the new
        ``_project.json`` path)
    """
    real_dir = get_data_dir(project_dir)
    project_meta_path = get_project_meta_path(project_dir)

    if project_meta_path.exists() and not force:
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'message': 'Use --force to overwrite',
        }

    # Import extension API for discovery (PYTHONPATH set by executor)
    from extension_discovery import discover_project_modules  # type: ignore[import-not-found]

    project_path = Path(project_dir).resolve()
    result = discover_project_modules(project_path)
    modules: dict[str, dict] = result.get('modules', {}) or {}

    # Build the project-meta document. The ``modules`` index here is the
    # canonical list — clients iterate this, not the per-module directory
    # listing on disk.
    project_meta = {
        'name': project_path.name,
        'description': '',
        'description_reasoning': '',
        'extensions_used': result.get('extensions_used', []),
        'modules': {name: {} for name in sorted(modules.keys())},
    }

    # Populate the per-module ``files`` inventory in-place. The walk happens
    # against the live working tree under ``project_path``, never against the
    # tmp-staged layout — the tree being inventoried is the user's checkout.
    _post_process_files(modules, project_dir)

    # Stage the entire new layout under .tmp/ so the swap is atomic.
    tmp_dir = get_tmp_data_dir(project_dir)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Write _project.json via the shared helper to keep encoding/formatting
    # consistent with non-tmp paths.
    project_meta_tmp = tmp_dir / FILE_PROJECT_META
    _write_json(project_meta_tmp, project_meta)

    # Write per-module derived.json + empty enriched.json stubs via the shared
    # helper so all on-disk JSON in the architecture layout flows through one
    # writer (encoding, indent, key-sort).
    for module_name, module_data in modules.items():
        module_tmp = tmp_dir / module_name
        module_tmp.mkdir(parents=True, exist_ok=True)
        _write_json(module_tmp / DIR_PER_MODULE_DERIVED, module_data)
        # Preserve any prior enrichment so re-discovery never loses LLM-authored
        # content; fall back to an empty stub on first-run discovery (driving
        # lesson 2026-05-01-21-001).
        existing = load_module_enriched_or_empty(module_name, project_dir)
        _write_json(module_tmp / DIR_PER_MODULE_ENRICHED, existing or _empty_module_enrichment())

    # Atomically swap the staged tree into place.
    swap_data_dir(tmp_dir, project_dir)

    return {
        'status': 'success',
        'modules_discovered': len(modules),
        'output_file': str(real_dir / FILE_PROJECT_META),
    }


def api_init(project_dir: str = '.', check: bool = False, force: bool = False) -> dict:
    """Initialize per-module ``enriched.json`` stubs for every module.

    With the per-module layout, ``api_discover()`` already seeds empty stubs,
    but ``api_init`` is preserved as an explicit-reset / repair entry point.

    Args:
        project_dir: Project directory path
        check: Only report status; do not write
        force: Overwrite existing per-module ``enriched.json`` stubs

    Returns:
        Dict with status and file info
    """
    project_meta_path = get_project_meta_path(project_dir)

    if check:
        if not project_meta_path.exists():
            return {'status': 'missing', 'file': str(project_meta_path)}
        try:
            module_names = iter_modules(project_dir)
        except DataNotFoundError as e:
            return {'status': 'error', 'error': str(e)}
        present = sum(
            1 for name in module_names if get_module_enriched_path(name, project_dir).exists()
        )
        return {
            'status': 'exists',
            'file': str(project_meta_path),
            'modules_enriched': present,
        }

    if not project_meta_path.exists():
        return {
            'status': 'error',
            'error': "Project metadata missing. Run 'architecture.py discover' first.",
        }

    try:
        module_names = iter_modules(project_dir)
    except DataNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

    initialised = 0
    for module_name in module_names:
        path = get_module_enriched_path(module_name, project_dir)
        if path.exists() and not force:
            continue
        save_module_enriched(module_name, _empty_module_enrichment(), project_dir)
        initialised += 1

    return {
        'status': 'success',
        'modules_initialized': initialised,
        'output_file': str(project_meta_path),
    }


def api_get_derived(project_dir: str = '.') -> dict:
    """Get raw discovered data assembled across all modules.

    Re-assembles the legacy ``{project, modules, extensions_used}`` shape from
    the per-module layout so downstream callers (CLI ``derived`` command,
    legacy tooling) continue to receive the dict shape they expect.
    """
    meta = load_project_meta(project_dir)
    modules: dict[str, dict] = {}
    for module_name in iter_modules(project_dir):
        try:
            modules[module_name] = load_module_derived(module_name, project_dir)
        except DataNotFoundError:
            # _project.json lists a module but its derived.json is missing —
            # treat as empty so callers get a stable shape.
            modules[module_name] = {}
    return {
        'project': {
            'name': meta.get('name', ''),
            'description': meta.get('description', ''),
            'description_reasoning': meta.get('description_reasoning', ''),
        },
        'modules': modules,
        'extensions_used': meta.get('extensions_used', []),
    }


def api_get_derived_module(module_name: str, project_dir: str = '.') -> dict:
    """Get raw discovered data for a single module.

    Raises:
        ModuleNotFoundInProjectError: If module not in ``_project.json``
        DataNotFoundError: If ``_project.json`` itself is missing
    """
    available = iter_modules(project_dir)
    if module_name not in available:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', available)
    try:
        return load_module_derived(module_name, project_dir)
    except DataNotFoundError:
        # Module is in the index but its derived.json is gone — surface as
        # missing data, not "module not found".
        raise


def list_modules(project_dir: str = '.') -> list:
    """List module names from ``_project.json``."""
    return iter_modules(project_dir)


# =============================================================================
# CLI Handlers
# =============================================================================


def cmd_discover(args) -> dict:
    """CLI handler for discover command."""
    try:
        return api_discover(args.project_dir, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_init(args) -> dict:
    """CLI handler for init command."""
    try:
        return api_init(args.project_dir, args.check, args.force)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived(args) -> dict:
    """CLI handler for derived command."""
    try:
        derived = api_get_derived(args.project_dir)
        return {'status': 'success', **derived}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_derived_module(args) -> dict:
    """CLI handler for derived-module command."""
    try:
        module = api_get_derived_module(args.module, args.project_dir)
        return {'status': 'success', 'module_name': args.module, 'module': module}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = iter_modules(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# Imports kept at end of file but referenced above; left in place so the
# module-level public surface remains stable for tests that introspect
# ``_cmd_manage`` (e.g. patched callable lookups).
__all__ = [
    'api_discover',
    'api_init',
    'api_get_derived',
    'api_get_derived_module',
    'list_modules',
    'cmd_discover',
    'cmd_init',
    'cmd_derived',
    'cmd_derived_module',
    '_post_process_files',
]


# Suppress unused-import lint warnings — a few helpers are imported solely so
# downstream tests can ``from _cmd_manage import ...`` them without bouncing
# through ``_architecture_core``.
_ = (
    get_module_derived_path,
    load_module_enriched,
    load_module_enriched_or_empty,
    save_project_meta,
    save_module_derived,
)
