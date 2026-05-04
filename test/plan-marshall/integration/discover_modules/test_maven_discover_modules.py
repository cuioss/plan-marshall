#!/usr/bin/env python3
"""Integration tests for Maven discover_modules().

Tests Maven module discovery against real projects in the local git directory.
Results are persisted to .plan/temp/test-results-maven/ for inspection.

IMPORTANT (H50): These tests depend on external git projects existing on disk.
They will fail in CI or on machines where the test projects are not cloned.
Consider them as local verification tests, not part of the CI gate.

Run with:
    python3 test/plan-marshall/integration/discover_modules/test_maven_discover_modules.py

Per-module on-disk layout (post phase-a-arch-split):

- ``.plan/project-architecture/_project.json`` — top-level project metadata; the
  ``modules`` field is the source of truth for module discovery.
- ``.plan/project-architecture/{module}/derived.json`` — deterministic discovery
  output for a single module (paths, packages, dependencies).
- ``.plan/project-architecture/{module}/enriched.json`` — LLM-augmented fields
  for a single module (internal_dependencies, is_leaf, …).

The fixture trees under ``resources/{project}/.plan/project-architecture/`` mirror
this layout, and the helpers below copy / synthesise the per-module files (never
the deprecated monolithic ``derived-data.json`` / ``llm-enriched.json`` pair).
"""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
RESOURCES_DIR = Path(__file__).parent / 'resources'

# Import Extension from plan-marshall:plan-marshall-plugin (relocated from
# pm-dev-java in phase-a-arch-split). The ``_architecture_core`` save helpers
# and ``_cmd_client.get_module_graph`` now live in plan-marshall:manage-architecture.
EXTENSION_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'plan-marshall-plugin'
sys.path.insert(0, str(EXTENSION_DIR))

# Direct imports - conftest sets up PYTHONPATH for cross-skill imports
from _architecture_core import (  # noqa: E402
    save_module_derived,
    save_module_enriched,
    save_project_meta,
)
from _cmd_client import get_module_graph  # noqa: E402
from _cmd_manage import _post_process_files  # noqa: E402
from extension import Extension  # noqa: E402

from integration_common import (  # noqa: E402
    INTEGRATION_TEST_OUTPUT_DIR,
    IntegrationContext,
    ProjectFixture,
    assert_has_root_aggregator,
    assert_maven_module_structure,
    assert_no_null_values,
    assert_paths_exist,
)

# =============================================================================
# Graph Output Helper
# =============================================================================


def format_graph_toon(result: dict) -> str:
    """Format graph result as dependency tree."""
    lines = []
    nodes = result['nodes']
    edges = result['edges']

    lines.append('status: success')
    lines.append('')

    # Single module: just the name
    if len(nodes) == 1:
        lines.append(f'module: {nodes[0]["name"]}')
        return '\n'.join(lines)

    # Build dependency lookup: what does each module depend on
    dependencies = {n['name']: [] for n in nodes}
    for edge in edges:
        dependencies[edge['to']].append(edge['from'])

    leaves = result['leaves']
    printed = set()

    def format_deps(module_name: str, indent: int = 0) -> list:
        """Format module and its dependencies with indentation."""
        dep_lines = []
        prefix = '  ' * indent
        if indent > 0:
            dep_lines.append(f'{prefix}- {module_name}')
        else:
            dep_lines.append(module_name)

        if module_name in printed:
            return dep_lines
        printed.add(module_name)

        deps = sorted(dependencies.get(module_name, []))
        for dep in deps:
            dep_lines.extend(format_deps(dep, indent + 1))
        return dep_lines

    for i, leaf in enumerate(sorted(leaves)):
        if i > 0:
            lines.append('')
        lines.extend(format_deps(leaf))

    # Circular dependencies
    if result.get('circular_dependencies'):
        lines.append('')
        lines.append('warning: circular_dependencies_detected')
        circular = result['circular_dependencies']
        lines.append(f'circular_dependencies[{len(circular)}]:')
        for c in circular:
            lines.append(f'  - {c}')

    lines.append('')
    return '\n'.join(lines)


