#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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


def _load_module(name: str, filename: str, *, base_dir: Path = _SCRIPTS_DIR, extra_syspath_dirs=()):
    """Load a module from ``base_dir / filename`` via importlib by explicit path.

    Mirrors the per-file importlib loading used across the manage-config tests so
    a test does not depend on conftest PYTHONPATH discovery order. ``extra_syspath_dirs``
    are inserted into ``sys.path`` (if absent) before the module is exec'd, for
    modules whose own top-level imports resolve against a sibling directory.
    """
    for d in extra_syspath_dirs:
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(name, base_dir / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_sensible_number():
    """Load the script-shared sensible_number module by explicit path.

    The module lives under the shared ``script-shared/scripts`` surface.
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
    return _load_module(
        '_sensible_number_for_config_defaults_test', 'sensible_number.py', base_dir=shared_dir
    )


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


def _discovered_seed_step_ids() -> list:
    """Return the materialized built-in finalize-step ids, in seed order.

    The hand-maintained ``BUILT_IN_FINALIZE_STEPS`` constant was removed; the seed
    is now derived from the reusable ``extension_discovery.find_implementors``
    query — the SOLE finalize-step discovery path. This mirrors the current
    ``_seed_finalize_steps()``: materialize EVERY built-in implementor (there is
    NO ``default_on == true`` filter — exclusion is expressed as a ``lane: off``
    override, never as absence), sort by ``(order, name)``, and project to the
    step ids. The result is the expected key insertion order of the seeded
    ``plan.phase-6-finalize.steps`` keyed map.
    """
    from extension_discovery import find_implementors

    seed_records = sorted(
        (
            rec
            for rec in find_implementors(_config_defaults_mod.FINALIZE_STEP_EXT_POINT)
            if rec.get('source') == 'built-in'
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [rec['name'] for rec in seed_records if rec.get('name')]


def _discovered_default_off_built_in_step_ids() -> list:
    """Return the built-in finalize-step ids whose ``default_on`` is False.

    These are the steps the materialize-all seed carries with a ``lane: off``
    override (exclusion expressed as ``lane: off``, never absence). Mirrors the
    source-filter of :func:`_discovered_seed_step_ids` but keeps only the
    ``default_on == false`` records.
    """
    from extension_discovery import find_implementors

    return [
        rec['name']
        for rec in find_implementors(_config_defaults_mod.FINALIZE_STEP_EXT_POINT)
        if rec.get('source') == 'built-in' and not rec.get('default_on') and rec.get('name')
    ]


def _discovered_step_description(step_id: str) -> str:
    """Return the discovered ``description`` for a finalize-step id.

    Replaces the removed ``BUILT_IN_FINALIZE_STEP_DESCRIPTIONS`` map: the per-step
    description is now a frontmatter field surfaced by the discovery query.
    """
    from extension_discovery import find_implementors

    for rec in find_implementors(_config_defaults_mod.FINALIZE_STEP_EXT_POINT):
        if rec.get('name') == step_id:
            # `or ''` (not the `.get` default) so a present-but-null description
            # coerces to '' rather than the truthy literal string 'None'.
            return str(rec.get('description') or '')
    return ''


def _discovered_verify_step_ids() -> list:
    """Return the built-in verify-step ids, in seed order.

    The hand-maintained ``BUILT_IN_VERIFY_STEPS`` constant was removed; the seed is
    now derived from the reusable ``extension_discovery.find_implementors`` query —
    the SOLE verify-step discovery path. This mirrors ``_seed_verify_steps()``:
    filter the discovered implementors to the built-in source, sort by
    ``(order, name)``, and expand each implementor's ``canonicals`` list into
    ``default:verify:{canonical}`` ids in list order. The result is the expected
    key insertion order of the seeded ``plan.phase-5-execute.verification_steps``
    keyed map.
    """
    from extension_discovery import find_implementors

    built_in = sorted(
        (
            rec
            for rec in find_implementors(_config_defaults_mod.BUILD_VERIFY_STEP_EXT_POINT)
            if rec.get('source') == 'built-in'
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [
        f'default:verify:{canonical}'
        for rec in built_in
        for canonical in rec.get('canonicals', [])
    ]


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


def test_default_plan_finalize_simplify_is_config_less_after_ceremony_lane_migration():
    """`default:finalize-step-simplify` is config-less — the `simplify` run-at-all param is gone.

    The four finalize ceremony gates (qgate / self_review / simplify /
    security_audit) moved off the run-at-all channel onto the per-element
    `steps.<step>.lane` override. The simplify step no longer declares a
    `simplify` param, so its seeded nested param object is the empty `{}`
    (default_on:true, non-infra → no `lane` override seeded).
    """
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Never a flat sibling of `steps`, and never a step-owned param anymore.
    assert 'simplify' not in finalize, (
        'simplify must NOT survive as a flat phase-level field'
    )
    config = _config_defaults_mod.get_default_config()
    simplify_step = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:finalize-step-simplify'
    )
    assert simplify_step == {}, (
        'default:finalize-step-simplify must be config-less after the ceremony '
        f'run-at-all → lane migration; got {simplify_step!r}'
    )
    assert 'simplify' not in simplify_step
    assert 'lane' not in simplify_step, (
        'a default_on:true non-infra step seeds no lane override'
    )


def test_get_default_config_finalize_simplify_carries_no_run_at_all_param():
    """get_default_config() surfaces the simplify step with no `simplify` run-at-all param."""
    config = _config_defaults_mod.get_default_config()

    finalize = config['plan']['phase-6-finalize']
    assert 'simplify' not in finalize
    simplify_step = _params_for(finalize['steps'], 'default:finalize-step-simplify')
    assert 'simplify' not in simplify_step
    assert simplify_step == {}


def test_default_plan_finalize_ceremony_gates_have_no_run_at_all_params():
    """None of the four finalize ceremony gates survives as a run-at-all knob.

    After the ceremony run-at-all → lane migration: `qgate` is no longer a flat
    phase-level sibling; `simplify` / `self_review` / `security_audit` are no
    longer step-owned params. Each gate's on/off is governed by its owning step's
    `steps.<step>.lane` override. The pre-submission-self-review step KEEPS its
    `drop_review_on_scope_gate` escape hatch (not a ceremony gate).
    """
    finalize = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # qgate no longer a flat phase-level sibling.
    assert 'qgate' not in finalize, (
        'plan.phase-6-finalize.qgate must NOT survive as a flat run-at-all sibling '
        '(finalize-qgate now rides steps[pre-push-quality-gate].lane)'
    )

    config = _config_defaults_mod.get_default_config()
    seeded_steps = config['plan']['phase-6-finalize']['steps']

    # simplify / security-audit steps are config-less (their run-at-all params gone).
    assert _params_for(seeded_steps, 'default:finalize-step-simplify') == {}
    assert _params_for(seeded_steps, 'default:finalize-step-security-audit') == {}

    # self_review param is gone; drop_review_on_scope_gate (escape hatch) is kept.
    self_review_params = _params_for(seeded_steps, 'default:pre-submission-self-review')
    assert 'self_review' not in self_review_params
    assert self_review_params == {'drop_review_on_scope_gate': False}


# ---------------------------------------------------------------------------
# Materialize-all seed + lane:off / lane:ask overrides (this plan, D1)
# ---------------------------------------------------------------------------
#
# _seed_finalize_steps() now materializes EVERY built-in finalize-step implementor
# (there is NO default_on filter): exclusion is expressed as a `lane: off` override
# on each default_on:false step, never as absence from the seed. The two
# adversarial infra elements (plan-marshall:automatic-review, default:sonar-roundtrip)
# seed a `lane: ask` override so marshall-steward always prompts about them.


def test_lane_ask_infra_steps_constant_names_the_two_infra_elements():
    """_LANE_ASK_INFRA_STEPS must name exactly the two adversarial infra elements."""
    assert _config_defaults_mod._LANE_ASK_INFRA_STEPS == (
        'plan-marshall:automatic-review',
        'default:sonar-roundtrip',
    )


def test_seed_finalize_steps_materializes_every_built_in_implementor():
    """_seed_finalize_steps() materializes EVERY built-in implementor, in seed order.

    The default_on filter is gone — exclusion is a `lane: off` override, never
    absence — so the seeded step-id set equals the full discovered built-in set
    (which includes the default_on:false steps architecture-refresh and adr-propose).
    """
    seeded = _config_defaults_mod._seed_finalize_steps()

    assert isinstance(seeded, dict)
    assert _step_ids(seeded) == _discovered_seed_step_ids()
    # the default_on:false built-in steps are now materialized into the seed
    for step_id in _discovered_default_off_built_in_step_ids():
        assert step_id in seeded, (
            f'materialize-all seed must include the default_on:false step {step_id!r}'
        )


def test_seed_finalize_steps_default_off_steps_carry_lane_off():
    """Every default_on:false built-in step seeds a `lane: off` override."""
    seeded = _config_defaults_mod._seed_finalize_steps()

    off_steps = _discovered_default_off_built_in_step_ids()
    # sanity: the discovery surfaces at least one default_on:false built-in step
    # (architecture-refresh / adr-propose), else this assertion is vacuous.
    assert off_steps, 'expected at least one default_on:false built-in finalize step'
    for step_id in off_steps:
        assert seeded[step_id].get('lane') == 'off', (
            f'default_on:false step {step_id!r} must seed lane:off, got {seeded[step_id]!r}'
        )


def test_seed_finalize_steps_infra_elements_carry_lane_ask():
    """The two adversarial infra elements seed a `lane: ask` override on top of their params."""
    seeded = _config_defaults_mod._seed_finalize_steps()

    for step_id in _config_defaults_mod._LANE_ASK_INFRA_STEPS:
        assert step_id in seeded, f'infra element {step_id!r} must be materialized into the seed'
        assert seeded[step_id].get('lane') == 'ask', (
            f'infra element {step_id!r} must seed lane:ask, got {seeded[step_id]!r}'
        )
    # the infra elements retain their own step-owned params alongside lane:ask
    assert seeded['default:sonar-roundtrip']['touched_file_cleanup'] == 'new_code_only'
    assert seeded['plan-marshall:automatic-review']['review_bot_buffer_seconds'] == 180


def test_seed_finalize_steps_default_on_non_infra_steps_have_no_lane_key():
    """A default_on:true non-infra step seeds no `lane` override (absent → auto)."""
    seeded = _config_defaults_mod._seed_finalize_steps()

    for step_id in ('default:finalize-step-simplify', 'default:finalize-step-security-audit'):
        assert 'lane' not in seeded[step_id], (
            f'default_on:true non-infra step {step_id!r} must seed no lane override'
        )


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


# ---------------------------------------------------------------------------
# D4/D5 new-knob seed assertions — this deliverable (6) is the SINGLE owner of
# the seed test for the three finalize-flow-hardening knobs declared in
# default:branch-cleanup's configurable: frontmatter: merge_hold_window and
# merge_hold_budget_seconds (D4), plus use_merge_queue (D5).
# ---------------------------------------------------------------------------


def test_default_plan_finalize_includes_merge_hold_window():
    """merge_hold_window nests under default:branch-cleanup with default 'full_window_release_at_waits' (D4)."""
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'merge_hold_window' in branch_cleanup, (
        'merge_hold_window must nest under default:branch-cleanup in the seeded steps map'
    )
    assert branch_cleanup['merge_hold_window'] == 'full_window_release_at_waits', (
        "merge_hold_window default must be 'full_window_release_at_waits'"
    )
    assert 'merge_hold_window' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE, (
        'merge_hold_window must not survive as a flat phase-level knob'
    )


def test_default_plan_finalize_includes_merge_hold_budget_seconds():
    """merge_hold_budget_seconds nests under default:branch-cleanup with default 3600 (D4)."""
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'merge_hold_budget_seconds' in branch_cleanup, (
        'merge_hold_budget_seconds must nest under default:branch-cleanup in the seeded steps map'
    )
    assert branch_cleanup['merge_hold_budget_seconds'] == 3600, (
        'merge_hold_budget_seconds default must be 3600 (~60 min, the max merge-hold budget)'
    )
    assert 'merge_hold_budget_seconds' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_default_plan_finalize_includes_use_merge_queue():
    """use_merge_queue nests under default:branch-cleanup with default False (D5)."""
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert 'use_merge_queue' in branch_cleanup, (
        'use_merge_queue must nest under default:branch-cleanup in the seeded steps map'
    )
    assert branch_cleanup['use_merge_queue'] is False, (
        'use_merge_queue default must be False (opt-in platform merge-queue complement)'
    )
    assert 'use_merge_queue' not in _config_defaults_mod.DEFAULT_PLAN_FINALIZE


def test_get_default_config_includes_finalize_flow_hardening_knobs():
    """get_default_config() surfaces all three finalize-flow-hardening knobs nested together."""
    config = _config_defaults_mod.get_default_config()
    branch_cleanup = _params_for(
        config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup'
    )
    assert branch_cleanup['merge_hold_window'] == 'full_window_release_at_waits'
    assert branch_cleanup['merge_hold_budget_seconds'] == 3600
    assert branch_cleanup['use_merge_queue'] is False


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


_EXPECTED_COST_SIZE_TOKEN_TABLE = {
    'XS': '5K',
    'S': '25K',
    'M': '60K',
    'L': '130K',
    'XL': '260K',
    'XXL': '520K',
}


def test_default_plan_execute_includes_cost_size_token_table():
    """DEFAULT_PLAN_EXECUTE must declare cost_size_token_table with the six-size default.

    The four original magnitudes (S/M/L/XL) are UNCHANGED; XS and XXL widen the
    scale at both ends.
    """
    execute_defaults = _config_defaults_mod.DEFAULT_PLAN_EXECUTE

    assert 'cost_size_token_table' in execute_defaults, (
        'cost_size_token_table must be schema-registered in DEFAULT_PLAN_EXECUTE'
    )
    assert execute_defaults['cost_size_token_table'] == _EXPECTED_COST_SIZE_TOKEN_TABLE, (
        'cost_size_token_table default must map XS/S/M/L/XL/XXL to '
        '5K/25K/60K/130K/260K/520K (the S/M/L/XL magnitudes calibrated to the '
        'forensic 134K-392K per-dispatch range are unchanged)'
    )
    # Every magnitude round-trips through the shared parser to the documented int.
    parsed = {k: parse_sensible_int(v) for k, v in execute_defaults['cost_size_token_table'].items()}
    assert parsed == {'XS': 5000, 'S': 25000, 'M': 60000, 'L': 130000, 'XL': 260000, 'XXL': 520000}


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


def test_cost_size_labels_enumerates_the_six_tshirt_sizes():
    """COST_SIZE_LABELS must enumerate exactly the six T-shirt sizes XS/S/M/L/XL/XXL."""
    assert _config_defaults_mod.COST_SIZE_LABELS == ('XS', 'S', 'M', 'L', 'XL', 'XXL')
    # the seeded default table keys must match the label set exactly
    assert set(_config_defaults_mod.DEFAULT_PLAN_EXECUTE['cost_size_token_table'].keys()) == set(
        _config_defaults_mod.COST_SIZE_LABELS
    )


def test_validate_cost_size_token_table_accepts_seeded_default():
    """validate_cost_size_token_table must accept the seeded six-size default table."""
    _config_defaults_mod.validate_cost_size_token_table(
        _config_defaults_mod.DEFAULT_PLAN_EXECUTE['cost_size_token_table']
    )
    # an explicit valid six-size table with int-typed magnitudes is also accepted
    _config_defaults_mod.validate_cost_size_token_table(
        {'XS': '5K', 'S': 25000, 'M': '60K', 'L': '130_000', 'XL': '260K', 'XXL': 520000}
    )


def test_validate_cost_size_token_table_rejects_non_dict():
    """validate_cost_size_token_table must reject a non-dict value."""
    import pytest

    with pytest.raises(ValueError, match='expected a dict'):
        _config_defaults_mod.validate_cost_size_token_table(['25K', '60K'])


def test_validate_cost_size_token_table_rejects_missing_key():
    """validate_cost_size_token_table must reject a table missing one of XS/S/M/L/XL/XXL.

    The four-size table (no XS, no XXL) is now incomplete under the six-size scale.
    """
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K'}
        )


def test_validate_cost_size_token_table_rejects_missing_new_xs_key():
    """validate_cost_size_token_table must reject a six-size table missing the new XS key."""
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K', 'XXL': '520K'}
        )


def test_validate_cost_size_token_table_rejects_extra_key():
    """validate_cost_size_token_table must reject a table carrying an unexpected size key.

    XXL is now a VALID key, so the extra-key case uses a genuinely out-of-enum
    label (XXXL) on top of the complete six-size set.
    """
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'XS': '5K', 'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K', 'XXL': '520K', 'XXXL': '999K'}
        )


def test_validate_cost_size_token_table_rejects_unparseable_magnitude():
    """validate_cost_size_token_table must reject a value that is not a sensible int."""
    import pytest

    with pytest.raises(ValueError, match='not a parseable token magnitude'):
        _config_defaults_mod.validate_cost_size_token_table(
            {'XS': '5K', 'S': '25K', 'M': 'sixty-thousand', 'L': '130K', 'XL': '260K', 'XXL': '520K'}
        )


def _load_tasks_cost():
    """Load the manage-tasks ``_tasks_cost.py`` consumer module by explicit path.

    ``_tasks_cost.py`` imports ``from sensible_number import parse_sensible_int``
    at module top, so the shared ``script-shared/scripts`` surface must be on
    ``sys.path`` before the module is exec'd.
    """
    root = Path(__file__).parent.parent.parent.parent / 'marketplace' / 'bundles' / 'plan-marshall'
    shared_dir = root / 'skills' / 'script-shared' / 'scripts'
    tasks_scripts_dir = root / 'skills' / 'manage-tasks' / 'scripts'
    return _load_module(
        '_tasks_cost_for_drift_test',
        '_tasks_cost.py',
        base_dir=tasks_scripts_dir,
        extra_syspath_dirs=(shared_dir, tasks_scripts_dir),
    )


def test_cost_size_token_table_seed_matches_consumer_default():
    """The config seed cost table must equal the _tasks_cost consumer default (drift guard).

    ``_config_defaults.DEFAULT_PLAN_EXECUTE['cost_size_token_table']`` (the
    operator-tunable config seed) and ``_tasks_cost.DEFAULT_SIZE_TABLE`` (the pure
    deriver's canonical default, used when the caller passes no ``size_table``)
    are two mirrors of the SAME six-size scale. If they diverge — a key added or
    removed on one side, or a magnitude changed — phase-4-plan cost derivation
    would silently use one table while the config advertises another. This
    cross-module drift test fails loud on any such divergence. Both sides are
    parsed through the shared ``parse_sensible_int`` so the comparison is on
    integer magnitudes, not string spelling (e.g. ``'130K'`` vs ``'130_000'``).
    """
    tasks_cost = _load_tasks_cost()
    seed = _config_defaults_mod.DEFAULT_PLAN_EXECUTE['cost_size_token_table']
    consumer = tasks_cost.DEFAULT_SIZE_TABLE

    # Identical six-key set, and it equals the canonical COST_SIZE_LABELS enum.
    expected_keys = set(_config_defaults_mod.COST_SIZE_LABELS)
    assert set(seed) == expected_keys, 'config seed keys must be the six-size set'
    assert set(consumer) == expected_keys, 'consumer default keys must be the six-size set'

    # Identical parsed magnitudes per key.
    seed_parsed = {k: parse_sensible_int(v) for k, v in seed.items()}
    consumer_parsed = {k: parse_sensible_int(v) for k, v in consumer.items()}
    assert seed_parsed == consumer_parsed, (
        'config seed and _tasks_cost consumer default must carry identical parsed '
        f'magnitudes; seed={seed_parsed} consumer={consumer_parsed}'
    )


# =============================================================================
# Execution-profile lane config knobs (this plan, D3)
# =============================================================================
#
# Three operator-facing knobs added to the lane mechanism:
#   - lane_selection (ask|auto) under DEFAULT_PLAN_INIT
#   - the per-element lane override validator (off|minimal|auto|full|ask)
#   - lane_prune_thresholds (confidence_complete, linear_change_max_deliverables)
#     under DEFAULT_PLAN_INIT
# The per-element vocabulary itself (lane.class enum, prune-predicate names) lives
# in ext-point-lane-element.md, not in config; these tests cover only the config
# defaults + validators.

_EXPECTED_LANE_PRUNE_THRESHOLDS = {
    'confidence_complete': 95,
    'linear_change_max_deliverables': 1,
}


def test_default_plan_init_includes_lane_selection_ask():
    """DEFAULT_PLAN_INIT must declare lane_selection with default 'ask'."""
    init_defaults = _config_defaults_mod.DEFAULT_PLAN_INIT

    assert 'lane_selection' in init_defaults, (
        'lane_selection must be schema-registered in DEFAULT_PLAN_INIT'
    )
    assert init_defaults['lane_selection'] == 'ask', (
        "lane_selection default must be 'ask' (surface the posture dialogue at init)"
    )


def test_get_default_config_includes_lane_selection():
    """get_default_config() must surface plan.phase-1-init.lane_selection == 'ask'."""
    config = _config_defaults_mod.get_default_config()

    assert config['plan']['phase-1-init'].get('lane_selection') == 'ask'


def test_valid_lane_selection_enumerates_ask_and_auto():
    """VALID_LANE_SELECTION must enumerate exactly ('ask', 'auto')."""
    assert _config_defaults_mod.VALID_LANE_SELECTION == ('ask', 'auto')
    # the seeded default must be a member of the enum
    assert (
        _config_defaults_mod.DEFAULT_PLAN_INIT['lane_selection']
        in _config_defaults_mod.VALID_LANE_SELECTION
    )


def test_validate_lane_selection_accepts_allowed_values():
    """validate_lane_selection must accept every value in VALID_LANE_SELECTION."""
    for value in _config_defaults_mod.VALID_LANE_SELECTION:
        _config_defaults_mod.validate_lane_selection(value)


def test_validate_lane_selection_rejects_unknown_value():
    """validate_lane_selection must raise ValueError for a value outside the enum."""
    import pytest

    with pytest.raises(ValueError, match='Invalid lane_selection'):
        _config_defaults_mod.validate_lane_selection('always')


def test_valid_lane_override_enumerates_five_values():
    """VALID_LANE_OVERRIDE must enumerate exactly off|minimal|auto|full|ask."""
    assert _config_defaults_mod.VALID_LANE_OVERRIDE == (
        'off', 'minimal', 'auto', 'full', 'ask'
    )


def test_validate_lane_override_accepts_allowed_values():
    """validate_lane_override must accept every value in VALID_LANE_OVERRIDE."""
    for value in _config_defaults_mod.VALID_LANE_OVERRIDE:
        _config_defaults_mod.validate_lane_override(value)


def test_validate_lane_override_rejects_unknown_value_naming_the_field():
    """validate_lane_override must raise ValueError naming the offending field path."""
    import pytest

    with pytest.raises(ValueError, match=r'plan\.phase-6-finalize\.steps\.sonar-roundtrip\.lane'):
        _config_defaults_mod.validate_lane_override(
            'sometimes', 'plan.phase-6-finalize.steps.sonar-roundtrip.lane'
        )


def test_validate_lane_override_default_field_name():
    """validate_lane_override default field_name is 'lane' (used in the error message)."""
    import pytest

    with pytest.raises(ValueError, match=r"Invalid lane 'nope'"):
        _config_defaults_mod.validate_lane_override('nope')


def test_default_lane_prune_thresholds_carries_expected_defaults():
    """DEFAULT_LANE_PRUNE_THRESHOLDS must map the two numeric predicate thresholds."""
    assert (
        _config_defaults_mod.DEFAULT_LANE_PRUNE_THRESHOLDS
        == _EXPECTED_LANE_PRUNE_THRESHOLDS
    )


def test_default_plan_init_includes_lane_prune_thresholds():
    """DEFAULT_PLAN_INIT must declare lane_prune_thresholds with the expected defaults."""
    init_defaults = _config_defaults_mod.DEFAULT_PLAN_INIT

    assert 'lane_prune_thresholds' in init_defaults, (
        'lane_prune_thresholds must be schema-registered in DEFAULT_PLAN_INIT'
    )
    assert init_defaults['lane_prune_thresholds'] == _EXPECTED_LANE_PRUNE_THRESHOLDS


def test_get_default_config_includes_lane_prune_thresholds():
    """get_default_config() must surface plan.phase-1-init.lane_prune_thresholds."""
    config = _config_defaults_mod.get_default_config()

    assert (
        config['plan']['phase-1-init'].get('lane_prune_thresholds')
        == _EXPECTED_LANE_PRUNE_THRESHOLDS
    )


def test_validate_lane_prune_thresholds_accepts_seeded_default():
    """validate_lane_prune_thresholds must accept the seeded default mapping."""
    _config_defaults_mod.validate_lane_prune_thresholds(
        _config_defaults_mod.DEFAULT_LANE_PRUNE_THRESHOLDS
    )
    # boundary in-range values are also accepted
    _config_defaults_mod.validate_lane_prune_thresholds(
        {'confidence_complete': 0, 'linear_change_max_deliverables': 1}
    )
    _config_defaults_mod.validate_lane_prune_thresholds(
        {'confidence_complete': 100, 'linear_change_max_deliverables': 5}
    )


def test_validate_lane_prune_thresholds_rejects_non_dict():
    """validate_lane_prune_thresholds must reject a non-dict value."""
    import pytest

    with pytest.raises(ValueError, match='expected a dict'):
        _config_defaults_mod.validate_lane_prune_thresholds([95, 1])


def test_validate_lane_prune_thresholds_rejects_missing_key():
    """validate_lane_prune_thresholds must reject a mapping missing a required key."""
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_lane_prune_thresholds({'confidence_complete': 95})


def test_validate_lane_prune_thresholds_rejects_extra_key():
    """validate_lane_prune_thresholds must reject a mapping carrying an unexpected key."""
    import pytest

    with pytest.raises(ValueError, match='expected exactly'):
        _config_defaults_mod.validate_lane_prune_thresholds(
            {
                'confidence_complete': 95,
                'linear_change_max_deliverables': 1,
                'bogus': 7,
            }
        )


def test_validate_lane_prune_thresholds_rejects_out_of_range_confidence():
    """validate_lane_prune_thresholds must reject confidence_complete outside [0, 100]."""
    import pytest

    with pytest.raises(ValueError, match='confidence_complete'):
        _config_defaults_mod.validate_lane_prune_thresholds(
            {'confidence_complete': 101, 'linear_change_max_deliverables': 1}
        )


def test_validate_lane_prune_thresholds_rejects_bool_confidence():
    """validate_lane_prune_thresholds must reject a bool confidence (bool is an int subclass)."""
    import pytest

    with pytest.raises(ValueError, match='confidence_complete'):
        _config_defaults_mod.validate_lane_prune_thresholds(
            {'confidence_complete': True, 'linear_change_max_deliverables': 1}
        )


def test_validate_lane_prune_thresholds_rejects_non_positive_deliverables():
    """validate_lane_prune_thresholds must reject linear_change_max_deliverables < 1."""
    import pytest

    with pytest.raises(ValueError, match='linear_change_max_deliverables'):
        _config_defaults_mod.validate_lane_prune_thresholds(
            {'confidence_complete': 95, 'linear_change_max_deliverables': 0}
        )


def test_plan_phase_1_init_get_lane_selection_returns_ask_default(plan_context):
    """`plan phase-1-init get --field lane_selection` returns 'ask' from the merged default.

    Exercises the actual cmd_phase get path against a fresh marshal.json, proving
    the lane_selection default surfaces even when the persisted config omits the key.
    """
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    args = Namespace(verb='get', field='lane_selection')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-1-init')

    assert result['status'] == 'success'
    assert result['value'] == 'ask'


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
    """default:finalize-step-simplify sits BEFORE default:push in the discovered seed.

    simplify is a mutates_source step (order 8) and push is the pure barrier
    (order 10), so simplify precedes push. The canonical head order is
    default:finalize-step-sync-baseline (index 0, order 3 — the early baseline
    rebase that runs before the local quality gates),
    default:pre-push-quality-gate (index 1, order 5),
    default:pre-submission-self-review (index 2, order 7 — the default-on
    built-in structural self-review that runs between the pre-push quality gate
    and the simplify pass), default:finalize-step-simplify (index 3, order 8),
    then the two order-9 settle steps in ``(order, name)`` tie-break order:
    default:architecture-refresh (index 4, order 9 — the D3 move from the
    post-push region into the pre-push settle band) sorts ahead of
    default:finalize-step-security-audit (index 5, order 9) because
    ``architecture-refresh`` < ``finalize-step-security-audit`` by name; then
    default:push (index 6, order 10) — matching the plain `order:` values (no
    special placement invariant). The seed is discovered via find_implementors,
    not a constant.
    """
    steps = _discovered_seed_step_ids()

    # presence and relative head order (self-review order 7 nests between the
    # pre-push quality gate (5) and simplify (8); the two order-9 settle steps
    # architecture-refresh and security-audit sit between simplify (8) and
    # push (10), name-ordered within the order-9 tie)
    assert 'default:finalize-step-simplify' in steps, (
        'default:finalize-step-simplify must be discovered into the default-on seed'
    )
    assert steps[0] == 'default:finalize-step-sync-baseline'
    assert steps[1] == 'default:pre-push-quality-gate'
    assert steps[2] == 'default:pre-submission-self-review'
    assert steps[3] == 'default:finalize-step-simplify'
    assert steps[4] == 'default:architecture-refresh'
    assert steps[5] == 'default:finalize-step-security-audit'
    assert steps[6] == 'default:push'
    # The D3 settle-before-push invariant: architecture-refresh (order 9) sits
    # in the pre-push settle band, ahead of the push barrier.
    assert steps.index('default:architecture-refresh') < steps.index('default:push')


def test_built_in_finalize_step_descriptions_includes_finalize_step_simplify():
    """default:finalize-step-simplify must carry a non-empty discovered description.

    The per-step description is now a frontmatter field surfaced by the discovery
    query (the BUILT_IN_FINALIZE_STEP_DESCRIPTIONS map was removed), so
    list-finalize-steps can still surface a human-readable description.
    """
    description = _discovered_step_description('default:finalize-step-simplify')

    assert description, (
        'default:finalize-step-simplify discovered description must be non-empty'
    )


def test_built_in_finalize_steps_orders_simplify_then_push():
    """Canonical order: simplify before push.

    simplify is a mutates_source step (order 8) and push is the pure barrier
    (order 10), so the canonical chain is simplify < push.
    """
    steps = _discovered_seed_step_ids()

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
    # key insertion order preserves the discovered default-on seed execution order
    assert _step_ids(steps) == _discovered_seed_step_ids()


def test_default_plan_finalize_steps_nests_step_owned_params():
    """Step-owned params nest in their owning step's value; config-less steps map to {}."""
    config = _config_defaults_mod.get_default_config()
    steps = config['plan']['phase-6-finalize']['steps']

    # sonar params nest under default:sonar-roundtrip, prefix-stripped; the
    # adversarial infra element additionally seeds a lane:ask override.
    sonar = _params_for(steps, 'default:sonar-roundtrip')
    assert sonar == {
        'touched_file_cleanup': 'new_code_only',
        'do_transition': False,
        'ce_wait_timeout_seconds': 600,
        'lane': 'ask',
    }
    # no sonar_-prefixed key survives inside the scoped object
    assert not any(k.startswith('sonar_') for k in sonar)

    # enabled-bots list + review buffer + completion-poll bound + re-review gates
    # + re-review timeout + rate-window await knobs nest under
    # plan-marshall:automatic-review; the adversarial infra element additionally
    # seeds a lane:ask override.
    assert _params_for(steps, 'plan-marshall:automatic-review') == {
        'enabled_bots': 'coderabbit,sourcery,gemini',
        'review_bot_buffer_seconds': 180,
        'review_completion_poll_timeout_seconds': 600,
        're_review_on_loopback': False,
        're_review_on_branch_cleanup': True,
        're_review_await_timeout_seconds': 600,
        're_review_on_timeout': 'ask',
        'review_rate_window_await': False,
        'review_rate_window_timeout_seconds': 3600,
        'lane': 'ask',
    }

    # branch-cleanup params nest under default:branch-cleanup
    assert _params_for(steps, 'default:branch-cleanup') == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
        'merge_queue_wait_budget_seconds': 1800,
        'merge_hold_window': 'full_window_release_at_waits',
        'merge_hold_budget_seconds': 3600,
        'use_merge_queue': False,
        'admin_merge_on_stuck_state': False,
        'pre_merge_comment_barrier': 'fail_into_loopback',
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
        # default:sonar-roundtrip owns the sonar params AND seeds a lane:ask override.
        'default:sonar-roundtrip',
        # plan-marshall:automatic-review owns the bot params AND seeds a lane:ask override.
        'plan-marshall:automatic-review',
        'default:branch-cleanup',
        # default:finalize-step-sync-baseline owns the `auto_rebase_threshold`
        # conflict-gate knob (default no_overlap_only), shared with branch-cleanup
        'default:finalize-step-sync-baseline',
        # default:pre-submission-self-review (the promoted default-on built-in,
        # order 7) owns the `drop_review_on_scope_gate` scope-gate toggle (the
        # ceremony `self_review` run-at-all param was removed in the lane migration)
        'default:pre-submission-self-review',
        # default:finalize-step-preference-emitter owns the per-plan
        # `preference_min_recurrence` promotion threshold knob
        'default:finalize-step-preference-emitter',
    }
    # default_on:false built-in steps carry a `lane: off` override (materialize-all:
    # exclusion is `lane: off`, never absence) — non-empty but not param-owning.
    # default:finalize-step-simplify and default:finalize-step-security-audit are
    # now config-less (their ceremony run-at-all params were removed).
    lane_off_steps = set(_discovered_default_off_built_in_step_ids())
    for step_id, params in steps.items():
        assert isinstance(params, dict), f'every step value must be a dict; got {params!r}'
        if step_id in lane_off_steps:
            assert params.get('lane') == 'off', (
                f'default_on:false built-in step {step_id!r} must carry a lane:off '
                f'override; got {params!r}'
            )
        elif step_id in param_owning:
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
        'merge_hold_window',
        'merge_hold_budget_seconds',
        'use_merge_queue',
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
    # qgate is no longer a flat run-at-all sibling — finalize-qgate now rides
    # steps[pre-push-quality-gate].lane (the ceremony run-at-all → lane migration).
    assert 'qgate' not in finalize


def test_default_plan_execute_verification_steps_is_lazy_placeholder():
    """DEFAULT_PLAN_EXECUTE['verification_steps'] must be the lazy `None` placeholder.

    The verify-step seed is materialized lazily by ``_seed_verify_steps()`` inside
    ``get_default_config()`` (the discovery query cannot run at module import
    without a hard cross-bundle dependency on the extension-api parser), so the
    module-level constant carries the ``None`` placeholder — mirroring the
    ``DEFAULT_PLAN_FINALIZE['steps']`` lazy-seed shape.
    """
    assert _config_defaults_mod.DEFAULT_PLAN_EXECUTE['verification_steps'] is None


def test_seed_verify_steps_returns_discovered_keyed_map():
    """``_seed_verify_steps()`` must return the discovered built-in steps as a keyed map."""
    seeded = _config_defaults_mod._seed_verify_steps()

    assert isinstance(seeded, dict)
    # key insertion order preserves the discovered (order, canonicals-list) order
    assert _step_ids(seeded) == _discovered_verify_step_ids()
    # verification steps own no params — every value is an empty {} param object.
    assert all(params == {} for params in seeded.values())


def test_verify_step_ext_point_constant_is_the_discovery_key():
    """BUILD_VERIFY_STEP_EXT_POINT must be the canonical ext-point notation, not a constant list."""
    assert (
        _config_defaults_mod.BUILD_VERIFY_STEP_EXT_POINT
        == 'plan-marshall:extension-api/standards/ext-point-build-verify-step'
    )
    # The hand-maintained constants were removed outright — no parallel registry.
    assert not hasattr(_config_defaults_mod, 'BUILT_IN_VERIFY_STEPS'), (
        'BUILT_IN_VERIFY_STEPS must be removed — discovery is the sole source'
    )
    assert not hasattr(_config_defaults_mod, 'BUILT_IN_VERIFY_STEP_DESCRIPTIONS'), (
        'BUILT_IN_VERIFY_STEP_DESCRIPTIONS must be removed — per-step description '
        'is now a frontmatter field surfaced by the discovery query'
    )


def test_get_default_config_finalize_steps_keyed_map_form_shape():
    """get_default_config() must surface the keyed-map finalize steps with nested params."""
    config = _config_defaults_mod.get_default_config()

    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    assert _step_ids(steps) == _discovered_seed_step_ids()
    assert _params_for(steps, 'default:sonar-roundtrip')['touched_file_cleanup'] == 'new_code_only'
    assert _params_for(steps, 'default:branch-cleanup')['pr_merge_strategy'] == 'squash'


def test_get_default_config_verification_steps_keyed_map_form_shape():
    """get_default_config() must surface the keyed-map verification steps with config-less values."""
    config = _config_defaults_mod.get_default_config()

    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert isinstance(verification_steps, dict)
    # the materialized seed matches the discovered built-in step ids, in seed order
    assert _step_ids(verification_steps) == _discovered_verify_step_ids()
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
# top-level keys alphabetically: extension_defaults, plan, build,
# credentials_config, project, providers, skill_domains, system.
# ``credentials_config`` (the non-secret per-provider config block written by
# manage-providers) takes its alphabetical slot between ``build`` and
# ``project``. These tests pin that contract and prove the committed
# marshal.json already round-trips through save_config with its key order
# unchanged.

_EXPECTED_CANONICAL_KEY_ORDER = [
    'extension_defaults',
    'plan',
    'build',
    'credentials_config',
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
        'credentials_config': {},
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


def test_default_config_seeds_no_require_wrapper():
    """get_default_config() must NOT seed any build.{tool}.require_wrapper key.

    The require_wrapper knob was removed entirely (wrapper presence is now
    auto-detected per build system), so a freshly-seeded build block carries no
    per-build-system block and no require_wrapper key anywhere — while the peer
    build.queue block is untouched (additive removal only, no regression of that
    peer block).
    """
    config = _config_defaults_mod.get_default_config()
    build = config.get('build', {})

    # No per-build-system block is seeded, so no require_wrapper key exists.
    for tool in ('maven', 'gradle', 'pyproject', 'npm'):
        assert tool not in build, (
            f'build.{tool} block must not be seeded — the require_wrapper knob was removed'
        )
    # Defensive: no nested block anywhere carries a require_wrapper key.
    for key, sub in build.items():
        if isinstance(sub, dict):
            assert 'require_wrapper' not in sub, (
                f'build.{key} must not carry a require_wrapper key'
            )
    # The peer build.queue block is still present (additive removal only).
    assert 'queue' in build


def test_config_defaults_module_drops_require_wrapper_seed_constant():
    """The DEFAULT_BUILD_REQUIRE_WRAPPER seed constant must be removed outright.

    The per-build-system wrapper-policy seed was deleted along with the knob; a
    surviving module-level constant would re-introduce the removed configuration
    surface, so the constant must no longer exist.
    """
    assert not hasattr(_config_defaults_mod, 'DEFAULT_BUILD_REQUIRE_WRAPPER'), (
        'DEFAULT_BUILD_REQUIRE_WRAPPER must be removed — the require_wrapper knob '
        'was retired in favour of auto-detection'
    )


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


def test_default_plan_init_includes_auto_route_recipe():
    """DEFAULT_PLAN_INIT must declare auto_route_recipe with default True.

    The Tier 1 recipe-match auto-route gate mirrors the sibling
    init_without_asking boolean-knob pattern: true ⇒ a high-confidence recipe
    match auto-routes without prompting.
    """
    init_defaults = _config_defaults_mod.DEFAULT_PLAN_INIT

    assert 'auto_route_recipe' in init_defaults, (
        'auto_route_recipe must be schema-registered in DEFAULT_PLAN_INIT'
    )
    assert init_defaults['auto_route_recipe'] is True, (
        'auto_route_recipe default must be True (auto-route high-confidence matches)'
    )


def test_default_plan_init_includes_auto_route_recipe_threshold_0_6():
    """DEFAULT_PLAN_INIT must declare auto_route_recipe_threshold with default 0.6.

    Free-form requests carry no plan domain/scope, so keyword-overlap-only
    confidence caps at 0.6 — the threshold the recipe-match verb's `--threshold`
    default and the aspect classifier share. The default is 0.6, NOT 0.7.
    """
    init_defaults = _config_defaults_mod.DEFAULT_PLAN_INIT

    assert 'auto_route_recipe_threshold' in init_defaults, (
        'auto_route_recipe_threshold must be schema-registered in DEFAULT_PLAN_INIT'
    )
    assert init_defaults['auto_route_recipe_threshold'] == 0.6, (
        'auto_route_recipe_threshold default must be 0.6 — keyword-only confidence '
        'for a domain/scope-less free-form request caps at 0.6'
    )


def test_get_default_config_phase_1_init_includes_auto_route_recipe_knobs():
    """get_default_config() must surface both recipe-match knobs under plan.phase-1-init."""
    config = _config_defaults_mod.get_default_config()

    init_block = config['plan']['phase-1-init']
    assert init_block.get('auto_route_recipe') is True
    assert init_block.get('auto_route_recipe_threshold') == 0.6


def test_plan_phase_1_init_get_auto_route_recipe_returns_true_default(plan_context):
    """`plan phase-1-init get --field auto_route_recipe` returns True from the merged default.

    Exercises the actual cmd_phase get path against a fresh marshal.json, proving
    the default surfaces even when the persisted config omits the key.
    """
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    args = Namespace(verb='get', field='auto_route_recipe')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-1-init')

    assert result['status'] == 'success'
    assert result['value'] is True


def test_plan_phase_1_init_get_auto_route_recipe_threshold_returns_0_6_default(plan_context):
    """`plan phase-1-init get --field auto_route_recipe_threshold` returns 0.6 from the merged default."""
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    args = Namespace(verb='get', field='auto_route_recipe_threshold')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-1-init')

    assert result['status'] == 'success'
    assert result['value'] == 0.6


# =============================================================================
# Planning-time q_gate_validation knob (this plan, D2)
# =============================================================================
#
# The planning-time `qgate` run-at-all gate on the outline step was retired
# (clean break) and replaced by the distinct `q_gate_validation` knob
# (off|once|until_clean) on BOTH the phase-3-outline and phase-4-plan blocks.
# The finalize-time `qgate` run-at-all gate is a different gate and stays
# untouched (covered by the finalize-gate tests above). These tests pin the new
# knob's defaults, the validator, and the seed on both planning phases.


def test_default_plan_outline_includes_q_gate_validation_once():
    """DEFAULT_PLAN_OUTLINE must declare q_gate_validation == 'once'."""
    outline_defaults = _config_defaults_mod.DEFAULT_PLAN_OUTLINE

    assert 'q_gate_validation' in outline_defaults, (
        'q_gate_validation must be schema-registered in DEFAULT_PLAN_OUTLINE'
    )
    assert outline_defaults['q_gate_validation'] == 'once', (
        "DEFAULT_PLAN_OUTLINE.q_gate_validation default must be 'once'"
    )


def test_default_plan_outline_drops_retired_qgate_gate():
    """The retired planning-time `qgate` run-at-all key must be gone from DEFAULT_PLAN_OUTLINE.

    The clean-break replacement removed the outline `qgate` gate entirely — a
    surviving seed would re-introduce the retired run-at-all gate alongside the
    new q_gate_validation knob.
    """
    assert 'qgate' not in _config_defaults_mod.DEFAULT_PLAN_OUTLINE, (
        'the retired outline qgate run-at-all gate must not survive'
    )


def test_default_plan_plan_includes_q_gate_validation_once():
    """DEFAULT_PLAN_PLAN must seed q_gate_validation == 'once'."""
    plan_defaults = _config_defaults_mod.DEFAULT_PLAN_PLAN

    assert 'q_gate_validation' in plan_defaults, (
        'q_gate_validation must be schema-registered in DEFAULT_PLAN_PLAN'
    )
    assert plan_defaults['q_gate_validation'] == 'once', (
        "DEFAULT_PLAN_PLAN.q_gate_validation default must be 'once'"
    )


def test_get_default_config_includes_q_gate_validation_on_both_planning_phases():
    """get_default_config() must surface q_gate_validation on phase-3-outline and phase-4-plan."""
    config = _config_defaults_mod.get_default_config()

    assert config['plan']['phase-3-outline'].get('q_gate_validation') == 'once'
    assert config['plan']['phase-4-plan'].get('q_gate_validation') == 'once'
    # the retired outline qgate gate must not surface either
    assert 'qgate' not in config['plan']['phase-3-outline']


def test_valid_q_gate_validation_enumerates_expected_values():
    """VALID_Q_GATE_VALIDATION must enumerate exactly off|once|until_clean."""
    values = _config_defaults_mod.VALID_Q_GATE_VALIDATION

    assert values == ('off', 'once', 'until_clean')
    # the seeded default must be a member of the enum
    assert _config_defaults_mod.DEFAULT_PLAN_OUTLINE['q_gate_validation'] in values
    assert _config_defaults_mod.DEFAULT_PLAN_PLAN['q_gate_validation'] in values


def test_validate_q_gate_validation_accepts_allowed_values():
    """validate_q_gate_validation must accept every off|once|until_clean value."""
    # no exception for any allowed value
    for value in _config_defaults_mod.VALID_Q_GATE_VALIDATION:
        _config_defaults_mod.validate_q_gate_validation(
            value, 'plan.phase-3-outline.q_gate_validation'
        )


def test_validate_q_gate_validation_rejects_invalid_value():
    """validate_q_gate_validation must raise ValueError naming the offending field path."""
    import pytest

    with pytest.raises(ValueError, match=r'plan\.phase-4-plan\.q_gate_validation'):
        _config_defaults_mod.validate_q_gate_validation(
            'sometimes', 'plan.phase-4-plan.q_gate_validation'
        )


def test_plan_phase_3_outline_get_q_gate_validation_returns_once_default(plan_context):
    """`plan phase-3-outline get --field q_gate_validation` returns 'once' from the merged default.

    Exercises the actual cmd_phase get path against a fresh marshal.json, proving
    the default surfaces even when the persisted config omits the key.
    """
    # fresh marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))

    args = Namespace(verb='get', field='q_gate_validation')
    result = _cmd_quality_phases_mod.cmd_phase(args, 'phase-3-outline')

    assert result['status'] == 'success'
    assert result['value'] == 'once'


# =============================================================================
# Config-seed provisioning fingerprint + stamps (this plan, D2)
# =============================================================================
#
# compute_config_seed_fingerprint() hashes the canonical JSON of
# get_default_config() — the SAME hash the target generator stamps as
# config_seed_fingerprint in dist-manifest.json. The runtime-only
# system.provisioned_version / system.config_seed_fingerprint stamps are NOT part
# of get_default_config(), so the fingerprint is stable under its own stamping.


def test_config_seed_fingerprint_stable_across_calls():
    """compute_config_seed_fingerprint() is deterministic across repeated calls."""
    fp1 = _config_defaults_mod.compute_config_seed_fingerprint()
    fp2 = _config_defaults_mod.compute_config_seed_fingerprint()

    assert fp1 == fp2, 'the config-seed fingerprint must be deterministic'
    assert len(fp1) == 8, f'fingerprint reuses the 8-char checksum width, got {len(fp1)}'


def test_provisioning_stamps_absent_from_default_config():
    """The runtime provisioning stamps must NOT be part of get_default_config().

    Keeping them out of the seed is what makes the fingerprint stable under its
    own stamping — the seed the fingerprint hashes never contains the stamp.
    """
    system = _config_defaults_mod.get_default_config().get('system', {})

    assert 'provisioned_version' not in system, 'provisioned_version must be runtime-only, not seeded'
    assert 'config_seed_fingerprint' not in system, 'config_seed_fingerprint must be runtime-only, not seeded'


def test_config_seed_fingerprint_independent_of_stamped_fields():
    """Stamping the runtime provisioning fields must not change the seed fingerprint."""
    fp_before = _config_defaults_mod.compute_config_seed_fingerprint()

    config = _config_defaults_mod.get_default_config()
    _config_defaults_mod.stamp_provisioning_fields(config)
    # the stamps are present on the config now ...
    assert config['system']['config_seed_fingerprint']
    # ... but the seed fingerprint (a hash of get_default_config(), which excludes
    # the stamps) is unchanged — the config never "drifts" from being fingerprinted.
    fp_after = _config_defaults_mod.compute_config_seed_fingerprint()

    assert fp_before == fp_after, 'stamping must not perturb the seed fingerprint'


def test_stamp_provisioning_fields_writes_both_fields():
    """stamp_provisioning_fields writes provisioned_version + config_seed_fingerprint."""
    config = _config_defaults_mod.get_default_config()

    _config_defaults_mod.stamp_provisioning_fields(config)

    system = config['system']
    assert 'provisioned_version' in system
    assert system['config_seed_fingerprint'] == _config_defaults_mod.compute_config_seed_fingerprint()


def test_stamp_provisioning_fields_creates_system_block_when_absent():
    """stamp_provisioning_fields creates the system block when the config lacks one."""
    config: dict = {}

    _config_defaults_mod.stamp_provisioning_fields(config)

    assert 'provisioned_version' in config['system']
    assert 'config_seed_fingerprint' in config['system']


def test_stamp_provisioning_fields_recovers_from_non_dict_system(tmp_path):
    """A malformed marshal.json where 'system' is not a dict (e.g. None or a
    string) must not raise — the non-dict value is replaced, not mutated."""
    config: dict = {'system': None}

    _config_defaults_mod.stamp_provisioning_fields(config)

    assert isinstance(config['system'], dict)
    assert 'provisioned_version' in config['system']
    assert 'config_seed_fingerprint' in config['system']


def test_stamp_provisioning_fields_preserves_existing_version_on_empty_read(monkeypatch):
    """An unstamped/absent executor (read_provisioned_version() -> '') must NOT
    blank a known-good pre-existing provisioned_version — the stamp is
    non-destructive on an empty read (defense-in-depth against the executor
    version-stamp regression)."""
    monkeypatch.setattr(_config_defaults_mod, 'read_provisioned_version', lambda: '')
    config: dict = {'system': {'provisioned_version': '0.1.1116'}}

    _config_defaults_mod.stamp_provisioning_fields(config)

    assert config['system']['provisioned_version'] == '0.1.1116', (
        'an empty read must preserve the existing provisioned_version, not blank it to the sentinel'
    )
    # config_seed_fingerprint is stamped unconditionally, even on an empty read.
    assert config['system']['config_seed_fingerprint'] == _config_defaults_mod.compute_config_seed_fingerprint()


def test_stamp_provisioning_fields_advances_version_on_real_read(monkeypatch):
    """A real (non-empty) embedded version advances provisioned_version to it,
    overwriting any prior stamp."""
    monkeypatch.setattr(_config_defaults_mod, 'read_provisioned_version', lambda: '0.1.1200')
    config: dict = {'system': {'provisioned_version': '0.1.1116'}}

    _config_defaults_mod.stamp_provisioning_fields(config)

    assert config['system']['provisioned_version'] == '0.1.1200', (
        'a real embedded version must advance the provisioned_version stamp'
    )


def test_read_provisioned_version_reads_executor_constant(tmp_path, monkeypatch):
    """read_provisioned_version reads MARSHALL_VERSION from the tracked executor."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'execute-script.py').write_text("MARSHALL_VERSION = '0.1.55'\n", encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    assert _config_defaults_mod.read_provisioned_version() == '0.1.55'


def test_read_provisioned_version_empty_when_executor_absent(tmp_path, monkeypatch):
    """read_provisioned_version returns the '' fresh-install sentinel when no executor exists."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    assert _config_defaults_mod.read_provisioned_version() == ''


def test_read_provisioned_version_empty_on_undecodable_executor(tmp_path, monkeypatch):
    """A ValueError/UnicodeDecodeError decoding the executor is treated like an
    absent executor — the '' sentinel, never an unhandled exception."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    # Invalid UTF-8 byte sequence raises UnicodeDecodeError (a ValueError subclass).
    (plan_dir / 'execute-script.py').write_bytes(b'\xff\xfe not valid utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    assert _config_defaults_mod.read_provisioned_version() == ''


# =============================================================================
# finding_raw_input_max_bytes knob (findings quarantine cap)
# =============================================================================


def test_default_finding_raw_input_max_bytes_constant_is_64_kib():
    """The module constant is the 64 KiB (65536-byte) default."""
    assert _config_defaults_mod.DEFAULT_FINDING_RAW_INPUT_MAX_BYTES == 65536


def test_get_default_config_seeds_finding_raw_input_max_bytes():
    """get_default_config() seeds plan.finding_raw_input_max_bytes at the 64 KiB default."""
    config = _config_defaults_mod.get_default_config()
    assert config['plan']['finding_raw_input_max_bytes'] == 65536


def test_finding_raw_input_max_bytes_matches_manage_findings_default():
    """The seed is byte-identical to manage-findings' DEFAULT_RAW_INPUT_MAX_BYTES.

    The config knob overrides that store-side default; the seed value must not
    drift from the store default, else a fresh project silently changes the cap.
    """
    findings_core_dir = (
        Path(__file__).parent.parent.parent.parent
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'manage-findings'
        / 'scripts'
    )
    findings_core = _load_module(
        '_findings_core_for_raw_input_cap_test',
        '_findings_core.py',
        base_dir=findings_core_dir,
    )
    assert (
        _config_defaults_mod.DEFAULT_FINDING_RAW_INPUT_MAX_BYTES
        == findings_core.DEFAULT_RAW_INPUT_MAX_BYTES
    )


def test_no_per_producer_triage_effort_subkeys_remain():
    """The effort role groups carry only the unified verification-feedback role.

    The consolidated find/triage flow runs ONE triage pass, so there are no
    per-producer (sonar / pr-comment / plugin-doctor / pr-state) effort subkeys —
    the producer is a runtime discriminator, never a config subkey.
    """
    config = _config_defaults_mod.get_default_config()
    p5_effort = config['plan']['phase-5-execute']['effort']
    p6_effort = config['plan']['phase-6-finalize']['effort']
    for producer in ('sonar', 'pr-comment', 'plugin-doctor', 'pr-state', 'build-runner'):
        assert producer not in p5_effort
        assert producer not in p6_effort
    # The unified triage role is present.
    assert 'verification-feedback' in p5_effort
    assert 'verification-feedback' in p6_effort


# =============================================================================
# project.pr_strategy / project.pr_compact_max_changed_files PR-batching knobs
# =============================================================================
#
# Two project-level policy knobs governing whether follow-up / config-migration /
# ad-hoc changes ride an already-pending related PR (compact, within the ceiling)
# or open a separate PR (distinct, or over-ceiling). The `pr-decision` CLI verb is
# the documented single consult surface — the ceiling-boundary test below drives
# it through the cmd_project handler, not only the internal helper.


def test_default_project_pr_strategy_is_compact():
    """DEFAULT_PROJECT must declare pr_strategy == 'compact'."""
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    assert 'pr_strategy' in project_defaults
    assert project_defaults['pr_strategy'] == 'compact'


def test_default_project_pr_compact_max_changed_files_is_150():
    """DEFAULT_PROJECT must declare pr_compact_max_changed_files == 150."""
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    assert 'pr_compact_max_changed_files' in project_defaults
    assert project_defaults['pr_compact_max_changed_files'] == 150


def test_get_default_config_includes_pr_strategy_and_ceiling():
    """get_default_config()['project'] must carry the two PR-batching knobs at their defaults."""
    config = _config_defaults_mod.get_default_config()

    assert config['project'].get('pr_strategy') == 'compact'
    assert config['project'].get('pr_compact_max_changed_files') == 150


def test_valid_pr_strategy_enumerates_compact_and_distinct():
    """VALID_PR_STRATEGY must enumerate exactly ('compact', 'distinct')."""
    assert _config_defaults_mod.VALID_PR_STRATEGY == ('compact', 'distinct')
    # the seeded default must be a member of the enum
    assert (
        _config_defaults_mod.DEFAULT_PROJECT['pr_strategy']
        in _config_defaults_mod.VALID_PR_STRATEGY
    )


def test_validate_pr_strategy_accepts_allowed_values():
    """validate_pr_strategy must accept every value in VALID_PR_STRATEGY."""
    for value in _config_defaults_mod.VALID_PR_STRATEGY:
        _config_defaults_mod.validate_pr_strategy(value)


def test_validate_pr_strategy_rejects_unknown_value():
    """validate_pr_strategy must raise ValueError for a value outside the enum."""
    import pytest

    with pytest.raises(ValueError, match='Invalid pr_strategy'):
        _config_defaults_mod.validate_pr_strategy('sloppy')


def test_validate_pr_compact_max_changed_files_accepts_valid_ints():
    """validate_pr_compact_max_changed_files must accept int >= 0 (151 and 0 boundaries)."""
    _config_defaults_mod.validate_pr_compact_max_changed_files(151)
    _config_defaults_mod.validate_pr_compact_max_changed_files(0)
    # the seeded default must validate
    _config_defaults_mod.validate_pr_compact_max_changed_files(
        _config_defaults_mod.DEFAULT_PROJECT['pr_compact_max_changed_files']
    )


def test_validate_pr_compact_max_changed_files_rejects_negative():
    """validate_pr_compact_max_changed_files must reject a negative int."""
    import pytest

    with pytest.raises(ValueError, match='pr_compact_max_changed_files'):
        _config_defaults_mod.validate_pr_compact_max_changed_files(-1)


def test_validate_pr_compact_max_changed_files_rejects_bool():
    """validate_pr_compact_max_changed_files must reject a bool (bool is an int subclass)."""
    import pytest

    with pytest.raises(ValueError, match='pr_compact_max_changed_files'):
        _config_defaults_mod.validate_pr_compact_max_changed_files(True)


def test_pr_compact_rides_existing_pr_helper_semantics():
    """pr_compact_rides_existing_pr: compact rides within ceiling; distinct never rides."""
    # compact strategy: rides when changed_file_count <= max
    assert _config_defaults_mod.pr_compact_rides_existing_pr('compact', 150, 150) is True
    assert _config_defaults_mod.pr_compact_rides_existing_pr('compact', 149, 150) is True
    assert _config_defaults_mod.pr_compact_rides_existing_pr('compact', 151, 150) is False
    # distinct strategy: always splits regardless of count
    assert _config_defaults_mod.pr_compact_rides_existing_pr('distinct', 1, 150) is False
    assert _config_defaults_mod.pr_compact_rides_existing_pr('distinct', 0, 150) is False


def test_project_set_then_get_roundtrip_pr_strategy(plan_context):
    """`project set --field pr_strategy --value distinct` must round-trip via get."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(verb='set', field='pr_strategy', value='distinct')
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    get_args = Namespace(verb='get', field='pr_strategy')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    assert get_result['status'] == 'success'
    assert get_result['value'] == 'distinct'


def test_project_set_then_get_roundtrip_pr_compact_max_changed_files(plan_context):
    """`project set --field pr_compact_max_changed_files --value 151` must round-trip via get."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(verb='set', field='pr_compact_max_changed_files', value='151')
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    get_args = Namespace(verb='get', field='pr_compact_max_changed_files')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    assert get_result['status'] == 'success'
    assert get_result['value'] == 151


def test_project_set_pr_strategy_rejects_invalid_value(plan_context):
    """`project set --field pr_strategy --value sloppy` must return status: error."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(verb='set', field='pr_strategy', value='sloppy')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


def test_project_set_pr_compact_max_changed_files_rejects_negative(plan_context):
    """`project set --field pr_compact_max_changed_files --value -1` must return status: error."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_args = Namespace(verb='set', field='pr_compact_max_changed_files', value='-1')
    result = _cmd_system_plan_mod.cmd_project(set_args)

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


def test_project_get_pr_strategy_returns_default_when_absent(plan_context):
    """A fresh marshal.json without pr_strategy returns the 'compact' default."""
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('project', {}).pop('pr_strategy', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    args = Namespace(verb='get', field='pr_strategy')
    result = _cmd_system_plan_mod.cmd_project(args)

    assert result['status'] == 'success'
    assert result['value'] == 'compact'


def test_project_pr_decision_ceiling_boundary_through_handler(plan_context):
    """`project pr-decision` proves the 150 → ride / 151 → split boundary at the callable surface.

    With the default compact/150 config, --changed-files 150 returns decision: ride
    and --changed-files 151 returns decision: split. Assert on the verb's returned
    `decision` field so the boundary is proven through cmd_project, not only the
    internal helper.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    ride_result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=150)
    )
    assert ride_result['status'] == 'success'
    assert ride_result['decision'] == 'ride'
    assert ride_result['strategy'] == 'compact'
    assert ride_result['changed_files'] == 150
    assert ride_result['max'] == 150
    assert ride_result['threshold'] == 151

    split_result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=151)
    )
    assert split_result['status'] == 'success'
    assert split_result['decision'] == 'split'


