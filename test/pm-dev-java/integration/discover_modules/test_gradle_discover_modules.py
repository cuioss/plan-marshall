#!/usr/bin/env python3
"""Integration tests for Gradle discover_modules().

Tests Gradle module discovery against real projects in the local git directory.
Results are persisted to .plan/temp/test-results-gradle/ for inspection.

Run with:
    python3 test/pm-dev-java/integration/discover_modules/test_gradle_discover_modules.py
"""

import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "test"))

# Import Extension from pm-dev-java
EXTENSION_DIR = PROJECT_ROOT / "marketplace" / "bundles" / "pm-dev-java" / "skills" / "plan-marshall-plugin"
sys.path.insert(0, str(EXTENSION_DIR))

# Direct imports - conftest sets up PYTHONPATH for cross-skill imports
from extension import Extension  # noqa: E402

from integration_common import (  # noqa: E402
    INTEGRATION_TEST_OUTPUT_DIR,
    IntegrationContext,
    ProjectFixture,
    assert_gradle_module_structure,
    assert_has_root_aggregator,
    assert_no_null_values,
    assert_paths_exist,
)

# =============================================================================
# Test Projects Configuration
# =============================================================================

# Projects relative to git directory (parent of plan-marshall)
# Gradle-only projects (no Maven pom.xml at root)
TEST_PROJECTS = [
    ProjectFixture(
        name="mrlonis-spring-boot-monorepo",
        relative_path="other-test-projects/mrlonis-spring-boot-monorepo",
        description="Multi-module Gradle Spring Boot monorepo"
    ),
    ProjectFixture(
        name="logbee-gradle-plugins",
        relative_path="other-test-projects/logbee-gradle-plugins",
        description="Gradle plugin project (may have version incompatibility)"
    ),
]

# Output directory for results
OUTPUT_DIR = INTEGRATION_TEST_OUTPUT_DIR / "discover_modules-gradle"


# =============================================================================
# Integration Tests
# =============================================================================

def run_integration_tests() -> int:
    """Run all Gradle discover_modules integration tests.

    Returns:
        0 if all tests pass, 1 if any fail
    """
    ext = Extension()
    all_passed = True
    test_count = 0
    pass_count = 0

    with IntegrationContext(OUTPUT_DIR, clean_before=True) as ctx:
        print("Gradle discover_modules() Integration Tests")
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

                # Filter to only Gradle modules (Extension may return mixed)
                gradle_modules = [m for m in modules if "gradle" in m.get("build_systems", [])]
                print(f"  Found: {len(gradle_modules)} Gradle module(s)")

                # Save result
                output_path = ctx.save_result(project, gradle_modules)
                print(f"  Saved: {output_path.name}")

                # Run assertions
                errors = []

                # Count modules with errors vs successful
                error_modules = [m for m in gradle_modules if "error" in m]
                success_modules = [m for m in gradle_modules if "error" not in m]

                if error_modules:
                    print(f"  Note: {len(error_modules)} module(s) with errors (version incompatibility)")
                    for em in error_modules:
                        print(f"    - {em.get('name', '?')}: {em.get('error', '?')}")

                # Assert no null values (only on successful modules)
                if success_modules:
                    nulls = assert_no_null_values(success_modules)
                    if nulls:
                        errors.append(f"Null values found at: {', '.join(nulls)}")

                    # Assert paths exist (only on successful modules)
                    missing = assert_paths_exist(success_modules, project_path)
                    if missing:
                        errors.extend(missing)

                # Assert Gradle-specific structure (handles error modules gracefully)
                gradle_errors = assert_gradle_module_structure(gradle_modules)
                if gradle_errors:
                    errors.extend(gradle_errors)

                # Assert multi-module projects have root aggregator
                root_errors = assert_has_root_aggregator(
                    gradle_modules, project_path, ["build.gradle", "build.gradle.kts"]
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

                # Print module summary (successful ones)
                for mod in success_modules:
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
