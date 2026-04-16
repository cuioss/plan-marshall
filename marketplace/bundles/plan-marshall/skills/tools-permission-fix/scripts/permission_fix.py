#!/usr/bin/env python3
"""Permission fix - write operations for Claude Code settings.

Provides:
- apply-fixes: Apply safe fixes (normalize, dedupe, sort, defaults)
- add: Add a permission to settings
- remove: Remove a permission from settings
- ensure: Ensure multiple permissions exist
- consolidate: Consolidate timestamped permissions with wildcards
- ensure-wildcards: Ensure marketplace wildcards exist
- apply-project-step-permissions: Append Skill({skill}) rules for project: steps in marshal.json
- generate-wildcards: Generate permission wildcards from marketplace inventory
- ensure-executor: Ensure the executor permission exists
- cleanup-scripts: Remove redundant individual script permissions
- migrate-executor: Full migration to executor-only permission pattern
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Bootstrap sys.path — this script may run before the executor sets up PYTHONPATH
# (called directly during wizard Step 3 to ensure executor permission).
# Step 1: locate script-shared/scripts via identity walk so we can import the
# shared anchor helper. Step 2: use resolve_skills_root to derive _SKILLS_DIR.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from marketplace_bundles import resolve_skills_root  # type: ignore[import-not-found]  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format', 'tools-file-ops', 'tools-permission-doctor'):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

from permission_common import (  # type: ignore[import-not-found]  # noqa: E402
    EXIT_SUCCESS,
    get_project_settings_path_for_write,
    get_settings_path,
    load_settings,
    load_settings_path,
    save_settings,
)
from permission_doctor import (  # type: ignore[import-not-found]  # noqa: E402
    extract_project_steps,
    load_marshal_config,
    skill_permission_covered,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402

# Executor-only permission pattern
EXECUTOR_PERMISSION = 'Bash(python3 .plan/execute-script.py *)'
OVERLY_BROAD_PYTHON = 'Bash(python3:*)'

# Default permissions for plan directory and plugin cache
DEFAULT_PERMISSIONS = [
    'Edit(.plan/**)',
    'Write(.plan/**)',
    'Read(~/.claude/plugins/cache/**)',  # Skills reference files via relative paths
]

# Timestamp patterns for consolidation
TIMESTAMP_PATTERN = re.compile(r'^(\w+)\((.*/)?(.+)-(\d{4}-\d{2}-\d{2}-\d{6})\.(\w+)\)$')
DATE_PATTERN = re.compile(r'^(\w+)\((.*/)?(.+)-(\d{4}-\d{2}-\d{2})\.(\w+)\)$')


# =============================================================================
# apply-fixes subcommand
# =============================================================================


def normalize_path_perm(permission: str) -> tuple[str, bool]:
    """Normalize a permission path."""
    match = re.match(r'^(\w+)\((.+?)(/)?\)$', permission)
    if not match:
        return permission, False

    perm_type = match.group(1)
    path = match.group(2)
    trailing = match.group(3)

    if trailing and not path.endswith('*'):
        return f'{perm_type}({path})', True

    return permission, False


def remove_duplicates(perm_list: list[str]) -> tuple[list[str], int]:
    """Remove duplicate permissions from a list."""
    seen = set()
    result = []
    duplicates = 0

    for perm in perm_list:
        if perm in seen:
            duplicates += 1
        else:
            seen.add(perm)
            result.append(perm)

    return result, duplicates


def process_permission_list(perm_list: list[str]) -> tuple[list[str], int, int, bool]:
    """Process a single permission list: normalize, dedupe, sort."""
    paths_fixed = 0
    normalized = []

    for perm in perm_list:
        norm_perm, changed = normalize_path_perm(perm)
        normalized.append(norm_perm)
        if changed:
            paths_fixed += 1

    deduplicated, dups = remove_duplicates(normalized)
    sorted_list = sorted(deduplicated)
    was_sorted = sorted_list != deduplicated

    return sorted_list, paths_fixed, dups, was_sorted


def add_default_permissions(allow_list: list[str]) -> list[str]:
    """Add default permissions if missing."""
    added = []
    for default_perm in DEFAULT_PERMISSIONS:
        if default_perm not in allow_list:
            allow_list.append(default_perm)
            added.append(default_perm)
    return added


def resolve_settings_arg(args) -> str:
    """Resolve settings path from --settings or --scope argument."""
    if hasattr(args, 'settings') and args.settings:
        return str(args.settings)
    if hasattr(args, 'scope') and args.scope:
        return str(get_settings_path(args.scope))
    return str(get_project_settings_path_for_write())


def cmd_apply_fixes(args) -> dict:
    """Handle apply-fixes subcommand."""
    settings_path = resolve_settings_arg(args)
    settings, error = load_settings(settings_path)
    if error:
        return {'status': 'error', 'error': error}

    total_duplicates = 0
    total_paths_fixed = 0
    was_sorted = False

    for key in ['allow', 'deny', 'ask']:
        perm_list = settings.get('permissions', {}).get(key, [])
        processed, paths_fixed, dups, sorted_flag = process_permission_list(perm_list)

        settings['permissions'][key] = processed
        total_paths_fixed += paths_fixed
        total_duplicates += dups
        was_sorted = was_sorted or sorted_flag

    defaults_added = []
    allow_list = settings['permissions']['allow']
    defaults_added = add_default_permissions(allow_list)
    if defaults_added:
        settings['permissions']['allow'] = sorted(allow_list)
        was_sorted = True

    changes_made = total_duplicates > 0 or total_paths_fixed > 0 or len(defaults_added) > 0 or was_sorted

    result = {
        'duplicates_removed': total_duplicates,
        'paths_fixed': total_paths_fixed,
        'defaults_added': defaults_added,
        'sorted': was_sorted,
        'changes_made': changes_made,
        'dry_run': args.dry_run,
        'settings_path': settings_path,
    }

    if not args.dry_run and changes_made:
        result['applied'] = save_settings(settings_path, settings)
        if not result['applied']:
            result['error'] = 'Failed to save settings'
    else:
        result['applied'] = False

    result.setdefault('status', 'success')
    return result


# =============================================================================
# add subcommand
# =============================================================================


def cmd_add(args) -> dict:
    """Handle add subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    result: dict[str, Any] = {'settings_file': str(settings_path)}

    if args.permission in allow_list:
        result['success'] = True
        result['action'] = 'already_exists'
        result.setdefault("status", "success")
        return result

    allow_list.append(args.permission)
    allow_list.sort()

    if save_settings(str(settings_path), settings):
        result['success'] = True
        result['action'] = 'added'
    else:
        result['success'] = False
        result['error'] = 'Failed to save settings'

    result['status'] = 'success' if result.get('success', True) else 'error'
    return result