def test_project_pr_decision_distinct_always_splits(plan_context):
    """With pr_strategy == distinct, `project pr-decision` splits for any changed-file count."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='set', field='pr_strategy', value='distinct')
    )
    assert set_result['status'] == 'success'

    result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=1)
    )
    assert result['status'] == 'success'
    assert result['decision'] == 'split'
    assert result['strategy'] == 'distinct'


def test_project_pr_decision_rejects_negative_changed_files(plan_context):
    """`project pr-decision --changed-files -1` must return status: error."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=-1)
    )
    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


def test_project_pr_decision_rejects_corrupt_pr_strategy(plan_context):
    """`project pr-decision` must fail loud on a hand-corrupted pr_strategy.

    The knobs are re-validated at the pr-decision READ boundary (mirroring the
    `set` verb), so a marshal.json hand-edited to an out-of-enum pr_strategy
    produces a clear `status: error` / `error_type: invalid_value` here rather
    than a silent wrong verdict or an opaque crash inside
    pr_compact_rides_existing_pr.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.setdefault('project', {})['pr_strategy'] = 'sloppy'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=10)
    )

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


def test_project_pr_decision_rejects_corrupt_pr_compact_max_changed_files(plan_context):
    """`project pr-decision` must fail loud on a hand-corrupted ceiling value.

    A marshal.json hand-edited to a negative pr_compact_max_changed_files is
    caught by the read-boundary validation before the ride/split rule runs,
    returning a clear `status: error` / `error_type: invalid_value` rather than
    an opaque TypeError deep inside the comparison.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.setdefault('project', {})['pr_compact_max_changed_files'] = -5
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    result = _cmd_system_plan_mod.cmd_project(
        Namespace(verb='pr-decision', changed_files=10)
    )

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


