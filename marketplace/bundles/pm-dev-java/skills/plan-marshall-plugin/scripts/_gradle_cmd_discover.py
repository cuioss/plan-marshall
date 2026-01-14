#!/usr/bin/env python3
"""Gradle module discovery command.

Discovers Gradle modules with complete metadata using Gradle commands
and file system analysis. Implements the discover_modules() contract
from build-project-structure.md.

Data Sources:
    FROM GRADLE (resolved/inherited):
        - coordinates: group, version, name from properties task
        - dependencies: via dependencies task (resolved with scopes)
        - quality tasks: via tasks --group="verification"
    FROM BUILD.GRADLE (local only - fallback):
        - description: if not available from properties
        - archivesBaseName: for artifact naming override

IMPORTANT: Uses Gradle commands per build-project-structure.md specification:
- properties for coordinates (group, version, name, description)
- dependencies for dependency tree
Both are combined where possible to minimize Gradle daemon startup overhead.

Usage:
    python3 gradle_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to build-project-structure.md contract.
"""

import argparse
import json
import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from extension_base import find_readme
from plan_logging import log_entry

# =============================================================================
# Constants
# =============================================================================

BUILD_GRADLE = 'build.gradle'
BUILD_GRADLE_KTS = 'build.gradle.kts'
SETTINGS_GRADLE = 'settings.gradle'
SETTINGS_GRADLE_KTS = 'settings.gradle.kts'

# JVM languages and their file extensions
JVM_LANGUAGES = ['java', 'kotlin', 'groovy', 'scala']
JVM_EXTENSIONS = {
    'java': '*.java',
    'kotlin': '*.kt',
    'groovy': '*.groovy',
    'scala': '*.scala',
}

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


def discover_gradle_modules(project_root: str) -> list:
    """Discover all Gradle modules with complete metadata.

    Uses Gradle commands to extract metadata, with file system analysis
    as fallback when Gradle execution fails.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to build-project-structure.md contract.
    """
    root = Path(project_root).resolve()
    modules = []
    log_entry('script', 'global', 'INFO', f'[GRADLE-DISCOVER] Starting discovery in {project_root}')

    # Check for settings.gradle to determine project structure
    settings_path = None
    for sf in [SETTINGS_GRADLE_KTS, SETTINGS_GRADLE]:
        if (root / sf).exists():
            settings_path = root / sf
            break

    # Get quality tasks once for the whole project
    quality_tasks = _get_quality_tasks(root)

    # Always check for root module first
    for bf in [BUILD_GRADLE_KTS, BUILD_GRADLE]:
        if (root / bf).exists():
            gradle_data = _get_gradle_metadata('', root)
            module_data = _extract_gradle_module(root, root, '', gradle_data, quality_tasks)
            if module_data:
                modules.append(module_data)
            break

    # Then add submodules from settings.gradle
    if settings_path:
        content = settings_path.read_text()
        for match in re.finditer(r'include\s*[(\'"]+:?([^)\'\"]+)[)\'"]+', content):
            module_name = match.group(1).replace(':', '/')
            module_path = root / module_name
            if module_path.exists():
                gradle_data = _get_gradle_metadata(module_name, root)
                module_data = _extract_gradle_module(module_path, root, module_name, gradle_data, quality_tasks)
                if module_data:
                    modules.append(module_data)

    log_entry('script', 'global', 'INFO', f'[GRADLE-DISCOVER] Discovered {len(modules)} modules')
    return modules


# =============================================================================
# Gradle Command Execution
# =============================================================================


