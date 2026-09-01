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
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from collections.abc import Iterator
from itertools import chain
from pathlib import Path

# Gate-coverage honesty helpers (freshness classification, the coverage-boundary
# reporter, and the derived parity population) live in a pure sibling module
# under the shared build-scripts dir, mirroring _test_scope_divergence. Put that
# dir on sys.path so the flat import resolves — the same mechanism
# _compute_mypypath() uses to reach marketplace_bundles.
_GATE_COVERAGE_DIR = (
    Path(__file__).parent
    / 'marketplace' / 'bundles' / 'plan-marshall'
    / 'skills' / 'script-shared' / 'scripts' / 'build'
)
if str(_GATE_COVERAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_GATE_COVERAGE_DIR))

from _gate_coverage import (  # noqa: E402
    CoverageBoundary,
    classify_check_duration,
    render_coverage_summary,
)

# Base paths
BUNDLES_DIR = Path('marketplace/bundles')
TEST_DIR = Path('test')
CLAUDE_DIR = Path('.claude')
TARGETS_DIR = Path('marketplace/targets')
# mypy's exclude patterns live in [tool.mypy] here. The emptiness guards below
# read them from this one declaration rather than restating them, so the guard
# and mypy always answer the same question about the same file set.
PYPROJECT_PATH = Path('pyproject.toml')

# Required SPDX header on every project-owned Python file (enforced below).
SPDX_HEADER = '# SPDX-License-Identifier: FSL-1.1-ALv2'
# PEP 263 encoding cookie: a comment matching coding[:=] on line 1 or 2.
_CODING_RE = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)')

# Native coverage threshold enforced by cmd_coverage via pytest's --cov-fail-under.
# Sourcing this from marshal.json (rather than a static constant) is deliberately
# deferred per the originating request constraint.
COVERAGE_THRESHOLD = 80

# The coverage dimensions each gate command performs at ANY scope, and (below) the
# subset a given invocation can reach at ITS scope. `_gate_coverage.coverage_gaps`
# needs BOTH to tell "absent because this invocation's scope did not include it"
# from "absent because this command never performs it at all" — two absences with
# different remedies. Deriving one from the other, or guessing either from the
# recorded boundary, is exactly how a module-scoped quality-gate came to print
# that the gate never performs plugin-doctor, which is false: it performs it
# whole-tree.
_QUALITY_GATE_DIMENSIONS = frozenset({'mypy(production)', 'ruff', 'SPDX headers', 'plugin-doctor'})
_VERIFY_DIMENSIONS = _QUALITY_GATE_DIMENSIONS | frozenset({'mypy(test)', 'module-tests'})


def _quality_gate_could_run(module: str | None) -> frozenset[str]:
    """Return the dimensions a ``quality-gate`` invocation reaches at ``module``'s scope.

    The marketplace-wide plugin-doctor pass is whole-tree only, so a module-scoped
    run cannot reach it. That is a statement about the SCOPE, not about the
    command, and keeping the two apart is the whole point of this declaration.
    """
    if module:
        return frozenset({'mypy(production)', 'ruff', 'SPDX headers'})
    return _QUALITY_GATE_DIMENSIONS


def _verify_could_run(module: str | None) -> frozenset[str]:
    """Return the dimensions a ``verify`` invocation reaches at ``module``'s scope.

    ``verify`` is ``quality-gate`` plus the test-tree type-check and the test run,
    neither of which is scope-restricted beyond the module filter itself.
    """
    return _quality_gate_could_run(module) | frozenset({'mypy(test)', 'module-tests'})


# Distinct non-zero exit code for a freshness-suspect type-check: mypy reported
# success but implausibly fast for the file set it claims to have checked, so the
# verdict rests on a cache, not on the current tree. Kept distinct from mypy's own
# 1 (type errors) and 2 (usage/collection error) so a caller can tell a fail-closed
# freshness halt from a real type error and render the PARTIAL coverage verdict.
_FRESHNESS_SUSPECT_RC = 3