# =============================================================================
# D7 — sync-defaults run_at_all → lane migration
#
# `_migrate_run_at_all_to_lane` moves the four finalize ceremony gates off their
# retired run_at_all locations onto the owning step's per-element `lane` override
# (`never→off` / `always→minimal` / `auto→` omit), removing the legacy key so the
# deep-merge back-fills the newly-materialized lane steps. The three planning
# gates (deep_lane / escalation / revalidation) — which live under
# phase-1-init / phase-2-refine, not phase-6-finalize — are untouched. The
# migration is idempotent.
# =============================================================================


_cmd_sync_defaults_mod = _load_module(
    '_cmd_sync_defaults_for_lane_migration_test', '_cmd_sync_defaults.py'
)
_migrate_run_at_all_to_lane = _cmd_sync_defaults_mod._migrate_run_at_all_to_lane


def test_migrate_qgate_never_materializes_lane_off():
    """qgate: never → materialize default:pre-push-quality-gate with lane: off."""
    live = {'plan': {'phase-6-finalize': {'qgate': 'never', 'steps': {}}}}
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    p6 = live['plan']['phase-6-finalize']
    assert 'qgate' not in p6
    assert p6['steps']['default:pre-push-quality-gate']['lane'] == 'off'
    assert migrated  # a change was recorded


