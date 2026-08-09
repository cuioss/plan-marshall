#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``corpus`` verb group of the marshall-orchestrator script.

Covers the three sub-verbs against a SCAFFOLDED FIXTURE EPIC under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree:

- ``corpus enumerate``: the bidirectional reconciliation of ``status.json``'s
  ``plans[]`` queue against the ``plans/PLAN-*.md`` spec files, with every count
  riding beside the population it was computed over.
- ``corpus verdicts``: the sole interpreter of the re-grounding verdict field —
  one control per row of the admission table in
  ``persona-marshall-orchestrator/standards/orchestration-model.md``
  § Re-Grounding Verdict Field.
- ``corpus set-verdict``: the sole emitter of that field — in-place replacement,
  and each rejection path proven to reject WITHOUT writing.

Every detector carries a matched pair. The positive controls are seeded defects
(an orphan row, an orphan spec, an unreadable spec, a blocking verdict); the
negative controls are legitimate near-misses that must stay silent (a fully
reconciled corpus, a ``running`` row that is present-but-excluded rather than
missing, an ``unverifiable`` verdict that must NOT be read as a refutation).

Two population guards keep the module non-vacuous: the fixture-materialization
guard below fails loudly when the fixture epic did not land on disk, and the
single-implementation guard enumerates the marketplace Python surface at test
time rather than asserting against a hard-coded file list.

Note on the rejection contract: these scripts follow the canonical output
contract, so a rejected call returns a ``status: error`` TOON envelope rather
than raising a Python exception. Each rejection test therefore asserts BOTH the
error envelope AND that the spec file is byte-identical afterwards — the "rejects
instead of writing" obligation is about the disk, not about the exception type.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_corpus_enumerate = _orch.cmd_corpus_enumerate
cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
format_verdict_line = _orch._format_verdict_line
parse_verdict_text = _orch._parse_verdict_text
VERDICT_KEYS = _orch.VERDICT_KEYS
VERDICT_SEPARATOR = _orch.VERDICT_SEPARATOR
VERDICT_VALUES = _orch.VERDICT_VALUES
RESCOPED_VALUES = _orch.RESCOPED_VALUES

SLUG = 'fixture-corpus-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
SHA = '9f3a1c2'
OTHER_SHA = 'abc1234'
PRODUCER = 'fixture-corpus-epic/cleanup'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context, slug: str = SLUG) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


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


def _write_status(plan_context, rows: list, slug: str = SLUG) -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Corpus Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _spec_text(claim_lines: list) -> str:
    """Render a minimal spec carrying a ``## Claim Labels`` section."""
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        'Fixture objective.',
        '',
        '## Claim Labels',
        '',
        *claim_lines,
        '',
        '## Expected Surface',
        '',
        '- OBSERVED: `a.py` — `f`',
    ]
    return '\n'.join(lines) + '\n'


def _write_spec(plan_context, name: str, claim_lines: list | None = None) -> Path:
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_spec_text(claim_lines or ['- OBSERVED: a claim — read at `a.py` § `f`']), encoding='utf-8')
    return path


def _verdict_bullet(verdict: str, rescoped: str, evidence: str = 'checked', checked_at: str = SHA) -> str:
    body = VERDICT_SEPARATOR.join(
        (
            f'verdict: {verdict}',
            f'checked_at: {checked_at}',
            f'by: {PRODUCER}',
            f'rescoped: {rescoped}',
            f'evidence: {evidence}',
        )
    )
    return f'  - {body}'


def _set_verdict_args(
    plan: str,
    claim_index: int,
    verdict: str = 'corroborated',
    rescoped: str = 'n/a',
    evidence: str = 'holds at this sha',
    checked_at: str = SHA,
    by: str = PRODUCER,
    slug: str = SLUG,
) -> Namespace:
    """Build a complete ``set-verdict`` Namespace so every flag attribute exists."""
    return Namespace(
        slug=slug,
        plan=plan,
        claim_index=claim_index,
        verdict=verdict,
        checked_at=checked_at,
        by=by,
        rescoped=rescoped,
        evidence=evidence,
    )


# =============================================================================
# corpus enumerate — population guard and the two directions
# =============================================================================


