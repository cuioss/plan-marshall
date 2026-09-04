#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared test infrastructure for plan-marshall marketplace scripts.

This module provides base classes, fixtures, and utilities for testing
Python scripts in the marketplace bundles. Uses only Python stdlib.

Usage:
    from conftest import run_script, create_temp_file

See test/README.md for the tree layout, what this module owns and deliberately
does not, and the rule for where a new helper belongs.
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

# =============================================================================
# Path Constants
# =============================================================================

TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'
PLAN_DIR_NAME = '.plan'  # Tracked config sub-directory inside the repo.
# Standalone test fixtures live under the repo-local .plan/temp/ so each
# worktree keeps its own isolated fixture tree and the existing
# ``Edit(.plan/**)`` permission keeps covering them.
TEST_FIXTURE_BASE = PROJECT_ROOT / PLAN_DIR_NAME / 'temp' / 'test-fixture'


# =============================================================================
# Pytest Collection Configuration
# =============================================================================

# Real-tree smoke tests — each spawns a scanner against the actual
# marketplace/bundles/ tree or the live executor, so they are slow and
# environment-coupled. They are excluded from default collection; the
# equivalent per-shape coverage lives in the in-process synthetic units named
# beside each entry.
collect_ignore = [
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

# Import the cross-skill modules the suite shares HERE, at root-conftest import
# time, which is before any test module is imported. That ordering is the whole
# point: whichever import runs first is the one that binds the name in
# ``sys.modules``, and every later importer gets that object. Binding them from
# the root conftest makes the real modules the ones every test sees, rather than
# leaving the binding to whichever test module happened to be collected first.
import plan_logging as _plan_logging  # noqa: F401, E402
import run_config as _run_config  # noqa: F401, E402

# Add test subdirectories with shared helpers to sys.path so tests can
# import them without manual sys.path manipulation
_TEST_HELPER_DIRS = [
    str(TEST_ROOT / 'plan-marshall'),
    str(TEST_ROOT / 'pm-plugin-development'),
    str(TEST_ROOT / '_shared'),
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


def get_skill_dir(bundle: str, skill: str) -> Path:
    """Return the root directory for a marketplace skill.

    The anchor for every file a skill ships, wherever it lives. :func:`get_scripts_dir`
    is the narrower accessor for the ``scripts/`` subtree and raises for a skill that
    has none; this one resolves the skill itself, so a module at the skill ROOT is
    addressable. The bundle ``plan-marshall-plugin`` skills are the shape that needs
    it: each ships a root-level ``extension.py``, and most of them ship no ``scripts/``
    directory at all for the scripts-relative accessor to resolve against.

    Args:
        bundle: Bundle name (e.g. ``'pm-dev-python'``).
        skill: Skill name (e.g. ``'plan-marshall-plugin'``).

    Returns:
        Absolute path to ``<bundle>/skills/<skill>``.

    Raises:
        FileNotFoundError: when the resolved skill directory does not exist.
    """
    skill_dir = MARKETPLACE_ROOT / bundle / 'skills' / skill
    if not skill_dir.is_dir():
        raise FileNotFoundError(f'Skill dir not found: {skill_dir}')
    return skill_dir


def add_skill_scripts_to_path(bundle: str, skill: str) -> Path:
    """Put a skill's ``scripts/`` directory on ``sys.path`` (idempotent).

    The narrow escape hatch for helper modules that :func:`load_script_module`
    cannot serve: a cluster of sibling scripts that reference **each other by
    bare name at import time**. Loading such a module by file location leaves
    its siblings unresolvable, so the directory itself must be importable.

    Prefer :func:`load_script_module` everywhere else — it needs no path
    mutation and keeps resolution keyed to ``(bundle, skill, script_file)``.

    Args:
        bundle: Bundle name (e.g., ``'plan-marshall'``).
        skill: Skill name (e.g., ``'plan-marshall'``).

    Returns:
        The scripts directory that is now on ``sys.path``.

    Raises:
        FileNotFoundError: when the resolved scripts directory does not exist.
    """
    scripts_dir = get_scripts_dir(bundle, skill)
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return scripts_dir


def load_script_module(
    bundle: str,
    skill: str,
    script_file: str,
    module_name: str | None = None,
    *,
    register: bool = True,
):
    """Load a marketplace script as a module via ``spec_from_file_location``.

    Replaces the per-test ``importlib.util.spec_from_file_location`` +
    ``module_from_spec`` + ``exec_module`` boilerplate. The loaded module is
    registered in :data:`sys.modules` (matching the historical per-test pattern)
    so intra-module relative references and dataclass ``__module__`` lookups
    resolve correctly.

    ⛔ That registration REPLACES any existing entry under the same name, and the
    displaced object does not disappear — a module that already did ``import X``
    keeps a reference to the old one, so the two copies coexist and only the loader's
    is reachable through ``sys.modules``. A later ``importlib.reload`` on the
    displaced copy then fails, and whether it does depends on collection order, which
    makes the defect a flaky green rather than a clean red. Two escapes are provided,
    and a caller that does not need the module reachable by name should take one:

    * ``module_name='...'`` publishes under a name of the caller's choosing, which
      can be made collision-proof;
    * ``register=False`` publishes nothing at all. Correct whenever the test only
      needs the returned object. It is NOT correct when the loaded module resolves
      its own name through ``sys.modules`` — a dataclass ``__module__`` lookup, or a
      ``pickle`` round-trip — which is what the default exists for.

    A guard test enumerates the names this function is called with across the test
    tree and fails when one of them is also imported plainly, so a collision
    introduced later is a red build rather than an order-dependent surprise.

    Both root-level test layouts (``test/<bundle>/test_x.py``) and nested
    layouts (``test/<bundle>/<skill>/test_x.py``) use the same call — resolution
    is by ``(bundle, skill, script_file)``, never by the test file's own path.

    ``script_file`` is relative to the skill's ``scripts/`` directory, so a skill
    that ships none is not addressable here at all — :func:`get_scripts_dir` raises
    first. For a module at the SKILL ROOT, call :func:`load_skill_module`.

    Args:
        bundle: Bundle name (e.g., ``'pm-plugin-development'``).
        skill: Skill name (e.g., ``'plugin-doctor'``).
        script_file: Script filename relative to ``scripts/`` (e.g.,
            ``'_analyze_verb_chains.py'``, or ``'build/_build_cli.py'``).
        module_name: Optional explicit module name for ``sys.modules``
            registration. Defaults to the script filename stem.
        register: Whether to publish the loaded module in ``sys.modules``.
            Defaults to True.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: when the scripts directory or the script file is absent.
        ImportError: when the module spec cannot be created or executed.
    """
    return _exec_module_from_path(get_scripts_dir(bundle, skill) / script_file, module_name, register)


def load_skill_module(
    bundle: str,
    skill: str,
    module_file: str,
    module_name: str | None = None,
    *,
    register: bool = True,
):
    """Load a module a skill ships, addressed from the SKILL ROOT.

    The companion to :func:`load_script_module` for a file that does not live under
    ``scripts/``. Both execute the module the same way and register it under the same
    ``sys.modules`` rule; they differ only in what the path is relative to, which is
    stated by the function you call rather than inferred from the filename.

    The shape this exists for is a bundle's ``plan-marshall-plugin`` skill, whose
    ``extension.py`` sits at the skill root — most such skills ship no ``scripts/``
    directory, so :func:`load_script_module` cannot address the file at all and
    :func:`get_scripts_dir` raises before it gets the chance. Without this, a test
    for one had no option but the per-module ``spec_from_file_location`` preamble the
    house style exists to remove.

    ⛔ **Pass ``module_name`` for that shape, or ``register=False``.** EVERY bundle
    ships its extension under the same filename, so the default name — the stem — is
    ``extension`` for all of them, and loading a second displaces the first. The
    hand-rolled preambles this replaces each pass a distinct name for exactly that
    reason, and nothing imports ``extension`` plainly, so the registration guard
    cannot see the collision either.

    Args:
        bundle: Bundle name (e.g. ``'pm-dev-python'``).
        skill: Skill name (e.g. ``'plan-marshall-plugin'``).
        module_file: Path to the module, relative to the skill root (e.g.
            ``'extension.py'``).
        module_name: Optional explicit module name for ``sys.modules``
            registration. Defaults to the module filename stem.
        register: Whether to publish the loaded module in ``sys.modules``. Carries
            the same collision hazard and the same escape as
            :func:`load_script_module`. Defaults to True.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: when the skill directory or the module file is absent.
        ImportError: when the module spec cannot be created or executed.
    """
    return _exec_module_from_path(get_skill_dir(bundle, skill) / module_file, module_name, register)


def _exec_module_from_path(path: Path, module_name: str | None, register: bool):
    """Execute ``path`` as a module, optionally registering it in ``sys.modules``.

    The one construction both public loaders share, so the two cannot drift in how
    they name, register, or execute what they load.

    Registration is by the resolved name and REPLACES any existing entry — see
    :func:`load_script_module` for what that costs a caller holding an earlier copy.

    ⛔ The registration happens BEFORE execution, because a module body that
    resolves its own name through ``sys.modules`` needs the entry to be there
    already. That ordering means a body which raises would leave a
    half-initialised module published under its name, and a later plain
    ``import`` of that name would succeed and hand back the broken object —
    failing far from its cause. The entry is therefore removed on failure,
    which is the standard importlib pattern, so an execution error leaves
    ``sys.modules`` exactly as it found it.

    Raises:
        FileNotFoundError: when ``path`` is not a file.
        ImportError: when the module spec cannot be created.
        Exception: whatever the module body raises — ``exec_module`` propagates
            the body's own exception type rather than wrapping it.
    """
    import importlib.util

    if not path.is_file():
        raise FileNotFoundError(f'Module not found: {path}')

    name = module_name or path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not create import spec for {path}')
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if register:
            sys.modules.pop(name, None)
        raise
    return module


# =============================================================================
# Argument Namespace Construction
# =============================================================================

#: Attribute names a script may publish its ``argparse.ArgumentParser`` builder
#: under. :func:`parse_ns` probes them in this order and takes the first
#: zero-argument callable that returns an ``ArgumentParser``.
#:
#: This is the documented convention referred to by :func:`parse_ns`. It is a
#: small CLOSED set rather than a name-shaped heuristic on purpose: a probe that
#: called anything matching ``*parser*`` would eventually call a function with
#: side effects, and a test helper that runs arbitrary script code to build an
#: argument list is worse than the hand-built namespace it replaces.
PARSER_BUILDER_NAMES: tuple[str, ...] = ('build_parser', '_build_parser', '_build_arg_parser')


class ParserSeamNotFound(RuntimeError):
    """A script exposes no reachable ``argparse`` parser seam.

    Raised by :func:`parse_ns` when neither seam resolves — the script publishes
    no builder from :data:`PARSER_BUILDER_NAMES`, and either has no ``main()`` or
    has one that returns without ever parsing.

    This error is deliberately loud. :func:`parse_ns` exists because a hand-built
    ``argparse.Namespace`` carries only the attributes its author remembered, not
    the parser's defaults — so a flag added to a script with a default breaks
    production while every hand-built namespace keeps passing. Degrading to a
    hand-built namespace on the no-seam path would reintroduce exactly that
    defect at exactly the call sites least able to notice it, so the no-seam path
    raises instead.
    """


class _ParseIntercepted(BaseException):
    """Internal sentinel that unwinds a script's ``main()`` at its parse call.

    Derives from :class:`BaseException` rather than :class:`Exception` so that a
    broad ``except Exception`` inside a script's ``main()`` cannot swallow it and
    let the command body run after all.
    """

    def __init__(self, namespace: argparse.Namespace) -> None:
        super().__init__('argparse namespace captured')
        self.namespace = namespace


def _parser_from_builder(module: ModuleType) -> argparse.ArgumentParser | None:
    """Return the parser from the module's published builder, or ``None``.

    A builder that requires arguments is not a seam :func:`parse_ns` can use
    (``ci_base.build_parser`` takes the script's command table, for example), so
    a ``TypeError`` from the zero-argument call falls through to the next
    candidate name rather than failing the whole resolution.
    """
    for name in PARSER_BUILDER_NAMES:
        builder = getattr(module, name, None)
        if not callable(builder):
            continue
        try:
            parser = builder()
        except TypeError:
            continue
        if isinstance(parser, argparse.ArgumentParser):
            return parser
    return None


def _parse_via_main(module: ModuleType, label: str, argv: list[str]) -> argparse.Namespace:
    """Capture the namespace a script's ``main()`` would parse, without running it.

    ``argparse.ArgumentParser.parse_args`` is patched for the duration of one
    ``main()`` call: the real parser still does the parsing (so every default,
    ``type=`` conversion and subparser binding is the production one), but the
    result is captured and the stack is unwound before ``main()`` reaches the
    command body.
    """
    main = getattr(module, 'main', None)
    if not callable(main):
        raise ParserSeamNotFound(
            f'{label}: no parser seam — the module publishes none of '
            f'{PARSER_BUILDER_NAMES} and has no callable main().'
        )

    real_parse_args = argparse.ArgumentParser.parse_args
    #: Set the moment the real parser is entered. It distinguishes the two ways
    #: ``main()`` can exit without yielding a namespace: a parser that REJECTED
    #: argv (reached, so the caller's command line is the defect) versus a script
    #: that exits BEFORE parsing (never reached, so there is no usable seam).
    parser_entered = False

    def _intercept(
        self: argparse.ArgumentParser,
        args: Any = None,
        namespace: Any = None,
    ) -> argparse.Namespace:
        nonlocal parser_entered
        parser_entered = True
        parsed = real_parse_args(self, argv if args is None else args, namespace)
        raise _ParseIntercepted(parsed)

    saved_argv = sys.argv
    sys.argv = [label, *argv]
    try:
        with mock.patch.object(argparse.ArgumentParser, 'parse_args', _intercept):
            main()
    except _ParseIntercepted as captured:
        return captured.namespace
    except SystemExit:
        if parser_entered:
            # The real parser rejected argv. That is the caller's command line
            # being wrong, which is exactly what the published-builder seam
            # surfaces as SystemExit too — so both seams fail the same way.
            raise
        raise ParserSeamNotFound(
            f'{label}: main() exited before reaching its parse_args call, so no '
            f'parser seam was reachable for argv {argv!r}.'
        ) from None
    finally:
        sys.argv = saved_argv

    if parser_entered:
        raise ParserSeamNotFound(
            f'{label}: the parser was entered for argv {argv!r} but main() returned '
            'without yielding a namespace — it caught the parse failure itself.'
        )
    raise ParserSeamNotFound(
        f'{label}: main() returned without calling parse_args, so no namespace '
        'could be captured.'
    )


def parse_ns(
    bundle: str, skill: str, script: str, *argv: str, register: bool = True
) -> argparse.Namespace:
    """Build an ``argparse.Namespace`` by running the script's OWN parser.

    The shared replacement for a hand-built ``argparse.Namespace(...)``. A
    hand-built namespace carries only the attributes its author remembered; the
    namespace returned here carries every default the production CLI would apply,
    because the production parser produced it.

    Args:
        bundle: Bundle name (e.g. ``'plan-marshall'``).
        skill: Skill name (e.g. ``'manage-tasks'``).
        script: Script filename (e.g. ``'manage-tasks.py'``).
        *argv: The command line, one token per argument, exactly as it would be
            typed after the script name — e.g.
            ``parse_ns('plan-marshall', 'manage-files', 'manage-files.py',
            'read', '--plan-id', 'p', '--file', 'task.md')``.
        register: Whether the script module this loads is published in
            ``sys.modules``. Defaults to True, matching :func:`load_script_module`.
            Pass False when the caller wants only the namespace — which is the usual
            case here — so building one cannot displace a registration another test
            module imports plainly. See :func:`load_script_module` for the hazard.

    Returns:
        The namespace the script's parser produces for ``argv``.

    Raises:
        ParserSeamNotFound: when no parser seam resolves — see below.
        SystemExit: propagated from the parser when ``argv`` is invalid. The
            caller passed a command line the real CLI would reject, which is a
            defect in the test rather than in the script. Both seams fail this
            way, so the error a caller sees does not depend on which seam the
            script happens to expose.

    Two seams, in order
    -------------------
    1. **A published builder.** The module attribute named by
       :data:`PARSER_BUILDER_NAMES` is called with no arguments and its parser is
       used directly. This is the cheap path: nothing but the builder runs.
    2. **Interception at ``main()``'s parse call.** Most scripts in this tree
       build their parser *inside* ``main()``, where it is not reachable as an
       object. For those, ``main()`` is invoked with
       ``argparse.ArgumentParser.parse_args`` patched, so the real parser still
       performs the parse and the stack is unwound the instant it returns.

    The handler the command line names never runs: interception unwinds the stack
    at the parse, before ``main()`` can dispatch. What seam 2 DOES run is whatever
    ``main()`` executes *before* it parses. For an ordinary argparse CLI that is
    nothing — a script cannot meaningfully act before it knows its arguments — but
    two shapes break that convention, and seam 1 is what a caller should prefer
    for them:

    * A **router** script that resolves and dispatches an operation *before*
      reaching ``parse_args`` runs that pre-dispatch logic.
      ``plan-marshall:platform-runtime:platform_runtime.py`` is the observed case:
      its ``main()`` reads the marshal config, mutates ``sys.path`` and dispatches,
      and only a *handler's* parser is ever interceptable.
    * A script that parses with ``parse_known_args`` instead of ``parse_args`` is
      not intercepted at all. Only ``parse_args`` is patched, deliberately:
      ``parse_args`` calls ``parse_known_args`` internally, so patching both would
      capture the inner call and yield a partially-parsed namespace.

    Both shapes end in :class:`ParserSeamNotFound` rather than in a wrong
    namespace, so neither fails silently — but a router script's pre-dispatch work
    will already have run by the time the error is raised.

    Neither seam is a fallback to a *hand-built* namespace: both return the real
    parser's own output, and the no-seam case raises
    :class:`ParserSeamNotFound` rather than degrading.

    Cost: this re-executes the script module on every call (via
    :func:`load_script_module`, which by default also re-registers it in
    ``sys.modules`` — pass ``register=False`` to suppress that). A
    test that builds many namespaces should hoist the call into a fixture or a
    module-level constant rather than calling it per assertion, and should not
    assume the module object the parser came from is the same instance the test
    holds a reference to.
    """
    module = load_script_module(bundle, skill, script, register=register)
    label = f'{bundle}:{skill}:{script}'

    parser = _parser_from_builder(module)
    if parser is not None:
        return parser.parse_args(list(argv))

    return _parse_via_main(module, label, list(argv))


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

#: Context managers that OWN ``PLAN_BASE_DIR`` for the block they wrap. A module
#: naming one of them drives real plan state even when it never requests the
#: ``plan_context`` fixture, which is the gap a fixture-name-only predicate left:
#: those modules are precisely the ones whose redirect the guard exists to verify,
#: and they were the ones it skipped. ``EmptyPlanContext`` is listed in full rather
#: than left to the ``PlanContext`` substring, so the set reads as the enumeration
#: it is.
_REAL_STATE_SYMBOLS = ('PlanContext', 'EmptyPlanContext', 'BuildContext')

#: Shapes that SET the ``PLAN_BASE_DIR`` binding, as opposed to reading it. Setting
#: it is choosing where plan state lands — the decision whose outcome the guard
#: checks. Reading it is being a passenger of the autouse sandbox, which needs no
#: check. Both the env-var and the ``_config_core`` module-attribute routes count,
#: because both redirect the same resolver.
_PLAN_BASE_DIR_SET_RE = re.compile(
    r"""setenv\(\s*['"]PLAN_BASE_DIR['"]
      | setattr\([^)]*['"]PLAN_BASE_DIR['"]
      | os\.environ\[\s*['"]PLAN_BASE_DIR['"]\s*\]\s*=
      | ^\s*PLAN_BASE_DIR\s*=
    """,
    re.VERBOSE | re.MULTILINE,
)

#: Per-module-path memo for :func:`_module_drives_real_state`. Collection asks the
#: question once per ITEM; without the memo a 400-test module would be read 400
#: times, turning an O(modules) scan into an O(tests) one.
_REAL_STATE_MODULE_CACHE: dict[str, bool] = {}


def _module_drives_real_state(module_path) -> bool:
    """Whether a test module's SOURCE shows it driving real plan state.

    Source text rather than imported module attributes, because the reference that
    matters is usually inside a function body — ``with PlanContext(...)`` or a
    ``monkeypatch.setenv('PLAN_BASE_DIR', ...)`` call — where no module-level
    attribute records it, and an attribute scan would report the module clean.

    An unreadable path answers ``False``: the predicate only ever ADDS a marker, so
    a read failure costs a skipped backstop snapshot rather than a spurious one,
    and it must not break collection for a file pytest could nonetheless import.
    """
    key = str(module_path)
    cached = _REAL_STATE_MODULE_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        source = Path(key).read_text(encoding='utf-8')
    except OSError:
        _REAL_STATE_MODULE_CACHE[key] = False
        return False
    drives = any(symbol in source for symbol in _REAL_STATE_SYMBOLS) or bool(
        _PLAN_BASE_DIR_SET_RE.search(source)
    )
    _REAL_STATE_MODULE_CACHE[key] = drives
    return drives


def pytest_collection_modifyitems(items):
    """Lock the ``allow_pollution`` escape hatch shut, and scope the pollution
    guard to the tests that drive real credential/plan state.

    **allow_pollution lock.** The ``allow_pollution`` marker stays registered in
    ``pyproject.toml`` and is still honoured by ``_pollution_guard``,
    ``_plan_base_dir_sandbox`` and ``_credentials_dir_sandbox`` — but no test in
    this suite is permitted to carry it. Locking the escape hatch shut at
    collection time means a new opt-out is rejected as a session-level error with
    the offending nodeids, instead of silently disarming the isolation guards for
    that test.

    **Guard scoping.** ``_pollution_guard`` takes a real-path snapshot before AND
    after every test it runs on, reading the developer's real
    ``~/.plan-marshall/credentials/`` listing and the tracked ``.plan/local/``
    tree. Because the autouse sandboxes already make a real-tree write
    structurally impossible, that snapshot is a BACKSTOP that only needs to verify
    the redirect held for the tests that actually drive credential/plan state.

    ``touches_real_state`` is therefore applied by DERIVATION, on two signals:

    1. the test requests the ``plan_context`` fixture — the canonical plan-state
       fixture; or
    2. the test's module names one of :data:`_REAL_STATE_SYMBOLS` or sets
       ``PLAN_BASE_DIR`` (:data:`_PLAN_BASE_DIR_SET_RE`) — i.e. it redirects the
       resolver itself rather than inheriting the autouse sandbox.

    Signal 1 alone left the state-driving modules that never touch the fixture
    unmarked, so the backstop skipped exactly the tests it exists for. Every other
    (pure-logic) test still skips the snapshot, which is the cost this scoping was
    introduced to remove.

    **Collection order (``PM_TEST_ORDER``).** Setting ``PM_TEST_ORDER=reverse``
    reverses ``items`` in place as this hook's LAST action, so a suite can be run
    in the opposite collection order to expose order-dependent state leaking
    between tests. Any other value — and the variable's absence — leaves the
    order untouched, so the default run is byte-for-byte unchanged. Pair it with
    ``--no-parallel``: the default ``-n auto --dist=loadgroup`` run distributes a
    module's items across workers, so it neither establishes nor tests a fixed
    order.
    """
    opted_out = [item.nodeid for item in items if item.get_closest_marker('allow_pollution')]
    if opted_out:
        raise pytest.UsageError(
            'Pollution escape hatch is locked: @pytest.mark.allow_pollution is not '
            'permitted in this suite, but the following tests carry it:\n  '
            + '\n  '.join(sorted(opted_out))
            + '\n\nIsolate the test via the autouse sandboxes (plan_context / '
            'PlanContext / monkeypatch) instead of opting out of them.'
        )

    for item in items:
        if 'plan_context' in getattr(item, 'fixturenames', ()):
            item.add_marker('touches_real_state')
            continue
        module_path = getattr(item, 'path', None)
        if module_path is not None and _module_drives_real_state(module_path):
            item.add_marker('touches_real_state')

    if os.environ.get('PM_TEST_ORDER') == 'reverse':
        items.reverse()


# =============================================================================
# Routing-guard population sizes, published on every run
# =============================================================================

#: The population-derived guards, as
#: ``(label, path-relative-to-TEST_ROOT)``. The family started as the routing
#: guards and now also carries the contract-text guards that derive their
#: population from a shipped document; the constant keeps its original name so
#: the rows below and the header line stay one identifiable set. Each module
#: publishes its own
#: ``GUARD_POPULATION_LABEL`` / ``GUARD_POPULATION_SIZE`` pair; this header reads
#: those rather than re-deriving anything, so the number reported is the number
#: the guard actually swept and the two cannot drift apart.
#:
#: No count is claimed for this tuple, and membership is NOT read from it. The
#: tuple supplies ORDER and the short names used in the UNAVAILABLE branch;
#: which modules are reported is derived from the tree by
#: :func:`_discover_guard_publishers`. A guard added without a row here is
#: therefore still reported — as an ``UNLISTED`` entry — rather than being
#: silent on exactly the run its population matters on, the passing one.
_ROUTING_GUARD_MODULES: tuple[tuple[str, str], ...] = (
    ('offrouting', 'plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py'),
    ('branch-cleanup', 'plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py'),
    ('review-merge', 'plan-marshall/phase-6-finalize/test_review_merge_invocation_contract.py'),
    (
        'envelope-plan-id',
        'plan-marshall/tools-integration-ci/test_envelope_contract_plan_id_placement.py',
    ),
    (
        'api-contract-parity',
        'plan-marshall/workflow-integration-github/test_pr_landing_state.py',
    ),
    (
        'gate-derivation',
        'plan-marshall/phase-6-finalize/test_gate_derivation_diagnosability.py',
    ),
    (
        'gate-arm-provenance',
        'plan-marshall/phase-6-finalize/test_gate_arm_resolver_provenance.py',
    ),
    (
        'self-review-surface',
        'plan-marshall/phase-6-finalize/test_self_review_unclassified_surface.py',
    ),
    (
        'pinned-build-tool',
        'plan-marshall/phase-6-finalize/test_no_pinned_build_tool_in_shipped_docs.py',
    ),
)


#: The module-level constant a routing-guard module publishes to opt into the
#: population header. Matched at the START of a line so a module that merely
#: MENTIONS the name — this file included — is not counted as a publisher.
_GUARD_PUBLISHER_MARKER = 'GUARD_POPULATION_LABEL'


def _discover_guard_publishers() -> list[str]:
    """Every ``TEST_ROOT``-relative test module that publishes a guard population.

    Derived from the tree, never transcribed. This is what closes the membership
    gap ``_ROUTING_GUARD_MODULES`` cannot close on its own: a hand-listed tuple
    omits a live publisher silently, so a green run is indistinguishable from one
    whose guard vanished from the report.

    Text-matched rather than imported: this runs before collection, and importing
    every test module in the tree to read one constant would be both far more
    expensive and a source of import side effects. Detection only decides what to
    REPORT; the size itself is still read from the loaded module.
    """
    found: list[str] = []
    for path in sorted(TEST_ROOT.rglob('test_*.py')):
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if any(line.startswith(_GUARD_PUBLISHER_MARKER) for line in text.splitlines()):
            found.append(path.relative_to(TEST_ROOT).as_posix())
    return found


def _guard_roster() -> tuple[list[tuple[str, str]], list[str]]:
    """The modules to report, in tuple order, plus any roster discrepancies.

    Returns ``(entries, discrepancies)`` where ``entries`` is
    ``(short_name, relative_path)`` — the ``_ROUTING_GUARD_MODULES`` rows first,
    in their declared order, followed by every discovered publisher that has no
    row. ``discrepancies`` names both failure directions: a publisher with no
    row, and a row whose module no longer publishes.
    """
    listed = list(_ROUTING_GUARD_MODULES)
    listed_paths = {relative for _short_name, relative in listed}
    discovered = _discover_guard_publishers()

    unlisted = [relative for relative in discovered if relative not in listed_paths]
    no_longer_publishing = [
        relative for relative in listed_paths if relative not in discovered
    ]

    entries = listed + [
        (f'UNLISTED:{relative.rsplit("/", 1)[-1].removesuffix(".py")}', relative)
        for relative in unlisted
    ]

    discrepancies: list[str] = []
    if unlisted:
        discrepancies.append(
            f'{len(unlisted)} publisher(s) with no _ROUTING_GUARD_MODULES row: '
            + ', '.join(unlisted)
        )
    if no_longer_publishing:
        discrepancies.append(
            f'{len(no_longer_publishing)} row(s) whose module no longer publishes '
            f'{_GUARD_PUBLISHER_MARKER}: ' + ', '.join(sorted(no_longer_publishing))
        )
    return entries, discrepancies


def _load_never_registering(path: Path):
    """Execute ``path`` as a module that is NEVER published in ``sys.modules``.

    A deliberately different primitive from :func:`_exec_module_from_path`, not a
    copy of it. That one's contract is "load, and register unless told otherwise",
    which is why the loader-contract guard treats every helper reaching it as one
    whose registrations the collision guard must account for. This one cannot
    register under any argument, so it has nothing for that guard to account for —
    and the distinction is real rather than a spelling: the caller here reads one
    constant off a module pytest is about to import under that same name, and a
    registration would leave a second copy published for collection to displace.

    Nothing is cached. The only caller runs once per session per module.
    """
    import importlib.util

    if not path.is_file():
        raise FileNotFoundError(f'Module not found: {path}')
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not create import spec for {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pytest_report_header(config):
    """Publish each routing guard's derived population size at session start.

    Every one of these guards asserts over a population it DERIVES from the tree,
    and each already publishes its size in its own failure messages. That leaves
    the case those messages cannot reach: a run where the derivation quietly
    shrank and every assertion over the smaller set still passed. A green run
    reports nothing, so a population that halved looks exactly like one that did
    not. Printing the sizes unconditionally makes the shrink visible in the
    ordinary output of a passing run.

    The sizes are READ from each module rather than recomputed here. A second
    derivation in this file would be a second thing to keep in step, and it could
    report a healthy number for a sweep that used a different one.

    A module that cannot be loaded is reported as ``UNAVAILABLE`` with its error
    rather than omitted or defaulted to zero: a missing number must not read as a
    small one, and collection will surface the underlying failure properly a
    moment later. Reporting it here — instead of raising — keeps a real test
    failure from being reshaped into a session-startup error that names neither
    the test nor the cause.

    The load goes through :func:`_load_never_registering`, NOT through
    :func:`_exec_module_from_path`. This hook runs before collection, so it
    cannot read a module pytest has already imported, and it must not leave one
    published under a name collection would then displace.
    """
    roster, discrepancies = _guard_roster()
    entries: list[str] = []
    for short_name, relative in roster:
        try:
            module = _load_never_registering(TEST_ROOT / relative)
            label = module.GUARD_POPULATION_LABEL
            size = module.GUARD_POPULATION_SIZE
        except BaseException as exc:  # noqa: BLE001 — reported, never swallowed
            entries.append(f'{short_name}: UNAVAILABLE ({type(exc).__name__}: {exc})')
            continue
        entries.append(f'{label}: {size}')
    lines = ['routing-guard populations: ' + '; '.join(entries)]
    if discrepancies:
        # Reported, not raised: this hook runs before collection, and raising here
        # reshapes a real roster defect into a session-startup error naming
        # neither the test nor the cause. The line is unconditional when it fires,
        # so the omission cannot pass unseen on a green run.
        lines.append('routing-guard roster DRIFT: ' + '; '.join(discrepancies))
    return lines


#: Opt-in flag for the reference-platform ``skipped == 0`` gate. The gate is off
#: by default so a developer's ``-k``-filtered or otherwise partial run is never
#: failed by it.
#:
#: ⛔ **No producer in this repository sets it.** A sweep over the inventoried tree
#: and over all seven files in ``.github/workflows/`` (which the inventory does not
#: reach, so they were read individually) finds this name on exactly three lines,
#: all of them below in this file. :func:`pytest_sessionfinish` therefore returns at
#: its first line on every run this project performs, and the gate has never once
#: rendered a verdict. The one thing this repository cannot see is the body of the
#: reusable org workflow ``python-verify.yml`` delegates to, which lives in another
#: repository; the claim is scoped accordingly, and is an absence of a producer
#: HERE rather than a proof that nothing anywhere sets it.
#:
#: Arming it (have CI export ``1``) and deleting it (drop an unreachable gate) are
#: both defensible and both change what the suite guarantees, so neither is made
#: here — the choice with its costs is recorded for the operator.
_STRICT_NO_SKIP_ENV = 'PLAN_MARSHALL_STRICT_NO_SKIP'


#: Nodeids of every test the session reported as skipped. Under xdist the
#: workers stream their reports back to the controller, so the controller's
#: copy of this set is complete and is the one the gate reads.
_SKIPPED_NODEIDS: set = set()


def pytest_runtest_logreport(report):
    """Accumulate skipped nodeids for the session-level zero-skip gate."""
    if report.skipped:
        _SKIPPED_NODEIDS.add(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    """Fail a reference-platform full run that skipped any test.

    Every skip in this suite is meant to be either a tracked-artifact guard
    (which is now a hard assertion) or a genuine environment guard that does
    not trigger on the reference platform. A non-zero skip count there means a
    guard silently disarmed a test, so the run fails rather than reporting a
    green suite that quietly covered less than it claims.

    The gate is deliberately narrow. It is active only when the opt-in flag is
    set, and it exempts a ``-k`` / ``-m`` filtered run, which legitimately
    skips tests. A developer's partial run is therefore never failed by it.
    """
    if os.environ.get(_STRICT_NO_SKIP_ENV) != '1':
        return
    config = session.config
    if hasattr(config, 'workerinput'):
        return  # xdist worker — the controller owns the session-level verdict
    if getattr(config.option, 'keyword', '') or getattr(config.option, 'markexpr', ''):
        return
    if not _SKIPPED_NODEIDS:
        return
    session.exitstatus = 1
    reporter = config.pluginmanager.get_plugin('terminalreporter')
    if reporter is not None:
        reporter.write_line('')
        reporter.write_line(
            f'ERROR: reference-platform run skipped {len(_SKIPPED_NODEIDS)} test(s), '
            f'but the suite must report zero skips when {_STRICT_NO_SKIP_ENV}=1:',
            red=True,
        )
        for nodeid in sorted(_SKIPPED_NODEIDS):
            reporter.write_line(f'  {nodeid}', red=True)


_ENTRY_CWD_KEY = pytest.StashKey[str]()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Record the cwd the test started from, for the leak check at teardown."""
    item.stash[_ENTRY_CWD_KEY] = os.getcwd()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """Fail loudly when a test leaks the process-wide cwd.

    Restoring silently hid the leak: the offending test passed while every
    later test inherited a cwd it never asked for. The original cwd is
    restored FIRST so the following test is not poisoned, then the leak is
    reported with the offending nodeid and the before -> after pair —
    symmetric with ``_pollution_guard``'s fail-loud message shape.

    This is a hook wrapper rather than an autouse fixture because
    ``monkeypatch.undo()`` — which reverts ``monkeypatch.chdir()`` — runs
    AFTER every fixture finalizer, including an autouse one declared here.
    A fixture-based check therefore observes the cwd before pytest has had
    the chance to restore it, and reports every correct ``monkeypatch.chdir``
    as a leak. Checking post-yield in the teardown hook runs after all
    fixture finalization, so only a genuinely unrestored cwd trips the guard.
    """
    result = yield
    original_cwd = item.stash.get(_ENTRY_CWD_KEY, None)
    if original_cwd is None:
        return result
    leaked_cwd = os.getcwd()
    if leaked_cwd != original_cwd:
        os.chdir(original_cwd)
        raise RuntimeError(
            f'cwd guard: test {item.nodeid} leaked the process-wide cwd:\n  '
            f'{original_cwd} -> {leaked_cwd}'
            '\n\nRestore the cwd in the test (use the monkeypatch.chdir fixture, '
            'or pass an explicit cwd= to the subprocess/API call) instead of '
            'relying on the safety net.'
        )
    return result


_REAL_CREDENTIALS_DIR = Path.home() / '.plan-marshall' / 'credentials'

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
    """Fail loudly if a test mutates the real ``~/.plan-marshall/credentials/``
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

    **Scoped.** The snapshot runs only for tests carrying ``touches_real_state``,
    which :func:`pytest_collection_modifyitems` DERIVES from two signals — the test
    requests ``plan_context``, or its module names a plan-state context manager /
    sets ``PLAN_BASE_DIR``. The autouse sandboxes make a real-tree write
    structurally impossible for every test, so this guard is a backstop that only
    needs to verify the redirect held for the state-driving subset; a pure-logic
    test never touches the watched paths, so its before/after snapshot — which
    reads the developer's real credentials-directory listing — is pure cost and is
    skipped.
    """
    if request.node.get_closest_marker('allow_pollution'):
        yield
        return

    if not request.node.get_closest_marker('touches_real_state'):
        # Not a credential/plan-state-driving test: the autouse sandboxes already
        # make a real-tree leak structurally impossible, so the snapshot has
        # nothing to verify. Skip it (see pytest_collection_modifyitems / D5).
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
    import _config_core

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
    into the real ``~/.plan-marshall/credentials/`` tree becomes structurally
    impossible. This closes the asymmetry the ``_pollution_guard`` exposed: the
    guard caught real-credentials leaks but there was no autouse redirect backing
    it, so a single un-isolated credential write (or a subprocess inheriting the
    real env) leaked into the developer's real credential dir.

    ``_providers_core.CREDENTIALS_DIR`` is bound at module-import time
    (``Path(PLAN_MARSHALL_CREDENTIALS_DIR)`` when set, else
    ``home_root()/credentials``), so an env-var set alone does not reach
    already-imported in-process callers;
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
    import _providers_core

    monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', sandbox)

    yield


#: Location carve-out for ``_neutralize_daemon_routing``. Every test module under
#: this directory owns the build-server routing seam as its SYSTEM UNDER TEST, so
#: neutralizing the seam there would delete the coverage rather than isolate it.
#: Resolved from the collected node's own path, so a new module added under the
#: directory inherits the carve-out with no registry to update.
_DAEMON_ROUTING_CARVE_OUT = TEST_ROOT / 'plan-marshall' / 'build-server'

#: The seam name the factory's ``cmd_run`` closure resolves at call time.
_ROUTING_SEAM_NAME = '_route_to_daemon'


def _no_daemon_routing(*_args, **_kwargs):
    """Stand-in for ``_route_to_daemon`` that always declines to route.

    Returns the factory's benign ``(result=None, reason)`` "do not route" signal
    using the ``no_notation`` reason — the one the factory already emits for an
    unroutable build tool. It is deliberately NOT recorded as a degradation, so a
    neutralized test produces the same audit trail as a host with no daemon.
    """
    return (None, 'no_notation')


def _routing_namespaces(test_module) -> list[dict]:
    """Return every globals dict a live ``cmd_run`` resolves the seam from.

    Patching by MODULE OBJECT is not sufficient here, and the reason is
    load-order dependent — which makes getting it wrong a FLAKY green rather
    than a clean red. Two facts combine:

    1. Any caller that loads the factory through :func:`load_script_module` —
       the shared build-test helper module does, to reach the factory's
       ``compute_command_key`` — re-registers it in ``sys.modules`` under its own
       stem. That REPLACES the entry, so a test module that already did
       ``import _build_execute_factory as factory`` at its own import time holds
       a copy that is no longer reachable from ``sys.modules`` at all — it
       survives only as a reference in that test module's globals. The helper is
       named by its ROLE rather than its path on purpose: the mechanism belongs
       to the loader, not to any one caller, so the explanation stays true when a
       caller is renamed or a second one appears.
    2. ``cmd_run`` is a CLOSURE created by ``create_execute_handlers``, so it
       resolves ``_route_to_daemon`` from ``cmd_run.__globals__`` — the dict of
       whichever factory copy produced it, not from whatever ``sys.modules``
       currently maps the name to.

    Targeting the ``__globals__`` DICT rather than the module object therefore
    reaches the exact binding the closure reads, regardless of how many copies
    exist or which one a given test happens to hold. Scanning is confined to the
    canonical ``sys.modules`` entry plus the test module's own globals, so the
    cost stays proportional to one module's namespace rather than to the whole
    import graph.
    """
    namespaces: dict[int, dict] = {}

    def _consider(obj: Any) -> None:
        # A module contributes its own globals; a function (e.g. a bound
        # ``cmd_run`` handler) contributes the globals it closes over.
        candidate = vars(obj) if isinstance(obj, ModuleType) else getattr(obj, '__globals__', None)
        # ``isinstance(candidate, dict)`` is load-bearing beyond a None-guard: the
        # membership test below must run against a real namespace mapping. Anything
        # else that answers ``__globals__`` — or any object whose attribute access
        # is synthetic, as a mock's is — would report the seam name as present and
        # be handed to ``monkeypatch.setitem``, patching a binding no closure reads.
        if isinstance(candidate, dict) and _ROUTING_SEAM_NAME in candidate:
            namespaces[id(candidate)] = candidate

    canonical = sys.modules.get('_build_execute_factory')
    if canonical is not None:
        _consider(canonical)
    if test_module is not None:
        for value in list(vars(test_module).values()):
            _consider(value)
    return list(namespaces.values())


@pytest.fixture(autouse=True)
def _neutralize_daemon_routing(request, monkeypatch):
    """Default the D5 build-routing seam to its non-routing outcome.

    WHY THIS EXISTS. ``_build_execute_factory.cmd_run`` consults
    ``_route_to_daemon`` whenever ``execution_mode`` is left at its ``auto``
    default, and routing then depends on MACHINE-GLOBAL state: whether the
    project is registered with marshalld and whether the daemon answers a
    verified handshake. A test that drives ``cmd_run`` without pinning
    ``execution_mode`` therefore behaves differently on a developer host where
    the daemon is registered and ready than on a bare CI runner — on the former
    it submits a real build job to a real daemon, and the in-process seams the
    test injected (queue doubles, exec recorders) are never reached. The test
    does not fail honestly; it silently stops testing what it claims to test.

    Neutralization used to be COPIED into each affected module as an inline
    ``monkeypatch.setattr(factory, '_route_to_daemon', ...)``. That made
    correctness a matter of every future author remembering to repeat it, and a
    test written without the incantation was ambiently host-dependent with
    nothing to catch it. Making the fixture autouse here inverts the default:
    neutralization is INHERITED BY CONSTRUCTION, and a test that genuinely wants
    live routing must say so explicitly.

    The patched value ``(None, 'no_notation')`` is the benign "do not route"
    signal the factory already understands for an unroutable build tool: it
    takes no fallback slot accounting of its own and is not recorded as a
    degradation, so ``cmd_run`` proceeds down its in-process path exactly as it
    would on a host with no daemon at all.

    Two disengagement paths, evaluated in this order:

    1. **Location carve-out** — the fixture is a no-op for any test collected
       under ``test/plan-marshall/build-server/`` (see
       :data:`_DAEMON_ROUTING_CARVE_OUT`), whose modules own routing as their
       subject.
    2. **Marker opt-out** — ``@pytest.mark.allow_daemon_routing`` for a one-off
       that owns routing but lives outside that directory, honoured the same way
       the isolation sandboxes above honour ``allow_pollution``.

    ``monkeypatch`` scopes the patch to the single test, so it unwinds on
    teardown and never leaks into a sibling. ``_build_execute_factory`` is
    imported lazily inside the body, matching the ``_config_core`` /
    ``_providers_core`` convention used by the sandboxes above. The patch targets
    the closure's ``__globals__`` dict rather than a module attribute — see
    :func:`_routing_namespaces` for why more than one factory copy exists and why
    patching a single module object is silently partial.
    """
    if _DAEMON_ROUTING_CARVE_OUT in request.node.path.parents:
        yield
        return

    if request.node.get_closest_marker('allow_daemon_routing'):
        yield
        return

    # Ensure the canonical copy is loaded before the scan below.
    import _build_execute_factory  # noqa: F401

    for namespace in _routing_namespaces(getattr(request, 'module', None)):
        monkeypatch.setitem(namespace, _ROUTING_SEAM_NAME, _no_daemon_routing)

    yield


# =============================================================================
# Root-writable filesystem-root pollution neutralization
# =============================================================================

#: The conventional "this path does not exist" sentinel that dozens of tests
#: hand to path-validation code as a hardcoded absolute path
#: (``analyze_jsdoc('/nonexistent/path', is_directory=True)``,
#: ``cmd_detect_artifacts(root='/nonexistent/path')``,
#: ``cmd_stats(directory='/nonexistent/path')``, and ~30 more). Each such test
#: passes it expecting the code under test to report an "absent path" — an
#: assumption that holds only while the process cannot create it.
#:
#: WHY A GUARD IS NEEDED. On a developer machine and on the GitHub Actions
#: runners the suite runs UNPRIVILEGED, so the filesystem root ``/`` is not
#: writable and ``/nonexistent`` can never be created — the sentinel is reliably
#: absent, and every probe of it correctly answers "absent". In a Claude Code
#: cloud sandbox the suite runs as ROOT (uid 0): the OS bypasses the DAC
#: permission check and ``/`` becomes writable. A test that hands a
#: ``/nonexistent/...`` path to a *creating* operation (e.g.
#: ``project_initial_setup`` doing ``Path(project_dir, '.plan').mkdir(
#: parents=True)``) then MATERIALIZES the sentinel under ``/``, and every other
#: test that probes ``/nonexistent/path`` for absence starts seeing it PRESENT.
#: That is a cross-test pollution that exists only on a root host — the exact
#: shape that is green in CI and red only in the sandbox.
_ROOT_FS_SENTINEL = Path('/nonexistent')


def _root_fs_sentinel_present() -> bool:
    """Whether the ``/nonexistent`` filesystem-root sentinel currently exists.

    Wrapped as a named seam so the matched-pair control can reason about the
    guard's decision without depending on the host being root — an unprivileged
    host can never create the sentinel to simulate a leak.
    """
    return _ROOT_FS_SENTINEL.exists()


def _clear_root_fs_sentinel() -> None:
    """Best-effort removal of a leaked ``/nonexistent`` sentinel tree.

    A no-op on the overwhelmingly common path where it does not exist. On an
    unprivileged host there is nothing to remove (and the ``rmtree`` could not
    succeed anyway); on a root host this un-poisons the shared root for the
    tests that run after a leak.
    """
    if _ROOT_FS_SENTINEL.exists():
        shutil.rmtree(_ROOT_FS_SENTINEL, ignore_errors=True)


def _root_fs_leak_allowed(node) -> bool:
    """True when *node* opts out of the root-fs pollution guard via marker."""
    return node.get_closest_marker('allow_root_filesystem_pollution') is not None


def _root_fs_leak_violation(node, before: bool, after: bool) -> str | None:
    """Return a failure message if *node* leaked the sentinel, else ``None``.

    This is the guard's decision core, factored out so the matched pair in
    ``test/plan-marshall/script-shared/test_root_fs_pollution_neutralization.py``
    can drive it with a simulated ``(before, after)`` — engaged, and (via the
    marker) disengaged — without needing to be root to create the sentinel for
    real.

    A leak is ``after and not before``: the sentinel was absent when the test
    started and present when it finished. A node carrying
    ``allow_root_filesystem_pollution`` is exempt (returns ``None``).
    """
    if _root_fs_leak_allowed(node):
        return None
    if after and not before:
        return (
            f'Root-fs pollution guard: test {node.nodeid} materialized the '
            f'filesystem-root sentinel {_ROOT_FS_SENTINEL} under "/". This is '
            'only possible as root (uid 0), where the OS bypasses the DAC '
            'permission check that keeps "/" unwritable on a developer machine '
            'and on CI. Every test that probes that sentinel for ABSENCE then '
            'sees it PRESENT, so the leak surfaces as unrelated failures '
            'elsewhere.\n\nHand the creating operation a path that cannot be '
            'created by any uid (request the ``unwritable_dir`` fixture, which '
            'yields a path under /dev/null), or mark this test with '
            '@pytest.mark.allow_root_filesystem_pollution if the real-root '
            'write is genuinely its subject.'
        )
    return None


@pytest.fixture(autouse=True)
def _root_fs_pollution_guard(request):
    """Neutralize root's writability of the ``/nonexistent`` filesystem-root
    sentinel, and fail loudly on any test that materializes it.

    Companion to ``_pollution_guard`` (which watches the real credentials dir
    and the tracked ``.plan/local/`` tree): this one watches the ``/nonexistent``
    sentinel that dozens of tests hand to path-validation code expecting an
    "absent path" answer. See :data:`_ROOT_FS_SENTINEL` for the full mechanism
    and why it fails only in a root sandbox.

    Two arms:

    * **Neutralize** — the sentinel is cleared BEFORE the test body runs, so a
      test probing ``/nonexistent/...`` for absence sees it absent regardless of
      what a prior test (running as root) may have leaked. This is what makes
      the existence-probe tests deterministic on a root host.
    * **Self-check** — a before/after snapshot flags any test that leaks the
      sentinel, attributing the failure to the offender's nodeid instead of to
      the distant victim it would otherwise poison.

    Opt out with ``@pytest.mark.allow_root_filesystem_pollution`` for a test that
    genuinely owns a real-root write under ``/`` as its subject (none does today;
    the marker exists so the guard has a documented escape hatch, exactly as
    ``allow_pollution`` does for ``_pollution_guard``).
    """
    node = request.node
    if _root_fs_leak_allowed(node):
        yield
        return

    _clear_root_fs_sentinel()
    before = _root_fs_sentinel_present()
    yield
    after = _root_fs_sentinel_present()
    violation = _root_fs_leak_violation(node, before, after)
    if violation:
        _clear_root_fs_sentinel()
        pytest.fail(violation)


@pytest.fixture
def unwritable_dir() -> str:
    """Yield a directory path whose creation FAILS for every uid, root included.

    A test that asserts "a bad target directory yields an io_error" needs an
    input whose ``mkdir`` genuinely raises regardless of privilege. A path under
    the filesystem root that is merely assumed absent (``/nonexistent/...``) is
    NOT such an input: as root the OS bypasses the DAC permission check, so the
    ``mkdir`` SUCCEEDS, the error branch is never taken, and the sentinel is
    leaked under ``/`` (see :data:`_ROOT_FS_SENTINEL`).

    A path *under* ``/dev/null`` is un-creatable for every uid because
    ``/dev/null`` is a character device, not a directory: resolving any child of
    it raises ``ENOTDIR`` (``NotADirectoryError``, an ``OSError``) on ``mkdir``
    and reports ``False`` from ``.exists()``. The error branch is therefore
    exercised identically on an unprivileged host and on a root host, and
    nothing is ever written, so there is no cross-test pollution.
    """
    return '/dev/null/pm-unwritable/project-dir'


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

    import _config_core

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


@pytest.fixture(autouse=True)
def _materialize_declared_plan_dirs(request):
    """Create ``plans/{plan_id}/`` for every id the module under test DECLARES.

    In production ``phase-1-init`` creates the plan directory before any artifact
    is filed against it, and the findings surfaces REFUSE a plan directory that
    is absent under the resolved root — a plan that exists in no checkout is not
    a plan that filed nothing, and answering it with a clean zero (or, on the
    ``add`` paths, manufacturing the directory chain) is the defect that refusal
    exists to surface. A test whose subject is the store's behaviour for a REAL
    plan therefore has to construct the plan context, exactly as the lifecycle
    does; this fixture is where that construction lives so it does not have to be
    repeated in every test body.

    Opt-in, and deliberately so. A module participates by declaring a
    module-level ``PLAN_IDS`` tuple naming the plan ids ITS tests use. A module
    that declares nothing is completely unaffected — the fixture returns before
    it even resolves ``plan_context``, so no isolation, no monkeypatching and no
    directory creation is imposed on a test that did not ask for it. That is what
    keeps this from becoming a blanket neutralisation of the refusal: a test
    whose subject IS the refusal simply keeps its plan id out of ``PLAN_IDS``
    (or lives in a module that declares none), and the guard stays observable.
    """
    plan_ids = getattr(request.module, 'PLAN_IDS', ())
    if not plan_ids:
        return

    # Resolve the base dir the test will actually resolve, rather than assuming
    # one. Two redirects are in play — the autouse ``_plan_base_dir_sandbox``
    # default and the explicit ``plan_context`` override, which wins when the
    # test requests it — so both are forced into place HERE, before the resolved
    # root is read.
    #
    # ⛔ The forcing is load-bearing, not defensive. Instantiation order among
    # autouse fixtures is NOT guaranteed by declaration order in the conftest, so
    # without it this fixture can run first, seed under whichever root is live at
    # that moment, and then have a later-instantiated redirect replace it. That
    # failure is SILENT: the seeding still succeeds, it just creates the
    # directories somewhere the test never looks, and every seeded test fails as
    # though it had never been seeded at all.
    request.getfixturevalue('_plan_base_dir_sandbox')
    if 'plan_context' in request.fixturenames:
        request.getfixturevalue('plan_context')

    from file_ops import get_base_dir  # noqa: PLC0415 — lazy: avoids a bootstrap import cycle

    plans_root = get_base_dir() / 'plans'
    for plan_id in plan_ids:
        (plans_root / plan_id).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def outside_repo_dir():
    """Yield a directory guaranteed to live OUTSIDE the repository worktree.

    ``build.py`` gives each pytest invocation an explicit repo-local
    ``--basetemp`` under ``.plan/temp/pytest-basetemp/`` (per-session,
    bounded-growth). As a consequence pytest's own ``tmp_path`` /
    ``tmp_path_factory`` trees now resolve INSIDE the git worktree — and inside
    the repo's ``.plan/`` tree and its ``marketplace/`` ancestor. A test that
    must exercise genuine *outside-the-repo* behaviour (a non-git directory, a
    path with no ``.plan/local`` ancestor, a tree with no ``marketplace/``
    ancestor, a cwd from which no marshal config resolves) therefore CANNOT use
    ``tmp_path`` for that role — ``tmp_path`` is now inside the repo.

    This fixture allocates a directory under the system temp root via
    ``tempfile.mkdtemp`` (which honours ``$TMPDIR`` and is never rooted in the
    repo — ``build.py`` sets only ``--basetemp``, it does not touch
    ``$TMPDIR``), so the yielded path is reliably outside the worktree, outside
    any git repo, and has no ``.plan/`` or ``marketplace/`` ancestor. The
    directory is removed on teardown.

    The path is ``resolve()``-d before it is yielded so it is the canonical
    (symlink-free) form. On macOS the system temp root is a symlink
    (``/var/folders/... -> /private/var/folders/...``); ``git`` and other
    subprocesses report the resolved form, so a test that compares the yielded
    path against a subprocess-reported path would otherwise mismatch on the
    ``/private`` prefix.
    """
    outside = Path(tempfile.mkdtemp(prefix='pm-outside-repo-')).resolve()
    try:
        yield outside
    finally:
        shutil.rmtree(outside, ignore_errors=True)


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

    Honours a TEST_FIXTURE_DIR environment variable when one is set (nothing in
    the suite sets it by default); otherwise creates a standalone directory in
    .plan/temp/test-fixture/.

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

    Uses a centralized test fixture directory under .plan/temp/test-fixture/
    instead of system temp, created and cleaned up by the context itself.
    PLAN_BASE_DIR, PLAN_DIR_NAME, and the _config_core paths are redirected via a
    MonkeyPatch instance and reverted atomically on exit — the same
    auto-reverting mechanism the autouse _plan_base_dir_sandbox fixture uses.

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

    def __init__(self, plan_id: str = 'test-plan'):
        """
        Initialize the test context.

        Args:
            plan_id: Plan identifier (kebab-case)
        """
        self.plan_id = plan_id
        self.fixture_dir: Path | None = None
        self.plan_dir: Path | None = None
        self._is_standalone: bool = False
        # One MonkeyPatch owns every global this context redirects (PLAN_BASE_DIR,
        # PLAN_DIR_NAME, and the _config_core paths). Populated in __enter__ so the
        # module stays lazily imported; reverted atomically by undo() in __exit__.
        self._mp: pytest.MonkeyPatch | None = None

    def __enter__(self) -> 'PlanContext':
        """Set up the test context."""
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        # Create plan directory structure
        self.plan_dir = self.fixture_dir / 'plans' / self.plan_id
        self.plan_dir.mkdir(parents=True, exist_ok=True)

        # Redirect PLAN_BASE_DIR / PLAN_DIR_NAME and the _config_core module-level
        # paths so in-process callers (and subprocesses that inherit the env)
        # resolve against the fixture tree instead of the real repo-local
        # .plan/local/. A single MonkeyPatch instance owns all of them and reverts
        # them atomically in __exit__ — no manual save/restore. _config_core is
        # imported lazily to avoid a top-level import cycle during test bootstrap.
        import _config_core

        self._mp = pytest.MonkeyPatch()
        self._mp.setenv('PLAN_BASE_DIR', str(self.fixture_dir))
        self._mp.setenv('PLAN_DIR_NAME', PLAN_DIR_NAME)
        self._mp.setattr(_config_core, 'PLAN_BASE_DIR', self.fixture_dir)
        self._mp.setattr(_config_core, 'MARSHAL_PATH', self.fixture_dir / 'marshal.json')
        self._mp.setattr(_config_core, 'RUN_CONFIG_PATH', self.fixture_dir / 'run-configuration.json')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test context."""
        # Revert PLAN_BASE_DIR / PLAN_DIR_NAME and the _config_core attributes in
        # one atomic step, BEFORE the filesystem cleanup below, so any teardown
        # path that resolves those globals sees the original values.
        if self._mp is not None:
            self._mp.undo()
            self._mp = None

        # Clean up the plan_dir to ensure test isolation.
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

        # Only cleanup fixture_dir if running standalone.
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)


# =============================================================================
# Marshal.json Schema Constants
# =============================================================================

# Key names - use these constants instead of hardcoding strings
MARSHAL_KEY_SKILL_DOMAINS = 'skill_domains'
MARSHAL_KEY_SYSTEM = 'system'
MARSHAL_KEY_PLAN = 'plan'

# Named baselines for :func:`create_marshal_json`.
#
# These two are NOT variants of one config that could be averaged into a third —
# they are different fixtures for different consumers, and a module that silently
# inherited the wrong one is the defect the single builder exists to close. A
# caller therefore names the baseline it wants.
#
# ``verification_steps`` (phase-5-execute) and ``steps`` (phase-6-finalize) are
# id-keyed maps: each key is a step id, each value is that step's nested param
# object (``{}`` when the step owns no params). Key insertion order is the
# execution order. Step-owned params nest under their owning step — here
# ``review_bot_buffer_seconds`` nests under ``plan-marshall:automatic-review`` rather
# than living as a flat sibling of ``steps``.

#: Preset name: the minimal schema — the smallest config that satisfies the
#: marshal schema, with no language domain and no providers.
MARSHAL_PRESET_MINIMAL = 'minimal'

#: Preset name: the java-flavoured schema — skill domains, retention knobs,
#: branch-cleanup params and a GitHub provider entry. This is the baseline the
#: manage-config suite asserts against.
MARSHAL_PRESET_JAVA = 'java'

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
                'default:push': {},
                'default:create-pr': {},
                'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 300},
                'default:sonar-roundtrip': {},
                'default:lessons-capture': {},
                'default:branch-cleanup': {},
                'default:archive-plan': {},
            },
        },
    },
}

