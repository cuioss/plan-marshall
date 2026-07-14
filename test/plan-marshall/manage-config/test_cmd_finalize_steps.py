#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    assert spec is not None and spec.loader is not None
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
    section: dict = config.get('plan', {}).get('phase-6-finalize', {})
    return section


# ``apply-preset`` persists ``plan.phase-6-finalize.steps`` in the canonical
# keyed-map form: an id-keyed object ``{step_id: {params}}`` (``{}`` for a
# config-less step) whose key insertion order is the execution order. These
# helpers extract the ordered id list and a single step's nested param object
# from that keyed map.


def _step_ids(steps_map: dict) -> list:
    """Return the ordered step-id list from a keyed-map steps object."""
    return list(steps_map.keys())


def _params_for(steps_map: dict, step_id: str):
    """Return the param object for ``step_id`` (``{}`` for config-less steps)."""
    return steps_map[step_id]


# ``apply-preset`` sorts the preset's step list ascending by resolved
# frontmatter ``order`` before persisting. The discovery-driven
# ``FinalizeStepPresets.get('full')`` already returns the ``full`` preset's
# members sorted ascending by ``(order, name)`` — the same ordering apply-preset
# produces — so the persisted keyed-map ids equal ``get('full')``. The members
# (least ➜ most coverage) put ``plan-marshall:plan-retrospective`` (order=995)
# before ``default:record-metrics`` (998 — the LAST token-accounting step, after
# retrospective folds its token spend into the phase row) before
# ``default:archive-plan`` (1000). Derived from the discovery query (no
# hand-maintained literal) so a future ``order`` / ``presets`` frontmatter change
# is reflected automatically.
_FULL_SORTED: list[str] = FinalizeStepPresets.get('full')


# =============================================================================
# (1) apply-preset writes the expected steps list per preset
# =============================================================================


def test_apply_preset_local_writes_local_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    assert result['status'] == 'success'
    assert result['preset'] == 'local'
    assert result['steps_count'] == len(FinalizeStepPresets.get('local'))

    section = _read_finalize_section(plan_context.fixture_dir)
    # steps persists as the canonical keyed-map form; key insertion order is the
    # execution order.
    assert isinstance(section['steps'], dict)
    assert _step_ids(section['steps']) == FinalizeStepPresets.get('local')


def test_apply_preset_standard_writes_standard_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    assert result['status'] == 'success'
    section = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(section['steps'], dict)
    assert _step_ids(section['steps']) == FinalizeStepPresets.get('standard')


def test_apply_preset_full_writes_full_steps_sorted(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))

    assert result['status'] == 'success'
    assert result['steps_count'] == len(FinalizeStepPresets.get('full'))
    section = _read_finalize_section(plan_context.fixture_dir)
    # The persisted keyed-map's ids are the FULL preset sorted ascending by
    # frontmatter order — same membership, ascending order (plan-retrospective
    # before archive-plan), not the literal constant order.
    assert isinstance(section['steps'], dict)
    assert _step_ids(section['steps']) == _FULL_SORTED
    assert set(_step_ids(section['steps'])) == set(FinalizeStepPresets.get('full'))


# =============================================================================
# (2) Sibling phase-6 knobs are preserved across the write
# =============================================================================


