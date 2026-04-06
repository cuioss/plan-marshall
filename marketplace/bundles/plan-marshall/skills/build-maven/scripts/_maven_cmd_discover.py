#!/usr/bin/env python3
"""Maven module discovery command.

Discovers Maven modules with complete metadata using Maven commands
and file system analysis. Implements the discover_modules() contract
from module-discovery.md.

Data Sources:
    FROM MAVEN (resolved/inherited):
        - coordinates: groupId:artifactId:packaging from dependency:tree header
        - profiles: via help:all-profiles (includes parent POM profiles)
        - dependencies: via dependency:tree (resolved with scopes)
    FROM POM.XML (local only - exceptional cases):
        - description: optional, rarely inherited
        - parent: GAV reference (not available in dependency:tree)

IMPORTANT: Uses Maven commands per module-discovery.md specification:
- help:all-profiles for profiles (includes inherited from parent POMs)
- dependency:tree for dependencies AND coordinates (resolved)
Both are combined in a single Maven call per module to minimize JVM startup overhead.

Usage:
    python3 maven_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_discover import (
    build_module_base,
    count_source_files,
    discover_descriptors,
    discover_packages,
    discover_sources,
)
from _build_shared import build_canonical_commands
from _extension_constants import PROFILE_PATTERNS

# =============================================================================
# Profile Pipeline Utilities (Maven-specific — only Maven uses build profiles)
# =============================================================================


def filter_command_line_profiles(raw_profiles: list[dict]) -> list[dict]:
    """Filter profiles to command-line activated only.

    Removes profiles that are default-activated (Active: true in build tool output).
    Only profiles with Active: false are kept — these require explicit activation.

    Args:
        raw_profiles: List of profile dicts with 'id' and 'is_active' fields.

    Returns:
        List of profile dicts with 'id' only (is_active removed).
    """
    return [{'id': p['id']} for p in raw_profiles if not p.get('is_active', False)]


def filter_skip_profiles(profiles: list[dict], skip_list: list[str] | None) -> list[dict]:
    """Filter out profiles in the skip list.

    Args:
        profiles: List of profile dicts with 'id' field.
        skip_list: Profile IDs to exclude (None or empty keeps all).

    Returns:
        Filtered list of profile dicts.
    """
    if not skip_list:
        return profiles
    skip_set = {s.strip() for s in skip_list}
    return [p for p in profiles if p['id'] not in skip_set]


def _classify_profile(profile_id: str) -> str:
    """Classify a profile ID to its canonical command name.

    Args:
        profile_id: The profile identifier (e.g., "pre-commit", "jacoco").

    Returns:
        Canonical command name (e.g., "quality-gate", "coverage") or "NO-MATCH-FOUND".
    """
    if profile_id in PROFILE_PATTERNS:
        return PROFILE_PATTERNS[profile_id]  # type: ignore[no-any-return]
    profile_lower = profile_id.lower()
    for alias, canonical in PROFILE_PATTERNS.items():
        if alias.lower() == profile_lower:
            return canonical  # type: ignore[no-any-return]
    return 'NO-MATCH-FOUND'


def map_canonical_profiles(profiles: list[dict], explicit_mapping: dict[str, str] | None = None) -> list[dict]:
    """Map profiles to canonical command names.

    Resolution order:
    1. Explicit mapping (from config) takes precedence
    2. PROFILE_PATTERNS aliases from extension_base.py

    Args:
        profiles: List of profile dicts with 'id' field.
        explicit_mapping: Dict mapping profile_id -> canonical (can be None).

    Returns:
        List of profile dicts with 'canonical' field added.
    """
    mapping = explicit_mapping or {}
    result = []
    for profile in profiles:
        pid = profile['id']
        canonical = mapping.get(pid) or _classify_profile(pid)
        result.append({'id': pid, 'canonical': canonical})
    return result


# =============================================================================
# Extension Defaults Keys (for config_defaults callback)
# =============================================================================
# These constants define configuration keys stored in run-configuration.json
# via the config_defaults callback. Extensions use these to set project-specific
# defaults that influence profile parsing and command generation.
#
# See: plan-marshall:extension-api:standards/extension-contract.md
# See: plan-marshall:build-maven:standards/maven-impl.md

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
        List of module dicts conforming to module-discovery.md contract.
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

        # If Maven failed, return error-only structure (matches Gradle contract)
        if maven_data is None:
            modules.append(
                {
                    'name': base.name,
                    'build_systems': ['maven'],
                    'error': 'Unable to retrieve metadata - Maven commands failed',
                }
            )
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
        Complete module dict conforming to module-discovery.md
    """
    module_path = pom_path.parent
    relative_path = base.paths.module

    # Get metadata from Maven output
    artifact_id = maven_data.get('artifact_id') or base.name
    group_id = maven_data.get('group_id')
    packaging = maven_data.get('packaging') or 'jar'
    profiles = maven_data.get('profiles', [])
    dependencies = maven_data.get('dependencies', [])

    # Description and parent from pom.xml (single read, per spec: not in dependency:tree)
    pom_local = _parse_pom_local_metadata(pom_path)
    description = pom_local['description']

    # Source directories (shared multi-language discovery)
    sources = discover_sources(module_path)
    source_paths = [f'{relative_path}/{s}' if relative_path != '.' else s for s in sources['main']]
    test_paths = [f'{relative_path}/{t}' if relative_path != '.' else t for t in sources['test']]

    # Packages (shared multi-language package discovery)
    rel = relative_path if relative_path != '.' else ''
    packages = discover_packages(module_path, sources.get('main', []), rel)
    test_packages = discover_packages(module_path, sources.get('test', []), rel)

    # Stats (shared multi-language file counting)
    source_files = count_source_files(module_path, sources['main'])
    test_files = count_source_files(module_path, sources['test'])

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
        'parent': pom_local['parent'],
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


