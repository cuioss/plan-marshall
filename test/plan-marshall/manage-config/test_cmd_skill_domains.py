#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for skill-domains commands in manage-config.

Tests skill-domains and list-verify-steps commands defined in _cmd_skill_domains.py,
including nested structure variants and edge cases.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

import importlib.util
import json
import os
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json

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


_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')

cmd_list_verify_steps = _cmd_skill_domains.cmd_list_verify_steps
cmd_skill_domains = _cmd_skill_domains.cmd_skill_domains

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402

_VERIFY_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-verify-step'


def _expected_verify_step_ids() -> list[str]:
    """Return the built-in verify-step ids the rerouted discovery must produce.

    Mirrors ``_config_defaults._verify_step_ids`` — the SOLE discovery path:
    filter the ``ext-point-verify-step`` implementors to the built-in source,
    sort by ``(order, name)``, and expand each implementor's ``canonicals`` list
    into ``default:verify:{canonical}`` ids in list order. The removed
    ``BUILT_IN_VERIFY_STEPS`` constant is gone; this is its discovery-derived
    replacement.
    """
    from extension_discovery import find_implementors  # type: ignore[import-not-found]

    built_in = sorted(
        (rec for rec in find_implementors(_VERIFY_STEP_EXT_POINT) if rec.get('source') == 'built-in'),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [
        f'default:verify:{canonical}'
        for rec in built_in
        for canonical in rec.get('canonicals', [])
    ]


# =============================================================================
# skill-domains Basic Tests (Flat Structure) - Tier 2
# =============================================================================


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


def test_skill_domains_get_defaults(plan_context, monkeypatch):
    """Test skill-domains get-defaults."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-defaults', domain='java'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:java-core' in result['defaults']


def test_skill_domains_get_optionals(plan_context, monkeypatch):
    """Test skill-domains get-optionals."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-optionals', domain='java'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:java-cdi' in result['optionals']


def test_skill_domains_unknown_domain(plan_context, monkeypatch):
    """Test skill-domains get with unknown domain returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get', domain='unknown'))

    assert result['status'] == 'error'
    assert 'unknown' in result['error'].lower()


def test_skill_domains_add(plan_context, monkeypatch):
    """Test skill-domains add."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='add',
            domain='python',
            defaults='pm-dev-python:cui-python-core',
            optionals=None,
        )
    )

    assert result['status'] == 'success'

    # Verify added
    verify = cmd_skill_domains(Namespace(verb='get', domain='python'))
    assert 'pm-dev-python:cui-python-core' in verify['defaults']


def test_skill_domains_validate(plan_context, monkeypatch):
    """Test skill-domains validate."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='validate',
            domain='java',
            skill='pm-dev-java:java-core',
        )
    )

    assert result['status'] == 'success'
    assert result['valid'] is True


def test_skill_domains_validate_returns_location(plan_context, monkeypatch):
    """Test skill-domains validate returns in_defaults or in_optionals."""
    create_marshal_json(plan_context.fixture_dir)

    # Skill in defaults
    result_defaults = cmd_skill_domains(
        Namespace(
            verb='validate',
            domain='java',
            skill='pm-dev-java:java-core',
        )
    )
    assert result_defaults['in_defaults'] is True

    # Skill in optionals
    result_optionals = cmd_skill_domains(
        Namespace(
            verb='validate',
            domain='java',
            skill='pm-dev-java:java-cdi',
        )
    )
    assert result_optionals['in_optionals'] is True


def test_skill_domains_validate_invalid_skill(plan_context, monkeypatch):
    """Test skill-domains validate with invalid skill returns false."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='validate',
            domain='java',
            skill='pm-dev-java:invalid-skill',
        )
    )

    assert result['status'] == 'success'
    assert result['valid'] is False


# =============================================================================
# skill-domains Nested Structure Tests (Tier 2)
# =============================================================================


