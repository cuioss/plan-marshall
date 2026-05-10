"""
Models command handler for manage-config.

Handles:
    models read --role <name>          (read-only resolver)
    models apply-preset --preset <name> (complete-overwrite writer)

The read path walks the documented resolution order:
    models.roles.<role> -> models.default -> inherit
Validates the resolved value against the allowed-levels enum from
`plan-marshall:plan-marshall/standards/model-levels.md`. Hard-errors on
invalid level values; warns (not errors) on unknown role names so the
registry can rename without breaking saved configs.

The write path imports :class:`ModelPresets` from the
``plan-marshall:plan-marshall`` skill (cross-skill import works because the
executor adds every skill's ``scripts/`` directory to ``PYTHONPATH``).
``apply-preset`` *completely overwrites* the ``models`` block — any keys not
present in the preset are discarded. This is the user-mandated semantic;
merging would defeat the purpose of preset selection.
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


def cmd_models_apply_preset(args) -> dict:
    """Handle `models apply-preset --preset <name>` subcommand.

    Completely overwrites ``config["models"]`` with the named preset
    payload — any keys not present in the preset are discarded.

    Resolution flow:

    1. ``ModelPresets.get(args.preset)`` returns a deep copy of the
       preset payload. The lookup is case-insensitive and accepts the
       underscore variant (``HIGH_END`` / ``high_end``). The argparse
       layer pre-validates ``--preset`` through a ``type=`` callable
       that delegates to :meth:`ModelPresets.get`, so unknown names are
       rejected at parse time with an ``ArgumentTypeError`` (exit code
       2) before the handler runs. The ``ValueError`` branch below is
       therefore a defense-in-depth path for programmatic callers (e.g.
       direct ``cmd_models_apply_preset(Namespace(...))`` invocations
       from tests).
    2. Defense-in-depth: re-validate every level value through
       :func:`_validate_level`. Preset values were validated at
       constant-class construction (``_validate_preset`` in
       ``model_presets.py``), but re-validating at write time catches
       any future drift between ``ALLOWED_LEVELS`` here and the copy in
       ``model_presets.py``.
    3. Load ``marshal.json`` via :func:`load_config`, replace
       ``config["models"]`` wholesale with the preset dict, and save
       via :func:`save_config`.
    4. Return TOON success payload so the wizard can confirm
       "Saved: applied preset '<name>'".
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    try:
        preset = ModelPresets.get(args.preset)
    except ValueError as exc:
        return error_exit(str(exc))

    # Defense-in-depth re-validation. Preset values were validated at
    # constant-class construction time; re-running here protects against
    # future drift between ALLOWED_LEVELS in this module and in
    # model_presets.py.
    default_level = preset.get('default')
    if not isinstance(default_level, str):
        return error_exit(
            f"preset '{args.preset}' missing required string 'default' level"
        )
    ok, err = _validate_level(default_level, 'preset.default')
    if not ok:
        return error_exit(err or 'invalid level')

    roles = preset.get('roles', {})
    if not isinstance(roles, dict):
        return error_exit(
            f"preset '{args.preset}' 'roles' must be a dict; "
            f'got {type(roles).__name__}'
        )
    for role_name, level in roles.items():
        if not isinstance(level, str):
            return error_exit(
                f"preset '{args.preset}' role '{role_name}' level must be a "
                f'string; got {type(level).__name__}'
            )
        ok, err = _validate_level(level, f'preset.roles.{role_name}')
        if not ok:
            return error_exit(err or 'invalid level')

    config = load_config()
    # User-mandated "completely overwritten" semantic: drop any existing
    # models block entirely and replace with the preset payload.
    config['models'] = preset
    save_config(config)

    return success_exit(
        {
            'preset': args.preset,
            'default': default_level,
            'roles_count': len(roles),
        }
    )