# =============================================================================
# remove subcommand
# =============================================================================


def cmd_remove(args) -> dict:
    """Handle remove subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    result: dict[str, Any] = {'settings_file': str(settings_path)}

    if args.permission not in allow_list:
        result['success'] = True
        result['action'] = 'not_found'
        result.setdefault("status", "success")
        return result

    allow_list.remove(args.permission)

    if save_settings(str(settings_path), settings):
        result['success'] = True
        result['action'] = 'removed'
    else:
        result['success'] = False
        result['error'] = 'Failed to save settings'

    result['status'] = 'success' if result.get('success', True) else 'error'
    return result


# =============================================================================
# ensure subcommand
# =============================================================================


def cmd_ensure(args) -> dict:
    """Handle ensure subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    permissions = [p.strip() for p in args.permissions.split(',')]

    added = []
    already_exists = []

    for perm in permissions:
        if perm in allow_list:
            already_exists.append(perm)
        else:
            allow_list.append(perm)
            added.append(perm)

    result = {
        'settings_file': str(settings_path),
        'added': added,
        'already_exists': already_exists,
        'added_count': len(added),
        'total_permissions': len(allow_list),
    }

    if added:
        allow_list.sort()
        if save_settings(str(settings_path), settings):
            result['success'] = True
        else:
            result['success'] = False
            result['error'] = 'Failed to save settings'
    else:
        result['success'] = True

    result['status'] = 'success' if result.get('success', True) else 'error'
    return result


# =============================================================================
# consolidate subcommand
# =============================================================================


def parse_timestamped_permission(permission: str) -> dict | None:
    """Parse a permission to check if it contains a timestamp pattern."""
    match = TIMESTAMP_PATTERN.match(permission)
    if match:
        perm_type, path_prefix, base_name, timestamp, extension = match.groups()
        return {
            'permission': permission,
            'type': perm_type,
            'path_prefix': path_prefix or '',
            'base_name': base_name,
            'timestamp': timestamp,
            'extension': extension,
        }

    match = DATE_PATTERN.match(permission)
    if match:
        perm_type, path_prefix, base_name, timestamp, extension = match.groups()
        return {
            'permission': permission,
            'type': perm_type,
            'path_prefix': path_prefix or '',
            'base_name': base_name,
            'timestamp': timestamp,
            'extension': extension,
        }

    return None


