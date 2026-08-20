#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


from pathlib import Path

import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _DATA_FORMAT_MD,
    _INLINE_BUCKET,
    _INLINE_SUM,
    _LATTICE_POPULATIONS,
    _LOGGING_GAP_ANALYSIS_MD,
    _SKILL_MD,
    _UNSEEDED_PLAN_IDS,
    SCRIPT_PATH,
    _assert_documented_set_matches_enum,
    _contract_attribution_keys,
    _contract_counter_keys,
    _contract_subsource_keys,
    _derived_usage_fields,
    _fields_missing_from_lattice,
    _parse_lattice_directions,
    _parse_termination_cause_sites,
    _phase_row,
    _row_field,
    _run_enrich_with_buckets,
    _seed_guarded_plan_dirs,
    cmd_end_phase,
    cmd_start_phase,
    manage_metrics,
)


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: ``cmd_accumulate_agent_usage``'s
    docstring must spell the accumulator location as ``.plan/local/plans/`` — the
    legacy bare ``.plan/plans/`` form is incorrect since runtime state moved
    under ``.plan/local``.
    """
    import re

    source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'


def test_subsource_group_is_disjoint_from_the_exploration_counter_group():
    """Matched control: the sub-sources are not a sixth bucket in the counter family.

    This is the assertion the ``_bytes``-not-``_result_bytes`` suffix choice
    exists to make possible — without it, a suffix-derivation bug could let
    ``_EXPLORATION_COUNTER_FIELDS`` swallow the sub-sources while its own
    set-equality test still passed against an equally-drifted contract.
    """
    counter_keys = _contract_counter_keys()
    subsource_keys = _contract_subsource_keys()

    assert not (subsource_keys & counter_keys), subsource_keys & counter_keys
    assert not (set(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS) & counter_keys)
    # The exploration counter family is unchanged by the sub-sources' arrival:
    # still exactly ten fields over the same five buckets.
    assert len(manage_metrics._EXPLORATION_COUNTER_FIELDS) == 10
    assert len(counter_keys) == 10
    assert len(manage_metrics._EXPLORATION_BUCKETS) == 5


def test_attribution_group_is_disjoint_from_the_exploration_counter_group():
    """Matched control: the two derived groups partition, they do not overlap.

    Without this, a suffix-matching bug on either side could let one group swallow
    the other's keys while both set-equality assertions above still passed.
    """
    counter_keys = _contract_counter_keys()
    attribution_keys = _contract_attribution_keys()

    assert not (attribution_keys & counter_keys), attribution_keys & counter_keys
    assert not (set(manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS) & counter_keys)
    # The exploration group is unchanged by the attribution group's arrival: still
    # five buckets x two measures.
    assert len(manage_metrics._EXPLORATION_COUNTER_FIELDS) == 10
    assert len(counter_keys) == 10


def test_lattice_names_every_usage_field_the_script_writes():
    """No token/usage field written by manage-metrics.py is absent from the lattice."""
    derived = _derived_usage_fields()
    assert derived, 'the script-derived field sweep produced nothing — the guard is vacuous'

    missing = _fields_missing_from_lattice(
        _DATA_FORMAT_MD.read_text(encoding='utf-8'), derived
    )

    assert missing == set(), (
        f'the lattice omits token/usage fields the script writes: {sorted(missing)}'
    )


def test_lattice_completeness_check_detects_a_removed_row():
    """Negative control: dropping one lattice row is caught.

    Guards the positive assertion above against a false pass — a completeness
    check that cannot fail proves nothing about the table it reads.
    """
    content = _DATA_FORMAT_MD.read_text(encoding='utf-8')
    derived = _derived_usage_fields()
    victim = 'subagent_total_tokens'
    assert victim in derived

    mutated = '\n'.join(
        line
        for line in content.splitlines()
        if not (line.startswith('|') and f'`{victim}`' in line)
    )
    assert mutated != content

    assert _fields_missing_from_lattice(mutated, derived) == {victim}


def test_lattice_carries_both_directions_with_known_populations():
    """Both directions are populated and every row names a known population.

    The "recorded but never rendered" direction is a first-class half of the
    lattice, so an empty Direction 2 table fails here rather than reading as an
    omitted footnote.
    """
    directions = _parse_lattice_directions(_DATA_FORMAT_MD.read_text(encoding='utf-8'))

    assert set(directions) == {'1', '2'}, f'unexpected lattice directions: {sorted(directions)}'

    offenders: list[tuple[str, str, str]] = []
    for direction, rows in directions.items():
        assert rows, f'Direction {direction} table carries no rows'
        for cells in rows:
            field = _row_field(cells[0])
            if field is None:
                offenders.append((direction, cells[0], 'row names no field'))
                continue
            if cells[2] not in _LATTICE_POPULATIONS:
                offenders.append((direction, field, f'unknown population {cells[2]!r}'))
            if not cells[3]:
                offenders.append((direction, field, 'empty measurement method'))
            if not cells[4]:
                offenders.append((direction, field, 'empty rendered flag'))

    assert offenders == [], f'malformed lattice rows: {offenders}'


def test_every_documented_termination_cause_site_matches_the_enum():
    """Every discovered SKILL.md site enumerates exactly DISPATCH_TERMINATION_CAUSES.

    Asserting over a single parsed list would be insufficient — that is precisely
    what let a second and a third site drift out of sync with the live tuple.
    """
    expected = set(manage_metrics.DISPATCH_TERMINATION_CAUSES)
    sites = _parse_termination_cause_sites(_SKILL_MD.read_text(encoding='utf-8'))

    assert sites, 'no --termination-cause value list found in SKILL.md'

    stale = [
        (label, sorted(expected - values), sorted(values - expected))
        for label, values in sites
        if values != expected
    ]

    assert stale == [], (
        'SKILL.md sites disagree with DISPATCH_TERMINATION_CAUSES '
        f'(site, missing, unexpected): {stale}'
    )


def test_every_declared_population_has_a_bullet_note():
    """No population may render without a qualifier — derived, not hand-listed.

    `_POPULATION_BULLET_NOTE` is indexed unconditionally at the render site, so a
    population added to the tuple without a note would raise there. This asserts
    the coverage directly instead of waiting for a KeyError in a report.
    """
    missing = set(manage_metrics.TOKEN_POPULATIONS) - set(manage_metrics._POPULATION_BULLET_NOTE)
    assert missing == set(), f'populations with no rendered qualifier: {sorted(missing)}'


def test_termination_cause_sites_cover_both_documented_shapes():
    """More than one site exists, and both documented shapes are discovered.

    Anti-vacuity guard: if the scanner silently stopped matching one shape, the
    per-site assertion above would pass over a shrunken population.
    """
    sites = _parse_termination_cause_sites(_SKILL_MD.read_text(encoding='utf-8'))
    shapes = {label.rsplit('-', 1)[0] for label, _ in sites}

    assert 'brace-form' in shapes
    assert 'bullet-form' in shapes
    assert len(sites) > 1


def test_termination_cause_check_detects_a_single_stale_site():
    """Negative control: staleness at exactly ONE site is caught.

    Leaving one of several documented sites behind is the recurrence this guard
    exists for, so the check must fail on a single-site mutation rather than only
    on a wholesale one.
    """
    content = _SKILL_MD.read_text(encoding='utf-8')
    expected = set(manage_metrics.DISPATCH_TERMINATION_CAUSES)
    victim = 'error'
    assert victim in expected

    brace_sites = [
        label for label, _ in _parse_termination_cause_sites(content)
        if label.startswith('brace-form')
    ]
    assert len(brace_sites) > 1, 'need more than one brace site to prove single-site detection'

    # Drop the victim from exactly ONE brace-form occurrence. `error` sits in the
    # middle of the pipe list, so `|error|` -> `|` removes it without depending
    # on which value happens to be last in the enum (which changes when a member
    # is appended).
    mutated = content.replace(f'|{victim}|', '|', 1)
    assert mutated != content

    stale = [
        label for label, values in _parse_termination_cause_sites(mutated) if values != expected
    ]

    assert len(stale) == 1, f'expected exactly one stale site to be reported, got {stale}'


def test_logging_gap_analysis_termination_cause_set_matches_the_enum():
    """The DISPATCH_TERMINATION_CAUSE rule's canonical value set equals the tuple.

    The reference tells the analyst which value set to distribute dispatch rows
    over; a subset there produces a distribution that silently omits the omitted
    causes. Both sides are derived — the documented set from the markdown, the
    expected set from DISPATCH_TERMINATION_CAUSES.
    """
    _assert_documented_set_matches_enum(
        _LOGGING_GAP_ANALYSIS_MD.read_text(encoding='utf-8'), 'the accepted causes:'
    )


def test_logging_gap_analysis_guard_detects_a_dropped_value():
    """Negative control: the guard's own ``==`` assertion FAILS on a dropped value.

    Executes ``_assert_documented_set_matches_enum`` (the SAME assertion the
    positive test runs) against a mutated document and requires it to raise —
    proving the guard has a real, executable failure path, not merely that the
    parsed sets differ.
    """
    content = _LOGGING_GAP_ANALYSIS_MD.read_text(encoding='utf-8')
    victim = 'agent_returned'
    assert victim in set(manage_metrics.DISPATCH_TERMINATION_CAUSES)

    mutated = content.replace(f'`{victim}`', '', 1)
    assert mutated != content, 'the victim value was not present to drop'

    with pytest.raises(AssertionError, match='disagrees with DISPATCH_TERMINATION_CAUSES'):
        _assert_documented_set_matches_enum(mutated, 'the accepted causes:')


def test_data_format_termination_cause_enum_matches_the_enum():
    """The data-format.md dispatch-boundary termination_cause enum equals the tuple."""
    _assert_documented_set_matches_enum(
        _DATA_FORMAT_MD.read_text(encoding='utf-8'), '`termination_cause` enum**:'
    )


def test_data_format_termination_cause_guard_detects_a_dropped_value():
    """Negative control: the guard's own ``==`` assertion FAILS on a dropped value."""
    content = _DATA_FORMAT_MD.read_text(encoding='utf-8')
    victim = 'agent_returned'
    assert victim in set(manage_metrics.DISPATCH_TERMINATION_CAUSES)

    mutated = content.replace(f'`{victim}`', '', 1)
    assert mutated != content, 'the victim value was not present to drop'

    with pytest.raises(AssertionError, match='disagrees with DISPATCH_TERMINATION_CAUSES'):
        _assert_documented_set_matches_enum(mutated, '`termination_cause` enum**:')


