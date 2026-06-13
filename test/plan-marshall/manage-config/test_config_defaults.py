#!/usr/bin/env python3
"""Test default-config schema additions for the split-gate / default-base-branch plan.

Covers:
- `DEFAULT_PLAN_FINALIZE` includes `auto_merge_after_ci` with default `False`.
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


def test_default_plan_finalize_includes_auto_merge_after_ci():
    """DEFAULT_PLAN_FINALIZE must declare auto_merge_after_ci with default True.

    The knob is a flat field under plan.phase-6-finalize — the ceremony_policy
    block was dissolved and every automation knob distributed back into its
    owning phase.
    """
    # Arrange
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert — homed in the phase block with the True default
    assert 'auto_merge_after_ci' in finalize, (
        'auto_merge_after_ci must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize['auto_merge_after_ci'] is True, (
        'auto_merge_after_ci default must be True '
        '(auto-merge after CI, serialized via the cross-plan merge-lock; '
        'set False to prompt on every merge)'
    )


def test_default_plan_finalize_simplify_defaults_to_auto():
    """DEFAULT_PLAN_FINALIZE must declare the simplify gate with default 'auto'.

    `simplify` is the symmetric peer of the other three finalize gates
    (self_review / qgate / plugin_doctor): `auto` defers to the manifest
    composer's `simplify_inactive` pre-filter, while always/never force the
    finalize-step-simplify step in/out.
    """
    # Arrange
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert
    assert 'simplify' in finalize, (
        'simplify must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize['simplify'] == 'auto', (
        "plan.phase-6-finalize.simplify default must be 'auto' "
        '(defer to the simplify_inactive pre-filter)'
    )


def test_get_default_config_includes_finalize_simplify():
    """get_default_config() must surface plan.phase-6-finalize.simplify == 'auto'."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    finalize = config['plan']['phase-6-finalize']
    assert finalize.get('simplify') == 'auto'


def test_default_plan_finalize_carries_all_four_finalize_gates():
    """DEFAULT_PLAN_FINALIZE must carry the four distributed finalize gates at 'auto'."""
    # Arrange / Act
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Assert — the symmetric-peer ladder: simplify joins the existing three gates
    for gate in ('self_review', 'qgate', 'plugin_doctor', 'simplify'):
        assert finalize.get(gate) == 'auto', (
            f'plan.phase-6-finalize.{gate} default must be auto'
        )


def test_validate_run_at_all_accepts_simplify_run_at_all_values():
    """validate_run_at_all must accept every auto|always|never value for the simplify gate."""
    # Arrange / Act / Assert — no exception for any allowed run-at-all value
    for value in _config_defaults_mod.VALID_RUN_AT_ALL:
        _config_defaults_mod.validate_run_at_all(value, 'plan.phase-6-finalize.simplify')


def test_validate_run_at_all_rejects_invalid_simplify_value():
    """validate_run_at_all must raise ValueError for a simplify value outside the enum."""
    # Arrange / Act / Assert
    import pytest

    with pytest.raises(ValueError, match=r'plan\.phase-6-finalize\.simplify'):
        _config_defaults_mod.validate_run_at_all('sometimes', 'plan.phase-6-finalize.simplify')


def test_default_plan_finalize_includes_auto_rebase_threshold():
    """DEFAULT_PLAN_FINALIZE must declare auto_rebase_threshold with default 'no_overlap_only'."""
    # Arrange
    finalize_defaults = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert
    assert 'auto_rebase_threshold' in finalize_defaults, (
        'auto_rebase_threshold must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize_defaults['auto_rebase_threshold'] == 'no_overlap_only', (
        "auto_rebase_threshold default must be 'no_overlap_only'"
    )


