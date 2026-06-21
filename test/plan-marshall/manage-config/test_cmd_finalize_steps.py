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


# ``apply-preset`` persists ``plan.phase-6-finalize.steps`` in the canonical LIST
# serial form: a JSON array whose elements are bare strings (ownerless steps) or
# single-key objects ``{step_id: {params}}`` (param-bearing steps). Array order is
# the execution order. These helpers extract the ordered id list and a single
# step's nested param object from that LIST form.


def _step_ids(steps_list: list) -> list:
    """Return the ordered step-id list from a LIST-form steps array."""
    ids = []
    for element in steps_list:
        if isinstance(element, str):
            ids.append(element)
        elif isinstance(element, dict) and len(element) == 1:
            ids.append(next(iter(element)))
    return ids


def _params_for(steps_list: list, step_id: str):
    """Return a step's params from a LIST-form steps array.

    Returns the nested param dict for a param-bearing single-key object, or
    ``None`` for an ownerless bare-string element. Raises ``KeyError`` when the
    step id is absent.
    """
    for element in steps_list:
        if isinstance(element, str) and element == step_id:
            return None
        if isinstance(element, dict) and len(element) == 1 and step_id in element:
            return element[step_id]
    raise KeyError(step_id)


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
    # steps persists as the canonical LIST serial form; array order is the
    # execution order.
    assert isinstance(section['steps'], list)
    assert _step_ids(section['steps']) == FinalizeStepPresets.LOCAL


def test_apply_preset_standard_writes_standard_steps(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    assert result['status'] == 'success'
    section = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(section['steps'], list)
    assert _step_ids(section['steps']) == FinalizeStepPresets.STANDARD


def test_apply_preset_full_writes_full_steps_sorted(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='full'))

    assert result['status'] == 'success'
    assert result['steps_count'] == len(FinalizeStepPresets.FULL)
    section = _read_finalize_section(plan_context.fixture_dir)
    # The persisted LIST's ids are the FULL preset sorted ascending by
    # frontmatter order — same membership, ascending order (plan-retrospective
    # before archive-plan), not the literal constant order.
    assert isinstance(section['steps'], list)
    assert _step_ids(section['steps']) == _FULL_SORTED
    assert set(_step_ids(section['steps'])) == set(FinalizeStepPresets.FULL)


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
    # The seed is the legacy keyed-map (dict); the param-bearing step nests its
    # params under the step id.
    assert before['steps']['default:automated-review']['review_bot_buffer_seconds'] == 300

    cmd_finalize_steps_apply_preset(Namespace(preset='standard'))

    after = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(after['steps'], list)
    assert _step_ids(after['steps']) == FinalizeStepPresets.STANDARD
    # Flat phase-level knob untouched by the steps write.
    assert after['max_iterations'] == 3
    # The nested step param is preserved across the LIST-form rewrite (the
    # writer reads existing per-step params through the dual-form reader and
    # carries them over for steps the preset keeps).
    assert _params_for(after['steps'], 'default:automated-review') == {
        'review_bot_buffer_seconds': 300
    }


# =============================================================================
# (2b) LIST-form on-disk input — write LIST form + preserve params (no drop)
# =============================================================================
#
# These lock the Deliverable-3 apply-preset fix: the writer (a) emits the
# canonical LIST serial form via `keyed_map_to_list_form`, and (b) reads
# existing per-step params through the dual-form reader so a LIST-form existing
# config is NOT dropped. Before the fix, a plain `isinstance(existing, dict)`
# check silently dropped every per-step param when the on-disk `steps` value was
# already a LIST — the param-drop regression these tests guard against.


def _seed_list_form_finalize_steps(fixture_dir: Path, steps_list: list) -> None:
    """Overwrite ``plan.phase-6-finalize.steps`` on disk with a LIST-form value."""
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.setdefault('plan', {}).setdefault('phase-6-finalize', {})['steps'] = steps_list
    marshal_path.write_text(json.dumps(config), encoding='utf-8')


