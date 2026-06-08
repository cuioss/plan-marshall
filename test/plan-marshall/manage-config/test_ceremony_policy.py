#!/usr/bin/env python3
"""Tests for the ``ceremony_policy`` schema, defaults, and footgun guardrails.

Covers the four contract areas the deliverable declares:

1. Defaults load correctly — ``DEFAULT_CEREMONY_POLICY`` carries the expected
   two-axis structure (run-at-all gates + automation), and ``get_default_config()``
   surfaces it at the top level (sibling to ``plan`` / ``ci`` / ``project``).
2. Footgun warnings fire at set-time — ``ceremony_set_footgun_warnings`` emits a
   ``[WARNING]`` for each gate set to ``never``, with the hard-footgun tier
   (``finalize.qgate``) naming the masking risk; non-footgun / non-``never``
   changes stay silent.
3. ``planning`` and ``automation`` sub-keys are independently settable — the
   validator accepts a policy that mutates one section while leaving the other at
   defaults, and the override-matcher scopes a row to plan facts.
4. Backward compatibility with existing automation config values is preserved —
   the migrated ``automation`` axis seeds today's loose-knob defaults verbatim.

The validator and footgun helpers are unit-level pure functions, so these tests
call them directly via per-file ``importlib`` loading (matching the manage-config
test convention).
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from pathlib import Path

import pytest

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
    '_config_defaults_for_ceremony_test', '_config_defaults.py'
)
# `_cmd_finalize_steps` imports `finalize_step_presets` and `_config_defaults`
# at module level; the scripts dir is already on sys.path above.
_cmd_finalize_steps_mod = _load_module(
    '_cmd_finalize_steps_for_ceremony_test', '_cmd_finalize_steps.py'
)

ceremony_set_footgun_warnings = _cmd_finalize_steps_mod.ceremony_set_footgun_warnings
ceremony_override_matches = _cmd_finalize_steps_mod.ceremony_override_matches
validate_ceremony_policy = _config_defaults_mod.validate_ceremony_policy


# =============================================================================
# (1) Defaults load correctly
# =============================================================================


def test_default_ceremony_policy_has_expected_structure():
    """DEFAULT_CEREMONY_POLICY must carry both axes plus an empty overrides list."""
    # Arrange
    policy = _config_defaults_mod.DEFAULT_CEREMONY_POLICY

    # Act / Assert — top-level sections
    assert set(policy.keys()) == {'planning', 'finalize', 'automation', 'overrides'}
    assert policy['overrides'] == []


def test_default_ceremony_policy_planning_gates_all_auto():
    """The planning run-at-all gates default to 'auto' for every declared gate."""
    # Arrange
    planning = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['planning']

    # Act / Assert — every CEREMONY_PLANNING_GATES key present and 'auto'
    for gate in _config_defaults_mod.CEREMONY_PLANNING_GATES:
        assert planning[gate] == 'auto', f'planning.{gate} default must be auto'
    assert set(planning.keys()) == set(_config_defaults_mod.CEREMONY_PLANNING_GATES)


def test_default_ceremony_policy_finalize_gates_all_auto():
    """The finalize run-at-all gates default to 'auto' for every declared gate."""
    # Arrange
    finalize = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['finalize']

    # Act / Assert
    for gate in _config_defaults_mod.CEREMONY_FINALIZE_GATES:
        assert finalize[gate] == 'auto', f'finalize.{gate} default must be auto'
    assert set(finalize.keys()) == set(_config_defaults_mod.CEREMONY_FINALIZE_GATES)


def test_get_default_config_includes_ceremony_policy_top_level():
    """get_default_config() must surface ceremony_policy as a top-level block."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert — sibling to plan / ci / project, NOT nested under plan
    assert 'ceremony_policy' in config
    assert 'ceremony_policy' not in config['plan']
    assert config['ceremony_policy'] == _config_defaults_mod.DEFAULT_CEREMONY_POLICY


