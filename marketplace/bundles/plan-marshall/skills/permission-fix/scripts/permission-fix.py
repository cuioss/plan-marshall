#!/usr/bin/env python3
"""Permission fix - write operations for Claude Code settings.

Provides:
- apply-fixes: Apply safe fixes (normalize, dedupe, sort, defaults)
- add: Add a permission to settings
- remove: Remove a permission from settings
- ensure: Ensure multiple permissions exist
- consolidate: Consolidate timestamped permissions with wildcards
- ensure-wildcards: Ensure marketplace wildcards exist
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1

# Default permissions for plan directory and plugin cache
DEFAULT_PERMISSIONS = [
    "Edit(.plan/**)",
    "Write(.plan/**)",
    "Read(~/.claude/plugins/cache/**)",  # Skills reference files via relative paths
]

# Timestamp patterns for consolidation
TIMESTAMP_PATTERN = re.compile(r'^(\w+)\((.*/)?(.+)-(\d{4}-\d{2}-\d{2}-\d{6})\.(\w+)\)$')
DATE_PATTERN = re.compile(r'^(\w+)\((.*/)?(.+)-(\d{4}-\d{2}-\d{2})\.(\w+)\)$')


# =============================================================================
# Shared Utilities
# =============================================================================

def load_settings(path: str) -> tuple[dict, str | None]:
    """Load settings from a JSON file."""
    settings_path = Path(path)

    if not settings_path.exists():
        return {}, f"Settings file not found: {path}"

    try:
        with open(settings_path) as f:
            data = json.load(f)

        if "permissions" not in data:
            data["permissions"] = {}
        for key in ["allow", "deny", "ask"]:
            if key not in data["permissions"]:
                data["permissions"][key] = []

        return data, None
    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON in {path}: {e}"


def save_settings(path: str, settings: dict) -> bool:
    """Save settings to a JSON file."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def get_global_settings_path() -> Path:
    """Get path to global settings file."""
    return Path.home() / ".claude" / "settings.json"


def get_project_settings_path_for_write(project_dir: Path | None = None) -> Path:
    """Get path for writing project settings."""
    if project_dir is None:
        project_dir = Path.cwd()

    settings_json = project_dir / ".claude" / "settings.json"
    if settings_json.exists():
        return settings_json

    return project_dir / ".claude" / "settings.local.json"


def load_settings_path(path: Path) -> dict[str, Any]:
    """Load settings from a Path."""
    if not path.exists():
        return {"permissions": {"allow": [], "deny": [], "ask": []}}

    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
        if "permissions" not in data:
            data["permissions"] = {}
        for key in ["allow", "deny", "ask"]:
            if key not in data["permissions"]:
                data["permissions"][key] = []
        return data
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "permissions": {"allow": [], "deny": [], "ask": []}}


def get_settings_path(target: str) -> Path:
    """Get settings path based on target."""
    if target == "global":
        return get_global_settings_path()
    return get_project_settings_path_for_write()


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
        return f"{perm_type}({path})", True

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


def cmd_apply_fixes(args) -> int:
    """Handle apply-fixes subcommand."""
    settings_path = resolve_settings_arg(args)
    settings, error = load_settings(settings_path)
    if error:
        print(json.dumps({"error": error}))
        return EXIT_ERROR

    total_duplicates = 0
    total_paths_fixed = 0
    was_sorted = False

    for key in ["allow", "deny", "ask"]:
        perm_list = settings.get("permissions", {}).get(key, [])
        processed, paths_fixed, dups, sorted_flag = process_permission_list(perm_list)

        settings["permissions"][key] = processed
        total_paths_fixed += paths_fixed
        total_duplicates += dups
        was_sorted = was_sorted or sorted_flag

    defaults_added = []
    allow_list = settings["permissions"]["allow"]
    defaults_added = add_default_permissions(allow_list)
    if defaults_added:
        settings["permissions"]["allow"] = sorted(allow_list)
        was_sorted = True

    changes_made = total_duplicates > 0 or total_paths_fixed > 0 or len(defaults_added) > 0 or was_sorted

    result = {
        "duplicates_removed": total_duplicates,
        "paths_fixed": total_paths_fixed,
        "defaults_added": defaults_added,
        "sorted": was_sorted,
        "changes_made": changes_made,
        "dry_run": args.dry_run,
        "settings_path": settings_path
    }

    if not args.dry_run and changes_made:
        result["applied"] = save_settings(settings_path, settings)
        if not result["applied"]:
            result["error"] = "Failed to save settings"
    else:
        result["applied"] = False

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# add subcommand
# =============================================================================

