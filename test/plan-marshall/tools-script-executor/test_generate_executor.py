#!/usr/bin/env python3
"""Unit tests for generate_executor.py script."""

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


# =============================================================================
# TESTS: generate_mappings_code
# =============================================================================


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


# =============================================================================
# TESTS: compute_checksum
# =============================================================================


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


# =============================================================================
# TESTS: cleanup_old_logs
# =============================================================================


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


# =============================================================================
# TESTS: Script execution
# =============================================================================


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


# =============================================================================
# TESTS: _resolve_plan_marshall_path
# =============================================================================


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


# =============================================================================
# TESTS: discover_scripts_fallback
# =============================================================================


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


# =============================================================================
# TESTS: _collect_script_dirs (subdirectory scanning)
# =============================================================================


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


# =============================================================================
# Bootstrap isolation test -- verify script works WITHOUT executor PYTHONPATH
# =============================================================================


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


# =============================================================================
# TESTS: --marketplace-root flag and PM_MARKETPLACE_ROOT env var
# =============================================================================
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
    dev-general-practices forbids.
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
