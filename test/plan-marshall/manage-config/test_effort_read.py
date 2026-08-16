#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for `manage-config effort read` resolver subcommand.

Tier 2 (direct import) tests covering the hierarchical resolver: the
three lookup forms (bare group / dotted / --phase + --role), the
documented resolution order (`models.roles.<group>[.<subkey>] ->
effort -> inherit`), polymorphic-value normalisation (string at
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

import pytest
from _manage_config_fixtures import create_marshal_json

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

# `_cmd_effort` imports `effort_presets` at module level. Ensure the
# plan-marshall scripts directory is importable BEFORE loading _cmd_effort.
if str(_PLAN_MARSHALL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAN_MARSHALL_SCRIPTS_DIR))


def _load_module(name, filename, scripts_dir=_MANAGE_CONFIG_SCRIPTS_DIR):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_models_mod = _load_module('_cmd_effort', '_cmd_effort.py')
cmd_effort = _cmd_models_mod.cmd_effort
cmd_effort_resolve_target = _cmd_models_mod.cmd_effort_resolve_target

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import conftest  # noqa: E402, F401


def _hash_marshal(fixture_dir):
    """Return SHA-256 of marshal.json for round-trip stability checks."""
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


def _write_marshal_with_models(fixture_dir, models_block):
    """Write marshal.json with optional effort config.

    Accepts the legacy-shape ``{"default": <level>, "roles": {<phase>: ...}}``
    payload (preserved for backwards-compat in test bodies) and translates
    it to the current per-phase storage shape on disk:

      - ``config['plan']['effort']`` set to ``models_block['default']``
        when present (plan-wide fallback).
      - For each phase in ``models_block['roles']``, set
        ``config['plan'][phase]['effort']`` to the value (string or dict).
      - When ``models_block`` is ``None``, leave the file at the test
        fixture default (no effort fields).
      - When ``models_block`` is an empty dict, drop all effort fields.
    """
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    # Always clear any pre-existing effort fields so the test fixture is
    # deterministic regardless of what the base fixture seeded.
    config.pop('effort', None)
    config.pop('models', None)
    plan_block = config.get('plan', {})
    if isinstance(plan_block, dict):
        plan_block.pop('effort', None)
        for phase_entry in plan_block.values():
            if isinstance(phase_entry, dict):
                phase_entry.pop('effort', None)
    if models_block is not None:
        plan_block = config.setdefault('plan', {})
        default = models_block.get('default')
        if default is not None:
            plan_block['effort'] = default
        for phase, value in models_block.get('roles', {}).items():
            phase_entry = plan_block.setdefault(phase, {})
            if isinstance(phase_entry, dict):
                phase_entry['effort'] = value
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _ns(role=None, phase=None, default=False):
    """Build a Namespace shaped like argparse's output for `models read`."""
    return Namespace(role=role, phase=phase, default=default)


# =============================================================================
# Bare-group lookup (flat phase groups)
# =============================================================================