def generate_per_module_enriched(modules_dict: dict) -> dict:
    """Generate per-module LLM-enriched data with computed internal_dependencies.

    Mirrors the per-module ``enriched.json`` contract: each value is the
    enrichment payload for a single module (NOT a project-level dict with a
    nested ``modules`` index).

    Computes:
    - internal_dependencies: which project modules this module depends on
    - is_leaf: True for pom modules that have internal dependencies (test modules, etc.)

    Args:
        modules_dict: Dict of module name -> module data

    Returns:
        Dict of module name -> per-module enrichment payload. Modules with no
        meaningful enrichment data are omitted.
    """
    # Build mapping of groupId:artifactId -> module_name
    artifact_to_module = {}
    for mod_name, mod_data in modules_dict.items():
        metadata = mod_data.get('metadata', {})
        group_id = metadata.get('group_id')
        artifact_id = metadata.get('artifact_id')
        if group_id and artifact_id:
            artifact_to_module[f'{group_id}:{artifact_id}'] = mod_name

    enriched_modules = {}
    for mod_name, mod_data in modules_dict.items():
        deps = mod_data.get('dependencies', [])
        internal = set()
        for dep in deps:
            parts = dep.split(':')
            if len(parts) >= 2:
                ga = f'{parts[0]}:{parts[1]}'
                if ga in artifact_to_module:
                    dep_module = artifact_to_module[ga]
                    if dep_module != mod_name:
                        internal.add(dep_module)

        internal_deps = sorted(internal)

        metadata = mod_data.get('metadata', {})
        packaging = metadata.get('packaging', 'jar')

        # Heuristics for pom modules
        name_lower = mod_name.lower()
        is_test_module = any(kw in name_lower for kw in ['test', 'e2e', 'e-2-e', 'playwright'])
        is_parent_module = 'parent' in name_lower

        if internal_deps or packaging == 'pom':
            enriched_mod = {}
            if internal_deps:
                enriched_mod['internal_dependencies'] = internal_deps
            # Mark as leaf if: pom test module (NOT parent modules with deps - those are aggregators)
            if packaging == 'pom' and is_test_module and not is_parent_module:
                enriched_mod['is_leaf'] = True
            if enriched_mod:  # Only add if not empty
                enriched_modules[mod_name] = enriched_mod

    return enriched_modules


def copy_resources_if_exists(project_name: str, output_dir: Path) -> bool:
    """Copy per-module architecture files from test resources if they exist.

    Mirrors the per-module on-disk layout:

    - ``_project.json`` (top-level project metadata)
    - ``{module}/derived.json`` (one per module)
    - ``{module}/enriched.json`` (one per module)

    Args:
        project_name: Project name (matches resources subdirectory)
        output_dir: Target output directory

    Returns:
        True if any resources were copied, False otherwise
    """
    resource_name = project_name.lower().replace(' ', '-').replace('/', '-')
    resource_dir = RESOURCES_DIR / resource_name / '.plan' / 'project-architecture'

    if not resource_dir.exists():
        return False

    target_dir = output_dir / '.plan' / 'project-architecture'
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = False

    # Copy top-level _project.json
    project_meta_src = resource_dir / '_project.json'
    if project_meta_src.exists():
        shutil.copy2(project_meta_src, target_dir / '_project.json')
        print('  Copied: _project.json (from test resources)')
        copied = True

    # Copy each module subdirectory's derived.json / enriched.json
    for module_subdir in sorted(p for p in resource_dir.iterdir() if p.is_dir()):
        target_module_dir = target_dir / module_subdir.name
        target_module_dir.mkdir(parents=True, exist_ok=True)
        for filename in ('derived.json', 'enriched.json'):
            src = module_subdir / filename
            if src.exists():
                shutil.copy2(src, target_module_dir / filename)
                print(f'  Copied: {module_subdir.name}/{filename} (from test resources)')
                copied = True

    return copied


