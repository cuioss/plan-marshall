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
from _config_defaults import get_default_config


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

    Reads the live marshal.json, deep-merges any missing keys from
    ``get_default_config()`` into it (preserving every existing value), writes
    the merged config back, and reports the added keys grouped by dotted path.

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

    added: list[str] = []
    merged = _deep_merge_missing(live, defaults, '', added)

    if added:
        save_config(merged)

    return success_exit({'added': sorted(added), 'added_count': len(added)})
