# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Effort command handler for manage-config.

Handles:
    effort read --role <name>           (role-based level resolver)
    effort read --role <group>.<sub>    (dotted-key resolver for nested groups)
    effort read --phase <g> --role <s>  (two-flag form, equivalent to dotted)
    effort read --phase <g>             (bare-group lookup, polymorphic)
    effort read --default               (raw `plan.effort` lookup)
    effort resolve-target --role <name> (target variant name resolver)
    effort apply-preset --preset <name> (whole-tree preset writer)
    effort set --scope <scope> --level <v> (surgical per-scope writer)

Storage layout — per-phase effort config lives **inside the matching
plan-phase entry** under the ``effort`` key, alongside the rest of the
phase's knobs. The plan-wide fallback is a single string at
``plan.effort``::

    plan.<phase>.effort.<subkey>  -> plan.<phase>.effort.default
                                  -> plan.<phase>.effort  (string shorthand)
                                  -> plan.effort           (plan-wide fallback)
                                  -> inherit

Polymorphic value normalisation:
    - String at ``plan.<phase>.effort``  -> single-level shorthand; any
                                            sub-key lookup on that phase
                                            resolves to the same string.
    - Object at ``plan.<phase>.effort`` -> per-workflow object. The optional
                                            ``default`` slot serves as the
                                            in-phase fallback for a bare
                                            lookup or an unmatched sub-key.

The ``resolve-target`` subcommand collapses the per-dispatch-site recipe
``level = ...; target = canonical if level=="inherit" else canonical-{level}``
into one helper call, returning ``execution-context-{level}`` directly.

The write path imports :class:`EffortPresets` from the
``plan-marshall:plan-marshall`` skill. ``apply-preset`` surgically merges
the per-phase ``effort`` attribute into each ``plan.<phase>`` entry and
sets ``plan.effort`` — other per-phase config knobs (steps,
max_iterations, etc.) are preserved.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from effort_presets import EffortPresets

# Allowed-effort-levels enum, kept in lock-step with effort-levels.md.
ALLOWED_LEVELS = (
    'level-1', 'level-2', 'level-3', 'level-4', 'level-5', 'level-6', 'level-7', 'inherit'
)

# No levels are currently reserved. `level-7` is the current top tier
# (resolves to fable, max — sits above Opus). Future palette expansion may
# repopulate this tuple.
RESERVED_LEVELS: tuple[str, ...] = ()

# The role registry, kept in lock-step with effort-roles.md.
#
# Structure: dict[group, tuple[str, ...]]. Every group is a phase whose
# config lives under ``plan.<phase>.effort``. The stored value may be a
# string (single-level shorthand for the whole phase) or an object whose
# recognised sub-keys are the tuple below. ``default`` is the in-phase
# fallback used when a sub-key lookup misses or the lookup is bare-phase.
#
# Lookup forms accepted by the resolver:
#   --role <group>                  (bare group; walks to <group>.default)
#   --role <group>.<subkey>         (dotted form)
#   --phase <group> --role <subkey> (two-flag form, equivalent to dotted)
#   --phase <group>                 (two-flag bare group; same as --role <group>)
KNOWN_ROLES: dict[str, tuple[str, ...]] = {
    'phase-2-refine':   ('default',),
    'phase-3-outline':  ('default',),
    'phase-4-plan':     ('default',),
    'phase-5-execute':  ('default', 'verification-feedback'),
    'phase-6-finalize': ('default', 'verification-feedback', 'post-run-review'),
}



def _validate_level(value: str, source: str) -> tuple[bool, str | None]:
    """Validate an effort level keyword.

    Args:
        value: The level keyword to validate.
        source: Human-readable description of where the value came from
            (e.g. 'plan.phase-6-finalize.effort.verification-feedback' or
            'plan.effort') — included verbatim in error messages for
            diagnosability.

    Returns:
        (True, None) when valid; (False, error_message) when invalid.
    """
    if value in ALLOWED_LEVELS:
        return True, None
    if value in RESERVED_LEVELS:
        return (
            False,
            f"effort '{value}' at {source} is reserved (future-additive); "
            f"use 'level-7' for the current top tier",
        )
    return (
        False,
        f"invalid effort '{value}' at {source}; expected one of {list(ALLOWED_LEVELS)}",
    )


