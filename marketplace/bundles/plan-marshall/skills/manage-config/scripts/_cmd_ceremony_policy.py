"""Ceremony-policy command handler for manage-config.

Handles:
    ceremony-policy get [--field <dotted.path>]            (runtime read surface)
    ceremony-policy set  --field <dotted.path> --value V   (operator write surface)

The ``ceremony_policy`` block is a top-level marshal.json section (sibling to
``plan`` / ``ci`` / ``project``) carrying two orthogonal axes plus an overrides
list — see :data:`_config_defaults.DEFAULT_CEREMONY_POLICY`. This module is the
read surface every runtime orchestrator consumes for the three automation knobs
(``automation.finalize_without_asking``, ``automation.loop_back_without_asking``,
``automation.auto_merge_after_ci``) and the run-at-all gates
(``planning.<gate>`` / ``finalize.<gate>``), mirroring the TOON shape the
``plan phase-X get --field`` verb returns.

Resolution merges :data:`_config_defaults.DEFAULT_CEREMONY_POLICY` under the live
``config['ceremony_policy']`` block (live values win, missing keys fall back to
the canonical default) so a fresh marshal.json that predates the block still
reads the canonical values. ``overrides[]`` is plan-fact-scoped and consumed by
the manifest composer with plan facts — a plain ``get`` returns the base section
value, never an override-resolved value.

``set`` writes a single dotted ``section.field`` path into the live block. It
coerces ``true``/``false``/digit values (matching the other config setters),
validates the resulting block via :func:`validate_ceremony_policy`, and — for a
run-at-all gate set to ``never`` — emits the set-time footgun ``[WARNING]`` via
:func:`ceremony_set_footgun_warnings` so the operator owns the risk knowingly.
Only the two-segment ``section.field`` shape is accepted (the automation knobs
and the per-section gates); writing a whole sub-block or ``overrides`` is out of
scope for the scalar setter.
"""

import copy
from typing import Any

from _config_core import (
    MarshalNotInitializedError,
    _coerce_value,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_CEREMONY_POLICY, validate_ceremony_policy


def _merged_ceremony_policy(config: dict) -> dict:
    """Return ``ceremony_policy`` with canonical defaults merged under live values.

    Deep-merges the live ``config['ceremony_policy']`` block over a deep copy of
    :data:`DEFAULT_CEREMONY_POLICY`: live ``planning`` / ``finalize`` /
    ``automation`` sub-keys win, and any sub-key absent from the live block falls
    back to the canonical default. ``overrides`` is replaced wholesale by the live
    list when present (it is a list, not a keyed sub-block).
    """
    merged: dict[str, Any] = copy.deepcopy(DEFAULT_CEREMONY_POLICY)
    live = config.get('ceremony_policy', {})
    if not isinstance(live, dict):
        return merged

    for section in ('planning', 'finalize', 'automation'):
        live_section = live.get(section)
        if isinstance(live_section, dict):
            merged[section] = {**merged[section], **live_section}
    if isinstance(live.get('overrides'), list):
        merged['overrides'] = live['overrides']
    return merged


# Top-level sections that accept a scalar `section.field` write.
_SETTABLE_SECTIONS = ('planning', 'finalize', 'automation')


def cmd_ceremony_policy(args) -> dict:
    """Dispatch ``ceremony-policy get`` / ``ceremony-policy set``."""
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    if args.verb == 'get':
        return _ceremony_get(args)
    if args.verb == 'set':
        return _ceremony_set(args)
    return error_exit('Unknown ceremony-policy verb')


def _ceremony_get(args) -> dict:
    """Handle ``ceremony-policy get [--field <dotted.path>]``.

    ``--field`` accepts a dotted path into the merged block:
      - ``automation.finalize_without_asking`` → the bool automation knob
      - ``planning.deep_lane`` / ``finalize.qgate`` → a run-at-all gate value
      - ``automation`` / ``planning`` / ``finalize`` → the whole sub-block

    Without ``--field``, returns the whole merged ``ceremony_policy`` block.
    An unresolvable path returns ``error_type: field_not_found``.
    """
    config = load_config()
    merged = _merged_ceremony_policy(config)

    field = getattr(args, 'field', None)
    if not field:
        return success_exit({'section': 'ceremony_policy', **merged})

    cursor: object = merged
    for part in field.split('.'):
        if not isinstance(cursor, dict) or part not in cursor:
            return error_exit(
                f"Unknown ceremony_policy field '{field}'",
                error_type='field_not_found',
            )
        cursor = cursor[part]

    return success_exit({'section': 'ceremony_policy', 'field': field, 'value': cursor})


def _ceremony_set(args) -> dict:
    """Handle ``ceremony-policy set --field <section.field> --value V``.

    Writes a single scalar into ``ceremony_policy.<section>.<field>``, coercing
    ``true``/``false``/digit values. The resulting block is validated before
    persisting; a run-at-all gate set to ``never`` emits the set-time footgun
    ``[WARNING]``. Returns ``error_type: invalid_field`` for a non
    ``section.field`` shape or an unknown top-level section.
    """
    # Local import avoids a module-level cycle: `_cmd_finalize_steps` imports
    # `_config_defaults`, which this module also imports.
    from _cmd_finalize_steps import ceremony_set_footgun_warnings

    field = args.field
    parts = field.split('.')
    if len(parts) != 2 or parts[0] not in _SETTABLE_SECTIONS:
        return error_exit(
            f"ceremony-policy set expects a '<section>.<field>' path where section "
            f"is one of {list(_SETTABLE_SECTIONS)}; got '{field}'",
            error_type='invalid_field',
        )
    section, key = parts
    value = _coerce_value(args.value)

    config = load_config()
    ceremony = config.get('ceremony_policy')
    if not isinstance(ceremony, dict):
        ceremony = copy.deepcopy(DEFAULT_CEREMONY_POLICY)
    section_block = ceremony.get(section)
    if not isinstance(section_block, dict):
        section_block = {}
    section_block[key] = value
    ceremony[section] = section_block

    try:
        validate_ceremony_policy(ceremony)
    except ValueError as e:
        return error_exit(str(e), error_type='invalid_value')

    config['ceremony_policy'] = ceremony
    save_config(config)

    # Footgun warning for a run-at-all gate set to `never` (planning/finalize).
    # Run-at-all gate values are strings; coerce defensively for the typed helper.
    warnings: list[str] = []
    if section in ('planning', 'finalize'):
        warnings = ceremony_set_footgun_warnings({f'{section}.{key}': str(value)})

    return success_exit(
        {'section': 'ceremony_policy', 'field': field, 'value': value, 'warnings': warnings}
    )