# Per-session pytest basetemp root. Each pytest invocation gets its own
# per-session subdirectory here (see _prepare_session_basetemp) instead of the
# shared pytest-of-{user} root, so concurrent worktrees and a killed-then-
# restarted session never share a basetemp and never race each other's cleanup.
PYTEST_BASETEMP_ROOT = Path('.plan/temp/pytest-basetemp')
# Retention is bounded on TWO dimensions, because neither implies the other and
# only the second is the one that actually grows.
#
# PYTEST_BASETEMP_KEEP bounds how MANY per-session dirs survive a prune. It
# exists because an explicit --basetemp forgoes pytest's own keep-last-3
# retention. It says nothing about how large those dirs are: three retained
# sessions of ~92k entries each satisfies it exactly, and that is precisely the
# 276,757-entry / 1.0 GB root measured on this repository.
PYTEST_BASETEMP_KEEP = 3
# PYTEST_BASETEMP_MAX_ENTRIES bounds the total filesystem entries retained
# across those dirs — the dimension the count bound leaves free. Sized to admit
# roughly one session of the measured size, so a suite whose sessions are small
# keeps all PYTEST_BASETEMP_KEEP of them and only a suite that produces large
# sessions retains fewer.
#
# Denominated in ENTRIES rather than bytes for the same reason
# git-workflow.py::_count_tree_entries is: os.walk consumes the directory-entry
# names scandir already supplies, so the measurement needs no per-entry stat and
# stays cheap over a tree with hundreds of thousands of files. Both surfaces
# therefore measure the same dimension in the same unit — there is no second,
# independent notion of "size" here. That helper is mirrored rather than
# imported because `git-workflow.py` is a hyphenated module in another bundle,
# so it is not importable by name, and reaching it through importlib would pull
# its whole provider/executor import chain into this build script.
PYTEST_BASETEMP_MAX_ENTRIES = 100_000


def _count_entries_within(root: Path, headroom: int) -> int | None:
    """Return the entry count under ``root``, or ``None`` when it does not fit.

    ``None`` means no exact count at or below ``headroom`` could be established:
    either the walk passed ``headroom`` (the tree provably does not fit) or it
    could not read the whole tree (the true count is unknown). Both outcomes
    retire the directory, which is why they share a return value; what they must
    NOT share is a number. A count the walk never established is
    indistinguishable from a measured one once it is added to a running total,
    and that running total is what decides how much history survives — so an
    unreadable tree reports ``None``, never ``0``, and is never admitted as a
    free one.

    Only directory-entry names are consumed (``scandir`` supplies the
    directory/file split without a per-entry ``stat``), and the walk stops as
    soon as the answer is decided, so its cost is bounded by ``headroom`` rather
    than by the tree. ``followlinks=False`` is stated rather than left to the
    default so the walk provably cannot leave the tree through a symlink and
    count some other directory's entries into this budget.
    """
    entries = 0
    yielded = False
    unreadable = False

    def _note_unreadable(_exc: OSError) -> None:
        nonlocal unreadable
        unreadable = True

    for _dirpath, dirnames, filenames in os.walk(root, onerror=_note_unreadable, followlinks=False):
        yielded = True
        entries += len(dirnames) + len(filenames)
        if entries > headroom:
            return None
    if not yielded or unreadable:
        return None
    return entries