def test_skill_domains_get_nested_structure(plan_context, monkeypatch):
    """Test skill-domains get returns nested structure for domains with bundle reference."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get', domain='java'))

    assert result['status'] == 'success'
    assert 'bundle' in result
    assert result['bundle'] == 'pm-dev-java'
    assert 'workflow_skill_extensions' in result


def test_skill_domains_get_defaults_nested(plan_context, monkeypatch):
    """Test skill-domains get-defaults loads core.defaults from extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-defaults', domain='java'))

    assert result['status'] == 'success'
    defaults_str = str(result['defaults'])
    assert 'pm-dev-java:java-core' in defaults_str


def test_skill_domains_get_optionals_nested(plan_context, monkeypatch):
    """Test skill-domains get-optionals loads core.optionals from extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-optionals', domain='java'))

    assert result['status'] == 'success'
    optionals_str = str(result['optionals'])
    assert 'pm-dev-java:java-null-safety' in optionals_str
    assert 'pm-dev-java:java-lombok' in optionals_str


def test_skill_domains_validate_nested(plan_context):
    """Test skill-domains validate loads profiles from extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)
    result = run_script(
        SCRIPT_PATH, 'skill-domains', 'validate', '--domain', 'java', '--skill', 'pm-dev-java:java-core'
    )
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()


def test_skill_domains_validate_nested_profile_skill(plan_context):
    """Test skill-domains validate finds skills in profile blocks loaded from extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)
    result = run_script(
        SCRIPT_PATH, 'skill-domains', 'validate', '--domain', 'java', '--skill', 'pm-dev-java:junit-core'
    )
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()
    assert 'in_defaults' in result.stdout.lower()


def test_skill_domains_get_system_returns_defaults_and_optionals(plan_context, monkeypatch):
    """Test skill-domains get returns system domain with defaults/optionals (no execute_task_skills)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get', domain='system'))

    assert result['status'] == 'success'
    assert 'defaults' in result
    assert 'plan-marshall:persona-plan-marshall-agent' in result['defaults']
    assert 'optionals' in result
    # execute_task_skills was removed from the system domain — get must not surface it.
    assert 'execute_task_skills' not in result


# =============================================================================
# skill-domains detect Tests (Tier 2)
# =============================================================================


def test_skill_domains_detect_runs(plan_context, monkeypatch):
    """Test skill-domains detect command runs successfully."""
    config = {
        'skill_domains': {'system': {'defaults': ['plan-marshall:persona-plan-marshall-agent'], 'optionals': []}},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='detect'))

    assert result['status'] == 'success'
    assert 'detected' in result


def test_skill_domains_detect_no_overwrite(plan_context, monkeypatch):
    """Test skill-domains detect does not overwrite existing domains."""
    config = {
        'skill_domains': {
            'system': {'defaults': [], 'optionals': []},
            'java': {
                'bundle': 'custom-java-bundle',
                'workflow_skill_extensions': {'outline': 'custom:outline-skill'},
            },
        },
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='detect'))

    assert result['status'] == 'success'

    # Verify existing java domain was NOT overwritten
    verify = cmd_skill_domains(Namespace(verb='get', domain='java'))
    assert verify['bundle'] == 'custom-java-bundle'


# =============================================================================
# get-extensions / set-extensions Tests (Tier 2)
# =============================================================================


def test_get_extensions_java(plan_context, monkeypatch):
    """Test get-extensions returns extensions for java domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-extensions', domain='java'))

    assert result['status'] == 'success'
    assert 'extensions' in result
    assert 'outline' in result['extensions']
    assert 'triage' in result['extensions']


def test_get_extensions_unknown_domain(plan_context, monkeypatch):
    """Test get-extensions returns error for unknown domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(Namespace(verb='get-extensions', domain='unknown'))

    assert result['status'] == 'error'


