#!/usr/bin/env python3
"""
Shared test infrastructure for plan-marshall marketplace scripts.

This module provides base classes, fixtures, and utilities for testing
Python scripts in the marketplace bundles. Uses only Python stdlib.

Usage:
    from conftest import run_script, create_temp_file

See test/README.md for full documentation.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# =============================================================================
# Path Constants
# =============================================================================

TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'
PLAN_DIR_NAME = '.plan'  # Tracked config sub-directory inside the repo.
# Standalone test fixtures live under the repo-local .plan/temp/ so each
# worktree keeps its own isolated fixture tree and the existing
# ``Write(.plan/**)`` permission keeps covering them.
TEST_FIXTURE_BASE = PROJECT_ROOT / PLAN_DIR_NAME / 'temp' / 'test-fixture'


# =============================================================================
# Pytest Collection Configuration
# =============================================================================

# Integration tests with unresolvable import dependencies (``integration_common``,
# pm-dev-java ``extension`` module) — never resolvable in the unit-test
# PYTHONPATH and therefore always excluded from default collection.
collect_ignore = [
    'plan-marshall/integration/discover_modules/test_gradle_discover_modules_integration.py',
    'plan-marshall/integration/discover_modules/test_maven_discover_modules.py',
    'plan-marshall/integration/module_aggregation/test_hybrid_merge.py',
    # Real-tree smoke that walks the actual marketplace/bundles/ tree — kept out
    # of the default module-tests run so it uses only the in-process synthetic
    # units in tools-marketplace-inventory/test_scan_marketplace_inventory.py.
    'pm-plugin-development/tools-marketplace-inventory/integration/test_scan_marketplace_inventory_smoke.py',
    # Real-tree planning-scan smoke — the planning scanner spawns
    # scan-marketplace-inventory.py against the real tree. The per-filter /
    # statistics coverage lives in the in-process synthetic units in
    # tools-marketplace-inventory/test_scan_planning_inventory.py.
    'pm-plugin-development/tools-marketplace-inventory/integration/test_scan_planning_inventory_smoke.py',
    # Real-tree dependency-graph smokes — build a dependency index over the
    # actual marketplace/bundles/ tree (full validate + a real shipped chain).
    # The per-subcommand / per-filter / output-format coverage lives in the
    # in-process synthetic-graph units in
    # tools-marketplace-inventory/test_resolve_dependencies.py.
    'pm-plugin-development/tools-marketplace-inventory/integration/test_resolve_dependencies_smoke.py',
    # Real-tree manage-invocation smokes — derive the real script --help surface
    # against the live .plan/execute-script.py executor (zero-false-positive
    # checks for the loop-registered / shared-flag / many-subcommand shapes).
    # The per-shape / per-finding-type coverage lives in the in-process
    # synthetic-argparse units in
    # plugin-doctor/test_analyze_manage_invocation.py.
    'pm-plugin-development/plugin-doctor/integration/test_analyze_manage_invocation_smoke.py',
]


# =============================================================================
# Executor Bootstrap (CI session setup)
# =============================================================================

def _ensure_executor_present() -> None:
    """Generate ``.plan/execute-script.py`` if missing.

    The executor is gitignored, so a fresh checkout (CI runner, ephemeral
    container) doesn't have it. Several script-under-test invocations
    (e.g., ``tools-input-validation``'s lesson-ID anchor) subprocess to
    ``python3 .plan/execute-script.py ...`` and fail without it. Local
    developer environments have it from prior ``/marshall-steward`` runs;
    CI needs it bootstrapped at session start.

    Idempotent: re-runs are no-ops if the executor is already present.
    """
    executor_path = PROJECT_ROOT / PLAN_DIR_NAME / 'execute-script.py'
    if executor_path.exists():
        return

    generator = (
        MARKETPLACE_ROOT
        / 'plan-marshall'
        / 'skills'
        / 'tools-script-executor'
        / 'scripts'
        / 'generate_executor.py'
    )
    if not generator.exists():
        # Generator script missing — surface a clear message instead of a
        # cryptic FileNotFoundError downstream. Tests that depend on the
        # executor will still fail loudly.
        print(
            f'WARNING: conftest could not bootstrap executor — generator missing at {generator}',
            file=sys.stderr,
        )
        return

    try:
        subprocess.run(
            ['python3', str(generator), 'generate'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        # Failure here is non-fatal at conftest-import time. Tests that
        # genuinely need the executor will fail with their own diagnostics;
        # tests that don't need it (the majority) keep running.
        print(
            f'WARNING: conftest executor bootstrap failed: {exc}',
            file=sys.stderr,
        )


_ensure_executor_present()


# =============================================================================
# Cross-Skill Import Setup (mirrors executor PYTHONPATH)
# =============================================================================


def _setup_marketplace_pythonpath() -> list[str]:
    """
    Set up sys.path for cross-skill imports, mirroring executor behavior.

    The executor (.plan/execute-script.py) builds PYTHONPATH from all script
    directories so scripts can import from any skill. This function does the
    same for tests.

    Returns:
        List of directories added to sys.path
    """
    script_dirs = set()

    # Scan marketplace for all scripts/ directories and their immediate subdirectories
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
                # Scan immediate subdirectories (supports organized layouts
                # like script-shared/scripts/build/, scripts/extension/)
                for child in scripts_dir.iterdir():
                    if child.is_dir() and not child.name.startswith('.') and child.name != '__pycache__':
                        script_dirs.add(str(child))

    # Add to sys.path (avoid duplicates)
    added = []
    for script_dir in sorted(script_dirs):
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            added.append(script_dir)

    return added


# Set up PYTHONPATH immediately on import
_MARKETPLACE_SCRIPT_DIRS = _setup_marketplace_pythonpath()

# Pre-import cross-skill modules so that test files using
# sys.modules.setdefault('plan_logging', MagicMock(...)) at import time
# cannot shadow the real module for later tests.
import plan_logging as _plan_logging  # noqa: F401, E402
import run_config as _run_config  # noqa: F401, E402

# Add test subdirectories with shared helpers to sys.path so tests can
# import them without manual sys.path manipulation
_TEST_HELPER_DIRS = [
    str(TEST_ROOT / 'plan-marshall'),
    str(TEST_ROOT / 'pm-plugin-development'),
]
for _helper_dir in _TEST_HELPER_DIRS:
    if _helper_dir not in sys.path:
        sys.path.insert(0, _helper_dir)

# Shared isolation fixtures live directly in this root conftest rather than
# in bundle-scoped ``_fixtures.py`` modules: the production modules they
# redirect (``_providers_core``, ``_config_core``) live in the plan-marshall
# bundle but are used by tests across every bundle, so a single root-level
# fixture avoids duplication. Bundle-scoped fixture modules via
# ``pytest_plugins`` are still the right pattern for anything genuinely
# bundle-specific.


# =============================================================================
# Script Runner
# =============================================================================


class ScriptResult:
    """Result from running a script."""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def success(self) -> bool:
        """True if script exited with code 0."""
        return self.returncode == 0

    def json(self) -> dict[str, Any]:
        """Parse stdout as JSON. Raises ValueError if invalid."""
        if not self.stdout.strip():
            raise ValueError(f'Empty stdout. stderr: {self.stderr}')
        data: dict[str, Any] = json.loads(self.stdout)
        return data

    def toon(self) -> dict[str, Any]:
        """Parse stdout as TOON. Raises ValueError if invalid."""
        from toon_parser import parse_toon

        if not self.stdout.strip():
            raise ValueError(f'Empty stdout. stderr: {self.stderr}')
        data: dict[str, Any] = parse_toon(self.stdout)
        return data

    def json_or_error(self) -> dict[str, Any]:
        """Parse stdout as JSON, or stderr if stdout is empty."""
        if self.stdout.strip():
            data: dict[str, Any] = json.loads(self.stdout)
            return data
        if self.stderr.strip():
            data = json.loads(self.stderr)
            return data
        return {'error': 'No output'}

    def toon_or_error(self) -> dict[str, Any]:
        """Parse stdout as TOON, or stderr if stdout is empty."""
        from toon_parser import parse_toon

        if self.stdout.strip():
            data: dict[str, Any] = parse_toon(self.stdout)
            return data
        if self.stderr.strip():
            data = parse_toon(self.stderr)
            return data
        return {'error': 'No output'}

    def __repr__(self) -> str:
        return f'ScriptResult(returncode={self.returncode}, stdout={len(self.stdout)}b, stderr={len(self.stderr)}b)'


def run_script(
    script_path: str | Path,
    *args: str,
    input_data: str | None = None,
    cwd: str | Path | None = None,
    timeout: int = 30,
    env_overrides: dict[str, str] | None = None,
) -> ScriptResult:
    """
    Run a Python script and capture its output.

    Args:
        script_path: Path to the script to run
        *args: Command line arguments to pass
        input_data: Optional stdin input
        cwd: Working directory (defaults to current)
        timeout: Timeout in seconds (default 30)

    Returns:
        ScriptResult with returncode, stdout, stderr

    Example:
        result = run_script(SCRIPT_PATH, '--mode', 'structured', input_data=content)
        assert result.success
        data = result.json()
    """
    # Build environment with PYTHONPATH for cross-skill imports
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath

    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        [sys.executable, str(script_path)] + list(args),
        capture_output=True,
        text=True,
        input=input_data,
        cwd=cwd,
        timeout=timeout,
        env=env,
    )
    return ScriptResult(result.returncode, result.stdout, result.stderr)


def get_script_path(bundle: str, skill: str, script: str) -> Path:
    """
    Get the path to a marketplace script.

    Args:
        bundle: Bundle name (e.g., 'plan-marshall')
        skill: Skill name (e.g., 'plan-files')
        script: Script filename (e.g., 'parse-plan.py')

    Returns:
        Absolute path to the script

    Raises:
        FileNotFoundError: If script doesn't exist
    """
    path = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts' / script
    if not path.exists():
        raise FileNotFoundError(f'Script not found: {path}')
    return path


def get_scripts_dir(bundle: str, skill: str) -> Path:
    """Return the ``scripts/`` directory for a marketplace skill.

    Centralizes the scripts-dir resolution that test files previously open-coded
    as a per-test ``_SCRIPTS_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' /
    ... / 'scripts'`` constant. Resolution anchors on :data:`MARKETPLACE_ROOT`
    (the marketplace-bundles layout) — no per-test ``Path(__file__).parents[N]``
    arithmetic.

    Args:
        bundle: Bundle name (e.g., ``'plan-marshall'``).
        skill: Skill name (e.g., ``'plugin-doctor'``).

    Returns:
        Absolute path to ``<bundle>/skills/<skill>/scripts``.

    Raises:
        FileNotFoundError: when the resolved scripts directory does not exist.
    """
    scripts_dir = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts'
    if not scripts_dir.is_dir():
        raise FileNotFoundError(f'Scripts dir not found: {scripts_dir}')
    return scripts_dir


def load_script_module(bundle: str, skill: str, script_file: str, module_name: str | None = None):
    """Load a marketplace script as a module via ``spec_from_file_location``.

    Replaces the per-test ``importlib.util.spec_from_file_location`` +
    ``module_from_spec`` + ``exec_module`` boilerplate. The loaded module is
    registered in :data:`sys.modules` (matching the historical per-test pattern)
    so intra-module relative references and dataclass ``__module__`` lookups
    resolve correctly.

    Both root-level test layouts (``test/<bundle>/test_x.py``) and nested
    layouts (``test/<bundle>/<skill>/test_x.py``) use the same call — resolution
    is by ``(bundle, skill, script_file)``, never by the test file's own path.

    Args:
        bundle: Bundle name (e.g., ``'pm-plugin-development'``).
        skill: Skill name (e.g., ``'plugin-doctor'``).
        script_file: Script filename (e.g., ``'_analyze_verb_chains.py'``).
        module_name: Optional explicit module name for ``sys.modules``
            registration. Defaults to the script filename stem.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: when the script file does not exist.
        ImportError: when the module spec cannot be created or executed.
    """
    import importlib.util

    script_path = get_scripts_dir(bundle, skill) / script_file
    if not script_path.is_file():
        raise FileNotFoundError(f'Script not found: {script_path}')

    name = module_name or script_path.stem
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not create import spec for {script_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Temp File Helpers
# =============================================================================


def create_temp_file(content: str, suffix: str = '.md', dir: str | Path | None = None) -> Path:
    """
    Create a temporary file with content.

    Args:
        content: File content
        suffix: File extension (default .md)
        dir: Directory to create in (default system temp)

    Returns:
        Path to created file (caller must delete)

    Example:
        temp_file = create_temp_file("# Test\\nContent")
        try:
            result = run_script(SCRIPT, str(temp_file))
        finally:
            temp_file.unlink()
    """
    fd, path = tempfile.mkstemp(suffix=suffix, dir=dir)
    try:
        os.write(fd, content.encode('utf-8'))
    finally:
        os.close(fd)
    return Path(path)


def create_temp_dir() -> Path:
    """
    Create a temporary directory.

    Returns:
        Path to created directory (caller must delete with shutil.rmtree)
    """
    return Path(tempfile.mkdtemp())


# =============================================================================
# Pytest Fixtures
# =============================================================================

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_cwd():
    """Safety net fixture to restore cwd after each test.

    This ensures test isolation even if a test changes cwd without
    restoring it. Scripts should use script-relative paths, but this
    provides defense-in-depth against test pollution.
    """
    original_cwd = os.getcwd()
    yield
    if os.getcwd() != original_cwd:
        os.chdir(original_cwd)


_REAL_CREDENTIALS_DIR = Path.home() / '.plan-marshall-credentials'

# NOTE: ``.plan/local/run-configuration.json`` is intentionally NOT watched by
# the pollution guard. The ``pw`` build harness writes adaptive-timeout
# telemetry there on every invocation of ``module-tests``/``verify``/``coverage``,
# which is legitimate and necessary for timeout learning across runs. The guard
# cannot distinguish harness-authored writes from test-authored writes via
# mtime, so watching that file produces only false positives once tests are
# correctly isolated via ``plan_context`` (which sets ``PLAN_BASE_DIR`` so test
# subprocesses write to ``tmp_path`` rather than the real path anyway).


def _snapshot_real_paths() -> list[str]:
    """Snapshot the file listing of the real credentials directory.

    Returns a sorted list of relative filenames (empty if the directory does
    not exist).
    """
    try:
        return sorted(str(p.relative_to(_REAL_CREDENTIALS_DIR)) for p in _REAL_CREDENTIALS_DIR.rglob('*'))
    except FileNotFoundError:
        return []


# Backstop for the ``_plan_base_dir_sandbox`` autouse default: snapshot the real
# repo-local ``.plan/local/`` tree and fail any non-opted-out test that adds a
# new entry there. The sandbox redirects ``PLAN_BASE_DIR`` so writes *should* be
# structurally impossible; this guard verifies the redirect actually held rather
# than trusting it silently.
_REAL_PLAN_LOCAL = PROJECT_ROOT / PLAN_DIR_NAME / 'local'

# ``run-configuration.json`` lives at ``.plan/run-configuration.json`` (outside
# ``local/``) and is intentionally excluded from the credentials/local guards —
# see the NOTE above ``_REAL_CREDENTIALS_DIR``. The ``local/`` snapshot below is
# already scoped under ``local/`` so it never observes that file, but the
# basename is excluded defensively in case the build harness ever relocates its
# telemetry under ``local/``.
_PLAN_LOCAL_IGNORED_BASENAMES = frozenset({'run-configuration.json'})

# Leak-prone container dirs under ``.plan/local/`` whose IMMEDIATE children we
# snapshot one level deep. A leaking test creates a new orphan worktree dir
# (``worktrees/{name}``), plan dir (``plans/{id}``), or lesson
# (``lessons-learned/{id}``) — all visible as a new depth-2 entry. ``logs/`` is
# deliberately excluded: the log-pollution leak is an APPEND to an existing file
# (not a new path, so a path snapshot cannot catch it anyway), and it is already
# prevented structurally by the ``_plan_base_dir_sandbox`` PLAN_BASE_DIR redirect.
_PLAN_LOCAL_LEAK_DIRS = ('worktrees', 'plans', 'lessons-learned')


def _snapshot_real_plan_local() -> set[str]:
    """Snapshot a SHALLOW path listing of the real repo-local ``.plan/local/`` tree.

    Returns a set of relative path strings (empty if the directory does not
    exist). ``run-configuration.json`` is excluded so legitimate build-harness
    telemetry writes never register as pollution. The set return type lets the
    guard compute a pure ``after - before`` difference, so only NEW entries
    count as leaks (pre-existing developer state is ignored).

    Intentionally SHALLOW (depth-1 of ``.plan/local/`` plus depth-2 into the
    small leak-prone container dirs) — NOT ``rglob('*')``. A recursive walk
    descends into every worktree under ``.plan/local/worktrees/`` (each a full
    repo checkout) and the deep ``logs/`` tree, which made this O(100k+) per
    call and, running before+after every test, dominated the whole suite's
    wall-clock. The documented leaks (orphan worktree dirs, stray plan/lesson
    dirs) all surface at depth ≤2, so the shallow scan preserves detection at a
    fraction of the cost.
    """
    if not _REAL_PLAN_LOCAL.exists():
        return set()
    snapshot: set[str] = set()
    try:
        for child in _REAL_PLAN_LOCAL.iterdir():
            if child.name in _PLAN_LOCAL_IGNORED_BASENAMES:
                continue
            snapshot.add(child.name)
    except OSError:
        return snapshot
    for container in _PLAN_LOCAL_LEAK_DIRS:
        sub = _REAL_PLAN_LOCAL / container
        if not sub.is_dir():
            continue
        try:
            for entry in sub.iterdir():
                snapshot.add(f'{container}/{entry.name}')
        except OSError:
            pass
    return snapshot


@pytest.fixture(autouse=True)
def _pollution_guard(request):
    """Fail loudly if a test mutates the real ``~/.plan-marshall-credentials/``
    directory or adds entries to the real repo-local ``.plan/local/`` tree.

    The ``.plan/local/`` arm backstops the ``_plan_base_dir_sandbox`` autouse
    default (deliverable 1): that fixture redirects ``PLAN_BASE_DIR`` into a
    per-test tmp sandbox so writes into the real tree become structurally
    impossible. This guard verifies the redirect actually held — if any
    non-opted-out test leaks a new path into ``.plan/local/``, it fails loudly
    with the offending nodeid and the path delta rather than silently passing.

    Only NEW ``.plan/local/`` entries count (``after - before`` set difference),
    so pre-existing developer state never trips the guard. Each xdist worker
    computes its own before/after snapshot inside its own process, so the guard
    is worker-safe with no cross-worker shared state.

    Any test that legitimately needs to exercise the real credentials path or
    the real tracked ``.plan/`` tree can opt out with the shared
    ``@pytest.mark.allow_pollution`` marker (the same marker the autouse
    ``_plan_base_dir_sandbox`` honours — no second marker is introduced).
    """
    if request.node.get_closest_marker('allow_pollution'):
        yield
        return

    before_creds = _snapshot_real_paths()
    before_plan_local = _snapshot_real_plan_local()
    yield
    after_creds = _snapshot_real_paths()
    after_plan_local = _snapshot_real_plan_local()

    if before_creds != after_creds:
        pytest.fail(
            f'Pollution guard: test {request.node.nodeid} leaked into real paths:\n  '
            f'Test mutated {_REAL_CREDENTIALS_DIR} '
            f'(listing {before_creds} -> {after_creds})'
            "\n\nIsolate via plan_context + monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', ...), "
            'or mark with @pytest.mark.allow_pollution if intentional.'
        )

    new_plan_local = after_plan_local - before_plan_local
    if new_plan_local:
        pytest.fail(
            f'Pollution guard: test {request.node.nodeid} leaked into the real '
            f'{_REAL_PLAN_LOCAL} tree:\n  '
            f'New entries: {sorted(new_plan_local)}'
            '\n\nThe autouse _plan_base_dir_sandbox fixture should have redirected '
            'PLAN_BASE_DIR into a tmp sandbox — a leak here means the test (or a '
            'subprocess it spawned) resolved the real base dir instead. Ensure the '
            'test relies on the autouse sandbox (do not unset PLAN_BASE_DIR), or '
            'mark with @pytest.mark.allow_pollution if the real-tree write is '
            'intentional.'
        )


def pytest_configure(config):
    """Register markers used by the isolation fixtures and pollution guard."""
    config.addinivalue_line(
        'markers',
        'allow_pollution: test may legitimately mutate the real '
        '~/.plan-marshall-credentials/ directory or the tracked .plan/ tree '
        '(opts out of the autouse PLAN_BASE_DIR and CREDENTIALS_DIR sandboxes '
        'and the pollution guard).',
    )
    config.addinivalue_line(
        'markers',
        'xdist_group(name): pin all tests sharing the same group name to a '
        'single xdist worker (requires --dist=loadgroup).',
    )


@pytest.fixture(autouse=True)
def _plan_base_dir_sandbox(request, tmp_path_factory, monkeypatch):
    """Default ``PLAN_BASE_DIR`` to a per-test, xdist-worker-safe tmp sandbox.

    This is the root-cause isolation fix: rather than monkeypatching
    ``PLAN_BASE_DIR`` in each test that touches plan-marshall runtime state,
    EVERY test is redirected into an isolated sandbox directory by default.
    ``file_ops.get_base_dir()`` (the sole base-dir resolver) and every derived
    path (worktrees / logs / plans / lessons / findings / metrics) — plus
    ``plan_logging`` which delegates to it — resolve into the sandbox, so writes
    into the real repo ``.plan/local/`` tree become structurally impossible.

    Tests that intentionally exercise the real tracked ``.plan/`` tree opt out
    with ``@pytest.mark.allow_pollution``; for those the fixture is a no-op and
    the real resolvers fall back to the repo tree as before.

    xdist-safety: the sandbox is derived from ``tmp_path_factory``, whose
    ``getbasetemp()`` is already per-worker under ``-n`` runs (each worker owns a
    distinct ``…/popen-gw{N}/`` base), so two workers never collide on the same
    sandbox path.

    Composition with ``plan_context``: this autouse fixture runs first and sets
    a default; the explicit ``plan_context`` fixture (when requested) sets its
    own ``PLAN_BASE_DIR=tmp_path`` afterwards and therefore wins. ``BuildContext``
    / ``PlanContext`` likewise set their own ``PLAN_BASE_DIR`` and override the
    default.

    Subprocess propagation: the set is applied via ``monkeypatch.setenv`` so it
    lands in ``os.environ``; the ``run_script`` helper copies the live
    environment (``os.environ.copy()``), so child ``execute-script.py`` processes
    inherit the sandbox path and cannot write to the real tree either.
    """
    if request.node.get_closest_marker('allow_pollution'):
        # Real-tree tests must see the genuine resolvers — do not redirect.
        yield
        return

    sandbox = tmp_path_factory.mktemp('plan-base-sandbox')

    monkeypatch.setenv('PLAN_BASE_DIR', str(sandbox))
    monkeypatch.setenv('PLAN_DIR_NAME', PLAN_DIR_NAME)

    # Redirect in-process callers too. ``_config_core`` caches the resolved
    # paths at module-import time, so an env-var set alone does not reach
    # already-imported callers; patch the module attributes the same way
    # ``plan_context`` / ``PlanContext`` do. Imported lazily to avoid a
    # top-level import cycle during test bootstrap.
    import _config_core  # type: ignore[import-not-found]

    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', sandbox)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', sandbox / 'marshal.json')
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', sandbox / 'run-configuration.json')

    yield


@pytest.fixture(autouse=True)
def _credentials_dir_sandbox(request, tmp_path_factory, monkeypatch):
    """Default ``CREDENTIALS_DIR`` to a per-test, xdist-worker-safe tmp sandbox.

    The credentials sibling of ``_plan_base_dir_sandbox``: rather than relying on
    each provider/sonar test to remember to redirect the credential store, EVERY
    test is redirected into an isolated sandbox by default, so a credential
    ``save_credential`` / ``ensure_credentials_dir`` / ``touch_verified_at`` write
    into the real ``~/.plan-marshall-credentials/`` tree becomes structurally
    impossible. This closes the asymmetry the ``_pollution_guard`` exposed: the
    guard caught real-credentials leaks but there was no autouse redirect backing
    it, so a single un-isolated credential write (or a subprocess inheriting the
    real env) leaked into the developer's real credential dir.

    ``_providers_core.CREDENTIALS_DIR`` is bound at module-import time
    (``Path(os.environ.get('PLAN_MARSHALL_CREDENTIALS_DIR') or Path.home()/...)``),
    so an env-var set alone does not reach already-imported in-process callers;
    patch the module attribute the same way ``_plan_base_dir_sandbox`` patches
    ``_config_core``. The env-var set additionally propagates to subprocess
    callers (``run_script`` copies ``os.environ``), so child ``execute-script.py``
    processes resolve the sandbox at their own import time.

    Tests that intentionally exercise the real credentials path opt out with
    ``@pytest.mark.allow_pollution`` (the same marker the PLAN_BASE_DIR sandbox
    and the pollution guard honour). Tests that set their own per-test
    ``CREDENTIALS_DIR`` (via ``monkeypatch.setattr`` / ``monkeypatch.setenv``)
    still win — this fixture runs first and only sets a default.
    """
    if request.node.get_closest_marker('allow_pollution'):
        yield
        return

    sandbox = tmp_path_factory.mktemp('plan-credentials-sandbox')

    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(sandbox))

    # Redirect in-process callers too — the module constant is import-bound.
    # Imported lazily to avoid a top-level import cycle during test bootstrap.
    import _providers_core  # type: ignore[import-not-found]

    monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', sandbox)

    yield


@pytest.fixture
def plan_context(tmp_path, monkeypatch):
    """
    Pytest fixture for plan-based tests.

    Sets up isolation primitives (PLAN_BASE_DIR redirect to tmp_path) without
    hardcoding any specific plan_id. Tests pass their own plan_id strings into
    script calls and resolve the corresponding plan directory via
    ``plan_context.plan_dir_for(plan_id)``.

    Redirects ``_config_core.PLAN_BASE_DIR``, ``_config_core.MARSHAL_PATH``
    and ``_config_core.RUN_CONFIG_PATH`` via ``monkeypatch.setattr`` so
    in-process callers resolve against ``tmp_path`` instead of the real
    repo-local paths.

    ``_config_core`` is imported lazily inside the fixture body to avoid
    top-level import cycles during test bootstrap.

    Yields:
        Context: Context object with ``fixture_dir`` (= tmp_path), ``plans_dir``
            (= tmp_path / 'plans'), and a ``plan_dir_for(plan_id)`` helper that
            returns ``plans_dir / plan_id`` (creating the parent on demand,
            idempotent).
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('PLAN_DIR_NAME', PLAN_DIR_NAME)

    import _config_core  # type: ignore[import-not-found]

    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', tmp_path)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', tmp_path / 'marshal.json')
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', tmp_path / 'run-configuration.json')

    plans_dir = tmp_path / 'plans'
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Default plan_id used by tests that pass plan_context.plan_id verbatim into
    # script calls and read plan_context.plan_dir back. Tests that pass arbitrary
    # plan_id strings into script calls (e.g. 'batch-3', 'nf-add-prof') MUST
    # resolve their own dir via plan_context.plan_dir_for(<literal_plan_id>).
    DEFAULT_PLAN_ID = 'pytest-test'
    default_plan_dir = plans_dir / DEFAULT_PLAN_ID
    default_plan_dir.mkdir(parents=True, exist_ok=True)

    class Context:
        def __init__(self):
            self.fixture_dir = tmp_path
            self.plans_dir = plans_dir
            self.plan_id = DEFAULT_PLAN_ID
            self.plan_dir = default_plan_dir

        def plan_dir_for(self, plan_id):
            """Return ``plans_dir / plan_id``, creating it on demand (idempotent)."""
            d = self.plans_dir / plan_id
            d.mkdir(parents=True, exist_ok=True)
            return d

    yield Context()


