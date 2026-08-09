#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``corpus`` verb group of the marshall-orchestrator script.

Covers the four sub-verbs against a SCAFFOLDED FIXTURE EPIC under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree:

- ``corpus enumerate``: the bidirectional reconciliation of ``status.json``'s
  ``plans[]`` queue against the ``plans/PLAN-*.md`` spec files, with every count
  riding beside the population it was computed over.
- ``corpus cross-check``: the cross-ledger duplication arm — this epic's specs
  scored against sibling epics (active and archived), the live plan set, and
  this epic's own corpus, on the two ``sibling-collision-check`` classes.
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

A further group pins the fenced-code-block state every line-wise markdown scan
carries. A ``#`` comment inside a fence is not a heading and a ``- item`` inside
one is not a bullet; admitting either truncates the enclosing section, which
drops Expected Surface paths behind a confident no-overlap and makes later
claims vanish from ``--claim-index`` addressing. Each detector there carries a
matched pair, because suppression that also disabled real headings would be a
different defect wearing the same green.

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
cmd_corpus_cross_check = _orch.cmd_corpus_cross_check
cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
format_verdict_line = _orch._format_verdict_line
parse_verdict_text = _orch._parse_verdict_text
fenced_mask = _orch._fenced_mask
section_span = _orch._section_span
expected_surface_paths = _orch._expected_surface_paths
EXPECTED_SURFACE_HEADING_RE = _orch.EXPECTED_SURFACE_HEADING_RE
VERDICT_KEYS = _orch.VERDICT_KEYS
VERDICT_SEPARATOR = _orch.VERDICT_SEPARATOR
VERDICT_VALUES = _orch.VERDICT_VALUES
RESCOPED_VALUES = _orch.RESCOPED_VALUES

SLUG = 'fixture-corpus-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
SHA = '9f3a1c2'
OTHER_SHA = 'abc1234'
PRODUCER = 'fixture-corpus-epic/cleanup'

# --- cross-check fixtures --------------------------------------------------

SIBLING_SLUG = 'fixture-sibling-epic'
ARCHIVED_SLUG = 'fixture-archived-epic'
LIVE_PLAN_ID = 'fixture-live-plan'

#: A concrete repo-relative path a spec declares in its ``## Expected Surface``
#: and a candidate carries on its own surface — the file-overlap class's input.
SHARED_PATH = 'marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py'
#: A DIFFERENT concrete path, so every file-overlap negative control is a real
#: non-empty surface that simply does not intersect — never an empty one.
OTHER_PATH = 'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_sibling_collision.py'
#: A lesson two documents both cite. A real file path and a real shared
#: reference, but NOT an orchestrator spec pointer — the near-miss the
#: deliberately narrow ``SPEC_POINTER_RE`` exists to keep silent.
SHARED_LESSON = '.plan/local/lessons-learned/LESSON-001-shared-origin.md'
#: A THIRD real path, cited outside the ``## Expected Surface`` section. The
#: section boundary must still exclude it once fenced lines stop truncating the
#: body — widening the body past a fenced comment is not the same as unbounding it.
OUTSIDE_PATH = 'marketplace/bundles/plan-marshall/skills/manage-files/scripts/manage-files.py'


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


#: The default ``## Expected Surface`` body. ``a.py`` carries no ``/`` segment,
#: so the path extractor never sees a path here — a spec written without an
#: explicit surface contributes NOTHING to the file-overlap class.
_DEFAULT_SURFACE = ['- OBSERVED: `a.py` — `f`']

_DEFAULT_CLAIM = '- OBSERVED: a claim — read at `a.py` § `f`'


