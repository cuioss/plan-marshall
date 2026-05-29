"""Finalize-steps command handler for manage-config.

Handles:
    finalize-steps apply-preset --preset <name>   (preset writer)

The write path imports :class:`FinalizeStepPresets` from this skill.
``apply-preset`` surgically writes the preset's step list into
``plan.phase-6-finalize.steps`` while preserving every other phase-6 knob
(``max_iterations``, ``pr_merge_strategy``, ``loop_back_without_asking``,
…). Step enumeration stays on the existing ``list-finalize-steps`` surface;
this module only adds the preset writer.
"""

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
    ``loop_back_without_asking``, …) are preserved.

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
    phase_entry = plan_block.setdefault(_PHASE_SECTION, {})
    if not isinstance(phase_entry, dict):
        return error_exit(
            f"plan['{_PHASE_SECTION}'] exists but is not a dict; "
            f'cannot merge steps attribute'
        )
    phase_entry['steps'] = steps

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'steps_count': len(steps),
        }
    )
