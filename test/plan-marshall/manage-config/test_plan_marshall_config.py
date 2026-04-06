#!/usr/bin/env python3
"""Integration tests for manage-config.py script.

Happy-path tests verifying the monolithic CLI API.
Detailed variant and corner case tests are in:
- test_cmd_init.py
- test_cmd_skill_domains.py
- test_cmd_system_plan.py

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import (
    SCRIPT_PATH,
    create_marshal_json,
    create_nested_marshal_json,
    create_run_config,
    patch_config_paths,
)

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_ci = _load_module('_cmd_ci', '_cmd_ci.py')
_cmd_ext_defaults = _load_module('_cmd_ext_defaults', '_cmd_ext_defaults.py')
_cmd_init_mod = _load_module('_cmd_init', '_cmd_init.py')
_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')
_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_ci = _cmd_ci.cmd_ci
cmd_ext_defaults = _cmd_ext_defaults.cmd_ext_defaults
cmd_init = _cmd_init_mod.cmd_init
cmd_skill_domains = _cmd_skill_domains.cmd_skill_domains
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills
cmd_plan = _cmd_system_plan.cmd_plan
cmd_system = _cmd_system_plan.cmd_system

from conftest import PlanContext, run_script  # noqa: E402

# =============================================================================
# Happy-Path Integration Tests (Tier 2 - direct import)
# =============================================================================


def test_init_creates_marshal_json():
    """Test init creates marshal.json with defaults."""
    with PlanContext() as ctx:
        patch_config_paths(ctx.fixture_dir)

        result = cmd_init(Namespace(force=False))

        assert result['status'] == 'success'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        assert marshal_path.exists(), 'marshal.json should be created'


def test_skill_domains_list():
    """Test skill-domains list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='list'))

        assert result['status'] == 'success'
        assert 'java' in result['domains']


def test_skill_domains_get():
    """Test skill-domains get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:java-core' in result['defaults']


def test_system_retention_get():
    """Test system retention get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_system(Namespace(sub_noun='retention', verb='get'))

        assert result['status'] == 'success'
        assert 'logs_days' in result['retention']


def test_plan_phase_5_execute_get():
    """Test plan phase-5-execute get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

        assert result['status'] == 'success'
        assert 'commit_strategy' in result


def test_resolve_domain_skills():
    """Test resolve-domain-skills command."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:java-core' in result['defaults']


def test_error_without_marshal_json():
    """Test operations fail gracefully without marshal.json."""
    with PlanContext() as ctx:
        patch_config_paths(ctx.fixture_dir)
        # Don't create marshal.json

        result = cmd_skill_domains(Namespace(verb='list'))

        assert result['status'] == 'error'


def test_ci_get():
    """Test ci get returns full CI config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ci(Namespace(verb='get'))

        assert result['status'] == 'success'
        assert 'ci' in result
        assert result['ci']['provider'] == 'github'
        assert 'repo_url' in result['ci']


def test_ci_get_provider():
    """Test ci get-provider returns provider info."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ci(Namespace(verb='get-provider'))

        assert result['status'] == 'success'
        assert result['provider'] == 'github'


def test_ci_get_tools():
    """Test ci get-tools returns authenticated tools from run-configuration.json."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        create_run_config(ctx.fixture_dir)  # Tools are stored in run-configuration.json
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ci(Namespace(verb='get-tools'))

        assert result['status'] == 'success'
        assert 'git' in result['authenticated_tools']
        assert 'gh' in result['authenticated_tools']


def test_ci_set_provider():
    """Test ci set-provider updates provider."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ci(Namespace(
            verb='set-provider',
            provider='gitlab',
            repo_url='https://gitlab.com/test/repo',
        ))

        assert result['status'] == 'success'
        assert result['provider'] == 'gitlab'


def test_ci_set_tools():
    """Test ci set-tools updates authenticated tools."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ci(Namespace(verb='set-tools', tools='git,glab,python3'))

        assert result['status'] == 'success'
        assert 'glab' in result['authenticated_tools']


# =============================================================================
# Extension Defaults Tests (Tier 2 - direct import)
# =============================================================================


def test_ext_defaults_set_adds_value():
    """Test ext-defaults set adds a value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='set', key='test.key', value='test-value'))

        assert result['status'] == 'success'
        assert result['key'] == 'test.key'


def test_ext_defaults_set_updates_existing():
    """Test ext-defaults set overwrites existing value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        # Set initial value
        cmd_ext_defaults(Namespace(verb='set', key='test.key', value='initial'))

        # Update value
        result = cmd_ext_defaults(Namespace(verb='set', key='test.key', value='updated'))

        assert result['status'] == 'success'
        assert result['value'] == 'updated'


def test_ext_defaults_set_json_array():
    """Test ext-defaults set with JSON array value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='set', key='test.array', value='["a","b","c"]'))

        assert result['status'] == 'success'