def test_get_default_config_includes_auto_rebase_threshold():
    """get_default_config() must surface plan.phase-6-finalize.auto_rebase_threshold == 'no_overlap_only'."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    finalize = config['plan']['phase-6-finalize']
    assert 'auto_rebase_threshold' in finalize, (
        'auto_rebase_threshold must round-trip through get_default_config()'
    )
    assert finalize['auto_rebase_threshold'] == 'no_overlap_only'


def test_default_plan_execute_includes_per_task_budget_reserve_tokens():
    """DEFAULT_PLAN_EXECUTE must declare per_task_budget_reserve_tokens with default "50K"."""
    # Arrange
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    # Act / Assert
    assert 'per_task_budget_reserve_tokens' in execute_defaults, (
        'per_task_budget_reserve_tokens must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['per_task_budget_reserve_tokens'] == '50K', (
        'per_task_budget_reserve_tokens default must be the human-friendly "50K" '
        '(phase-5-execute sentinel reserve)'
    )
    # The human-friendly string round-trips to the documented int via the shared parser.
    assert parse_sensible_int(execute_defaults['per_task_budget_reserve_tokens']) == 50000


def test_get_default_config_includes_per_task_budget_reserve_tokens():
    """get_default_config() must surface plan.phase-5-execute.per_task_budget_reserve_tokens == "50K"."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    execute = config['plan']['phase-5-execute']
    assert execute.get('per_task_budget_reserve_tokens') == '50K'
    assert parse_sensible_int(execute['per_task_budget_reserve_tokens']) == 50000


def test_default_plan_execute_includes_per_deliverable_build():
    """DEFAULT_PLAN_EXECUTE must declare per_deliverable_build with default compile+scoped-test."""
    # Arrange
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    # Act / Assert
    assert 'per_deliverable_build' in execute_defaults, (
        'per_deliverable_build must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['per_deliverable_build'] == 'compile+scoped-test', (
        'per_deliverable_build default must be compile+scoped-test (focused per-deliverable build)'
    )


def test_get_default_config_includes_per_deliverable_build():
    """get_default_config() must surface plan.phase-5-execute.per_deliverable_build == compile+scoped-test."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    execute = config['plan']['phase-5-execute']
    assert execute.get('per_deliverable_build') == 'compile+scoped-test'


def test_valid_per_deliverable_build_enumerates_expected_values():
    """VALID_PER_DELIVERABLE_BUILD must enumerate exactly the four allowed enum values."""
    # Arrange / Act
    values = _config_defaults_mod.VALID_PER_DELIVERABLE_BUILD

    # Assert — default must be a member of the enum
    assert values == ('off', 'compile-only', 'compile+scoped-test', 'full')
    assert _config_defaults_mod.DEFAULT_PLAN_EXECUTE['per_deliverable_build'] in values


def test_validate_per_deliverable_build_accepts_allowed_values():
    """validate_per_deliverable_build must accept every value in VALID_PER_DELIVERABLE_BUILD."""
    # Arrange / Act / Assert — no exception for any allowed value
    for value in _config_defaults_mod.VALID_PER_DELIVERABLE_BUILD:
        _config_defaults_mod.validate_per_deliverable_build(value)


def test_validate_per_deliverable_build_rejects_unknown_value():
    """validate_per_deliverable_build must raise ValueError for a value outside the enum."""
    # Arrange / Act / Assert
    import pytest

    with pytest.raises(ValueError, match='Invalid per_deliverable_build'):
        _config_defaults_mod.validate_per_deliverable_build('reckless')


def test_default_plan_finalize_omits_pre_push_quality_gate_activation_globs():
    """DEFAULT_PLAN_FINALIZE must NOT carry a pre_push_quality_gate.activation_globs knob.

    Pre-push activation is derived entirely from build.map globs
    (D7/D8); the separate finalize-phase pre_push_quality_gate config field was
    dropped, so a surviving seed would re-introduce a dead activation source.
    """
    # Arrange / Act / Assert
    assert 'pre_push_quality_gate' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_omits_pre_push_quality_gate():
    """get_default_config() must NOT surface plan.phase-6-finalize.pre_push_quality_gate."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'pre_push_quality_gate' not in config['plan']['phase-6-finalize']


def test_default_project_default_base_branch_is_main():
    """DEFAULT_PROJECT must declare default_base_branch == 'main'."""
    # Arrange
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    # Act / Assert
    assert 'default_base_branch' in project_defaults
    assert project_defaults['default_base_branch'] == 'main'


