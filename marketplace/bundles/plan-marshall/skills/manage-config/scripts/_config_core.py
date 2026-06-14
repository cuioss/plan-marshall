"""
Core utilities for manage-config.

Shared functions for configuration loading, saving, output formatting,
and error handling used by all command modules.
"""

import json
from pathlib import Path
from typing import Any

# Direct imports - PYTHONPATH set by executor
from file_ops import (  # type: ignore[import-not-found]
    get_base_dir,
    get_marshal_path,
    get_tracked_config_dir,
    output_toon,
)
from marketplace_bundles import (  # type: ignore[import-not-found]
    resolve_bundle_path,
    resolve_bundles_root,
)

# Bundle path for skill description resolution. Resolved by walking up to a
# plan-marshall bundle ancestor instead of relying on a hard-coded depth.
BUNDLES_DIR = resolve_bundles_root(Path(__file__))

# marshal.json is tracked in the repo under .plan/; runtime state
# (run-configuration.json) lives in the per-project global directory.
PLAN_BASE_DIR = get_base_dir()
TRACKED_CONFIG_DIR = get_tracked_config_dir()
MARSHAL_PATH = get_marshal_path()
# Note: uses 'run-configuration.json', distinct from constants.FILE_RUN_CONFIG ('run-config.json')
RUN_CONFIG_PATH = PLAN_BASE_DIR / 'run-configuration.json'


class MarshalNotInitializedError(Exception):
    """Raised when marshal.json doesn't exist and operation requires it."""

    pass


def is_initialized() -> bool:
    """Check if marshal.json exists."""
    return MARSHAL_PATH.exists()


def require_initialized() -> None:
    """Raise exception if marshal.json doesn't exist."""
    if not TRACKED_CONFIG_DIR.exists():
        raise MarshalNotInitializedError(
            f"Directory '{TRACKED_CONFIG_DIR}' does not exist. Run command /marshall-steward first"
        )
    if not MARSHAL_PATH.exists():
        raise MarshalNotInitializedError('marshal.json not found. Run command /marshall-steward first')


def load_config() -> dict:
    """Load marshal.json."""
    try:
        config: dict = json.loads(MARSHAL_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f'Invalid JSON in {MARSHAL_PATH}: {e}') from e
    return config


def save_config(config: dict) -> None:
    """Save config to marshal.json with ordered keys."""
    MARSHAL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Canonical key order for marshal.json. Several legacy top-level blocks were
    # dissolved or relocated: their config was distributed back into the owning
    # phase blocks, and the build map now lives at the top-level build.map. The
    # order leads with ``plan`` (the primary user-facing config) followed by
    # ``build`` (build infrastructure), then lists the remaining top-level keys
    # alphabetically. ``extension_defaults`` precedes both as the
    # extension-seeded defaults block.
    key_order = [
        'extension_defaults',
        'plan',
        'build',
        'project',
        'providers',
        'skill_domains',
        'system',
    ]

    # Build ordered dict: known keys first in order, then any remaining keys
    ordered = {}
    for key in key_order:
        if key in config:
            ordered[key] = config[key]
    for key in config:
        if key not in ordered:
            ordered[key] = config[key]

    MARSHAL_PATH.write_text(json.dumps(ordered, indent=2, ensure_ascii=False), encoding='utf-8')


def load_run_config() -> dict:
    """Load run-configuration.json (local, not shared via git)."""
    if RUN_CONFIG_PATH.exists():
        config: dict = json.loads(RUN_CONFIG_PATH.read_text(encoding='utf-8'))
        return config
    return {'version': 1, 'commands': {}}


def save_run_config(config: dict) -> None:
    """Save config to run-configuration.json."""
    RUN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding='utf-8')


def output(data: dict) -> None:
    """Output TOON result to stdout."""
    output_toon(data)


def error_exit(message: str, **extra) -> dict:
    """Return error dict."""
    return {'status': 'error', 'error': message, **extra}


def success_exit(data: dict) -> dict:
    """Return success dict."""
    return {'status': 'success', **data}


def _parse_skill_md_description(skill_path: Path, fallback: str) -> str:
    """Parse description from a SKILL.md file's YAML frontmatter.

    Args:
        skill_path: Path to SKILL.md file
        fallback: Value to return if parsing fails

    Returns:
        Description string or fallback
    """
    if not skill_path.exists():
        return fallback

    content = skill_path.read_text(encoding='utf-8')

    # Parse YAML frontmatter (between --- markers)
    if not content.startswith('---'):
        return fallback

    end_marker = content.find('---', 3)
    if end_marker == -1:
        return fallback

    frontmatter = content[3:end_marker].strip()

    # Simple YAML parsing for description field
    for line in frontmatter.split('\n'):
        if line.lstrip().startswith('description:'):
            desc = line.split(':', 1)[1].strip()
            # Remove quotes if present
            if len(desc) > 1 and desc[0] == desc[-1] and desc[0] in ('"', "'"):
                desc = desc[1:-1]
            return desc

    return fallback


