#!/usr/bin/env python3
"""Test default-config schema additions for the split-gate / default-base-branch plan.

Covers:
- `DEFAULT_PLAN_FINALIZE` includes `final_merge_without_asking` with default `False`.
- A fresh marshal.json carries `project.default_base_branch == 'main'`.
- The new `project` CLI noun round-trips a custom `default_base_branch`.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_sensible_number():
    """Load the script-shared sensible_number module by explicit path.

    Mirrors the per-file importlib loading used for the manage-config scripts so
    the test does not depend on conftest PYTHONPATH discovery order. The module
    lives under the shared ``script-shared/scripts`` surface.
    """
    shared_dir = (
        Path(__file__).parent.parent.parent.parent
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'script-shared'
        / 'scripts'
    )
    spec = importlib.util.spec_from_file_location(
        '_sensible_number_for_config_defaults_test', shared_dir / 'sensible_number.py'
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['_sensible_number_for_config_defaults_test'] = mod
    spec.loader.exec_module(mod)
    return mod


_sensible_number_mod = _load_sensible_number()
parse_sensible_int = _sensible_number_mod.parse_sensible_int


_config_core_mod = _load_module(
    '_config_core_for_split_gate_test', '_config_core.py'
)
_config_defaults_mod = _load_module(
    '_config_defaults_for_split_gate_test', '_config_defaults.py'
)
_cmd_init_mod = _load_module(
    '_cmd_init_for_split_gate_test', '_cmd_init.py'
)
_cmd_system_plan_mod = _load_module(
    '_cmd_system_plan_for_split_gate_test', '_cmd_system_plan.py'
)
_cmd_quality_phases_mod = _load_module(
    '_cmd_quality_phases_for_simplicity_test', '_cmd_quality_phases.py'
)
_cmd_effort_mod = _load_module(
    '_cmd_effort_for_effort_defaults_test', '_cmd_effort.py'
)


# =============================================================================
# Keyed-map serial-form helpers
# =============================================================================
#
# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical keyed map: an id-keyed object
# `{step_id: {params}}` (`{}` for a config-less step) whose key insertion order
# is the execution order. These helpers extract the ordered id list and a
# single step's nested param object from that keyed map.


def _step_ids(steps_map: dict) -> list:
    """Return the ordered step-id list from a keyed-map steps object.

    Key insertion order is preserved (= execution order).
    """
    return list(steps_map.keys())


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from a keyed-map steps object.

    Returns the step's nested param object (``{}`` for a config-less step).
    Raises ``KeyError`` when the step id is absent so a wrong-id assertion fails
    loudly rather than silently returning ``None``.
    """
    return steps_map[step_id]


def test_finalize_step_params_constant_is_deleted():
    """The centralized _FINALIZE_STEP_PARAMS constant MUST no longer exist.

    Step-owned param defaults are now declared self-describingly in each step's
    `configurable:` body-doc frontmatter and resolved by the
    configurable_contract parser; the centralized constant was deleted.
    """
    assert not hasattr(_config_defaults_mod, '_FINALIZE_STEP_PARAMS'), (
        '_FINALIZE_STEP_PARAMS must be deleted — step-param defaults now resolve '
        'via the configurable_contract parser delegation'
    )


def test_default_plan_finalize_includes_final_merge_without_asking():
    """final_merge_without_asking nests under default:branch-cleanup with default False.

    The knob is a step-owned param of `default:branch-cleanup` in the keyed-map
    `steps` structure (no longer a flat sibling of `steps`). It is resolved via
    the configurable_contract parser delegation, folded into the step's
    nested param object by the get_default_config() finalize-step seed.
    """
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )

    # homed in the branch-cleanup step's nested param object with the False default
    assert 'final_merge_without_asking' in branch_cleanup, (
        'final_merge_without_asking must nest under default:branch-cleanup in the seeded steps map'
    )
    assert branch_cleanup['final_merge_without_asking'] is False, (
        'final_merge_without_asking default must be False '
        '(interactive-by-default: prompt the operator before the final merge; '
        'set True to merge without asking, serialized via the cross-plan merge-lock)'
    )
    # it is NOT a flat sibling of steps anymore
    assert 'final_merge_without_asking' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE, (
        'final_merge_without_asking must not survive as a flat phase-level knob'
    )


def test_default_plan_finalize_simplify_defaults_to_auto():
    """`simplify` folds under its owning step `default:finalize-step-simplify`, default 'auto'.

    `simplify` moved out of its former flat-sibling location into the
    simplify-step's nested param object: `auto` defers to the manifest composer's
    `simplify_inactive` pre-filter, while always/never force the
    finalize-step-simplify step in/out.
    """
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # No longer a flat sibling of `steps`.
    assert 'simplify' not in finalize, (
        'simplify must NOT survive as a flat phase-level field'
    )
    # It is nested under the owning step in the seeded keyed-map `steps` form (the
    # module-level DEFAULT_PLAN_FINALIZE['steps'] is a None placeholder filled
    # lazily by get_default_config()).
    config = _config_defaults_mod.get_default_config()
    simplify_step = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:finalize-step-simplify'
    )
    assert simplify_step['simplify'] == 'auto', (
        "default:finalize-step-simplify.simplify default must be 'auto' "
        '(defer to the simplify_inactive pre-filter)'
    )


def test_get_default_config_includes_finalize_simplify():
    """get_default_config() surfaces simplify nested under its owning finalize step."""
    config = _config_defaults_mod.get_default_config()

    finalize = config['plan']['phase-6-finalize']
    assert 'simplify' not in finalize
    simplify_step = _params_for(finalize['steps'], 'default:finalize-step-simplify')
    assert simplify_step['simplify'] == 'auto'


def test_default_plan_finalize_carries_all_finalize_gates():
    """The three finalize gates default to 'auto' at their respective homes.

    `qgate` stays a flat phase-level sibling; `simplify` / `self_review` fold
    under their owning finalize step's nested param object.
    """
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # qgate stays a flat phase-level sibling.
    assert finalize.get('qgate') == 'auto', (
        'plan.phase-6-finalize.qgate default must be auto'
    )
    # simplify folds under its owning step in the seeded keyed-map `steps` form.
    config = _config_defaults_mod.get_default_config()
    seeded_steps = config['plan']['phase-6-finalize']['steps']
    assert _params_for(seeded_steps, 'default:finalize-step-simplify')['simplify'] == 'auto'
    # self_review is owned by the project-only pre-submission-self-review step,
    # which is NOT a built-in candidate, so it is absent from the seed; its
    # default resolves directly via the configurable_contract parser.
    from configurable_contract import resolve_step_defaults  # type: ignore[import-not-found]

    self_review_defaults = resolve_step_defaults(
        'project:finalize-step-pre-submission-self-review'
    )
    assert self_review_defaults['self_review'] == 'auto'


def test_validate_run_at_all_accepts_simplify_run_at_all_values():
    """validate_run_at_all must accept every auto|always|never value for the simplify gate."""
    # no exception for any allowed run-at-all value
    for value in _config_defaults_mod.VALID_RUN_AT_ALL:
        _config_defaults_mod.validate_run_at_all(value, 'plan.phase-6-finalize.simplify')


def test_validate_run_at_all_rejects_invalid_simplify_value():
    """validate_run_at_all must raise ValueError for a simplify value outside the enum."""
    import pytest

    with pytest.raises(ValueError, match=r'plan\.phase-6-finalize\.simplify'):
        _config_defaults_mod.validate_run_at_all('sometimes', 'plan.phase-6-finalize.simplify')


def test_default_plan_finalize_includes_auto_rebase_threshold():
    """auto_rebase_threshold nests under default:branch-cleanup with default 'no_overlap_only'."""
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )

    assert 'auto_rebase_threshold' in branch_cleanup, (
        'auto_rebase_threshold must nest under default:branch-cleanup in the seeded steps list'
    )
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only', (
        "auto_rebase_threshold default must be 'no_overlap_only'"
    )
    # not a flat sibling of steps anymore
    assert 'auto_rebase_threshold' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_includes_auto_rebase_threshold():
    """get_default_config() surfaces auto_rebase_threshold nested under default:branch-cleanup."""
    config = _config_defaults_mod.get_default_config()

    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'auto_rebase_threshold' in branch_cleanup, (
        'auto_rebase_threshold must round-trip through the LIST steps under default:branch-cleanup'
    )
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'


