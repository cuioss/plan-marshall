#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Three-way scope reconciliation for manage-references, by SYMMETRIC DIFFERENCE.

The plan's file surface is asserted in three independent places, and nothing
reconciled them:

* **A — the recorded declaration**: ``references.affected_files``, the value every
  downstream consumer actually reads.
* **B — the declared derivation**: the union of every deliverable's
  mutation-intent paths, derived from the outline's STRUCTURED per-path ``intent``
  data via :func:`_plan_parsing.declared_paths_by_intent` — never scraped from
  outline prose.
* **C — the realized footprint**: what the landing actually touched, resolved
  through the shared whole-chain resolver
  (:func:`_footprint_resolver.resolve_footprint`).

This module compares all three pairwise and publishes where they disagree. It is
read-only: it writes no key, emits no finding, and returns no failing status. It
reports.

Why symmetric difference, never cardinality
-------------------------------------------
The verdict is computed from the set difference in **both directions** and never
from ``len(A) == len(B)``. Two sets of equal size that share no member are
maximally different, and a cardinality check calls them identical — that is
precisely the defect this verb exists to detect, and it is not hypothetical: a
measured instance had two 29-entry lists disagreeing on 7 members each way, which
a size check reported as clean. Both directions are published as named lists,
with their own sizes, alongside the pair's symmetric-difference size. No code path
here compares only set sizes.

Why every count names its population
------------------------------------
Each side publishes the size of the set it built (``a_count`` / ``b_count`` /
``c_count``), and side B additionally publishes the walk it derived from
(``deliverables_scanned`` / ``headings_found`` / ``bullets_parsed``). A count with
no population behind it cannot be told apart from a count over nothing — ADR-014
(an aggregation carries producer identity) and ADR-019 (an audit separates what it
could not evaluate from what it evaluated and found wanting).

Why a side that could not be built is a THIRD state
---------------------------------------------------
A side is either **established** or **unmeasured**, never "empty". An empty set is
a measurement — the plan declared nothing, or the landing touched nothing — and it
compares meaningfully. A side that could not be built is not a measurement at all,
and reporting it as an empty set would make every difference against it read as a
total disagreement (or, against another empty side, as agreement). The three
unmeasured causes the request names are kept distinct: an unparseable outline, an
absent ``references.json``, and an unresolvable footprint are three different
failures and each reports its own reason (:data:`UNMEASURED_REASONS`).

Why agreement needs more than a zero difference
------------------------------------------------
An agreement verdict is admissible only when **both** sides of that pair were
established AND at least one of them carried a member. Two conditions, because two
different things can manufacture a false clean:

* one side unbuilt — the pair reports :data:`PAIR_UNMEASURED`, naming which sides
  were unbuilt (their reasons are published once, on the sides themselves);
* both sides established but both empty — nothing was compared, so the zero
  symmetric difference certifies nothing. That pair reports :data:`PAIR_VACUOUS`,
  not :data:`PAIR_AGREE`. This is the empty-population-reported-as-clean shape,
  and a comparison is exactly the place it hides.

Agreement is never inferred from a non-empty overlap either: the overlap is not
consulted at all, only the two differences are.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, NamedTuple

from _footprint_resolver import footprint_resolved, resolve_footprint
from _plan_parsing import declared_paths_by_intent, declared_paths_population
from _references_core import get_references_path
from _references_crud import _AFFECTED_FILES_FIELD, _MUTATION_INTENTS, _read_outline
from file_ops import get_plan_dir
from input_validation import require_valid_plan_id

# ---------------------------------------------------------------------------
# The three sides, and the pairs over them
# ---------------------------------------------------------------------------
#
# Exposed as DATA — the same discipline ``_footprint_resolver.RESOLVING_TIERS``
# follows — so the emitted roster, the comparison loop, and any test all read the
# one declaration instead of a hand-copied list. A fourth side added here grows the
# published roster and the pair set by construction, with nothing to keep in sync.

#: A — the RECORDED declaration: what ``references.affected_files`` currently holds.
SIDE_A = 'a'

#: B — the DECLARED derivation: the outline's structured mutation-intent paths.
SIDE_B = 'b'

#: C — the REALIZED footprint: what the landing actually touched.
SIDE_C = 'c'

#: The sides this verb reconciles, in the order they are reported.
SIDES: tuple[str, ...] = (SIDE_A, SIDE_B, SIDE_C)

#: What each side IS, published beside its verdict so a reader never has to
#: remember which letter names which set.
SIDE_SOURCES: dict[str, str] = {
    SIDE_A: 'references.affected_files',
    SIDE_B: 'outline.declared_mutation_intent',
    SIDE_C: 'realized_footprint',
}

