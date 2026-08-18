#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The one build-extension fixture surface, shared by all six ``build-*`` directories.

Stages the extension contract every build backend implements — coverage
reports, ``ExecuteConfig`` construction, the ``run`` subcommand, the
``run-config-key`` contract, and the ``BuildExtension`` (Axis-B) file-to-build
map — so the six directories assert one contract through one surface instead of
staging it six times.

Underscore-prefixed so pytest does not collect it and the ``plugin-doctor``
``unique-fixture-basenames`` rule (which enumerates only ``_``-prefixed helper
modules) can see it.

Usage:
    from _build_extension_fixtures import assert_coverage_high, execute_config, ...

⛔ LOADING THE FACTORY HERE RE-REGISTERS IT IN ``sys.modules``.
:func:`assert_run_config_key_contract` resolves ``compute_command_key`` through
``conftest.load_script_module``, and that helper REGISTERS the module it builds
under its own stem — unlike a bare ``spec_from_file_location``. The registration
REPLACES whatever ``sys.modules['_build_execute_factory']`` previously held, so a
test module that already did ``import _build_execute_factory as factory`` at its
own import time keeps a copy that is no longer reachable from ``sys.modules`` at
all; it survives only as a reference in that module's globals.

``test/conftest.py``'s ``_neutralize_daemon_routing`` fixture depends on exactly
this fact. ``cmd_run`` is a CLOSURE, so it resolves the ``_route_to_daemon`` seam
from ``cmd_run.__globals__`` — the globals of whichever factory copy produced it,
not from whatever ``sys.modules`` currently maps the name to. That is why the
fixture patches closure ``__globals__`` DICTS rather than a module object:
patching the module object would be silently partial, and load-order dependent,
which makes getting it wrong a flaky green rather than a clean red.

Two consequences bind anything added to this module:

* Do NOT hoist the factory load to module scope. Loading it here at import time
  would register a copy at a DIFFERENT moment than the lazy call below, adding a
  second live copy to a hazard that already has two.
* :func:`build_scripts_dir` deliberately only puts the build scripts directory on
  ``sys.path``; it does NOT import the factory. Each consumer keeps its own
  module-level ``import _build_execute_factory as factory`` so its binding timing
  is unchanged by sharing this bootstrap.