def generate_wildcard(parsed_permissions: list[dict]) -> str:
    """Generate a wildcard pattern from a list of parsed timestamped permissions."""
    if not parsed_permissions:
        return ''

    first = parsed_permissions[0]
    perm_type = first['type']
    base_name = first['base_name']
    extension = first['extension']
    path_prefixes = {p['path_prefix'] for p in parsed_permissions}

    if len(path_prefixes) == 1:
        path_prefix = first['path_prefix']
        return f'{perm_type}({path_prefix}{base_name}-*.{extension})'

    return f'{perm_type}(**/{base_name}-*.{extension})'


def cmd_consolidate(args) -> dict:
    """Handle consolidate subcommand."""
    settings_path = resolve_settings_arg(args)
    settings, error = load_settings(settings_path)
    if error:
        return {'status': 'error', 'error': error}

    allow_list = settings.get('permissions', {}).get('allow', [])
    timestamped_groups = defaultdict(list)
    non_timestamped = []

    for permission in allow_list:
        parsed = parse_timestamped_permission(permission)
        if parsed:
            key = (parsed['type'], parsed['base_name'], parsed['extension'])
            timestamped_groups[key].append(parsed)
        else:
            non_timestamped.append(permission)

    wildcards_to_add = []
    permissions_to_remove = []

    for _key, group in timestamped_groups.items():
        if len(group) >= 2:
            wildcard = generate_wildcard(group)
            wildcards_to_add.append(wildcard)
            permissions_to_remove.extend([p['permission'] for p in group])

    result = {
        'consolidated': len(permissions_to_remove),
        'removed': permissions_to_remove,
        'wildcards_added': wildcards_to_add,
        'changes': {'timestamped_groups_found': len(timestamped_groups), 'non_timestamped_kept': len(non_timestamped)},
        'dry_run': args.dry_run,
        'settings_path': settings_path,
    }

    if not args.dry_run and result['consolidated'] > 0:
        for perm in permissions_to_remove:
            if perm in allow_list:
                allow_list.remove(perm)
        for wildcard in wildcards_to_add:
            if wildcard not in allow_list:
                allow_list.append(wildcard)
        allow_list.sort()

        if save_settings(settings_path, settings):
            result['applied'] = True
        else:
            result['error'] = 'Failed to save settings'
            result['applied'] = False
    else:
        result['applied'] = False

    result.setdefault('status', 'success')
    return result


# =============================================================================
# ensure-wildcards subcommand
# =============================================================================


def has_skills(bundle: dict) -> bool:
    """Check if a bundle has skills defined.

    Returns True if:
    - 'skills' key exists and is a non-empty list, OR
    - Neither 'skills' nor 'commands' keys exist (assume bundle has both)
    """
    skills = bundle.get('skills')
    commands = bundle.get('commands')

    # If skills key exists, check if it's a non-empty list
    if skills is not None:
        return isinstance(skills, list) and len(skills) > 0

    # If neither skills nor commands exist (real marketplace.json format),
    # assume the bundle has skills
    if skills is None and commands is None:
        return True

    return False


def has_commands(bundle: dict) -> bool:
    """Check if a bundle has commands defined.

    Returns True if:
    - 'commands' key exists and is a non-empty list, OR
    - Neither 'skills' nor 'commands' keys exist (assume bundle has both)
    """
    skills = bundle.get('skills')
    commands = bundle.get('commands')

    # If commands key exists, check if it's a non-empty list
    if commands is not None:
        return isinstance(commands, list) and len(commands) > 0

    # If neither skills nor commands exist (real marketplace.json format),
    # assume the bundle has commands
    if skills is None and commands is None:
        return True

    return False


