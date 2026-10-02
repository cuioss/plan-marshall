# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the upgrade-flow Stage 2 reconcile sub-steps against silent regression.

Stage 2's fine reconcile steps (`sync-defaults`, `steps-sort`, `normalize-keys`)
live in ``references/upgrade-flow.md`` as the doc-level expansion of the coarse
``reconcile-marshal-json`` sub-step the planner emits — they are driven by the LLM
router, not enumerated in ``upgrade.py``. This test is the only detector for the
failure mode D5 closes: Stage 2 losing the **unconditional** top-level canonicalizer
(`normalize-keys`) so a non-canonical key order survives the post-version-bump flow.
It pins that `normalize-keys` is invoked in Stage 2, and LAST — after the two
conditional-write reconcile verbs (D1(c): normalize-keys after any key-adding op).

It ALSO pins the coarse layer: every `sub_steps` entry the planner emits for
Stage 2 must be named in the Stage 2 prose. That check is DERIVED from
``upgrade._STAGE_SPECS`` rather than restating the expected names, so a sub-step
added to the planner and not to the doc fails here. Without it, `migrate-bot-lists`
was emitted by the planner and mentioned nowhere in the file, and a project
carrying a legacy `enabled_bots` value could complete the documented upgrade with
the migration never run.
"""

from __future__ import annotations

from pathlib import Path

import upgrade

from conftest import get_skill_dir

# Annotated because ``conftest`` is deliberately untyped to mypy (see pyproject's
# ``ignore_missing_imports`` override for it), so the accessor's return would
# otherwise be ``Any`` and ``_stage2_block`` would return ``Any`` as ``str``.
_UPGRADE_FLOW: Path = get_skill_dir('plan-marshall', 'marshall-steward') / 'references' / 'upgrade-flow.md'


def _stage2_block() -> str:
    """Return the text of the '## Stage 2: reconcile-config' section only."""
    text = _UPGRADE_FLOW.read_text(encoding='utf-8')
    start = text.index('## Stage 2: reconcile-config')
    end = text.index('## Stage 3', start)
    return text[start:end]


def _review_held_defaults_block() -> str:
    """Return the '### Sub-step `review-held-defaults`' subsection only.

    Scoping the wording assertions to this block keeps them load-bearing: a
    whole-Stage-2 search already matches unrelated `held`/`removal` prose, so
    only the subsection proves the ask step itself carries the wording.
    """
    block = _stage2_block()
    start = block.index('### Sub-step `review-held-defaults`')
    end = block.index('### Sub-step `migrate-bot-lists`', start)
    return block[start:end]


def _invocation_index(block: str, verb: str) -> int:
    """Return the position of the manage-config invocation of ``verb`` in ``block``."""
    return block.index(f'plan-marshall:manage-config:manage-config {verb}')


def _stage2_emitted_sub_steps() -> list[str]:
    """Return the Stage 2 ``sub_steps`` the planner emits, read from the planner.

    Derived, never restated: the expected set is whatever ``_STAGE_SPECS``
    declares, so a sub-step added there is immediately in scope for the doc
    check below. Stage 2's list is kind-invariant (a plain list, not a
    per-kind dict), which the assertion states rather than assumes.
    """
    stage2 = next(spec for spec in upgrade._STAGE_SPECS if spec['key'] == 'reconcile-config')
    sub_steps = stage2['sub_steps']
    assert isinstance(sub_steps, list), 'Stage 2 sub_steps became kind-dependent; this check must resolve per kind'
    return sub_steps


def test_stage2_invokes_normalize_keys_after_sync_defaults_and_steps_sort():
    block = _stage2_block()

    sync_defaults = _invocation_index(block, 'sync-defaults')
    steps_sort = _invocation_index(block, 'steps-sort')
    normalize_keys = _invocation_index(block, 'normalize-keys')

    # All three present, and normalize-keys is LAST — after both conditional-write verbs.
    assert normalize_keys > steps_sort > sync_defaults


def test_stage2_prose_names_every_sub_step_the_planner_emits():
    # The coarse layer the fine-verb check above cannot see: the doc's Stage 2
    # section must name each emitted sub-step, so a reader following the prose
    # runs the set the planner actually emitted.
    block = _stage2_block()
    emitted = _stage2_emitted_sub_steps()

    # A population size, not just a pass/fail: an empty _STAGE_SPECS entry would
    # otherwise satisfy the loop below by iterating over nothing.
    assert len(emitted) >= 2, f'Stage 2 emits only {emitted!r} — the check would be vacuous'

    missing = [sub_step for sub_step in emitted if sub_step not in block]
    assert missing == [], (
        f'Stage 2 emits {emitted!r} but upgrade-flow.md § "Stage 2: reconcile-config" never names {missing!r}'
    )


def test_stage2_runs_migrate_bot_lists_after_the_reconcile_verbs():
    # Order within the emitted set: the migration follows the three reconcile
    # verbs and precedes the build-map drift gate, matching the emitted order.
    block = _stage2_block()

    normalize_keys = _invocation_index(block, 'normalize-keys')
    migrate = block.index('plan-marshall:marshall-steward:upgrade migrate-bot-lists')
    build_map_drift = _invocation_index(block, 'build-map drift')

    assert normalize_keys < migrate < build_map_drift


def test_stage2_runs_the_descriptor_migration_after_validate_bot_lists_and_before_build_map():
    # The descriptor migration is the last emitted Stage 2 sub-step: it follows the
    # bot-list validation and precedes the stage-level build-map drift gate.
    block = _stage2_block()

    validate = block.index('plan-marshall:marshall-steward:upgrade validate-bot-lists')
    migrate_descriptors = block.index('discover --force --apply migration')
    build_map_drift = _invocation_index(block, 'build-map drift')

    assert validate < migrate_descriptors < build_map_drift


def test_stage2_descriptor_migration_is_gated_on_the_regression_check_against_head():
    # A written migration is checked against the committed HEAD baseline before it is
    # left for Stage 4 — and the check follows the write it gates.
    block = _stage2_block()

    migrate_descriptors = block.index('discover --force --apply migration')
    regression_check = block.index('descriptor-regression-check --pre-ref HEAD')

    assert migrate_descriptors < regression_check


# =============================================================================
# D3 upgrade-path controls (PLAN-TRUTH-168)
# =============================================================================
#
# Stage-2 order preserves a prior removal (sync first, atomic-once-present),
# the upgrade report words `re-add` vs `new default` identically to sync, and
# the operator-intent ask step runs before the bot-list migration.


def test_stage2_review_held_defaults_runs_after_reconcile_and_before_migrate_bot_lists():
    """D3: the operator-intent ask step runs between reconcile and bot migration."""
    stage2 = next(spec for spec in upgrade._STAGE_SPECS if spec['key'] == 'reconcile-config')
    sub_steps = stage2['sub_steps']
    assert isinstance(sub_steps, list)
    assert sub_steps.index('review-held-defaults') == sub_steps.index('reconcile-marshal-json') + 1
    assert sub_steps.index('review-held-defaults') < sub_steps.index('migrate-bot-lists')


def test_stage2_prose_words_re_add_vs_new_default_identically_to_sync():
    """D3: the review-held-defaults block uses `re-add`/`re_added` for removals, `new default`/`held_for_ask` for fresh gaps."""
    block = _review_held_defaults_block()

    assert '`re_added`' in block
    assert 're-add' in block
    assert '`held_for_ask`' in block
    assert 'new default' in block
    # the ask-once, never-auto-add posture is stated inside the block itself
    assert 'never auto-add' in block or 'never auto-adding' in block


def test_stage2_prose_states_removal_survives_sync():
    """D3: the review-held-defaults block states a prior removal survives reconcile untouched."""
    block = _review_held_defaults_block()

    assert 'removal' in block
    assert 'atomic-once-present' in block
    assert 'crosses operator removal' in block