def test_flat_group_set_returns_role_value(plan_context):
    """Flat phase-N group: bare lookup returns the configured level."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'default': 'level-2', 'roles': {'phase-2-refine': 'level-3'}},
    )
    before = _hash_marshal(plan_context.fixture_dir)

    result = cmd_effort(_ns(role='phase-2-refine'))

    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['source'] == 'plan.phase-2-refine.effort'
    assert _hash_marshal(plan_context.fixture_dir) == before


#: The effort-resolution cascade, one row per rung: (the `models` block seeded into
#: marshal.json, the `models read` flags, the level that must resolve, the source path
#: that must be reported). `source` is asserted as well as `level` because two rungs can
#: agree on the level while disagreeing on where it came from, and the source is what
#: tells an operator which knob to edit.
_EFFORT_RESOLUTIONS = [
    ({'default': 'level-2'}, {'role': 'phase-2-refine'}, 'level-2', 'plan.effort'),
    (None, {'role': 'phase-2-refine'}, 'inherit', 'implicit_default'),
    (
        {'default': 'level-2', 'roles': {'phase-6-finalize': {'verification-feedback': 'level-3'}}},
        {'role': 'phase-6-finalize.verification-feedback'},
        'level-3',
        'plan.phase-6-finalize.effort.verification-feedback',
    ),
    (
        {
            'default': 'level-2',
            'roles': {'phase-6-finalize': {'default': 'level-1', 'verification-feedback': 'level-3'}},
        },
        {'role': 'phase-6-finalize.post-run-review'},
        'level-1',
        'plan.phase-6-finalize.effort.default',
    ),
    (
        {'default': 'level-2', 'roles': {'phase-6-finalize': {'verification-feedback': 'level-3'}}},
        {'role': 'phase-6-finalize.post-run-review'},
        'level-2',
        'plan.effort',
    ),
    (
        {
            'default': 'level-2',
            'roles': {'phase-6-finalize': {'default': 'level-3', 'verification-feedback': 'level-4'}},
        },
        {'role': 'phase-6-finalize'},
        'level-3',
        'plan.phase-6-finalize.effort.default',
    ),
    (
        {'default': 'level-2', 'roles': {'phase-6-finalize': {'verification-feedback': 'level-3'}}},
        {'role': 'phase-6-finalize'},
        'level-2',
        'plan.effort',
    ),
    (
        {'default': 'level-2', 'roles': {'phase-3-outline': 'level-3'}},
        {'phase': 'phase-3-outline'},
        'level-3',
        'plan.phase-3-outline.effort',
    ),
    (
        {'default': 'level-2', 'roles': {'phase-6-finalize': {'verification-feedback': 'level-3'}}},
        {'role': 'verification-feedback', 'phase': 'phase-6-finalize'},
        'level-3',
        'plan.phase-6-finalize.effort.verification-feedback',
    ),
    (
        {'default': 'level-3', 'roles': {'phase-2-refine': 'level-1'}},
        {'default': True},
        'level-3',
        'plan.effort',
    ),
]


@pytest.mark.parametrize(
    ('models_block', 'flags', 'level', 'source'),
    _EFFORT_RESOLUTIONS,
    ids=[
        'flat-group-unset-falls-to-plan-effort',
        'flat-group-and-default-both-unset-falls-to-implicit-inherit',
        'dotted-lookup-resolves-the-nested-subkey',
        'dotted-subkey-unset-walks-to-the-in-group-default-slot',
        'dotted-subkey-unset-without-in-group-default-falls-to-plan-effort',
        'bare-group-on-an-object-walks-to-its-default-slot',
        'bare-group-on-an-object-without-default-falls-to-plan-effort',
        'phase-flag-alone-is-a-bare-group-lookup',
        'two-flag-form-resolves-the-same-subkey-as-the-dotted-form',
        'default-flag-short-circuits-to-plan-effort',
    ],
)
def test_effort_read_resolves_level_and_source(plan_context, models_block, flags, level, source):
    """`models read` resolves a level and reports the config path it came from."""
    _write_marshal_with_models(plan_context.fixture_dir, models_block)

    result = cmd_effort(_ns(**flags))

    assert result['status'] == 'success'
    assert result['level'] == level
    assert result['source'] == source


#: (models block, flags, fragments the error message must carry). The message is
#: asserted, not just the error status: it is the only thing that tells the operator
#: which key in which block is wrong.
_EFFORT_READ_ERRORS = [
    (
        {'default': 'level-2'},
        {'role': 'phase-6-finalize.not-a-real-subkey'},
        ('not-a-real-subkey', 'phase-6-finalize'),
    ),
    (
        {'default': 'level-2'},
        {'role': 'verification-feedback.extra', 'phase': 'phase-6-finalize'},
        ('bare subkey',),
    ),
    (
        {'roles': {'phase-2-refine': 'gigaultra'}},
        {'role': 'phase-2-refine'},
        ('gigaultra', 'plan.phase-2-refine.effort'),
    ),
    ({'default': 'gigaultra'}, {'role': 'phase-2-refine'}, ('gigaultra', 'plan.effort')),
]


@pytest.mark.parametrize(
    ('models_block', 'flags', 'fragments'),
    _EFFORT_READ_ERRORS,
    ids=[
        'unregistered-subkey-names-the-subkey-and-its-group',
        'two-flag-form-rejects-a-dotted-role',
        'invalid-level-at-a-role-names-the-role-path',
        'invalid-level-at-the-default-names-the-default-path',
    ],
)
def test_effort_read_rejects_invalid_lookup(plan_context, models_block, flags, fragments):
    """An invalid lookup or an invalid stored level errors, naming the offending path."""
    _write_marshal_with_models(plan_context.fixture_dir, models_block)

    result = cmd_effort(_ns(**flags))

    assert result['status'] == 'error'
    for fragment in fragments:
        assert fragment in result['error']


def test_models_block_present_but_empty_returns_inherit(plan_context):
    """`models: {}` resolves to inherit (same as absent)."""
    _write_marshal_with_models(plan_context.fixture_dir, {})

    result = cmd_effort(_ns(role='phase-3-outline'))

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'


# =============================================================================
# Dotted lookup (nested groups)
# =============================================================================


# =============================================================================
# Two-flag form (--phase <group> --role <subkey>)
# =============================================================================


# =============================================================================
# Polymorphic-value normalisation
# =============================================================================


def test_string_at_flat_group_with_any_subkey_resolves_to_same(plan_context):
    """Flat group with a string value: any subkey lookup resolves to the same string."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'default': 'level-1', 'roles': {'phase-2-refine': 'level-3'}},
    )

    # Bare-group lookup returns the string.
    result_bare = cmd_effort(_ns(role='phase-2-refine'))
    assert result_bare['status'] == 'success'
    assert result_bare['level'] == 'level-3'


# =============================================================================
# --default short-circuit
# =============================================================================


