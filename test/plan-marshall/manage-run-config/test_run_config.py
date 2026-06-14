#!/usr/bin/env python3
"""Tests for run_config.py script.

Tests run-configuration.json initialization, validation, and cleanup.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')

# In-process handle for resolver-behaviour tests (mirrors test_git_merge_lock.py).
_spec = importlib.util.spec_from_file_location('run_config', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
run_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_config)


# =============================================================================
# Init Subcommand Tests
# =============================================================================


def test_init_create_new_config(plan_context):
    """Test init creates new run-configuration.json."""
    result = run_script(SCRIPT_PATH, 'init')
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('action') == 'created', "Action should be 'created'"

    config_file = plan_context.fixture_dir / 'run-configuration.json'
    assert config_file.exists(), 'Config file should be created'


def test_init_skip_existing(plan_context):
    """Test init skips if file already exists."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {}}')

    result = run_script(SCRIPT_PATH, 'init')
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('action') == 'skipped', "Action should be 'skipped'"


def test_init_force_overwrite(plan_context):
    """Test init with --force overwrites existing file."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {"old": {}}}')

    result = run_script(SCRIPT_PATH, 'init', '--force')
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'

    content = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert 'old' not in content.get('commands', {}), 'Old command should be removed'


def test_init_correct_structure(plan_context):
    """Test init creates file with correct structure."""
    run_script(SCRIPT_PATH, 'init')

    config_file = plan_context.fixture_dir / 'run-configuration.json'
    content = json.loads(config_file.read_text())

    assert content.get('version') == 1, 'Version should be 1'

    assert content.get('commands') == {}, 'Commands should be empty object'

    maven = content.get('maven', {})
    aw = maven.get('acceptable_warnings', {})
    assert 'transitive_dependency' in aw, 'Should have transitive_dependency category'
    assert 'plugin_compatibility' in aw, 'Should have plugin_compatibility category'
    assert 'platform_specific' in aw, 'Should have platform_specific category'


def test_init_creates_config_in_base_dir(plan_context):
    """Test init creates run-configuration.json in base directory."""
    config_file = plan_context.fixture_dir / 'run-configuration.json'
    if config_file.exists():
        config_file.unlink()

    run_script(SCRIPT_PATH, 'init')

    assert config_file.exists(), 'Config file should be created in base directory'


def test_init_output_includes_path(plan_context):
    """Test init output includes path."""
    result = run_script(SCRIPT_PATH, 'init')
    data = result.toon()

    assert 'path' in data, 'Output should include path field'


def test_init_output_includes_structure(plan_context):
    """Test init output includes structure when created."""
    result = run_script(SCRIPT_PATH, 'init')
    data = result.toon()

    assert data.get('action') == 'created', 'Should be created'
    assert 'structure' in data, 'Output should include structure field'


# =============================================================================
# Validate Subcommand Tests
# =============================================================================


def test_validate_valid_run_config(plan_context):
    """Test validate valid run-configuration.json."""
    (plan_context.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {
    "test-cmd": {
      "last_execution": {
        "date": "2025-11-25",
        "status": "SUCCESS"
      }
    }
  }
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'run-configuration.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('valid') is True, 'Valid config should be valid'


def test_validate_missing_version(plan_context):
    """Test validate detects missing version."""
    (plan_context.fixture_dir / 'missing-version.json').write_text("""{
  "commands": {
    "test-cmd": {}
  }
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'missing-version.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('valid') is False, 'Missing version should be invalid'


def test_validate_missing_commands(plan_context):
    """Test validate detects missing commands."""
    (plan_context.fixture_dir / 'missing-commands.json').write_text("""{
  "version": 1
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'missing-commands.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('valid') is False, 'Missing commands should be invalid'


def test_validate_wrong_version_type(plan_context):
    """Test validate detects wrong version type."""
    (plan_context.fixture_dir / 'wrong-version-type.json').write_text("""{
  "version": "1",
  "commands": {}
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'wrong-version-type.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('valid') is False, 'Wrong version type should be invalid'


def test_validate_with_maven(plan_context):
    """Test validate with maven section."""
    (plan_context.fixture_dir / 'with-maven.json').write_text("""{
  "version": 1,
  "commands": {},
  "maven": {
    "build": {
      "last_execution": {
        "duration_ms": 45000
      }
    }
  }
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'with-maven.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    assert data.get('valid') is True, 'Config with maven section should be valid'


def test_validate_invalid_json_syntax(plan_context):
    """Test validate detects invalid JSON syntax."""
    (plan_context.fixture_dir / 'invalid-json.json').write_text("""{
  "broken": true,
  missing-quotes: "value"
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'invalid-json.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed (validation ran)'
    assert data.get('valid') is False, 'Invalid JSON should be invalid'


def test_validate_checks_array(plan_context):
    """Test validate output includes checks array."""
    (plan_context.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'run-configuration.json'))
    data = result.toon()

    assert data.get('status') == 'success', 'Should succeed'
    checks = data.get('checks', [])
    assert len(checks) > 0, 'Should include checks array with items'


def test_validate_file_not_found(plan_context):
    """Test validate file not found returns error."""
    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'nonexistent.json'))
    # Script may output to stderr for errors
    data = result.toon_or_error()

    assert data.get('status') == 'error', 'Should fail for non-existent file'


def test_validate_format_is_run_config(plan_context):
    """Test validate format is run-config."""
    (plan_context.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(plan_context.fixture_dir / 'run-configuration.json'))
    data = result.toon()

    assert data.get('format') == 'manage-run-config', "Format should be 'manage-run-config'"


# =============================================================================
# Timeout Subcommand Tests
# =============================================================================


def test_timeout_get_default_when_no_persisted(plan_context):
    """Test timeout get returns default when no persisted value."""
    (plan_context.fixture_dir).mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data['timeout_seconds'] == 300


def test_timeout_get_with_safety_margin(plan_context):
    """Test timeout get applies safety margin to persisted value."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 240}}}
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # 240 * 1.25 = 300
    assert data['timeout_seconds'] == 300


def test_timeout_get_enforces_minimum_on_persisted(plan_context):
    """Test timeout get enforces minimum bound when persisted value is too low."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    # A very low persisted timeout, e.g. from a warm JVM run.
    config = {
        'version': 1,
        'commands': {
            'maven:discover': {
                'timeout_seconds': 15
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'maven:discover', '--default', '60')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # 15 * 1.25 = 18.75 -> 18, but minimum is 120
    assert data['timeout_seconds'] == 120


def test_timeout_get_enforces_minimum_on_default(plan_context):
    """Test timeout get enforces minimum bound when default is too low."""
    (plan_context.fixture_dir).mkdir(parents=True, exist_ok=True)

    result = run_script(
        SCRIPT_PATH, 'timeout', 'get', '--command', 'quick:command', '--default', '30'
    )

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # Default 30 is below minimum 120
    assert data['timeout_seconds'] == 120


def test_timeout_set_initial_value(plan_context):
    """Test timeout set writes directly when no existing value."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '180')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('timeout_seconds') == 180
    assert data.get('source') == 'initial'

    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['commands']['ci:pr_checks']['timeout_seconds'] == 180


def test_timeout_set_weighted_update(plan_context):
    """Test timeout set computes weighted value when existing."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 240}}}
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '180')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    # 0.8 * 240 + 0.2 * 180 = 192 + 36 = 228
    assert data.get('timeout_seconds') == 228
    assert data.get('previous_seconds') == 240
    assert data.get('source') == 'computed'


def test_timeout_set_weighted_favors_higher(plan_context):
    """Test timeout set weighted calculation favors higher value regardless of order."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 180}}}
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '240')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # Higher=240, Lower=180: 0.8 * 240 + 0.2 * 180 = 228
    assert data.get('timeout_seconds') == 228


def test_timeout_set_same_value(plan_context):
    """Test timeout set with same value returns same value."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 300}}}
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '300')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    # 0.8 * 300 + 0.2 * 300 = 300
    assert data.get('timeout_seconds') == 300


def test_timeout_help():
    """Test timeout subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'timeout', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'get' in result.stdout
    assert 'set' in result.stdout


def test_timeout_get_help():
    """Test timeout get subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'timeout', 'get', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--command' in result.stdout
    assert '--default' in result.stdout


def test_timeout_set_help():
    """Test timeout set subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'timeout', 'set', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--command' in result.stdout
    assert '--duration' in result.stdout


# =============================================================================
# Warning Subcommand Tests
# =============================================================================


def test_warning_add_pattern(plan_context):
    """Test warning add adds pattern to acceptable list."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    run_script(SCRIPT_PATH, 'init')

    result = run_script(
        SCRIPT_PATH,
        'warning',
        'add',
        '--category',
        'transitive_dependency',
        '--pattern',
        'uses transitive dependency',
    )

    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'added'

    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    patterns = config['maven']['acceptable_warnings']['transitive_dependency']
    assert 'uses transitive dependency' in patterns


def test_warning_add_duplicate_skips(plan_context):
    """Test warning add skips duplicate pattern."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'commands': {},
        'maven': {
            'acceptable_warnings': {
                'transitive_dependency': ['existing pattern'],
                'plugin_compatibility': [],
                'platform_specific': [],
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(
        SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'existing pattern'
    )

    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'skipped'


def test_warning_add_invalid_category(plan_context):
    """Test warning add rejects invalid category."""
    run_script(SCRIPT_PATH, 'init')

    result = run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'invalid_category', '--pattern', 'test')

    assert result.returncode != 0


def test_warning_list_all_categories(plan_context):
    """Test warning list returns all categories."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'commands': {},
        'maven': {
            'acceptable_warnings': {
                'transitive_dependency': ['pattern1', 'pattern2'],
                'plugin_compatibility': ['pattern3'],
                'platform_specific': [],
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'warning', 'list')

    data = result.toon()
    assert data.get('status') == 'success'
    assert 'categories' in data
    assert data['categories']['transitive_dependency'] == ['pattern1', 'pattern2']
    assert data['categories']['plugin_compatibility'] == ['pattern3']


def test_warning_list_single_category(plan_context):
    """Test warning list with category filter."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'commands': {},
        'maven': {
            'acceptable_warnings': {
                'transitive_dependency': ['pattern1', 'pattern2'],
                'plugin_compatibility': ['pattern3'],
                'platform_specific': [],
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(SCRIPT_PATH, 'warning', 'list', '--category', 'transitive_dependency')

    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('category') == 'transitive_dependency'
    assert data.get('patterns') == ['pattern1', 'pattern2']


def test_warning_remove_pattern(plan_context):
    """Test warning remove removes pattern from list."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'commands': {},
        'maven': {
            'acceptable_warnings': {
                'transitive_dependency': ['pattern1', 'pattern2'],
                'plugin_compatibility': [],
                'platform_specific': [],
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(
        SCRIPT_PATH, 'warning', 'remove', '--category', 'transitive_dependency', '--pattern', 'pattern1'
    )

    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'removed'

    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    patterns = config['maven']['acceptable_warnings']['transitive_dependency']
    assert 'pattern1' not in patterns
    assert 'pattern2' in patterns


def test_warning_remove_nonexistent_skips(plan_context):
    """Test warning remove skips non-existent pattern."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'commands': {},
        'maven': {
            'acceptable_warnings': {
                'transitive_dependency': ['pattern1'],
                'plugin_compatibility': [],
                'platform_specific': [],
            }
        },
    }
    (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

    result = run_script(
        SCRIPT_PATH, 'warning', 'remove', '--category', 'transitive_dependency', '--pattern', 'nonexistent'
    )

    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'skipped'


def test_warning_help():
    """Test warning subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'warning', '--help')
    assert result.success
    assert 'add' in result.stdout
    assert 'list' in result.stdout
    assert 'remove' in result.stdout


def test_warning_add_help():
    """Test warning add subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'warning', 'add', '--help')
    assert result.success
    assert '--category' in result.stdout
    assert '--pattern' in result.stdout


def test_warning_list_empty_config(plan_context):
    """Test warning list with empty/missing config."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'warning', 'list')

    data = result.toon()
    assert data.get('status') == 'success'
    categories = data.get('categories', {})
    for cat in categories.values():
        assert cat == []


# =============================================================================
# Cleanup Subcommand Tests (via unified entry point)
# =============================================================================

# Default retention config for cleanup tests
DEFAULT_RETENTION = {'logs_days': 1, 'archived_plans_days': 5, 'lessons_superseded_days': 0, 'temp_on_maintenance': True}


def setup_marshal_json(fixture_dir, retention=None):
    """Create marshal.json with retention settings."""
    config = {'system': {'retention': retention or DEFAULT_RETENTION}}
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))


def test_cleanup_temp_via_unified(plan_context):
    """Cleanup subcommand cleans temp directory."""
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / 'file1.txt').write_text('content1')
    (temp_dir / 'file2.json').write_text('{"key": "value"}')

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'temp')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'temp_files: 2' in result.stdout

    remaining = list(temp_dir.iterdir())
    assert len(remaining) == 0, f'Files remain: {remaining}'


