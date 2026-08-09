#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for generate_executor.py script."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

from conftest import _MARKETPLACE_SCRIPT_DIRS, MARKETPLACE_ROOT

# Path to the script
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts'
)
GENERATE_SCRIPT = SCRIPTS_DIR / 'generate_executor.py'

#: Fixed date used to name a "recent" global log fixture. Cleanup selects by
#: mtime, so the filename date is cosmetic — pinning it keeps the assertion
#: from recomputing ``date.today()`` and disagreeing across a midnight rollover.
_FROZEN_LOG_DATE = date(2026, 1, 15)


def _subprocess_env() -> dict[str, str]:
    """Build environment with PYTHONPATH for subprocess calls."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    return env


def load_module():
    """Load the generate_executor module."""
    with open(GENERATE_SCRIPT) as f:
        code = f.read()

    import types

    module = types.ModuleType('generate_executor')
    # Provide __file__ for the module
    module.__dict__['__file__'] = str(GENERATE_SCRIPT)
    exec(code, module.__dict__)
    return module


def test_generates_valid_python_dict_syntax():
    """Generated code is valid Python dict syntax."""
    module = load_module()

    mappings = {
        'planning:manage-files': '/path/to/manage-files.py',
        'builder:maven': '/path/to/maven.py',
    }

    code = module.generate_mappings_code(mappings)

    # Should be valid Python when wrapped in dict
    full_code = f'SCRIPTS = {{\n{code}\n}}'
    exec(full_code)  # Should not raise


def test_sorts_mappings_alphabetically():
    """Mappings are sorted alphabetically by notation."""
    module = load_module()

    mappings = {
        'z-bundle:skill': '/path/z.py',
        'a-bundle:skill': '/path/a.py',
        'm-bundle:skill': '/path/m.py',
    }

    code = module.generate_mappings_code(mappings)
    lines = code.strip().split('\n')

    # First line should be a-bundle, last should be z-bundle
    assert 'a-bundle' in lines[0], f"Expected 'a-bundle' in first line, got {lines[0]}"
    assert 'z-bundle' in lines[-1], f"Expected 'z-bundle' in last line, got {lines[-1]}"


def test_same_mappings_same_checksum():
    """Same mappings produce same checksum."""
    module = load_module()

    mappings = {'a:b': '/path/a.py', 'c:d': '/path/c.py'}

    checksum1 = module.compute_checksum(mappings)
    checksum2 = module.compute_checksum(mappings)

    assert checksum1 == checksum2, f'Checksums should be equal: {checksum1} != {checksum2}'


def test_different_mappings_different_checksum():
    """Different mappings produce different checksums."""
    module = load_module()

    mappings1 = {'a:b': '/path/a.py'}
    mappings2 = {'c:d': '/path/c.py'}

    checksum1 = module.compute_checksum(mappings1)
    checksum2 = module.compute_checksum(mappings2)

    assert checksum1 != checksum2, f'Checksums should be different: {checksum1} == {checksum2}'


def test_checksum_is_8_chars():
    """Checksum is truncated to 8 characters."""
    module = load_module()

    mappings = {'a:b': '/path/a.py'}
    checksum = module.compute_checksum(mappings)

    assert len(checksum) == 8, f'Expected 8 chars, got {len(checksum)}'


def test_cleanup_deletes_old_logs(monkeypatch):
    """Cleanup deletes logs older than max_age_days."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / 'logs'
        logs_dir.mkdir()

        # Create old log
        old_log = logs_dir / 'script-execution-2020-01-01.log'
        old_log.write_text('old')

        # Make it old
        old_time = time.time() - (30 * 86400)
        os.utime(old_log, (old_time, old_time))

        # Route the module's logs_dir() helper at the test's temp directory
        # by pointing PLAN_BASE_DIR at tmp (logs live under {base}/logs).
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp))

        deleted = module.cleanup_old_logs(max_age_days=7)
        assert deleted == 1, f'Expected 1 deleted, got {deleted}'
        assert not old_log.exists(), 'Old log should be deleted'


def test_cleanup_preserves_recent_logs(monkeypatch):
    """Cleanup preserves recent logs."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / 'logs'
        logs_dir.mkdir()

        recent_log = logs_dir / f'script-execution-{_FROZEN_LOG_DATE}.log'
        recent_log.write_text('recent')

        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp))

        deleted = module.cleanup_old_logs(max_age_days=7)
        assert deleted == 0, f'Expected 0 deleted, got {deleted}'
        assert recent_log.exists(), 'Recent log should be preserved'


def test_help_output():
    """Script shows help with --help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), '--help'], capture_output=True, text=True, env=_subprocess_env()
    )

    assert result.returncode == 0, f'Script failed: {result.stderr}'
    assert 'generate' in result.stdout, "Missing 'generate' in help"
    assert 'verify' in result.stdout, "Missing 'verify' in help"
    assert 'drift' in result.stdout, "Missing 'drift' in help"
    assert 'paths' in result.stdout, "Missing 'paths' in help"
    assert 'cleanup' in result.stdout, "Missing 'cleanup' in help"
    assert 'write-shim' not in result.stdout, 'write-shim subcommand must be removed'


def test_executor_path_is_tracked_config_dir(monkeypatch, tmp_path):
    """executor_path() resolves to <root>/.plan/execute-script.py via the
    tracked config dir, NOT under the runtime-state base directory."""
    module = load_module()
    # PLAN_BASE_DIR overrides both runtime base and tracked config dir
    # (file_ops.get_tracked_config_dir falls back to PLAN_BASE_DIR before git).
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    result = module.executor_path()
    assert result == plan_dir / 'execute-script.py'


def test_module_has_no_legacy_shim_symbols():
    """Removed symbols should be gone — guards against accidental reintroduction."""
    module = load_module()
    for symbol in ('SHIM_TEMPLATE', 'SHIM_PATH', 'SHIM_DIR', 'write_shim', 'cmd_write_shim', 'detect_legacy_drift'):
        assert not hasattr(module, symbol), f'Legacy symbol {symbol!r} must be removed'


def test_generate_help():
    """Generate subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'generate', '--help'], capture_output=True, text=True, env=_subprocess_env()
    )

    assert result.returncode == 0, f'Script failed: {result.stderr}'
    assert '--force' in result.stdout, "Missing '--force' in help"
    assert '--dry-run' in result.stdout, "Missing '--dry-run' in help"


def test_verify_requires_executor():
    """Verify fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        # Run in temp directory where .plan doesn't exist
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'verify'], capture_output=True, text=True, cwd=tmp, env=_subprocess_env()
        )

        assert result.returncode == 0, f'Expected exit 0 (error in TOON output), got {result.returncode}'


def test_drift_requires_executor():
    """Drift fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        env = _subprocess_env()
        env['PLAN_BASE_DIR'] = tmp
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'drift'], capture_output=True, text=True, cwd=tmp, env=env
        )

        assert result.returncode == 0, f'Expected exit 0 (error in TOON output), got {result.returncode}'
        assert 'Could not read executor mappings' in result.stdout


def test_paths_requires_executor():
    """Paths fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        env = _subprocess_env()
        env['PLAN_BASE_DIR'] = tmp
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'paths'], capture_output=True, text=True, cwd=tmp, env=env
        )

        assert result.returncode == 0, f'Expected exit 0 (error in TOON output), got {result.returncode}'
        assert 'Could not read executor mappings' in result.stdout


def test_drift_help():
    """Drift subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'drift', '--help'], capture_output=True, text=True, env=_subprocess_env()
    )

    assert result.returncode == 0, f'Script failed: {result.stderr}'
    assert 'drift' in result.stdout.lower(), "Missing 'drift' in help"


def test_paths_help():
    """Paths subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'paths', '--help'], capture_output=True, text=True, env=_subprocess_env()
    )

    assert result.returncode == 0, f'Script failed: {result.stderr}'
    assert 'paths' in result.stdout.lower(), "Missing 'paths' in help"


def test_resolve_finds_versioned_path():
    """Resolves path in versioned cache structure (any version)."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create versioned structure: plan-marshall/0.1-BETA/skills/...
        versioned_path = base / 'plan-marshall' / '0.1-BETA' / 'skills' / 'test-skill' / 'scripts'
        versioned_path.mkdir(parents=True)
        script = versioned_path / 'test.py'
        script.write_text('# test')

        result = module._resolve_plan_marshall_path(base, 'skills/test-skill/scripts/test.py')

        assert result.exists(), f'Should find versioned path, got {result}'
        assert '0.1-BETA' in str(result), f'Should include version dir, got {result}'


def test_resolve_finds_any_version():
    """Resolves path regardless of version string (1.0.0, 0.1-BETA, etc)."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create structure with arbitrary version
        versioned_path = base / 'plan-marshall' / '2.5.0-RC1' / 'skills' / 'my-skill'
        versioned_path.mkdir(parents=True)
        (versioned_path / 'SKILL.md').write_text('# skill')

        result = module._resolve_plan_marshall_path(base, 'skills/my-skill/SKILL.md')

        assert result.exists(), f'Should find path with any version, got {result}'
        assert '2.5.0-RC1' in str(result)


def test_resolve_falls_back_to_non_versioned():
    """Falls back to non-versioned path (marketplace structure)."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create non-versioned structure: plan-marshall/skills/...
        non_versioned = base / 'plan-marshall' / 'skills' / 'test-skill'
        non_versioned.mkdir(parents=True)
        (non_versioned / 'SKILL.md').write_text('# skill')

        result = module._resolve_plan_marshall_path(base, 'skills/test-skill/SKILL.md')

        assert result.exists(), f'Should find non-versioned path, got {result}'
        assert 'skills/test-skill/SKILL.md' in str(result)


def test_resolve_skips_hidden_dirs():
    """Skips hidden directories (starting with .)."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create hidden dir with matching structure (should be skipped)
        hidden = base / 'plan-marshall' / '.git' / 'skills' / 'test'
        hidden.mkdir(parents=True)
        (hidden / 'script.py').write_text('# hidden')

        # Create real versioned path
        real = base / 'plan-marshall' / '1.0.0' / 'skills' / 'test'
        real.mkdir(parents=True)
        (real / 'script.py').write_text('# real')

        result = module._resolve_plan_marshall_path(base, 'skills/test/script.py')

        assert '.git' not in str(result), f'Should skip hidden dirs, got {result}'
        assert '1.0.0' in str(result), f'Should find real version, got {result}'


def test_discovers_scripts_from_directory_structure():
    """Fallback discovery finds scripts in expected structure - tests the actual marketplace."""
    # Test against the real marketplace structure rather than mocking
    # This validates the function works with the actual codebase
    module = load_module()

    # Try to get marketplace path
    try:
        base_path = module.get_base_path(use_marketplace=True)
    except FileNotFoundError:
        # Marketplace not available, skip test
        return

    # Run against real marketplace - should find at least some scripts
    mappings = module.discover_scripts_fallback(base_path)

    # If marketplace exists and has scripts, verify format
    if mappings:
        # Check format: all keys should be bundle:skill:script format
        for notation in mappings:
            assert ':' in notation, f'Notation should be bundle:skill:script format, got {notation}'
            parts = notation.split(':')
            assert len(parts) == 3, f'Expected 3 parts in notation, got {parts}'
        # Check values are paths
        for path in mappings.values():
            assert path.endswith('.py'), f'Script path should end with .py, got {path}'
    # If no mappings found, that's also acceptable (marketplace might not exist)
    # The function works correctly - just nothing to discover


def test_skips_test_files():
    """Fallback discovery skips test files."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        bundles_dir = Path(tmp) / 'bundles'
        skill = bundles_dir / 'bundle' / 'skills' / 'skill' / 'scripts'
        skill.mkdir(parents=True)

        # Create test file (should be skipped)
        (skill / 'test_script.py').write_text('test')

        # Create real script
        (skill / 'script.py').write_text('real')

        # Call with temporary bundles directory as base_path
        mappings = module.discover_scripts_fallback(bundles_dir)

        # Should find the real script, not the test
        expected_key = 'bundle:skill:script'
        assert expected_key in mappings, f'Expected {expected_key} in {list(mappings.keys())}'
        assert 'test_' not in mappings[expected_key], 'Should not include test files'


def test_skips_private_modules():
    """Fallback discovery skips underscore-prefixed files (private modules)."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        bundles_dir = Path(tmp) / 'bundles'
        skill = bundles_dir / 'bundle' / 'skills' / 'skill' / 'scripts'
        skill.mkdir(parents=True)

        # Create private module (should be skipped)
        (skill / '_internal.py').write_text('internal')
        (skill / '_helper.py').write_text('helper')

        # Create public script
        (skill / 'main.py').write_text('main')

        # Call with temporary bundles directory as base_path
        mappings = module.discover_scripts_fallback(bundles_dir)

        # Should find the public script, not the private ones
        expected_key = 'bundle:skill:main'
        assert expected_key in mappings, f'Expected {expected_key} in {list(mappings.keys())}'
        path = mappings[expected_key]
        assert '_internal' not in path, 'Should not include _internal.py'
        assert '_helper' not in path, 'Should not include _helper.py'
        assert 'main.py' in path, 'Should include main.py'


def test_collect_script_dirs_includes_subdirectories():
    """Subdirectories of script directories are included in collected paths."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create marketplace structure with subdirectories
        scripts_dir = base / 'bundle' / 'skills' / 'script-shared' / 'scripts'
        (scripts_dir / 'build').mkdir(parents=True)
        (scripts_dir / 'extension').mkdir(parents=True)
        # Place a .py file so the scripts dir is meaningful
        (scripts_dir / 'build' / '_build_shared.py').write_text('# shared')
        (scripts_dir / 'extension' / 'extension_base.py').write_text('# ext')

        dirs = module.collect_script_dirs(base)

        # Should contain the parent scripts dir
        assert str(scripts_dir) in dirs, f'Expected {scripts_dir} in {dirs}'
        # Should contain subdirectories
        assert str(scripts_dir / 'build') in dirs, f'Expected build subdir in {dirs}'
        assert str(scripts_dir / 'extension') in dirs, f'Expected extension subdir in {dirs}'


def test_collect_script_dirs_skips_pycache():
    """__pycache__ directories are excluded from subdirectory scanning."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        scripts_dir = base / 'bundle' / 'skills' / 'my-skill' / 'scripts'
        (scripts_dir / '__pycache__').mkdir(parents=True)
        (scripts_dir / 'real_subdir').mkdir(parents=True)
        (scripts_dir / 'main.py').write_text('# main')

        dirs = module.collect_script_dirs(base)

        pycache_str = str(scripts_dir / '__pycache__')
        real_str = str(scripts_dir / 'real_subdir')
        assert pycache_str not in dirs, f'__pycache__ should be excluded, got {dirs}'
        assert real_str in dirs, f'Expected real_subdir in {dirs}'


def test_collect_script_dirs_skips_hidden_subdirectories():
    """Hidden subdirectories (starting with .) are excluded from scanning."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        scripts_dir = base / 'bundle' / 'skills' / 'my-skill' / 'scripts'
        (scripts_dir / '.hidden').mkdir(parents=True)
        (scripts_dir / 'visible').mkdir(parents=True)
        (scripts_dir / 'main.py').write_text('# main')

        dirs = module.collect_script_dirs(base)

        hidden_str = str(scripts_dir / '.hidden')
        visible_str = str(scripts_dir / 'visible')
        assert hidden_str not in dirs, f'.hidden should be excluded, got {dirs}'
        assert visible_str in dirs, f'Expected visible in {dirs}'


def test_build_pythonpath_includes_subdirectories():
    """build_pythonpath includes subdirectory paths in the PYTHONPATH string."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create structure with subdirectories
        scripts_dir = base / 'my-bundle' / 'skills' / 'script-shared' / 'scripts'
        (scripts_dir / 'build').mkdir(parents=True)
        (scripts_dir / 'build' / '_helper.py').write_text('# helper')

        pythonpath = module.build_pythonpath(base)

        assert str(scripts_dir) in pythonpath, f'Parent dir missing from PYTHONPATH: {pythonpath}'
        assert str(scripts_dir / 'build') in pythonpath, f'Subdir missing from PYTHONPATH: {pythonpath}'