def get_skill_description(skill_notation: str) -> str:
    """Extract description from SKILL.md frontmatter.

    Supports two notation formats:
    - Marketplace: "bundle:skill" → bundles/{bundle}/skills/{skill}/SKILL.md
    - Project-level: "project:skill" → .claude/skills/{skill}/SKILL.md

    Args:
        skill_notation: e.g., "pm-dev-java:java-core" or "project:sync-plugin-cache"

    Returns:
        Description string or skill name as fallback
    """
    try:
        parts = skill_notation.split(':')
        if len(parts) != 2:
            return skill_notation
        prefix, skill = parts

        if prefix == 'project':
            # Project-level skill: resolve from .claude/skills/
            skill_path = Path('.claude') / 'skills' / skill / 'SKILL.md'
        else:
            # Marketplace skill: resolve from bundles directory, handling the
            # versioned plugin-cache layout via resolve_bundle_path.
            skill_path = resolve_bundle_path(BUNDLES_DIR, prefix, f'skills/{skill}/SKILL.md')

        return _parse_skill_md_description(skill_path, skill_notation)
    except (OSError, ValueError):
        # Path resolution or a SKILL.md read failure falls back to the raw
        # notation; a genuine bug (e.g. a programming error) still propagates.
        return skill_notation


def _coerce_value(value: str) -> str | bool | int:
    """Coerce string value to appropriate Python type.

    Converts 'true'/'false' (case-insensitive) to bool and digit strings to int.
    All other values are returned unchanged.
    """
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    elif value.isdigit():
        return int(value)
    return value


def is_nested_domain(domain_config: dict) -> bool:
    """Check if domain config uses nested structure.

    Nested domains have one of:
    - 'bundle' key (technical domains with profiles in extension.py)
    - 'execute_task_skills' key (system domain with profile-to-execute-task-skill mapping)
    - 'workflow_skill_extensions' key (domain extensions for outline/triage)
    - 'project_skills' key (project-level skills attached to a domain)
    """
    return (
        'bundle' in domain_config
        or 'execute_task_skills' in domain_config
        or 'workflow_skill_extensions' in domain_config
        or 'project_skills' in domain_config
    )


# =============================================================================
# Extension Defaults API
# =============================================================================


def get_extension_defaults(config: dict) -> dict:
    """Get extension_defaults section from config, ensuring it exists."""
    if 'extension_defaults' not in config:
        config['extension_defaults'] = {}
    ext: dict = config['extension_defaults']
    return ext


def ext_defaults_get(key: str, project_dir: str = '.') -> str | None:
    """Get extension default value by key.

    Args:
        key: The key to retrieve
        project_dir: Project directory containing .plan/

    Returns:
        The value if found, None otherwise
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return None

    config: dict = json.loads(marshal_path.read_text(encoding='utf-8'))
    ext = get_extension_defaults(config)
    result: str | None = ext.get(key)
    return result


def ext_defaults_set(key: str, value: str, project_dir: str = '.') -> None:
    """Set extension default value (always overwrites).

    Args:
        key: The key to set
        value: The value to store
        project_dir: Project directory containing .plan/
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    config: dict = json.loads(marshal_path.read_text(encoding='utf-8')) if marshal_path.exists() else {}
    ext = get_extension_defaults(config)
    ext[key] = value

    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def ext_defaults_set_default(key: str, value: str, project_dir: str = '.') -> bool:
    """Set extension default value only if key doesn't exist (write-once).

    Args:
        key: The key to set
        value: The value to store
        project_dir: Project directory containing .plan/

    Returns:
        True if value was set, False if key already existed
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    config: dict = json.loads(marshal_path.read_text(encoding='utf-8')) if marshal_path.exists() else {}
    ext = get_extension_defaults(config)

    if key in ext:
        return False

    ext[key] = value
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return True


def ext_defaults_list(project_dir: str = '.') -> dict:
    """List all extension defaults.

    Args:
        project_dir: Project directory containing .plan/

    Returns:
        Dictionary of all extension defaults
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return {}

    config: dict = json.loads(marshal_path.read_text(encoding='utf-8'))
    result: dict = get_extension_defaults(config)
    return result


