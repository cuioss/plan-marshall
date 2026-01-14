#!/usr/bin/env python3
"""Marketplace sync - permission synchronization for Claude Code marketplace.

Provides:
- generate-wildcards: Generate permission wildcards from marketplace inventory
- ensure-executor: Ensure the executor permission exists
- cleanup-scripts: Remove redundant individual script permissions
- migrate-executor: Full migration to executor-only permission pattern
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1

# Executor-only permission pattern
EXECUTOR_PERMISSION = "Bash(python3 .plan/execute-script.py *)"
OVERLY_BROAD_PYTHON = "Bash(python3:*)"


# =============================================================================
# Shared Utilities
# =============================================================================

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
# generate-wildcards subcommand
# =============================================================================

def extract_command_prefix(command_name: str) -> str:
    """Extract the prefix from a command name."""
    parts = command_name.split("-")
    if len(parts) > 1:
        return parts[0]
    return command_name


def extract_skill_prefix(skill_name: str) -> str:
    """Extract the prefix from a skill name."""
    parts = skill_name.split("-")
    if len(parts) > 1:
        return parts[0]
    return skill_name


def generate_skill_wildcards(bundles: list[dict]) -> list[str]:
    """Generate Skill wildcards for bundles with skills."""
    wildcards = []
    for bundle in bundles:
        if bundle.get("skills") and len(bundle["skills"]) > 0:
            wildcards.append(f"Skill({bundle['name']}:*)")
    return sorted(wildcards)


def generate_command_bundle_wildcards(bundles: list[dict]) -> list[str]:
    """Generate SlashCommand wildcards for bundles with commands."""
    wildcards = []
    for bundle in bundles:
        if bundle.get("commands") and len(bundle["commands"]) > 0:
            wildcards.append(f"SlashCommand(/{bundle['name']}:*)")
    return sorted(wildcards)


def generate_command_shortform_permissions(bundles: list[dict]) -> list[str]:
    """Generate SlashCommand permissions for each command."""
    permissions = []
    for bundle in bundles:
        for command in bundle.get("commands", []):
            permissions.append(f"SlashCommand(/{command['name']}:*)")
    return sorted(permissions)


def count_scripts(bundles: list[dict]) -> int:
    """Count total scripts in bundles."""
    total = 0
    for bundle in bundles:
        total += len(bundle.get("scripts", []))
    return total


def analyze_naming_patterns(bundles: list[dict]) -> dict[str, Any]:
    """Analyze naming patterns in skills and commands."""
    skill_prefixes = set()
    command_prefixes = set()
    bundle_names = []

    for bundle in bundles:
        bundle_names.append(bundle["name"])
        for skill in bundle.get("skills", []):
            prefix = extract_skill_prefix(skill["name"])
            skill_prefixes.add(prefix)
        for command in bundle.get("commands", []):
            prefix = extract_command_prefix(command["name"])
            command_prefixes.add(prefix)

    return {
        "bundle_names": sorted(bundle_names),
        "skill_prefixes": sorted(skill_prefixes),
        "command_prefixes": sorted(command_prefixes)
    }


def build_bundle_summary(bundles: list[dict]) -> list[dict]:
    """Build summary of each bundle's contents."""
    summaries = []
    for bundle in bundles:
        summaries.append({
            "name": bundle["name"],
            "skills": {
                "count": len(bundle.get("skills", [])),
                "names": [s["name"] for s in bundle.get("skills", [])]
            },
            "commands": {
                "count": len(bundle.get("commands", [])),
                "names": [c["name"] for c in bundle.get("commands", [])]
            },
            "scripts": {
                "count": len(bundle.get("scripts", [])),
                "names": [s["name"] for s in bundle.get("scripts", [])]
            }
        })
    return summaries


