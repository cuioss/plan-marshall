# SPDX-License-Identifier: FSL-1.1-ALv2
"""Finalize-steps command handler for manage-config.

Handles:
    finalize-steps apply-preset --preset <name>       (preset writer)
    finalize-steps list-ask-lane                       (ask-tier enumerate)
    finalize-steps set-lane --step-id <id> --lane <v>  (resolved-ask writer)

The write path imports :class:`FinalizeStepPresets` from this skill.
``apply-preset`` surgically writes the preset's step list into
``plan.phase-6-finalize.steps`` while preserving every other phase-6 knob
(``max_iterations``, ``pr_merge_strategy``, ``auto_rebase_threshold``,
…). Step enumeration stays on the existing ``list-finalize-steps`` surface;
this module only adds the preset writer.

``list-ask-lane`` / ``set-lane`` back the marshall-steward always-prompt flow
(setup + update-config) for the two adversarial infra elements seeded with a
``lane: ask`` override (``plan-marshall:automatic-review`` /
``default:sonar-roundtrip``): ``list-ask-lane`` enumerates the finalize steps
whose effective lane override is still ``ask`` (unresolved), and ``set-lane``
persists the operator's resolved answer (``off`` = no bots / Sonar;
``auto`` / ``full`` = has them) as the step's ``lane`` override. A steward-set
answer is a RESOLVED ask that the compose-time drop-when-no-provider safety net
never drops.
"""

from _cmd_quality_phases import _resolve_step_orders, _steps_map
from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from _config_defaults import FINALIZE_STEP_EXT_POINT
from finalize_step_presets import (
    FinalizeStepPresets,
)

# Phase key the preset writes into.
_PHASE_SECTION = 'phase-6-finalize'

# The lane values an operator may persist when RESOLVING an ask-tier infra
# element. ``ask`` and ``minimal`` are deliberately excluded: ``ask`` is the
# unresolved seed the steward is resolving (persisting it would be a no-op), and
# ``minimal`` is not an operator-facing answer for these auto-tier adversarial
# infra elements. ``off`` = "no bots / no Sonar"; ``auto`` / ``full`` = "has them".
_RESOLVED_ASK_LANE_VALUES: tuple[str, ...] = ('off', 'auto', 'full')


def _known_finalize_steps() -> frozenset[str]:
    """Return the known finalize-step universe via the discovery query.

    Defence-in-depth: recomputed from the reusable
    ``extension_discovery.find_implementors`` query (the same SOLE discovery path
    the seed and preset builder consume) so the writer re-validates the preset
    payload against the live discovered universe — built-in, bundle-optional, and
    project step ids alike. Computed on demand (not at module import) so this
    module stays a leaf and the universe always reflects the current step docs.
    """
    from extension_discovery import find_implementors

    return frozenset(
        rec['name'] for rec in find_implementors(FINALIZE_STEP_EXT_POINT) if rec.get('name')
    )