# =============================================================================
# Build Map API
# =============================================================================
#
# The build.map block in marshal.json is the file-to-build contract: a
# per-domain inventory of {glob, role, build_class} entries seeded from every
# registered extension's explicit (pattern, role) routes (classify_globs()) +
# classify_build_class(). It is the user-adaptable persistence layer for what
# each domain's predicates compute in Python. The build_map lives at the
# top-level build.map (its owning block) and is required and always seeded —
# there is no separate override layer; user corrections are made directly to the
# seeded entries.


class BuildMapMissingError(Exception):
    """Raised when build.map is required but absent (fail-closed)."""

    pass


def get_build_map(config: dict) -> dict[str, list[dict[str, str]]]:
    """Return the ``build.map`` block, or an empty dict when absent.

    Read-only helper that locates the relocated ``build_map`` under the
    top-level ``build`` block. Returns ``{}`` (not an error) when the block is
    absent — callers that require it fail-closed via :func:`merge_build_map`.
    """
    build = config.get('build')
    if not isinstance(build, dict):
        return {}
    build_map = build.get('map')
    if not isinstance(build_map, dict):
        return {}
    return build_map


def aggregate_build_map() -> dict[str, list[dict[str, str]]]:
    """Aggregate the ``(glob, role, build_class)`` build map per *applicable* domain.

    Seeds the build map from each build system's explicit ``(pattern, role)``
    routes. Every build skill's ``BuildExtensionBase`` subclass declares its routes
    via ``classify_globs()``; the ``script-shared`` route collector
    (``derive_globs_from_tree``, reached via the
    ``extension_discovery.derive_build_map_globs`` bridge) gathers those routes
    verbatim, keyed by each build extension's served domain key — it no longer
    scans the tree to enumerate one glob per directory. A route's single-``*``
    fnmatch pattern can span ``/`` (e.g. ``marketplace/targets/*.py`` covers
    ``marketplace/targets/generate.py`` and any nested file, and
    ``marketplace/bundles/*.py`` covers every
    ``*/skills/plan-marshall-plugin/extension.py``), so a compact route set covers
    files outside the obvious roots. Each collected ``(glob, role)`` route is then
    stamped with its build extension's ``classify_build_class(glob, role)``.
    Completeness is a separate concern: ``validate_tree_completeness`` scans
    git-tracked source files and flags any tracked ``.py`` no declared route
    covers.

    Routes and build_class come from the build extensions (Axis-B); applicability
    scoping remains gated on the *language* extension's ``applies_to_module()``
    (Axis-A skill-loading domain applicability — the single source of truth for
    "does this project use python/java/..."). A domain's routes are included only
    when that domain's owning *language* extension's ``applies_to_module()`` returns
    ``applicable: True`` for at least one discovered project module.
    ``applies_to_module()`` over the discovered module architecture
    (``discover_project_modules`` keyed off the tracked-config parent) is the same
    predicate architecture enrichment uses — so a Python-only project never
    receives java/oci/javascript routes merely because those build skills are
    installed. When module discovery yields no modules (e.g. architecture not yet
    discovered), the aggregation is empty: the seed runs only after architecture
    discovery (wizard Step 8b, the sole authoritative seed point). Each
    ``applies_to_module()`` call is wrapped in the same defensive try/except as the
    build_class stamp so one misbehaving extension cannot crash the seed.

    Returns:
        A dict keyed by domain-key with a list of ``{glob, role, build_class}``
        dicts as values. Non-applicable domains and domains contributing no routes
        are omitted entirely.
    """
    from extension_discovery import (  # type: ignore[import-not-found]
        derive_build_map_globs,
        discover_all_extensions,
        discover_build_extensions,
    )

    build_extensions = discover_build_extensions()

    # Map each domain key to the BUILD extension module that owns its routes, so
    # the build_class stamp below queries the right build system's classifier. The
    # deriver keys its output by domain key (its tie-break mirrors _safe_domain_key),
    # so an identical first-domain-key lookup recovers the owning build extension.
    # build-maven and build-gradle both serve 'java'; the first wins here, but the
    # role->build_class default is identical for both, so the stamp is the same.
    build_module_by_domain: dict[str, Any] = {}
    for entry in build_extensions:
        ext = entry.get('module')
        if ext is None:
            continue
        domain_key = _safe_domain_key(ext)
        if domain_key and domain_key not in build_module_by_domain:
            build_module_by_domain[domain_key] = ext

    # Applicability ground truth comes from the LANGUAGE extensions (Axis-A):
    # whether the project's modules use python/java/... gates whether that domain's
    # build routes are seeded. Map each domain key to its language extension module.
    language_extensions = discover_all_extensions()
    language_module_by_domain: dict[str, Any] = {}
    for entry in language_extensions:
        ext = entry.get('module')
        if ext is None:
            continue
        domain_key = _safe_domain_key(ext)
        if domain_key and domain_key not in language_module_by_domain:
            language_module_by_domain[domain_key] = ext

    project_root = get_tracked_config_dir().parent

    # Applicability ground truth: a domain applies when its owning LANGUAGE
    # extension's applies_to_module() is applicable for at least one discovered
    # module. With no discovered modules the seed is post-architecture-only, so the
    # aggregation is empty rather than the unscoped full set.
    applicable_domains = _applicable_domain_keys(project_root, language_module_by_domain)

    derived = derive_build_map_globs(project_root, build_extensions)

    aggregated: dict[str, list[dict[str, str]]] = {}
    for domain_key, entries in derived.items():
        if domain_key not in applicable_domains:
            continue
        ext = build_module_by_domain.get(domain_key)
        if ext is None:
            continue
        domain_entries: list[dict[str, str]] = []
        for glob, role in entries:
            try:
                build_class = ext.classify_build_class(glob, role)
            except Exception:
                continue
            domain_entries.append({'glob': glob, 'role': role, 'build_class': build_class})
        if domain_entries:
            aggregated[domain_key] = domain_entries
    return aggregated


