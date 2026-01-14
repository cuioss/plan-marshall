#!/usr/bin/env python3
"""Tests for run_config.py script.

Consolidated from:
- test_init_run_config.py → init subcommand tests
- test_validate_run_config.py → validate subcommand tests

Tests run-configuration.json initialization and validation.
"""

import json
import shutil

from conftest import PLAN_DIR_NAME, PlanContext, get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'run-config', 'run_config.py')


# =============================================================================
# Init Subcommand Tests
# =============================================================================


def test_init_create_new_config():
    """Test init creates new run-configuration.json."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('action') == 'created', "Action should be 'created'"

        # Verify file exists (uses .plan)
        config_file = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        assert config_file.exists(), 'Config file should be created'


def test_init_skip_existing():
    """Test init skips if file already exists."""
    with PlanContext() as ctx:
        # Create existing file
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)
        (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {}}')

        result = run_script(SCRIPT_PATH, 'init')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('action') == 'skipped', "Action should be 'skipped'"


def test_init_force_overwrite():
    """Test init with --force overwrites existing file."""
    with PlanContext() as ctx:
        # Create existing file with old content
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)
        (plan_dir / 'run-configuration.json').write_text('{"version": 1, "commands": {"old": {}}}')

        result = run_script(SCRIPT_PATH, 'init', '--force')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'

        # Verify old command entry is gone
        content = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert 'old' not in content.get('commands', {}), 'Old command should be removed'


def test_init_correct_structure():
    """Test init creates file with correct structure."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        config_file = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
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


def test_init_creates_plan_dir():
    """Test init creates .plan directory if needed."""
    with PlanContext() as ctx:
        # Ensure .plan doesn't exist
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        if plan_dir.exists():
            shutil.rmtree(plan_dir)

        run_script(SCRIPT_PATH, 'init')

        assert plan_dir.exists(), '.plan directory should be created'
        assert (plan_dir / 'run-configuration.json').exists(), 'Config file should be created'


def test_init_output_includes_path():
    """Test init output includes path."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'init')
        data = result.json()

        assert 'path' in data, 'Output should include path field'


def test_init_output_includes_structure():
    """Test init output includes structure when created."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'init')
        data = result.json()

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
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
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
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('valid') is False, 'Missing version should be invalid'


def test_validate_missing_commands():
    """Test validate detects missing commands."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'missing-commands.json').write_text("""{
  "version": 1
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'missing-commands.json'))
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('valid') is False, 'Missing commands should be invalid'


def test_validate_wrong_version_type():
    """Test validate detects wrong version type."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'wrong-version-type.json').write_text("""{
  "version": "1",
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'wrong-version-type.json'))
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
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
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
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
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('valid') is True, 'Config with agent_decisions should be valid'


def test_validate_invalid_json_syntax():
    """Test validate detects invalid JSON syntax."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'invalid-json.json').write_text("""{
  "broken": true,
  missing-quotes: "value"
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'invalid-json.json'))
        data = result.json()

        assert data.get('success') is True, 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Invalid JSON should be invalid'


def test_validate_checks_array():
    """Test validate output includes checks array."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'run-configuration.json'))
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        checks = data.get('checks', [])
        assert len(checks) > 0, 'Should include checks array with items'


def test_validate_file_not_found():
    """Test validate file not found returns error."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'nonexistent.json'))
        # Script may output to stderr for errors
        data = result.json_or_error()

        assert data.get('success') is False, 'Should fail for non-existent file'


def test_validate_format_is_run_config():
    """Test validate format is run-config."""
    with PlanContext() as ctx:
        (ctx.fixture_dir / 'run-configuration.json').write_text("""{
  "version": 1,
  "commands": {}
}""")

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(ctx.fixture_dir / 'run-configuration.json'))
        data = result.json()

        assert data.get('format') == 'run-config', "Format should be 'run-config'"


# =============================================================================
# Timeout Subcommand Tests
# =============================================================================


