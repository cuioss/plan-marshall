#!/usr/bin/env python3
"""Tests for `manage-config models read` resolver subcommand.

Tier 2 (direct import) tests covering the hierarchical resolver: the
three lookup forms (bare group / dotted / --phase + --role), the
documented resolution order (`models.roles.<group>[.<subkey>] ->
models.default -> inherit`), polymorphic-value normalisation (string at
group / object at group), the `--default` short-circuit, the
`resolve-target` subcommand, and the error/warning paths for invalid
levels and unregistered role groups. Read-only round-trip stability is
asserted by hashing marshal.json before and after each call.
"""

import hashlib
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)
_PLAN_MARSHALL_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'scripts'
)

# `_cmd_models` imports `model_presets` at module level. Ensure the
# plan-marshall scripts directory is importable BEFORE loading _cmd_models.
if str(_PLAN_MARSHALL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAN_MARSHALL_SCRIPTS_DIR))


def _load_module(name, filename, scripts_dir=_MANAGE_CONFIG_SCRIPTS_DIR):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_models_mod = _load_module('_cmd_models', '_cmd_models.py')
cmd_models = _cmd_models_mod.cmd_models
cmd_models_resolve_target = _cmd_models_mod.cmd_models_resolve_target

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext  # noqa: E402


def _hash_marshal(fixture_dir):
    """Return SHA-256 of marshal.json for round-trip stability checks."""
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


def _write_marshal_with_models(fixture_dir, models_block):
    """Write marshal.json with optional `models` block on top of the test default."""
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    if models_block is not None:
        config['models'] = models_block
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _ns(role=None, phase=None, default=False):
    """Build a Namespace shaped like argparse's output for `models read`."""
    return Namespace(role=role, phase=phase, default=default)


# =============================================================================
# Bare-group lookup (flat phase groups)
# =============================================================================


def test_flat_group_set_returns_role_value():
    """Flat phase-N group: bare lookup returns the configured level."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'phase-2': 'high'}},
        )
        before = _hash_marshal(ctx.fixture_dir)

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.roles.phase-2'
        assert _hash_marshal(ctx.fixture_dir) == before


def test_flat_group_unset_with_default_returns_default():
    """Flat group absent: falls through to models.default."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'medium'})

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'


def test_flat_group_unset_no_default_returns_inherit():
    """Flat group absent and default absent: implicit `inherit` fallback."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, models_block=None)

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert result['source'] == 'implicit_default'


def test_models_block_present_but_empty_returns_inherit():
    """`models: {}` resolves to inherit (same as absent)."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {})

        result = cmd_models(_ns(role='phase-3'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'


# =============================================================================
# Dotted lookup (nested groups)
# =============================================================================


def test_dotted_lookup_returns_subkey_value():
    """`--role phase-6.create-pr` resolves the nested object's subkey."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {
                'default': 'medium',
                'roles': {'phase-6': {'create-pr': 'high'}},
            },
        )

        result = cmd_models(_ns(role='phase-6.create-pr'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.roles.phase-6.create-pr'


def test_dotted_lookup_subkey_unset_falls_through_to_default():
    """Subkey absent within a multi-workflow group: falls through to default."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'phase-6': {'retrospective': 'high'}}},
        )

        result = cmd_models(_ns(role='phase-6.create-pr'))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'


def test_dotted_lookup_cross_group():
    """`cross.triage` (and other cross subkeys) resolve correctly."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'low', 'roles': {'cross': {'triage': 'high'}}},
        )

        result = cmd_models(_ns(role='cross.triage'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.roles.cross.triage'


def test_dotted_unknown_subkey_errors():
    """Subkey not registered in the group's schema produces an error."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium'},
        )

        result = cmd_models(_ns(role='phase-6.not-a-real-subkey'))

        assert result['status'] == 'error'
        assert 'not-a-real-subkey' in result['error']
        assert 'phase-6' in result['error']