"""

import importlib.util
import sys

from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# =============================================================================
# Extension-contract staging — the surface all six build-* directories share
# =============================================================================


def build_scripts_dir():
    """Put ``script-shared/scripts/build`` on ``sys.path`` and return it.

    The build backends' shared modules (``_build_execute_factory``,
    ``_build_execute``, ``_build_server_protocol``) live outside every
    ``scripts/`` directory pytest already resolves, so a consumer must add that
    directory before importing them.

    Idempotent: the insert is skipped when the directory is already on the path.

    This function does NOT import the factory, and must not start doing so — see
    the ``sys.modules`` re-registration hazard in this module's docstring. The
    caller keeps its own module-level ``import _build_execute_factory as
    factory`` so that binding happens at the caller's import time, exactly as it
    did before this bootstrap was shared.

    Returns:
        The build scripts directory, so a caller can derive sibling paths.
    """
    build_dir = get_script_path('plan-marshall', 'script-shared', 'marketplace_paths.py').parent / 'build'
    if str(build_dir) not in sys.path:
        sys.path.insert(0, str(build_dir))
    return build_dir


def execute_config(factory, capture_strategy, **overrides):
    """Build the minimal ``ExecuteConfig`` that drives ``cmd_run`` in a test.

    The eight-field Maven-shaped baseline every routing and execution test
    starts from, with keyword overrides for the fields a given test varies.

    Args:
        factory: The consumer's own ``_build_execute_factory`` module object.
            Passed in rather than imported here so this module never binds a
            factory copy of its own (see the re-registration hazard above), and
            so the config is built from the SAME copy whose seams the caller
            patches.
        capture_strategy: The ``CaptureStrategy`` member for the backend.
        **overrides: Fields to replace in the baseline.

    Returns:
        A ``factory.ExecuteConfig`` instance.
    """
    base = {
        'tool_name': 'maven',
        'unix_wrapper': 'mvnw',
        'windows_wrapper': 'mvnw.cmd',
        'system_fallback': 'mvn',
        'capture_strategy': capture_strategy,
        'build_command_fn': factory.default_build_command_fn,
        'scope_fn': lambda a: 'default',
        'command_key_fn': factory.default_command_key_fn,
    }
    base.update(overrides)
    return factory.ExecuteConfig(**base)


def load_build_extension(skill, module_name):
    """Load a build skill's ``BuildExtension`` class WITHOUT registering it.

    Every build skill ships an ``extension.py`` sharing the module basename
    ``extension``, so each load is given an explicit distinct module name to
    avoid the cross-skill ``import extension`` collision.

    Uses ``spec_from_file_location``, which — unlike ``load_script_module`` —
    does NOT enter the module in ``sys.modules``. That is the point: two backends
    loaded here stay two distinct objects with independent module-level state,
    and neither displaces a registration another module already holds. A consumer
    that genuinely wants the registered form calls ``load_script_module``
    directly with its own distinct ``module_name``.

    Args:
        skill: The build skill's name, e.g. ``'build-maven'``.
        module_name: The distinct name to load under. Required, not derived, so
            two call sites loading the same skill cannot silently collapse onto
            one name.

    Returns:
        The skill's ``BuildExtension`` class.
    """
    extension_path = get_script_path('plan-marshall', skill, 'extension.py')
    spec = importlib.util.spec_from_file_location(module_name, extension_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load module from {extension_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BuildExtension


# =============================================================================
# Coverage Report Test Helpers
# =============================================================================


def assert_coverage_missing_file(script_path, report_path='/nonexistent/report'):
    """Test coverage-report with non-existent report returns error.

    Shared across all build tools — the behavior is identical.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        report_path,
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'report_not_found'
    return data


def assert_coverage_high(script_path, fixture_path, threshold=80):
    """Test coverage-report with report above threshold passes.

    Shared across all build tools — verifies status, passed, and line coverage.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is True
    assert float(data['overall']['line']) >= threshold
    return data


def assert_coverage_low(script_path, fixture_path, threshold=80):
    """Test coverage-report with report below threshold fails.

    Shared across all build tools — verifies status, passed=False, and message.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is False
    assert 'below threshold' in data['message']
    return data


def assert_coverage_has_low_items(script_path, fixture_path, threshold=80):
    """Test that low-coverage items are identified in report.

    Shared across all build tools — verifies low_coverage list is populated.
    Returns the data dict for tool-specific assertions on item names.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
    )
    data = parse_toon(result.stdout)
    assert 'low_coverage' in data
    assert len(data['low_coverage']) > 0
    return data


def assert_coverage_custom_threshold(script_path, fixture_path, threshold):
    """Test coverage-report with custom threshold that passes.

    Shared across all build tools — verifies passed=True and threshold value.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['passed'] is True
    assert str(data['threshold']) == str(threshold)
    return data


#: The backend-invariant ``coverage-report`` cases, in execution order. Each
#: name is dispatched by :func:`run_coverage_report_case`; a backend
#: parametrizes over the subset its report format actually supports.
COVERAGE_REPORT_CASES = ('missing_file', 'high', 'low', 'low_items', 'custom_threshold')