def test_cleanup_dry_run_via_unified(plan_context):
    """Cleanup subcommand dry-run shows what would be deleted."""
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    test_file = temp_dir / 'keep-me.txt'
    test_file.write_text('should not be deleted')

    result = run_script(SCRIPT_PATH, 'cleanup', '--dry-run', '--target', 'temp')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: dry_run' in result.stdout

    assert test_file.exists(), 'File should not be deleted in dry-run mode'


def test_cleanup_logs_via_unified(plan_context):
    """Cleanup subcommand cleans old log files."""
    setup_marshal_json(plan_context.fixture_dir)

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    old_log = logs_dir / 'old.log'
    old_log.write_text('old log content')
    old_time = time.time() - (2 * 86400)
    os.utime(old_log, (old_time, old_time))

    recent_log = logs_dir / 'recent.log'
    recent_log.write_text('recent log content')

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'logs')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'logs_deleted: 1' in result.stdout

    assert not old_log.exists(), 'Old log should be deleted'
    assert recent_log.exists(), 'Recent log should be kept'


def test_cleanup_status_via_unified(plan_context):
    """Cleanup-status subcommand shows directory statistics."""
    for subdir in ['temp', 'logs', 'archived-plans', 'memory']:
        path = plan_context.fixture_dir / subdir
        if path.exists():
            shutil.rmtree(path)

    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / 'file1.txt').write_text('12345')

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: ok' in result.stdout
    assert 'temp_files: 1' in result.stdout


