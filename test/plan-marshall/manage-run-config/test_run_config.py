#!/usr/bin/env python3
"""Tests for run_config.py script.

Consolidated from:
- test_init_run_config.py → init subcommand tests
- test_validate_run_config.py → validate subcommand tests
- cleanup subcommands (cleanup, cleanup-status)

Tests run-configuration.json initialization, validation, and cleanup.
"""

import json
import os
import shutil
import time

from conftest import PlanContext, get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# Init Subcommand Tests
# =============================================================================


def test_init_create_new_config():
    """Test init creates new run-configuration.json."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('action') == 'created', "Action should be 'created'"

        # Verify file exists in base directory
        config_file = ctx.fixture_dir / 'run-configuration.json'
        assert config_file.exists(), 'Config file should be created'


def test_init_skip_existing():
    """Test init skips if file already exists."""
    with PlanContext() as ctx:
        # Create existing file
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {}}')

        result = run_script(SCRIPT_PATH, 'init')
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('action') == 'skipped', "Action should be 'skipped'"


def test_init_force_overwrite():
    """Test init with --force overwrites existing file."""
    with PlanContext() as ctx:
        # Create existing file with old content
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {"old": {}}}')

        result = run_script(SCRIPT_PATH, 'init', '--force')
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'

        # Verify old command entry is gone
        content = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert 'old' not in content.get('commands', {}), 'Old command should be removed'


def test_init_correct_structure():
    """Test init creates file with correct structure."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        config_file = ctx.fixture_dir / 'run-configuration.json'
        content = json.loads(config_file.read_text())

        # Check version
        assert content.get('version') == 1, 'Version should be 1'

        # Check commands is empty object
        assert content.get('commands') == {}, 'Commands should be empty object'

        # Check maven section with acceptable_warnings
        maven = content.get('maven', {})
        aw = maven.get('acceptable_warnings', {})
        assert 'transitive_dependency' in aw, 'Should have transitive_dependency category'
        assert 'plugin_compatibility' in aw, 'Should have plugin_compatibility category'
        assert 'platform_specific' in aw, 'Should have platform_specific category'


def test_init_creates_config_in_base_dir():
    """Test init creates run-configuration.json in base directory."""
    with PlanContext() as ctx:
        # Ensure config does not exist yet
        config_file = ctx.fixture_dir / 'run-configuration.json'
        if config_file.exists():
            config_file.unlink()

        run_script(SCRIPT_PATH, 'init')

        assert config_file.exists(), 'Config file should be created in base directory'


def test_init_output_includes_path():
    """Test init output includes path."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'init')
        data = result.toon()

        assert 'path' in data, 'Output should include path field'


def test_init_output_includes_structure():
    """Test init output includes structure when created."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'init')
        data = result.toon()

        assert data.get('action') == 'created', 'Should be created'
        assert 'structure' in data, 'Output should include structure field'


# =============================================================================
# Validate Subcommand Tests
# =============================================================================


