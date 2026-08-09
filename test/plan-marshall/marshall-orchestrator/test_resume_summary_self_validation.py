#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``resume-summary``'s two self-validation detectors.

Both detectors run on the RENDERED START-HERE block rather than on its inputs,
because in every recorded divergence the inputs were individually fine and the
rendering combined them wrongly — a narrated anchor sentence and the
generator's own enumeration disagreeing inside ONE emission. Every fixture here
is therefore built the same way: a well-formed ``status.json`` whose fields are
each individually valid, rendered into a block that is not.

- **Derived-count parity** (``count_divergences[]``) — a count the block claims
  against the count re-derived from ``plans[]``. Matched pair: a seeded
  disagreement, and a corpus whose narration is correct. Plus the near-miss the
  detector must stay silent on — the **denominator trap**, where two counts over
  DIFFERENT populations are correctly different and reporting them would be the
  false positive that teaches readers to ignore the detector.
- **Within-rendering self-contradiction** (``contradictions[]``) — two claims
  that cannot both hold in one rendering while each is individually plausible.
  Matched pair: the recorded ``AT CAP`` / ``genuinely free`` shape, and a
  rendering whose repeated claim agrees with itself. Plus a near-miss where the
  two claims are over different denominators and so do not conflict.

Every negative control runs over a NON-EMPTY claim population, and each list's
scanned count is asserted alongside it — a detector that scanned nothing would
otherwise report the same clean zero as one that scanned and found nothing.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_resume_summary = _orch.cmd_resume_summary

SLUG = 'fixture-selfvalidation-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, status: str = 'staged') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context, rows: list, resume_anchor: str) -> Path:
    """Write a status.json whose FIELDS are each individually well-formed.

    The anchor is prose an operator wrote and the queue is a valid row list;
    neither is malformed on its own. Anything the detectors find therefore comes
    from the rendering that combines them, which is the property under test.
    """
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Self-Validation Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': resume_anchor,
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


#: A three-row queue: two shipped, one staged. Small enough that every derived
#: count is obvious, and non-empty so no assertion below can pass vacuously.
THREE_ROWS = [_row('PLAN-01', 'shipped'), _row('PLAN-02', 'shipped'), _row('PLAN-03', 'staged')]


def _run() -> dict:
    result: dict = cmd_resume_summary(Namespace(slug=SLUG))
    return result


# =============================================================================
# Payload shape — each list rides with the population it was computed over
# =============================================================================


