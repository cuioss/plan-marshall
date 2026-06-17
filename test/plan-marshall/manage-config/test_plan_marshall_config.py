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
)

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_ext_defaults = _load_module('_cmd_ext_defaults', '_cmd_ext_defaults.py')
_cmd_init_mod = _load_module('_cmd_init', '_cmd_init.py')
_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')
_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_ext_defaults = _cmd_ext_defaults.cmd_ext_defaults
cmd_init = _cmd_init_mod.cmd_init
cmd_skill_domains = _cmd_skill_domains.cmd_skill_domains
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills
cmd_plan = _cmd_system_plan.cmd_plan
cmd_system = _cmd_system_plan.cmd_system

from conftest import run_script  # noqa: E402

# =============================================================================
# Happy-Path Integration Tests (Tier 2 - direct import)
# =============================================================================


def test_init_creates_marshal_json(plan_context, monkeypatch):
    """Test init creates marshal.json with defaults."""
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists(), 'marshal.json should be created'


def test_skill_domains_list(plan_context, monkeypatch):
    """Test skill-domains list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='list'))

    assert result['status'] == 'success'
    assert 'java' in result['domains']


def test_skill_domains_get(plan_context, monkeypatch):
    """Test skill-domains get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get', domain='java'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:java-core' in result['defaults']


def test_system_retention_get(plan_context, monkeypatch):
    """Test system retention get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='get'))

    assert result['status'] == 'success'
    assert 'logs_days' in result['retention']


def test_plan_phase_5_execute_get(plan_context, monkeypatch):
    """Test plan phase-5-execute get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'commit_and_push' in result


def test_plan_phase_6_finalize_get(plan_context, monkeypatch):
    """Test plan phase-6-finalize get returns config including the keyed-map steps."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='get', field=None))

    assert result['status'] == 'success'
    # steps is the id-keyed map; pr_merge_strategy is a nested param under
    # default:branch-cleanup (the default config seeds it there).
    assert 'default:branch-cleanup' in result['steps']
    assert result['steps']['default:branch-cleanup']['pr_merge_strategy'] == 'squash'


def test_plan_phase_6_finalize_step_get_pr_merge_strategy(plan_context, monkeypatch):
    """Test plan phase-6-finalize step get --step-id default:branch-cleanup yields pr_merge_strategy."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:branch-cleanup',
        )
    )

    assert result['status'] == 'success'
    assert result['params']['pr_merge_strategy'] == 'squash'


def test_plan_phase_6_finalize_step_set_pr_merge_strategy(plan_context, monkeypatch):
    """Test plan phase-6-finalize step set writes pr_merge_strategy and round-trips via step get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:branch-cleanup',
            param='pr_merge_strategy',
            value='rebase',
        )
    )

    assert result['status'] == 'success'
    assert result['params']['pr_merge_strategy'] == 'rebase'

    # Verify persisted via step get
    result2 = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:branch-cleanup',
        )
    )
    assert result2['params']['pr_merge_strategy'] == 'rebase'


def test_resolve_domain_skills(plan_context, monkeypatch):
    """Test resolve-domain-skills command."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:java-core' in result['defaults']


def test_error_without_marshal_json(plan_context, monkeypatch):
    """Test operations fail gracefully without marshal.json."""
    # Don't create marshal.json

    result = cmd_skill_domains(Namespace(verb='list'))

    assert result['status'] == 'error'


# CI tests removed — CI config now owned by tools-integration-ci/ci_health.py
# See test/plan-marshall/tools-integration-ci/test_ci_health.py


# =============================================================================
# Extension Defaults Tests (Tier 2 - direct import)
# =============================================================================


def test_ext_defaults_set_adds_value(plan_context, monkeypatch):
    """Test ext-defaults set adds a value."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='set', key='test.key', value='test-value'))

    assert result['status'] == 'success'
    assert result['key'] == 'test.key'


def test_ext_defaults_set_updates_existing(plan_context, monkeypatch):
    """Test ext-defaults set overwrites existing value."""
    create_marshal_json(plan_context.fixture_dir)

    # Set initial value
    cmd_ext_defaults(Namespace(verb='set', key='test.key', value='initial'))

    # Update value
    result = cmd_ext_defaults(Namespace(verb='set', key='test.key', value='updated'))

    assert result['status'] == 'success'
    assert result['value'] == 'updated'


def test_ext_defaults_set_json_array(plan_context, monkeypatch):
    """Test ext-defaults set with JSON array value."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='set', key='test.array', value='["a","b","c"]'))

    assert result['status'] == 'success'


