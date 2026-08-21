#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Key-space and population guards for the plan-efficiency calibration anchors.

``plan-retrospective/references/plan-efficiency.md`` § "2. Calibration anchors
table" is keyed on ``(scope_estimate, change_type)``. Its key space is NOT a
free-form list: it is the exact cross-product of two enums that live in other
files entirely, and both axes drift independently of the document. Before this
guard existed the table had rotted in BOTH directions at once — 8 of its 12 rows
were dead keys (``cross_cutting`` / ``complex`` were never members of
``SCOPE_ESTIMATE_VALUES``; ``refactor`` was never a canonical change_type) while
31 live pairs had no row at all. Neither direction was visible at the table,
because a lookup table looks complete no matter how few rows it has.

The guards here are therefore deliberately two-directional and deliberately
derived:

1. **Set equality, not superset** — ``parsed - expected`` (dead / non-canonical
   keys) and ``expected - parsed`` (unanchored pairs) are asserted SEPARATELY, so
   a failure names which kind of rot occurred. A retired enum value fails until
   its dead row is removed; a new enum value fails until it is anchored or
   explicitly ``fallback``-graded.
2. **Both axes re-derived at check time** — ``scope_estimate`` is imported from
   ``SCOPE_ESTIMATE_VALUES`` (``manage-solution-outline.py``); ``change_type`` is
   parsed from the Change-Type Definitions table in ``change-types.md`` and
   unioned with the planning-lane router's ``_DEEP_CHANGE_TYPES``. Neither axis is
   hand-copied into this module, so the test cannot silently agree with a stale
   document.
3. **The guard's own discrimination is tested** — ``test_..._pair_is_removed``
   and ``test_..._non_canonical_key_is_added`` run the same parse-and-diff over a
   MUTATED copy of the document and assert the corresponding direction fires.
   Set equality that is never observed failing is an assertion nobody has proven
   can fail.

The second cluster guards the POPULATION the audit-side sibling anchors score.
``audit.py``'s ``lane-lever-effectiveness`` checkpoint verdict scores a plan's
summed ``metrics.toon`` ``total_tokens`` against
``THRESHOLDS['checkpoint_token_targets']``. What that sum measures is a
default-plus-exception population: dispatched-subagent on every phase row except
those whose ``total_tokens_population`` is ``inline``, where ``manage-metrics
enrich`` folds a main-context figure in. The guards below pin the two facts that
are actually true of the built code:

- the sum takes ``total_tokens`` and ONLY ``total_tokens`` — the derived-cost
  ``billing_weighted_total`` measures what a phase cost to buy, not work done,
  and folding it in would inflate every checkpoint verdict; and
- an ``inline``-labelled row IS included, so the sum spans populations and is
  NOT a dispatched-only total.