#: Every unordered pair over :data:`SIDES`, in reporting order. DERIVED from the
#: sides rather than enumerated independently, so the two cannot drift.
PAIRS: tuple[tuple[str, str], ...] = tuple(
    (left, right)
    for index, left in enumerate(SIDES)
    for right in SIDES[index + 1 :]
)

#: The pair the request names as the primary validated comparison: the recorded
#: declaration against the structured derivation. The other two are reported
#: alongside it, not instead of it.
PRIMARY_PAIR: tuple[str, str] = (SIDE_A, SIDE_B)


# ---------------------------------------------------------------------------
# Side states
# ---------------------------------------------------------------------------

#: The side was built. Its set may legitimately be EMPTY — that is a measurement.
SIDE_ESTABLISHED = 'established'

#: The side could not be built at all. Distinct from an empty set, and never
#: substituted for one: an empty set compares, a missing side does not.
SIDE_UNMEASURED = 'unmeasured'


# ---------------------------------------------------------------------------
# Pair states
# ---------------------------------------------------------------------------

#: Both sides established, at least one non-empty, and neither difference carries a
#: member. The only admissible agreement verdict.
PAIR_AGREE = 'agree'

#: Both sides established and at least one difference carries a member.
PAIR_DISAGREE = 'disagree'

#: Both sides established and BOTH empty. The symmetric difference is zero because
#: nothing was compared, not because the two sets were found to match — reported as
#: its own state so a vacuous zero can never be read as an agreement.
PAIR_VACUOUS = 'vacuous'

#: At least one side of the pair could not be built, so no comparison was made. The
#: unbuilt sides are named on the pair; each one's REASON is published once, on the
#: side itself.
PAIR_UNMEASURED = 'unmeasured'

#: The pair verdict population, declared so a consumer can enumerate it.
PAIR_STATES: tuple[str, ...] = (PAIR_AGREE, PAIR_DISAGREE, PAIR_VACUOUS, PAIR_UNMEASURED)


# ---------------------------------------------------------------------------
# Unmeasured causes — one token per distinct failure
# ---------------------------------------------------------------------------

#: A: ``references.json`` does not exist.
REASON_REFERENCES_ABSENT = 'references_absent'

#: A: ``references.json`` exists but could not be read as a JSON object.
REASON_REFERENCES_UNREADABLE = 'references_unreadable'

#: A: ``references.json`` was read and carries no ``affected_files`` key at all.
#: A MISSING key is not an empty list — nothing was ever recorded, so there is no
#: recorded declaration to compare. (A key present as an empty list IS a
#: measurement and establishes the side.)
REASON_AFFECTED_FILES_ABSENT = 'affected_files_absent'

#: A: the ``affected_files`` key exists but is not a list, so no path set can be
#: built from it.
REASON_AFFECTED_FILES_NOT_A_LIST = 'affected_files_not_a_list'

#: B: ``solution_outline.md`` does not exist.
REASON_OUTLINE_NOT_FOUND = 'outline_not_found'

#: B: ``solution_outline.md`` exists but could not be read.
REASON_OUTLINE_UNREADABLE = 'outline_unreadable'

#: B: the outline was read and yielded no deliverable blocks, so the derivation
#: walked nothing. The published population reports the measured zero.
REASON_NO_DELIVERABLES_PARSED = 'no_deliverables_parsed'

#: C: no tier of the shared resolver answered.
REASON_FOOTPRINT_UNRESOLVED = 'footprint_unresolved'

#: Every reason a side can report, declared as data so the causes stay
#: enumerable — the request's three named causes (unparseable outline, absent
#: ``references.json``, unresolvable footprint) plus the finer distinctions each
#: side can actually tell apart.
UNMEASURED_REASONS: tuple[str, ...] = (
    REASON_REFERENCES_ABSENT,
    REASON_REFERENCES_UNREADABLE,
    REASON_AFFECTED_FILES_ABSENT,
    REASON_AFFECTED_FILES_NOT_A_LIST,
    REASON_OUTLINE_NOT_FOUND,
    REASON_OUTLINE_UNREADABLE,
    REASON_NO_DELIVERABLES_PARSED,
    REASON_FOOTPRINT_UNRESOLVED,
)


class _Side(NamedTuple):
    """One side of the reconciliation: its paths, or why they could not be built.

    ``paths`` is ``None`` **only** when the side is unmeasured, and ``reason`` is
    populated **only** then. The two are never both meaningful: an established side
    carries a set (possibly empty) and no reason; an unmeasured side carries a
    reason and no set. Nothing coerces one into the other.

    ``population`` is what the side's derivation walked, published when the side
    knows it. It is deliberately empty rather than zero-filled when nothing was
    walked at all — a zero population from a derivation that never ran is the same
    false measurement this module exists to prevent one level up.
    """

    key: str
    paths: frozenset[str] | None
    reason: str | None
    population: dict[str, int]


