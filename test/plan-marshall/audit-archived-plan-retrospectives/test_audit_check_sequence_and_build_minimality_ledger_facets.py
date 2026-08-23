#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``sequence-and-build-minimality`` change-ledger facets — build rows are re-based
from the ledger, and the derived facets reflect the staged ``kind=build`` rows.
"""

from pathlib import Path

from _audit_fixtures import (
    _BUILD,
    _sbm_call,
    _sbm_index,
    _sbm_ledger_row,
    _write_change_ledger,
    _write_sbm_plan,
    audit,
)

# A NON-pyproject build notation, used to prove the single-tool blindness closed:
# the re-base reads `command` per build system, so a Maven row exercises the path
# a pyproject-only fixture cannot reach.
_LEDGER_NOTATION_MAVEN = 'plan-marshall:build-maven:maven_build'


def _row_cell(block: str, plan_id: str, column: str) -> str:
    """One named cell of one plan's emitted row.

    The column INDEX is derived from the block's own ``rows[N]{...}`` header
    rather than hard-coded, so a column inserted ahead of the requested one moves
    this reader with it instead of silently shifting it onto a neighbour. A
    column the header does not carry raises ``ValueError`` from ``.index`` —
    an absent column is a failure, never a silently skipped assertion.

    Reading the cell POSITIONALLY is the point: a bare ``',n/a,' in block``
    passes on that token appearing anywhere in the block — for another column, or
    for another plan's row — so it cannot tell one column's value from an
    unrelated occurrence elsewhere in the same output.
    """
    header = next(ln for ln in block.splitlines() if ln.startswith('rows['))
    columns = header.split('{', 1)[1].rsplit('}', 1)[0].split(',')
    row_line = next(
        ln.strip() for ln in block.splitlines() if ln.strip().startswith(f'{plan_id},')
    )
    return row_line.split(',')[columns.index(column)]


def _share_cell(block: str, plan_id: str) -> str:
    """The ``build_share`` cell of one plan's emitted row."""
    return _row_cell(block, plan_id, 'build_share')


