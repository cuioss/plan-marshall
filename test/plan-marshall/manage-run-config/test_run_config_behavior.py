#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for run_config.py.

The existing manage-run-config suites drive the script through the ``run_script``
subprocess wrapper, which exercises behaviour but yields no coverage. This module
loads ``run_config`` in-process and calls its command handlers and pure helpers
directly so the config get/set/validation/persistence/migration paths and their
error branches are covered. Each test isolates ``run-configuration.json`` into a
tmp directory via the ``rc_env`` fixture (PLAN_BASE_DIR redirect + cleared
``file_ops`` override), mirroring the main-anchored resolver used in production.
"""

import argparse
import json
import sys

import pytest

from conftest import load_script_module

# In-process module handle (coverage counts; unique module name avoids clobbering
# the conftest-preimported ``run_config`` and the per-suite copy in
# ``test_run_config.py``).
run_config = load_script_module(
    'plan-marshall', 'manage-run-config', 'run_config.py', 'run_config_behavior_cov'
)


@pytest.fixture
def rc_env(tmp_path, monkeypatch):
    """Redirect run-configuration.json resolution into an isolated tmp directory.

    Sets ``PLAN_BASE_DIR`` to ``tmp_path`` and clears any leftover
    ``file_ops._BASE_DIR_OVERRIDE`` so ``get_run_config_path()`` resolves to
    ``tmp_path/run-configuration.json`` deterministically (the main-anchored
    resolver honours the override / env var first).
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('PLAN_DIR_NAME', '.plan')
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    return tmp_path


def _config_path():
    """Return the resolved run-configuration.json path under the active sandbox."""
    return run_config.get_run_config_path()