def test_set_extensions(plan_context, monkeypatch):
    """Test set-extensions adds extension to domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='set-extensions',
            domain='java',
            type='triage',
            skill='pm-dev-java:new-triage',
        )
    )

    assert result['status'] == 'success'
    assert result['type'] == 'triage'
    assert result['skill'] == 'pm-dev-java:new-triage'


def test_set_extensions_rejects_self_review_type(plan_context):
    """argparse rejects `set-extensions --type self-review`.

    The self-review surfacer is no longer resolved through a
    workflow_skill_extensions registration — the consumer dispatch calls the
    implementor's fixed notation directly — so `self-review` is no longer an
    accepted `--type` choice. argparse must reject it (exit 2) before the
    handler runs.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'skill-domains',
        'set-extensions',
        '--domain',
        'java',
        '--type',
        'self-review',
        '--skill',
        'pm-dev-java:whatever',
        cwd=plan_context.fixture_dir,
    )

    assert not result.success, 'self-review must be rejected by argparse'
    assert result.returncode == 2, f'Expected argparse exit 2, got {result.returncode}'
    assert 'self-review' in result.stderr


def test_set_extensions_accepts_outline_type(plan_context):
    """argparse still accepts `set-extensions --type outline`."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'skill-domains',
        'set-extensions',
        '--domain',
        'java',
        '--type',
        'outline',
        '--skill',
        'pm-dev-java:ext-outline-java',
        cwd=plan_context.fixture_dir,
    )

    assert result.success, f'outline type must be accepted: {result.stderr}'


def test_set_extensions_accepts_triage_type(plan_context):
    """argparse still accepts `set-extensions --type triage`."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'skill-domains',
        'set-extensions',
        '--domain',
        'java',
        '--type',
        'triage',
        '--skill',
        'pm-dev-java:ext-triage-java',
        cwd=plan_context.fixture_dir,
    )

    assert result.success, f'triage type must be accepted: {result.stderr}'


# =============================================================================
# get-available / configure Tests (Tier 2)
# =============================================================================


def test_get_available_uses_discovery(plan_context, monkeypatch):
    """Test get-available uses discovery for domains."""
    config = {
        'skill_domains': {'system': {'defaults': []}},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='get-available'))

    assert result['status'] == 'success'
    assert 'discovered_domains' in result


def test_get_available_domain_only_extensions_use_applies_to_module():
    """Domain-only extensions (no discover_modules override) get applicable via applies_to_module().

    Extensions like pm-dev-java don't override discover_modules() (returns []),
    so discover_applicable_extensions() excludes them. But they define applies_to_module()
    which should be checked against build-discovered modules.
    """
    discover_available = _cmd_skill_domains.discover_available_domains

    # Run against real plan-marshall repo — build extensions discover modules,
    # domain extensions should be checked via applies_to_module()
    result = discover_available(project_root=Path(__file__).parent.parent.parent.parent)
    domains = result.get('domains', [])

    # plan-marshall-plugin-dev should be applicable (build extension with discover_modules)
    plugin_dev = [d for d in domains if d['key'] == 'plan-marshall-plugin-dev']
    assert plugin_dev, 'plan-marshall-plugin-dev domain should be discovered'
    assert plugin_dev[0].get('applicable') is True, 'plugin-dev should be applicable (build extension)'

    # All domains should have the applicable field when project_root is provided
    for domain in domains:
        assert 'applicable' in domain, f"Domain {domain['key']} missing 'applicable' field"


