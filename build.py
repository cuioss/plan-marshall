#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build script with module filtering support.

Provides canonical commands (compile, test-compile, module-tests, quality-gate, coverage, verify)
with optional module filtering similar to Maven's -pl flag.

Usage:
    ./pw build compile                      # All production sources
    ./pw build compile pm-dev-frontend      # Single bundle
    ./pw build module-tests                 # All tests
    ./pw build module-tests plan-marshall     # Single test directory
    ./pw build verify pm-dev-java           # Full verification on single bundle
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Base paths
BUNDLES_DIR = Path('marketplace/bundles')
TEST_DIR = Path('test')
CLAUDE_DIR = Path('.claude')
TARGETS_DIR = Path('marketplace/targets')

# Required SPDX header on every project-owned Python file (enforced below).
SPDX_HEADER = '# SPDX-License-Identifier: FSL-1.1-ALv2'
# PEP 263 encoding cookie: a comment matching coding[:=] on line 1 or 2.
_CODING_RE = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)')

# Native coverage threshold enforced by cmd_coverage via pytest's --cov-fail-under.
# Sourcing this from marshal.json (rather than a static constant) is deliberately
# deferred per the originating request constraint.
COVERAGE_THRESHOLD = 70


# Single source of truth: delegate to collect_script_dirs so mypy_path matches runtime PYTHONPATH.
def _compute_mypypath() -> str:
    bundles_root = Path(__file__).parent / 'marketplace' / 'bundles'
    shared_scripts = str(bundles_root / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts')
    if shared_scripts not in sys.path:
        sys.path.insert(0, shared_scripts)
    from marketplace_bundles import collect_script_dirs
    return os.pathsep.join(collect_script_dirs(bundles_root))


def run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
    """Run a command and return exit code."""
    print(f'>>> {description}')
    print(f'    {" ".join(cmd)}')
    result = subprocess.run(cmd, env=env)
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
    mypy_env = {**os.environ, 'MYPYPATH': _compute_mypypath()}
    if module:
        return run(['uv', 'run', 'mypy', path], f'compile: mypy {path}', env=mypy_env)
    else:
        paths = [path]
        # Include .claude/ only if it exists and contains at least one .py file.
        # Passing an empty directory makes mypy fail with "There are no .py[i]
        # files in directory '.claude'" (exit 2), which breaks CI whenever the
        # repo happens to not ship any top-level skill scripts there.
        if CLAUDE_DIR.exists() and any(CLAUDE_DIR.rglob('*.py')):
            paths.append(str(CLAUDE_DIR))
        return run(['uv', 'run', 'mypy'] + paths, f'compile: mypy {" ".join(paths)}', env=mypy_env)


def cmd_test_compile(module: str | None) -> int:
    """Run mypy on test sources."""
    path = get_test_path(module)
    mypy_env = {**os.environ, 'MYPYPATH': _compute_mypypath()}
    return run(['uv', 'run', 'mypy', path], f'test-compile: mypy {path}', env=mypy_env)


def cmd_module_tests(module: str | None, parallel: bool = True) -> int:
    """Run pytest on test sources.

    Parallel by default: the canonical full-suite run uses pytest-xdist with
    ``-n auto`` so worker count tracks available CPUs. ``--dist=loadgroup`` is
    mandatory whenever ``-n`` is active so that ``xdist_group`` markers (e.g.
    the ``real_marshal_json`` group) keep their tests pinned to a single worker
    — without it, xdist scatters grouped tests across workers and the grouping
    is silently ignored. Pass ``parallel=False`` for serial single-file debug
    runs (CLI: ``--no-parallel``).
    """
    path = get_test_path(module)
    cmd = ['uv', 'run', 'pytest', path]
    if parallel:
        cmd.extend(['-n', 'auto', '--dist=loadgroup'])
    return run(cmd, f'module-tests: pytest {path}')


def check_spdx_headers(paths: list[str]) -> list[str]:
    """Return the list of project-owned .py files missing the FSL SPDX header.

    For each directory in ``paths``, every ``*.py`` file is examined; its first
    non-shebang, non-encoding-cookie line must equal ``SPDX_HEADER``. A file path
    in ``paths`` is checked directly. Pure-stdlib; introduces no new dependency.
    """
    offenders: list[str] = []
    for entry in paths:
        p = Path(entry)
        if p.is_file() and p.suffix == '.py':
            files = [p]
        elif p.is_dir():
            files = sorted(p.rglob('*.py'))
        else:
            continue
        for f in files:
            try:
                lines = f.read_text(encoding='utf-8').splitlines()
            except (UnicodeDecodeError, OSError) as exc:
                print(f'quality-gate: SPDX-header check could not read {f}: {exc}', file=sys.stderr)
                offenders.append(str(f))
                continue
            idx = 0
            if lines and lines[0].startswith('#!'):
                idx = 1
            if idx < len(lines) and _CODING_RE.match(lines[idx]):
                idx += 1
            candidate = lines[idx].rstrip('\n').rstrip('\r') if idx < len(lines) else None
            if candidate != SPDX_HEADER:
                offenders.append(str(f))
    return offenders


def cmd_quality_gate(module: str | None) -> int:
    """Run mypy + ruff + plugin-doctor static-analysis on production sources.

    For full-tree quality-gate (module is None), also runs the plugin-doctor
    quality-gate subcommand which enforces marketplace-wide static-analysis
    invariants (argparse safety, extension-point contracts, argument-naming
    cluster). Module-scoped quality-gate skips the marketplace-wide sweep
    because it is scoped to a single bundle.
    """
    exit_code = cmd_compile(module)
    if exit_code != 0:
        return exit_code

    bundle_path = get_bundle_path(module)
    test_path = get_test_path(module) if module else str(TEST_DIR)

    # If module specified, only check that module's bundle and tests
    if module:
        paths = [bundle_path]
        if Path(test_path).exists():
            paths.append(test_path)
    else:
        # Include .claude/ scripts when running full quality-gate
        paths = [str(BUNDLES_DIR), str(TEST_DIR), str(CLAUDE_DIR)]

    exit_code = run(['uv', 'run', 'ruff', 'check'] + paths, f'quality-gate: ruff check {" ".join(paths)}')
    if exit_code != 0:
        return exit_code

    # SPDX-header enforcement: every project-owned .py file in scope must carry
    # the FSL-1.1-ALv2 SPDX header. Full-tree runs also cover marketplace/targets
    # and build.py (the broader D5 scope beyond the ruff paths above).
    spdx_paths = list(paths)
    if module is None:
        spdx_paths += [str(TARGETS_DIR), 'build.py']
    offenders = check_spdx_headers(spdx_paths)
    if offenders:
        print('quality-gate: SPDX-header check FAILED — missing/incorrect header:', file=sys.stderr)
        for offender in offenders:
            print(f'    {offender}', file=sys.stderr)
        print(f'    Each file must carry "{SPDX_HEADER}" as its first non-shebang, non-encoding-cookie line.', file=sys.stderr)
        return 1
    print('>>> quality-gate: SPDX-header check passed')

    if module is None:
        doctor_script = (
            BUNDLES_DIR / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
            / 'scripts' / 'doctor-marketplace.py'
        )
        doctor_env = {**os.environ, 'PYTHONPATH': _compute_mypypath()}
        exit_code = run(
            ['python3', str(doctor_script), 'quality-gate'],
            'quality-gate: plugin-doctor static-analysis (marketplace-wide invariants)',
            env=doctor_env,
        )

    return exit_code


def cmd_coverage(module: str | None) -> int:
    """Run pytest with coverage."""
    test_path = get_test_path(module)
    bundle_path = get_bundle_path(module)

    # Ensure output directory exists
    Path('.plan/temp').mkdir(parents=True, exist_ok=True)

    cmd = [
        'uv', 'run', 'pytest', test_path,
        f'--cov={bundle_path}',
        '--cov-report=html:.plan/temp/htmlcov',
        '--cov-report=xml:.plan/temp/coverage.xml',
        f'--cov-fail-under={COVERAGE_THRESHOLD}',
    ]
    return run(cmd, f'coverage: pytest {test_path} --cov={bundle_path}')


def cmd_verify(module: str | None) -> int:
    """Run full verification: quality-gate + module-tests."""
    print(f'=== verify: {"all" if not module else module} ===')

    exit_code = cmd_quality_gate(module)
    if exit_code != 0:
        print('verify: quality-gate failed', file=sys.stderr)
        return exit_code

    exit_code = cmd_module_tests(module, parallel=True)
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
  %(prog)s module-tests plan-marshall   # pytest test/plan-marshall
  %(prog)s verify pm-dev-java         # Full verification on single bundle
'''
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # compile
    p = subparsers.add_parser('compile', help='mypy on production sources')
    p.add_argument('module', nargs='?', help='Bundle name (e.g., pm-dev-frontend)')

    # test-compile
    p = subparsers.add_parser('test-compile', help='mypy on test sources')
    p.add_argument('module', nargs='?', help='Test directory (e.g., plan-marshall)')

    # module-tests
    # Parallel-by-default (pytest-xdist -n auto --dist=loadgroup). --parallel/-p
    # is retained for backward compatibility (no-op: parallel is already the
    # default); --no-parallel opts into serial single-file debug runs.
    p = subparsers.add_parser('module-tests', help='pytest on test sources')
    p.add_argument('module', nargs='?', help='Test directory (e.g., plan-marshall)')
    p.add_argument('--parallel', '-p', dest='parallel', action='store_true', default=True,
                   help='Run tests in parallel (default; -n auto --dist=loadgroup)')
    p.add_argument('--no-parallel', dest='parallel', action='store_false',
                   help='Run tests serially (single-file debug)')

    # quality-gate
    p = subparsers.add_parser('quality-gate', help='mypy + ruff check on sources')
    p.add_argument('module', nargs='?', help='Module name (e.g., pm-dev-frontend)')

    # coverage
    p = subparsers.add_parser('coverage', help='pytest with coverage')
    p.add_argument('module', nargs='?', help='Module name (e.g., pm-dev-frontend)')

    # verify
    p = subparsers.add_parser('verify', help='Full verification (quality-gate + module-tests)')
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