class TestCorpusEnumeratePopulation:
    def test_should_report_a_materialized_fixture_population(self, plan_context):
        """Non-empty-population guard: a fixture that did not land must fail loudly."""
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-enumerate'
        assert result['rows_total'] == 2, 'fixture queue did not materialize'
        assert result['specs_total'] == 2, 'fixture spec files did not materialize'
        assert result['rows_scanned'] == 2
        assert result['specs_scanned'] == 2

    def test_should_ride_every_count_beside_its_population(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        for count_field, population_field in (
            ('rows_without_spec_count', 'rows_total'),
            ('specs_without_row_count', 'specs_total'),
            ('unreadable_count', 'specs_total'),
        ):
            assert count_field in result
            assert population_field in result

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_corpus_enumerate(Namespace(slug='absent-corpus-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_enumerate(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestCorpusEnumerateDirections:
    """The two directions are separate defects with separate causes."""

    def test_should_report_a_seeded_orphan_row(self, plan_context):
        # Positive control for direction one: a queue row whose spec is absent.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec'] == [{'id': 'PLAN-02', 'status': 'staged'}]
        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row_count'] == 0

    def test_should_report_a_seeded_orphan_spec(self, plan_context):
        # Positive control for direction two, asserted INDEPENDENTLY of the first.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-09-unqueued.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['specs_without_row'] == ['PLAN-09-unqueued.md']
        assert result['specs_without_row_count'] == 1
        assert result['rows_without_spec_count'] == 0

    def test_should_report_zero_in_both_directions_for_a_reconciled_corpus(self, plan_context):
        # Negative control: a legitimate near-miss (a real, fully-reconciled
        # corpus), not an empty input — an empty corpus would report zero
        # vacuously.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec_count'] == 0
        assert result['specs_without_row_count'] == 0
        assert result['rows_total'] == 2
        assert result['specs_total'] == 2

    def test_should_not_confuse_a_prefix_row_id_with_a_longer_one(self, plan_context):
        # PLAN-1 must not claim PLAN-10's spec: the separating hyphen is what
        # keeps the exact-or-prefix match honest.
        _write_status(plan_context, [_row('PLAN-1')])
        _write_spec(plan_context, 'PLAN-10-decoy.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row'] == ['PLAN-10-decoy.md']

    def test_should_enumerate_from_status_json_not_from_a_plans_glob(self, plan_context):
        """The authority is ``plans[]``; a directory glob returns a DIFFERENT set."""
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-02-orphan.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        glob_stems = sorted(path.stem for path in (_epic_dir(plan_context) / 'plans').glob('PLAN-*.md'))
        row_ids = sorted(row['id'] for row in result['rows'])
        assert row_ids == ['PLAN-01']
        assert glob_stems == ['PLAN-02-orphan']
        assert row_ids != glob_stems
        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row_count'] == 1


class TestCorpusEnumerateRunningExclusion:
    def test_should_report_a_running_row_as_present_but_excluded(self, plan_context):
        # Positive control: the running row is ENUMERATED, carrying its reason.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        by_id = {row['id']: row for row in result['rows']}
        assert set(by_id) == {'PLAN-01', 'PLAN-02'}, 'a running row was omitted rather than excluded'
        assert by_id['PLAN-02']['excluded_reason'] == 'running'

    def test_should_leave_a_staged_row_unexcluded(self, plan_context):
        # Negative control: exclusion is status-scoped, not blanket.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows'][0]['excluded_reason'] == ''

    def test_should_tally_rows_by_status_over_the_scanned_population(self, plan_context):
        _write_status(
            plan_context,
            [_row('PLAN-01'), _row('PLAN-02', status='running'), _row('PLAN-03', status='shipped')],
        )

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status_tally'] == [
            {'status': 'running', 'count': 1},
            {'status': 'shipped', 'count': 1},
            {'status': 'staged', 'count': 1},
        ]
        assert sum(entry['count'] for entry in result['status_tally']) == result['rows_total']


class TestCorpusEnumerateUnreadable:
    def test_should_report_an_unreadable_spec_without_aborting(self, plan_context):
        # Positive control: report-never-skip. The enumeration still completes.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-02-broken.md'
        broken.write_bytes(b'\xff\xfe not valid utf-8 \xff')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['unreadable'] == [{'spec': 'PLAN-02-broken.md', 'error': 'unreadable'}]
        assert result['unreadable_count'] == 1
        assert result['specs_total'] == 2
        assert result['specs_scanned'] == 1, 'the unreadable spec must not count as scanned'

    def test_should_report_no_unreadable_specs_for_a_healthy_corpus(self, plan_context):
        # Negative control: a real corpus of readable specs, not an empty one.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['unreadable'] == []
        assert result['unreadable_count'] == 0
        assert result['specs_scanned'] == result['specs_total'] == 1


# =============================================================================
# corpus verdicts — one control per admission-table row
# =============================================================================

_ADMISSION_CLAIMS = [
    '- HYPOTHESIS: absent clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '- HYPOTHESIS: corroborated clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('corroborated', 'n/a', 'the branch is present at this sha'),
    '- HYPOTHESIS: unverifiable clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('unverifiable', 'n/a', 'the population could not be reached'),
    '- HYPOTHESIS: absorbed clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('contradicted', 'yes', 'refuted and the spec now reflects it'),
    '- HYPOTHESIS: blocking clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('contradicted', 'no', 'refuted and not yet re-scoped'),
    '- HYPOTHESIS: malformed clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '  - verdict: contradicted | checked_at: nothexvalue | by: x/y | rescoped: no | evidence: bad sha',
]

_MALFORMED_LINE = _ADMISSION_CLAIMS[-1].strip()


class TestCorpusVerdictsAdmissionTable:
    """One passing control per row of the admission table, plus its blocking pair."""

    def _rows(self, plan_context) -> dict:
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        assert result['status'] == 'success'
        assert result['claims_scanned'] == 6, 'the claim population did not materialize'
        return {row['claim_index']: row for row in result['claims']}

    def test_absent_field_yields_no_row_at_all(self, plan_context):
        rows = self._rows(plan_context)

        assert 0 not in rows, 'an unstamped claim must produce no verdict row'

    def test_corroborated_admits(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[1]['verdict'] == 'corroborated'
        assert rows[1]['admits'] is True
        assert rows[1]['rescoped'] == 'n/a'

    def test_unverifiable_admits(self, plan_context):
        # ⛔ An unreached population is not a refutation.
        rows = self._rows(plan_context)

        assert rows[2]['verdict'] == 'unverifiable'
        assert rows[2]['admits'] is True

    def test_contradicted_with_rescoped_yes_admits(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[3]['verdict'] == 'contradicted'
        assert rows[3]['rescoped'] == 'yes'
        assert rows[3]['admits'] is True

    def test_contradicted_with_rescoped_no_blocks(self, plan_context):
        # The ONE blocking settled state.
        rows = self._rows(plan_context)

        assert rows[4]['verdict'] == 'contradicted'
        assert rows[4]['rescoped'] == 'no'
        assert rows[4]['admits'] is False

    def test_malformed_blocks_and_is_quoted_never_dropped(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[5]['verdict'] == 'indeterminate'
        assert rows[5]['admits'] is False
        assert rows[5]['line'] == _MALFORMED_LINE

    def test_counts_ride_with_their_populations(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_total'] == 1
        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 6
        assert result['count'] == 5
        assert result['blocking_count'] == 2

    def test_a_zero_count_states_which_zero_it_is(self, plan_context):
        # A corpus of real, unstamped specs — not an empty corpus.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['count'] == 0
        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 1

    def test_should_report_an_unreadable_spec_rather_than_dropping_it(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-01-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe \xff')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['unreadable'] == [{'spec': 'PLAN-01-broken.md', 'error': 'unreadable'}]
        assert result['specs_scanned'] == 0
        assert result['specs_total'] == 1

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_verdicts(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestVerdictStaleness:
    def test_a_verdict_at_another_sha_is_reported_stale_yet_still_admits(self, plan_context):
        # Staleness is REPORTED, never promoted to blocking.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            [
                '- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
                _verdict_bullet('corroborated', 'n/a', 'held', checked_at=OTHER_SHA),
            ],
        )

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        row = result['claims'][0]

        if result['head_sha']:
            assert row['stale'] is True
        assert row['admits'] is True


# =============================================================================
# The parse rule — evidence is the remainder
# =============================================================================


class TestVerdictParseRule:
    def test_evidence_containing_the_separator_round_trips_byte_identically(self):
        """Negative control for a naive full split, at the emitter/parser pair."""
        evidence = 'left | middle | right'
        values = {
            'verdict': 'contradicted',
            'checked_at': SHA,
            'by': PRODUCER,
            'rescoped': 'no',
            'evidence': evidence,
        }

        parsed = parse_verdict_text(format_verdict_line(values))

        assert parsed is not None
        assert parsed['evidence'] == evidence
        assert parsed == values

    def test_evidence_containing_the_separator_survives_the_disk_round_trip(self, plan_context):
        evidence = 'left | middle | right'
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            ['- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)'],
        )

        cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no', evidence=evidence)
        )
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['claims'][0]['evidence'] == evidence

    def test_the_key_order_is_fixed(self):
        assert VERDICT_KEYS == ('verdict', 'checked_at', 'by', 'rescoped', 'evidence')

    def test_a_reordered_line_does_not_parse(self):
        reordered = VERDICT_SEPARATOR.join(
            (f'checked_at: {SHA}', 'verdict: corroborated', f'by: {PRODUCER}', 'rescoped: n/a', 'evidence: x')
        )

        assert parse_verdict_text(reordered) is None

    def test_a_verdict_outside_the_closed_set_does_not_parse(self):
        line = VERDICT_SEPARATOR.join(
            ('verdict: probably', f'checked_at: {SHA}', f'by: {PRODUCER}', 'rescoped: n/a', 'evidence: x')
        )

        assert parse_verdict_text(line) is None
        assert 'probably' not in VERDICT_VALUES

    def test_rescoped_no_on_a_non_refutation_does_not_parse(self):
        line = VERDICT_SEPARATOR.join(
            ('verdict: corroborated', f'checked_at: {SHA}', f'by: {PRODUCER}', 'rescoped: no', 'evidence: x')
        )

        assert parse_verdict_text(line) is None
        assert 'no' in RESCOPED_VALUES, 'the value is legal — only this COMBINATION is not'


# =============================================================================
# corpus set-verdict — the single write action
# =============================================================================

_ONE_CLAIM = ['- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)']

_TWO_CLAIMS = [
    '- HYPOTHESIS: first clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '- HYPOTHESIS: second clause — confirm/refute at `b.py` § `g` (verify-at-outline)',
]


class TestCorpusSetVerdict:
    def test_should_stamp_a_nested_bullet_under_the_addressed_claim(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-set-verdict'
        assert result['replaced'] is False
        assert result['claims_total'] == 1
        text = spec.read_text(encoding='utf-8')
        assert '  - verdict: corroborated' in text
        assert text.index(_ONE_CLAIM[0]) < text.index('  - verdict:')

    def test_should_bind_the_verdict_by_nesting_not_by_ordinal_position(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _TWO_CLAIMS)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 1
        assert result['claims'][0]['evidence'] == 'second only'

    def test_should_replace_an_existing_verdict_in_place(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        first = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='first pass'))
        second = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no', evidence='second pass')
        )

        assert first['replaced'] is False
        assert second['replaced'] is True
        assert 'first pass' in second['previous_line']
        text = spec.read_text(encoding='utf-8')
        assert text.count('- verdict:') == 1, 'a claim must never carry two verdicts'
        assert 'first pass' not in text
        assert 'second pass' in text

    def test_should_be_idempotent_on_an_identical_restamp(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))
        after_first = spec.read_bytes()
        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert spec.read_bytes() == after_first

    def test_should_preserve_the_trailing_newline(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert spec.read_text(encoding='utf-8').endswith('\n')

    def test_should_error_when_the_spec_is_absent(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-99', 0))

        assert result['status'] == 'error'
        assert result['error'] == 'spec_not_found'
        assert result['available_specs'] == ['PLAN-01-alpha.md']


class TestCorpusSetVerdictRejections:
    """Each rejection path rejects WITHOUT writing — asserted against the bytes."""

    def _spec(self, plan_context) -> Path:
        _write_status(plan_context, [_row('PLAN-01')])
        return _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

    def test_should_reject_a_rescoped_verdict_combination_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='corroborated', rescoped='no')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_rescoped_combination'
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_range_claim_index_without_appending(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 7))

        assert result['status'] == 'error'
        assert result['error'] == 'claim_index_out_of_range'
        assert result['claims_total'] == 1
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_set_verdict_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, verdict='probably'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_verdict'
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_set_rescoped_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='maybe')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_rescoped'
        assert spec.read_bytes() == before

    def test_should_reject_a_non_hex_checked_at_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, checked_at='HEAD'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_checked_at'
        assert spec.read_bytes() == before

    def test_should_reject_empty_evidence_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='   '))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'
        assert spec.read_bytes() == before

    def test_should_accept_the_legal_counterpart_of_each_rejection(self, plan_context):
        """Negative control: the rejections are combination-scoped, not blanket."""
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no')
        )

        assert result['status'] == 'success'
        assert spec.read_bytes() != before


