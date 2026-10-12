#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Settle-band order: the quality gate certifies the tree the push ships.

The defect this module pins: ``default:pre-push-quality-gate`` sorted EARLY in
the settle band while ``default:finalize-step-simplify`` (and the security
audit) sorted AFTER it. A forward pass therefore certified one SHA at the gate
and shipped another — the simplify commit advanced HEAD past the recorded
``head_at_completion`` — and the dispatcher's re-entry check re-fired the gate
on the next entry. One run fired the quality gate four times for three tasks,
and finalize cost several times the execute phase with the gate as the dominant
cost. The gate's verdict never covered the tree review saw.

The fix is a re-space of the settle sub-cluster (the order band 1-11 carries no
insertion room, so the remedy is a permutation, not an insertion): the
code-mutating settle steps sort first, the structural self-review sorts after
them so it examines the settled tree, the derived-state refresh follows, and
the quality gate sorts LAST — immediately before the push barrier. The gate's
``head_at_completion`` is then the single-pass HEAD anchor: no settle step
ordered after it can advance HEAD again, every ``mutates_source: true`` step
ordered below it commits before the ledger row its builds write (so those
commits are covered by it and produce no re-stale), and the push freshness
precondition verifies the anchor before shipping.

Every assertion below is RELATIONAL — read off discovery, never a literal order
number — so a future re-space that preserves the relations stays green and only
a re-introduction of the defect goes red:

* The gate is the maximum of the settle population (every step ordered below
  the push barrier sorts at or below the gate, and the gate sorts strictly
  below the barrier).
* No ``mutates_source: true`` step sorts strictly between the gate and the
  push barrier (the only post-gate HEAD moves a pass can see are the gate's
  own trailing auto-fix commit and post-push advances, both of which the
  push reconciliation record and the SHA-equality checks already govern).
* The self-review sorts strictly after both code-mutating settle steps, so it
  reviews the final tree rather than a pre-simplification diff.
* The functional and the code review each sort after the code-mutating settle
  steps and before the refresh, the gate and the barrier; the code review sorts
  directly after the functional review, and both are head-dependent and
  read-only.
* The anchor step itself is both head-dependent and source-mutating: it records
  ``head_at_completion`` on its terminal ``done`` (the anchor) and its builds
  write the ``kind=build`` ledger rows the push freshness gate reads.
* The settle population is non-empty and the named steps resolve — an empty
  derivation or an unresolvable name fails here rather than reporting a clean
  result it never measured.
"""

from __future__ import annotations

from pathlib import Path

import extension_discovery
import pytest
from extension_discovery import find_implementors

#: The canonical ext-point whose implementors are the finalize steps.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The single-pass anchor: the last settle gate before the push barrier.
_GATE = 'default:pre-push-quality-gate'

#: The push barrier the gate anchors.
_PUSH = 'default:push'

#: The structural review that must see the settled tree.
_SELF_REVIEW = 'default:pre-submission-self-review'

#: The code-mutating settle steps the review and the gate must follow.
_MUTATORS = (
    'default:finalize-step-simplify',
    'default:finalize-step-security-audit',
)

#: The functional review — it grades the settled tree, so it must follow the
#: mutators and precede the derived-state refresh, the gate and the barrier.
_FUNCTIONAL_REVIEW = 'default:functional-review'

#: The code review — it judges the same settled tree, directly after the
#: functional review and under the same ordering constraints.
_CODE_REVIEW = 'default:code-review'

#: Both reviews of the settled tree.
_REVIEWS = (_FUNCTIONAL_REVIEW, _CODE_REVIEW)

#: The derived-state refresh that must run after every review of the settled tree.
_ARCHITECTURE_REFRESH = 'default:architecture-refresh'


def _records() -> list[dict]:
    return list(find_implementors(_EXT_POINT))


def _order_of(step_name: str) -> int:
    """Read one discovered step's ``order`` off the registry, never a literal."""
    for record in _records():
        if record.get('name') == step_name:
            order = record.get('order')
            assert isinstance(order, int), (
                f'{step_name} was discovered but its frontmatter ``order`` is '
                f'{order!r}, not an int, so no ordering assertion can read it.'
            )
            return order
    raise AssertionError(
        f'{step_name} is not among the discovered {_EXT_POINT} implementors, so '
        'the settle-order assertion has nothing to read and would pass vacuously.'
    )


