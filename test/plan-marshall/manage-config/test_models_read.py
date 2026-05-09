#!/usr/bin/env python3
"""Tests for `manage-config models read --role <name>` resolver subcommand.

Tier 2 (direct import) tests covering the resolver's level enum, the
documented resolution order (`models.roles.<role> -> models.default ->
inherit`), and the error/warning paths for invalid levels, pending roles,
and unknown role names. Read-only round-trip stability is asserted by
hashing marshal.json before and after each call.
"""

import hashlib
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json

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


_cmd_models_mod = _load_module('_cmd_models', '_cmd_models.py')
cmd_models = _cmd_models_mod.cmd_models

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext  # noqa: E402


def _hash_marshal(fixture_dir: Path) -> str:
    """Return SHA-256 of marshal.json for round-trip stability checks."""
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


def _write_marshal_with_models(fixture_dir: Path, models_block: dict | None) -> None:
    """Write marshal.json with optional `models` block on top of the test default."""
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    if models_block is not None:
        config['models'] = models_block
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


# =============================================================================
# Resolution order (effective roles)
# =============================================================================


def test_role_set_returns_role_value():
    """Role explicit value beats default."""
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'q_gate_validation': 'high'}},
        )
        before = _hash_marshal(ctx.fixture_dir)

        result = cmd_models(Namespace(role='q_gate_validation'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'
        assert result['source'] == 'models.roles.q_gate_validation'
        assert _hash_marshal(ctx.fixture_dir) == before, 'read must not mutate marshal.json'


def test_role_unset_with_default_returns_default():
    """Role absent: falls through to models.default."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'medium'})

        result = cmd_models(Namespace(role='q_gate_validation'))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'


def test_role_unset_no_default_returns_inherit():
    """Role absent and default absent: implicit `inherit` fallback."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, models_block=None)

        result = cmd_models(Namespace(role='q_gate_validation'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert result['source'] == 'implicit_default'


def test_models_block_present_but_empty_returns_inherit():
    """`models: {}` resolves to inherit (same as absent)."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {})

        result = cmd_models(Namespace(role='research'))

        assert result['status'] == 'success'
        assert result['level'] == 'inherit'


# =============================================================================
# Level enum coverage
# =============================================================================


def test_level_low():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'low'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'low'


def test_level_medium():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'medium'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'medium'


def test_level_high():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'high'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'high'


def test_level_xhigh():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'xhigh'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'xhigh'


def test_level_xxhigh():
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'xxhigh'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'xxhigh'


def test_level_inherit_explicit():
    """Explicit `inherit` is a valid level keyword."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'inherit'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert result['source'] == 'models.roles.research'


# =============================================================================
# Error paths
# =============================================================================


def test_invalid_level_role_value_errors():
    """Invalid level on role: hard error."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'ultra'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'error'
        assert "invalid level 'ultra'" in result['error']
        assert 'models.roles.research' in result['error']


def test_invalid_level_default_value_errors():
    """Invalid level on default: hard error."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'ultra'})
        result = cmd_models(Namespace(role='q_gate_validation'))
        assert result['status'] == 'error'
        assert 'models.default' in result['error']


def test_reserved_level_max_errors():
    """`max` is reserved-future-additive: clear error message."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'roles': {'research': 'max'}})
        result = cmd_models(Namespace(role='research'))
        assert result['status'] == 'error'
        assert 'reserved' in result['error']
        assert 'xxhigh' in result['error']


def test_marshal_not_initialized_errors():
    """marshal.json missing: hard error."""
    with PlanContext():
        result = cmd_models(Namespace(role='q_gate_validation'))
        assert result['status'] == 'error'
        assert 'not initialized' in result['error']


# =============================================================================
# Pending and unknown roles
# =============================================================================


def test_pending_role_resolves_normally():
    """Pending role keys validate and resolve via default/inherit just like effective ones."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'high', 'roles': {'phase_refine': 'low'}})
        result = cmd_models(Namespace(role='phase_refine'))
        assert result['status'] == 'success'
        assert result['level'] == 'low'
        # No warning — pending is a known role; only unknown roles warn.
        assert 'warnings' not in result


def test_unknown_role_warns_and_falls_back():
    """Unknown role key: warns (not errors) and resolves to default/inherit."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, {'default': 'medium'})
        result = cmd_models(Namespace(role='nonexistent_role'))
        assert result['status'] == 'success'
        # Falls back through default since role lookup is skipped for unknown roles.
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'
        assert 'warnings' in result
        assert any('not registered' in w for w in result['warnings'])


def test_unknown_role_no_default_warns_and_inherits():
    """Unknown role + no default: warns and resolves to inherit."""
    with PlanContext() as ctx:
        _write_marshal_with_models(ctx.fixture_dir, models_block=None)
        result = cmd_models(Namespace(role='nonexistent_role'))
        assert result['status'] == 'success'
        assert result['level'] == 'inherit'
        assert 'warnings' in result


def test_unknown_role_with_role_value_still_warns_but_skips_role_lookup():
    """When the role is unknown, the resolver skips the per-role value entirely.

    This is the deliberate guard against a stale config carrying a value
    keyed under a removed role; the value is ignored, the user is warned,
    and resolution falls through default/inherit.
    """
    with PlanContext() as ctx:
        _write_marshal_with_models(
            ctx.fixture_dir,
            {'default': 'medium', 'roles': {'nonexistent_role': 'high'}},
        )
        result = cmd_models(Namespace(role='nonexistent_role'))
        assert result['status'] == 'success'
        # `high` from the unknown-role entry is intentionally ignored.
        assert result['level'] == 'medium'
        assert result['source'] == 'models.default'
        assert 'warnings' in result
