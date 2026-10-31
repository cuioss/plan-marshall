# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Interaction-mode command handler for manage-config.

Handles the top-level ``interaction_mode`` scalar preference::

    interaction-mode get --field interaction_mode
    interaction-mode set --field interaction_mode --value advanced

The preference is a top-level scalar sibling of ``plan``, ``project``, and
``orchestrator`` in marshal.json (default ``advanced``; allowed
``basic|advanced|expert``). Every read applies the same fallback and validation
(an absent key falls back to the default; a present-but-invalid value fails
closed), and every write routes the
field through :func:`_config_core.reject_unknown_provisioning_field` and the
value through :func:`_config_defaults.validate_interaction_mode` before
:func:`_config_core.save_config`, so a typo'd field or an out-of-schema value
returns ``status: error`` instead of persisting silently to ``marshal.json``
where no reader would ever consult it.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    reject_unknown_provisioning_field,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_INTERACTION_MODE, validate_interaction_mode
from command_forms import STEWARD_COMMAND

# The interaction-mode noun's known fields — the fail-closed whitelist
# consulted by every read/write. The noun owns exactly one field, the top-level
# scalar itself, so the set is a singleton by design, not by omission.
INTERACTION_MODE_FIELDS: tuple[str, ...] = ('interaction_mode',)


def cmd_interaction_mode_get(args) -> dict:
    """Handle ``interaction-mode get --field interaction_mode``.

    Returns the stored value when the key is set; when it is absent, returns
    the canonical default (``advanced``). The accompanying ``set`` flag
    distinguishes a configured value from an unset one.
    """
    if not is_initialized():
        return error_exit(f'marshal.json not initialized; run {STEWARD_COMMAND} first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')

    rejection = reject_unknown_provisioning_field(field, INTERACTION_MODE_FIELDS, 'interaction-mode')
    if rejection is not None:
        return rejection

    try:
        config = load_config()
    except ValueError as e:
        return error_exit(str(e), error_type='invalid_config')
    if field in config:
        is_set = True
        value = config[field]
        try:
            validate_interaction_mode(value)
        except ValueError as e:
            return error_exit(str(e), error_type='invalid_value')
    else:
        is_set = False
        value = DEFAULT_INTERACTION_MODE

    return success_exit({'field': field, 'value': value, 'set': is_set})


def cmd_interaction_mode_set(args) -> dict:
    """Handle ``interaction-mode set --field interaction_mode --value <mode>``.

    Rejects an unknown field against the whitelist, then validates the value
    against the allowed mode set before persisting it as the top-level scalar.
    """
    if not is_initialized():
        return error_exit(f'marshal.json not initialized; run {STEWARD_COMMAND} first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')
    raw_value = getattr(args, 'value', None)
    if raw_value is None:
        return error_exit('--value is required')

    rejection = reject_unknown_provisioning_field(field, INTERACTION_MODE_FIELDS, 'interaction-mode')
    if rejection is not None:
        return rejection

    try:
        validate_interaction_mode(raw_value)
    except ValueError as e:
        return error_exit(str(e), error_type='invalid_value')

    try:
        config = load_config()
    except ValueError as e:
        return error_exit(str(e), error_type='invalid_config')
    config[field] = raw_value
    save_config(config)

    return success_exit({'field': field, 'value': raw_value, 'target': f'{field}'})
