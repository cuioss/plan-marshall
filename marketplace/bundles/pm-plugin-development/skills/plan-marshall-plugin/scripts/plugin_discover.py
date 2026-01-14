#!/usr/bin/env python3
"""Plugin bundle discovery for marketplace bundles.

Discovers Claude Code marketplace bundles with complete metadata.
Each bundle becomes a module in derived-data.json format.

Packages are:
- skills: Each skill directory (description from SKILL.md frontmatter)
- agents: Each .md file in agents/ (description from frontmatter)
- commands: Each .md file in commands/ (description from frontmatter)

Usage:
    python3 plugin_discover.py discover --root /path/to/project

Output:
    JSON array of module objects conforming to build-project-structure.md contract.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Add extension-api scripts to path for base library imports
EXTENSION_API_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "plan-marshall"
    / "skills"
    / "extension-api"
    / "scripts"
)
if str(EXTENSION_API_DIR) not in sys.path:
    sys.path.insert(0, str(EXTENSION_API_DIR))

from _build_discover import find_readme

# =============================================================================
# Constants
# =============================================================================

PLUGIN_JSON = ".claude-plugin/plugin.json"
"""Descriptor file that identifies a bundle."""

SKILL_MD = "SKILL.md"
"""Skill definition file containing frontmatter."""

BUNDLES_DIR = "marketplace/bundles"
"""Directory containing marketplace bundles."""

BUILD_SYSTEM = "marshall-plugin"
"""Build system identifier for plugin bundles."""


# =============================================================================
# Frontmatter Extraction
# =============================================================================


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from content.

    Args:
        content: File content starting with potential frontmatter.

    Returns:
        Tuple of (has_frontmatter, frontmatter_content).
    """
    if not content.startswith("---"):
        return False, ""

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        return True, match.group(1)
    return False, ""


def extract_description_from_frontmatter(frontmatter: str) -> str | None:
    """Extract description field from YAML frontmatter.

    Handles both single-line and YAML multiline (|) descriptions.

    Args:
        frontmatter: YAML frontmatter content (without delimiters).

    Returns:
        Description string or None if not found.
    """
    lines = frontmatter.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            value = line[len("description:") :].strip()

            # Single-line: description: Some text
            if value and value not in ("|", ">"):
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                return value.strip()

            # Multiline (| or >): collect indented lines
            if value in ("|", ">"):
                multiline_parts = []
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    # Stop at non-indented line (next field)
                    if next_line and not next_line.startswith(" "):
                        break
                    # Collect indented content
                    if next_line.strip():
                        multiline_parts.append(next_line.strip())
                if multiline_parts:
                    # Return first paragraph (up to blank line or Examples:)
                    result = []
                    for part in multiline_parts:
                        if part.startswith("Examples:") or not part:
                            break
                        result.append(part)
                    return " ".join(result) if result else multiline_parts[0]

    return None


def get_component_description(file_path: Path) -> str | None:
    """Get description from a component file's frontmatter.

    Args:
        file_path: Path to .md file with frontmatter.

    Returns:
        Description string or None if not found.
    """
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        has_fm, frontmatter = extract_frontmatter(content)
        if has_fm:
            return extract_description_from_frontmatter(frontmatter)
    except OSError:
        pass
    return None


# =============================================================================
# Bundle Discovery
# =============================================================================


def discover_bundles(project_root: str) -> list[Path]:
    """Discover all marketplace bundles in project.

    A bundle is identified by the presence of .claude-plugin/plugin.json.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of absolute paths to plugin.json files, sorted by bundle name.
    """
    root = Path(project_root).resolve()
    bundles_path = root / BUNDLES_DIR

    if not bundles_path.is_dir():
        return []

    plugin_files = []
    for bundle_dir in sorted(bundles_path.iterdir()):
        if bundle_dir.is_dir():
            plugin_json = bundle_dir / PLUGIN_JSON
            if plugin_json.is_file():
                plugin_files.append(plugin_json)

    return plugin_files


def load_plugin_json(plugin_path: Path) -> dict | None:
    """Load and parse plugin.json file.

    Args:
        plugin_path: Absolute path to plugin.json.

    Returns:
        Parsed JSON as dict, or None on error.
    """
    try:
        content = plugin_path.read_text(encoding="utf-8")
        data: dict = json.loads(content)
        return data
    except (OSError, json.JSONDecodeError):
        return None