class TestSequenceBuildMinimalityLedgerFacets:
    """The re-base onto the change-ledger (D1/D2): build time comes from the
    ledger's structured `duration_seconds` for every build system and every phase,
    the pass/fail/timeout/killed status ratio (killed SEPARATE), the
    build-vs-wall-clock share, the suspect-zero rule, and the
    build-time-exceeds-wall-clock invariant.

    Each test states, in its comment, why it would have FAILED against the pre-fix
    (log-derived, pyproject-only, no-ledger) implementation — the plan requires
    each seen red first.
    """

    def test_status_ratio_counts_all_four_with_killed_separate(self, tmp_path: Path):
        # D4(a). A ledger with all four statuses; `killed` is an INFRASTRUCTURE
        # event, never folded into `error`. Pre-fix there was no ledger status
        # field at all (build state came only from a log duration), so no status
        # ratio existed and this row's four columns did not exist — red.
        inputs = _write_sbm_plan(
            tmp_path, 'ledger-status',
            modified_files=['a.py'],
            ledger_builds=[
                {'dur': 10.0, 'status': 'success'},
                {'dur': 10.0, 'status': 'error'},
                {'dur': 10.0, 'status': 'timeout'},
                {'dur': 10.0, 'status': 'killed', 'ts': '2026-06-01T11:00:00Z'},
                {'dur': 10.0, 'status': 'killed', 'ts': '2026-06-01T12:00:00Z'},
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['build_success'] == 1
        assert row['build_error'] == 1          # killed is NOT counted here
        assert row['build_timeout'] == 1
        assert row['build_killed'] == 2         # counted on its own axis

    def test_status_ratio_visibly_separate_in_emitted_block(self, tmp_path: Path):
        # `killed` must be VISIBLY separate in the output, not merely in the code:
        # the block carries a distinct corpus_build_killed line and a `killed`
        # column. Pre-fix the block had neither line nor column — red.
        inputs = _write_sbm_plan(
            tmp_path, 'ledger-killed',
            modified_files=['a.py'],
            ledger_builds=[{'dur': 10.0, 'status': 'killed'}],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))

        block = audit.emit_sequence_build_minimality_block(result)

        assert 'corpus_build_killed: 1' in block
        assert 'corpus_build_error: 0' in block   # the kill did not read as an error
        assert ',pass,error,timeout,killed,' in block

    def test_status_unknown_reconciles_corpus_build_count(self, tmp_path: Path):
        # A build carrying an unrecognized status is tallied in
        # corpus_build_status_unknown so the status ratio accounts for every build:
        # pass + error + timeout + killed + status_unknown == corpus_builds. Pre-fix
        # the field was computed but emitted nowhere, so the sum silently fell short.
        inputs = _write_sbm_plan(
            tmp_path, 'status-unknown',
            modified_files=['a.py'],
            ledger_builds=[
                {'dur': 10.0, 'status': 'success'},
                {'dur': 10.0, 'status': 'weird-unrecognized-status'},
            ],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))
        block = audit.emit_sequence_build_minimality_block(result)
        corpus = result['corpus']

        assert corpus['status_unknown'] == 1
        assert 'corpus_build_status_unknown: 1' in block
        assert (
            corpus['success'] + corpus['error'] + corpus['timeout']
            + corpus['killed'] + corpus['status_unknown']
        ) == corpus['builds']

    def test_status_unknown_is_a_row_column_that_partitions_that_row_builds(
        self, tmp_path: Path
    ):
        # THE ROW-SCOPE HALF of the same defect the corpus test above covers. The
        # corpus totals named the undetermined build; the per-plan row did not —
        # its emitted columns ran pass,error,timeout,killed straight into
        # total_build_seconds, so one row's four status cells summed to LESS than
        # that same row's own `builds` cell with nothing naming the difference,
        # and the undetermined build read as a build that never ran. The corpus
        # assertion cannot observe this: it sums the row DICTS, which carried
        # `build_status_unknown` all along — only the emitted header and cell list
        # dropped it. Pre-fix `_row_cell(..., 'status_unknown')` raises ValueError
        # because the column is absent from the emitted rows[N]{...} header.
        inputs = _write_sbm_plan(
            tmp_path, 'row-status-unknown',
            modified_files=['a.py'],
            ledger_builds=[
                {'dur': 10.0, 'status': 'success', 'ts': '2026-06-01T10:00:00Z'},
                {'dur': 10.0, 'status': 'error', 'ts': '2026-06-01T11:00:00Z'},
                # Outside the recognised vocabulary — the outcome is UNDETERMINED.
                {'dur': 10.0, 'status': 'weird-unrecognized-status',
                 'ts': '2026-06-01T12:00:00Z'},
            ],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))
        block = audit.emit_sequence_build_minimality_block(result)

        assert _row_cell(block, 'row-status-unknown', 'status_unknown') == '1'
        five_terms = sum(
            int(_row_cell(block, 'row-status-unknown', column))
            for column in ('pass', 'error', 'timeout', 'killed', 'status_unknown')
        )
        assert five_terms == int(_row_cell(block, 'row-status-unknown', 'builds')) == 3

    def test_build_time_exceeds_wallclock_is_flagged(self, tmp_path: Path):
        # D4(b). A 500s build against a 100s plan wall-clock is impossible — a
        # recording defect (a duration plumbed through wrongly). Pre-fix there was
        # no wall-clock denominator and no such invariant, so nothing flagged — red.
        inputs = _write_sbm_plan(
            tmp_path, 'inv-violate',
            modified_files=['a.py'],
            ledger_builds=[{'dur': 500.0}],
            metrics_phases={'5-execute': 100.0},
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['wall_clock_seconds'] == 100
        assert any(f.startswith('build_exceeds_wallclock(') for f in row['flags'])

    def test_build_within_wallclock_does_not_flag_invariant(self, tmp_path: Path):
        # Negative control: a build well inside wall-clock must NOT trip the
        # invariant (else the flag would fire on every plan).
        inputs = _write_sbm_plan(
            tmp_path, 'inv-ok',
            modified_files=['a.py'],
            ledger_builds=[{'dur': 50.0}],
            metrics_phases={'5-execute': 500.0},
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert not any(f.startswith('build_exceeds_wallclock(') for f in row['flags'])

    def test_non_pyproject_build_appears_in_totals(self, tmp_path: Path):
        # D4(c) — the test that proves the SINGLE-TOOL blindness is closed. A Maven
        # build carries no `build-pyproject:pyproject_build` notation, so the
        # pre-fix log matcher (`_sbm_is_build`) never saw it and its time was
        # invisible. The ledger records `command` per build system, so its duration
        # now lands in the totals. Pre-fix: builds==0, total==0 — red.
        inputs = _write_sbm_plan(
            tmp_path, 'maven-plan',
            modified_files=['a.py'],
            ledger_builds=[{
                'dur': 250.0,
                'notation': _LEDGER_NOTATION_MAVEN,
                'command': 'mvn -q verify',
            }],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['builds'] == 1
        assert row['total_build_seconds'] == 250      # the Maven build's time
        assert row['build_scoped'] == 1               # 250s ⇒ scoped band
        # and it is NOT invisible to the corpus total either
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))
        assert result['corpus']['build_seconds'] == 250

    def test_suspect_zero_flagged_not_averaged_in(self, tmp_path: Path):
        # The suspect-zero rule (Verification): feed a zero duration alongside a
        # real one; the zero is FLAGGED and counted separately, never averaged into
        # the total. Pre-fix a 0.0 log duration classified as `unknown` but was
        # still summed (adding 0) with no suspect flag — the defect this closes is
        # that a 0 could not be told from a real measurement.
        inputs = _write_sbm_plan(
            tmp_path, 'suspect-zero',
            modified_files=['a.py'],
            ledger_builds=[
                {'dur': 300.0, 'ts': '2026-06-01T10:00:00Z'},
                {'dur': 0.0, 'ts': '2026-06-01T11:00:00Z'},   # killed-as-0 / cache-hit shape
                {'dur': None, 'ts': '2026-06-01T12:00:00Z'},  # absent duration
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['total_build_seconds'] == 300       # the two suspects added nothing
        assert row['build_unknown'] == 2               # counted on the suspect axis
        assert any(f.startswith('suspect_build_duration(2') for f in row['flags'])

    def test_wallclock_denominator_derivation_is_non_empty(self, tmp_path: Path):
        # D4(d). D0's derived denominator — the sum of per-phase metrics
        # `duration_seconds` — is a REAL value, not a vacuous zero: with metrics
        # present the wall-clock is non-empty and the build-vs-wall-clock share
        # computes. Pre-fix there was no denominator derivation at all — red.
        inputs = _write_sbm_plan(
            tmp_path, 'denominator',
            modified_files=['a.py'],
            ledger_builds=[{'dur': 120.0}],
            metrics_phases={'4-plan': 100.0, '5-execute': 300.0, '6-finalize': 100.0},
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['wall_clock_seconds'] == 500        # 100 + 300 + 100, summable
        assert row['wall_clock_seconds'] > 0           # the denominator is non-empty
        assert row['build_share'] is not None          # so the share is computed
        assert abs(row['build_share'] - (120 / 500)) < 1e-9

    def test_build_share_withheld_when_metrics_absent(self, tmp_path: Path):
        # The denominator inherits the metrics ABSENT-FILE hole: with no
        # metrics.toon the share is WITHHELD (None → `n/a`), never a fabricated
        # ratio over a zero denominator.
        inputs = _write_sbm_plan(
            tmp_path, 'no-metrics',
            modified_files=['a.py'],
            ledger_builds=[{'dur': 120.0}],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))
        block = audit.emit_sequence_build_minimality_block(result)

        assert row['wall_clock_seconds'] == 0
        assert row['build_share'] is None
        assert _share_cell(block, 'no-metrics') == 'n/a'   # rendered as n/a, not 0%

    def test_build_share_withheld_when_the_ledger_is_absent(self, tmp_path: Path):
        # The NUMERATOR's absent-ledger hole — the mirror of the denominator case
        # above. Metrics ARE present, so wall-clock is a real positive number and
        # the denominator gate passes; what is missing is the numerator, because
        # the plan carries no kind=build rows at all and `total_build_seconds` is
        # therefore zero BY ABSENCE rather than by measurement. Gating on the
        # denominator alone rendered 0/500 as a fabricated `0%` — a cell reading
        # "this plan spent no time building" one column away from the
        # `has_ledger: false` cell saying the build time was never measured.
        inputs = _write_sbm_plan(
            tmp_path, 'no-ledger',
            modified_files=['a.py'],
            metrics_phases={'5-execute': 500.0},
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))
        block = audit.emit_sequence_build_minimality_block(result)

        assert row['has_ledger'] is False              # the numerator is UNAVAILABLE
        assert row['wall_clock_seconds'] == 500        # while the denominator is not
        assert row['build_share'] is None              # so the share is withheld
        assert _share_cell(block, 'no-ledger') == 'n/a'

    def test_ledger_delta_over_ledger_bearing_population(self, tmp_path: Path):
        # D1's delta: the ledger total vs the OLD log-derived total, measured over
        # the SAME ledger-bearing plans. A plan whose only build reached the log
        # (a pyproject build logged with a duration) shows the delta the ledger
        # adds. A plan with no ledger rows is UNAVAILABLE (absent is not zero) and
        # named separately, never folded into the delta.
        logged = _write_sbm_plan(
            tmp_path, 'logged',
            modified_files=['a.py'],
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 40.0)],
            ledger_builds=[
                {'dur': 40.0, 'ts': '2026-06-01T10:00:00Z'},                       # the same pyproject build
                {'dur': 200.0, 'ts': '2026-06-01T11:00:00Z',                       # a maven build the log never saw
                 'notation': _LEDGER_NOTATION_MAVEN, 'command': 'mvn verify'},
            ],
        )
        absent = _write_sbm_plan(tmp_path, 'absent', modified_files=['a.py'])

        result = audit.cross_sequence_build_minimality([logged, absent], _sbm_index(tmp_path))
        corpus = result['corpus']

        assert corpus['build_seconds'] == 240                      # ledger: 40 + 200
        assert corpus['build_seconds_log_derived'] == 40           # log saw only pyproject
        assert corpus['build_seconds_delta'] == 200                # what the re-base now sees
        assert result['plans_without_ledger'] == 1
        assert result['plans_without_ledger_ids'] == ['absent']

    def test_load_build_ledger_index_attributes_date_prefixed_dir(self, tmp_path: Path):
        # End-to-end attribution: an archived plan dir named {YYYY-MM-DD}-{plan_id}
        # is matched to ledger rows carrying the BARE plan_id. Stage a real ledger
        # and an archived-shaped plan, and assert the build lands.
        archived = tmp_path / '.plan' / 'local' / 'archived-plans' / '2026-06-01-real-plan'
        (archived / 'logs').mkdir(parents=True)
        (archived / 'logs' / 'script-execution.log').write_text('\n', encoding='utf-8')
        (archived / 'logs' / 'work.log').write_text('\n', encoding='utf-8')
        (archived / 'references.json').write_text('{"modified_files": ["a.py"]}', encoding='utf-8')
        (archived / 'status.json').write_text('{"metadata": {}}', encoding='utf-8')
        _write_change_ledger(tmp_path, [_sbm_ledger_row('real-plan', dur=99.0)])

        inputs = audit.collect_inputs(archived)
        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        assert row['has_ledger'] is True
        assert row['builds'] == 1
        assert row['total_build_seconds'] == 99


