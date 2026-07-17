#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Maven module discovery command.

Discovers Maven modules with complete metadata. The default discovery path is
SUBPROCESS-FREE: it parses each ``pom.xml`` with stdlib ``xml.etree`` and walks
the filesystem for sources/tests. A multi-module reactor therefore discovers in
O(N) cheap reads rather than O(N) Maven JVM startups (and, because the
architecture crawl memoizes its result, O(N) rather than the former O(N²)).

Data Sources:
    FROM POM.XML PARSE (cheap, default path — no subprocess):
        - coordinates: artifactId / groupId (parent-fallback) / packaging
        - profiles: declared ``/project/profiles/profile/id`` ids
        - description / parent GAV
    FROM MAVEN (resolved/inherited — enrich path only, one module at a time):
        - resolved coordinates from dependency:tree header
        - profiles via help:all-profiles (includes parent POM profiles)
        - dependencies via dependency:tree (resolved with scopes)

The enrich path (:func:`enrich_maven_module`) runs ``help:all-profiles
dependency:tree`` for a SINGLE module and is invoked lazily by the dependency
graph and the resolver's profile-canonical path — never by the cheap default
discovery.

Usage:
    python3 maven_cmd_discover.py discover --root /path/to/project [--format json]

Output:
    JSON array of module objects conforming to module-discovery.md contract.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

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
        return PROFILE_PATTERNS[profile_id]
    profile_lower = profile_id.lower()
    for alias, canonical in PROFILE_PATTERNS.items():
        if alias.lower() == profile_lower:
            return canonical
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


def mark_mutating_profiles(profiles: list[dict], mutating_list: list[str] | None) -> list[dict]:
    """Stamp ``mutating: True`` onto profiles authored as source-mutating.

    The authored ``build.maven.profiles.mutating`` CSV is the only source —
    no pattern inference. Profiles not listed carry no ``mutating`` key.

    Args:
        profiles: List of profile dicts with 'id' field.
        mutating_list: Authored profile IDs that mutate sources (None or empty
            stamps nothing).

    Returns:
        List of profile dicts, listed ones carrying ``mutating: True``.
    """
    if not mutating_list:
        return profiles
    mutating_set = {m.strip() for m in mutating_list}
    return [{**p, 'mutating': True} if p['id'] in mutating_set else p for p in profiles]


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

# Key: build.maven.profiles.mutating
# Value: Comma-separated list of profile IDs the operator authors as
#        source-mutating (e.g. an OpenRewrite-bearing pre-commit profile)
# Example: "pre-commit"
# Effect: Command-map entries derived from a listed profile carry
#         `mutating: true`; entries not derived from a listed profile carry no
#         `mutating` key, so authored-true vs unknown stays distinguishable.
#         No pattern inference of any kind — the operator authoring is the
#         only source.
EXT_KEY_PROFILES_MUTATING = 'build.maven.profiles.mutating'


def _read_profile_ext_config(project_root: str) -> tuple[list[str] | None, dict[str, str] | None, list[str] | None]:
    """Read the three authored profile ext-defaults keys for ``project_root``.

    Returns:
        Tuple of (skip_list, explicit_mapping, mutating_list); each element is
        ``None`` when its key is unset.
    """
    from _config_core import ext_defaults_get

    skip_list = None
    explicit_mapping = None
    mutating_list = None

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

    mutating_csv = ext_defaults_get(EXT_KEY_PROFILES_MUTATING, project_root)
    if mutating_csv:
        mutating_list = [m.strip() for m in mutating_csv.split(',')]

    return skip_list, explicit_mapping, mutating_list


# =============================================================================
# Module Discovery
# =============================================================================