def test_migrate_qgate_always_materializes_lane_minimal():
    """qgate: always → lane: minimal on the materialized owning step."""
    live = {'plan': {'phase-6-finalize': {'qgate': 'always', 'steps': {}}}}
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    p6 = live['plan']['phase-6-finalize']
    assert 'qgate' not in p6
    assert p6['steps']['default:pre-push-quality-gate']['lane'] == 'minimal'


def test_migrate_qgate_auto_omits_lane_but_removes_legacy_key():
    """qgate: auto → the legacy key is removed but NO lane override is written."""
    live = {'plan': {'phase-6-finalize': {'qgate': 'auto', 'steps': {}}}}
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    p6 = live['plan']['phase-6-finalize']
    assert 'qgate' not in p6
    # auto is the lane default — the owning step is NOT materialized with a lane.
    assert 'default:pre-push-quality-gate' not in p6['steps']
    # The removal is still reported so sync-defaults persists the change.
    assert migrated


def test_migrate_step_owned_simplify_always_to_lane_minimal():
    """simplify: always (step-owned param) → lane: minimal, legacy param removed."""
    live = {
        'plan': {
            'phase-6-finalize': {
                'steps': {'default:finalize-step-simplify': {'simplify': 'always'}}
            }
        }
    }
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    params = live['plan']['phase-6-finalize']['steps']['default:finalize-step-simplify']
    assert params['lane'] == 'minimal'
    assert 'simplify' not in params


