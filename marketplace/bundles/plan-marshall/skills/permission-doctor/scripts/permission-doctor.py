#!/usr/bin/env python3
"""Permission doctor - read-only analysis for Claude Code settings.

Provides:
- detect-redundant: Detect redundant permissions between global and local settings
- detect-suspicious: Detect suspicious permissions matching anti-patterns
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1


# =============================================================================
# Shared Utilities
# =============================================================================

def load_settings(path: str) -> tuple[dict, Optional[str]]:
    """Load settings from a JSON file."""
    settings_path = Path(path)

    if not settings_path.exists():
        return {}, f"Settings file not found: {path}"

    try:
        with open(settings_path, 'r') as f:
            data = json.load(f)

        if "permissions" not in data:
            data["permissions"] = {}
        for key in ["allow", "deny", "ask"]:
            if key not in data["permissions"]:
                data["permissions"][key] = []

        return data, None
    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON in {path}: {e}"


def output_result(result: dict, format_type: str = "json") -> None:
    """Output result in specified format."""
    if format_type == "json":
        print(json.dumps(result, indent=2))


def get_global_settings_path() -> Path:
    """Get path to global settings file."""
    return Path.home() / ".claude" / "settings.json"


def get_project_settings_path() -> Path:
    """Get path to project settings file (prefers settings.local.json if exists)."""
    project_dir = Path.cwd()
    settings_local = project_dir / ".claude" / "settings.local.json"
    if settings_local.exists():
        return settings_local
    return project_dir / ".claude" / "settings.json"


def resolve_scope_to_paths(scope: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve scope to global and local settings paths.

    Returns:
        Tuple of (global_path, local_path). For 'global' or 'project' scope,
        one will be None. For 'both', both paths are returned.
    """
    if scope == "global":
        return str(get_global_settings_path()), None
    elif scope == "project":
        return None, str(get_project_settings_path())
    elif scope == "both":
        return str(get_global_settings_path()), str(get_project_settings_path())
    return None, None


# =============================================================================
# detect-redundant subcommand
# =============================================================================

def is_marketplace_permission(permission: str, project_root: Optional[Path] = None) -> bool:
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
    if permission.startswith("Skill("):
        return True

    # SlashCommand permissions need special handling
    if permission.startswith("SlashCommand(/"):
        # Extract command name from SlashCommand(/command-name)
        match = re.match(r'^SlashCommand\(/([^)]+)\)$', permission)
        if match:
            command_name = match.group(1)
            # Check if this is a project-local command
            root = project_root or Path.cwd()
            local_command_path = root / ".claude" / "commands" / f"{command_name}.md"
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
    return permission, ""


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


def cmd_detect_redundant(args) -> int:
    """Handle detect-redundant subcommand."""
    # Resolve paths from --scope or explicit args
    if args.scope:
        global_path, local_path = resolve_scope_to_paths(args.scope)
    else:
        global_path = args.global_settings
        local_path = args.local_settings

    global_settings, global_error = load_settings(global_path)
    if global_error:
        print(json.dumps({"error": global_error, "global_exists": False}))
        return EXIT_ERROR

    local_settings, local_error = load_settings(local_path)
    if local_error:
        print(json.dumps({"error": local_error, "local_exists": False}))
        return EXIT_ERROR

    global_allow = set(global_settings.get("permissions", {}).get("allow", []))
    local_allow = local_settings.get("permissions", {}).get("allow", [])

    # Derive project root from local settings path for command detection
    project_root = Path(local_path).parent.parent if local_path else None

    redundant = []
    marketplace_in_local = []

    for local_perm in local_allow:
        if local_perm in global_allow:
            redundant.append({
                "permission": local_perm,
                "reason": "Exact duplicate exists in global settings",
                "type": "exact_duplicate",
                "covered_by": local_perm
            })
            continue

        if is_marketplace_permission(local_perm, project_root):
            marketplace_in_local.append({
                "permission": local_perm,
                "reason": "Marketplace permissions should be in global settings",
                "type": "marketplace_permission"
            })
            continue

        for global_perm in global_allow:
            if is_covered_by_wildcard(local_perm, global_perm):
                redundant.append({
                    "permission": local_perm,
                    "reason": "Covered by broader wildcard in global settings",
                    "type": "covered_by_wildcard",
                    "covered_by": global_perm
                })
                break

    result = {
        "redundant": redundant,
        "marketplace_in_local": marketplace_in_local,
        "summary": {
            "redundant_count": len(redundant),
            "marketplace_in_local_count": len(marketplace_in_local),
            "total_issues": len(redundant) + len(marketplace_in_local),
            "local_permissions_checked": len(local_allow),
            "global_permissions_count": len(global_allow)
        },
        "global_exists": True,
        "local_exists": True,
        "global_path": global_path,
        "local_path": local_path
    }
    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# detect-suspicious subcommand
# =============================================================================