def _pair_key(left: str, right: str) -> str:
    """The reported name of a pair, e.g. ``a_b``."""
    return f'{left}_{right}'


def _path_set(values: list[Any]) -> frozenset[str]:
    """Normalize a raw path list into a comparable set.

    Entries are stringified and stripped, and blank entries are dropped, so the
    comparison is not defeated by whitespace or a stray empty string. Deduplication
    is inherent to the set — a path recorded twice contributes one member, exactly
    as it does on the derived side.
    """
    return frozenset(text for text in (str(value).strip() for value in values) if text)


def _build_recorded_side(plan_id: str) -> _Side:
    """Side A: ``references.affected_files`` as it stands on disk.

    Reads the file directly rather than through ``read_references`` because that
    helper degrades every failure to ``{}`` — an absent file, an unreadable one and
    a genuinely empty one all arrive identically, and telling them apart is the
    whole job here.

    A present-but-empty ``affected_files`` list ESTABLISHES the side with an empty
    set: that is a recorded declaration that names no path. An absent key does not:
    nothing was ever recorded, which is the state a plan is in before
    ``sync-affected-files`` first runs, and it is reported as unmeasured. The same
    distinction ``_footprint_resolver._coerce_path_set`` draws on the realized side.
    """
    path = get_references_path(plan_id)
    if not path.exists():
        return _Side(SIDE_A, None, REASON_REFERENCES_ABSENT, {})
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return _Side(SIDE_A, None, REASON_REFERENCES_UNREADABLE, {})
    if not isinstance(raw, dict):
        return _Side(SIDE_A, None, REASON_REFERENCES_UNREADABLE, {})
    if _AFFECTED_FILES_FIELD not in raw:
        return _Side(SIDE_A, None, REASON_AFFECTED_FILES_ABSENT, {})
    value = raw[_AFFECTED_FILES_FIELD]
    if not isinstance(value, list):
        return _Side(SIDE_A, None, REASON_AFFECTED_FILES_NOT_A_LIST, {})
    return _Side(SIDE_A, _path_set(value), None, {})


def _build_declared_side(plan_id: str) -> _Side:
    """Side B: the outline's declared MUTATION-intent paths, structurally derived.

    Consumes :func:`_plan_parsing.declared_paths_by_intent` and the mutation half of
    the intent partition (``_references_crud._MUTATION_INTENTS``) rather than
    re-deriving either. That is what makes B comparable to A at all: A is written by
    ``sync-affected-files`` from exactly this derivation and exactly this partition,
    so any difference between them is real drift rather than two readings of the
    same outline disagreeing about what a declaration means.

    The private names are imported rather than restated for the same reason. A
    second copy of the partition rule would let A's production rule and B's
    comparison rule drift apart silently, and every difference this verb reported
    would then be uninterpretable.
    """
    content, error = _read_outline(plan_id)
    if content is None:
        reason = str(error.get('error') or REASON_OUTLINE_UNREADABLE)
        return _Side(SIDE_B, None, reason, {})

    population = declared_paths_population(content)
    if population['deliverables_scanned'] == 0:
        # The outline was READ, so its population is a measurement and is published;
        # but it yielded no deliverable to derive from, so no set was built.
        return _Side(SIDE_B, None, REASON_NO_DELIVERABLES_PARSED, population)

    by_intent = declared_paths_by_intent(content)
    mutation: set[str] = set()
    for intent in _MUTATION_INTENTS:
        mutation |= by_intent.get(intent, set())
    return _Side(SIDE_B, frozenset(mutation), None, population)


def _build_realized_side(plan_id: str) -> _Side:
    """Side C: the realized footprint from the shared whole-chain resolver.

    Resolution state is read through the named
    :func:`_footprint_resolver.footprint_resolved` predicate, never by testing
    emptiness: a resolved-but-empty footprint is a landing that touched no file, and
    collapsing it onto the unresolvable sentinel is exactly what that predicate
    exists to prevent.
    """
    footprint = resolve_footprint(get_plan_dir(plan_id), plan_id)
    if not footprint_resolved(footprint):
        return _Side(SIDE_C, None, REASON_FOOTPRINT_UNRESOLVED, {})
    return _Side(SIDE_C, frozenset(footprint), None, {})