class TestCheckProseMatchesTheLedgerRebase:
    """The check's own prose describes the ledger re-base, not the log derivation.

    The re-base moved build count / duration / status onto the change-ledger, but
    the module docstring and the check's section comment still described the OLD
    log-derived behaviour and still named two machine-local prototype scripts as
    the check's basis. Stale prose beside correct code is the documentation half
    of the same defect: a reader who trusts the description reads every build
    number as pyproject-only.

    Asserted over the source TEXT because that is the only form these claims have
    — they are comments, so no runtime behaviour can carry them, and nothing else
    in the suite fails when they drift.
    """

    @staticmethod
    def _source() -> str:
        return Path(audit.__file__).read_text(encoding='utf-8')

    def test_the_old_log_matcher_is_named_only_at_its_own_definition(self):
        """`pyproject_build run` survives only as `_sbm_is_build`'s delta baseline.

        Anywhere else it is a claim that the check classifies builds by parsing
        pyproject calls out of a log — which is what the re-base replaced.
        """
        hits = [
            ln.strip()
            for ln in self._source().splitlines()
            if 'pyproject_build run' in ln
        ]

        assert hits == [
            '# A pyproject_build run call in the plan-scoped log — the OLD build derivation,'
        ]

    def test_the_machine_local_prototype_paths_are_gone(self):
        """Both named `.plan/temp/` prototypes are absent from this clone.

        A comment pointing a reader at a path that does not exist sends them
        looking for the check's basis in a file they cannot open; the basis is
        the build-time ORACLE block in this same source.
        """
        source = self._source()

        assert '.plan/temp/build_minimality' not in source
        assert '.plan/temp/sequence_analysis' not in source
        assert 'build-time ORACLE' in source          # the pointer that replaced them

    def test_the_two_ledger_derived_flags_are_catalogued(self):
        """The MODULE DOCSTRING's flag list names both ledger-derived flags.

        The docstring is what a reader consults to know which signals the check
        can raise, so a flag the code emits but the docstring omits is invisible
        until it fires. Asserted against `audit.__doc__` specifically rather than
        against the whole source, where the emit site's own f-string would
        satisfy the search and the catalogue could stay silent.
        """
        docstring = audit.__doc__ or ''

        for flag in ('suspect_build_duration', 'build_exceeds_wallclock'):
            assert flag in docstring, flag