def run_coverage_report_case(
    case,
    script_path,
    fixtures_dir,
    *,
    high_report='high-coverage.xml',
    low_report='low-coverage.xml',
    custom_threshold_report='high-coverage.xml',
    custom_threshold=60,
):
    """Dispatch one backend-invariant ``coverage-report`` case.

    Replaces the one-line wrapper function each backend used to re-declare per
    case. Every knob that genuinely differs per backend is a parameter: the
    fixtures directory, the report filenames (XML for the JaCoCo/Cobertura
    backends, JSON for npm), and the custom-threshold pair. Assertions that are
    NOT interchangeable — the per-backend low-coverage item-name checks — stay
    in the backend's own test module and call :func:`assert_coverage_has_low_items`
    directly.

    Args:
        case: One of :data:`COVERAGE_REPORT_CASES`.
        script_path: Path to the backend's entry script.
        fixtures_dir: The backend's own coverage fixtures directory.
        high_report: Filename of the above-threshold report fixture.
        low_report: Filename of the below-threshold report fixture.
        custom_threshold_report: Filename of the report the custom-threshold
            case runs against.
        custom_threshold: Threshold value that the custom-threshold case passes at.

    Returns:
        The parsed TOON data dict for the dispatched case.

    Raises:
        AssertionError: when the dispatched case's contract does not hold.
        ValueError: when ``case`` is not a known case name.
    """
    if case == 'missing_file':
        return assert_coverage_missing_file(script_path)
    if case == 'high':
        return assert_coverage_high(script_path, fixtures_dir / high_report)
    if case == 'low':
        return assert_coverage_low(script_path, fixtures_dir / low_report)
    if case == 'low_items':
        return assert_coverage_has_low_items(script_path, fixtures_dir / low_report)
    if case == 'custom_threshold':
        return assert_coverage_custom_threshold(
            script_path, fixtures_dir / custom_threshold_report, threshold=custom_threshold
        )
    raise ValueError(f'unknown coverage-report case: {case!r}')


# =============================================================================
# run-config-key Contract Helper
# =============================================================================


