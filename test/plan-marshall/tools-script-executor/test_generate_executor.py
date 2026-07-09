#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for generate_executor.py script."""

import hashlib
import os
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

        recent_log = logs_dir / f'script-execution-{date.today()}.log'
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


def test_marketplace_root_flag_anchors_discovery_to_supplied_path(tmp_path, monkeypatch):
    """generate --marketplace-root <path> roots the SCRIPTS dict at <path>.

    Regression for the case where worktree-driven invocations of
    generate_executor.py picked up the wrong marketplace tree because the
    cwd-based fallback resolved to the parent checkout. The flag must
    override every other resolution branch.
    """
    fake_ws = _build_fake_marketplace(tmp_path)

    mappings = _generate_with_anchor(tmp_path, fake_ws, use_flag=True, monkeypatch=monkeypatch)

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
        # discovery. Allow paths under tmp_path which (on macOS) may resolve
        # via /private/var symlinks.
        if not path.startswith(str(tmp_path.resolve())) and not path.startswith(str(tmp_path)):
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


# These tests exercise the session active-plan cache writer that the executor
# template emits in main() on every invocation carrying --plan-id or
# --audit-plan-id. The helper feeds the per-target terminal-title reader
# (cluster-01 `session render-title`) so the main orchestration tab
# (cwd = repo root) renders pm:{phase}[:{short_description}] instead of
# falling through to the active-command segment.

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


def _seed_session_cache(home_dir: Path, session_id: str, cwd: str) -> None:
    """Seed the ~/.cache/plan-marshall/sessions/by-cwd/<sha256(cwd)> file.

    Mirrors what the per-target terminal-title hook writes on
    UserPromptSubmit. The template's session-id resolver reads exactly
    this layout.
    """
    cache_base = home_dir / '.cache' / 'plan-marshall' / 'sessions' / 'by-cwd'
    cache_base.mkdir(parents=True, exist_ok=True)
    cwd_hash = hashlib.sha256(cwd.encode('utf-8')).hexdigest()
    (cache_base / cwd_hash).write_text(session_id, encoding='utf-8')


def test_template_contains_write_active_plan_helper():
    """Generated executor source string must contain the _write_active_plan
    helper definition and the main() call site so the runtime executor
    actually populates the cache."""
    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    assert 'def _write_active_plan(' in source, '_write_active_plan helper missing from template'
    assert '_write_active_plan(_active_plan_id)' in source, (
        'main() must invoke _write_active_plan after extracting plan_id'
    )
    # The helper reads session_id from $CLAUDE_CODE_SESSION_ID (populated by the
    # platform-runtime SessionStart hook).
    assert 'CLAUDE_CODE_SESSION_ID' in source, (
        'template must read session id from CLAUDE_CODE_SESSION_ID env var'
    )


def test_write_active_plan_writes_cache_when_session_resolvable(tmp_path, monkeypatch):
    """When $CLAUDE_CODE_SESSION_ID is set, the helper writes plan_id to
    ~/.cache/.../sessions/<session_id>/active-plan."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-abc')
    # Patch Path.home to honour the patched HOME under py3.14 where
    # Path.home() consults os.path.expanduser via passwd db on some platforms.
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))

    module._write_active_plan('my-plan-id')

    cache_file = tmp_path / '.cache' / 'plan-marshall' / 'sessions' / 'sess-abc' / 'active-plan'
    assert cache_file.is_file(), f'Expected cache file at {cache_file}'
    assert cache_file.read_text(encoding='utf-8') == 'my-plan-id'


def test_write_active_plan_noop_when_no_session_resolvable(tmp_path, monkeypatch):
    """When $CLAUDE_CODE_SESSION_ID is unset/empty, the helper is a no-op
    and writes no file."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))

    module._write_active_plan('my-plan-id')

    # Nothing should have been written under sessions/.
    sessions_dir = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
    if sessions_dir.exists():
        children = [p.name for p in sessions_dir.iterdir() if p.is_dir()]
        assert children == [], f'No per-session dirs should be created, got {children}'