def cmd_finalize_steps_apply_preset(args) -> dict:
    """Handle ``finalize-steps apply-preset --preset <name>`` subcommand.

    Surgically writes the preset's step list into
    ``config['plan']['phase-6-finalize']['steps']``. Other per-phase config
    knobs (``max_iterations``, ``pr_merge_strategy``,
    ``auto_rebase_threshold``, …) are preserved.

    Resolution flow:

    1. ``FinalizeStepPresets.get(args.preset)`` returns a deep copy of the
       preset's step list. The lookup is case-insensitive.
    2. Defence-in-depth: re-validate every step against the known
       finalize-step universe imported from ``_config_defaults`` — guards
       against a preset that passed the registry import-time check drifting
       out of sync with the registry at write time.
    3. Load ``marshal.json``, merge the ``steps`` map into the
       ``plan.phase-6-finalize`` entry (creating the entry if absent) in the
       canonical keyed-map form (``{step_id: {params}}``, ``{}`` for config-less
       steps), and save.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    try:
        steps = FinalizeStepPresets.get(args.preset)
    except ValueError as exc:
        return error_exit(str(exc))

    # Defence-in-depth re-validation against the discovered universe.
    known_steps = _known_finalize_steps()
    for step in steps:
        if step not in known_steps:
            return error_exit(
                f"preset '{args.preset}' references unknown finalize step "
                f"'{step}'"
            )

    config = load_config()
    plan_block = config.setdefault('plan', {})
    if not isinstance(plan_block, dict):
        return error_exit(
            "plan block in marshal.json is not a dict; cannot merge preset steps"
        )
    phase_entry = plan_block.setdefault(_PHASE_SECTION, {})
    if not isinstance(phase_entry, dict):
        return error_exit(
            f"plan['{_PHASE_SECTION}'] exists but is not a dict; "
            f'cannot merge steps attribute'
        )

    # Sort the preset's step list ascending by resolved frontmatter `order`
    # before persisting, reusing the same helper `set-steps`/`add-step` use.
    # This closes the durability gap that let a preset persist an out-of-order
    # phase-6-finalize steps list. On the helper's error return (missing order
    # / collision) propagate the error rather than persisting.
    resolved, err = _resolve_step_orders(steps, _PHASE_SECTION)
    if err is not None:
        return err
    sorted_ids = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
    # Read any existing per-step params through `_steps_map`, which normalizes the
    # on-disk keyed map to the internal id-keyed map ({step_id: param-object}, {}
    # for config-less steps) so the preset preserves them.
    existing_params = _steps_map(phase_entry.get('steps'))
    # Build the ordered id-keyed map (preset order = execution order), preserving
    # existing params for retained steps and seeding empty params for new ones,
    # then persist the keyed map directly (the sole on-disk shape).
    ordered_map = {step_id: existing_params.get(step_id, {}) for step_id in sorted_ids}
    phase_entry['steps'] = ordered_map

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'steps_count': len(sorted_ids),
        }
    )


def _read_phase6_steps_raw(config: dict) -> dict:
    """Return the raw ``plan.phase-6-finalize.steps`` keyed map from ``config``.

    Reads the on-disk keyed map verbatim (step ids keep their ``default:`` /
    ``plan-marshall:`` prefixes) so an enumerate returns exactly the key form a
    subsequent ``set-lane`` writes back. Returns an empty dict when the plan
    block, phase entry, or steps map is absent or malformed.
    """
    plan_block = config.get('plan', {})
    if not isinstance(plan_block, dict):
        return {}
    phase = plan_block.get(_PHASE_SECTION, {})
    if not isinstance(phase, dict):
        return {}
    steps = phase.get('steps')
    return steps if isinstance(steps, dict) else {}


def cmd_finalize_steps_list_ask_lane(args) -> dict:
    """Handle ``finalize-steps list-ask-lane`` — enumerate unresolved ask-tier steps.

    Returns the finalize steps whose effective ``lane`` override is still ``ask``
    (the UNRESOLVED case — the seed is ``ask`` and a steward-persisted answer
    overwrites it to ``off`` / ``auto`` / ``full``). The marshall-steward flow
    surfaces these steps in a mandatory prompt at setup and update-config; the
    two seeded infra elements (``plan-marshall:automatic-review`` /
    ``default:sonar-roundtrip``) are the canonical members.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    steps_map = _read_phase6_steps_raw(load_config())
    ask_steps = [
        step_id
        for step_id, params in steps_map.items()
        if isinstance(params, dict) and params.get('lane') == 'ask'
    ]
    return success_exit(
        {
            'ask_steps': ask_steps,
            'ask_steps_count': len(ask_steps),
        }
    )


def cmd_finalize_steps_set_lane(args) -> dict:
    """Handle ``finalize-steps set-lane --step-id <id> --lane <off|auto|full>``.

    Persists the operator's RESOLVED answer as the finalize step's ``lane``
    override under ``plan.phase-6-finalize.steps[<step_id>].lane``, preserving any
    other params on the step and materializing the step entry when absent. The
    lane value is validated against :data:`_RESOLVED_ASK_LANE_VALUES` (``off`` /
    ``auto`` / ``full`` — never ``ask`` / ``minimal``), and the step id is
    re-validated against the discovered finalize-step universe (defence in depth,
    mirroring the preset writer). A resolved answer written here is never dropped
    by the compose-time drop-when-no-provider safety net.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    lane = args.lane
    if lane not in _RESOLVED_ASK_LANE_VALUES:
        return error_exit(
            f"invalid lane '{lane}'; must be one of {list(_RESOLVED_ASK_LANE_VALUES)}"
        )

    step_id = args.step_id
    if step_id not in _known_finalize_steps():
        return error_exit(f"unknown finalize step '{step_id}'")

    config = load_config()
    plan_block = config.setdefault('plan', {})
    if not isinstance(plan_block, dict):
        return error_exit('plan block in marshal.json is not a dict; cannot set lane')
    phase_entry = plan_block.setdefault(_PHASE_SECTION, {})
    if not isinstance(phase_entry, dict):
        return error_exit(
            f"plan['{_PHASE_SECTION}'] exists but is not a dict; cannot set lane"
        )
    steps = phase_entry.get('steps')
    if not isinstance(steps, dict):
        steps = {}
        phase_entry['steps'] = steps
    params = steps.get(step_id)
    if not isinstance(params, dict):
        params = {}
    params['lane'] = lane
    steps[step_id] = params

    save_config(config)

    return success_exit(
        {
            'step_id': step_id,
            'lane': lane,
        }
    )
