#!/usr/bin/env python3
"""Integration tests for Maven discover_modules().

Tests Maven module discovery against real projects in the local git directory.
Results are persisted to .plan/temp/test-results-maven/ for inspection.

Run with:
    python3 test/pm-dev-java/integration/discover_modules/test_maven_discover_modules.py
"""

import json
import shutil
import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
RESOURCES_DIR = Path(__file__).parent / "resources"
sys.path.insert(0, str(PROJECT_ROOT / "test"))

# Import Extension from pm-dev-java
EXTENSION_DIR = PROJECT_ROOT / "marketplace" / "bundles" / "pm-dev-java" / "skills" / "plan-marshall-plugin"
sys.path.insert(0, str(EXTENSION_DIR))

# Direct imports - conftest sets up PYTHONPATH for cross-skill imports
from _architecture_core import save_derived_data  # noqa: E402
from _cmd_client import get_module_graph  # noqa: E402
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

    lines.append("status: success")
    lines.append("")

    # Single module: just the name
    if len(nodes) == 1:
        lines.append(f"module: {nodes[0]['name']}")
        return "\n".join(lines)

    # Build dependency lookup: what does each module depend on
    dependencies = {n['name']: [] for n in nodes}
    for edge in edges:
        dependencies[edge['to']].append(edge['from'])

    leaves = result['leaves']
    printed = set()

    def format_deps(module_name: str, indent: int = 0) -> list:
        """Format module and its dependencies with indentation."""
        dep_lines = []
        prefix = "  " * indent
        if indent > 0:
            dep_lines.append(f"{prefix}- {module_name}")
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
            lines.append("")
        lines.extend(format_deps(leaf))

    # Circular dependencies
    if result.get('circular_dependencies'):
        lines.append("")
        lines.append("warning: circular_dependencies_detected")
        circular = result['circular_dependencies']
        lines.append(f"circular_dependencies[{len(circular)}]:")
        for c in circular:
            lines.append(f"  - {c}")

    lines.append("")
    return "\n".join(lines)


def generate_enriched_data(modules_dict: dict) -> dict:
    """Generate LLM-enriched data with computed internal_dependencies.

    Computes:
    - internal_dependencies: which project modules this module depends on
    - is_leaf: True for pom modules that have internal dependencies (test modules, etc.)

    Args:
        modules_dict: Dict of module name -> module data

    Returns:
        Enriched data structure with modules section
    """
    # Build mapping of groupId:artifactId -> module_name
    artifact_to_module = {}
    for mod_name, mod_data in modules_dict.items():
        metadata = mod_data.get("metadata", {})
        group_id = metadata.get("group_id")
        artifact_id = metadata.get("artifact_id")
        if group_id and artifact_id:
            artifact_to_module[f"{group_id}:{artifact_id}"] = mod_name

    # Compute internal dependencies and is_leaf for each module
    enriched_modules = {}
    for mod_name, mod_data in modules_dict.items():
        deps = mod_data.get("dependencies", [])
        internal = set()
        for dep in deps:
            parts = dep.split(":")
            if len(parts) >= 2:
                ga = f"{parts[0]}:{parts[1]}"
                if ga in artifact_to_module:
                    dep_module = artifact_to_module[ga]
                    if dep_module != mod_name:
                        internal.add(dep_module)

        internal_deps = sorted(internal)

        # Only add to enriched if there's something meaningful
        metadata = mod_data.get("metadata", {})
        packaging = metadata.get("packaging", "jar")

        # Heuristics for pom modules
        name_lower = mod_name.lower()
        is_test_module = any(kw in name_lower for kw in ["test", "e2e", "e-2-e", "playwright"])
        is_parent_module = "parent" in name_lower

        if internal_deps or packaging == "pom":
            enriched_mod = {}
            if internal_deps:
                enriched_mod["internal_dependencies"] = internal_deps
            # Mark as leaf if: pom test module (NOT parent modules with deps - those are aggregators)
            if packaging == "pom" and is_test_module and not is_parent_module:
                enriched_mod["is_leaf"] = True
            if enriched_mod:  # Only add if not empty
                enriched_modules[mod_name] = enriched_mod

    return {
        "project": {},
        "modules": enriched_modules
    }


def copy_resources_if_exists(project_name: str, output_dir: Path) -> bool:
    """Copy architecture files from test resources if they exist.

    Args:
        project_name: Project name (matches resources subdirectory)
        output_dir: Target output directory

    Returns:
        True if resources were copied, False otherwise
    """
    resource_name = project_name.lower().replace(" ", "-").replace("/", "-")
    resource_dir = RESOURCES_DIR / resource_name / ".plan" / "project-architecture"

    if not resource_dir.exists():
        return False

    target_dir = output_dir / ".plan" / "project-architecture"
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = False
    for filename in ["derived-data.json", "llm-enriched.json"]:
        src = resource_dir / filename
        if src.exists():
            shutil.copy2(src, target_dir / filename)
            print(f"  Copied: {filename} (from test resources)")
            copied = True

    return copied