def _spec_text(
    claim_lines: list,
    surface_lines: list | None = None,
    objective: str = 'Fixture objective.',
) -> str:
    """Render a minimal spec carrying ``## Claim Labels`` and ``## Expected Surface``.

    ``objective`` and ``surface_lines`` are separately addressable because the
    two sections mean different things to ``corpus cross-check``: the surface is
    the declared file set the overlap class compares, while the objective is
    ordinary prose whose paths must NOT be read as a surface.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        objective,
        '',
        '## Claim Labels',
        '',
        *claim_lines,
        '',
        '## Expected Surface',
        '',
        *(_DEFAULT_SURFACE if surface_lines is None else surface_lines),
    ]
    return '\n'.join(lines) + '\n'


def _write_spec(
    plan_context,
    name: str,
    claim_lines: list | None = None,
    *,
    epic_dir: Path | None = None,
    surface_lines: list | None = None,
    objective: str = 'Fixture objective.',
) -> Path:
    """Write one spec file, defaulting to this fixture epic's ``plans/`` dir.

    ``epic_dir`` retargets the write at a sibling epic (active or archived) so
    the cross-check's candidate populations can be materialized with the same
    builder the own-corpus tests use.
    """
    root = _epic_dir(plan_context) if epic_dir is None else epic_dir
    path = root / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _spec_text(claim_lines or [_DEFAULT_CLAIM], surface_lines, objective), encoding='utf-8'
    )
    return path


def _archived_epic_dir(plan_context, slug: str) -> Path:
    """The ARCHIVED home of one epic — the second store root the scan walks."""
    return Path(plan_context.fixture_dir) / 'archived-orchestrators' / slug


def _pointer(spec_name: str, slug: str = SLUG, store: str = 'orchestrator') -> str:
    """Render the on-disk spec-pointer text a ``source_id`` or a spec carries."""
    return f'.plan/local/{store}/{slug}/plans/{spec_name}'


def _surface(*paths: str) -> list:
    """Render an ``## Expected Surface`` body declaring ``paths``."""
    return [f'- OBSERVED: `{path}` — `f`' for path in paths]