def cmd_generate_wildcards(args) -> int:
    """Handle generate-wildcards subcommand."""
    try:
        if args.input:
            with open(args.input) as f:
                inventory = json.load(f)
        else:
            inventory = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        return EXIT_ERROR
    except FileNotFoundError:
        print(json.dumps({"error": f"Input file not found: {args.input}"}))
        return EXIT_ERROR

    bundles = inventory.get("bundles", [])

    if not bundles:
        result: dict[str, Any] = {
            "error": "No bundles found in inventory",
            "statistics": {
                "bundles_scanned": 0,
                "skills_found": 0,
                "commands_found": 0,
                "scripts_found": 0,
                "wildcards_generated": 0
            }
        }
        print(json.dumps(result, indent=2))
        return EXIT_SUCCESS

    skill_wildcards = generate_skill_wildcards(bundles)
    command_bundle_wildcards = generate_command_bundle_wildcards(bundles)
    command_shortform = generate_command_shortform_permissions(bundles)

    stats = inventory.get("statistics", {})
    total_scripts = count_scripts(bundles)
    wildcards_generated = len(skill_wildcards) + len(command_bundle_wildcards) + len(command_shortform)
    patterns = analyze_naming_patterns(bundles)
    bundle_summary = build_bundle_summary(bundles)

    result = {
        "statistics": {
            "bundles_scanned": stats.get("total_bundles", len(bundles)),
            "skills_found": stats.get("total_skills", 0),
            "commands_found": stats.get("total_commands", 0),
            "scripts_found": total_scripts,
            "wildcards_generated": wildcards_generated,
            "breakdown": {
                "skill_bundle_wildcards": len(skill_wildcards),
                "command_bundle_wildcards": len(command_bundle_wildcards),
                "command_shortform_permissions": len(command_shortform)
            }
        },
        "naming_patterns": patterns,
        "bundle_summary": bundle_summary,
        "permissions": {
            "skill_wildcards": skill_wildcards,
            "command_bundle_wildcards": command_bundle_wildcards,
            "command_shortform": command_shortform
        },
        "coverage": {
            "skills_covered": f"{stats.get('total_skills', 0)} skills covered by {len(skill_wildcards)} bundle wildcards",
            "commands_covered": f"{stats.get('total_commands', 0)} commands covered by {len(command_bundle_wildcards)} bundle wildcards + {len(command_shortform)} short-form permissions",
            "scripts_note": f"{total_scripts} scripts - handled by relative path architecture (no permissions needed)"
        }
    }
    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# ensure-executor subcommand
# =============================================================================

def cmd_ensure_executor(args) -> int:
    """Handle ensure-executor subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    result = {
        "executor_permission": EXECUTOR_PERMISSION,
        "settings_file": str(settings_path),
        "dry_run": args.dry_run
    }

    if EXECUTOR_PERMISSION in allow_list:
        result["action"] = "already_exists"
        result["success"] = True
        print(json.dumps(result, indent=2))
        return EXIT_SUCCESS

    if not args.dry_run:
        allow_list.append(EXECUTOR_PERMISSION)
        allow_list.sort()
        if save_settings(str(settings_path), settings):
            result["action"] = "added"
            result["success"] = True
        else:
            result["error"] = "Failed to save settings"
            result["success"] = False
    else:
        result["action"] = "would_add"
        result["success"] = True

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


# =============================================================================
# cleanup-scripts subcommand
# =============================================================================

def is_individual_script_permission(permission: str) -> bool:
    """Check if permission is an individual marketplace script path permission."""
    return (
        permission.startswith("Bash(python3 ") and
        "/marketplace/bundles/" in permission and
        "/scripts" in permission
    )


def cmd_cleanup_scripts(args) -> int:
    """Handle cleanup-scripts subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    # Find permissions to remove
    individual_scripts = [p for p in allow_list if is_individual_script_permission(p)]
    broad_python = OVERLY_BROAD_PYTHON in allow_list and args.remove_broad_python

    result = {
        "settings_file": str(settings_path),
        "individual_script_permissions": individual_scripts,
        "individual_count": len(individual_scripts),
        "broad_python_found": OVERLY_BROAD_PYTHON in allow_list,
        "broad_python_removed": broad_python,
        "dry_run": args.dry_run
    }

    if not individual_scripts and not broad_python:
        result["action"] = "nothing_to_remove"
        result["success"] = True
        print(json.dumps(result, indent=2))
        return EXIT_SUCCESS

    if not args.dry_run:
        # Remove individual script permissions
        for perm in individual_scripts:
            allow_list.remove(perm)

        # Optionally remove overly broad python permission
        if broad_python:
            allow_list.remove(OVERLY_BROAD_PYTHON)

        if save_settings(str(settings_path), settings):
            result["action"] = "removed"
            result["success"] = True
            result["total_removed"] = len(individual_scripts) + (1 if broad_python else 0)
        else:
            result["error"] = "Failed to save settings"
            result["success"] = False
    else:
        result["action"] = "would_remove"
        result["success"] = True
        result["total_would_remove"] = len(individual_scripts) + (1 if broad_python else 0)

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