def test_bare_nested_group_lookup_errors():
    """Bare-group lookup on a multi-workflow group requires --role <group>.<sub>."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'phase-6': {'create-pr': 'high'}}},
        )

        result = cmd_models(_ns(role='phase-6'))

        assert result['status'] == 'error'
        assert 'multi-workflow group' in result['error']


# =============================================================================
# Two-flag form (--phase <group> --role <subkey>)
# =============================================================================


def test_two_flag_form_resolves_subkey():
    """`--phase phase-6 --role create-pr` is equivalent to the dotted form."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'phase-6': {'create-pr': 'high'}}},
        )

        result = cmd_models(_ns(role='create-pr', phase='phase-6'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.roles.phase-6.create-pr'


def test_two_flag_form_rejects_dotted_role():
    """In two-flag mode, --role must be a bare subkey (no dot)."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'medium'})

        result = cmd_models(_ns(role='create-pr.extra', phase='phase-6'))

        assert result['status'] == 'error'
        assert 'bare subkey' in result['error']


# =============================================================================
# Polymorphic-value normalisation
# =============================================================================


def test_string_at_flat_group_with_any_subkey_resolves_to_same():
    """Flat group with a string value: any subkey lookup resolves to the same string."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'low', 'roles': {'phase-1': 'high'}},
        )

        # Bare-group lookup returns the string.
        result_bare = cmd_models(_ns(role='phase-1'))
        assert result_bare['status'] == 'success'
        assert result_bare['level'] == 'high'


# =============================================================================
# --default short-circuit
# =============================================================================


def test_default_flag_returns_models_default():
    """`--default` returns models.default without role lookup."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'high', 'roles': {'phase-1': 'low'}},
        )

        result = cmd_models(_ns(default=True))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.default'


def test_default_flag_without_default_set_returns_inherit():
    """`--default` with no models.default configured returns inherit."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {})

        result = cmd_models(_ns(default=True))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert result['source'] == 'implicit_default'


# =============================================================================
# resolve-target subcommand
# =============================================================================


def test_resolve_target_high_level():
    """resolve-target returns execution-context-{level} for non-inherit levels."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'cross': {'triage': 'high'}}},
        )

        result = cmd_models_resolve_target(_ns(role='cross.triage'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['target'] == 'execution-context-high'


def test_resolve_target_inherit_returns_canonical():
    """resolve-target returns canonical `execution-context` when level is inherit."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {})

        result = cmd_models_resolve_target(_ns(role='phase-1'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert result['target'] == 'execution-context'


def test_resolve_target_each_level():
    """Every level keyword produces the matching variant target name."""
    levels = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max')
    for level in levels:
        with PlanContext(plan_id=f'resolve-target-{level}') as ctx:
            _write_marshal_with_models(
                ctx.fixture_dir,
                {'roles': {'phase-2': level}},
            )

            result = cmd_models_resolve_target(_ns(role='phase-2'))

            assert result['status'] == 'success'
            assert result['level'] == level
            assert result['target'] == f'execution-context-{level}'


# =============================================================================
# Level enum coverage
# =============================================================================


def test_invalid_level_at_role_errors():
    """Invalid level value at a role: error with full source path."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'roles': {'phase-2': 'gigaultra'}},
        )

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'error'
        assert 'gigaultra' in result['error']
        assert 'models.roles.phase-2' in result['error']


def test_invalid_level_at_default_errors():
    """Invalid level value at models.default: error."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'gigaultra'},
        )

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'error'
        assert 'gigaultra' in result['error']
        assert 'models.default' in result['error']


def test_max_level_resolves_to_max_variant():
    """`max` is a live level; resolver returns it and the variant target."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'roles': {'phase-2': 'max'}},
        )

        result = cmd_models(_ns(role='phase-2'))

        assert result['status'] == 'success'
        assert result['level'] == 'max'

        target_result = cmd_models_resolve_target(_ns(role='phase-2'))
        assert target_result['status'] == 'success'
        assert target_result['target'] == 'execution-context-max'


def test_legacy_xhigh_xxhigh_resolve_silent_downgrade():
    """Old `xhigh` / `xxhigh` keywords still resolve after the palette rebind.

    Migration contract: pre-1.0 palette expansion rebinds the existing
    keywords to weaker primitives (xhigh: opus-high → opus-medium; xxhigh:
    opus-xhigh → opus-high). The resolver still accepts the keywords so
    consumer marshal.json files do not break — they silently bind to the
    new primitive. There is no auto-migration.
    """
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'roles': {'phase-2': 'xhigh', 'phase-3': 'xxhigh'}},
        )

        # Both keywords still resolve cleanly.
        for role, expected_level in (('phase-2', 'xhigh'), ('phase-3', 'xxhigh')):
            result = cmd_models(_ns(role=role))
            assert result['status'] == 'success', f'{role}: {result}'
            assert result['level'] == expected_level

            target_result = cmd_models_resolve_target(_ns(role=role))
            assert target_result['status'] == 'success'
            assert target_result['target'] == f'execution-context-{expected_level}'


# =============================================================================
# Unknown role warning (legacy keys, registry renames)
# =============================================================================


def test_unknown_role_emits_warning_and_falls_through():
    """Legacy / unknown role keys produce a warning but do not error."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'q_gate_validation': 'high'}},
        )

        result = cmd_models(_ns(role='q_gate_validation'))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'
        assert 'warnings' in result
        assert any('q_gate_validation' in w for w in result['warnings'])
        assert any('not registered' in w for w in result['warnings'])


def test_unknown_role_with_no_default_returns_inherit_and_warns():
    """Unknown role with no default: inherit + warning."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {})

        result = cmd_models(_ns(role='legacy_thing'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert 'warnings' in result


# =============================================================================
# Read-only round-trip stability
# =============================================================================


def test_read_does_not_mutate_marshal():
    """`models read` must not touch marshal.json."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {
                'default': 'medium',
                'roles': {
                    'phase-2': 'high',
                    'cross': {'triage': 'high'},
                },
            },
        )
        before = _hash_marshal(ctx.fixture_dir)

        cmd_models(_ns(role='phase-2'))
        cmd_models(_ns(role='cross.triage'))
        cmd_models(_ns(default=True))
        cmd_models_resolve_target(_ns(role='cross.triage'))

        assert _hash_marshal(ctx.fixture_dir) == before