def _applicable_domain_keys(project_root: Path, module_by_domain: dict[str, Any]) -> set[str]:
    """Return the set of domain keys applicable to the discovered project modules.

    A domain key is applicable when its owning extension's ``applies_to_module()``
    returns ``applicable: True`` for at least one module from
    ``discover_project_modules(project_root)``. ``discover_project_modules`` is
    resolved from the ``extension_discovery`` module at call time (mirroring the
    other collaborators) so tests can redirect it. When no modules are discovered
    the returned set is empty — the seed runs only after architecture discovery.
    Each ``applies_to_module()`` call is defended so a single misbehaving extension
    cannot crash the seed.
    """
    from extension_discovery import (  # type: ignore[import-not-found]
        discover_project_modules,
    )

    try:
        discovered = discover_project_modules(project_root)
    except Exception:
        return set()
    modules = discovered.get('modules') if isinstance(discovered, dict) else None
    if not isinstance(modules, dict) or not modules:
        return set()

    applicable: set[str] = set()
    for domain_key, ext in module_by_domain.items():
        for module_data in modules.values():
            try:
                result = ext.applies_to_module(module_data)
            except Exception:
                continue
            if isinstance(result, dict) and result.get('applicable'):
                applicable.add(domain_key)
                break
    return applicable


def _safe_domain_key(ext: object) -> str:
    """Return the extension's first domain key, or empty string on failure.

    Mirrors the manage-execution-manifest aggregator's tie-break helper: an
    extension whose ``get_skill_domains()`` cannot be resolved is skipped rather
    than crashing the seed.
    """
    try:
        domains = ext.get_skill_domains()  # type: ignore[attr-defined]
        if domains:
            return str(domains[0].get('domain', {}).get('key', '') or '')
    except Exception:
        pass
    return ''


def seed_build_map_into(config: dict, force: bool = False) -> dict:
    """Seed ``build.map`` into ``config``.

    Aggregates the per-domain build map from every registered extension and
    writes it into ``config['build']['map']``. The top-level ``build`` container
    is created when absent. The caller is responsible for persisting ``config``
    (e.g. via :func:`save_config`).

    Default (``force=False``): write-once semantics — an existing ``build_map``
    is NEVER clobbered, so a re-seed preserves any user correction made directly
    to the seeded block.

    With ``force=True``: the write-once guard is bypassed — any existing
    ``build_map`` is cleared and re-derived from the current project state.

    Args:
        config: The loaded marshal.json config dict (mutated in place when
            seeded or re-derived).
        force: When True, clear any existing ``build_map`` and re-derive a clean
            one, discarding stale or hand-edited entries.

    Returns:
        A result dict with ``action`` (``seeded`` | ``preserved`` |
        ``re-derived``), the ``build_map`` that is now in ``config``, and its
        ``domain_count``.
    """
    build = config.get('build')
    if not isinstance(build, dict):
        build = {}
        config['build'] = build

    existing = build.get('map')
    if isinstance(existing, dict) and not force:
        return {'action': 'preserved', 'build_map': existing, 'domain_count': len(existing)}

    action = 're-derived' if 'map' in build else 'seeded'
    aggregated = aggregate_build_map()
    build['map'] = aggregated
    return {'action': action, 'build_map': aggregated, 'domain_count': len(aggregated)}


