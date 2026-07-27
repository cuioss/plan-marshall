#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for ``cmd_resolve`` augmentation with bash-timeout / execution-tier fields.

Pins the contract documented in ``_cmd_client`` § "Build-executable
classification": when the resolved ``executable`` is a Bucket B build
notation (``plan-marshall:build-{maven,gradle,npm,pyproject_build}``),
``cmd_resolve`` augments today's TOON shape with four additional fields
(``bash_timeout_seconds``, ``exceeds_bash_ceiling``, ``execution_tier``,
``hint``). Non-build executables (Bucket A ``manage-*`` notations, raw
shell invocations) keep today's shape verbatim.

``bash_timeout_seconds`` is computed as ``max(timeout_get(key,
DEFAULT_BUILD_TIMEOUT), config.min_timeout) + OUTER_TIMEOUT_BUFFER`` — the
engine's OWN declared floor is applied, the same clamp ``execute_direct_base``
enforces at build time. The tier follows that FLOORED value, never the raw
learned value, so the engine's floor decides which verdicts are reachable:
pyproject declares 600 (so ``600 + 30 = 630`` always exceeds the ceiling and
every pyproject command is ``orchestrator``), while Maven / Gradle / npm
declare 300 (so an unmeasured command yields ``330`` and stays ``per_task``).

The cases below cover the public surface:

* Bucket B pyproject, learned value BELOW the engine floor -> floor binds ->
  ``orchestrator`` tier (the under-report the floor clamp fixes).
* Bucket B pyproject, learned value ABOVE the ceiling -> learned value binds
  (floor inert) -> ``orchestrator`` tier.
* Bucket B pyproject with no persisted measurement -> floor binds ->
  ``orchestrator`` tier (first-run truthfulness).
* Bucket B Maven with no persisted measurement -> ``per_task`` tier, proving
  the floor clamp does not collapse every engine onto the orchestrator tier.
* Bucket A ``manage-*`` notation -> legacy TOON (no augmentation).
* Pinned hint strings match exactly so an LLM can recognise them — seeded
  across BOTH tiers so neither template's exact-match guard goes vacuous.

A sixth case (``test_cmd_resolve_cache_tree_layout_emits_augmentation``)
pins the cache-tree regression that PR #515 closed. ``cmd_resolve``'s
augmentation path resolves the build skill's ``_CONFIG`` via
``_MARKETPLACE_BUNDLES_DIR`` (an import-time ``resolve_bundles_root``
result) plus ``resolve_bundle_path``. Pre-#515 ``_cmd_client`` anchored
that lookup with ``parents[4]`` index arithmetic that silently produced
the wrong directory under the versioned plugin-cache layout
(``<base>/plan-marshall/<version>/skills/...``), so ``_load_build_config``
returned ``None`` and the four augmentation fields were dropped. The case
constructs exactly that versioned layout from the real build skill
scripts, points ``_MARKETPLACE_BUNDLES_DIR`` at it, and asserts all four
fields survive — failing on the pre-#515 arithmetic, passing on the
post-#515 ``resolve_bundle_path`` rerouting.
"""

import shutil
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_scripts_dir, load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project as _seed_project  # noqa: E402


_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_maven_cmd_discover = load_script_module('plan-marshall', 'build-maven', '_maven_cmd_discover.py', '_maven_cmd_discover')

cmd_resolve = _cmd_client.cmd_resolve
resolve_command = _cmd_client.resolve_command


# Canonical Bucket B executable shape ``cmd_resolve`` returns for a pyproject
# ``verify`` command scoped to the ``plan-marshall`` bundle module. The
# ``command_args`` string after ``--command-args`` is the literal value that
# ``default_command_key_fn`` normalises to the persisted key
# ``python:verify_plan_marshall``.
_PYPROJECT_VERIFY_EXECUTABLE = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
    'run --command-args "verify plan-marshall"'
)

# Canonical Bucket B executable shape for a MAVEN command. Maven declares a
# 300s outer floor (``MAVEN_OUTER_FLOOR_SECONDS``) against pyproject's 600s, so
# ``max(learned, 300) + 30`` stays under the 600s ceiling for modest learned
# values — this is the only engine family that still yields a ``per_task``
# verdict, and therefore the only one that can keep the per_task hint template
# under exact-match coverage. ``default_command_key_fn`` normalises the
# ``--command-args`` value to the persisted key ``maven:test__pl_core``.
_MAVEN_TEST_EXECUTABLE = (
    'python3 .plan/execute-script.py plan-marshall:build-maven:maven '
    'run --command-args "test -pl core"'
)
_MAVEN_TEST_COMMAND_KEY = 'maven:test__pl_core'

# Bucket A manage-* notation — passes classification's filter and the four
# augmentation fields MUST be absent from the resolve TOON.
_BUCKET_A_MANAGE_EXECUTABLE = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read'
)


def _seed_single_module(tmpdir: str, command: str, executable: str) -> None:
    """Seed a single ``root`` module exposing ``command`` with ``executable``."""
    modules = {
        'root': {
            'name': 'root',
            'build_systems': ['pyproject'],
            'paths': {'module': '.'},
            'commands': {command: executable},
        }
    }
    _seed_project(tmpdir, modules)


def _set_persisted_timeout(plan_dir: Path, command_key: str, duration_seconds: int) -> None:
    """Write a persisted timeout under ``plan_dir/run-configuration.json``.

    The file path mirrors what ``get_run_config_path`` returns when
    ``PLAN_BASE_DIR`` is set to ``plan_dir``.
    """
    import json

    config_path = plan_dir / 'run-configuration.json'
    config = {
        'version': 1,
        'commands': {command_key: {'timeout_seconds': duration_seconds}},
    }
    config_path.write_text(json.dumps(config, indent=2))


@pytest.fixture
def isolated_run_config(monkeypatch, tmp_path):
    """Redirect ``run-configuration.json`` lookup to an isolated tmp dir.

    Routes both the env var (consumed by ``file_ops.get_base_dir``) and the
    module-level ``_config_core.RUN_CONFIG_PATH`` so the in-process
    ``timeout_get`` lookup reads from ``tmp_path`` instead of the real
    repo-local ``.plan/local/run-configuration.json``.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    import _config_core

    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', plan_dir)
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', plan_dir / 'run-configuration.json')

    return plan_dir