def generate_required_wildcards(marketplace: dict) -> list[str]:
    """Generate list of required wildcard permissions from marketplace.

    Expects 'bundles' as a dict where keys are bundle names and values
    are bundle data (from scan-marketplace-inventory JSON output).

    For bundles without explicit skills/commands arrays,
    assumes the bundle has both skills and commands.
    """
    wildcards = []
    bundles = marketplace.get('bundles', {})

    for bundle_name, bundle_data in bundles.items():
        if not bundle_name:
            continue

        if has_skills(bundle_data):
            wildcards.append(f'Skill({bundle_name}:*)')
        if has_commands(bundle_data):
            wildcards.append(f'SlashCommand(/{bundle_name}:*)')

    return wildcards


def cmd_ensure_wildcards(args) -> dict:
    """Handle ensure-wildcards subcommand."""
    settings, error = load_settings(args.settings)
    if error:
        return {'status': 'error', 'error': error}

    marketplace_path = Path(args.marketplace_json)
    if not marketplace_path.exists():
        return {'status': 'error', 'error': f'Marketplace file not found: {args.marketplace_json}'}

    try:
        with open(marketplace_path) as f:
            marketplace = json.load(f)
    except json.JSONDecodeError as e:
        return {'status': 'error', 'error': f'Invalid JSON in {args.marketplace_json}: {e}'}

    allow_list = settings.get('permissions', {}).get('allow', [])
    allow_set = set(allow_list)
    required_wildcards = generate_required_wildcards(marketplace)

    added = []
    already_present = 0

    for wildcard in required_wildcards:
        if wildcard in allow_set:
            already_present += 1
        else:
            added.append(wildcard)

    # Count bundles from dict
    bundles = marketplace.get('bundles', {})

    result = {
        'added': added,
        'already_present': already_present,
        'total': len(required_wildcards),
        'bundles_analyzed': len(bundles),
        'dry_run': args.dry_run,
        'settings_path': args.settings,
        'marketplace_path': args.marketplace_json,
    }

    if not args.dry_run and len(added) > 0:
        for wildcard in added:
            if wildcard not in allow_list:
                allow_list.append(wildcard)
        allow_list.sort()

        if save_settings(args.settings, settings):
            result['applied'] = True
        else:
            result['error'] = 'Failed to save settings'
            result['applied'] = False
    else:
        result['applied'] = False

    result.setdefault('status', 'success')
    return result


# =============================================================================
# apply-project-step-permissions subcommand
# =============================================================================


def cmd_apply_project_step_permissions(args) -> dict:
    """Handle apply-project-step-permissions subcommand.

    Detects project:{skill} step references in marshal.json that lack matching
    Skill({skill}) allow rules, then appends the missing entries to the allow
    list (sorted). Supports --dry-run to preview without writing.
    """
    marshal_config, marshal_error = load_marshal_config(args.marshal)
    if marshal_error:
        return {'status': 'error', 'error': marshal_error}

    settings_path = args.settings
    settings, settings_error = load_settings(settings_path)
    if settings_error:
        return {'status': 'error', 'error': settings_error}

    allow_list = settings.setdefault('permissions', {}).setdefault('allow', [])
    project_steps = extract_project_steps(marshal_config)

    # Preserve insertion order while deduplicating: each skill only gets one rule.
    seen_skills: set[str] = set()
    to_add: list[dict] = []
    already_present: list[dict] = []

    for entry in project_steps:
        covering = skill_permission_covered(entry['skill'], allow_list)
        if covering is not None:
            already_present.append({**entry, 'covered_by': covering})
            continue
        if entry['skill'] in seen_skills:
            continue
        seen_skills.add(entry['skill'])
        to_add.append({**entry, 'rule': f'Skill({entry["skill"]})'})

    added_rules = [item['rule'] for item in to_add]

    if not args.dry_run and added_rules:
        for rule in added_rules:
            if rule not in allow_list:
                allow_list.append(rule)
        allow_list.sort()

        if save_settings(settings_path, settings):
            applied = True
        else:
            return {
                'status': 'error',
                'error': 'Failed to save settings',
                'missing': to_add,
                'settings_path': settings_path,
            }
    else:
        applied = False

    return {
        'status': 'success',
        'added': added_rules,
        'missing': to_add,
        'already_present': already_present,
        'summary': {
            'added_count': len(added_rules),
            'already_present_count': len(already_present),
            'project_steps_checked': len(project_steps),
        },
        'dry_run': args.dry_run,
        'applied': applied,
        'marshal_path': args.marshal,
        'settings_path': settings_path,
    }


# =============================================================================
# generate-wildcards subcommand
# =============================================================================