def test_default_plan_finalize_includes_merge_queue_wait_budget_seconds():
    """merge_queue_wait_budget_seconds nests under default:branch-cleanup with default 1800.

    The knob is a step-owned param of `default:branch-cleanup`, declared in that
    step's `configurable:` body-doc frontmatter (PR #716 removed the centralized
    _FINALIZE_STEP_PARAMS) and surfaced through get_default_config() via
    resolve_step_defaults_optional. It bounds (in seconds, ~30 min) the Pre-Merge
    Gate FIFO merge-queue poll loop before the last-resort AskUserQuestion.
    """
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )

    assert 'merge_queue_wait_budget_seconds' in branch_cleanup, (
        'merge_queue_wait_budget_seconds must nest under default:branch-cleanup in the seeded steps list'
    )
    assert branch_cleanup['merge_queue_wait_budget_seconds'] == 1800, (
        'merge_queue_wait_budget_seconds default must be 1800 (~30 min, the merge-queue wait budget)'
    )
    # not a flat sibling of steps anymore
    assert 'merge_queue_wait_budget_seconds' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_includes_merge_queue_wait_budget_seconds():
    """get_default_config() surfaces merge_queue_wait_budget_seconds nested under default:branch-cleanup."""
    config = _config_defaults_mod.get_default_config()

    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'merge_queue_wait_budget_seconds' in branch_cleanup, (
        'merge_queue_wait_budget_seconds must round-trip through the LIST steps under default:branch-cleanup'
    )
    assert branch_cleanup['merge_queue_wait_budget_seconds'] == 1800


def test_default_plan_finalize_includes_admin_merge_on_stuck_state():
    """admin_merge_on_stuck_state nests under default:branch-cleanup with default False.

    The knob is a step-owned param of `default:branch-cleanup`, declared in that
    step's `configurable:` body-doc frontmatter and surfaced through
    get_default_config() via resolve_step_defaults_optional. It gates the
    GitHub-only stuck-state `--admin` fallback inside `ci pr safe-merge`;
    `False` (the default) refuses the admin merge and surfaces the stuck PR to
    the operator.
    """
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )

    assert 'admin_merge_on_stuck_state' in branch_cleanup, (
        'admin_merge_on_stuck_state must nest under default:branch-cleanup in the seeded steps list'
    )
    assert branch_cleanup['admin_merge_on_stuck_state'] is False, (
        'admin_merge_on_stuck_state default must be False (admin fallback opt-in, off by default)'
    )
    # not a flat sibling of steps anymore
    assert 'admin_merge_on_stuck_state' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_includes_admin_merge_on_stuck_state():
    """get_default_config() surfaces admin_merge_on_stuck_state nested under default:branch-cleanup."""
    config = _config_defaults_mod.get_default_config()

    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'admin_merge_on_stuck_state' in branch_cleanup, (
        'admin_merge_on_stuck_state must round-trip through the steps map under default:branch-cleanup'
    )
    assert branch_cleanup['admin_merge_on_stuck_state'] is False


def test_default_plan_execute_omits_retired_per_task_budget_reserve_tokens():
    """DEFAULT_PLAN_EXECUTE must NOT carry the retired per_task_budget_reserve_tokens key.

    The reserve key gated a continue-vs-yield clause whose `remaining_budget`
    input is harness-infeasible (a running subagent cannot measure its own
    context use mid-turn). It is replaced (clean break) by the plan-time
    bin-packing model — cost_size_token_table + per_envelope_budget_tokens — so a
    surviving seed would re-introduce the unevaluable knob.
    """
    assert 'per_task_budget_reserve_tokens' not in _config_defaults_mod.DEFAULT_PLAN_EXECUTE


def test_get_default_config_omits_retired_per_task_budget_reserve_tokens():
    """get_default_config() must NOT surface plan.phase-5-execute.per_task_budget_reserve_tokens."""
    config = _config_defaults_mod.get_default_config()

    assert 'per_task_budget_reserve_tokens' not in config['plan']['phase-5-execute']


_EXPECTED_COST_SIZE_TOKEN_TABLE = {'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K'}


def test_default_plan_execute_includes_cost_size_token_table():
    """DEFAULT_PLAN_EXECUTE must declare cost_size_token_table with the calibrated default."""
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    assert 'cost_size_token_table' in execute_defaults, (
        'cost_size_token_table must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['cost_size_token_table'] == _EXPECTED_COST_SIZE_TOKEN_TABLE, (
        'cost_size_token_table default must map S/M/L/XL to 25K/60K/130K/260K '
        '(calibrated to the forensic 134K-392K per-dispatch range)'
    )
    # Every magnitude round-trips through the shared parser to the documented int.
    parsed = {k: parse_sensible_int(v) for k, v in execute_defaults['cost_size_token_table'].items()}
    assert parsed == {'S': 25000, 'M': 60000, 'L': 130000, 'XL': 260000}


def test_get_default_config_includes_cost_size_token_table():
    """get_default_config() must surface plan.phase-5-execute.cost_size_token_table."""
    config = _config_defaults_mod.get_default_config()

    execute = config['plan']['phase-5-execute']
    assert execute.get('cost_size_token_table') == _EXPECTED_COST_SIZE_TOKEN_TABLE


def test_default_plan_execute_includes_per_envelope_budget_tokens():
    """DEFAULT_PLAN_EXECUTE must declare per_envelope_budget_tokens with default "400K"."""
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    assert 'per_envelope_budget_tokens' in execute_defaults, (
        'per_envelope_budget_tokens must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['per_envelope_budget_tokens'] == '400K', (
        'per_envelope_budget_tokens default must be the human-friendly "400K" '
        '(plan-time bin-packer packing budget)'
    )
    # The human-friendly string round-trips to the documented int via the shared parser.
    assert parse_sensible_int(execute_defaults['per_envelope_budget_tokens']) == 400000


def test_get_default_config_includes_per_envelope_budget_tokens():
    """get_default_config() must surface plan.phase-5-execute.per_envelope_budget_tokens == "400K"."""
    config = _config_defaults_mod.get_default_config()

    execute = config['plan']['phase-5-execute']
    assert execute.get('per_envelope_budget_tokens') == '400K'
    assert parse_sensible_int(execute['per_envelope_budget_tokens']) == 400000


def test_cost_size_labels_enumerates_the_four_tshirt_sizes():
    """COST_SIZE_LABELS must enumerate exactly the four T-shirt sizes S/M/L/XL."""
    assert _config_defaults_mod.COST_SIZE_LABELS == ('S', 'M', 'L', 'XL')
    # the seeded default table keys must match the label set exactly
    assert set(_config_defaults_mod.DEFAULT_PLAN_EXECUTE['cost_size_token_table'].keys()) == set(
        _config_defaults_mod.COST_SIZE_LABELS
    )


def test_validate_cost_size_token_table_accepts_seeded_default():
    """validate_cost_size_token_table must accept the seeded default table."""
    _config_defaults_mod.validate_cost_size_token_table(
        _config_defaults_mod.DEFAULT_PLAN_EXECUTE['cost_size_token_table']
    )
    # an explicit valid table with int-typed magnitudes is also accepted
    _config_defaults_mod.validate_cost_size_token_table(
        {'S': 25000, 'M': '60K', 'L': '130_000', 'XL': '260K'}
    )


def test_validate_cost_size_token_table_rejects_non_dict():
    """validate_cost_size_token_table must reject a non-dict value."""
    import pytest

    with pytest.raises(ValueError, match='expected a dict'):
        _config_defaults_mod.validate_cost_size_token_table(['25K', '60K'])