def test_validate_valid_run_config():
    """Test validate valid run-configuration.json."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'run-configuration.json').write_text("""{
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

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'run-configuration.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is True, 'Valid config should be valid'


def test_validate_missing_version():
    """Test validate detects missing version."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'missing-version.json').write_text("""{
  "commands": {
    "test-cmd": {}
  }
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'missing-version.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is False, 'Missing version should be invalid'


def test_validate_missing_commands():
    """Test validate detects missing commands."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'missing-commands.json').write_text("""{
  "version": 1
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'missing-commands.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is False, 'Missing commands should be invalid'


def test_validate_wrong_version_type():
    """Test validate detects wrong version type."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'wrong-version-type.json').write_text("""{
  "version": "1",
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'wrong-version-type.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is False, 'Wrong version type should be invalid'


def test_validate_with_maven():
    """Test validate with maven section."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'with-maven.json').write_text("""{
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

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'with-maven.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is True, 'Config with maven section should be valid'


def test_validate_with_agent_decisions():
    """Test validate with agent_decisions section."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'with-agent-decisions.json').write_text("""{
  "version": 1,
  "commands": {},
  "agent_decisions": {
    "test-agent": {
      "status": "keep-monolithic",
      "decision_date": "2025-11-25"
    }
  }
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'with-agent-decisions.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        assert data.get('valid') is True, 'Config with agent_decisions should be valid'


def test_validate_invalid_json_syntax():
    """Test validate detects invalid JSON syntax."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'invalid-json.json').write_text("""{
  "broken": true,
  missing-quotes: "value"
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'invalid-json.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Invalid JSON should be invalid'


def test_validate_checks_array():
    """Test validate output includes checks array."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'run-configuration.json'))
        data = result.toon()

        assert data.get('status') == 'success', 'Should succeed'
        checks = data.get('checks', [])
        assert len(checks) > 0, 'Should include checks array with items'


def test_validate_file_not_found():
    """Test validate file not found returns error."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'nonexistent.json'))
        # Script may output to stderr for errors
        data = result.toon_or_error()

        assert data.get('status') == 'error', 'Should fail for non-existent file'


def test_validate_format_is_run_config():
    """Test validate format is run-config."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'run-configuration.json'))
        data = result.toon()

        assert data.get('format') == 'manage-run-config', "Format should be 'manage-run-config'"


# =============================================================================
# Timeout Subcommand Tests
# =============================================================================


def parse_toon_output(output: str) -> dict:
    """Parse TOON output into dict using toon_parser."""
    from toon_parser import parse_toon

    return parse_toon(output)


def test_timeout_get_default_when_no_persisted():
    """Test timeout get returns default when no persisted value."""
    with PlanContext() as ctx:
        # Create .plan directory
        (ctx.fixture_dir).mkdir(parents=True, exist_ok=True)

        result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data['timeout_seconds'] == 300


def test_timeout_get_with_safety_margin():
    """Test timeout get applies safety margin to persisted value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with persisted timeout
        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 240}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        # 240 * 1.25 = 300
        assert data['timeout_seconds'] == 300


def test_timeout_get_enforces_minimum_on_persisted():
    """Test timeout get enforces minimum bound when persisted value is too low."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with very low persisted timeout (e.g., from warm JVM run)
        config = {
            'version': 1,
            'commands': {
                'maven:discover': {
                    'timeout_seconds': 15  # Very short from warm run
                }
            },
        }
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'maven:discover', '--default', '60')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        # 15 * 1.25 = 18.75 -> 18, but minimum is 120
        assert data['timeout_seconds'] == 120


def test_timeout_get_enforces_minimum_on_default():
    """Test timeout get enforces minimum bound when default is too low."""
    with PlanContext() as ctx:
        # Create .plan directory
        (ctx.fixture_dir).mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH, 'timeout', 'get', '--command', 'quick:command', '--default', '30'
        )  # Very low default

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        # Default 30 is below minimum 120
        assert data['timeout_seconds'] == 120


def test_timeout_set_initial_value():
    """Test timeout set writes directly when no existing value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '180')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('status') == 'success'
        assert data.get('timeout_seconds') == 180
        assert data.get('source') == 'initial'

        # Verify file was written
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['commands']['ci:pr_checks']['timeout_seconds'] == 180


def test_timeout_set_weighted_update():
    """Test timeout set computes weighted value when existing."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with existing timeout
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


def test_timeout_set_weighted_favors_higher():
    """Test timeout set weighted calculation favors higher value regardless of order."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with lower existing timeout
        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 180}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        # Set higher duration
        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '240')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        # Higher=240, Lower=180: 0.8 * 240 + 0.2 * 180 = 228
        assert data.get('timeout_seconds') == 228


def test_timeout_set_same_value():
    """Test timeout set with same value returns same value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
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


def test_warning_add_pattern():
    """Test warning add adds pattern to acceptable list."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Initialize config
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

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        patterns = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'uses transitive dependency' in patterns


def test_warning_add_duplicate_skips():
    """Test warning add skips duplicate pattern."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with existing pattern
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


def test_warning_add_invalid_category():
    """Test warning add rejects invalid category."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'invalid_category', '--pattern', 'test')

        # argparse will fail with invalid choice
        assert result.returncode != 0


def test_warning_list_all_categories():
    """Test warning list returns all categories."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create config with patterns
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


def test_warning_list_single_category():
    """Test warning list with category filter."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
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


def test_warning_remove_pattern():
    """Test warning remove removes pattern from list."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
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

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        patterns = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'pattern1' not in patterns
        assert 'pattern2' in patterns


def test_warning_remove_nonexistent_skips():
    """Test warning remove skips non-existent pattern."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
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


def test_warning_list_empty_config():
    """Test warning list with empty/missing config."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(SCRIPT_PATH, 'warning', 'list')

        data = result.toon()
        assert data.get('status') == 'success'
        # All categories should be empty
        categories = data.get('categories', {})
        for cat in categories.values():
            assert cat == []


# =============================================================================
# Cleanup Subcommand Tests (via unified entry point)
# =============================================================================

# Default retention config for cleanup tests
DEFAULT_RETENTION = {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}


def setup_marshal_json(fixture_dir, retention=None):
    """Create marshal.json with retention settings."""
    config = {'system': {'retention': retention or DEFAULT_RETENTION}}
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))


def test_cleanup_temp_via_unified():
    """Cleanup subcommand cleans temp directory."""
    with PlanContext(plan_id='test-cleanup-unified-temp') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / 'file1.txt').write_text('content1')
        (temp_dir / 'file2.json').write_text('{"key": "value"}')

        result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'temp')
        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'temp_files: 2' in result.stdout

        # Verify files were deleted
        remaining = list(temp_dir.iterdir())
        assert len(remaining) == 0, f'Files remain: {remaining}'


def test_cleanup_dry_run_via_unified():
    """Cleanup subcommand dry-run shows what would be deleted."""
    with PlanContext(plan_id='test-cleanup-unified-dryrun') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        test_file = temp_dir / 'keep-me.txt'
        test_file.write_text('should not be deleted')

        result = run_script(SCRIPT_PATH, 'cleanup', '--dry-run', '--target', 'temp')
        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: dry_run' in result.stdout

        # File should NOT be deleted
        assert test_file.exists(), 'File should not be deleted in dry-run mode'


def test_cleanup_logs_via_unified():
    """Cleanup subcommand cleans old log files."""
    with PlanContext(plan_id='test-cleanup-unified-logs') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        logs_dir = ctx.fixture_dir / 'logs'
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


def test_cleanup_status_via_unified():
    """Cleanup-status subcommand shows directory statistics."""
    with PlanContext(plan_id='test-cleanup-unified-status') as ctx:
        # Clean any leftover dirs
        for subdir in ['temp', 'logs', 'archived-plans', 'memory']:
            path = ctx.fixture_dir / subdir
            if path.exists():
                shutil.rmtree(path)

        setup_marshal_json(ctx.fixture_dir)

        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / 'file1.txt').write_text('12345')

        result = run_script(SCRIPT_PATH, 'cleanup-status')
        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: ok' in result.stdout
        assert 'temp_files: 1' in result.stdout


def test_cleanup_missing_marshal_json_via_unified():
    """Cleanup subcommand outputs TOON error and exits 0 when marshal.json is missing."""
    with PlanContext(plan_id='test-cleanup-unified-nomarshal') as ctx:
        marshal_path = ctx.fixture_dir / 'marshal.json'
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