def _parse_pom_local_metadata(pom_path: Path) -> dict:
    """Extract description and parent from pom.xml in a single read.

    These fields are not available from Maven commands (dependency:tree, etc.)
    so they must be parsed from the POM file directly.

    Args:
        pom_path: Path to pom.xml file.

    Returns:
        Dict with 'description' (str|None) and 'parent' (str|None).
    """
    content = pom_path.read_text()

    # Description: skip <parent> block to avoid matching parent's description
    description = None
    content_no_parent = re.sub(r'<parent>.*?</parent>', '', content, flags=re.DOTALL)
    desc_match = re.search(r'<description>([^<]+)</description>', content_no_parent)
    if desc_match:
        description = desc_match.group(1).strip()

    # Parent GAV
    parent = None
    parent_match = re.search(r'<parent>(.*?)</parent>', content, flags=re.DOTALL)
    if parent_match:
        parent_block = parent_match.group(1)
        group_match = re.search(r'<groupId>([^<]+)</groupId>', parent_block)
        artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', parent_block)
        if group_match and artifact_match:
            parent = f'{group_match.group(1).strip()}:{artifact_match.group(1).strip()}'

    return {'description': description, 'parent': parent}


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


def _get_maven_metadata(module_path: Path, project_root: Path) -> dict | None:
    """Get coordinates, profiles and dependencies using Maven commands.

    Per module-discovery.md specification, runs:
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

    return {
        'artifact_id': coordinates.get('artifact_id'),
        'group_id': coordinates.get('group_id'),
        'packaging': coordinates.get('packaging'),
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

    # 1. Filter to command-line only (Active: false)
    profiles = filter_command_line_profiles(raw_profiles)

    # 2. Get skip list and mapping from configuration (if available)
    skip_list = None
    explicit_mapping = None

    skip_csv = ext_defaults_get(EXT_KEY_PROFILES_SKIP, project_root)
    if skip_csv:
        skip_list = [s.strip() for s in skip_csv.split(',')]

    map_csv = ext_defaults_get(EXT_KEY_PROFILES_MAP, project_root)
    if map_csv:
        explicit_mapping = {}
        for pair in map_csv.split(','):
            if ':' in pair:
                profile_id, canonical = pair.split(':', 1)
                explicit_mapping[profile_id.strip()] = canonical.strip()

    # 3. Apply skip list
    profiles = filter_skip_profiles(profiles, skip_list)

    # 4. Map to canonical names
    profiles = map_canonical_profiles(profiles, explicit_mapping)

    log_entry(
        'script',
        'global',
        'INFO',
        f'[PROFILE-PIPELINE] {len(raw_profiles)} raw → {len(profiles)} mapped'
        f' (skip={skip_list or "none"}, mapping={explicit_mapping or "none"})',
    )

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
    skill = 'plan-marshall:build-maven:maven'
    is_root_module = not relative_path or relative_path == '.'
    pl_arg = '' if is_root_module else f' -pl {module_name}'

    # 1. Always: clean (all modules including pom)
    cmd_map: dict[str, str] = {
        'clean': f'clean{pl_arg}',
        'quality-gate': f'verify{pl_arg}',
        'verify': f'verify{pl_arg}',
        'install': f'install{pl_arg}',
    }

    # 2. Non-pom modules get additional commands
    if packaging != 'pom':
        cmd_map['clean-install'] = f'clean install{pl_arg}'
        cmd_map['package'] = f'package{pl_arg}'

        if has_sources:
            cmd_map['compile'] = f'compile{pl_arg}'

        if has_tests:
            cmd_map['test-compile'] = f'test-compile{pl_arg}'
            cmd_map['module-tests'] = f'test{pl_arg}'

    # 3. Profile-based commands (integration-tests, coverage, benchmark)
    # Track which profiles map to each canonical for conflict detection
    canonical_profiles: dict[str, list[str]] = {}
    for profile in profiles or []:
        canonical = profile.get('canonical')
        profile_id = profile.get('id')

        if canonical and profile_id:
            canonical_profiles.setdefault(canonical, []).append(profile_id)
            profile_args = f'verify -P{profile_id}{pl_arg}'
            if canonical == 'quality-gate':
                # Only use the first profile match — subsequent matches are conflicts
                if cmd_map.get('quality-gate') == f'verify{pl_arg}':
                    cmd_map['quality-gate'] = profile_args
            elif canonical in ['integration-tests', 'e2e', 'coverage', 'benchmark']:
                cmd_map[canonical] = profile_args

    result = build_canonical_commands(skill, cmd_map)

    # Report conflicts when multiple profiles map to the same canonical
    conflicts = {c: ps for c, ps in canonical_profiles.items() if len(ps) > 1}
    if conflicts:
        result['conflicts'] = conflicts

    return result