SUSPICIOUS_PATTERNS = [
    {"pattern": r"^Write\(\/\*\*\)$", "reason": "Root write access", "severity": "high", "category": "root_access"},
    {"pattern": r"^Read\(\/\*\*\)$", "reason": "Root read access", "severity": "high", "category": "root_access"},
    {"pattern": r"^Write\(\/etc\/.*\)$", "reason": "System configuration write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Write\(\/dev\/.*\)$", "reason": "Device file write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Write\(\/sys\/.*\)$", "reason": "System kernel interface write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Write\(\/proc\/.*\)$", "reason": "Process information write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Write\(\/boot\/.*\)$", "reason": "Boot files write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Write\(\/root\/.*\)$", "reason": "Root user home directory write access", "severity": "high", "category": "system_directory"},
    {"pattern": r"^Bash\(sudo:.*\)$", "reason": "Privilege escalation - sudo access", "severity": "high", "category": "dangerous_command"},
    {"pattern": r"^Bash\(rm:-rf.*\)$", "reason": "Recursive force delete", "severity": "high", "category": "dangerous_command"},
    {"pattern": r"^Bash\(dd:.*\)$", "reason": "Low-level disk operations", "severity": "high", "category": "dangerous_command"},
    {"pattern": r"^Bash\(mkfs:.*\)$", "reason": "Filesystem creation", "severity": "high", "category": "dangerous_command"},
    {"pattern": r"^Bash\(fdisk:.*\)$", "reason": "Disk partitioning", "severity": "high", "category": "dangerous_command"},
    {"pattern": r".*\|\s*bash.*", "reason": "Piping to bash", "severity": "high", "category": "dangerous_command"},
    {"pattern": r".*\|\s*sh.*", "reason": "Piping to sh", "severity": "high", "category": "dangerous_command"},
    {"pattern": r"^Write\(\/tmp\/.*\)$", "reason": "System temp directory write access", "severity": "medium", "category": "temp_directory"},
    {"pattern": r"^Write\(\/var\/tmp\/.*\)$", "reason": "Persistent temp directory write access", "severity": "medium", "category": "temp_directory"},
    {"pattern": r"^Write\(\/private\/tmp\/.*\)$", "reason": "macOS private temp directory write access", "severity": "medium", "category": "temp_directory"},
    {"pattern": r"^Read\(\/\/Users\/\*\*\)$", "reason": "All users read access", "severity": "medium", "category": "broad_access"},
    {"pattern": r"^Write\(\/\/Users\/\*\*\)$", "reason": "All users write access", "severity": "high", "category": "broad_access"},
    {"pattern": r"^Read\(\/\/home\/\*\*\)$", "reason": "All home directories read access", "severity": "medium", "category": "broad_access"},
    {"pattern": r"^Write\(\/\/home\/\*\*\)$", "reason": "All home directories write access", "severity": "high", "category": "broad_access"},
    {"pattern": r"^Bash\(curl:\*\)$", "reason": "Unrestricted curl access", "severity": "low", "category": "network_access"},
    {"pattern": r"^Bash\(wget:\*\)$", "reason": "Unrestricted wget access", "severity": "low", "category": "network_access"},
]


def load_approved_permissions(approved_file: Optional[str]) -> set[str]:
    """Load user-approved permissions from run-configuration file."""
    if not approved_file:
        return set()

    approved_path = Path(approved_file)
    if not approved_path.exists():
        return set()

    try:
        with open(approved_path, 'r') as f:
            data = json.load(f)
        commands = data.get("commands", {})
        setup_perms = commands.get("setup-project-permissions", {})
        approved_list = setup_perms.get("user_approved_permissions", [])
        return set(approved_list)
    except (json.JSONDecodeError, KeyError):
        return set()


def check_permission(permission: str) -> Optional[dict]:
    """Check if a permission matches any suspicious pattern."""
    for pattern_info in SUSPICIOUS_PATTERNS:
        if re.match(pattern_info["pattern"], permission, re.IGNORECASE):
            return {
                "permission": permission,
                "reason": pattern_info["reason"],
                "severity": pattern_info["severity"],
                "category": pattern_info["category"]
            }
    return None


def cmd_detect_suspicious(args) -> int:
    """Handle detect-suspicious subcommand."""
    # Resolve path from --scope or explicit --settings
    if args.scope:
        if args.scope == "global":
            settings_path = str(get_global_settings_path())
        else:  # project
            settings_path = str(get_project_settings_path())
    else:
        settings_path = args.settings

    settings, error = load_settings(settings_path)
    if error:
        print(json.dumps({"error": error}))
        return EXIT_ERROR

    approved_permissions = load_approved_permissions(args.approved_file)
    allow_list = settings.get("permissions", {}).get("allow", [])

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

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for item in suspicious:
        severity_counts[item["severity"]] += 1

    result = {
        "suspicious": suspicious,
        "already_approved": already_approved,
        "summary": {
            "total_suspicious": len(suspicious),
            "already_approved_count": len(already_approved),
            "by_severity": severity_counts,
            "permissions_checked": len(allow_list)
        },
        "settings_path": settings_path
    }
    if args.approved_file:
        result["approved_file"] = args.approved_file

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Permission doctor - read-only analysis for Claude Code settings'
    )
    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # detect-redundant subcommand
    p_red = subparsers.add_parser('detect-redundant', help='Detect redundant permissions between global and local settings')
    p_red_group = p_red.add_mutually_exclusive_group(required=True)
    p_red_group.add_argument('--scope', choices=['both'], help='Analyze both global and project settings (auto-resolves paths)')
    p_red_group.add_argument('--global-settings', help='Path to global settings file (requires --local-settings)')
    p_red.add_argument('--local-settings', help='Path to local/project settings file (required with --global-settings)')
    p_red.set_defaults(func=cmd_detect_redundant)

    # detect-suspicious subcommand
    p_sus = subparsers.add_parser('detect-suspicious', help='Detect suspicious permissions matching anti-patterns')
    p_sus_group = p_sus.add_mutually_exclusive_group(required=True)
    p_sus_group.add_argument('--settings', help='Path to settings file to analyze')
    p_sus_group.add_argument('--scope', choices=['global', 'project'], help='Target scope (auto-resolves path)')
    p_sus.add_argument('--approved-file', help='Path to run-configuration file with user-approved permissions')
    p_sus.set_defaults(func=cmd_detect_suspicious)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return EXIT_ERROR

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
