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


def discover_skill_subdirs(
    skill_dir: Path,
    content_include: list[str] | None = None,
    content_exclude: list[str] | None = None,
) -> dict[str, list[str]]:
    """Discover subdirectories in a skill and list their files.

    Returns dict mapping subdir name to list of repo-relative file paths.
    Excludes 'scripts' directory (handled separately).

    When content_include/content_exclude are provided, filters subdocument files
    by content patterns (same logic as main resource filtering).
    """
    subdirs: dict[str, list[str]] = {}

    for subdir in sorted(skill_dir.iterdir()):
        if subdir.is_dir() and subdir.name != 'scripts':
            files = []
            for f in sorted(subdir.iterdir()):
                if not f.is_file():
                    continue

                # Filter by content if patterns provided
                if content_include or content_exclude:
                    try:
                        content = f.read_text()
                    except (OSError, UnicodeDecodeError):
                        continue
                    if content_include and not matches_any_content_pattern(content, content_include):
                        continue
                    if content_exclude and matches_any_content_pattern(content, content_exclude):
                        continue

                files.append(safe_relative_path(f))

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


def discover_skills(
    bundle_dir: Path,
    include_descriptions: bool,
    full: bool = False,
    content_include: list[str] | None = None,
    content_exclude: list[str] | None = None,
) -> list[dict]:
    """Discover skill directories containing SKILL.md.

    When content_include/content_exclude are provided with full=True,
    subdocument files are also filtered by the same content patterns.
    """
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
            # Add subdirectory contents (filtered if content patterns active)
            subdirs = discover_skill_subdirs(skill_dir, content_include, content_exclude)
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


def discover_tests(bundle_name: str) -> list[dict]:
    """Discover test files for a bundle from test/{bundle-name}/ directory.

    Returns test files (test_*.py, conftest.py) with type indicator.
    """
    test_dir = Path('test') / bundle_name
    if not test_dir.is_dir():
        return []

    tests = []
    # Test files (test_*.py)
    for test_file in test_dir.rglob('test_*.py'):
        if test_file.is_file():
            tests.append(
                {
                    'name': test_file.stem,
                    'path': safe_relative_path(test_file),
                    'type': 'test',
                }
            )
    # conftest.py files
    for conftest in test_dir.rglob('conftest.py'):
        if conftest.is_file():
            tests.append(
                {
                    'name': 'conftest',
                    'path': safe_relative_path(conftest),
                    'type': 'conftest',
                }
            )
    return sorted(tests, key=lambda x: (x['name'], x['path']))


