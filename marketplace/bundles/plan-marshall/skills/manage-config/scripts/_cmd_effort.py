"""
Effort command handler for manage-config.

Handles:
    effort read --role <name>           (role-based level resolver)
    effort read --role <group>.<sub>    (dotted-key resolver for nested groups)
    effort read --phase <g> --role <s>  (two-flag form, equivalent to dotted)
    effort read --phase <g>             (bare-group lookup, polymorphic)
    effort read --default               (raw top-level effort lookup)
    effort resolve-target --role <name> (target variant name resolver)
    effort apply-preset --preset <name> (preset writer)

Storage layout — per-phase effort config lives **inside the matching
plan-phase entry** under the ``effort`` key. The top-level ``effort``
field is the plan-wide fallback (a single string)::

    plan.<phase>.effort.<subkey>  -> plan.<phase>.effort.default
                                  -> plan.<phase>.effort  (string shorthand)
                                  -> effort                (top-level fallback)
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
sets the top-level ``effort`` string — other per-phase config knobs
(steps, max_iterations, etc.) are preserved.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from effort_presets import EffortPresets  # type: ignore[import-not-found]

# Allowed-effort-levels enum, kept in lock-step with effort-levels.md.
ALLOWED_LEVELS = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max', 'inherit')

# No levels are currently reserved. `max` was promoted from reserved-future to
# live (resolves to opus, xhigh — Opus-4.7-only). Future palette expansion may
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
    'phase-1-init':     ('default',),
    'phase-2-refine':   ('default',),
    'phase-3-outline':  ('default',),
    'phase-4-plan':     ('default',),
    'phase-5-execute':  ('default', 'verification-feedback'),
    'phase-6-finalize': ('default', 'verification-feedback', 'post-run-review'),
}

# Legacy role keys retired by the phase-scoped resolver rewrite. Reads that
# target these keys return ``status: error`` with the per-key remediation
# below. Plan-marshall is pre-1.0; we error rather than alias-and-warn so
# stale dispatch sites and stale marshal.json entries surface immediately.
#
# The remediations point at the current registry shape (phase-N-{suffix}
# keys, no `research` sub-key — research dispatches resolve under the
# calling phase's default or via --default).
LEGACY_REMEDIATION: dict[tuple[str, str], str] = {
    ('cross', 'research'): (
        "use --phase <caller-phase-N-suffix> (no --role; research "
        "inherits the calling phase's default) or --default for "
        "standalone /research outside any plan"
    ),
    ('cross', 'triage'): (
        "use --phase <caller-phase-N-suffix> --role verification-feedback "
        "(producer in {build-runner, sonar, pr-comment, plugin-doctor, pr-state})"
    ),
    ('cross', 'q-gate-validation'): (
        "use --phase <caller-phase-N-suffix> (no --role; q-gate-validation "
        "tracks the calling phase's default)"
    ),
    ('cross', 'plugin-doctor'): (
        "use --phase phase-6-finalize --role verification-feedback "
        "(with producer=plugin-doctor)"
    ),
    ('cross', 'manage-architecture-enrich-module'): (
        "use --phase phase-6-finalize (no --role; tracks phase-6-finalize.default)"
    ),
    ('phase-6', 'create-pr'): (
        "use --phase phase-6-finalize (no --role; create-pr tracks "
        "phase-6-finalize.default)"
    ),
    ('phase-6', 'pre-submission-self-review'): (
        "use --phase phase-6-finalize (no --role; pre-submission-self-review "
        "tracks phase-6-finalize.default)"
    ),
    ('phase-6', 'lessons-capture'): (
        "use --phase phase-6-finalize --role post-run-review "
        "(lessons-capture folded into post-run-review)"
    ),
    ('phase-6', 'retrospective'): (
        "use --phase phase-6-finalize --role post-run-review "
        "(retrospective folded into post-run-review)"
    ),
    ('phase-6', 'pr-doctor'): (
        "use --phase phase-6-finalize --role verification-feedback "
        "(with producer=pr-state)"
    ),
}


def _validate_level(value: str, source: str) -> tuple[bool, str | None]:
    """Validate an effort level keyword.

    Args:
        value: The level keyword to validate.
        source: Human-readable description of where the value came from
            (e.g. 'plan.phase-6-finalize.effort.verification-feedback' or
            'effort') — included verbatim in error messages for
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
            f"use 'max' for the current top tier",
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
        group's ``default`` slot or the top-level ``effort`` fallback).

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
           - No ``default`` slot          -> fall through to top-level effort.
        5. top-level ``effort`` -> fall through when nothing matched above.
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
        # No ``default`` slot — fall through to top-level effort below.

    # Case 3: phase absent OR effort absent OR object missing both subkey + default
    #         -> top-level effort.
    if default_level is not None:
        return default_level, 'effort', None

    # Case 4: no top-level effort set.
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
    default_level = config.get('effort')

    # --default short-circuit: return top-level effort directly (no role lookup).
    if getattr(args, 'default', False):
        if default_level is None:
            return success_exit(
                {
                    'level': 'inherit',
                    'source': 'implicit_default',
                }
            )
        ok, err = _validate_level(default_level, 'effort')
        if not ok:
            return error_exit(err or 'invalid effort')
        return success_exit(
            {
                'level': default_level,
                'source': 'effort',
            }
        )

    group, subkey, err = _split_role(args)
    if err is not None:
        return error_exit(err)
    # When err is None, _split_role guarantees group is non-None.
    assert group is not None

    # Retired-key check: legacy `cross.*` and `phase-6.{retired}` reads
    # error with a remediation pointing to the new shape. Runs before the
    # unknown-group warning so `cross.*` does not silently fall back.
    if subkey is not None:
        remediation = LEGACY_REMEDIATION.get((group, subkey))
        if remediation is not None:
            return error_exit(
                f"role key '{group}.{subkey}' is retired; {remediation}"
            )

    # Validate the top-level effort value (if present) once so callers see
    # invalid defaults via a clear message even when the role itself has a value.
    if default_level is not None:
        ok, default_err = _validate_level(default_level, 'effort')
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
            source = 'effort'
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


def cmd_effort_apply_preset(args) -> dict:
    """Handle ``effort apply-preset --preset <name>`` subcommand.

    Surgically writes the preset payload into the per-phase storage shape:

        - ``config['effort']`` set to the preset's top-level default.
        - For each phase in :data:`KNOWN_ROLES`, set
          ``config['plan'][phase]['effort']`` to the preset's value for
          that phase (or the global default when omitted). Other per-phase
          config knobs (``steps``, ``max_iterations``, ``branch_strategy``,
          …) are preserved.
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
    # Set top-level effort fallback.
    config['effort'] = default_level
    # Surgically write per-phase effort attributes. Preserve other phase knobs.
    plan_block = config.setdefault('plan', {})
    for phase, phase_effort in expanded.items():
        phase_entry = plan_block.setdefault(phase, {})
        if not isinstance(phase_entry, dict):
            return error_exit(
                f"plan['{phase}'] exists but is not a dict; "
                f'cannot merge effort attribute'
            )
        phase_entry['effort'] = phase_effort
    # Clean up legacy top-level `models` block from the previous layout.
    config.pop('models', None)

    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'default': default_level,
            'roles_count': roles_count,
            'overrides_count': overrides_count,
        }
    )