def test_collect_script_dirs_versioned_includes_subdirectories():
    """Subdirectory scanning works with versioned plugin-cache structure."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create versioned structure: bundle/1.0.0/skills/skill/scripts/subdir/
        scripts_dir = base / 'plan-marshall' / '1.0.0' / 'skills' / 'script-shared' / 'scripts'
        (scripts_dir / 'build').mkdir(parents=True)
        (scripts_dir / 'build' / '_build_shared.py').write_text('# shared')

        dirs = module.collect_script_dirs(base)

        assert str(scripts_dir) in dirs, f'Expected versioned scripts dir in {dirs}'
        assert str(scripts_dir / 'build') in dirs, f'Expected versioned build subdir in {dirs}'


def test_generate_executor_imports_without_executor_pythonpath():
    """generate_executor.py must resolve its own imports without executor PYTHONPATH.

    This script is called directly during wizard Step 4 (before executor exists)
    to generate the executor. It must self-resolve its dependencies.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT), '--help'],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f'generate_executor.py failed without PYTHONPATH:\n{result.stderr}'


# These tests pin the marketplace-discovery resolution order documented in
# script-shared/marketplace_paths.find_marketplace_path: explicit param > env
# var > script-relative walk > cwd. They construct a fake marketplace tree
# with a sentinel bundle/skill/scripts/foo.py and verify the regenerated
# executor's SCRIPTS dict reflects the fake path — not the project cwd or
# plugin cache.
def _build_fake_marketplace(tmp_path: Path) -> Path:
    """Build a minimal but functional fake marketplace under tmp_path.

    Copies the real ``plan-marshall`` and ``pm-plugin-development`` bundles so
    ``generate_executor.py`` can run end-to-end (it needs the executor template,
    logging scripts, and inventory script). Then adds a sentinel
    ``fake-bundle/skills/fake-skill/scripts/foo.py`` whose absolute path
    serves as the load-bearing assertion target — that path can ONLY be
    discovered if ``--marketplace-root`` (or ``PM_MARKETPLACE_ROOT``)
    correctly anchored discovery to the fake tree.

    Returns:
        Path to ``tmp_path / 'fake-ws'`` — the value to pass as
        ``--marketplace-root`` (the layout is ``<root>/marketplace/bundles``).
    """
    fake_ws = tmp_path / 'fake-ws'
    fake_bundles = fake_ws / 'marketplace' / 'bundles'
    fake_bundles.mkdir(parents=True)

    # Copy real bundles required for the generate flow:
    # - plan-marshall: provides the executor template, logging scripts, and
    #   shared script-shared modules used by collect_script_dirs/build_pythonpath.
    # - pm-plugin-development: provides scan-marketplace-inventory used by
    #   discover_scripts. Without it, generate falls back to glob discovery
    #   (which still works — but we mirror the real flow here).
    for bundle_name in ('plan-marshall', 'pm-plugin-development'):
        src = MARKETPLACE_ROOT / bundle_name
        dst = fake_bundles / bundle_name
        shutil.copytree(src, dst)

    # Add the sentinel fake bundle/skill/script. Inventory discovery requires
    # ``.claude-plugin/plugin.json`` to recognize a directory as a bundle.
    fake_bundle = fake_bundles / 'fake-bundle'
    plugin_json_dir = fake_bundle / '.claude-plugin'
    plugin_json_dir.mkdir(parents=True)
    (plugin_json_dir / 'plugin.json').write_text(
        '{"name": "fake-bundle", "version": "0.0.1", "description": "Test fixture"}\n'
    )

    fake_scripts = fake_bundle / 'skills' / 'fake-skill' / 'scripts'
    fake_scripts.mkdir(parents=True)
    fake_script = fake_scripts / 'foo.py'
    fake_script.write_text('"""Sentinel script for marketplace-root regression test."""\n')

    return fake_ws


def _read_generated_scripts(generated_executor: Path) -> dict[str, str]:
    """Load the generated executor and return its SCRIPTS dict.

    Spawns a subprocess (mirroring how get_executor_mappings does it) to avoid
    polluting the test's interpreter with the generated module.
    """
    import json as _json

    code = (
        'import importlib.util, json, sys\n'
        f"spec = importlib.util.spec_from_file_location('gen_executor', '{generated_executor}')\n"
        'module = importlib.util.module_from_spec(spec)\n'
        '# The generated executor injects sys.path entries and imports plan_logging\n'
        '# at module-import time. Skip that side-effect by loading without\n'
        '# executing — but we DO need module-level SCRIPTS, which is just a\n'
        '# literal dict assignment, so executing the module body is required.\n'
        'spec.loader.exec_module(module)\n'
        'print(json.dumps(module.SCRIPTS))\n'
    )
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath

    result = subprocess.run(
        [sys.executable, '-c', code], capture_output=True, text=True, env=env, timeout=30
    )
    assert result.returncode == 0, (
        f'Failed to load generated executor: stdout={result.stdout!r} stderr={result.stderr!r}'
    )
    mappings: dict[str, str] = _json.loads(result.stdout.strip())
    return mappings


def _gen_module_budget_env() -> str:
    """The generator's own budget env-var name — read, never re-typed here."""
    return str(load_module()._SURFACE_DERIVATION_BUDGET_ENV)