# =============================================================================
# Utilities
# =============================================================================


def assert_json_structure(data: dict, expected_keys: list, context: str = ''):
    """
    Assert JSON has expected top-level keys.

    Args:
        data: Parsed JSON dict
        expected_keys: List of required keys
        context: Optional context for error message
    """
    missing = [k for k in expected_keys if k not in data]
    if missing:
        raise AssertionError(f'Missing keys {missing} in {context or "data"}: {list(data.keys())}')


def load_fixture(fixture_path: str | Path) -> str:
    """Load fixture file content."""
    path = Path(fixture_path)
    if not path.is_absolute():
        # Assume relative to test file's directory
        path = Path(os.getcwd()) / path
    return path.read_text()


# =============================================================================
# Plan Test Context
# =============================================================================


def get_test_fixture_dir() -> Path:
    """
    Get the test fixture directory.

    When run via test/run-tests.py, uses the TEST_FIXTURE_DIR environment variable.
    When run standalone, creates a directory in .plan/temp/test-fixture/.

    Returns:
        Path to the test fixture directory
    """
    env_dir = os.environ.get('TEST_FIXTURE_DIR')
    if env_dir:
        return Path(env_dir)

    # Fallback for standalone execution
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    fixture_dir = TEST_FIXTURE_BASE / f'standalone-{timestamp}'
    fixture_dir.mkdir(parents=True, exist_ok=True)
    return fixture_dir


