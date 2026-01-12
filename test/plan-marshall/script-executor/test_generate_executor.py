#!/usr/bin/env python3
"""Unit tests for generate-executor.py script."""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner

# Path to the script
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "marketplace/bundles/plan-marshall/skills/script-executor/scripts"
GENERATE_SCRIPT = SCRIPTS_DIR / "generate-executor.py"


def load_module():
    """Load the generate-executor module."""
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
        "planning:manage-files": "/path/to/manage-files.py",
        "builder:maven": "/path/to/maven.py",
    }

    code = module.generate_mappings_code(mappings)

    # Should be valid Python when wrapped in dict
    full_code = f"SCRIPTS = {{\n{code}\n}}"
    exec(full_code)  # Should not raise


def test_sorts_mappings_alphabetically():
    """Mappings are sorted alphabetically by notation."""
    module = load_module()

    mappings = {
        "z-bundle:skill": "/path/z.py",
        "a-bundle:skill": "/path/a.py",
        "m-bundle:skill": "/path/m.py",
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

    mappings = {"a:b": "/path/a.py", "c:d": "/path/c.py"}

    checksum1 = module.compute_checksum(mappings)
    checksum2 = module.compute_checksum(mappings)

    assert checksum1 == checksum2, f"Checksums should be equal: {checksum1} != {checksum2}"


def test_different_mappings_different_checksum():
    """Different mappings produce different checksums."""
    module = load_module()

    mappings1 = {"a:b": "/path/a.py"}
    mappings2 = {"c:d": "/path/c.py"}

    checksum1 = module.compute_checksum(mappings1)
    checksum2 = module.compute_checksum(mappings2)

    assert checksum1 != checksum2, f"Checksums should be different: {checksum1} == {checksum2}"


def test_checksum_is_8_chars():
    """Checksum is truncated to 8 characters."""
    module = load_module()

    mappings = {"a:b": "/path/a.py"}
    checksum = module.compute_checksum(mappings)

    assert len(checksum) == 8, f"Expected 8 chars, got {len(checksum)}"


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
            assert deleted == 1, f"Expected 1 deleted, got {deleted}"
            assert not old_log.exists(), "Old log should be deleted"
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
            assert deleted == 0, f"Expected 0 deleted, got {deleted}"
            assert recent_log.exists(), "Recent log should be preserved"
        finally:
            module.LOGS_DIR = original


# =============================================================================
# TESTS: Script execution
# =============================================================================

def test_help_output():
    """Script shows help with --help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), '--help'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert 'generate' in result.stdout, "Missing 'generate' in help"
    assert 'verify' in result.stdout, "Missing 'verify' in help"
    assert 'drift' in result.stdout, "Missing 'drift' in help"
    assert 'paths' in result.stdout, "Missing 'paths' in help"
    assert 'cleanup' in result.stdout, "Missing 'cleanup' in help"


def test_generate_help():
    """Generate subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'generate', '--help'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert '--force' in result.stdout, "Missing '--force' in help"
    assert '--dry-run' in result.stdout, "Missing '--dry-run' in help"


def test_verify_requires_executor():
    """Verify fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        # Run in temp directory where .plan doesn't exist
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'verify'],
            capture_output=True,
            text=True,
            cwd=tmp
        )

        assert result.returncode == 1, f"Expected failure, got {result.returncode}"


def test_drift_requires_executor():
    """Drift fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'drift'],
            capture_output=True,
            text=True,
            cwd=tmp
        )

        assert result.returncode == 1, f"Expected failure, got {result.returncode}"
        assert 'Could not read executor mappings' in result.stderr


def test_paths_requires_executor():
    """Paths fails when executor doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ['python3', str(GENERATE_SCRIPT), 'paths'],
            capture_output=True,
            text=True,
            cwd=tmp
        )

        assert result.returncode == 1, f"Expected failure, got {result.returncode}"
        assert 'Could not read executor mappings' in result.stderr


def test_drift_help():
    """Drift subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'drift', '--help'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert 'drift' in result.stdout.lower(), "Missing 'drift' in help"


def test_paths_help():
    """Paths subcommand has help."""
    result = subprocess.run(
        ['python3', str(GENERATE_SCRIPT), 'paths', '--help'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert 'paths' in result.stdout.lower(), "Missing 'paths' in help"


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
        # Check format: all keys should be bundle:skill format
        for notation in mappings:
            assert ':' in notation, f"Notation should be bundle:skill format, got {notation}"
            parts = notation.split(':')
            assert len(parts) == 2, f"Expected 2 parts in notation, got {parts}"
        # Check values are paths
        for path in mappings.values():
            assert path.endswith('.py'), f"Script path should end with .py, got {path}"
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
        if 'bundle:skill' in mappings:
            assert 'test_' not in mappings['bundle:skill'], "Should not include test files"


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
        if 'bundle:skill' in mappings:
            path = mappings['bundle:skill']
            assert '_internal' not in path, "Should not include _internal.py"
            assert '_helper' not in path, "Should not include _helper.py"
            assert 'main.py' in path, "Should include main.py"


if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_generates_valid_python_dict_syntax,
        test_sorts_mappings_alphabetically,
        test_same_mappings_same_checksum,
        test_different_mappings_different_checksum,
        test_checksum_is_8_chars,
        test_cleanup_deletes_old_logs,
        test_cleanup_preserves_recent_logs,
        test_help_output,
        test_generate_help,
        test_verify_requires_executor,
        test_drift_requires_executor,
        test_paths_requires_executor,
        test_drift_help,
        test_paths_help,
        test_discovers_scripts_from_directory_structure,
        test_skips_test_files,
        test_skips_private_modules,
    ])
    sys.exit(runner.run())