def _write_config(data):
    """Write ``data`` as JSON to the resolved run-configuration.json path."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


# =============================================================================
# init
# =============================================================================


def test_cmd_init_creates_new_config(rc_env):
    """cmd_init writes the default structure and reports 'created'."""
    result = run_config.cmd_init(argparse.Namespace(force=False))

    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert _config_path().exists()
    written = json.loads(_config_path().read_text())
    assert written['version'] == 1
    assert written['commands'] == {}


def test_cmd_init_skips_when_present_without_force(rc_env):
    """cmd_init returns 'skipped' when the file exists and --force is absent."""
    _write_config({'version': 1, 'commands': {'keep': {}}})

    result = run_config.cmd_init(argparse.Namespace(force=False))

    assert result['action'] == 'skipped'
    # The pre-existing content is untouched.
    assert json.loads(_config_path().read_text())['commands'] == {'keep': {}}


def test_cmd_init_force_overwrites_existing(rc_env):
    """cmd_init --force rewrites an existing file with the default structure."""
    _write_config({'version': 1, 'commands': {'stale': {}}})

    result = run_config.cmd_init(argparse.Namespace(force=True))

    assert result['status'] == 'success'
    assert result['action'] == 'recreated'
    assert 'stale' not in json.loads(_config_path().read_text())['commands']


def test_cmd_init_error_branch_returns_config_error(rc_env, monkeypatch):
    """cmd_init surfaces an error envelope when the path resolver raises."""
    monkeypatch.setattr(
        run_config, 'get_run_config_path', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
    )

    result = run_config.cmd_init(argparse.Namespace(force=False))

    assert result['status'] == 'error'
    assert result['error'] == 'config_error'
    assert 'boom' in result['message']


# =============================================================================
# validate_run_config / cmd_validate
# =============================================================================


def test_validate_run_config_flags_missing_required_fields():
    """validate_run_config reports the required-fields check as failed."""
    checks = run_config.validate_run_config({})

    required = next(c for c in checks if c['check'] == 'required_fields')
    assert required['passed'] is False
    assert 'version' in required['missing']
    assert 'commands' in required['missing']


def test_validate_run_config_flags_wrong_version_type():
    """validate_run_config flags a non-integer version."""
    checks = run_config.validate_run_config({'version': '1', 'commands': {}})

    version_check = next(c for c in checks if c['check'] == 'version_type')
    assert version_check['passed'] is False


def test_validate_run_config_flags_non_object_command_entry():
    """validate_run_config flags a command whose value is not an object."""
    checks = run_config.validate_run_config(
        {'version': 1, 'commands': {'bad': 'not-a-dict', 'good': {}}}
    )

    entries = next(c for c in checks if c['check'] == 'command_entries')
    assert entries['passed'] is False
    assert any('bad' in entry for entry in entries['invalid'])


def test_validate_run_config_accepts_valid_command_entries():
    """validate_run_config counts valid command entries when all are objects."""
    checks = run_config.validate_run_config(
        {'version': 1, 'commands': {'a': {}, 'b': {}}, 'maven': {}}
    )

    entries = next(c for c in checks if c['check'] == 'command_entries')
    assert entries['passed'] is True
    assert entries['count'] == 2
    assert any(c['check'] == 'maven_object' for c in checks)


def test_cmd_validate_file_not_found_returns_error(rc_env, tmp_path):
    """cmd_validate returns a config_error when the target file is absent."""
    result = run_config.cmd_validate(argparse.Namespace(file=str(tmp_path / 'absent.json')))

    assert result['status'] == 'error'
    assert 'File not found' in result['message']


def test_cmd_validate_invalid_json_reports_syntax_failure(rc_env, tmp_path):
    """cmd_validate marks invalid JSON as not valid via the json_syntax check."""
    bad = tmp_path / 'bad.json'
    bad.write_text('{ not json')

    result = run_config.cmd_validate(argparse.Namespace(file=str(bad)))

    assert result['status'] == 'success'
    assert result['valid'] is False
    assert result['checks'][0]['check'] == 'json_syntax'
    assert result['checks'][0]['passed'] is False


def test_cmd_validate_valid_file_reports_valid(rc_env, tmp_path):
    """cmd_validate marks a well-formed config as valid."""
    good = tmp_path / 'good.json'
    good.write_text(json.dumps({'version': 1, 'commands': {}}))

    result = run_config.cmd_validate(argparse.Namespace(file=str(good)))

    assert result['valid'] is True
    assert result['format'] == 'manage-run-config'


# =============================================================================
# read_run_config / timeout helpers
# =============================================================================


def test_read_run_config_returns_default_when_absent(rc_env, tmp_path):
    """read_run_config falls back to the baseline default for a missing file."""
    config = run_config.read_run_config(tmp_path / 'nope.json')

    assert config == {'version': 1, 'commands': {}}


def test_compute_weighted_timeout_favors_higher_value():
    """compute_weighted_timeout weights the larger of the two values by 0.8."""
    # Higher=300, lower=100 -> 0.8*300 + 0.2*100 = 260, regardless of arg order.
    assert run_config.compute_weighted_timeout(300, 100) == 260
    assert run_config.compute_weighted_timeout(100, 300) == 260


def test_timeout_get_returns_default_when_not_persisted(rc_env):
    """timeout_get returns the supplied default when no value is persisted."""
    assert run_config.timeout_get('ci:checks', 300) == 300


def test_timeout_get_applies_safety_margin(rc_env):
    """timeout_get scales a persisted value by the 1.25 safety margin."""
    _write_config({'version': 1, 'commands': {'ci:checks': {'timeout_seconds': 240}}})

    # 240 * 1.25 = 300.
    assert run_config.timeout_get('ci:checks', 60) == 300


def test_timeout_get_enforces_minimum_floor(rc_env):
    """timeout_get never returns below the 120 s minimum floor."""
    _write_config({'version': 1, 'commands': {'fast': {'timeout_seconds': 10}}})

    # 10 * 1.25 = 12.5 -> below the 120 floor.
    assert run_config.timeout_get('fast', 30) == 120


def test_cmd_timeout_get_wraps_value(rc_env):
    """cmd_timeout_get returns the resolved timeout in a success envelope."""
    result = run_config.cmd_timeout_get(argparse.Namespace(command='ci:checks', default=300))

    assert result['status'] == 'success'
    assert result['command'] == 'ci:checks'
    assert result['timeout_seconds'] == 300


def test_cmd_timeout_set_initial_then_weighted(rc_env):
    """cmd_timeout_set writes the raw duration first, then weights subsequent updates."""
    first = run_config.cmd_timeout_set(argparse.Namespace(command='build', duration=240))
    assert first['source'] == 'initial'
    assert first['timeout_seconds'] == 240

    second = run_config.cmd_timeout_set(argparse.Namespace(command='build', duration=180))
    assert second['source'] == 'computed'
    # 0.8*240 + 0.2*180 = 228.
    assert second['timeout_seconds'] == 228
    assert second['previous_seconds'] == 240


def test_cmd_timeout_set_error_branch(rc_env, monkeypatch):
    """cmd_timeout_set surfaces a config_error when persistence fails."""
    monkeypatch.setattr(
        run_config, 'get_run_config_path', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('io'))
    )

    result = run_config.cmd_timeout_set(argparse.Namespace(command='x', duration=1))

    assert result['status'] == 'error'
    assert 'io' in result['message']


# =============================================================================
# warning subcommands
# =============================================================================


def test_get_acceptable_warnings_reads_nested_section():
    """get_acceptable_warnings returns the acceptable_warnings block for a system."""
    config = {'maven': {'acceptable_warnings': {'platform_specific': ['x']}}}

    assert run_config.get_acceptable_warnings(config, 'maven') == {'platform_specific': ['x']}
    # Missing build system yields an empty mapping.
    assert run_config.get_acceptable_warnings(config, 'gradle') == {}


def test_cmd_warning_add_creates_structure_and_appends(rc_env):
    """cmd_warning_add materialises the warnings structure and stores the pattern."""
    _write_config({'version': 1, 'commands': {}})

    result = run_config.cmd_warning_add(
        argparse.Namespace(
            category='transitive_dependency',
            pattern='uses transitive dependency',
            build_system='maven',
        )
    )

    assert result['action'] == 'added'
    stored = json.loads(_config_path().read_text())
    assert 'uses transitive dependency' in stored['maven']['acceptable_warnings']['transitive_dependency']


def test_cmd_warning_add_duplicate_is_skipped(rc_env):
    """cmd_warning_add reports 'skipped' for an already-present pattern."""
    _write_config(
        {
            'version': 1,
            'commands': {},
            'maven': {'acceptable_warnings': {'platform_specific': ['dup']}},
        }
    )

    result = run_config.cmd_warning_add(
        argparse.Namespace(category='platform_specific', pattern='dup', build_system='maven')
    )

    assert result['action'] == 'skipped'


def test_cmd_warning_add_rejects_invalid_category(rc_env):
    """cmd_warning_add returns an error for a category outside the valid set."""
    _write_config({'version': 1, 'commands': {}})

    result = run_config.cmd_warning_add(
        argparse.Namespace(category='bogus', pattern='p', build_system='maven')
    )

    assert result['status'] == 'error'
    assert 'Invalid category' in result['message']


def test_cmd_warning_list_all_categories(rc_env):
    """cmd_warning_list returns every valid category when no filter is given."""
    _write_config(
        {
            'version': 1,
            'commands': {},
            'maven': {'acceptable_warnings': {'transitive_dependency': ['a']}},
        }
    )

    result = run_config.cmd_warning_list(argparse.Namespace(category=None, build_system='maven'))

    assert result['status'] == 'success'
    assert result['categories']['transitive_dependency'] == ['a']
    for cat in run_config.VALID_WARNING_CATEGORIES:
        assert cat in result['categories']


def test_cmd_warning_list_single_category(rc_env):
    """cmd_warning_list returns only the requested category's patterns."""
    _write_config(
        {
            'version': 1,
            'commands': {},
            'maven': {'acceptable_warnings': {'plugin_compatibility': ['c']}},
        }
    )

    result = run_config.cmd_warning_list(
        argparse.Namespace(category='plugin_compatibility', build_system='maven')
    )

    assert result['category'] == 'plugin_compatibility'
    assert result['patterns'] == ['c']