def merge_build_map(config: dict) -> dict[str, list[dict[str, str]]]:
    """Return the effective build map read from ``build.map``.

    The ``build_map`` is the single source of truth — there is no override
    layer. This function fails closed: when ``build.map`` is absent or is a
    non-dict (corrupt) value it raises :class:`BuildMapMissingError` rather than
    returning an empty dict or crashing, so a missing or corrupt seed surfaces
    as a structured error instead of a silent no-build or an untyped
    ``AttributeError``.

    Args:
        config: The loaded marshal.json config dict (read-only — never mutated).

    Returns:
        A deep copy of the ``{domain: [{glob, role, build_class}]}`` dict from
        ``build.map``.

    Raises:
        BuildMapMissingError: When ``build.map`` is absent or is not a dict.
    """
    build = config.get('build')
    seed = build.get('map') if isinstance(build, dict) else None
    if not isinstance(seed, dict):
        raise BuildMapMissingError(
            'build.map is absent or not a dict. Run `manage-config build-map seed` '
            'or re-run /marshall-steward to seed it.'
        )

    # Deep-copy the seed so the caller never mutates the persisted block.
    # Wrap in try/except to surface partially corrupt entries (e.g. {'python': None}
    # or {'python': 'not a list'}) as a structured BuildMapMissingError instead of
    # an untyped TypeError from the inner list comprehension.
    try:
        return {domain: [dict(entry) for entry in entries] for domain, entries in seed.items()}
    except (TypeError, ValueError) as exc:
        raise BuildMapMissingError(
            'build.map is corrupt. Run `manage-config build-map seed` '
            'or re-run /marshall-steward to seed it.'
        ) from exc


def _glob_set(entries: list[dict[str, str]]) -> set[str]:
    """Return the set of ``glob`` strings from a list of build-map entries.

    Tolerates non-dict / glob-less entries by skipping them, so a partially
    corrupt persisted block degrades to a glob diff over the entries it can read
    rather than raising.
    """
    globs: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict):
            glob = entry.get('glob')
            if isinstance(glob, str):
                globs.add(glob)
    return globs


def compute_build_map_drift(config: dict) -> dict:
    """Diff the persisted ``build.map`` against the live derivation.

    Read-only comparison of the current derived map (via
    :func:`aggregate_build_map`) against the persisted ``build.map`` block (via
    :func:`get_build_map`). The diff is per-domain on the ``glob`` surface:

    - ``added_globs``: globs present in the derivation but absent from the
      persisted block (a route the project gained since the map was last seeded).
    - ``removed_globs``: globs present in the persisted block but absent from the
      derivation (a route the project lost, or a deliberate hand-edit).

    A domain that appears in only one of the two maps contributes its globs
    entirely to ``added_globs`` (derivation-only) or ``removed_globs``
    (persisted-only).

    Never mutates ``config``.

    Args:
        config: The loaded marshal.json config dict (read-only).

    Returns:
        A dict with ``in_sync: bool`` and ``drift: {domain: {added_globs,
        removed_globs}}``. ``drift`` carries only domains with a non-empty diff;
        ``in_sync`` is ``True`` exactly when ``drift`` is empty.
    """
    derived = aggregate_build_map()
    persisted = get_build_map(config)

    drift: dict[str, dict[str, list[str]]] = {}
    for domain in sorted(set(derived) | set(persisted)):
        derived_globs = _glob_set(derived.get(domain, []))
        persisted_globs = _glob_set(persisted.get(domain, []))
        added = sorted(derived_globs - persisted_globs)
        removed = sorted(persisted_globs - derived_globs)
        if added or removed:
            drift[domain] = {'added_globs': added, 'removed_globs': removed}

    return {'in_sync': not drift, 'drift': drift}


def normalize_keys() -> dict:
    """Re-write marshal.json with the canonical top-level key order.

    Loads the persisted config and re-saves it via :func:`save_config`, whose
    ``key_order`` is the single source of truth for the canonical order. No
    ordering logic is duplicated here. Idempotent: an already-canonical file is
    rewritten to the same bytes.

    Returns:
        A result dict with ``action: 'normalized'``.
    """
    require_initialized()
    config = load_config()
    save_config(config)
    return {'action': 'normalized'}