The second is stated as a guard rather than left implicit precisely because the
tempting claim — "the verdict is computed over the dispatched population only" —
is FALSE of the built code: the inline fold was deliberately retained, so
asserting a dispatched-only population would pin a false claim into the suite.
"""


from __future__ import annotations

from pathlib import Path
from typing import Any

from _plan_efficiency_anchors_fixtures import (
    _ANCHORS_DOC,
    _RETIRED_PAIR,
    _anchor_keys,
    _canonical_change_types,
    _expected_cross_product,
    _insert_anchor_row,
    _key_diff,
    _live_change_types,
    _live_scope_estimates,
    _load_audit,
    _remove_anchor_row,
    _router_change_types,
    _write_metrics,
)

# ===========================================================================
# Cross-product guard
# ===========================================================================


def test_anchor_table_keys_are_exactly_the_live_cross_product() -> None:
    """The § 2 table carries EXACTLY the live ``(scope_estimate, change_type)`` pairs.

    Set equality, asserted in both directions separately so the failure message
    names the kind of rot. Superset would let a dead key survive forever; subset
    would let a live pair go silently unanchored.
    """
    parsed = _anchor_keys(_ANCHORS_DOC.read_text(encoding='utf-8'))
    expected = _expected_cross_product()
    extra, missing = _key_diff(parsed, expected)

    assert not extra, (
        f'{_ANCHORS_DOC} § 2 carries {len(extra)} key(s) that are NOT in the live '
        f'cross-product: {sorted(extra)}. A retired enum value leaves a dead row '
        f'that can never match a real plan — remove the row (remapping its '
        f'calibration data onto a live band if it carries any).'
    )
    assert not missing, (
        f'{_ANCHORS_DOC} § 2 is missing {len(missing)} live pair(s): '
        f'{sorted(missing)}. Every pair in the key space must be present as a row, '
        f'either `anchored` or explicitly `fallback`-graded — a silently-absent '
        f'pair is the defect this guard exists to catch.'
    )


def test_anchor_table_has_no_duplicate_keys() -> None:
    """No ``(scope_estimate, change_type)`` pair appears twice in the § 2 table.

    Set equality alone cannot see a duplicate: two rows for one key collapse into
    one set member and the equality still holds while the lookup is ambiguous.
    """
    parsed = _anchor_keys(_ANCHORS_DOC.read_text(encoding='utf-8'))
    duplicates = sorted({key for key in parsed if parsed.count(key) > 1})

    assert not duplicates, (
        f'{_ANCHORS_DOC} § 2 carries duplicate key row(s): {duplicates}. A lookup '
        f'on a duplicated key is ambiguous — keep exactly one row per pair.'
    )


def test_cross_product_guard_fails_when_a_pair_is_removed() -> None:
    """Deleting one row makes the guard's ``expected - parsed`` direction fire.

    This is the discrimination proof for the "unanchored pair" direction: an
    equality assertion that has never been observed failing has not been shown to
    be capable of failing.
    """
    content = _ANCHORS_DOC.read_text(encoding='utf-8')
    expected = _expected_cross_product()
    victim = sorted(set(_anchor_keys(content)))[0]

    extra, missing = _key_diff(_anchor_keys(_remove_anchor_row(content, victim)), expected)

    assert missing == {victim}, (
        f'Removing the {victim} row should leave exactly that pair unanchored; the '
        f'guard reported {sorted(missing)}.'
    )
    assert not extra, f'Removing a row must not introduce extra keys; got {sorted(extra)}.'


def test_cross_product_guard_fails_when_a_non_canonical_key_is_added() -> None:
    """Adding a retired-key row makes the guard's ``parsed - expected`` direction fire.

    The discrimination proof for the "dead key" direction — the failure mode the
    table actually had, where ``cross_cutting`` / ``refactor`` rows outlived the
    enums that once contained them.
    """
    content = _ANCHORS_DOC.read_text(encoding='utf-8')
    expected = _expected_cross_product()
    assert _RETIRED_PAIR not in expected, (
        f'{_RETIRED_PAIR} is now a live pair, so it can no longer serve as the '
        f'out-of-cross-product mutation; pick a genuinely retired pair.'
    )

    extra, missing = _key_diff(_anchor_keys(_insert_anchor_row(content, _RETIRED_PAIR)), expected)

    assert extra == {_RETIRED_PAIR}, (
        f'Adding the {_RETIRED_PAIR} row should be reported as exactly that dead '
        f'key; the guard reported {sorted(extra)}.'
    )
    assert not missing, f'Adding a row must not make a live pair go missing; got {sorted(missing)}.'


def test_change_type_axis_is_derived_from_both_owning_sources() -> None:
    """The change_type axis is the canonical vocabulary UNIONED with the router's.

    ``feature_breaking`` is scored as a live change_type by the planning-lane
    router but is absent from the canonical Change-Type Definitions table — the
    source discrepancy § 2 records explicitly. Pinning it here means that when the
    two sources are eventually reconciled, this test fails and forces the § 2 note
    to be updated instead of quietly going stale.
    """
    canonical = _canonical_change_types()
    router = _router_change_types()

    assert 'feature_breaking' in router, (
        'The planning-lane router no longer scores `feature_breaking`; the § 2 '
        'source-discrepancy note in plan-efficiency.md must be updated.'
    )
    assert 'feature_breaking' not in canonical, (
        '`feature_breaking` is now part of the canonical Change-Type Definitions '
        'table; the § 2 source-discrepancy note in plan-efficiency.md is stale and '
        'the UNION wording should collapse to the canonical vocabulary.'
    )
    assert _live_change_types() == canonical | router


# ===========================================================================
# Population guard for the audit-side checkpoint anchors
# ===========================================================================


def test_checkpoint_total_sums_total_tokens_and_only_total_tokens(tmp_path: Path) -> None:
    """``_plan_total_tokens`` sums ``total_tokens`` — and nothing else.

    ``billing_weighted_total`` is a DERIVED-COST measure (what the phase cost to
    buy) over a different population than the work total the checkpoint targets
    score. Folding it in would inflate every verdict, so the guard fixes a
    metrics.toon that carries both fields with deliberately far-apart magnitudes:
    the summed result can only equal the ``total_tokens`` sum.
    """
    audit = _load_audit()
    plan_dir = _write_metrics(
        tmp_path / 'plan-a',
        '[1-init]\n'
        '  total_tokens: 100000\n'
        '  billing_weighted_total: 5000000\n'
        '[5-execute]\n'
        '  total_tokens: 200000\n'
        '  billing_weighted_total: 5000000\n',
    )

    total = audit._plan_total_tokens(audit.PlanInputs(plan_id='plan-a', plan_dir=plan_dir))

    assert total == 300000, (
        f'Checkpoint total is {total}, expected 300000 (the summed `total_tokens`). '
        f'A larger value means a second field — most likely the derived-cost '
        f'`billing_weighted_total` — was folded into the work total.'
    )


def test_checkpoint_total_spans_populations_when_an_inline_row_is_present(
    tmp_path: Path,
) -> None:
    """An ``inline``-labelled phase row IS summed — the total is not dispatched-only.

    This pins the AS-BUILT population honestly. ``manage-metrics enrich`` folds a
    zero-dispatch phase's main-context figure into ``total_tokens`` and marks the
    row ``inline``; that fold was deliberately RETAINED, so the checkpoint sum
    spans populations. Asserting a dispatched-only population here would pin a
    claim the code does not implement.
    """
    audit = _load_audit()
    plan_dir = _write_metrics(
        tmp_path / 'plan-b',
        '[1-init]\n'
        '  total_tokens: 40000\n'
        '  total_tokens_population: inline\n'
        '  inline_main_context_tokens: 40000\n'
        '[5-execute]\n'
        '  total_tokens: 60000\n'
        '  total_tokens_population: dispatched\n',
    )

    total = audit._plan_total_tokens(audit.PlanInputs(plan_id='plan-b', plan_dir=plan_dir))

    assert total == 100000, (
        f'Checkpoint total is {total}, expected 100000. The `inline`-labelled row '
        f'must still be summed — the checkpoint verdict is computed over a '
        f'default-plus-exception population that SPANS populations, not over the '
        f'dispatched population alone.'
    )


def test_checkpoint_targets_are_read_from_the_single_thresholds_constant() -> None:
    """The armed targets live in ``THRESHOLDS`` and cover the classed scope bands.

    The checkpoint classes are a deliberate SUBSET of the live ``scope_estimate``
    enum — an unlisted band scores ``unclassed`` rather than being silently
    graded against a borrowed target — so this asserts subset membership, not
    equality, and would catch a target keyed on a value the enum never had.
    """
    audit = _load_audit()
    targets = audit.THRESHOLDS['checkpoint_token_targets']
    live_scopes = _live_scope_estimates()

    assert targets, 'THRESHOLDS["checkpoint_token_targets"] is empty.'
    unknown = set(targets) - live_scopes
    assert not unknown, (
        f'THRESHOLDS["checkpoint_token_targets"] is keyed on {sorted(unknown)}, '
        f'which are not members of the live scope_estimate enum {sorted(live_scopes)} '
        f'— those targets can never be selected and the class reads `unclassed`.'
    )
    assert all(isinstance(value, int) and value > 0 for value in targets.values()), (
        f'Every checkpoint target must be a positive integer token budget; got {targets}.'
    )


def test_lane_lever_verdict_is_unaffected_by_billing_weighted_total(tmp_path: Path) -> None:
    """The checkpoint verdict is identical with and without a billing column.

    The magnitudes are chosen so the two answers are distinguishable: the work
    total (300K) is inside the ``surgical`` target, while a total that folded the
    billing figures in (10.3M) would blow past it and flip the verdict to ``over``.
    A green here therefore means the verdict really is computed over the
    ``total_tokens`` sum alone.
    """
    audit = _load_audit()
    targets = audit.THRESHOLDS['checkpoint_token_targets']
    work_only = (
        '[1-init]\n  total_tokens: 100000\n[5-execute]\n  total_tokens: 200000\n'
    )
    with_billing = (
        '[1-init]\n'
        '  total_tokens: 100000\n'
        '  billing_weighted_total: 5000000\n'
        '[5-execute]\n'
        '  total_tokens: 200000\n'
        '  billing_weighted_total: 5000000\n'
    )

    def _row(name: str, body: str) -> dict[str, Any]:
        inputs = audit.PlanInputs(
            plan_id=name,
            plan_dir=_write_metrics(tmp_path / name, body),
            scope_estimate='surgical',
        )
        row = audit._lane_lever_row(inputs, targets)
        row.pop('plan_id')
        return dict(row)

    baseline = _row('plan-work-only', work_only)
    billed = _row('plan-with-billing', with_billing)

    assert baseline == billed, (
        'Adding a `billing_weighted_total` column to metrics.toon changed the '
        'lane-lever checkpoint row; the derived-cost figure must never reach the '
        'work total the verdict scores.'
    )
    assert baseline['verdict'] == 'within', (
        f"Expected a `within` verdict for a 300K surgical plan against target "
        f"{targets['surgical']}; got {baseline['verdict']}. If this flipped to "
        f'`over`, a second token field is being summed into the work total.'
    )