def extract_command_prefix(command_name: str) -> str:
    """Extract the prefix from a command name."""
    parts = command_name.split('-')
    if len(parts) > 1:
        return parts[0]
    return command_name


def extract_skill_prefix(skill_name: str) -> str:
    """Extract the prefix from a skill name."""
    parts = skill_name.split('-')
    if len(parts) > 1:
        return parts[0]
    return skill_name


def generate_skill_wildcards(bundles: list[dict]) -> list[str]:
    """Generate Skill wildcards for bundles with skills."""
    wildcards = []
    for bundle in bundles:
        if bundle.get('skills') and len(bundle['skills']) > 0:
            wildcards.append(f'Skill({bundle["name"]}:*)')
    return sorted(wildcards)


def generate_command_bundle_wildcards(bundles: list[dict]) -> list[str]:
    """Generate SlashCommand wildcards for bundles with commands."""
    wildcards = []
    for bundle in bundles:
        if bundle.get('commands') and len(bundle['commands']) > 0:
            wildcards.append(f'SlashCommand(/{bundle["name"]}:*)')
    return sorted(wildcards)


def generate_command_shortform_permissions(bundles: list[dict]) -> list[str]:
    """Generate SlashCommand permissions for each command."""
    permissions = []
    for bundle in bundles:
        for command in bundle.get('commands', []):
            permissions.append(f'SlashCommand(/{command["name"]}:*)')
    return sorted(permissions)


def count_scripts(bundles: list[dict]) -> int:
    """Count total scripts in bundles."""
    total = 0
    for bundle in bundles:
        total += len(bundle.get('scripts', []))
    return total


def analyze_naming_patterns(bundles: list[dict]) -> dict[str, Any]:
    """Analyze naming patterns in skills and commands."""
    skill_prefixes = set()
    command_prefixes = set()
    bundle_names = []

    for bundle in bundles:
        bundle_names.append(bundle['name'])
        for skill in bundle.get('skills', []):
            prefix = extract_skill_prefix(skill['name'])
            skill_prefixes.add(prefix)
        for command in bundle.get('commands', []):
            prefix = extract_command_prefix(command['name'])
            command_prefixes.add(prefix)

    return {
        'bundle_names': sorted(bundle_names),
        'skill_prefixes': sorted(skill_prefixes),
        'command_prefixes': sorted(command_prefixes),
    }


def build_bundle_summary(bundles: list[dict]) -> list[dict]:
    """Build summary of each bundle's contents."""
    summaries = []
    for bundle in bundles:
        summaries.append(
            {
                'name': bundle['name'],
                'skills': {
                    'count': len(bundle.get('skills', [])),
                    'names': [s['name'] for s in bundle.get('skills', [])],
                },
                'commands': {
                    'count': len(bundle.get('commands', [])),
                    'names': [c['name'] for c in bundle.get('commands', [])],
                },
                'scripts': {
                    'count': len(bundle.get('scripts', [])),
                    'names': [s['name'] for s in bundle.get('scripts', [])],
                },
            }
        )
    return summaries


def scan_marketplace_dir(marketplace_dir: str) -> dict:
    """Scan a marketplace directory to build inventory from plugin.json files.

    Reads marketplace.json to discover bundles, then reads each bundle's
    plugin.json to extract skills, commands, and scripts counts.
    """
    base = Path(marketplace_dir)
    marketplace_json = base / '.claude-plugin' / 'marketplace.json'
    if not marketplace_json.exists():
        return {'status': 'error', 'error': f'marketplace.json not found at {marketplace_json}'}

    try:
        with open(marketplace_json, encoding='utf-8') as f:
            marketplace = json.load(f)
    except json.JSONDecodeError as e:
        return {'status': 'error', 'error': f'Invalid JSON in {marketplace_json}: {e}'}

    bundles = []
    for plugin in marketplace.get('plugins', []):
        bundle_name = plugin.get('name', '')
        source = plugin.get('source', '')
        # Resolve bundle path relative to marketplace dir
        bundle_dir = (base / source).resolve() if source else base / 'bundles' / bundle_name
        plugin_json_path = bundle_dir / '.claude-plugin' / 'plugin.json'

        bundle_entry: dict[str, Any] = {'name': bundle_name}
        if plugin_json_path.exists():
            try:
                with open(plugin_json_path, encoding='utf-8') as pf:
                    plugin_data = json.load(pf)
                bundle_entry['skills'] = [{'name': Path(s).stem} for s in plugin_data.get('skills', [])]
                bundle_entry['commands'] = [{'name': Path(c).stem} for c in plugin_data.get('commands', [])]
                bundle_entry['scripts'] = []  # Scripts not listed in plugin.json
            except json.JSONDecodeError:
                bundle_entry['skills'] = []
                bundle_entry['commands'] = []
                bundle_entry['scripts'] = []
        else:
            bundle_entry['skills'] = []
            bundle_entry['commands'] = []
            bundle_entry['scripts'] = []

        bundles.append(bundle_entry)

    total_skills = sum(len(b.get('skills', [])) for b in bundles)
    total_commands = sum(len(b.get('commands', [])) for b in bundles)

    return {
        'bundles': bundles,
        'statistics': {
            'total_bundles': len(bundles),
            'total_skills': total_skills,
            'total_commands': total_commands,
        },
    }