def test_write_active_plan_noop_on_invalid_plan_id(tmp_path, monkeypatch):
    """Plan ids containing path separators / ../. / oversize / empty must be
    rejected silently — no file written."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    fake_cwd = '/Users/test/project'
    _seed_session_cache(tmp_path, 'sess-eval', fake_cwd)

    class _FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(*_args, **_kwargs):
        return _FakeResult(0, fake_cwd + '\n')

    monkeypatch.setattr(module.subprocess, 'run', _fake_run)

    bad_values = [
        '',  # empty
        None,  # falsy non-string
        '../escape',  # path traversal
        'with/slash',  # path separator
        'with\\backslash',  # win-style path separator
        '..',  # traversal sentinel
        '.',  # traversal sentinel
        'a' * 200,  # oversize (>120)
    ]
    for value in bad_values:
        module._write_active_plan(value)

    cache_file = tmp_path / '.cache' / 'plan-marshall' / 'sessions' / 'sess-eval' / 'active-plan'
    assert not cache_file.exists(), f'No file should be written for invalid plan_ids; found {cache_file}'


def test_write_active_plan_swallows_oserror(tmp_path, monkeypatch):
    """Any OSError raised during the write path is silently swallowed; the
    helper never propagates exceptions to the calling script."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    fake_cwd = '/Users/test/project'
    _seed_session_cache(tmp_path, 'sess-oserr', fake_cwd)

    class _FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(*_args, **_kwargs):
        return _FakeResult(0, fake_cwd + '\n')

    monkeypatch.setattr(module.subprocess, 'run', _fake_run)

    # Patch Path.write_text on the helper's Path import to raise.
    real_write_text = module.Path.write_text

    def _raise(*_args, **_kwargs):
        raise OSError('disk full simulation')

    monkeypatch.setattr(module.Path, 'write_text', _raise)
    try:
        # Must not raise.
        module._write_active_plan('plan-x')
    finally:
        monkeypatch.setattr(module.Path, 'write_text', real_write_text)


# --- No-overwrite-with-stale-reclaim binding policy -------------------------
# The executor binds a session to a plan on the first plan-scoped invocation
# and then PROTECTS that binding: a read-only inspection call naming a
# different, still-live plan must NOT steal the slot (the observed
# mis-attribution defect). The slot is only rewritten when it is unbound,
# already names the incoming plan, or names a different plan whose live plan
# dir is gone (stale reclaim). The live plan dir is resolved as
# ``{executor_dir}/local/plans/{plan_id}`` where ``executor_dir`` is the
# directory holding the generated executor — i.e. ``Path(__file__).parent``.


def _point_executor_at(module, tmp_path, monkeypatch) -> Path:
    """Point the loaded template module's ``__file__`` at a tmp
    ``.plan/execute-script.py`` so ``_active_plan_dir_exists`` resolves live
    plan dirs under ``{tmp_path}/.plan/local/plans``.

    Returns:
        The plans root (``{tmp_path}/.plan/local/plans``) — create a
        ``{plan_id}`` subdirectory under it to mark that plan as live.
    """
    executor_dir = tmp_path / '.plan'
    executor_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, '__file__', str(executor_dir / 'execute-script.py'))
    return executor_dir / 'local' / 'plans'


def _seed_active_plan(tmp_path, session_id: str, plan_id: str) -> Path:
    """Seed the session's ``active-plan`` cache file with ``plan_id``.

    Returns the cache file path so the caller can assert on its contents.
    """
    cache = tmp_path / '.cache' / 'plan-marshall' / 'sessions' / session_id / 'active-plan'
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(plan_id, encoding='utf-8')
    return cache