def test_cmd_warning_list_invalid_category_errors(rc_env):
    """cmd_warning_list rejects a filter category outside the valid set."""
    _write_config({'version': 1, 'commands': {}})

    result = run_config.cmd_warning_list(argparse.Namespace(category='bogus', build_system='maven'))

    assert result['status'] == 'error'


def test_cmd_warning_remove_existing_pattern(rc_env):
    """cmd_warning_remove deletes a stored pattern and reports 'removed'."""
    _write_config(
        {
            'version': 1,
            'commands': {},
            'maven': {'acceptable_warnings': {'platform_specific': ['x', 'y']}},
        }
    )

    result = run_config.cmd_warning_remove(
        argparse.Namespace(category='platform_specific', pattern='x', build_system='maven')
    )

    assert result['action'] == 'removed'
    remaining = json.loads(_config_path().read_text())['maven']['acceptable_warnings']['platform_specific']
    assert remaining == ['y']


def test_cmd_warning_remove_missing_pattern_skips(rc_env):
    """cmd_warning_remove reports 'skipped' when the pattern is absent."""
    _write_config(
        {
            'version': 1,
            'commands': {},
            'maven': {'acceptable_warnings': {'platform_specific': []}},
        }
    )

    result = run_config.cmd_warning_remove(
        argparse.Namespace(category='platform_specific', pattern='ghost', build_system='maven')
    )

    assert result['action'] == 'skipped'