def cmd_generate_wildcards(args) -> dict:
    """Handle generate-wildcards subcommand."""
    if args.marketplace_dir:
        inventory = scan_marketplace_dir(args.marketplace_dir)
        if inventory.get('status') == 'error':
            return inventory
    else:
        try:
            if args.input:
                with open(args.input) as f:
                    inventory = json.load(f)
            else:
                inventory = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            return {'status': 'error', 'error': f'Invalid JSON input: {e}'}
        except FileNotFoundError:
            return {'status': 'error', 'error': f'Input file not found: {args.input}'}

    bundles = inventory.get('bundles', [])

    if not bundles:
        result: dict[str, Any] = {
            'error': 'No bundles found in inventory',
            'statistics': {
                'bundles_scanned': 0,
                'skills_found': 0,
                'commands_found': 0,
                'scripts_found': 0,
                'wildcards_generated': 0,
            },
        }
        result.setdefault("status", "success")
        return result

    skill_wildcards = generate_skill_wildcards(bundles)
    command_bundle_wildcards = generate_command_bundle_wildcards(bundles)
    command_shortform = generate_command_shortform_permissions(bundles)

    stats = inventory.get('statistics', {})
    total_scripts = count_scripts(bundles)
    wildcards_generated = len(skill_wildcards) + len(command_bundle_wildcards) + len(command_shortform)
    patterns = analyze_naming_patterns(bundles)
    bundle_summary = build_bundle_summary(bundles)

    result = {
        'statistics': {
            'bundles_scanned': stats.get('total_bundles', len(bundles)),
            'skills_found': stats.get('total_skills', 0),
            'commands_found': stats.get('total_commands', 0),
            'scripts_found': total_scripts,
            'wildcards_generated': wildcards_generated,
            'breakdown': {
                'skill_bundle_wildcards': len(skill_wildcards),
                'command_bundle_wildcards': len(command_bundle_wildcards),
                'command_shortform_permissions': len(command_shortform),
            },
        },
        'naming_patterns': patterns,
        'bundle_summary': bundle_summary,
        'permissions': {
            'skill_wildcards': skill_wildcards,
            'command_bundle_wildcards': command_bundle_wildcards,
            'command_shortform': command_shortform,
        },
        'coverage': {
            'skills_covered': f'{stats.get("total_skills", 0)} skills covered by {len(skill_wildcards)} bundle wildcards',
            'commands_covered': f'{stats.get("total_commands", 0)} commands covered by {len(command_bundle_wildcards)} bundle wildcards + {len(command_shortform)} short-form permissions',
            'scripts_note': f'{total_scripts} scripts - handled by relative path architecture (no permissions needed)',
        },
    }
    result.setdefault('status', 'success')
    return result


# =============================================================================
# ensure-executor subcommand
# =============================================================================