def _generate_with_anchor(
    tmp_path: Path,
    fake_ws: Path,
    *,
    use_flag: bool,
    monkeypatch,
) -> dict[str, str]:
    """Run ``generate_executor.py generate`` against a fake marketplace.

    Routes both the discovery anchor (via ``--marketplace-root`` flag OR
    ``PM_MARKETPLACE_ROOT`` env var) and the executor write target (via
    ``PLAN_BASE_DIR``) so the generated executor lands inside ``tmp_path``
    instead of the real project's ``.plan/execute-script.py``.

    Returns:
        The SCRIPTS dict from the regenerated executor.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)

    # PLAN_BASE_DIR redirects executor_path() AND state_path()/logs_dir()
    # away from the real project tree.
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    # CWD-discovery-poisoning safety: chdir into tmp_path so the cwd-based
    # branch of find_marketplace_path can NEVER accidentally resolve to the
    # real project marketplace. This forces any non-flag/non-env-var success
    # to come from the script-relative walk (branch 3) — which we explicitly
    # avoid by deleting that anchor below would be impractical, so we lean
    # on the assertion target (fake foo.py path under tmp_path) instead.
    monkeypatch.chdir(tmp_path)

    cmd = [sys.executable, str(GENERATE_SCRIPT), 'generate']
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    env['PLAN_BASE_DIR'] = str(plan_dir)
    # These tests assert DISCOVERY ANCHORING, not accept-set derivation, and the
    # fake workspace is a full copy of the real bundles — so a cold derivation
    # here would probe ~145 scripts' --help to prove a path. Zero the budget: the
    # generator then emits no surfaces, which is the documented safe degrade, and
    # the SCRIPTS dict these tests read is unaffected.
    env[_gen_module_budget_env()] = '0'

    if use_flag:
        cmd.extend(['--marketplace-root', str(fake_ws)])
        env.pop('PM_MARKETPLACE_ROOT', None)
    else:
        env['PM_MARKETPLACE_ROOT'] = str(fake_ws)

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, (
        f'generate failed (use_flag={use_flag}):\nstdout={result.stdout}\nstderr={result.stderr}'
    )

    generated_executor = plan_dir / 'execute-script.py'
    assert generated_executor.exists(), (
        f'Expected generated executor at {generated_executor}, stdout={result.stdout}'
    )

    return _read_generated_scripts(generated_executor)


def test_marketplace_root_flag_anchors_discovery_to_supplied_path(outside_repo_dir, monkeypatch):
    """generate --marketplace-root <path> roots the SCRIPTS dict at <path>.

    Regression for the case where worktree-driven invocations of
    generate_executor.py picked up the wrong marketplace tree because the
    cwd-based fallback resolved to the parent checkout. The flag must
    override every other resolution branch.

    Uses ``outside_repo_dir`` (not ``tmp_path``): the helper chdir's into this
    directory precisely so the cwd-based discovery branch finds NO marketplace
    ancestor, isolating the ``--marketplace-root`` flag as the sole anchor.
    pytest's tmp_path now roots under the repo-local --basetemp, whose ancestry
    HAS a real marketplace/bundles — which would poison the cwd branch.
    """
    fake_ws = _build_fake_marketplace(outside_repo_dir)

    mappings = _generate_with_anchor(outside_repo_dir, fake_ws, use_flag=True, monkeypatch=monkeypatch)

    # Sentinel: the fake bundle script must appear in SCRIPTS, with its
    # absolute path rooted at the fake marketplace tree (NOT the real
    # project's marketplace and NOT the plugin cache).
    expected_notation = 'fake-bundle:fake-skill:foo'
    assert expected_notation in mappings, (
        f'Expected {expected_notation!r} in SCRIPTS keys; got {sorted(mappings)[:10]}...'
    )

    sentinel_path = mappings[expected_notation]
    assert sentinel_path.startswith(str(fake_ws)), (
        f'Expected sentinel path rooted at {fake_ws}, got {sentinel_path}'
    )

    # No mapping may resolve under the real project's marketplace tree or
    # the plugin cache when --marketplace-root is supplied.
    real_marketplace = str(MARKETPLACE_ROOT.resolve())
    plugin_cache = str(Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall')
    real_cwd = str(Path(__file__).resolve().parents[3])  # project root
    for notation, path in mappings.items():
        assert not path.startswith(real_marketplace), (
            f'{notation} resolved to real marketplace {path}, not fake {fake_ws}'
        )
        assert not path.startswith(plugin_cache), (
            f'{notation} resolved to plugin cache {path}, not fake {fake_ws}'
        )
        # Defense-in-depth: the sentinel path is the strongest signal, but
        # also verify no path leaked back to the real project root via cwd
        # discovery. Allow paths under the out-of-repo working dir which (on
        # macOS) may resolve via /private/var symlinks.
        if not path.startswith(str(outside_repo_dir.resolve())) and not path.startswith(str(outside_repo_dir)):
            assert not path.startswith(real_cwd), (
                f'{notation} resolved under real cwd {real_cwd}: {path}'
            )


def test_pm_marketplace_root_env_var_anchors_discovery(tmp_path, monkeypatch):
    """PM_MARKETPLACE_ROOT (env var path) anchors discovery identically.

    Equivalent to the flag, but sourced from the environment per the
    documented resolution order in find_marketplace_path. Set via
    monkeypatch.setenv to avoid the inline ``VAR=val cmd`` shell shape that
    persona-plan-marshall-agent forbids.
    """
    fake_ws = _build_fake_marketplace(tmp_path)

    mappings = _generate_with_anchor(tmp_path, fake_ws, use_flag=False, monkeypatch=monkeypatch)

    expected_notation = 'fake-bundle:fake-skill:foo'
    assert expected_notation in mappings, (
        f'Expected {expected_notation!r} in SCRIPTS keys; got {sorted(mappings)[:10]}...'
    )

    sentinel_path = mappings[expected_notation]
    assert sentinel_path.startswith(str(fake_ws)), (
        f'Expected sentinel path rooted at {fake_ws} (via PM_MARKETPLACE_ROOT), '
        f'got {sentinel_path}'
    )

    real_marketplace = str(MARKETPLACE_ROOT.resolve())
    for notation, path in mappings.items():
        assert not path.startswith(real_marketplace), (
            f'{notation} leaked through to real marketplace {path} despite '
            f'PM_MARKETPLACE_ROOT={fake_ws}'
        )


# The executor template no longer writes any session->plan binding — the
# in-template active-plan cache writer was removed outright (clean break,
# compatibility: breaking). The binding policy now lives in platform-runtime's
# `session bind`, fired from the manage-status phase-state-write drive seam.
# The removal guard below (test_template_carries_no_session_binding_code) pins
# that no binding symbol survives in the rendered template AND that the build-
# class change-ledger boundary's own `_active_plan_id` resolution — independent
# of the removed binder — is preserved. Mirrors the "removed" precedent in
# test/plan-marshall/manage-status/test_merge_lock_removed.py.

TEMPLATE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
)


def _load_template_module():
    """Load the executor template as a Python module with stub placeholders.

    The template contains ``{{...}}`` substitution tokens that are filled in by
    generate_executor.py at generation time. For unit testing helper functions
    we replace those tokens with inert stand-ins and exec the resulting source
    as a fresh module — no subprocess, no real PYTHONPATH writes.
    """
    import types

    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    # Inert substitutions: empty mappings, no shared dirs, a temp logging
    # placeholder pointing at the real logging scripts so `from plan_logging
    # import ...` succeeds at module load.
    logging_dir = str(
        Path(__file__).parent.parent.parent.parent
        / 'marketplace/bundles/plan-marshall/skills/manage-logging/scripts'
    )
    source = source.replace('{{SCRIPT_MAPPINGS}}', '')
    source = source.replace('{{SCRIPT_SURFACES}}', '')
    source = source.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    source = source.replace('{{LOGGING_DIR}}', logging_dir)
    source = source.replace('{{SHARED_MODULE_DIRS}}', '# (none)')
    source = source.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    source = source.replace('{{PLAN_DIR_NAME}}', '.plan')
    source = source.replace('{{EXECUTOR_TARGET}}', 'claude')
    source = source.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )

    # Ensure shared dirs are importable for plan_logging's transitive imports.
    for extra in _MARKETPLACE_SCRIPT_DIRS:
        if extra not in sys.path:
            sys.path.insert(0, extra)

    module = types.ModuleType('executor_template_under_test')
    module.__dict__['__file__'] = str(TEMPLATE_PATH)
    exec(compile(source, str(TEMPLATE_PATH), 'exec'), module.__dict__)
    return module


def test_template_carries_no_session_binding_code():
    """Clean-break guard: the rendered executor template carries NO session->plan
    binding code, and the loaded template module exposes none of the removed
    binding symbols. Mirrors the "removed" precedent in
    test/plan-marshall/manage-status/test_merge_lock_removed.py.

    The binding was relocated to platform-runtime's `session bind` (fired from
    the manage-status phase-state-write drive seam); the executor no longer
    writes any binding on any call.
    """
    source = TEMPLATE_PATH.read_text(encoding='utf-8')

    # No binding helper definitions, constant, or session-env read survive.
    for needle in (
        'def _write_active_plan(',
        'def _read_active_plan(',
        'def _active_plan_dir_exists(',
        'def _validate_active_plan_id(',
        '_ACTIVE_PLAN_ID_MAX_LEN',
        'CLAUDE_CODE_SESSION_ID',
        'active-plan',
    ):
        assert needle not in source, (
            f'removed binding artifact {needle!r} still present in the executor template'
        )

    # The build-class change-ledger boundary's own _active_plan_id resolution is
    # PRESERVED (it is independent of the removed binder).
    assert '_active_plan_id = extract_plan_id(script_args) or audit_plan_id' in source, (
        'the build-class ledger boundary _active_plan_id resolution must be preserved'
    )

    # The loaded template module exposes none of the removed binding symbols.
    module = _load_template_module()
    for symbol in (
        '_write_active_plan',
        '_read_active_plan',
        '_active_plan_dir_exists',
        '_validate_active_plan_id',
        '_ACTIVE_PLAN_ID_MAX_LEN',
    ):
        assert not hasattr(module, symbol), (
            f'removed binding symbol {symbol!r} must be absent from the rendered template module'
        )


# AST subcommand extractor removed (lesson 2026-05-26-09-001 / plan
# fix-generate-executor-ast-subcommands). The generator no longer emits a
# SUBCOMMANDS dict; drift is now detected at dev-time via plugin-doctor and
# post-hoc via plan-retrospective.
def test_ast_subcommand_extractor_symbols_removed():
    """Removed AST extractor symbols must be absent — guards against reintroduction."""
    module = load_module()
    for symbol in (
        '_extract_subcommands_from_source',
        'extract_subcommands_for_path',
        'build_subcommands_mapping',
        'generate_subcommands_code',
        'generate_subcommands_block',
    ):
        assert not hasattr(module, symbol), (
            f'AST extractor symbol {symbol!r} must be removed from generate_executor.py'
        )


# Executor-guard backstop decision (ADR-002, deliverable 11): under the
# move-based, cwd-pinned hermetic worktree model the structural cwd-pinning is
# the PRIMARY enforcement; a secondary runtime worktree-write refusal guard
# inside generate_executor.py was evaluated and REJECTED as redundant. These
# tests pin the recorded decision so the rejected backstop is not silently
# reintroduced and the ADR cross-reference does not rot.
def test_module_docstring_records_executor_guard_backstop_decision():
    """The module docstring MUST record the keep/remove backstop decision and
    cross-reference ADR-002 (deliverable 11 acceptance criterion)."""
    module = load_module()
    docstring = module.__doc__ or ''

    assert 'ADR-002' in docstring, 'Module docstring must cross-reference ADR-002'
    # The decision is recorded explicitly (keep/remove wording present).
    assert 'DECISION:' in docstring, 'Module docstring must record an explicit DECISION line'
    lowered = docstring.lower()
    assert 'backstop' in lowered, 'Decision must frame the guard/lint as a secondary backstop'
    assert 'cwd-pinning' in lowered or 'cwd pinning' in lowered, (
        'Decision must name structural cwd-pinning as the primary enforcement'
    )


def test_no_worktree_write_refusal_guard_symbol_present():
    """The rejected runtime worktree-write refusal guard must NOT exist — guards
    against accidental reintroduction of the redundant backstop."""
    module = load_module()
    for symbol in (
        'refuse_worktree_write',
        'assert_main_checkout',
        'guard_worktree_executor',
        '_refuse_worktree_bound_regen',
    ):
        assert not hasattr(module, symbol), (
            f'Rejected worktree-write refusal guard symbol {symbol!r} must be absent '
            f'(ADR-002: structural cwd-pinning is the primary enforcement)'
        )


# The executor template appends one kind=build change-ledger entry after every
# build-EXECUTING dispatch — a notation under plan-marshall:build-pyproject /
# build-maven / build-gradle / build-npm, dispatched with the build-executing
# subcommand. Build-class-ness is the conjunction of both conditions, so a query
# verb under a build wrapper writes no row. The freshness gate reads these
# entries to answer "was this exact working-tree state built?". The append is
# fire-and-forget and — critically — fires AFTER the subprocess returns, never
# before dispatch, so only completed builds (regardless of exit_code) are
# recorded. These tests pin the source-level presence, the structural import of
# the ledger primitives, and the after-return ordering.
def test_template_contains_build_ledger_append_at_dispatch_boundary():
    """The executor template must invoke the build-class ledger append at the
    dispatch boundary, guarded by the build-class notation predicate."""
    source = TEMPLATE_PATH.read_text(encoding='utf-8')

    assert 'def _append_build_ledger_record(' in source, (
        '_append_build_ledger_record helper missing from template'
    )
    assert 'def _is_build_class_notation(' in source, (
        '_is_build_class_notation predicate missing from template'
    )
    # main() must guard the append behind the build-class predicate and call
    # the appender with the resolved plan_id and exit_code. The guard passes BOTH
    # conjuncts — the notation and the already-computed subcommand — so a query
    # verb under a build wrapper cannot reach the append.
    assert 'if _is_build_class_notation(notation, subcommand):' in source, (
        'main() must guard the ledger append behind '
        '_is_build_class_notation(notation, subcommand)'
    )
    assert '_append_build_ledger_record(' in source, (
        'main() must invoke _append_build_ledger_record at the dispatch boundary'
    )


def test_template_build_ledger_uses_shared_primitives():
    """The append must reuse the manage-change-ledger writer and the shared
    worktree-sha helper rather than re-implementing the hash or the append.

    The status symbol pinned here is ``WRAPPER_CLAIMABLE_BUILD_STATUSES``, NOT
    the full ``BUILD_STATUSES`` vocabulary. That narrowing is the enforcement
    point for the derived-only statuses: the boundary compares a wrapper's
    stdout claim against the claimable half alone, so importing the wider set
    here would let a wrapper mint ``killed`` or ``unknown`` for itself.
    """
    source = TEMPLATE_PATH.read_text(encoding='utf-8')

    expected_import = (
        'from _ledger_core import (  # type: ignore[import-not-found]\n'
        '    WRAPPER_CLAIMABLE_BUILD_STATUSES,\n'
        '    append_entry,\n'
        '    build_record,\n'
        ')'
    )
    assert expected_import in source, (
        'template must import WRAPPER_CLAIMABLE_BUILD_STATUSES + append_entry + build_record '
        'from the manage-change-ledger core'
    )
    assert 'from worktree_sha import compute_worktree_sha' in source, (
        'template must import compute_worktree_sha from the shared script-shared helper'
    )


def test_shared_module_dirs_wires_ledger_import_dirs():
    """get_shared_module_dirs must include the dirs the template imports at
    executor module level.

    The template imports ``_ledger_core`` (from manage-change-ledger/scripts)
    and ``worktree_sha`` (from script-shared/scripts) at the executor's own
    module level. Those imports resolve at runtime ONLY if get_shared_module_dirs
    places both dirs on the executor's sys.path via the {{SHARED_MODULE_DIRS}}
    block. This is the generator-side half of the contract whose template-side
    half is asserted by test_template_build_ledger_uses_shared_primitives — a
    regression guard against the broken-executor defect where the template
    imported the modules but the generator never wired their dirs.
    """
    module = load_module()

    dirs = module.get_shared_module_dirs(MARKETPLACE_ROOT)
    dir_strs = [str(d) for d in dirs]

    assert any(d.endswith('manage-change-ledger/scripts') for d in dir_strs), (
        'get_shared_module_dirs must include manage-change-ledger/scripts so the '
        f'executor-level `from _ledger_core import ...` resolves; got {dir_strs}'
    )
    assert any(d.endswith('script-shared/scripts') for d in dir_strs), (
        'get_shared_module_dirs must include script-shared/scripts so the '
        f'executor-level `from worktree_sha import ...` resolves; got {dir_strs}'
    )


def test_template_build_ledger_append_fires_after_dispatch_not_before():
    """The ledger append must be placed AFTER the subprocess dispatch returns,
    never before it — only completed dispatches are recorded.

    Asserted positionally on the rendered source: the
    ``_append_build_ledger_record(`` call site in main() must appear strictly
    after the ``subprocess.run(`` dispatch and after the exit_code is bound.
    """
    source = TEMPLATE_PATH.read_text(encoding='utf-8')

    dispatch_idx = source.find('result = subprocess.run(')
    assert dispatch_idx != -1, 'subprocess.run dispatch not found in template'

    # The call site inside main() is guarded by the predicate; locate the guard
    # and the call that follows it.
    guard_idx = source.find('if _is_build_class_notation(notation, subcommand):')
    assert guard_idx != -1, 'build-class guard not found in main()'

    call_site_idx = source.find('_append_build_ledger_record(', guard_idx)
    assert call_site_idx != -1, 'ledger append call site not found after the guard'

    assert call_site_idx > dispatch_idx, (
        'ledger append must fire AFTER the subprocess dispatch, not before — '
        f'append at {call_site_idx} precedes dispatch at {dispatch_idx}'
    )

    # The exit_code the append records is bound from the dispatch result, so the
    # call site must also follow the exit_code assignment.
    exit_code_idx = source.find('exit_code = result.returncode')
    assert exit_code_idx != -1, 'exit_code assignment not found in template'
    assert call_site_idx > exit_code_idx, (
        'ledger append must fire after exit_code is bound from the dispatch result'
    )


def test_template_build_ledger_helpers_loadable_and_predicate_works():
    """The rendered template loads as a module (its new ledger-core and
    worktree-sha imports resolve), and the build-class predicate classifies
    build-* notations correctly while rejecting non-build notations."""
    module = _load_template_module()

    assert hasattr(module, '_is_build_class_notation'), (
        '_is_build_class_notation must be defined in the loaded template module'
    )
    assert hasattr(module, '_append_build_ledger_record'), (
        '_append_build_ledger_record must be defined in the loaded template module'
    )

    # Build-class notations across all four build-* skills classify as build when
    # dispatched with the build-executing subcommand.
    for build_notation in (
        'plan-marshall:build-pyproject:pyproject_build',
        'plan-marshall:build-maven:maven',
        'plan-marshall:build-gradle:gradle',
        'plan-marshall:build-npm:npm',
    ):
        assert module._is_build_class_notation(build_notation, 'run'), (
            f'{build_notation} run must classify as a build-class dispatch'
        )

    # Non-build notations must NOT classify as build, even with the run verb.
    for non_build_notation in (
        'plan-marshall:manage-files:manage-files',
        'plan-marshall:manage-logging:manage-logging',
        'pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory',
    ):
        assert not module._is_build_class_notation(non_build_notation, 'run'), (
            f'{non_build_notation} must NOT classify as a build-class dispatch'
        )


# ============================================================================
# Deliverable 1: machine-portable script-set fingerprint
# ============================================================================
# compute_executor_scripts_fingerprint() relativizes the discover_scripts
# notation→path mapping before hashing, so the fingerprint is identical across
# machines/checkouts (absolute prefixes differ) and moves only when a script is
# added, removed, moved, or renamed — never on a content-only edit. The target
# generator (marketplace/targets/generate.py) consumes it to stamp
# executor_scripts_fingerprint into dist-manifest.json.


def test_scripts_fingerprint_machine_portable_across_absolute_roots():
    """Two checkouts with an identical script layout under different absolute
    roots produce a byte-identical fingerprint (path-relativization)."""
    module = load_module()

    root_a = Path('/machine-a/home/dev/marketplace/bundles')
    root_b = Path('/entirely/other/ci-runner/work/marketplace/bundles')

    def _layout(root: Path) -> dict[str, str]:
        return {
            'plan-marshall:manage-files:manage-files': str(
                root / 'plan-marshall/skills/manage-files/scripts/manage-files.py'
            ),
            'pm-dev-java:java-core:foo': str(root / 'pm-dev-java/skills/java-core/scripts/foo.py'),
        }

    fp_a = module.compute_executor_scripts_fingerprint(_layout(root_a), root_a)
    fp_b = module.compute_executor_scripts_fingerprint(_layout(root_b), root_b)

    assert fp_a == fp_b, f'Fingerprint must be machine-portable: {fp_a} != {fp_b}'
    assert len(fp_a) == 8, f'Fingerprint reuses the 8-char checksum machinery, got {len(fp_a)}'


def test_scripts_fingerprint_insensitive_to_content_only_edits(tmp_path):
    """Editing a script's body (same notation, same path) leaves the fingerprint
    unchanged — the hash never reads file content."""
    module = load_module()

    base = tmp_path / 'bundles'
    script = base / 'plan-marshall' / 'skills' / 'my-skill' / 'scripts' / 'foo.py'
    script.parent.mkdir(parents=True)
    script.write_text('# original body\n')
    mappings = {'plan-marshall:my-skill:foo': str(script)}

    fp_before = module.compute_executor_scripts_fingerprint(mappings, base)
    # Heavily rewrite the body — path and notation are unchanged.
    script.write_text('# a completely rewritten, much longer body\n' * 50)
    fp_after = module.compute_executor_scripts_fingerprint(mappings, base)

    assert fp_before == fp_after, 'Content-only edit must not change the fingerprint'


def test_scripts_fingerprint_changes_on_add_remove_and_move():
    """Adding, removing, moving, or renaming a script changes the fingerprint."""
    module = load_module()

    base = Path('/ws/marketplace/bundles')
    baseline = {'a:b:c': str(base / 'a/skills/b/scripts/c.py')}
    added = {**baseline, 'd:e:f': str(base / 'd/skills/e/scripts/f.py')}
    moved = {'a:b:c': str(base / 'a/skills/b/scripts/c_renamed.py')}

    fp_baseline = module.compute_executor_scripts_fingerprint(baseline, base)
    fp_added = module.compute_executor_scripts_fingerprint(added, base)
    fp_moved = module.compute_executor_scripts_fingerprint(moved, base)

    assert fp_baseline != fp_added, 'Adding a script must change the fingerprint'
    assert fp_baseline != fp_moved, 'Moving/renaming a script must change the fingerprint'


# ============================================================================
# Deliverable 1: template version/fingerprint placeholder substitution
# ============================================================================


def test_generate_substitutes_version_and_fingerprint_from_manifest(tmp_path, monkeypatch):
    """generate_executor resolves {{GENERATED_VERSION}} / {{MAPPINGS_FINGERPRINT}}
    from the installed dist-manifest.json (via $PM_DIST_MANIFEST)."""
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps(
            {
                'version': '0.1.42',
                'source_sha': 'abc123',
                'executor_scripts_fingerprint': 'deadbeef',
                'executor_changed_at_version': '0.1.40',
                'config_seed_fingerprint': 'cafef00d',
                'config_changed_at_version': '0.1.30',
            }
        ),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=False)
    assert result['status'] == 'success', f'generate_executor should succeed with an empty mapping set: {result}'

    generated = plan_dir / 'execute-script.py'
    assert generated.is_file(), f'Expected generated executor at {generated}'
    text = generated.read_text(encoding='utf-8')

    assert "MARSHALL_VERSION = '0.1.42'" in text, 'MARSHALL_VERSION must be substituted from manifest.version'
    assert "MAPPINGS_FINGERPRINT = 'deadbeef'" in text, (
        'MAPPINGS_FINGERPRINT must be substituted from manifest.executor_scripts_fingerprint'
    )
    assert '{{GENERATED_VERSION}}' not in text, 'placeholder must be fully substituted'
    assert '{{MAPPINGS_FINGERPRINT}}' not in text, 'placeholder must be fully substituted'


def test_generate_uses_empty_sentinel_on_fresh_install(tmp_path, monkeypatch):
    """With no installed manifest, the version/fingerprint placeholders resolve
    to the empty sentinel — no error, executor still generates."""
    module = load_module()

    # Point PM_DIST_MANIFEST at a non-existent file so no manifest is found.
    monkeypatch.setenv('PM_DIST_MANIFEST', str(tmp_path / 'absent-dist-manifest.json'))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=False)
    assert result['status'] == 'success', f'fresh install (no manifest) must still generate the executor: {result}'

    text = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')
    assert "MARSHALL_VERSION = ''" in text, 'fresh install must stamp the empty version sentinel'
    assert "MAPPINGS_FINGERPRINT = ''" in text, 'fresh install must stamp the empty fingerprint sentinel'


def test_find_installed_manifest_path_uses_resolved_target(tmp_path, monkeypatch):
    """The meta-project target-tree fallback looks under target/<target>/, not
    a hard-coded target/claude/ — so an opencode preflight reads the opencode
    manifest instead of falling back to (or missing) claude's."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    bundles_dir = tmp_path / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)

    claude_manifest = tmp_path / 'target' / 'claude' / 'dist-manifest.json'
    claude_manifest.parent.mkdir(parents=True)
    claude_manifest.write_text('{"version": "claude-version"}', encoding='utf-8')

    opencode_manifest = tmp_path / 'target' / 'opencode' / 'dist-manifest.json'
    opencode_manifest.parent.mkdir(parents=True)
    opencode_manifest.write_text('{"version": "opencode-version"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(bundles_dir, target='opencode')

    assert resolved == opencode_manifest, 'opencode target must resolve target/opencode/dist-manifest.json'


def test_find_installed_manifest_path_defaults_to_claude(tmp_path, monkeypatch):
    """Omitting ``target`` preserves the pre-existing claude-only behavior."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    bundles_dir = tmp_path / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)

    claude_manifest = tmp_path / 'target' / 'claude' / 'dist-manifest.json'
    claude_manifest.parent.mkdir(parents=True)
    claude_manifest.write_text('{"version": "claude-version"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(bundles_dir)

    assert resolved == claude_manifest


def test_find_installed_manifest_path_resolves_cache_root_manifest(tmp_path, monkeypatch):
    """A plugin-cache-root-shaped base_path (no ``/marketplace/bundles`` marker)
    resolves its own ``base_path/dist-manifest.json`` candidate.

    This is the meta-project's own preflight/executor-regen context: base_path
    is the plugin-cache root (``~/.claude/plugins/cache/plan-marshall``), which
    the sync engine populates with a top-level ``dist-manifest.json``. The
    existing ``uses_resolved_target`` / ``defaults_to_claude`` cases exercise
    only the ``/marketplace/bundles``-marker target candidate; this pins the
    ``base_path/dist-manifest.json`` candidate the fix relies on, guarding
    against its silent removal.
    """
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    # Plugin-cache-root-shaped dir: it does NOT contain '/marketplace/bundles',
    # so the target-tree candidate never fires and resolution falls to the
    # base_path/dist-manifest.json candidate.
    cache_root = tmp_path / 'cache' / 'plan-marshall'
    cache_root.mkdir(parents=True)
    assert '/marketplace/bundles' not in str(cache_root)

    manifest = cache_root / 'dist-manifest.json'
    manifest.write_text('{"version": "0.1.1068"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(cache_root)

    assert resolved == manifest, 'a plugin-cache-root base_path must resolve base_path/dist-manifest.json'


def test_find_installed_manifest_path_resolves_marketplace_clone_root(tmp_path, monkeypatch):
    """A plugin-cache-INSTALL base_path (``.../plugins/cache/<marketplace>/...``)
    resolves the manifest at the marketplace CLONE ROOT
    (``.../plugins/marketplaces/<marketplace>/dist-manifest.json``).

    On a marketplace install the sync engine does NOT copy ``dist-manifest.json``
    into the ``/plugins/cache/<marketplace>`` tree — it stays at the clone root
    under ``/plugins/marketplaces/<marketplace>``. Without the clone-root
    candidate the manifest is unresolvable there, ``read_installed_manifest``
    returns ``{}``, and the executor stamps the empty version sentinel instead
    of the real version. This pins the (4) clone-root candidate against silent
    removal.
    """
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    # Plugin-cache-install layout: base_path lives under
    # .../plugins/cache/<marketplace>/... and carries NO manifest at any
    # pre-existing candidate — no '/marketplace/bundles' marker, no
    # base_path/dist-manifest.json, and no base_path.parent/dist-manifest.json.
    cache_base = tmp_path / 'plugins' / 'cache' / 'plan-marshall' / '0.1.1200' / 'skills'
    cache_base.mkdir(parents=True)
    assert '/marketplace/bundles' not in str(cache_base)
    assert not (cache_base / 'dist-manifest.json').exists()
    assert not (cache_base.parent / 'dist-manifest.json').exists()

    # The manifest lives ONLY at the marketplace clone root.
    clone_root = tmp_path / 'plugins' / 'marketplaces' / 'plan-marshall'
    clone_root.mkdir(parents=True)
    manifest = clone_root / 'dist-manifest.json'
    manifest.write_text('{"version": "0.1.1200"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(cache_base)

    assert resolved == manifest, (
        'a plugin-cache-install base_path must resolve the marketplace clone-root dist-manifest.json'
    )

    # Companion: the value the executor stamps as MARSHALL_VERSION is
    # manifest['version'] (read via read_installed_manifest at generation time),
    # so a resolvable clone-root manifest yields the real, non-empty version —
    # never the empty sentinel a fresh install produces.
    stamped = module.read_installed_manifest(cache_base)
    assert stamped.get('version') == '0.1.1200', (
        'the executor must stamp the real manifest version on a marketplace-cache install, not the empty sentinel'
    )


def test_find_installed_manifest_path_rejects_traversal_marketplace_segment(tmp_path, monkeypatch):
    """The clone-root candidate (4) must reject a ``..``-shaped marketplace-name
    segment rather than mapping it into a path outside ``plugins/marketplaces/``.

    ``marketplace_name`` is derived from a string split of ``base_path`` — a
    defense-in-depth guard rejects ``.``/``..`` and any segment carrying a path
    separator before it is used to build a filesystem path, so a pathologically
    shaped ``base_path`` (however it arose) can never make candidate (4) climb
    outside the intended ``plugins/marketplaces/<marketplace>/`` directory.
    """
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    # 'plugins/marketplaces/' must actually exist on disk for the OS to resolve
    # a '..' segment walked from inside it — otherwise the escape path would
    # ENOENT regardless of the guard, making the test a false negative.
    (tmp_path / 'plugins' / 'marketplaces').mkdir(parents=True)

    # A file planted one level above 'plugins/marketplaces/' that a
    # '..'-shaped segment resolves to (plugins/marketplaces/../dist-manifest.json
    # == plugins/dist-manifest.json) when the guard is absent.
    escape_target = tmp_path / 'plugins' / 'dist-manifest.json'
    escape_target.write_text('{"version": "escaped"}', encoding='utf-8')

    # base_path shaped so the '/plugins/cache/' marker is followed immediately
    # by '..' as the marketplace-name segment.
    cache_base = tmp_path / 'plugins' / 'cache' / '..'

    resolved = module.find_installed_manifest_path(cache_base)

    assert resolved is None, 'a .. marketplace-name segment must never resolve to a candidate path'


def test_find_installed_manifest_path_highest_version_wins_over_stale_cache_root(tmp_path, monkeypatch):
    """Highest-version-wins: a stale cache-root manifest must NOT shadow a newer
    clone-root manifest merely because the cache-root candidate is iterated
    first. The resolver reads every existing candidate's ``version`` and returns
    the path whose ``_version_tuple(version)`` is the maximum.

    Fixture: a plugin-cache-INSTALL base_path (``.../plugins/cache/<mkt>/...``)
    where BOTH the ``base_path/dist-manifest.json`` (cache-root) candidate AND
    the ``.../plugins/marketplaces/<mkt>/dist-manifest.json`` (clone-root)
    candidate exist, at differing versions. The cache-root candidate is iterated
    first — first-hit-wins would return the stale ``0.1.1144``; highest-version
    selection returns the newer clone-root ``0.1.1152``.
    """
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    cache_base = tmp_path / 'plugins' / 'cache' / 'plan-marshall' / '0.1.1144' / 'skills'
    cache_base.mkdir(parents=True)
    stale = cache_base / 'dist-manifest.json'
    stale.write_text('{"version": "0.1.1144"}', encoding='utf-8')

    clone_root = tmp_path / 'plugins' / 'marketplaces' / 'plan-marshall'
    clone_root.mkdir(parents=True)
    newer = clone_root / 'dist-manifest.json'
    newer.write_text('{"version": "0.1.1152"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(cache_base)

    assert resolved == newer, (
        'a newer clone-root manifest must win over the earlier-iterated stale '
        f'cache-root manifest; got {resolved}'
    )


def test_find_installed_manifest_path_resolves_lone_stale_cache_root(tmp_path, monkeypatch):
    """With only a (stale) cache-root manifest present and no newer sibling, the
    resolver still resolves it — highest-version selection over a single
    candidate returns that candidate, so the single-manifest path is unchanged."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    cache_base = tmp_path / 'plugins' / 'cache' / 'plan-marshall' / '0.1.1144' / 'skills'
    cache_base.mkdir(parents=True)
    lone = cache_base / 'dist-manifest.json'
    lone.write_text('{"version": "0.1.1144"}', encoding='utf-8')

    resolved = module.find_installed_manifest_path(cache_base)

    assert resolved == lone, 'a lone stale cache-root manifest must still resolve'


def test_find_installed_manifest_path_none_when_no_candidate_resolvable(tmp_path, monkeypatch):
    """Fail-closed preserved: with no resolvable manifest at any candidate, the
    resolver returns ``None`` (→ ``unknown`` downstream), never a fabricated
    path. Highest-version selection over an empty existing-candidate set yields
    ``None``."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)

    module = load_module()

    cache_base = tmp_path / 'plugins' / 'cache' / 'plan-marshall' / '0.1.1144' / 'skills'
    cache_base.mkdir(parents=True)
    # No dist-manifest.json at any candidate site.

    resolved = module.find_installed_manifest_path(cache_base)

    assert resolved is None, 'no resolvable manifest must fail closed with None'


def test_template_declares_version_and_fingerprint_constants():
    """The template carries the MARSHALL_VERSION / MAPPINGS_FINGERPRINT
    placeholder constants beside PLAN_DIR_NAME."""
    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    assert "MARSHALL_VERSION = '{{GENERATED_VERSION}}'" in source, 'template must declare MARSHALL_VERSION placeholder'
    assert "MAPPINGS_FINGERPRINT = '{{MAPPINGS_FINGERPRINT}}'" in source, (
        'template must declare MAPPINGS_FINGERPRINT placeholder'
    )


# ============================================================================
# Deliverable 1: preflight verb
# ============================================================================
# The preflight verb compares the executor's embedded MARSHALL_VERSION and
# marshal.json's system.provisioned_version against the installed manifest's
# changed_at versions. The executor is safe derived state (regenerated in place
# when stale); marshal.json is never auto-mutated (staleness is advisory only).


_PREFLIGHT_FIELDS = frozenset(
    {
        'status',
        'executor_action',
        'marshal_status',
        'installed_version',
        'executor_version',
        'marshal_version',
        'warning',
    }
)


def _preflight_args():
    """Build a minimal argparse-style namespace for cmd_preflight."""
    import types

    return types.SimpleNamespace(marketplace=False, marketplace_root=None, target=None, dry_run=False)


def test_read_executor_version_unknown_on_undecodable_executor(tmp_path, monkeypatch):
    """A ValueError/UnicodeDecodeError decoding the executor is treated like an
    absent executor — the 'unknown' sentinel, never an unhandled exception."""
    module = load_module()

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    # Invalid UTF-8 byte sequence raises UnicodeDecodeError (a ValueError subclass).
    (plan_dir / 'execute-script.py').write_bytes(b'\xff\xfe not valid utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    assert module.read_executor_version() == 'unknown'


def test_preflight_fails_closed_on_unresolvable_manifest(outside_repo_dir, monkeypatch, capsys):
    """With no resolvable manifest, preflight fails CLOSED: it reports the full
    seven-field TOON with marshal_status 'unknown' (never a vacuous 'fresh'),
    populates the warning field, and emits a legible warning to stderr — so a
    caller can never mistake "could not determine" for "confirmed fresh"."""
    module = load_module()

    # cwd/base must be OUTSIDE the repo: pytest's tmp_path now roots under the
    # repo-local --basetemp, whose ancestry carries a resolvable dist-manifest /
    # marketplace version, so the manifest would resolve to a real version
    # instead of the 'unknown' this fail-closed test requires.
    monkeypatch.setenv('PM_DIST_MANIFEST', str(outside_repo_dir / 'absent.json'))
    monkeypatch.setenv('PLAN_BASE_DIR', str(outside_repo_dir / '.plan'))
    (outside_repo_dir / '.plan').mkdir()
    monkeypatch.chdir(outside_repo_dir)
    # Isolate the orthogonal multi-version-pollution scan (which reads the real
    # plugin-cache tree) so this fail-closed case stays hermetic.
    monkeypatch.setattr(module, '_detect_multi_version_pollution', lambda *a, **k: [])

    result = module.cmd_preflight(_preflight_args())

    assert set(result.keys()) == _PREFLIGHT_FIELDS, f'preflight must return exactly the seven fields, got {set(result)}'
    assert result['status'] == 'success'
    assert result['executor_action'] == 'fresh'
    assert result['installed_version'] == 'unknown'
    assert result['executor_version'] == 'unknown'
    assert result['marshal_version'] == 'unknown'
    # Fail CLOSED: an unresolvable manifest reports 'unknown', never a vacuous 'fresh'.
    assert result['marshal_status'] == 'unknown', 'unresolvable manifest must not report a vacuous fresh'
    assert result['warning'], 'the fail-closed warning field must be populated when marshal_status is unknown'

    # The legible warning is also emitted to stderr.
    captured = capsys.readouterr()
    assert 'could not be resolved' in captured.err, (
        f'preflight must emit a legible fail-closed warning to stderr; got: {captured.err!r}'
    )


def test_preflight_reports_executor_fresh_when_embedded_not_older(tmp_path, monkeypatch):
    """When the embedded MARSHALL_VERSION is not older than the manifest's
    executor_changed_at_version, the executor is fresh (no regeneration)."""
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps({'version': '0.1.99', 'executor_changed_at_version': '0.1.5'}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    # Seed an executor stamped at a newer version than the changed_at gate.
    (plan_dir / 'execute-script.py').write_text("MARSHALL_VERSION = '0.1.99'\n", encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)
    # Isolate the orthogonal multi-version-pollution scan (which reads the real
    # plugin-cache tree) so this version-staleness case stays hermetic.
    monkeypatch.setattr(module, '_detect_multi_version_pollution', lambda *a, **k: [])

    result = module.cmd_preflight(_preflight_args())

    assert result['status'] == 'success'
    assert result['executor_action'] == 'fresh', 'embedded 0.1.99 >= changed_at 0.1.5 must be fresh (no regen)'
    assert result['executor_version'] == '0.1.99'
    assert result['installed_version'] == '0.1.99'


def test_preflight_reports_marshal_stale_advisory_without_mutation(tmp_path, monkeypatch):
    """A provisioned_version older than config_changed_at_version reports
    marshal_status=stale (advisory) and never mutates marshal.json."""
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps({'version': '0.1.20', 'config_changed_at_version': '0.1.15'}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    # Seed a stamped, older provisioned_version — must be reported stale, untouched.
    marshal = plan_dir / 'marshal.json'
    marshal_body = {'system': {'provisioned_version': '0.1.3'}}
    marshal.write_text(json.dumps(marshal_body), encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)
    # Isolate the orthogonal multi-version-pollution scan (which reads the real
    # plugin-cache tree) so this config-staleness case stays hermetic.
    monkeypatch.setattr(module, '_detect_multi_version_pollution', lambda *a, **k: [])

    result = module.cmd_preflight(_preflight_args())

    assert result['status'] == 'success'
    assert result['marshal_status'] == 'stale', 'provisioned 0.1.3 < config_changed_at 0.1.15 must be stale'
    assert result['marshal_version'] == '0.1.3'
    # marshal.json must be byte-identical — advisory only, never auto-mutated.
    assert json.loads(marshal.read_text(encoding='utf-8')) == marshal_body, 'preflight must NOT mutate marshal.json'


def test_preflight_int_tuple_version_compare_avoids_lexical_bug(tmp_path, monkeypatch):
    """Version comparison is int-tuple, not lexical: 0.1.9 < 0.1.10 (a lexical
    compare would wrongly rank '0.1.9' above '0.1.10')."""
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps({'version': '0.1.10', 'config_changed_at_version': '0.1.10'}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = plan_dir / 'marshal.json'
    marshal.write_text(json.dumps({'system': {'provisioned_version': '0.1.9'}}), encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)
    # Isolate the orthogonal multi-version-pollution scan (which reads the real
    # plugin-cache tree) so this int-tuple compare case stays hermetic.
    monkeypatch.setattr(module, '_detect_multi_version_pollution', lambda *a, **k: [])

    result = module.cmd_preflight(_preflight_args())

    assert result['marshal_status'] == 'stale', '0.1.9 < 0.1.10 under int-tuple compare must be stale'


def test_preflight_regenerates_stale_executor_in_place(tmp_path, monkeypatch):
    """When the embedded MARSHALL_VERSION is older than executor_changed_at_version,
    preflight regenerates the executor in place and reports the new version.

    ``cmd_generate`` itself is stubbed (its full discovery pipeline is exercised
    by the dedicated generate-command tests elsewhere in this file); this test
    isolates the ``cmd_preflight`` regeneration branch: it must invoke the
    regeneration, treat a ``status: success`` result as ``executor_action:
    regenerated``, and re-read the freshly stamped version afterward.
    """
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps({'version': '0.1.42', 'executor_changed_at_version': '0.1.40'}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    executor = plan_dir / 'execute-script.py'
    executor.write_text("MARSHALL_VERSION = '0.1.10'\n", encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)

    def _fake_cmd_generate(args):
        # Simulate a successful in-place regeneration stamping the published version.
        executor.write_text("MARSHALL_VERSION = '0.1.42'\n", encoding='utf-8')
        return {'status': 'success'}

    monkeypatch.setattr(module, 'cmd_generate', _fake_cmd_generate)

    result = module.cmd_preflight(_preflight_args())

    assert result['status'] == 'success'
    assert result['executor_action'] == 'regenerated'
    assert result['executor_version'] == '0.1.42'


def test_preflight_surfaces_error_when_regeneration_fails(tmp_path, monkeypatch):
    """A failed in-place regeneration surfaces a structured error instead of
    silently reporting a stale executor as fresh."""
    import json

    module = load_module()

    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text(
        json.dumps({'version': '0.1.42', 'executor_changed_at_version': '0.1.40'}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'execute-script.py').write_text("MARSHALL_VERSION = '0.1.10'\n", encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(module, 'cmd_generate', lambda args: {'status': 'error', 'error': 'discovery failed'})

    result = module.cmd_preflight(_preflight_args())

    assert result['status'] == 'error'
    assert 'discovery failed' in result['error']


def test_preflight_marks_superseded_version_dirs_and_clears_pollution(tmp_path, monkeypatch):
    """Deferred-prune: a pollution-triggered regen marks every superseded
    (non-newest) version dir with the orphan-GC ``.orphaned_at`` deferral marker
    (never an immediate ``rmtree``), so a SECOND consecutive preflight sees one
    live version dir per bundle and reports ``executor_action: fresh`` — closing
    the regenerated-every-run loop where the pollution survived its own remedy.
    """
    module = load_module()

    # Seed a plugin-cache-shaped bundles root: one bundle with TWO version dirs
    # (each carrying a skills/ tree) → multi-version PYTHONPATH pollution.
    bundles_root = tmp_path / 'cache'
    for version in ('0.1.100', '0.1.200'):
        skills = bundles_root / 'plan-marshall' / version / 'skills' / 'some-skill' / 'scripts'
        skills.mkdir(parents=True)
        (skills / 'foo.py').write_text('# foo\n')

    # Manifest carries NO executor_changed_at, so the executor stays fresh and the
    # ONLY regen driver is the pollution path (isolating the behavior under test).
    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text('{"version": "0.1.200"}', encoding='utf-8')
    monkeypatch.setenv('PM_DIST_MANIFEST', str(manifest))

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'execute-script.py').write_text("MARSHALL_VERSION = '0.1.200'\n", encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    monkeypatch.chdir(tmp_path)

    # base_path resolves to the seeded cache tree; cmd_generate is stubbed (its
    # full discovery pipeline is covered elsewhere) so the pollution regen branch
    # is isolated to the marking behavior under test.
    monkeypatch.setattr(module, 'get_base_path', lambda *a, **k: bundles_root)
    monkeypatch.setattr(module, 'cmd_generate', lambda args: {'status': 'success'})

    superseded = bundles_root / 'plan-marshall' / '0.1.100'
    newest = bundles_root / 'plan-marshall' / '0.1.200'

    # First preflight: pollution detected → regenerated, and the superseded
    # (older) version dir now carries the .orphaned_at deferral marker while the
    # newest stays live (unmarked).
    first = module.cmd_preflight(_preflight_args())
    assert first['status'] == 'success'
    assert first['executor_action'] == 'regenerated', 'multi-version pollution must trigger a regen'
    assert (superseded / '.orphaned_at').is_file(), 'the superseded version dir must be marked orphaned'
    assert not (newest / '.orphaned_at').exists(), 'the newest version dir must stay live (unmarked)'

    # Both version dirs still exist on disk — marking defers removal to the
    # orphan GC, it never rmtree's the superseded dir out from under a live
    # process's PYTHONPATH.
    assert superseded.is_dir() and newest.is_dir(), 'deferred prune must NOT delete the superseded dir'

    # Second consecutive preflight, nothing else changed: the marked dir is
    # excluded from the pollution count, so exactly one live version dir remains
    # → no repeat regen.
    second = module.cmd_preflight(_preflight_args())
    assert second['status'] == 'success'
    assert second['executor_action'] == 'fresh', (
        'the pollution signal must clear on the second run — no regenerated-every-run loop'
    )


def test_detect_multi_version_pollution_excludes_marked_dirs(tmp_path):
    """_detect_multi_version_pollution excludes ``.orphaned_at``-marked version
    dirs: a bundle with one live dir and one marked-superseded dir is NOT
    reported as polluted (the marked dir is deferred-GC state, not live
    pollution)."""
    module = load_module()

    bundles_root = tmp_path / 'cache'
    live = bundles_root / 'plan-marshall' / '0.1.200' / 'skills' / 's' / 'scripts'
    live.mkdir(parents=True)
    marked = bundles_root / 'plan-marshall' / '0.1.100' / 'skills' / 's' / 'scripts'
    marked.mkdir(parents=True)
    (bundles_root / 'plan-marshall' / '0.1.100' / '.orphaned_at').write_text('2026-01-01T00:00:00Z')

    assert module._detect_multi_version_pollution(bundles_root) == [], (
        'a bundle with one live dir and one marked-superseded dir must not be reported polluted'
    )

    # Sanity: two LIVE (unmarked) dirs ARE reported polluted.
    (bundles_root / 'plan-marshall' / '0.1.100' / '.orphaned_at').unlink()
    assert module._detect_multi_version_pollution(bundles_root) == ['plan-marshall']


def test_cmd_generate_returns_error_when_base_path_unresolvable(tmp_path):
    """cmd_generate returns a structured error (not an unhandled exception)
    when the marketplace base path cannot be resolved."""
    import types

    module = load_module()
    args = types.SimpleNamespace(
        marketplace=True,
        marketplace_root=tmp_path / 'does-not-exist',
        dry_run=False,
        target=None,
    )

    result = module.cmd_generate(args)

    assert result['status'] == 'error'
    assert 'error' in result


def test_preflight_subcommand_registered_and_emits_toon(tmp_path):
    """The preflight subparser is registered and the verb emits a TOON carrying
    the seven documented fields end-to-end."""
    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text('{"version": "0.1.7"}', encoding='utf-8')

    env = _subprocess_env()
    env['PM_DIST_MANIFEST'] = str(manifest)
    env['PLAN_BASE_DIR'] = str(tmp_path / '.plan')
    # Isolate HOME so the orthogonal multi-version-pollution scan cannot read a
    # real (possibly stale/polluted) plugin-cache tree — cache-first resolution
    # then falls back to the marketplace source, keeping this end-to-end case
    # hermetic. Mirrors the _detect_multi_version_pollution stub the in-process
    # preflight tests use (which a subprocess cannot monkeypatch).
    env['HOME'] = str(tmp_path)
    (tmp_path / '.plan').mkdir()

    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'preflight'],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=60,
    )

    assert result.returncode == 0, f'preflight failed: {result.stderr}'
    for field in _PREFLIGHT_FIELDS:
        assert field in result.stdout, f'preflight TOON must carry {field!r}; got:\n{result.stdout}'
    assert 'installed_version: 0.1.7' in result.stdout, 'installed_version must reflect the fixture manifest'


def test_preflight_help_listed_in_top_level_help():
    """The preflight verb appears in the top-level --help output."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), '--help'], capture_output=True, text=True, env=_subprocess_env()
    )
    assert result.returncode == 0, f'Script failed: {result.stderr}'
    assert 'preflight' in result.stdout, "Missing 'preflight' in help"


# ============================================================================
# Orphaned plugin-cache version-dir drift false-positive (consumer-chain angle)
# ============================================================================
# Reproduces the reported `generate_executor drift` false-positive from the
# discovery consumer angle: a plugin-cache-shaped bundle with a current version
# dir PLUS a stale/orphaned duplicate whose name sorts AFTER the current one
# would, before the fix, be returned by find_bundles and overwrite the current
# notation->path mappings in the last-write-wins merge. The unit-level
# complement — direct find_bundles assertions — lives in
# test/plan-marshall/script-shared/test_marketplace_bundles.py TestFindBundles
# (test_multi_version_selects_newest / test_orphaned_version_skipped /
# test_all_orphaned_contributes_nothing).


def _add_versioned_cache_bundle(
    bundles_root: Path, bundle_name: str, current_version: str, stale_version: str
) -> None:
    """Add a plugin-cache-shaped bundle with a current and an orphaned stale version dir.

    Both version dirs carry the same skill/script (``foo.py``) plus their own
    ``.claude-plugin/plugin.json`` (plugin-cache layout, where each version dir is
    a self-contained bundle). The stale dir sorts AFTER the current one and is
    marked with a ``.orphaned_at`` file, so it would shadow the current dir in the
    last-write-wins discovery merge unless find_bundles skips orphaned dirs.
    """
    for version, orphaned in ((current_version, False), (stale_version, True)):
        version_dir = bundles_root / bundle_name / version
        plugin_dir = version_dir / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'plugin.json').write_text(
            f'{{"name": "{bundle_name}", "version": "{version}", "description": "fixture"}}\n'
        )
        scripts = version_dir / 'skills' / 'stale-skill' / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'foo.py').write_text('"""Sentinel script for orphaned-cache drift regression."""\n')
        if orphaned:
            (version_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z')


def test_orphaned_non_pinned_cache_version_dir_never_overwrites_current_mappings(tmp_path, monkeypatch):
    """A stale/orphaned NON-PINNED cache version dir must not shadow the mappings.

    Integration regression for the drift false-positive: an orphaned version dir
    that sorts after the current one ('1.0.10' > '1.0.0') must be skipped by
    find_bundles, so every discovered notation->path mapping resolves under the
    current (non-orphaned) version dir only and drift reports no stale overwrite.

    The fixture adds a bare '1.0.20' dir carrying no plugin.json so the newest dir
    ON DISK is ineligible: ``select_live_version_dir`` ignores a mark only on the
    retention-pinned newest-on-disk dir, and honouring the mark on 1.0.10 is the
    behaviour under test here. Without that third dir the marked 1.0.10 IS the pin
    and legitimately wins — a different case, covered in test_marketplace_bundles.

    The anchor is supplied via ``PM_MARKETPLACE_ROOT`` (``use_flag=False``), NOT
    the ``--marketplace-root`` flag. This is load-bearing for the consumer angle:
    ``generate_executor.discover_scripts`` spawns ``scan-marketplace-inventory``
    as a subprocess (which has no ``--marketplace-root`` flag). Only the env-var
    anchor is inherited by that subprocess, so it discovers the versioned fixture
    through the real ``find_bundles`` chain. Under the ``--marketplace-root``
    flag the env var is popped, the inventory subprocess loses the anchor,
    cwd-walk-up cannot reach the ``tmp_path``-nested fake tree, and discovery
    silently degrades to the version-unaware glob fallback — which never sees the
    ``bundle/<version>/skills`` layout at all, so the orphaned-overwrite defect
    this test guards would never be exercised.
    """
    fake_ws = _build_fake_marketplace(tmp_path)
    bundles_root = fake_ws / 'marketplace' / 'bundles'
    _add_versioned_cache_bundle(bundles_root, 'stale-cache-bundle', '1.0.0', '1.0.10')
    # Newest ON DISK, but eligible for no leg (no plugin.json, no skills/): this
    # makes 1.0.10 non-pinned, so its .orphaned_at mark is honoured.
    (bundles_root / 'stale-cache-bundle' / '1.0.20').mkdir(parents=True)

    mappings = _generate_with_anchor(tmp_path, fake_ws, use_flag=False, monkeypatch=monkeypatch)

    notation = 'stale-cache-bundle:stale-skill:foo'
    assert notation in mappings, f'Expected {notation!r} discovered; got {sorted(mappings)[:10]}...'

    resolved = mappings[notation]
    current_prefix = str(bundles_root / 'stale-cache-bundle' / '1.0.0') + os.sep
    stale_prefix = str(bundles_root / 'stale-cache-bundle' / '1.0.10') + os.sep
    assert resolved.startswith(current_prefix), (
        f'{notation} must resolve under the current version dir {current_prefix}, got {resolved}'
    )
    assert not resolved.startswith(stale_prefix), (
        f'{notation} leaked to the orphaned stale version dir {stale_prefix}: {resolved}'
    )


# ============================================================================
# FIX C: Claude resolver-template newest-version selection
# ============================================================================
# The generated Claude resolver (_resolve_notation_by_target, injected via the
# {{TARGET_AWARE_RESOLVER}} token) collects EVERY plugin-cache version dir that
# carries the candidate script and returns the NEWEST by numeric version-tuple —
# never the first-iterated. These tests render the REAL resolver template source
# (via generate_target_aware_resolver_code, not the inert _load_template_module
# stub) and exercise it against a fake plugin cache under a monkeypatched
# Path.home, so the production resolver body is what is under test.


def _load_claude_resolver():
    """Render and load the real Claude target-aware resolver function.

    Pulls the actual ``_CLAUDE_RESOLVER_TEMPLATE`` body via
    ``generate_target_aware_resolver_code('claude')`` and execs it into a fresh
    namespace with ``Path`` available, returning the ``_resolve_notation_by_target``
    callable. Unlike ``_load_template_module`` (which substitutes the resolver
    token with a no-op stub), this exercises the production resolver source.
    """
    module = load_module()
    src = module.generate_target_aware_resolver_code('claude')
    namespace: dict = {'Path': Path}
    exec(src, namespace)  # noqa: S102 — controlled, generator-owned template source
    return namespace['_resolve_notation_by_target']


def _make_cache_script(home: Path, version: str, skill: str, script: str) -> Path:
    """Create a plugin-cache script under a fake home and return its path.

    Layout: ``{home}/.claude/plugins/cache/plan-marshall/{version}/skills/{skill}/scripts/{script}.py``.
    """
    scripts_dir = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / version / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / f'{script}.py'
    script_file.write_text(f'# {version} {skill} {script}\n')
    return script_file


def test_claude_resolver_multi_version_pollution_returns_newest(tmp_path, monkeypatch):
    """multi-version-pollution-notation-resolver: with several version dirs each
    carrying the script, the resolver returns the NEWEST version's path, not the
    first-iterated. Guards the multi-version-pollution shadowing class.

    Numeric ordering is load-bearing: '0.1.200' -> (0, 1, 200) must win over the
    lexically-earlier '0.1.100' -> (0, 1, 100) and '0.1.9' -> (0, 1, 9). A
    first-match (pre-fix) resolver would return whichever version dir ``iterdir``
    yields first, so pinning the result to the newest is what catches the
    regression.
    """
    home = tmp_path / 'home'
    _make_cache_script(home, '0.1.9', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files')
    newest = _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files')

    monkeypatch.setattr(Path, 'home', lambda: home)

    resolve = _load_claude_resolver()
    result = resolve('plan-marshall:manage-files:manage-files')

    assert result == str(newest.resolve()), (
        f'resolver must return the newest version dir path {newest.resolve()!r}, got {result!r}'
    )


def test_claude_resolver_reresolves_after_pinned_version_pruned(tmp_path, monkeypatch):
    """pinned-version-pruned-runtime-reresolve: after the currently-resolved
    (newest) version dir is pruned from disk, a later resolve re-resolves at
    runtime to the newest surviving version dir.

    This is the GC-sweep scenario: the newest cache version dir the resolver was
    returning gets pruned, and the resolver must fall through to the next-newest
    surviving version dir rather than returning a stale pinned path or ``None``.
    """
    home = tmp_path / 'home'
    older = _make_cache_script(home, '0.1.5', 'manage-status', 'manage-status')
    newest = _make_cache_script(home, '0.1.10', 'manage-status', 'manage-status')

    monkeypatch.setattr(Path, 'home', lambda: home)

    resolve = _load_claude_resolver()

    # First resolution returns the newest version dir on disk.
    first = resolve('plan-marshall:manage-status:manage-status')
    assert first == str(newest.resolve()), f'expected newest {newest.resolve()!r}, got {first!r}'

    # Prune the pinned newest version dir wholesale (the '0.1.10' dir).
    shutil.rmtree(newest.parents[3])

    # A later resolve re-resolves to the newest surviving version dir.
    second = resolve('plan-marshall:manage-status:manage-status')
    assert second == str(older.resolve()), (
        f'after pruning the pinned version, resolver must re-resolve to the newest '
        f'surviving dir {older.resolve()!r}, got {second!r}'
    )


# ============================================================================
# Deliverable 1: regeneration safety — format handshake, residue guard,
# py_compile self-check, atomic write
# ============================================================================
# generate_executor() runs four deterministic guards on the substituted content
# BEFORE any write and commits atomically (write-temp + os.replace), so a
# malformed generation can never overwrite a working executor. Guard 4
# (emitted-path provenance) has its own section further down. These tests pin:
# (a) a well-formed generation still writes a compilable executor and reports
#     status: success;
# (b) a template TEMPLATE_FORMAT_VERSION skew is refused with no write and a
#     byte-identical pre-existing executor;
# (c) an unsubstituted {{...}} placeholder residue fails loudly with no write;
# (d) a py_compile-failing substitution is refused and the pre-existing working
#     executor is preserved (the direct Leg B acceptance assertion).
# They reuse the _build_fake_marketplace scaffolding so generate_executor runs
# end-to-end against a controllable template, and PLAN_BASE_DIR isolation so the
# executor write target lands under tmp_path, never the real project tree.


def _fake_bundles_root(tmp_path: Path) -> Path:
    """Return the bundles dir of a fake marketplace copied under tmp_path."""
    fake_ws = _build_fake_marketplace(tmp_path)
    return fake_ws / 'marketplace' / 'bundles'


def _fake_template_path(bundles_root: Path) -> Path:
    """Return the copied executor template inside a fake bundles tree."""
    return bundles_root / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates' / 'execute-script.py.template'


def _seed_pre_existing_executor(tmp_path: Path) -> tuple[Path, str]:
    """Create a sentinel pre-existing executor under tmp_path/.plan and return it.

    Returns the executor path and its exact byte content so a caller can assert
    a refused regeneration left it untouched.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    sentinel = "# SENTINEL pre-existing executor — must survive a refused regen\nSCRIPTS = {}\n"
    executor.write_text(sentinel, encoding='utf-8')
    return executor, sentinel


def test_generate_executor_wellformed_writes_compilable_and_reports_success(tmp_path, monkeypatch):
    """(a) A well-formed generation writes a compilable executor and reports
    status: success — the happy path through all three guards + atomic write."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = module.generate_executor({'a:b:c': '/x/y/z.py'}, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'success', f'well-formed generation must succeed, got {result}'
    generated = plan_dir / 'execute-script.py'
    assert generated.is_file(), 'a successful generation must write the executor'
    # The written executor itself compiles — the self-check gate's positive case.
    compile(generated.read_text(encoding='utf-8'), str(generated), 'exec')


def test_generate_executor_format_skew_refuses_write_and_preserves_existing(tmp_path, monkeypatch):
    """(b) A template whose TEMPLATE_FORMAT_VERSION marker mismatches the
    generator's supported version returns status: error, writes no executor, and
    leaves any pre-existing executor byte-identical."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    template = _fake_template_path(bundles_root)
    body = template.read_text(encoding='utf-8')
    # Rewrite whatever version the fixture declares, rather than pinning the
    # literal current one: hard-coding ``: 1`` here made the fixture a silent
    # no-op the moment the real format version was bumped, and a skew test that
    # writes an UNSKEWED template passes for the wrong reason.
    skewed = re.sub(
        r'#\s*TEMPLATE_FORMAT_VERSION:\s*\d+', '# TEMPLATE_FORMAT_VERSION: 999', body
    )
    assert skewed != body, 'fixture must actually alter the format marker'
    template.write_text(skewed, encoding='utf-8')

    # Post-Q-Gate-6dcc8f, get_templates_dir() resolves the template script-relative
    # to the executing generator and IGNORES base_path, so writing the fixture into
    # the fake bundles tree no longer redirects generate_executor's template read.
    # Point get_templates_dir at the fixture's own dir so the skewed template is the
    # one under test (test-only injection; production resolution is unchanged).
    monkeypatch.setattr(module, 'get_templates_dir', lambda base_path: template.parent)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    result = module.generate_executor({'a:b:c': '/x/y/z.py'}, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', f'a format skew must be refused, got {result}'
    assert 'format' in result['error'].lower() or 'version' in result['error'].lower()
    assert executor.read_text(encoding='utf-8') == sentinel, 'pre-existing executor must be byte-identical after refusal'


def test_generate_executor_placeholder_residue_refuses_write_and_preserves_existing(tmp_path, monkeypatch):
    """(c) A substituted content carrying a residual {{...}} placeholder token
    (a placeholder the generator never fills) is refused with no write and the
    pre-existing executor preserved."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    template = _fake_template_path(bundles_root)
    body = template.read_text(encoding='utf-8')
    # Inject an unfillable placeholder inside a comment: it survives substitution
    # (the generator fills no {{NEVER_FILLED}}) yet keeps the format marker intact.
    injected = body.replace('VALIDATE_TOON = False', 'VALIDATE_TOON = False  # residue {{NEVER_FILLED}}')
    assert injected != body, 'fixture must actually inject the residue token'
    template.write_text(injected, encoding='utf-8')

    # Post-Q-Gate-6dcc8f, get_templates_dir() resolves the template script-relative
    # to the executing generator and IGNORES base_path, so writing the fixture into
    # the fake bundles tree no longer redirects generate_executor's template read.
    # Point get_templates_dir at the fixture's own dir so the residue-injected
    # template is the one under test (test-only injection; production unchanged).
    monkeypatch.setattr(module, 'get_templates_dir', lambda base_path: template.parent)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    result = module.generate_executor({'a:b:c': '/x/y/z.py'}, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', f'placeholder residue must be refused, got {result}'
    assert 'residue' in result['error'].lower() or 'placeholder' in result['error'].lower()
    assert executor.read_text(encoding='utf-8') == sentinel, 'pre-existing executor must be byte-identical after refusal'


def test_generate_executor_py_compile_failure_refuses_write_and_preserves_existing(tmp_path, monkeypatch):
    """(d) A substitution that produces non-compiling Python returns status: error
    and preserves the pre-existing working executor untouched — the direct Leg B
    acceptance assertion (a broken executor can never be emitted)."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    template = _fake_template_path(bundles_root)
    body = template.read_text(encoding='utf-8')
    # Inject a module-level syntax error that carries no {{...}} residue and
    # keeps the format marker intact, so guards 1 and 2 pass and guard 3 (the
    # py_compile self-check) is the one that trips.
    broken = body.replace('VALIDATE_TOON = False', 'VALIDATE_TOON = False\ndef __broken_syntax(:\n    pass')
    assert broken != body, 'fixture must actually inject the syntax error'
    template.write_text(broken, encoding='utf-8')

    # Post-Q-Gate-6dcc8f, get_templates_dir() resolves the template script-relative
    # to the executing generator and IGNORES base_path, so writing the fixture into
    # the fake bundles tree no longer redirects generate_executor's template read.
    # Point get_templates_dir at the fixture's own dir so the syntax-broken template
    # is the one under test (test-only injection; production resolution unchanged).
    monkeypatch.setattr(module, 'get_templates_dir', lambda base_path: template.parent)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    result = module.generate_executor({'a:b:c': '/x/y/z.py'}, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', f'a non-compiling substitution must be refused, got {result}'
    assert 'compile' in result['error'].lower() or 'syntax' in result['error'].lower()
    assert executor.read_text(encoding='utf-8') == sentinel, 'pre-existing working executor must be preserved on a failed self-check'


# ============================================================================
# Guard 4: emitted-path provenance (never write a version-split executor)
# ============================================================================
# Guards 1-3 are SHAPE checks — they cannot see an executor whose script
# mappings and import paths come from different version dirs of the same bundle,
# because such a file is perfectly well-formed. Guard 4 is the only one that
# compares the emitted path families against each other, and it fails closed:
# status: error, nothing written, any pre-existing executor byte-identical.


def _cache_script_path(cache_root: Path, bundle: str, version: str, script: str) -> str:
    """Return a plugin-cache-shaped emitted path for ``bundle`` at ``version``.

    The path is rooted at ``cache_root`` because the provenance split is anchored
    on the known cache root — a path outside it carries no comparable provenance
    and is skipped by the guard.
    """
    return str(cache_root / bundle / version / 'skills' / 'skill-x' / 'scripts' / f'{script}.py')


def test_guard4_two_version_dirs_for_one_bundle_refuses_write_and_preserves_existing(tmp_path, monkeypatch):
    """A mapping set spanning two version dirs of ONE bundle is refused, and the
    pre-existing executor is left byte-identical."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    mappings = {
        'split-bundle:skill-x:one': _cache_script_path(bundles_root, 'split-bundle', '1.0.0', 'one'),
        'split-bundle:skill-x:two': _cache_script_path(bundles_root, 'split-bundle', '1.0.10', 'two'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', f'a version-split path set must be refused, got {result}'
    assert 'split-bundle' in result['error'], 'the error must name the offending bundle'
    assert '1.0.0' in result['error'] and '1.0.10' in result['error'], (
        'the error must name the conflicting version dirs'
    )
    assert executor.read_text(encoding='utf-8') == sentinel, (
        'pre-existing executor must be byte-identical after a provenance refusal'
    )


def test_guard4_single_version_mapping_set_still_writes(tmp_path, monkeypatch):
    """Two paths under the SAME version dir are consistent — generation proceeds."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    mappings = {
        'one-bundle:skill-x:one': _cache_script_path(bundles_root, 'one-bundle', '1.0.10', 'one'),
        'one-bundle:skill-x:two': _cache_script_path(bundles_root, 'one-bundle', '1.0.10', 'two'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'success', f'a single-version path set must still write, got {result}'
    assert (plan_dir / 'execute-script.py').is_file()


def test_guard4_no_ops_in_marketplace_mode(tmp_path, monkeypatch):
    """Marketplace-layout paths carry no version-dir segment, so the guard has
    nothing to compare and must not fail — different bundles are also fine."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    mappings = {
        'bundle-a:skill-x:one': '/repo/marketplace/bundles/bundle-a/skills/skill-x/scripts/one.py',
        'bundle-b:skill-x:two': '/repo/marketplace/bundles/bundle-b/skills/skill-x/scripts/two.py',
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'success', f'marketplace mode must be unaffected by guard 4, got {result}'
    assert (plan_dir / 'execute-script.py').is_file()


def test_guard4_allows_different_version_dirs_across_different_bundles(tmp_path, monkeypatch):
    """The invariant is PER BUNDLE: the cache legitimately holds one version dir
    per bundle, so two bundles at different versions are not a split."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    mappings = {
        'bundle-a:skill-x:one': _cache_script_path(bundles_root, 'bundle-a', '1.0.0', 'one'),
        'bundle-b:skill-x:two': _cache_script_path(bundles_root, 'bundle-b', '2.5.3', 'two'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'success', f'per-bundle single-version must permit this, got {result}'


# ============================================================================
# Guard 4 anchoring: the split is taken against the KNOWN cache root
# ============================================================================
# PR #1013 review findings. Selecting the FIRST version-shaped path segment
# anywhere in the path (instead of relativizing against base_path) mis-splits on
# two real inputs: (a) a version-shaped ANCESTOR directory above the cache root,
# and (b) a bundle whose own name starts with ``N.N`` — the supported naming
# convention pinned by
# test_marketplace_bundles.py::test_non_versioned_bundle_starting_with_digits and
# gated in find_bundles by ``bundle_dir.parent != base_path``. Either trigger
# returns the wrong (bundle, version) key, so Guard 4 compares the wrong thing
# and silently misses a genuine version split — a vacuous guard inside the guard.


def test_split_bundle_version_anchors_on_base_path_for_digit_prefixed_bundle():
    """(b) A bundle whose NAME is version-shaped still splits into
    (bundle, version dir) — never (cache root, bundle name)."""
    module = load_module()

    split = module._split_bundle_version(
        '/cache/1.0-my-bundle/0.1.1194/skills/skill-x/scripts/x.py', Path('/cache')
    )

    assert split == ('1.0-my-bundle', '0.1.1194'), (
        f'the version dir is the segment AFTER the bundle segment, got {split}'
    )


def test_split_bundle_version_ignores_version_shaped_ancestor_directory():
    """(a) A version-shaped ANCESTOR above the cache root is not the version dir."""
    module = load_module()

    split = module._split_bundle_version(
        '/srv/1.0-workspace/cache/my-bundle/0.1.1194/skills/skill-x/scripts/x.py',
        Path('/srv/1.0-workspace/cache'),
    )

    assert split == ('my-bundle', '0.1.1194'), (
        f'the ancestor segment must not be mistaken for the cache version dir, got {split}'
    )


def test_split_bundle_version_returns_none_outside_base_path():
    """A path that is not under the cache root carries no comparable provenance
    (e.g. a project-local .claude/skills script)."""
    module = load_module()

    assert module._split_bundle_version('/repo/.claude/skills/s/scripts/x.py', Path('/cache')) is None


def test_split_bundle_version_returns_none_for_marketplace_layout():
    """The version-less marketplace layout has nothing for the guard to compare."""
    module = load_module()

    split = module._split_bundle_version(
        '/repo/marketplace/bundles/my-bundle/skills/skill-x/scripts/x.py',
        Path('/repo/marketplace/bundles'),
    )

    assert split is None, f'marketplace-layout paths carry no version dir, got {split}'


def test_guard4_detects_split_for_digit_prefixed_bundle_name(tmp_path, monkeypatch):
    """(b) end-to-end: a genuine version split of a digit-prefixed bundle is
    still refused — the bundle-name segment never masquerades as the version."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    mappings = {
        '1.0-my-bundle:skill-x:one': _cache_script_path(bundles_root, '1.0-my-bundle', '0.1.100', 'one'),
        '1.0-my-bundle:skill-x:two': _cache_script_path(bundles_root, '1.0-my-bundle', '0.1.200', 'two'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', f'a version-split digit-prefixed bundle must be refused, got {result}'
    assert '1.0-my-bundle' in result['error'], 'the error must name the digit-prefixed bundle'
    assert '0.1.100' in result['error'] and '0.1.200' in result['error'], (
        'the error must name the conflicting version dirs, not the bundle-name segment'
    )
    assert executor.read_text(encoding='utf-8') == sentinel, 'pre-existing executor must survive the refusal'


def test_guard4_digit_prefixed_bundles_in_marketplace_layout_are_not_a_split(tmp_path, monkeypatch):
    """(b) false-positive direction: two sibling digit-prefixed bundles in the
    version-less marketplace layout are distinct bundles, not one bundle at two
    versions — generation must proceed."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    bundles_root = _fake_bundles_root(tmp_path)

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    mappings = {
        '1.0-bundle-a:skill-x:one': str(bundles_root / '1.0-bundle-a' / 'skills' / 'skill-x' / 'scripts' / 'one.py'),
        '1.0-bundle-b:skill-x:two': str(bundles_root / '1.0-bundle-b' / 'skills' / 'skill-x' / 'scripts' / 'two.py'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'success', (
        f'digit-prefixed marketplace bundles are not a version split, got {result}'
    )
    assert (plan_dir / 'execute-script.py').is_file()


def test_guard4_detects_split_under_version_shaped_ancestor_directory(tmp_path, monkeypatch):
    """(a) end-to-end: with a version-shaped ancestor ABOVE the cache root, a
    genuine per-bundle version split is still detected — the ancestor segment is
    relativized away instead of being read as the version dir for every path."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    module = load_module()
    ancestor = tmp_path / '1.0-workspace'
    ancestor.mkdir()
    bundles_root = _fake_bundles_root(ancestor)

    executor, sentinel = _seed_pre_existing_executor(tmp_path)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))

    mappings = {
        'split-bundle:skill-x:one': _cache_script_path(bundles_root, 'split-bundle', '0.1.100', 'one'),
        'split-bundle:skill-x:two': _cache_script_path(bundles_root, 'split-bundle', '0.1.200', 'two'),
    }
    result = module.generate_executor(mappings, bundles_root, dry_run=False, target='claude')

    assert result['status'] == 'error', (
        f'a version-shaped ancestor must not mask a genuine split, got {result}'
    )
    assert 'split-bundle' in result['error'], 'the error must name the offending bundle'
    assert '1.0-workspace' not in result['error'], (
        'the ancestor directory must never be reported as a version dir'
    )
    assert executor.read_text(encoding='utf-8') == sentinel, 'pre-existing executor must survive the refusal'


# ============================================================================
# The embedded runtime resolver tracks select_live_version_dir
# ============================================================================
# _CLAUDE_RESOLVER_TEMPLATE is substituted verbatim into the generated executor,
# which is bootstrap-free and therefore CANNOT import the selector. Its copy of
# the liveness-and-ordering policy is the single sanctioned duplicate, and these
# cases are what make it safe: over an identical on-disk fixture the embedded
# resolver and select_live_version_dir must choose the SAME version dir in every
# marker state.


def _mark_cache_version(home: Path, version: str) -> None:
    """Stamp ``.orphaned_at`` on a fake plugin-cache version dir."""
    version_dir = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / version
    (version_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z')


def _selector_choice(home: Path, skill: str, script: str) -> Path:
    """The version dir select_live_version_dir picks over the same fixture."""
    module = load_module()
    cache_root = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
    selected = module.select_live_version_dir(
        cache_root, lambda d: (d / 'skills' / skill / 'scripts' / f'{script}.py').is_file()
    )
    assert selected is not None, 'fixture must offer at least one eligible version dir'
    return Path(selected)


def _assert_resolver_agrees_with_selector(home: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, 'home', lambda: home)
    expected = _selector_choice(home, 'manage-files', 'manage-files')

    resolve = _load_claude_resolver()
    result = resolve('plan-marshall:manage-files:manage-files')

    assert result is not None, 'the embedded resolver must resolve the fixture notation'
    assert Path(result).parents[3] == expected.resolve(), (
        f'embedded resolver chose {Path(result).parents[3]}, selector chose {expected.resolve()}'
    )


def test_embedded_resolver_agrees_with_selector_none_marked(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files')

    _assert_resolver_agrees_with_selector(home, monkeypatch)


def test_embedded_resolver_agrees_with_selector_newest_marked(tmp_path, monkeypatch):
    # The marked newest dir is the retention pin, so BOTH sides keep it.
    home = tmp_path / 'home'
    _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files')
    _mark_cache_version(home, '0.1.200')

    _assert_resolver_agrees_with_selector(home, monkeypatch)


def test_embedded_resolver_agrees_with_selector_all_marked(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files')
    _mark_cache_version(home, '0.1.100')
    _mark_cache_version(home, '0.1.200')

    _assert_resolver_agrees_with_selector(home, monkeypatch)


def test_embedded_resolver_agrees_with_selector_marked_non_pinned(tmp_path, monkeypatch):
    # The pin (0.1.300) carries no candidate script, so the mark on 0.1.200 is
    # honoured — the one state in which a mark still moves the verdict.
    home = tmp_path / 'home'
    _make_cache_script(home, '0.1.100', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.200', 'manage-files', 'manage-files')
    _make_cache_script(home, '0.1.300', 'other-skill', 'other')
    _mark_cache_version(home, '0.1.200')

    _assert_resolver_agrees_with_selector(home, monkeypatch)


# ============================================================================
# Q-Gate finding 6dcc8f: template resolves script-relative, never cache-newest
# ============================================================================
# get_templates_dir() must resolve the executor template as a script-relative
# sibling of the EXECUTING generator (SCRIPT_DIR.parent / 'templates'), IGNORING
# the base_path (the newest cache-version dir). The live incident: an old pinned
# executor (0.1.1105) ran its own old generator code but substituted against the
# NEWEST (0.1.1116) template, producing a version-mismatched SyntaxError-bricked
# executor. Binding the template to the executing generator closes that class
# structurally. get_shared_module_dirs() is the INVERSE — it correctly STAYS
# newest-cache-version (PR #894 FIX C / GC-prune self-heal) and must not regress.


def test_get_templates_dir_is_script_relative_sibling_of_generator():
    """get_templates_dir returns SCRIPT_DIR.parent / 'templates' — the real
    templates dir co-located with generate_executor.py — and that dir carries
    the actual executor template."""
    module = load_module()

    result = module.get_templates_dir(Path('/some/unrelated/base/path'))

    expected = module.SCRIPT_DIR.parent / 'templates'
    assert result == expected, f'expected script-relative templates dir {expected}, got {result}'
    assert (result / 'execute-script.py.template').is_file(), (
        f'resolved templates dir must be the real co-located one, got {result}'
    )


def test_get_templates_dir_is_base_path_independent():
    """The resolved templates dir is identical regardless of which base_path is
    passed — base_path is intentionally unused."""
    module = load_module()

    a = module.get_templates_dir(Path('/nonexistent/cache/version-a'))
    b = module.get_templates_dir(Path('/totally/other/root/version-b'))

    assert a == b == module.SCRIPT_DIR.parent / 'templates', (
        f'get_templates_dir must ignore base_path; got a={a}, b={b}'
    )


def test_get_templates_dir_ignores_cache_newest_base_path(tmp_path):
    """Version-mismatch simulation: a base_path pointing at a DIFFERENT (newer)
    cache-version tree that itself carries a valid templates dir. get_templates_dir
    must STILL resolve to the executing generator's own co-located templates,
    never the base_path's — the exact skew from the live incident.

    Against the pre-fix resolution (``_resolve_plan_marshall_path(base_path, ...)``)
    this base_path WOULD resolve to the decoy templates dir below; the fix makes
    it resolve script-relative instead.
    """
    module = load_module()

    # Build a decoy cache-version tree carrying its own (wrong-version) template.
    decoy_templates = (
        tmp_path / 'plan-marshall' / '0.1.9999' / 'skills' / 'tools-script-executor' / 'templates'
    )
    decoy_templates.mkdir(parents=True)
    (decoy_templates / 'execute-script.py.template').write_text('# decoy newer-version template\n')

    result = module.get_templates_dir(tmp_path)

    expected = module.SCRIPT_DIR.parent / 'templates'
    assert result == expected, f'expected script-relative templates dir {expected}, got {result}'
    assert result != decoy_templates, 'must not select the decoy templates under base_path'
    assert not str(result).startswith(str(tmp_path)), (
        f'resolved templates dir must not live under the passed base_path, got {result}'
    )
    assert (result / 'execute-script.py.template').is_file(), (
        'resolved dir must be the real co-located templates dir'
    )


def test_get_shared_module_dirs_stays_base_path_newest_version(tmp_path):
    """Regression guard: get_shared_module_dirs MUST remain base_path-dependent
    (newest-cache-version) resolution — the INVERSE of get_templates_dir. This
    preserves the PR #894 FIX C / GC-prune self-heal contract governing the
    executor's OWN runtime sys.path bootstrap.
    """
    module = load_module()

    # Build a versioned cache tree carrying the shared-module dirs under base_path.
    version_root = tmp_path / 'plan-marshall' / '0.1.500' / 'skills'
    for sub in (
        'tools-file-ops',
        'tools-input-validation',
        'ref-toon-format',
        'script-shared',
        'manage-change-ledger',
    ):
        (version_root / sub / 'scripts').mkdir(parents=True)

    dirs = module.get_shared_module_dirs(tmp_path)
    dir_strs = [str(d) for d in dirs]

    assert dir_strs, 'expected shared dirs resolved under the versioned base_path'
    base_resolved = str(tmp_path.resolve())
    for d in dir_strs:
        assert d.startswith(base_resolved), (
            f'get_shared_module_dirs must resolve under the passed base_path {base_resolved}; got {d}'
        )
    # And the version dir is honoured (proving newest-cache-version resolution).
    assert all('0.1.500' in d for d in dir_strs), (
        f'shared dirs must resolve through the versioned cache tree; got {dir_strs}'
    )


# ============================================================================
# SCRIPT_SURFACES: embedded per-notation argparse accept-sets
# ============================================================================
# The generator derives each registered script's accept-set through the shared
# ``argparse_surface`` module and embeds it beside SCRIPTS, so the executor can
# reject an invalid invocation BEFORE spawning. Three properties are pinned
# here, each for a different failure the embedding could have:
#
#   - what lands in the map (populated, alias-aware, imported-module-aware, and
#     fail-closed — a non-derivable notation is ABSENT, never present-and-empty);
#   - what the digest cache does (reuse on an unchanged script set with a
#     byte-identical executor; invalidation on a sibling-module edit; and a
#     FAILED re-derivation drops the entry rather than resurrecting the stale one);
#   - the format-version lockstep that makes a mixed generator/template pair a
#     loud refusal rather than a broken executor.
#
# The synthetic scripts are laid out at the real marketplace path shape
# (``{root}/marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py``)
# because the derivation resolves a script file — and therefore its content
# hash and disk cache key — relative to the probe executor's repo root. A
# flat-layout fixture would silently fall through to the no-content-hash branch
# and exercise a code path production never takes.

_SURF_BUNDLE = 'synthetic-bundle'
_SURF_SKILL = 'synthetic-skill'


def _surface_notation(script: str) -> str:
    return f'{_SURF_BUNDLE}:{_SURF_SKILL}:{script}'


def _surface_scripts_dir(root: Path) -> Path:
    return (
        root / 'marketplace' / 'bundles' / _SURF_BUNDLE / 'skills' / _SURF_SKILL / 'scripts'
    )


def _write_surface_script(root: Path, name: str, body: str) -> str:
    """Write ``{name}.py`` at the real marketplace path shape; return its path."""
    scripts_dir = _surface_scripts_dir(root)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    path = scripts_dir / f'{name}.py'
    path.write_text(body, encoding='utf-8')
    return str(path)


_ALIAS_SCRIPT = """\
import argparse

parser = argparse.ArgumentParser(prog='aliased')
subparsers = parser.add_subparsers(dest='command')
read_p = subparsers.add_parser('read', aliases=['get'], help='Read a record')
read_p.add_argument('--plan-id')

if __name__ == '__main__':
    parser.parse_args()
"""

# The ``ci.py`` / ``ci_base.py`` relationship: this entry point declares no
# parser of its own. A static add_parser walk of this file derives nothing.
_IMPORTED_PARSER_SCRIPT = """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _surface_parser_lib import build_parser

if __name__ == '__main__':
    build_parser().parse_args()
"""

_IMPORTED_PARSER_LIB = """\
import argparse


def build_parser():
    parser = argparse.ArgumentParser(prog='imported')
    subparsers = parser.add_subparsers(dest='command')
    for name in ('pr', 'checks'):
        subparsers.add_parser(name)
    return parser
"""

_IMPORTED_PARSER_LIB_EXTENDED = """\
import argparse


def build_parser():
    parser = argparse.ArgumentParser(prog='imported')
    subparsers = parser.add_subparsers(dest='command')
    for name in ('pr', 'checks', 'issue'):
        subparsers.add_parser(name)
    return parser
"""

_BROKEN_SCRIPT = """\
import sys

sys.stderr.write('cannot start\\n')
sys.exit(3)
"""


def _generate_with_surfaces(module, tmp_path: Path, mappings: dict[str, str]) -> dict:
    """Run a real generation into ``tmp_path/.plan``; return the flattened result.

    ``generate_executor`` nests the four counts under ``surface_stats``; the
    ``generate`` command flattens them into its TOON. Flattening here keeps
    every assertion below written against the shape a CALLER sees.
    """
    result = module.generate_executor(mappings, MARKETPLACE_ROOT, dry_run=False, target='claude')
    return {**result, **(result.get('surface_stats') or {})}


def _surface_fixture(tmp_path: Path, monkeypatch, module) -> Path:
    """Point PLAN_BASE_DIR at ``tmp_path/.plan`` and return the executor path."""
    monkeypatch.delenv('PM_DIST_MANIFEST', raising=False)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    return plan_dir / 'execute-script.py'


def test_generated_executor_carries_populated_script_surfaces(tmp_path, monkeypatch):
    """A derivable script lands a SCRIPT_SURFACES entry beside its SCRIPTS entry."""
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}

    result = _generate_with_surfaces(module, tmp_path, mappings)
    assert result['status'] == 'success', result

    text = executor.read_text(encoding='utf-8')
    assert 'SCRIPT_SURFACES = {' in text, 'the executor must declare SCRIPT_SURFACES'
    assert notation in text
    surfaces = module.read_previous_surfaces(executor)
    assert notation in surfaces, f'expected a surface entry for {notation}: {surfaces!r}'
    assert surfaces[notation]['digest'], 'each entry must carry its source digest'


def test_surface_entry_accepts_both_alias_and_canonical_spelling(tmp_path, monkeypatch):
    """Alias awareness survives the round-trip into the generated executor."""
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}
    assert _generate_with_surfaces(module, tmp_path, mappings)['status'] == 'success'

    children = module.read_previous_surfaces(executor)[notation]['surface']['root']['children']
    assert 'read' in children
    assert 'get' in children, (
        'the alias spelling must be an accepted child — argparse renders it flat '
        'in the choice list, and rejecting it would be a false rejection of a '
        'documented call'
    )


def test_surface_entry_present_for_parser_built_in_an_imported_module(tmp_path, monkeypatch):
    """The mechanism's whole purpose: an entry point that declares no parser."""
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    _write_surface_script(tmp_path, '_surface_parser_lib', _IMPORTED_PARSER_LIB)
    notation = _surface_notation('imported')
    mappings = {notation: _write_surface_script(tmp_path, 'imported', _IMPORTED_PARSER_SCRIPT)}
    assert _generate_with_surfaces(module, tmp_path, mappings)['status'] == 'success'

    surfaces = module.read_previous_surfaces(executor)
    assert notation in surfaces, (
        'a parser assembled in an imported module must still yield a surface — '
        'this is the coverage a static AST walk cannot provide'
    )
    children = surfaces[notation]['surface']['root']['children']
    assert set(children) == {'pr', 'checks'}


def test_non_derivable_notation_is_absent_not_present_and_empty(tmp_path, monkeypatch):
    """Fail-closed: no entry at all, never an entry that accepts nothing.

    An empty-but-present surface would read as "this script declares no
    subcommands and no flags", which is the shape that rejects every call. The
    counts must say so too — the notation lands in ``surfaces_not_derivable``.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    notation = _surface_notation('broken')
    mappings = {notation: _write_surface_script(tmp_path, 'broken', _BROKEN_SCRIPT)}

    result = _generate_with_surfaces(module, tmp_path, mappings)
    assert result['status'] == 'success', result
    assert result['scripts_registered'] == 1
    assert result['surfaces_derived'] == 0
    assert result['surfaces_not_derivable'] == 1

    assert notation not in module.read_previous_surfaces(executor)


def test_counts_partition_the_registered_population(tmp_path, monkeypatch):
    """The three buckets sum to ``scripts_registered`` — no notation unaccounted.

    Published counts are only trustworthy if they cover the whole population; a
    partition check is what stops a silently-dropped notation from vanishing
    between the buckets.
    """
    module = load_module()
    _surface_fixture(tmp_path, monkeypatch, module)

    _write_surface_script(tmp_path, '_surface_parser_lib', _IMPORTED_PARSER_LIB)
    mappings = {
        _surface_notation('aliased'): _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT),
        _surface_notation('imported'): _write_surface_script(
            tmp_path, 'imported', _IMPORTED_PARSER_SCRIPT
        ),
        _surface_notation('broken'): _write_surface_script(tmp_path, 'broken', _BROKEN_SCRIPT),
    }

    result = _generate_with_surfaces(module, tmp_path, mappings)
    assert result['scripts_registered'] == 3
    total = (
        result['surfaces_derived']
        + result['surfaces_reused']
        + result['surfaces_not_derivable']
    )
    assert total == result['scripts_registered'], result
    assert result['surfaces_derived'] == 2
    assert result['surfaces_not_derivable'] == 1


def test_regeneration_with_unchanged_scripts_reuses_and_is_byte_identical(tmp_path, monkeypatch):
    """The steady-state claim: zero help invocations, byte-identical executor.

    ``surfaces_derived == 0`` is the observable proof that no ``--help`` child
    was spawned, and byte-identity is what makes an executor diff a real signal
    rather than per-run churn.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}

    first = _generate_with_surfaces(module, tmp_path, mappings)
    assert first['surfaces_derived'] == 1
    assert first['surfaces_reused'] == 0
    first_bytes = executor.read_bytes()

    second = _generate_with_surfaces(module, tmp_path, mappings)
    assert second['surfaces_derived'] == 0, (
        'an unchanged script set must perform ZERO derivations on regeneration'
    )
    assert second['surfaces_reused'] == 1
    assert executor.read_bytes() == first_bytes, (
        'regeneration over an unchanged script set must be byte-stable'
    )


def test_editing_an_imported_sibling_module_invalidates_the_cached_surface(tmp_path, monkeypatch):
    """A change in an IMPORTED module must re-derive the dependent surface.

    The entry-point file is byte-identical across both generations; only its
    sibling changed. A digest that covered the script file alone would reuse a
    surface that no longer describes the parser.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    _write_surface_script(tmp_path, '_surface_parser_lib', _IMPORTED_PARSER_LIB)
    notation = _surface_notation('imported')
    mappings = {notation: _write_surface_script(tmp_path, 'imported', _IMPORTED_PARSER_SCRIPT)}

    first = _generate_with_surfaces(module, tmp_path, mappings)
    assert first['surfaces_derived'] == 1
    before = module.read_previous_surfaces(executor)[notation]
    assert set(before['surface']['root']['children']) == {'pr', 'checks'}

    # Only the sibling module changes — the entry point is untouched.
    _write_surface_script(tmp_path, '_surface_parser_lib', _IMPORTED_PARSER_LIB_EXTENDED)

    second = _generate_with_surfaces(module, tmp_path, mappings)
    assert second['surfaces_derived'] == 1, (
        'a sibling-module edit must invalidate the dependent surface, not reuse it'
    )
    assert second['surfaces_reused'] == 0
    after = module.read_previous_surfaces(executor)[notation]
    assert after['digest'] != before['digest']
    assert set(after['surface']['root']['children']) == {'pr', 'checks', 'issue'}


def test_failed_rederivation_drops_the_entry_rather_than_reusing_the_cached_one(
    tmp_path, monkeypatch
):
    """A stale surface is never resurrected by a derivation that failed.

    The very edit that broke the help may be the edit that changed the surface,
    so carrying the old entry forward would assert an accept-set the script no
    longer has — and reject a call that is now valid.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}

    assert _generate_with_surfaces(module, tmp_path, mappings)['surfaces_derived'] == 1
    assert notation in module.read_previous_surfaces(executor)

    # Same notation and path, now a script whose --help exits non-zero.
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _BROKEN_SCRIPT)}

    result = _generate_with_surfaces(module, tmp_path, mappings)
    assert result['surfaces_derived'] == 0
    assert result['surfaces_reused'] == 0
    assert result['surfaces_not_derivable'] == 1
    assert notation not in module.read_previous_surfaces(executor), (
        'a failed re-derivation must DROP the entry, not fall back to the cached one'
    )


def test_generator_and_shipped_template_declare_the_same_format_version():
    """The lockstep the handshake guard depends on.

    The guard compares the template's marker against the generator's constant,
    so it can only protect a MIXED pair. If the shipped pair itself drifts,
    every generation fails — this test catches that at edit time instead.
    """
    module = load_module()
    template = (module.SCRIPT_DIR.parent / 'templates' / 'execute-script.py.template').read_text(
        encoding='utf-8'
    )
    declared = module.parse_template_format_version(template)
    assert declared == module._SUPPORTED_TEMPLATE_FORMAT_VERSION, (
        f'shipped template declares TEMPLATE_FORMAT_VERSION={declared!r} but the '
        f'generator supports {module._SUPPORTED_TEMPLATE_FORMAT_VERSION} — the new '
        f'SCRIPT_SURFACES placeholder must bump BOTH in lockstep'
    )


def test_template_declares_the_script_surfaces_placeholder():
    """The placeholder the generator fills must exist in the template.

    Paired with the residue guard: the generator substituting a placeholder the
    template lacks is silent, while the template carrying one the generator does
    not fill is caught at generation. This pins the first direction.
    """
    module = load_module()
    template = (module.SCRIPT_DIR.parent / 'templates' / 'execute-script.py.template').read_text(
        encoding='utf-8'
    )
    assert 'SCRIPT_SURFACES = {' in template
    assert '{{' + 'SCRIPT_SURFACES' + '}}' in template


def test_zero_budget_disables_derivation_without_failing_generation(tmp_path, monkeypatch):
    """``PM_SURFACE_BUDGET_SECONDS=0`` emits no surfaces and still succeeds.

    The knob's whole point is that a surface-less executor is a SAFE
    configuration — it dispatches exactly as it did before the map existed — so
    zeroing the budget must degrade, never fail. The notation lands in
    ``surfaces_not_derivable`` so the absence is still counted rather than
    silently indistinguishable from a healthy derivation.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)
    monkeypatch.setenv(module._SURFACE_DERIVATION_BUDGET_ENV, '0')

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}

    # Drop the process-lifetime memo. It is keyed on the derivation INPUTS, not
    # on paths, so a sibling test that derived a byte-identical script would
    # otherwise serve this one from memory — a legitimate hit that spends no
    # budget and therefore says nothing about the knob. Production always starts
    # a generation in a fresh process; clearing here reproduces that boundary.
    module.surface_api.clear_memo()

    result = _generate_with_surfaces(module, tmp_path, mappings)
    assert result['status'] == 'success', result
    assert result['surfaces_derived'] == 0
    assert result['surfaces_not_derivable'] == 1
    assert notation not in module.read_previous_surfaces(executor)
    assert executor.is_file(), 'a zeroed budget must still write the executor'


def test_unparseable_budget_falls_back_to_the_default(monkeypatch):
    """A malformed budget must not fail generation — it falls back."""
    module = load_module()
    monkeypatch.setenv(module._SURFACE_DERIVATION_BUDGET_ENV, 'not-a-number')
    assert (
        module._surface_derivation_config().total_budget_seconds
        == module._DEFAULT_SURFACE_BUDGET_SECONDS
    )
    monkeypatch.setenv(module._SURFACE_DERIVATION_BUDGET_ENV, '-5')
    assert (
        module._surface_derivation_config().total_budget_seconds
        == module._DEFAULT_SURFACE_BUDGET_SECONDS
    )
    monkeypatch.setenv(module._SURFACE_DERIVATION_BUDGET_ENV, '12.5')
    assert module._surface_derivation_config().total_budget_seconds == 12.5


def test_read_previous_surfaces_is_empty_for_an_executor_without_the_block(tmp_path):
    """A pre-SCRIPT_SURFACES executor yields "nothing to reuse", never an error."""
    module = load_module()
    legacy = tmp_path / 'execute-script.py'
    legacy.write_text('#!/usr/bin/env python3\nSCRIPTS = {\n}\n', encoding='utf-8')
    assert module.read_previous_surfaces(legacy) == {}


def test_read_previous_surfaces_is_empty_for_a_missing_executor(tmp_path):
    module = load_module()
    assert module.read_previous_surfaces(tmp_path / 'absent.py') == {}


def test_surfaces_code_emission_is_sorted_and_deterministic():
    """Mirrors generate_mappings_code's sorted emission, so output is stable."""
    module = load_module()
    surfaces = {
        'z:z:z': {'digest': 'd1', 'surface': {'root': {'flags': ['b', 'a']}}},
        'a:a:a': {'digest': 'd2', 'surface': {'root': {'flags': []}}},
    }
    code = module.generate_surfaces_code(surfaces)
    lines = code.strip().split('\n')
    assert lines[0].strip().startswith('"a:a:a"')
    assert lines[-1].strip().startswith('"z:z:z"')
    assert module.generate_surfaces_code(surfaces) == code

    # And the emitted literal is valid Python that round-trips.
    import ast as _ast

    parsed = _ast.literal_eval('{\n' + code + '\n}')
    assert set(parsed) == {'a:a:a', 'z:z:z'}


def test_format_skew_refuses_before_spending_the_accept_set_derivation(
    tmp_path, monkeypatch
):
    """The cheap refusal runs FIRST — ahead of the expensive derivation.

    The format handshake is a comparison against a marker already in hand and it
    writes nothing when it trips, while derivation spawns one ``--help`` child
    per parser node under a multi-minute budget. Running them the other way
    round spends the whole budget to reach a conclusion that was available up
    front — and on a real script set that is minutes per refused generation.

    The order is asserted through an observable (the derivation never ran), not
    through source inspection, and the positive control below is what makes the
    zero mean something: it proves the spy is wired to a call site that DOES
    fire at the supported version, so ``calls == []`` reports ordering rather
    than a probe that could never have observed anything.
    """
    module = load_module()
    executor = _surface_fixture(tmp_path, monkeypatch, module)

    calls: list[tuple] = []

    def _spy(*args, **kwargs):
        calls.append(args)
        return {}, dict(module._EMPTY_SURFACE_STATS)

    monkeypatch.setattr(module, 'derive_script_surfaces', _spy)

    notation = _surface_notation('aliased')
    mappings = {notation: _write_surface_script(tmp_path, 'aliased', _ALIAS_SCRIPT)}

    # Positive control — supported version, derivation reached.
    ok = module.generate_executor(
        mappings, MARKETPLACE_ROOT, dry_run=False, target='claude'
    )
    assert ok['status'] == 'success', ok
    assert len(calls) == 1, 'the spy never observed the derivation call site'
    unchanged = executor.read_bytes()

    # Now skew the handshake by moving the generator's supported version.
    calls.clear()
    monkeypatch.setattr(module, '_SUPPORTED_TEMPLATE_FORMAT_VERSION', 999)

    result = module.generate_executor(
        mappings, MARKETPLACE_ROOT, dry_run=False, target='claude'
    )

    assert result['status'] == 'error'
    assert 'Template format skew' in result['error']
    assert calls == [], (
        'the accept-set derivation ran before a refusal that writes nothing — '
        'the whole derivation budget is spent to reach a conclusion available '
        'from a string comparison'
    )
    assert executor.read_bytes() == unchanged, (
        'a refused generation must leave the existing executor byte-identical'
    )
    assert list(executor.parent.glob('*.probe.tmp')) == [], (
        'the throwaway probe executor leaked — it is written only for the '
        'derivation and unlinked on every exit path'
    )


def test_dry_run_surface_stats_is_a_copy_of_the_shared_default(capsys):
    """The dry-run path hands out a COPY of the module-level empty default.

    ``_EMPTY_SURFACE_STATS`` is a mutable module-level dict serving as the
    baseline for three producers. Returning it by reference makes any caller
    that aggregates in place — ``stats['scripts_registered'] += n``, the exact
    shape the OSError path already uses on its own copy — permanently rewrite
    the baseline every LATER caller receives. The second dry run below is what
    makes the identity assertion bite: it observes the consequence, not just
    the mechanism.
    """
    module = load_module()

    first = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=True)
    capsys.readouterr()

    assert first['surface_stats'] is not module._EMPTY_SURFACE_STATS
    assert first['surface_stats'] == module._EMPTY_SURFACE_STATS

    baseline = dict(module._EMPTY_SURFACE_STATS)
    first['surface_stats']['scripts_registered'] = 99

    assert module._EMPTY_SURFACE_STATS == baseline, (
        'mutating the returned stats rewrote the shared module-level default'
    )

    second = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=True)
    capsys.readouterr()

    assert second['surface_stats'] == baseline, (
        'a later dry run inherited the earlier caller mutation'
    )