def test_cmd_warning_remove_invalid_category_errors(rc_env):
    """cmd_warning_remove rejects an invalid category."""
    _write_config({'version': 1, 'commands': {}})

    result = run_config.cmd_warning_remove(
        argparse.Namespace(category='bogus', pattern='p', build_system='maven')
    )

    assert result['status'] == 'error'


# =============================================================================
# architecture-refresh knobs
# =============================================================================


def test_architecture_refresh_tier_0_default_when_absent(rc_env):
    """get-tier-0 returns the 'enabled' default when the section is absent."""
    result = run_config.cmd_architecture_refresh_get_tier_0(argparse.Namespace())

    assert result['field'] == 'tier_0'
    assert result['value'] == 'enabled'


def test_architecture_refresh_tier_0_set_then_get(rc_env):
    """set-tier-0 persists a value that get-tier-0 reads back."""
    run_config.cmd_architecture_refresh_set_tier_0(argparse.Namespace(value='disabled'))

    stored = json.loads(_config_path().read_text())
    assert stored['architecture_refresh']['tier_0'] == 'disabled'
    assert run_config.cmd_architecture_refresh_get_tier_0(argparse.Namespace())['value'] == 'disabled'


def test_architecture_refresh_set_tier_0_rejects_unknown(rc_env):
    """set-tier-0 returns an invalid_value error for an out-of-enum value."""
    result = run_config.cmd_architecture_refresh_set_tier_0(argparse.Namespace(value='maybe'))

    assert result['error'] == 'invalid_value'
    assert 'enabled' in result['allowed']


def test_architecture_refresh_tier_1_default_and_set(rc_env):
    """tier-1 defaults to 'prompt' and round-trips an explicit value."""
    assert run_config.cmd_architecture_refresh_get_tier_1(argparse.Namespace())['value'] == 'prompt'

    run_config.cmd_architecture_refresh_set_tier_1(argparse.Namespace(value='auto'))
    assert run_config.cmd_architecture_refresh_get_tier_1(argparse.Namespace())['value'] == 'auto'


def test_architecture_refresh_set_tier_1_rejects_unknown(rc_env):
    """set-tier-1 returns invalid_value for a value outside its enum."""
    result = run_config.cmd_architecture_refresh_set_tier_1(argparse.Namespace(value='enabled'))

    assert result['error'] == 'invalid_value'


def test_read_architecture_refresh_value_ignores_non_string(rc_env):
    """_read_architecture_refresh_value falls back to default for non-string stored values."""
    _write_config({'version': 1, 'commands': {}, 'architecture_refresh': {'tier_0': 123}})

    value = run_config._read_architecture_refresh_value('tier_0', 'enabled')

    assert value == 'enabled'


# =============================================================================
# build-queue-limit knob
# =============================================================================


def test_clamp_build_queue_upper_limit_bounds():
    """_clamp_build_queue_upper_limit pins values into the [600, 3600] range."""
    assert run_config._clamp_build_queue_upper_limit(100) == 600
    assert run_config._clamp_build_queue_upper_limit(99999) == 3600
    assert run_config._clamp_build_queue_upper_limit(1800) == 1800


