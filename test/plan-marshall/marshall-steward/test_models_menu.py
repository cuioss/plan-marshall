#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the marshall-steward Models submenu round-trip.

The Models submenu is a markdown-driven wizard step that calls
``manage-config models read --role`` for resolution and writes the
``models`` block of ``marshal.json``. The wizard contract lives in
``marshall-steward/standards/models-menu.md``; this test suite pins
the underlying read/write round-trip behaviour the wizard depends on:

- Setting ``default=medium`` and ``roles.q_gate_validation=high``
  produces the expected resolver outputs.
- Re-reading the same marshal.json yields the saved values
  (round-trip stable).
- Invalid level values are refused at read time — the wizard's
  validation contract ("never let the user save an invalid level") is
  enforced by the same enum that the resolver uses.
- Pending role keys validate and resolve normally; the registry
  documents the not-yet-effective status.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from conftest import MARKETPLACE_ROOT, PlanContext  # type: ignore[import-not-found]

_MANAGE_CONFIG_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_models_mod = _load_module(
    '_cmd_models', _MANAGE_CONFIG_SCRIPTS_DIR / '_cmd_models.py'
)
cmd_models = _cmd_models_mod.cmd_models


def _seed_marshal(plan_dir: Path, models: dict | None) -> Path:
    """Write a minimal marshal.json with optional `models` block."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {'plan': {}}
    if models is not None:
        config['models'] = models
    marshal_path = plan_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return marshal_path


def _read_models_block(plan_dir: Path) -> dict:
    return json.loads((plan_dir / 'marshal.json').read_text(encoding='utf-8')).get(
        'models', {}
    )


# =============================================================================
# Round-trip: write → resolve → re-read
# =============================================================================


def test_round_trip_default_and_role_persist():
    """Set default=medium and roles.phase-6.verification-feedback=high; resolver returns saved values."""
    with PlanContext() as ctx:
        _seed_marshal(
            ctx.fixture_dir,
            {
                'default': 'medium',
                'roles': {'phase-6': {'verification-feedback': 'high'}},
            },
        )

        result_role = cmd_models(
            Namespace(role='phase-6.verification-feedback', phase=None, default=False)
        )
        result_other = cmd_models(
            Namespace(role='phase-3.research', phase=None, default=False)
        )

        assert result_role['status'] == 'success'
        assert result_role['level'] == 'high'
        assert result_role['source'] == 'models.roles.phase-6.verification-feedback'

        assert result_other['status'] == 'success'
        assert result_other['level'] == 'medium'
        assert result_other['source'] == 'models.default'

        # Re-read marshal.json — stored block matches what the wizard would have written.
        block = _read_models_block(ctx.fixture_dir)
        assert block == {
            'default': 'medium',
            'roles': {'phase-6': {'verification-feedback': 'high'}},
        }


def test_round_trip_repeated_reads_do_not_mutate():
    """Multiple `manage-config models read` invocations leave marshal.json byte-identical."""
    with PlanContext() as ctx:
        marshal_path = _seed_marshal(
            ctx.fixture_dir, {'default': 'low', 'roles': {'research': 'xxhigh'}}
        )
        before = marshal_path.read_bytes()

        for role in ('research', 'q_gate_validation', 'phase_init'):
            cmd_models(Namespace(role=role))

        after = marshal_path.read_bytes()
        assert before == after, 'wizard reads must not mutate marshal.json'


# =============================================================================
# Validation: refuse invalid levels (wizard "never lets user save invalid")
# =============================================================================


def test_invalid_level_refused_at_read():
    """`models.roles.phase-6.verification-feedback = 'ultra'` errors out — wizard refuses save."""
    with PlanContext() as ctx:
        _seed_marshal(
            ctx.fixture_dir,
            {'roles': {'phase-6': {'verification-feedback': 'ultra'}}},
        )

        result = cmd_models(
            Namespace(role='phase-6.verification-feedback', phase=None, default=False)
        )

        assert result['status'] == 'error'
        assert "invalid level 'ultra'" in result['error']
        # The error names the source so the wizard can re-prompt with context.
        assert 'models.roles.phase-6.verification-feedback' in result['error']


def test_max_level_resolves_for_research():
    """`max` is a live level (promoted from reserved-future); resolves cleanly."""
    with PlanContext() as ctx:
        _seed_marshal(ctx.fixture_dir, {'default': 'max'})

        result = cmd_models(Namespace(role='phase-3.research'))

        assert result['status'] == 'success'
        assert result['level'] == 'max'


# =============================================================================
# Pending role surfacing (registry is not hidden)
# =============================================================================


def test_pending_role_surfaced_not_hidden():
    """Every registered role key validates and resolves — wizard surfaces them in the registry walk."""
    with PlanContext() as ctx:
        # phase-2 in the new registry corresponds to the legacy 'phase_refine'.
        _seed_marshal(ctx.fixture_dir, {'roles': {'phase-2': 'medium'}})

        result = cmd_models(Namespace(role='phase-2', phase=None, default=False))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        # No "unknown role" warning — phase-2 is a known registered role.
        assert 'warnings' not in result


def test_unknown_role_warns_does_not_block_save():
    """Unknown roles warn (not error) so a renamed registry doesn't break saved configs."""
    with PlanContext() as ctx:
        _seed_marshal(ctx.fixture_dir, {'default': 'high'})

        result = cmd_models(Namespace(role='legacy_renamed_role'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'  # falls through to default
        assert 'warnings' in result
        assert any('not registered' in w for w in result['warnings'])


# =============================================================================
# Clear-all (Step 3c equivalent — remove models block entirely)
# =============================================================================


def test_clear_models_block_reverts_to_inherit():
    """Removing the models block restores `inherit` everywhere."""
    with PlanContext() as ctx:
        # Step 1: seed a configured block.
        marshal_path = _seed_marshal(
            ctx.fixture_dir, {'default': 'high', 'roles': {'research': 'xxhigh'}}
        )
        # Step 2: simulate "clear all" by re-writing without the models block.
        cleared = json.loads(marshal_path.read_text(encoding='utf-8'))
        cleared.pop('models', None)
        marshal_path.write_text(json.dumps(cleared, indent=2), encoding='utf-8')

        # Step 3: every resolver call returns inherit / implicit_default.
        for role in ('research', 'q_gate_validation', 'phase_init'):
            result = cmd_models(Namespace(role=role))
            assert result['status'] == 'success'
            assert result['level'] == 'inherit'
            assert result['source'] == 'implicit_default'
