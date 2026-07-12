# SPDX-License-Identifier: FSL-1.1-ALv2
"""``steps-sort`` command handler for manage-config.

Physically re-sorts the on-disk ``plan.phase-6-finalize.steps`` keyed-map into
ascending frontmatter ``order`` sequence, REUSING the manifest composer's
single-source ``_sort_steps_by_frontmatter_order`` choke-point rather than
re-implementing an order table. ``sync-defaults`` deep-merges newly-added steps
by appending them, so the operator-visible ``marshal.json`` drifts out of
frontmatter order over time; the composer already corrects this inside the
plan-local manifest (PR #871) but never on disk. This verb closes that gap.

Scope is fixed to ``phase-6-finalize.steps``. ``phase-5-execute.verification_steps``
is explicitly NOT sorted — it is already composer-ordered and carries no
per-step frontmatter-order doc.
"""

from _config_core import (
    MarshalNotInitializedError,
    error_exit,
    load_config,
    require_initialized,
    save_config,
    success_exit,
)

# Reuse the manifest composer's single-source sort choke-point via the executor's
# PYTHONPATH (every skill's scripts dir is on sys.path). No order table is
# duplicated here — the composer's ``_resolve_step_order`` / frontmatter reader
# is the sole authority for a step's order, and its unresolvable-order fallback
# (external ``bundle:skill`` steps and non-string keys pinned at their original
# index) is inherited verbatim.
from _manifest_validation import _sort_steps_by_frontmatter_order

# The single phase whose on-disk keyed step-map carries per-step frontmatter
# order and therefore drifts. Fixed by design; phase-5-execute is out of scope.
_TARGET_PHASE = 'phase-6-finalize'
_STEP_KEY = 'steps'


def cmd_steps_sort(args) -> dict:
    """Re-sort ``plan.phase-6-finalize.steps`` into ascending frontmatter order.

    Reads the persisted on-disk keyed-map, reorders its keys via the composer's
    ``_sort_steps_by_frontmatter_order`` (values preserved byte-identically; only
    key order changes), and persists ONLY when the order actually changed. A
    re-run on an already-sorted map is a no-op that produces zero diff
    (idempotent). Steps whose frontmatter order is unresolvable are pinned at
    their original index by the reused helper.

    Returns a result dict with ``phase``, ``reordered`` (bool), and the
    ``before`` / ``after`` ordered key lists.
    """
    try:
        require_initialized()
    except MarshalNotInitializedError as e:
        return error_exit(str(e))

    config = load_config()
    plan_config = config.get('plan', {})
    section = plan_config.get(_TARGET_PHASE, {})
    raw = section.get(_STEP_KEY)

    # Only a persisted keyed-map is sortable. An absent / non-dict value means
    # there is nothing on disk to re-sort (a plan relying purely on defaults).
    steps = raw if isinstance(raw, dict) else {}
    before = list(steps.keys())
    after = _sort_steps_by_frontmatter_order(before)

    if before == after:
        return success_exit(
            {'phase': _TARGET_PHASE, 'reordered': False, 'before': before, 'after': after}
        )

    # Rebuild the keyed-map in sorted key order; per-step values are carried over
    # by reference, so each step's nested param object is preserved byte-identically.
    section[_STEP_KEY] = {key: steps[key] for key in after}
    plan_config[_TARGET_PHASE] = section
    config['plan'] = plan_config
    save_config(config)

    return success_exit(
        {'phase': _TARGET_PHASE, 'reordered': True, 'before': before, 'after': after}
    )