def discover_project_skills() -> dict | None:
    """Discover project-level skills from .claude/skills/ directory.

    Returns a pseudo-bundle dict for project-skills, or None if no skills found.
    """
    claude_skills = Path('.claude/skills')
    if not claude_skills.is_dir():
        return None

    bundle: dict[str, Any] = {
        'name': 'project-skills',
        'path': '.claude/skills',
        'skills': [],
        'scripts': [],
    }

    for skill_dir in sorted(claude_skills.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / 'SKILL.md'
        if skill_md.exists():
            skill_entry: dict[str, Any] = {
                'name': skill_dir.name,
                'path': safe_relative_path(skill_dir),
            }
            bundle['skills'].append(skill_entry)

            # Also discover scripts
            scripts_dir = skill_dir / 'scripts'
            if scripts_dir.is_dir():
                for script in sorted(scripts_dir.glob('*.py')):
                    if script.is_file() and not script.name.startswith('_'):
                        bundle['scripts'].append(
                            {
                                'name': script.stem,
                                'skill': skill_dir.name,
                                'path': safe_relative_path(script),
                                'notation': f'project-skills:{skill_dir.name}:{script.stem}',
                            }
                        )

    return bundle if bundle['skills'] else None


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


def matches_any_content_pattern(content: str, patterns: list[str]) -> bool:
    """Check if content matches any of the regex patterns (OR logic)."""
    return any(re.search(p, content, re.MULTILINE) for p in patterns)


def filter_resources_by_content(
    resources: list[dict],
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> tuple[list[dict], dict[str, int]]:
    """Filter resources by content patterns.

    Args:
        resources: List of resource dicts (must have 'path' key)
        include_patterns: Include if matches any (OR). Empty = include all.
        exclude_patterns: Exclude if matches any (OR). Empty = exclude none.

    Returns:
        Tuple of (filtered_resources, stats_dict)
        stats_dict has keys: input_count, matched_count, excluded_count

    Note: Resource paths are expected to be relative from cwd (as produced by safe_relative_path).
    """
    stats = {'input_count': len(resources), 'matched_count': 0, 'excluded_count': 0}

    if not include_patterns and not exclude_patterns:
        stats['matched_count'] = len(resources)
        return resources, stats

    result = []
    for r in resources:
        path_str = r.get('path')
        if not path_str:
            # Resources without path can't be content-filtered, skip
            stats['excluded_count'] += 1
            continue

        file_path = Path(path_str)

        # For skills, the path points to directory; read SKILL.md instead
        if file_path.is_dir():
            skill_md = file_path / 'SKILL.md'
            if skill_md.exists():
                file_path = skill_md
            else:
                stats['excluded_count'] += 1
                continue

        try:
            content = file_path.read_text()
        except (OSError, UnicodeDecodeError):
            stats['excluded_count'] += 1
            continue

        # Include logic: if patterns specified, must match at least one
        if include_patterns and not matches_any_content_pattern(content, include_patterns):
            stats['excluded_count'] += 1
            continue

        # Exclude logic: if matches any exclude pattern, skip
        if exclude_patterns and matches_any_content_pattern(content, exclude_patterns):
            stats['excluded_count'] += 1
            continue

        result.append(r)
        stats['matched_count'] += 1

    return result, stats


VALID_RESOURCE_TYPES = ('agents', 'commands', 'skills', 'scripts', 'tests')


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
    bundle_dir: Path,
    include: dict[str, bool],
    include_descriptions: bool,
    name_patterns: list[str],
    full: bool = False,
    content_include: list[str] | None = None,
    content_exclude: list[str] | None = None,
    include_tests: bool = False,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Process a single bundle directory and return its data.

    Returns:
        Tuple of (bundle_data, content_filter_stats)
        content_filter_stats has keys: input_count, matched_count, excluded_count
    """
    bundle_name = _extract_bundle_name(bundle_dir)
    bundle: dict[str, Any] = {'name': bundle_name, 'path': safe_relative_path(bundle_dir)}

    # Discover and filter resources
    agents = discover_agents(bundle_dir, include_descriptions, full) if include['agents'] else []
    commands = discover_commands(bundle_dir, include_descriptions, full) if include['commands'] else []
    skills = (
        discover_skills(bundle_dir, include_descriptions, full, content_include, content_exclude)
        if include['skills']
        else []
    )
    scripts = discover_scripts(bundle_dir, bundle_name) if include['scripts'] else []
    tests = discover_tests(bundle_name) if include_tests and include.get('tests', True) else []

    # Apply name pattern filter
    bundle['agents'] = filter_resources_by_pattern(agents, name_patterns)
    bundle['commands'] = filter_resources_by_pattern(commands, name_patterns)
    bundle['skills'] = filter_resources_by_pattern(skills, name_patterns)
    bundle['scripts'] = filter_resources_by_pattern(scripts, name_patterns)
    bundle['tests'] = filter_resources_by_pattern(tests, name_patterns)

    # Track content filter stats
    total_stats = {'input_count': 0, 'matched_count': 0, 'excluded_count': 0}

    # Apply content pattern filters (requires paths - enabled by --include-descriptions or --full)
    if content_include or content_exclude:
        inc = content_include or []
        exc = content_exclude or []

        # Filter agents
        bundle['agents'], stats = filter_resources_by_content(bundle['agents'], inc, exc)
        total_stats['input_count'] += stats['input_count']
        total_stats['matched_count'] += stats['matched_count']
        total_stats['excluded_count'] += stats['excluded_count']

        # Filter commands
        bundle['commands'], stats = filter_resources_by_content(bundle['commands'], inc, exc)
        total_stats['input_count'] += stats['input_count']
        total_stats['matched_count'] += stats['matched_count']
        total_stats['excluded_count'] += stats['excluded_count']

        # Filter skills
        bundle['skills'], stats = filter_resources_by_content(bundle['skills'], inc, exc)
        total_stats['input_count'] += stats['input_count']
        total_stats['matched_count'] += stats['matched_count']
        total_stats['excluded_count'] += stats['excluded_count']

        # Note: Scripts are NOT content-filtered (they're Python/Bash, not markdown)
        # Just track their counts for completeness
        total_stats['input_count'] += len(bundle['scripts'])
        total_stats['matched_count'] += len(bundle['scripts'])

    return bundle, total_stats


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
    lines.append(f'scope: {data["scope"]}')
    lines.append(f'base_path: {data["base_path"]}')

    # Add content filter info if present
    if data.get('content_pattern'):
        lines.append(f'content_pattern: "{data["content_pattern"]}"')
    if data.get('content_exclude'):
        lines.append(f'content_exclude: "{data["content_exclude"]}"')
    if data.get('content_filter_stats'):
        stats = data['content_filter_stats']
        lines.append('content_filter_stats:')
        lines.append(f'  input_count: {stats["input_count"]}')
        lines.append(f'  matched_count: {stats["matched_count"]}')
        lines.append(f'  excluded_count: {stats["excluded_count"]}')

    lines.append('')

    for bundle in data['bundles']:
        bundle_name = bundle['name']
        lines.append(f'{bundle_name}:')
        lines.append(f'  path: {bundle["path"]}')

        for resource_type in ['agents', 'commands', 'skills', 'scripts', 'tests']:
            items = bundle.get(resource_type, [])
            if items:
                lines.append(f'  {resource_type}[{len(items)}]:')
                for item in items:
                    if full:
                        # Detailed format with frontmatter
                        lines.append(f'    - name: {item["name"]}')
                        if item.get('path'):
                            lines.append(f'      path: {item["path"]}')
                        if item.get('description'):
                            lines.append(f'      description: {item["description"]}')
                        if item.get('user_invocable') is not None:
                            lines.append(f'      user_invocable: {str(item["user_invocable"]).lower()}')
                        if item.get('allowed_tools'):
                            lines.append(f'      allowed_tools: [{", ".join(item["allowed_tools"])}]')
                        if item.get('model'):
                            lines.append(f'      model: {item["model"]}')
                        # Scripts have additional fields
                        if item.get('skill'):
                            lines.append(f'      skill: {item["skill"]}')
                        if item.get('notation'):
                            lines.append(f'      notation: {item["notation"]}')
                        if item.get('type'):
                            lines.append(f'      type: {item["type"]}')
                        # Skill subdirectories
                        for subdir_name in [
                            'standards',
                            'templates',
                            'references',
                            'knowledge',
                            'examples',
                            'documents',
                        ]:
                            if item.get(subdir_name):
                                subdir_files = item[subdir_name]
                                lines.append(f'      {subdir_name}[{len(subdir_files)}]:')
                                for file_name in subdir_files:
                                    lines.append(f'        - {file_name}')
                    else:
                        # Simple format - just names
                        lines.append(f'    - {item["name"]}')
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
        f'scope: {output["scope"]}',
        f'base_path: {output["base_path"]}',
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
        '--content-pattern',
        default='',
        help='Include only files matching content pattern(s). Regex, pipe-separated for multiple (OR logic).',
    )
    parser.add_argument(
        '--content-exclude',
        default='',
        help='Exclude files matching content pattern(s). Regex, pipe-separated for multiple (OR logic).',
    )
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
    parser.add_argument(
        '--include-tests',
        action='store_true',
        help='Include test files from test/{bundle-name}/ directories. Adds tests resource type.',
    )
    parser.add_argument(
        '--include-project-skills',
        action='store_true',
        help='Include project-level skills from .claude/skills/. Adds project-skills pseudo-bundle.',
    )

    args = parser.parse_args()

    # Parse name patterns (pipe-separated for multiple patterns)
    name_patterns = [p.strip() for p in args.name_pattern.split('|') if p.strip()] if args.name_pattern else []

    # Parse content patterns (pipe-separated for multiple regex patterns)
    content_include = [p.strip() for p in args.content_pattern.split('|') if p.strip()] if args.content_pattern else []
    content_exclude = [p.strip() for p in args.content_exclude.split('|') if p.strip()] if args.content_exclude else []

    # Content filtering requires paths - enforce --include-descriptions or --full
    if (content_include or content_exclude) and not (args.include_descriptions or args.full):
        print('ERROR: --content-pattern/--content-exclude require --include-descriptions or --full', file=sys.stderr)
        return 1

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
    bundles_data = []
    total_content_stats = {'input_count': 0, 'matched_count': 0, 'excluded_count': 0}
    for bundle_dir in bundle_dirs:
        bundle, stats = process_bundle(
            bundle_dir,
            include,
            args.include_descriptions,
            name_patterns,
            args.full,
            content_include,
            content_exclude,
            args.include_tests,
        )
        bundles_data.append(bundle)
        total_content_stats['input_count'] += stats['input_count']
        total_content_stats['matched_count'] += stats['matched_count']
        total_content_stats['excluded_count'] += stats['excluded_count']

    # Add project-skills pseudo-bundle if requested
    if args.include_project_skills:
        project_skills = discover_project_skills()
        if project_skills:
            # Apply bundle filter if specified
            if not bundle_filter or 'project-skills' in bundle_filter:
                # Apply name pattern filter
                project_skills['skills'] = filter_resources_by_pattern(project_skills['skills'], name_patterns)
                project_skills['scripts'] = filter_resources_by_pattern(project_skills['scripts'], name_patterns)
                bundles_data.append(project_skills)

    # Calculate totals
    total_agents = sum(len(b.get('agents', [])) for b in bundles_data)
    total_commands = sum(len(b.get('commands', [])) for b in bundles_data)
    total_skills = sum(len(b.get('skills', [])) for b in bundles_data)
    total_scripts = sum(len(b.get('scripts', [])) for b in bundles_data)
    total_tests = sum(len(b.get('tests', [])) for b in bundles_data)

    # Output structure (bundles remain as list internally, serialization handles format)
    output: dict[str, Any] = {
        'scope': args.scope,
        'base_path': str(base_path),
        'bundles': bundles_data,
        'statistics': {
            'total_bundles': len(bundles_data),
            'total_agents': total_agents,
            'total_commands': total_commands,
            'total_skills': total_skills,
            'total_scripts': total_scripts,
            'total_tests': total_tests,
            'total_resources': total_agents + total_commands + total_skills + total_scripts + total_tests,
        },
    }

    # Add content filter stats if content filtering was used
    if content_include or content_exclude:
        output['content_filter_stats'] = total_content_stats
        if content_include:
            output['content_pattern'] = '|'.join(content_include)
        if content_exclude:
            output['content_exclude'] = '|'.join(content_exclude)

    if args.direct_result:
        # Direct mode: output to stdout (for small results or piped usage)
        if args.format == 'json':
            import json

            # For JSON, convert bundles list to dict keyed by name
            json_output = {
                'status': 'success',
                'scope': output['scope'],
                'base_path': output['base_path'],
                'bundles': {b['name']: {k: v for k, v in b.items() if k != 'name'} for b in bundles_data},
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