def _get_gradle_metadata(module_path: str, project_root: Path) -> dict | None:
    """Get metadata using Gradle properties and dependencies commands.

    Per build-project-structure.md specification, runs Gradle commands
    to extract resolved metadata rather than parsing build.gradle directly.

    Args:
        module_path: Module path relative to root (empty string for root module)
        project_root: Project root directory

    Returns:
        Dict with group_id, name, version, description, dependencies, or None if fails
    """
    from _gradle_execute import execute_direct

    # Build module prefix for Gradle task addressing
    module_prefix = f':{module_path.replace("/", ":")}' if module_path else ''

    # Run properties task to get coordinates
    props_result = execute_direct(
        args=f'{module_prefix}:properties -q',
        command_key='gradle:discover-properties',
        default_timeout=120,
        project_dir=str(project_root),
    )

    if props_result['status'] != 'success':
        return None

    # Read output from log file
    log_content = Path(props_result['log_file']).read_text() if props_result.get('log_file') else ''
    metadata = _parse_properties_output(log_content)

    # Run dependencies task
    deps_result = execute_direct(
        args=f'{module_prefix}:dependencies --configuration compileClasspath -q',
        command_key='gradle:discover-dependencies',
        default_timeout=120,
        project_dir=str(project_root),
    )

    if deps_result['status'] == 'success':
        # Read output from log file
        deps_log_content = Path(deps_result['log_file']).read_text() if deps_result.get('log_file') else ''
        metadata['dependencies'] = _parse_dependencies_output(deps_log_content)
    else:
        metadata['dependencies'] = []

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

    Uses Gradle command data when available, falls back to file system analysis.

    Args:
        module_path: Path to module directory
        project_root: Project root path
        relative_path: Path relative to project root ("" for root module)
        gradle_data: Metadata from Gradle commands (None if commands failed)
        quality_tasks: List of detected quality task names

    Returns:
        Module dict conforming to build-project-structure.md or None
    """
    build_file = None
    for bf in [BUILD_GRADLE_KTS, BUILD_GRADLE]:
        if (module_path / bf).exists():
            build_file = module_path / bf
            break

    if not build_file:
        return None

    # Root module is always named "default"
    is_root_module = not relative_path or relative_path == '.'

    # Get name - root is "default", submodules use Gradle data or directory name
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

    # Source directories
    sources = _discover_sources(module_path)
    source_paths = [f'{relative_path}/{s}' if relative_path else s for s in sources['main']]
    test_paths = [f'{relative_path}/{t}' if relative_path else t for t in sources['test']]

    # README
    readme = find_readme(str(module_path))
    readme_path = f'{relative_path}/{readme}' if readme and relative_path else readme

    # Stats
    source_files = _count_source_files(module_path, sources['main'])
    test_files = _count_source_files(module_path, sources['test'])

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
                'module': relative_path if relative_path else '.',
                'descriptor': f'{relative_path}/{build_file.name}' if relative_path else build_file.name,
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
        'packages': {},
        'dependencies': dependencies,
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


# =============================================================================
# Source Discovery
# =============================================================================


def _discover_sources(module_path: Path) -> dict:
    """Discover source directories for all JVM languages.

    Checks for Java, Kotlin, Groovy, and Scala source directories.

    Returns:
        Dict with main and test source directories
    """
    sources: dict[str, list[str]] = {'main': [], 'test': []}

    for lang in JVM_LANGUAGES:
        main_dir = module_path / 'src' / 'main' / lang
        test_dir = module_path / 'src' / 'test' / lang
        if main_dir.exists():
            sources['main'].append(f'src/main/{lang}')
        if test_dir.exists():
            sources['test'].append(f'src/test/{lang}')

    return sources


def _count_source_files(module_path: Path, source_dirs: list) -> int:
    """Count JVM source files (Java, Kotlin, Groovy, Scala) in source directories."""
    count = 0
    for src in source_dirs:
        src_path = module_path / src
        if src_path.exists():
            # Determine language from path (e.g., src/main/kotlin -> kotlin)
            lang = Path(src).name
            if lang in JVM_EXTENSIONS:
                count += len(list(src_path.rglob(JVM_EXTENSIONS[lang])))
            else:
                # Fallback: count all known JVM files
                for ext in JVM_EXTENSIONS.values():
                    count += len(list(src_path.rglob(ext)))
    return count


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
        relative_path: Path relative to project root ("" for root module)
        quality_tasks: List of detected quality task names
    """
    base = 'python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:gradle run'

    # For Gradle, embed module as :module:task prefix in commandArgs
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
        'clean': f'{base} --commandArgs "{_tasks("clean")}"',
        # quality-gate: uses check (static analysis, linting) - NOT build
        'quality-gate': f'{base} --commandArgs "{_tasks(quality_target)}"',
        # verify: full build including tests
        'verify': f'{base} --commandArgs "{_tasks("build")}"',
        # install/deploy commands
        'install': f'{base} --commandArgs "{_tasks("publishToMavenLocal")}"',
        'clean-install': f'{base} --commandArgs "{_tasks("clean publishToMavenLocal")}"',
        'package': f'{base} --commandArgs "{_tasks("jar")}"',
    }

    # Source-conditional: compile
    if has_sources:
        commands['compile'] = f'{base} --commandArgs "{_tasks("classes")}"'

    # Test-conditional: test-compile, module-tests
    if has_tests:
        commands['test-compile'] = f'{base} --commandArgs "{_tasks("testClasses")}"'
        commands['module-tests'] = f'{base} --commandArgs "{_tasks("test")}"'

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
