#!/usr/bin/env python3
"""Integration tests for hybrid module aggregation.

Tests the discover_project_modules() function which aggregates modules
from multiple extensions and merges hybrid modules (e.g., Maven + npm).

Results are persisted to .plan/temp/integration-tests/module-aggregation/ for inspection.

Run with:
    python3 test/plan-marshall/integration/module_aggregation/test_hybrid_merge.py
"""

import sys
from pathlib import Path

# Setup paths - conftest.py sets up PYTHONPATH for marketplace scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from integration_common import (
    INTEGRATION_TEST_OUTPUT_DIR,
    IntegrationTestContext,
    TestProject,
    assert_no_null_values,
)
from extension import discover_project_modules


# =============================================================================
# Test Projects Configuration
# =============================================================================

# Projects relative to git directory (parent of plan-marshall)
TEST_PROJECTS = [
    TestProject(
        name="nifi-extensions",
        relative_path="nifi-extensions",
        description="Hybrid Java+npm project with overlapping modules"
    ),
    TestProject(
        name="cui-jwt",
        relative_path="cui-jwt",
        description="Maven-only project (no npm)"
    ),
    TestProject(
        name="sample-monorepo",
        relative_path="other-test-projects/sample-monorepo",
        description="npm-only monorepo"
    ),
]

# Output directory for results
OUTPUT_DIR = INTEGRATION_TEST_OUTPUT_DIR / "module-aggregation"


# =============================================================================
# Hybrid Module Assertions
# =============================================================================

def assert_hybrid_module_structure(modules: dict) -> list[str]:
    """Validate hybrid module structure from discover_project_modules().

    Checks:
    - modules dict keyed by module name
    - all modules have build_systems array (always, even single-tech)
    - commands are nested for conflicts in multi-tech modules

    Args:
        modules: The "modules" dict from discover_project_modules() result

    Returns:
        List of validation errors
    """
    errors = []

    for name, module in modules.items():
        # Check required fields
        if "paths" not in module:
            errors.append(f"{name}: missing 'paths' field")

        # Check build_systems is present (always required, no 'technology' field anymore)
        if "build_systems" not in module:
            errors.append(f"{name}: missing 'build_systems' field")
        elif not isinstance(module["build_systems"], list):
            errors.append(f"{name}: 'build_systems' should be a list")
        elif len(module["build_systems"]) == 0:
            errors.append(f"{name}: 'build_systems' should not be empty")

        # technology field should not exist (deprecated)
        if "technology" in module:
            errors.append(f"{name}: has deprecated 'technology' field, should only have 'build_systems'")

        # If hybrid (multiple build systems), verify command nesting
        if "build_systems" in module:
            build_systems = module.get("build_systems", [])
            if len(build_systems) > 1:
                # Check commands have proper nesting for conflicts
                commands = module.get("commands", {})
                for cmd_name, cmd_value in commands.items():
                    # Commands can be either:
                    # - string (provided by one extension only)
                    # - dict (provided by multiple extensions, nested by tech)
                    if isinstance(cmd_value, dict):
                        # Verify nested keys match build systems
                        for tech in cmd_value.keys():
                            if tech not in build_systems:
                                errors.append(
                                    f"{name}: command '{cmd_name}' has tech '{tech}' not in build_systems {build_systems}"
                                )
                    elif not isinstance(cmd_value, str):
                        errors.append(f"{name}: command '{cmd_name}' should be string or dict")

        # Check stats structure if present
        stats = module.get("stats", {})
        if stats:
            if "source_files" not in stats:
                errors.append(f"{name}: stats missing 'source_files'")
            if "test_files" not in stats:
                errors.append(f"{name}: stats missing 'test_files'")

    return errors


def assert_extensions_used(result: dict, expected_extensions: list[str] | None = None) -> list[str]:
    """Validate extensions_used field in result.

    Args:
        result: The discover_project_modules() result
        expected_extensions: Optional list of expected extension names

    Returns:
        List of validation errors
    """
    errors = []

    if "extensions_used" not in result:
        errors.append("Result missing 'extensions_used' field")
        return errors

    extensions_used = result["extensions_used"]
    if not isinstance(extensions_used, list):
        errors.append(f"extensions_used should be list, got {type(extensions_used).__name__}")
        return errors

    if expected_extensions:
        for ext in expected_extensions:
            if ext not in extensions_used:
                errors.append(f"Expected extension '{ext}' not in extensions_used: {extensions_used}")

    return errors


# =============================================================================
# Integration Tests
# =============================================================================

def run_integration_tests() -> int:
    """Run all module aggregation integration tests.

    Returns:
        0 if all tests pass, 1 if any fail
    """
    all_passed = True
    test_count = 0
    pass_count = 0

    with IntegrationTestContext(OUTPUT_DIR, clean_before=True) as ctx:
        print("Module Aggregation Integration Tests")
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
                print(f"  SKIP: Project not found")
                continue

            test_count += 1
            project_path = project.absolute_path(ctx.git_dir)

            # Run discovery
            try:
                result = discover_project_modules(project_path)
                modules = result.get("modules", {})
                extensions = result.get("extensions_used", [])

                print(f"  Found: {len(modules)} module(s)")
                print(f"  Extensions: {extensions}")

                # Save result
                output_path = ctx.save_result(project, result)
                print(f"  Saved: {output_path.name}")

                # Run assertions
                errors = []

                # Assert extensions_used is valid
                ext_errors = assert_extensions_used(result)
                errors.extend(ext_errors)

                # Assert hybrid module structure
                hybrid_errors = assert_hybrid_module_structure(modules)
                errors.extend(hybrid_errors)

                # Assert no unexpected null values
                nulls = assert_no_null_values(
                    result,
                    allowed_null_suffixes=[".readme", ".description", ".parent"]
                )
                if nulls:
                    errors.append(f"Null values found at: {', '.join(nulls)}")

                # Report results
                if errors:
                    print(f"  FAIL: {len(errors)} error(s)")
                    for err in errors:
                        print(f"    - {err}")
                    ctx.errors.extend([f"{project.name}: {e}" for e in errors])
                    all_passed = False
                else:
                    print(f"  PASS: All assertions passed")
                    pass_count += 1

                # Print module summary
                for mod_name, mod in modules.items():
                    build_systems = mod.get("build_systems", ["?"])
                    mod_path = mod.get("paths", {}).get("module", "?")
                    print(f"    - {mod_name} {build_systems} ({mod_path})")

            except Exception as e:
                import traceback
                print(f"  ERROR: {e}")
                traceback.print_exc()
                ctx.errors.append(f"{project.name}: {e}")
                all_passed = False

        # Print summary
        ctx.print_summary()
        print(f"\nTests: {pass_count}/{test_count} passed")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())
