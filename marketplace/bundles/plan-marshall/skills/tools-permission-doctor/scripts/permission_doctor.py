#!/usr/bin/env python3
"""Permission doctor - read-only analysis for Claude Code settings.

Provides:
- detect-redundant: Detect redundant permissions between global and local settings
- detect-suspicious: Detect suspicious permissions matching anti-patterns
- detect-missing-project-step-permissions: Detect project:{skill} steps in marshal.json
  without matching Skill({skill}) allow rules in project settings
"""

import argparse
import json
import re
from pathlib import Path

from permission_common import (  # type: ignore[import-not-found]
    EXIT_SUCCESS,
    get_global_settings_path,
    get_project_settings_path,
    load_settings,
    resolve_scope_to_paths,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# detect-redundant subcommand
# =============================================================================


def is_marketplace_permission(permission: str, project_root: Path | None = None) -> bool:
    """Check if a permission is a marketplace permission.

    Args:
        permission: The permission string to check
        project_root: Project root directory for checking project-local commands.
                      If None, uses current working directory.

    Returns:
        True if the permission is for a marketplace plugin (should be in global settings),
        False if it's a project-local command or not a marketplace permission.
    """
    # Skill permissions are always marketplace
    if permission.startswith('Skill('):
        return True

    # SlashCommand permissions need special handling
    if permission.startswith('SlashCommand(/'):
        # Extract command name from SlashCommand(/command-name)
        match = re.match(r'^SlashCommand\(/([^)]+)\)$', permission)
        if match:
            command_name = match.group(1)
            # Check if this is a project-local command
            root = project_root or Path.cwd()
            local_command_path = root / '.claude' / 'commands' / f'{command_name}.md'
            if local_command_path.exists():
                # This is a project-local command, NOT a marketplace permission
                return False
        # SlashCommand not found locally - assume marketplace
        return True

    return False


def extract_permission_parts(permission: str) -> tuple[str, str]:
    """Extract the type and pattern from a permission string."""
    match = re.match(r'^(\w+)\((.+)\)$', permission)
    if match:
        return match.group(1), match.group(2)
    return permission, ''


def is_covered_by_wildcard(specific: str, broader: str) -> bool:
    """Check if a specific permission is covered by a broader wildcard pattern."""
    spec_type, spec_pattern = extract_permission_parts(specific)
    broad_type, broad_pattern = extract_permission_parts(broader)

    if spec_type != broad_type:
        return False

    if broad_pattern.endswith(':*'):
        prefix = broad_pattern[:-1]
        if spec_pattern.startswith(prefix):
            return True

    if broad_type in ('Read', 'Write', 'Edit'):
        broad_base = broad_pattern.rstrip('*').rstrip('/')
        spec_base = spec_pattern.rstrip('*').rstrip('/')
        if spec_base.startswith(broad_base) and len(spec_base) > len(broad_base):
            return True

    return False


def cmd_detect_redundant(args) -> dict:
    """Handle detect-redundant subcommand."""
    # Resolve paths from --scope or explicit args
    if args.scope:
        global_path, local_path = resolve_scope_to_paths(args.scope)
    else:
        global_path = args.global_settings
        local_path = args.local_settings

    global_settings, global_error = load_settings(global_path)
    if global_error:
        return {'status': 'error', 'error': global_error, 'global_exists': False}

    local_settings, local_error = load_settings(local_path)
    if local_error:
        return {'status': 'error', 'error': local_error, 'local_exists': False}

    global_allow = set(global_settings.get('permissions', {}).get('allow', []))
    local_allow = local_settings.get('permissions', {}).get('allow', [])

    # Derive project root from local settings path for command detection
    project_root = Path(local_path).parent.parent if local_path else None

    redundant = []
    marketplace_in_local = []

    for local_perm in local_allow:
        if local_perm in global_allow:
            redundant.append(
                {
                    'permission': local_perm,
                    'reason': 'Exact duplicate exists in global settings',
                    'type': 'exact_duplicate',
                    'covered_by': local_perm,
                }
            )
            continue

        if is_marketplace_permission(local_perm, project_root):
            marketplace_in_local.append(
                {
                    'permission': local_perm,
                    'reason': 'Marketplace permissions should be in global settings',
                    'type': 'marketplace_permission',
                }
            )
            continue

        for global_perm in global_allow:
            if is_covered_by_wildcard(local_perm, global_perm):
                redundant.append(
                    {
                        'permission': local_perm,
                        'reason': 'Covered by broader wildcard in global settings',
                        'type': 'covered_by_wildcard',
                        'covered_by': global_perm,
                    }
                )
                break

    result = {
        'redundant': redundant,
        'marketplace_in_local': marketplace_in_local,
        'summary': {
            'redundant_count': len(redundant),
            'marketplace_in_local_count': len(marketplace_in_local),
            'total_issues': len(redundant) + len(marketplace_in_local),
            'local_permissions_checked': len(local_allow),
            'global_permissions_count': len(global_allow),
        },
        'global_exists': True,
        'local_exists': True,
        'global_path': global_path,
        'local_path': local_path,
        'status': 'success',
    }
    return result


# =============================================================================
# detect-suspicious subcommand
# =============================================================================

SUSPICIOUS_PATTERNS = [
    {'pattern': r'^Write\(\/\*\*\)$', 'reason': 'Root write access', 'severity': 'high', 'category': 'root_access'},
    {'pattern': r'^Read\(\/\*\*\)$', 'reason': 'Root read access', 'severity': 'high', 'category': 'root_access'},
    {
        'pattern': r'^Write\(\/etc\/.*\)$',
        'reason': 'System configuration write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Write\(\/dev\/.*\)$',
        'reason': 'Device file write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Write\(\/sys\/.*\)$',
        'reason': 'System kernel interface write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Write\(\/proc\/.*\)$',
        'reason': 'Process information write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Write\(\/boot\/.*\)$',
        'reason': 'Boot files write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Write\(\/root\/.*\)$',
        'reason': 'Root user home directory write access',
        'severity': 'high',
        'category': 'system_directory',
    },
    {
        'pattern': r'^Bash\(sudo:.*\)$',
        'reason': 'Privilege escalation - sudo access',
        'severity': 'high',
        'category': 'dangerous_command',
    },
    {
        'pattern': r'^Bash\(rm:-rf.*\)$',
        'reason': 'Recursive force delete',
        'severity': 'high',
        'category': 'dangerous_command',
    },
    {
        'pattern': r'^Bash\(dd:.*\)$',
        'reason': 'Low-level disk operations',
        'severity': 'high',
        'category': 'dangerous_command',
    },
    {
        'pattern': r'^Bash\(mkfs:.*\)$',
        'reason': 'Filesystem creation',
        'severity': 'high',
        'category': 'dangerous_command',
    },
    {
        'pattern': r'^Bash\(fdisk:.*\)$',
        'reason': 'Disk partitioning',
        'severity': 'high',
        'category': 'dangerous_command',
    },
    {'pattern': r'.*\|\s*bash.*', 'reason': 'Piping to bash', 'severity': 'high', 'category': 'dangerous_command'},
    {'pattern': r'.*\|\s*sh.*', 'reason': 'Piping to sh', 'severity': 'high', 'category': 'dangerous_command'},
    {
        'pattern': r'^Write\(\/tmp\/.*\)$',
        'reason': 'System temp directory write access',
        'severity': 'medium',
        'category': 'temp_directory',
    },
    {
        'pattern': r'^Write\(\/var\/tmp\/.*\)$',
        'reason': 'Persistent temp directory write access',
        'severity': 'medium',
        'category': 'temp_directory',
    },
    {
        'pattern': r'^Write\(\/private\/tmp\/.*\)$',
        'reason': 'macOS private temp directory write access',
        'severity': 'medium',
        'category': 'temp_directory',
    },
    {
        'pattern': r'^Read\(\/\/Users\/\*\*\)$',
        'reason': 'All users read access',
        'severity': 'medium',
        'category': 'broad_access',
    },
    {
        'pattern': r'^Write\(\/\/Users\/\*\*\)$',
        'reason': 'All users write access',
        'severity': 'high',
        'category': 'broad_access',
    },
    {
        'pattern': r'^Read\(\/\/home\/\*\*\)$',
        'reason': 'All home directories read access',
        'severity': 'medium',
        'category': 'broad_access',
    },
    {
        'pattern': r'^Write\(\/\/home\/\*\*\)$',
        'reason': 'All home directories write access',
        'severity': 'high',
        'category': 'broad_access',
    },
    {
        'pattern': r'^Bash\(curl:\*\)$',
        'reason': 'Unrestricted curl access',
        'severity': 'low',
        'category': 'network_access',
    },
    {
        'pattern': r'^Bash\(wget:\*\)$',
        'reason': 'Unrestricted wget access',
        'severity': 'low',
        'category': 'network_access',
    },
]


def load_approved_permissions(approved_file: str | None) -> set[str]:
    """Load user-approved permissions from run-configuration file."""
    if not approved_file:
        return set()

    approved_path = Path(approved_file)
    if not approved_path.exists():
        return set()

    try:
        with open(approved_path) as f:
            data = json.load(f)
        commands = data.get('commands', {})
        setup_perms = commands.get('setup-project-permissions', {})
        approved_list = setup_perms.get('user_approved_permissions', [])
        return set(approved_list)
    except (json.JSONDecodeError, KeyError):
        return set()


def check_permission(permission: str) -> dict | None:
    """Check if a permission matches any suspicious pattern."""
    for pattern_info in SUSPICIOUS_PATTERNS:
        if re.match(pattern_info['pattern'], permission, re.IGNORECASE):
            return {
                'permission': permission,
                'reason': pattern_info['reason'],
                'severity': pattern_info['severity'],
                'category': pattern_info['category'],
            }
    return None


def cmd_detect_suspicious(args) -> dict:
    """Handle detect-suspicious subcommand."""
    # Resolve path from --scope or explicit --settings
    if args.scope:
        if args.scope == 'global':
            settings_path = str(get_global_settings_path())
        else:  # project
            settings_path = str(get_project_settings_path())
    else:
        settings_path = args.settings

    settings, error = load_settings(settings_path)
    if error:
        return {'status': 'error', 'error': error}

    approved_permissions = load_approved_permissions(args.approved_file)
    allow_list = settings.get('permissions', {}).get('allow', [])

    suspicious = []
    already_approved = []

    for permission in allow_list:
        if permission in approved_permissions:
            check_result = check_permission(permission)
            if check_result:
                already_approved.append(permission)
            continue

        check_result = check_permission(permission)
        if check_result:
            suspicious.append(check_result)

    severity_counts = {'high': 0, 'medium': 0, 'low': 0}
    for item in suspicious:
        severity_counts[item['severity']] += 1

    result = {
        'suspicious': suspicious,
        'already_approved': already_approved,
        'summary': {
            'total_suspicious': len(suspicious),
            'already_approved_count': len(already_approved),
            'by_severity': severity_counts,
            'permissions_checked': len(allow_list),
        },
        'settings_path': settings_path,
    }
    if args.approved_file:
        result['approved_file'] = args.approved_file

    result['status'] = 'success'
    return result


# =============================================================================
# detect-missing-project-step-permissions subcommand
# =============================================================================

# Phases in marshal.json that may contain project:{skill} step references
PROJECT_STEP_PHASES = ('phase-5-execute', 'phase-6-finalize')


def load_marshal_config(path: str) -> tuple[dict, str | None]:
    """Load marshal.json config file.

    Args:
        path: Absolute or relative path to marshal.json.

    Returns:
        Tuple of (config_dict, error_message). Error is None on success.
    """
    marshal_path = Path(path)
    if not marshal_path.exists():
        return {}, f'marshal.json not found: {path}'

    try:
        with open(marshal_path) as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return {}, f'Invalid JSON in {path}: {e}'


def extract_project_steps(marshal_config: dict) -> list[dict]:
    """Enumerate project:{skill} step references from marshal.json.

    Scans phases in PROJECT_STEP_PHASES under `plan.{phase}.steps` and filters
    entries beginning with `project:`.

    Returns:
        List of dicts with keys: skill, step, phase.
    """
    plan = marshal_config.get('plan', {})
    project_steps = []

    for phase in PROJECT_STEP_PHASES:
        phase_config = plan.get(phase, {})
        steps = phase_config.get('steps', [])
        for step in steps:
            if isinstance(step, str) and step.startswith('project:'):
                skill = step[len('project:') :]
                project_steps.append({'skill': skill, 'step': step, 'phase': phase})

    return project_steps


def skill_permission_covered(skill: str, allow_list: list[str]) -> str | None:
    """Check if a skill is covered by an allow rule.

    Matches exact `Skill({skill})` or covering wildcard `Skill({skill}:*)`.

    Returns:
        The matching rule string, or None if no match found.
    """
    exact = f'Skill({skill})'
    wildcard = f'Skill({skill}:*)'
    for rule in allow_list:
        if rule == exact or rule == wildcard:
            return rule
    return None


def cmd_detect_missing_project_step_permissions(args) -> dict:
    """Handle detect-missing-project-step-permissions subcommand."""
    marshal_config, marshal_error = load_marshal_config(args.marshal)
    if marshal_error:
        return {'status': 'error', 'error': marshal_error}

    if args.scope:
        settings_path = str(get_project_settings_path()) if args.scope == 'project' else str(get_global_settings_path())
    else:
        settings_path = args.settings

    settings, settings_error = load_settings(settings_path)
    if settings_error:
        return {'status': 'error', 'error': settings_error}

    allow_list = settings.get('permissions', {}).get('allow', [])
    project_steps = extract_project_steps(marshal_config)

    missing = []
    present = []
    for entry in project_steps:
        covering = skill_permission_covered(entry['skill'], allow_list)
        if covering is None:
            missing.append(entry)
        else:
            present.append({**entry, 'covered_by': covering})

    result = {
        'missing': missing,
        'present': present,
        'summary': {
            'missing_count': len(missing),
            'present_count': len(present),
            'project_steps_checked': len(project_steps),
        },
        'marshal_path': args.marshal,
        'settings_path': settings_path,
        'status': 'success',
    }
    return result


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Permission doctor - read-only analysis for Claude Code settings', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # detect-redundant subcommand
    p_red = subparsers.add_parser(
        'detect-redundant', help='Detect redundant permissions between global and local settings', allow_abbrev=False
    )
    p_red_group = p_red.add_mutually_exclusive_group(required=True)
    p_red_group.add_argument(
        '--scope', choices=['both'], help='Analyze both global and project settings (auto-resolves paths)'
    )
    p_red_group.add_argument('--global-settings', help='Path to global settings file (requires --local-settings)')
    p_red.add_argument('--local-settings', help='Path to local/project settings file (required with --global-settings)')
    p_red.set_defaults(func=cmd_detect_redundant)

    # detect-suspicious subcommand
    p_sus = subparsers.add_parser(
        'detect-suspicious', help='Detect suspicious permissions matching anti-patterns', allow_abbrev=False
    )
    p_sus_group = p_sus.add_mutually_exclusive_group(required=True)
    p_sus_group.add_argument('--settings', help='Path to settings file to analyze')
    p_sus_group.add_argument('--scope', choices=['global', 'project'], help='Target scope (auto-resolves path)')
    p_sus.add_argument('--approved-file', help='Path to run-configuration file with user-approved permissions')
    p_sus.set_defaults(func=cmd_detect_suspicious)

    # detect-missing-project-step-permissions subcommand
    p_missing = subparsers.add_parser(
        'detect-missing-project-step-permissions',
        help='Detect project:{skill} steps in marshal.json without matching Skill() allow rules',
        allow_abbrev=False,
    )
    p_missing.add_argument('--marshal', required=True, help='Path to marshal.json')
    p_missing_group = p_missing.add_mutually_exclusive_group(required=True)
    p_missing_group.add_argument('--settings', help='Path to settings file to check')
    p_missing_group.add_argument('--scope', choices=['global', 'project'], help='Target scope (auto-resolves path)')
    p_missing.set_defaults(func=cmd_detect_missing_project_step_permissions)

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
