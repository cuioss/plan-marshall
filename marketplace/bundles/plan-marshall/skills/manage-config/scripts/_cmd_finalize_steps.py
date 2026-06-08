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

import sys

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
    CEREMONY_FOOTGUNS,
    CEREMONY_HARD_FOOTGUNS,
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
    sorted_steps = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
    phase_entry['steps'] = sorted_steps

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'steps_count': len(sorted_steps),
        }
    )


def ceremony_set_footgun_warnings(changes: dict[str, str]) -> list[str]:
    """Return (and emit) the set-time footgun warnings for ceremony-policy changes.

    The ``ceremony_policy`` gate fields named in :data:`CEREMONY_FOOTGUNS`
    disable a safety net when set to ``never``. Per the DQ4 footgun catalogue,
    such a change is allowed (the operator owns the risk) but MUST NEVER be
    silent: this helper emits a ``[WARNING]`` line to stderr naming the disabled
    safety for each footgun set to ``never``, and returns the list of emitted
    warning messages so callers / tests can assert the emission.

    Args:
        changes: A mapping of dotted ceremony-policy gate paths (e.g.
            ``'finalize.qgate'``) to the value being set (e.g. ``'never'``).
            Non-footgun paths and non-``never`` values are ignored.

    Returns:
        The list of warning messages emitted (empty when no footgun fired).
    """
    warnings: list[str] = []
    for path, value in changes.items():
        if value != 'never':
            continue
        disabled = CEREMONY_FOOTGUNS.get(path)
        if disabled is None:
            continue
        if path in CEREMONY_HARD_FOOTGUNS:
            message = (
                f'[WARNING] (plan-marshall:manage-config) ceremony_policy.{path}=never disables '
                f'{disabled} — this is the highest-risk footgun and can push a red tree; '
                'set explicitly and own the risk (CI may still fail).'
            )
        else:
            message = (
                f'[WARNING] (plan-marshall:manage-config) ceremony_policy.{path}=never disables '
                f'{disabled} — allowed, but you own the risk.'
            )
        print(message, file=sys.stderr)
        warnings.append(message)
    return warnings


def ceremony_override_matches(when: dict[str, str], plan_facts: dict[str, str]) -> bool:
    """Return ``True`` iff an ``overrides[]`` row's ``when`` clause matches the plan facts.

    An override row wins over the section value only when every key/value pair
    in its ``when`` clause is present and equal in ``plan_facts``. An empty
    ``when`` clause matches every plan (the unconditional override). Plan facts
    are the deterministic per-plan values the router / composer pass in
    (``scope_estimate``, ``plan_source``, ``change_type``).

    Args:
        when: The override row's condition clause.
        plan_facts: The plan's deterministic facts.

    Returns:
        ``True`` when the row applies to this plan, else ``False``.
    """
    if not isinstance(when, dict):
        return False
    for fact, expected in when.items():
        if plan_facts.get(fact) != expected:
            return False
    return True