def test_configure_domains(plan_context, monkeypatch):
    """Test configure adds system domain and selected domains."""
    config = {
        'skill_domains': {},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java,javascript'))

    assert result['status'] == 'success'
    assert 'system_domain' in result

    # Verify marshal.json was updated
    updated = json.loads(marshal_path.read_text())
    assert 'system' in updated['skill_domains']
    assert 'java' in updated['skill_domains']
    assert 'javascript' in updated['skill_domains']


def test_configure_seeds_verification_steps_as_keyed_map(plan_context, monkeypatch):
    """configure seeds plan.phase-5-execute.verification_steps as the id-keyed map.

    The producer writes the built-in verify steps as an id-keyed map of empty
    param objects — NOT a flat list. Key insertion order is the execution order,
    and each verify step owns no params so every value is the empty object. This
    is the keyed-map shape the manifest composer's keyed-map-only reader consumes.
    The built-in set is sourced from the single _seed_verify_steps() discovery
    query (the removed BUILT_IN_VERIFY_STEPS constant is gone).
    """
    expected_built_in = list(_expected_verify_step_ids())

    config = {
        'skill_domains': {},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {'max_iterations': 3, 'steps': {}},
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java'))
    assert result['status'] == 'success'

    updated = json.loads(marshal_path.read_text())
    verification_steps = updated['plan']['phase-5-execute']['verification_steps']
    # configure fully rewrites the map from _seed_verify_steps(); assert the
    # complete key set and every entry maps to empty params
    assert list(verification_steps.keys()) == expected_built_in
    assert verification_steps == {step_id: {} for step_id in expected_built_in}


def test_configure_always_adds_system(plan_context, monkeypatch):
    """Test configure always adds system domain even with empty selection."""
    config = {
        'skill_domains': {},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains=''))

    assert result['status'] == 'success'

    updated = json.loads(marshal_path.read_text())
    assert 'system' in updated['skill_domains']


# =============================================================================
# set with --profile Tests (Tier 2)
# =============================================================================


def test_set_with_profile_returns_error(plan_context, monkeypatch):
    """Test set with --profile returns error since profiles are in extension.py."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='set',
            domain='java',
            profile='quality',
            defaults='pm-dev-java:new-skill',
            optionals=None,
        )
    )

    assert result['status'] == 'error'


# =============================================================================
# Tests for verbs that work without skill_domains (Tier 2)
# =============================================================================


def test_get_available_works_without_skill_domains(plan_context, monkeypatch):
    """Test get-available works without skill_domains being configured."""
    config = {
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='get-available'))

    assert result['status'] == 'success'
    assert 'discovered_domains' in result


def test_configure_works_without_skill_domains(plan_context, monkeypatch):
    """Test configure works without skill_domains being configured."""
    config = {
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

    assert result['status'] == 'success'
    assert 'system_domain' in result

    updated = json.loads(marshal_path.read_text())
    assert 'skill_domains' in updated
    assert 'system' in updated['skill_domains']
    assert 'java' in updated['skill_domains']


def test_list_requires_skill_domains(plan_context, monkeypatch):
    """Test list verb requires skill_domains to be configured."""
    config = {
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='list'))

    assert result['status'] == 'error'
    assert 'skill_domains not configured' in result['error']


# =============================================================================
# Project Skills Tests (Tier 2)
# =============================================================================


def test_discover_project_discovers_skills(plan_context):
    """Test discover-project finds skills in .claude/skills/.

    This test scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    create_nested_marshal_json(plan_context.fixture_dir)

    # Create .claude/skills/ with a test skill (relative to cwd)
    skills_dir = Path('.claude/skills/test-skill')
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skills_dir / 'SKILL.md'
    skill_md.write_text('---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n')

    try:
        result = run_script(SCRIPT_PATH, 'skill-domains', 'discover-project')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'project:test-skill' in result.stdout
    finally:
        skill_md.unlink()
        skills_dir.rmdir()


def test_discover_project_returns_structured_output(plan_context):
    """Test discover-project returns TOON output with status, count, and skills fields."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'skill-domains', 'discover-project')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'count: ' in result.stdout


# =============================================================================
# Prefix-exclusion filter tests (deliverable 2 / Finding B)
# =============================================================================


def _run_discover_project_skills_in_cwd(cwd: Path) -> list[dict]:
    """Invoke discover_project_skills() with cwd switched to ``cwd``.

    discover_project_skills() scans ``.claude/skills/`` relative to the process
    cwd, so tests needing custom project-level layouts must chdir into an
    isolated temp directory. Parallels ``_run_verify_discovery_in_cwd``.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _cmd_skill_domains.discover_project_skills()
    finally:
        os.chdir(original_cwd)


def _make_skill_dir(base: Path, name: str) -> None:
    """Create a ``.claude/skills/{name}`` dir with a minimal SKILL.md under ``base``."""
    skill_dir = base / '.claude' / 'skills' / name
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: {name} desc\n---\n\n# {name}\n')


def test_discover_project_skills_excludes_recipe_prefix(tmp_path):
    """discover_project_skills() excludes recipe-* dirs owned by _discover_all_recipes."""
    _make_skill_dir(tmp_path, 'recipe-lesson-cleanup')
    _make_skill_dir(tmp_path, 'genuine-helper')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    names = [s['name'] for s in skills]
    assert 'recipe-lesson-cleanup' not in names
    assert 'genuine-helper' in names


def test_discover_project_skills_excludes_verify_step_prefix(tmp_path):
    """discover_project_skills() excludes verify-step-* dirs owned by verify-step discovery."""
    _make_skill_dir(tmp_path, 'verify-step-lint')
    _make_skill_dir(tmp_path, 'genuine-helper')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    names = [s['name'] for s in skills]
    assert 'verify-step-lint' not in names
    assert 'genuine-helper' in names


def test_discover_project_skills_excludes_finalize_step_prefix(tmp_path):
    """discover_project_skills() excludes finalize-step-* dirs owned by finalize-step discovery."""
    _make_skill_dir(tmp_path, 'finalize-step-plugin-doctor')
    _make_skill_dir(tmp_path, 'genuine-helper')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    names = [s['name'] for s in skills]
    assert 'finalize-step-plugin-doctor' not in names
    assert 'genuine-helper' in names


def test_discover_project_skills_excludes_audit_prefix(tmp_path):
    """discover_project_skills() excludes audit-* dirs owned by audit-recipe discovery."""
    _make_skill_dir(tmp_path, 'audit-archived-plan-retrospectives')
    _make_skill_dir(tmp_path, 'genuine-helper')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    names = [s['name'] for s in skills]
    assert 'audit-archived-plan-retrospectives' not in names
    assert 'genuine-helper' in names


def test_discover_project_skills_all_excluded_returns_empty(tmp_path):
    """A .claude/skills/ holding only dedicated-prefix dirs yields an empty candidate set."""
    _make_skill_dir(tmp_path, 'recipe-lesson-cleanup')
    _make_skill_dir(tmp_path, 'verify-step-lint')
    _make_skill_dir(tmp_path, 'finalize-step-plugin-doctor')
    _make_skill_dir(tmp_path, 'audit-archived-plan-retrospectives')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    assert skills == []


def test_discover_project_skills_consumer_angle_regression(tmp_path):
    """Consumer-angle regression: the domain-attach candidate set the wizard sees
    contains ONLY the genuine domain-attachable skill when the .claude/skills/
    fixture mixes all four dedicated-prefix dirs with exactly one genuine skill.

    Asserts on the `notation`-shaped candidate set surfaced by
    discover_project_skills() — the exact surface the `discover-project` verb
    wraps and hands to the wizard. This pins the wizard-visible outcome so a future
    refactor cannot silently regress the prefix-exclusion fix. Against the pre-fix
    (unfiltered) behaviour this assertion FAILS — the unfiltered scanner surfaced
    all five dirs as domain-attach candidates.
    """
    _make_skill_dir(tmp_path, 'recipe-lesson-cleanup')
    _make_skill_dir(tmp_path, 'verify-step-lint')
    _make_skill_dir(tmp_path, 'finalize-step-plugin-doctor')
    _make_skill_dir(tmp_path, 'audit-archived-plan-retrospectives')
    _make_skill_dir(tmp_path, 'genuine-domain-skill')

    skills = _run_discover_project_skills_in_cwd(tmp_path)

    surfaced = {s['notation'] for s in skills}
    # ONLY the genuine skill is surfaced to the wizard as a domain-attach candidate.
    assert surfaced == {'project:genuine-domain-skill'}
    assert len(skills) == 1


def test_attach_project_to_domain(plan_context, monkeypatch):
    """Test attach-project adds project skills to a domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='attach-project',
            domain='java',
            skills='project:my-custom-skill',
        )
    )

    assert result['status'] == 'success'
    assert 'project:my-custom-skill' in result['project_skills']

    # Verify marshal.json was updated
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    updated = json.loads(marshal_path.read_text())
    assert 'project:my-custom-skill' in updated['skill_domains']['java']['project_skills']


def test_attach_project_to_system_domain(plan_context, monkeypatch):
    """Test attach-project works with system domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='attach-project',
            domain='system',
            skills='project:cross-domain-skill',
        )
    )

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    updated = json.loads(marshal_path.read_text())
    assert 'project:cross-domain-skill' in updated['skill_domains']['system']['project_skills']