def _split_role(args) -> tuple[str | None, str | None, str | None]:
    """Resolve the requested (group, subkey) from argparse Namespace.

    Returns:
        (group, subkey, error). ``group`` and ``subkey`` are None when an
        error is set. ``subkey`` is None when the caller asked for a bare
        group (legitimate for every group — bare-group resolves via the
        group's ``default`` slot or the ``plan.effort`` plan-wide fallback).

    Supports four input shapes:
        --role <group>             -> (group, None, None)
        --role <group>.<subkey>    -> (group, subkey, None)
        --phase <g> --role <s>     -> (g, s, None)
        --phase <g>                -> (g, None, None)
    """
    phase = getattr(args, 'phase', None)
    role = getattr(args, 'role', None)
    if role is None and phase is None:
        return None, None, '--role (or --phase [--role]) is required'

    if phase is not None:
        # Two-flag form. `role` may be None (bare-group via --phase alone).
        if role is None:
            return phase, None, None
        if '.' in role:
            return (
                None,
                None,
                f"--role '{role}' must be a bare subkey when used with "
                f'--phase; do not include the group prefix',
            )
        return phase, role, None

    # Single-flag form. Detect dotted vs bare. (Reaching here implies
    # `phase is None` AND `role is not None` per the early-return guards
    # above; the assertion narrows the type for mypy.)
    assert role is not None
    if '.' in role:
        parts = role.split('.', 1)
        return parts[0], parts[1], None
    return role, None, None


def _resolve_level(
    plan_block: dict,
    default_level: str | None,
    group: str,
    subkey: str | None,
) -> tuple[str, str, str | None]:
    """Walk the per-phase ``effort`` config to a single level keyword.

    Returns:
        (level, source, error). When ``error`` is set, ``level`` and
        ``source`` are empty strings.

    Resolution order:
        1. group must be in :data:`KNOWN_ROLES`.
        2. subkey (if supplied) must be in the group's schema. Unknown
           sub-keys error.
        3. If ``plan.<group>.effort`` is a **string**, the value is the
           level (sub-key is informational).
        4. If ``plan.<group>.effort`` is an **object**:
           - Sub-key supplied AND present -> that value.
           - Sub-key supplied but absent  -> walk to the ``default`` slot.
           - Sub-key absent (bare group)  -> walk to the ``default`` slot.
           - No ``default`` slot          -> fall through to ``plan.effort``.
        5. ``plan.effort`` -> fall through when nothing matched above.
        6. ``inherit`` -> implicit final fallback.
    """
    if group not in KNOWN_ROLES:
        return '', '', f"role group '{group}' is not registered in effort-roles.md"

    group_schema = KNOWN_ROLES[group]
    if subkey is not None and subkey not in group_schema:
        return (
            '',
            '',
            f"subkey '{subkey}' is not registered under group "
            f"'{group}' in effort-roles.md (valid: {list(group_schema)})",
        )

    phase_entry = plan_block.get(group)
    group_value = None
    if isinstance(phase_entry, dict):
        group_value = phase_entry.get('effort')

    # Case 1: phase has an effort key, scalar value (single-level shorthand).
    if isinstance(group_value, str):
        return group_value, f'plan.{group}.effort', None

    # Case 2: phase has an effort key, object value.
    if isinstance(group_value, dict):
        if subkey is not None:
            sub_value = group_value.get(subkey)
            if isinstance(sub_value, str):
                return sub_value, f'plan.{group}.effort.{subkey}', None
            # Sub-key missing from the object — walk to ``default`` slot.

        default_slot = group_value.get('default')
        if isinstance(default_slot, str):
            return default_slot, f'plan.{group}.effort.default', None
        # No ``default`` slot — fall through to `plan.effort` below.

    # Case 3: phase absent OR effort absent OR object missing both subkey + default
    #         -> plan.effort.
    if default_level is not None:
        return default_level, 'plan.effort', None

    # Case 4: no plan.effort set.
    return 'inherit', 'implicit_default', None


def _compute_target(level: str) -> str:
    """Compute the dispatched-variant target name from a resolved level."""
    if level == 'inherit' or not level:
        return 'execution-context'
    return f'execution-context-{level}'