def test_migrate_all_four_gates_preserve_values():
    """All four ceremony gates migrate together with values preserved."""
    live = {
        'plan': {
            'phase-6-finalize': {
                'qgate': 'never',
                'steps': {
                    'default:pre-submission-self-review': {
                        'self_review': 'always',
                        'drop_review_on_scope_gate': False,
                    },
                    'default:finalize-step-simplify': {'simplify': 'auto'},
                    'default:finalize-step-security-audit': {'security_audit': 'never'},
                },
            }
        }
    }
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    steps = live['plan']['phase-6-finalize']['steps']
    # qgate never → materialized lane off.
    assert steps['default:pre-push-quality-gate']['lane'] == 'off'
    # self_review always → minimal, sibling escape hatch preserved, legacy removed.
    self_review = steps['default:pre-submission-self-review']
    assert self_review['lane'] == 'minimal'
    assert self_review['drop_review_on_scope_gate'] is False
    assert 'self_review' not in self_review
    # simplify auto → legacy removed, no lane written.
    simplify = steps['default:finalize-step-simplify']
    assert 'lane' not in simplify
    assert 'simplify' not in simplify
    # security_audit never → off, legacy removed.
    security = steps['default:finalize-step-security-audit']
    assert security['lane'] == 'off'
    assert 'security_audit' not in security


