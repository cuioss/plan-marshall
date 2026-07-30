# SPDX-License-Identifier: FSL-1.1-ALv2
"""Finalize-steps command handler for manage-config.

Handles:
    finalize-steps apply-preset --preset <name>       (preset writer)
    finalize-steps list-ask-lane                       (ask-tier enumerate)
    finalize-steps set-lane --step-id <id> --lane <v> [--plan-id <p>]
                                                       (resolved-ask writer)

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
``standard`` / ``full`` = has them) as the step's ``lane`` override. A steward-set
answer is a RESOLVED ask that the compose-time drop-when-no-provider safety net
never drops.

``set-lane`` writes into one of TWO channels, selected by the optional
``--plan-id`` argument — one verb, one mechanism, two destinations:

- **absent** — the project-wide ``marshal.json`` map at
  ``plan.phase-6-finalize.steps[<step>].lane`` (the steward's channel; unchanged).
- **present** — that ONE plan's ``status.metadata.finalize_step_overrides``
  map, and marshal.json is not touched at all. The plan-local map mirrors the
  marshal shape exactly (id-keyed map of nested param objects, same key forms,
  same lane enum), so both compose-side readers resolve it through the same
  merged source. Keeping the operator's per-plan answer out of marshal.json is
  the point: one plan's answer must not leak into every later plan.
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
from constants import FILE_STATUS
from file_ops import get_plan_dir, read_json, write_json
from finalize_step_presets import (
    FinalizeStepPresets,
)
from input_validation import validate_plan_id

# Phase key the preset writes into.
_PHASE_SECTION = 'phase-6-finalize'

# The ``status.metadata`` key holding the plan-local per-step declaration map —
# the plan-scoped sibling of marshal.json's ``plan.phase-6-finalize.steps``.
_PLAN_LOCAL_STEP_MAP_KEY = 'finalize_step_overrides'

# The lane values an operator may persist when RESOLVING an ask-tier infra
# element. ``ask`` and ``minimal`` are deliberately excluded: ``ask`` is the
# unresolved seed the steward is resolving (persisting it would be a no-op), and
# ``minimal`` is not an operator-facing answer for these standard-tier adversarial
# infra elements. ``off`` = "no bots / no Sonar"; ``standard`` / ``full`` = "has them".
_RESOLVED_ASK_LANE_VALUES: tuple[str, ...] = ('off', 'standard', 'full')


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
    overwrites it to ``off`` / ``standard`` / ``full``). The marshall-steward flow
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


def _set_lane_plan_local(plan_id: str, step_id: str, lane: str) -> dict:
    """Write the resolved ``lane`` into one plan's ``status.metadata`` map.

    The plan-local half of the ``set-lane`` channel selector. Writes
    ``status.metadata.finalize_step_overrides[<step_id>]['lane']`` and touches
    marshal.json not at all, so the operator's answer for THIS plan never leaks
    into every later plan. Sibling params already on the step survive — only the
    ``lane`` knob is replaced — mirroring the marshal-side writer's behaviour.

    An existing map that cannot be parsed as the documented shape is an EXPLICIT
    ERROR, never a silent overwrite: a non-dict ``metadata``, a non-dict override
    map, or a non-dict param object for the target step each abort the write with
    a named reason, so a malformed file is repaired deliberately rather than
    destroyed by the next write.

    Args:
        plan_id: The already-validated plan identifier to write into.
        step_id: The finalize step id whose lane is being declared.
        lane: The resolved lane value.

    Returns:
        The ``success_exit`` / ``error_exit`` result dict.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return error_exit(f"no status.json for plan '{plan_id}'; cannot set plan-local lane")
    status = read_json(status_path, default=None)
    if not isinstance(status, dict):
        return error_exit(
            f"status.json for plan '{plan_id}' is not a JSON object; refusing to overwrite it"
        )
    metadata = status.get('metadata')
    if metadata is None:
        metadata = {}
        status['metadata'] = metadata
    if not isinstance(metadata, dict):
        return error_exit(
            f"status.json metadata for plan '{plan_id}' is not a dict; refusing to overwrite it"
        )
    overrides = metadata.get(_PLAN_LOCAL_STEP_MAP_KEY)
    if overrides is None:
        overrides = {}
        metadata[_PLAN_LOCAL_STEP_MAP_KEY] = overrides
    if not isinstance(overrides, dict):
        return error_exit(
            f"status.metadata.{_PLAN_LOCAL_STEP_MAP_KEY} for plan '{plan_id}' is not a map; "
            'refusing to overwrite it'
        )
    params = overrides.get(step_id)
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return error_exit(
            f"status.metadata.{_PLAN_LOCAL_STEP_MAP_KEY}['{step_id}'] for plan '{plan_id}' is not a "
            'param object; refusing to overwrite it'
        )
    params['lane'] = lane
    overrides[step_id] = params

    write_json(status_path, status)

    return success_exit(
        {
            'step_id': step_id,
            'lane': lane,
            'channel': 'plan_local',
            'plan_id': plan_id,
        }
    )


def cmd_finalize_steps_set_lane(args) -> dict:
    """Handle ``finalize-steps set-lane --step-id <id> --lane <off|standard|full> [--plan-id <p>]``.

    Persists the operator's RESOLVED answer as the finalize step's ``lane``
    override, preserving any other params on the step and materializing the step
    entry when absent. ``--plan-id`` selects the CHANNEL, and is the only new
    argument — there is no second writer verb:

    - **absent** → ``plan.phase-6-finalize.steps[<step_id>].lane`` in the
      project-wide marshal.json (unchanged behaviour).
    - **present** → ``status.metadata.finalize_step_overrides[<step_id>].lane``
      for that plan only, leaving marshal.json byte-unchanged.

    The lane value is validated against :data:`_RESOLVED_ASK_LANE_VALUES` (``off``
    / ``standard`` / ``full``) on BOTH channels, and the step id is re-validated
    against the discovered finalize-step universe (defence in depth, mirroring the
    preset writer). That writer enum is a deliberate SUBSET of the reader's
    ``LANE_OVERRIDES``: ``off`` / ``standard`` / ``full`` are the resolved answers an
    operator dialogue produces, while ``minimal`` and ``ask`` are seed values only
    shipped frontmatter and marshal seeding emit. A writer emitting a subset of a
    valid enum is not the two-readers-disagreeing drift — both readers accept the
    full enum; this writer simply never produces the seed half of it.

    A resolved answer written here is never dropped by the compose-time
    drop-when-no-provider safety net.
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

    # Channel selection. An ABSENT --plan-id is the project-wide channel; a
    # PRESENT-but-invalid value is an explicit error, never a silent fall-through
    # to the project-wide write, which would leak one plan's answer into every
    # later plan — precisely the outcome the plan-local channel exists to prevent.
    plan_id = getattr(args, 'plan_id', None)
    if plan_id is not None:
        try:
            plan_id = validate_plan_id(plan_id)
        except ValueError as exc:
            return error_exit(str(exc))
        return _set_lane_plan_local(plan_id, step_id, lane)

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
            'channel': 'project',
        }
    )