def _write_live_plan(
    plan_context,
    plan_id: str,
    source_id: str = '',
    affected_files: list | None = None,
) -> Path:
    """Materialize one ACTIVE plan — the OTHER ledger the cross-check reaches into.

    A plan directory counts as active only when it carries the ``status.json``
    sentinel, so the sentinel is written even though the cross-check reads only
    ``request.md`` (for the origin) and ``references.json`` (for the surface).
    """
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': plan_id}), encoding='utf-8')
    (plan_dir / 'request.md').write_text(
        '\n'.join(
            [
                f'# Request: {plan_id}',
                '',
                f'plan_id: {plan_id}',
                'source: orchestrator',
                f'source_id: {source_id}',
                '',
                '## Clarified Request',
                '',
                'Fixture live plan.',
            ]
        )
        + '\n',
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(
        json.dumps({'affected_files': list(affected_files or [])}), encoding='utf-8'
    )
    return plan_dir


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
# corpus cross-check — the cross-ledger duplication arm
# =============================================================================
#
# The arm a single ledger structurally CANNOT perform: a duplicate held in
# another epic's ledger, or in a launched plan's own ledger, is invisible to
# this epic's ``plans[]`` queue. Three candidate populations are therefore
# scanned — sibling epics (active AND archived), the live plan set, and this
# epic's own corpus — and each is named in the payload so a zero states which
# zero it is.
#
# Both collision classes carry a matched pair. The positives are seeded
# duplicates (a live plan launched from one of these specs, a sibling spec
# citing one, a shared declared surface); the negatives are legitimate
# near-misses that must stay silent — two documents citing the same LESSON
# (a shared reference that is not an origin pointer), a description-sourced
# plan with no traceable origin, two real-but-disjoint surfaces, and the same
# path cited as background prose rather than declared as a surface.


class TestCorpusCrossCheckPopulation:
    def test_should_name_all_three_scanned_populations(self, plan_context):
        """Non-empty-population guard: each candidate source must materialize."""
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')
        _write_spec(plan_context, 'PLAN-77-sibling.md', epic_dir=_epic_dir(plan_context, SIBLING_SLUG))
        _write_live_plan(plan_context, LIVE_PLAN_ID)

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-cross-check'
        assert result['specs_total'] == 2, 'the own corpus did not materialize'
        assert result['specs_scanned'] == 2
        assert result['epics_scanned'] == 1, 'the sibling epic did not materialize'
        assert result['plans_scanned'] == 1, 'the live plan did not materialize'
        assert result['candidates_scanned'] == 2

    def test_should_ride_every_count_beside_its_population(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        for count_field, population_field in (
            ('source_origin_match_count', 'candidates_scanned'),
            ('file_overlap_match_count', 'candidates_scanned'),
            ('unreadable_count', 'specs_total'),
        ):
            assert count_field in result
            assert population_field in result
        for population_field in ('epics_scanned', 'plans_scanned', 'specs_scanned'):
            assert population_field in result

    def test_a_zero_count_states_which_zero_it_is(self, plan_context):
        # Every population is REAL and non-empty — an empty corpus, an epic with
        # no siblings, or no live plans would report the same zeros vacuously.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(OTHER_PATH),
        )
        _write_live_plan(
            plan_context,
            LIVE_PLAN_ID,
            source_id=_pointer('PLAN-99-elsewhere.md', slug='some-other-epic'),
            affected_files=[OTHER_PATH],
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['file_overlap_match_count'] == 0
        assert result['unreadable_count'] == 0
        assert result['collision_detected'] is False
        assert result['specs_scanned'] == 1
        assert result['epics_scanned'] == 1
        assert result['plans_scanned'] == 1
        assert result['candidates_scanned'] == 2

    def test_should_error_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_corpus_cross_check(Namespace(slug='absent-corpus-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_cross_check(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestCrossCheckSourceOriginClass:
    """Collision class one — a shared spec-pointer origin. Matched pair."""

    def test_should_match_a_live_plan_launched_from_this_epics_spec(self, plan_context):
        # Positive control, CROSS-LEDGER: the duplicate this epic's own queue
        # structurally cannot see, because it is recorded in the plan's ledger.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_live_plan(plan_context, LIVE_PLAN_ID, source_id=_pointer('PLAN-01-alpha.md'))

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_matches'] == [
            {
                'spec': 'PLAN-01-alpha.md',
                'candidate_kind': 'live_plan',
                'candidate': LIVE_PLAN_ID,
                'shared_origin': f'{SLUG}/plans/PLAN-01-alpha.md',
            }
        ]
        assert result['source_origin_match_count'] == 1
        assert result['collision_detected'] is True
        assert result['plans_scanned'] == 1

    def test_should_match_a_sibling_epic_spec_that_cites_this_epics_spec(self, plan_context):
        # Positive control, cross-EPIC.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            objective=f'Supersedes {_pointer("PLAN-01-alpha.md")} in full.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 1
        row = result['source_origin_matches'][0]
        assert row['spec'] == 'PLAN-01-alpha.md'
        assert row['candidate_kind'] == 'sibling_epic_spec'
        assert row['candidate'] == f'{SIBLING_SLUG}/PLAN-77-sibling.md'
        assert row['shared_origin'] == f'{SLUG}/plans/PLAN-01-alpha.md'

    def test_should_see_an_archived_sibling_epic(self, plan_context):
        # An archived epic still holds work; closing it does not make its specs
        # invisible to the duplication check.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(
            plan_context,
            'PLAN-88-archived.md',
            epic_dir=_archived_epic_dir(plan_context, ARCHIVED_SLUG),
            objective=f'Already delivered by {_pointer("PLAN-01-alpha.md")}.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['epics_scanned'] == 1
        assert result['source_origin_match_count'] == 1
        assert result['source_origin_matches'][0]['candidate'] == f'{ARCHIVED_SLUG}/PLAN-88-archived.md'

    def test_should_stay_silent_when_two_documents_merely_cite_the_same_lesson(self, plan_context):
        # Negative control: a REAL shared reference that is not an origin
        # pointer. The narrow pointer shape is the whole reason this stays a
        # near-miss instead of a match.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', objective=f'Grounded in {SHARED_LESSON}.')
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            objective=f'Grounded in {SHARED_LESSON}.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['collision_detected'] is False
        assert result['candidates_scanned'] == 1, 'the candidate population must be non-empty'

    def test_should_stay_silent_for_a_live_plan_with_no_traceable_origin(self, plan_context):
        # Negative control on the cross-ledger arm: a description-sourced plan
        # carries no source_id, so it can never match on origin.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_live_plan(plan_context, LIVE_PLAN_ID, source_id='')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['plans_scanned'] == 1, 'the plan population must be non-empty'

    def test_should_not_match_a_spec_against_itself(self, plan_context):
        # Every spec carries its OWN pointer in its pointer set — deliberately,
        # so a candidate citing it matches. The self-exclusion is therefore the
        # only thing keeping a lone spec silent.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['specs_scanned'] == 1


class TestCrossCheckFileOverlapClass:
    """Collision class two — an exact declared-surface overlap. Matched pair."""

    def test_should_match_a_live_plans_affected_files(self, plan_context):
        # Positive control, CROSS-LEDGER: the spec's declared surface against
        # the launched plan's references.json.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH, OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_matches'] == [
            {
                'spec': 'PLAN-01-alpha.md',
                'candidate_kind': 'live_plan',
                'candidate': LIVE_PLAN_ID,
                'overlap_count': 1,
                'overlapping_files': SHARED_PATH,
            }
        ]
        assert result['file_overlap_match_count'] == 1
        assert result['collision_detected'] is True

    def test_should_match_a_sibling_epic_specs_expected_surface(self, plan_context):
        # Positive control, cross-EPIC: spec surface against spec surface.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(SHARED_PATH, OTHER_PATH),
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 1
        row = result['file_overlap_matches'][0]
        assert row['candidate_kind'] == 'sibling_epic_spec'
        assert row['candidate'] == f'{SIBLING_SLUG}/PLAN-77-sibling.md'
        assert row['overlap_count'] == 1
        assert row['overlapping_files'] == SHARED_PATH

    def test_should_name_every_overlapping_file_never_a_bare_score(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH, OTHER_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH, SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        row = result['file_overlap_matches'][0]
        assert row['overlap_count'] == 2
        assert sorted(row['overlapping_files'].split(';')) == sorted([SHARED_PATH, OTHER_PATH])

    def test_should_match_within_this_epics_own_corpus(self, plan_context):
        # The within-corpus direction. Rows are emitted per (spec, candidate)
        # pair, so a surface shared by two of this epic's own specs is reported
        # from BOTH sides — the symmetry is the report shape, not a duplicate.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(plan_context, 'PLAN-02-beta.md', surface_lines=_surface(SHARED_PATH))

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 2
        assert {row['candidate_kind'] for row in result['file_overlap_matches']} == {'corpus_spec'}
        assert sorted((row['spec'], row['candidate']) for row in result['file_overlap_matches']) == [
            ('PLAN-01-alpha.md', 'PLAN-02-beta.md'),
            ('PLAN-02-beta.md', 'PLAN-01-alpha.md'),
        ]

    def test_should_stay_silent_for_disjoint_surfaces(self, plan_context):
        # Negative control: two REAL non-empty surfaces that do not intersect.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 0
        assert result['collision_detected'] is False
        assert result['candidates_scanned'] == 1

    def test_should_ignore_a_path_cited_outside_the_expected_surface_section(self, plan_context):
        # Negative control on the SECTION boundary: the very same path, cited as
        # background prose in the objective rather than DECLARED as the surface.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            objective=f'Background reading: {SHARED_PATH} explains the seam.',
            surface_lines=_surface(OTHER_PATH),
        )
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 0
        assert result['candidates_scanned'] == 1


class TestCrossCheckUnreadable:
    """Report-never-skip, on BOTH sides of the comparison."""

    def test_should_report_an_unreadable_own_spec_without_aborting(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-02-broken.md'
        broken.write_bytes(b'\xff\xfe not valid utf-8 \xff')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['unreadable'] == [{'spec': 'PLAN-02-broken.md', 'error': 'unreadable'}]
        assert result['unreadable_count'] == 1
        assert result['specs_total'] == 2
        assert result['specs_scanned'] == 1, 'the unreadable spec must not count as scanned'

    def test_should_report_an_unreadable_candidate_under_its_own_epic(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context, SIBLING_SLUG) / 'plans' / 'PLAN-77-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe \xff')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['unreadable'] == [
            {'spec': f'{SIBLING_SLUG}/PLAN-77-broken.md', 'error': 'unreadable'}
        ]
        assert result['unreadable_count'] == 1
        assert result['epics_scanned'] == 1, 'the epic itself was still scanned'
        assert result['candidates_scanned'] == 0, 'an unreadable candidate must not count as scanned'


class TestCrossCheckReadOnlyBoundary:
    def test_cross_check_leaves_every_scanned_tree_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(SHARED_PATH),
        )
        _write_live_plan(
            plan_context,
            LIVE_PLAN_ID,
            source_id=_pointer('PLAN-01-alpha.md'),
            affected_files=[SHARED_PATH],
        )
        root = Path(plan_context.fixture_dir)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['collision_detected'] is True, (
            'the read-only claim must be proven on a scan that actually HIT — '
            'a scan finding nothing would leave the tree untouched vacuously'
        )


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
# Fenced-code-block state — suppression of the heading and bullet scans
# =============================================================================
#
# Every line-wise markdown scan in the module runs against a fence mask, because
# a ``#`` comment inside a fenced example is not a heading and a ``- item``
# inside one is not a bullet. Without the mask a fenced comment TERMINATES the
# enclosing section: the Expected Surface body is truncated at that line and
# every later path is dropped, so ``corpus cross-check`` reports a confident
# no-overlap while still counting the spec in ``specs_scanned`` — a silently
# narrowed population behind a clean zero. In ``_parse_claims`` the same
# truncation makes every later claim vanish, shifting ``--claim-index``
# addressing and understating ``claims_total``.
#
# Every detector carries a MATCHED PAIR. The positive controls prove a REAL
# heading still terminates the scan (the suppression is fence-scoped, not a
# blanket disable); the negative controls prove the fenced look-alike does not.

#: A fenced Expected Surface path list whose FIRST body line is a ``#`` comment —
#: the exact shape that truncated the section. ``OTHER_PATH`` is deliberately
#: LAST, so an assertion that finds it proves the whole list survived.
_FENCED_SURFACE = [
    '```text',
    '# the files this spec expects to touch',
    SHARED_PATH,
    OTHER_PATH,
    '```',
]

#: Two real claims with a fenced example between them. The fence carries both a
#: ``#`` comment (a heading look-alike) and a ``- `` line (a bullet look-alike),
#: so one fixture exercises both suppressions.
_FENCED_CLAIMS = [
    _DEFAULT_CLAIM,
    '',
    '```text',
    '# an illustrative fragment, not a heading',
    '- an illustrative bullet, not a claim',
    '```',
    '',
    '- OBSERVED: a second claim — read at `b.py` § `g`',
]


class TestFenceMask:
    """The mask itself, asserted against a published per-line population."""

    def test_should_mark_only_the_fenced_run(self):
        lines = ['before', '```text', '# not a heading', '```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines), 'the mask must carry one entry per scanned line'
        assert mask == [False, True, True, True, False]

    def test_an_unterminated_fence_runs_to_the_end_of_the_document(self):
        # CommonMark's rule, and the conservative reading: text that may be code
        # is treated as code rather than admitted as a heading.
        lines = ['```text', '# not a heading', 'still inside the block']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True]

    def test_a_tilde_line_does_not_close_a_backtick_fence(self):
        # A close must be built from the character that OPENED the block.
        lines = ['```text', '~~~', '# still fenced', '```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, True, False]

    def test_an_unfenced_document_masks_nothing(self):
        # Negative control on the mask itself: a REAL document with real
        # headings, not an empty one, must produce an all-False mask.
        lines = ['## Expected Surface', '', SHARED_PATH, '', '## Objective']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert not any(mask)


class TestFencedSectionSpan:
    def test_a_real_heading_still_ends_a_section(self):
        # Positive control: the terminator works, so the negative control below
        # is testing suppression rather than a scan that never terminates.
        lines = ['## Expected Surface', '', SHARED_PATH, '', '## Objective', '', OTHER_PATH]

        start, end = section_span(lines, EXPECTED_SURFACE_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert (start, end) == (1, 4)
        assert SHARED_PATH in body
        assert OTHER_PATH not in body

    def test_a_hash_line_inside_a_fence_does_not_end_a_section(self):
        lines = ['## Expected Surface', '', *_FENCED_SURFACE, '', '## Objective']

        start, end = section_span(lines, EXPECTED_SURFACE_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert '# the files this spec expects to touch' in body
        assert OTHER_PATH in body, 'a fenced comment truncated the section body'

    def test_a_fenced_heading_does_not_open_a_section(self):
        # The opening scan carries the same state: a fenced ``## Expected
        # Surface`` line inside an earlier example is not this document's section.
        lines = ['```text', '## Expected Surface', OTHER_PATH, '```']

        assert section_span(lines, EXPECTED_SURFACE_HEADING_RE) == (-1, -1)


class TestFencedExpectedSurface:
    def test_a_fenced_path_list_with_a_leading_comment_yields_every_path(self):
        declared = (SHARED_PATH, OTHER_PATH)
        text = _spec_text([_DEFAULT_CLAIM], list(_FENCED_SURFACE))

        paths = expected_surface_paths(text)

        assert len(paths) == len(declared), (
            f'{len(declared)} path(s) declared in the fenced list, {len(paths)} extracted'
        )
        assert paths == set(declared)

    def test_a_path_outside_the_section_is_still_excluded(self):
        # Negative control: the fix widens the body past a fenced comment, it
        # does not stop bounding the section.
        text = _spec_text(
            [_DEFAULT_CLAIM],
            list(_FENCED_SURFACE),
            objective=f'Background reading: {OUTSIDE_PATH} explains the seam.',
        )

        paths = expected_surface_paths(text)

        assert OUTSIDE_PATH not in paths
        assert paths == {SHARED_PATH, OTHER_PATH}

    def test_cross_check_reports_the_overlap_a_fenced_comment_used_to_hide(self, plan_context):
        # The end-to-end consequence: the overlap is on the LAST path of the
        # fenced list, the one a truncated body drops.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=list(_FENCED_SURFACE))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1, 'the own corpus did not materialize'
        assert result['candidates_scanned'] == 1, 'the candidate population did not materialize'
        assert result['file_overlap_match_count'] == 1
        assert result['file_overlap_matches'][0]['overlapping_files'] == OTHER_PATH
        assert result['collision_detected'] is True


class TestFencedClaimParsing:
    def test_a_real_heading_still_ends_the_claim_section(self, plan_context):
        # Positive control: ``_DEFAULT_SURFACE`` is itself a top-level bullet, so
        # a claim count of 1 proves the ``## Expected Surface`` heading terminated
        # the claim section rather than the scan simply finding one bullet.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 1

    def test_a_fenced_bullet_is_not_counted_and_later_claims_survive(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 2, (
            'the fenced bullet was counted as a claim, or the fenced comment '
            'truncated the section and dropped the claim after it'
        )

    def test_claim_index_addressing_survives_a_fenced_block(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        stamped = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert stamped['status'] == 'success'
        assert stamped['claims_total'] == 2
        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 1
        assert result['claims'][0]['evidence'] == 'second only'

    def test_a_verdict_stamped_before_a_fence_round_trips(self, plan_context):
        # Exercises ``_claim_block_end`` with fence state: the insertion point for
        # a claim whose block CONTAINS a fenced example.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='first only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['claims_scanned'] == 2, 'the stamp changed the claim population'
        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 0
        assert result['claims'][0]['evidence'] == 'first only'


# =============================================================================
# Separate vocabularies, separate bindings
# =============================================================================


def test_the_parse_outcome_and_the_readiness_verdict_have_distinct_bindings():
    """Two independent vocabularies must not share one module-level binding.

    They coincide in spelling, so a single ``INDETERMINATE`` name would let a
    change to either silently move the other. The value equality is asserted
    alongside the binding separation so this reads as "two names, same spelling"
    rather than as an accidental divergence.
    """
    assert _orch.VERDICT_INDETERMINATE == 'indeterminate'
    assert _orch.READINESS_INDETERMINATE == 'indeterminate'
    assert not hasattr(_orch, 'INDETERMINATE'), (
        'the shadowed shared binding is back — each vocabulary owns its own name'
    )


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

    def test_should_cross_check_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = run_script(SCRIPT_PATH, 'corpus', 'cross-check', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'plans_scanned: 1' in result.stdout
        assert 'file_overlap_match_count: 1' in result.stdout
        assert 'collision_detected: true' in result.stdout

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