def test_apply_preset_writes_list_form_to_disk(plan_context):
    """apply-preset persists ``plan.phase-6-finalize.steps`` as the canonical LIST form.

    The default fixture seeds the legacy keyed-map; after apply-preset the
    on-disk value is a JSON array (LIST form), with ownerless steps as bare
    strings — proving the writer emits the canonical serial form via
    ``keyed_map_to_list_form`` rather than re-persisting the keyed map.
    """
    create_marshal_json(plan_context.fixture_dir)

    # Precondition: the seed is the legacy keyed-map (dict) on disk.
    before = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(before['steps'], dict)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))
    assert result['status'] == 'success'

    section = _read_finalize_section(plan_context.fixture_dir)
    # Persisted as the canonical LIST form (a list, not a dict).
    assert isinstance(section['steps'], list)
    # Same membership/order as LOCAL.
    assert _step_ids(section['steps']) == FinalizeStepPresets.LOCAL
    # The seed carries no params on commit-push, so it persists as a bare string
    # (no noisy {step_id: {}} object — empty-{} suppression).
    assert 'default:commit-push' in section['steps']
    assert _params_for(section['steps'], 'default:commit-push') is None
    # branch-cleanup carried params in the keyed-map seed, so it survives the
    # migration as a param-bearing single-key object in the LIST form.
    assert _params_for(section['steps'], 'default:branch-cleanup') == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }


def test_apply_preset_preserves_params_when_existing_config_is_list_form(plan_context):
    """apply-preset preserves existing per-step params when the on-disk config is already LIST form.

    This is the param-drop regression guard: the writer must read existing params
    through the dual-form reader. With a LIST-form existing config carrying params
    on ``default:branch-cleanup``, applying a preset that KEEPS that step must
    carry the params over — a plain ``isinstance(existing, dict)`` check would
    have dropped them because the existing value is a LIST.
    """
    create_marshal_json(plan_context.fixture_dir)
    # Replace the seeded keyed-map with a LIST-form value carrying params on a
    # step every preset retains (branch-cleanup is in LOCAL/STANDARD/FULL).
    _seed_list_form_finalize_steps(
        plan_context.fixture_dir,
        [
            'default:commit-push',
            {
                'default:branch-cleanup': {
                    'pr_merge_strategy': 'rebase',
                    'final_merge_without_asking': True,
                }
            },
            'default:archive-plan',
        ],
    )

    # Precondition: the existing on-disk config is the LIST form (a list).
    before = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(before['steps'], list)

    result = cmd_finalize_steps_apply_preset(Namespace(preset='local'))
    assert result['status'] == 'success'

    section = _read_finalize_section(plan_context.fixture_dir)
    assert isinstance(section['steps'], list)
    # The preset's full step set is written, in LIST form.
    assert _step_ids(section['steps']) == FinalizeStepPresets.LOCAL
    # The existing params on the retained step survived the LIST-form rewrite —
    # NOT dropped (the param-drop regression this test guards).
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
    assert isinstance(second['steps'], list)
    assert _step_ids(second['steps']) == _FULL_SORTED


def test_apply_preset_overwrites_previous_preset(plan_context):
    create_marshal_json(plan_context.fixture_dir)

    cmd_finalize_steps_apply_preset(Namespace(preset='full'))
    cmd_finalize_steps_apply_preset(Namespace(preset='local'))

    section = _read_finalize_section(plan_context.fixture_dir)
    # No residue from FULL — the LIST's ids are exactly LOCAL.
    assert isinstance(section['steps'], list)
    assert _step_ids(section['steps']) == FinalizeStepPresets.LOCAL


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
    assert isinstance(section['steps'], list)
    assert _step_ids(section['steps']) == _FULL_SORTED


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

    persisted_steps = _read_finalize_section(plan_context.fixture_dir)['steps']
    assert isinstance(persisted_steps, list)
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
