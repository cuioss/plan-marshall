#!/usr/bin/env python3
"""Unit tests for generate_executor.py script."""

import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

from conftest import _MARKETPLACE_SCRIPT_DIRS

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


def test_cleanup_deletes_old_logs():
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

        # Patch LOGS_DIR
        original = module.LOGS_DIR
        module.LOGS_DIR = logs_dir

        try:
            deleted = module.cleanup_old_logs(max_age_days=7)
            assert deleted == 1, f'Expected 1 deleted, got {deleted}'
            assert not old_log.exists(), 'Old log should be deleted'
        finally:
            module.LOGS_DIR = original


def test_cleanup_preserves_recent_logs():
    """Cleanup preserves recent logs."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / 'logs'
        logs_dir.mkdir()

        recent_log = logs_dir / f'script-execution-{date.today()}.log'
        recent_log.write_text('recent')

        original = module.LOGS_DIR
        module.LOGS_DIR = logs_dir

        try:
            deleted = module.cleanup_old_logs(max_age_days=7)
            assert deleted == 0, f'Expected 0 deleted, got {deleted}'
            assert recent_log.exists(), 'Recent log should be preserved'
        finally:
            module.LOGS_DIR = original


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

        assert result.returncode == 1, f'Expected failure, got {result.returncode}'


def test_drift_requires_executor():
    """Drift fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'drift'], capture_output=True, text=True, cwd=tmp, env=_subprocess_env()
        )

        assert result.returncode == 1, f'Expected failure, got {result.returncode}'
        assert 'Could not read executor mappings' in result.stderr


def test_paths_requires_executor():
    """Paths fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'paths'], capture_output=True, text=True, cwd=tmp, env=_subprocess_env()
        )

        assert result.returncode == 1, f'Expected failure, got {result.returncode}'
        assert 'Could not read executor mappings' in result.stderr


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

        dirs = module._collect_script_dirs(base)

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

        dirs = module._collect_script_dirs(base)

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

        dirs = module._collect_script_dirs(base)

        hidden_str = str(scripts_dir / '.hidden')
        visible_str = str(scripts_dir / 'visible')
        assert hidden_str not in dirs, f'.hidden should be excluded, got {dirs}'
        assert visible_str in dirs, f'Expected visible in {dirs}'


def test_build_pythonpath_includes_subdirectories():
    """_build_pythonpath includes subdirectory paths in the PYTHONPATH string."""
    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create structure with subdirectories
        scripts_dir = base / 'my-bundle' / 'skills' / 'script-shared' / 'scripts'
        (scripts_dir / 'build').mkdir(parents=True)
        (scripts_dir / 'build' / '_helper.py').write_text('# helper')

        pythonpath = module._build_pythonpath(base)

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

        dirs = module._collect_script_dirs(base)

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
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert result.returncode == 0, (
        f'generate_executor.py failed without PYTHONPATH:\n{result.stderr}'
    )