def test_validate_cost_size_token_table_rejects_missing_key():
    """validate_cost_size_token_table must reject a table missing one of S/M/L/XL."""
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_cost_size_token_table({'S': '25K', 'M': '60K', 'L': '130K'})


def test_validate_cost_size_token_table_rejects_extra_key():
    """validate_cost_size_token_table must reject a table carrying an unexpected size key."""
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K', 'XXL': '500K'}
        )


def test_validate_cost_size_token_table_rejects_unparseable_magnitude():
    """validate_cost_size_token_table must reject a value that is not a sensible int."""
    import pytest

    with pytest.raises(ValueError, match='not a parseable token magnitude'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'S': '25K', 'M': 'sixty-thousand', 'L': '130K', 'XL': '260K'}
        )


_EXPECTED_PER_DELIVERABLE_BUILD = ['default:verify:compile', 'default:verify:module-tests']


def test_default_plan_execute_includes_per_deliverable_build():
    """DEFAULT_PLAN_EXECUTE must declare per_deliverable_build as the canonical-verify list."""
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    assert 'per_deliverable_build' in execute_defaults, (
        'per_deliverable_build must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    # The knob is now a LIST of default:verify:{canonical} step IDs (the former
    # 'compile+scoped-test' enum expanded to compile + module-tests rungs).
    assert execute_defaults['per_deliverable_build'] == _EXPECTED_PER_DELIVERABLE_BUILD, (
        "per_deliverable_build default must be ['default:verify:compile',"
        "'default:verify:module-tests'] (focused per-deliverable build)"
    )


def test_get_default_config_includes_per_deliverable_build():
    """get_default_config() must surface plan.phase-5-execute.per_deliverable_build as the list default."""
    config = _config_defaults_mod.get_default_config()

    execute = config['plan']['phase-5-execute']
    assert execute.get('per_deliverable_build') == _EXPECTED_PER_DELIVERABLE_BUILD


def test_retired_per_deliverable_build_enum_names_the_old_vocabulary():
    """RETIRED_PER_DELIVERABLE_BUILD_ENUM must name the four retired enum strings.

    The old enum vocabulary is no longer accepted; the validator names these
    explicitly so a config carrying an old value gets an actionable migration
    error rather than a generic "not a list" rejection.
    """
    retired = _config_defaults_mod.RETIRED_PER_DELIVERABLE_BUILD_ENUM

    assert retired == ('off', 'compile-only', 'compile+scoped-test', 'full')
    # the default value must NOT be one of the retired enum strings
    assert _config_defaults_mod.DEFAULT_PLAN_EXECUTE['per_deliverable_build'] not in retired


def test_validate_per_deliverable_build_accepts_canonical_verify_list():
    """validate_per_deliverable_build must accept a list of default:verify:{canonical} IDs."""
    # no exception for a valid canonical-verify list
    _config_defaults_mod.validate_per_deliverable_build(
        ['default:verify:compile', 'default:verify:module-tests']
    )
    # the seeded default must validate
    _config_defaults_mod.validate_per_deliverable_build(
        _config_defaults_mod.DEFAULT_PLAN_EXECUTE['per_deliverable_build']
    )


def test_validate_per_deliverable_build_accepts_empty_list():
    """validate_per_deliverable_build must accept [] (disables the per-deliverable build)."""
    # the empty list is the replacement for the retired 'off' enum value
    _config_defaults_mod.validate_per_deliverable_build([])


def test_validate_per_deliverable_build_rejects_retired_enum_values():
    """validate_per_deliverable_build must reject every retired enum string with a migration error."""
    import pytest

    for retired in _config_defaults_mod.RETIRED_PER_DELIVERABLE_BUILD_ENUM:
        with pytest.raises(ValueError, match='no longer accepts the enum value'):
            _config_defaults_mod.validate_per_deliverable_build(retired)


def test_validate_per_deliverable_build_rejects_non_list():
    """validate_per_deliverable_build must reject a non-list value that is not a retired enum string."""
    import pytest

    with pytest.raises(ValueError, match='expected a list'):
        _config_defaults_mod.validate_per_deliverable_build('reckless')


def test_validate_per_deliverable_build_rejects_non_canonical_entries():
    """validate_per_deliverable_build must reject list entries lacking the default:verify: prefix."""
    import pytest

    with pytest.raises(ValueError, match='every entry must be a'):
        _config_defaults_mod.validate_per_deliverable_build(
            ['default:verify:compile', 'bogus-step']
        )


# =============================================================================
# remove-field verb (cmd_phase) — deletes a key under a phase section
# =============================================================================


def test_remove_field_deletes_explicit_phase_key(plan_context):
    """`phase-5-execute remove-field --field per_deliverable_build` deletes the persisted key.

    The verb operates on the on-disk section only: removing a key that the
    defaults still seed re-exposes the default on the next read, so the
    follow-up get surfaces the seeded default rather than KeyError.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # set an explicit override so the key is present in the persisted section
    set_args = Namespace(
        verb='set', field='per_deliverable_build', value='default:verify:compile'
    )
    set_result = _cmd_quality_phases_mod.cmd_phase(set_args, 'phase-5-execute')
    assert set_result['status'] == 'success'

    # remove the persisted override
    remove_args = Namespace(verb='remove-field', field='per_deliverable_build')
    remove_result = _cmd_quality_phases_mod.cmd_phase(remove_args, 'phase-5-execute')

    assert remove_result['status'] == 'success'
    assert remove_result['field'] == 'per_deliverable_build'
    assert remove_result['removed'] is True

    # removing a key the defaults seed re-exposes the default on the next read
    get_args = Namespace(verb='get', field='per_deliverable_build')
    get_result = _cmd_quality_phases_mod.cmd_phase(get_args, 'phase-5-execute')
    assert get_result['status'] == 'success'
    assert get_result['value'] == _EXPECTED_PER_DELIVERABLE_BUILD


def test_remove_field_errors_on_absent_key(plan_context):
    """`remove-field` must error when the key is not present in the persisted section.

    Removing an absent key is an explicit error (not a silent no-op) so callers
    get a clear signal.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # the legacy `steps` key has no default and is absent from a fresh config
    remove_args = Namespace(verb='remove-field', field='steps')
    result = _cmd_quality_phases_mod.cmd_phase(remove_args, 'phase-5-execute')

    assert result['status'] == 'error'


def test_remove_field_removes_legacy_steps_key(plan_context):
    """`remove-field --field steps` cleanly removes the legacy phase-5 steps key.

    The legacy `plan.phase-5-execute.steps` key has no default, so removing it
    leaves a clean section with no re-exposed default.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'

    # inject a legacy `steps` key into the persisted phase-5-execute section
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['plan']['phase-5-execute']['steps'] = ['default:verify:quality-gate']
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    remove_args = Namespace(verb='remove-field', field='steps')
    result = _cmd_quality_phases_mod.cmd_phase(remove_args, 'phase-5-execute')

    assert result['status'] == 'success'
    assert result['removed'] is True

    # the legacy key is gone from the persisted section
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'steps' not in persisted['plan']['phase-5-execute']


def test_default_plan_finalize_omits_pre_push_quality_gate_activation_globs():
    """DEFAULT_PLAN_FINALIZE must NOT carry a pre_push_quality_gate.activation_globs knob.

    Pre-push activation is derived entirely from build.map globs
    (D7/D8); the separate finalize-phase pre_push_quality_gate config field was
    dropped, so a surviving seed would re-introduce a dead activation source.
    """
    assert 'pre_push_quality_gate' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_omits_pre_push_quality_gate():
    """get_default_config() must NOT surface plan.phase-6-finalize.pre_push_quality_gate."""
    config = _config_defaults_mod.get_default_config()

    assert 'pre_push_quality_gate' not in config['plan']['phase-6-finalize']


def test_default_project_default_base_branch_is_main():
    """DEFAULT_PROJECT must declare default_base_branch == 'main'."""
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    assert 'default_base_branch' in project_defaults
    assert project_defaults['default_base_branch'] == 'main'


def test_get_default_config_includes_project_block():
    """get_default_config() must include the 'project' block with default_base_branch == 'main'."""
    config = _config_defaults_mod.get_default_config()

    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_fresh_marshal_seeds_project_default_base_branch_main(plan_context):
    """`manage-config init` against a fresh fixture must seed project.default_base_branch=main."""
    result = _cmd_init_mod.cmd_init(Namespace(force=False))

    assert result['status'] == 'success'
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists()

    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_project_set_then_get_roundtrip_default_base_branch(plan_context):
    """`project set --field default_base_branch --value develop` must round-trip via get."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # set
    set_args = Namespace(verb='set', field='default_base_branch', value='develop')
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # get
    get_args = Namespace(verb='get', field='default_base_branch')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    assert get_result['status'] == 'success'
    assert get_result['value'] == 'develop'


def test_project_get_returns_default_when_block_absent(plan_context):
    """A fresh marshal.json without the `project` block returns DEFAULT_PROJECT values."""
    # initialize then remove `project` block to emulate legacy schema
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('project', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    args = Namespace(verb='get', field='default_base_branch')
    result = _cmd_system_plan_mod.cmd_project(args)

    # implicit-default semantics mirror open_in_ide / DEFAULT_PLAN_* blocks
    assert result['status'] == 'success'
    assert result['value'] == 'main'


_EXPECTED_WORKING_PREFIXES = ['feature/', 'fix/', 'chore/']


def test_default_project_includes_working_prefixes():
    """DEFAULT_PROJECT must declare working_prefixes with the canonical set."""
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    assert 'working_prefixes' in project_defaults
    assert project_defaults['working_prefixes'] == _EXPECTED_WORKING_PREFIXES


def test_default_project_drops_branch_naming_wrapper():
    """The flattened model removes the nested branch_naming wrapper entirely."""
    assert 'branch_naming' not in _config_defaults_mod.DEFAULT_PROJECT


def test_get_default_config_includes_working_prefixes():
    """get_default_config() must surface project.working_prefixes."""
    config = _config_defaults_mod.get_default_config()

    assert config['project'].get('working_prefixes') == _EXPECTED_WORKING_PREFIXES


def test_default_working_prefixes_excludes_docs_prefix():
    """The default working_prefixes must NOT contain the retired 'docs/' prefix."""
    working = _config_defaults_mod.DEFAULT_PROJECT['working_prefixes']

    # 'docs/' is explicitly retired
    assert 'docs/' not in working


def test_project_get_working_prefixes_returns_default_when_key_absent(plan_context):
    """A fresh marshal.json lacking working_prefixes returns the default list."""
    # init then strip working_prefixes to emulate a legacy marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('project', {}).pop('working_prefixes', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    args = Namespace(verb='get', field='working_prefixes')
    result = _cmd_system_plan_mod.cmd_project(args)

    # implicit-default fallback to DEFAULT_PROJECT['working_prefixes']
    assert result['status'] == 'success'
    assert result['value'] == _EXPECTED_WORKING_PREFIXES


def test_project_set_then_get_roundtrip_working_prefixes(plan_context):
    """`project set --field working_prefixes --value <json>` round-trips via get."""
    _cmd_init_mod.cmd_init(Namespace(force=False))
    custom = ['feature/', 'fix/', 'chore/', 'spike/']

    # set (JSON array value)
    set_args = Namespace(verb='set', field='working_prefixes', value=json.dumps(custom))
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # get
    get_args = Namespace(verb='get', field='working_prefixes')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    # the list round-trips, not a bare JSON string
    assert get_result['status'] == 'success'
    assert get_result['value'] == custom


def test_project_set_working_prefixes_rejects_invalid_json(plan_context):
    """`project set --field working_prefixes` with a non-JSON value errors out."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(verb='set', field='working_prefixes', value='not-json')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_json'


def test_project_set_working_prefixes_rejects_non_array(plan_context):
    """`project set --field working_prefixes` with a non-array JSON value errors out."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # a JSON object is valid JSON but the wrong shape
    set_args = Namespace(verb='set', field='working_prefixes', value='{"a": 1}')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_type'


def test_default_project_omits_sanctioned_conftest_key():
    """DEFAULT_PROJECT must NOT declare sanctioned_conftest — the seed was removed (D2).

    The conftest-vs-_fixtures.py naming rule is now advisory prose only; it is no
    longer a shipped config field. A surviving seed would re-introduce the
    meta-project-convention leak this deliverable removed.
    """
    assert 'sanctioned_conftest' not in _config_defaults_mod.DEFAULT_PROJECT


def test_get_default_config_omits_sanctioned_conftest_key():
    """get_default_config() must NOT surface project.sanctioned_conftest — the field is gone."""
    config = _config_defaults_mod.get_default_config()

    assert 'sanctioned_conftest' not in config['project']


def test_default_plan_refine_includes_simplicity_lean():
    """DEFAULT_PLAN_REFINE must declare simplicity with default 'lean'.

    Mirrors the sibling `compatibility` knob — simplicity controls how
    aggressively the implementation favours the minimum viable surface.
    """
    refine_defaults = _config_defaults_mod.DEFAULT_PLAN_REFINE

    assert 'simplicity' in refine_defaults, (
        'simplicity must be schema-registered in DEFAULT_PLAN_REFINE'
    )
    assert refine_defaults['simplicity'] == 'lean', (
        "simplicity default must be 'lean' (implement the strict minimum)"
    )


def test_get_default_config_phase_2_refine_includes_simplicity_lean():
    """get_default_config() must surface simplicity == 'lean' under plan.phase-2-refine."""
    config = _config_defaults_mod.get_default_config()

    refine_block = config['plan']['phase-2-refine']
    assert refine_block.get('simplicity') == 'lean'


def test_valid_simplicity_levels_enumerates_expected_values():
    """VALID_SIMPLICITY_LEVELS must enumerate exactly the three allowed enum values."""
    levels = _config_defaults_mod.VALID_SIMPLICITY_LEVELS

    # default 'lean' must be a member of the enum
    assert levels == ('lean', 'pragmatic', 'defensive')
    assert _config_defaults_mod.DEFAULT_PLAN_REFINE['simplicity'] in levels


def test_validate_simplicity_accepts_allowed_values():
    """validate_simplicity must accept every value in VALID_SIMPLICITY_LEVELS."""
    # no exception for any allowed value
    for value in _config_defaults_mod.VALID_SIMPLICITY_LEVELS:
        _config_defaults_mod.validate_simplicity(value)


def test_validate_simplicity_rejects_unknown_value():
    """validate_simplicity must raise ValueError for a value outside the enum."""
    import pytest

    with pytest.raises(ValueError, match='Invalid simplicity'):
        _config_defaults_mod.validate_simplicity('reckless')


def test_plan_phase_2_refine_get_simplicity_returns_lean_default(plan_context):
    """`plan phase-2-refine get --field simplicity` returns 'lean' from the merged default config.

    Exercises the actual cmd_phase get path (same code `manage-config plan
    phase-2-refine get --field simplicity` runs) against a fresh marshal.json,
    proving the default surfaces even when the persisted config omits the key.
    """
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # get the simplicity field via the phase handler
    args = Namespace(verb='get', field='simplicity')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-2-refine')

    # default merge surfaces 'lean'
    assert result['status'] == 'success'
    assert result['value'] == 'lean'


def test_built_in_finalize_steps_places_simplify_before_push():
    """default:finalize-step-simplify sits BEFORE default:push in BUILT_IN_FINALIZE_STEPS.

    simplify is a mutates_source step (order 8) and push is the pure barrier
    (order 10), so simplify precedes push. The canonical head order is
    default:pre-push-quality-gate (index 0), default:finalize-step-simplify
    (index 1), then default:push (index 2) — matching the plain `order:` values
    (no special placement invariant).
    """
    steps = _config_defaults_mod.BUILT_IN_FINALIZE_STEPS

    # presence and ordinal placement
    assert 'default:finalize-step-simplify' in steps, (
        'default:finalize-step-simplify must be seeded into BUILT_IN_FINALIZE_STEPS'
    )
    assert steps[0] == 'default:pre-push-quality-gate'
    assert steps[1] == 'default:finalize-step-simplify'
    assert steps[2] == 'default:push'


def test_built_in_finalize_step_descriptions_includes_finalize_step_simplify():
    """default:finalize-step-simplify must carry a non-empty description entry.

    The descriptions dict must stay in sync with BUILT_IN_FINALIZE_STEPS so
    list-finalize-steps can surface a human-readable description.
    """
    descriptions = _config_defaults_mod.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS

    assert 'default:finalize-step-simplify' in descriptions, (
        'default:finalize-step-simplify must have a BUILT_IN_FINALIZE_STEP_DESCRIPTIONS entry'
    )
    assert descriptions['default:finalize-step-simplify'], (
        'default:finalize-step-simplify description must be non-empty'
    )


def test_built_in_finalize_steps_orders_simplify_then_push():
    """Canonical order: simplify before push.

    simplify is a mutates_source step (order 8) and push is the pure barrier
    (order 10), so the canonical chain is simplify < push.
    """
    steps = _config_defaults_mod.BUILT_IN_FINALIZE_STEPS

    simplify_index = steps.index('default:finalize-step-simplify')
    push_index = steps.index('default:push')
    # direct mirror of the request mandate: simplify precedes push
    assert simplify_index < push_index, (
        'finalize-step-simplify must precede push'
    )


# =============================================================================
# Keyed-map serial-form step structure with nested params (this plan)
# =============================================================================
#
# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize as the canonical keyed map (an id-keyed object, not a list). Each
# value is the step's nested param object (`{}` for a config-less step). Key
# insertion order is the execution order. The sonar params are prefix-stripped
# within the `default:sonar-roundtrip` value. These regression tests pin the
# exact keyed-map structure so any future shape drift is caught immediately.


def test_default_plan_finalize_steps_is_keyed_map_form():
    """The seeded finalize steps must be the keyed-map form, not a list.

    The module-level DEFAULT_PLAN_FINALIZE['steps'] is a None placeholder; the
    keyed map is materialized lazily by get_default_config() via the
    configurable_contract parser delegation.
    """
    config = _config_defaults_mod.get_default_config()
    steps = config['plan']['phase-6-finalize']['steps']

    assert isinstance(steps, dict), 'steps must be the keyed-map form, not a list'
    # key insertion order preserves the BUILT_IN_FINALIZE_STEPS execution order
    assert _step_ids(steps) == _config_defaults_mod.BUILT_IN_FINALIZE_STEPS


def test_default_plan_finalize_steps_nests_step_owned_params():
    """Step-owned params nest in their owning step's value; config-less steps map to {}."""
    config = _config_defaults_mod.get_default_config()
    steps = config['plan']['phase-6-finalize']['steps']

    # sonar params nest under default:sonar-roundtrip, prefix-stripped
    sonar = _params_for(steps, 'default:sonar-roundtrip')
    assert sonar == {
        'touched_file_cleanup': 'new_code_only',
        'do_transition': False,
        'ce_wait_timeout_seconds': 600,
    }
    # no sonar_-prefixed key survives inside the scoped object
    assert not any(k.startswith('sonar_') for k in sonar)

    # review buffer + re-review gates + re-review timeout knobs nest under default:automated-review
    assert _params_for(steps, 'default:automated-review') == {
        'review_bot_buffer_seconds': 180,
        're_review_on_loopback': False,
        're_review_on_branch_cleanup': True,
        're_review_await_timeout_seconds': 600,
        're_review_on_timeout': 'ask',
    }

    # branch-cleanup params nest under default:branch-cleanup
    assert _params_for(steps, 'default:branch-cleanup') == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
        'merge_queue_wait_budget_seconds': 1800,
        'admin_merge_on_stuck_state': False,
    }

    # a step that owns no params maps to an empty {} param object.
    assert 'default:create-pr' in steps
    assert _params_for(steps, 'default:create-pr') == {}


def test_default_plan_finalize_config_less_steps_map_to_empty_dict():
    """Every config-less finalize step maps to {}; param-owning steps carry a non-empty dict.

    Keyed-map serial form: a config-less step's value is an empty ``{}`` object,
    and a param-owning step's value is a non-empty param dict.
    """
    config = _config_defaults_mod.get_default_config()
    steps = config['plan']['phase-6-finalize']['steps']

    param_owning = {
        'default:sonar-roundtrip',
        'default:automated-review',
        'default:branch-cleanup',
        # default:finalize-step-simplify owns the folded `simplify` run-at-all gate
        'default:finalize-step-simplify',
    }
    for step_id, params in steps.items():
        assert isinstance(params, dict), f'every step value must be a dict; got {params!r}'
        if step_id in param_owning:
            assert params, f'param-owning step {step_id!r} must carry a non-empty nested dict'
        else:
            assert params == {}, (
                f'config-less step {step_id!r} must map to {{}}, not {params!r}'
            )


def test_default_plan_finalize_drops_flat_step_owned_knobs():
    """No flat step-owned knob survives as a sibling of `steps`."""
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    for knob in (
        'sonar_touched_file_cleanup',
        'sonar_do_transition',
        'sonar_ce_wait_timeout_seconds',
        'review_bot_buffer_seconds',
        'pr_merge_strategy',
        'final_merge_without_asking',
        'auto_rebase_threshold',
        'merge_queue_wait_budget_seconds',
        'admin_merge_on_stuck_state',
    ):
        assert knob not in finalize, f'flat step-owned knob {knob!r} must not survive'

    # the three step-folded run-at-all / escape-hatch knobs are gone from the
    # flat section too (they fold under their owning finalize step)
    for knob in ('simplify', 'self_review', 'drop_review_on_scope_gate'):
        assert knob not in finalize, f'flat step-owned knob {knob!r} must not survive'

    # phase-level knobs stay flat
    assert finalize['checks_wait_timeout_seconds'] == 600
    assert finalize['max_iterations'] == 3
    assert finalize['finalize_without_asking'] is True
    # qgate is the one finalize run-at-all gate that stays a flat sibling
    assert finalize['qgate'] == 'auto'


def test_default_plan_execute_verification_steps_is_keyed_map_form():
    """DEFAULT_PLAN_EXECUTE['verification_steps'] must be the keyed map of config-less steps."""
    verification_steps = _config_defaults_mod.DEFAULT_PLAN_EXECUTE['verification_steps']

    assert isinstance(verification_steps, dict), (
        'verification_steps must be the keyed-map form, not a list'
    )
    # key insertion order preserves the BUILT_IN_VERIFY_STEPS execution order
    assert _step_ids(verification_steps) == _config_defaults_mod.BUILT_IN_VERIFY_STEPS
    # verification steps own no params — every value is an empty {} param object.
    assert all(params == {} for params in verification_steps.values())


def test_get_default_config_finalize_steps_keyed_map_form_shape():
    """get_default_config() must surface the keyed-map finalize steps with nested params."""
    config = _config_defaults_mod.get_default_config()

    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    assert _step_ids(steps) == _config_defaults_mod.BUILT_IN_FINALIZE_STEPS
    assert _params_for(steps, 'default:sonar-roundtrip')['touched_file_cleanup'] == 'new_code_only'
    assert _params_for(steps, 'default:branch-cleanup')['pr_merge_strategy'] == 'squash'


def test_get_default_config_verification_steps_keyed_map_form_shape():
    """get_default_config() must surface the keyed-map verification steps with config-less values."""
    config = _config_defaults_mod.get_default_config()

    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert isinstance(verification_steps, dict)
    assert _step_ids(verification_steps) == _config_defaults_mod.BUILT_IN_VERIFY_STEPS
    # config-less verify steps surface with empty {} param objects.
    assert all(params == {} for params in verification_steps.values())


# =============================================================================
# Read-path coercion: the keyed map normalizes to the internal id-keyed dict
# =============================================================================
#
# `_steps_map` (the `_cmd_quality_phases` read boundary) reads the canonical
# keyed-map on-disk form. Every per-step value that is not a dict — None, the
# empty {}, and the TOON-round-tripped '' — coerces back to an empty dict, so a
# config-less step reads identically no matter which empty representation it
# carries on disk. A param-owning step keeps its nested object. A non-dict
# top-level value (the key absent / a malformed scalar / a stray list) yields an
# empty dict.


def test_steps_map_reads_keyed_map_to_internal_id_keyed_dict():
    """The keyed map reads to the internal id-keyed dict, preserving insertion order.

    A config-less step's value (None / {} / '') coerces to {}; a param-bearing
    step keeps its nested object. Key insertion (= execution) order is preserved.
    """
    raw = {
        'default:push': {},
        'default:branch-cleanup': {'pr_merge_strategy': 'squash'},
        'default:create-pr': {},
    }

    result = _cmd_quality_phases_mod._steps_map(raw)

    assert result == {
        'default:push': {},
        'default:branch-cleanup': {'pr_merge_strategy': 'squash'},
        'default:create-pr': {},
    }
    # key insertion order is preserved in the normalized dict
    assert list(result.keys()) == ['default:push', 'default:branch-cleanup', 'default:create-pr']


def test_steps_map_coerces_none_value_to_empty_dict():
    """A None per-step value (a config-less step) coerces to {}."""
    raw = {'default:push': None, 'default:create-pr': None}

    result = _cmd_quality_phases_mod._steps_map(raw)

    assert result == {'default:push': {}, 'default:create-pr': {}}


def test_steps_map_coerces_empty_dict_to_empty_dict():
    """An empty {} per-step value coerces to {} (idempotent)."""
    raw = {'default:push': {}, 'default:create-pr': {}}

    result = _cmd_quality_phases_mod._steps_map(raw)

    assert result == {'default:push': {}, 'default:create-pr': {}}


def test_steps_map_coerces_toon_empty_string_to_empty_dict():
    """A TOON-round-tripped empty-dict value ('') coerces to {}.

    Persisting {} as TOON and reading it back yields the empty string '', so the
    read boundary must treat '' identically to None / {}.
    """
    raw = {'default:push': '', 'default:create-pr': ''}

    result = _cmd_quality_phases_mod._steps_map(raw)

    assert result == {'default:push': {}, 'default:create-pr': {}}


def test_steps_map_mixed_shapes_read_identically_for_config_less_steps():
    """All of {None, {}, ''} read identically as {} for config-less steps.

    The full empty-value representation set coerces to the same {} so a
    config-less step reads identically no matter which empty representation it
    carries, while a param-owning step keeps its nested object.
    """
    raw = {
        'default:push': None,
        'default:create-pr': {},
        'default:lessons-capture': '',
        'default:branch-cleanup': {'pr_merge_strategy': 'squash'},
    }

    result = _cmd_quality_phases_mod._steps_map(raw)

    # every config-less representation reads back as the empty dict
    assert result['default:push'] == {}
    assert result['default:create-pr'] == {}
    assert result['default:lessons-capture'] == {}
    # the param-owning step keeps its nested object untouched
    assert result['default:branch-cleanup'] == {'pr_merge_strategy': 'squash'}


def test_steps_map_non_dict_top_level_yields_empty_dict():
    """A non-dict top-level value (None / absent key / a stray list) yields an empty dict."""
    assert _cmd_quality_phases_mod._steps_map(None) == {}
    assert _cmd_quality_phases_mod._steps_map({}) == {}
    assert _cmd_quality_phases_mod._steps_map(['default:push']) == {}


def test_default_plan_coverage_is_inherit_inherit():
    """DEFAULT_PLAN_COVERAGE must declare the behavior-preserving inherit/inherit seed."""
    coverage_default = _config_defaults_mod.DEFAULT_PLAN_COVERAGE

    assert coverage_default == {'thoroughness': 'inherit', 'scope': 'inherit'}, (
        'DEFAULT_PLAN_COVERAGE must be the byte-identical inherit/inherit fallback seed'
    )


def test_get_default_config_includes_plan_wide_coverage():
    """get_default_config() must surface plan.coverage == inherit/inherit (plan-wide knob)."""
    config = _config_defaults_mod.get_default_config()

    assert config['plan']['coverage'] == {'thoroughness': 'inherit', 'scope': 'inherit'}


def test_get_default_config_seeds_no_per_phase_coverage():
    """No per-phase default block may carry a coverage key — coverage is plan-wide only.

    The per-invocation coverage cell lives in status.json metadata per the
    coverage-gathering contract; only plan.coverage is the operator-visible
    project default. A per-phase coverage seed would be inert and is forbidden.
    """
    plan_config = _config_defaults_mod.get_default_config()['plan']

    # walk every per-phase block (keys shaped 'phase-N-...')
    for key, block in plan_config.items():
        if key.startswith('phase-') and isinstance(block, dict):
            assert 'coverage' not in block, (
                f'per-phase block {key!r} must NOT seed a coverage key — '
                'coverage is plan-wide only'
            )


# =============================================================================
# build_map relocation + required-seed defaults (D6/D7/D14)
# =============================================================================


def test_get_default_config_does_not_seed_build_map():
    """get_default_config() must NOT seed build.map — neither nested nor top level.

    The premature init-time auto-seed was removed (seed-ordering fix): build_map is
    materialised only at wizard Step 8b (`build-map seed`) after architecture
    discovery, so the applicability filter has discovered modules to scope against.
    The default config therefore ships skill_domains (with the system domain) but
    no build.map block anywhere.
    """
    config = _config_defaults_mod.get_default_config()

    # no build.map block, and the legacy skill_domains.build_map is absent.
    assert 'map' not in config.get('build', {}), (
        'get_default_config() must NOT seed build.map (seeded at Step 8b '
        'after architecture discovery)'
    )
    assert 'skill_domains' in config
    assert 'build_map' not in config['skill_domains'], (
        'the legacy skill_domains.build_map block must not be present'
    )


def test_get_default_config_omits_retired_build_map_overrides():
    """get_default_config() must NOT carry the retired build_map_overrides key.

    The override layer was dropped (D14): the seeded build_map is the single
    source of truth and user corrections are made directly to the seeded entries.
    """
    config = _config_defaults_mod.get_default_config()

    # no override layer anywhere.
    assert 'build_map_overrides' not in config
    assert 'build_map_overrides' not in config['skill_domains']
    assert 'build_map_overrides' not in config.get('build', {})


def test_build_map_round_trips_at_top_level_build_path(tmp_path, monkeypatch):
    """A build.map block round-trips through save_config / merge_build_map unchanged.

    Regression for the relocation (skill_domains.build_map -> build.map): writing a
    config carrying a top-level build.map block, persisting it via save_config, and
    reading it back via merge_build_map must yield the same {domain: [...]} data,
    proving the new top-level path is the live read/write contract.
    """
    # a config with a build.map block at the relocated top-level path.
    build_map = {
        'python': [
            {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
            {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
        ],
    }
    config = {'build': {'map': build_map}, 'skill_domains': {'system': {}}}
    marshal_path = tmp_path / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)

    # persist then read back through the live readers.
    _config_core_mod.save_config(config)
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    merged = _config_core_mod.merge_build_map(persisted)

    # the relocated top-level path round-trips the data unchanged.
    assert persisted['build']['map'] == build_map
    assert merged == build_map


# =============================================================================
# Top-level marshal.json key ordering (D13)
# =============================================================================
#
# save_config() in _config_core.py enforces a canonical top-level key order when
# persisting marshal.json. After the D1–D6 dissolutions and the build_map
# relocation to the top-level build block, the surviving top-level blocks
# (ci/ceremony_policy/build_map_overrides removed) lead with ``extension_defaults``
# (the extension-seeded defaults block), then ``plan`` (the primary user-facing
# config), then ``build`` (build infrastructure), and finally the remaining
# top-level keys alphabetically: extension_defaults, plan, build, project,
# providers, skill_domains, system. These tests pin that contract and prove the
# committed marshal.json already round-trips through save_config with its key
# order unchanged.

_EXPECTED_CANONICAL_KEY_ORDER = [
    'extension_defaults',
    'plan',
    'build',
    'project',
    'providers',
    'skill_domains',
    'system',
]

# The committed marshal.json the repo ships. Resolved relative to this test file:
# test/plan-marshall/manage-config/test_config_defaults.py -> repo root -> .plan/marshal.json.
_COMMITTED_MARSHAL_PATH = (
    Path(__file__).parent.parent.parent.parent / '.plan' / 'marshal.json'
)


def _save_config_to(tmp_marshal_path, config, monkeypatch):
    """Run _config_core.save_config against a redirected MARSHAL_PATH.

    Points the loaded _config_core module's MARSHAL_PATH at ``tmp_marshal_path``
    so save_config writes the fixture file instead of the real committed
    marshal.json, then returns the re-loaded top-level key order.
    """
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', tmp_marshal_path)
    _config_core_mod.save_config(config)
    written = json.loads(tmp_marshal_path.read_text(encoding='utf-8'))
    return list(written.keys())


def test_save_config_emits_canonical_top_level_key_order(tmp_path, monkeypatch):
    """save_config must emit the surviving top-level keys in canonical order.

    A scrambled-input dict carrying every surviving top-level block must come
    back out in the canonical order (extension_defaults, plan, build, then the
    rest alphabetically), proving save_config's key_order is the authoritative
    ordering — independent of insertion order.
    """
    # every canonical key present, deliberately reverse-scrambled
    scrambled = {
        'system': {},
        'skill_domains': {},
        'providers': {},
        'project': {},
        'plan': {},
        'extension_defaults': {},
        'build': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    actual_order = _save_config_to(marshal_path, scrambled, monkeypatch)

    # canonical order regardless of input order
    assert actual_order == _EXPECTED_CANONICAL_KEY_ORDER


def test_save_config_omits_absent_keys_preserving_relative_order(tmp_path, monkeypatch):
    """save_config must list only the present keys, in canonical relative order.

    The committed marshal.json omits extension_defaults; save_config must not
    fabricate an empty block for it, and the surviving keys must keep their
    canonical relative order.
    """
    # drop extension_defaults (matching the committed file), scramble the rest
    config = {
        'system': {},
        'plan': {},
        'skill_domains': {},
        'project': {},
        'providers': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    actual_order = _save_config_to(marshal_path, config, monkeypatch)

    # extension_defaults absent, others in canonical relative order
    assert actual_order == ['plan', 'project', 'providers', 'skill_domains', 'system']


def test_save_config_appends_unknown_keys_after_canonical_block(tmp_path, monkeypatch):
    """save_config must append unrecognized top-level keys after the canonical block.

    Unknown keys are preserved (never dropped) and placed after every canonical
    key, so a stray block survives a save without corrupting the canonical order.
    """
    config = {
        'zzz_unknown': {},
        'system': {},
        'plan': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    actual_order = _save_config_to(marshal_path, config, monkeypatch)

    # canonical keys first (in order), unknown appended last
    assert actual_order == ['plan', 'system', 'zzz_unknown']


def test_committed_marshal_json_top_level_keys_already_canonical():
    """The committed .plan/marshal.json must already be in canonical key order.

    Regression guard: the shipped file must not drift out of the order
    save_config enforces, otherwise the next save would reorder it and produce a
    spurious diff.
    """
    assert _COMMITTED_MARSHAL_PATH.exists(), (
        f'committed marshal.json must exist at {_COMMITTED_MARSHAL_PATH}'
    )
    committed = json.loads(_COMMITTED_MARSHAL_PATH.read_text(encoding='utf-8'))
    committed_keys = list(committed.keys())

    # the committed key order equals the canonical order filtered to present keys
    expected = [k for k in _EXPECTED_CANONICAL_KEY_ORDER if k in committed]
    assert committed_keys == expected, (
        f'committed marshal.json top-level keys {committed_keys} are not in canonical '
        f'order {expected}'
    )


def test_committed_marshal_json_round_trips_through_save_config_unchanged(tmp_path, monkeypatch):
    """The committed marshal.json must round-trip through save_config unchanged.

    Loading the shipped file and re-saving it via save_config must leave the
    top-level key order byte-for-byte identical — the strongest guarantee that
    save_config will never reorder the committed config.
    """
    # load the committed config and capture its current key order
    committed = json.loads(_COMMITTED_MARSHAL_PATH.read_text(encoding='utf-8'))
    before = list(committed.keys())
    marshal_path = tmp_path / 'marshal.json'

    # persist via save_config to the redirected fixture path
    after = _save_config_to(marshal_path, committed, monkeypatch)

    # key order is unchanged by the round-trip
    assert after == before


def test_save_config_orders_build_after_plan(tmp_path, monkeypatch):
    """save_config must order the ``build`` block immediately after ``plan``.

    Regression for the key-order fix: ``build`` was previously emitted as the
    FIRST top-level block (ahead of ``plan``), producing a spurious reorder diff
    on every save. The canonical order now leads with the primary user-facing
    ``plan`` block and places ``build`` (build infrastructure) directly after it,
    ahead of the remaining alphabetical keys.
    """
    # Arrange — only plan + build present, with build deliberately inserted first
    config = {
        'build': {},
        'plan': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    # Act
    actual_order = _save_config_to(marshal_path, config, monkeypatch)

    # Assert — plan precedes build regardless of insertion order
    assert actual_order == ['plan', 'build']
    assert actual_order.index('plan') < actual_order.index('build')


# =============================================================================
# build.queue.* config keys (under the top-level build block)
# =============================================================================
#
# DEFAULT_BUILD_QUEUE seeds the cross-session build-queue admission bounds under
# the marshal.json top-level `build` block (peer to build.map, not under plan.*)
# because the build queue is a project-wide, cross-plan resource. `max_slots`
# defaults to 5 (concurrent build admissions before enqueue) and `max_retries`
# defaults to 10 (blocked-admission re-polls). These tests pin the defaults
# surfaced by get_default_config() and prove that an explicit marshal.json value
# overrides each default via load_config().


def test_default_build_queue_declares_max_slots_5_and_max_retries_10():
    """DEFAULT_BUILD_QUEUE must declare max_slots=5 and max_retries=10."""
    build_queue = _config_defaults_mod.DEFAULT_BUILD_QUEUE

    assert 'max_slots' in build_queue, (
        'max_slots must be schema-registered in DEFAULT_BUILD_QUEUE'
    )
    assert build_queue['max_slots'] == 5, (
        'build_queue.max_slots default must be 5 (concurrent build admissions)'
    )
    assert 'max_retries' in build_queue, (
        'max_retries must be schema-registered in DEFAULT_BUILD_QUEUE'
    )
    assert build_queue['max_retries'] == 10, (
        'build_queue.max_retries default must be 10 (blocked-admission re-polls)'
    )


def test_default_build_queue_declares_upper_limit_seconds_600():
    """DEFAULT_BUILD_QUEUE must seed upper_limit_seconds=600 (the clamp floor).

    Seeding the key makes the adaptive stale-reclaim ceiling operator-visible in a
    freshly-seeded config instead of fallback-only; 600 is the floor of the
    clamped [600, 3600] range manage-run-config enforces.
    """
    build_queue = _config_defaults_mod.DEFAULT_BUILD_QUEUE

    assert 'upper_limit_seconds' in build_queue, (
        'upper_limit_seconds must be schema-registered in DEFAULT_BUILD_QUEUE'
    )
    assert build_queue['upper_limit_seconds'] == 600, (
        'build_queue.upper_limit_seconds default must be 600 (the clamp floor)'
    )


def test_get_default_config_surfaces_build_queue_max_slots_default_5():
    """get_default_config() must surface build.queue.max_slots == 5 when unconfigured.

    The build.queue block lives under the marshal.json top-level `build` block
    (cross-plan resource), not under plan.*.
    """
    config = _config_defaults_mod.get_default_config()

    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('max_slots') == 5


def test_get_default_config_surfaces_build_queue_max_retries_default_10():
    """get_default_config() must surface build.queue.max_retries == 10 when unconfigured."""
    config = _config_defaults_mod.get_default_config()

    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('max_retries') == 10


def test_get_default_config_surfaces_build_queue_upper_limit_seconds_default_600():
    """get_default_config() must surface build.queue.upper_limit_seconds == 600."""
    config = _config_defaults_mod.get_default_config()

    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('upper_limit_seconds') == 600


def test_default_config_seeds_build_require_wrapper():
    """get_default_config() must seed build.{tool}.require_wrapper with the
    documented per-system defaults (true for maven/gradle/pyproject, false for
    npm), peer to the build.queue block (no regression of that peer block)."""
    config = _config_defaults_mod.get_default_config()
    build = config.get('build', {})

    assert build.get('maven', {}).get('require_wrapper') is True
    assert build.get('gradle', {}).get('require_wrapper') is True
    assert build.get('pyproject', {}).get('require_wrapper') is True
    assert build.get('npm', {}).get('require_wrapper') is False
    # The peer build.queue block is still present (additive seeding).
    assert 'queue' in build


def test_marshal_build_queue_max_slots_override_wins(plan_context, monkeypatch):
    """An explicit marshal.json build.queue.max_slots overrides the default of 5.

    Seeds a fresh marshal.json (which carries the default build.queue block),
    rewrites build.queue.max_slots to a custom value, and proves load_config()
    reads the override back rather than the 5 default. The importlib-loaded
    `_config_core_mod` is a distinct module object from the conftest-imported
    `_config_core` that plan_context monkeypatches, so MARSHAL_PATH must be
    redirected on `_config_core_mod` itself for its load_config() to resolve the
    fixture marshal.json.
    """
    # fresh marshal.json with the seeded default block
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['queue']['max_slots'] == 5  # precondition: seeded default

    # write a custom max_slots override into the persisted config
    config['build']['queue']['max_slots'] = 12
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    reloaded = _config_core_mod.load_config()

    # load_config surfaces the override, not the 5 default
    assert reloaded['build']['queue']['max_slots'] == 12


def test_marshal_build_queue_max_retries_override_wins(plan_context, monkeypatch):
    """An explicit marshal.json build.queue.max_retries overrides the default of 10."""
    # fresh marshal.json with the seeded default block
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['queue']['max_retries'] == 10  # precondition: seeded default

    # write a custom max_retries override into the persisted config
    config['build']['queue']['max_retries'] = 3
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    reloaded = _config_core_mod.load_config()

    # load_config surfaces the override, not the 10 default
    assert reloaded['build']['queue']['max_retries'] == 3


# =============================================================================
# Per-phase effort defaults seeded at init (D9)
# =============================================================================
#
# get_default_config() seeds per-phase `effort` keys (plan.<phase>.effort) plus
# the plan-wide `plan.effort` fallback, mirroring the `balanced` named preset's
# expanded shape, so a freshly-initialized project gets per-phase model tuning
# out of the box and `effort resolve-target` resolves a concrete
# `execution-context-{level}` rather than falling back to `inherit`.

# The seeded per-phase effort shape (mirrors EffortPresets.BALANCED expanded).
_EXPECTED_PHASE_EFFORT = {
    'phase-1-init': 'level-3',
    'phase-2-refine': 'level-3',
    'phase-3-outline': 'level-4',
    'phase-4-plan': 'level-3',
    'phase-5-execute': {'default': 'level-4', 'verification-feedback': 'level-3'},
    'phase-6-finalize': {
        'default': 'level-3',
        'verification-feedback': 'level-3',
        'post-run-review': 'level-4',
    },
}
_EXPECTED_PLAN_WIDE_EFFORT = 'level-3'


def test_default_plan_blocks_carry_per_phase_effort():
    """Each DEFAULT_PLAN_* block must seed an `effort` key matching the balanced baseline."""
    blocks = {
        'phase-1-init': _config_defaults_mod.DEFAULT_PLAN_INIT,
        'phase-2-refine': _config_defaults_mod.DEFAULT_PLAN_REFINE,
        'phase-3-outline': _config_defaults_mod.DEFAULT_PLAN_OUTLINE,
        'phase-4-plan': _config_defaults_mod.DEFAULT_PLAN_PLAN,
        'phase-5-execute': _config_defaults_mod.DEFAULT_PLAN_EXECUTE,
        'phase-6-finalize': _config_defaults_mod.DEFAULT_PLAN_FINALIZE,
    }

    # each block carries the expected effort shape
    for phase, block in blocks.items():
        assert 'effort' in block, (
            f'{phase} DEFAULT_PLAN block must seed a per-phase effort key'
        )
        assert block['effort'] == _EXPECTED_PHASE_EFFORT[phase], (
            f'{phase} effort default must be {_EXPECTED_PHASE_EFFORT[phase]!r}'
        )


def test_default_plan_effort_plan_wide_fallback_is_level_3():
    """DEFAULT_PLAN_EFFORT must seed the plan-wide fallback at level-3."""
    assert _config_defaults_mod.DEFAULT_PLAN_EFFORT == _EXPECTED_PLAN_WIDE_EFFORT


def test_get_default_config_seeds_per_phase_effort():
    """get_default_config() must surface per-phase effort under each plan.<phase>."""
    config = _config_defaults_mod.get_default_config()

    # every phase block carries the expected effort
    plan_block = config['plan']
    for phase, expected in _EXPECTED_PHASE_EFFORT.items():
        assert plan_block[phase].get('effort') == expected, (
            f'plan.{phase}.effort must be seeded as {expected!r}'
        )


def test_get_default_config_seeds_plan_wide_effort_fallback():
    """get_default_config() must surface plan.effort == level-3 (plan-wide fallback)."""
    config = _config_defaults_mod.get_default_config()

    assert config['plan'].get('effort') == _EXPECTED_PLAN_WIDE_EFFORT


def test_effort_resolve_target_resolves_concrete_level_on_fresh_config(plan_context):
    """`effort resolve-target` resolves a concrete level (not inherit) on a freshly-seeded config.

    Initializes a fresh marshal.json (which now carries per-phase effort
    defaults) via the plan_context-redirected _config_core, then resolves the
    phase-5-execute default role — it must return a concrete
    `execution-context-level-4` target rather than the `inherit`/`implicit_default`
    fallback that an unseeded config produced. `_cmd_init`, `_cmd_effort`, and the
    fixture all bind the same cached `_config_core`, so plan_context's MARSHAL_PATH
    redirect is sufficient (mirrors the simplicity-default get test).
    """
    # fresh marshal.json with the seeded effort defaults
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # resolve the phase-5-execute default role target
    args = Namespace(phase='phase-5-execute', role='default', default=False)
    result = _cmd_effort_mod.cmd_effort_resolve_target(args)

    # concrete level-4 resolution, not inherit
    assert result['status'] == 'success'
    assert result['level'] == 'level-4'
    assert result['target'] == 'execution-context-level-4'
    assert result['source'] == 'plan.phase-5-execute.effort.default'


def test_effort_resolve_target_default_resolves_plan_wide_level_on_fresh_config(plan_context):
    """`effort resolve-target --default` resolves the plan-wide level-3 on a fresh config.

    The plan-wide `plan.effort` fallback is seeded, so the --default short-circuit
    no longer reports `level: inherit, source: implicit_default`.
    """
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # resolve via plan.effort (no role/phase lookup)
    args = Namespace(phase=None, role=None, default=True)
    result = _cmd_effort_mod.cmd_effort_resolve_target(args)

    # concrete plan-wide level, sourced from plan.effort
    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['target'] == 'execution-context-level-3'
    assert result['source'] == 'plan.effort'
