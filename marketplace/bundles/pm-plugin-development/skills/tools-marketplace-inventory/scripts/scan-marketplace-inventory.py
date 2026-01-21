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
    --full                   Include full details: frontmatter fields and skill subdirectory contents
    --name-pattern <pattern> Filter resources by name pattern (fnmatch glob, pipe-separated for multiple)
    --bundles <names>        Filter to specific bundles (comma-separated)
    --output <path>          Custom output file path (default: .plan/temp/.../inventory-{timestamp}.toon)
    --direct-result          Output full TOON directly to stdout (default: write to file)

Output Modes:
    Default:        Writes full inventory to .plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon
                    Prints TOON summary with output_file path to stdout
    --direct-result: Outputs full TOON directly to stdout (for small results or piped usage)

Output Format:
    Bundles are top-level keys in the output. Each bundle contains agents, commands, skills, scripts.
    Default mode shows simple name lists. With --full, includes frontmatter and skill subdirectories.

Script Output:
    Scripts include a 'notation' field in {bundle}:{skill}:{script} format for use with
    the script executor (e.g., "pm-workflow:manage-files:manage-files").

Exit codes:
    0 - Success
    1 - Error (invalid parameters, missing directory)
"""

import argparse
import fnmatch
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Note: toon_parser not needed - using custom serialize_inventory_toon for hierarchical output

# Constants
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'
DEFAULT_OUTPUT_SUBDIR = 'tools-marketplace-inventory'


def get_plan_dir() -> Path:
    """Get the .plan directory path, respecting PLAN_BASE_DIR override."""
    base = os.environ.get('PLAN_BASE_DIR', '.plan')
    return Path(base)


def get_temp_dir(subdir: str) -> Path:
    """Get temp directory under .plan/temp/{subdir}."""
    return get_plan_dir() / 'temp' / subdir

# Script-relative path discovery (works regardless of cwd)
# Script is at: marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/
# So bundles directory is 5 levels up from script
SCRIPT_DIR = Path(__file__).resolve().parent
_BUNDLES_FROM_SCRIPT = SCRIPT_DIR.parent.parent.parent.parent.parent


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
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
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
    if not content.startswith('---'):
        return None

    # Extract frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)

    # Extract description field
    for line in frontmatter.split('\n'):
        if line.startswith('description:'):
            desc = line[len('description:') :].strip()
            return desc if desc else None

    return None


def extract_frontmatter_fields(file_path: Path) -> dict[str, Any]:
    """Extract additional frontmatter fields for --full output.

    Returns dict with optional fields: user_invocable, allowed_tools, model
    """
    result: dict[str, Any] = {}
    if not file_path.exists():
        return result

    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return result

    if not content.startswith('---'):
        return result

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return result

    frontmatter = match.group(1)

    for line in frontmatter.split('\n'):
        line = line.strip()
        if line.startswith('user-invocable:'):
            value = line[len('user-invocable:') :].strip().lower()
            result['user_invocable'] = value == 'true'
        elif line.startswith('allowed-tools:'):
            # Parse YAML list format: [Read, Write, Bash] or - Read\n- Write
            value = line[len('allowed-tools:') :].strip()
            if value.startswith('[') and value.endswith(']'):
                # Inline list format
                tools = [t.strip() for t in value[1:-1].split(',') if t.strip()]
                result['allowed_tools'] = tools
        elif line.startswith('model:'):
            result['model'] = line[len('model:') :].strip()

    return result


def discover_skill_subdirs(skill_dir: Path) -> dict[str, list[str]]:
    """Discover subdirectories in a skill and list their files.

    Returns dict mapping subdir name to list of repo-relative file paths.
    Excludes 'scripts' directory (handled separately).
    """
    subdirs: dict[str, list[str]] = {}

    for subdir in sorted(skill_dir.iterdir()):
        if subdir.is_dir() and subdir.name != 'scripts':
            files = sorted([safe_relative_path(f) for f in subdir.iterdir() if f.is_file()])
            if files:
                subdirs[subdir.name] = files

    return subdirs


def discover_agents(bundle_dir: Path, include_descriptions: bool, full: bool = False) -> list[dict]:
    """Discover agent .md files in bundle/agents/."""
    agents_dir = bundle_dir / 'agents'
    if not agents_dir.is_dir():
        return []

    agents = []
    for agent_file in sorted(agents_dir.glob('*.md')):
        if agent_file.is_file():
            agent: dict[str, Any] = {'name': agent_file.stem}
            if full:
                agent['path'] = safe_relative_path(agent_file)
                agent['description'] = extract_description(agent_file)
                agent.update(extract_frontmatter_fields(agent_file))
            elif include_descriptions:
                agent['path'] = safe_relative_path(agent_file)
                agent['description'] = extract_description(agent_file)
            agents.append(agent)
    return agents


def discover_commands(bundle_dir: Path, include_descriptions: bool, full: bool = False) -> list[dict]:
    """Discover command .md files in bundle/commands/."""
    commands_dir = bundle_dir / 'commands'
    if not commands_dir.is_dir():
        return []

    commands = []
    for command_file in sorted(commands_dir.glob('*.md')):
        if command_file.is_file():
            command: dict[str, Any] = {'name': command_file.stem}
            if full:
                command['path'] = safe_relative_path(command_file)
                command['description'] = extract_description(command_file)
                command.update(extract_frontmatter_fields(command_file))
            elif include_descriptions:
                command['path'] = safe_relative_path(command_file)
                command['description'] = extract_description(command_file)
            commands.append(command)
    return commands


def discover_skills(bundle_dir: Path, include_descriptions: bool, full: bool = False) -> list[dict]:
    """Discover skill directories containing SKILL.md."""
    skills_dir = bundle_dir / 'skills'
    if not skills_dir.is_dir():
        return []

    skills = []
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        skill_dir = skill_md.parent
        skill: dict[str, Any] = {'name': skill_dir.name}
        if full:
            skill['path'] = safe_relative_path(skill_dir)
            skill['description'] = extract_description(skill_md)
            skill.update(extract_frontmatter_fields(skill_md))
            # Add subdirectory contents
            subdirs = discover_skill_subdirs(skill_dir)
            skill.update(subdirs)
        elif include_descriptions:
            skill['path'] = safe_relative_path(skill_dir)
            skill['description'] = extract_description(skill_md)
        skills.append(skill)
    return skills


def discover_scripts(bundle_dir: Path, bundle_name: str) -> list[dict]:
    """Discover script files (.sh, .py) in skill/scripts/ directories.

    Returns scripts with 'notation' field in {bundle}:{skill}:{script} format.

    Note: Skips private/internal modules (underscore-prefixed files like _module.py)
    per PEP 8 naming convention. Only public CLI entry points are exposed.
    """
    skills_dir = bundle_dir / 'skills'
    if not skills_dir.is_dir():
        return []

    scripts = []
    # Find all .sh and .py files in scripts/ subdirectories
    for script_file in sorted(skills_dir.rglob('scripts/*.sh')) + sorted(skills_dir.rglob('scripts/*.py')):
        # Skip private/internal modules (underscore prefix = internal per PEP 8)
        if script_file.name.startswith('_'):
            continue
        if script_file.is_file():
            skill_dir = script_file.parent.parent
            skill_name = skill_dir.name

            # Determine script type
            script_type = 'python' if script_file.suffix == '.py' else 'bash'

            # Generate path formats
            relative_path = safe_relative_path(script_file)
            runtime_mount = f'./.claude/skills/{skill_name}/scripts/{script_file.name}'

            scripts.append(
                {
                    'name': script_file.stem,
                    'skill': skill_name,
                    'notation': f'{bundle_name}:{skill_name}:{script_file.stem}',
                    'type': script_type,
                    'path_formats': {
                        'runtime': runtime_mount,
                        'relative': relative_path,
                        'absolute': str(script_file.resolve()),
                    },
                }
            )

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


VALID_RESOURCE_TYPES = ('agents', 'commands', 'skills', 'scripts')


def parse_resource_types(resource_types_str: str) -> tuple[dict, str | None]:
    """Parse resource types string and return inclusion flags and optional error."""
    if resource_types_str == 'all':
        return dict.fromkeys(VALID_RESOURCE_TYPES, True), None

    include = dict.fromkeys(VALID_RESOURCE_TYPES, False)
    for rtype in resource_types_str.split(','):
        rtype = rtype.strip()
        if rtype in VALID_RESOURCE_TYPES:
            include[rtype] = True
        else:
            return include, f'Invalid resource type: {rtype}'

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


def process_bundle(
    bundle_dir: Path, include: dict[str, bool], include_descriptions: bool, name_patterns: list[str], full: bool = False
) -> dict[str, Any]:
    """Process a single bundle directory and return its data."""
    bundle_name = _extract_bundle_name(bundle_dir)
    bundle: dict[str, Any] = {'name': bundle_name, 'path': safe_relative_path(bundle_dir)}

    # Discover and filter resources
    agents = discover_agents(bundle_dir, include_descriptions, full) if include['agents'] else []
    commands = discover_commands(bundle_dir, include_descriptions, full) if include['commands'] else []
    skills = discover_skills(bundle_dir, include_descriptions, full) if include['skills'] else []
    scripts = discover_scripts(bundle_dir, bundle_name) if include['scripts'] else []

    # Apply name pattern filter
    bundle['agents'] = filter_resources_by_pattern(agents, name_patterns)
    bundle['commands'] = filter_resources_by_pattern(commands, name_patterns)
    bundle['skills'] = filter_resources_by_pattern(skills, name_patterns)
    bundle['scripts'] = filter_resources_by_pattern(scripts, name_patterns)

    return bundle


def _find_marketplace_path() -> Path | None:
    """Find marketplace/bundles directory relative to cwd or script.

    First checks cwd-based discovery (supports test fixtures),
    then falls back to script-relative path (works regardless of cwd).
    """
    # First try cwd-based discovery (allows tests to use fixture directories)
    if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd() / MARKETPLACE_BUNDLES_PATH
    if (Path.cwd().parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd().parent / MARKETPLACE_BUNDLES_PATH
    # Fallback to script-relative path (works regardless of cwd)
    if _BUNDLES_FROM_SCRIPT.is_dir():
        return _BUNDLES_FROM_SCRIPT
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
    if scope == 'auto':
        marketplace = _find_marketplace_path()
        if marketplace:
            return marketplace
        cache = _get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(
            f'Neither {MARKETPLACE_BUNDLES_PATH} nor plugin cache found. '
            f'Run from marketplace repo or ensure plugin is installed.'
        )

    if scope == 'marketplace':
        marketplace = _find_marketplace_path()
        if marketplace:
            return marketplace
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} directory not found')

    if scope == 'global':
        return Path.home() / CLAUDE_DIR

    if scope == 'project':
        return Path.cwd() / CLAUDE_DIR

    if scope == 'plugin-cache':
        cache = _get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(f'Plugin cache not found: {Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}')

    raise ValueError(f'Invalid scope: {scope}')


def serialize_inventory_toon(data: dict, full: bool = False) -> str:
    """Serialize inventory to TOON with bundle-block structure.

    Bundles are top-level keys. Components are nested lists.
    Default mode shows simple name lists.
    Full mode includes paths, descriptions, frontmatter, and skill subdirs.
    """
    lines: list[str] = []
    lines.append('status: success')
    lines.append(f"scope: {data['scope']}")
    lines.append(f"base_path: {data['base_path']}")
    lines.append('')

    for bundle in data['bundles']:
        bundle_name = bundle['name']
        lines.append(f'{bundle_name}:')
        lines.append(f"  path: {bundle['path']}")

        for resource_type in ['agents', 'commands', 'skills', 'scripts']:
            items = bundle.get(resource_type, [])
            if items:
                lines.append(f'  {resource_type}[{len(items)}]:')
                for item in items:
                    if full:
                        # Detailed format with frontmatter
                        lines.append(f"    - name: {item['name']}")
                        if item.get('path'):
                            lines.append(f"      path: {item['path']}")
                        if item.get('description'):
                            lines.append(f"      description: {item['description']}")
                        if item.get('user_invocable') is not None:
                            lines.append(f"      user_invocable: {str(item['user_invocable']).lower()}")
                        if item.get('allowed_tools'):
                            lines.append(f"      allowed_tools: [{', '.join(item['allowed_tools'])}]")
                        if item.get('model'):
                            lines.append(f"      model: {item['model']}")
                        # Scripts have additional fields
                        if item.get('skill'):
                            lines.append(f"      skill: {item['skill']}")
                        if item.get('notation'):
                            lines.append(f"      notation: {item['notation']}")
                        if item.get('type'):
                            lines.append(f"      type: {item['type']}")
                        # Skill subdirectories
                        for subdir_name in ['standards', 'templates', 'references', 'knowledge', 'examples', 'documents']:
                            if item.get(subdir_name):
                                subdir_files = item[subdir_name]
                                lines.append(f'      {subdir_name}[{len(subdir_files)}]:')
                                for file_name in subdir_files:
                                    lines.append(f'        - {file_name}')
                    else:
                        # Simple format - just names
                        lines.append(f"    - {item['name']}")
        lines.append('')

    # Statistics
    lines.append('statistics:')
    for key, value in data['statistics'].items():
        lines.append(f'  {key}: {value}')

    return '\n'.join(lines)


def write_file_output(output: dict, output_dir: Path, custom_output: str = '', full: bool = False) -> tuple[Path, str]:
    """Write full output to TOON file, return (file_path, summary_toon_for_stdout).

    Args:
        output: The inventory data to write
        output_dir: Default directory for timestamped output files
        custom_output: Optional custom output file path (overrides output_dir)
        full: Whether to include full details in output
    """
    if custom_output:
        # Use custom output path
        output_file = Path(custom_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Use default timestamped path
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = output_dir / f'inventory-{timestamp}.toon'

    # Write full inventory in TOON format with bundle-block structure
    output_file.write_text(serialize_inventory_toon(output, full))

    # Return summary in TOON format
    summary_lines = [
        'status: success',
        'output_mode: file',
        f'output_file: {output_file}',
        f"scope: {output['scope']}",
        f"base_path: {output['base_path']}",
        '',
        'statistics:',
    ]
    for key, value in output['statistics'].items():
        summary_lines.append(f'  {key}: {value}')
    summary_lines.append('')
    summary_lines.append(f'next_step: Read {output_file} for full inventory details')
    return output_file, '\n'.join(summary_lines)


def main():
    parser = argparse.ArgumentParser(description='Scan marketplace directories and return structured inventory')
    parser.add_argument(
        '--scope',
        choices=['auto', 'marketplace', 'global', 'project', 'plugin-cache'],
        default='auto',
        help='Directory scope: auto (default, tries marketplace then plugin-cache), '
        'marketplace, plugin-cache, global, project',
    )
    parser.add_argument(
        '--resource-types', default='all', help='Resource types: agents, commands, skills, scripts, or comma-separated'
    )
    parser.add_argument(
        '--include-descriptions', action='store_true', help='Extract descriptions from YAML frontmatter'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Include full details: frontmatter fields and skill subdirectory contents',
    )
    parser.add_argument(
        '--name-pattern',
        default='',
        help='Filter resources by name pattern (fnmatch glob, pipe-separated for multiple)',
    )
    parser.add_argument('--bundles', default='', help='Filter to specific bundles (comma-separated)')
    parser.add_argument(
        '--output',
        default='',
        help='Custom output file path (default: .plan/temp/.../inventory-{timestamp}.toon)',
    )
    parser.add_argument(
        '--direct-result',
        action='store_true',
        help='Output directly to stdout (default: write to file)',
    )
    parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format: toon (default) or json',
    )

    args = parser.parse_args()

    # Parse name patterns (pipe-separated for multiple patterns)
    name_patterns = [p.strip() for p in args.name_pattern.split('|') if p.strip()] if args.name_pattern else []

    # Parse bundle filter
    bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()} if args.bundles else set()

    # Parse resource types
    include, error = parse_resource_types(args.resource_types)
    if error:
        print(f'ERROR: {error}', file=sys.stderr)
        print(f'Valid values: {", ".join(VALID_RESOURCE_TYPES)}', file=sys.stderr)
        return 1

    # Get base path
    try:
        base_path = get_base_path(args.scope)
    except (FileNotFoundError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1

    if not base_path.is_dir():
        print(f'ERROR: Base path not found: {base_path}', file=sys.stderr)
        return 1

    # Find and filter bundles
    bundle_dirs = find_bundles(base_path)
    if bundle_filter:
        bundle_dirs = [b for b in bundle_dirs if b.name in bundle_filter]

    # Build inventory
    bundles_data = [
        process_bundle(bundle_dir, include, args.include_descriptions, name_patterns, args.full)
        for bundle_dir in bundle_dirs
    ]

    # Calculate totals
    total_agents = sum(len(b.get('agents', [])) for b in bundles_data)
    total_commands = sum(len(b.get('commands', [])) for b in bundles_data)
    total_skills = sum(len(b.get('skills', [])) for b in bundles_data)
    total_scripts = sum(len(b.get('scripts', [])) for b in bundles_data)

    # Output structure (bundles remain as list internally, serialization handles format)
    output = {
        'scope': args.scope,
        'base_path': str(base_path),
        'bundles': bundles_data,
        'statistics': {
            'total_bundles': len(bundles_data),
            'total_agents': total_agents,
            'total_commands': total_commands,
            'total_skills': total_skills,
            'total_scripts': total_scripts,
            'total_resources': total_agents + total_commands + total_skills + total_scripts,
        },
    }

    if args.direct_result:
        # Direct mode: output to stdout (for small results or piped usage)
        if args.format == 'json':
            import json

            # For JSON, convert bundles list to dict keyed by name
            json_output = {
                'status': 'success',
                'scope': output['scope'],
                'base_path': output['base_path'],
                'bundles': {
                    b['name']: {k: v for k, v in b.items() if k != 'name'} for b in bundles_data
                },
                'statistics': output['statistics'],
            }
            print(json.dumps(json_output, indent=2))
        else:
            print(serialize_inventory_toon(output, args.full))
    else:
        # Default: File mode - write full output to file, print summary
        output_dir = get_temp_dir(DEFAULT_OUTPUT_SUBDIR)
        try:
            _, summary_toon = write_file_output(output, output_dir, args.output, args.full)
            print(summary_toon)
        except OSError as e:
            print(f'ERROR: Failed to write output file: {e}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