def test_ext_defaults_set_json_object(plan_context, monkeypatch):
    """Test ext-defaults set with JSON object value."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='set', key='test.obj', value='{"nested": true}'))

    assert result['status'] == 'success'


def test_ext_defaults_set_plain_string(plan_context, monkeypatch):
    """Test ext-defaults set with plain string (not JSON)."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='set', key='test.str', value='hello-world'))

    assert result['status'] == 'success'
    assert result['value'] == 'hello-world'


def test_ext_defaults_get_existing(plan_context, monkeypatch):
    """Test ext-defaults get retrieves existing value."""
    create_marshal_json(plan_context.fixture_dir)
    cmd_ext_defaults(Namespace(verb='set', key='my.key', value='my-value'))

    result = cmd_ext_defaults(Namespace(verb='get', key='my.key'))

    assert result['status'] == 'success'
    assert result['value'] == 'my-value'


def test_ext_defaults_get_nonexistent(plan_context, monkeypatch):
    """Test ext-defaults get returns not_found for missing key."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='get', key='nonexistent'))

    assert result['status'] == 'not_found'


def test_ext_defaults_set_default_adds_new(plan_context, monkeypatch):
    """Test ext-defaults set-default adds value when key doesn't exist."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='set-default', key='new.key', value='new-value'))

    assert result['status'] == 'success'
    assert result['value'] == 'new-value'


def test_ext_defaults_set_default_skips_existing(plan_context, monkeypatch):
    """Test ext-defaults set-default skips when key exists."""
    create_marshal_json(plan_context.fixture_dir)
    cmd_ext_defaults(Namespace(verb='set', key='existing.key', value='original'))

    result = cmd_ext_defaults(Namespace(verb='set-default', key='existing.key', value='new'))

    assert result['status'] == 'skipped'
    assert result['reason'] == 'key_exists'


def test_ext_defaults_list_all(plan_context, monkeypatch):
    """Test ext-defaults list shows all values."""
    create_marshal_json(plan_context.fixture_dir)
    cmd_ext_defaults(Namespace(verb='set', key='key1', value='value1'))
    cmd_ext_defaults(Namespace(verb='set', key='key2', value='value2'))

    result = cmd_ext_defaults(Namespace(verb='list'))

    assert result['status'] == 'success'
    assert 'key1' in result['extension_defaults']
    assert 'key2' in result['extension_defaults']


def test_ext_defaults_list_empty(plan_context, monkeypatch):
    """Test ext-defaults list with no values."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_ext_defaults(Namespace(verb='list'))

    assert result['status'] == 'success'
    assert result['count'] == 0


def test_ext_defaults_remove_existing(plan_context, monkeypatch):
    """Test ext-defaults remove deletes existing key."""
    create_marshal_json(plan_context.fixture_dir)
    cmd_ext_defaults(Namespace(verb='set', key='to.remove', value='value'))

    result = cmd_ext_defaults(Namespace(verb='remove', key='to.remove'))

    assert result['status'] == 'success'
    assert result['action'] == 'removed'


def test_ext_defaults_remove_nonexistent_skips(plan_context, monkeypatch):
    """Test ext-defaults remove skips non-existent key."""
    create_marshal_json(plan_context.fixture_dir)

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


# test_cli_ci_get removed — CI config now owned by tools-integration-ci


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
    domain = {'defaults': ['plan-marshall:dev-agent-behavior-rules'], 'optionals': ['plan-marshall:dev-agent-behavior-rules']}
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


def test_dev_agent_behavior_rules_not_in_system_domain():
    """dev-agent-behavior-rules must not be in system defaults or optionals.

    Each phase skill and agent loads it explicitly via Skill: directive,
    so the global system domain entry is redundant.
    """
    system = _config_defaults.DEFAULT_SYSTEM_DOMAIN
    all_skills = system.get('defaults', []) + system.get('optionals', [])
    assert 'plan-marshall:dev-agent-behavior-rules' not in all_skills, (
        'dev-agent-behavior-rules should not be in system domain — loaded explicitly by each phase skill and agent'
    )


# =============================================================================
# Main
# =============================================================================