def _declares_true(doc_path: Path, key: str) -> bool:
    """Read one boolean fact off a discovered step doc via the registry parser."""
    fields = extension_discovery._read_frontmatter_fields(doc_path, (key,))
    return bool(fields.get(key, False))


def _doc_path(step_name: str) -> Path:
    for record in _records():
        if record.get('name') == step_name:
            return Path(record['path'])
    raise AssertionError(f'{step_name} is not among the discovered {_EXT_POINT} implementors.')


def _settle_orders() -> dict[str, int]:
    """Every discovered step ordered strictly below the push barrier."""
    push_order = _order_of(_PUSH)
    settle: dict[str, int] = {}
    for record in _records():
        name, order = record.get('name'), record.get('order')
        if name == _PUSH or not isinstance(order, int):
            continue
        if order < push_order:
            settle[str(name)] = order
    return settle


def test_settle_population_is_non_empty():
    """The derivation resolves a settle population, so the gates below measure."""
    assert _settle_orders(), (
        f'No discovered {_EXT_POINT} implementor sorts below {_PUSH}: the '
        'settle-order gates below would pass without examining a single step.'
    )


def test_gate_sorts_last_in_the_settle_band():
    """GATE: the quality gate is the settle maximum and sits below the barrier.

    Before the fix the gate sorted early while mutating steps sorted after it,
    so a forward pass certified one SHA and shipped another. With the gate
    last, its ``head_at_completion`` anchors the exact tree the push ships and
    no intra-pass re-stale can arise: at most one gate firing per pass, plus
    one per genuine loop-back re-entry — never one per downstream mutator.
    """
    settle = _settle_orders()
    gate_order = _order_of(_GATE)
    push_order = _order_of(_PUSH)
    assert gate_order < push_order, (
        f'{_GATE} (order {gate_order}) must sort strictly below {_PUSH} '
        f'(order {push_order}): the anchor has to settle before the barrier ships it.'
    )
    offenders = [f'{name} (order {order})' for name, order in settle.items() if order > gate_order]
    assert not offenders, (
        f'These settle steps sort AFTER {_GATE} (order {gate_order}), so their '
        f'commits advance HEAD past the tree the gate certified: {offenders}'
    )


def test_no_mutating_step_sorts_between_gate_and_push():
    """GATE: nothing source-mutating runs between the anchor and the barrier.

    A ``mutates_source: true`` step in (gate, push) would move the hash after
    the ledger row the gate's builds wrote, re-staling the anchor inside the
    same pass. The gate's own trailing auto-fix commit is the one sanctioned
    exception: it is the gate's own output, committed by the dispatcher's
    instrumentation, and covered by the push reconciliation record — not by a
    second step.
    """
    gate_order = _order_of(_GATE)
    push_order = _order_of(_PUSH)
    offenders = []
    for record in _records():
        name, order = record.get('name'), record.get('order')
        if name in (_GATE, _PUSH) or not isinstance(order, int):
            continue
        if gate_order < order < push_order and _declares_true(Path(record['path']), 'mutates_source'):
            offenders.append(f'{name} (order {order})')
    assert not offenders, (
        f'These steps declare mutates_source: true between {_GATE} (order '
        f'{gate_order}) and {_PUSH} (order {push_order}): their commits would '
        f're-stale the single-pass anchor: {offenders}'
    )


def test_self_review_sorts_after_the_code_mutators():
    """GATE: the structural review examines the settled tree, not a pre-diff.

    Before the fix the self-review sorted before simplify, so it reviewed a
    diff a later pass rewrote. After the mutators it reviews the same tree the
    gate then certifies and the push ships; a loop-back re-fire scopes itself
    as a delta round via ``--since-ref`` instead of re-sweeping the whole diff.
    """
    review_order = _order_of(_SELF_REVIEW)
    offenders = [f'{name} (order {_order_of(name)})' for name in _MUTATORS if _order_of(name) >= review_order]
    assert not offenders, (
        f'These code-mutating settle steps sort at or after {_SELF_REVIEW} '
        f'(order {review_order}), so the review examines a tree they later '
        f'rewrite: {offenders}'
    )


