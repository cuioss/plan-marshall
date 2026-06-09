"""
Core utilities for manage-config.

Shared functions for configuration loading, saving, output formatting,
and error handling used by all command modules.
"""

import json
from pathlib import Path

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

    # Canonical key order for marshal.json. The dissolved/relocated top-level
    # blocks (ci, ceremony_policy, build_map, build_map_overrides) are gone:
    # ci/ceremony-policy config was distributed back into its owning phase
    # blocks, and build_map lives nested under skill_domains. The order lists
    # every surviving top-level key alphabetically.
    key_order = [
        'extension_defaults',
        'plan',
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
    except Exception:
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
# The skill_domains.build_map block in marshal.json is the file-to-build
# contract: a per-domain inventory of {glob, role, build_class} entries seeded
# from every registered extension's classify_globs() + classify_build_class().
# It is the user-adaptable persistence layer for what each domain's predicates
# compute in Python. The build_map lives under skill_domains (its owning block)
# and is required and always seeded — there is no separate override layer; user
# corrections are made directly to the seeded entries.


class BuildMapMissingError(Exception):
    """Raised when skill_domains.build_map is required but absent (fail-closed)."""

    pass


def get_build_map(config: dict) -> dict[str, list[dict[str, str]]]:
    """Return the ``skill_domains.build_map`` block, or an empty dict when absent.

    Read-only helper that locates the relocated ``build_map`` under
    ``skill_domains``. Returns ``{}`` (not an error) when the block is absent —
    callers that require it fail-closed via :func:`merge_build_map`.
    """
    skill_domains = config.get('skill_domains')
    if not isinstance(skill_domains, dict):
        return {}
    build_map = skill_domains.get('build_map')
    if not isinstance(build_map, dict):
        return {}
    return build_map


def aggregate_build_map() -> dict[str, list[dict[str, str]]]:
    """Walk every registered extension and aggregate its (glob, role, build_class).

    For each discovered extension, calls ``classify_globs()`` to learn the
    domain's (glob, role) inventory and ``classify_build_class(glob, role)`` per
    entry to derive the build_class. Extensions with no classify override
    contribute an empty list (the base ``classify_globs()`` default), so they are
    skipped — the resulting map only carries domains that own file types.

    Returns:
        A dict keyed by domain-key with a list of ``{glob, role, build_class}``
        dicts as values. Domains contributing no globs are omitted entirely.
    """
    from extension_discovery import discover_all_extensions  # type: ignore[import-not-found]

    aggregated: dict[str, list[dict[str, str]]] = {}
    for entry in discover_all_extensions():
        ext = entry.get('module')
        if ext is None:
            continue
        try:
            inventory = ext.classify_globs()
        except Exception:
            continue
        if not inventory:
            continue
        domain_key = _safe_domain_key(ext)
        if not domain_key:
            continue
        domain_entries: list[dict[str, str]] = []
        for glob, role in inventory:
            try:
                build_class = ext.classify_build_class(glob, role)
            except Exception:
                continue
            domain_entries.append({'glob': glob, 'role': role, 'build_class': build_class})
        if domain_entries:
            aggregated[domain_key] = domain_entries
    return aggregated


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


def seed_build_map_into(config: dict) -> dict:
    """Seed ``skill_domains.build_map`` into ``config`` (write-once).

    Aggregates the per-domain build map from every registered extension and
    writes it into ``config['skill_domains']['build_map']`` using write-once
    semantics: an existing ``build_map`` is NEVER clobbered, so a re-seed
    preserves any user correction made directly to the seeded block. The
    ``skill_domains`` container is created when absent. The caller is
    responsible for persisting ``config`` (e.g. via :func:`save_config`).

    Args:
        config: The loaded marshal.json config dict (mutated in place when seeded).

    Returns:
        A result dict with ``action`` (``seeded`` | ``preserved``), the
        ``build_map`` that is now in ``config``, and its ``domain_count``.
    """
    skill_domains = config.get('skill_domains')
    if not isinstance(skill_domains, dict):
        skill_domains = {}
        config['skill_domains'] = skill_domains

    if 'build_map' in skill_domains:
        existing: dict = skill_domains['build_map']
        return {'action': 'preserved', 'build_map': existing, 'domain_count': len(existing)}

    aggregated = aggregate_build_map()
    skill_domains['build_map'] = aggregated
    return {'action': 'seeded', 'build_map': aggregated, 'domain_count': len(aggregated)}


def merge_build_map(config: dict) -> dict[str, list[dict[str, str]]]:
    """Return the effective build map read from ``skill_domains.build_map``.

    The ``build_map`` is the single source of truth — there is no override
    layer. This function fails closed: when ``skill_domains.build_map`` is
    absent it raises :class:`BuildMapMissingError` rather than returning an
    empty dict, so a missing seed surfaces as a structured error instead of a
    silent no-build.

    Args:
        config: The loaded marshal.json config dict (read-only — never mutated).

    Returns:
        A deep copy of the ``{domain: [{glob, role, build_class}]}`` dict from
        ``skill_domains.build_map``.

    Raises:
        BuildMapMissingError: When ``skill_domains.build_map`` is absent.
    """
    skill_domains = config.get('skill_domains')
    if not isinstance(skill_domains, dict) or 'build_map' not in skill_domains:
        raise BuildMapMissingError(
            'skill_domains.build_map is absent. Run `manage-config build-map seed` '
            'or re-run /marshall-steward to seed it.'
        )
    seed: dict[str, list[dict[str, str]]] = skill_domains['build_map']

    # Deep-copy the seed so the caller never mutates the persisted block.
    return {domain: [dict(entry) for entry in entries] for domain, entries in seed.items()}
