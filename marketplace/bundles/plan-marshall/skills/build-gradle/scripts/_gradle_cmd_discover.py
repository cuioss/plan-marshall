#!/usr/bin/env python3
"""Gradle module discovery command.

Discovers Gradle modules with complete metadata using Gradle commands
and file system analysis. Implements the discover_modules() contract
from module-discovery.md.

Data Sources:
    FROM GRADLE (resolved/inherited):
        - coordinates: group, version, name from properties task
        - dependencies: via dependencies task (resolved with scopes)
        - quality tasks: via tasks --group="verification"
    FROM BUILD.GRADLE (local only - fallback):
        - description: if not available from properties
        - archivesBaseName: for artifact naming override

IMPORTANT: Uses Gradle commands per module-discovery.md specification:
- properties for coordinates (group, version, name, description)
- dependencies for dependency tree
Both are combined where possible to minimize Gradle daemon startup overhead.

Usage:
    python3 gradle_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import argparse
import json
import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from extension_base import (
    count_source_files,
    discover_packages,
    discover_sources,
    find_readme,
)
from plan_logging import log_entry

# =============================================================================
# Constants
# =============================================================================

BUILD_GRADLE = 'build.gradle'
BUILD_GRADLE_KTS = 'build.gradle.kts'
SETTINGS_GRADLE = 'settings.gradle'
SETTINGS_GRADLE_KTS = 'settings.gradle.kts'

# Quality task patterns that indicate quality tooling
QUALITY_TASK_PATTERNS = {
    'spotlessCheck': 'spotless',
    'checkstyleMain': 'checkstyle',
    'pmdMain': 'pmd',
    'detekt': 'detekt',
    'ktlintCheck': 'ktlint',
}


# =============================================================================
# Module Discovery
# =============================================================================


def _find_gradle_descriptors(project_root: str) -> list[tuple[Path, str]]:
    """Find all Gradle build files via settings.gradle parsing.

    Returns list of (module_path, relative_path) tuples. The root module
    always comes first if it has a build file.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of (absolute_module_path, relative_path_from_root) tuples.
    """
    root = Path(project_root).resolve()
    descriptors: list[tuple[Path, str]] = []

    # Root module — check for build.gradle[.kts]
    for bf in [BUILD_GRADLE_KTS, BUILD_GRADLE]:
        if (root / bf).exists():
            descriptors.append((root, '.'))
            break

    # Submodules from settings.gradle
    settings_path = None
    for sf in [SETTINGS_GRADLE_KTS, SETTINGS_GRADLE]:
        if (root / sf).exists():
            settings_path = root / sf
            break

    if settings_path:
        content = settings_path.read_text()
        for match in re.finditer(r'include\s*[(\'"]+:?([^)\'\"]+)[)\'"]+', content):
            module_name = match.group(1).replace(':', '/')
            module_path = root / module_name
            if module_path.exists():
                # Verify it has a build file
                has_build = any((module_path / bf).exists() for bf in [BUILD_GRADLE_KTS, BUILD_GRADLE])
                if has_build:
                    descriptors.append((module_path, module_name))

    return descriptors


def discover_gradle_modules(project_root: str) -> list:
    """Discover all Gradle modules with complete metadata.

    Uses Gradle commands to extract metadata, with file system analysis
    as fallback when Gradle execution fails.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to module-discovery.md contract.
    """
    root = Path(project_root).resolve()
    modules = []
    log_entry('script', 'global', 'INFO', f'[GRADLE-DISCOVER] Starting discovery in {project_root}')

    # Get quality tasks once for the whole project
    quality_tasks = _get_quality_tasks(root)

    # Find all modules via settings.gradle + root build file
    descriptors = _find_gradle_descriptors(project_root)

    for module_path, relative_path in descriptors:
        gradle_data = _get_gradle_metadata(
            relative_path if relative_path != '.' else '', root
        )
        module_data = _extract_gradle_module(module_path, root, relative_path, gradle_data, quality_tasks)
        if module_data:
            modules.append(module_data)

    log_entry('script', 'global', 'INFO', f'[GRADLE-DISCOVER] Discovered {len(modules)} modules')
    return modules


# =============================================================================
# Gradle Command Execution
# =============================================================================


def _get_gradle_metadata(module_path: str, project_root: Path) -> dict | None:
    """Get metadata using a single combined Gradle command.

    Combines properties and dependencies tasks in a single Gradle call
    to minimize daemon startup overhead (same approach as Maven discovery).

    Args:
        module_path: Module path relative to root (empty string for root module)
        project_root: Project root directory

    Returns:
        Dict with group_id, name, version, description, dependencies, or None if fails
    """
    from _gradle_execute import execute_direct

    # Build module prefix for Gradle task addressing
    module_prefix = f':{module_path.replace("/", ":")}' if module_path else ''

    # Run properties + dependencies in a single Gradle call
    result = execute_direct(
        args=f'{module_prefix}:properties {module_prefix}:dependencies --configuration compileClasspath -q',
        command_key='gradle:discover',
        default_timeout=120,
        project_dir=str(project_root),
    )

    if result['status'] != 'success':
        return None

    log_content = Path(result['log_file']).read_text() if result.get('log_file') else ''
    metadata = _parse_properties_output(log_content)
    metadata['dependencies'] = _parse_dependencies_output(log_content)

    return metadata


def _get_quality_tasks(project_root: Path) -> list:
    """Get verification tasks to detect quality tooling.

    Args:
        project_root: Project root directory

    Returns:
        List of quality task names (spotlessCheck, checkstyleMain, etc.)
    """
    from _gradle_execute import execute_direct

    result = execute_direct(
        args='tasks --group=verification -q',
        command_key='gradle:discover-tasks',
        default_timeout=120,
        project_dir=str(project_root),
    )

    if result['status'] != 'success':
        return []

    # Read output from log file
    log_content = Path(result['log_file']).read_text() if result.get('log_file') else ''

    tasks = []
    for line in log_content.split('\n'):
        # Task lines are like: "spotlessCheck - Checks that sourcecode..."
        match = re.match(r'^(\w+)\s+-\s+', line)
        if match:
            task_name = match.group(1)
            if task_name in QUALITY_TASK_PATTERNS:
                tasks.append(task_name)

    return tasks


def _parse_properties_output(log_content: str) -> dict:
    """Parse Gradle properties output for metadata.

    Output format:
        group: com.example
        name: my-module
        version: 1.0.0
        description: My module description

    Args:
        log_content: Content of Gradle properties output

    Returns:
        Dict with group_id, name, version, description
    """
    metadata: dict[str, str | None] = {
        'group_id': None,
        'name': None,
        'version': None,
        'description': None,
    }

    for line in log_content.split('\n'):
        if line.startswith('group:'):
            value = line[6:].strip()
            if value and value != 'null':
                metadata['group_id'] = value
        elif line.startswith('name:'):
            value = line[5:].strip()
            if value and value != 'null':
                metadata['name'] = value
        elif line.startswith('version:'):
            value = line[8:].strip()
            if value and value not in ('null', 'unspecified'):
                metadata['version'] = value
        elif line.startswith('description:'):
            value = line[12:].strip()
            if value and value != 'null':
                metadata['description'] = value

    return metadata


def _parse_dependencies_output(log_content: str) -> list:
    r"""Parse Gradle dependencies output for direct dependencies.

    Output format (direct dependencies only - first level):
        compileClasspath - Compile classpath for source set 'main'.
        +--- org.springframework.boot:spring-boot-starter -> 3.0.0
        +--- project :lib-mrlonis-types
        \--- com.google.guava:guava:31.1-jre

    Args:
        log_content: Content of Gradle dependencies output

    Returns:
        List of dependency strings in format 'groupId:artifactId:scope'
    """
    dependencies = []

    # Match ONLY direct dependencies (first level with +- or \-)
    # Format: groupId:artifactId or groupId:artifactId:version or -> resolved_version
    pattern = r'^[+\\]--- ([^:\s]+):([^:\s]+)(?::([^\s]+))?(?:\s+->\s+(\S+))?'

    for line in log_content.split('\n'):
        line = line.strip()
        # Skip transitive dependencies (have | prefix)
        if '|' in line:
            continue
        # Skip project dependencies
        if 'project :' in line:
            # Extract inter-module dependencies
            proj_match = re.search(r'project :(\S+)', line)
            if proj_match:
                dependencies.append(f'project:{proj_match.group(1)}:compile')
            continue

        match = re.match(pattern, line)
        if match:
            group_id = match.group(1)
            artifact_id = match.group(2)
            # Scope is always 'compile' for compileClasspath
            dependencies.append(f'{group_id}:{artifact_id}:compile')

    return dependencies


# =============================================================================
# Module Extraction
# =============================================================================


def _extract_gradle_module(
    module_path: Path, project_root: Path, relative_path: str, gradle_data: dict | None, quality_tasks: list
) -> dict | None:
    """Extract Gradle module with contract-compliant structure.

    Uses shared discovery utilities from extension-api for source directories,
    file counting, and package discovery. Gradle command data provides
    coordinates and dependencies.

    Args:
        module_path: Path to module directory
        project_root: Project root path
        relative_path: Path relative to project root ("." for root module)
        gradle_data: Metadata from Gradle commands (None if commands failed)
        quality_tasks: List of detected quality task names

    Returns:
        Module dict conforming to module-discovery.md or None
    """
    build_file = None
    for bf in [BUILD_GRADLE_KTS, BUILD_GRADLE]:
        if (module_path / bf).exists():
            build_file = module_path / bf
            break

    if not build_file:
        return None

    # Determine if root module
    is_root_module = relative_path == '.' or not relative_path
    rel_path_str = relative_path if not is_root_module else '.'

    # Get name — use build_module_base for root module naming convention
    if is_root_module:
        name = 'default'
    elif gradle_data and gradle_data.get('name'):
        name = gradle_data['name']
    else:
        name = module_path.name
        # Check for archivesBaseName override in build file
        content = build_file.read_text()
        match = re.search(r'archivesBaseName\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        if match:
            name = match.group(1)

    # If Gradle commands failed, return error-only structure
    if not gradle_data:
        return {
            'name': name,
            'build_systems': ['gradle'],
            'error': 'Unable to retrieve metadata - Gradle commands failed (incompatible Gradle/Java version)',
        }

    # Get metadata from Gradle
    group_id = gradle_data.get('group_id')
    description = gradle_data.get('description')
    dependencies = gradle_data.get('dependencies', [])

    # Shared source discovery (multi-language + resources)
    sources = discover_sources(module_path)
    prefix = relative_path if not is_root_module else ''
    source_paths = [f'{prefix}/{s}' if prefix else s for s in sources['main']]
    test_paths = [f'{prefix}/{t}' if prefix else t for t in sources['test']]

    # README via shared utility
    readme = find_readme(str(module_path))
    readme_path = f'{prefix}/{readme}' if readme and prefix else readme

    # Packages via shared discovery (parity with Maven discovery)
    rel = prefix if prefix else ''
    packages = discover_packages(module_path, sources.get('main', []), rel)
    test_packages = discover_packages(module_path, sources.get('test', []), rel)

    # Stats via shared counting
    source_files = count_source_files(module_path, sources['main'])
    test_files = count_source_files(module_path, sources['test'])

    # Commands
    commands = _build_commands(
        module_name=name,
        has_sources=source_files > 0,
        has_tests=test_files > 0,
        relative_path=relative_path,
        quality_tasks=quality_tasks,
    )

    return {
        'name': name,
        'build_systems': ['gradle'],
        'paths': {
            k: v
            for k, v in {
                'module': rel_path_str,
                'descriptor': f'{prefix}/{build_file.name}' if prefix else build_file.name,
                'sources': source_paths if source_paths else None,
                'tests': test_paths if test_paths else None,
                'readme': readme_path,
            }.items()
            if v is not None
        },
        'metadata': {
            k: v
            for k, v in {
                'artifact_id': name,
                'group_id': group_id,
                'packaging': 'jar',
                'description': description,
            }.items()
            if v is not None
        },
        'packages': packages,
        'test_packages': test_packages,
        'dependencies': dependencies,
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


# =============================================================================
# Commands
# =============================================================================


def _build_commands(
    module_name: str, has_sources: bool, has_tests: bool, relative_path: str, quality_tasks: list
) -> dict:
    """Build commands object with resolved canonical command strings.

    Resolution rules per canonical-commands.md:
    - Always: clean (separate), verify, install, clean-install, package
    - Always: quality-gate (uses check task, enhanced with spotless/checkstyle if detected)
    - Source-conditional: compile
    - Test-conditional: test-compile, module-tests

    Note: clean is a separate command. Other commands do NOT include clean goal.
    Use clean-install for the combined clean + install workflow.

    Args:
        module_name: Module name or directory name
        has_sources: Whether module has source files
        has_tests: Whether module has test files
        relative_path: Path relative to project root ("." or "" for root module)
        quality_tasks: List of detected quality task names
    """
    base = 'python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run'

    # For Gradle, embed module as :module:task prefix in command-args
    is_root_module = not relative_path or relative_path == '.'
    task_prefix = '' if is_root_module else f':{module_name}:'

    def _tasks(tasks: str) -> str:
        """Prefix each task with module path for submodules."""
        if not task_prefix:
            return tasks
        # Handle multiple tasks: "clean build" -> ":module:clean :module:build"
        return ' '.join(f'{task_prefix}{t}' for t in tasks.split())

    # Determine quality-gate task
    # Default to 'check' which is Gradle's standard verification task
    # If quality plugins detected, use their check tasks
    quality_target = 'check'
    if 'spotlessCheck' in quality_tasks:
        quality_target = 'spotlessCheck check'
    elif 'checkstyleMain' in quality_tasks:
        quality_target = 'checkstyleMain check'

    commands = {
        # Always: clean (separate)
        'clean': f'{base} --command-args "{_tasks("clean")}"',
        # quality-gate: uses check (static analysis, linting) - NOT build
        'quality-gate': f'{base} --command-args "{_tasks(quality_target)}"',
        # verify: full build including tests
        'verify': f'{base} --command-args "{_tasks("build")}"',
        # install/deploy commands
        'install': f'{base} --command-args "{_tasks("publishToMavenLocal")}"',
        'clean-install': f'{base} --command-args "{_tasks("clean publishToMavenLocal")}"',
        'package': f'{base} --command-args "{_tasks("jar")}"',
    }

    # Source-conditional: compile
    if has_sources:
        commands['compile'] = f'{base} --command-args "{_tasks("classes")}"'

    # Test-conditional: test-compile, module-tests
    if has_tests:
        commands['test-compile'] = f'{base} --command-args "{_tasks("testClasses")}"'
        commands['module-tests'] = f'{base} --command-args "{_tasks("test")}"'

    return commands


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Gradle module discovery')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # discover subcommand
    discover_parser = subparsers.add_parser('discover', help='Discover Gradle modules')
    discover_parser.add_argument('--root', required=True, help='Project root directory')
    discover_parser.add_argument('--format', choices=['json'], default='json', help='Output format')

    args = parser.parse_args()

    if args.command == 'discover':
        modules = discover_gradle_modules(args.root)
        print(json.dumps(modules, indent=2))


if __name__ == '__main__':
    main()