def _compare_pair(left: _Side, right: _Side) -> dict[str, Any]:
    """Compare two sides by symmetric difference and return the pair's report.

    Emits BOTH difference directions as named lists (``{left}_not_{right}`` and
    ``{right}_not_{left}``), both of their sizes, and the pair's
    ``symmetric_difference_count`` — which is the sum of the two direction sizes,
    since the two differences are disjoint by construction. The intersection is
    never computed, so no verdict here can rest on an overlap.

    An unmeasured pair publishes NO difference keys and NO counts at all. Their
    absence is the contract: a consumer that branches on
    ``{pair}_symmetric_difference_count`` finds no key rather than a zero, so a
    comparison that never happened cannot be read as one that found nothing.
    """
    pair = _pair_key(left.key, right.key)

    if left.paths is None or right.paths is None:
        return {
            f'{pair}_state': PAIR_UNMEASURED,
            f'{pair}_unmeasured_sides': [side.key for side in (left, right) if side.paths is None],
        }

    left_not_right = sorted(left.paths - right.paths)
    right_not_left = sorted(right.paths - left.paths)
    symmetric_difference_count = len(left_not_right) + len(right_not_left)

    if not left.paths and not right.paths:
        # Both established, both empty: nothing was compared, so the zero certifies
        # nothing. Never PAIR_AGREE.
        state = PAIR_VACUOUS
    elif symmetric_difference_count == 0:
        state = PAIR_AGREE
    else:
        state = PAIR_DISAGREE

    return {
        f'{pair}_state': state,
        f'{left.key}_not_{right.key}_count': len(left_not_right),
        f'{right.key}_not_{left.key}_count': len(right_not_left),
        f'{pair}_symmetric_difference_count': symmetric_difference_count,
        f'{left.key}_not_{right.key}': left_not_right,
        f'{right.key}_not_{left.key}': right_not_left,
    }


def cmd_reconcile_scope(args: argparse.Namespace) -> dict:
    """Reconcile the recorded, declared and realized file sets three ways.

    Read-only. Nothing is written to ``references.json``, no finding is persisted,
    and the return status is ``success`` even when every side is unmeasured — an
    audit that could not evaluate something reports that it could not, it does not
    fail. The only error path is an invalid ``--plan-id``, which
    :func:`input_validation.require_valid_plan_id` raises before any side is built.

    The returned TOON is flat and self-describing:

    * ``sides`` / ``pairs`` — the rosters, derived from :data:`SIDES` and
      :data:`PAIRS`, so a reader knows what was supposed to be compared before
      reading what was.
    * ``{side}_source`` / ``{side}_state`` — what each side is and whether it was
      built; plus ``{side}_count`` when established, or
      ``{side}_unmeasured_reason`` when not. Exactly one of those two keys is
      present per side.
    * ``deliverables_scanned`` / ``headings_found`` / ``bullets_parsed`` — the walk
      side B derived from, present whenever the outline was read.
    * per pair: ``{pair}_state``, both difference lists, both direction sizes and
      ``{pair}_symmetric_difference_count`` — or, when unmeasured,
      ``{pair}_unmeasured_sides`` and nothing else.
    * ``established_side_count`` / ``side_count`` and ``measured_pair_count`` /
      ``unmeasured_pair_count`` / ``pair_count`` — the coverage of the run itself,
      each against the population it was computed from.
    """
    require_valid_plan_id(args)
    plan_id = args.plan_id

    sides: dict[str, _Side] = {
        SIDE_A: _build_recorded_side(plan_id),
        SIDE_B: _build_declared_side(plan_id),
        SIDE_C: _build_realized_side(plan_id),
    }

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'primary_pair': _pair_key(*PRIMARY_PAIR),
        'sides': list(SIDES),
        'side_count': len(SIDES),
        'pairs': [_pair_key(left, right) for left, right in PAIRS],
        'pair_count': len(PAIRS),
    }

    for key in SIDES:
        side = sides[key]
        result[f'{key}_source'] = SIDE_SOURCES[key]
        if side.paths is None:
            result[f'{key}_state'] = SIDE_UNMEASURED
            result[f'{key}_unmeasured_reason'] = side.reason
        else:
            result[f'{key}_state'] = SIDE_ESTABLISHED
            result[f'{key}_count'] = len(side.paths)
        # The population a side walked, published only when it walked one.
        result.update(side.population)

    for left_key, right_key in PAIRS:
        result.update(_compare_pair(sides[left_key], sides[right_key]))

    result['established_side_count'] = sum(1 for key in SIDES if sides[key].paths is not None)
    measured_pair_count = sum(
        1 for left_key, right_key in PAIRS if result[f'{_pair_key(left_key, right_key)}_state'] != PAIR_UNMEASURED
    )
    result['measured_pair_count'] = measured_pair_count
    result['unmeasured_pair_count'] = len(PAIRS) - measured_pair_count

    return result