def test_get_default_config_ceremony_policy_is_deep_copy():
    """get_default_config() must return a fresh ceremony_policy, not the module singleton."""
    # Arrange / Act — two independent calls
    first = _config_defaults_mod.get_default_config()['ceremony_policy']
    second = _config_defaults_mod.get_default_config()['ceremony_policy']

    # Assert — equal value, distinct identity (mutation isolation)
    assert first == second
    assert first is not second
    first['planning']['deep_lane'] = 'never'
    assert second['planning']['deep_lane'] == 'auto'


def test_valid_ceremony_run_at_all_enumerates_expected_values():
    """VALID_CEREMONY_RUN_AT_ALL must enumerate exactly auto|always|never."""
    # Arrange / Act / Assert
    assert _config_defaults_mod.VALID_CEREMONY_RUN_AT_ALL == ('auto', 'always', 'never')


# =============================================================================
# (2) Footgun warnings fire at set-time
# =============================================================================


def test_footgun_warning_fires_for_finalize_qgate_never(capsys):
    """Setting finalize.qgate=never emits a hard-footgun [WARNING] naming the masking risk."""
    # Arrange / Act
    warnings = ceremony_set_footgun_warnings({'finalize.qgate': 'never'})

    # Assert — one warning returned, naming the disabled safety + red-tree risk
    assert len(warnings) == 1
    message = warnings[0]
    assert '[WARNING]' in message
    assert 'finalize.qgate' in message
    assert 'red tree' in message
    # The hard-footgun tier must surface on stderr, not stdout.
    captured = capsys.readouterr()
    assert message in captured.err


def test_footgun_warning_fires_for_each_soft_footgun(capsys):
    """Each non-hard footgun gate set to never emits a warn-tier [WARNING]."""
    # Arrange — every soft footgun (all catalogue entries except the hard one)
    soft_footguns = [
        path
        for path in _config_defaults_mod.CEREMONY_FOOTGUNS
        if path not in _config_defaults_mod.CEREMONY_HARD_FOOTGUNS
    ]
    changes = dict.fromkeys(soft_footguns, 'never')

    # Act
    warnings = ceremony_set_footgun_warnings(changes)

    # Assert — one warning per soft footgun, each naming its path + "own the risk"
    assert len(warnings) == len(soft_footguns)
    joined = '\n'.join(warnings)
    for path in soft_footguns:
        assert path in joined
    assert 'own the risk' in joined
    captured = capsys.readouterr()
    assert captured.err  # emitted to stderr


def test_footgun_warning_silent_for_non_never_value():
    """A footgun gate set to a safe value (auto/always) emits no warning."""
    # Arrange / Act
    warnings = ceremony_set_footgun_warnings(
        {'finalize.qgate': 'auto', 'planning.deep_lane': 'always'}
    )

    # Assert — the operator is not warned for safe values
    assert warnings == []


def test_footgun_warning_silent_for_non_footgun_path():
    """A non-footgun path set to never emits no warning (not in the catalogue)."""
    # Arrange — planning.qgate is NOT in CEREMONY_FOOTGUNS
    assert 'planning.qgate' not in _config_defaults_mod.CEREMONY_FOOTGUNS

    # Act
    warnings = ceremony_set_footgun_warnings({'planning.qgate': 'never'})

    # Assert
    assert warnings == []


def test_hard_footgun_set_contains_only_finalize_qgate():
    """CEREMONY_HARD_FOOTGUNS must be exactly {finalize.qgate} (the red-tree risk)."""
    # Arrange / Act / Assert
    assert _config_defaults_mod.CEREMONY_HARD_FOOTGUNS == frozenset({'finalize.qgate'})


def test_every_hard_footgun_is_also_in_the_footgun_catalogue():
    """Each hard footgun must have a CEREMONY_FOOTGUNS catalogue entry (no orphans)."""
    # Arrange / Act / Assert
    for path in _config_defaults_mod.CEREMONY_HARD_FOOTGUNS:
        assert path in _config_defaults_mod.CEREMONY_FOOTGUNS


# =============================================================================
# (3) planning / automation sub-keys are independently settable
# =============================================================================


