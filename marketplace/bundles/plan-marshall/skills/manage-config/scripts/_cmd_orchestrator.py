# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Orchestrator scalar-knob command handler for manage-config.

Handles the non-effort scalar knobs of the top-level ``orchestrator`` block::

    orchestrator get --field parallelization_scope
    orchestrator set --field parallelization_scope --value N

The effort knobs (``orchestrator.effort.*``) are NOT handled here — they live in
the effort resolver (``_cmd_effort.py``: ``effort read``/``resolve-target --role
orchestrator.{surface}`` and ``effort set --scope orchestrator[.{surface}|.max]``).
This handler owns only the scalar provisioning fields.

Every scalar write routes through
:func:`_config_core.reject_unknown_provisioning_field` against the orchestrator
block's known-field whitelist (:data:`ORCHESTRATOR_SCALAR_FIELDS`), so a typo'd
or retired field fails closed (``status: error``) instead of persisting silently
to ``marshal.json`` where no reader would consult it.

Known scalar fields:
    ``parallelization_scope``  int >= 1  — project default that pre-fills the
        per-epic parallelization-scope ask in ``marshall-orchestrator`` init.
    ``auto_emit``  bool  — the orchestrator-tier autonomy knob (default False);
        when true the epic orchestrator auto-fills the emit queue on landing.

Both scalar knobs read/write through this same verb against the shared
whitelist — no schema rework as the block grows.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    reject_unknown_provisioning_field,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_ORCHESTRATOR

# The orchestrator block's known scalar (non-effort) fields — the fail-closed
# whitelist consulted by every scalar read/write.
ORCHESTRATOR_SCALAR_FIELDS: tuple[str, ...] = ('parallelization_scope', 'auto_emit')


def _validate_parallelization_scope(value: object) -> tuple[bool, str | None]:
    """Validate ``parallelization_scope`` as an int >= 1.

    ``bool`` is explicitly rejected even though ``bool`` is an ``int`` subclass —
    ``True``/``False`` are never a valid scope count.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return False, 'parallelization_scope must be an integer >= 1'
    if value < 1:
        return False, 'parallelization_scope must be an integer >= 1'
    return True, None


def _coerce_bool(raw_value: object) -> bool | None:
    """Coerce a CLI value into a bool, or ``None`` when it is not boolean-shaped.

    Accepts an actual ``bool`` and the case-insensitive strings ``true``/``false``
    (and their ``1``/``0`` synonyms), mirroring how the plan-tier autonomy knobs
    round-trip ``true``/``false`` from the CLI. Any other value yields ``None`` so
    the caller can fail closed.
    """
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in ('true', '1', 'yes'):
            return True
        if lowered in ('false', '0', 'no'):
            return False
    return None


def cmd_orchestrator_get(args) -> dict:
    """Handle ``orchestrator get --field <field>``.

    Returns the stored value (or ``None`` when the field is unset), plus a
    ``set`` flag distinguishing a configured value from an unset one so callers
    (e.g. the per-epic ask pre-fill) can fall back to their own default.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')

    rejection = reject_unknown_provisioning_field(
        field, ORCHESTRATOR_SCALAR_FIELDS, 'orchestrator'
    )
    if rejection is not None:
        return rejection

    config = load_config()
    orch_block = config.get('orchestrator')
    # When the field is unset in the live block, fall back to the canonical
    # default (so `auto_emit` reads its seeded `False`); `parallelization_scope`
    # carries no seeded default, so its fallback is `None` and callers key off
    # `set` to apply their own default.
    if isinstance(orch_block, dict) and field in orch_block:
        is_set = True
        value = orch_block[field]
    else:
        is_set = False
        value = DEFAULT_ORCHESTRATOR.get(field)

    return success_exit({'field': field, 'value': value, 'set': is_set})


def cmd_orchestrator_set(args) -> dict:
    """Handle ``orchestrator set --field <field> --value <value>``.

    Rejects an unknown field against the whitelist, then coerces/validates the
    value per-field before persisting it into ``config['orchestrator']``.
    """
    if not is_initialized():
        return error_exit('marshal.json not initialized; run /marshall-steward first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')
    raw_value = getattr(args, 'value', None)
    if raw_value is None:
        return error_exit('--value is required')

    rejection = reject_unknown_provisioning_field(
        field, ORCHESTRATOR_SCALAR_FIELDS, 'orchestrator'
    )
    if rejection is not None:
        return rejection

    # Field-specific coercion + validation.
    coerced: object
    if field == 'parallelization_scope':
        try:
            coerced = int(raw_value)
        except (TypeError, ValueError):
            return error_exit('parallelization_scope must be an integer >= 1')
        ok, err = _validate_parallelization_scope(coerced)
        if not ok:
            return error_exit(err or 'invalid parallelization_scope')
    elif field == 'auto_emit':
        coerced = _coerce_bool(raw_value)
        if coerced is None:
            return error_exit('auto_emit must be a boolean (true/false)')
    else:
        # Unreachable while the whitelist is fully enumerated above; the branch
        # keeps the coercion contract explicit as further fields are added.
        coerced = raw_value

    config = load_config()
    orch_block = config.setdefault('orchestrator', {})
    if not isinstance(orch_block, dict):
        return error_exit('orchestrator block in marshal.json is not a dictionary')
    orch_block[field] = coerced
    save_config(config)

    return success_exit(
        {'field': field, 'value': coerced, 'target': f'orchestrator.{field}'}
    )
