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
from _manifest_lanes import LANE_TIERS, _effective_lane_tier, _read_frontmatter_lane
from _manifest_validation import _REPO_ROOT, _is_external_step, _resolve_standards_path
from marketplace_paths import resolve_project_skill_path

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


# Legacy run_at_all → lane migration (D7). Maps each of the four finalize
# ceremony gates' retired run_at_all values onto the per-element ``lane`` override
# channel: ``never→off``, ``always→minimal``, and ``auto→`` omit (``auto`` is the
# lane default — an absent override resolves to ``auto``, so no key is written).
# The mapping table below covers only the two force values; ``auto`` (and any
# malformed value) falls through to "omit" while STILL removing the retired key so
# a re-run is a no-op.
_RUN_AT_ALL_TO_LANE: dict[str, str] = {'never': 'off', 'always': 'minimal'}

# Owning finalize step id (marshal.json keyed form, ``default:``-prefixed) for
# each ceremony gate's ``lane`` override. Mirrors
# ``_manifest_rules._CEREMONY_GATE_OWNER_STEP`` — the manifest ceremony transform
# reads the same owning-step lane overrides this migration writes.
_CEREMONY_GATE_OWNER_STEP: dict[str, str] = {
    'qgate': 'default:pre-push-quality-gate',
    'self_review': 'default:pre-submission-self-review',
    'simplify': 'default:finalize-step-simplify',
    'security_audit': 'default:finalize-step-security-audit',
}

# The three ceremony gates whose legacy run_at_all value lived as a step-owned
# param (keyed by the gate name) under the owning step's nested param object in
# ``plan.phase-6-finalize.steps[<owner>]``. ``qgate`` is the flat phase-level
# sibling handled separately.
_STEP_OWNED_CEREMONY_GATES: tuple[str, ...] = ('self_review', 'simplify', 'security_audit')


def _find_step_key(steps_map: dict, owner: str) -> str | None:
    """Return the actual key in ``steps_map`` matching ``owner``.

    Matches the ``default:``-prefixed owner id first, then the prefix-stripped
    bare form, so a legacy config that stored the owning step under either form is
    handled. Returns ``None`` when neither form is present.
    """
    if owner in steps_map:
        return owner
    bare = owner[len('default:') :] if owner.startswith('default:') else owner
    if bare in steps_map:
        return bare
    return None


def _set_step_lane(phase6: dict, owner: str, lane_value: str) -> None:
    """Write ``lane_value`` into the owning step's param object under ``steps``.

    Materializes the ``steps`` map and the owning step entry when absent (the
    ``qgate`` case — ``default:pre-push-quality-gate`` may not yet be present in a
    legacy config). Preserves any existing sibling params on the step.
    """
    steps_map = phase6.get('steps')
    if not isinstance(steps_map, dict):
        steps_map = {}
        phase6['steps'] = steps_map
    key = _find_step_key(steps_map, owner) or owner
    params = steps_map.get(key)
    if not isinstance(params, dict):
        params = {}
    params['lane'] = lane_value
    steps_map[key] = params


