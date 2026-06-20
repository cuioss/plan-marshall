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
from _config_defaults import (
    get_default_config,
    validate_per_deliverable_build,
)
from constants import PHASES  # type: ignore[import-not-found]

# Valid phase sections - derived from centralized PHASES with 'phase-' prefix for marshal.json keys
PHASE_SECTIONS = {f'phase-{p}' for p in PHASES}

# Phases that use ordered steps list (set-steps, add-step, remove-step, set-max-iterations)
LIST_STEP_PHASES = {'phase-5-execute', 'phase-6-finalize'}

# Per-phase config key holding the ordered step list. phase-5-execute stores its
# verify-step list under `verification_steps` (the self-describing name decoupling
# it from phase-6-finalize's generic `steps`); phase-6-finalize keeps `steps`.
LIST_STEP_KEYS = {
    'phase-5-execute': 'verification_steps',
    'phase-6-finalize': 'steps',
}

# Phases with simple scalar fields only
SCALAR_PHASES = {'phase-1-init', 'phase-2-refine', 'phase-3-outline', 'phase-4-plan'}

# Canonical-verify step prefixes. Every step ID of the shape
# ``default:verify:{canonical}`` (and its legacy ``verify:{canonical}`` form) is
# backed by the single ``canonical_verify.md`` standards doc, so they all resolve
# to the SAME frontmatter ``order`` (10). They are therefore exempt from the
# distinct-order collision check: their effective ordering comes from their
# position in the persisted ``verification_steps`` list, not from the shared
# frontmatter order. See ``phase-5-execute/standards/canonical_verify.md`` §
# "Ordering among canonical-verify entries".
_CANONICAL_VERIFY_PREFIXES = ('default:verify:', 'verify:')


def _is_canonical_verify_step(step: str) -> bool:
    """Return True when ``step`` is a canonical-verify step ID.

    Canonical-verify steps (``default:verify:{canonical}`` / ``verify:{canonical}``)
    all share the single ``canonical_verify.md`` backing doc and its order, so
    they are ordered by list position rather than by their (shared) resolved
    order.
    """
    return step.startswith(_CANONICAL_VERIFY_PREFIXES)


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
    steps: list[str], phase_section: str
) -> tuple[list[tuple[str, float]], dict | None]:
    """Resolve `(step, order)` pairs and detect missing/colliding orders.

    Order is taken exclusively from each step's authoritative source (frontmatter
    on built-in standards docs, frontmatter on project-local SKILL.md for
    `project:` steps, or the return-dict `order` field for extension-contributed
    skills).

    Canonical-verify steps (``default:verify:{canonical}`` / ``verify:{canonical}``)
    are a special case: they all share the single ``canonical_verify.md`` backing
    doc and therefore resolve to the SAME frontmatter order. They are exempt from
    the distinct-order collision check — multiple canonical-verify steps are valid
    and are ordered by their position in the input ``steps`` list. To preserve that
    list position while still sorting them relative to non-canonical steps, each
    canonical-verify step's effective order is its shared base order plus a tiny
    fractional offset derived from its list index (``base + index * 1e-6``), so the
    sorted output keeps the input order within the canonical-verify group. Only
    NON-canonical-verify steps participate in the distinct-order collision check.

    Returns:
        (resolved, error):
            - On success: (list of (step, order) in input order, None). Orders are
              floats so canonical-verify steps can carry a fractional list-position
              offset.
            - On missing order: ([], error_exit payload).
            - On collision (non-canonical steps only): ([], error_exit payload).
    """
    discovered = {s['name']: s.get('order') for s in _discover_steps_for_phase(phase_section)}

    resolved: list[tuple[str, float]] = []
    for index, step in enumerate(steps):
        discovered_order = discovered.get(step)
        if isinstance(discovered_order, int):
            if _is_canonical_verify_step(step):
                # Order by list position within the shared canonical-verify slot.
                resolved.append((step, discovered_order + index * 1e-6))
            else:
                resolved.append((step, float(discovered_order)))
            continue
        return [], error_exit(
            'missing_order',
            step=step,
            phase=phase_section,
            detail=(
                f"Step '{step}' has no resolved order in {phase_section}. "
                'Declare an `order` field in its authoritative source.'
            ),
        )

    # Collision check: canonical-verify steps may freely share their common base
    # order with one another (they are disambiguated by the list-position offset
    # above), but every OTHER pair sharing an integer base order is a genuine
    # collision. We therefore record one representative per base order and flag a
    # collision whenever a step lands on an already-seen base order UNLESS both the
    # incoming step and the recorded representative are canonical-verify steps.
    seen: dict[int, str] = {}
    for step, order in resolved:
        int_order = int(order)
        prior = seen.get(int_order)
        if prior is not None:
            both_canonical = _is_canonical_verify_step(step) and _is_canonical_verify_step(prior)
            if not both_canonical:
                return [], error_exit(
                    'order_collision',
                    steps=[prior, step],
                    order=int_order,
                    phase=phase_section,
                    detail=(
                        f"Steps '{prior}' and '{step}' share order={int_order} in {phase_section}. "
                        'Reassign one of the colliding steps in its authoritative source.'
                    ),
                )
            # Both canonical — keep the FIRST representative so a later
            # non-canonical step on the same base order still collides.
            continue
        seen[int_order] = step

    return resolved, None


