#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_path_attribution_merge`` — the N-attributor claim merge (Axis-D).

Loaded in-process via ``load_script_module`` (real filename → coverage counts).

The merge owns the provenance half of the Axis-D contract: core merges, stamps
producers and resolves ownership order; attributors only declare claims. The
properties pinned here:

- Single-attributor passthrough and the null-on-absent return.
- Two attributors claiming the same normalized prefix for the SAME module
  collapse to ONE claim carrying both producer ids — corroboration, not conflict.
- Two attributors claiming the same normalized prefix for DIFFERENT modules yield
  NO claim **and a reported collision note naming both modules**. A dropped
  element with an empty ``notes[]`` is exactly the silent suppression this test
  exists to prevent, and an iteration-order winner is exactly the
  non-deterministic answer the contract forbids.
- **Every merge-side drop is reported.** Each of the three validity filters —
  malformed candidate, blank/root-ish prefix, unknown module — appends its own
  ``merge:``-prefixed note, so an attributor whose every candidate the merge
  discarded never reports ``status: ok`` / ``claim_count: 0`` / ``notes: []``.
- A raising attributor reports ``status: error`` with ``claim_count: 0`` while
  its siblings still contribute — one broken implementor never blanks the map.
- A ``claims`` value that is not a usable collection degrades identically,
  because the collection is materialized inside the same guard: a truthy
  non-iterable would otherwise escape as an uncaught ``TypeError``, and a bare
  string would iterate into characters rather than pairs — a broken implementor
  misreported as a running one. A **falsy** non-iterable (``0`` / ``None`` /
  ``[]``) is not broken and still reports ``status: ok``.
- Claim ordering is deterministic across runs (sorted by ``(prefix, module)``).
- ``lookup_claim`` resolves the LONGEST containing prefix, matches a bare root
  segment such as ``.plan``, and does NOT over-match a sibling path that merely
  shares the string prefix (``.plans/x``) — the nest-inside guard.
"""

from typing import Any

from conftest import load_script_module

_merge = load_script_module(
    'plan-marshall', 'extension-api', '_path_attribution_merge.py', 'path_attribution_merge'
)

# The known-module universe every test validates claim modules against.
_MODULES = {'plan-marshall', 'documentation', 'other'}


class _StubAttributor:
    """An attributor returning canned ``(claims, notes)``, or raising on demand."""

    def __init__(self, claims=None, notes=None, raises: bool = False):
        self._claims = claims if claims is not None else []
        self._notes = notes if notes is not None else []
        self._raises = raises

    def claim_paths(self):
        if self._raises:
            raise RuntimeError('boom-claim-paths')
        return self._claims, self._notes


def _record(attributor_id: str, attributor: Any) -> dict[str, Any]:
    """Build a discovery-shaped ``{origin, id, module}`` record."""
    return {'origin': f'origin-{attributor_id}', 'id': attributor_id, 'module': attributor}


def _merge_with(*pairs: tuple[str, Any]):
    """Run the merge over ``(attributor_id, attributor)`` pairs."""
    records = [_record(aid, att) for aid, att in pairs]
    return _merge.merge_path_claims(records, _MODULES)


def _report_for(reports: list[dict[str, Any]], attributor_id: str) -> dict[str, Any]:
    """Return the single report belonging to ``attributor_id``."""
    matching = [rep for rep in reports if rep['id'] == attributor_id]
    assert len(matching) == 1, f'expected exactly one report for {attributor_id!r}'
    return matching[0]


def _merge_notes(report: dict[str, Any]) -> list[str]:
    """Return only the notes the MERGE appended, not the attributor's own."""
    return [note for note in report['notes'] if note.startswith('merge: ')]


# =============================================================================
# Null-on-absent
# =============================================================================


def test_zero_attributors_returns_empty_claims_and_empty_reports():
    # Act
    claims, reports = _merge.merge_path_claims([], _MODULES)

    # Assert — attributor_count 0 is distinguishable from "ran and claimed nothing"
    assert claims == []
    assert reports == []