def test_apply_preset_preserves_sibling_phase6_knobs(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    # Sanity: the fixture carries a flat phase-level knob and a nested step param
    # we expect to survive. review_bot_buffer_seconds now nests under
    # plan-marshall:automatic-review inside the keyed-map steps structure.
    before = _read_finalize_section(plan_context.fixture_dir)
    assert before['max_iterations'] == 3
    # The seed is the keyed map (dict); the param-bearing step nests its
    # params under the step id.
    assert before['steps']['plan-marshall:automatic-review']['review_bot_buffer_seconds'] == 300

    cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    after = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(after['steps'], dict)
    assert _step_ids(after['steps']) == FinalizeStepPresets.get('standard')
    # Flat phase-level knob untouched by the steps write.
    assert after['max_iterations'] == 3
    # The nested step param is preserved across the keyed-map rewrite (the
    # writer reads existing per-step params through `_steps_map` and carries
    # them over for steps the preset keeps).
    assert _params_for(after['steps'], 'plan-marshall:automatic-review') == {
        'review_bot_buffer_seconds': 300
    }


# =============================================================================
# (2b) keyed-map on-disk input — write keyed map + preserve params (no drop)
# =============================================================================
#
# These lock the apply-preset param-preservation contract: the writer (a)
# persists the canonical keyed-map form, and (b) reads existing per-step params
# through `_steps_map` so an existing config's params are NOT dropped.


def _seed_finalize_steps_map(fixture_dir: Path, steps_map: dict) -> None:
    """Overwrite ``plan.phase-6-finalize.steps`` on disk with a keyed-map value."""
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.setdefault('plan', {}).setdefault('phase-6-finalize', {})['steps'] = steps_map
    marshal_path.write_text(json.dumps(config), encoding='utf-8')


def test_apply_preset_writes_keyed_map_form_to_disk(plan_context):
    """apply-preset persists ``plan.phase-6-finalize.steps`` as the canonical keyed map.

    The default fixture seeds the keyed map; after apply-preset the on-disk value
    is still a JSON object (keyed-map form), with config-less steps mapping to
    {} — proving the writer persists the keyed map directly.
    """
    create_marshal_json(plan_context.fixture_dir)

    # Precondition: the seed is the keyed map (dict) on disk.
    before = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(before['steps'], dict)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))
    assert result['status'] == 'success'

    section = _read_finalize_section(plan_context.fixture_dir)
    # Persisted as the canonical keyed map (a dict, not a list).
    assert isinstance(section['steps'], dict)
    # Same membership/order as LOCAL.
    assert _step_ids(section['steps']) == FinalizeStepPresets.get('local')
    # The seed carries no params on push, so it maps to an empty {}.
    assert 'default:push' in section['steps']
    assert _params_for(section['steps'], 'default:push') == {}
    # branch-cleanup carried params in the keyed-map seed, so it keeps its nested
    # param object.
    assert _params_for(section['steps'], 'default:branch-cleanup') == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }


def test_apply_preset_preserves_params_from_existing_keyed_map(plan_context):
    """apply-preset preserves existing per-step params from the on-disk keyed map.

    This is the param-preservation guard: the writer must read existing params
    through `_steps_map`. With a keyed-map existing config carrying params on
    ``default:branch-cleanup``, applying a preset that KEEPS that step must carry
    the params over.
    """
    create_marshal_json(plan_context.fixture_dir)
    # Replace the seeded keyed-map with one carrying params on a step every preset
    # retains (branch-cleanup is in LOCAL/STANDARD/FULL).
    _seed_finalize_steps_map(
        plan_context.fixture_dir,
        {
            'default:push': {},
            'default:branch-cleanup': {
                'pr_merge_strategy': 'rebase',
                'final_merge_without_asking': True,
            },
            'default:archive-plan': {},
        },
    )

    # Precondition: the existing on-disk config is the keyed map (a dict).
    before = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(before['steps'], dict)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))
    assert result['status'] == 'success'

    section = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(section['steps'], dict)
    # The preset's full step set is written, in keyed-map form.
    assert _step_ids(section['steps']) == FinalizeStepPresets.get('local')
    # The existing params on the retained step survived the rewrite —
    # NOT dropped (the param-preservation contract this test guards).
    assert _params_for(section['steps'], 'default:branch-cleanup') == {
        'pr_merge_strategy': 'rebase',
        'final_merge_without_asking': True,
    }


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
    assert isinstance(second['steps'], dict)
    assert _step_ids(second['steps']) == _FULL_SORTED


def test_apply_preset_overwrites_previous_preset(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    section = _read_finalize_section(plan_context.fixture_dir)
    # No residue from FULL — the keyed map's ids are exactly LOCAL.
    assert isinstance(section['steps'], dict)
    assert _step_ids(section['steps']) == FinalizeStepPresets.get('local')


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
    assert isinstance(section['steps'], dict)
    assert _step_ids(section['steps']) == _FULL_SORTED


# =============================================================================
# (6) Auto-sort — persisted steps are ascending by resolved frontmatter order
# =============================================================================


def test_apply_preset_persists_steps_in_ascending_frontmatter_order(plan_context):
    """apply-preset sorts the preset's steps ascending by frontmatter order.

    The persisted ``plan.phase-6-finalize.steps`` must be ascending by resolved
    frontmatter ``order``, which places ``plan-marshall:plan-retrospective``
    (order=995) before ``default:record-metrics`` (998) before
    ``default:archive-plan`` (1000). The discovery-driven preset membership is
    already order-sorted, so the persisted ids equal ``get('full')`` — this test
    independently re-resolves the persisted ids' orders to prove ascendance.
    """
    _resolve_step_orders = _cmd_mod._resolve_step_orders

    create_marshal_json(plan_context.fixture_dir)
    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    assert result['status'] == 'success'

    persisted_steps = _read_finalize_section(plan_context.fixture_dir)['steps']
    assert isinstance(persisted_steps, dict)
    persisted_ids = _step_ids(persisted_steps)
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