def cmd_ensure_executor(args) -> dict:
    """Handle ensure-executor subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    result = {'executor_permission': EXECUTOR_PERMISSION, 'settings_file': str(settings_path), 'dry_run': args.dry_run}

    if EXECUTOR_PERMISSION in allow_list:
        result['action'] = 'already_exists'
        result['success'] = True
        result.setdefault("status", "success")
        return result

    if not args.dry_run:
        allow_list.append(EXECUTOR_PERMISSION)
        allow_list.sort()
        if save_settings(str(settings_path), settings):
            result['action'] = 'added'
            result['success'] = True
        else:
            result['error'] = 'Failed to save settings'
            result['success'] = False
    else:
        result['action'] = 'would_add'
        result['success'] = True

    result['status'] = 'success' if result.get('success', True) else 'error'
    return result


# =============================================================================
# cleanup-scripts subcommand
# =============================================================================


def is_individual_script_permission(permission: str) -> bool:
    """Check if permission is an individual marketplace script path permission."""
    return permission.startswith('Bash(python3 ') and '/marketplace/bundles/' in permission and '/scripts' in permission


def cmd_cleanup_scripts(args) -> dict:
    """Handle cleanup-scripts subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    # Find permissions to remove
    individual_scripts = [p for p in allow_list if is_individual_script_permission(p)]
    broad_python = OVERLY_BROAD_PYTHON in allow_list and args.remove_broad_python

    result = {
        'settings_file': str(settings_path),
        'individual_script_permissions': individual_scripts,
        'individual_count': len(individual_scripts),
        'broad_python_found': OVERLY_BROAD_PYTHON in allow_list,
        'broad_python_removed': broad_python,
        'dry_run': args.dry_run,
    }

    if not individual_scripts and not broad_python:
        result['action'] = 'nothing_to_remove'
        result['success'] = True
        result.setdefault("status", "success")
        return result

    if not args.dry_run:
        # Remove individual script permissions
        for perm in individual_scripts:
            allow_list.remove(perm)

        # Optionally remove overly broad python permission
        if broad_python:
            allow_list.remove(OVERLY_BROAD_PYTHON)

        if save_settings(str(settings_path), settings):
            result['action'] = 'removed'
            result['success'] = True
            result['total_removed'] = len(individual_scripts) + (1 if broad_python else 0)
        else:
            result['error'] = 'Failed to save settings'
            result['success'] = False
    else:
        result['action'] = 'would_remove'
        result['success'] = True
        result['total_would_remove'] = len(individual_scripts) + (1 if broad_python else 0)

    result['status'] = 'success' if result.get('success', True) else 'error'
    return result


# =============================================================================
# migrate-executor subcommand
# =============================================================================


