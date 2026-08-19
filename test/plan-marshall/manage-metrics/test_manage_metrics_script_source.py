#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


from pathlib import Path

import pytest
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
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
    cmd_end_phase,
    cmd_start_phase,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


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


def test_exploration_buckets_match_platform_runtime_contract():
    """``_EXPLORATION_BUCKETS`` matches the bucket set the runtime contract declares.

    Contract-level drift guard for the cross-process hand-mirror: the bucket names
    are recovered from the contract's ``*_tool_calls`` keys, so adding a bucket to
    the producer without extending ``_EXPLORATION_BUCKETS`` fails loudly here.
    """
    contract_buckets = {
        key[: -len('_tool_calls')]
        for key in _contract_counter_keys()
        if key.endswith('_tool_calls')
    }

    assert contract_buckets, 'contract declares no *_tool_calls counter keys'
    assert set(manage_metrics._EXPLORATION_BUCKETS) == contract_buckets
    # The mirror must also stay duplicate-free — a repeated name would silently
    # double a bucket's counter fields below.
    assert len(manage_metrics._EXPLORATION_BUCKETS) == len(contract_buckets)


def test_exploration_counter_fields_match_platform_runtime_contract():
    """``_EXPLORATION_COUNTER_FIELDS`` equals the contract's counter key set exactly.

    The derived ``{bucket}_{measure}`` product must reproduce the contract's ten
    published counter keys — no extra field manage-metrics would persist but the
    producer never emits, and no missing field the producer emits but the report
    would drop.
    """
    assert set(manage_metrics._EXPLORATION_COUNTER_FIELDS) == _contract_counter_keys()


def test_cache_read_attribution_fields_match_platform_runtime_contract():
    """``_CACHE_READ_ATTRIBUTION_FIELDS`` equals the contract's attribution key set exactly.

    The derived product over ``_EXPLORATION_BUCKETS`` plus the residual literal must
    reproduce the published group — no field manage-metrics would persist that the
    producer never emits, and no field the producer emits that the report drops.
    """
    contract_keys = _contract_attribution_keys()

    assert contract_keys, 'contract declares no cache-read attribution keys'
    assert set(manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS) == contract_keys
    # The residual is a member of the group, not an optional extra: dropping it
    # would turn a partial split into an apparently complete one.
    assert 'cache_read_unattributed' in contract_keys


def test_exploration_subsource_fields_match_platform_runtime_contract():
    """``_EXPLORATION_SUBSOURCE_FIELDS`` equals the contract's sub-source key set exactly.

    Same cross-process hand-mirror guard as the two drift tests above: a
    sub-source added on the producer side without extending the mirror would
    silently under-persist and under-render, and fails loudly here instead.
    """
    contract_keys = _contract_subsource_keys()

    assert contract_keys, 'contract declares no exploration sub-source keys'
    assert set(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS) == contract_keys
    # The mirror stays duplicate-free — a repeated name would double a field.
    assert len(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS) == len(contract_keys)


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


def test_enrich_labels_a_zero_dispatch_phase_as_inline(plan_context, monkeypatch):
    """The inline fold still happens — and the row says so, twice.

    The folded figure lands in `total_tokens` (so the phase stays countable) AND
    under its own population-honest name `inline_main_context_tokens`, with
    `total_tokens_population: inline` naming which population `total_tokens`
    measures here. Reading the figure ONLY through the dispatched-population
    field is what the second record removes.
    """
    plan_id = 'population-inline-only'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']

    row = _phase_row(plan_id, '1-init')
    assert row['total_tokens'] == _INLINE_SUM
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['total_tokens_population'] == manage_metrics.POPULATION_INLINE
