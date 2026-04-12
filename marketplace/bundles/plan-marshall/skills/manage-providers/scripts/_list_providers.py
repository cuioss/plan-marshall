"""
List and discover providers using marshal.json declarations.

discover-and-persist: Scans PYTHONPATH directories for *_provider.py files,
loads each module, calls get_provider_declarations(), and persists the
combined declarations to marshal.json under the 'providers' key.

list-providers: Reads the 'providers' list from marshal.json and outputs it.
No filesystem scanning at runtime.
"""

import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Any

from _config_core import load_config, require_initialized, save_config  # type: ignore[import-not-found]
from file_ops import output_toon  # type: ignore[import-not-found]


def _scan_pythonpath_for_providers() -> list[dict[str, Any]]:
    """Scan PYTHONPATH directories for *_provider.py files.

    For each file found, loads the module and calls get_provider_declarations().
    Uses PYTHONPATH set by the executor (execute-script.py) which includes
    all skill script directories.

    Returns:
        List of provider declaration dicts.
    """
    providers: list[dict[str, Any]] = []
    pythonpath = os.environ.get('PYTHONPATH', '')
    if not pythonpath:
        return providers

    seen_paths: set[str] = set()

    for dir_str in pythonpath.split(os.pathsep):
        dir_path = Path(dir_str)
        if not dir_path.is_dir():
            continue

        for provider_file in sorted(dir_path.glob('*_provider.py')):
            # Deduplicate by resolved path (executor may list dirs multiple times)
            real_path = str(provider_file.resolve())
            if real_path in seen_paths:
                continue
            seen_paths.add(real_path)

            loaded = _load_provider_module(provider_file)
            if loaded:
                providers.extend(loaded)

    return providers


def _load_provider_module(path: Path) -> list[dict[str, Any]]:
    """Load a *_provider.py module and call get_provider_declarations().

    Args:
        path: Absolute path to the provider module.

    Returns:
        List of provider declaration dicts, or empty list on failure.
    """
    try:
        module_name = f'provider_{path.stem}'
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return []
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, 'get_provider_declarations'):
            result: list[dict[str, Any]] = module.get_provider_declarations()
            return result
        return []
    except Exception:
        return []


