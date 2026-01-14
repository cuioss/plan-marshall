#!/usr/bin/env python3
"""Integration tests for npm discover_modules().

Tests npm module discovery against real projects in the local git directory.
Results are persisted to .plan/temp/test-results-npm/ for inspection.

Run with:
    python3 test/pm-dev-frontend/integration/discover_modules/test_npm_discover_modules.py
"""

import importlib.util
import sys
from pathlib import Path

# Modules under test (PYTHONPATH set by conftest)
from integration_common import (
    INTEGRATION_TEST_OUTPUT_DIR,
    IntegrationContext,
    ProjectFixture,
    assert_has_root_aggregator,
    assert_no_null_values,
    assert_npm_module_structure,
    assert_paths_exist,
)

# Use importlib to avoid module naming conflicts with other Extension classes
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-dev-frontend' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
)


def _load_npm_extension():
    """Load npm Extension class avoiding conflicts."""
    spec = importlib.util.spec_from_file_location('npm_extension', EXTENSION_FILE)
    npm_ext = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(npm_ext)
    return npm_ext.Extension


Extension = _load_npm_extension()


# =============================================================================
# Test Projects Configuration
# =============================================================================

# Projects relative to git directory (parent of plan-marshall)
TEST_PROJECTS = [
    ProjectFixture(
        name='sample-monorepo',
        relative_path='other-test-projects/sample-monorepo',
        description='npm workspaces monorepo with 3 packages',
    ),
    ProjectFixture(
        name='nifi-extensions',
        relative_path='nifi-extensions',
        description='Hybrid Java+npm project with 2 npm modules',
    ),
    ProjectFixture(
        name='OAuth-Sheriff', relative_path='OAuth-Sheriff', description='Nested npm module in Java project'
    ),
]

# Output directory for results
OUTPUT_DIR = INTEGRATION_TEST_OUTPUT_DIR / 'discover_modules-npm'


# =============================================================================
# Integration Tests
# =============================================================================


def run_integration_tests() -> int:
    """Run all npm discover_modules integration tests.

    Returns:
        0 if all tests pass, 1 if any fail
    """
    ext = Extension()
    all_passed = True
    test_count = 0
    pass_count = 0

    with IntegrationContext(OUTPUT_DIR, clean_before=True) as ctx:
        print('npm discover_modules() Integration Tests')
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

                # Save result
                output_path = ctx.save_result(project, modules)
                print(f'  Saved: {output_path.name}')

                # Run assertions
                errors = []

                # Assert no null values
                nulls = assert_no_null_values(modules)
                if nulls:
                    errors.append(f'Null values found at: {", ".join(nulls)}')

                # Assert paths exist
                missing = assert_paths_exist(modules, project_path)
                if missing:
                    errors.extend(missing)

                # Assert npm-specific structure
                npm_errors = assert_npm_module_structure(modules)
                if npm_errors:
                    errors.extend(npm_errors)

                # Assert multi-module projects have root aggregator (if root package.json exists)
                root_errors = assert_has_root_aggregator(modules, project_path, ['package.json'])
                if root_errors:
                    errors.extend(root_errors)

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