def _steps_map(raw) -> dict:
    """Return the keyed-map step structure as a fresh ordered dict.

    The on-disk schema for ``verification_steps`` / ``steps`` is an id-keyed map
    (``{step_id: {param: value, ...}, ...}``); key insertion order is the
    execution order. This normaliser returns a shallow copy so callers can mutate
    it without touching the loaded config. A falsy top-level value (the key
    absent / ``None``) yields an empty dict.

    Per-step values are coerced: an ownerless step now seeds as ``None``
    (serialized as ``null``), but a legacy ``{}`` and a TOON round-tripped ``''``
    are also possible on-disk shapes. Every per-step value that is not a
    non-empty dict (i.e. ``None`` / ``{}`` / ``''`` / any non-dict) is coerced to
    an empty dict, so ``_cmd_step get`` returns ``{}`` for an ownerless step
    regardless of its on-disk representation. A param-owning step keeps its
    nested object.

    Args:
        raw: The value read from ``section[list_key]`` — expected to be a dict in
            the keyed-map schema, or ``None`` when the key is absent.

    Returns:
        A new dict mapping step id -> nested param object (``{}`` for ownerless
        steps), in insertion order.
    """
    if not raw:
        return {}
    return {
        step_id: (value if isinstance(value, dict) else {})
        for step_id, value in raw.items()
    }


def _collapse_ownerless_steps(steps: dict) -> dict:
    """Return a copy of the keyed-map with ownerless steps collapsed to ``None``.

    The write-side mirror of :func:`_steps_map`'s per-step coercion: an ownerless
    step (its param value is an empty dict ``{}``) is written as ``None``
    (serialized as ``null`` by :func:`save_config`) so marshal.json never carries
    a noisy empty ``{}`` object. A param-owning step keeps its nested object.
    Applied right before persisting any mutated keyed-map (``step set`` /
    ``set-steps`` / ``add-step`` / ``remove-step``), so every config-write path is
    consistent with the no-empty-``{}`` contract; the read path
    (:func:`_steps_map`) coerces ``null`` / ``{}`` / ``''`` back to ``{}``.
    """
    return {step_id: (params if params else None) for step_id, params in steps.items()}