class PlanContext:
    """
    Context manager for tests that need PLAN_BASE_DIR.

    Uses centralized test fixture directory instead of system temp.
    When run via test/run-tests.py, the fixture directory is managed
    by the runner and cleaned up automatically after all tests.

    Usage:
        with PlanContext(plan_id='my-plan') as ctx:
            result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'my-plan', ...)
            # ctx.fixture_dir contains the base directory
            # ctx.plan_dir contains the plan directory

    Attributes:
        fixture_dir: Base test fixture directory
        plan_id: The plan identifier
        plan_dir: Path to .../plans/{plan_id}
    """

    __test__ = False  # Not a test class - prevent pytest collection warning

    # Sentinel used to distinguish "attribute was missing" from "attribute was None"
    # in the _config_core save/restore book-keeping.
    _MISSING = object()

    def __init__(self, plan_id: str = 'test-plan'):
        """
        Initialize the test context.

        Args:
            plan_id: Plan identifier (kebab-case)
        """
        self.plan_id = plan_id
        self.fixture_dir: Path | None = None
        self.plan_dir: Path | None = None
        self._original_plan_base_dir: str | None = None
        self._original_plan_dir_name: str | None = None
        self._is_standalone: bool = False
        # Book-keeping for _config_core attribute restoration. Populated in
        # __enter__ so the module stays lazily imported.
        self._config_core_module: Any = None
        self._config_core_saved: dict[str, Any] = {}

    def __enter__(self) -> 'PlanContext':
        """Set up the test context."""
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        # Create plan directory structure
        self.plan_dir = self.fixture_dir / 'plans' / self.plan_id
        self.plan_dir.mkdir(parents=True, exist_ok=True)

        # Set PLAN_BASE_DIR and PLAN_DIR_NAME environment variables
        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        self._original_plan_dir_name = os.environ.get('PLAN_DIR_NAME')
        os.environ['PLAN_BASE_DIR'] = str(self.fixture_dir)
        os.environ['PLAN_DIR_NAME'] = PLAN_DIR_NAME

        # Redirect _config_core module-level paths so in-process callers
        # resolve against the fixture tree instead of the real repo-local
        # .plan/local/. Imported lazily to avoid top-level import cycles
        # during test bootstrap. Save originals for restoration in __exit__.
        import _config_core  # type: ignore[import-not-found]

        self._config_core_module = _config_core
        overrides = {
            'PLAN_BASE_DIR': self.fixture_dir,
            'MARSHAL_PATH': self.fixture_dir / 'marshal.json',
            'RUN_CONFIG_PATH': self.fixture_dir / 'run-configuration.json',
        }
        for attr, new_value in overrides.items():
            self._config_core_saved[attr] = getattr(_config_core, attr, self._MISSING)
            setattr(_config_core, attr, new_value)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test context."""
        # Restore _config_core attributes first so any teardown code that
        # touches it sees the original values.
        if self._config_core_module is not None:
            for attr, saved in self._config_core_saved.items():
                if saved is self._MISSING:
                    try:
                        delattr(self._config_core_module, attr)
                    except AttributeError:
                        pass
                else:
                    setattr(self._config_core_module, attr, saved)
            self._config_core_saved = {}
            self._config_core_module = None

        # Clean up the plan_dir to ensure test isolation
        # (when via runner, fixture_dir is shared but each test should get fresh plan_dir)
        if self.plan_dir and self.plan_dir.exists():
            shutil.rmtree(self.plan_dir, ignore_errors=True)

        # Clean up common files and directories to ensure test isolation
        if self.fixture_dir:
            files_to_clean = ['marshal.json', 'raw-project-data.json']
            for filename in files_to_clean:
                filepath = self.fixture_dir / filename
                if filepath.exists():
                    filepath.unlink()
            # Clean up directories that tests may create
            dirs_to_clean = [
                'project-architecture',
                PLAN_DIR_NAME,  # .plan directory - critical for run-config tests
            ]
            for dirname in dirs_to_clean:
                dirpath = self.fixture_dir / dirname
                if dirpath.exists():
                    shutil.rmtree(dirpath, ignore_errors=True)

        # Restore original PLAN_BASE_DIR
        if self._original_plan_base_dir is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir

        # Restore original PLAN_DIR_NAME
        if self._original_plan_dir_name is None:
            os.environ.pop('PLAN_DIR_NAME', None)
        else:
            os.environ['PLAN_DIR_NAME'] = self._original_plan_dir_name

        # Only cleanup fixture_dir if running standalone (not via run-tests.py)
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)


# =============================================================================
# Marshal.json Schema Constants
# =============================================================================

# Key names - use these constants instead of hardcoding strings
MARSHAL_KEY_SKILL_DOMAINS = 'skill_domains'
MARSHAL_KEY_SYSTEM = 'system'
MARSHAL_KEY_PLAN = 'plan'

# Default schema for marshal.json
#
# ``verification_steps`` (phase-5-execute) and ``steps`` (phase-6-finalize) are
# id-keyed maps: each key is a step id, each value is that step's nested param
# object (``{}`` when the step owns no params). Key insertion order is the
# execution order. Step-owned params nest under their owning step — here
# ``review_bot_buffer_seconds`` nests under ``default:automated-review`` rather
# than living as a flat sibling of ``steps``.
MARSHAL_SCHEMA_DEFAULT: dict[str, Any] = {
    MARSHAL_KEY_SKILL_DOMAINS: {'system': {}},
    MARSHAL_KEY_SYSTEM: {'retention': {}},
    MARSHAL_KEY_PLAN: {
        'phase-1-init': {'branch_strategy': 'direct'},
        'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
        'phase-5-execute': {
            'commit_and_push': True,
            'max_iterations': 5,
            'verification_steps': {
                'default:verify:quality-gate': {},
                'default:verify:module-tests': {},
            },
        },
        'phase-6-finalize': {
            'max_iterations': 3,
            'steps': {
                'default:commit-push': {},
                'default:create-pr': {},
                'default:automated-review': {'review_bot_buffer_seconds': 300},
                'default:sonar-roundtrip': {},
                'default:lessons-capture': {},
                'default:branch-cleanup': {},
                'default:archive-plan': {},
            },
        },
    },
}


def create_marshal_json(base_dir: Path, skill_domains: dict | None = None, extra: dict | None = None) -> Path:
    """
    Create marshal.json with proper schema.

    Args:
        base_dir: Directory to create .plan/marshal.json in (or directory containing marshal.json)
        skill_domains: Skill domains dict (optional, defaults to {"system": {}})
        extra: Additional top-level keys to merge (optional)

    Returns:
        Path to created marshal.json

    Example:
        marshal_path = create_marshal_json(temp_dir, skill_domains={
            "system": {"defaults": [...], "execute_task_skills": {...}}
        })
    """
    # Determine the correct location for marshal.json
    plan_dir = base_dir / '.plan'
    if not plan_dir.exists():
        plan_dir.mkdir(parents=True)
    marshal_path = plan_dir / 'marshal.json'

    # Build the data structure
    data = MARSHAL_SCHEMA_DEFAULT.copy()
    if skill_domains is not None:
        data[MARSHAL_KEY_SKILL_DOMAINS] = skill_domains
    if extra:
        data.update(extra)

    marshal_path.write_text(json.dumps(data, indent=2))
    return marshal_path


def create_raw_project_data(
    base_dir: Path,
    modules: list | None = None,
    module_details: dict | None = None,
    project_name: str | None = None,
    frameworks: list | None = None,
) -> Path:
    """
    Create raw-project-data.json with module facts.

    Args:
        base_dir: Directory to create .plan/raw-project-data.json in
        modules: List of module dicts with name, path, build_systems, packaging
        module_details: Dict of module_name -> enrichment data (packages, dependencies)
        project_name: Project name (defaults to base_dir.name)
        frameworks: List of detected frameworks

    Returns:
        Path to created raw-project-data.json

    Example:
        raw_data_path = create_raw_project_data(temp_dir, modules=[
            {"name": "core", "path": "core", "build_systems": ["maven"], "packaging": "jar"},
            {"name": "web", "path": "web", "build_systems": ["maven"], "packaging": "war"}
        ])
    """
    plan_dir = base_dir / '.plan'
    if not plan_dir.exists():
        plan_dir.mkdir(parents=True)
    raw_data_path = plan_dir / 'raw-project-data.json'

    data = {
        'project': {'name': project_name or base_dir.name},
        'frameworks': frameworks or [],
        'documentation': {'readme': '', 'doc_files': []},
        'modules': modules or [],
        'module_details': module_details or {},
    }

    raw_data_path.write_text(json.dumps(data, indent=2))
    return raw_data_path


# =============================================================================
# Build Test Context
# =============================================================================


class BuildContext:
    """
    Context manager for build-operations tests.

    Provides a complete test environment with:
    - Temporary directory for project files
    - .plan directory with marshal.json
    - Optional raw-project-data.json
    - Automatic cleanup

    Usage:
        with BuildContext() as ctx:
            # Create a pom.xml
            (ctx.temp_dir / 'pom.xml').write_text('<project></project>')

            # Run project-structure script
            result = run_script(SCRIPT_PATH, 'collect-raw-data', '--project-root', str(ctx.temp_dir))

            # Check marshal.json
            config = ctx.load_marshal_json()
            assert 'skill_domains' in config

    Attributes:
        temp_dir: Root directory for test files
        plan_dir: The .plan directory
    """

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self, modules: list | None = None, module_details: dict | None = None):
        """
        Initialize the build test context.

        Args:
            modules: Initial modules list for raw-project-data.json
            module_details: Initial module_details for raw-project-data.json
        """
        self.temp_dir: Path | None = None
        self.plan_dir: Path | None = None
        self._initial_modules = modules
        self._initial_module_details = module_details

    def __enter__(self) -> 'BuildContext':
        """Set up the test context."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plan_dir = self.temp_dir / '.plan'
        self.plan_dir.mkdir()

        # Isolate plan-marshall runtime state to this test's tmp dir.
        # file_ops.get_base_dir() honours PLAN_BASE_DIR and falls back the
        # tracked config dir to the same value — so marshal.json (staged at
        # {temp_dir}/.plan/marshal.json) and runtime state both land inside
        # the fixture tree, not the project-local <root>/.plan/local/.
        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        os.environ['PLAN_BASE_DIR'] = str(self.plan_dir)

        # Create initial marshal.json
        create_marshal_json(self.temp_dir)

        # Create raw-project-data.json if modules provided
        if self._initial_modules is not None:
            create_raw_project_data(
                self.temp_dir, modules=self._initial_modules, module_details=self._initial_module_details
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test context."""
        if getattr(self, '_original_plan_base_dir', None) is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def load_marshal_json(self) -> dict[str, Any]:
        """Load and return the current marshal.json content."""
        assert self.plan_dir is not None, 'BuildContext not entered'
        marshal_path = self.plan_dir / 'marshal.json'
        if not marshal_path.exists():
            raise FileNotFoundError(f'marshal.json not found at {marshal_path}')
        data: dict[str, Any] = json.loads(marshal_path.read_text())
        return data

    def load_raw_project_data(self) -> dict[str, Any]:
        """Load and return the current raw-project-data.json content."""
        assert self.plan_dir is not None, 'BuildContext not entered'
        raw_data_path = self.plan_dir / 'raw-project-data.json'
        if not raw_data_path.exists():
            raise FileNotFoundError(f'raw-project-data.json not found at {raw_data_path}')
        data: dict[str, Any] = json.loads(raw_data_path.read_text())
        return data

    def create_pom(
        self,
        path: str = '.',
        packaging: str = 'jar',
        artifact_id: str = 'test-module',
        with_quarkus: bool = False,
        profiles: list | None = None,
    ) -> Path:
        """
        Create a pom.xml file.

        Args:
            path: Relative path from temp_dir (default: root)
            packaging: Maven packaging type (jar, war, pom)
            artifact_id: Artifact ID
            with_quarkus: Include Quarkus plugin
            profiles: List of profile IDs to include

        Returns:
            Path to created pom.xml
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Build pom content
        parts = ['<project>']
        if packaging != 'jar':  # jar is default, no need to specify
            parts.append(f'  <packaging>{packaging}</packaging>')
        parts.append(f'  <artifactId>{artifact_id}</artifactId>')

        if with_quarkus:
            parts.append("""  <build>
    <plugins>
      <plugin>
        <groupId>io.quarkus</groupId>
        <artifactId>quarkus-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>""")

        if profiles:
            parts.append('  <profiles>')
            for profile_id in profiles:
                parts.append(f"""    <profile>
      <id>{profile_id}</id>
    </profile>""")
            parts.append('  </profiles>')

        parts.append('</project>')

        pom_path = target_dir / 'pom.xml'
        pom_path.write_text('\n'.join(parts))
        return pom_path

    def create_parent_pom(self, modules: list) -> Path:
        """
        Create a parent pom.xml with modules section.

        Args:
            modules: List of module directory names

        Returns:
            Path to created pom.xml
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        modules_xml = '\n'.join(f'    <module>{m}</module>' for m in modules)
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
{modules_xml}
  </modules>
</project>"""
        pom_path = self.temp_dir / 'pom.xml'
        pom_path.write_text(content)
        return pom_path

    def create_package_json(self, path: str = '.', name: str = 'test-module', version: str = '1.0.0') -> Path:
        """
        Create a package.json file.

        Args:
            path: Relative path from temp_dir (default: root)
            name: Package name
            version: Package version

        Returns:
            Path to created package.json
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        content = json.dumps({'name': name, 'version': version}, indent=2)
        pkg_path = target_dir / 'package.json'
        pkg_path.write_text(content)
        return pkg_path

    def create_build_gradle(
        self, path: str = '.', with_war: bool = False, with_quarkus: bool = False, kotlin: bool = False
    ) -> Path:
        """
        Create a build.gradle or build.gradle.kts file.

        Args:
            path: Relative path from temp_dir (default: root)
            with_war: Include war plugin
            with_quarkus: Include Quarkus plugin
            kotlin: Use Kotlin DSL (.kts)

        Returns:
            Path to created build file
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        if kotlin:
            plugins = ['java']
            if with_war:
                plugins.append('war')
            if with_quarkus:
                plugins.append('id("io.quarkus")')
            plugin_lines = '\n    '.join(plugins)
            content = f"""plugins {{
    {plugin_lines}
}}"""
            filename = 'build.gradle.kts'
        else:
            plugins = ['"java"']
            if with_war:
                plugins.append('"war"')
            plugin_block = ' '.join(f'id {p}' for p in plugins)
            content = f'plugins {{ {plugin_block} }}'
            if with_quarkus:
                content = 'plugins { id "java"\n    id "io.quarkus" }'
            filename = 'build.gradle'

        build_path = target_dir / filename
        build_path.write_text(content)
        return build_path