def test_attributor_claiming_nothing_still_reports_ok():
    # Arrange
    claims, reports = _merge_with(('quiet', _StubAttributor()))

    # Assert — a ran-and-claimed-nothing attributor is a positive negative
    assert claims == []
    assert reports == [{'id': 'quiet', 'claim_count': 0, 'status': 'ok', 'notes': []}]


def test_single_attributor_claims_pass_through():
    # Arrange
    attributor = _StubAttributor(claims=[('.plan', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('plan-marshall', attributor))

    # Assert
    assert claims == [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['plan-marshall']}]
    assert _report_for(reports, 'plan-marshall')['claim_count'] == 1


# =============================================================================
# Corroboration — same prefix, same module, two attributors
# =============================================================================


def test_same_prefix_same_module_collapses_to_one_claim_with_both_producers():
    # Arrange — two attributors independently assert the same ownership
    first = _StubAttributor(claims=[('.plan', 'plan-marshall')])
    second = _StubAttributor(claims=[('.plan', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('zeta', first), ('alpha', second))

    # Assert — ONE claim, both producers, sorted
    assert claims == [
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha', 'zeta']}
    ]
    assert _report_for(reports, 'zeta')['claim_count'] == 1
    assert _report_for(reports, 'alpha')['claim_count'] == 1


def test_corroboration_is_detected_after_prefix_normalization():
    # Arrange — the same directory spelled with and without a trailing slash
    first = _StubAttributor(claims=[('.plan', 'plan-marshall')])
    second = _StubAttributor(claims=[('.plan/', 'plan-marshall')])

    # Act
    claims, _ = _merge_with(('alpha', first), ('zeta', second))

    # Assert — one identity, not two claims that both happen to match
    assert claims == [
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha', 'zeta']}
    ]


def test_disjoint_claims_from_two_attributors_union_to_the_sum():
    # Arrange
    first = _StubAttributor(claims=[('.plan', 'plan-marshall')])
    second = _StubAttributor(claims=[('doc', 'documentation')])

    # Act
    claims, _ = _merge_with(('alpha', first), ('zeta', second))

    # Assert
    assert claims == [
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']},
        {'prefix': 'doc', 'module': 'documentation', 'producers': ['zeta']},
    ]


# =============================================================================
# Collision abstention — same prefix, DIFFERENT modules
# =============================================================================


def test_same_prefix_different_modules_emits_no_claim():
    # Arrange — two well-formed but mutually exclusive ownership assertions
    first = _StubAttributor(claims=[('doc', 'documentation')])
    second = _StubAttributor(claims=[('doc', 'plan-marshall')])

    # Act
    claims, _ = _merge_with(('alpha', first), ('zeta', second))

    # Assert — abstention, never an iteration-order winner
    assert claims == []


def test_collision_appends_a_reported_note_naming_both_modules():
    # Arrange
    first = _StubAttributor(claims=[('doc', 'documentation')])
    second = _StubAttributor(claims=[('doc', 'plan-marshall')])

    # Act
    _, reports = _merge_with(('alpha', first), ('zeta', second))

    # Assert — the suppression is visible on BOTH contenders' reports, naming
    # both modules. A dropped claim with an empty notes[] is the failure mode.
    for attributor_id in ('alpha', 'zeta'):
        notes = _merge_notes(_report_for(reports, attributor_id))
        assert len(notes) == 1
        assert 'documentation' in notes[0]
        assert 'plan-marshall' in notes[0]
        assert 'doc' in notes[0]


def test_collision_leaves_neither_attributor_with_a_silent_confident_zero():
    # Arrange
    first = _StubAttributor(claims=[('doc', 'documentation')])
    second = _StubAttributor(claims=[('doc', 'plan-marshall')])

    # Act
    _, reports = _merge_with(('alpha', first), ('zeta', second))

    # Assert — claim_count drops to zero, but notes[] explains why
    for attributor_id in ('alpha', 'zeta'):
        report = _report_for(reports, attributor_id)
        assert report['claim_count'] == 0
        assert report['status'] == 'ok'
        assert report['notes'] != []


def test_collision_does_not_suppress_an_uncontested_sibling_claim():
    # Arrange — one contested prefix plus one each attributor owns alone
    first = _StubAttributor(claims=[('doc', 'documentation'), ('.plan', 'plan-marshall')])
    second = _StubAttributor(claims=[('doc', 'plan-marshall'), ('other', 'other')])

    # Act
    claims, _ = _merge_with(('alpha', first), ('zeta', second))

    # Assert — only the contested prefix is dropped
    assert claims == [
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']},
        {'prefix': 'other', 'module': 'other', 'producers': ['zeta']},
    ]


def test_three_way_collision_names_every_contending_module():
    # Arrange
    first = _StubAttributor(claims=[('doc', 'documentation')])
    second = _StubAttributor(claims=[('doc', 'plan-marshall')])
    third = _StubAttributor(claims=[('doc', 'other')])

    # Act
    claims, reports = _merge_with(('a', first), ('b', second), ('c', third))

    # Assert
    assert claims == []
    note = _merge_notes(_report_for(reports, 'a'))[0]
    for module_name in ('documentation', 'plan-marshall', 'other'):
        assert module_name in note


# =============================================================================
# Merge-side validity drops — each appends its own ``merge:`` note
# =============================================================================


def test_malformed_candidate_is_dropped_with_a_merge_note():
    # Arrange — not a two-element pair of strings
    attributor = _StubAttributor(claims=['.plan'])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == []
    notes = _merge_notes(_report_for(reports, 'alpha'))
    assert len(notes) == 1
    assert 'malformed' in notes[0]


def test_blank_prefix_is_dropped_with_a_merge_note():
    # Arrange — a prefix that would claim the whole tree
    attributor = _StubAttributor(claims=[('', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == []
    notes = _merge_notes(_report_for(reports, 'alpha'))
    assert len(notes) == 1
    assert 'root-ish' in notes[0]


def test_root_slash_prefix_is_dropped_with_a_merge_note():
    # Arrange — ``/`` normalizes to the empty prefix
    attributor = _StubAttributor(claims=[('/', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == []
    assert len(_merge_notes(_report_for(reports, 'alpha'))) == 1


def test_dot_prefix_is_dropped_with_a_merge_note():
    # Arrange — ``.`` is the repo root, not a bounded subtree
    attributor = _StubAttributor(claims=[('.', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == []
    assert len(_merge_notes(_report_for(reports, 'alpha'))) == 1


def test_unknown_module_claim_is_dropped_with_a_merge_note():
    # Arrange — an attributor cannot invent an owner
    attributor = _StubAttributor(claims=[('.plan', 'no-such-module')])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == []
    notes = _merge_notes(_report_for(reports, 'alpha'))
    assert len(notes) == 1
    assert 'unknown module' in notes[0]


def test_attributor_whose_every_candidate_was_dropped_is_not_a_silent_zero():
    # Arrange — the headline anti-vacuity property: three drops, three notes
    attributor = _StubAttributor(
        claims=['.plan', ('', 'plan-marshall'), ('.plan', 'no-such-module')]
    )

    # Act
    claims, reports = _merge_with(('alpha', attributor))
    report = _report_for(reports, 'alpha')

    # Assert — claim_count 0 with an EXPLAINED zero, never a bare confident one
    assert claims == []
    assert report['claim_count'] == 0
    assert report['status'] == 'ok'
    assert len(_merge_notes(report)) == 3


def test_attributor_own_notes_are_preserved_alongside_merge_notes():
    # Arrange
    attributor = _StubAttributor(
        claims=[('', 'plan-marshall')], notes=['attributor-side suppression']
    )

    # Act
    _, reports = _merge_with(('alpha', attributor))
    report = _report_for(reports, 'alpha')

    # Assert — the ``merge:`` prefix keeps the two sources distinguishable
    assert report['notes'][0] == 'attributor-side suppression'
    assert len(_merge_notes(report)) == 1


def test_a_valid_claim_survives_alongside_a_dropped_sibling():
    # Arrange
    attributor = _StubAttributor(claims=[('.plan', 'plan-marshall'), ('', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('alpha', attributor))

    # Assert
    assert claims == [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]
    assert _report_for(reports, 'alpha')['claim_count'] == 1


# =============================================================================
# A raising attributor degrades without aborting its siblings
# =============================================================================


def test_raising_attributor_reports_error_and_contributes_nothing():
    # Arrange
    broken = _StubAttributor(raises=True)
    healthy = _StubAttributor(claims=[('.plan', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('broken', broken), ('healthy', healthy))

    # Assert — the sibling still contributes; the map is never blanked
    assert claims == [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['healthy']}]
    broken_report = _report_for(reports, 'broken')
    assert broken_report['status'] == 'error'
    assert broken_report['claim_count'] == 0
    assert broken_report['notes'] != []


def test_non_iterable_claims_value_reports_error_rather_than_raising():
    # Arrange — a truthy non-iterable claims value is a broken-implementor
    # condition of exactly the same class as a raising ``claim_paths()``:
    # iterating it outside the guard would let a TypeError escape and blank the
    # whole ownership map.
    broken = _StubAttributor(claims=123)
    healthy = _StubAttributor(claims=[('.plan', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('broken', broken), ('healthy', healthy))

    # Assert — the sibling still contributes; the map is never blanked
    assert claims == [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['healthy']}]
    broken_report = _report_for(reports, 'broken')
    assert broken_report['status'] == 'error'
    assert broken_report['claim_count'] == 0
    assert broken_report['notes'] != []


def test_string_claims_value_reports_error_rather_than_iterating_characters():
    # Arrange — a bare string IS iterable, so it would NOT raise: left
    # undefended it would silently iterate into characters and report one
    # malformed-candidate note per character, i.e. a broken implementor
    # misreported as a running one.
    broken = _StubAttributor(claims='.plan')
    healthy = _StubAttributor(claims=[('.plan', 'plan-marshall')])

    # Act
    claims, reports = _merge_with(('broken', broken), ('healthy', healthy))

    # Assert — the sibling still contributes; the map is never blanked
    assert claims == [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['healthy']}]
    broken_report = _report_for(reports, 'broken')
    assert broken_report['status'] == 'error'
    assert broken_report['claim_count'] == 0
    assert broken_report['notes'] != []


def test_falsy_non_iterable_claims_value_is_an_empty_claim_set_not_an_error():
    # Arrange — the guard must NOT reclassify a legitimately empty return as a
    # broken implementor: ``raw_claims or []`` keeps 0 / None / [] meaning
    # "ran and claimed nothing".
    attributor = _StubAttributor(claims=0)

    # Act
    claims, reports = _merge_with(('quiet', attributor))

    # Assert — a positive negative, not an error report
    assert claims == []
    assert reports == [{'id': 'quiet', 'claim_count': 0, 'status': 'ok', 'notes': []}]


def test_record_missing_its_module_key_reports_error_rather_than_raising():
    # Arrange — a malformed discovery record is a broken-implementor condition
    records = [{'origin': 'origin-broken', 'id': 'broken'}]

    # Act
    claims, reports = _merge.merge_path_claims(records, _MODULES)

    # Assert
    assert claims == []
    assert reports[0]['status'] == 'error'


# =============================================================================
# Deterministic ordering
# =============================================================================


def test_claims_are_sorted_by_prefix_then_module():
    # Arrange — supplied deliberately out of order
    attributor = _StubAttributor(
        claims=[('other', 'other'), ('.plan', 'plan-marshall'), ('doc', 'documentation')]
    )

    # Act
    claims, _ = _merge_with(('alpha', attributor))

    # Assert — byte-stable output
    assert [claim['prefix'] for claim in claims] == ['.plan', 'doc', 'other']


def test_reports_follow_the_supplied_attributor_order():
    # Arrange
    claims, reports = _merge_with(
        ('zeta', _StubAttributor()), ('alpha', _StubAttributor())
    )

    # Assert — report order mirrors the input, not an alphabetical re-sort
    assert claims == []
    assert [rep['id'] for rep in reports] == ['zeta', 'alpha']


# =============================================================================
# lookup_claim — longest-prefix containment with the nest-inside guard
# =============================================================================


def test_lookup_claim_matches_a_bare_root_segment_claim():
    # Arrange — the boundary case a fnmatch ``**/`` shape would miss
    claims = [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]

    # Act / Assert
    assert _merge.lookup_claim('.plan/execute-script.py', claims) == 'plan-marshall'


def test_lookup_claim_matches_the_claimed_directory_itself():
    # Arrange
    claims = [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]

    # Act / Assert — ``path == prefix`` is the first half of the predicate
    assert _merge.lookup_claim('.plan', claims) == 'plan-marshall'


def test_lookup_claim_matches_a_deeply_nested_path():
    # Arrange
    claims = [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]

    # Act / Assert
    assert _merge.lookup_claim('.plan/local/plans/x/status.json', claims) == 'plan-marshall'


def test_lookup_claim_does_not_match_a_sibling_sharing_the_string_prefix():
    # Arrange — the nest-inside guard: ``.plans`` is NOT inside ``.plan``
    claims = [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]

    # Act / Assert
    assert _merge.lookup_claim('.plans/x', claims) is None


def test_lookup_claim_resolves_the_longest_containing_prefix():
    # Arrange — two differently-scoped prefixes both contain the path. This is
    # resolution ORDER, not a tie-break over a collision: both claims are
    # well-formed and neither was suppressed.
    claims = [
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']},
        {'prefix': '.plan/local', 'module': 'other', 'producers': ['zeta']},
    ]

    # Act / Assert
    assert _merge.lookup_claim('.plan/local/x', claims) == 'other'
    assert _merge.lookup_claim('.plan/marshal.json', claims) == 'plan-marshall'


def test_lookup_claim_longest_prefix_wins_regardless_of_claim_order():
    # Arrange — the same two claims supplied in the opposite order
    claims = [
        {'prefix': '.plan/local', 'module': 'other', 'producers': ['zeta']},
        {'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']},
    ]

    # Act / Assert — the result is a property of prefix length, not list position
    assert _merge.lookup_claim('.plan/local/x', claims) == 'other'


def test_lookup_claim_returns_none_when_no_claim_contains_the_path():
    # Arrange
    claims = [{'prefix': '.plan', 'module': 'plan-marshall', 'producers': ['alpha']}]

    # Act / Assert
    assert _merge.lookup_claim('marketplace/bundles/x.py', claims) is None


def test_lookup_claim_returns_none_against_an_empty_claim_list():
    # Act / Assert — the null-on-absent outcome at the lookup site
    assert _merge.lookup_claim('.plan/execute-script.py', []) is None


def test_lookup_claim_consumes_the_merge_output_end_to_end():
    # Arrange — the two claims the seam ships, produced by the real merge
    attributor = _StubAttributor(
        claims=[('.claude/skills', 'plan-marshall'), ('.plan', 'plan-marshall')]
    )
    claims, _ = _merge_with(('plan-marshall', attributor))

    # Act / Assert — merge output feeds the matcher without reshaping
    assert _merge.lookup_claim('.plan/execute-script.py', claims) == 'plan-marshall'
    assert _merge.lookup_claim('.claude/skills/foo/SKILL.md', claims) == 'plan-marshall'
    assert _merge.lookup_claim('.claude/settings.json', claims) is None