# =============================================================================
# Read-only boundary
# =============================================================================


class TestCorpusReadOnlyBoundary:
    def test_enumerate_and_verdicts_leave_the_tree_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)
        _write_spec(plan_context, 'PLAN-02-beta.md', _ONE_CLAIM)
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        cmd_corpus_enumerate(Namespace(slug=SLUG))
        cmd_corpus_verdicts(Namespace(slug=SLUG))

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before


# =============================================================================
# Single-implementation guard (population-derived)
# =============================================================================


#: The code-level signature of the verdict grammar: the distinctive key names
#: together with the separator literal. A second formatter or parser cannot be
#: written without carrying all three.
_GRAMMAR_SIGNATURE = ('checked_at', 'rescoped', VERDICT_SEPARATOR)


def _marketplace_modules() -> list:
    return sorted(MARKETPLACE_ROOT.rglob('*.py'))


def test_marketplace_module_population_is_non_empty():
    """Guards the single-implementation assertion below against a vacuous pass."""
    modules = _marketplace_modules()

    assert modules, f'no Python modules enumerated under {MARKETPLACE_ROOT}'
    assert any(module.name == 'orchestrator.py' for module in modules)


def test_only_one_module_implements_the_verdict_grammar():
    """Fails the moment a second formatter or parser of the field appears.

    Population-derived: the marketplace Python surface is enumerated at test
    time, never listed by hand — a hard-coded list would pass vacuously against
    exactly the duplicate this guard exists to catch.
    """
    carriers = [
        module
        for module in _marketplace_modules()
        if all(token in module.read_text(encoding='utf-8', errors='ignore') for token in _GRAMMAR_SIGNATURE)
    ]

    assert [module.name for module in carriers] == ['orchestrator.py'], (
        'the re-grounding verdict grammar has a second implementation: '
        f'{[str(module) for module in carriers]}'
    )


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCorpusCli:
    def test_should_enumerate_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = run_script(SCRIPT_PATH, 'corpus', 'enumerate', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'rows_total: 2' in result.stdout
        assert 'rows_without_spec_count: 1' in result.stdout

    def test_should_set_and_read_a_verdict_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        stamped = run_script(
            SCRIPT_PATH,
            'corpus',
            'set-verdict',
            '--slug',
            SLUG,
            '--plan',
            'PLAN-01',
            '--claim-index',
            '0',
            '--verdict',
            'contradicted',
            '--checked-at',
            SHA,
            '--by',
            PRODUCER,
            '--rescoped',
            'no',
            '--evidence',
            'no such branch at this sha',
            env_overrides=env,
        )
        read_back = run_script(SCRIPT_PATH, 'corpus', 'verdicts', '--slug', SLUG, env_overrides=env)

        assert stamped.returncode == 0
        assert 'replaced: false' in stamped.stdout
        assert read_back.returncode == 0
        assert 'blocking_count: 1' in read_back.stdout