def save_graph_outputs(output_dir: Path, project_name: str, modules: list, project_path: Path):
    """Save graph outputs (default and --full) for a discovered project.

    Writes the per-module on-disk layout (``_project.json`` plus
    ``{module}/derived.json`` and ``{module}/enriched.json``) using the
    relocated ``_architecture_core`` save helpers.

    Args:
        output_dir: Directory to save outputs
        project_name: Project name for output filenames
        modules: Discovered modules list
        project_path: Absolute path to the project
    """
    # Create project-specific output directory
    filename = project_name.lower().replace(' ', '-').replace('/', '-')
    project_output_dir = output_dir / filename
    project_output_dir.mkdir(parents=True, exist_ok=True)

    # Copy architecture files from test resources if available
    resources_copied = copy_resources_if_exists(project_name, project_output_dir)

    # Build module-name -> module-data map. The Phase B files-inventory
    # has already been populated on the modules list by the main test loop;
    # rebuilding the dict here just gives downstream code a name-keyed view.
    modules_dict = {}
    for mod in modules:
        mod_name = mod.get('name', 'unknown')
        modules_dict[mod_name] = mod

    arch_dir = project_output_dir / '.plan' / 'project-architecture'

    # Save top-level _project.json (skip if already copied from resources to
    # preserve marshal-steward output and any hand-curated description fields).
    project_meta_path = arch_dir / '_project.json'
    if project_meta_path.exists():
        if not resources_copied:
            print('  Project meta: _project.json (existing)')
    else:
        project_meta = {
            'name': project_name,
            'modules': {name: {} for name in sorted(modules_dict)},
        }
        save_project_meta(project_meta, str(project_output_dir))
        print('  Project meta: _project.json (generated)')

    # Save per-module derived.json files (skip any already provided by
    # resources to preserve marshal-steward output).
    derived_generated = 0
    derived_existing = 0
    for mod_name, mod_data in modules_dict.items():
        module_derived_path = arch_dir / mod_name / 'derived.json'
        if module_derived_path.exists():
            derived_existing += 1
            continue
        save_module_derived(mod_name, mod_data, str(project_output_dir))
        derived_generated += 1
    if derived_generated:
        print(f'  Derived: {derived_generated} module(s) generated')
    if derived_existing and not resources_copied:
        print(f'  Derived: {derived_existing} module(s) existing')

    # Save per-module enriched.json files where computed enrichment is
    # meaningful (internal_dependencies / is_leaf). Skip modules where a
    # resources-supplied enriched.json already exists.
    enriched_payloads = generate_per_module_enriched(modules_dict)
    enriched_generated = 0
    for mod_name, payload in enriched_payloads.items():
        module_enriched_path = arch_dir / mod_name / 'enriched.json'
        if module_enriched_path.exists():
            continue
        save_module_enriched(mod_name, payload, str(project_output_dir))
        enriched_generated += 1
    if enriched_generated:
        print(f'  Enriched: {enriched_generated} module(s) generated')

    # Generate graph without --full (filters aggregators)
    try:
        graph_default = get_module_graph(str(project_output_dir), full=False)
        graph_default_path = project_output_dir / 'graph-default.txt'
        with open(graph_default_path, 'w') as f:
            f.write(format_graph_toon(graph_default))
        print(f'  Graph (default): {graph_default_path.name}')
    except Exception as e:
        print(f'  Graph (default): ERROR - {e}')

    # Generate graph with --full (includes aggregators)
    try:
        graph_full = get_module_graph(str(project_output_dir), full=True)
        graph_full_path = project_output_dir / 'graph-full.txt'
        with open(graph_full_path, 'w') as f:
            f.write(format_graph_toon(graph_full))
        print(f'  Graph (--full): {graph_full_path.name}')
    except Exception as e:
        print(f'  Graph (--full): ERROR - {e}')


# =============================================================================
# Phase B Files-Inventory Schema Assertion
# =============================================================================


def assert_files_inventory_schema(modules: list) -> list:
    """Schema-only assertions for the ``files`` block on each module.

    Cardinality / content is intentionally NOT checked — exact path lists
    drift with project content. The contract pinned here is structural:
    the key exists, the value is a dict whose values are either lists of
    strings or the canonical ``{elided, sample}`` shape.

    Returns:
        List of error strings (empty list on full pass).
    """
    errors: list[str] = []
    for mod in modules:
        name = mod.get('name', '?')
        files_block = mod.get('files')
        if files_block is None:
            errors.append(f'{name}: missing ``files`` block')
            continue
        if not isinstance(files_block, dict):
            errors.append(f'{name}: ``files`` is not a dict (got {type(files_block).__name__})')
            continue
        for category, value in files_block.items():
            if isinstance(value, list):
                if not all(isinstance(p, str) for p in value):
                    errors.append(f'{name}.files.{category}: non-string entry in path list')
            elif isinstance(value, dict):
                if 'elided' not in value or 'sample' not in value:
                    errors.append(f'{name}.files.{category}: dict value missing ``elided``/``sample`` keys')
                elif not isinstance(value.get('elided'), int):
                    errors.append(f'{name}.files.{category}: ``elided`` is not an integer')
                elif not isinstance(value.get('sample'), list):
                    errors.append(f'{name}.files.{category}: ``sample`` is not a list')
            else:
                errors.append(f'{name}.files.{category}: unexpected value type {type(value).__name__}')
    return errors