def test_validate_accepts_planning_only_mutation():
    """A policy mutating only the planning section (other sections at default) validates."""
    # Arrange — flip one planning gate; finalize + automation untouched
    policy = {
        'planning': {'deep_lane': 'never', 'revalidation': 'auto'},
        'finalize': {'self_review': 'auto'},
        'automation': {'finalize_without_asking': True},
        'overrides': [],
    }

    # Act / Assert — no exception
    validate_ceremony_policy(policy)


def test_validate_accepts_automation_only_mutation():
    """A policy mutating only the automation axis validates independently of gates."""
    # Arrange
    policy = {
        'planning': {'deep_lane': 'auto'},
        'automation': {
            'finalize_without_asking': False,
            'auto_merge_after_ci': False,
        },
        'overrides': [],
    }

    # Act / Assert — automation is boolean-only and independent of the run-at-all axis
    validate_ceremony_policy(policy)


def test_validate_rejects_unknown_planning_gate():
    """An unknown planning gate key is rejected by the validator."""
    # Arrange
    policy = {'planning': {'bogus_gate': 'auto'}}

    # Act / Assert
    with pytest.raises(ValueError, match="Unknown ceremony_policy.planning gate 'bogus_gate'"):
        validate_ceremony_policy(policy)


def test_validate_rejects_invalid_run_at_all_value():
    """A run-at-all gate value outside auto|always|never is rejected."""
    # Arrange
    policy = {'finalize': {'qgate': 'sometimes'}}

    # Act / Assert
    with pytest.raises(ValueError, match='Invalid ceremony_policy.finalize.qgate'):
        validate_ceremony_policy(policy)


def test_validate_rejects_non_bool_automation_value():
    """The automation axis is boolean-only — a string value is rejected."""
    # Arrange
    policy = {'automation': {'finalize_without_asking': 'yes'}}

    # Act / Assert
    with pytest.raises(ValueError, match='ceremony_policy.automation.finalize_without_asking must be a bool'):
        validate_ceremony_policy(policy)


def test_validate_rejects_non_list_overrides():
    """overrides must be a list."""
    # Arrange
    policy = {'overrides': {'not': 'a list'}}

    # Act / Assert
    with pytest.raises(ValueError, match='ceremony_policy.overrides must be a list'):
        validate_ceremony_policy(policy)