def test_attach_project_rejects_invalid_notation(plan_context, monkeypatch):
    """Test attach-project rejects skills not starting with project:."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='attach-project',
            domain='java',
            skills='pm-dev-java:invalid-notation',
        )
    )

    assert result['status'] == 'error'


def test_attach_project_rejects_unknown_domain(plan_context, monkeypatch):
    """Test attach-project rejects unknown domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_skill_domains(
        Namespace(
            verb='attach-project',
            domain='nonexistent',
            skills='project:some-skill',
        )
    )

    assert result['status'] == 'error'


def test_attach_project_no_duplicates(plan_context, monkeypatch):
    """Test attach-project does not add duplicate skills."""
    create_nested_marshal_json(plan_context.fixture_dir)

    # Attach first time
    cmd_skill_domains(Namespace(verb='attach-project', domain='java', skills='project:my-skill'))

    # Attach same skill again
    cmd_skill_domains(Namespace(verb='attach-project', domain='java', skills='project:my-skill'))

    # Verify no duplicate
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    updated = json.loads(marshal_path.read_text())
    project_skills = updated['skill_domains']['java']['project_skills']
    assert project_skills.count('project:my-skill') == 1


def test_configure_preserves_project_skills(plan_context, monkeypatch):
    """Test configure preserves existing project_skills when reconfiguring domains."""
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:persona-plan-marshall-agent'],
                'project_skills': ['project:system-skill'],
            },
            'java': {
                'bundle': 'pm-dev-java',
                'project_skills': ['project:java-helper'],
                'workflow_skill_extensions': {'triage': 'pm-dev-java:ext-triage-java'},
            },
        },
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

    assert result['status'] == 'success'

    updated = json.loads(marshal_path.read_text())
    assert 'project:system-skill' in updated['skill_domains']['system']['project_skills']
    assert 'project:java-helper' in updated['skill_domains']['java']['project_skills']