def assert_run_config_key_contract(script_path, build_tool, canonical_args, *, config, suffix_cases):
    """Assert the whole ``run-config-key`` contract for one build backend.

    Consolidates the five assertions every backend previously re-declared:

    1. **TOON shape** — ``status`` / ``build_tool`` / ``key_suffix`` /
       ``command_key`` are all present and correct.
    2. **JSON format** — ``--format json`` emits the same four fields as
       parseable JSON.
    3. **Canonical args mapping** — each ``(args, expected_suffix)`` case maps to
       the expected ``key_suffix`` and the full ``{build_tool}:{suffix}`` key.
    4. **Round-trip drift guard** — the CLI-emitted ``command_key`` matches
       ``compute_command_key(config, args)`` for every canonical args string.
       This is the structural guard against drift between the key
       ``run-config-key`` advertises and the key ``cmd_run`` persists via
       ``timeout_set`` at execute time; it runs once per backend.
    5. **Required-flag error path** — omitting ``--command-args`` is an
       argparse rejection (non-zero exit).

    Args:
        script_path: Path to the backend's entry script.
        build_tool: The backend's ``build_tool`` value (e.g. ``'gradle'``).
        canonical_args: Args strings driving the round-trip drift guard.
        config: The backend's own ``_CONFIG`` ExecuteConfig — the drift guard's
            left-hand side. Kept per-backend because the key function is
            backend-specific (Gradle strips leading colons and uses only the
            first task; the others use ``default_command_key_fn``).
        suffix_cases: ``(args, expected_suffix)`` pairs. The first pair doubles
            as the representative case for the TOON and JSON shape assertions.

    Raises:
        AssertionError: when any part of the contract does not hold.
    """
    compute_command_key = load_script_module(
        'plan-marshall', 'script-shared', 'build/_build_execute_factory.py'
    ).compute_command_key

    representative_args, representative_suffix = suffix_cases[0]

    # Spawn ``run-config-key --command-args X`` ONCE per UNIQUE args string, then
    # run every assertion below against the cached real-CLI TOON. The subcommand
    # is a pure, deterministic function of ``--command-args``, so a second
    # subprocess for an args string already spawned re-verifies nothing the first
    # did not. Previously the representative case (sections 1 + 3) and every
    # canonical arg (sections 3 + 4) were each spawned twice; deduping keeps the
    # full E2E surface — every DISTINCT CLI invocation still runs as a real
    # subprocess and every field is still asserted — while removing the redundant
    # process starts that dominated this test's wall-clock (a ~14→8 spawn drop for
    # the pyproject backend). Insertion order is preserved so a failure names a
    # stable arg.
    unique_args: list[str] = []
    for args in [a for a, _ in suffix_cases] + list(canonical_args):
        if args not in unique_args:
            unique_args.append(args)

    toon_by_args = {}
    for args in unique_args:
        result = run_script(script_path, 'run-config-key', '--command-args', args)
        assert result.success, f'Script failed for args={args!r}: {result.stderr}'
        toon_by_args[args] = result.toon()

    # 1. TOON shape (representative case).
    data = toon_by_args[representative_args]
    assert data['status'] == 'success'
    assert data['build_tool'] == build_tool
    assert data['key_suffix'] == representative_suffix
    assert data['command_key'] == f'{build_tool}:{representative_suffix}'

    # 2. JSON format emits the same four fields (distinct CLI invocation — the
    #    ``--format json`` surface is not covered by the TOON spawns above).
    result = run_script(
        script_path, 'run-config-key', '--command-args', representative_args, '--format', 'json'
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert data['status'] == 'success'
    assert data['build_tool'] == build_tool
    assert data['key_suffix'] == representative_suffix
    assert data['command_key'] == f'{build_tool}:{representative_suffix}'

    # 3. Canonical args -> key_suffix / command_key mapping.
    for args, expected_suffix in suffix_cases:
        data = toon_by_args[args]
        assert data['build_tool'] == build_tool
        assert data['key_suffix'] == expected_suffix, (
            f'key_suffix {data["key_suffix"]!r} != expected {expected_suffix!r} for args={args!r}'
        )
        assert data['command_key'] == f'{build_tool}:{expected_suffix}'

    # 4. Round-trip drift guard against compute_command_key.
    for args in canonical_args:
        expected_key = compute_command_key(config, args)
        data = toon_by_args[args]
        assert data['command_key'] == expected_key, (
            f'CLI command_key {data["command_key"]!r} drifted from '
            f'compute_command_key {expected_key!r} for args={args!r}'
        )

    # 5. Omitting --command-args is an argparse rejection (distinct invocation).
    result = run_script(script_path, 'run-config-key')
    assert not result.success, 'Expected non-zero exit when --command-args is omitted'


# =============================================================================
# Execute Config Test Helpers
# =============================================================================


def assert_execute_config(config, *, tool_name, unix_wrapper, system_fallback):
    """Verify ExecuteConfig has expected base fields.

    Shared across all build tools — checks tool_name, unix_wrapper, system_fallback.
    """
    assert config.tool_name == tool_name
    assert config.unix_wrapper == unix_wrapper
    assert config.system_fallback == system_fallback


def assert_command_key_fn(config, cases):
    """Test command_key_fn with multiple input/expected pairs.

    Args:
        config: ExecuteConfig instance.
        cases: List of (input, expected) tuples.
    """
    for args, expected in cases:
        result = config.command_key_fn(args)
        assert result == expected, f'command_key_fn({args!r}) = {result!r}, expected {expected!r}'


def assert_scope_fn(config, cases):
    """Test scope_fn with multiple input/expected pairs.

    Args:
        config: ExecuteConfig instance.
        cases: List of (input, expected) tuples.
    """
    for args, expected in cases:
        result = config.scope_fn(args)
        assert result == expected, f'scope_fn({args!r}) = {result!r}, expected {expected!r}'


# =============================================================================
# Run Subcommand Test Helpers
# =============================================================================


def assert_run_help(script_path):
    """Test that 'run --help' works without error.

    Shared across all build tools.
    """
    result = run_script(script_path, 'run', '--help')
    assert result.success, f'Help failed: {result.stderr}'
    assert 'command-args' in result.stdout.lower() or 'command_args' in result.stdout.lower()
