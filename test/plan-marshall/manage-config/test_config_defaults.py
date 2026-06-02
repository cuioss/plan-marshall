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


def test_default_plan_finalize_includes_auto_merge_after_ci():
    """DEFAULT_PLAN_FINALIZE must declare auto_merge_after_ci with default True."""
    # Arrange
    finalize_defaults = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert
    assert 'auto_merge_after_ci' in finalize_defaults, (
        'auto_merge_after_ci must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize_defaults['auto_merge_after_ci'] is True, (
        'auto_merge_after_ci default must be True '
        '(auto-merge after CI, serialized via the cross-plan merge-lock; '
        'set False to prompt on every merge)'
    )


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


def test_default_plan_execute_includes_per_task_budget_reserve():
    """DEFAULT_PLAN_EXECUTE must declare per_task_budget_reserve with default 50000."""
    # Arrange
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    # Act / Assert
    assert 'per_task_budget_reserve' in execute_defaults, (
        'per_task_budget_reserve must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['per_task_budget_reserve'] == 50000, (
        'per_task_budget_reserve default must be 50000 (phase-5-execute sentinel reserve)'
    )


def test_get_default_config_includes_per_task_budget_reserve():
    """get_default_config() must surface plan.phase-5-execute.per_task_budget_reserve == 50000."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    execute = config['plan']['phase-5-execute']
    assert execute.get('per_task_budget_reserve') == 50000


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


def test_default_plan_finalize_includes_pre_push_quality_gate():
    """DEFAULT_PLAN_FINALIZE must declare pre_push_quality_gate with empty activation_globs."""
    # Arrange
    finalize_defaults = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert
    assert 'pre_push_quality_gate' in finalize_defaults, (
        'pre_push_quality_gate must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize_defaults['pre_push_quality_gate'] == {'activation_globs': []}, (
        'pre_push_quality_gate default must be {activation_globs: []} (step inactive by default)'
    )


def test_get_default_config_includes_pre_push_quality_gate():
    """get_default_config() must surface plan.phase-6-finalize.pre_push_quality_gate.activation_globs == []."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    finalize = config['plan']['phase-6-finalize']
    assert finalize.get('pre_push_quality_gate') == {'activation_globs': []}


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


_EXPECTED_BRANCH_NAMING = {
    'working_prefixes': ['feature/', 'fix/', 'chore/'],
    'ci_allowlist': ['main', 'feature/*', 'fix/*', 'chore/*', 'dependabot/**'],
}


def test_default_project_includes_branch_naming_block():
    """DEFAULT_PROJECT must declare branch_naming with the canonical sets."""
    # Arrange
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    # Act / Assert
    assert 'branch_naming' in project_defaults
    assert project_defaults['branch_naming'] == _EXPECTED_BRANCH_NAMING


def test_get_default_config_includes_branch_naming():
    """get_default_config() must surface project.branch_naming with both sets."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert config['project'].get('branch_naming') == _EXPECTED_BRANCH_NAMING


def test_default_branch_naming_excludes_docs_prefix():
    """The default ci_allowlist must NOT contain the retired 'docs/' prefix."""
    # Arrange
    allowlist = _config_defaults_mod.DEFAULT_PROJECT['branch_naming']['ci_allowlist']
    working = _config_defaults_mod.DEFAULT_PROJECT['branch_naming']['working_prefixes']

    # Act / Assert — 'docs/' is explicitly retired from both sets
    assert not any('docs' in entry for entry in allowlist), (
        "'docs/' is explicitly retired and must be absent from ci_allowlist"
    )
    assert 'docs/' not in working


def test_project_get_branch_naming_returns_default_when_key_absent(plan_context):
    """A fresh marshal.json lacking branch_naming returns the default block."""
    # Arrange — init then strip branch_naming to emulate a legacy marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('project', {}).pop('branch_naming', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    args = Namespace(verb='get', field='branch_naming')
    result = _cmd_system_plan_mod.cmd_project(args)

    # Assert — implicit-default fallback to DEFAULT_PROJECT['branch_naming']
    assert result['status'] == 'success'
    assert result['value'] == _EXPECTED_BRANCH_NAMING


def test_project_set_then_get_roundtrip_branch_naming(plan_context):
    """`project set --field branch_naming --value <json>` round-trips via get."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    custom = {
        'working_prefixes': ['feature/', 'fix/', 'chore/', 'spike/'],
        'ci_allowlist': ['main', 'feature/*', 'fix/*', 'chore/*', 'spike/*', 'dependabot/**'],
    }

    # Act — set (JSON value)
    set_args = Namespace(verb='set', field='branch_naming', value=json.dumps(custom))
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # Act — get
    get_args = Namespace(verb='get', field='branch_naming')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    # Assert — the dict round-trips, not a bare JSON string
    assert get_result['status'] == 'success'
    assert get_result['value'] == custom


def test_project_set_branch_naming_rejects_invalid_json(plan_context):
    """`project set --field branch_naming` with a non-JSON value errors out."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act
    set_args = Namespace(verb='set', field='branch_naming', value='not-json')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    # Assert
    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_json'


def test_read_branch_naming_returns_live_block():
    """read_branch_naming returns the live project.branch_naming when present."""
    # Arrange
    custom = {
        'working_prefixes': ['feature/', 'spike/'],
        'ci_allowlist': ['main', 'feature/*'],
    }
    config = {'project': {'branch_naming': custom}}

    # Act
    result = _cmd_system_plan_mod.read_branch_naming(config)

    # Assert
    assert result == custom


def test_read_branch_naming_falls_back_to_default():
    """read_branch_naming returns the default block when the key is absent."""
    # Arrange — config with no project.branch_naming
    config: dict = {'project': {}}

    # Act
    result = _cmd_system_plan_mod.read_branch_naming(config)

    # Assert — fail-closed to DEFAULT_PROJECT['branch_naming']
    assert result == _EXPECTED_BRANCH_NAMING


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
    and before default:commit-push (order 10, index 2).
    """
    # Arrange
    steps = _config_defaults_mod.BUILT_IN_FINALIZE_STEPS

    # Act / Assert — presence and ordinal placement
    assert 'default:finalize-step-simplify' in steps, (
        'default:finalize-step-simplify must be seeded into BUILT_IN_FINALIZE_STEPS'
    )
    assert steps[0] == 'default:pre-push-quality-gate'
    assert steps[1] == 'default:finalize-step-simplify'
    assert steps[2] == 'default:commit-push'


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