def test_configure_preserves_build_map_and_active_profiles(plan_context, monkeypatch):
    """Test configure after init preserves build.map and active_profiles alongside project_skills.

    Regression for the skill-domains configure preservation bug: the global
    active_profiles list lives as a top-level sibling of the domain entries under
    skill_domains, and per-domain active_profiles live inside the domain configs.
    A configure call (as run by /marshall-steward after init) must not drop any of
    them. The build_map (file-to-build contract) now lives as a top-level
    build.map block, so reconfigure (which only rewrites skill_domains) must leave
    it untouched.
    """
    config = {
        'build': {
            'map': {
                'marketplace/bundles/**/*.py': 'verify',
                'test/**/*.py': 'module-tests',
            },
        },
        'skill_domains': {
            'active_profiles': ['quality', 'security'],
            'system': {
                'defaults': ['plan-marshall:persona-plan-marshall-agent'],
                'project_skills': ['project:system-skill'],
            },
            'java': {
                'bundle': 'pm-dev-java',
                'project_skills': ['project:java-helper'],
                'active_profiles': ['testing'],
                'workflow_skill_extensions': {'triage': 'pm-dev-java:ext-triage-java'},
            },
        },
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

    assert result['status'] == 'success'

    updated = json.loads(marshal_path.read_text())
    skill_domains = updated['skill_domains']

    # The top-level build.map block is unaffected by reconfigure.
    assert updated['build']['map'] == {
        'marketplace/bundles/**/*.py': 'verify',
        'test/**/*.py': 'module-tests',
    }
    # The global active_profiles sibling survives reconfigure unconditionally.
    assert skill_domains['active_profiles'] == ['quality', 'security']

    # Per-domain active_profiles restored to domains that still exist.
    assert skill_domains['java']['active_profiles'] == ['testing']

    # project_skills preservation is unchanged (regression-guarded alongside).
    assert 'project:system-skill' in skill_domains['system']['project_skills']
    assert 'project:java-helper' in skill_domains['java']['project_skills']


def test_configure_drops_project_skills_for_removed_domains(plan_context, monkeypatch):
    """Test configure drops project_skills for domains that are no longer selected."""
    config = {
        'skill_domains': {
            'system': {'defaults': []},
            'java': {'bundle': 'pm-dev-java', 'project_skills': ['project:java-helper']},
            'javascript': {'bundle': 'pm-dev-frontend', 'project_skills': ['project:js-helper']},
        },
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

    assert result['status'] == 'success'

    updated = json.loads(marshal_path.read_text())
    assert 'project:java-helper' in updated['skill_domains']['java'].get('project_skills', [])
    assert 'javascript' not in updated['skill_domains']


def test_get_nested_includes_project_skills(plan_context, monkeypatch):
    """Test skill-domains get includes project_skills in output for nested domains."""
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:persona-plan-marshall-agent'],
                'project_skills': ['project:my-tool'],
            },
        },
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 300},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {},
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                },
            },
        },
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    result = cmd_skill_domains(Namespace(verb='get', domain='system'))

    assert result['status'] == 'success'
    assert 'project_skills' in result
    assert 'project:my-tool' in result['project_skills']