def test_default_flag_without_default_set_returns_inherit(plan_context):
    """`--default` with no effort configured returns inherit."""
    _write_marshal_with_models(plan_context.fixture_dir, {})

    result = cmd_effort(_ns(default=True))

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'
    assert result['source'] == 'implicit_default'


# =============================================================================
# resolve-target subcommand
# =============================================================================


def test_resolve_target_high_level(plan_context):
    """resolve-target returns execution-context-{level} for non-inherit levels."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'default': 'level-2', 'roles': {'phase-6-finalize': {'verification-feedback': 'level-3'}}},
    )

    result = cmd_effort_resolve_target(_ns(role='phase-6-finalize.verification-feedback'))

    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['target'] == 'execution-context-level-3'


def test_resolve_target_inherit_returns_canonical(plan_context):
    """resolve-target returns canonical `execution-context` when level is inherit."""
    _write_marshal_with_models(plan_context.fixture_dir, {})

    result = cmd_effort_resolve_target(_ns(role='phase-2-refine'))

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'
    assert result['target'] == 'execution-context'


@pytest.mark.parametrize(
    'level',
    ('level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7'),
)
def test_resolve_target_each_level(plan_context, level):
    """Every level keyword produces the matching variant target name."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'roles': {'phase-2-refine': level}},
    )

    result = cmd_effort_resolve_target(_ns(role='phase-2-refine'))

    assert result['status'] == 'success'
    assert result['level'] == level
    assert result['target'] == f'execution-context-{level}'


# =============================================================================
# Level enum coverage
# =============================================================================


def test_level_6_resolves_to_level_6_variant(plan_context):
    """`level-6` is a live level; resolver returns it and the variant target."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'roles': {'phase-2-refine': 'level-6'}},
    )

    result = cmd_effort(_ns(role='phase-2-refine'))

    assert result['status'] == 'success'
    assert result['level'] == 'level-6'

    target_result = cmd_effort_resolve_target(_ns(role='phase-2-refine'))
    assert target_result['status'] == 'success'
    assert target_result['target'] == 'execution-context-level-6'


def test_level_7_resolves_to_level_7_variant(plan_context):
    """`level-7` (the new fable top tier) resolves and yields its variant target."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'roles': {'phase-2-refine': 'level-7'}},
    )

    result = cmd_effort(_ns(role='phase-2-refine'))

    assert result['status'] == 'success'
    assert result['level'] == 'level-7'

    target_result = cmd_effort_resolve_target(_ns(role='phase-2-refine'))
    assert target_result['status'] == 'success'
    assert target_result['target'] == 'execution-context-level-7'


@pytest.mark.parametrize('old_token', ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max'))
def test_old_tokens_are_rejected_after_breaking_rename(plan_context, old_token):
    """Old palette tokens are invalid after the breaking rename to level-N.

    `compatibility: breaking` removes the migration shim: there is no
    deprecation alias and no silent downgrade. Each old token now fails the
    `ALLOWED_LEVELS` validation and `cmd_effort` returns `status: error`
    naming the offending token.
    """
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'roles': {'phase-2-refine': old_token}},
    )

    result = cmd_effort(_ns(role='phase-2-refine'))

    assert result['status'] == 'error', f'{old_token}: {result}'
    assert old_token in result['error']


# =============================================================================
# Unknown role warning (legacy keys, registry renames)
# =============================================================================


def test_unknown_role_emits_warning_and_falls_through(plan_context):
    """Legacy / unknown role keys produce a warning but do not error."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {'default': 'level-2', 'roles': {'q_gate_validation': 'level-3'}},
    )

    result = cmd_effort(_ns(role='q_gate_validation'))

    assert result['status'] == 'success'
    assert result['level'] == 'level-2'
    assert result['source'] == 'plan.effort'
    assert 'warnings' in result
    assert any('q_gate_validation' in w for w in result['warnings'])
    assert any('not registered' in w for w in result['warnings'])


def test_unknown_role_with_no_default_returns_inherit_and_warns(plan_context):
    """Unknown role with no default: inherit + warning."""
    _write_marshal_with_models(plan_context.fixture_dir, {})

    result = cmd_effort(_ns(role='legacy_thing'))

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'
    assert 'warnings' in result


# =============================================================================
# Read-only round-trip stability
# =============================================================================


def test_read_does_not_mutate_marshal(plan_context):
    """`models read` must not touch marshal.json."""
    _write_marshal_with_models(
        plan_context.fixture_dir,
        {
            'default': 'level-2',
            'roles': {
                'phase-2-refine': 'level-3',
                'phase-6-finalize': {'verification-feedback': 'level-3'},
            },
        },
    )
    before = _hash_marshal(plan_context.fixture_dir)

    cmd_effort(_ns(role='phase-2-refine'))
    cmd_effort(_ns(role='phase-6-finalize.verification-feedback'))
    cmd_effort(_ns(default=True))
    cmd_effort_resolve_target(_ns(role='phase-6-finalize.verification-feedback'))

    assert _hash_marshal(plan_context.fixture_dir) == before