def cmd_effort(args) -> dict:
    """Handle ``effort read`` subcommand (role lookup or --default fetch)."""
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    config = load_config()
    plan_block = config.get('plan', {})
    # `plan.effort` is the plan-wide fallback (a single string); per-phase
    # overrides live at `plan.<phase>.effort`. Both keys are children of
    # the `plan` block, alongside the phase entries.
    default_level = plan_block.get('effort') if isinstance(plan_block, dict) else None

    # --default short-circuit: return plan.effort directly (no role lookup).
    if getattr(args, 'default', False):
        if default_level is None:
            return success_exit(
                {
                    'level': 'inherit',
                    'source': 'implicit_default',
                }
            )
        ok, err = _validate_level(default_level, 'plan.effort')
        if not ok:
            return error_exit(err or 'invalid effort')
        return success_exit(
            {
                'level': default_level,
                'source': 'plan.effort',
            }
        )

    group, subkey, err = _split_role(args)
    if err is not None:
        return error_exit(err)
    # When err is None, _split_role guarantees group is non-None.
    assert group is not None

    # Validate the plan-wide effort value (if present) once so callers see
    # invalid defaults via a clear message even when the role itself has a value.
    if default_level is not None:
        ok, default_err = _validate_level(default_level, 'plan.effort')
        if not ok:
            return error_exit(default_err or 'invalid effort')

    warnings: list[str] = []

    if group not in KNOWN_ROLES:
        # Unknown role group: warn but proceed with default/inherit. Registry
        # renames must not break saved configs; users see a clear warning so
        # they can update marshal.json when convenient.
        if subkey is not None:
            warning_role = f'{group}.{subkey}'
        else:
            warning_role = group
        warnings.append(
            f"role '{warning_role}' is not registered in effort-roles.md; "
            f'resolving to default/inherit. Update marshal.json or effort-roles.md.'
        )
        if default_level is not None:
            level = default_level
            source = 'plan.effort'
        else:
            level = 'inherit'
            source = 'implicit_default'
    else:
        level, source, err = _resolve_level(plan_block, default_level, group, subkey)
        if err is not None:
            return error_exit(err)

    # Final validation: the resolved value must be a valid effort level.
    if level != 'inherit':
        ok, validation_err = _validate_level(level, source)
        if not ok:
            return error_exit(validation_err or 'invalid effort')

    payload: dict = {
        'role': f'{group}.{subkey}' if subkey is not None else group,
        'level': level,
        'source': source,
    }
    if warnings:
        payload['warnings'] = warnings

    return success_exit(payload)


def cmd_effort_resolve_target(args) -> dict:
    """Handle ``effort resolve-target --role <name>`` subcommand.

    Resolves the role to an effort level, then computes the target variant
    name ``execution-context-{level}`` (or the canonical ``execution-context``
    when the level is ``inherit``). Collapses the per-dispatch-site
    "level -> target name" recipe into one call.
    """
    read_result = cmd_effort(args)
    if read_result.get('status') != 'success':
        return read_result

    level = read_result.get('level', 'inherit')
    target = _compute_target(level)

    payload: dict = {
        'role': read_result.get('role'),
        'level': level,
        'source': read_result.get('source'),
        'target': target,
    }
    if 'warnings' in read_result:
        payload['warnings'] = read_result['warnings']

    return success_exit(payload)


def _expand_phase_effort(
    preset_phase_value: object,
    schema: tuple[str, ...],
    default_level: str,
) -> str | dict[str, str]:
    """Expand a preset's per-phase value into the on-disk effort shape.

    Behaviour:
        - Preset wrote a string at the phase  -> emit the same string
          (single-level shorthand for the whole phase).
        - Preset wrote an object             -> emit a dict keyed by every
          sub-key in the phase's schema, with explicit overrides honoured
          and missing sub-keys filled with ``default_level``.
        - Preset omitted the phase           -> emit the global default as
          a single string (compact shorthand; identical to inheriting).
    """
    if isinstance(preset_phase_value, str):
        return preset_phase_value
    if isinstance(preset_phase_value, dict):
        expanded: dict[str, str] = {}
        for subkey in schema:
            value = preset_phase_value.get(subkey, default_level)
            expanded[subkey] = value if isinstance(value, str) else default_level
        return expanded
    # Preset did not declare the phase: shorthand-equivalent of "use default".
    return default_level


