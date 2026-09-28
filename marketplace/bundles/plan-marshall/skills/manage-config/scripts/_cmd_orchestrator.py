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
        per-epic parallelization-scope ask in ``plan-orchestrator`` init.
    ``auto_emit``  bool  — the orchestrator-tier autonomy knob (default False);
        when true the epic orchestrator auto-fills the emit queue on landing.
    ``use_worktree``  bool  — the repository-wide switch (default False) that
        routes the orchestrator ledger store through the shared ledger worktree.

``use_worktree`` is anchored on the MAIN checkout for both directions, so every
checkout agrees on it. ``get`` reports the main-anchored effective value — the
value the store seam actually uses — rather than the cwd-relative file. ``set``
refuses (``use_worktree_requires_main_checkout``) unless the ``marshal.json`` it
would write is that same main-anchored file, and before persisting a CHANGED
value it runs the cutover refusal: switching on while the main checkout holds
uncommitted or unlanded ledger paths, or switching off while the shared ledger
worktree does, is refused (``ledger_cutover_refused``, naming every path); a
drift check git cannot answer refuses with ``ledger_drift_unevaluable``. On any
refusal nothing is written.

All scalar knobs read/write through this same verb against the shared
whitelist — no schema rework as the block grows.
"""

import json
from pathlib import Path

import _config_core
from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    reject_unknown_provisioning_field,
    save_config,
    success_exit,
)
from _config_defaults import DEFAULT_ORCHESTRATOR, DEFAULT_PROJECT
from command_forms import STEWARD_COMMAND
from marketplace_paths import main_checkout_root
from orchestrator_worktree import (
    OrchestratorStoreUnavailable,
    detect_ledger_drift,
    orchestrator_knob_config_path,
    orchestrator_use_worktree,
    orchestrator_worktree_path,
)

# The orchestrator block's known scalar (non-effort) fields — the fail-closed
# whitelist consulted by every scalar read/write.
ORCHESTRATOR_SCALAR_FIELDS: tuple[str, ...] = ('parallelization_scope', 'auto_emit', 'use_worktree')

# The base branch the cutover drift check compares against when the project
# configures none — the same seeded default ``project.default_base_branch`` carries.
DEFAULT_PROJECT_BASE_BRANCH: str = str(DEFAULT_PROJECT['default_base_branch'])


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


def _same_file(left: Path, right: Path) -> bool:
    """Return whether two paths name the same file, resolving symlinks and ``..``."""
    return left.resolve() == right.resolve()


def _main_anchored_use_worktree_is_set(knob_path: Path | None) -> bool:
    """Return whether the main-anchored ``marshal.json`` carries ``orchestrator.use_worktree``.

    An absent path, an unreadable or malformed file, and a missing block all read
    as unset — the same fall-through :func:`orchestrator_use_worktree` applies to
    the value itself.
    """
    if knob_path is None:
        return False
    try:
        data = json.loads(knob_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    block = data.get('orchestrator') if isinstance(data, dict) else None
    return isinstance(block, dict) and 'use_worktree' in block


def _use_worktree_anchor_refusal() -> dict | None:
    """Refuse a ``use_worktree`` write whose target is not the main-anchored ``marshal.json``.

    The knob is READ from the main checkout's ``marshal.json`` only, so a write
    to any other file would land where no reader looks — while the cutover guard
    had been evaluated against main. Returns the refusal dict, or ``None`` when
    the write targets the file the reader reads.
    """
    write_path = Path(_config_core.MARSHAL_PATH)
    knob_path = orchestrator_knob_config_path()
    if knob_path is not None and _same_file(write_path, knob_path):
        return None
    return error_exit(
        'use_worktree_requires_main_checkout',
        detail=(
            'orchestrator.use_worktree is read from the main checkout marshal.json only; '
            'run this set from the main checkout'
        ),
        write_path=str(write_path),
        knob_path=str(knob_path) if knob_path is not None else None,
    )


def _cutover_refusal(config: dict, switching_on: bool) -> dict | None:
    """Run the cutover drift check for a ``use_worktree`` flip.

    Switching ON inspects the main checkout; switching OFF inspects the shared
    ledger worktree when it exists (no worktree means no ledger state to strand).
    Either side compares against ``origin/{project.default_base_branch}``.

    Returns:
        The refusal dict when ledger state would be stranded or the check could
        not be evaluated, else ``None``.
    """
    project = config.get('project')
    configured = project.get('default_base_branch') if isinstance(project, dict) else None
    base = configured.strip() if isinstance(configured, str) else ''
    base_ref = f'origin/{base or DEFAULT_PROJECT_BASE_BRANCH}'

    try:
        if switching_on:
            checkout = main_checkout_root()
        else:
            checkout = orchestrator_worktree_path()
            if not checkout.is_dir():
                return None
        dirty_paths = detect_ledger_drift(checkout, base_ref)
    except RuntimeError as exc:
        return error_exit(
            'ledger_drift_unevaluable',
            detail=f'cannot resolve the checkout the cutover drift check must inspect: {exc}',
            base_ref=base_ref,
        )
    except OrchestratorStoreUnavailable as exc:
        return error_exit(exc.code, detail=exc.message, **exc.fields)

    if not dirty_paths:
        return None
    side = 'main checkout' if switching_on else 'shared ledger worktree'
    return error_exit(
        'ledger_cutover_refused',
        detail=(
            f'the {side} holds {len(dirty_paths)} uncommitted or unlanded ledger path(s); '
            'land or discard them before switching orchestrator.use_worktree'
        ),
        checkout=str(checkout),
        base_ref=base_ref,
        dirty_paths=dirty_paths,
    )


def cmd_orchestrator_get(args) -> dict:
    """Handle ``orchestrator get --field <field>``.

    Returns the stored value when the field is set; when it is unset, returns the
    field's canonical default from :data:`DEFAULT_ORCHESTRATOR` (``None`` only for
    a field that carries no seeded default). The accompanying ``set`` flag
    distinguishes a configured value from an unset one, so callers (e.g. the
    per-epic ask pre-fill) key off ``set`` — not the value — to decide whether to
    apply their own default.

    ``use_worktree`` is the exception to the cwd-relative read: it reports the
    main-anchored effective value (:func:`orchestrator_use_worktree`) and whether
    the main-anchored file sets it, so a ``get`` from a plan worktree answers with
    the value the store seam actually uses.
    """
    if not is_initialized():
        return error_exit(f'marshal.json not initialized; run {STEWARD_COMMAND} first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')

    rejection = reject_unknown_provisioning_field(field, ORCHESTRATOR_SCALAR_FIELDS, 'orchestrator')
    if rejection is not None:
        return rejection

    if field == 'use_worktree':
        knob_path = orchestrator_knob_config_path()
        return success_exit(
            {
                'field': field,
                'value': orchestrator_use_worktree(),
                'set': _main_anchored_use_worktree_is_set(knob_path),
                'knob_path': str(knob_path) if knob_path is not None else None,
            }
        )

    config = load_config()
    orch_block = config.get('orchestrator')
    # When the field is unset in the live block, fall back to the canonical
    # default from DEFAULT_ORCHESTRATOR (so `auto_emit` reads its seeded `False`
    # and `parallelization_scope` its seeded `1`). The value is advisory on an
    # unset read: `set` is `False`, and callers key off `set` — not the value —
    # to apply their own default. A field with no seeded default falls back to
    # `None`.
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
    value per-field before persisting it into ``config['orchestrator']``. A
    ``use_worktree`` write additionally passes the main-checkout anchor check and,
    when the value changes, the cutover refusal before anything is persisted.
    """
    if not is_initialized():
        return error_exit(f'marshal.json not initialized; run {STEWARD_COMMAND} first')

    field = getattr(args, 'field', None)
    if not field:
        return error_exit('--field is required')
    raw_value = getattr(args, 'value', None)
    if raw_value is None:
        return error_exit('--value is required')

    rejection = reject_unknown_provisioning_field(field, ORCHESTRATOR_SCALAR_FIELDS, 'orchestrator')
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
    elif field in ('auto_emit', 'use_worktree'):
        coerced = _coerce_bool(raw_value)
        if coerced is None:
            return error_exit(f'{field} must be a boolean (true/false)')
    else:
        # Unreachable while the whitelist is fully enumerated above; the branch
        # keeps the coercion contract explicit as further fields are added.
        coerced = raw_value

    if field == 'use_worktree':
        anchor_refusal = _use_worktree_anchor_refusal()
        if anchor_refusal is not None:
            return anchor_refusal

    config = load_config()
    orch_block = config.setdefault('orchestrator', {})
    if not isinstance(orch_block, dict):
        return error_exit('orchestrator block in marshal.json is not a dictionary')

    if field == 'use_worktree' and coerced != (orch_block.get('use_worktree') is True):
        cutover_refusal = _cutover_refusal(config, switching_on=coerced is True)
        if cutover_refusal is not None:
            return cutover_refusal

    orch_block[field] = coerced
    save_config(config)

    return success_exit({'field': field, 'value': coerced, 'target': f'orchestrator.{field}'})