def cmd_add(args) -> int:
    """Handle add subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    result: dict[str, Any] = {"settings_file": str(settings_path)}

    if args.permission in allow_list:
        result["success"] = True
        result["action"] = "already_exists"
        print(json.dumps(result, indent=2))
        return EXIT_SUCCESS

    allow_list.append(args.permission)
    allow_list.sort()

    if save_settings(str(settings_path), settings):
        result["success"] = True
        result["action"] = "added"
    else:
        result["success"] = False
        result["error"] = "Failed to save settings"

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


# =============================================================================
# remove subcommand
# =============================================================================

def cmd_remove(args) -> int:
    """Handle remove subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    result: dict[str, Any] = {"settings_file": str(settings_path)}

    if args.permission not in allow_list:
        result["success"] = True
        result["action"] = "not_found"
        print(json.dumps(result, indent=2))
        return EXIT_SUCCESS

    allow_list.remove(args.permission)

    if save_settings(str(settings_path), settings):
        result["success"] = True
        result["action"] = "removed"
    else:
        result["success"] = False
        result["error"] = "Failed to save settings"

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


# =============================================================================
# ensure subcommand
# =============================================================================

def cmd_ensure(args) -> int:
    """Handle ensure subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    permissions = [p.strip() for p in args.permissions.split(",")]

    added = []
    already_exists = []

    for perm in permissions:
        if perm in allow_list:
            already_exists.append(perm)
        else:
            allow_list.append(perm)
            added.append(perm)

    result = {
        "settings_file": str(settings_path),
        "added": added,
        "already_exists": already_exists,
        "added_count": len(added),
        "total_permissions": len(allow_list)
    }

    if added:
        allow_list.sort()
        if save_settings(str(settings_path), settings):
            result["success"] = True
        else:
            result["success"] = False
            result["error"] = "Failed to save settings"
    else:
        result["success"] = True

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


# =============================================================================
# consolidate subcommand
# =============================================================================

def parse_timestamped_permission(permission: str) -> dict | None:
    """Parse a permission to check if it contains a timestamp pattern."""
    match = TIMESTAMP_PATTERN.match(permission)
    if match:
        perm_type, path_prefix, base_name, timestamp, extension = match.groups()
        return {
            "permission": permission,
            "type": perm_type,
            "path_prefix": path_prefix or "",
            "base_name": base_name,
            "timestamp": timestamp,
            "extension": extension
        }

    match = DATE_PATTERN.match(permission)
    if match:
        perm_type, path_prefix, base_name, timestamp, extension = match.groups()
        return {
            "permission": permission,
            "type": perm_type,
            "path_prefix": path_prefix or "",
            "base_name": base_name,
            "timestamp": timestamp,
            "extension": extension
        }

    return None


def generate_wildcard(parsed_permissions: list[dict]) -> str:
    """Generate a wildcard pattern from a list of parsed timestamped permissions."""
    if not parsed_permissions:
        return ""

    first = parsed_permissions[0]
    perm_type = first["type"]
    base_name = first["base_name"]
    extension = first["extension"]
    path_prefixes = set(p["path_prefix"] for p in parsed_permissions)

    if len(path_prefixes) == 1:
        path_prefix = first["path_prefix"]
        return f"{perm_type}({path_prefix}{base_name}-*.{extension})"

    return f"{perm_type}(**/{base_name}-*.{extension})"


def cmd_consolidate(args) -> int:
    """Handle consolidate subcommand."""
    settings_path = resolve_settings_arg(args)
    settings, error = load_settings(settings_path)
    if error:
        print(json.dumps({"error": error}))
        return EXIT_ERROR

    allow_list = settings.get("permissions", {}).get("allow", [])
    timestamped_groups = defaultdict(list)
    non_timestamped = []

    for permission in allow_list:
        parsed = parse_timestamped_permission(permission)
        if parsed:
            key = (parsed["type"], parsed["base_name"], parsed["extension"])
            timestamped_groups[key].append(parsed)
        else:
            non_timestamped.append(permission)

    wildcards_to_add = []
    permissions_to_remove = []

    for key, group in timestamped_groups.items():
        if len(group) >= 1:
            wildcard = generate_wildcard(group)
            wildcards_to_add.append(wildcard)
            permissions_to_remove.extend([p["permission"] for p in group])

    result = {
        "consolidated": len(permissions_to_remove),
        "removed": permissions_to_remove,
        "wildcards_added": wildcards_to_add,
        "changes": {
            "timestamped_groups_found": len(timestamped_groups),
            "non_timestamped_kept": len(non_timestamped)
        },
        "dry_run": args.dry_run,
        "settings_path": settings_path
    }

    if not args.dry_run and result["consolidated"] > 0:
        for perm in permissions_to_remove:
            if perm in allow_list:
                allow_list.remove(perm)
        for wildcard in wildcards_to_add:
            if wildcard not in allow_list:
                allow_list.append(wildcard)
        allow_list.sort()

        if save_settings(settings_path, settings):
            result["applied"] = True
        else:
            result["error"] = "Failed to save settings"
            result["applied"] = False
    else:
        result["applied"] = False

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# ensure-wildcards subcommand
# =============================================================================

def has_skills(bundle: dict) -> bool:
    """Check if a bundle has skills defined.

    Returns True if:
    - 'skills' key exists and is a non-empty list, OR
    - Neither 'skills' nor 'commands' keys exist (assume bundle has both)
    """
    skills = bundle.get("skills")
    commands = bundle.get("commands")

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
    skills = bundle.get("skills")
    commands = bundle.get("commands")

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

    Supports both 'bundles' key (from scan-marketplace-inventory output)
    and 'plugins' key (from marketplace.json format).

    For real marketplace.json format (no skills/commands arrays),
    assumes all bundles have both skills and commands.
    """
    wildcards = []
    # Support both 'bundles' (inventory output) and 'plugins' (marketplace.json)
    bundles = marketplace.get("bundles", marketplace.get("plugins", []))

    for bundle in bundles:
        bundle_name = bundle.get("name", "")
        if not bundle_name:
            continue

        if has_skills(bundle):
            wildcards.append(f"Skill({bundle_name}:*)")
        if has_commands(bundle):
            wildcards.append(f"SlashCommand(/{bundle_name}:*)")

    return wildcards


