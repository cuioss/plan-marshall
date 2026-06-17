"""Finalize-steps command handler for manage-config.

Handles:
    finalize-steps apply-preset --preset <name>   (preset writer)

The write path imports :class:`FinalizeStepPresets` from this skill.
``apply-preset`` surgically writes the preset's step list into
``plan.phase-6-finalize.steps`` while preserving every other phase-6 knob
(``max_iterations``, ``pr_merge_strategy``, ``auto_rebase_threshold``,
…). Step enumeration stays on the existing ``list-finalize-steps`` surface;
this module only adds the preset writer.
"""

from _cmd_quality_phases import _resolve_step_orders
from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from _config_defaults import (
    BUILT_IN_FINALIZE_STEPS,
    OPTIONAL_BUNDLE_FINALIZE_STEPS,
)
from finalize_step_presets import (  # type: ignore[import-not-found]
    FinalizeStepPresets,
)

# Phase key the preset writes into.
_PHASE_SECTION = 'phase-6-finalize'

# Defence-in-depth: the known finalize-step universe, recomputed here from
# the authoritative _config_defaults registry. Mirrors KNOWN_FINALIZE_STEPS
# in finalize_step_presets.py but kept local so the writer re-validates the
# preset payload independently of the registry module's import-time check.
_KNOWN_FINALIZE_STEPS: frozenset[str] = frozenset(BUILT_IN_FINALIZE_STEPS) | frozenset(
    OPTIONAL_BUNDLE_FINALIZE_STEPS
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
    3. Load ``marshal.json``, merge the ``steps`` list into the
       ``plan.phase-6-finalize`` entry (creating the entry if absent), and
       save.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    try:
        steps = FinalizeStepPresets.get(args.preset)
    except ValueError as exc:
        return error_exit(str(exc))

    # Defence-in-depth re-validation against the authoritative registry.
    for step in steps:
        if step not in _KNOWN_FINALIZE_STEPS:
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
    # `steps` is an id-keyed map (step_id -> nested param object). Preserve any
    # existing per-step params for steps the preset keeps, and seed empty params
    # for newly-introduced steps. Key insertion order is the execution order.
    existing = phase_entry.get('steps')
    existing_params = existing if isinstance(existing, dict) else {}
    phase_entry['steps'] = {
        step_id: existing_params.get(step_id, {}) for step_id in sorted_ids
    }

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'steps_count': len(sorted_ids),
        }
    )