def parse_toon(output: str) -> dict:
    """Parse TOON output into dict."""
    result = {}
    for line in output.strip().split('\n'):
        if '\t' in line:
            key, value = line.split('\t', 1)
            result[key.strip()] = value.strip()
    return result


def test_timeout_get_default_when_no_persisted():
    """Test timeout get returns default when no persisted value."""
    with PlanContext() as ctx:
        # Create .plan directory
        (ctx.fixture_dir / PLAN_DIR_NAME).mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

        assert result.success, f'Should succeed: {result.stderr}'
        # Plain number output
        assert result.stdout.strip() == '300'


def test_timeout_get_with_safety_margin():
    """Test timeout get applies safety margin to persisted value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Create config with persisted timeout
        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 240}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'timeout', 'get', '--command', 'ci:pr_checks', '--default', '300')

        assert result.success, f'Should succeed: {result.stderr}'
        # 240 * 1.25 = 300 (plain number output)
        assert result.stdout.strip() == '300'


def test_timeout_get_enforces_minimum_on_persisted():
    """Test timeout get enforces minimum bound when persisted value is too low."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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
        # 15 * 1.25 = 18.75 -> 18, but minimum is 120
        assert result.stdout.strip() == '120'


def test_timeout_get_enforces_minimum_on_default():
    """Test timeout get enforces minimum bound when default is too low."""
    with PlanContext() as ctx:
        # Create .plan directory
        (ctx.fixture_dir / PLAN_DIR_NAME).mkdir(parents=True)

        result = run_script(
            SCRIPT_PATH, 'timeout', 'get', '--command', 'quick:command', '--default', '30'
        )  # Very low default

        assert result.success, f'Should succeed: {result.stderr}'
        # Default 30 is below minimum 120
        assert result.stdout.strip() == '120'


def test_timeout_set_initial_value():
    """Test timeout set writes directly when no existing value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '180')

        assert result.success, f'Should succeed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data.get('status') == 'success'
        assert data.get('timeout_seconds') == '180'
        assert data.get('source') == 'initial'

        # Verify file was written
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['commands']['ci:pr_checks']['timeout_seconds'] == 180


def test_timeout_set_weighted_update():
    """Test timeout set computes weighted value when existing."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Create config with existing timeout
        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 240}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '180')

        assert result.success, f'Should succeed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data.get('status') == 'success'
        # 0.8 * 240 + 0.2 * 180 = 192 + 36 = 228
        assert data.get('timeout_seconds') == '228'
        assert data.get('previous_seconds') == '240'
        assert data.get('source') == 'computed'


def test_timeout_set_weighted_favors_higher():
    """Test timeout set weighted calculation favors higher value regardless of order."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Create config with lower existing timeout
        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 180}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        # Set higher duration
        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '240')

        assert result.success, f'Should succeed: {result.stderr}'
        data = parse_toon(result.stdout)
        # Higher=240, Lower=180: 0.8 * 240 + 0.2 * 180 = 228
        assert data.get('timeout_seconds') == '228'


def test_timeout_set_same_value():
    """Test timeout set with same value returns same value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {'ci:pr_checks': {'timeout_seconds': 300}}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'timeout', 'set', '--command', 'ci:pr_checks', '--duration', '300')

        assert result.success, f'Should succeed: {result.stderr}'
        data = parse_toon(result.stdout)
        # 0.8 * 300 + 0.2 * 300 = 300
        assert data.get('timeout_seconds') == '300'


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
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'added'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        patterns = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'uses transitive dependency' in patterns


def test_warning_add_duplicate_skips():
    """Test warning add skips duplicate pattern."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
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
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
        assert 'categories' in data
        assert data['categories']['transitive_dependency'] == ['pattern1', 'pattern2']
        assert data['categories']['plugin_compatibility'] == ['pattern3']


def test_warning_list_single_category():
    """Test warning list with category filter."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
        assert data.get('category') == 'transitive_dependency'
        assert data.get('patterns') == ['pattern1', 'pattern2']