# =============================================================================
# list-verify-steps Tests (Tier 2)
# =============================================================================


def test_list_verify_steps_returns_built_in(plan_context, monkeypatch):
    """Test list-verify-steps returns built-in steps with default: prefix."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_list_verify_steps(Namespace())

    assert result['status'] == 'success'
    step_names = [s['name'] for s in result['steps']]
    assert 'default:verify:quality-gate' in step_names
    assert 'default:verify:module-tests' in step_names


def test_list_verify_steps_discovers_project_skills(plan_context):
    """Test list-verify-steps discovers project-local verify-step-* skills.

    Scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    create_marshal_json(plan_context.fixture_dir)

    skill_dir = plan_context.fixture_dir / '.claude' / 'skills' / 'verify-step-hello-world'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: verify-step-hello-world\ndescription: Hello World\n---\n\n# Hello World\n'
    )

    result = run_script(SCRIPT_PATH, 'list-verify-steps', cwd=plan_context.fixture_dir)

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'project:verify-step-hello-world' in result.stdout
    assert 'Hello World' in result.stdout


# =============================================================================
# Order field discovery tests (deliverable 5)
# =============================================================================


def _run_verify_discovery_in_cwd(cwd: Path) -> list[dict]:
    """Invoke _discover_all_verify_steps() with cwd switched to ``cwd``.

    Parallels ``_run_discovery_in_cwd`` in test_cmd_skill_resolution.py but targets
    verify-step discovery. Discovery scans ``.claude/skills/`` relative to the
    process cwd, so tests needing custom project-level layouts must chdir into an
    isolated temp directory.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _cmd_skill_domains._discover_all_verify_steps()
    finally:
        os.chdir(original_cwd)


def test_list_verify_steps_builtins_have_order(tmp_path):
    """Built-in verify steps carry the order parsed from canonical_verify.md frontmatter.

    Every built-in verify step is now the parameterized canonical-verify form
    ``default:verify:{canonical}``; all three share the single backing standards
    doc ``canonical_verify.md`` (``order: 10``), so each discovered step exposes
    order 10.
    """
    steps = _run_verify_discovery_in_cwd(tmp_path)

    by_name = {s['name']: s for s in steps if s['source'] == 'built-in'}
    assert by_name['default:verify:quality-gate']['order'] == 10
    assert by_name['default:verify:module-tests']['order'] == 10
    assert by_name['default:verify:coverage']['order'] == 10


def test_list_verify_steps_project_skill_order_from_frontmatter(tmp_path):
    """Project verify-step-* skills expose the `order` declared in their SKILL.md."""
    skill_dir = tmp_path / '.claude' / 'skills' / 'verify-step-custom'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: verify-step-custom\ndescription: Custom\norder: 150\n---\n\n# Custom\n'
    )

    steps = _run_verify_discovery_in_cwd(tmp_path)

    custom = next(s for s in steps if s['name'] == 'project:verify-step-custom')
    assert custom['order'] == 150


def test_list_verify_steps_project_skill_without_order_returns_none(tmp_path):
    """Project verify-step-* skill without `order` frontmatter exposes order: None."""
    skill_dir = tmp_path / '.claude' / 'skills' / 'verify-step-bare'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('---\nname: verify-step-bare\ndescription: Bare\n---\n\n# Bare\n')

    steps = _run_verify_discovery_in_cwd(tmp_path)

    bare = next(s for s in steps if s['name'] == 'project:verify-step-bare')
    assert bare['order'] is None


# =============================================================================
# Rerouted built-in verify-step discovery (find_implementors is the sole path)
# =============================================================================
#
# Built-in verify-step order/layout resolution is now owned by
# ``extension_discovery.find_implementors`` (the cache-aware doc-root primitives
# in ``configurable_contract.py``), NOT by ``_cmd_skill_domains.BUNDLES_DIR`` +
# ``resolve_bundle_path``. The source/cache layout-resolution coverage therefore
# belongs to the extension-api ``find_implementors`` test suite; the tests below
# assert that ``_discover_all_verify_steps`` delegates to that query and expands
# each implementor's ``canonicals`` list correctly.


def test_discover_all_verify_steps_built_in_matches_discovery(tmp_path):
    """Built-in source-1 steps equal the discovery-derived expected ids, in order."""
    steps = _run_verify_discovery_in_cwd(tmp_path)

    built_in_names = [s['name'] for s in steps if s['source'] == 'built-in']
    assert built_in_names == _expected_verify_step_ids()


def test_discover_all_verify_steps_delegates_to_find_implementors(tmp_path):
    """_discover_all_verify_steps expands a mocked implementor's canonicals list.

    Patching ``find_implementors`` proves the rerouted discovery sources the
    built-in set from the single extension-discovery query — there is no parallel
    constant list — and expands ``canonicals`` into ``default:verify:{canonical}``
    ids in list order, carrying the implementor's ``order`` and ``description``.
    """
    fake = [
        {
            'name': 'default:verify',
            'order': 10,
            'canonicals': ['quality-gate', 'module-tests', 'coverage'],
            'description': 'Parameterized canonical-verify step',
            'source': 'built-in',
        }
    ]
    with patch('extension_discovery.find_implementors', return_value=fake):
        steps = _run_verify_discovery_in_cwd(tmp_path)

    built_ins = [s for s in steps if s['source'] == 'built-in']
    assert [s['name'] for s in built_ins] == [
        'default:verify:quality-gate',
        'default:verify:module-tests',
        'default:verify:coverage',
    ]
    assert all(s['order'] == 10 for s in built_ins)
    assert all(s['description'] == 'Parameterized canonical-verify step' for s in built_ins)


def test_discover_all_verify_steps_empty_implementors_yields_no_built_ins(tmp_path):
    """No ext-point-verify-step implementors → empty built-in set (fallback path).

    The discovery query is the SOLE source of the built-in universe, so an empty
    implementor list yields zero built-in steps — there is no constant-list
    fallback that would re-introduce the removed BUILT_IN_VERIFY_STEPS ids.
    """
    with patch('extension_discovery.find_implementors', return_value=[]):
        steps = _run_verify_discovery_in_cwd(tmp_path)

    assert [s for s in steps if s['source'] == 'built-in'] == []


def test_seed_verify_steps_empty_implementors_yields_empty_map(tmp_path):
    """_seed_verify_steps with no implementors yields an empty keyed map (fallback path)."""
    config_defaults = _load_module('_config_defaults', '_config_defaults.py')
    with patch('extension_discovery.find_implementors', return_value=[]):
        seeded = config_defaults._seed_verify_steps()

    assert seeded == {}


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_skill_domains_list(plan_context):
    """Test CLI plumbing: skill-domains list outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'skill-domains', 'list')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'java' in result.stdout


def test_cli_skill_domains_get(plan_context):
    """Test CLI plumbing: skill-domains get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'pm-dev-java:java-core' in result.stdout


# =============================================================================
# Main
# =============================================================================