def discover_maven_modules(project_root: str) -> list:
    """Discover all Maven modules with complete metadata — subprocess-free.

    Uses ``discover_descriptors`` from the base library to find all ``pom.xml``
    files, then derives each module's shape from a stdlib XML parse of the POM
    plus filesystem source/test discovery. No Maven subprocess is invoked: the
    resolved-coordinate / inherited-profile / dependency-tree fields are filled
    lazily by :func:`enrich_maven_module` only when a consumer needs them.

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

        # Build complete module data from the cheap POM parse + filesystem walk.
        module_data = _build_module(base, pom_path, root)
        if module_data:
            modules.append(module_data)

    return modules


# =============================================================================
# Module Building
# =============================================================================


def _build_module(base, pom_path: Path, project_root: Path) -> dict | None:
    """Build complete module dict from base info and a cheap POM parse.

    The whole module shape — coordinates, packaging, paths, sources/tests,
    declared profiles, and the full command map — is computed WITHOUT invoking
    Maven. Resolved-coordinate / inherited-profile / dependency-tree fields are
    deliberately NOT populated here; ``dependencies`` is an empty list. A
    consumer that needs the resolved view calls :func:`enrich_maven_module`.

    Args:
        base: ModuleBase from build_module_base
        pom_path: Path to pom.xml file
        project_root: Project root path

    Returns:
        Complete module dict conforming to module-discovery.md
    """
    module_path = pom_path.parent
    relative_path = base.paths.module

    # Coordinates / packaging / declared profiles from the cheap POM parse.
    pom_data = _parse_pom_xml(pom_path)
    artifact_id = pom_data.get('artifact_id') or base.name
    group_id = pom_data.get('group_id')
    packaging = pom_data.get('packaging') or 'jar'
    # Declared profile ids → the canonical-mapping pipeline (no Maven filtering
    # for default-activation is possible without a subprocess, so every declared
    # id is treated as a command-line-activatable profile).
    declared_profile_ids = pom_data.get('profile_ids', [])
    profiles = _map_canonical_declared_profiles(declared_profile_ids, str(project_root))

    # Description and parent from the same POM parse.
    description = pom_data.get('description')
    parent = pom_data.get('parent')

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
        'parent': parent,
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
        # Resolved dependency tree is an enrich-path concern; the cheap crawl
        # leaves this empty. ``enrich_maven_module`` fills it on demand.
        'dependencies': [],
        'stats': {'source_files': source_files, 'test_files': test_files},
        'commands': commands,
    }


def _map_canonical_declared_profiles(profile_ids: list[str], project_root: str) -> list[dict]:
    """Map cheaply-parsed declared profile ids through the canonical pipeline.

    The cheap POM parse yields bare profile ids (no Maven ``Active:`` flag), so
    the command-line-activation filter ``_apply_profile_pipeline`` applies to
    the Maven ``help:all-profiles`` output is not relevant here — every declared
    id is a candidate. This applies the SAME skip-list + canonical-mapping
    config the enrich pipeline uses (so an in-pom ``coverage`` profile still maps
    to the ``coverage`` canonical), but reads its inputs from the declared ids.

    Args:
        profile_ids: Declared ``/project/profiles/profile/id`` values.
        project_root: Project root for configuration lookup (skip-list, mapping).

    Returns:
        List of ``{id, canonical}`` dicts (authored-mutating ones carrying
        ``mutating: True``), skip-filtered, in declared order.
    """
    profiles = [{'id': pid} for pid in profile_ids]

    skip_list, explicit_mapping, mutating_list = _read_profile_ext_config(project_root)

    profiles = filter_skip_profiles(profiles, skip_list)
    profiles = map_canonical_profiles(profiles, explicit_mapping)
    return mark_mutating_profiles(profiles, mutating_list)


# =============================================================================
# Cheap POM parse (stdlib xml.etree — no subprocess)
# =============================================================================


def _strip_ns(tag: str) -> str:
    """Return the local tag name, dropping any ``{namespace}`` prefix.

    Maven POMs declare the ``http://maven.apache.org/POM/4.0.0`` namespace, so
    ``ElementTree`` reports tags as ``{http://...}artifactId``. Matching on the
    local name lets one code path handle both namespaced and namespace-less
    POMs.
    """
    return tag.rsplit('}', 1)[-1]


def _find_child(element: ET.Element, local_name: str) -> ET.Element | None:
    """Return the first direct child of ``element`` whose local tag matches."""
    for child in element:
        if _strip_ns(child.tag) == local_name:
            return child
    return None


def _child_text(element: ET.Element, local_name: str) -> str | None:
    """Return the stripped text of ``element``'s first matching direct child."""
    child = _find_child(element, local_name)
    if child is not None and child.text is not None:
        text = child.text.strip()
        return text or None
    return None


def _parse_pom_xml(pom_path: Path) -> dict:
    """Parse a ``pom.xml`` with stdlib ``xml.etree`` — no Maven subprocess.

    Extracts the fields the cheap discovery path needs. Handles both namespaced
    POMs (the usual ``http://maven.apache.org/POM/4.0.0`` declaration) and
    namespace-less POMs by matching on local tag names.

    Args:
        pom_path: Path to the ``pom.xml`` file.

    Returns:
        Dict with:
            - ``packaging``: ``<packaging>`` text, defaulting to ``'jar'``.
            - ``artifact_id``: ``<artifactId>`` text (or ``None``).
            - ``group_id``: ``<groupId>`` text, falling back to
              ``<parent><groupId>`` when the child omits it (or ``None``).
            - ``profile_ids``: declared ``/project/profiles/profile/id`` values.
            - ``description``: ``<description>`` text (or ``None``).
            - ``parent``: ``groupId:artifactId`` of ``<parent>`` (or ``None``).
        On a malformed/unreadable POM, returns the packaging default with all
        other fields ``None``/empty so discovery degrades gracefully.
    """
    try:
        root = ET.parse(pom_path).getroot()
    except (ET.ParseError, OSError):
        return {
            'packaging': 'jar',
            'artifact_id': None,
            'group_id': None,
            'profile_ids': [],
            'description': None,
            'parent': None,
        }

    packaging = _child_text(root, 'packaging') or 'jar'
    artifact_id = _child_text(root, 'artifactId')
    description = _child_text(root, 'description')

    # Parent block: GAV reference + groupId fallback source.
    parent_el = _find_child(root, 'parent')
    parent = None
    parent_group_id = None
    if parent_el is not None:
        parent_group_id = _child_text(parent_el, 'groupId')
        parent_artifact_id = _child_text(parent_el, 'artifactId')
        if parent_group_id and parent_artifact_id:
            parent = f'{parent_group_id}:{parent_artifact_id}'

    # groupId: child declaration wins; otherwise inherit from <parent>.
    group_id = _child_text(root, 'groupId') or parent_group_id

    # Declared profile ids under /project/profiles/profile/id.
    profile_ids: list[str] = []
    profiles_el = _find_child(root, 'profiles')
    if profiles_el is not None:
        for profile_el in profiles_el:
            if _strip_ns(profile_el.tag) != 'profile':
                continue
            pid = _child_text(profile_el, 'id')
            if pid:
                profile_ids.append(pid)

    return {
        'packaging': packaging,
        'artifact_id': artifact_id,
        'group_id': group_id,
        'profile_ids': profile_ids,
        'description': description,
        'parent': parent,
    }


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


def enrich_maven_module(module_path: str | Path, project_root: str | Path) -> dict | None:
    """Resolve one module's Maven-derived metadata (the lazy enrich entry).

    The single public seam onto the Maven subprocess. Runs
    :func:`_get_maven_metadata` for ONE module (``help:all-profiles
    dependency:tree``) and returns the resolved coordinates, the active/inherited
    profiles, and the resolved dependency tree. Callers — the dependency-graph
    path and the resolver's lazy profile-canonical path — invoke this only when
    they need a field the cheap POM-parse discovery does not populate.

    Args:
        module_path: Path to the module directory containing ``pom.xml``.
        project_root: Project root used for Maven execution and config lookup.

    Returns:
        Dict with ``artifact_id`` / ``group_id`` / ``packaging`` / ``profiles``
        (canonical-mapped, command-line-activated) / ``dependencies``
        (``groupId:artifactId:scope`` strings), or ``None`` when the Maven
        invocation fails or the POM is absent.
    """
    return _get_maven_metadata(Path(module_path), Path(project_root))


def _apply_profile_pipeline(raw_profiles: list, project_root: str) -> list:
    """Apply the full profile processing pipeline.

    Pipeline stages:
    1. Filter to command-line activated profiles only (Active: false)
    2. Apply skip list from configuration
    3. Map to canonical command names
    4. Stamp authored-mutating profiles

    Args:
        raw_profiles: Raw profiles from Maven output with is_active field
        project_root: Project root for configuration lookup

    Returns:
        List of processed profile dicts with id and canonical fields
        (authored-mutating ones carrying ``mutating: True``)
    """
    # Import directly - executor sets up PYTHONPATH for cross-skill imports
    from plan_logging import log_entry

    # 1. Filter to command-line only (Active: false)
    profiles = filter_command_line_profiles(raw_profiles)

    # 2. Get skip list, mapping, and mutating list from configuration
    skip_list, explicit_mapping, mutating_list = _read_profile_ext_config(project_root)

    # 3. Apply skip list
    profiles = filter_skip_profiles(profiles, skip_list)

    # 4. Map to canonical names
    profiles = map_canonical_profiles(profiles, explicit_mapping)

    # 5. Stamp authored-mutating profiles
    profiles = mark_mutating_profiles(profiles, mutating_list)

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
    - Always (all modules including pom): clean, verify, quality-gate, install,
      compile, package
    - Test-conditional (non-pom): test-compile, module-tests
    - Non-pom: clean-install
    - Profile-based: integration-tests, coverage, benchmark

    Entries derived from an authored-mutating profile (see
    ``EXT_KEY_PROFILES_MUTATING``) are emitted in dict form
    ``{'executable': ..., 'mutating': True}``; all other entries are plain
    executable strings.

    ``compile`` / ``package`` are emitted for ``pom`` aggregators too as a
    reactor passthrough — ``compile`` at the root drives the whole reactor's
    compile, and ``compile -pl {relative_path}`` a nested aggregator's subtree.
    A docs-only / aggregator change still resolves a real ``compile`` verb this
    way instead of falling through to the root cascade. ``compile`` for a
    source-less leaf is harmless (Maven no-ops it).

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
    # ``-am`` (--also-make) builds the selected module's upstream reactor
    # dependencies first, so an intra-reactor test-jar resolves on a clean
    # checkout. It is safe for build commands, but MUST NOT be used with
    # ``clean``: ``mvn clean -pl <module> -am`` would wipe the ``target/``
    # directories of all upstream reactor dependencies, forcing a full rebuild.
    pl_arg = '' if is_root_module else f' -pl {relative_path} -am'
    # ``clean`` only scopes to the target module — no upstream cleanup.
    pl_no_am_arg = '' if is_root_module else f' -pl {relative_path}'

    # 1. Always (all modules including pom): clean, the verify/quality-gate
    #    gate, install, plus the compile/package reactor passthrough.
    cmd_map: dict[str, str] = {
        'clean': f'clean{pl_no_am_arg}',
        'quality-gate': f'verify{pl_arg}',
        'verify': f'verify{pl_arg}',
        'install': f'install{pl_arg}',
        'compile': f'compile{pl_arg}',
        'package': f'package{pl_arg}',
    }

    # 2. Non-pom modules get the combined clean+install and (when present) the
    #    test ladder. pom aggregators have no own tests, so module-tests stays
    #    non-pom-only.
    if packaging != 'pom':
        cmd_map['clean-install'] = f'clean install{pl_arg}'

        if has_tests:
            cmd_map['test-compile'] = f'test-compile{pl_arg}'
            cmd_map['module-tests'] = f'test{pl_arg}'

    # 3. Profile-based commands (integration-tests, coverage, benchmark)
    # Track which profiles map to each canonical for conflict detection, and
    # which canonicals were derived from an authored-mutating profile.
    canonical_profiles: dict[str, list[str]] = {}
    mutating_canonicals: set[str] = set()
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
                    if profile.get('mutating'):
                        mutating_canonicals.add('quality-gate')
            elif canonical in ['integration-tests', 'e2e', 'coverage', 'benchmark']:
                cmd_map[canonical] = profile_args
                if profile.get('mutating'):
                    mutating_canonicals.add(canonical)

    result: dict[str, Any] = build_canonical_commands(skill, cmd_map)

    # Stamp the authored mutating signal onto profile-derived entries: dict-form
    # entries carry `mutating: true`; unlisted entries stay plain strings so
    # authored-true vs unknown remains distinguishable downstream.
    for canonical in mutating_canonicals:
        if canonical in result:
            result[canonical] = {'executable': result[canonical], 'mutating': True}

    # Report conflicts when multiple profiles map to the same canonical
    conflicts = {c: ps for c, ps in canonical_profiles.items() if len(ps) > 1}
    if conflicts:
        result['conflicts'] = conflicts

    return result
