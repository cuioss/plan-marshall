"""
Phase-based plan command handler for manage-config.

Handles plan sub-nouns: phase-1-init, phase-2-refine, phase-5-execute,
phase-6-finalize.

All phases read/write from config['plan'][phase_section].
"""

from _cmd_skill_domains import _discover_all_verify_steps
from _cmd_skill_resolution import _discover_all_finalize_steps
from _config_core import (
    MarshalNotInitializedError,
    _coerce_value,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)
from _config_defaults import get_default_config
from constants import PHASES  # type: ignore[import-not-found]

# Valid phase sections - derived from centralized PHASES with 'phase-' prefix for marshal.json keys
PHASE_SECTIONS = {f'phase-{p}' for p in PHASES}

# Phases that use ordered steps list (set-steps, add-step, remove-step, set-max-iterations)
LIST_STEP_PHASES = {'phase-5-execute', 'phase-6-finalize'}

# Phases with simple scalar fields only
SCALAR_PHASES = {'phase-1-init', 'phase-2-refine', 'phase-3-outline', 'phase-4-plan'}


def _discover_steps_for_phase(phase_section: str) -> list[dict]:
    """Return the list of discovered step dicts for an order-aware phase.

    Each dict carries `name` and `order` (int or None). Raises nothing — empty
    list signals no discovered steps for the phase.
    """
    if phase_section == 'phase-5-execute':
        return _discover_all_verify_steps()
    if phase_section == 'phase-6-finalize':
        return _discover_all_finalize_steps()
    return []


def _resolve_step_orders(
    steps: list[str], phase_section: str, overrides: dict
) -> tuple[list[tuple[str, int]], dict | None]:
    """Resolve `(step, order)` pairs and detect missing/colliding orders.

    Override precedence: `overrides[step_ref]` > discovery-time `order`.

    Returns:
        (resolved, error):
            - On success: (list of (step, order) in input order, None).
            - On missing order: ([], error_exit payload).
            - On collision: ([], error_exit payload).
    """
    discovered = {s['name']: s.get('order') for s in _discover_steps_for_phase(phase_section)}

    resolved: list[tuple[str, int]] = []
    for step in steps:
        if step in overrides and isinstance(overrides[step], int):
            resolved.append((step, overrides[step]))
            continue
        discovered_order = discovered.get(step)
        if isinstance(discovered_order, int):
            resolved.append((step, discovered_order))
            continue
        return [], error_exit(
            'missing_order',
            step=step,
            phase=phase_section,
            detail=(
                f"Step '{step}' has no resolved order in {phase_section}. "
                'Declare an `order` field in its authoritative source, or persist an override via '
                '`set-step-order-override`.'
            ),
        )

    seen: dict[int, str] = {}
    for step, order in resolved:
        if order in seen:
            return [], error_exit(
                'order_collision',
                steps=[seen[order], step],
                order=order,
                phase=phase_section,
                detail=(
                    f"Steps '{seen[order]}' and '{step}' share order={order} in {phase_section}. "
                    'Reassign one via `set-step-order-override`.'
                ),
            )
        seen[order] = step

    return resolved, None


def cmd_phase(args, phase_section: str) -> dict:
    """Handle phase-based plan sub-nouns.

    Args:
        args: Parsed arguments with verb and optional parameters
        phase_section: Phase key (e.g., 'phase-5-execute')
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    plan_config = config.get('plan', {})
    # Merge defaults for missing fields (supports config evolution without migration)
    defaults = get_default_config().get('plan', {}).get(phase_section, {})
    section = {**defaults, **plan_config.get(phase_section, {})}

    if args.verb == 'get':
        field = getattr(args, 'field', None)
        if field:
            if field not in section:
                return error_exit(f"Unknown field '{field}' in {phase_section}")
            return success_exit({'phase': phase_section, 'field': field, 'value': section[field]})
        return success_exit({'phase': phase_section, **section})

    elif args.verb == 'set' and phase_section in (SCALAR_PHASES | LIST_STEP_PHASES):
        field = args.field
        value = _coerce_value(args.value)
        section[field] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'field': field, 'value': value})

    elif args.verb == 'set-max-iterations' and phase_section in LIST_STEP_PHASES:
        value = int(args.value)
        key = 'verification_max_iterations' if phase_section == 'phase-5-execute' else 'max_iterations'
        section[key] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, key: value})

    elif args.verb == 'set-steps' and phase_section in LIST_STEP_PHASES:
        steps_str = args.steps  # comma-separated
        steps = [s.strip() for s in steps_str.split(',') if s.strip()]
        if not steps:
            return error_exit('Steps list cannot be empty')

        overrides = section.get('step_order_overrides', {})
        resolved, err = _resolve_step_orders(steps, phase_section, overrides)
        if err is not None:
            return err

        sorted_steps = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
        section['steps'] = sorted_steps
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'steps': sorted_steps, 'count': len(sorted_steps)})

    elif args.verb == 'add-step' and phase_section in LIST_STEP_PHASES:
        step = args.step
        steps = list(section.get('steps', []))
        if step in steps:
            return error_exit(f"Step '{step}' already exists in {phase_section}")

        overrides = section.get('step_order_overrides', {})
        resolved, err = _resolve_step_orders(steps + [step], phase_section, overrides)
        if err is not None:
            return err

        sorted_steps = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
        section['steps'] = sorted_steps
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'step': step, 'steps': sorted_steps, 'count': len(sorted_steps)})

    elif args.verb == 'remove-step' and phase_section in LIST_STEP_PHASES:
        step = args.step
        steps = list(section.get('steps', []))
        if step not in steps:
            return error_exit(f"Step '{step}' not found in {phase_section}")

        steps.remove(step)
        section['steps'] = steps
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'step': step, 'steps': steps, 'count': len(steps)})

    elif args.verb == 'set-step-order-override' and phase_section in LIST_STEP_PHASES:
        step = args.step
        order = int(args.order)
        overrides = dict(section.get('step_order_overrides', {}))
        overrides[step] = order
        section['step_order_overrides'] = overrides
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {
                'phase': phase_section,
                'step': step,
                'order': order,
                'step_order_overrides': overrides,
            }
        )

    elif args.verb == 'remove-step-order-override' and phase_section in LIST_STEP_PHASES:
        step = args.step
        overrides = dict(section.get('step_order_overrides', {}))
        if step not in overrides:
            return error_exit(
                f"No order override for step '{step}' in {phase_section}",
                step=step,
                phase=phase_section,
            )
        del overrides[step]
        section['step_order_overrides'] = overrides
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {
                'phase': phase_section,
                'step': step,
                'removed': True,
                'step_order_overrides': overrides,
            }
        )

    return error_exit('Unknown phase verb')
