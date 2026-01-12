#!/usr/bin/env python3
"""
Central test runner for plan-marshall.

Usage:
    python3 test/run-tests.py                    # Run all tests
    python3 test/run-tests.py test/pm-workflow/     # Run tests in directory
    python3 test/run-tests.py test/pm-workflow/plan-files/test_parse_plan.py  # Run single test

Features:
    - Centralized test fixture directory at .plan/temp/test-fixture/{timestamp}
    - Automatic cleanup after test run
    - Sets TEST_FIXTURE_DIR environment variable for tests
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent
PLAN_DIR_NAME = '.plan'  # Configurable plan directory name
TEST_FIXTURE_BASE = PROJECT_ROOT / PLAN_DIR_NAME / 'temp' / 'test-fixture'
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'


def build_marketplace_pythonpath() -> str:
    """
    Build PYTHONPATH for cross-skill imports, mirroring executor behavior.

    The executor (.plan/execute-script.py) builds PYTHONPATH from all script
    directories so scripts can import from any skill. This function does the
    same for tests.

    Returns:
        Colon-separated PYTHONPATH string
    """
    script_dirs = set()

    # Scan marketplace for all scripts/ directories
    for bundle_dir in MARKETPLACE_ROOT.iterdir():
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.exists():
            continue
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / 'scripts'
            if scripts_dir.exists():
                script_dirs.add(str(scripts_dir))

    return ':'.join(sorted(script_dirs))


# Build PYTHONPATH once at startup
_MARKETPLACE_PYTHONPATH = build_marketplace_pythonpath()


def find_test_files(path: Path) -> list[Path]:
    """Find all test files in a path."""
    if path.is_file():
        return [path] if path.name.startswith('test_') and path.suffix == '.py' else []
    return sorted(path.rglob('test_*.py'))


def create_test_fixture_dir() -> Path:
    """
    Create a timestamped test fixture directory.

    Returns:
        Path to .plan/temp/test-fixture/{timestamp}
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    fixture_dir = TEST_FIXTURE_BASE / timestamp
    fixture_dir.mkdir(parents=True, exist_ok=True)
    return fixture_dir


def cleanup_test_fixture_dir(fixture_dir: Path) -> None:
    """
    Remove the test fixture directory.

    Args:
        fixture_dir: Path to the fixture directory to remove
    """
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir, ignore_errors=True)


def run_test(test_file: Path, fixture_dir: Path) -> tuple[bool, str]:
    """
    Run a single test file. Returns (success, output).

    Args:
        test_file: Path to the test file
        fixture_dir: Path to the test fixture directory
    """
    env = os.environ.copy()
    env['TEST_FIXTURE_DIR'] = str(fixture_dir)
    env['PLAN_BASE_DIR'] = str(fixture_dir)  # Default for plan-based tests
    env['PLAN_DIR_NAME'] = PLAN_DIR_NAME  # Directory name for path construction

    # Add test root (for conftest.py) and marketplace script dirs to PYTHONPATH
    existing_pythonpath = env.get('PYTHONPATH', '')
    test_root_path = str(TEST_ROOT)
    full_pythonpath = test_root_path + ':' + _MARKETPLACE_PYTHONPATH
    env['PYTHONPATH'] = full_pythonpath + (':' + existing_pythonpath if existing_pythonpath else '')

    result = subprocess.run(
        [sys.executable, str(test_file)],
        capture_output=True,
        text=True,
        cwd=TEST_ROOT.parent,
        env=env
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def main():
    # Determine test path
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.is_absolute():
            target = TEST_ROOT.parent / target
    else:
        target = TEST_ROOT

    if not target.exists():
        print(f"Error: Path not found: {target}")
        sys.exit(1)

    # Find test files
    test_files = find_test_files(target)
    if not test_files:
        print(f"No test files found in: {target}")
        sys.exit(1)

    # Create centralized test fixture directory
    fixture_dir = create_test_fixture_dir()
    print(f"Test fixture directory: {fixture_dir}")
    print(f"Running {len(test_files)} test file(s)...")
    print("=" * 60)

    passed = 0
    failed = 0
    failed_tests = []

    try:
        for test_file in test_files:
            relative_path = test_file.relative_to(TEST_ROOT.parent)
            success, output = run_test(test_file, fixture_dir)

            if success:
                passed += 1
                print(f"  ✓ {relative_path}")
            else:
                failed += 1
                failed_tests.append((relative_path, output))
                print(f"  ✗ {relative_path}")

        print("=" * 60)
        print(f"Passed: {passed}, Failed: {failed}")

        # Show failure details
        if failed_tests:
            print("\nFailure details:")
            for path, output in failed_tests:
                print(f"\n--- {path} ---")
                print(output)

    finally:
        # Always cleanup the fixture directory
        cleanup_test_fixture_dir(fixture_dir)
        print(f"\nCleaned up: {fixture_dir}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
