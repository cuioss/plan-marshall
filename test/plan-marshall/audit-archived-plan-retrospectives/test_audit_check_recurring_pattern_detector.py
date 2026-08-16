#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``cross-plan recurring pattern`` — patterns recurring across archived plans are
aggregated and threshold-gated.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit


def _write_recurring_plan(
    repo_root: Path,
    plan_id: str,
    finding_titles: list[str],
) -> Any:
    """Materialise a plan whose ``artifacts/findings/findings.jsonl`` carries
    one finding per supplied title.

    ``cross_recurring_pattern`` derives each finding's signature from its
    ``title`` (or ``type``) up to the first colon, lowercased, dedupes per plan,
    and counts the distinct plans each signature appears in.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'rp-corpus' / plan_id
    findings_dir = plan_dir / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    lines = '\n'.join(_json.dumps({'title': t}) for t in finding_titles) + '\n'
    (findings_dir / 'findings.jsonl').write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)


class TestCrossRecurringPattern:
    """``cross_recurring_pattern`` aggregates finding signatures across plans and
    surfaces any appearing in N>=3 distinct plans as a systemic signal."""

    def test_signature_in_three_plans_is_systemic(self, tmp_path: Path):
        # the same signature appears in exactly 3 plans (threshold).
        all_inputs = [
            _write_recurring_plan(tmp_path, f'plan-{i}', ['Argparse rejection: phase-5'])
            for i in range(3)
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # colon suffix stripped, signature lowercased, count 3
        assert result['threshold'] == 3
        assert result['systemic_count'] == 1
        row = result['rows'][0]
        assert row['signature'] == 'argparse rejection'
        assert row['occurrence_count'] == 3
        assert row['plan_ids'] == ['plan-0', 'plan-1', 'plan-2']

    def test_signature_below_threshold_not_systemic(self, tmp_path: Path):
        # a signature in only 2 plans stays below the N>=3 threshold.
        all_inputs = [
            _write_recurring_plan(tmp_path, 'plan-a', ['Worktree leak']),
            _write_recurring_plan(tmp_path, 'plan-b', ['Worktree leak']),
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # 2 < 3 → nothing systemic
        assert result['systemic_count'] == 0
        assert result['rows'] == []

    def test_duplicate_signature_within_plan_counts_once(self, tmp_path: Path):
        # one plan repeats a signature; two other plans carry it once.
        all_inputs = [
            _write_recurring_plan(
                tmp_path, 'dup', ['Flaky test: foo', 'Flaky test: bar']
            ),
            _write_recurring_plan(tmp_path, 'p2', ['Flaky test: baz']),
            _write_recurring_plan(tmp_path, 'p3', ['Flaky test: qux']),
        ]

        result = audit.cross_recurring_pattern(all_inputs)

        # per-plan dedup → 3 distinct plans, not 4 raw occurrences
        row = result['rows'][0]
        assert row['signature'] == 'flaky test'
        assert row['occurrence_count'] == 3
        assert sorted(row['plan_ids']) == ['dup', 'p2', 'p3']

    def test_rows_sorted_by_descending_occurrence(self, tmp_path: Path):
        # signature A in 4 plans, signature B in 3 plans.
        all_inputs = []
        for i in range(4):
            all_inputs.append(
                _write_recurring_plan(tmp_path, f'a-{i}', ['Alpha sig'])
            )
        for i in range(3):
            all_inputs.append(
                _write_recurring_plan(tmp_path, f'b-{i}', ['Beta sig'])
            )

        result = audit.cross_recurring_pattern(all_inputs)

        # both systemic; higher occurrence first
        assert result['systemic_count'] == 2
        assert result['rows'][0]['signature'] == 'alpha sig'
        assert result['rows'][0]['occurrence_count'] == 4
        assert result['rows'][1]['signature'] == 'beta sig'

    def test_type_field_used_when_title_absent(self, tmp_path: Path):
        # findings carry ``type`` instead of ``title``.
        import json as _json

        all_inputs = []
        for i in range(3):
            plan_dir = tmp_path / '.plan' / 'temp' / 'rp-corpus' / f't-{i}'
            findings_dir = plan_dir / 'artifacts' / 'findings'
            findings_dir.mkdir(parents=True, exist_ok=True)
            (findings_dir / 'f.jsonl').write_text(
                _json.dumps({'type': 'lint-issue'}) + '\n', encoding='utf-8'
            )
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_recurring_pattern(all_inputs)

        # ``type`` supplies the signature when ``title`` is missing
        assert result['systemic_count'] == 1
        assert result['rows'][0]['signature'] == 'lint-issue'

    def test_no_findings_dir_yields_no_systemic(self, tmp_path: Path):
        # plans with no artifacts/findings directory at all.
        all_inputs = []
        for i in range(3):
            plan_dir = tmp_path / '.plan' / 'temp' / 'rp-corpus' / f'bare-{i}'
            plan_dir.mkdir(parents=True, exist_ok=True)
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_recurring_pattern(all_inputs)

        # nothing to aggregate
        assert result['systemic_count'] == 0
        assert result['rows'] == []