@pytest.mark.parametrize('review', _REVIEWS)
def test_review_sorts_after_the_mutators_and_before_refresh_gate_and_push(review):
    """GATE: each review grades the settled tree before anything certifies it.

    Ordered before a code-mutating settle step, the review would grade a diff
    that step later rewrites; ordered after the derived-state refresh, the quality
    gate or the push barrier, a blocking finding would surface after the tree it
    blocks was already refreshed, certified or shipped. Both directions are read
    off discovery, never a literal order.
    """
    review_order = _order_of(review)
    early = [f'{name} (order {_order_of(name)})' for name in _MUTATORS if _order_of(name) >= review_order]
    assert not early, (
        f'These code-mutating settle steps sort at or after {review} '
        f'(order {review_order}), so the review grades a tree they later rewrite: {early}'
    )
    late = [
        f'{name} (order {_order_of(name)})'
        for name in (_ARCHITECTURE_REFRESH, _GATE, _PUSH)
        if _order_of(name) <= review_order
    ]
    assert not late, (
        f'{review} (order {review_order}) must sort strictly before these steps, which act on the tree it grades: {late}'
    )


def test_code_review_sorts_directly_after_the_functional_review():
    """The two reviews are adjacent: nothing discovered sorts between them.

    A step between the two would act on the tree after one review graded it and
    before the other judged it, so the two would not read the same tree.
    """
    functional_order = _order_of(_FUNCTIONAL_REVIEW)
    code_order = _order_of(_CODE_REVIEW)
    assert functional_order < code_order, (
        f'{_CODE_REVIEW} (order {code_order}) must sort after {_FUNCTIONAL_REVIEW} (order {functional_order}).'
    )
    between = [
        f'{record.get("name")} (order {record.get("order")})'
        for record in _records()
        if isinstance(record.get('order'), int) and functional_order < record['order'] < code_order
    ]
    assert not between, f'These steps sort between the two reviews: {between}'


@pytest.mark.parametrize('review', _REVIEWS)
def test_review_is_head_dependent_and_read_only(review):
    """Each review's verdict is a function of HEAD, and the review writes no source.

    ``head_dependent: true`` makes a later commit re-fire the review instead of
    leaving a stale verdict standing; ``mutates_source`` must stay false, or the
    dispatcher would commit after it and the review would grade a tree it then
    advanced past. A control on a known source-mutating step proves the reader
    distinguishes the two answers.
    """
    doc_path = _doc_path(review)
    assert _declares_true(doc_path, 'head_dependent'), (
        f'{review} must declare head_dependent: true — a review verdict is computed against a HEAD.'
    )
    assert not _declares_true(doc_path, 'mutates_source'), (
        f'{review} must not declare mutates_source: true — the review edits no tracked source.'
    )
    assert _declares_true(_doc_path(_GATE), 'mutates_source'), (
        'control: the reader must report mutates_source: true for the quality gate, '
        'or the negative assertion above proves nothing'
    )


def test_anchor_step_is_head_dependent_and_source_mutating():
    """The anchor both records its SHA and writes the ledger rows that prove it.

    ``head_dependent: true`` obliges the terminal ``done`` to persist
    ``head_at_completion`` (refused when absent); ``mutates_source: true``
    means its builds write ``kind=build`` ledger entries the push freshness
    gate reads. An anchor missing either half is a claim without the mechanism
    that makes it checkable.
    """
    doc_path = _doc_path(_GATE)
    assert _declares_true(doc_path, 'head_dependent'), (
        f'{_GATE} must declare head_dependent: true — without it no SHA is persisted and the anchor names no tree.'
    )
    assert _declares_true(doc_path, 'mutates_source'), (
        f'{_GATE} must declare mutates_source: true — its builds write the '
        'ledger rows the push freshness precondition verifies the anchor against.'
    )
