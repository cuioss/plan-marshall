#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``quality-verification`` findings — which verification outcomes a plan records and
which raise a genuine signal.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _write_qv_plan(
    repo_root: Path,
    plan_id: str,
    *,
    report_md: str | None = None,
    findings_by_file: dict[str, list[dict[str, Any]]] | None = None,
) -> Any:
    """Materialise a plan carrying ``quality-verification-report.md`` and/or
    ``artifacts/findings/*.jsonl``.

    ``report_md`` is written verbatim as the report body (the check mines its
    ```json fenced blocks for ``findings`` / ``proposed_lessons``).
    ``findings_by_file`` adds JSONL findings (each list entry one line), whose
    count rolls into ``findings_present``.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'qv-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    if report_md is not None:
        (plan_dir / 'quality-verification-report.md').write_text(
            report_md, encoding='utf-8'
        )
    if findings_by_file is not None:
        findings_dir = plan_dir / 'artifacts' / 'findings'
        findings_dir.mkdir(parents=True, exist_ok=True)
        for fname, records in findings_by_file.items():
            lines = '\n'.join(_json.dumps(r) for r in records) + '\n'
            (findings_dir / fname).write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)


class TestCheckQualityVerification:
    """``check_quality_verification`` mines the report's JSON blocks for findings
    and proposed lessons, sums JSONL findings, and cross-checks proposed lessons
    against the supplied lessons-corpus signatures to surface the unfiled set."""

    def test_unfiled_lesson_surfaced(self, tmp_path: Path):
        # one proposed lesson whose title is absent from the corpus.
        report = (
            '# Quality Verification\n\n'
            '```json\n'
            '{"findings": [{"id": 1}], '
            '"proposed_lessons": [{"title": "Brand New Signature"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'unfiled', report_md=report)

        # empty corpus → the proposed lesson is unfiled
        result = audit.check_quality_verification(inputs, [])

        assert result['findings_present'] == 1
        assert result['proposed_lessons'] == 1
        assert result['unfiled_lessons'] == 1
        assert result['unfiled_signatures'] == ['Brand New Signature']

    def test_filed_lesson_excluded_from_unfiled(self, tmp_path: Path):
        # the proposed lesson title matches a corpus signature
        # (substring match is enough per ``_signature_filed``).
        report = (
            '```json\n'
            '{"proposed_lessons": [{"title": "Argparse Rejection Drift"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'filed', report_md=report)

        # corpus already carries a covering signature
        result = audit.check_quality_verification(
            inputs, ['argparse rejection drift across phase skills']
        )

        # proposed but filed → zero unfiled
        assert result['proposed_lessons'] == 1
        assert result['unfiled_lessons'] == 0
        assert result['unfiled_signatures'] == []

    def test_jsonl_findings_rolled_into_count(self, tmp_path: Path):
        # no report; two JSONL findings files contribute to the count.
        inputs = _write_qv_plan(
            tmp_path,
            'jsonl',
            findings_by_file={
                'test-failure.jsonl': [{'id': 1}, {'id': 2}],
                'pr-comment.jsonl': [{'id': 3}],
            },
        )

        result = audit.check_quality_verification(inputs, [])

        # 2 + 1 JSONL findings, no proposed lessons
        assert result['findings_present'] == 3
        assert result['proposed_lessons'] == 0
        assert result['unfiled_lessons'] == 0

    def test_report_and_jsonl_findings_combine(self, tmp_path: Path):
        # report findings AND a JSONL findings file both count.
        report = '```json\n{"findings": [{"id": 1}, {"id": 2}]}\n```\n'
        inputs = _write_qv_plan(
            tmp_path,
            'combined',
            report_md=report,
            findings_by_file={'build-error.jsonl': [{'id': 9}]},
        )

        result = audit.check_quality_verification(inputs, [])

        # 2 report + 1 JSONL = 3
        assert result['findings_present'] == 3

    def test_lessons_key_alias_and_bare_string_lessons(self, tmp_path: Path):
        # the alternate ``lessons`` key plus a bare-string lesson entry
        # (both supported by the proposed-lesson extraction).
        report = (
            '```json\n'
            '{"lessons": ["Bare String Lesson", {"signature": "Dict Lesson"}]}\n'
            '```\n'
        )
        inputs = _write_qv_plan(tmp_path, 'alias', report_md=report)

        result = audit.check_quality_verification(inputs, [])

        # both forms captured as proposed lessons
        assert result['proposed_lessons'] == 2
        assert set(result['unfiled_signatures']) == {'Bare String Lesson', 'Dict Lesson'}

    def test_missing_report_yields_empty_counts(self, tmp_path: Path):
        # a plan dir with neither report nor findings.
        plan_dir = tmp_path / '.plan' / 'temp' / 'qv-corpus' / 'empty'
        plan_dir.mkdir(parents=True, exist_ok=True)
        inputs = audit.collect_inputs(plan_dir)

        result = audit.check_quality_verification(inputs, [])

        # no inputs → all-zero, nothing unfiled
        assert result['findings_present'] == 0
        assert result['proposed_lessons'] == 0
        assert result['unfiled_lessons'] == 0
        assert result['unfiled_signatures'] == []

    def test_malformed_json_block_ignored(self, tmp_path: Path):
        # a non-JSON fenced block must not raise; it is skipped.
        report = '```json\nthis is not valid json\n```\n'
        inputs = _write_qv_plan(tmp_path, 'malformed', report_md=report)

        result = audit.check_quality_verification(inputs, [])

        # best-effort skip leaves all counts at zero
        assert result['findings_present'] == 0
        assert result['proposed_lessons'] == 0