def _migrate_run_at_all_to_lane(live: dict, migrated: list[str]) -> dict:
    """Migrate the four finalize ceremony gates off run_at_all onto the lane channel.

    Reads each gate's retired run_at_all value from its legacy location, maps it
    (:data:`_RUN_AT_ALL_TO_LANE`), writes the owning step's ``lane`` override
    (materializing ``default:pre-push-quality-gate`` for ``qgate``), and removes
    the legacy run_at_all key so the subsequent deep-merge back-fills the
    newly-materialized ``lane:off`` / ``lane:ask`` steps cleanly.

    Legacy locations:

    - ``qgate`` — flat ``plan.phase-6-finalize.qgate``.
    - ``self_review`` / ``simplify`` / ``security_audit`` — a step-owned param
      (keyed by the gate name) under the owning step's nested param object in
      ``plan.phase-6-finalize.steps[<owner>]``.

    The three planning gates (``deep_lane`` / ``escalation`` / ``revalidation``)
    need NO migration — only the enum they validate against was renamed (D2), so
    their field names and values are unchanged. Runs BEFORE the deep-merge and is
    idempotent: once the legacy keys are gone, a re-run reports no migration.
    Mutates ``live`` in place and returns it; each migration is recorded as a
    human-readable dotted-path string in ``migrated``.
    """
    plan = live.get('plan')
    if not isinstance(plan, dict):
        return live
    phase6 = plan.get('phase-6-finalize')
    if not isinstance(phase6, dict):
        return live

    # qgate — flat phase-level sibling.
    if 'qgate' in phase6:
        legacy = phase6.pop('qgate')
        mapped = _RUN_AT_ALL_TO_LANE.get(legacy) if isinstance(legacy, str) else None
        owner = _CEREMONY_GATE_OWNER_STEP['qgate']
        if mapped is not None:
            _set_step_lane(phase6, owner, mapped)
            migrated.append(f'plan.phase-6-finalize.qgate={legacy} -> steps[{owner}].lane={mapped}')
        else:
            migrated.append(f'plan.phase-6-finalize.qgate={legacy} -> (auto: omitted)')

    # self_review / simplify / security_audit — step-owned params.
    steps_map = phase6.get('steps')
    if isinstance(steps_map, dict):
        for gate in _STEP_OWNED_CEREMONY_GATES:
            owner = _CEREMONY_GATE_OWNER_STEP[gate]
            key = _find_step_key(steps_map, owner)
            if key is None:
                continue
            params = steps_map.get(key)
            if not isinstance(params, dict) or gate not in params:
                continue
            legacy = params.pop(gate)
            mapped = _RUN_AT_ALL_TO_LANE.get(legacy) if isinstance(legacy, str) else None
            if mapped is not None:
                params['lane'] = mapped
                migrated.append(f'plan.phase-6-finalize.steps[{key}].{gate}={legacy} -> .lane={mapped}')
            else:
                migrated.append(f'plan.phase-6-finalize.steps[{key}].{gate}={legacy} -> (auto: omitted)')
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


def _resolve_finalize_step_lane(step_id: str) -> dict[str, str] | None:
    """Resolve a phase-6-finalize step's ``lane:`` frontmatter block from its source doc.

    Mirrors ``manage-execution-manifest``'s composer resolver
    (``manage-execution-manifest.py`` ``_resolve_element_lane``) verbatim so the
    materialized effective lane is exactly the composer's own default:

    - Built-in steps (bare or ``default:``-prefixed) resolve via the phase-6
      standards / workflow doc (:func:`_resolve_standards_path`).
    - ``project:`` steps resolve via the project-local ``{bare}/SKILL.md``.
    - Other ``bundle:skill`` external steps have no project-local source and
      return ``None`` (not lane-participating — left untouched by the materializer).

    Returns the nested ``lane:`` sub-key dict (``class`` / ``tier`` / …), or
    ``None`` when the source doc is missing, has no frontmatter, or declares no
    ``lane:`` block.
    """
    if step_id.startswith('project:'):
        bare = step_id[len('project:') :]
        skill_path = resolve_project_skill_path(f'{bare}/SKILL.md', base=_REPO_ROOT)
        return _read_frontmatter_lane(skill_path)
    if _is_external_step(step_id):
        return None
    return _read_frontmatter_lane(_resolve_standards_path(step_id))