def test_write_active_plan_binds_when_slot_unbound(tmp_path, monkeypatch):
    """Case 1 — the first plan-scoped invocation in an unbound session binds
    the slot (bind-on-entry), so the title keeps rendering with no
    orchestrator wiring."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-bind')
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))
    _point_executor_at(module, tmp_path, monkeypatch)

    module._write_active_plan('plan-a')

    cache_file = tmp_path / '.cache' / 'plan-marshall' / 'sessions' / 'sess-bind' / 'active-plan'
    assert cache_file.read_text(encoding='utf-8') == 'plan-a'


def test_write_active_plan_protects_binding_when_other_plan_live(tmp_path, monkeypatch):
    """Case 2 — a subsequent call naming a DIFFERENT plan whose live plan dir
    still exists is a no-op: the active binding is preserved. This is the
    exact mis-attribution scenario the fix closes — a read-only inspection
    call naming another plan must NOT steal the session's binding."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-protect')
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))
    plans_root = _point_executor_at(module, tmp_path, monkeypatch)
    # 'plan-a' is the bound plan and its live plan dir exists.
    (plans_root / 'plan-a').mkdir(parents=True, exist_ok=True)
    cache_file = _seed_active_plan(tmp_path, 'sess-protect', 'plan-a')

    module._write_active_plan('plan-b')

    assert cache_file.read_text(encoding='utf-8') == 'plan-a', (
        'a differing-plan inspection call must not overwrite a live binding'
    )


def test_write_active_plan_idempotent_for_same_plan(tmp_path, monkeypatch):
    """Case 3 — a call naming the same plan as the current binding is
    idempotent (the slot is rewritten with the identical value; no theft, no
    error)."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-same')
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))
    plans_root = _point_executor_at(module, tmp_path, monkeypatch)
    (plans_root / 'plan-a').mkdir(parents=True, exist_ok=True)
    cache_file = _seed_active_plan(tmp_path, 'sess-same', 'plan-a')

    module._write_active_plan('plan-a')

    assert cache_file.read_text(encoding='utf-8') == 'plan-a'


def test_write_active_plan_reclaims_stale_slot(tmp_path, monkeypatch):
    """Case 4 — a call naming a DIFFERENT plan whose live plan dir is absent
    reclaims the slot (stale binding → overwrite). This delivers
    release-on-exit implicitly: once the bound plan is archived/deleted its
    live dir is gone, so the next differing-plan invocation rebinds."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-stale')
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))
    # Point the executor at a tmp .plan but do NOT create a live dir for
    # 'gone-plan' — its binding is therefore stale.
    _point_executor_at(module, tmp_path, monkeypatch)
    cache_file = _seed_active_plan(tmp_path, 'sess-stale', 'gone-plan')

    module._write_active_plan('new-plan')

    assert cache_file.read_text(encoding='utf-8') == 'new-plan'


