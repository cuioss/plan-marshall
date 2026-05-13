#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the marshall-steward Effort submenu round-trip.

The Effort submenu is a markdown-driven wizard step that calls
``manage-config effort read --role`` for resolution and writes the
``models`` block of ``marshal.json``. The wizard contract lives in
``marshall-steward/standards/effort-menu.md``; this test suite pins
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
    '_cmd_effort', _MANAGE_CONFIG_SCRIPTS_DIR / '_cmd_effort.py'
)
cmd_effort = _cmd_models_mod.cmd_effort


def _seed_marshal(plan_dir: Path, models: dict | None) -> Path:
    """Write a minimal marshal.json with optional effort config.

    Accepts the legacy-shape ``{"default": <level>, "roles": {<phase>: ...}}``
    payload for backwards-compat in test bodies, and translates it to the
    current per-phase storage shape (``plan.<phase>.effort`` + top-level
    ``effort``) on disk.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    config: dict = {'plan': {}}
    if models is not None:
        default = models.get('default')
        if default is not None:
            config['effort'] = default
        for phase, value in models.get('roles', {}).items():
            config['plan'].setdefault(phase, {})['effort'] = value
    marshal_path = plan_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return marshal_path


def _read_models_block(plan_dir: Path) -> dict:
    """Reconstruct the legacy ``{"default": …, "roles": {…}}`` view from
    the current per-phase storage so existing test bodies keep asserting
    the same shape without re-implementing the inverse transform inline.
    """
    config = json.loads((plan_dir / 'marshal.json').read_text(encoding='utf-8'))
    result: dict = {}
    if 'effort' in config:
        result['default'] = config['effort']
    plan_block = config.get('plan', {})
    roles: dict = {}
    for phase, entry in plan_block.items():
        if isinstance(entry, dict) and 'effort' in entry:
            roles[phase] = entry['effort']
    if roles:
        result['roles'] = roles
    return result


# =============================================================================
# Round-trip: write → resolve → re-read
# =============================================================================


def test_round_trip_default_and_role_persist():
    """Set default=medium and roles.phase-6-finalize.verification-feedback=high; resolver returns saved values."""
    with PlanContext() as ctx:
        _seed_marshal(
            ctx.fixture_dir,
            {
                'default': 'medium',
                'roles': {'phase-6-finalize': {'verification-feedback': 'high'}},
            },
        )

        result_role = cmd_effort(
            Namespace(role='phase-6-finalize.verification-feedback', phase=None, default=False)
        )
        result_other = cmd_effort(
            Namespace(role='phase-3-outline', phase=None, default=False)
        )

        assert result_role['status'] == 'success'
        assert result_role['level'] == 'high'
        assert result_role['source'] == 'plan.phase-6-finalize.effort.verification-feedback'

        assert result_other['status'] == 'success'
        assert result_other['level'] == 'medium'
        assert result_other['source'] == 'effort'

        # Re-read marshal.json — stored block matches what the wizard would have written.
        block = _read_models_block(ctx.fixture_dir)
        assert block == {
            'default': 'medium',
            'roles': {'phase-6-finalize': {'verification-feedback': 'high'}},
        }


def test_round_trip_repeated_reads_do_not_mutate():
    """Multiple `manage-config effort read` invocations leave marshal.json byte-identical."""
    with PlanContext() as ctx:
        marshal_path = _seed_marshal(
            ctx.fixture_dir, {'default': 'low', 'roles': {'research': 'xxhigh'}}
        )
        before = marshal_path.read_bytes()

        for role in ('research', 'q_gate_validation', 'phase_init'):
            cmd_effort(Namespace(role=role))

        after = marshal_path.read_bytes()
        assert before == after, 'wizard reads must not mutate marshal.json'


# =============================================================================
# Validation: refuse invalid levels (wizard "never lets user save invalid")
# =============================================================================


def test_invalid_level_refused_at_read():
    """`plan.phase-6-finalize.effort.verification-feedback = 'ultra'` errors out — wizard refuses save."""
    with PlanContext() as ctx:
        _seed_marshal(
            ctx.fixture_dir,
            {'roles': {'phase-6-finalize': {'verification-feedback': 'ultra'}}},
        )

        result = cmd_effort(
            Namespace(role='phase-6-finalize.verification-feedback', phase=None, default=False)
        )

        assert result['status'] == 'error'
        assert "invalid effort 'ultra'" in result['error']
        # The error names the source so the wizard can re-prompt with context.
        assert 'plan.phase-6-finalize.effort.verification-feedback' in result['error']


def test_max_level_resolves_via_top_level_effort():
    """`max` is a live level (promoted from reserved-future); resolves cleanly via top-level effort."""
    with PlanContext() as ctx:
        _seed_marshal(ctx.fixture_dir, {'default': 'max'})

        result = cmd_effort(Namespace(role='phase-3-outline'))

        assert result['status'] == 'success'
        assert result['level'] == 'max'


# =============================================================================
# Pending role surfacing (registry is not hidden)
# =============================================================================


def test_pending_role_surfaced_not_hidden():
    """Every registered role key validates and resolves — wizard surfaces them in the registry walk."""
    with PlanContext() as ctx:
        # phase-2-refine in the new registry corresponds to the legacy 'phase_refine'.
        _seed_marshal(ctx.fixture_dir, {'roles': {'phase-2-refine': 'medium'}})

        result = cmd_effort(Namespace(role='phase-2-refine', phase=None, default=False))

        assert result['status'] == 'success'
        assert result['level'] == 'medium'
        # No "unknown role" warning — phase-2-refine is a known registered role.
        assert 'warnings' not in result


def test_unknown_role_warns_does_not_block_save():
    """Unknown roles warn (not error) so a renamed registry doesn't break saved configs."""
    with PlanContext() as ctx:
        _seed_marshal(ctx.fixture_dir, {'default': 'high'})

        result = cmd_effort(Namespace(role='legacy_renamed_role'))

        assert result['status'] == 'success'
        assert result['level'] == 'high'  # falls through to default
        assert 'warnings' in result
        assert any('not registered' in w for w in result['warnings'])


# =============================================================================
# Clear-all (Step 3c equivalent — remove models block entirely)
# =============================================================================


def test_clear_effort_config_reverts_to_inherit():
    """Removing every effort field restores `inherit` everywhere."""
    with PlanContext() as ctx:
        # Step 1: seed a configured block.
        marshal_path = _seed_marshal(
            ctx.fixture_dir, {'default': 'high', 'roles': {'phase-3-outline': 'xxhigh'}}
        )
        # Step 2: simulate "clear all" by removing the top-level effort plus
        # every per-phase effort attribute.
        cleared = json.loads(marshal_path.read_text(encoding='utf-8'))
        cleared.pop('effort', None)
        for phase_entry in cleared.get('plan', {}).values():
            if isinstance(phase_entry, dict):
                phase_entry.pop('effort', None)
        marshal_path.write_text(json.dumps(cleared, indent=2), encoding='utf-8')

        # Step 3: every resolver call returns inherit / implicit_default.
        for role in ('phase-2-refine', 'phase-3-outline', 'phase-6-finalize'):
            result = cmd_effort(Namespace(role=role))
            assert result['status'] == 'success'
            assert result['level'] == 'inherit'
            assert result['source'] == 'implicit_default'
