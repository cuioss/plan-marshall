#!/usr/bin/env python3
"""Tests for `manage-config finalize-steps apply-preset --preset <name>` write subcommand.

Covers the writer end-to-end:

1. ``apply-preset --preset local|standard|full`` writes the expected
   ``plan.phase-6-finalize.steps`` list.
2. Sibling phase-6 knobs (``max_iterations``, ``review_bot_buffer_seconds``)
   are preserved across the write.
3. The writer is idempotent — applying the same preset twice yields the
   same on-disk state.
4. A bogus preset is rejected at the argparse layer (exit code 2) with the
   valid names surfaced in the error.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH, create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

# `_cmd_finalize_steps` imports `finalize_step_presets` and `_config_defaults`
# at module level. Make sure the manage-config scripts directory is importable
# BEFORE we load the handler module.
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_presets_mod = _load_module(
    'finalize_step_presets', 'finalize_step_presets.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
FinalizeStepPresets = _presets_mod.FinalizeStepPresets

_cmd_mod = _load_module(
    '_cmd_finalize_steps', '_cmd_finalize_steps.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
cmd_finalize_steps_apply_preset = _cmd_mod.cmd_finalize_steps_apply_preset

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402


def _read_finalize_section(fixture_dir: Path) -> dict:
    """Return the on-disk ``plan.phase-6-finalize`` section."""
    config = json.loads((fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    return config.get('plan', {}).get('phase-6-finalize', {})


# ``apply-preset`` sorts the preset's step list ascending by resolved
# frontmatter ``order`` before persisting (Deliverable 3). The FULL preset
# is declared with ``archive-plan`` (order=1000) ahead of
# ``plan-marshall:plan-retrospective`` (order=995), so the persisted order
# differs from the literal ``FinalizeStepPresets.FULL`` constant. LOCAL and
# STANDARD are already in ascending order, so the sort is a no-op for them.
_FULL_SORTED: list[str] = [
    'default:pre-push-quality-gate',
    'default:commit-push',
    'default:create-pr',
    'default:ci-verify',
    'default:automated-review',
    'default:sonar-roundtrip',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:record-metrics',
    'plan-marshall:plan-retrospective',
    'default:archive-plan',
]


# =============================================================================
# (1) apply-preset writes the expected steps list per preset
# =============================================================================


def test_apply_preset_local_writes_local_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    assert result['status'] == 'success'
    assert result['preset'] == 'local'
    assert result['steps_count'] == len(FinalizeStepPresets.LOCAL)

    section = _read_finalize_section(plan_context.fixture_dir)
    assert section['steps'] == FinalizeStepPresets.LOCAL


def test_apply_preset_standard_writes_standard_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    assert result['status'] == 'success'
    section = _read_finalize_section(plan_context.fixture_dir)
    assert section['steps'] == FinalizeStepPresets.STANDARD


def test_apply_preset_full_writes_full_steps_sorted(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))

    assert result['status'] == 'success'
    assert result['steps_count'] == len(FinalizeStepPresets.FULL)
    section = _read_finalize_section(plan_context.fixture_dir)
    # The persisted list is the FULL preset sorted ascending by frontmatter
    # order — same membership, ascending order (plan-retrospective before
    # archive-plan), not the literal constant order.
    assert section['steps'] == _FULL_SORTED
    assert set(section['steps']) == set(FinalizeStepPresets.FULL)


# =============================================================================
# (2) Sibling phase-6 knobs are preserved across the write
# =============================================================================


def test_apply_preset_preserves_sibling_phase6_knobs(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    # Sanity: the fixture carries non-step knobs we expect to survive.
    before = _read_finalize_section(plan_context.fixture_dir)
    assert before['max_iterations'] == 3
    assert before['review_bot_buffer_seconds'] == 300

    cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    after = _read_finalize_section(plan_context.fixture_dir)
    assert after['steps'] == FinalizeStepPresets.STANDARD
    # Sibling knobs untouched by the steps write.
    assert after['max_iterations'] == 3
    assert after['review_bot_buffer_seconds'] == 300


# =============================================================================
# (3) Idempotency — applying the same preset twice yields the same state
# =============================================================================


def test_apply_preset_is_idempotent(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    first = _read_finalize_section(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    second = _read_finalize_section(plan_context.fixture_dir)

    assert first == second
    assert second['steps'] == _FULL_SORTED


def test_apply_preset_overwrites_previous_preset(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    section = _read_finalize_section(plan_context.fixture_dir)
    # No residue from FULL — the steps list is exactly LOCAL.
    assert section['steps'] == FinalizeStepPresets.LOCAL


# =============================================================================
# (4) Bogus preset rejected at the argparse layer
# =============================================================================


def test_apply_preset_bogus_rejected_by_argparse(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH, 'finalize-steps', 'apply-preset', '--preset', 'bogus'
    )

    assert not result.success, 'argparse should reject unknown preset'
    combined = (result.stdout + result.stderr).lower()
    assert 'local' in combined
    assert 'standard' in combined
    assert 'full' in combined


# =============================================================================
# (5) Case-insensitive alias resolves past the handler
# =============================================================================


def test_apply_preset_uppercase_alias_succeeds(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='FULL'))

    assert result['status'] == 'success'
    section = _read_finalize_section(plan_context.fixture_dir)
    assert section['steps'] == _FULL_SORTED


# =============================================================================
# (6) Auto-sort — persisted steps are ascending by resolved frontmatter order
# =============================================================================


def test_apply_preset_persists_steps_in_ascending_frontmatter_order(plan_context):
    """apply-preset sorts the preset's steps ascending by frontmatter order.

    The FULL preset is declared with ``default:archive-plan`` (order=1000)
    ahead of ``plan-marshall:plan-retrospective`` (order=995). Before the
    auto-sort, that out-of-order pair would persist verbatim into
    ``plan.phase-6-finalize.steps`` — exactly the durability gap this
    deliverable closes. After the sort, the persisted list must be ascending.
    """
    _resolve_step_orders = _cmd_mod._resolve_step_orders

    create_marshal_json(plan_context.fixture_dir)
    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    assert result['status'] == 'success'

    persisted = _read_finalize_section(plan_context.fixture_dir)['steps']
    resolved, err = _resolve_step_orders(persisted, 'phase-6-finalize')
    assert err is None
    orders = [order for _, order in resolved]
    assert orders == sorted(orders), (
        f'persisted phase-6-finalize.steps are not ascending by order: {orders}'
    )
    # Concretely: plan-retrospective (995) must precede archive-plan (1000).
    assert persisted.index('plan-marshall:plan-retrospective') < persisted.index(
        'default:archive-plan'
    )
