"""
Models command handler for manage-config.

Handles: models read --role <name>

Pure read-only resolver against the `models` block of `.plan/marshal.json`.
Walks the documented resolution order:
    models.roles.<role> -> models.default -> inherit
Validates the resolved value against the allowed-levels enum from
`plan-marshall:plan-marshall/standards/model-levels.md`. Hard-errors on
invalid level values; warns (not errors) on unknown role names so the
registry can rename without breaking saved configs.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    success_exit,
)

# Allowed-levels enum, kept in lock-step with model-levels.md.
ALLOWED_LEVELS = ('low', 'medium', 'high', 'xhigh', 'xxhigh', 'inherit')

# `max` is reserved as a future-additive level (see model-levels.md). It is
# recognised by the resolver only to produce a clear error message rather than
# falling through to the generic invalid-level branch.
RESERVED_LEVELS = ('max',)

# Effective + pending role keys, kept in lock-step with model-roles.md.
# Unknown roles produce a warning (not an error) so the resolver remains stable
# when the registry renames keys; the warning is surfaced in the `warnings`
# field of the success payload.
KNOWN_ROLES = (
    # effective
    'q_gate_validation',
    'research',
    'pr_creation',
    'automated_review',
    'sonar_roundtrip',
    'lessons_capture',
    'change_type_detection',
    'phase_init',
    'phase_plan',
    'component_analysis',
    'inventory_analysis',
    'tool_coverage_analysis',
    # pending
    'phase_refine',
    'phase_outline',
    'phase_execute',
    'phase_finalize',
    'retrospective',
    'implementation',
    'testing',
    'build_runner',
)


def _validate_level(value: str, source: str) -> tuple[bool, str | None]:
    """Validate a level keyword.

    Args:
        value: The level keyword to validate.
        source: Human-readable description of where the value came from
            (e.g. 'models.roles.q_gate_validation' or 'models.default') —
            included verbatim in error messages for diagnosability.

    Returns:
        (True, None) when valid; (False, error_message) when invalid.
    """
    if value in ALLOWED_LEVELS:
        return True, None
    if value in RESERVED_LEVELS:
        return (
            False,
            f"level '{value}' at {source} is reserved (future-additive); "
            f"use 'xxhigh' for the current top tier",
        )
    return (
        False,
        f"invalid level '{value}' at {source}; expected one of {list(ALLOWED_LEVELS)}",
    )


def cmd_models(args) -> dict:
    """Handle `models read --role <name>` subcommand."""
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    config = load_config()
    models_block = config.get('models', {})

    # Note: when the `models` block is absent entirely, `roles` and `default`
    # are absent too; the resolver returns `inherit` (the documented implicit
    # fallback), preserving "behaviour unchanged when models block absent".
    roles = models_block.get('roles', {})
    default_level = models_block.get('default')

    role = args.role
    warnings: list[str] = []

    if role not in KNOWN_ROLES:
        # Unknown role: warn but proceed with `inherit`. Registry renames must
        # not break saved configs; users will see a clear warning so they can
        # update the config when convenient.
        warnings.append(
            f"role '{role}' is not registered in model-roles.md; "
            f"resolving to default/inherit. Update marshal.json or model-roles.md."
        )
        # Skip role lookup entirely for unknown roles.
        role_value = None
    else:
        role_value = roles.get(role)

    # Resolution order: models.roles.<role> -> models.default -> inherit.
    if role_value is not None:
        ok, err = _validate_level(role_value, f"models.roles.{role}")
        if not ok:
            return error_exit(err or 'invalid level')
        resolved_level = role_value
        resolution_source = f'models.roles.{role}'
    elif default_level is not None:
        ok, err = _validate_level(default_level, 'models.default')
        if not ok:
            return error_exit(err or 'invalid level')
        resolved_level = default_level
        resolution_source = 'models.default'
    else:
        resolved_level = 'inherit'
        resolution_source = 'implicit_default'

    payload: dict = {
        'role': role,
        'level': resolved_level,
        'source': resolution_source,
    }
    if warnings:
        payload['warnings'] = warnings

    return success_exit(payload)