# =============================================================================
# Package Discovery
# =============================================================================


def discover_skills(bundle_dir: Path, plugin_data: dict) -> dict:
    """Discover skill packages in a bundle.

    Each skill directory becomes a package. Description from SKILL.md frontmatter.

    Args:
        bundle_dir: Absolute path to bundle directory.
        plugin_data: Parsed plugin.json data.

    Returns:
        Dict of skill packages keyed by skill name.
    """
    packages = {}
    skills_list = plugin_data.get("skills", [])

    for skill_ref in skills_list:
        # skill_ref is like "./skills/plugin-doctor"
        skill_path = bundle_dir / skill_ref.lstrip("./")
        if skill_path.is_dir():
            skill_name = skill_path.name
            skill_md = skill_path / SKILL_MD
            description = get_component_description(skill_md)

            pkg_path = skill_ref.lstrip("./")

            packages[f"skill:{skill_name}"] = {
                "path": pkg_path,
                "type": "skill",
            }
            if description:
                packages[f"skill:{skill_name}"]["description"] = description

    return packages


def discover_agents(bundle_dir: Path, plugin_data: dict) -> dict:
    """Discover agent packages in a bundle.

    Each .md file in agents/ becomes a package. Description from frontmatter.

    Args:
        bundle_dir: Absolute path to bundle directory.
        plugin_data: Parsed plugin.json data.

    Returns:
        Dict of agent packages keyed by agent name.
    """
    packages = {}
    agents_list = plugin_data.get("agents", [])

    for agent_ref in agents_list:
        # agent_ref is like "./agents/tool-coverage-agent.md"
        agent_path = bundle_dir / agent_ref.lstrip("./")
        if agent_path.is_file() and agent_path.suffix == ".md":
            agent_name = agent_path.stem  # Remove .md extension
            description = get_component_description(agent_path)

            pkg_path = agent_ref.lstrip("./")

            packages[f"agent:{agent_name}"] = {
                "path": pkg_path,
                "type": "agent",
            }
            if description:
                packages[f"agent:{agent_name}"]["description"] = description

    return packages


def discover_commands(bundle_dir: Path, plugin_data: dict) -> dict:
    """Discover command packages in a bundle.

    Each .md file in commands/ becomes a package. Description from frontmatter.

    Args:
        bundle_dir: Absolute path to bundle directory.
        plugin_data: Parsed plugin.json data.

    Returns:
        Dict of command packages keyed by command name.
    """
    packages = {}
    commands_list = plugin_data.get("commands", [])

    for cmd_ref in commands_list:
        # cmd_ref is like "./commands/plugin-doctor.md"
        cmd_path = bundle_dir / cmd_ref.lstrip("./")
        if cmd_path.is_file() and cmd_path.suffix == ".md":
            cmd_name = cmd_path.stem  # Remove .md extension
            description = get_component_description(cmd_path)

            pkg_path = cmd_ref.lstrip("./")

            packages[f"command:{cmd_name}"] = {
                "path": pkg_path,
                "type": "command",
            }
            if description:
                packages[f"command:{cmd_name}"]["description"] = description

    return packages


# =============================================================================
# Command Building
# =============================================================================


def build_commands(bundle_name: str) -> dict:
    """Build commands for a bundle module.

    Args:
        bundle_name: Name of the bundle.

    Returns:
        Dict of canonical commands.
    """
    return {
        "module-tests": f"python3 test/run-tests.py test/{bundle_name}",
        "quality-gate": f"/plugin-doctor --bundle {bundle_name}",
    }


# =============================================================================
# Module Building
# =============================================================================


