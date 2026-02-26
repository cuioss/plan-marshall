#!/usr/bin/env python3
"""Maven module discovery command.

Discovers Maven modules with complete metadata using Maven commands
and file system analysis. Implements the discover_modules() contract
from build-project-structure.md.

Data Sources:
    FROM MAVEN (resolved/inherited):
        - coordinates: groupId:artifactId:packaging from dependency:tree header
        - profiles: via help:all-profiles (includes parent POM profiles)
        - dependencies: via dependency:tree (resolved with scopes)
    FROM POM.XML (local only - exceptional cases):
        - description: optional, rarely inherited
        - parent: GAV reference (not available in dependency:tree)

IMPORTANT: Uses Maven commands per build-project-structure.md specification:
- help:all-profiles for profiles (includes inherited from parent POMs)
- dependency:tree for dependencies AND coordinates (resolved)
Both are combined in a single Maven call per module to minimize JVM startup overhead.

Usage:
    python3 maven_cmd_discover.py discover --root /path/to/project [--format json]

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
    Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'extension-api' / 'scripts'
)
if str(EXTENSION_API_DIR) not in sys.path:
    sys.path.insert(0, str(EXTENSION_API_DIR))

from extension_base import PROFILE_PATTERNS, build_module_base, discover_descriptors  # noqa: E402

# =============================================================================
# Extension Defaults Keys (for config_defaults callback)
# =============================================================================
# These constants define configuration keys stored in run-configuration.json
# via the config_defaults callback. Extensions use these to set project-specific
# defaults that influence profile parsing and command generation.
#
# See: plan-marshall:extension-api:standards/config-callback.md
# See: pm-dev-java:plan-marshall-plugin:standards/maven-impl.md

# Key: build.maven.profiles.skip
# Value: Comma-separated list of profile names to ignore during discovery
# Example: "itest,native,jfr"
# Effect: Profiles in this list are excluded from command generation
EXT_KEY_PROFILES_SKIP = 'build.maven.profiles.skip'

# Key: build.maven.profiles.map.canonical
# Value: Comma-separated list of profile:canonical mappings
# Example: "pre-commit:quality-gate,coverage:coverage,javadoc:javadoc"
# Format: profile1:canonical1,profile2:canonical2,...
# Effect: Maps profile IDs to canonical command names during discovery
EXT_KEY_PROFILES_MAP = 'build.maven.profiles.map.canonical'


# =============================================================================
# Module Discovery
# =============================================================================


def discover_maven_modules(project_root: str) -> list:
    """Discover all Maven modules with complete metadata.

    Uses discover_descriptors from base library to find all pom.xml files,
    then gets metadata from Maven (not pom.xml parsing).

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts conforming to build-project-structure.md contract.
    """
    root = Path(project_root).resolve()

    # Use base library to find all pom.xml files
    descriptors = discover_descriptors(project_root, 'pom.xml')

    modules = []
    for pom_path in descriptors:
        # Build base module info from descriptor
        base = build_module_base(project_root, str(pom_path))

        # Get all metadata from Maven (coordinates, profiles, dependencies)
        maven_data = _get_maven_metadata(pom_path.parent, root)

        # Skip if Maven failed (no fallback - requires Maven for correct data)
        if maven_data is None:
            continue

        # Build complete module data
        module_data = _build_module(base, pom_path, root, maven_data)
        if module_data:
            modules.append(module_data)

    return modules


# =============================================================================
# Module Building
# =============================================================================


def _build_module(base, pom_path: Path, project_root: Path, maven_data: dict) -> dict | None:
    """Build complete module dict from base info and Maven data.

    Args:
        base: ModuleBase from build_module_base
        pom_path: Path to pom.xml file
        project_root: Project root path
        maven_data: Dict with coordinates, profiles, dependencies from Maven

    Returns:
        Complete module dict conforming to build-project-structure.md
    """
    module_path = pom_path.parent
    relative_path = base.paths.module

    # Get metadata from Maven output
    artifact_id = maven_data.get('artifact_id') or base.name
    group_id = maven_data.get('group_id')
    packaging = maven_data.get('packaging') or 'jar'
    profiles = maven_data.get('profiles', [])
    dependencies = maven_data.get('dependencies', [])

    # Description from pom.xml (per spec: "description is optional - parse from pom.xml if present")
    description = _get_description(pom_path)

    # Source directories
    sources = _discover_sources(module_path)
    source_paths = [f'{relative_path}/{s}' if relative_path != '.' else s for s in sources['main']]
    test_paths = [f'{relative_path}/{t}' if relative_path != '.' else t for t in sources['test']]

    # Packages
    rel = relative_path if relative_path != '.' else ''
    packages = _discover_packages(module_path, sources, rel)
    test_packages = _discover_test_packages(module_path, sources, rel)

    # Stats
    source_files = _count_java_files(module_path, sources['main'])
    test_files = _count_java_files(module_path, sources['test'])

    # Commands
    commands = _build_commands(
        module_name=artifact_id,
        packaging=packaging,
        has_sources=source_files > 0,
        has_tests=test_files > 0,
        profiles=profiles,
        relative_path=relative_path,
    )

    # Build metadata - omit profiles if empty
    metadata = {
        'artifact_id': artifact_id,
        'group_id': group_id,
        'packaging': packaging,
        'description': description,
        'parent': maven_data.get('parent'),
    }
    if profiles:
        metadata['profiles'] = profiles

    return {
        'name': artifact_id,
        'build_systems': ['maven'],
        'paths': {
            'module': relative_path,
            'descriptor': base.paths.descriptor,
            'sources': source_paths,
            'tests': test_paths,
            'readme': base.paths.readme,
        },
        'metadata': metadata,
        'packages': packages,
        'test_packages': test_packages,
        'dependencies': dependencies,
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


def _get_description(pom_path: Path) -> str | None:
    """Get description from pom.xml (per spec: parse from pom.xml if present)."""
    content = pom_path.read_text()
    # Skip description inside <parent> block
    content_no_parent = re.sub(r'<parent>.*?</parent>', '', content, flags=re.DOTALL)
    match = re.search(r'<description>([^<]+)</description>', content_no_parent)
    return match.group(1).strip() if match else None


def _get_parent(pom_path: Path) -> str | None:
    """Get parent GAV from pom.xml (not available in dependency:tree).

    Returns:
        Parent reference as 'groupId:artifactId' or None
    """
    content = pom_path.read_text()
    # Extract <parent> block
    parent_match = re.search(r'<parent>(.*?)</parent>', content, flags=re.DOTALL)
    if not parent_match:
        return None

    parent_block = parent_match.group(1)
    group_match = re.search(r'<groupId>([^<]+)</groupId>', parent_block)
    artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', parent_block)

    if group_match and artifact_match:
        return f'{group_match.group(1).strip()}:{artifact_match.group(1).strip()}'
    return None


# =============================================================================
# Maven Output Parsing
# =============================================================================


def _parse_coordinates_from_maven_output(log_content: str) -> dict:
    """Parse project coordinates from Maven dependency:tree header.

    Header format (first line after [INFO] --- dependency:tree):
        [INFO] groupId:artifactId:packaging:version

    Example:
        [INFO] de.cuioss:cui-http:jar:1.0-SNAPSHOT

    Args:
        log_content: Content of Maven log file

    Returns:
        Dict with artifact_id, group_id, packaging (empty dict if not found)
    """
    # Find the dependency:tree header line
    # Format: [INFO] groupId:artifactId:packaging:version
    # This is the first non-empty [INFO] line after dependency:tree starts
    # It does NOT have +- or \- prefix (those are dependencies)
    pattern = r'\[INFO\] ([^:\s]+):([^:\s]+):([^:\s]+):([^:\s\n]+)\s*$'

    for line in log_content.split('\n'):
        # Skip dependency lines (have +- or \- prefix)
        if '[INFO] +-' in line or '[INFO] \\-' in line or '[INFO] |' in line:
            continue
        # Skip empty or non-coordinate lines
        match = re.match(pattern, line)
        if match:
            return {
                'group_id': match.group(1),
                'artifact_id': match.group(2),
                'packaging': match.group(3),
                # version = match.group(4) - not needed per spec
            }

    return {}


# =============================================================================
# Profile Extraction (via Maven help:all-profiles)
# =============================================================================

# PROFILE_PATTERNS imported above from extension_base for canonical classification


def _get_maven_metadata(module_path: Path, project_root: Path) -> dict | None:
    """Get coordinates, profiles and dependencies using Maven commands.

    Per build-project-structure.md specification, runs:
        ./mvnw help:all-profiles dependency:tree -DoutputType=text

    This combines both commands in a single JVM startup for efficiency.
    Coordinates are parsed from dependency:tree header line:
        [INFO] groupId:artifactId:packaging:version

    Note: The timeout system enforces a minimum of 120 seconds to handle
    cold JVM startup times properly.

    Args:
        module_path: Path to module directory containing pom.xml
        project_root: Project root for Maven execution

    Returns:
        Dict with coordinates, profiles, dependencies, or None if Maven fails:
        {
            "artifact_id": str,
            "group_id": str,
            "packaging": str,
            "parent": str | None,  # from pom.xml (per spec)
            "profiles": list,
            "dependencies": list
        }
    """
    from _maven_execute import execute_direct

    pom_path = module_path / 'pom.xml'
    if not pom_path.exists():
        return None

    # Calculate relative pom.xml path from project root
    try:
        rel_pom = pom_path.relative_to(project_root)
    except ValueError:
        rel_pom = pom_path

    # Run Maven help:all-profiles + dependency:tree in single call
    # Per spec: "Single call: profiles + dependencies + resolved coordinates (one JVM startup)"
    # Use -N (non-recursive) to avoid reactor builds that mix up coordinates
    result = execute_direct(
        args=f'-N -f {rel_pom} help:all-profiles dependency:tree -DoutputType=text',
        command_key='maven:discover',
        default_timeout=120,  # Cold Maven startup can take time
        project_dir=str(project_root),
    )

    if result['status'] != 'success':
        return None  # Maven failed - no fallback

    log_file = Path(result['log_file'])
    if not log_file.exists():
        return None

    log_content = log_file.read_text()
    coordinates = _parse_coordinates_from_maven_output(log_content)
    raw_profiles = _parse_profiles_from_maven_output(log_content)
    dependencies = _parse_dependencies_from_maven_output(log_content)

    # Apply profile pipeline: parse -> filter command-line -> skip -> map
    profiles = _apply_profile_pipeline(raw_profiles, str(project_root))

    # Parent and description from pom.xml (per spec: not available in dependency:tree)
    parent = _get_parent(pom_path)

    return {
        'artifact_id': coordinates.get('artifact_id'),
        'group_id': coordinates.get('group_id'),
        'packaging': coordinates.get('packaging'),
        'parent': parent,
        'profiles': profiles,
        'dependencies': dependencies,
    }


def _apply_profile_pipeline(raw_profiles: list, project_root: str) -> list:
    """Apply the full profile processing pipeline.

    Pipeline stages:
    1. Filter to command-line activated profiles only (Active: false)
    2. Apply skip list from configuration
    3. Map to canonical command names

    Args:
        raw_profiles: Raw profiles from Maven output with is_active field
        project_root: Project root for configuration lookup

    Returns:
        List of processed profile dicts with id and canonical fields only
    """
    # Import directly - executor sets up PYTHONPATH for cross-skill imports
    from _config_core import ext_defaults_get
    from plan_logging import log_entry

    log_entry('script', 'global', 'INFO', f'[PROFILE-PIPELINE] called with {len(raw_profiles)} raw profiles')

    # 1. Filter to command-line only (Active: false)
    profiles = _filter_command_line_profiles(raw_profiles)
    log_entry('script', 'global', 'INFO', f'[PROFILE-PIPELINE] After command-line filter: {len(profiles)} profiles')

    # 2. Get skip list and mapping from configuration (if available)
    skip_list = None
    explicit_mapping = None

    skip_csv = ext_defaults_get(EXT_KEY_PROFILES_SKIP, project_root)
    if skip_csv:
        skip_list = [s.strip() for s in skip_csv.split(',')]
        log_entry('script', 'global', 'INFO', f'[PROFILE-PIPELINE] Loaded skip list from config: {skip_list}')
    else:
        log_entry('script', 'global', 'INFO', '[PROFILE-PIPELINE] No skip list configured in marshal.json')

    map_csv = ext_defaults_get(EXT_KEY_PROFILES_MAP, project_root)
    if map_csv:
        explicit_mapping = {}
        for pair in map_csv.split(','):
            if ':' in pair:
                profile_id, canonical = pair.split(':', 1)
                explicit_mapping[profile_id.strip()] = canonical.strip()
        log_entry(
            'script', 'global', 'INFO', f'[PROFILE-PIPELINE] Loaded explicit mapping from config: {explicit_mapping}'
        )
    else:
        log_entry(
            'script', 'global', 'INFO', '[PROFILE-PIPELINE] No explicit mapping configured in run-configuration.json'
        )

    # 3. Apply skip list
    before_skip = len(profiles)
    profiles = _filter_skip_profiles(profiles, skip_list)
    skipped_count = before_skip - len(profiles)
    if skipped_count > 0:
        log_entry('script', 'global', 'INFO', f'[PROFILE-PIPELINE] Filtered out {skipped_count} profiles via skip list')

    # 4. Map to canonical names
    profiles = _map_canonical_profiles(profiles, explicit_mapping)
    log_entry('script', 'global', 'INFO', f'[PROFILE-PIPELINE] Final profile count: {len(profiles)}')

    return profiles


def _parse_profiles_from_maven_output(log_content: str) -> list:
    """Parse raw profiles from Maven help:all-profiles output.

    Output format:
        Profile Id: coverage (Active: false, Source: pom)
        Profile Id: pre-commit (Active: false, Source: pom)

    Args:
        log_content: Content of Maven log file

    Returns:
        List of raw profile dicts with id and is_active fields.
        Further processing (filtering, mapping) is done by pipeline functions.
    """
    profiles = []

    # Match: Profile Id: <id> (Active: <bool>, Source: <source>)
    pattern = r'Profile Id:\s+(\S+)\s+\(Active:\s+(true|false),\s+Source:\s+(\S+)\)'

    for match in re.finditer(pattern, log_content):
        profile_id = match.group(1)
        is_active = match.group(2).lower() == 'true'
        # source = match.group(3)  # Not used in output

        profiles.append({'id': profile_id, 'is_active': is_active})

    return profiles


def _filter_command_line_profiles(raw_profiles: list) -> list:
    """Filter profiles to command-line activated only.

    Removes profiles that are default-activated (Active: true in Maven output).
    Only profiles with Active: false are kept - these require explicit -P activation.

    Args:
        raw_profiles: List of profile dicts with id and is_active fields

    Returns:
        List of profile dicts with is_active field removed
    """
    return [{'id': p['id']} for p in raw_profiles if not p.get('is_active', False)]


def _filter_skip_profiles(profiles: list, skip_list: list | None) -> list:
    """Filter out profiles in the skip list.

    Args:
        profiles: List of profile dicts with id field
        skip_list: List of profile IDs to exclude (None or empty keeps all)

    Returns:
        Filtered list of profile dicts
    """
    if not skip_list:
        return profiles

    # Normalize skip list entries (trim whitespace)
    skip_set = {s.strip() for s in skip_list}

    return [p for p in profiles if p['id'] not in skip_set]


def _map_canonical_profiles(profiles: list, explicit_mapping: dict | None) -> list:
    """Map profiles to canonical command names.

    Resolution order:
    1. Explicit mapping (from config) takes precedence
    2. PROFILE_PATTERNS aliases from extension_base.py

    Args:
        profiles: List of profile dicts with id field
        explicit_mapping: Dict mapping profile_id -> canonical (can be None)

    Returns:
        List of profile dicts with canonical field added
    """
    mapping = explicit_mapping or {}
    result = []

    for profile in profiles:
        profile_id = profile['id']

        # 1. Check explicit mapping first
        if profile_id in mapping:
            canonical = mapping[profile_id]
        else:
            # 2. Fall back to alias matching
            canonical = _classify_profile(profile_id)

        result.append({'id': profile_id, 'canonical': canonical})

    return result


def _parse_dependencies_from_maven_output(log_content: str) -> list:
    """Parse dependencies from Maven dependency:tree output.

    Output format (direct dependencies only - first level):
        [INFO] de.cuioss:cui-http:jar:1.0-SNAPSHOT
        [INFO] +- de.cuioss:cui-java-tools:jar:2.6.1:compile
        [INFO] +- org.projectlombok:lombok:jar:1.18.42:provided
        [INFO] \\- org.awaitility:awaitility:jar:4.3.0:test

    Transitive dependencies have indentation:
        [INFO] |  \\- org.hamcrest:hamcrest:jar:2.1:test

    Args:
        log_content: Content of Maven log file

    Returns:
        List of dependency strings in format 'groupId:artifactId:scope'
    """
    dependencies = []

    # Match ONLY direct dependencies (first level)
    # Direct deps have exactly "[INFO] +-" or "[INFO] \-" with no extra chars before +/\
    # Transitive deps have indentation like "[INFO] |  \-" or "[INFO]    \-"
    # Format: groupId:artifactId:type:version:scope
    pattern = r'\[INFO\] [+\\]- ([^:]+):([^:]+):([^:]+):([^:]+):(\S+)'

    for match in re.finditer(pattern, log_content):
        group_id = match.group(1)
        artifact_id = match.group(2)
        # type = match.group(3)  # jar, war, etc - not needed
        # version = match.group(4)  # not included per spec
        scope = match.group(5)

        dependencies.append(f'{group_id}:{artifact_id}:{scope}')

    return dependencies


def _classify_profile(profile_id: str) -> str:
    """Classify a profile ID to its canonical command name.

    Uses PROFILE_PATTERNS from extension_base.py which maps aliases to
    canonical command names. Only exact matches are supported - no substring
    or partial matching.

    Args:
        profile_id: The profile identifier (e.g., "pre-commit", "jacoco")

    Returns:
        Canonical command name (e.g., "quality-gate", "coverage") or "NO-MATCH-FOUND"
    """
    # PROFILE_PATTERNS is alias -> canonical (from extension_base.py)
    # Exact match required - no substring matching
    if profile_id in PROFILE_PATTERNS:
        return PROFILE_PATTERNS[profile_id]  # type: ignore[no-any-return]

    # Case-insensitive exact match
    profile_lower = profile_id.lower()
    for alias, canonical in PROFILE_PATTERNS.items():
        if alias.lower() == profile_lower:
            return canonical  # type: ignore[no-any-return]

    return 'NO-MATCH-FOUND'


# =============================================================================
# Source Discovery
# =============================================================================


def _discover_sources(module_path: Path) -> dict:
    """Discover source directories including resources.

    Returns both code and resources directories:
    - main: src/main/java, src/main/resources
    - test: src/test/java, src/test/resources
    """
    sources: dict[str, list[str]] = {'main': [], 'test': []}

    # Main sources
    if (module_path / 'src' / 'main' / 'java').exists():
        sources['main'].append('src/main/java')
    if (module_path / 'src' / 'main' / 'resources').exists():
        sources['main'].append('src/main/resources')

    # Test sources
    if (module_path / 'src' / 'test' / 'java').exists():
        sources['test'].append('src/test/java')
    if (module_path / 'src' / 'test' / 'resources').exists():
        sources['test'].append('src/test/resources')

    return sources


def _discover_packages_from_dirs(
    module_path: Path, source_dirs: list[str], relative_path: str
) -> dict:
    """Discover Java packages from a list of source directories.

    Returns dict keyed by package name with path, optional package_info,
    and optional files (sorted list of direct .java children).
    """
    packages = {}

    for source_dir in source_dirs:
        source_path = module_path / source_dir
        if not source_path.exists():
            continue

        seen = set()
        for java_file in source_path.rglob('*.java'):
            pkg_dir = java_file.parent
            pkg_name = str(pkg_dir.relative_to(source_path)).replace('/', '.').replace('\\', '.')

            # Skip root "." package - files directly in source root are not valid packages
            if pkg_name and pkg_name != '.' and pkg_name not in seen:
                seen.add(pkg_name)

                rel_path = str(pkg_dir.relative_to(module_path))
                if relative_path:
                    rel_path = f'{relative_path}/{rel_path}'

                pkg_info: dict[str, str | list[str]] = {'path': rel_path}

                # Check for package-info.java
                info_file = pkg_dir / 'package-info.java'
                if info_file.exists():
                    info_path = str(info_file.relative_to(module_path))
                    if relative_path:
                        info_path = f'{relative_path}/{info_path}'
                    pkg_info['package_info'] = info_path

                # List direct .java files (not recursive — sub-package files belong to their own entry)
                direct_files = sorted(
                    f.name for f in pkg_dir.iterdir()
                    if f.is_file() and f.suffix == '.java' and f.name != 'package-info.java'
                )
                if direct_files:
                    pkg_info['files'] = direct_files

                packages[pkg_name] = pkg_info

    return packages


def _discover_packages(module_path: Path, sources: dict, relative_path: str) -> dict:
    """Discover Java packages as dict keyed by package name."""
    return _discover_packages_from_dirs(module_path, sources.get('main', []), relative_path)


def _discover_test_packages(module_path: Path, sources: dict, relative_path: str) -> dict:
    """Discover Java test packages as dict keyed by package name."""
    return _discover_packages_from_dirs(module_path, sources.get('test', []), relative_path)


def _count_java_files(module_path: Path, source_dirs: list) -> int:
    """Count Java files in source directories."""
    count = 0
    for src in source_dirs:
        src_path = module_path / src
        if src_path.exists():
            count += len(list(src_path.rglob('*.java')))
    return count


# =============================================================================
# Commands
# =============================================================================


def _build_commands(
    module_name: str, packaging: str, has_sources: bool, has_tests: bool, profiles: list, relative_path: str
) -> dict:
    """Build commands object with resolved canonical command strings.

    Resolution rules:
    - Always (all modules): clean
    - Always (non-pom): verify, install, clean-install, quality-gate, package
    - Source-conditional: compile
    - Test-conditional: test-compile, module-tests
    - Profile-based: integration-tests, coverage, benchmark

    Note: clean is a separate command. Other commands do NOT include clean goal.
    Use clean-install for the combined clean + install workflow.

    Args:
        module_name: Module artifact ID or directory name
        packaging: Maven packaging type (jar, pom, etc.)
        has_sources: Whether module has source files
        has_tests: Whether module has test files
        profiles: List of profile dicts with id, canonical
        relative_path: Path relative to project root ("" or "." for root module)
    """
    base = 'python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run'
    commands = {}
    # Embed -pl in command-args for submodules, empty for root
    is_root_module = not relative_path or relative_path == '.'
    pl_arg = '' if is_root_module else f' -pl {module_name}'

    # 1. Always: clean (all modules including pom)
    commands['clean'] = f'{base} --command-args "clean{pl_arg}"'

    # 2. Always: quality-gate, verify, install (all modules including pom)
    commands['quality-gate'] = f'{base} --command-args "verify{pl_arg}"'
    commands['verify'] = f'{base} --command-args "verify{pl_arg}"'
    commands['install'] = f'{base} --command-args "install{pl_arg}"'

    # 3. Non-pom modules get additional commands
    if packaging != 'pom':
        commands['clean-install'] = f'{base} --command-args "clean install{pl_arg}"'
        commands['package'] = f'{base} --command-args "package{pl_arg}"'

        # 4. Source-conditional: compile
        if has_sources:
            commands['compile'] = f'{base} --command-args "compile{pl_arg}"'

        # 5. Test-conditional: test-compile, module-tests
        if has_tests:
            commands['test-compile'] = f'{base} --command-args "test-compile{pl_arg}"'
            commands['module-tests'] = f'{base} --command-args "test{pl_arg}"'

    # 6. Profile-based commands (integration-tests, coverage, benchmark)
    for profile in profiles or []:
        canonical = profile.get('canonical')
        profile_id = profile.get('id')

        if canonical and profile_id:
            # quality-gate enhancement with profile
            if canonical == 'quality-gate':
                cmd = _generate_profile_command(profile_id, module_name, relative_path)
                if cmd:
                    commands['quality-gate'] = cmd
            # Additional profile-based commands
            elif canonical in ['integration-tests', 'coverage', 'benchmark']:
                cmd = _generate_profile_command(profile_id, module_name, relative_path)
                if cmd:
                    commands[canonical] = cmd

    return commands


def _generate_profile_command(profile_id: str, module_name: str, relative_path: str) -> str:
    """Generate command for a profile.

    Note: Commands do NOT include clean goal. Run clean separately if needed.

    Args:
        profile_id: Maven profile ID
        module_name: Module artifact ID
        relative_path: Path relative to project root ("" or "." for root module)
    """
    base = 'python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run'

    # Embed -pl in command-args for submodules, empty for root
    is_root_module = not relative_path or relative_path == '.'
    pl_arg = '' if is_root_module else f' -pl {module_name}'

    # Profile activation via -P flag (no clean goal), module via -pl
    return f'{base} --command-args "verify -P{profile_id}{pl_arg}"'


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Maven module discovery')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # discover subcommand
    discover_parser = subparsers.add_parser('discover', help='Discover Maven modules')
    discover_parser.add_argument('--root', required=True, help='Project root directory')
    discover_parser.add_argument('--format', choices=['json'], default='json', help='Output format')

    args = parser.parse_args()

    if args.command == 'discover':
        modules = discover_maven_modules(args.root)
        print(json.dumps(modules, indent=2))


if __name__ == '__main__':
    main()