def cmd_migrate_executor(args) -> dict:
    """Handle migrate-executor subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings['permissions']['allow']

    # Step 1: Check/add executor permission
    executor_action = 'already_exists'
    if EXECUTOR_PERMISSION not in allow_list:
        if not args.dry_run:
            allow_list.append(EXECUTOR_PERMISSION)
            executor_action = 'added'
        else:
            executor_action = 'would_add'

    # Step 2: Find permissions to remove
    individual_scripts = [p for p in allow_list if is_individual_script_permission(p)]
    broad_python = OVERLY_BROAD_PYTHON in allow_list and args.remove_broad_python

    # Calculate removals
    total_to_remove = len(individual_scripts) + (1 if broad_python else 0)

    if not args.dry_run:
        # Remove individual script permissions
        for perm in individual_scripts:
            if perm in allow_list:
                allow_list.remove(perm)

        # Optionally remove overly broad python permission
        if broad_python and OVERLY_BROAD_PYTHON in allow_list:
            allow_list.remove(OVERLY_BROAD_PYTHON)

        allow_list.sort()

        if not save_settings(str(settings_path), settings):
            return {'status': 'error', 'error': 'Failed to save settings', 'success': False}

    result = {
        'success': True,
        'settings_file': str(settings_path),
        'dry_run': args.dry_run,
        'executor': {'permission': EXECUTOR_PERMISSION, 'action': executor_action},
        'cleanup': {
            'individual_removed': total_to_remove if not args.dry_run else 0,
            'individual_would_remove': total_to_remove if args.dry_run else 0,
            'individual_permissions': individual_scripts,
            'broad_python_removed': broad_python,
        },
        'summary': f'Migrated to executor-only pattern: 1 permission replaces {len(individual_scripts)} individual script permissions',
    }

    result.setdefault('status', 'success')
    return result


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Permission fix - write operations for Claude Code settings')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # apply-fixes subcommand
    p_fix = subparsers.add_parser('apply-fixes', help='Apply safe fixes to permission settings')
    p_fix_group = p_fix.add_mutually_exclusive_group(required=True)
    p_fix_group.add_argument('--settings', help='Path to settings file to fix')
    p_fix_group.add_argument('--scope', choices=['global', 'project'], help='Target scope (auto-resolves path)')
    p_fix.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_fix.set_defaults(func=cmd_apply_fixes)

    # add subcommand
    p_add = subparsers.add_parser('add', help='Add a permission to settings')
    p_add.add_argument('--permission', required=True, help='Permission to add')
    p_add.add_argument(
        '--target', default='project', choices=['global', 'project'], help='Target settings file (default: project)'
    )
    p_add.set_defaults(func=cmd_add)

    # remove subcommand
    p_rem = subparsers.add_parser('remove', help='Remove a permission from settings')
    p_rem.add_argument('--permission', required=True, help='Permission to remove')
    p_rem.add_argument(
        '--target', default='project', choices=['global', 'project'], help='Target settings file (default: project)'
    )
    p_rem.set_defaults(func=cmd_remove)

    # ensure subcommand
    p_ens = subparsers.add_parser('ensure', help='Ensure multiple permissions exist')
    p_ens.add_argument('--permissions', required=True, help='Comma-separated permissions to ensure')
    p_ens.add_argument(
        '--target', default='global', choices=['global', 'project'], help='Target settings file (default: global)'
    )
    p_ens.set_defaults(func=cmd_ensure)

    # consolidate subcommand
    p_con = subparsers.add_parser('consolidate', help='Consolidate timestamped permissions with wildcards')
    p_con_group = p_con.add_mutually_exclusive_group(required=True)
    p_con_group.add_argument('--settings', help='Path to settings file to analyze and modify')
    p_con_group.add_argument('--scope', choices=['global', 'project'], help='Target scope (auto-resolves path)')
    p_con.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_con.set_defaults(func=cmd_consolidate)

    # ensure-wildcards subcommand
    p_ewc = subparsers.add_parser('ensure-wildcards', help='Ensure marketplace wildcards exist in settings')
    p_ewc.add_argument('--settings', required=True, help='Path to settings file to update')
    p_ewc.add_argument('--marketplace-json', required=True, help='Path to marketplace.json file')
    p_ewc.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_ewc.set_defaults(func=cmd_ensure_wildcards)

    # apply-project-step-permissions subcommand
    p_apps = subparsers.add_parser(
        'apply-project-step-permissions',
        help='Append Skill({skill}) allow rules for project: steps in marshal.json',
    )
    p_apps.add_argument('--marshal', required=True, help='Path to marshal.json')
    p_apps.add_argument('--settings', required=True, help='Path to settings file to update')
    p_apps.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_apps.set_defaults(func=cmd_apply_project_step_permissions)

    # generate-wildcards subcommand
    p_gen = subparsers.add_parser('generate-wildcards', help='Generate permission wildcards from marketplace inventory')
    p_gen_group = p_gen.add_mutually_exclusive_group()
    p_gen_group.add_argument('--marketplace-dir', help='Marketplace directory to scan (reads plugin.json files)')
    p_gen_group.add_argument('--input', '-i', help='Input JSON file (default: stdin)')
    p_gen.set_defaults(func=cmd_generate_wildcards)

    # ensure-executor subcommand
    p_exe = subparsers.add_parser('ensure-executor', help='Ensure the executor permission exists')
    p_exe.add_argument(
        '--target', default='global', choices=['global', 'project'], help='Target settings file (default: global)'
    )
    p_exe.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_exe.set_defaults(func=cmd_ensure_executor)

    # cleanup-scripts subcommand
    p_cln = subparsers.add_parser('cleanup-scripts', help='Remove redundant individual script permissions')
    p_cln.add_argument(
        '--target', default='global', choices=['global', 'project'], help='Target settings file (default: global)'
    )
    p_cln.add_argument('--remove-broad-python', action='store_true', help='Also remove Bash(python3:*) wildcard')
    p_cln.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_cln.set_defaults(func=cmd_cleanup_scripts)

    # migrate-executor subcommand
    p_mig = subparsers.add_parser('migrate-executor', help='Full migration to executor-only permission pattern')
    p_mig.add_argument(
        '--target', default='global', choices=['global', 'project'], help='Target settings file (default: global)'
    )
    p_mig.add_argument('--remove-broad-python', action='store_true', help='Also remove Bash(python3:*) wildcard')
    p_mig.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_mig.set_defaults(func=cmd_migrate_executor)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 2

    result = args.func(args)
    print(serialize_toon(result))
    return EXIT_SUCCESS


if __name__ == '__main__':
    from file_ops import safe_main  # type: ignore[import-not-found]

    safe_main(main)()