def test_read_build_queue_upper_limit_default_when_absent(rc_env):
    """_read_build_queue_upper_limit returns the 600 s floor when unset."""
    assert run_config._read_build_queue_upper_limit() == 600


def test_read_build_queue_upper_limit_non_dict_build(rc_env):
    """_read_build_queue_upper_limit floors when 'build' is not a mapping."""
    _write_config({'version': 1, 'commands': {}, 'build': 'oops'})

    assert run_config._read_build_queue_upper_limit() == 600


def test_read_build_queue_upper_limit_non_dict_queue(rc_env):
    """_read_build_queue_upper_limit floors when 'build.queue' is not a mapping."""
    _write_config({'version': 1, 'commands': {}, 'build': {'queue': 5}})

    assert run_config._read_build_queue_upper_limit() == 600


def test_read_build_queue_upper_limit_rejects_bool(rc_env):
    """_read_build_queue_upper_limit floors when the stored value is a bool."""
    _write_config({'version': 1, 'commands': {}, 'build': {'queue': {'upper_limit_seconds': True}}})

    assert run_config._read_build_queue_upper_limit() == 600


def test_read_build_queue_upper_limit_clamps_stored_value(rc_env):
    """_read_build_queue_upper_limit clamps an out-of-range stored value."""
    _write_config(
        {'version': 1, 'commands': {}, 'build': {'queue': {'upper_limit_seconds': 99999}}}
    )

    assert run_config._read_build_queue_upper_limit() == 3600


def test_cmd_build_queue_limit_get_default(rc_env):
    """cmd_build_queue_limit_get returns the floor default in a success envelope."""
    result = run_config.cmd_build_queue_limit_get(argparse.Namespace())

    assert result['field'] == 'build_queue_upper_limit'
    assert result['value'] == 600


def test_cmd_build_queue_limit_set_clamps_and_persists(rc_env):
    """cmd_build_queue_limit_set stores a clamped value and reports it."""
    result = run_config.cmd_build_queue_limit_set(argparse.Namespace(value=1800))

    assert result['value'] == 1800
    stored = json.loads(_config_path().read_text())
    assert stored['build']['queue']['upper_limit_seconds'] == 1800


def test_cmd_build_queue_limit_set_rejects_non_positive(rc_env):
    """cmd_build_queue_limit_set rejects a value <= 0 with invalid_value."""
    result = run_config.cmd_build_queue_limit_set(argparse.Namespace(value=0))

    assert result['error'] == 'invalid_value'


# =============================================================================
# main() dispatch — covers the argparse construction + routing
# =============================================================================


def test_main_init_dispatch(rc_env, monkeypatch, capsys):
    """main() routes the 'init' subcommand and emits a TOON success line."""
    monkeypatch.setattr(sys, 'argv', ['run_config', 'init'])

    rc = run_config.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert _config_path().exists()


def test_main_validate_dispatch(rc_env, monkeypatch, capsys, tmp_path):
    """main() routes 'validate' against an explicit --file."""
    cfg = tmp_path / 'cfg.json'
    cfg.write_text(json.dumps({'version': 1, 'commands': {}}))
    monkeypatch.setattr(sys, 'argv', ['run_config', 'validate', '--file', str(cfg)])

    rc = run_config.main()

    assert rc == 0
    assert 'valid: true' in capsys.readouterr().out


def test_main_timeout_get_dispatch(rc_env, monkeypatch, capsys):
    """main() routes the nested 'timeout get' subcommand."""
    monkeypatch.setattr(
        sys, 'argv', ['run_config', 'timeout', 'get', '--command', 'x', '--default', '300']
    )

    rc = run_config.main()

    assert rc == 0
    assert 'timeout_seconds: 300' in capsys.readouterr().out


def test_main_build_queue_limit_get_dispatch(rc_env, monkeypatch, capsys):
    """main() routes the nested 'build-queue-limit get' subcommand."""
    monkeypatch.setattr(sys, 'argv', ['run_config', 'build-queue-limit', 'get'])

    rc = run_config.main()

    assert rc == 0
    assert 'build_queue_upper_limit' in capsys.readouterr().out