def test_warning_remove_pattern():
    """Test warning remove removes pattern from list."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'removed'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        patterns = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'pattern1' not in patterns
        assert 'pattern2' in patterns


def test_warning_remove_nonexistent_skips():
    """Test warning remove skips non-existent pattern."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

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

        data = result.json()
        assert data.get('success') is True
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
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'warning', 'list')

        data = result.json()
        assert data.get('success') is True
        # All categories should be empty
        categories = data.get('categories', {})
        for cat in categories.values():
            assert cat == []


# =============================================================================
# Profile Mapping Subcommand Tests
# =============================================================================


def test_profile_mapping_set():
    """Test profile-mapping set adds mapping."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Initialize config
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'set', '--profile-id', 'jfr', '--canonical', 'benchmark')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'added'
        assert data.get('profile_id') == 'jfr'
        assert data.get('canonical') == 'benchmark'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config.get('profile_mappings', {}).get('jfr') == 'benchmark'


def test_profile_mapping_set_skip():
    """Test profile-mapping set with skip canonical."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'set', '--profile-id', 'quick', '--canonical', 'skip')

        data = result.json()
        assert data.get('success') is True
        assert data.get('canonical') == 'skip'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config.get('profile_mappings', {}).get('quick') == 'skip'


def test_profile_mapping_set_update_existing():
    """Test profile-mapping set updates existing mapping."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Create config with existing mapping
        config = {'version': 1, 'commands': {}, 'profile_mappings': {'jfr': 'skip'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'set', '--profile-id', 'jfr', '--canonical', 'benchmark')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'updated'
        assert data.get('previous') == 'skip'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['profile_mappings']['jfr'] == 'benchmark'


def test_profile_mapping_set_invalid_canonical():
    """Test profile-mapping set rejects invalid canonical."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'profile-mapping', 'set', '--profile-id', 'jfr', '--canonical', 'invalid_canonical'
        )

        # argparse will fail with invalid choice
        assert result.returncode != 0


def test_profile_mapping_get_mapped():
    """Test profile-mapping get returns mapping."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'profile_mappings': {'jfr': 'benchmark'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'get', '--profile-id', 'jfr')

        data = result.json()
        assert data.get('success') is True
        assert data.get('profile_id') == 'jfr'
        assert data.get('mapped') is True
        assert data.get('canonical') == 'benchmark'


def test_profile_mapping_get_unmapped():
    """Test profile-mapping get returns unmapped for unknown profile."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'profile_mappings': {}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'get', '--profile-id', 'unknown')

        data = result.json()
        assert data.get('success') is True
        assert data.get('profile_id') == 'unknown'
        assert data.get('mapped') is False
        assert 'canonical' not in data


def test_profile_mapping_list_all():
    """Test profile-mapping list returns all mappings."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {
            'version': 1,
            'commands': {},
            'profile_mappings': {'jfr': 'skip', 'quick': 'skip', 'benchmark': 'benchmark'},
        }
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'list')

        data = result.json()
        assert data.get('success') is True
        assert data.get('count') == 3
        assert data.get('mappings') == {'jfr': 'skip', 'quick': 'skip', 'benchmark': 'benchmark'}


def test_profile_mapping_list_filter_by_canonical():
    """Test profile-mapping list with canonical filter."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {
            'version': 1,
            'commands': {},
            'profile_mappings': {'jfr': 'skip', 'quick': 'skip', 'benchmark': 'benchmark'},
        }
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'list', '--canonical', 'skip')

        data = result.json()
        assert data.get('success') is True
        assert data.get('filter') == 'skip'
        assert data.get('count') == 2
        assert data.get('mappings') == {'jfr': 'skip', 'quick': 'skip'}


