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
# is declared with ``record-metrics`` and ``archive-plan`` ahead of
# ``plan-marshall:plan-retrospective`` in the literal constant, but the
# resolved frontmatter orders put them in a different sequence:
# ``plan-marshall:plan-retrospective`` (order=995), then
# ``default:record-metrics`` (order=998 — it is the LAST token-accounting
# step, so it runs after retrospective folds its token spend into the phase
# row), then ``default:archive-plan`` (order=1000). The persisted order thus
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
    'plan-marshall:plan-retrospective',
    'default:record-metrics',
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
    # steps is an id-keyed map; key insertion order is the execution order.
    assert list(section['steps'].keys()) == FinalizeStepPresets.LOCAL


def test_apply_preset_standard_writes_standard_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    assert result['status'] == 'success'
    section = _read_finalize_section(plan_context.fixture_dir)
    assert list(section['steps'].keys()) == FinalizeStepPresets.STANDARD


def test_apply_preset_full_writes_full_steps_sorted(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))

    assert result['status'] == 'success'
    assert result['steps_count'] == len(FinalizeStepPresets.FULL)
    section = _read_finalize_section(plan_context.fixture_dir)
    # The persisted keyed map's keys are the FULL preset sorted ascending by
    # frontmatter order — same membership, ascending order (plan-retrospective
    # before archive-plan), not the literal constant order.
    assert list(section['steps'].keys()) == _FULL_SORTED
    assert set(section['steps'].keys()) == set(FinalizeStepPresets.FULL)


# =============================================================================
# (2) Sibling phase-6 knobs are preserved across the write
# =============================================================================


def test_apply_preset_preserves_sibling_phase6_knobs(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    # Sanity: the fixture carries a flat phase-level knob and a nested step param
    # we expect to survive. review_bot_buffer_seconds now nests under
    # default:automated-review inside the keyed-map steps structure.
    before = _read_finalize_section(plan_context.fixture_dir)
    assert before['max_iterations'] == 3
    assert before['steps']['default:automated-review']['review_bot_buffer_seconds'] == 300

    cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    after = _read_finalize_section(plan_context.fixture_dir)
    assert list(after['steps'].keys()) == FinalizeStepPresets.STANDARD
    # Flat phase-level knob untouched by the steps write.
    assert after['max_iterations'] == 3
    # The nested step param is preserved across the keyed-map rewrite (the
    # writer carries over existing per-step params for steps the preset keeps).
    assert after['steps']['default:automated-review']['review_bot_buffer_seconds'] == 300


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
    assert list(second['steps'].keys()) == _FULL_SORTED


def test_apply_preset_overwrites_previous_preset(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    section = _read_finalize_section(plan_context.fixture_dir)
    # No residue from FULL — the steps map keys are exactly LOCAL.
    assert list(section['steps'].keys()) == FinalizeStepPresets.LOCAL


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
    assert list(section['steps'].keys()) == _FULL_SORTED


# =============================================================================
# (6) Auto-sort — persisted steps are ascending by resolved frontmatter order
# =============================================================================


def test_apply_preset_persists_steps_in_ascending_frontmatter_order(plan_context):
    """apply-preset sorts the preset's steps ascending by frontmatter order.

    The FULL preset is declared with ``default:record-metrics`` and
    ``default:archive-plan`` ahead of ``plan-marshall:plan-retrospective``
    (order=995). Before the auto-sort, that out-of-order group would persist
    verbatim into ``plan.phase-6-finalize.steps`` — exactly the durability
    gap this deliverable closes. After the sort, the persisted list must be
    ascending, which places ``plan-marshall:plan-retrospective`` (995) before
    ``default:record-metrics`` (998) before ``default:archive-plan`` (1000).
    """
    _resolve_step_orders = _cmd_mod._resolve_step_orders

    create_marshal_json(plan_context.fixture_dir)
    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    assert result['status'] == 'success'

    persisted_ids = list(_read_finalize_section(plan_context.fixture_dir)['steps'].keys())
    resolved, err = _resolve_step_orders(persisted_ids, 'phase-6-finalize')
    assert err is None
    orders = [order for _, order in resolved]
    assert orders == sorted(orders), (
        f'persisted phase-6-finalize.steps are not ascending by order: {orders}'
    )
    # Concretely: plan-retrospective (995) precedes record-metrics (998),
    # which precedes archive-plan (1000) — record-metrics is the last
    # token-accounting step, after retrospective and before the read-only tail.
    assert persisted_ids.index('plan-marshall:plan-retrospective') < persisted_ids.index(
        'default:record-metrics'
    )
    assert persisted_ids.index('default:record-metrics') < persisted_ids.index(
        'default:archive-plan'
    )


# =============================================================================
# (7) Malformed (non-dict) plan block returns a structured error, not a crash
# =============================================================================
#
# `config['plan']` is sourced from a hand-editable marshal.json. The preset
# writer treats it as a dict (`setdefault(_PHASE_SECTION, {})`). A non-dict
# `plan` block must produce a structured `status: error` rather than crashing
# with an AttributeError — the Pattern B2 isinstance-guard contract.


def _marshal_with_plan_block(plan_value) -> dict:
    """Return a minimal valid marshal.json config with `plan` set to `plan_value`."""
    return {
        'skill_domains': {},
        'system': {'retention': {'logs_days': 1}},
        'plan': plan_value,
        'providers': [],
    }


def test_apply_preset_non_dict_plan_block_returns_structured_error(plan_context):
    """A list-valued `config['plan']` yields status: error, not an AttributeError."""
    create_marshal_json(
        plan_context.fixture_dir,
        config=_marshal_with_plan_block(['not', 'a', 'dict']),
    )

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    assert result['status'] == 'error'
    assert 'plan block' in result['error']
    assert 'not a dict' in result['error']


def test_apply_preset_string_plan_block_returns_structured_error(plan_context):
    """A string-valued `config['plan']` is also caught by the isinstance guard."""
    create_marshal_json(
        plan_context.fixture_dir,
        config=_marshal_with_plan_block('totally-wrong'),
    )

    result = cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    assert result['status'] == 'error'
    assert 'plan block' in result['error']