# =============================================================================
# migrate-executor subcommand
# =============================================================================

def cmd_migrate_executor(args) -> int:
    """Handle migrate-executor subcommand."""
    settings_path = get_settings_path(args.target)
    settings = load_settings_path(settings_path)
    allow_list = settings["permissions"]["allow"]

    # Step 1: Check/add executor permission
    executor_action = "already_exists"
    if EXECUTOR_PERMISSION not in allow_list:
        if not args.dry_run:
            allow_list.append(EXECUTOR_PERMISSION)
            executor_action = "added"
        else:
            executor_action = "would_add"

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
            print(json.dumps({"error": "Failed to save settings", "success": False}))
            return EXIT_ERROR

    result = {
        "success": True,
        "settings_file": str(settings_path),
        "dry_run": args.dry_run,
        "executor": {
            "permission": EXECUTOR_PERMISSION,
            "action": executor_action
        },
        "cleanup": {
            "individual_removed": total_to_remove if not args.dry_run else 0,
            "individual_would_remove": total_to_remove if args.dry_run else 0,
            "individual_permissions": individual_scripts,
            "broad_python_removed": broad_python
        },
        "summary": f"Migrated to executor-only pattern: 1 permission replaces {len(individual_scripts)} individual script permissions"
    }

    print(json.dumps(result, indent=2))
    return EXIT_SUCCESS


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Marketplace sync - permission synchronization for Claude Code marketplace'
    )
    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # generate-wildcards subcommand
    p_gen = subparsers.add_parser('generate-wildcards', help='Generate permission wildcards from marketplace inventory')
    p_gen.add_argument('--input', '-i', help='Input JSON file (default: stdin)')
    p_gen.set_defaults(func=cmd_generate_wildcards)

    # ensure-executor subcommand
    p_exe = subparsers.add_parser('ensure-executor', help='Ensure the executor permission exists')
    p_exe.add_argument('--target', default='global', choices=['global', 'project'],
                       help='Target settings file (default: global)')
    p_exe.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_exe.set_defaults(func=cmd_ensure_executor)

    # cleanup-scripts subcommand
    p_cln = subparsers.add_parser('cleanup-scripts', help='Remove redundant individual script permissions')
    p_cln.add_argument('--target', default='global', choices=['global', 'project'],
                       help='Target settings file (default: global)')
    p_cln.add_argument('--remove-broad-python', action='store_true',
                       help='Also remove Bash(python3:*) wildcard')
    p_cln.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_cln.set_defaults(func=cmd_cleanup_scripts)

    # migrate-executor subcommand
    p_mig = subparsers.add_parser('migrate-executor', help='Full migration to executor-only permission pattern')
    p_mig.add_argument('--target', default='global', choices=['global', 'project'],
                       help='Target settings file (default: global)')
    p_mig.add_argument('--remove-broad-python', action='store_true',
                       help='Also remove Bash(python3:*) wildcard')
    p_mig.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    p_mig.set_defaults(func=cmd_migrate_executor)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return EXIT_ERROR

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