def test_profile_mapping_remove():
    """Test profile-mapping remove removes mapping."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'profile_mappings': {'jfr': 'skip', 'quick': 'skip'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'remove', '--profile-id', 'jfr')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'removed'
        assert data.get('previous') == 'skip'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert 'jfr' not in config['profile_mappings']
        assert 'quick' in config['profile_mappings']


def test_profile_mapping_remove_nonexistent_skips():
    """Test profile-mapping remove skips non-existent mapping."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'profile_mappings': {}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'remove', '--profile-id', 'nonexistent')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'skipped'


def test_profile_mapping_batch_set():
    """Test profile-mapping batch-set sets multiple mappings."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH,
            'profile-mapping',
            'batch-set',
            '--mappings-json',
            '{"jfr": "skip", "quick": "skip", "benchmark": "benchmark"}',
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'batch_set'
        assert data.get('added') == 3
        assert data.get('updated') == 0

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['profile_mappings'] == {'jfr': 'skip', 'quick': 'skip', 'benchmark': 'benchmark'}


def test_profile_mapping_batch_set_with_updates():
    """Test profile-mapping batch-set handles updates and adds."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'profile_mappings': {'jfr': 'skip'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(
            SCRIPT_PATH, 'profile-mapping', 'batch-set', '--mappings-json', '{"jfr": "benchmark", "quick": "skip"}'
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('added') == 1
        assert data.get('updated') == 1


def test_profile_mapping_batch_set_invalid_canonical():
    """Test profile-mapping batch-set rejects invalid canonical."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'batch-set', '--mappings-json', '{"jfr": "invalid"}')

        data = result.json_or_error()
        assert data.get('success') is False


def test_profile_mapping_batch_set_invalid_json():
    """Test profile-mapping batch-set rejects invalid JSON."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'profile-mapping', 'batch-set', '--mappings-json', 'not valid json')

        data = result.json_or_error()
        assert data.get('success') is False


def test_profile_mapping_help():
    """Test profile-mapping subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'profile-mapping', '--help')
    assert result.success
    assert 'set' in result.stdout
    assert 'get' in result.stdout
    assert 'list' in result.stdout
    assert 'remove' in result.stdout
    assert 'batch-set' in result.stdout


def test_init_includes_profile_mappings():
    """Test init creates profile_mappings section."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        config_file = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        content = json.loads(config_file.read_text())

        assert 'profile_mappings' in content, 'Should have profile_mappings section'
        assert content['profile_mappings'] == {}, 'profile_mappings should be empty object'


def test_init_includes_extension_defaults():
    """Test init creates extension_defaults section."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        config_file = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        content = json.loads(config_file.read_text())

        assert 'extension_defaults' in content, 'Should have extension_defaults section'
        assert content['extension_defaults'] == {}, 'extension_defaults should be empty object'


# =============================================================================
# Extension Defaults Subcommand Tests (Generic key-value in extension_defaults)
# =============================================================================


def test_ext_defaults_set_adds_value():
    """Test extension-defaults set adds a new value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH,
            'extension-defaults',
            'set',
            '--key',
            'build.maven.profiles.ignore',
            '--value',
            '["itest", "native"]',
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'added'
        assert data.get('key') == 'build.maven.profiles.ignore'
        assert data.get('value') == ['itest', 'native']

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config.get('extension_defaults', {}).get('build.maven.profiles.ignore') == ['itest', 'native']


def test_ext_defaults_set_updates_existing():
    """Test extension-defaults set updates existing value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        # Create config with existing value
        config = {'version': 1, 'commands': {}, 'extension_defaults': {'my.key': 'old-value'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'set', '--key', 'my.key', '--value', '"new-value"')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'updated'
        assert data.get('previous') == 'old-value'
        assert data.get('value') == 'new-value'


def test_ext_defaults_set_json_array():
    """Test extension-defaults set with JSON array value."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'set', '--key', 'test.array', '--value', '[1, 2, 3]')

        data = result.json()
        assert data.get('success') is True
        assert data.get('value') == [1, 2, 3]


