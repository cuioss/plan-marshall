#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``quality-chain`` flagging — the genuine-signal predicate, the cross-plan check,
and per-finding severity.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _write_findings_plan(
    repo_root: Path,
    plan_id: str,
    findings_by_file: dict[str, list[dict[str, Any]]],
) -> Any:
    """Materialise a plan carrying ``artifacts/findings/{file}`` JSONL findings.

    ``findings_by_file`` maps a findings filename (e.g. ``test-failure.jsonl``,
    ``pr-comment.jsonl``, ``qgate-phase-6.jsonl``) to a list of finding dicts;
    each dict is written as one JSONL line. The plan is parsed through the real
    ``collect_inputs`` so the quality-chain check reads it end-to-end.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'qc-corpus' / plan_id
    findings_dir = plan_dir / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    for fname, records in findings_by_file.items():
        lines = '\n'.join(_json.dumps(r) for r in records) + '\n'
        (findings_dir / fname).write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)


class TestQualityChainFlags:
    """``_quality_chain_flags`` computes the per-plan chain anti-pattern flags."""

    def test_auto_review_only_when_no_build_or_self_review(self, tmp_path: Path):
        # only a bot PR comment, no build/self-review surface
        inputs = _write_findings_plan(
            tmp_path,
            'plan-auto-only',
            {'pr-comment.jsonl': [{'detail': 'gemini flagged a regex', 'resolution': 'fixed'}]},
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('auto_review_only') for f in flags)
        # no self-review surface → no_qgate6 also fires
        assert 'no_qgate6' in flags

    def test_build_pending_pile_fires_at_two_pending(self, tmp_path: Path):
        # two unresolved build failures
        inputs = _write_findings_plan(
            tmp_path,
            'plan-build-pile',
            {
                'test-failure.jsonl': [
                    {'resolution': 'pending', 'title': 'test a fails'},
                    {'resolution': 'pending', 'title': 'test b fails'},
                ]
            },
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('build_pending_pile') for f in flags)

    def test_review_body_duplicate_when_title_spans_self_and_auto(self, tmp_path: Path):
        # same title in both self-review and auto-review
        inputs = _write_findings_plan(
            tmp_path,
            'plan-dupe',
            {
                'qgate-phase-6.jsonl': [{'title': 'Missing null guard', 'resolution': 'fixed'}],
                'pr-comment.jsonl': [
                    {'detail': 'gemini: Missing null guard', 'title': 'Missing null guard', 'resolution': 'fixed'}
                ],
            },
        )
        plan = audit._collect_quality_chain([inputs])[0]

        flags = audit._quality_chain_flags(plan)

        assert any(f.startswith('review_body_duplicate') for f in flags)


class TestQualityChainCrossCheck:
    """``cross_quality_chain`` assembles the matrix, per-plan rows, per-finding
    rows, and shift-left histogram; ``emit_quality_chain_block`` renders them
    with the D1 severity column."""

    def test_plans_without_findings_dir_excluded(self, tmp_path: Path):
        # one plan with findings, one bare plan dir
        good = _write_findings_plan(
            tmp_path, 'has-findings',
            {'test-failure.jsonl': [{'resolution': 'fixed', 'title': 't'}]},
        )
        bare_dir = tmp_path / '.plan' / 'temp' / 'qc-corpus' / 'no-findings'
        bare_dir.mkdir(parents=True, exist_ok=True)
        bare = audit.collect_inputs(bare_dir)

        result = audit.cross_quality_chain([good, bare])

        # only the plan with a findings dir is in the corpus
        assert result['plans_in_corpus'] == 1
        assert result['rows'][0]['plan_id'] == 'has-findings'

    def test_corpus_matrix_sums_per_plan_matrices(self, tmp_path: Path):
        # two plans, each one direct-fix build finding
        inputs = [
            _write_findings_plan(
                tmp_path, 'p1',
                {'test-failure.jsonl': [{'resolution': 'fixed', 'title': 'a'}]},
            ),
            _write_findings_plan(
                tmp_path, 'p2',
                {'build-error.jsonl': [{'resolution': 'fixed', 'title': 'b'}]},
            ),
        ]

        result = audit.cross_quality_chain(inputs)

        # corpus build/direct_fix cell == 2
        assert result['corpus_matrix']['build']['direct_fix'] == 2

    def test_empty_corpus_yields_zero_aggregates(self):
        result = audit.cross_quality_chain([])

        # best-effort empty, never raises
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert result['findings'] == []

    def test_emit_block_carries_severity_and_shift_left_summary(self, tmp_path: Path):
        # an auto-review-only plan with a Tier-1 regex finding
        inputs = _write_findings_plan(
            tmp_path, 'plan-shift',
            {'pr-comment.jsonl': [
                {'detail': 'gemini: regex over-fits', 'title': 'regex over-fits', 'resolution': 'fixed'}
            ]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)

        # header, the matrix/plan/finding tables, severity + shift-left
        assert 'check: quality-chain' in block
        assert 'status: success' in block
        assert 'corpus_matrix[' in block
        assert 'plans[' in block
        assert 'findings[' in block
        assert 'shift_left_tiers:' in block
        assert 'tier1=1' in block
        # the auto-review finding row is a genuine signal (D1 severity column)
        assert 'genuine' in block

    def test_per_finding_rows_emitted_for_every_finding(self, tmp_path: Path):
        # three findings across two files
        inputs = _write_findings_plan(
            tmp_path, 'plan-rows',
            {
                'test-failure.jsonl': [
                    {'resolution': 'fixed', 'title': 'one'},
                    {'resolution': 'pending', 'title': 'two'},
                ],
                'qgate-phase-6.jsonl': [{'resolution': 'fixed', 'title': 'three'}],
            },
        )
        result = audit.cross_quality_chain([inputs])

        # every finding produced a per-finding record (walk-every-finding)
        assert len(result['findings']) == 3
        titles = {f['title'] for f in result['findings']}
        assert titles == {'one', 'two', 'three'}

    def test_check_registered_in_registries(self):
        # the check is dispatchable and marked cross-plan
        assert 'quality-chain' in audit.CHECK_NAMES
        assert 'quality-chain' in audit.CROSS_PLAN_CHECKS


class TestQualityChainFindingSeverity:
    """``_qc_finding_genuine`` is the D1 severity predicate stamped onto every
    per-finding row by ``emit_quality_chain_block``. A finding is genuine
    (actionable) when it is an auto-review row (caught only at the most expensive
    stage) OR is still ``pending`` at archive time (unresolved chain debt); a
    finding cleanly resolved by an earlier mechanism is informational. The
    existing emit test only proves an auto-review row stamps ``genuine`` — these
    pin the ``pending`` branch and the informational disposition directly."""

    def test_pending_build_finding_is_genuine(self):
        # unresolved chain debt, even though build is the
        # cheapest mechanism, is a genuine signal.
        assert audit._qc_finding_genuine(
            {'mechanism': 'build', 'resolution': 'pending'}
        )

    def test_pending_self_review_finding_is_genuine(self):
        # a self-review finding left pending is debt too
        assert audit._qc_finding_genuine(
            {'mechanism': 'self-review', 'resolution': 'pending'}
        )

    def test_auto_review_finding_is_genuine_regardless_of_resolution(self):
        # auto-review is the shift-left subject; a cleanly
        # direct-fixed auto-review row is STILL genuine (it shifted right).
        assert audit._qc_finding_genuine(
            {'mechanism': 'auto-review', 'resolution': 'direct_fix'}
        )

    def test_direct_fix_build_finding_is_informational(self):
        # the expected disposition, not a signal
        assert not audit._qc_finding_genuine(
            {'mechanism': 'build', 'resolution': 'direct_fix'}
        )

    def test_lesson_self_review_finding_is_informational(self):
        # promoted-to-lesson self-review is informational
        assert not audit._qc_finding_genuine(
            {'mechanism': 'self-review', 'resolution': 'lesson'}
        )

    def test_human_review_direct_fix_is_informational(self):
        # a resolved human-review row is expected, not a signal
        assert not audit._qc_finding_genuine(
            {'mechanism': 'human-review', 'resolution': 'direct_fix'}
        )

    def test_emit_block_renders_pending_finding_row_as_genuine(self, tmp_path: Path):
        # a single self-review finding left pending (no auto-review row,
        # so the only `genuine` cell must come from the pending-branch predicate).
        inputs = _write_findings_plan(
            tmp_path,
            'plan-pending',
            {'qgate-phase-6.jsonl': [{'title': 'unguarded null', 'resolution': 'pending'}]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)
        finding_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('plan-pending,self-review,pending,')
        )

        # the pending self-review finding row ends on the genuine cell,
        # and the finding-genuine summary count reflects it.
        assert finding_line.endswith(',genuine')
        assert 'finding_genuine_signal_count: 1' in block

    def test_emit_block_renders_direct_fixed_build_finding_as_informational(
        self, tmp_path: Path
    ):
        # a single cleanly direct-fixed build finding: the expected
        # disposition, so its per-finding row must stamp informational and the
        # finding-genuine count must be zero.
        inputs = _write_findings_plan(
            tmp_path,
            'plan-clean',
            {'test-failure.jsonl': [{'title': 'flaky boundary', 'resolution': 'fixed'}]},
        )
        result = audit.cross_quality_chain([inputs])

        block = audit.emit_quality_chain_block(result)
        finding_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('plan-clean,build,direct_fix,')
        )

        assert finding_line.endswith(',informational')
        assert 'finding_genuine_signal_count: 0' in block