MARSHAL_SCHEMA_JAVA: dict[str, Any] = {
    MARSHAL_KEY_SKILL_DOMAINS: {
        'java': {'defaults': ['pm-dev-java:java-core'], 'optionals': ['pm-dev-java:java-cdi']},
        'java-testing': {'defaults': ['pm-dev-java:junit-core'], 'optionals': []},
    },
    MARSHAL_KEY_SYSTEM: {'retention': {'logs_days': 1, 'archived_plans_days': 5, 'temp_on_maintenance': True}},
    MARSHAL_KEY_PLAN: {
        'phase-1-init': {'branch_strategy': 'direct'},
        'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
        'phase-3-outline': {},
        'phase-4-plan': {},
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
                'default:push': {},
                'default:create-pr': {},
                'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 300},
                'default:sonar-roundtrip': {},
                'default:lessons-capture': {},
                'default:branch-cleanup': {
                    'pr_merge_strategy': 'squash',
                    'final_merge_without_asking': False,
                    'auto_rebase_threshold': 'no_overlap_only',
                },
                'default:record-metrics': {},
                'default:archive-plan': {},
            },
        },
    },
    'providers': [
        {
            'skill_name': 'workflow-integration-github',
            'display_name': 'GitHub CLI (gh)',
            'auth_type': 'system',
            'default_url': 'https://github.com',
            'description': 'GitHub CI provider via gh CLI',
            'verify_command': 'gh auth status',
            'provider': 'github',
            'repo_url': 'https://github.com/test/repo',
            'detected_at': '2025-01-15T10:30:00Z',
        },
    ],
}