def build_bundle_module(
    plugin_path: Path, project_root: Path, plugin_data: dict
) -> dict:
    """Build complete module dict from bundle.

    Args:
        plugin_path: Absolute path to plugin.json.
        project_root: Project root path.
        plugin_data: Parsed plugin.json data.

    Returns:
        Complete module dict conforming to build-project-structure.md.
    """
    bundle_dir = plugin_path.parent.parent  # .claude-plugin/plugin.json -> bundle root
    bundle_name = bundle_dir.name

    # Calculate relative paths
    try:
        relative_path = str(bundle_dir.relative_to(project_root))
        descriptor_path = str(plugin_path.relative_to(project_root))
    except ValueError:
        relative_path = bundle_name
        descriptor_path = f"{bundle_name}/{PLUGIN_JSON}"

    # Find README
    readme_path = find_readme(str(bundle_dir))
    if readme_path:
        readme_full = f"{relative_path}/{readme_path}"
    else:
        readme_full = None

    # Discover packages
    packages = {}
    packages.update(discover_skills(bundle_dir, plugin_data))
    packages.update(discover_agents(bundle_dir, plugin_data))
    packages.update(discover_commands(bundle_dir, plugin_data))

    # Count stats
    skill_count = len([k for k in packages if k.startswith("skill:")])
    agent_count = len([k for k in packages if k.startswith("agent:")])
    command_count = len([k for k in packages if k.startswith("command:")])

    # Build source paths
    sources = []
    if (bundle_dir / "skills").is_dir():
        sources.append(f"{relative_path}/skills")
    if (bundle_dir / "agents").is_dir():
        sources.append(f"{relative_path}/agents")
    if (bundle_dir / "commands").is_dir():
        sources.append(f"{relative_path}/commands")

    # Build commands
    commands = build_commands(bundle_name)

    # Extract author name
    author = plugin_data.get("author")
    if isinstance(author, dict):
        author = author.get("name")

    return {
        "name": bundle_name,
        "build_systems": [BUILD_SYSTEM],
        "paths": {
            "module": relative_path,
            "descriptor": descriptor_path,
            "sources": sources,
            "tests": [f"test/{bundle_name}"],
            "readme": readme_full,
        },
        "metadata": {
            "bundle_name": bundle_name,
            "version": plugin_data.get("version"),
            "description": plugin_data.get("description"),
            "author": author,
        },
        "packages": packages,
        "dependencies": [],
        "stats": {
            "skill_count": skill_count,
            "agent_count": agent_count,
            "command_count": command_count,
        },
        "commands": commands,
    }


def build_default_module(project_root: Path, bundle_count: int) -> dict:
    """Build default root module for project-wide testing.

    Args:
        project_root: Project root path.
        bundle_count: Number of bundles discovered.

    Returns:
        Default module dict with project-wide test command.
    """
    readme_path = find_readme(str(project_root))

    return {
        "name": "default",
        "build_systems": [BUILD_SYSTEM],
        "paths": {
            "module": ".",
            "descriptor": "marketplace/.claude-plugin/marketplace.json",
            "sources": ["marketplace/bundles"],
            "tests": ["test"],
            "readme": readme_path,
        },
        "metadata": {
            "description": "Plan Marshall marketplace root module",
        },
        "packages": {},
        "dependencies": [],
        "stats": {
            "bundle_count": bundle_count,
        },
        "commands": {
            "module-tests": "python3 test/run-tests.py",
            "quality-gate": "/plugin-doctor marketplace",
        },
    }


# =============================================================================
# Main Discovery
# =============================================================================


def discover_plugin_modules(project_root: str) -> list:
    """Discover all plugin bundle modules with complete metadata.

    Implements the discover_modules() contract from ExtensionBase.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to build-project-structure.md contract.
        Includes default root module plus one module per bundle.
    """
    root = Path(project_root).resolve()
    modules = []

    # Discover bundles
    plugin_files = discover_bundles(project_root)

    for plugin_path in plugin_files:
        plugin_data = load_plugin_json(plugin_path)
        if plugin_data:
            module = build_bundle_module(plugin_path, root, plugin_data)
            modules.append(module)

    # Add default root module at the beginning
    default_module = build_default_module(root, len(modules))
    modules.insert(0, default_module)

    return modules


# =============================================================================
# CLI
# =============================================================================


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Plugin bundle discovery")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # discover subcommand
    discover_parser = subparsers.add_parser("discover", help="Discover plugin bundles")
    discover_parser.add_argument(
        "--root", required=True, help="Project root directory"
    )

    args = parser.parse_args()

    if args.command == "discover":
        modules = discover_plugin_modules(args.root)
        print(json.dumps(modules, indent=2))


if __name__ == "__main__":
    main()