def test_validate_rejects_non_dict_policy():
    """A non-dict policy is rejected outright."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match='ceremony_policy must be a dict'):
        validate_ceremony_policy(['not', 'a', 'dict'])


def test_default_ceremony_policy_passes_its_own_validator():
    """The shipped DEFAULT_CEREMONY_POLICY must be self-consistent under the validator."""
    # Arrange / Act / Assert — the default seed must never trip validation
    validate_ceremony_policy(_config_defaults_mod.DEFAULT_CEREMONY_POLICY)


def test_override_matches_when_all_facts_equal():
    """An overrides[] when-clause matches when every fact equals the plan fact."""
    # Arrange
    when = {'scope_estimate': 'surgical', 'change_type': 'bugfix'}
    plan_facts = {'scope_estimate': 'surgical', 'change_type': 'bugfix', 'plan_source': 'cli'}

    # Act / Assert
    assert ceremony_override_matches(when, plan_facts) is True


def test_override_does_not_match_on_fact_mismatch():
    """An overrides[] when-clause does not match when any fact differs."""
    # Arrange
    when = {'scope_estimate': 'surgical'}
    plan_facts = {'scope_estimate': 'multi_module'}

    # Act / Assert
    assert ceremony_override_matches(when, plan_facts) is False


def test_empty_when_clause_matches_every_plan():
    """An empty when-clause is the unconditional override — it matches any plan."""
    # Arrange / Act / Assert
    assert ceremony_override_matches({}, {'scope_estimate': 'anything'}) is True


def test_override_does_not_match_missing_fact():
    """A when-clause referencing a fact absent from plan_facts does not match."""
    # Arrange
    when = {'plan_source': 'sonar'}
    plan_facts = {'scope_estimate': 'surgical'}

    # Act / Assert
    assert ceremony_override_matches(when, plan_facts) is False


# =============================================================================
# (4) Backward compatibility — migrated automation values preserve today's knobs
# =============================================================================


def test_automation_axis_preserves_today_finalize_without_asking():
    """automation.finalize_without_asking must seed True (the migrated phase-5-execute value)."""
    # Arrange
    automation = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — the migrated knob preserves the historical True default. The
    # loose DEFAULT_PLAN_EXECUTE['finalize_without_asking'] key was removed by the
    # migration, so ceremony_policy.automation is now the single source of truth.
    assert automation['finalize_without_asking'] is True
    assert 'finalize_without_asking' not in _config_defaults_mod.DEFAULT_PLAN_EXECUTE


def test_automation_axis_preserves_today_loop_back_without_asking():
    """automation.loop_back_without_asking must seed False (the migrated phase-6-finalize value)."""
    # Arrange
    automation = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — migrated knob preserves the historical False default; the loose
    # DEFAULT_PLAN_FINALIZE key was removed.
    assert automation['loop_back_without_asking'] is False
    assert 'loop_back_without_asking' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_automation_axis_preserves_today_auto_merge_after_ci():
    """automation.auto_merge_after_ci must seed True (the migrated phase-6-finalize value)."""
    # Arrange
    automation = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — migrated knob preserves the historical True default; the loose
    # DEFAULT_PLAN_FINALIZE key was removed.
    assert automation['auto_merge_after_ci'] is True
    assert 'auto_merge_after_ci' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_loose_finalize_knobs_are_fully_migrated_out_of_plan_blocks():
    """The three migrated knobs MUST NOT survive in the loose plan-phase blocks."""
    # Arrange / Act / Assert — config-doc-contract: no loose-path survivors. The
    # ceremony_policy.automation axis is the sole home for these three knobs.
    for knob in ('finalize_without_asking', 'loop_back_without_asking', 'auto_merge_after_ci'):
        assert knob not in _config_defaults_mod.DEFAULT_PLAN_EXECUTE
        assert knob not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_automation_axis_carries_exactly_the_three_migrated_knobs():
    """The automation axis consolidates exactly the three previously-scattered finalize knobs."""
    # Arrange
    automation = _config_defaults_mod.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — no extra/missing keys vs the three migrated knobs
    assert set(automation.keys()) == {
        'finalize_without_asking',
        'loop_back_without_asking',
        'auto_merge_after_ci',
    }


# =============================================================================
# (5) ceremony-policy --field accepts the dotted <section>.<field> path
# =============================================================================
#
# Regression: ``manage-config.py`` previously bound the shared ``add_field_arg``
# (``validate_field_name`` — bare snake_case, no dots) to the ceremony-policy
# get/set ``--field`` argument, which rejected every dotted path the runtime
# readers and the docs use (``automation.finalize_without_asking``,
# ``finalize.self_review``). The parser now binds the dotted-snake-case
# validator (``validate_package_name``). These tests pin the validator contract.

from input_validation import (  # type: ignore[import-not-found]  # noqa: E402
    validate_field_name,
    validate_package_name,
)

_CEREMONY_DOTTED_FIELDS = [
    'automation.finalize_without_asking',
    'automation.loop_back_without_asking',
    'automation.auto_merge_after_ci',
    'planning.deep_lane',
    'planning.revalidation',
    'planning.escalation',
    'planning.qgate',
    'finalize.self_review',
    'finalize.qgate',
    'finalize.plugin_doctor',
]


@pytest.mark.parametrize('dotted', _CEREMONY_DOTTED_FIELDS)
def test_ceremony_field_validator_accepts_every_dotted_path(dotted):
    """The validator bound to ceremony-policy ``--field`` accepts every canonical dotted path."""
    # Act — validate_package_name returns the value unchanged on success.
    assert validate_package_name(dotted) == dotted


@pytest.mark.parametrize('dotted', _CEREMONY_DOTTED_FIELDS)
def test_old_field_validator_would_reject_dotted_path(dotted):
    """The former binding (``validate_field_name``) rejected dotted paths — the bug being fixed."""
    # Act / Assert — the old bare-snake-case validator raises on any dot.
    with pytest.raises(ValueError):
        validate_field_name(dotted)