def _prune_basetemp_roots(
    keep: int = PYTEST_BASETEMP_KEEP,
    max_entries: int = PYTEST_BASETEMP_MAX_ENTRIES,
) -> None:
    """Retire per-session basetemp dirs until the root satisfies BOTH bounds.

    On return the root holds at most ``keep`` per-session dirs AND at most
    ``max_entries`` filesystem entries across them. Retention walks newest-first
    and stops at the first dir that would breach either bound, so removal is
    oldest-first and the newest session's scratch is the last thing given up. A
    dir whose size could not be established exactly is retired rather than
    retained — admitting an unmeasured dir as free is how a count-only bound came
    to permit a 1.0 GB root in the first place.

    Best-effort: a prune failure (a dir vanishing mid-scan, a permission error,
    an unreadable subtree) never aborts the build — retention is a housekeeping
    concern, not a correctness gate — and a root that cannot be listed at all is
    left untouched. This is the retention step that replaces pytest's own
    keep-last-3 behaviour, which an explicit ``--basetemp`` disables.

    Concurrency-safe: an in-process test that invokes ``cmd_module_tests`` /
    ``cmd_coverage`` while the outer suite runs under xdist produces concurrent
    prunes over the shared root, so two callers can race to remove the same
    stale dir. ``shutil.rmtree(..., ignore_errors=True)`` does NOT fully cover
    that race — its fd-based safe walk raises ``FileNotFoundError`` directly from
    the ``os.fstat`` samestat guard when the directory vanishes mid-walk — so the
    per-dir removal is additionally wrapped to swallow ``OSError``.
    """
    try:
        session_dirs = sorted(
            (d for d in PYTEST_BASETEMP_ROOT.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return

    retained = 0
    retained_entries = 0
    for session in session_dirs[:keep]:
        counted = _count_entries_within(session, max_entries - retained_entries)
        if counted is None:
            break
        retained_entries += counted
        retained += 1

    for stale in session_dirs[retained:]:
        try:
            shutil.rmtree(stale, ignore_errors=True)
        except OSError:
            # A concurrent prune removed ``stale`` mid-walk (the samestat guard
            # in shutil's fd-based rmtree can raise past ignore_errors). The dir
            # is already gone, which is the desired end state — keep pruning.
            continue


def _prepare_session_basetemp() -> Path:
    """Return a unique per-session pytest ``--basetemp`` path, bounding growth.

    The session key combines the current pid with a uuid4, so concurrent
    worktrees and a killed-then-restarted session that reuses a pid never share
    a basetemp root. Sharing the default ``pytest-of-{user}`` root is what lets
    pytest's keep-last-3 ``rm_rf`` cleanup race across concurrent/killed
    sessions; under ``filterwarnings=["error"]`` that race promotes a cleanup
    ``OSError`` into a session-killing exception on an otherwise-green suite.

    The root is created if missing and pruned before the new path is returned,
    so the RETAINED history is bounded on both dimensions
    :func:`_prune_basetemp_roots` enforces: at most ``PYTEST_BASETEMP_KEEP``
    per-session dirs, holding at most ``PYTEST_BASETEMP_MAX_ENTRIES`` entries
    between them. The session about to run is NOT bounded by this function — it
    is created after the prune and grows as the suite writes to it. Bringing it
    back inside the budget is the next invocation's prune.
    """
    PYTEST_BASETEMP_ROOT.mkdir(parents=True, exist_ok=True)
    _prune_basetemp_roots()
    return PYTEST_BASETEMP_ROOT / f'{os.getpid()}-{uuid.uuid4().hex}'


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


def _mypy_exclude_patterns(label: str = 'mypy') -> list[re.Pattern[str]]:
    """Return the compiled ``[tool.mypy] exclude`` regexes declared in pyproject.toml.

    Fails open by design: an unreadable config, a malformed ``exclude`` value, or
    an uncompilable pattern yields FEWER exclusions, so ``_mypy_collects_any``
    answers "there is something to check" and mypy still runs. The guards built
    on it may suppress a mypy invocation only when the configuration is known and
    nothing survives it. ``pyproject.toml`` is externally-sourced config, so an
    ``exclude`` that is neither a string nor a list (a typo such as
    ``exclude = true``) is a real input this boundary must absorb rather than
    raise ``TypeError`` through every caller.

    ``label`` prefixes the two diagnostics below. It is threaded from the calling
    command rather than hardcoded because this helper is reachable from BOTH
    ``compile`` and ``test-compile``; attributing a ``test-compile`` diagnostic to
    ``compile`` would send an operator to the wrong command. The default is the
    command-neutral ``mypy`` so a caller that cannot name a command still emits an
    honest prefix rather than a wrong one.
    """
    try:
        with PYPROJECT_PATH.open('rb') as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f'{label}: could not read mypy excludes from {PYPROJECT_PATH} ({exc}) — assuming none',
              file=sys.stderr)
        return []
    raw = config.get('tool', {}).get('mypy', {}).get('exclude', [])
    if isinstance(raw, str):
        raw = [raw]
    elif not isinstance(raw, list):
        print(f'{label}: ignoring malformed [tool.mypy] exclude of type '
              f'{type(raw).__name__} (expected string or list) — assuming none',
              file=sys.stderr)
        raw = []
    patterns: list[re.Pattern[str]] = []
    for entry in raw:
        try:
            patterns.append(re.compile(entry))
        except re.error as exc:
            print(f'{label}: ignoring uncompilable [tool.mypy] exclude {entry!r} ({exc})', file=sys.stderr)
    return patterns


def _mypy_collects_any(path: str, label: str = 'mypy') -> bool:
    """Return True when at least one file under ``path`` survives mypy's excludes.

    This is the exclude-AWARE emptiness predicate. "Does any ``.py`` file exist"
    answers a different question and misses the case this guard exists for: a
    bundle whose only Python file is excluded tree-wide plainly contains a
    ``.py`` file, yet mypy collects nothing there and exits 2 with "There are no
    .py[i] files in directory". Matching mirrors mypy's own crawl — ``re.search``
    of each configured pattern against the POSIX path as passed on the command
    line — so the two agree on which files are in scope.
    """
    target = Path(path)
    if target.is_dir():
        candidates: Iterator[Path] = chain(target.rglob('*.py'), target.rglob('*.pyi'))
    elif target.is_file() and target.suffix in ('.py', '.pyi'):
        candidates = iter((target,))
    else:
        return False
    patterns = _mypy_exclude_patterns(label)
    return any(
        not any(pattern.search(candidate.as_posix()) for pattern in patterns)
        for candidate in candidates
    )


def _mypy_collect_count(paths: list[str]) -> int:
    """Count the files under ``paths`` that survive mypy's excludes.

    A conservative lower bound on the work a mypy invocation over ``paths``
    represents: it counts the files passed on the command line that mypy would
    collect (the import graph mypy actually analyses is a superset). Undercounting
    is safe for the freshness backstop — it lowers the implied throughput, which
    only makes a run *less* likely to be judged implausibly fast. Mirrors the
    exclude-aware crawl of :func:`_mypy_collects_any` so the count agrees with what
    mypy sees.
    """
    patterns = _mypy_exclude_patterns()
    count = 0
    for entry in paths:
        target = Path(entry)
        if target.is_dir():
            candidates: Iterator[Path] = chain(target.rglob('*.py'), target.rglob('*.pyi'))
        elif target.is_file() and target.suffix in ('.py', '.pyi'):
            candidates = iter((target,))
        else:
            continue
        for candidate in candidates:
            if not any(pattern.search(candidate.as_posix()) for pattern in patterns):
                count += 1
    return count


def _run_mypy(
    paths: list[str],
    description: str,
    env: dict[str, str],
    *,
    dimension: str,
    boundary: CoverageBoundary | None = None,
) -> int:
    """Run mypy over ``paths`` COLD, with a freshness backstop, recording coverage.

    Two gate-honesty properties (plan 160 D4) ride on every mypy invocation:

    1. **Cold, like CI.** ``--no-incremental`` is always passed, so the verdict is
       computed against the current tree rather than a possibly-stale incremental
       cache. A fresh CI clone has no cache and runs cold; a developer machine
       keeps one across runs, and a stale cache answering "nothing I have cached
       changed" is exactly how a clean local verdict diverged from a red CI. This
       closes that hole deterministically — a cache the gate never consults cannot
       produce a false-clean.

    2. **Freshness backstop (gate paths only).** When a ``boundary`` is supplied
       (the ``verify`` / ``quality-gate`` paths assembling a coverage verdict), a
       mypy that exits 0 in a wall-time no real analysis of its file set could
       achieve is treated as suspect, not reassurance: the boundary records the
       degradation and the call returns :data:`_FRESHNESS_SUSPECT_RC` so the gate
       fails closed. A plausibly-timed run records the dimension as checked. Bare
       ``compile`` / ``test-compile`` (no boundary) still run cold but skip the
       gate-verdict machinery.

    A non-zero mypy exit (real type error) is returned unchanged; the caller halts
    and mypy's own output is the signal.
    """
    argv = ['uv', 'run', 'mypy', '--no-incremental', *paths]
    start = time.monotonic()
    exit_code = run(argv, description, env=env)
    elapsed = time.monotonic() - start
    if exit_code != 0:
        return exit_code
    if boundary is not None:
        files_checked = _mypy_collect_count(paths)
        verdict = classify_check_duration(files_checked, elapsed)
        if not verdict.plausible:
            print(f'>>> {description}: FRESHNESS SUSPECT — {verdict.reason}', file=sys.stderr)
            boundary.record_degraded(dimension, f'freshness suspect — {verdict.reason}')
            return _FRESHNESS_SUSPECT_RC
        boundary.record_checked(f'{dimension} [{files_checked} files, cache disabled]')
    return exit_code


def _skip_empty_mypy_scope(command: str, path: str) -> bool:
    """Report whether ``command`` must skip mypy over ``path``, printing the reason.

    Returns True (and explains the skip on stdout) when no file under ``path``
    survives mypy's configured excludes. Nothing is weakened: those files are
    excluded tree-wide, so the whole-tree run does not type-check them either —
    the scoped run reporting "nothing to check" merely matches that truth
    instead of surfacing mypy's exit 2 as a defect that does not exist.
    """
    if _mypy_collects_any(path, command):
        return False
    print(f'>>> {command}: skipping mypy for {path} — no file there survives the '
          f'[tool.mypy] exclude patterns in {PYPROJECT_PATH} (nothing to type-check)')
    return True


def cmd_compile(module: str | None, boundary: CoverageBoundary | None = None) -> int:
    """Run mypy on production sources (cold; freshness-checked on the gate paths)."""
    path = get_bundle_path(module)
    mypy_env = {**os.environ, 'MYPYPATH': _compute_mypypath()}
    if module:
        if _skip_empty_mypy_scope('compile', path):
            # Record the empty scope rather than returning silently. An unrecorded
            # skip leaves the dimension indistinguishable from one this gate never
            # performs, so the verdict would report a skipped type-check as an
            # absence rather than as "reached it, nothing there to check".
            if boundary is not None:
                boundary.record_empty_scope(
                    'mypy(production)',
                    f'{path} — no file survives the [tool.mypy] exclude patterns in {PYPROJECT_PATH}',
                )
            return 0
        return _run_mypy([path], f'compile: mypy {path}', mypy_env,
                         dimension='mypy(production)', boundary=boundary)
    paths = [path]
    # Include .claude/ only when a file there survives mypy's excludes. Passing a
    # directory mypy collects nothing from makes it fail with "There are no
    # .py[i] files in directory '.claude'" (exit 2), which breaks CI whenever the
    # repo ships no top-level skill scripts — or ships them only under the
    # excluded .claude/worktrees/, which an exclude-blind .py count would miss.
    if _mypy_collects_any(str(CLAUDE_DIR), 'compile'):
        paths.append(str(CLAUDE_DIR))
    return _run_mypy(paths, f'compile: mypy {" ".join(paths)}', mypy_env,
                     dimension='mypy(production)', boundary=boundary)


def cmd_test_compile(module: str | None, boundary: CoverageBoundary | None = None) -> int:
    """Run mypy on test sources (cold; freshness-checked on the gate paths)."""
    path = get_test_path(module)
    mypy_env = {**os.environ, 'MYPYPATH': _compute_mypypath()}
    if _skip_empty_mypy_scope('test-compile', path):
        # Same contract as cmd_compile's module arm: an unrecorded skip is
        # indistinguishable from a dimension the gate never performs.
        if boundary is not None:
            boundary.record_empty_scope(
                'mypy(test)',
                f'{path} — no file survives the [tool.mypy] exclude patterns in {PYPROJECT_PATH}',
            )
        return 0
    return _run_mypy([path], f'test-compile: mypy {path}', mypy_env,
                     dimension='mypy(test)', boundary=boundary)


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
    basetemp = _prepare_session_basetemp()
    cmd = ['uv', 'run', 'pytest', path, f'--basetemp={basetemp}']
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


def ensure_executor_substrate() -> int:
    """Generate ``.plan/execute-script.py`` when it is absent; 0 on success.

    The marketplace-wide plugin-doctor gate below derives the argument-naming
    cluster's whole accept-set from this executor, and the path is **git-ignored**
    — a fresh clone carries none, which is exactly what CI runs on. Without this
    step the cluster reports ``ARGUMENT_NAMING_SUBSTRATE_ABSENT`` on every CI run:
    the gate fails not because the corpus is wrong but because CI never had the
    substrate to judge it. Generating it here is what lets CI actually examine the
    2800-odd documented invocations instead of reporting that it could not.

    The alternatives were considered and rejected for the same reason: dropping
    the rule's severity to warning, or scoping the cluster out of the CI gate,
    each keep CI green while leaving it structurally blind to argument-naming
    drift — which is the false-clean the rule exists to remove, moved one layer
    out to the gate that consumes it.

    **Fail closed.** A generation failure returns non-zero and halts the gate
    rather than letting plugin-doctor run against an absent registry. Proceeding
    would produce a substrate-absent finding whose real cause is this step, and a
    reader would triage the corpus instead of the bootstrap.

    Idempotent and local-safe: an executor that already exists is left untouched,
    so a developer machine's own (possibly newer) executor is never overwritten by
    the gate.
    """
    executor = Path('.plan/execute-script.py')
    if executor.is_file():
        print(f'>>> quality-gate: executor substrate present at {executor}')
        return 0
    generator = (
        BUNDLES_DIR / 'plan-marshall' / 'skills' / 'tools-script-executor'
        / 'scripts' / 'generate_executor.py'
    )
    # Invoked by DIRECT PATH, never through .plan/execute-script.py — the file
    # this step exists to create cannot be the thing that dispatches its own
    # creation.
    exit_code = run(
        ['python3', str(generator), 'generate', '--marketplace', '--marketplace-root', '.'],
        'quality-gate: bootstrapping the executor substrate (absent — fresh checkout)',
    )
    if exit_code != 0:
        print('quality-gate: executor generation FAILED — the argument-naming cluster '
              'has no notation registry to judge against, so this gate cannot report on '
              'it. Halting rather than running plugin-doctor over an absent substrate.',
              file=sys.stderr)
        return exit_code
    if not executor.is_file():
        print(f'quality-gate: executor generation reported success but {executor} does '
              'not exist. Halting: a zero exit code is not evidence the file landed.',
              file=sys.stderr)
        return 1
    return 0


def cmd_quality_gate(module: str | None, boundary: CoverageBoundary | None = None) -> int:
    """Run mypy + ruff + plugin-doctor static-analysis on production sources.

    For full-tree quality-gate (module is None), also runs the plugin-doctor
    quality-gate subcommand which enforces marketplace-wide static-analysis
    invariants (argparse safety, extension-point contracts, argument-naming
    cluster). Module-scoped quality-gate skips the marketplace-wide sweep
    because it is scoped to a single bundle.

    Records each dimension it clears into a :class:`CoverageBoundary` (plan 160
    D5) so the run's own output can distinguish a full pass from a partial one.
    When called standalone (no ``boundary`` supplied) it owns the boundary and
    prints the coverage summary; when ``cmd_verify`` supplies one, the caller
    owns the consolidated summary instead.
    """
    owns_summary = boundary is None
    if boundary is None:
        boundary = CoverageBoundary()

    exit_code = cmd_compile(module, boundary=boundary)
    # A freshness-suspect type-check is a fail-closed halt, not a plain failure:
    # surface the PARTIAL coverage verdict so a reader sees the gate did not
    # certify the tree, then stop.
    if exit_code == _FRESHNESS_SUSPECT_RC:
        if owns_summary:
            print(render_coverage_summary(
                boundary, _quality_gate_could_run(module), _QUALITY_GATE_DIMENSIONS))
        return exit_code
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
        paths = [str(BUNDLES_DIR), str(TARGETS_DIR), str(TEST_DIR), str(CLAUDE_DIR)]

    exit_code = run(['uv', 'run', 'ruff', 'check'] + paths, f'quality-gate: ruff check {" ".join(paths)}')
    if exit_code != 0:
        return exit_code
    boundary.record_checked(f'ruff [{", ".join(paths)}]')

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
    boundary.record_checked(f'SPDX headers [{", ".join(spdx_paths)}]')

    if module is None:
        exit_code = ensure_executor_substrate()
        if exit_code != 0:
            return exit_code
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
        if exit_code != 0:
            return exit_code
        boundary.record_checked('plugin-doctor [marketplace-wide]')

    if owns_summary:
        print(render_coverage_summary(
            boundary, _quality_gate_could_run(module), _QUALITY_GATE_DIMENSIONS))
    return exit_code


def cmd_coverage(module: str | None) -> int:
    """Run pytest with coverage.

    Parallel by default, mirroring ``cmd_module_tests``: the coverage run
    executes the identical full suite, so it must ride pytest-xdist (``-n auto``)
    too — a serial coverage run is the same ~10k tests on a single core and
    walls in at several times the parallel test runtime, which pushed it past
    the background-duration ceiling and got it killed mid-suite. pytest-cov
    supports xdist natively: each worker writes its own coverage data file and
    pytest-cov combines them at session end before applying ``--cov-fail-under``.
    ``--dist=loadgroup`` is mandatory whenever ``-n`` is active so ``xdist_group``
    markers (e.g. the ``real_marshal_json`` group that touches shared real
    ``.plan/`` state) keep their tests pinned to a single worker.
    """
    test_path = get_test_path(module)
    bundle_path = get_bundle_path(module)

    # Ensure output directory exists
    Path('.plan/temp').mkdir(parents=True, exist_ok=True)

    basetemp = _prepare_session_basetemp()
    cmd = [
        'uv', 'run', 'pytest', test_path,
        f'--basetemp={basetemp}',
        '-n', 'auto', '--dist=loadgroup',
        f'--cov={bundle_path}',
        '--cov-report=html:.plan/temp/htmlcov',
        '--cov-report=xml:.plan/temp/coverage.xml',
        f'--cov-fail-under={COVERAGE_THRESHOLD}',
    ]
    return run(cmd, f'coverage: pytest {test_path} --cov={bundle_path}')


def cmd_verify(module: str | None) -> int:
    """Run full verification: quality-gate + test-compile + module-tests.

    Threads one :class:`CoverageBoundary` through the type-check steps (plan 160
    D5) and prints a consolidated coverage verdict: COMPLETE when every dimension
    was checked over its full scope, PARTIAL — naming the un-certified dimension —
    when a step was freshness-suspect. A freshness-suspect halt returns
    :data:`_FRESHNESS_SUSPECT_RC` and prints the PARTIAL verdict so the failure is
    legible rather than read as a plain error.
    """
    print(f'=== verify: {"all" if not module else module} ===')
    boundary = CoverageBoundary()
    could_run = _verify_could_run(module)

    exit_code = cmd_quality_gate(module, boundary=boundary)
    if exit_code != 0:
        print('verify: quality-gate failed', file=sys.stderr)
        if exit_code == _FRESHNESS_SUSPECT_RC:
            print(render_coverage_summary(boundary, could_run, _VERIFY_DIMENSIONS))
        return exit_code

    exit_code = cmd_test_compile(module, boundary=boundary)
    if exit_code != 0:
        print('verify: test-compile failed', file=sys.stderr)
        if exit_code == _FRESHNESS_SUSPECT_RC:
            print(render_coverage_summary(boundary, could_run, _VERIFY_DIMENSIONS))
        return exit_code

    exit_code = cmd_module_tests(module, parallel=True)
    if exit_code != 0:
        print('verify: module-tests failed', file=sys.stderr)
        return exit_code
    boundary.record_checked('module-tests [whole-tree pytest]' if module is None else f'module-tests [{module}]')

    print(render_coverage_summary(boundary, could_run, _VERIFY_DIMENSIONS))
    print('=== verify: SUCCESS ===')
    return 0


def cmd_clean() -> int:
    """Clean build artifacts."""
    dirs = ['.venv', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.plan/temp']
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f'Removing {d}')
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
