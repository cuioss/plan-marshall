#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-level footprint-derivation aggregate in ``compile-report``.

Every footprint-consuming aspect already degrades honestly on its own when the
shared derivation cannot be resolved. The aggregate adds the statement none of
them can make alone — that they went unmeasurable *together*, on the same missing
derivation — and it must make that statement only when it is true:

* the positive fire, with the roster named and the counts reconciling;
* the matched control, where every producer resolves and NO record is emitted;
* the partial-coverage state, where an unread member suppresses the verdict
  rather than letting an aggregate rest on a roster it did not fully read;
* a mixed roster, which is not the signal and so emits nothing.

Two vacuity shapes are closed explicitly. The roster is asserted **derived** — a
footprint-consuming aspect added to the registry grows ``producer_count`` with no
change to the consumer — and the positive fire is asserted against the **rendered
report text**, because a record that is computed and never emitted is the failure
mode a test stopping at the returned dict cannot see.

The degradation probe's key/value split has its own matched pair, because that is
where this feature is one line away from being unable to fire at all:
``check-artifact-consistency`` publishes a ``summary.inconclusive`` COUNTER on
every run, so a probe that matched dict keys would read a perfectly clean plan as
degraded.
"""

from __future__ import annotations

import copy
from argparse import Namespace
from pathlib import Path

import retro_sections as _rs
from toon_parser import serialize_toon

from conftest import load_script_module

_cr = load_script_module(
    'plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_footprint_aggregate_mod'
)

_AGGREGATE_HEADING = 'Footprint Derivation Coverage'


# =============================================================================
# Fragment builders — the REAL shapes the producers emit
# =============================================================================


def _artifact_consistency(*, degraded: bool) -> dict:
    """``check-artifact-consistency``. The clean shape carries the counter trap.

    ``summary.inconclusive`` is present on BOTH shapes — as a key — and is ``0``
    on the clean one. That is the whole reason the probe reads values only.
    """
    status = 'inconclusive' if degraded else 'pass'
    message = 'footprint could not be resolved' if degraded else 'Recall 100% meets threshold'
    return {
        'status': 'success',
        'aspect': 'artifact_consistency',
        'checks': [{'name': 'affected_files_recall', 'status': status, 'message': message}],
        'summary': {'passed': 5, 'failed': 0, 'skipped': 0, 'inconclusive': 1 if degraded else 0},
        'findings': [],
    }


def _log_analysis(*, degraded: bool) -> dict:
    """``analyze-logs``. Its token is embedded in a finding MESSAGE, not a value."""
    findings = (
        [{'severity': 'warning', 'message': 'ARTIFACT_COVERAGE_UNMEASURABLE: no tier resolved it'}]
        if degraded
        else []
    )
    return {
        'status': 'success',
        'aspect': 'log_analysis',
        'counts': {'work_entries': 80, 'errors_script': 0},
        'findings': findings,
    }


def _routing_decisions(*, degraded: bool) -> dict:
    """``check-routing-decisions``. Its token is an exact per-check status value."""
    return {
        'status': 'success',
        'aspect': 'routing-decisions',
        'manifest_present': True,
        'mis_prune_checks': [
            {
                'check': 'mis_prune:sonar-roundtrip',
                'status': 'inconclusive' if degraded else 'pass',
                'predicate': 'no_code_delta',
                'detail': 'step ran',
            }
        ],
    }


_BUILDERS = {
    'artifact-consistency': _artifact_consistency,
    'log-analysis': _log_analysis,
    'routing-decisions': _routing_decisions,
}


def _fragments(*, degraded: bool) -> dict:
    """A bundle covering every registry-derived roster member with a real shape.

    Filtered by :data:`_BUILDERS` rather than assuming one exists for every roster
    key, so a test that EXTENDS the roster (the derivation proof below) supplies
    its own synthetic fragment instead of failing here on a missing builder.
    """
    return {
        key: _BUILDERS[key](degraded=degraded)
        for key in _rs.footprint_consuming_aspect_keys()
        if key in _BUILDERS
    }


def _plan_dir(tmp_path: Path, *, compose_degraded: bool | None) -> Path:
    """A plan directory whose manifest carries / omits the compose-time token.

    ``compose_degraded=None`` writes NO manifest at all, which is the unread
    state — distinct from a manifest that was read and reported nothing.
    """
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    if compose_degraded is None:
        return plan_dir
    body = 'manifest_version: 1\n'
    if compose_degraded:
        body += f'phase_6_state: {_rs.COMPOSE_TIME_DEGRADED_TOKEN}\n'
    (plan_dir / _rs.COMPOSE_TIME_ARTIFACT).write_text(body, encoding='utf-8')
    return plan_dir


# =============================================================================
# The roster is DERIVED from the registry
# =============================================================================


class TestRosterIsDerived:
    """A hard-coded roster drifts from its source; a derived one cannot."""

    def test_every_roster_member_is_a_registry_row(self):
        spec_keys = {fragment_key for _h, fragment_key, _t in _rs.SECTION_SPEC}
        assert set(_rs.footprint_consuming_aspect_keys()) <= spec_keys

    def test_the_roster_is_walked_in_registry_order(self):
        spec_order = [fragment_key for _h, fragment_key, _t in _rs.SECTION_SPEC]
        roster = list(_rs.footprint_consuming_aspect_keys())
        assert roster == [key for key in spec_order if key in set(roster)]

    def test_a_declared_consumer_with_no_registry_row_contributes_nothing(self, monkeypatch):
        """It has no fragment to read, so counting it would invent an unread member."""
        monkeypatch.setattr(
            _rs, 'FOOTPRINT_CONSUMING_ASPECTS', (*_rs.FOOTPRINT_CONSUMING_ASPECTS, 'not-a-row')
        )
        assert 'not-a-row' not in _rs.footprint_consuming_aspect_keys()

    def test_adding_a_consuming_aspect_to_the_registry_grows_producer_count(
        self, tmp_path, monkeypatch
    ):
        """The derivation proof: the roster grows with the registry, not with an edit here.

        Both the registry row and the consumer declaration are extended — the two
        steps any new aspect takes anyway — and ``producer_count`` follows with no
        change to ``compile-report``.
        """
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)
        before = _cr.footprint_derivation_record(_fragments(degraded=True), plan_dir)

        monkeypatch.setattr(
            _rs, 'SECTION_SPEC', (*_rs.SECTION_SPEC, ('New Aspect', 'new-aspect', None))
        )
        monkeypatch.setattr(
            _rs, 'FOOTPRINT_CONSUMING_ASPECTS', (*_rs.FOOTPRINT_CONSUMING_ASPECTS, 'new-aspect')
        )
        fragments = _fragments(degraded=True)
        fragments['new-aspect'] = {'status': 'success', 'verdict': 'inconclusive'}

        after = _cr.footprint_derivation_record(fragments, plan_dir)

        assert after['producer_count'] == before['producer_count'] + 1
        assert 'new-aspect' in [p['producer'] for p in after['producers']]


# =============================================================================
# The degradation probe reads VALUES, never keys
# =============================================================================


class TestDegradationProbeKeyValueSplit:
    """The matched pair that keeps the aggregate able to fire at all."""

    def test_a_clean_fragment_carrying_a_zero_inconclusive_counter_is_not_degraded(self):
        """The trap: ``summary.inconclusive`` is a KEY on every clean run."""
        clean = _artifact_consistency(degraded=False)
        assert clean['summary']['inconclusive'] == 0
        assert _cr._declares_degraded(clean, _rs.FOOTPRINT_DEGRADED_TOKENS) is False

    def test_the_same_fragment_shape_with_the_token_as_a_status_value_is_degraded(self):
        """The matched positive: same shape, the token moved into a VALUE."""
        assert _cr._declares_degraded(
            _artifact_consistency(degraded=True), _rs.FOOTPRINT_DEGRADED_TOKENS
        ) is True

    def test_a_token_embedded_in_a_finding_message_is_degraded(self):
        """``analyze-logs`` never emits its token bare — an equality probe would miss it."""
        assert _cr._declares_degraded(
            _log_analysis(degraded=True), _rs.FOOTPRINT_DEGRADED_TOKENS
        ) is True
        assert _cr._declares_degraded(
            _log_analysis(degraded=False), _rs.FOOTPRINT_DEGRADED_TOKENS
        ) is False


# =============================================================================
# The compose-time member's three states
# =============================================================================


class TestComposeTimeProducer:
    """Absent, read-and-clean, and read-and-degraded are three answers."""

    def test_an_absent_manifest_is_unread_not_resolved(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=None)
        assert _cr._compose_time_producer_verdict(plan_dir) == _rs.PRODUCER_UNREAD

    def test_a_manifest_without_the_token_is_resolved(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=False)
        assert _cr._compose_time_producer_verdict(plan_dir) == _rs.PRODUCER_RESOLVED

    def test_a_manifest_carrying_the_token_is_degraded(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)
        assert _cr._compose_time_producer_verdict(plan_dir) == _rs.PRODUCER_DEGRADED


# =============================================================================
# Positive fire, matched control, and the two suppressing states
# =============================================================================


class TestAggregateStates:
    """One record when they all failed together — and nothing otherwise."""

    def test_positive_fire_names_every_producer_and_reconciles_its_counts(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)

        record = _cr.footprint_derivation_record(_fragments(degraded=True), plan_dir)

        assert record['state'] == _rs.AGGREGATE_UNMEASURABLE
        assert record['degraded_count'] == record['producer_count']
        assert record['resolved_count'] == 0
        assert record['unread_count'] == 0
        # Every count names the population behind it.
        assert (
            record['degraded_count'] + record['resolved_count'] + record['unread_count']
            == record['producer_count'] == len(record['producers'])
        )
        assert record['producer_count'] == len(_rs.footprint_consuming_aspect_keys()) + 1
        assert _rs.COMPOSE_TIME_PRODUCER in [p['producer'] for p in record['producers']]

    def test_the_two_roster_provenances_are_published_separately(self, tmp_path):
        """The derived half must stay distinguishable from the named one."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)

        record = _cr.footprint_derivation_record(_fragments(degraded=True), plan_dir)

        by_provenance = {p['provenance'] for p in record['producers']}
        assert by_provenance == {_rs.PROVENANCE_ASPECT_REGISTRY, _rs.PROVENANCE_COMPOSE_TIME}
        compose = [
            p for p in record['producers'] if p['provenance'] == _rs.PROVENANCE_COMPOSE_TIME
        ]
        assert len(compose) == 1
        assert record['roster_source']

    def test_matched_control_every_producer_resolves_and_no_record_is_emitted(self, tmp_path):
        """The must-not-fire half: the same roster, every member clean."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=False)

        assert _cr.footprint_derivation_record(_fragments(degraded=False), plan_dir) is None

    def test_an_unread_member_suppresses_the_verdict_into_partial_coverage(self, tmp_path):
        """A verdict over a roster that was not fully read asserts more than it measured."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=None)
        fragments = _fragments(degraded=True)

        record = _cr.footprint_derivation_record(fragments, plan_dir)

        assert record['state'] == _rs.AGGREGATE_PARTIAL_COVERAGE
        assert record['state'] != _rs.AGGREGATE_UNMEASURABLE
        assert record['unread_count'] == 1
        assert record['degraded_count'] == len(_rs.footprint_consuming_aspect_keys())

    def test_an_absent_aspect_fragment_counts_as_unread_not_resolved(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)
        fragments = _fragments(degraded=True)
        dropped = _rs.footprint_consuming_aspect_keys()[0]
        del fragments[dropped]

        record = _cr.footprint_derivation_record(fragments, plan_dir)

        assert record['state'] == _rs.AGGREGATE_PARTIAL_COVERAGE
        assert {'producer': dropped, 'verdict': _rs.PRODUCER_UNREAD,
                'provenance': _rs.PROVENANCE_ASPECT_REGISTRY} in record['producers']

    def test_a_mixed_roster_is_not_the_signal_and_emits_nothing(self, tmp_path):
        """They failed TOGETHER is the claim; one resolved member refutes it."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)
        fragments = _fragments(degraded=True)
        fragments['log-analysis'] = _log_analysis(degraded=False)

        assert _cr.footprint_derivation_record(fragments, plan_dir) is None

    def test_no_producer_fragment_is_modified(self, tmp_path):
        """The aggregate reads; it never rewrites a consumer's own report."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)
        fragments = _fragments(degraded=True)
        before = copy.deepcopy(fragments)

        _cr.footprint_derivation_record(fragments, plan_dir)

        assert fragments == before


