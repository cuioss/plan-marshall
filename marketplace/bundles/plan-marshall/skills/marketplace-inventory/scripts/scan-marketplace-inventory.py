#!/usr/bin/env python3
"""
scan-marketplace-inventory.py

Scans marketplace directories and returns structured inventory of bundles,
agents, commands, skills, and scripts.

Usage:
    python3 scan-marketplace-inventory.py [options]

Options:
    --scope <value>          Directory scope: auto (default), marketplace, plugin-cache, global, project
                             'auto' tries marketplace/bundles first, then falls back to plugin-cache
    --resource-types <types> Resource types: agents, commands, skills, scripts, or comma-separated (default: all)
    --include-descriptions   Extract descriptions from YAML frontmatter
    --name-pattern <pattern> Filter resources by name pattern (fnmatch glob, pipe-separated for multiple)
    --bundles <names>        Filter to specific bundles (comma-separated)

Script Output:
    Scripts include a 'notation' field in {bundle}:{skill}:{script} format for use with
    the script executor (e.g., "pm-workflow:manage-files:manage-files").

Exit codes:
    0 - Success (JSON output)
    1 - Error (invalid parameters, missing directory)
"""

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

# Constants
MARKETPLACE_BUNDLES_PATH = "marketplace/bundles"
CLAUDE_DIR = ".claude"
PLUGIN_CACHE_SUBPATH = "plugins/cache/plan-marshall"