def cmd_ensure_wildcards(args) -> int:
    """Handle ensure-wildcards subcommand."""
    settings, error = load_settings(args.settings)
    if error:
        print(json.dumps({"error": error}))
        return EXIT_ERROR

    marketplace_path = Path(args.marketplace_json)
    if not marketplace_path.exists():
        print(json.dumps({"error": f"Marketplace file not found: {args.marketplace_json}"}))
        return EXIT_ERROR

    try:
        with open(marketplace_path) as f:
            marketplace = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON in {args.marketplace_json}: {e}"}))
        return EXIT_ERROR

    allow_list = settings.get("permissions", {}).get("allow", [])
    allow_set = set(allow_list)
    required_wildcards = generate_required_wildcards(marketplace)

    added = []
    already_present = 0

    for wildcard in required_wildcards:
        if wildcard in allow_set:
            already_present += 1
        else:
            added.append(wildcard)

    # Count bundles from either 'bundles' or 'plugins' key
    bundles = marketplace.get("bundles", marketplace.get("plugins", []))

    result = {
        "added": added,
        "already_present": already_present,
        "total": len(required_wildcards),
        "bundles_analyzed": len(bundles),
        "dry_run": args.dry_run,
        "settings_path": args.settings,
        "marketplace_path": args.marketplace_json
    }

    if not args.dry_run and len(added) > 0:
        for wildcard in added:
            if wildcard not in allow_list:
                allow_list.append(wildcard)
        allow_list.sort()

        if save_settings(args.settings, settings):
            result["applied"] = True
        else:
            result["error"] = "Failed to save settings"
            result["applied"] = False
    else:
        result["applied"] = False

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Permission fix - write operations for Claude Code settings'
    )
    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

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
    p_add.add_argument('--target', default='project', choices=['global', 'project'],
                       help='Target settings file (default: project)')
    p_add.set_defaults(func=cmd_add)

    # remove subcommand
    p_rem = subparsers.add_parser('remove', help='Remove a permission from settings')
    p_rem.add_argument('--permission', required=True, help='Permission to remove')
    p_rem.add_argument('--target', default='project', choices=['global', 'project'],
                       help='Target settings file (default: project)')
    p_rem.set_defaults(func=cmd_remove)

    # ensure subcommand
    p_ens = subparsers.add_parser('ensure', help='Ensure multiple permissions exist')
    p_ens.add_argument('--permissions', required=True, help='Comma-separated permissions to ensure')
    p_ens.add_argument('--target', default='global', choices=['global', 'project'],
                       help='Target settings file (default: global)')
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return EXIT_ERROR

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