#: Baseline lookup for :func:`create_marshal_json`'s ``preset`` argument.
MARSHAL_PRESETS: dict[str, dict[str, Any]] = {
    MARSHAL_PRESET_MINIMAL: MARSHAL_SCHEMA_DEFAULT,
    MARSHAL_PRESET_JAVA: MARSHAL_SCHEMA_JAVA,
}

#: Module facts written beside marshal.json when ``with_project_data`` is set.
#: ``raw-project-data.json`` is the source of truth for modules, so a fixture
#: whose script resolves modules needs both files or it resolves none.
_RAW_PROJECT_DATA_COMPANION: dict[str, Any] = {
    'project': {'name': 'test-project'},
    'modules': [
        {'name': 'my-core', 'path': 'my-core', 'parent': None, 'build_systems': ['maven'], 'packaging': 'jar'},
        {'name': 'my-ui', 'path': 'my-ui', 'parent': None, 'build_systems': ['maven', 'npm'], 'packaging': 'war'},
    ],
}


def create_marshal_json(
    base_dir: Path,
    config: dict | None = None,
    *,
    preset: str = MARSHAL_PRESET_MINIMAL,
    skill_domains: dict | None = None,
    extra: dict | None = None,
    nest_in_plan_dir: bool = True,
    with_project_data: bool = False,
) -> Path:
    """Write a ``marshal.json`` fixture. The one builder for the whole test tree.

    Supersedes the three incompatible ``create_marshal_json`` definitions the
    tree used to carry, whose behaviour differed in the baseline config, in the
    destination path, and in whether a ``raw-project-data.json`` companion was
    written. Which one a module got depended on which it happened to import, so
    each difference is now an explicit argument instead.

    Two call forms:

    * **Full config** — pass ``config``; it is written verbatim. Use when the
      test asserts against a config shape it states in full.
    * **Defaults plus overrides** — pass ``preset`` (and optionally
      ``skill_domains`` / ``extra``); the named baseline is deep-copied and the
      overrides applied. Use when the test cares about one knob.

    Args:
        base_dir: Directory the fixture is written under. See ``nest_in_plan_dir``
            for exactly where.
        config: Complete config dict, written as-is. Mutually exclusive with
            ``skill_domains`` / ``extra``.
        preset: Which named baseline to start from — :data:`MARSHAL_PRESET_MINIMAL`
            or :data:`MARSHAL_PRESET_JAVA`. Ignored when ``config`` is given.
        skill_domains: Replaces the baseline's ``skill_domains`` key.
        extra: Top-level keys merged over the baseline.
        nest_in_plan_dir: When true (default) the file is written to
            ``base_dir/.plan/marshal.json``, the layout a project root uses. When
            false it is written to ``base_dir/marshal.json``, the layout
            ``plan_context`` sets up — that fixture points ``MARSHAL_PATH`` at
            ``tmp_path/'marshal.json'`` directly, so a nested write would land
            somewhere the script under test never looks.
        with_project_data: Also write the ``raw-project-data.json`` companion
            beside the config.

    Returns:
        Path to the written ``marshal.json``.

    Raises:
        ValueError: when ``config`` is combined with ``skill_domains`` / ``extra``
            (the two forms would disagree about what the result should be), or
            when ``preset`` names no known baseline.

    Example:
        marshal_path = create_marshal_json(temp_dir, skill_domains={
            "system": {"defaults": [...], "optionals": [...]}
        })
    """
    if config is not None and (skill_domains is not None or extra is not None):
        raise ValueError(
            'create_marshal_json: pass either config (full-config form) or '
            'skill_domains/extra (defaults-plus-overrides form), not both.'
        )

    if config is not None:
        data = copy.deepcopy(config)
    else:
        if preset not in MARSHAL_PRESETS:
            raise ValueError(
                f'create_marshal_json: unknown preset {preset!r}; '
                f'known presets are {sorted(MARSHAL_PRESETS)}.'
            )
        # Deep-copied, not ``.copy()``-ed: a shallow copy shares every nested
        # dict with the module-level baseline, so one test mutating
        # ``data['plan']['phase-6-finalize']`` would rewrite the baseline for
        # every later test in the session.
        data = copy.deepcopy(MARSHAL_PRESETS[preset])
        if skill_domains is not None:
            data[MARSHAL_KEY_SKILL_DOMAINS] = skill_domains
        if extra:
            data.update(extra)

    target_dir = base_dir / PLAN_DIR_NAME if nest_in_plan_dir else base_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    marshal_path = target_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(data, indent=2))

    if with_project_data:
        raw_path = target_dir / 'raw-project-data.json'
        raw_path.write_text(json.dumps(copy.deepcopy(_RAW_PROJECT_DATA_COMPANION), indent=2))

    return marshal_path


