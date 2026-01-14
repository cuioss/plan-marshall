#!/usr/bin/env python3
"""Build script with module filtering support.

Provides canonical commands (compile, test-compile, module-tests, quality-gate, coverage, verify)
with optional module filtering similar to Maven's -pl flag.

Usage:
    ./pw build compile                      # All production sources
    ./pw build compile pm-dev-frontend      # Single bundle
    ./pw build module-tests                 # All tests
    ./pw build module-tests pm-workflow     # Single test directory
    ./pw build verify pm-dev-java           # Full verification on single bundle
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Base paths
BUNDLES_DIR = Path('marketplace/bundles')
TEST_DIR = Path('test')


def run(cmd: list[str], description: str) -> int:
    """Run a command and return exit code."""
    print(f'>>> {description}')
    print(f'    {" ".join(cmd)}')
    result = subprocess.run(cmd)
    return result.returncode


def get_bundle_path(module: str | None) -> str:
    """Get bundle path, optionally filtered by module."""
    if module:
        path = BUNDLES_DIR / module
        if not path.exists():
            print(f'Error: Bundle not found: {path}', file=sys.stderr)
            sys.exit(1)
        return str(path)
    return str(BUNDLES_DIR)


def get_test_path(module: str | None) -> str:
    """Get test path, optionally filtered by module."""
    if module:
        path = TEST_DIR / module
        if not path.exists():
            print(f'Error: Test directory not found: {path}', file=sys.stderr)
            sys.exit(1)
        return str(path)
    return str(TEST_DIR)


def cmd_compile(module: str | None) -> int:
    """Run mypy on production sources."""
    path = get_bundle_path(module)
    return run(['uv', 'run', 'mypy', path], f'compile: mypy {path}')


def cmd_test_compile(module: str | None) -> int:
    """Run mypy on test sources."""
    path = get_test_path(module)
    return run(['uv', 'run', 'mypy', path], f'test-compile: mypy {path}')


def cmd_module_tests(module: str | None, parallel: bool = False) -> int:
    """Run pytest on test sources."""
    path = get_test_path(module)
    cmd = ['uv', 'run', 'pytest', path]
    if parallel:
        cmd.extend(['-n', 'auto'])
    return run(cmd, f'module-tests: pytest {path}')


def cmd_quality_gate(module: str | None) -> int:
    """Run ruff check on sources."""
    bundle_path = get_bundle_path(module)
    test_path = get_test_path(module) if module else str(TEST_DIR)

    # If module specified, only check that module's bundle and tests
    if module:
        paths = [bundle_path]
        if Path(test_path).exists():
            paths.append(test_path)
    else:
        paths = [str(BUNDLES_DIR), str(TEST_DIR)]

    return run(['uv', 'run', 'ruff', 'check'] + paths, f'quality-gate: ruff check {" ".join(paths)}')


def cmd_coverage(module: str | None) -> int:
    """Run pytest with coverage."""
    test_path = get_test_path(module)
    bundle_path = get_bundle_path(module)

    # Ensure output directory exists
    Path('.plan/temp').mkdir(parents=True, exist_ok=True)

    cmd = [
        'uv', 'run', 'pytest', test_path,
        f'--cov={bundle_path}',
        '--cov-report=html:.plan/temp/htmlcov'
    ]
    return run(cmd, f'coverage: pytest {test_path} --cov={bundle_path}')


def cmd_verify(module: str | None) -> int:
    """Run full verification: compile + quality-gate + module-tests."""
    print(f'=== verify: {"all" if not module else module} ===')

    exit_code = cmd_compile(module)
    if exit_code != 0:
        print('verify: compile failed', file=sys.stderr)
        return exit_code

    exit_code = cmd_quality_gate(module)
    if exit_code != 0:
        print('verify: quality-gate failed', file=sys.stderr)
        return exit_code

    exit_code = cmd_module_tests(module)
    if exit_code != 0:
        print('verify: module-tests failed', file=sys.stderr)
        return exit_code

    print('=== verify: SUCCESS ===')
    return 0


def cmd_clean() -> int:
    """Clean build artifacts."""
    dirs = ['.venv', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.plan/temp']
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f'Removing {d}')
            import shutil
            shutil.rmtree(path)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Build script with module filtering (canonical commands from extension_base.py)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s compile                    # mypy marketplace/bundles/
  %(prog)s compile pm-dev-frontend    # mypy marketplace/bundles/pm-dev-frontend
  %(prog)s module-tests               # pytest test/
  %(prog)s module-tests pm-workflow   # pytest test/pm-workflow
  %(prog)s verify pm-dev-java         # Full verification on single bundle
'''
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # compile
    p = subparsers.add_parser('compile', help='mypy on production sources')
    p.add_argument('module', nargs='?', help='Bundle name (e.g., pm-dev-frontend)')

    # test-compile
    p = subparsers.add_parser('test-compile', help='mypy on test sources')
    p.add_argument('module', nargs='?', help='Test directory (e.g., pm-workflow)')

    # module-tests
    p = subparsers.add_parser('module-tests', help='pytest on test sources')
    p.add_argument('module', nargs='?', help='Test directory (e.g., pm-workflow)')
    p.add_argument('--parallel', '-p', action='store_true', help='Run tests in parallel')

    # quality-gate
    p = subparsers.add_parser('quality-gate', help='ruff check on sources')
    p.add_argument('module', nargs='?', help='Module name (e.g., pm-dev-frontend)')

    # coverage
    p = subparsers.add_parser('coverage', help='pytest with coverage')
    p.add_argument('module', nargs='?', help='Module name (e.g., pm-dev-frontend)')

    # verify
    p = subparsers.add_parser('verify', help='Full verification (compile + quality-gate + module-tests)')
    p.add_argument('module', nargs='?', help='Module name (e.g., pm-dev-frontend)')

    # clean
    subparsers.add_parser('clean', help='Remove build artifacts')

    args = parser.parse_args()

    if args.command == 'compile':
        sys.exit(cmd_compile(args.module))
    elif args.command == 'test-compile':
        sys.exit(cmd_test_compile(args.module))
    elif args.command == 'module-tests':
        sys.exit(cmd_module_tests(args.module, getattr(args, 'parallel', False)))
    elif args.command == 'quality-gate':
        sys.exit(cmd_quality_gate(args.module))
    elif args.command == 'coverage':
        sys.exit(cmd_coverage(args.module))
    elif args.command == 'verify':
        sys.exit(cmd_verify(args.module))
    elif args.command == 'clean':
        sys.exit(cmd_clean())


if __name__ == '__main__':
    main()