def test_ext_defaults_set_json_object():
    """Test extension-defaults set with JSON object value."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'extension-defaults', 'set', '--key', 'test.object', '--value', '{"foo": "bar", "num": 42}'
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('value') == {'foo': 'bar', 'num': 42}


def test_ext_defaults_set_plain_string():
    """Test extension-defaults set with plain string (non-JSON) value."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'extension-defaults', 'set', '--key', 'test.string', '--value', 'just a plain string'
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('value') == 'just a plain string'


def test_ext_defaults_get_existing():
    """Test extension-defaults get returns existing value."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'extension_defaults': {'my.key': ['value1', 'value2']}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'get', '--key', 'my.key')

        data = result.json()
        assert data.get('success') is True
        assert data.get('key') == 'my.key'
        assert data.get('exists') is True
        assert data.get('value') == ['value1', 'value2']


def test_ext_defaults_get_nonexistent():
    """Test extension-defaults get returns exists=false for missing key."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'get', '--key', 'nonexistent.key')

        data = result.json()
        assert data.get('success') is True
        assert data.get('key') == 'nonexistent.key'
        assert data.get('exists') is False
        assert 'value' not in data


def test_ext_defaults_set_default_adds_new():
    """Test extension-defaults set-default adds value when key doesn't exist."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'extension-defaults', 'set-default', '--key', 'new.key', '--value', '["a", "b"]'
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'added'
        assert data.get('value') == ['a', 'b']


def test_ext_defaults_set_default_skips_existing():
    """Test extension-defaults set-default skips when key already exists (write-once)."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'extension_defaults': {'existing.key': 'user-defined-value'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(
            SCRIPT_PATH, 'extension-defaults', 'set-default', '--key', 'existing.key', '--value', '"new-value"'
        )

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'skipped'
        assert data.get('reason') == 'Key already exists'
        assert data.get('existing_value') == 'user-defined-value'

        # Verify file was NOT updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['extension_defaults']['existing.key'] == 'user-defined-value'


def test_ext_defaults_list_all():
    """Test extension-defaults list returns all extension defaults."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'extension_defaults': {'key1': 'value1', 'key2': [1, 2, 3]}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'list')

        data = result.json()
        assert data.get('success') is True
        assert data.get('count') == 2
        assert 'key1' in data.get('keys', [])
        assert 'key2' in data.get('keys', [])
        assert data.get('values') == {'key1': 'value1', 'key2': [1, 2, 3]}


def test_ext_defaults_list_empty():
    """Test extension-defaults list with empty extension_defaults."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'list')

        data = result.json()
        assert data.get('success') is True
        assert data.get('count') == 0
        assert data.get('keys') == []


def test_ext_defaults_remove_existing():
    """Test extension-defaults remove removes existing key."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir / PLAN_DIR_NAME
        plan_dir.mkdir(parents=True)

        config = {'version': 1, 'commands': {}, 'extension_defaults': {'to.remove': 'value', 'to.keep': 'other'}}
        (plan_dir / 'run-configuration.json').write_text(json.dumps(config))

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'remove', '--key', 'to.remove')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'removed'
        assert data.get('previous') == 'value'

        # Verify file was updated
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert 'to.remove' not in config['extension_defaults']
        assert config['extension_defaults']['to.keep'] == 'other'


def test_ext_defaults_remove_nonexistent_skips():
    """Test extension-defaults remove skips non-existent key."""
    with PlanContext():
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'extension-defaults', 'remove', '--key', 'nonexistent')

        data = result.json()
        assert data.get('success') is True
        assert data.get('action') == 'skipped'


def test_ext_defaults_help():
    """Test extension-defaults subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'extension-defaults', '--help')
    assert result.success
    assert 'get' in result.stdout
    assert 'set' in result.stdout
    assert 'set-default' in result.stdout
    assert 'list' in result.stdout
    assert 'remove' in result.stdout


# =============================================================================
# Main
# =============================================================================