def _cmd_step(args, phase_section: str, section: dict, plan_config: dict, config: dict) -> dict:
    """Handle the one-stop ``step get`` / ``step set`` verb.

    ``step get --step-id {id}`` returns the complete nested param object for a
    step in a single call; ``step set --step-id {id} --param {k} --value {v}``
    writes one step-owned param into the step's nested object (value-coerced).
    Both operate on the keyed-map step structure under the phase's list key. An
    absent step id is an explicit error.

    Args:
        args: Parsed arguments carrying ``step_verb``, ``step_id``, and (for set)
            ``param`` / ``value``.
        phase_section: Phase key (e.g., ``'phase-6-finalize'``).
        section: The defaults-merged phase section.
        plan_config: The mutable ``config['plan']`` subtree.
        config: The full loaded config (persisted on a successful set).
    """
    list_key = LIST_STEP_KEYS[phase_section]
    step_id = args.step_id
    steps = _steps_map(section.get(list_key))

    if args.step_verb == 'get':
        if step_id not in steps:
            return error_exit(f"Step '{step_id}' not found in {phase_section}")
        return success_exit(
            {'phase': phase_section, 'step_id': step_id, 'params': steps[step_id]}
        )

    if args.step_verb == 'set':
        if step_id not in steps:
            return error_exit(f"Step '{step_id}' not found in {phase_section}")
        param = args.param
        value = _coerce_value(args.value)
        params = dict(steps[step_id])
        params[param] = value
        steps[step_id] = params
        section[list_key] = _collapse_ownerless_steps(steps)
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {'phase': phase_section, 'step_id': step_id, 'params': params}
        )

    return error_exit(f"Unknown step verb '{args.step_verb}'")


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
        # Guard: the phase's keyed step-map field (`steps` for phase-6-finalize,
        # `verification_steps` for phase-5-execute) is a structured keyed map, not
        # a scalar — routing it through `_coerce_value` would string-corrupt the
        # map. Reject and direct the caller to the keyed-map verbs instead.
        if phase_section in LIST_STEP_PHASES and field == LIST_STEP_KEYS[phase_section]:
            return error_exit(
                f"Field '{field}' is a keyed step-map and cannot be set via "
                "'set --field'. Use: set-steps, add-step, remove-step, or step set."
            )
        # per_deliverable_build is a LIST of 'default:verify:{canonical}' step
        # IDs — parse the comma-separated --value into a list (empty string ->
        # empty list, which disables the per-deliverable build) and validate the
        # list shape before mutating config. All other fields coerce as scalars.
        value: str | bool | int | list[str]
        if phase_section == 'phase-5-execute' and field == 'per_deliverable_build':
            value = [s.strip() for s in args.value.split(',') if s.strip()]
            try:
                validate_per_deliverable_build(value)
            except ValueError as e:
                return error_exit(str(e))
        else:
            value = _coerce_value(args.value)
        section[field] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'field': field, 'value': value})

    elif args.verb == 'set-max-iterations' and phase_section in LIST_STEP_PHASES:
        value = int(args.value)
        key = 'max_iterations'
        section[key] = value
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, key: value})

    elif args.verb == 'step' and phase_section in LIST_STEP_PHASES:
        # One-stop step verb: `step get` / `step set` against the keyed-map step
        # structure. `step get --step-id {id}` returns the complete nested param
        # object for a step in a single call; `step set --step-id {id} --param {k}
        # --value {v}` writes one step-owned param into the step's nested object.
        return _cmd_step(args, phase_section, section, plan_config, config)

    elif args.verb == 'set-steps' and phase_section in LIST_STEP_PHASES:
        list_key = LIST_STEP_KEYS[phase_section]
        steps_str = args.steps  # comma-separated
        steps = [s.strip() for s in steps_str.split(',') if s.strip()]
        if not steps:
            return error_exit('Steps list cannot be empty')

        resolved, err = _resolve_step_orders(steps, phase_section)
        if err is not None:
            return err

        existing = _steps_map(section.get(list_key))
        sorted_ids = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
        # Build the ordered keyed map, preserving any existing per-step params.
        sorted_map = {step_id: existing.get(step_id, {}) for step_id in sorted_ids}
        # Persist with ownerless steps collapsed to `null` (no empty `{}`).
        section[list_key] = _collapse_ownerless_steps(sorted_map)
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {'phase': phase_section, list_key: sorted_map, 'count': len(sorted_map)}
        )

    elif args.verb == 'add-step' and phase_section in LIST_STEP_PHASES:
        list_key = LIST_STEP_KEYS[phase_section]
        step = args.step
        existing = _steps_map(section.get(list_key))
        if step in existing:
            return error_exit(f"Step '{step}' already exists in {phase_section}")

        resolved, err = _resolve_step_orders(list(existing.keys()) + [step], phase_section)
        if err is not None:
            return err

        sorted_ids = [s for s, _ in sorted(resolved, key=lambda pair: pair[1])]
        # Preserve existing per-step params; the new key starts with empty params.
        sorted_map = {step_id: existing.get(step_id, {}) for step_id in sorted_ids}
        # Persist with ownerless steps collapsed to `null` (no empty `{}`).
        section[list_key] = _collapse_ownerless_steps(sorted_map)
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {'phase': phase_section, 'step': step, list_key: sorted_map, 'count': len(sorted_map)}
        )

    elif args.verb == 'remove-step' and phase_section in LIST_STEP_PHASES:
        list_key = LIST_STEP_KEYS[phase_section]
        step = args.step
        existing = _steps_map(section.get(list_key))
        if step not in existing:
            return error_exit(f"Step '{step}' not found in {phase_section}")

        del existing[step]
        # Persist with ownerless steps collapsed to `null` (no empty `{}`).
        section[list_key] = _collapse_ownerless_steps(existing)
        plan_config[phase_section] = section
        config['plan'] = plan_config
        save_config(config)
        return success_exit(
            {'phase': phase_section, 'step': step, list_key: existing, 'count': len(existing)}
        )

    elif args.verb == 'remove-field':
        # Delete an arbitrary scalar/list key from the persisted phase section.
        # Operates on the on-disk section only (NOT the defaults-merged view), so
        # removing a key the defaults still seed re-exposes the default value on
        # the next read — the verb removes an explicit override, it cannot
        # suppress a default. The legacy `plan.phase-5-execute.steps` key (which
        # has no default) is removed cleanly. Removing an absent key is an error
        # so callers get an explicit signal rather than a silent no-op.
        field = args.field
        persisted = plan_config.get(phase_section, {})
        if field not in persisted:
            return error_exit(f"Field '{field}' not present in {phase_section}")
        del persisted[field]
        plan_config[phase_section] = persisted
        config['plan'] = plan_config
        save_config(config)
        return success_exit({'phase': phase_section, 'field': field, 'removed': True})

    return error_exit('Unknown phase verb')