def save_graph_outputs(output_dir: Path, project_name: str, modules: list, project_path: Path):
    """Save graph outputs (default and --full) for a discovered project.

    Args:
        output_dir: Directory to save outputs
        project_name: Project name for output filenames
        modules: Discovered modules list
        project_path: Absolute path to the project
    """
    # Create project-specific output directory
    filename = project_name.lower().replace(" ", "-").replace("/", "-")
    project_output_dir = output_dir / filename
    project_output_dir.mkdir(parents=True, exist_ok=True)

    # Copy architecture files from test resources if available
    resources_copied = copy_resources_if_exists(project_name, project_output_dir)

    # Build derived data structure
    modules_dict = {}
    for mod in modules:
        mod_name = mod.get("name", "unknown")
        modules_dict[mod_name] = mod

    # Save derived data for architecture script
    # Only generate if no existing derived-data.json (preserve marshal-steward output)
    derived_path = project_output_dir / ".plan" / "project-architecture" / "derived-data.json"
    if derived_path.exists():
        if not resources_copied:
            print("  Derived: derived-data.json (existing)")
    else:
        derived_data = {
            "project": {
                "name": project_name
            },
            "modules": modules_dict
        }
        save_derived_data(derived_data, str(project_output_dir))
        print("  Derived: derived-data.json (generated)")

    # Generate and save enriched data with computed internal_dependencies
    # Only generate if no existing llm-enriched.json (preserve marshal-steward output)
    enriched_path = project_output_dir / ".plan" / "project-architecture" / "llm-enriched.json"
    if enriched_path.exists():
        if not resources_copied:
            print("  Enriched: llm-enriched.json (existing)")
    else:
        enriched_data = generate_enriched_data(modules_dict)
        if enriched_data["modules"]:
            enriched_path.parent.mkdir(parents=True, exist_ok=True)
            with open(enriched_path, "w") as f:
                json.dump(enriched_data, f, indent=2)
            print("  Enriched: llm-enriched.json (generated)")

    # Generate graph without --full (filters aggregators)
    try:
        graph_default = get_module_graph(str(project_output_dir), full=False)
        graph_default_path = project_output_dir / "graph-default.txt"
        with open(graph_default_path, "w") as f:
            f.write(format_graph_toon(graph_default))
        print(f"  Graph (default): {graph_default_path.name}")
    except Exception as e:
        print(f"  Graph (default): ERROR - {e}")

    # Generate graph with --full (includes aggregators)
    try:
        graph_full = get_module_graph(str(project_output_dir), full=True)
        graph_full_path = project_output_dir / "graph-full.txt"
        with open(graph_full_path, "w") as f:
            f.write(format_graph_toon(graph_full))
        print(f"  Graph (--full): {graph_full_path.name}")
    except Exception as e:
        print(f"  Graph (--full): ERROR - {e}")


# =============================================================================
# Test Projects Configuration
# =============================================================================

# Projects relative to git directory (parent of plan-marshall)
TEST_PROJECTS = [
    ProjectFixture(
        name="cui-http",
        relative_path="cui-http",
        description="Single-module Maven library"
    ),
    ProjectFixture(
        name="cui-java-tools",
        relative_path="cui-java-tools",
        description="Single-module Maven utility library"
    ),
    ProjectFixture(
        name="nifi-extensions",
        relative_path="nifi-extensions",
        description="Multi-module Maven project with hybrid Java+npm"
    ),
    ProjectFixture(
        name="OAuth-Sheriff",
        relative_path="OAuth-Sheriff",
        description="Multi-module Maven Quarkus project"
    ),
]

# Output directory for results
OUTPUT_DIR = INTEGRATION_TEST_OUTPUT_DIR / "discover_modules-maven"


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
        print("Maven discover_modules() Integration Tests")
        print("=" * 60)
        print(f"Output directory: {OUTPUT_DIR}")
        print(f"Git directory: {ctx.git_dir}")
        print()

        for project in TEST_PROJECTS:
            print(f"\n--- {project.name} ---")
            print(f"Path: {project.relative_path}")
            print(f"Description: {project.description}")

            # Check if project exists
            if not ctx.validate_project(project):
                print("  SKIP: Project not found")
                continue

            test_count += 1
            project_path = project.absolute_path(ctx.git_dir)

            # Run discovery
            try:
                modules = ext.discover_modules(str(project_path))
                print(f"  Found: {len(modules)} module(s)")

                # Save result
                output_path = ctx.save_result(project, modules)
                print(f"  Saved: {output_path.name}")

                # Generate graph outputs (default and --full)
                save_graph_outputs(OUTPUT_DIR, project.name, modules, project_path)

                # Run assertions
                errors = []

                # Assert no null values (readme and description can be null)
                nulls = assert_no_null_values(
                    modules,
                    allowed_null_suffixes=[".readme", ".description"]
                )
                if nulls:
                    errors.append(f"Null values found at: {', '.join(nulls)}")

                # Assert paths exist
                missing = assert_paths_exist(modules, project_path)
                if missing:
                    errors.extend(missing)

                # Assert Maven-specific structure
                maven_errors = assert_maven_module_structure(modules)
                if maven_errors:
                    errors.extend(maven_errors)

                # Assert multi-module projects have root aggregator (if root pom.xml exists)
                root_errors = assert_has_root_aggregator(
                    modules, project_path, ["pom.xml"]
                )
                if root_errors:
                    errors.extend(root_errors)

                # Report results
                if errors:
                    print(f"  FAIL: {len(errors)} error(s)")
                    for err in errors:
                        print(f"    - {err}")
                    ctx.errors.extend([f"{project.name}: {e}" for e in errors])
                    all_passed = False
                else:
                    print("  PASS: All assertions passed")
                    pass_count += 1

                # Print module summary
                for mod in modules:
                    mod_name = mod.get("name", "?")
                    mod_path = mod.get("paths", {}).get("module", "?")
                    print(f"    - {mod_name} ({mod_path})")

            except Exception as e:
                print(f"  ERROR: {e}")
                ctx.errors.append(f"{project.name}: {e}")
                all_passed = False

        # Print summary
        ctx.print_summary()
        print(f"\nTests: {pass_count}/{test_count} passed")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())