# =============================================================================
# Case (a): Bucket B notation, short duration -> floored to orchestrator tier
# =============================================================================


def test_cmd_resolve_bucket_b_short_learned_value_is_raised_by_the_engine_floor(isolated_run_config):
    """A learned value BELOW the engine floor is raised to the floor by the stamp.

    persisted=400 -> timeout_get=max(120, int(400*1.25))=500. The pyproject
    engine declares ``PYTEST_OUTER_FLOOR_SECONDS = 600``, so the stamp applies
    the same ``max(learned, min_timeout)`` clamp ``execute_direct_base``
    enforces: inner=max(500, 600)=600 -> bash=600+30=630.

    630 > 600 so the verdict is ``orchestrator``. This is the whole point of the
    floor clamp: WITHOUT it the stamp reported 530/``per_task`` while the real
    run measured against 600s, under-reporting the bound and mis-tiering the
    command. The learned value never binds below the engine's own floor.
    """
    _set_persisted_timeout(isolated_run_config, 'python:verify_plan_marshall', 400)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['executable'] == _PYPROJECT_VERIFY_EXECUTABLE
    assert result['bash_timeout_seconds'] == 630
    assert result['exceeds_bash_ceiling'] is True
    assert result['execution_tier'] == 'orchestrator'
    assert result['hint'] == 'Exceeds Bash ceiling; orchestrator-tier only'


# =============================================================================
# Case (b): Bucket B notation, long duration -> orchestrator tier
# =============================================================================


def test_cmd_resolve_bucket_b_long_duration_returns_orchestrator(isolated_run_config):
    """Bucket B + persisted timeout > 600s ceiling -> orchestrator tier.

    persisted=800 -> inner=max(120, int(800*1.25))=1000 -> bash=1000+30=1030.
    1030 > 600 so exceeds_bash_ceiling=True, execution_tier=orchestrator,
    hint pins the ceiling overflow phrase.
    """
    _set_persisted_timeout(isolated_run_config, 'python:verify_plan_marshall', 800)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['bash_timeout_seconds'] == 1030
    assert result['exceeds_bash_ceiling'] is True
    assert result['execution_tier'] == 'orchestrator'
    assert result['hint'] == 'Exceeds Bash ceiling; orchestrator-tier only'


# =============================================================================
# Case (c): Bucket B notation, no persisted measurement -> engine floor binds
# =============================================================================


