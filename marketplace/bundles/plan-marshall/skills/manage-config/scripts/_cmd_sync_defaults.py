# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Sync-defaults command handler for manage-config.

Handles: sync-defaults

Non-destructively merges any missing keys from ``get_default_config()`` into the
live ``.plan/marshal.json`` so existing projects (which never re-run ``init``)
pick up new default rows without losing user-set overrides.
"""

from _config_core import (
    error_exit,
    is_initialized,
    load_config,
    save_config,
    success_exit,
)
from _config_defaults import get_default_config, stamp_provisioning_fields

# Retired step keys and their canonical replacements. Each entry maps a step id
# that a prior release emitted (and which live consumer configs may still carry)
# to the canonical id in use today. The table is the single, explicit, extensible
# rename set: future renames add rows here. The first (and currently only) rename
# collapses both the built-in-prefixed and bare legacy forms of the review step to
# the promoted bundle:skill canonical.
RETIRED_STEP_KEY_RENAMES: dict[str, str] = {
    'default:automated-review': 'plan-marshall:automatic-review',
    'automated-review': 'plan-marshall:automatic-review',
}

# The two keyed-map step containers a rename pass walks: (phase key, map key).
_STEP_MAP_LOCATIONS: tuple[tuple[str, str], ...] = (
    ('phase-5-execute', 'verification_steps'),
    ('phase-6-finalize', 'steps'),
)


def _rename_in_map(steps_map: dict, prefix: str, renamed: list[str]) -> dict:
    """Rebuild a keyed-map steps object with retired keys migrated to canonicals.

    Semantics (idempotent):
    - A retired key whose canonical is ABSENT from the map is renamed in place:
      the canonical takes the retired key's position and its knob block verbatim,
      so surrounding insertion order and the nested params are preserved.
    - A retired key whose canonical is already PRESENT (anywhere in the original
      map, or already emitted by an earlier retired form) is dropped as a
      duplicate — the canonical's own knob block wins; no double step is produced.
    - A non-retired key is copied through unchanged.

    Each migrated retired key is reported as a human-readable dotted-path string in
    ``renamed``.
    """
    original_keys = set(steps_map)
    new_map: dict = {}
    for step_id, params in steps_map.items():
        canonical = RETIRED_STEP_KEY_RENAMES.get(step_id)
        if canonical is None:
            new_map[step_id] = params
            continue
        if canonical in original_keys or canonical in new_map:
            # canonical already present -> drop the retired duplicate
            renamed.append(f'{prefix}.{step_id} (dropped duplicate of {canonical})')
            continue
        # rename in place, preserving the knob block and position
        new_map[canonical] = params
        renamed.append(f'{prefix}.{step_id} -> {canonical}')
    return new_map


def _migrate_retired_step_keys(live: dict, renamed: list[str]) -> dict:
    """Migrate retired step keys to their canonicals across the keyed-map containers.

    Walks ``plan.phase-5-execute.verification_steps`` and
    ``plan.phase-6-finalize.steps``, applying :func:`_rename_in_map` to each. Runs
    BEFORE the deep-merge so the canonical is already present when the merge
    inspects the map — the merge then never re-adds a default canonical alongside a
    surviving retired key (which would produce a double review step). Mutates
    ``live`` in place and returns it.
    """
    plan = live.get('plan')
    if not isinstance(plan, dict):
        return live
    for phase_key, map_key in _STEP_MAP_LOCATIONS:
        phase = plan.get(phase_key)
        if not isinstance(phase, dict):
            continue
        steps_map = phase.get(map_key)
        if not isinstance(steps_map, dict):
            continue
        prefix = f'plan.{phase_key}.{map_key}'
        phase[map_key] = _rename_in_map(steps_map, prefix, renamed)
    return live


def _deep_merge_missing(live: dict, defaults: dict, prefix: str, added: list[str]) -> dict:
    """Recursively add keys present in ``defaults`` but absent from ``live``.

    Semantics:
    - A key already present in ``live`` is preserved unchanged. "Present" means
      "key exists" — value comparison is NOT performed, so a user-set ``False``
      survives a default of ``False`` or ``True``.
    - When both sides hold a dict under the same key, the merge recurses so
      deeply-nested missing sub-keys are added.
    - Lists (and all non-dict values) are atomic: if the key is present in
      ``live``, the user's value is kept verbatim; if absent, the default is
      copied in.

    Ownerless-step interaction: an ownerless ``steps`` / ``verification_steps``
    entry now defaults to ``None`` (no noisy empty ``{}``). Because ``None`` is a
    non-dict atomic value, a step id absent from ``live`` is back-filled with
    ``None`` (never ``{}``), and a step id already present — whether its on-disk
    value is the new ``None`` or a legacy ``{}`` — is preserved untouched. The
    merge therefore writes no ``{}`` for ownerless steps and is idempotent
    against both the new no-``{}`` shape and a pre-existing legacy ``{}`` shape;
    the read path coerces all of {absent, ``null``, ``{}``, TOON-``''``} to an
    empty dict, so the two on-disk shapes read identically.

    Args:
        live: The live config subtree (mutated in place).
        defaults: The default config subtree to merge from.
        prefix: Dotted path prefix for the current subtree (for reporting).
        added: Accumulator of dotted paths that were newly added.

    Returns:
        The mutated ``live`` subtree.
    """
    for key, default_value in defaults.items():
        path = f'{prefix}.{key}' if prefix else key
        if key not in live:
            live[key] = default_value
            added.append(path)
        elif isinstance(default_value, dict) and isinstance(live[key], dict):
            _deep_merge_missing(live[key], default_value, path, added)
    return live


def cmd_sync_defaults(args) -> dict:
    """Handle sync-defaults command.

    Reads the live marshal.json, migrates any retired step keys to their
    canonicals (see :data:`RETIRED_STEP_KEY_RENAMES`), deep-merges any missing keys
    from ``get_default_config()`` into it (preserving every existing value), writes
    the merged config back, and reports the added and renamed keys.

    The retired-key migration runs BEFORE the deep-merge: renaming a retired key to
    its canonical first means the deep-merge sees the canonical already present and
    does not re-add it, so no duplicate (double-review) step is produced. The
    migration preserves each step's nested knob block byte-identically and its
    insertion order, and is idempotent (a re-run reports no renames).

    ``get_default_config()`` does NOT seed ``build.map`` — the
    build_map is materialized only by the wizard's explicit build-map seed
    step (Step 8b), never at init or by sync-defaults. The deep-merge therefore
    back-fills other missing default keys while leaving the user's seeded
    ``build.map`` untouched.
    """
    if not is_initialized():
        return error_exit('marshal.json not found. Run command /marshall-steward first')

    live = load_config()
    defaults = get_default_config()

    renamed: list[str] = []
    _migrate_retired_step_keys(live, renamed)

    added: list[str] = []
    merged = _deep_merge_missing(live, defaults, '', added)

    # Refresh the provisioning stamps (system.provisioned_version /
    # system.config_seed_fingerprint). The deep-merge only ADDS missing keys, so
    # an already-present stamp would go stale after a default-config change; this
    # reconcile path (invoked by marshall-steward) re-stamps both unconditionally
    # and persists when either the merge added keys or a stamp changed.
    existing_system = merged.get('system')
    before_stamps = (
        (existing_system.get('provisioned_version'), existing_system.get('config_seed_fingerprint'))
        if isinstance(existing_system, dict)
        else (None, None)
    )
    stamp_provisioning_fields(merged)
    after_system = merged['system']
    stamps_changed = before_stamps != (
        after_system['provisioned_version'],
        after_system['config_seed_fingerprint'],
    )

    if added or stamps_changed or renamed:
        save_config(merged)

    return success_exit(
        {
            'added': sorted(added),
            'added_count': len(added),
            'renamed': sorted(renamed),
            'renamed_count': len(renamed),
        }
    )