def test_migrate_bare_owner_key_form_handled():
    """A legacy config storing the owning step under the bare (unprefixed) form migrates."""
    live = {
        'plan': {
            'phase-6-finalize': {
                'steps': {'finalize-step-security-audit': {'security_audit': 'never'}}
            }
        }
    }
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    params = live['plan']['phase-6-finalize']['steps']['finalize-step-security-audit']
    assert params['lane'] == 'off'
    assert 'security_audit' not in params


def test_migration_is_idempotent():
    """A second run reports no migration and leaves the lane values unchanged."""
    live = {
        'plan': {
            'phase-6-finalize': {
                'qgate': 'never',
                'steps': {'default:finalize-step-simplify': {'simplify': 'always'}},
            }
        }
    }
    migrated_first: list = []
    _migrate_run_at_all_to_lane(live, migrated_first)
    assert migrated_first

    migrated_second: list = []
    _migrate_run_at_all_to_lane(live, migrated_second)
    assert migrated_second == []

    steps = live['plan']['phase-6-finalize']['steps']
    assert steps['default:pre-push-quality-gate']['lane'] == 'off'
    assert steps['default:finalize-step-simplify']['lane'] == 'minimal'


def test_planning_gates_untouched_by_run_at_all_migration():
    """deep_lane / escalation / revalidation (under init/refine) are never touched."""
    live = {
        'plan': {
            'phase-1-init': {'deep_lane': 'auto', 'escalation': 'always'},
            'phase-2-refine': {'revalidation': 'never'},
            'phase-6-finalize': {'qgate': 'auto', 'steps': {}},
        }
    }
    migrated: list = []
    _migrate_run_at_all_to_lane(live, migrated)

    assert live['plan']['phase-1-init'] == {'deep_lane': 'auto', 'escalation': 'always'}
    assert live['plan']['phase-2-refine'] == {'revalidation': 'never'}