def test_get_default_config_includes_project_block():
    """get_default_config() must include the 'project' block with default_base_branch == 'main'."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_fresh_marshal_seeds_project_default_base_branch_main(plan_context):
    """`manage-config init` against a fresh fixture must seed project.default_base_branch=main."""
    # Arrange / Act
    result = _cmd_init_mod.cmd_init(Namespace(force=False))

    # Assert
    assert result['status'] == 'success'
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists()

    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_project_set_then_get_roundtrip_default_base_branch(plan_context):
    """`project set --field default_base_branch --value develop` must round-trip via get."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — set
    set_args = Namespace(verb='set', field='default_base_branch', value='develop')
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # Act — get
    get_args = Namespace(verb='get', field='default_base_branch')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    # Assert
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'develop'


def test_project_get_returns_default_when_block_absent(plan_context):
    """A fresh marshal.json without the `project` block returns DEFAULT_PROJECT values."""
    # Arrange — initialize then remove `project` block to emulate legacy schema
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('project', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    args = Namespace(verb='get', field='default_base_branch')
    result = _cmd_system_plan_mod.cmd_project(args)

    # Assert — implicit-default semantics mirror open_in_ide / DEFAULT_PLAN_* blocks
    assert result['status'] == 'success'
    assert result['value'] == 'main'


_EXPECTED_WORKING_PREFIXES = ['feature/', 'fix/', 'chore/']


def test_default_project_includes_working_prefixes():
    """DEFAULT_PROJECT must declare working_prefixes with the canonical set."""
    # Arrange
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    # Act / Assert
    assert 'working_prefixes' in project_defaults
    assert project_defaults['working_prefixes'] == _EXPECTED_WORKING_PREFIXES


def test_default_project_drops_branch_naming_wrapper():
    """The flattened model removes the nested branch_naming wrapper entirely."""
    # Arrange / Act / Assert
    assert 'branch_naming' not in _config_defaults_mod.DEFAULT_PROJECT


def test_get_default_config_includes_working_prefixes():
    """get_default_config() must surface project.working_prefixes."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert config['project'].get('working_prefixes') == _EXPECTED_WORKING_PREFIXES


def test_default_working_prefixes_excludes_docs_prefix():
    """The default working_prefixes must NOT contain the retired 'docs/' prefix."""
    # Arrange
    working = _config_defaults_mod.DEFAULT_PROJECT['working_prefixes']

    # Act / Assert — 'docs/' is explicitly retired
    assert 'docs/' not in working


def test_project_get_working_prefixes_returns_default_when_key_absent(plan_context):
    """A fresh marshal.json lacking working_prefixes returns the default list."""
    # Arrange — init then strip working_prefixes to emulate a legacy marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('project', {}).pop('working_prefixes', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    args = Namespace(verb='get', field='working_prefixes')
    result = _cmd_system_plan_mod.cmd_project(args)

    # Assert — implicit-default fallback to DEFAULT_PROJECT['working_prefixes']
    assert result['status'] == 'success'
    assert result['value'] == _EXPECTED_WORKING_PREFIXES


def test_project_set_then_get_roundtrip_working_prefixes(plan_context):
    """`project set --field working_prefixes --value <json>` round-trips via get."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    custom = ['feature/', 'fix/', 'chore/', 'spike/']

    # Act — set (JSON array value)
    set_args = Namespace(verb='set', field='working_prefixes', value=json.dumps(custom))
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # Act — get
    get_args = Namespace(verb='get', field='working_prefixes')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    # Assert — the list round-trips, not a bare JSON string
    assert get_result['status'] == 'success'
    assert get_result['value'] == custom


def test_project_set_working_prefixes_rejects_invalid_json(plan_context):
    """`project set --field working_prefixes` with a non-JSON value errors out."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act
    set_args = Namespace(verb='set', field='working_prefixes', value='not-json')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    # Assert
    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_json'


def test_project_set_working_prefixes_rejects_non_array(plan_context):
    """`project set --field working_prefixes` with a non-array JSON value errors out."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — a JSON object is valid JSON but the wrong shape
    set_args = Namespace(verb='set', field='working_prefixes', value='{"a": 1}')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    # Assert
    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_type'


def test_default_project_omits_sanctioned_conftest_key():
    """DEFAULT_PROJECT must NOT declare sanctioned_conftest — the seed was removed (D2).

    The conftest-vs-_fixtures.py naming rule is now advisory prose only; it is no
    longer a shipped config field. A surviving seed would re-introduce the
    meta-project-convention leak this deliverable removed.
    """
    # Arrange / Act / Assert
    assert 'sanctioned_conftest' not in _config_defaults_mod.DEFAULT_PROJECT


def test_get_default_config_omits_sanctioned_conftest_key():
    """get_default_config() must NOT surface project.sanctioned_conftest — the field is gone."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'sanctioned_conftest' not in config['project']


def test_default_plan_refine_includes_simplicity_lean():
    """DEFAULT_PLAN_REFINE must declare simplicity with default 'lean'.

    Mirrors the sibling `compatibility` knob — simplicity controls how
    aggressively the implementation favours the minimum viable surface.
    """
    # Arrange
    refine_defaults = _config_defaults_mod.DEFAULT_PLAN_REFINE

    # Act / Assert
    assert 'simplicity' in refine_defaults, (
        'simplicity must be schema-registered in DEFAULT_PLAN_REFINE'
    )
    assert refine_defaults['simplicity'] == 'lean', (
        "simplicity default must be 'lean' (implement the strict minimum)"
    )


def test_get_default_config_phase_2_refine_includes_simplicity_lean():
    """get_default_config() must surface simplicity == 'lean' under plan.phase-2-refine."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    refine_block = config['plan']['phase-2-refine']
    assert refine_block.get('simplicity') == 'lean'


def test_valid_simplicity_levels_enumerates_expected_values():
    """VALID_SIMPLICITY_LEVELS must enumerate exactly the three allowed enum values."""
    # Arrange / Act
    levels = _config_defaults_mod.VALID_SIMPLICITY_LEVELS

    # Assert — default 'lean' must be a member of the enum
    assert levels == ('lean', 'pragmatic', 'defensive')
    assert _config_defaults_mod.DEFAULT_PLAN_REFINE['simplicity'] in levels


def test_validate_simplicity_accepts_allowed_values():
    """validate_simplicity must accept every value in VALID_SIMPLICITY_LEVELS."""
    # Arrange / Act / Assert — no exception for any allowed value
    for value in _config_defaults_mod.VALID_SIMPLICITY_LEVELS:
        _config_defaults_mod.validate_simplicity(value)


def test_validate_simplicity_rejects_unknown_value():
    """validate_simplicity must raise ValueError for a value outside the enum."""
    # Arrange / Act / Assert
    import pytest

    with pytest.raises(ValueError, match='Invalid simplicity'):
        _config_defaults_mod.validate_simplicity('reckless')


def test_plan_phase_2_refine_get_simplicity_returns_lean_default(plan_context):
    """`plan phase-2-refine get --field simplicity` returns 'lean' from the merged default config.

    Exercises the actual cmd_phase get path (same code `manage-config plan
    phase-2-refine get --field simplicity` runs) against a fresh marshal.json,
    proving the default surfaces even when the persisted config omits the key.
    """
    # Arrange — fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — get the simplicity field via the phase handler
    args = Namespace(verb='get', field='simplicity')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-2-refine')

    # Assert — default merge surfaces 'lean'
    assert result['status'] == 'success'
    assert result['value'] == 'lean'


def test_built_in_finalize_steps_includes_finalize_step_simplify_at_order_8_position():
    """default:finalize-step-simplify occupies the order-8 ordinal slot in BUILT_IN_FINALIZE_STEPS.

    The slot is index 1: after default:pre-push-quality-gate (order 5, index 0)
    and before default:finalize-step-whole-tree-gate (order 9, index 2) and
    default:commit-push (order 10, index 3).
    """
    # Arrange
    steps = _config_defaults_mod.BUILT_IN_FINALIZE_STEPS

    # Act / Assert — presence and ordinal placement
    assert 'default:finalize-step-simplify' in steps, (
        'default:finalize-step-simplify must be seeded into BUILT_IN_FINALIZE_STEPS'
    )
    assert steps[0] == 'default:pre-push-quality-gate'
    assert steps[1] == 'default:finalize-step-simplify'
    assert steps[2] == 'default:finalize-step-whole-tree-gate'
    assert steps[3] == 'default:commit-push'


def test_built_in_finalize_step_descriptions_includes_finalize_step_simplify():
    """default:finalize-step-simplify must carry a non-empty description entry.

    The descriptions dict must stay in sync with BUILT_IN_FINALIZE_STEPS so
    list-finalize-steps can surface a human-readable description.
    """
    # Arrange
    descriptions = _config_defaults_mod.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS

    # Act / Assert
    assert 'default:finalize-step-simplify' in descriptions, (
        'default:finalize-step-simplify must have a BUILT_IN_FINALIZE_STEP_DESCRIPTIONS entry'
    )
    assert descriptions['default:finalize-step-simplify'], (
        'default:finalize-step-simplify description must be non-empty'
    )


def test_built_in_finalize_steps_includes_whole_tree_gate_before_commit_push():
    """default:finalize-step-whole-tree-gate must sit before default:commit-push.

    The gate must run pre-commit so a surviving deleted-symbol reference BLOCKS
    the push — mirroring the pre-push-quality-gate ordering rationale. The new
    step is inserted after default:finalize-step-simplify (index 1) and before
    default:commit-push.
    """
    # Arrange
    steps = _config_defaults_mod.BUILT_IN_FINALIZE_STEPS

    # Act / Assert — presence and pre-commit ordinal placement
    assert 'default:finalize-step-whole-tree-gate' in steps, (
        'default:finalize-step-whole-tree-gate must be seeded into BUILT_IN_FINALIZE_STEPS'
    )
    gate_index = steps.index('default:finalize-step-whole-tree-gate')
    commit_index = steps.index('default:commit-push')
    simplify_index = steps.index('default:finalize-step-simplify')
    assert simplify_index < gate_index < commit_index, (
        'finalize-step-whole-tree-gate must run after finalize-step-simplify and '
        'before commit-push (pre-commit gate)'
    )


def test_built_in_finalize_step_descriptions_includes_whole_tree_gate():
    """default:finalize-step-whole-tree-gate must carry a non-empty description entry."""
    # Arrange
    descriptions = _config_defaults_mod.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS

    # Act / Assert
    assert 'default:finalize-step-whole-tree-gate' in descriptions, (
        'default:finalize-step-whole-tree-gate must have a BUILT_IN_FINALIZE_STEP_DESCRIPTIONS entry'
    )
    assert descriptions['default:finalize-step-whole-tree-gate'], (
        'default:finalize-step-whole-tree-gate description must be non-empty'
    )


def test_get_default_config_seeds_whole_tree_gate_in_finalize_steps():
    """get_default_config() must surface finalize-step-whole-tree-gate in the default candidate set."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    steps = config['plan']['phase-6-finalize']['steps']
    assert 'default:finalize-step-whole-tree-gate' in steps


def test_default_plan_coverage_is_inherit_inherit():
    """DEFAULT_PLAN_COVERAGE must declare the behavior-preserving inherit/inherit seed."""
    # Arrange
    coverage_default = _config_defaults_mod.DEFAULT_PLAN_COVERAGE

    # Act / Assert
    assert coverage_default == {'thoroughness': 'inherit', 'scope': 'inherit'}, (
        'DEFAULT_PLAN_COVERAGE must be the byte-identical inherit/inherit fallback seed'
    )


def test_get_default_config_includes_plan_wide_coverage():
    """get_default_config() must surface plan.coverage == inherit/inherit (plan-wide knob)."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert config['plan']['coverage'] == {'thoroughness': 'inherit', 'scope': 'inherit'}


def test_get_default_config_seeds_no_per_phase_coverage():
    """No per-phase default block may carry a coverage key — coverage is plan-wide only.

    The per-invocation coverage cell lives in status.json metadata per the
    coverage-gathering contract; only plan.coverage is the operator-visible
    project default. A per-phase coverage seed would be inert and is forbidden.
    """
    # Arrange / Act
    plan_config = _config_defaults_mod.get_default_config()['plan']

    # Assert — walk every per-phase block (keys shaped 'phase-N-...')
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
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert — no build.map block, and the legacy skill_domains.build_map is absent.
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
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert — no override layer anywhere.
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
    # Arrange — a config with a build.map block at the relocated top-level path.
    build_map = {
        'python': [
            {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
            {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
        ],
    }
    config = {'build': {'map': build_map}, 'skill_domains': {'system': {}}}
    marshal_path = tmp_path / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)

    # Act — persist then read back through the live readers.
    _config_core_mod.save_config(config)
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    merged = _config_core_mod.merge_build_map(persisted)

    # Assert — the relocated top-level path round-trips the data unchanged.
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
    # Arrange — every canonical key present, deliberately reverse-scrambled
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

    # Act
    actual_order = _save_config_to(marshal_path, scrambled, monkeypatch)

    # Assert — canonical order regardless of input order
    assert actual_order == _EXPECTED_CANONICAL_KEY_ORDER


def test_save_config_omits_absent_keys_preserving_relative_order(tmp_path, monkeypatch):
    """save_config must list only the present keys, in canonical relative order.

    The committed marshal.json omits extension_defaults; save_config must not
    fabricate an empty block for it, and the surviving keys must keep their
    canonical relative order.
    """
    # Arrange — drop extension_defaults (matching the committed file), scramble the rest
    config = {
        'system': {},
        'plan': {},
        'skill_domains': {},
        'project': {},
        'providers': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    # Act
    actual_order = _save_config_to(marshal_path, config, monkeypatch)

    # Assert — extension_defaults absent, others in canonical relative order
    assert actual_order == ['plan', 'project', 'providers', 'skill_domains', 'system']


def test_save_config_appends_unknown_keys_after_canonical_block(tmp_path, monkeypatch):
    """save_config must append unrecognized top-level keys after the canonical block.

    Unknown keys are preserved (never dropped) and placed after every canonical
    key, so a stray block survives a save without corrupting the canonical order.
    """
    # Arrange
    config = {
        'zzz_unknown': {},
        'system': {},
        'plan': {},
    }
    marshal_path = tmp_path / 'marshal.json'

    # Act
    actual_order = _save_config_to(marshal_path, config, monkeypatch)

    # Assert — canonical keys first (in order), unknown appended last
    assert actual_order == ['plan', 'system', 'zzz_unknown']


def test_committed_marshal_json_top_level_keys_already_canonical():
    """The committed .plan/marshal.json must already be in canonical key order.

    Regression guard: the shipped file must not drift out of the order
    save_config enforces, otherwise the next save would reorder it and produce a
    spurious diff.
    """
    # Arrange / Act
    assert _COMMITTED_MARSHAL_PATH.exists(), (
        f'committed marshal.json must exist at {_COMMITTED_MARSHAL_PATH}'
    )
    committed = json.loads(_COMMITTED_MARSHAL_PATH.read_text(encoding='utf-8'))
    committed_keys = list(committed.keys())

    # Assert — the committed key order equals the canonical order filtered to present keys
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
    # Arrange — load the committed config and capture its current key order
    committed = json.loads(_COMMITTED_MARSHAL_PATH.read_text(encoding='utf-8'))
    before = list(committed.keys())
    marshal_path = tmp_path / 'marshal.json'

    # Act — persist via save_config to the redirected fixture path
    after = _save_config_to(marshal_path, committed, monkeypatch)

    # Assert — key order is unchanged by the round-trip
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
    # Arrange
    build_queue = _config_defaults_mod.DEFAULT_BUILD_QUEUE

    # Act / Assert
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
    # Arrange
    build_queue = _config_defaults_mod.DEFAULT_BUILD_QUEUE

    # Act / Assert
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
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('max_slots') == 5


def test_get_default_config_surfaces_build_queue_max_retries_default_10():
    """get_default_config() must surface build.queue.max_retries == 10 when unconfigured."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('max_retries') == 10


def test_get_default_config_surfaces_build_queue_upper_limit_seconds_default_600():
    """get_default_config() must surface build.queue.upper_limit_seconds == 600."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'queue' in config.get('build', {}), (
        'build.queue must live under the top-level build block in get_default_config()'
    )
    assert config['build']['queue'].get('upper_limit_seconds') == 600


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
    # Arrange — fresh marshal.json with the seeded default block
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['queue']['max_slots'] == 5  # precondition: seeded default

    # Act — write a custom max_slots override into the persisted config
    config['build']['queue']['max_slots'] = 12
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    reloaded = _config_core_mod.load_config()

    # Assert — load_config surfaces the override, not the 5 default
    assert reloaded['build']['queue']['max_slots'] == 12


def test_marshal_build_queue_max_retries_override_wins(plan_context, monkeypatch):
    """An explicit marshal.json build.queue.max_retries overrides the default of 10."""
    # Arrange — fresh marshal.json with the seeded default block
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    monkeypatch.setattr(_config_core_mod, 'MARSHAL_PATH', marshal_path)
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['queue']['max_retries'] == 10  # precondition: seeded default

    # Act — write a custom max_retries override into the persisted config
    config['build']['queue']['max_retries'] = 3
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    reloaded = _config_core_mod.load_config()

    # Assert — load_config surfaces the override, not the 10 default
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
    # Arrange
    blocks = {
        'phase-1-init': _config_defaults_mod.DEFAULT_PLAN_INIT,
        'phase-2-refine': _config_defaults_mod.DEFAULT_PLAN_REFINE,
        'phase-3-outline': _config_defaults_mod.DEFAULT_PLAN_OUTLINE,
        'phase-4-plan': _config_defaults_mod.DEFAULT_PLAN_PLAN,
        'phase-5-execute': _config_defaults_mod.DEFAULT_PLAN_EXECUTE,
        'phase-6-finalize': _config_defaults_mod.DEFAULT_PLAN_FINALIZE,
    }

    # Act / Assert — each block carries the expected effort shape
    for phase, block in blocks.items():
        assert 'effort' in block, (
            f'{phase} DEFAULT_PLAN block must seed a per-phase effort key'
        )
        assert block['effort'] == _EXPECTED_PHASE_EFFORT[phase], (
            f'{phase} effort default must be {_EXPECTED_PHASE_EFFORT[phase]!r}'
        )


def test_default_plan_effort_plan_wide_fallback_is_level_3():
    """DEFAULT_PLAN_EFFORT must seed the plan-wide fallback at level-3."""
    # Arrange / Act / Assert
    assert _config_defaults_mod.DEFAULT_PLAN_EFFORT == _EXPECTED_PLAN_WIDE_EFFORT


def test_get_default_config_seeds_per_phase_effort():
    """get_default_config() must surface per-phase effort under each plan.<phase>."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert — every phase block carries the expected effort
    plan_block = config['plan']
    for phase, expected in _EXPECTED_PHASE_EFFORT.items():
        assert plan_block[phase].get('effort') == expected, (
            f'plan.{phase}.effort must be seeded as {expected!r}'
        )


def test_get_default_config_seeds_plan_wide_effort_fallback():
    """get_default_config() must surface plan.effort == level-3 (plan-wide fallback)."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
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
    # Arrange — fresh marshal.json with the seeded effort defaults
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — resolve the phase-5-execute default role target
    args = Namespace(phase='phase-5-execute', role='default', default=False)
    result = _cmd_effort_mod.cmd_effort_resolve_target(args)

    # Assert — concrete level-4 resolution, not inherit
    assert result['status'] == 'success'
    assert result['level'] == 'level-4'
    assert result['target'] == 'execution-context-level-4'
    assert result['source'] == 'plan.phase-5-execute.effort.default'


def test_effort_resolve_target_default_resolves_plan_wide_level_on_fresh_config(plan_context):
    """`effort resolve-target --default` resolves the plan-wide level-3 on a fresh config.

    The plan-wide `plan.effort` fallback is seeded, so the --default short-circuit
    no longer reports `level: inherit, source: implicit_default`.
    """
    # Arrange — fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — resolve via plan.effort (no role/phase lookup)
    args = Namespace(phase=None, role=None, default=True)
    result = _cmd_effort_mod.cmd_effort_resolve_target(args)

    # Assert — concrete plan-wide level, sourced from plan.effort
    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['target'] == 'execution-context-level-3'
    assert result['source'] == 'plan.effort'