def test_cmd_resolve_bucket_b_no_measurement_uses_the_engine_floor(isolated_run_config):
    """Without a measurement the ENGINE FLOOR binds, not ``DEFAULT_BUILD_TIMEOUT``.

    No timeout_set call -> timeout_get falls back to DEFAULT_BUILD_TIMEOUT=300
    -> inner=max(120, 300)=300. The pyproject floor then raises it:
    max(300, 600)=600 -> bash=600+30=630 -> orchestrator.

    This is the first-run truthfulness property: a command that WILL measure
    past the ceiling is no longer mis-tiered ``per_task`` merely because no
    measurement exists yet. The floor makes the very first stamp honest.
    """
    # No call to _set_persisted_timeout. Empty run-config -> default path.
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['bash_timeout_seconds'] == 630
    assert result['exceeds_bash_ceiling'] is True
    assert result['execution_tier'] == 'orchestrator'
    assert result['hint'] == 'Exceeds Bash ceiling; orchestrator-tier only'


def test_cmd_resolve_maven_no_measurement_stays_per_task(isolated_run_config):
    """An unmeasured MAVEN command still resolves ``per_task``.

    Maven's declared floor is 300, so max(300, 300)=300 -> bash=330 < 600. The
    floor clamp raises the pyproject stamp without dragging every engine to the
    orchestrator tier — the per_task verdict remains reachable and is pinned
    here so a future floor change cannot silently collapse the whole tier axis
    to ``orchestrator``.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _MAVEN_TEST_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['bash_timeout_seconds'] == 330
    assert result['exceeds_bash_ceiling'] is False
    assert result['execution_tier'] == 'per_task'
    assert result['hint'] == 'Bash timeout=330000ms'


# =============================================================================
# Case (d): Bucket A manage-* notation -> legacy TOON (no augmentation)
# =============================================================================


def test_cmd_resolve_bucket_a_manage_notation_returns_legacy_toon(isolated_run_config):
    """Bucket A ``manage-*`` notation does NOT receive the four new fields.

    Classification returns ``None`` for non-build executables, so
    ``cmd_resolve`` falls through without invoking the augmentation helper.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'status', _BUCKET_A_MANAGE_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='status', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['executable'] == _BUCKET_A_MANAGE_EXECUTABLE
    # Legacy TOON shape: none of the four augmentation fields are present.
    assert 'bash_timeout_seconds' not in result
    assert 'exceeds_bash_ceiling' not in result
    assert 'execution_tier' not in result
    assert 'hint' not in result


# =============================================================================
# Case (e): Pinned hint strings match exactly
# =============================================================================


@pytest.mark.parametrize(
    ('executable', 'command_key', 'persisted_seconds', 'expected_bash_timeout', 'expected_hint'),
    [
        # per_task variants — MAVEN-seeded, because Maven's 300s floor leaves
        # headroom under the 600s ceiling. Seeding these against pyproject would
        # push every row past the ceiling and collapse the whole parametrisation
        # onto the orchestrator phrase, silently making the per_task template's
        # exact-match guard vacuous while still LOOKING like a four-row sweep.
        # Row 1: the FLOOR binds (learned 250 < 300).
        (_MAVEN_TEST_EXECUTABLE, _MAVEN_TEST_COMMAND_KEY, 200, 330, 'Bash timeout=330000ms'),
        # Row 2: the LEARNED value binds (500 > 300) — proves the floor is a
        # lower bound, not a replacement for the learned value.
        (_MAVEN_TEST_EXECUTABLE, _MAVEN_TEST_COMMAND_KEY, 400, 530, 'Bash timeout=530000ms'),
        # orchestrator variants — pyproject, learned value already above its
        # 600s floor so the floor is inert here and the learned value binds.
        (
            _PYPROJECT_VERIFY_EXECUTABLE,
            'python:verify_plan_marshall',
            800,
            1030,
            'Exceeds Bash ceiling; orchestrator-tier only',
        ),
        (
            _PYPROJECT_VERIFY_EXECUTABLE,
            'python:verify_plan_marshall',
            5000,
            6280,
            'Exceeds Bash ceiling; orchestrator-tier only',
        ),
    ],
)
def test_cmd_resolve_hint_pins_recognition_token(
    isolated_run_config, executable, command_key, persisted_seconds, expected_bash_timeout, expected_hint
):
    """Hint string is a pinned recognition token, NOT human prose.

    Asserts exact-match equality on the hint string for BOTH tiers, so a
    future refactor that re-words either template (e.g., adds a period,
    changes capitalisation) trips this guard. Keeping at least one per_task row
    and one orchestrator row is load-bearing: a parametrisation in which every
    row renders the same phrase pins only one of the two templates.
    """
    _set_persisted_timeout(isolated_run_config, command_key, persisted_seconds)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', executable)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['bash_timeout_seconds'] == expected_bash_timeout
    assert result['hint'] == expected_hint