def test_migration_no_op_on_config_without_phase_6():
    """A config without plan.phase-6-finalize (or without plan) does not crash."""
    for live in ({'plan': {}}, {}, {'plan': {'phase-6-finalize': {}}}):
        migrated: list = []
        # No exception; nothing to migrate.
        _migrate_run_at_all_to_lane(live, migrated)
        assert migrated == []


def test_cmd_sync_defaults_migrates_legacy_run_at_all(plan_context):
    """End-to-end: a legacy marshal.json migrates its ceremony run_at_all to lane.

    Seed a fresh marshal.json, hand-inject a legacy run_at_all shape (flat qgate +
    a step-owned simplify param), then run sync-defaults. The migration converts
    both to the lane channel, removes the legacy keys, and the deep-merge
    back-fills the materialized finalize steps.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    p6 = config['plan']['phase-6-finalize']
    p6['qgate'] = 'never'
    p6.setdefault('steps', {}).setdefault('default:finalize-step-simplify', {})['simplify'] = 'always'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    result = _cmd_sync_defaults_mod.cmd_sync_defaults(Namespace())
    assert result['status'] == 'success'
    assert result['migrated_count'] >= 2

    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    p6_after = after['plan']['phase-6-finalize']
    assert 'qgate' not in p6_after
    steps_after = p6_after['steps']
    assert steps_after['default:pre-push-quality-gate']['lane'] == 'off'
    assert steps_after['default:finalize-step-simplify']['lane'] == 'minimal'
    assert 'simplify' not in steps_after['default:finalize-step-simplify']


def test_cmd_sync_defaults_migration_idempotent_end_to_end(plan_context):
    """A second sync-defaults run reports zero migrations (idempotent end-to-end)."""
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['plan']['phase-6-finalize']['qgate'] = 'always'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    first = _cmd_sync_defaults_mod.cmd_sync_defaults(Namespace())
    assert first['migrated_count'] >= 1

    second = _cmd_sync_defaults_mod.cmd_sync_defaults(Namespace())
    assert second['migrated_count'] == 0