def create_run_config(base_dir: Path, config: dict | None = None, *, nest_in_plan_dir: bool = False) -> Path:
    """Write a ``run-configuration.json`` fixture beside its marshal config.

    The companion builder to :func:`create_marshal_json`, moved here from the
    manage-config subtree so both files come from one place. ``nest_in_plan_dir``
    defaults to false because ``plan_context`` points ``RUN_CONFIG_PATH`` at
    ``tmp_path/'run-configuration.json'`` directly.

    Args:
        base_dir: Directory the fixture is written under.
        config: Complete config dict. Defaults to an empty version-1 command map.
        nest_in_plan_dir: Write to ``base_dir/.plan/`` instead of ``base_dir``.

    Returns:
        Path to the written ``run-configuration.json``.
    """
    if config is None:
        config = {'version': 1, 'commands': {}}
    target_dir = base_dir / PLAN_DIR_NAME if nest_in_plan_dir else base_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    run_config_path = target_dir / 'run-configuration.json'
    run_config_path.write_text(json.dumps(config, indent=2))
    return run_config_path


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
        # One MonkeyPatch owns PLAN_BASE_DIR for this context; reverted atomically
        # by undo() in __exit__.
        self._mp: pytest.MonkeyPatch | None = None

    def __enter__(self) -> 'BuildContext':
        """Set up the test context."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plan_dir = self.temp_dir / '.plan'
        self.plan_dir.mkdir()

        # Isolate plan-marshall runtime state to this test's tmp dir.
        # file_ops.get_base_dir() honours PLAN_BASE_DIR and falls back the
        # tracked config dir to the same value — so marshal.json (staged at
        # {temp_dir}/.plan/marshal.json) and runtime state both land inside
        # the fixture tree, not the project-local <root>/.plan/local/. A
        # MonkeyPatch instance owns the env var and reverts it atomically in
        # __exit__ (the same mechanism the autouse sandbox uses), so an exception
        # before __exit__ cannot leave PLAN_BASE_DIR pointing at the torn-down dir.
        self._mp = pytest.MonkeyPatch()
        self._mp.setenv('PLAN_BASE_DIR', str(self.plan_dir))

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
        if self._mp is not None:
            self._mp.undo()
            self._mp = None
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