class TestSelfValidationPayload:
    def test_both_detector_fields_ride_beside_the_summary(self, plan_context):
        _write_status(plan_context, THREE_ROWS, 'Epic total: 3 rows and 2 shipped.')

        result = _run()

        assert result['status'] == 'success'
        assert result['summary']
        for count_field, population_field in (
            ('count_divergences_count', 'count_claims_scanned'),
            ('contradictions_count', 'ratio_claims_scanned'),
        ):
            assert count_field in result
            assert population_field in result
        assert result['count_divergences_count'] == len(result['count_divergences'])
        assert result['contradictions_count'] == len(result['contradictions'])

    def test_should_error_when_status_json_is_absent(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='absent-selfvalidation-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# Detector (a) — derived-count parity
# =============================================================================


class TestCountDivergenceDetector:
    def test_should_report_a_narrated_count_that_the_queue_refutes(self, plan_context):
        # Positive control. Both halves are individually valid: the anchor is a
        # sentence an operator wrote, and the queue is a well-formed row list.
        _write_status(plan_context, THREE_ROWS, 'Ledger check: 81 rows total and 46 shipped.')

        result = _run()

        by_claim = {row['claim']: row for row in result['count_divergences']}
        assert by_claim['81 rows']['narrated'] == 81
        assert by_claim['81 rows']['derived'] == 3
        assert by_claim['46 shipped']['narrated'] == 46
        assert by_claim['46 shipped']['derived'] == 2
        assert result['count_divergences_count'] == 2
        assert result['count_claims_scanned'] == 2

    def test_the_detector_reads_the_rendering_not_the_inputs(self, plan_context):
        # The claim exists ONLY in the rendered block: the anchor is rendered
        # verbatim, and it is the rendering the detector scans.
        anchor = 'Ledger check: 81 rows total.'
        _write_status(plan_context, THREE_ROWS, anchor)

        result = _run()

        assert anchor in result['summary'], 'the claim must be present in the rendering'
        assert result['count_divergences'][0]['claim'] == '81 rows'

    def test_should_stay_silent_when_the_narration_matches_the_queue(self, plan_context):
        # Negative control over a REAL claim population — an anchor carrying no
        # counts at all would report the same clean zero vacuously.
        _write_status(plan_context, THREE_ROWS, 'Ledger check: 3 rows total and 2 shipped.')

        result = _run()

        assert result['count_divergences'] == []
        assert result['count_divergences_count'] == 0
        assert result['count_claims_scanned'] == 2, 'the claim population must be non-empty'

    def test_should_not_report_two_counts_over_different_populations(self, plan_context):
        # The DENOMINATOR TRAP near-miss: a scoped count is correctly different
        # from the whole-epic count, and flagging it would be a false positive.
        _write_status(
            plan_context, THREE_ROWS, 'Epic total: 3 rows. WS-01 holds 2 rows in that set.'
        )

        result = _run()

        assert result['count_divergences'] == []
        assert result['count_claims_scanned'] == 1, (
            'the scoped claim must be EXCLUDED from the scan rather than compared '
            'against the whole-epic derivation'
        )

    def test_should_report_a_per_status_claim_against_its_own_tally(self, plan_context):
        # The tally is per status, so a wrong `staged` count is caught even when
        # the total row count is narrated correctly.
        _write_status(plan_context, THREE_ROWS, 'Ledger check: 3 rows total and 9 staged.')

        result = _run()

        assert [row['claim'] for row in result['count_divergences']] == ['9 staged']
        assert result['count_divergences'][0]['derived'] == 1


# =============================================================================
# Detector (b) — within-rendering self-contradiction
# =============================================================================


class TestContradictionDetector:
    def test_should_report_two_claims_that_cannot_both_hold(self, plan_context):
        # Positive control, in the recorded shape: an AT-CAP line coexisting with
        # a genuinely-free line, each individually plausible.
        _write_status(
            plan_context,
            THREE_ROWS,
            'Capacity: R = 3 of 3 — AT CAP. Re-read: R = 0 of 3 so a slot is genuinely free.',
        )

        result = _run()

        assert result['contradictions_count'] == 1
        row = result['contradictions'][0]
        assert row['denominator'] == 3
        assert row['left'] == 'R = 3 of 3'
        assert row['right'] == 'R = 0 of 3'
        assert result['ratio_claims_scanned'] == 2

    def test_should_stay_silent_when_the_repeated_claim_agrees_with_itself(self, plan_context):
        # Negative control over a REAL claim population.
        _write_status(
            plan_context, THREE_ROWS, 'Capacity: R = 2 of 3 today. Re-checked: R = 2 of 3.'
        )

        result = _run()

        assert result['contradictions'] == []
        assert result['contradictions_count'] == 0
        assert result['ratio_claims_scanned'] == 2, 'the claim population must be non-empty'

    def test_should_not_report_claims_over_different_denominators(self, plan_context):
        # Near-miss: two capacity claims about DIFFERENT sets are not in
        # conflict, however different their numerators look side by side.
        _write_status(
            plan_context, THREE_ROWS, 'Capacity: R = 3 of 3 for WS-01. R = 0 of 5 for WS-02.'
        )

        result = _run()

        assert result['contradictions'] == []
        assert result['ratio_claims_scanned'] == 2


# =============================================================================
# Report-never-rewrite boundary
# =============================================================================


class TestSelfValidationIsReportOnly:
    def test_a_divergent_anchor_is_reported_and_rendered_verbatim(self, plan_context):
        # The existing derivation-beside-the-prose rule is preserved: the block
        # is never silently corrected, only annotated in the payload beside it.
        anchor = 'Ledger check: 81 rows total.'
        _write_status(plan_context, THREE_ROWS, anchor)

        result = _run()

        assert anchor in result['summary']
        assert '3 rows' not in result['summary'], 'the anchor must not be rewritten'
        assert result['count_divergences_count'] == 1

    def test_the_verb_leaves_the_fixture_tree_byte_identical(self, plan_context):
        _write_status(plan_context, THREE_ROWS, 'Capacity: R = 3 of 3 — AT CAP. R = 0 of 3.')
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = _run()

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['contradictions_count'] == 1, (
            'the report-only claim must be proven on a run that actually DETECTED something'
        )