def test_write_active_plan_noop_when_session_id_absent(tmp_path, monkeypatch):
    """Case 5 — a missing ``$CLAUDE_CODE_SESSION_ID`` remains a silent no-op
    under the new binding policy (the session-id guard short-circuits before
    any read-or-write of the slot)."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
    monkeypatch.setattr(module.Path, 'home', staticmethod(lambda: tmp_path))
    _point_executor_at(module, tmp_path, monkeypatch)

    module._write_active_plan('plan-a')

    sessions_dir = tmp_path / '.cache' / 'plan-marshall' / 'sessions'
    if sessions_dir.exists():
        children = [p.name for p in sessions_dir.iterdir() if p.is_dir()]
        assert children == [], f'No per-session dirs should be created, got {children}'


def test_active_plan_dir_exists_reports_live_and_absent(tmp_path, monkeypatch):
    """Focused unit test for the ``_active_plan_dir_exists`` staleness probe:
    a present ``{executor_dir}/local/plans/{plan_id}`` dir → True; an absent
    one → False."""
    module = _load_template_module()

    plans_root = _point_executor_at(module, tmp_path, monkeypatch)
    (plans_root / 'live-plan').mkdir(parents=True, exist_ok=True)

    assert module._active_plan_dir_exists('live-plan') is True
    assert module._active_plan_dir_exists('missing-plan') is False


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


def test_write_active_plan_validate_helper_rejects_unsafe_session_id(tmp_path, monkeypatch):
    """Even when by-cwd cache contains a malformed session id (e.g.
    ``../etc``), the helper must reject it via _validate_active_plan_id and
    never traverse out of the sessions directory."""
    module = _load_template_module()

    monkeypatch.setenv('HOME', str(tmp_path))
    fake_cwd = '/Users/test/project'
    # Seed a path-traversal session id — the validator must reject it.
    _seed_session_cache(tmp_path, '../etc', fake_cwd)

    class _FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(*_args, **_kwargs):
        return _FakeResult(0, fake_cwd + '\n')

    monkeypatch.setattr(module.subprocess, 'run', _fake_run)

    module._write_active_plan('my-plan-id')

    # No file under ~/.cache/plan-marshall/etc or similar.
    escape_dir = tmp_path / '.cache' / 'plan-marshall' / 'etc'
    assert not escape_dir.exists(), 'Helper must not traverse out of sessions/ via malformed session id'


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
# build-class dispatch (a notation under plan-marshall:build-pyproject /
# build-maven / build-gradle / build-npm). The freshness gate reads these
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
    # the appender with the resolved plan_id and exit_code.
    assert 'if _is_build_class_notation(notation):' in source, (
        'main() must guard the ledger append behind _is_build_class_notation(notation)'
    )
    assert '_append_build_ledger_record(' in source, (
        'main() must invoke _append_build_ledger_record at the dispatch boundary'
    )


def test_template_build_ledger_uses_shared_primitives():
    """The append must reuse the manage-change-ledger writer and the shared
    worktree-sha helper rather than re-implementing the hash or the append."""
    source = TEMPLATE_PATH.read_text(encoding='utf-8')

    assert 'from _ledger_core import append_entry, build_record' in source, (
        'template must import append_entry + build_record from the manage-change-ledger core'
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
    guard_idx = source.find('if _is_build_class_notation(notation):')
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

    # Build-class notations across all four build-* skills classify as build.
    for build_notation in (
        'plan-marshall:build-pyproject:pyproject_build',
        'plan-marshall:build-maven:maven',
        'plan-marshall:build-gradle:gradle',
        'plan-marshall:build-npm:npm',
    ):
        assert module._is_build_class_notation(build_notation), (
            f'{build_notation} must classify as a build-class dispatch'
        )

    # Non-build notations must NOT classify as build.
    for non_build_notation in (
        'plan-marshall:manage-files:manage-files',
        'plan-marshall:manage-logging:manage-logging',
        'pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory',
    ):
        assert not module._is_build_class_notation(non_build_notation), (
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

    ok = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=False)
    assert ok, 'generate_executor should succeed with an empty mapping set'

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

    ok = module.generate_executor({}, MARKETPLACE_ROOT, dry_run=False)
    assert ok, 'fresh install (no manifest) must still generate the executor'

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


def test_preflight_returns_six_field_toon_on_fresh_install(tmp_path, monkeypatch):
    """With no manifest, preflight is a no-op reporting the full six-field TOON
    with both surfaces fresh."""
    module = load_module()

    monkeypatch.setenv('PM_DIST_MANIFEST', str(tmp_path / 'absent.json'))
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path / '.plan'))
    (tmp_path / '.plan').mkdir()
    monkeypatch.chdir(tmp_path)
    # Isolate the orthogonal multi-version-pollution scan (which reads the real
    # plugin-cache tree) so this version-staleness case stays hermetic.
    monkeypatch.setattr(module, '_detect_multi_version_pollution', lambda *a, **k: [])

    result = module.cmd_preflight(_preflight_args())

    assert set(result.keys()) == _PREFLIGHT_FIELDS, f'preflight must return exactly the six fields, got {set(result)}'
    assert result['status'] == 'success'
    assert result['executor_action'] == 'fresh'
    assert result['marshal_status'] == 'fresh'
    assert result['installed_version'] == 'unknown'
    assert result['executor_version'] == 'unknown'
    assert result['marshal_version'] == 'unknown'


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
    the six documented fields end-to-end."""
    manifest = tmp_path / 'dist-manifest.json'
    manifest.write_text('{"version": "0.1.7"}', encoding='utf-8')

    env = _subprocess_env()
    env['PM_DIST_MANIFEST'] = str(manifest)
    env['PLAN_BASE_DIR'] = str(tmp_path / '.plan')
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