# =============================================================================
# Case (f): Cache-tree layout — augmentation survives the versioned plugin-cache
#           shape (PR #515 regression).
# =============================================================================


# Build skills whose ``scripts/`` directories ``cmd_resolve``'s augmentation
# path imports from. ``_load_build_config`` loads ``build-pyproject``'s
# ``_CONFIG``; ``_lookup_bash_timeout`` then imports ``compute_command_key``
# and the timeout helpers from ``script-shared`` (the ``build`` subtree) and
# ``manage-run-config``. The cache-tree fixture mirrors each of these under a
# versioned root so the live resolve path is forced through
# ``resolve_bundle_path``'s versioned branch.
_CACHE_TREE_SKILL_SUBPATHS: tuple[str, ...] = (
    'skills/manage-architecture/scripts',
    'skills/build-pyproject/scripts',
    'skills/script-shared/scripts',
    'skills/manage-run-config/scripts',
)


def _build_cache_tree(base: Path, version: str = '0.1-BETA') -> Path:
    """Materialise a versioned plugin-cache layout of the real build skills.

    Copies each skill's ``scripts/`` directory from the live marketplace
    source into ``<base>/plan-marshall/<version>/skills/<skill>/scripts`` —
    the installed-plugin-cache shape whose depth differs from the
    marketplace-source shape the pre-#515 ``parents[N]`` anchor assumed.

    Returns the bundles-root anchor (``<base>``) suitable for assignment to
    ``_cmd_client._MARKETPLACE_BUNDLES_DIR``: ``resolve_bundle_path(base,
    'plan-marshall', subpath)`` walks ``base/plan-marshall/<version>/subpath``.
    """
    versioned_root = base / 'plan-marshall' / version
    for subpath in _CACHE_TREE_SKILL_SUBPATHS:
        skill_scripts_src = get_scripts_dir('plan-marshall', subpath.split('/')[1])
        dest = versioned_root / subpath
        shutil.copytree(skill_scripts_src, dest, ignore=shutil.ignore_patterns('__pycache__'))
    return base


