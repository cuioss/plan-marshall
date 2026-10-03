#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Key-space guards for the plan-efficiency calibration anchors.

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
"""

from __future__ import annotations

from _plan_efficiency_anchors_fixtures import (
    _ANCHORS_DOC,
    _RETIRED_PAIR,
    _anchor_keys,
    _canonical_change_types,
    _expected_cross_product,
    _insert_anchor_row,
    _key_diff,
    _live_change_types,
    _remove_anchor_row,
    _router_change_types,
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
        f'Removing the {victim} row should leave exactly that pair unanchored; the guard reported {sorted(missing)}.'
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