# =============================================================================
# The section reaches the RENDERED document
# =============================================================================


def _run_compile(plan_dir: Path, fragments: dict) -> tuple[dict, str]:
    """Drive ``cmd_run`` end-to-end and return ``(result, rendered_document)``."""
    bundle = plan_dir / 'fragments.toon'
    bundle.write_text(serialize_toon(fragments), encoding='utf-8')
    args = Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
        fragments_file=str(bundle),
        session_id=None,
    )
    result = _cr.cmd_run(args)
    return result, Path(result['output_path']).read_text(encoding='utf-8')


class TestTheSectionIsRendered:
    """A record computed and never emitted is the failure a dict-only test misses."""

    def test_positive_fire_reaches_the_rendered_report(self, tmp_path):
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)

        result, document = _run_compile(plan_dir, _fragments(degraded=True))

        assert result['footprint_derivation_state'] == _rs.AGGREGATE_UNMEASURABLE
        assert f'## {_AGGREGATE_HEADING}' in document
        assert _AGGREGATE_HEADING in result['sections_written']

    def test_the_matched_control_renders_no_such_section(self, tmp_path):
        """Same pipeline, clean producers: the heading must be absent entirely."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=False)

        result, document = _run_compile(plan_dir, _fragments(degraded=False))

        assert result['footprint_derivation_state'] is None
        assert f'## {_AGGREGATE_HEADING}' not in document
        assert _AGGREGATE_HEADING not in result['sections_written']

    def test_the_rendered_section_names_the_degraded_producers(self, tmp_path):
        """Naming which producers degraded is the point of carrying the roster."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)

        _result, document = _run_compile(plan_dir, _fragments(degraded=True))

        for producer in _rs.footprint_consuming_aspect_keys():
            assert producer in document

    def test_the_aggregate_is_not_reported_as_an_unattributed_zero(self, tmp_path):
        """It carries a finding, so its section makes no bare zero claim."""
        plan_dir = _plan_dir(tmp_path, compose_degraded=True)

        result, _document = _run_compile(plan_dir, _fragments(degraded=True))

        assert _AGGREGATE_HEADING not in result['sections_unattributed_zero']