def safe_relative_path(path: Path) -> str:
    """Return path relative to cwd if possible, otherwise absolute path."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        # Path is not under cwd, return absolute
        return str(path)


def find_bundles(base_path: Path) -> list[Path]:
    """Find all bundle directories by locating plugin.json files."""
    bundles = []
    for plugin_json in base_path.rglob(".claude-plugin/plugin.json"):
        # Bundle is two levels up from plugin.json
        bundle_dir = plugin_json.parent.parent
        if bundle_dir not in bundles:
            bundles.append(bundle_dir)
    return sorted(bundles)


def extract_description(file_path: Path) -> str | None:
    """Extract description from YAML frontmatter."""
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return None

    # Check for YAML frontmatter
    if not content.startswith("---"):
        return None

    # Extract frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)

    # Extract description field
    for line in frontmatter.split('\n'):
        if line.startswith('description:'):
            desc = line[len('description:'):].strip()
            return desc if desc else None

    return None


def discover_agents(bundle_dir: Path, include_descriptions: bool) -> list[dict]:
    """Discover agent .md files in bundle/agents/."""
    agents_dir = bundle_dir / "agents"
    if not agents_dir.is_dir():
        return []

    agents = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        if agent_file.is_file():
            agent: dict[str, Any] = {
                "name": agent_file.stem,
                "path": safe_relative_path(agent_file)
            }
            if include_descriptions:
                agent["description"] = extract_description(agent_file)
            agents.append(agent)
    return agents


def discover_commands(bundle_dir: Path, include_descriptions: bool) -> list[dict]:
    """Discover command .md files in bundle/commands/."""
    commands_dir = bundle_dir / "commands"
    if not commands_dir.is_dir():
        return []

    commands = []
    for command_file in sorted(commands_dir.glob("*.md")):
        if command_file.is_file():
            command: dict[str, Any] = {
                "name": command_file.stem,
                "path": safe_relative_path(command_file)
            }
            if include_descriptions:
                command["description"] = extract_description(command_file)
            commands.append(command)
    return commands


def discover_skills(bundle_dir: Path, include_descriptions: bool) -> list[dict]:
    """Discover skill directories containing SKILL.md."""
    skills_dir = bundle_dir / "skills"
    if not skills_dir.is_dir():
        return []

    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        skill: dict[str, Any] = {
            "name": skill_dir.name,
            "path": safe_relative_path(skill_dir)
        }
        if include_descriptions:
            skill["description"] = extract_description(skill_md)
        skills.append(skill)
    return skills


def discover_scripts(bundle_dir: Path, bundle_name: str) -> list[dict]:
    """Discover script files (.sh, .py) in skill/scripts/ directories.

    Returns scripts with 'notation' field in {bundle}:{skill}:{script} format.

    Note: Skips private/internal modules (underscore-prefixed files like _module.py)
    per PEP 8 naming convention. Only public CLI entry points are exposed.
    """
    skills_dir = bundle_dir / "skills"
    if not skills_dir.is_dir():
        return []

    scripts = []
    # Find all .sh and .py files in scripts/ subdirectories
    for script_file in sorted(skills_dir.rglob("scripts/*.sh")) + sorted(skills_dir.rglob("scripts/*.py")):
        # Skip private/internal modules (underscore prefix = internal per PEP 8)
        if script_file.name.startswith('_'):
            continue
        if script_file.is_file():
            skill_dir = script_file.parent.parent
            skill_name = skill_dir.name

            # Determine script type
            script_type = "python" if script_file.suffix == ".py" else "bash"

            # Generate path formats
            relative_path = safe_relative_path(script_file)
            runtime_mount = f"./.claude/skills/{skill_name}/scripts/{script_file.name}"

            scripts.append({
                "name": script_file.stem,
                "skill": skill_name,
                "notation": f"{bundle_name}:{skill_name}:{script_file.stem}",
                "type": script_type,
                "path_formats": {
                    "runtime": runtime_mount,
                    "relative": relative_path,
                    "absolute": str(script_file.resolve())
                }
            })

    return scripts


def matches_name_pattern(name: str, patterns: list[str]) -> bool:
    """Check if name matches any of the given fnmatch patterns."""
    if not patterns:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def filter_resources_by_pattern(resources: list[dict], patterns: list[str]) -> list[dict]:
    """Filter resources list by name patterns."""
    if not patterns:
        return resources
    return [r for r in resources if matches_name_pattern(r.get('name', ''), patterns)]


VALID_RESOURCE_TYPES = ("agents", "commands", "skills", "scripts")


def parse_resource_types(resource_types_str: str) -> tuple[dict, str | None]:
    """Parse resource types string and return inclusion flags and optional error."""
    if resource_types_str == "all":
        return dict.fromkeys(VALID_RESOURCE_TYPES, True), None

    include = dict.fromkeys(VALID_RESOURCE_TYPES, False)
    for rtype in resource_types_str.split(","):
        rtype = rtype.strip()
        if rtype in VALID_RESOURCE_TYPES:
            include[rtype] = True
        else:
            return include, f"Invalid resource type: {rtype}"

    return include, None


def _extract_bundle_name(bundle_dir: Path) -> str:
    """Extract bundle name, handling versioned plugin-cache structure.

    For versioned structure (plugin-cache): .../plan-marshall/0.1-BETA/ -> "plan-marshall"
    For non-versioned structure (marketplace): .../plan-marshall/ -> "plan-marshall"
    """
    name = bundle_dir.name
    # If name looks like a version (e.g., "1.0.0", "0.1-BETA", "2.0.0-rc1"), use parent name
    # Pattern: starts with digit.digit, optionally followed by more version info
    if re.match(r'^\d+\.\d+', name):
        return bundle_dir.parent.name
    return name


def process_bundle(bundle_dir: Path, include: dict[str, bool], include_descriptions: bool,
                   name_patterns: list[str]) -> dict[str, Any]:
    """Process a single bundle directory and return its data."""
    bundle_name = _extract_bundle_name(bundle_dir)
    bundle: dict[str, Any] = {
        "name": bundle_name,
        "path": safe_relative_path(bundle_dir)
    }

    # Discover and filter resources
    agents = discover_agents(bundle_dir, include_descriptions) if include["agents"] else []
    commands = discover_commands(bundle_dir, include_descriptions) if include["commands"] else []
    skills = discover_skills(bundle_dir, include_descriptions) if include["skills"] else []
    scripts = discover_scripts(bundle_dir, bundle_name) if include["scripts"] else []

    # Apply name pattern filter
    bundle["agents"] = filter_resources_by_pattern(agents, name_patterns)
    bundle["commands"] = filter_resources_by_pattern(commands, name_patterns)
    bundle["skills"] = filter_resources_by_pattern(skills, name_patterns)
    bundle["scripts"] = filter_resources_by_pattern(scripts, name_patterns)

    # Bundle statistics
    bundle["statistics"] = {
        "agents": len(bundle["agents"]),
        "commands": len(bundle["commands"]),
        "skills": len(bundle["skills"]),
        "scripts": len(bundle["scripts"]),
        "total_resources": sum(len(bundle[k]) for k in ["agents", "commands", "skills", "scripts"])
    }

    return bundle


def _find_marketplace_path() -> Path | None:
    """Find marketplace/bundles directory in cwd or parent."""
    if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd() / MARKETPLACE_BUNDLES_PATH
    if (Path.cwd().parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd().parent / MARKETPLACE_BUNDLES_PATH
    return None


def _get_plugin_cache_path() -> Path | None:
    """Get plugin cache path if it exists."""
    cache_path = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
    return cache_path if cache_path.is_dir() else None


def get_base_path(scope: str) -> Path:
    """Determine base path based on scope.

    The 'auto' scope (default) tries marketplace first, then falls back to plugin-cache.
    This enables the script to work both in the marketplace repo and in other projects.
    """
    if scope == "auto":
        marketplace = _find_marketplace_path()
        if marketplace:
            return marketplace
        cache = _get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(
            f"Neither {MARKETPLACE_BUNDLES_PATH} nor plugin cache found. "
            f"Run from marketplace repo or ensure plugin is installed."
        )

    if scope == "marketplace":
        marketplace = _find_marketplace_path()
        if marketplace:
            return marketplace
        raise FileNotFoundError(f"{MARKETPLACE_BUNDLES_PATH} directory not found")

    if scope == "global":
        return Path.home() / CLAUDE_DIR

    if scope == "project":
        return Path.cwd() / CLAUDE_DIR

    if scope == "plugin-cache":
        cache = _get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(f"Plugin cache not found: {Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}")

    raise ValueError(f"Invalid scope: {scope}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan marketplace directories and return structured inventory"
    )
    parser.add_argument(
        "--scope",
        choices=["auto", "marketplace", "global", "project", "plugin-cache"],
        default="auto",
        help="Directory scope: auto (default, tries marketplace then plugin-cache), "
             "marketplace, plugin-cache, global, project"
    )
    parser.add_argument(
        "--resource-types",
        default="all",
        help="Resource types: agents, commands, skills, scripts, or comma-separated"
    )
    parser.add_argument(
        "--include-descriptions",
        action="store_true",
        help="Extract descriptions from YAML frontmatter"
    )
    parser.add_argument(
        "--name-pattern",
        default="",
        help="Filter resources by name pattern (fnmatch glob, pipe-separated for multiple)"
    )
    parser.add_argument(
        "--bundles",
        default="",
        help="Filter to specific bundles (comma-separated)"
    )

    args = parser.parse_args()

    # Parse name patterns (pipe-separated for multiple patterns)
    name_patterns = [p.strip() for p in args.name_pattern.split("|") if p.strip()] if args.name_pattern else []

    # Parse bundle filter
    bundle_filter = {b.strip() for b in args.bundles.split(",") if b.strip()} if args.bundles else set()

    # Parse resource types
    include, error = parse_resource_types(args.resource_types)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(f"Valid values: {', '.join(VALID_RESOURCE_TYPES)}", file=sys.stderr)
        return 1

    # Get base path
    try:
        base_path = get_base_path(args.scope)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not base_path.is_dir():
        print(f"ERROR: Base path not found: {base_path}", file=sys.stderr)
        return 1

    # Find and filter bundles
    bundle_dirs = find_bundles(base_path)
    if bundle_filter:
        bundle_dirs = [b for b in bundle_dirs if b.name in bundle_filter]

    # Build inventory
    bundles_data = [
        process_bundle(bundle_dir, include, args.include_descriptions, name_patterns)
        for bundle_dir in bundle_dirs
    ]

    # Calculate totals
    total_agents = sum(b["statistics"]["agents"] for b in bundles_data)
    total_commands = sum(b["statistics"]["commands"] for b in bundles_data)
    total_skills = sum(b["statistics"]["skills"] for b in bundles_data)
    total_scripts = sum(b["statistics"]["scripts"] for b in bundles_data)

    # Output
    output = {
        "scope": args.scope,
        "base_path": str(base_path),
        "bundles": bundles_data,
        "statistics": {
            "total_bundles": len(bundles_data),
            "total_agents": total_agents,
            "total_commands": total_commands,
            "total_skills": total_skills,
            "total_scripts": total_scripts,
            "total_resources": total_agents + total_commands + total_skills + total_scripts
        }
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