def test_repeated_enrich_keeps_an_inline_only_row_labelled_inline(plan_context, monkeypatch):
    """A second enrich run must not read its OWN fold as a dispatched total.

    The inline branch writes `total_tokens`, so a branch keyed on
    `not total_tokens` is self-defeating: run two sees run one's fold, falls
    through to the mixed branch, and stamps `mixed` on a row where nothing was
    ever dispatched. Re-invocation is the ordinary case — `record-metrics` runs
    enrich on every finalize entry and a loop-back re-enters it — so a
    single-run assertion proves nothing about the stamp a report actually reads.
    """
    plan_id = 'population-enrich-idempotent-inline'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']
    first = dict(_phase_row(plan_id, '1-init'))
    assert first['total_tokens_population'] == manage_metrics.POPULATION_INLINE
    assert first['total_tokens'] == _INLINE_SUM

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']
    second = _phase_row(plan_id, '1-init')

    # The discriminator survives the re-run, and the folded figure is unchanged —
    # the second run recognised its own prior fold instead of re-classifying it.
    assert second['total_tokens_population'] == manage_metrics.POPULATION_INLINE
    assert second['total_tokens'] == first['total_tokens']
    assert second['inline_main_context_tokens'] == _INLINE_SUM


def test_repeated_enrich_keeps_a_genuinely_mixed_row_labelled_mixed(plan_context, monkeypatch):
    """Matched control: the idempotence fix does not disable the `mixed` stamp.

    Keying the inline branch off the discriminator could have been "widened" into
    never reaching the mixed branch at all, which would pass the inline test
    above while destroying the signature it exists to distinguish. A row carrying
    a REAL dispatched total plus inline spend must still read `mixed` on the
    first run and on every run after it.
    """
    plan_id = 'population-enrich-idempotent-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    assert _phase_row(plan_id, '6-finalize')['total_tokens_population'] == (
        manage_metrics.POPULATION_MIXED
    )

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})
    row = _phase_row(plan_id, '6-finalize')

    assert row['total_tokens_population'] == manage_metrics.POPULATION_MIXED
    assert row['total_tokens'] == 88000, 'the dispatched total must never be overwritten'
    assert row['inline_main_context_tokens'] == _INLINE_SUM