def _get_git_remote_url() -> str:
    """Get the git remote origin URL, or empty string if unavailable."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ''
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''


def _build_persisted_entry(p: dict[str, Any]) -> dict[str, Any]:
    """Build a provider entry for marshal.json persistence.

    Persists all fields needed by runtime consumers: core identity,
    URL, detection patterns, and HTTP-auth configuration.
    Maps default_url to url. For version-control providers without
    default_url, resolves url from git remote origin.
    """
    # Core fields
    entry = {k: p[k] for k in ('skill_name', 'category', 'verify_command', 'description') if k in p}
    # URL mapping
    if p.get('default_url'):
        entry['url'] = p['default_url']
    elif p.get('category') == 'version-control':
        remote_url = _get_git_remote_url()
        if remote_url:
            entry['url'] = remote_url
    # Optional structured fields (persisted when present)
    for key in ('detection', 'verify_endpoint', 'verify_method',
                'header_name', 'header_value_template', 'extra_fields'):
        if p.get(key):
            entry[key] = p[key]
    return entry


def _validate_provider_selection(
    providers: list[dict[str, Any]],
    selected_names: list[str],
) -> list[str]:
    """Validate selected providers against category cardinality rules.

    Groups selected providers by their ``category`` field and enforces:
    - ``version-control``: exactly 1 required
    - ``ci``: 0 or 1 allowed
    - ``other``: 0..N (no constraints)

    Args:
        providers: Full list of discovered provider dicts (must contain ``category``).
        selected_names: Skill names the user selected for activation.

    Returns:
        List of validation error strings. Empty list means valid.
    """
    selected_set = set(selected_names)
    # Deduplicate by skill_name (scan may find same provider via multiple PYTHONPATH entries)
    seen_skills: set[str] = set()
    selected_providers: list[dict[str, Any]] = []
    for p in providers:
        skill = p.get('skill_name', '')
        if skill in selected_set and skill not in seen_skills:
            seen_skills.add(skill)
            selected_providers.append(p)

    # Group by category
    by_category: dict[str, list[str]] = {}
    for p in selected_providers:
        cat = p.get('category', 'other')
        by_category.setdefault(cat, []).append(p.get('skill_name', ''))

    errors: list[str] = []

    # version-control: exactly 1 required
    vc_providers = by_category.get('version-control', [])
    if len(vc_providers) == 0:
        errors.append(
            'Category version-control: exactly 1 provider required but none selected'
        )
    elif len(vc_providers) > 1:
        errors.append(
            f'Category version-control: exactly 1 provider required but '
            f'{len(vc_providers)} selected: {", ".join(vc_providers)}'
        )

    # ci: 0 or 1
    ci_providers = by_category.get('ci', [])
    if len(ci_providers) > 1:
        errors.append(
            f'Category ci: at most 1 provider allowed but '
            f'{len(ci_providers)} selected: {", ".join(ci_providers)}'
        )

    # other: no constraints

    return errors


def run_discover_and_persist(args) -> int:
    """Execute the discover-and-persist subcommand.

    Scans PYTHONPATH for *_provider.py files and collects declarations.
    If --providers is given, persists only the selected subset to marshal.json.
    Otherwise, outputs the discovered list without persisting (discovery-only mode).
    """
    require_initialized()
    providers = _scan_pythonpath_for_providers()

    selected_names = [n.strip() for n in args.providers.split(',') if n.strip()] if getattr(args, 'providers', None) is not None else None

    if selected_names is None:
        # Discovery-only mode: output what was found, don't persist
        output_toon({
            'status': 'success',
            'action': 'discover',
            'count': len(providers),
            'providers': [
                {'skill_name': p.get('skill_name', ''), 'display_name': p.get('display_name', '')}
                for p in providers
            ],
        })
        return 0

    # Activation mode: persist only selected providers (deduplicate by skill_name)
    selected_set = set(selected_names)
    discovered_names = {p.get('skill_name', '') for p in providers}
    activated_seen: set[str] = set()
    activated: list[dict[str, Any]] = []
    for p in providers:
        skill = p.get('skill_name', '')
        if skill in selected_set and skill not in activated_seen:
            activated_seen.add(skill)
            activated.append(p)
    unknown = [n for n in selected_names if n not in discovered_names]

    # Validate category cardinality before persisting
    validation_errors = _validate_provider_selection(providers, selected_names)
    if validation_errors:
        output_toon({
            'status': 'error',
            'action': 'discover-and-persist',
            'validation_errors': validation_errors,
        })
        return 1

    config = load_config()
    config['providers'] = [
        _build_persisted_entry(p) for p in activated
    ]
    save_config(config)

    result: dict[str, Any] = {
        'status': 'success',
        'action': 'discover-and-persist',
        'discovered': len(providers),
        'activated': len(activated),
        'providers': [p.get('skill_name', '') for p in activated],
    }
    if unknown:
        result['unknown'] = unknown

    output_toon(result)
    return 0


def find_by_category(category: str) -> list[dict[str, Any]]:
    """Find providers by category from marshal.json.

    Args:
        category: Category to filter by (e.g., 'ci', 'version-control')

    Returns:
        List of provider dicts matching the category.
    """
    config = load_config()
    return [p for p in config.get('providers', []) if p.get('category') == category]


def run_find_by_category(args) -> int:
    """Execute the find-by-category subcommand."""
    require_initialized()
    results = find_by_category(args.category)

    output_toon({
        'status': 'success',
        'category': args.category,
        'count': len(results),
        'providers': results,
    })
    return 0


def run_list_providers(args) -> int:
    """Execute the list-providers subcommand.

    Reads the 'providers' list from marshal.json. If not present,
    outputs an empty list with a hint to run discover-and-persist.
    """
    require_initialized()
    config = load_config()
    providers: list[dict[str, Any]] = config.get('providers', [])

    formatted = []
    for p in providers:
        entry: dict[str, Any] = {
            'skill_name': p.get('skill_name', ''),
            'category': p.get('category', ''),
            'verify_command': p.get('verify_command', ''),
            'url': p.get('url', ''),
            'description': p.get('description', ''),
        }
        for key in ('detection', 'verify_endpoint', 'verify_method',
                    'header_name', 'header_value_template', 'extra_fields'):
            if p.get(key):
                entry[key] = p[key]
        formatted.append(entry)

    output_toon({
        'status': 'success',
        'count': len(providers),
        'providers': formatted,
    })
    return 0