def test_cmd_resolve_cache_tree_layout_emits_augmentation(isolated_run_config, monkeypatch):
    """Augmentation fields survive the versioned plugin-cache layout (PR #515).

    Builds the versioned ``<base>/plan-marshall/<version>/skills/...`` cache
    tree, repoints ``_cmd_client._MARKETPLACE_BUNDLES_DIR`` at it, and runs
    ``cmd_resolve`` for a Bucket B ``verify`` command. With a persisted
    timeout above the ceiling, all four augmentation fields MUST be present
    and carry the orchestrator-tier values.

    Pre-#515 the ``parents[4]`` anchor resolved the build-config module path
    to a non-existent directory under this layout, so ``_load_build_config``
    returned ``None`` and the four fields were silently dropped — this case
    failed. Post-#515 ``resolve_bundle_path`` reroutes through the versioned
    subdir and the fields are emitted.
    """
    _set_persisted_timeout(isolated_run_config, 'python:verify_plan_marshall', 800)

    original_path = list(sys.path)
    original_modules = dict(sys.modules)

    try:
        with tempfile.TemporaryDirectory() as cache_dir:
            cache_base = _build_cache_tree(Path(cache_dir))
            # Repoint the bundles-root anchor at the versioned cache tree. This is
            # the value pre-#515 arithmetic mis-resolved; resolve_bundle_path()
            # must now find the build-config module under the <version> subdir.
            monkeypatch.setattr(_cmd_client, '_MARKETPLACE_BUNDLES_DIR', cache_base)

            with tempfile.TemporaryDirectory() as project_dir:
                _seed_single_module(project_dir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

                args = Namespace(project_dir=project_dir, resolve_command='verify', module=None)
                result = cmd_resolve(args)
    finally:
        sys.path[:] = original_path
        sys.modules.clear()
        sys.modules.update(original_modules)

    assert result['status'] == 'success'
    assert result['executable'] == _PYPROJECT_VERIFY_EXECUTABLE
    # The four augmentation fields MUST survive the cache-tree resolution.
    assert result['bash_timeout_seconds'] == 1030
    assert result['exceeds_bash_ceiling'] is True
    assert result['execution_tier'] == 'orchestrator'
    assert result['hint'] == 'Exceeds Bash ceiling; orchestrator-tier only'


# =============================================================================
# Case (g): --module default resolves to the real root module
# =============================================================================


def _seed_multi_module(tmpdir: str) -> None:
    """Seed a root module (paths.module='.') plus a nested child module."""
    modules = {
        'root-mod': {
            'name': 'root-mod',
            'build_systems': ['maven'],
            'paths': {'module': '.'},
            'metadata': {'packaging': 'pom'},
            'stats': {},
            'commands': {
                'verify': 'mvn verify',
                'compile': 'mvn compile',
            },
        },
        'child-mod': {
            'name': 'child-mod',
            'build_systems': ['maven'],
            'paths': {'module': 'child-mod'},
            'metadata': {'packaging': 'jar'},
            'stats': {'source_files': 3, 'test_files': 2},
            'commands': {
                'verify': 'mvn verify -pl child-mod',
                'compile': 'mvn compile -pl child-mod',
                'test-compile': 'mvn test-compile -pl child-mod',
                'module-tests': 'mvn test -pl child-mod',
                # quality-gate present but == verify base: profile MIGHT override.
                'quality-gate': 'mvn verify -pl child-mod',
            },
        },
    }
    _seed_project(tmpdir, modules)


def test_resolve_default_alias_resolves_to_root_module():
    """``--module default`` resolves to the real root module (paths.module='.')."""
    _architecture_core.invalidate_crawl_cache()
    _cmd_client._ENRICH_CACHE.clear()
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_multi_module(tmpdir)
        try:
            result = resolve_command('verify', 'default', tmpdir)
        finally:
            _architecture_core.invalidate_crawl_cache(tmpdir)

    assert result['module'] == 'root-mod'
    assert result['command'] == 'verify'


# =============================================================================
# Case (h): profile-canonical request triggers at most one lazy enrich;
#           plain build verbs trigger ZERO _get_maven_metadata calls.
# =============================================================================


def test_resolve_coverage_triggers_at_most_one_enrich(monkeypatch):
    """A ``coverage`` request (absent from cheap map) lazily enriches ONE module."""
    _architecture_core.invalidate_crawl_cache()
    _cmd_client._ENRICH_CACHE.clear()

    enrich_calls = []

    def _spy_enrich(module_path, project_root):
        enrich_calls.append((module_path, project_root))
        # Return a coverage profile so the rebuilt command map carries coverage.
        return {
            'artifact_id': 'child-mod',
            'group_id': 'com.example',
            'packaging': 'jar',
            'profiles': [{'id': 'jacoco', 'canonical': 'coverage'}],
            'dependencies': [],
        }

    monkeypatch.setattr(_maven_cmd_discover, 'enrich_maven_module', _spy_enrich)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_multi_module(tmpdir)
        try:
            result = resolve_command('coverage', 'child-mod', tmpdir)
        finally:
            _architecture_core.invalidate_crawl_cache(tmpdir)
            _cmd_client._ENRICH_CACHE.clear()

    assert result['command'] == 'coverage'
    # The enriched coverage canonical maps to the jacoco profile invocation.
    assert '-Pjacoco' in result['executable']
    assert len(enrich_calls) <= 1, f'coverage must enrich at most once, got {len(enrich_calls)}'
    assert len(enrich_calls) == 1


@pytest.mark.parametrize('verb', ['compile', 'verify', 'module-tests'])
def test_resolve_plain_verbs_trigger_zero_enrich(monkeypatch, verb):
    """``compile`` / ``verify`` / ``test`` (module-tests) NEVER enrich."""
    _architecture_core.invalidate_crawl_cache()
    _cmd_client._ENRICH_CACHE.clear()

    metadata_calls = []
    enrich_calls = []

    def _spy_metadata(module_path, project_root):
        metadata_calls.append((module_path, project_root))
        return None

    def _spy_enrich(module_path, project_root):
        enrich_calls.append((module_path, project_root))
        return None

    monkeypatch.setattr(_maven_cmd_discover, '_get_maven_metadata', _spy_metadata)
    monkeypatch.setattr(_maven_cmd_discover, 'enrich_maven_module', _spy_enrich)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_multi_module(tmpdir)
        try:
            resolve_command(verb, 'child-mod', tmpdir)
        finally:
            _architecture_core.invalidate_crawl_cache(tmpdir)
            _cmd_client._ENRICH_CACHE.clear()

    assert metadata_calls == [], 'plain build verbs must not call _get_maven_metadata'
    assert enrich_calls == [], 'plain build verbs must not call enrich_maven_module'