def _materialize_finalize_lanes(live: dict, materialized: list[str], added: list[str]) -> dict:
    """Fill an explicit ``lane`` on every lane-less ``plan.phase-6-finalize.steps`` entry.

    Runs AFTER :func:`_deep_merge_missing` (so it sees the back-filled default
    rows and consumes the populated ``added`` accumulator) and BEFORE the
    provisioning re-stamp. Walks the finalize keyed-map and, for each step whose
    param object carries no ``lane`` key, decides the fill value by PROVENANCE:

    - **Freshly deep-merged default row** — the step's dotted path
      ``plan.phase-6-finalize.steps.{step_id}`` is in ``added`` (a default row the
      user's config did not previously have): filled with ``lane: off`` (opt-in,
      per the "infra steps must be opt-in" principle).
    - **Pre-existing step** (not in ``added``): filled with its **effective lane**
      — the frontmatter-class default the composer would apply with no override,
      resolved via :func:`_resolve_finalize_step_lane` +
      :func:`_effective_lane_tier` (declared ``tier`` ▸ class default: ``core`` /
      ``derived-state`` → ``minimal``, ``adversarial`` / ``prunable`` → ``auto``).
      This is a semantic no-op — it surfaces the implicit default as an explicit
      value, changing nothing operationally.
    - **Unresolvable pre-existing step** — the frontmatter lane cannot be resolved
      to a concrete lattice tier (no source doc / no ``lane:`` block / external
      ``bundle:skill`` step): left untouched and NOT reported. The composer keeps
      such elements by default; materializing a value it cannot resolve would not
      be a no-op.

    Idempotent: a step already carrying any explicit ``lane`` (``off`` / ``ask`` /
    a resolved tier) is left untouched, so a re-run materializes nothing. Scope is
    ``plan.phase-6-finalize.steps`` ONLY. Mutates ``live`` in place and returns it;
    each materialized step is recorded as an annotated dotted-path string in
    ``materialized``.
    """
    plan = live.get('plan')
    if not isinstance(plan, dict):
        return live
    phase6 = plan.get('phase-6-finalize')
    if not isinstance(phase6, dict):
        return live
    steps_map = phase6.get('steps')
    if not isinstance(steps_map, dict):
        return live

    added_set = set(added)
    for step_id, params in steps_map.items():
        if not isinstance(step_id, str) or not step_id:
            continue
        # Idempotent: an explicit lane (off / ask / a resolved tier) is left as-is.
        if isinstance(params, dict) and 'lane' in params:
            continue

        dotted = f'plan.phase-6-finalize.steps.{step_id}'
        if dotted in added_set:
            fill = 'off'
        else:
            lane_block = _resolve_finalize_step_lane(step_id)
            if not lane_block:
                continue  # unresolvable frontmatter — leave lane-less, do not report
            effective, _is_off = _effective_lane_tier(lane_block, None)
            if effective not in LANE_TIERS:
                continue  # undeterminable tier — leave untouched (not a no-op otherwise)
            fill = effective

        if not isinstance(params, dict):
            params = {}
        params['lane'] = fill
        steps_map[step_id] = params
        materialized.append(f'{dotted} -> lane={fill}')
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

    A second migration pass (:func:`_migrate_run_at_all_to_lane`) runs alongside
    the retired-key migration (also BEFORE the deep-merge): it moves the four
    finalize ceremony gates (``qgate`` / ``self_review`` / ``simplify`` /
    ``security_audit``) off their retired run_at_all locations onto the owning
    step's per-element ``lane`` override (``never→off`` / ``always→minimal`` /
    ``auto→`` omit) and removes the legacy key, so the deep-merge back-fills the
    newly-materialized ``lane:off`` / ``lane:ask`` finalize steps automatically.
    The three planning gates (``deep_lane`` / ``escalation`` / ``revalidation``)
    need no migration. This pass is idempotent too (a re-run reports no
    migration).

    A materialization pass (:func:`_materialize_finalize_lanes`) runs AFTER the
    deep-merge and BEFORE the provisioning re-stamp: it fills an explicit ``lane``
    on every lane-less ``plan.phase-6-finalize.steps`` entry so the finalize
    step-set is fully explicit. A **pre-existing** lane-less step is filled with
    its frontmatter-class effective lane (a semantic no-op surfacing the composer's
    own default); only a **freshly deep-merged default** row (one in ``added``) is
    filled with ``lane: off`` (opt-in). It is idempotent (a step already carrying
    an explicit ``lane`` is untouched) and scoped to ``phase-6-finalize.steps``
    only.

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

    migrated: list[str] = []
    _migrate_run_at_all_to_lane(live, migrated)

    added: list[str] = []
    merged = _deep_merge_missing(live, defaults, '', added)

    # Materialize an explicit lane on every lane-less phase-6-finalize step. Runs
    # AFTER the deep-merge (consumes the populated ``added`` accumulator to
    # distinguish a freshly-merged default row from a pre-existing step) and
    # BEFORE the provisioning re-stamp.
    materialized: list[str] = []
    _materialize_finalize_lanes(merged, materialized, added)

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

    if added or stamps_changed or renamed or migrated or materialized:
        save_config(merged)

    return success_exit(
        {
            'added': sorted(added),
            'added_count': len(added),
            'renamed': sorted(renamed),
            'renamed_count': len(renamed),
            'migrated': sorted(migrated),
            'migrated_count': len(migrated),
            'materialized': sorted(materialized),
            'materialized_count': len(materialized),
        }
    )