def test_ext_defaults_set_json_object():
    """Test ext-defaults set with JSON object value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='set', key='test.obj', value='{"nested": true}'))

        assert result['status'] == 'success'


def test_ext_defaults_set_plain_string():
    """Test ext-defaults set with plain string (not JSON)."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='set', key='test.str', value='hello-world'))

        assert result['status'] == 'success'
        assert result['value'] == 'hello-world'


def test_ext_defaults_get_existing():
    """Test ext-defaults get retrieves existing value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)
        cmd_ext_defaults(Namespace(verb='set', key='my.key', value='my-value'))

        result = cmd_ext_defaults(Namespace(verb='get', key='my.key'))

        assert result['status'] == 'success'
        assert result['value'] == 'my-value'


def test_ext_defaults_get_nonexistent():
    """Test ext-defaults get returns not_found for missing key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='get', key='nonexistent'))

        assert result['status'] == 'not_found'


def test_ext_defaults_set_default_adds_new():
    """Test ext-defaults set-default adds value when key doesn't exist."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='set-default', key='new.key', value='new-value'))

        assert result['status'] == 'success'
        assert result['value'] == 'new-value'


def test_ext_defaults_set_default_skips_existing():
    """Test ext-defaults set-default skips when key exists."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)
        cmd_ext_defaults(Namespace(verb='set', key='existing.key', value='original'))

        result = cmd_ext_defaults(Namespace(verb='set-default', key='existing.key', value='new'))

        assert result['status'] == 'skipped'
        assert result['reason'] == 'key_exists'


def test_ext_defaults_list_all():
    """Test ext-defaults list shows all values."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)
        cmd_ext_defaults(Namespace(verb='set', key='key1', value='value1'))
        cmd_ext_defaults(Namespace(verb='set', key='key2', value='value2'))

        result = cmd_ext_defaults(Namespace(verb='list'))

        assert result['status'] == 'success'
        assert 'key1' in result['extension_defaults']
        assert 'key2' in result['extension_defaults']


def test_ext_defaults_list_empty():
    """Test ext-defaults list with no values."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='list'))

        assert result['status'] == 'success'
        assert result['count'] == 0


def test_ext_defaults_remove_existing():
    """Test ext-defaults remove deletes existing key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)
        cmd_ext_defaults(Namespace(verb='set', key='to.remove', value='value'))

        result = cmd_ext_defaults(Namespace(verb='remove', key='to.remove'))

        assert result['status'] == 'success'
        assert result['action'] == 'removed'


def test_ext_defaults_remove_nonexistent_skips():
    """Test ext-defaults remove skips non-existent key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_ext_defaults(Namespace(verb='remove', key='nonexistent'))

        assert result['status'] == 'skipped'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_help_output():
    """Test --help outputs usage information."""
    result = run_script(SCRIPT_PATH, '--help')

    assert result.success, 'Help should succeed'
    assert 'skill-domains' in result.stdout
    assert 'ci' in result.stdout


def test_cli_ext_defaults_help():
    """Test ext-defaults --help shows usage."""
    result = run_script(SCRIPT_PATH, 'ext-defaults', '--help')

    assert result.success, 'Help should succeed'
    assert 'get' in result.stdout
    assert 'set' in result.stdout
    assert 'set-default' in result.stdout


def test_cli_ci_get():
    """Test CLI plumbing: ci get outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ci', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'github' in result.stdout


# =============================================================================
# Domain Invariant Validation Tests
# =============================================================================

_config_defaults = _load_module('_config_defaults', '_config_defaults.py')


def test_validate_domain_invariants_no_overlap():
    """Validation passes when defaults and optionals have no overlap."""
    domain = {'defaults': ['a'], 'optionals': ['b']}
    _config_defaults.validate_domain_invariants(domain)


def test_validate_domain_invariants_overlap_raises():
    """Validation raises ValueError when defaults and optionals overlap."""
    domain = {'defaults': ['plan-marshall:dev-general-practices'], 'optionals': ['plan-marshall:dev-general-practices']}
    import pytest
    with pytest.raises(ValueError, match='must not appear in both defaults and optionals'):
        _config_defaults.validate_domain_invariants(domain)


def test_default_system_domain_no_overlap():
    """DEFAULT_SYSTEM_DOMAIN must not have overlapping defaults and optionals."""
    _config_defaults.validate_domain_invariants(_config_defaults.DEFAULT_SYSTEM_DOMAIN)


def test_get_default_config_validates_invariants():
    """get_default_config runs invariant validation on system domain."""
    config = _config_defaults.get_default_config()
    system = config['skill_domains']['system']
    defaults = set(system.get('defaults', []))
    optionals = set(system.get('optionals', []))
    assert not (defaults & optionals), 'defaults and optionals must not overlap'


# =============================================================================
# Main
# =============================================================================
