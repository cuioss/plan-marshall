"""
Models command handler for manage-config.

Handles:
    models read --role <name>           (role-based level resolver)
    models read --role <group>.<sub>    (dotted-key resolver for nested groups)
    models read --phase <g> --role <s>  (two-flag form, equivalent to dotted)
    models read --phase <g>             (bare-group lookup, polymorphic)
    models read --default               (raw models.default lookup)
    models resolve-target --role <name> (target variant name resolver)
    models apply-preset --preset <name> (complete-overwrite writer)

The read path walks the hierarchical JSON per ``model-roles.md`` § Resolver:

    models.roles.<group>.<subkey> -> models.roles.<group>.default
                                  -> models.default
                                  -> inherit

Polymorphic value normalisation:
    - String at ``<group>``  -> single-level shorthand; any sub-key lookup
                                on a flat group resolves to the same string.
    - Object at ``<group>`` -> per-workflow group. The optional ``default``
                                slot serves as the in-group fallback for a
                                bare-group lookup or an unmatched sub-key.

The ``resolve-target`` subcommand collapses the per-dispatch-site recipe
``level = ...; target = canonical if level=="inherit" else canonical-{level}``
into one helper call, returning ``execution-context-{level}`` directly.

The write path imports :class:`ModelPresets` from the
``plan-marshall:plan-marshall`` skill. ``apply-preset`` *completely
overwrites* the ``models`` block.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from model_presets import ModelPresets  # type: ignore[import-not-found]

# Allowed-levels enum, kept in lock-step with model-levels.md.
ALLOWED_LEVELS = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'max', 'inherit')

# No levels are currently reserved. `max` was promoted from reserved-future to
# live (resolves to opus, xhigh — Opus-4.7-only). Future palette expansion may
# repopulate this tuple.
RESERVED_LEVELS: tuple[str, ...] = ()

# The role registry, kept in lock-step with model-roles.md.
#
# Structure: dict[group, tuple[str, ...]]. Every group is polymorphic — its
# stored value may be a string (single-level shorthand for the whole phase)
# or an object whose recognised sub-keys are the tuple below. ``default`` is
# the in-group fallback used when a sub-key lookup misses or the lookup is
# bare-group.
#
# Lookup forms accepted by the resolver:
#   --role <group>                  (bare group; walks to <group>.default)
#   --role <group>.<subkey>         (dotted form)
#   --phase <group> --role <subkey> (two-flag form, equivalent to dotted)
#   --phase <group>                 (two-flag bare group; same as --role <group>)
KNOWN_ROLES: dict[str, tuple[str, ...]] = {
    'phase-1': ('default', 'research'),
    'phase-2': ('default', 'research'),
    'phase-3': ('default', 'research'),
    'phase-4': ('default', 'research'),
    'phase-5': ('default', 'verification-feedback', 'research'),
    'phase-6': ('default', 'verification-feedback', 'post-run-review', 'research'),
}

# Legacy role keys retired by the phase-scoped resolver rewrite. Reads that
# target these keys return ``status: error`` with the per-key remediation
# below. Plan-marshall is pre-1.0; we error rather than alias-and-warn so
# stale dispatch sites and stale marshal.json entries surface immediately.
LEGACY_REMEDIATION: dict[tuple[str, str], str] = {
    ('cross', 'research'): (
        "use --phase <caller-phase> --role research (or --default for "
        "standalone /research outside any plan)"
    ),
    ('cross', 'triage'): (
        "use --phase <caller-phase> --role verification-feedback "
        "(producer in {build-runner, sonar, pr-comment, plugin-doctor, pr-state})"
    ),
    ('cross', 'q-gate-validation'): (
        "use --phase <caller-phase> (no --role; q-gate-validation tracks "
        "the calling phase's default)"
    ),
    ('cross', 'plugin-doctor'): (
        "use --phase phase-6 --role verification-feedback "
        "(with producer=plugin-doctor)"
    ),
    ('cross', 'manage-architecture-enrich-module'): (
        "use --phase phase-6 (no --role; tracks phase-6.default)"
    ),
    ('phase-6', 'create-pr'): (
        "use --phase phase-6 (no --role; create-pr tracks phase-6.default)"
    ),
    ('phase-6', 'pre-submission-self-review'): (
        "use --phase phase-6 (no --role; pre-submission-self-review tracks "
        "phase-6.default)"
    ),
    ('phase-6', 'lessons-capture'): (
        "use --phase phase-6 --role post-run-review "
        "(lessons-capture folded into post-run-review)"
    ),
    ('phase-6', 'retrospective'): (
        "use --phase phase-6 --role post-run-review "
        "(retrospective folded into post-run-review)"
    ),
    ('phase-6', 'pr-doctor'): (
        "use --phase phase-6 --role verification-feedback "
        "(with producer=pr-state)"
    ),
}


def _validate_level(value: str, source: str) -> tuple[bool, str | None]:
    """Validate a level keyword.

    Args:
        value: The level keyword to validate.
        source: Human-readable description of where the value came from
            (e.g. 'models.roles.phase-6.verification-feedback' or
            'models.default') — included verbatim in error messages for
            diagnosability.

    Returns:
        (True, None) when valid; (False, error_message) when invalid.
    """
    if value in ALLOWED_LEVELS:
        return True, None
    if value in RESERVED_LEVELS:
        return (
            False,
            f"level '{value}' at {source} is reserved (future-additive); "
            f"use 'max' for the current top tier",
        )
    return (
        False,
        f"invalid level '{value}' at {source}; expected one of {list(ALLOWED_LEVELS)}",
    )


def _split_role(args) -> tuple[str | None, str | None, str | None]:
    """Resolve the requested (group, subkey) from argparse Namespace.

    Returns:
        (group, subkey, error). ``group`` and ``subkey`` are None when an
        error is set. ``subkey`` is None when the caller asked for a bare
        group (legitimate for every group — bare-group resolves via the
        group's ``default`` slot or the global ``models.default``).

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


def _resolve_level(roles: dict, default_level: str | None, group: str, subkey: str | None) -> tuple[str, str, str | None]:
    """Walk the hierarchical roles JSON to a single level keyword.

    Returns:
        (level, source, error). When ``error`` is set, ``level`` and
        ``source`` are empty strings.

    Resolution order:
        1. group must be in :data:`KNOWN_ROLES`.
        2. subkey (if supplied) must be in the group's schema. Unknown
           sub-keys error.
        3. If ``models.roles.<group>`` is a **string**, the value is the
           level (sub-key is informational).
        4. If ``models.roles.<group>`` is an **object**:
           - Sub-key supplied AND present -> that value.
           - Sub-key supplied but absent  -> walk to the ``default`` slot.
           - Sub-key absent (bare group)  -> walk to the ``default`` slot.
           - No ``default`` slot          -> fall through to global default.
        5. ``models.default`` -> fall through when nothing matched above.
        6. ``inherit`` -> implicit final fallback.
    """
    if group not in KNOWN_ROLES:
        return '', '', f"role group '{group}' is not registered in model-roles.md"

    group_schema = KNOWN_ROLES[group]
    if subkey is not None and subkey not in group_schema:
        return (
            '',
            '',
            f"subkey '{subkey}' is not registered under group "
            f"'{group}' in model-roles.md (valid: {list(group_schema)})",
        )

    group_value = roles.get(group)

    # Case 1: group present, scalar at group (single-level shorthand).
    if isinstance(group_value, str):
        return group_value, f'models.roles.{group}', None

    # Case 2: group present, object at group.
    if isinstance(group_value, dict):
        if subkey is not None:
            sub_value = group_value.get(subkey)
            if isinstance(sub_value, str):
                return sub_value, f'models.roles.{group}.{subkey}', None
            # Sub-key missing from the object — walk to ``default`` slot.

        default_slot = group_value.get('default')
        if isinstance(default_slot, str):
            return default_slot, f'models.roles.{group}.default', None
        # No ``default`` slot — fall through to global default below.

    # Case 3: group absent OR object missing both subkey + default -> global default.
    if default_level is not None:
        return default_level, 'models.default', None

    # Case 4: no default set anywhere.
    return 'inherit', 'implicit_default', None


def _compute_target(level: str) -> str:
    """Compute the dispatched-variant target name from a resolved level."""
    if level == 'inherit' or not level:
        return 'execution-context'
    return f'execution-context-{level}'


def cmd_models(args) -> dict:
    """Handle ``models read`` subcommand (role lookup or --default fetch)."""
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    config = load_config()
    models_block = config.get('models', {})

    # Note: when the `models` block is absent entirely, `roles` and `default`
    # are absent too; the resolver returns `inherit` (the documented implicit
    # fallback), preserving "behaviour unchanged when models block absent".
    roles = models_block.get('roles', {})
    default_level = models_block.get('default')

    # --default short-circuit: return models.default directly (no role lookup).
    if getattr(args, 'default', False):
        if default_level is None:
            return success_exit(
                {
                    'level': 'inherit',
                    'source': 'implicit_default',
                }
            )
        ok, err = _validate_level(default_level, 'models.default')
        if not ok:
            return error_exit(err or 'invalid level')
        return success_exit(
            {
                'level': default_level,
                'source': 'models.default',
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

    # Validate the default value (if present) once so callers see invalid
    # defaults via a clear message even when the role itself has a value.
    if default_level is not None:
        ok, default_err = _validate_level(default_level, 'models.default')
        if not ok:
            return error_exit(default_err or 'invalid level')

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
            f"role '{warning_role}' is not registered in model-roles.md; "
            f'resolving to default/inherit. Update marshal.json or model-roles.md.'
        )
        if default_level is not None:
            level = default_level
            source = 'models.default'
        else:
            level = 'inherit'
            source = 'implicit_default'
    else:
        level, source, err = _resolve_level(roles, default_level, group, subkey)
        if err is not None:
            return error_exit(err)

    # Final validation: the resolved value must be a valid level.
    if level != 'inherit':
        ok, validation_err = _validate_level(level, source)
        if not ok:
            return error_exit(validation_err or 'invalid level')

    payload: dict = {
        'role': f'{group}.{subkey}' if subkey is not None else group,
        'level': level,
        'source': source,
    }
    if warnings:
        payload['warnings'] = warnings

    return success_exit(payload)


def cmd_models_resolve_target(args) -> dict:
    """Handle ``models resolve-target --role <name>`` subcommand.

    Resolves the role to a level, then computes the target variant name
    ``execution-context-{level}`` (or the canonical ``execution-context``
    when the level is ``inherit``). Collapses the per-dispatch-site
    "level -> target name" recipe into one call.
    """
    read_result = cmd_models(args)
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


def _expand_roles(preset_roles: dict, default_level: str) -> dict:
    """Expand a preset's per-role overrides into a fully-qualified roles map.

    For every entry in KNOWN_ROLES, produce a nested dict whose keys are the
    group's schema sub-keys. Each value is the preset's override when
    present, otherwise the preset's ``default``.

    The function rejects any role override in ``preset_roles`` whose key
    is not registered (defence-in-depth — model_presets does not import
    KNOWN_ROLES to keep the dependency graph one-way).
    """
    expanded: dict = {}
    for group, schema in KNOWN_ROLES.items():
        preset_group = preset_roles.get(group)
        sub_dict: dict = {}
        if isinstance(preset_group, dict):
            for subkey in schema:
                sub_value = preset_group.get(subkey, default_level)
                sub_dict[subkey] = (
                    sub_value if isinstance(sub_value, str) else default_level
                )
        elif isinstance(preset_group, str):
            # Preset wrote a string at the group: apply it to every sub-key
            # (degraded interpretation — shorthand for "set every workflow
            # under this phase to this level").
            for subkey in schema:
                sub_dict[subkey] = preset_group
        else:
            # Preset did not declare the group: fill with the global default.
            for subkey in schema:
                sub_dict[subkey] = default_level
        expanded[group] = sub_dict
    return expanded


def _count_overrides(expanded_roles: dict, default_level: str) -> int:
    """Count role entries whose level differs from ``default_level``.

    Walks both flat and nested groups (post-rewrite every group is nested,
    but the function tolerates both shapes for forward compatibility). A
    role written at the same level as ``default`` is functionally
    equivalent to inheriting the default, so it does NOT inflate the
    override count.
    """
    count = 0
    for value in expanded_roles.values():
        if isinstance(value, str):
            if value != default_level:
                count += 1
        elif isinstance(value, dict):
            for sub_value in value.values():
                if isinstance(sub_value, str) and sub_value != default_level:
                    count += 1
    return count


def cmd_models_apply_preset(args) -> dict:
    """Handle ``models apply-preset --preset <name>`` subcommand.

    Completely overwrites ``config["models"]`` with the named preset
    payload expanded to the full KNOWN_ROLES registry.

    Resolution flow:

    1. ``ModelPresets.get(args.preset)`` returns a deep copy of the
       preset payload. The lookup is case-insensitive and accepts the
       underscore variant (``HIGH_END`` / ``high_end``).
    2. Defence-in-depth: re-validate every level value through
       :func:`_validate_level`.
    3. Expand the preset's per-role overrides through KNOWN_ROLES so
       every dispatch site is written explicitly to marshal.json.
    4. Load ``marshal.json``, replace ``config["models"]`` wholesale
       with the expanded payload, and save.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    try:
        preset = ModelPresets.get(args.preset)
    except ValueError as exc:
        return error_exit(str(exc))

    default_level = preset.get('default')
    if not isinstance(default_level, str):
        return error_exit(
            f"preset '{args.preset}' missing required string 'default' level"
        )
    ok, err = _validate_level(default_level, 'preset.default')
    if not ok:
        return error_exit(err or 'invalid level')

    preset_roles = preset.get('roles', {})
    if not isinstance(preset_roles, dict):
        return error_exit(
            f"preset '{args.preset}' 'roles' must be a dict; "
            f'got {type(preset_roles).__name__}'
        )

    # Validate every level value in the preset before expansion.
    for group, group_value in preset_roles.items():
        if isinstance(group_value, str):
            ok, err = _validate_level(group_value, f'preset.roles.{group}')
            if not ok:
                return error_exit(err or 'invalid level')
        elif isinstance(group_value, dict):
            for subkey, sub_value in group_value.items():
                if not isinstance(sub_value, str):
                    return error_exit(
                        f"preset '{args.preset}' role "
                        f"'{group}.{subkey}' level must be a string; "
                        f'got {type(sub_value).__name__}'
                    )
                ok, err = _validate_level(
                    sub_value, f'preset.roles.{group}.{subkey}'
                )
                if not ok:
                    return error_exit(err or 'invalid level')
        else:
            return error_exit(
                f"preset '{args.preset}' role '{group}' must be a string "
                f'or dict; got {type(group_value).__name__}'
            )

    expanded_roles = _expand_roles(preset_roles, default_level)
    overrides_count = _count_overrides(expanded_roles, default_level)

    config = load_config()
    # User-mandated "completely overwritten" semantic: drop any existing
    # models block entirely and replace with the expanded preset payload.
    config['models'] = {
        'default': default_level,
        'roles': expanded_roles,
    }
    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'default': default_level,
            'roles_count': sum(
                1 if isinstance(v, str) else len(v)
                for v in expanded_roles.values()
            ),
            'overrides_count': overrides_count,
        }
    )