def _count_overrides(expanded: dict[str, object], default_level: str) -> int:
    """Count leaf-level effort values that differ from ``default_level``.

    Walks both string-valued phases and object-valued phases. A value
    written at the same level as the top-level default is functionally
    equivalent to inheriting, so it does NOT inflate the override count.
    """
    count = 0
    for value in expanded.values():
        if isinstance(value, str):
            if value != default_level:
                count += 1
        elif isinstance(value, dict):
            for sub_value in value.values():
                if isinstance(sub_value, str) and sub_value != default_level:
                    count += 1
    return count


def _count_roles(expanded: dict[str, object]) -> int:
    """Count leaf-level effort values across the expanded preset.

    A string-valued phase contributes 1; an object-valued phase contributes
    its sub-key count.
    """
    count = 0
    for value in expanded.values():
        if isinstance(value, str):
            count += 1
        elif isinstance(value, dict):
            count += len(value)
    return count


def cmd_effort_set(args) -> dict:
    """Handle ``effort set --scope <scope> --level <value>`` subcommand.

    Surgical per-scope writer — the write-path counterpart to the
    whole-tree :func:`cmd_effort_apply_preset`. Writes exactly one effort
    scope without disturbing siblings:

        - ``--scope {phase}.{role}`` (dotted nested scope, e.g.
          ``phase-6-finalize.verification-feedback``): validate ``phase``
          against :data:`KNOWN_ROLES` and ``role`` against that group's
          schema, validate ``--level`` via :func:`_validate_level`, then
          write ``config['plan'][phase]['effort'][role] = level`` —
          creating the ``plan.<phase>`` entry and its ``effort`` object as
          needed, and normalising a pre-existing **scalar** ``effort``
          string into an object (seeding the prior value into ``default``)
          so the per-scope write does not clobber sibling sub-keys.
        - ``--scope plan`` (the plan-wide scalar): write
          ``config['plan']['effort'] = level``.

    Unknown phase/role and invalid level are rejected with clear errors
    mirroring :func:`_resolve_level`'s messages.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    scope = getattr(args, 'scope', None)
    if not scope:
        return error_exit('--scope is required')
    level = getattr(args, 'level', None)
    if not level:
        return error_exit('--level is required')

    # Plan-wide scalar scope.
    if scope == 'plan':
        ok, err = _validate_level(level, 'plan.effort')
        if not ok:
            return error_exit(err or 'invalid effort')
        config = load_config()
        plan_block = config.setdefault('plan', {})
        if not isinstance(plan_block, dict):
            return error_exit("plan block in marshal.json is not a dictionary")
        plan_block['effort'] = level
        save_config(config)
        return success_exit(
            {
                'scope': 'plan',
                'level': level,
                'target': 'plan.effort',
            }
        )

    # Nested scope: {phase}.{role}.
    if '.' not in scope:
        return error_exit(
            f"scope '{scope}' must be 'plan' or a dotted '{{phase}}.{{role}}' scope "
            f'(e.g. phase-6-finalize.verification-feedback)'
        )
    phase, role = scope.split('.', 1)

    if phase not in KNOWN_ROLES:
        return error_exit(
            f"role group '{phase}' is not registered in effort-roles.md"
        )
    group_schema = KNOWN_ROLES[phase]
    if role not in group_schema:
        return error_exit(
            f"subkey '{role}' is not registered under group "
            f"'{phase}' in effort-roles.md (valid: {list(group_schema)})"
        )

    ok, err = _validate_level(level, f'plan.{phase}.effort.{role}')
    if not ok:
        return error_exit(err or 'invalid effort')

    config = load_config()
    plan_block = config.setdefault('plan', {})
    if not isinstance(plan_block, dict):
        return error_exit("plan block in marshal.json is not a dictionary")
    phase_entry = plan_block.setdefault(phase, {})
    if not isinstance(phase_entry, dict):
        return error_exit(
            f"plan['{phase}'] exists but is not a dict; "
            f'cannot merge effort attribute'
        )

    existing_effort = phase_entry.get('effort')
    if isinstance(existing_effort, dict):
        effort_obj = existing_effort
    elif isinstance(existing_effort, str):
        # Normalise the scalar shorthand into an object, preserving the
        # prior value's intent under the in-phase ``default`` slot so the
        # per-scope write does not silently drop it.
        effort_obj = {'default': existing_effort}
        phase_entry['effort'] = effort_obj
    else:
        effort_obj = {}
        phase_entry['effort'] = effort_obj

    effort_obj[role] = level
    save_config(config)

    return success_exit(
        {
            'scope': scope,
            'level': level,
            'target': f'plan.{phase}.effort.{role}',
        }
    )


def cmd_effort_apply_preset(args) -> dict:
    """Handle ``effort apply-preset --preset <name>`` subcommand.

    Surgically writes the preset payload into the per-phase storage shape:

        - ``config['plan']['effort']`` set to the preset's plan-wide
          default.
        - For each phase in :data:`KNOWN_ROLES`, set
          ``config['plan'][phase]['effort']`` to the preset's value for
          that phase (or the plan-wide default when omitted). Other
          per-phase config knobs (``steps``, ``max_iterations``,
          ``branch_strategy``, …) are preserved.
        - Any pre-existing top-level ``models`` block is removed
          (clean-slate cleanup of the previous storage layout).

    Resolution flow:

    1. ``EffortPresets.get(args.preset)`` returns a deep copy of the
       preset payload. The lookup is case-insensitive and accepts the
       underscore variant (``HIGH_END`` / ``high_end``).
    2. Defence-in-depth: re-validate every effort value through
       :func:`_validate_level`.
    3. Expand the preset's per-phase overrides through KNOWN_ROLES so
       every dispatch site is written explicitly to marshal.json.
    4. Load ``marshal.json``, merge the per-phase ``effort`` attributes
       into each ``plan.<phase>`` entry (creating the entry if absent),
       set the top-level ``effort`` string, and save.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    try:
        preset = EffortPresets.get(args.preset)
    except ValueError as exc:
        return error_exit(str(exc))

    default_level = preset.get('default')
    if not isinstance(default_level, str):
        return error_exit(
            f"preset '{args.preset}' missing required string 'default' effort"
        )
    ok, err = _validate_level(default_level, 'preset.default')
    if not ok:
        return error_exit(err or 'invalid effort')

    preset_roles = preset.get('roles', {})
    if not isinstance(preset_roles, dict):
        return error_exit(
            f"preset '{args.preset}' 'roles' must be a dict; "
            f'got {type(preset_roles).__name__}'
        )

    # Validate every effort value in the preset before expansion.
    for group, group_value in preset_roles.items():
        if isinstance(group_value, str):
            ok, err = _validate_level(group_value, f'preset.roles.{group}')
            if not ok:
                return error_exit(err or 'invalid effort')
        elif isinstance(group_value, dict):
            for subkey, sub_value in group_value.items():
                if not isinstance(sub_value, str):
                    return error_exit(
                        f"preset '{args.preset}' role "
                        f"'{group}.{subkey}' effort must be a string; "
                        f'got {type(sub_value).__name__}'
                    )
                ok, err = _validate_level(
                    sub_value, f'preset.roles.{group}.{subkey}'
                )
                if not ok:
                    return error_exit(err or 'invalid effort')
        else:
            return error_exit(
                f"preset '{args.preset}' role '{group}' must be a string "
                f'or dict; got {type(group_value).__name__}'
            )

    # Expand the preset into per-phase on-disk values keyed by phase.
    expanded: dict[str, object] = {}
    for phase, schema in KNOWN_ROLES.items():
        expanded[phase] = _expand_phase_effort(
            preset_roles.get(phase), schema, default_level
        )

    overrides_count = _count_overrides(expanded, default_level)
    roles_count = _count_roles(expanded)

    config = load_config()
    plan_block = config.setdefault('plan', {})
    # Set plan-wide effort fallback (string at plan.effort).
    plan_block['effort'] = default_level
    # Surgically write per-phase effort attributes. Preserve other phase knobs.
    for phase, phase_effort in expanded.items():
        phase_entry = plan_block.setdefault(phase, {})
        if not isinstance(phase_entry, dict):
            return error_exit(
                f"plan['{phase}'] exists but is not a dict; "
                f'cannot merge effort attribute'
            )
        phase_entry['effort'] = phase_effort
    # Defensive cleanup: remove stray top-level `models` / `effort` keys so
    # the writer's output is canonical regardless of what the caller's
    # marshal.json looked like before this call.
    config.pop('models', None)
    config.pop('effort', None)

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'default': default_level,
            'roles_count': roles_count,
            'overrides_count': overrides_count,
        }
    )