# =============================================================================
# Test Projects Configuration
# =============================================================================

# Projects relative to git directory (parent of plan-marshall)
TEST_PROJECTS = [
    ProjectFixture(name='cui-http', relative_path='cui-http', description='Single-module Maven library'),
    ProjectFixture(
        name='cui-java-tools', relative_path='cui-java-tools', description='Single-module Maven utility library'
    ),
    ProjectFixture(
        name='nifi-extensions',
        relative_path='nifi-extensions',
        description='Multi-module Maven project with hybrid Java+npm',
    ),
    ProjectFixture(
        name='OAuth-Sheriff', relative_path='OAuth-Sheriff', description='Multi-module Maven Quarkus project'
    ),
]

# Output directory for results
OUTPUT_DIR = INTEGRATION_TEST_OUTPUT_DIR / 'discover_modules-maven'


# =============================================================================
# Integration Tests
# =============================================================================


def run_integration_tests() -> int:
    """Run all Maven discover_modules integration tests.

    Returns:
        0 if all tests pass, 1 if any fail
    """
    ext = Extension()
    all_passed = True
    test_count = 0
    pass_count = 0

    with IntegrationContext(OUTPUT_DIR, clean_before=True) as ctx:
        print('Maven discover_modules() Integration Tests')
        print('=' * 60)
        print(f'Output directory: {OUTPUT_DIR}')
        print(f'Git directory: {ctx.git_dir}')
        print()

        for project in TEST_PROJECTS:
            print(f'\n--- {project.name} ---')
            print(f'Path: {project.relative_path}')
            print(f'Description: {project.description}')

            # Check if project exists
            if not ctx.validate_project(project):
                print('  SKIP: Project not found')
                continue

            test_count += 1
            project_path = project.absolute_path(ctx.git_dir)

            # Run discovery
            try:
                modules = ext.discover_modules(str(project_path))
                print(f'  Found: {len(modules)} module(s)')

                # Phase B: populate the per-module ``files`` inventory so
                # downstream save/assertion steps see the same shape that
                # ``api_discover`` would produce.
                modules_dict = {mod.get('name', 'unknown'): mod for mod in modules}
                _post_process_files(modules_dict, str(project_path))

                # Save result
                output_path = ctx.save_result(project, modules)
                print(f'  Saved: {output_path.name}')

                # Generate graph outputs (default and --full)
                save_graph_outputs(OUTPUT_DIR, project.name, modules, project_path)

                # Run assertions
                errors = []

                # Assert no null values (readme and description can be null)
                nulls = assert_no_null_values(modules, allowed_null_suffixes=['.readme', '.description'])
                if nulls:
                    errors.append(f'Null values found at: {", ".join(nulls)}')

                # Assert paths exist
                missing = assert_paths_exist(modules, project_path)
                if missing:
                    errors.extend(missing)

                # Assert Maven-specific structure
                maven_errors = assert_maven_module_structure(modules)
                if maven_errors:
                    errors.extend(maven_errors)

                # Assert multi-module projects have root aggregator (if root pom.xml exists)
                root_errors = assert_has_root_aggregator(modules, project_path, ['pom.xml'])
                if root_errors:
                    errors.extend(root_errors)

                # Assert Phase B files-inventory schema: every module's
                # post-discovery dict must contain a ``files`` block whose
                # values are either lists or the elision shape. Only schema
                # / cardinality checks — exact path lists drift with project
                # content and are not pinned here.
                files_errors = assert_files_inventory_schema(modules)
                if files_errors:
                    errors.extend(files_errors)

                # Report results
                if errors:
                    print(f'  FAIL: {len(errors)} error(s)')
                    for err in errors:
                        print(f'    - {err}')
                    ctx.errors.extend([f'{project.name}: {e}' for e in errors])
                    all_passed = False
                else:
                    print('  PASS: All assertions passed')
                    pass_count += 1

                # Print module summary
                for mod in modules:
                    mod_name = mod.get('name', '?')
                    mod_path = mod.get('paths', {}).get('module', '?')
                    print(f'    - {mod_name} ({mod_path})')

            except Exception as e:
                print(f'  ERROR: {e}')
                ctx.errors.append(f'{project.name}: {e}')
                all_passed = False

        # Print summary
        ctx.print_summary()
        print(f'\nTests: {pass_count}/{test_count} passed')

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(run_integration_tests())