def test_cleanup_missing_marshal_json_via_unified(plan_context):
    """Cleanup subcommand outputs TOON error and exits 0 when marshal.json is missing."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    if marshal_path.exists():
        marshal_path.unlink()

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout
    assert 'marshal.json not found' in result.stdout


def test_cleanup_help():
    """Cleanup subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'cleanup', '--help')
    assert result.success
    assert '--dry-run' in result.stdout
    assert '--target' in result.stdout


def test_cleanup_status_help():
    """Cleanup-status subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'cleanup-status', '--help')
    assert result.success


# =============================================================================
# Main-anchored resolution via the shared utility (deliverable 2)
# =============================================================================


def _init_repo(repo: Path) -> None:
    """Initialise a fixture git repo so ``git worktree add`` runs end-to-end."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    (repo / '.gitignore').write_text('.plan/local\n.plan/local/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


class TestRunConfigMainAnchoring:
    """run-configuration.json resolves to the MAIN checkout via
    ``resolve_main_anchored_path`` regardless of caller cwd (deliverable 2).

    The override-first branch keeps every PLAN_BASE_DIR-based test green; the
    production branch (real ``git worktree add``) proves a worktree-cwd resolve
    still lands on main.
    """

    def test_run_config_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PLAN_BASE_DIR is the main-checkout stand-in; cwd is pinned into a
        # worktree dir with its own .plan/local — the override must win over cwd.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = run_config.get_run_config_path()

        # Lands under MAIN's base, NOT the worktree-relative path.
        assert resolved == main_base / 'run-configuration.json'
        assert resolved != worktree / '.plan' / 'local' / 'run-configuration.json'

    def test_run_config_resolves_to_main_via_git_common_dir_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # REAL git repo + REAL linked worktree, no override — exercises the
        # production git-common-dir branch of the shared utility.
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        main_repo = tmp_path / 'main'
        main_repo.mkdir()
        _init_repo(main_repo)
        worktree = tmp_path / 'wt'
        subprocess.run(
            ['git', '-C', str(main_repo), 'worktree', 'add', '-q', '-b', 'feat', str(worktree)],
            check=True,
        )
        monkeypatch.chdir(worktree)

        resolved = run_config.get_run_config_path()

        # Anchored under MAIN's .plan/local, NOT the worktree's.
        expected = main_repo.resolve() / '.plan' / 'local' / 'run-configuration.json'
        assert resolved.resolve() == expected

    def test_timeout_set_writes_to_main_base_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PLAN_BASE_DIR is the main stand-in; cwd is in a worktree with its own
        # .plan/local. timeout_set must land the write on main, not the worktree.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        run_config.timeout_set('build:verify', 300)

        # The write landed under MAIN's base, NOT the worktree.
        assert (main_base / 'run-configuration.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'run-configuration.json').exists()


# =============================================================================
# Build-queue-limit knob — main-anchored round-trip (deliverable 5)
# =============================================================================


class TestBuildQueueLimitMainAnchoring:
    """The build.queue.upper_limit_seconds knob round-trips MAIN-anchored: the
    adaptive stale-reclaim limit is a cross-session corpus, so a write/read issued
    from a worktree cwd must land on (and read from) the MAIN checkout's
    run-configuration.json — never the worktree-relative copy.

    The reaper in build_queue.py reads this limit, and the release-time
    adaptive-limit recompute writes it; both run with cwd pinned to a worktree
    under ADR-002, so the main-anchored round-trip is the load-bearing property.
    """

    def test_build_queue_limit_round_trips_main_anchored_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # PLAN_BASE_DIR is the main stand-in; cwd is pinned into a worktree dir
        # with its own .plan/local — the main-anchored resolver must win over cwd.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        # Write the limit from the worktree cwd, then read it back.
        run_config._write_build_queue_upper_limit(1800)
        read_back = run_config._read_build_queue_upper_limit()

        # The write landed on MAIN's run-configuration.json (NOT the
        # worktree-relative copy) and the read resolves the same main-anchored file.
        assert read_back == 1800
        main_config = main_base / 'run-configuration.json'
        assert main_config.is_file()
        assert json.loads(main_config.read_text())['build']['queue']['upper_limit_seconds'] == 1800
        assert not (worktree / '.plan' / 'local' / 'run-configuration.json').exists()

    def test_build_queue_limit_write_clamps_then_round_trips_main_anchored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Same worktree-cwd / main-anchored setup as above.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        # Write an above-ceiling value — the clamp pins it to 3600 on main.
        run_config._write_build_queue_upper_limit(99999)

        # The persisted (and read-back) value is the 3600 s ceiling, stored on
        # MAIN, never higher.
        assert run_config._read_build_queue_upper_limit() == 3600
        main_config = main_base / 'run-configuration.json'
        assert json.loads(main_config.read_text())['build']['queue']['upper_limit_seconds'] == 3600
        assert not (worktree / '.plan' / 'local' / 'run-configuration.json').exists()
